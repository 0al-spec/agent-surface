#!/usr/bin/env python3
"""Validate and execute the ASP v1 conformance catalog."""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
import unicodedata
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import resource
except ImportError:  # pragma: no cover - the reference runner targets POSIX.
    resource = None

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
V1_DIR = ROOT / "conformance" / "v1"
RFC_PATH = ROOT / "drafts" / "agent-surface.md"
SUITE_PATH = V1_DIR / "suite.json"
VECTORS_PATH = V1_DIR / "vectors.json"
FIXTURES_PATH = V1_DIR / "fixtures.json"
SCHEMA_CASES_PATH = V1_DIR / "schema-cases.json"
SCHEMA_NAMES = (
    "capacity-error",
    "fixtures",
    "observation",
    "operational-limits",
    "report",
    "schema-cases",
    "subject",
    "suite",
    "vectors",
)
SCHEMA_IDS = {
    name: f"https://github.com/0al-spec/agent-surface/conformance/schemas/{name}/v1"
    for name in SCHEMA_NAMES
}
CATALOG_RELATIVE_PATHS = tuple(
    sorted(
        (
            *(f"conformance/v1/{name}.schema.json" for name in SCHEMA_NAMES),
            "conformance/v1/fixtures.json",
            "conformance/v1/schema-cases.json",
            "conformance/v1/suite.json",
            "conformance/v1/vectors.json",
        )
    )
)
SUITE_ID = "https://github.com/0al-spec/agent-surface/conformance/suite/v1"
PROTOCOL_VERSION = "agent-surface/0.1"
REPORT_PROFILE = "https://github.com/0al-spec/agent-surface/conformance/report/v1"
RECEIPT_PROFILE = (
    "https://github.com/0al-spec/agent-surface/conformance/receipt-producer/v1"
)
PROFILE_ROLES = {
    "https://github.com/0al-spec/agent-surface/conformance/surface-publisher/v1": (
        "surface_publisher"
    ),
    "https://github.com/0al-spec/agent-surface/conformance/grant-issuer/v1": (
        "grant_issuer"
    ),
    "https://github.com/0al-spec/agent-surface/conformance/action-executor/v1": (
        "action_executor"
    ),
    RECEIPT_PROFILE: "receipt_producer",
    "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1": (
        "runtime_mediator"
    ),
    "https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1": (
        "agent_adapter"
    ),
}
SAFE_INTEGER = 2**53 - 1
OPERATIONAL_LIMITS_SCHEMA_ID = SCHEMA_IDS["operational-limits"]
CAPACITY_ERROR_SCHEMA_ID = SCHEMA_IDS["capacity-error"]
OPERATIONAL_LIMITS_FEATURE_ID = (
    "https://github.com/0al-spec/agent-surface/profiles/operational-limits/v1"
)
CORE_CONTROL_EVENT_IDS = frozenset(
    {"budget.warning", "budget.exceeded", "session.paused_budget", "grant.revoked"}
)
MAX_ADAPTER_OUTPUT_BYTES = 1024 * 1024
DIGEST_PATTERN = re.compile(r"^sha-256:[A-Za-z0-9_-]{43}$")
RFC3339_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$"
)
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class ConformanceError(ValueError):
    """Raised when a suite artifact or report fails closed validation."""


@dataclass(frozen=True)
class Catalog:
    """Validated canonical suite data and derived indexes."""

    root: Path
    suite: dict[str, Any]
    vector_catalog: dict[str, Any]
    fixture_catalog: dict[str, Any]
    schema_case_catalog: dict[str, Any]
    requirements: dict[str, dict[str, Any]]
    vectors: dict[str, dict[str, Any]]
    profiles: dict[str, dict[str, Any]]
    features: dict[str, dict[str, Any]]
    fixtures: dict[str, dict[str, Any]]
    mutations: dict[str, dict[str, Any]]


def _reject_float(value: str) -> None:
    raise ConformanceError(f"I-JSON floating-point values are not permitted: {value}")


def _reject_constant(value: str) -> None:
    raise ConformanceError(f"non-finite JSON value is not permitted: {value}")


def _parse_safe_integer(value: str) -> int:
    number = int(value)
    if not -SAFE_INTEGER <= number <= SAFE_INTEGER:
        raise ConformanceError(f"JSON integer is outside the I-JSON safe range: {value}")
    return number


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConformanceError(f"duplicate JSON object member: {key!r}")
        result[key] = value
    return result


def _validate_unicode(value: Any, path: str = "$") -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ConformanceError(f"unpaired Unicode surrogate at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_unicode(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_unicode(key, f"{path}.<key>")
            _validate_unicode(item, f"{path}.{key}")


def _validate_ijson_value(value: Any, path: str = "$") -> None:
    """Reject Python values that cannot have one unambiguous I-JSON encoding."""

    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -SAFE_INTEGER <= value <= SAFE_INTEGER:
            raise ConformanceError(f"JSON integer is outside the I-JSON safe range at {path}")
        return
    if isinstance(value, float):
        raise ConformanceError(f"I-JSON floating-point values are not permitted at {path}")
    if isinstance(value, str):
        _validate_unicode(value, path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_ijson_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ConformanceError(f"JSON object key is not a string at {path}")
            _validate_unicode(key, f"{path}.<key>")
            _validate_ijson_value(item, f"{path}.{key}")
        return
    raise ConformanceError(f"value at {path} is not representable as I-JSON")


def _validate_digest(value: str, path: str) -> None:
    if not DIGEST_PATTERN.fullmatch(value):
        raise ConformanceError(f"invalid SHA-256 digest at {path}")
    encoded = value.removeprefix("sha-256:")
    try:
        raw = base64.urlsafe_b64decode(encoded + "=")
    except (ValueError, binascii.Error) as error:
        raise ConformanceError(f"invalid base64url digest at {path}") from error
    canonical = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if len(raw) != 32 or canonical != encoded:
        raise ConformanceError(f"non-canonical SHA-256 digest at {path}")


def _validate_digest_members(value: Any, path: str = "$") -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_digest_members(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if key.endswith("_sha256") and isinstance(item, str):
                _validate_digest(item, item_path)
            else:
                _validate_digest_members(item, item_path)


def loads_strict_json(document: str, *, source: str = "JSON input") -> Any:
    """Parse closed I-JSON input without silently accepting duplicate keys."""

    try:
        value = json.loads(
            document,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_int=_parse_safe_integer,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ConformanceError) as error:
        raise ConformanceError(f"{source} is not strict I-JSON: {error}") from error
    _validate_unicode(value)
    _validate_ijson_value(value)
    return value


def load_strict_json(path: Path) -> Any:
    try:
        return loads_strict_json(path.read_text(encoding="utf-8"), source=str(path))
    except (OSError, UnicodeError) as error:
        raise ConformanceError(f"cannot read {path}: {error}") from error


def _format_schema_errors(validator: Draft202012Validator, value: Any) -> str:
    errors = sorted(
        validator.iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    details: list[str] = []
    for error in errors:
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        details.append(f"{path}: {error.message}")
    return "\n".join(details)


def _schema_registry(root: Path) -> Registry:
    resources = []
    for name in SCHEMA_NAMES:
        schema = load_strict_json(
            root / "conformance" / "v1" / f"{name}.schema.json"
        )
        if schema.get("$id") != SCHEMA_IDS[name]:
            raise ConformanceError(f"{name} schema has a non-canonical $id")
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _external_schema_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, list):
        for item in value:
            refs.extend(_external_schema_refs(item))
    elif isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str) and not item.startswith("#"):
                refs.append(item)
            else:
                refs.extend(_external_schema_refs(item))
    return refs


def _validate_schema_ref_closure(
    schemas: dict[str, dict[str, Any]], registry: Registry
) -> None:
    for name, schema in schemas.items():
        resolver = registry.resolver(base_uri=schema["$id"])
        for ref in _external_schema_refs(schema):
            try:
                resolver.lookup(ref)
            except Exception as error:
                raise ConformanceError(
                    f"{name} schema has an unresolved external $ref: {ref}"
                ) from error


def _validate_with_schema(
    value: Any,
    schema: dict[str, Any],
    label: str,
    *,
    registry: Registry | None = None,
) -> None:
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(
        schema,
        registry=registry or Registry(),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    details = _format_schema_errors(validator, value)
    if details:
        raise ConformanceError(f"{label} does not match its schema:\n{details}")


def validate_operational_limits(
    value: Any,
    context: dict[str, Any],
    *,
    root: Path = ROOT,
    registry: Registry | None = None,
    schema: dict[str, Any] | None = None,
) -> None:
    """Validate an Operational Limits declaration and its manifest bindings."""

    _validate_ijson_value(value)
    _validate_with_schema(
        value,
        schema
        or load_strict_json(
            root / "conformance" / "v1" / "operational-limits.schema.json"
        ),
        "Operational Limits declaration",
        registry=registry or _schema_registry(root),
    )

    context_fields = (
        "action_ids",
        "idempotency_required_action_ids",
        "event_ids",
        "control_event_ids",
    )
    if set(context) != set(context_fields):
        raise ConformanceError(
            "Operational Limits context must contain exactly action_ids, "
            "idempotency_required_action_ids, event_ids, and control_event_ids"
        )
    for field in context_fields:
        identifiers = context[field]
        if (
            not isinstance(identifiers, list)
            or any(not isinstance(item, str) or not item for item in identifiers)
            or len(identifiers) != len(set(identifiers))
        ):
            raise ConformanceError(
                f"Operational Limits context {field} must contain unique non-empty ids"
            )

    action_ids = set(context["action_ids"])
    idempotent_action_ids = set(context["idempotency_required_action_ids"])
    event_ids = set(context["event_ids"])
    control_event_ids = set(context["control_event_ids"])
    if not idempotent_action_ids.issubset(action_ids):
        raise ConformanceError(
            "idempotency_required_action_ids must be a subset of action_ids"
        )
    if not control_event_ids.issubset(event_ids):
        raise ConformanceError("control_event_ids must be a subset of event_ids")

    declared_actions = [item["action_id"] for item in value["actions"]]
    if len(declared_actions) != len(set(declared_actions)):
        raise ConformanceError("Operational Limits repeats an action_id")
    declared_events = [item["event_id"] for item in value["events"]]
    if len(declared_events) != len(set(declared_events)):
        raise ConformanceError("Operational Limits repeats an event_id")

    limit_ids: list[str] = []
    for action in value["actions"]:
        action_id = action["action_id"]
        if action_id not in action_ids:
            raise ConformanceError(
                f"Operational Limits references unknown action_id {action_id!r}"
            )
        if action_id not in idempotent_action_ids:
            raise ConformanceError(
                f"limited action {action_id!r} does not require idempotency"
            )
        limit_ids.extend(
            window["limit_id"] for window in action.get("windows", [])
        )
        if "in_flight" in action:
            limit_ids.append(action["in_flight"]["limit_id"])

    for event in value["events"]:
        event_id = event["event_id"]
        if event_id not in event_ids:
            raise ConformanceError(
                f"Operational Limits references unknown event_id {event_id!r}"
            )
        if event_id in CORE_CONTROL_EVENT_IDS or event_id in control_event_ids:
            raise ConformanceError(
                f"core control event {event_id!r} cannot be rate limited"
            )
        limit_ids.extend(window["limit_id"] for window in event["windows"])

    duplicate_limit_ids = sorted(
        identifier
        for identifier, count in Counter(limit_ids).items()
        if count > 1
    )
    if duplicate_limit_ids:
        raise ConformanceError(
            "Operational Limits repeats limit_id values: "
            + ", ".join(duplicate_limit_ids)
        )


def validate_capacity_error(
    value: Any,
    context: dict[str, Any],
    *,
    root: Path = ROOT,
    registry: Registry | None = None,
    schema: dict[str, Any] | None = None,
) -> None:
    """Validate a capacity envelope and privacy-safe active-partition binding."""

    _validate_ijson_value(value)
    _validate_with_schema(
        value,
        schema
        or load_strict_json(
            root / "conformance" / "v1" / "capacity-error.schema.json"
        ),
        "capacity error envelope",
        registry=registry or _schema_registry(root),
    )
    context_fields = ("declared_limit_ids", "disclosable_limit_ids")
    if set(context) != set(context_fields):
        raise ConformanceError(
            "capacity error context must contain exactly declared_limit_ids "
            "and disclosable_limit_ids"
        )
    for field in context_fields:
        identifiers = context[field]
        if (
            not isinstance(identifiers, list)
            or any(not isinstance(item, str) or not item for item in identifiers)
            or len(identifiers) != len(set(identifiers))
        ):
            raise ConformanceError(
                f"capacity error context {field} must contain unique non-empty ids"
            )
    declared_limit_ids = set(context["declared_limit_ids"])
    disclosable_limit_ids = set(context["disclosable_limit_ids"])
    if not disclosable_limit_ids.issubset(declared_limit_ids):
        raise ConformanceError(
            "disclosable_limit_ids must be a subset of declared_limit_ids"
        )
    disclosed_limit_ids = set(value.get("limit", {}).get("limit_ids", []))
    undisclosable = sorted(disclosed_limit_ids - disclosable_limit_ids)
    if undisclosable:
        raise ConformanceError(
            "capacity error discloses an undeclared or cross-partition limit_id: "
            + ", ".join(undisclosable)
        )


def _validate_schema_cases(
    root: Path,
    catalog: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
    registry: Registry,
) -> None:
    case_ids = [item["case_id"] for item in catalog["cases"]]
    if len(case_ids) != len(set(case_ids)):
        raise ConformanceError("schema case catalog repeats a case_id")

    polarities: dict[str, set[str]] = {
        OPERATIONAL_LIMITS_SCHEMA_ID: set(),
        CAPACITY_ERROR_SCHEMA_ID: set(),
    }
    for case in catalog["cases"]:
        schema_id = case["schema_id"]
        expected_prefix = (
            "ASP-SC-OL-"
            if schema_id == OPERATIONAL_LIMITS_SCHEMA_ID
            else "ASP-SC-CE-"
        )
        if not case["case_id"].startswith(expected_prefix):
            raise ConformanceError(
                f"schema case {case['case_id']} has a mismatched schema prefix"
            )
        polarities[schema_id].add(case["polarity"])

        error: ConformanceError | None = None
        try:
            instance = loads_strict_json(
                case["instance_json"], source=f"schema case {case['case_id']}"
            )
            if schema_id == OPERATIONAL_LIMITS_SCHEMA_ID:
                validate_operational_limits(
                    instance,
                    case["context"],
                    root=root,
                    registry=registry,
                    schema=schemas["operational-limits"],
                )
            else:
                validate_capacity_error(
                    instance,
                    case["context"],
                    root=root,
                    registry=registry,
                    schema=schemas["capacity-error"],
                )
        except ConformanceError as caught:
            error = caught

        if case["polarity"] == "positive" and error is not None:
            raise ConformanceError(
                f"positive schema case {case['case_id']} failed: {error}"
            ) from error
        if case["polarity"] == "negative" and error is None:
            raise ConformanceError(
                f"negative schema case {case['case_id']} unexpectedly passed"
            )

    for schema_id, actual in polarities.items():
        if actual != {"positive", "negative"}:
            raise ConformanceError(
                f"schema case catalog requires both polarities for {schema_id}"
            )


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "section"


def _rfc_anchor_ids(rfc_path: Path) -> set[str]:
    occurrences: Counter[str] = Counter()
    anchors: set[str] = set()
    for line in rfc_path.read_text(encoding="utf-8").splitlines():
        match = HEADING_PATTERN.match(line)
        if not match:
            continue
        title = match.group(2).rstrip("#").strip()
        occurrences[title] += 1
        anchor = _slugify(title)
        if occurrences[title] > 1:
            anchor = f"{anchor}-{occurrences[title]}"
        anchors.add(anchor)
    return anchors


def _unique_index(
    items: list[dict[str, Any]], key: str, label: str
) -> dict[str, dict[str, Any]]:
    identifiers = [item[key] for item in items]
    duplicates = sorted(
        identifier
        for identifier, count in Counter(identifiers).items()
        if count > 1
    )
    if duplicates:
        raise ConformanceError(f"duplicate {label} ids: {', '.join(duplicates)}")
    return {item[key]: item for item in items}


def _semantic_validate_catalog(
    root: Path,
    suite: dict[str, Any],
    vector_catalog: dict[str, Any],
    fixture_catalog: dict[str, Any],
    schema_case_catalog: dict[str, Any],
) -> Catalog:
    if (
        suite["suite_id"] != SUITE_ID
        or vector_catalog["suite_id"] != SUITE_ID
        or fixture_catalog["suite_id"] != SUITE_ID
        or schema_case_catalog["suite_id"] != SUITE_ID
    ):
        raise ConformanceError("catalog suite_id must be the exact ASP v1 suite identifier")
    if len(
        {
            suite["suite_version"],
            vector_catalog["suite_version"],
            fixture_catalog["suite_version"],
            schema_case_catalog["suite_version"],
        }
    ) != 1:
        raise ConformanceError("suite, vector, and fixture catalog versions differ")
    if suite["protocol_version"] != PROTOCOL_VERSION:
        raise ConformanceError("suite protocol_version must be exactly agent-surface/0.1")
    specification = suite["specification"]
    if specification["path"] != "drafts/agent-surface.md":
        raise ConformanceError("suite specification path is not canonical")
    if specification["hash_domain"] != "ASP-SPECIFICATION-SOURCE-V1":
        raise ConformanceError("suite specification hash domain is not canonical")

    profiles = _unique_index(suite["profiles"], "profile_id", "profile")
    if set(profiles) != set(PROFILE_ROLES):
        raise ConformanceError("suite must register exactly the six ASP v1 role profiles")
    for profile_id, expected_role in PROFILE_ROLES.items():
        if profiles[profile_id]["role"] != expected_role:
            raise ConformanceError(f"profile {profile_id} has the wrong role")

    features = _unique_index(suite["features"], "feature_id", "feature")
    requirements = _unique_index(
        suite["requirements"], "requirement_id", "requirement"
    )
    vectors = _unique_index(vector_catalog["vectors"], "vector_id", "vector")
    fixtures = _unique_index(fixture_catalog["fixtures"], "fixture_id", "fixture")
    mutations = _unique_index(fixture_catalog["mutations"], "mutation_id", "mutation")
    fixtures_by_baseline = _unique_index(
        fixture_catalog["fixtures"], "baseline_vector_id", "fixture baseline"
    )
    mutations_by_variant = _unique_index(
        fixture_catalog["mutations"], "input_variant", "fixture mutation variant"
    )
    rfc_anchors = _rfc_anchor_ids(root / specification["path"])
    for feature_id, feature in features.items():
        if feature["rfc_anchor"] not in rfc_anchors:
            raise ConformanceError(
                f"feature {feature_id} references unknown RFC anchor "
                f"{feature['rfc_anchor']!r}"
            )

    requirement_ids_by_profile: dict[str, list[str]] = {
        profile_id: [] for profile_id in profiles
    }
    requirement_ids_by_feature: dict[str, list[str]] = {
        feature_id: [] for feature_id in features
    }
    vectors_by_requirement: dict[str, list[str]] = {
        requirement_id: [] for requirement_id in requirements
    }

    for requirement_id, requirement in requirements.items():
        profile_id = requirement["profile_id"]
        if profile_id not in profiles:
            raise ConformanceError(
                f"requirement {requirement_id} references unknown profile {profile_id}"
            )
        if requirement["rfc_anchor"] not in rfc_anchors:
            raise ConformanceError(
                f"requirement {requirement_id} references unknown RFC anchor "
                f"{requirement['rfc_anchor']!r}"
            )
        requirement_ids_by_profile[profile_id].append(requirement_id)
        applicability = requirement["applicability"]
        if applicability["kind"] == "feature":
            feature_id = applicability["feature_id"]
            if feature_id not in features:
                raise ConformanceError(
                    f"requirement {requirement_id} references unknown feature {feature_id}"
                )
            requirement_ids_by_feature[feature_id].append(requirement_id)
        if (
            applicability["kind"] == "producer_role"
            and profile_id != RECEIPT_PROFILE
        ):
            raise ConformanceError(
                f"non-Receipt requirement {requirement_id} uses producer_role applicability"
            )
        vector_ids = requirement["vector_ids"]
        if len(vector_ids) != len(set(vector_ids)):
            raise ConformanceError(f"requirement {requirement_id} repeats a vector id")
        for vector_id in vector_ids:
            if vector_id not in vectors:
                raise ConformanceError(
                    f"requirement {requirement_id} references unknown vector {vector_id}"
                )
            vectors_by_requirement[requirement_id].append(vector_id)

    for profile_id, profile in profiles.items():
        if profile["requirement_ids"] != requirement_ids_by_profile[profile_id]:
            raise ConformanceError(
                f"profile {profile_id} requirement_ids are not the canonical matrix order"
            )
    for feature_id, feature in features.items():
        if feature["requirement_ids"] != requirement_ids_by_feature[feature_id]:
            raise ConformanceError(
                f"feature {feature_id} requirement_ids are not the canonical matrix order"
            )

    polarities_by_profile: dict[str, set[str]] = {
        profile_id: set() for profile_id in profiles
    }
    receipt_polarities: dict[str, set[str]] = {
        "application": set(),
        "runtime": set(),
    }
    used_fixtures: set[str] = set()
    used_mutations: set[str] = set()
    for vector_id, vector in vectors.items():
        profile_id = vector["profile_id"]
        if profile_id not in profiles:
            raise ConformanceError(
                f"vector {vector_id} references unknown profile {profile_id}"
            )
        if profile_id == RECEIPT_PROFILE:
            receipt_polarities[vector["producer_role"]].add(vector["polarity"])
        elif "producer_role" in vector:
            raise ConformanceError(
                f"non-Receipt vector {vector_id} declares producer_role"
            )
        polarities_by_profile[profile_id].add(vector["polarity"])
        baseline_id = vector.get("baseline_vector_id", vector_id)
        input_variant = vector["stimulus"]["input_variant"]
        fixture = fixtures_by_baseline.get(baseline_id)
        mutation = mutations_by_variant.get(input_variant)
        if fixture is None or mutation is None:
            raise ConformanceError(
                f"vector {vector_id} references an unknown fixture or mutation"
            )
        used_fixtures.add(fixture["fixture_id"])
        used_mutations.add(mutation["mutation_id"])

        referenced_requirements = vector["requirement_ids"]
        expected_requirements = [
            requirement_id
            for requirement_id, required_vector_ids in vectors_by_requirement.items()
            if vector_id in required_vector_ids
        ]
        if referenced_requirements != expected_requirements:
            raise ConformanceError(
                f"vector {vector_id} requirement mapping is not reciprocal and ordered"
            )
        applicability_values = {
            json.dumps(requirements[item]["applicability"], sort_keys=True)
            for item in referenced_requirements
        }
        if len(applicability_values) != 1:
            raise ConformanceError(
                f"vector {vector_id} mixes requirements with different applicability"
            )
        if any(
            requirements[item]["profile_id"] != profile_id
            for item in referenced_requirements
        ):
            raise ConformanceError(f"vector {vector_id} crosses target role profiles")
        if any(
            requirements[item]["execution_class"] != vector["execution_class"]
            for item in referenced_requirements
        ):
            raise ConformanceError(
                f"vector {vector_id} execution_class differs from its matrix row"
            )
        unknown_features = set(vector["features"]) - set(features)
        if unknown_features:
            raise ConformanceError(
                f"vector {vector_id} references unknown features: "
                + ", ".join(sorted(unknown_features))
            )
        required_feature_ids = {
            requirements[item]["applicability"]["feature_id"]
            for item in referenced_requirements
            if requirements[item]["applicability"]["kind"] == "feature"
        }
        if not required_feature_ids.issubset(vector["features"]):
            raise ConformanceError(
                f"vector {vector_id} omits its applicability feature"
            )
        has_operational_feature = OPERATIONAL_LIMITS_FEATURE_ID in vector["features"]
        has_operational_state = "operational" in fixture["document"]
        if has_operational_feature != has_operational_state:
            raise ConformanceError(
                f"Operational Limits vector {vector_id} feature selection and "
                "fixture state differ"
            )
        if has_operational_feature:
            operational_state = fixture["document"]["operational"]
            if not set(operational_state["disclosable_limit_ids"]).issubset(
                operational_state["declared_limit_ids"]
            ):
                raise ConformanceError(
                    f"Operational Limits vector {vector_id} has unsafe limit disclosure state"
                )
            capacity_response = operational_state["capacity_response"]
            if isinstance(capacity_response, dict):
                validate_capacity_error(
                    capacity_response,
                    {
                        "declared_limit_ids": operational_state[
                            "declared_limit_ids"
                        ],
                        "disclosable_limit_ids": operational_state[
                            "disclosable_limit_ids"
                        ],
                    },
                    root=root,
                )
        if vector["polarity"] == "negative":
            baseline_id = vector["baseline_vector_id"]
            baseline = vectors.get(baseline_id)
            if baseline is None or baseline["polarity"] != "positive":
                raise ConformanceError(
                    f"negative vector {vector_id} lacks a positive baseline"
                )
            if baseline["profile_id"] != profile_id:
                raise ConformanceError(
                    f"negative vector {vector_id} baseline targets another profile"
                )
            if baseline.get("producer_role") != vector.get("producer_role"):
                raise ConformanceError(
                    f"negative vector {vector_id} baseline uses another producer role"
                )
        elif "baseline_vector_id" in vector:
            raise ConformanceError(
                f"positive vector {vector_id} must not declare baseline_vector_id"
            )
        required_tokens = set(vector["required_observations"])
        forbidden_tokens = set(vector["forbidden_observations"])
        overlap = sorted(required_tokens & forbidden_tokens)
        if overlap:
            raise ConformanceError(
                f"vector {vector_id} both requires and forbids: {', '.join(overlap)}"
            )
        states = [item["state"] for item in vector["state_deltas"]]
        if len(states) != len(set(states)):
            raise ConformanceError(f"vector {vector_id} repeats a state delta")

    for profile_id, polarities in polarities_by_profile.items():
        if polarities != {"positive", "negative"}:
            raise ConformanceError(
                f"profile {profile_id} requires positive and negative vectors"
            )
    for producer_role, polarities in receipt_polarities.items():
        if polarities != {"positive", "negative"}:
            raise ConformanceError(
                f"Receipt Producer role {producer_role} requires positive and negative vectors"
            )
    if used_fixtures != set(fixtures):
        raise ConformanceError("fixture catalog contains unused or unreferenced fixtures")
    if used_mutations != set(mutations):
        raise ConformanceError("fixture catalog contains unused or unreferenced mutations")

    return Catalog(
        root=root,
        suite=suite,
        vector_catalog=vector_catalog,
        fixture_catalog=fixture_catalog,
        schema_case_catalog=schema_case_catalog,
        requirements=requirements,
        vectors=vectors,
        profiles=profiles,
        features=features,
        fixtures=fixtures,
        mutations=mutations,
    )


def validate_catalog(root: Path = ROOT) -> Catalog:
    """Validate JSON Schemas, catalog shapes, RFC anchors, and matrix closure."""

    root = root.resolve()
    v1_dir = root / "conformance" / "v1"
    schema_paths = {
        name: v1_dir / f"{name}.schema.json" for name in SCHEMA_NAMES
    }
    schemas = {name: load_strict_json(path) for name, path in schema_paths.items()}
    for name, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as error:
            raise ConformanceError(f"invalid {name} JSON Schema: {error}") from error
    suite = load_strict_json(v1_dir / "suite.json")
    vector_catalog = load_strict_json(v1_dir / "vectors.json")
    fixture_catalog = load_strict_json(v1_dir / "fixtures.json")
    schema_case_catalog = load_strict_json(v1_dir / "schema-cases.json")
    registry = _schema_registry(root)
    _validate_schema_ref_closure(schemas, registry)
    _validate_with_schema(suite, schemas["suite"], "suite.json", registry=registry)
    _validate_with_schema(
        vector_catalog, schemas["vectors"], "vectors.json", registry=registry
    )
    _validate_with_schema(
        fixture_catalog, schemas["fixtures"], "fixtures.json", registry=registry
    )
    _validate_with_schema(
        schema_case_catalog,
        schemas["schema-cases"],
        "schema-cases.json",
        registry=registry,
    )
    _validate_schema_cases(root, schema_case_catalog, schemas, registry)
    return _semantic_validate_catalog(
        root, suite, vector_catalog, fixture_catalog, schema_case_catalog
    )


def _domain_digest(domain: str, content: bytes) -> str:
    digest = hashlib.sha256(domain.encode("ascii") + b"\x00" + content).digest()
    return "sha-256:" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def catalog_digest(root: Path = ROOT) -> str:
    payload = bytearray()
    for relative_path in CATALOG_RELATIVE_PATHS:
        path = root / relative_path
        payload.extend(path.relative_to(root).as_posix().encode("utf-8"))
        payload.extend(b"\x00")
        payload.extend(path.read_bytes())
        payload.extend(b"\x00")
    return _domain_digest("ASP-CONFORMANCE-CATALOG-V1", bytes(payload))


def specification_digest(root: Path = ROOT) -> str:
    return _domain_digest(
        "ASP-SPECIFICATION-SOURCE-V1",
        (root / "drafts" / "agent-surface.md").read_bytes(),
    )


def _canonical_json_bytes(value: dict[str, Any]) -> bytes:
    # The catalog and subject schemas permit only I-JSON integers and ASCII
    # member names, making this compact, sorted serialization identical to
    # RFC 8785 for these closed objects.
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def vector_digest(vector: dict[str, Any]) -> str:
    return _domain_digest("ASP-CONFORMANCE-VECTOR-V1", _canonical_json_bytes(vector))


def subject_digest(subject: dict[str, Any]) -> str:
    return _domain_digest("ASP-CONFORMANCE-SUBJECT-V1", _canonical_json_bytes(subject))


def _schema_for(catalog: Catalog, name: str) -> dict[str, Any]:
    return load_strict_json(catalog.root / "conformance" / "v1" / f"{name}.schema.json")


def validate_subject(subject: dict[str, Any], catalog: Catalog) -> None:
    _validate_ijson_value(subject)
    _validate_digest_members(subject)
    _validate_with_schema(
        subject,
        _schema_for(catalog, "subject"),
        "subject",
        registry=_schema_registry(catalog.root),
    )
    profile_id = subject["profile_id"]
    if profile_id not in catalog.profiles:
        raise ConformanceError(f"subject references unknown profile {profile_id}")
    if subject["protocol_version"] != catalog.suite["protocol_version"]:
        raise ConformanceError("subject protocol_version does not match the suite")
    unknown_features = sorted(set(subject["features"]) - set(catalog.features))
    if unknown_features:
        raise ConformanceError(
            "subject references unknown features: "
            + ", ".join(unknown_features)
        )
    if subject["features"] != sorted(subject["features"]):
        raise ConformanceError("subject features must use canonical lexicographic order")
    if profile_id == RECEIPT_PROFILE and "producer_role" not in subject:
        raise ConformanceError("Receipt Producer subject requires producer_role")
    if profile_id != RECEIPT_PROFILE and "producer_role" in subject:
        raise ConformanceError("producer_role is forbidden for this profile")


def _requirement_is_applicable(
    requirement: dict[str, Any], subject: dict[str, Any]
) -> tuple[bool, str]:
    applicability = requirement["applicability"]
    if applicability["kind"] == "always":
        return True, "always"
    if applicability["kind"] == "feature":
        feature_id = applicability["feature_id"]
        return feature_id in subject["features"], f"feature_not_selected:{feature_id}"
    producer_role = applicability["producer_role"]
    return (
        subject.get("producer_role") == producer_role,
        f"producer_role_mismatch:{producer_role}",
    )


def applicable_vectors(
    catalog: Catalog, subject: dict[str, Any]
) -> tuple[list[str], list[dict[str, str]], list[str]]:
    applicable: list[str] = []
    not_applicable: list[dict[str, str]] = []
    applicable_seen: set[str] = set()
    not_applicable_seen: set[str] = set()
    profile = catalog.profiles[subject["profile_id"]]
    for requirement_id in profile["requirement_ids"]:
        requirement = catalog.requirements[requirement_id]
        is_applicable, reason = _requirement_is_applicable(requirement, subject)
        for vector_id in requirement["vector_ids"]:
            vector = catalog.vectors[vector_id]
            vector_role_matches = (
                vector.get("producer_role") is None
                or vector.get("producer_role") == subject.get("producer_role")
            )
            if not vector_role_matches:
                is_vector_applicable = False
                vector_reason = "producer_role_mismatch"
            else:
                is_vector_applicable = is_applicable
                vector_reason = (
                    "feature_not_selected"
                    if reason.startswith("feature_not_selected:")
                    else "producer_role_mismatch"
                )
            if is_vector_applicable:
                if vector_id not in applicable_seen:
                    applicable.append(vector_id)
                    applicable_seen.add(vector_id)
            elif vector_id not in not_applicable_seen:
                not_applicable.append(
                    {
                        "vector_id": vector_id,
                        "reason": vector_reason,
                    }
                )
                not_applicable_seen.add(vector_id)
    overlap = applicable_seen & not_applicable_seen
    if overlap:
        raise ConformanceError(
            "matrix gives conflicting applicability to vectors: "
            + ", ".join(sorted(overlap))
        )
    covered_features = {
        requirement["applicability"]["feature_id"]
        for requirement in catalog.requirements.values()
        if requirement["profile_id"] == subject["profile_id"]
        and requirement["applicability"]["kind"] == "feature"
    }
    uncovered_features = sorted(set(subject["features"]) - covered_features)
    return applicable, not_applicable, uncovered_features


def _compare_observation(
    vector: dict[str, Any], observation: dict[str, Any]
) -> tuple[bool, str | None]:
    if observation["vector_id"] != vector["vector_id"]:
        return False, "vector_id_mismatch"
    for expected_member, observed_member in (
        ("expected_error", "asp_error"),
        ("expected_policy_reason", "policy_reason"),
        ("expected_match_reason", "match_reason"),
    ):
        if observation.get(observed_member) != vector.get(expected_member):
            return False, f"{observed_member}_mismatch"
    tokens = set(observation["tokens"])
    required_tokens = set(vector["required_observations"])
    if tokens != required_tokens:
        return False, "observation_token_set_mismatch"
    forbidden = set(vector["forbidden_observations"]) & tokens
    if forbidden:
        return False, "forbidden_observation_present"
    expected_deltas = sorted(
        vector["state_deltas"], key=lambda item: item["state"]
    )
    observed_deltas = sorted(
        observation["state_deltas"], key=lambda item: item["state"]
    )
    if observed_deltas != expected_deltas:
        return False, "state_delta_mismatch"
    return True, None


def file_digest(domain: str, path: Path) -> str:
    try:
        content = path.read_bytes()
    except OSError as error:
        raise ConformanceError(f"cannot hash executable {path}: {error}") from error
    return _domain_digest(domain, content)


def counterpart_digest(counterpart: dict[str, Any]) -> str:
    return _domain_digest(
        "ASP-CONFORMANCE-COUNTERPART-V1", _canonical_json_bytes(counterpart)
    )


def harness_digest(runner: dict[str, Any]) -> str:
    return _domain_digest("ASP-CONFORMANCE-HARNESS-V1", _canonical_json_bytes(runner))


def _subject_locator(subject: dict[str, Any]) -> dict[str, Any]:
    locator = {
        "subject_id": subject["subject_id"],
        "boundary_id": subject["boundary_id"],
        "implementation": subject["implementation"],
        "profile_id": subject["profile_id"],
        "protocol_version": subject["protocol_version"],
    }
    if "producer_role" in subject:
        locator["producer_role"] = subject["producer_role"]
    return locator


def _limit_child_resources() -> None:
    if resource is None:
        return
    resource.setrlimit(
        resource.RLIMIT_FSIZE,
        (MAX_ADAPTER_OUTPUT_BYTES, MAX_ADAPTER_OUTPUT_BYTES),
    )
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CPU, (31, 31))


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _execute_json_process(
    *,
    executable: Path,
    invocation: dict[str, Any],
    workdir: Path,
    timeout_seconds: int,
    label: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Execute one closed JSON exchange with bounded output and process-group cleanup."""

    output_path = workdir / f"{label}.stdout"
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(workdir),
        "TMPDIR": str(workdir),
        "LANG": "C.UTF-8",
        "ASP_CONFORMANCE_RUN_ID": invocation["run_id"],
        "ASP_CONFORMANCE_VECTOR_ID": invocation.get("vector_id", "inventory"),
    }
    payload = json.dumps(
        invocation, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    process: subprocess.Popen[bytes] | None = None
    try:
        with output_path.open("wb") as output:
            process = subprocess.Popen(
                [str(executable)],
                stdin=subprocess.PIPE,
                stdout=output,
                stderr=subprocess.DEVNULL,
                cwd=workdir,
                env=environment,
                start_new_session=True,
                preexec_fn=_limit_child_resources if resource is not None else None,
            )
            try:
                process.communicate(input=payload, timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _kill_process_group(process)
                process.wait()
                return None, "timeout"
            finally:
                if process.poll() is not None:
                    _kill_process_group(process)
    except OSError:
        return None, "unavailable"
    if process is None or process.returncode != 0:
        return None, "failed"
    try:
        if output_path.stat().st_size >= MAX_ADAPTER_OUTPUT_BYTES:
            return None, "invalid_output"
        document = output_path.read_bytes().decode("utf-8", errors="strict")
        response = loads_strict_json(document, source=f"{label} response")
        if not isinstance(response, dict):
            raise ConformanceError(f"{label} response must be a JSON object")
    except (OSError, UnicodeError, ConformanceError):
        return None, "invalid_output"
    return response, None


def _required_counterpart_digests(
    vector: dict[str, Any], subject: dict[str, Any]
) -> list[str] | None:
    required = vector.get("required_counterparts", [])
    matched: list[dict[str, Any]] = []
    for requirement in required:
        candidates = [
            counterpart
            for counterpart in subject["counterparts"]
            if counterpart["kind"] == "implementation"
            and counterpart["profile_id"] == requirement["profile_id"]
            and counterpart.get("producer_role") == requirement.get("producer_role")
            and counterpart["boundary_id"] != subject["boundary_id"]
            and counterpart["artifact_sha256"]
            != subject["implementation"]["artifact_sha256"]
            and counterpart not in matched
        ]
        if len(candidates) != 1:
            return None
        matched.append(candidates[0])
    return [counterpart_digest(item) for item in matched]


def _resolved_fixture(catalog: Catalog, vector: dict[str, Any]) -> dict[str, Any]:
    baseline_id = vector.get("baseline_vector_id", vector["vector_id"])
    fixture = next(
        item
        for item in catalog.fixtures.values()
        if item["baseline_vector_id"] == baseline_id
    )
    mutation = next(
        item
        for item in catalog.mutations.values()
        if item["input_variant"] == vector["stimulus"]["input_variant"]
    )
    document = copy.deepcopy(fixture["document"])
    for operation in mutation["patch"]:
        if operation["op"] != "replace":
            raise ConformanceError("v1 fixture runner supports only closed replace patches")
        parts = operation["path"].removeprefix("/").split("/")
        if len(parts) != 2 or parts[0] not in document or parts[1] not in document[parts[0]]:
            raise ConformanceError("fixture mutation path is not present in its baseline")
        document[parts[0]][parts[1]] = operation["value"]
    _validate_with_schema(
        document,
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": SCHEMA_IDS["fixtures"] + "#/$defs/semanticDocument",
        },
        "resolved fixture",
        registry=_schema_registry(catalog.root),
    )
    return {
        "fixture_id": fixture["fixture_id"],
        "mutation_id": mutation["mutation_id"],
        "input_variant": mutation["input_variant"],
        "document": document,
    }


def _adapter_case(catalog: Catalog, vector: dict[str, Any]) -> dict[str, Any]:
    """Return the stimulus-only vector view; the assertion oracle stays in the runner."""

    case = {
        "vector_id": vector["vector_id"],
        "profile_id": vector["profile_id"],
        "execution_class": vector["execution_class"],
        "setup": vector["setup"],
        "initial_state": [
            {"state": item["state"], "value": item["before"]}
            for item in vector["state_deltas"]
        ],
        "stimulus": {
            "operation": vector["stimulus"]["operation"],
            "fixture": _resolved_fixture(catalog, vector),
        },
        "required_counterparts": vector.get("required_counterparts", []),
    }
    if "producer_role" in vector:
        case["producer_role"] = vector["producer_role"]
    return case


def _validate_adapter_ack(
    response: dict[str, Any], *, run_id: str, vector_id: str
) -> None:
    expected = {
        "schema_version": 1,
        "run_id": run_id,
        "vector_id": vector_id,
        "status": "completed",
    }
    if response != expected:
        raise ConformanceError("adapter acknowledgement is not the exact closed shape")


def _validate_inventory(
    inventory: dict[str, Any],
    *,
    run_id: str,
    expected_subject_sha256: str,
    expected_harness_sha256: str,
    catalog: Catalog,
) -> None:
    if set(inventory) != {
        "schema_version",
        "run_id",
        "subject_sha256",
        "harness_sha256",
        "captured_at",
        "feature_ids",
    }:
        raise ConformanceError("feature inventory is not the exact closed shape")
    if (
        inventory["schema_version"] != 1
        or inventory["run_id"] != run_id
        or inventory["subject_sha256"] != expected_subject_sha256
        or inventory["harness_sha256"] != expected_harness_sha256
    ):
        raise ConformanceError("feature inventory binding is invalid")
    if (
        not isinstance(inventory["feature_ids"], list)
        or len(inventory["feature_ids"]) != len(set(inventory["feature_ids"]))
        or any(item not in catalog.features for item in inventory["feature_ids"])
    ):
        raise ConformanceError("feature inventory contains unknown or duplicate features")
    _parse_timestamp(inventory["captured_at"])


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _summary(
    results: list[dict[str, Any]],
    not_applicable_count: int,
    *,
    uncovered_features: list[str],
    subject_kind: str,
) -> dict[str, Any]:
    counts = Counter(result["status"] for result in results)
    incomplete_reasons: list[str] = []
    if counts["error"]:
        incomplete_reasons.append("execution_error")
    if uncovered_features:
        incomplete_reasons.append("uncovered_feature")
    if subject_kind == "suite_fixture":
        incomplete_reasons.append("suite_fixture")
    if counts["fail"]:
        verdict = "fail"
    elif incomplete_reasons:
        verdict = "incomplete"
    else:
        verdict = "pass"
    return {
        "suite_verdict": verdict,
        "total": len(results),
        "passed": counts["pass"],
        "failed": counts["fail"],
        "errors": counts["error"],
        "not_applicable": not_applicable_count,
        "incomplete_reasons": incomplete_reasons,
    }


def _is_bundled_fixture_executable(executable: Path, root: Path) -> bool:
    """Recognize canonical or byte-identical repository fixture executables."""

    fixture_directories = (
        root / "conformance" / "tests",
        root / "mocks",
    )
    executable_bytes = executable.read_bytes()
    executable_digest = hashlib.sha256(executable_bytes).digest()
    for directory in fixture_directories:
        if not directory.exists():
            continue
        resolved_directory = directory.resolve()
        if executable.is_relative_to(resolved_directory):
            return True
        for candidate in resolved_directory.rglob("*.py"):
            if (
                candidate.is_file()
                and os.access(candidate, os.X_OK)
                and hashlib.sha256(candidate.read_bytes()).digest()
                == executable_digest
            ):
                return True
    return False


def run_suite(
    *,
    subject: dict[str, Any],
    adapter: Path,
    probe: Path,
    adapter_id: str,
    adapter_version: str,
    adapter_configuration_sha256: str,
    probe_id: str,
    probe_version: str,
    probe_configuration_sha256: str,
    timeout_seconds: int = 10,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Execute every applicable vector and return a validated report object."""

    if not 1 <= timeout_seconds <= 30:
        raise ConformanceError("adapter timeout must be between 1 and 30 seconds")
    _validate_digest(adapter_configuration_sha256, "adapter configuration")
    _validate_digest(probe_configuration_sha256, "probe configuration")
    executables = {
        "adapter": adapter.expanduser().resolve(),
        "probe": probe.expanduser().resolve(),
    }
    for label, executable in executables.items():
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ConformanceError(f"{label} must be one executable file path")
    adapter = executables["adapter"]
    probe = executables["probe"]
    catalog = validate_catalog(root)
    validate_subject(subject, catalog)
    if subject["subject_kind"] == "implementation" and any(
        _is_bundled_fixture_executable(executable, root)
        for executable in executables.values()
    ):
        raise ConformanceError(
            "repository reference fixtures cannot produce implementation evidence"
        )
    observation_schema = _schema_for(catalog, "observation")
    run_id = f"urn:uuid:{uuid.uuid4()}"
    started_at = _utc_now()
    runner = {
        "runner_id": "asp-reference-conformance-runner",
        "runner_version": "1.1.0",
        "runner_artifact_sha256": file_digest(
            "ASP-CONFORMANCE-RUNNER-V1", root / "conformance" / "check.py"
        ),
        "adapter_id": adapter_id,
        "adapter_version": adapter_version,
        "adapter_artifact_sha256": file_digest(
            "ASP-CONFORMANCE-ADAPTER-V1", adapter
        ),
        "adapter_configuration_sha256": adapter_configuration_sha256,
        "probe_id": probe_id,
        "probe_version": probe_version,
        "probe_artifact_sha256": file_digest("ASP-CONFORMANCE-PROBE-V1", probe),
        "probe_configuration_sha256": probe_configuration_sha256,
        "timeout_seconds": timeout_seconds,
        "execution_environment": {
            "os": platform.system().lower(),
            "architecture": platform.machine().lower(),
            "python": platform.python_version(),
        },
    }
    subject_sha256 = subject_digest(subject)
    harness_sha256 = harness_digest(runner)

    with tempfile.TemporaryDirectory(prefix="asp-conformance-inventory-") as directory:
        inventory, inventory_error = _execute_json_process(
            executable=probe,
            invocation={
                "probe_protocol": "asp-conformance-probe/1",
                "operation": "inventory",
                "run_id": run_id,
                "subject_sha256": subject_sha256,
                "harness_sha256": harness_sha256,
                "subject_locator": _subject_locator(subject),
            },
            workdir=Path(directory),
            timeout_seconds=timeout_seconds,
            label="inventory",
        )
    if inventory_error is not None or inventory is None:
        raise ConformanceError("authoritative feature inventory is unavailable")
    _validate_inventory(
        inventory,
        run_id=run_id,
        expected_subject_sha256=subject_sha256,
        expected_harness_sha256=harness_sha256,
        catalog=catalog,
    )
    if inventory["feature_ids"] != subject["features"]:
        raise ConformanceError(
            "observed feature inventory differs from the declared exact scope"
        )
    applicable, not_applicable, uncovered_features = applicable_vectors(
        catalog, subject
    )
    results: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []

    for vector_id in applicable:
        vector = catalog.vectors[vector_id]
        expected_counterpart_digests = _required_counterpart_digests(vector, subject)
        if expected_counterpart_digests is None:
            results.append(
                {
                    "vector_id": vector_id,
                    "vector_sha256": vector_digest(vector),
                    "status": "error",
                    "requirement_ids": vector["requirement_ids"],
                    "observation_ids": [],
                    "failure_token": "unavailable_probe",
                }
            )
            continue
        with tempfile.TemporaryDirectory(prefix="asp-conformance-") as directory:
            workdir = Path(directory)
            common_binding = {
                "run_id": run_id,
                "subject_sha256": subject_sha256,
                "harness_sha256": harness_sha256,
            }
            acknowledgement, adapter_error = _execute_json_process(
                executable=adapter,
                invocation={
                    "adapter_protocol": "asp-conformance-adapter/1",
                    **common_binding,
                    "vector_id": vector_id,
                    "subject": subject,
                    "case": _adapter_case(catalog, vector),
                },
                workdir=workdir,
                timeout_seconds=timeout_seconds,
                label="adapter",
            )
            if adapter_error is None and acknowledgement is not None:
                try:
                    _validate_adapter_ack(
                        acknowledgement, run_id=run_id, vector_id=vector_id
                    )
                except ConformanceError:
                    adapter_error = "invalid_output"
            observation: dict[str, Any] | None = None
            probe_error: str | None = None
            if adapter_error is None:
                observation, probe_error = _execute_json_process(
                    executable=probe,
                    invocation={
                        "probe_protocol": "asp-conformance-probe/1",
                        "operation": "observe",
                        **common_binding,
                        "vector_id": vector_id,
                        "subject_locator": _subject_locator(subject),
                        "requested_states": sorted(
                            item["state"] for item in vector["state_deltas"]
                        ),
                    },
                    workdir=workdir,
                    timeout_seconds=timeout_seconds,
                    label="probe",
                )
        execution_error = adapter_error or probe_error
        if execution_error is not None:
            failure_token = {
                "timeout": "timeout",
                "invalid_output": "invalid_observation",
            }.get(execution_error, "adapter_error")
            results.append(
                {
                    "vector_id": vector_id,
                    "vector_sha256": vector_digest(vector),
                    "status": "error",
                    "requirement_ids": vector["requirement_ids"],
                    "observation_ids": [],
                    "failure_token": failure_token,
                }
            )
            continue
        assert observation is not None
        try:
            _validate_with_schema(
                observation,
                observation_schema,
                "probe observation",
                registry=_schema_registry(catalog.root),
            )
        except ConformanceError:
            observation = None
        if observation is None or (
            observation["run_id"] != run_id
            or observation["subject_sha256"] != subject_sha256
            or observation["harness_sha256"] != harness_sha256
            or observation["counterpart_sha256s"] != expected_counterpart_digests
        ):
            results.append(
                {
                    "vector_id": vector_id,
                    "vector_sha256": vector_digest(vector),
                    "status": "error",
                    "requirement_ids": vector["requirement_ids"],
                    "observation_ids": [],
                    "failure_token": "invalid_observation",
                }
            )
            continue
        passed, failure_token = _compare_observation(vector, observation)
        observations.append(observation)
        result = {
            "vector_id": vector_id,
            "vector_sha256": vector_digest(vector),
            "status": "pass" if passed else "fail",
            "requirement_ids": vector["requirement_ids"],
            "observation_ids": [observation["observation_id"]],
        }
        if failure_token is not None:
            result["failure_token"] = "assertion_failed"
        results.append(result)

    report = {
        "$schema": "./report.schema.json",
        "schema_version": 1,
        "report_profile": REPORT_PROFILE,
        "report_id": f"report-{run_id.removeprefix('urn:uuid:')}",
        "run_id": run_id,
        "claim_effect": "descriptive_only",
        "suite": {
            "suite_id": catalog.suite["suite_id"],
            "suite_version": catalog.suite["suite_version"],
            "protocol_version": catalog.suite["protocol_version"],
            "catalog_sha256": catalog_digest(root),
            "specification_sha256": specification_digest(root),
        },
        "subject": subject,
        "runner": runner,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "feature_inventory": inventory,
        "applicability": {
            "applicable_vector_ids": applicable,
            "not_applicable": not_applicable,
            "uncovered_feature_ids": uncovered_features,
        },
        "results": results,
        "observations": observations,
        "summary": _summary(
            results,
            len(not_applicable),
            uncovered_features=uncovered_features,
            subject_kind=subject["subject_kind"],
        ),
    }
    _validate_with_schema(
        report,
        _schema_for(catalog, "report"),
        "generated report",
        registry=_schema_registry(catalog.root),
    )
    verify_report(report, root=root, catalog=catalog)
    return report


def _parse_timestamp(value: str) -> datetime:
    if not RFC3339_PATTERN.fullmatch(value):
        raise ConformanceError(f"invalid RFC 3339 timestamp: {value}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ConformanceError(f"invalid RFC 3339 timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise ConformanceError(f"timestamp lacks an offset: {value}")
    return parsed


def verify_report(
    report: dict[str, Any],
    *,
    root: Path = ROOT,
    catalog: Catalog | None = None,
    adapter: Path | None = None,
    probe: Path | None = None,
) -> None:
    """Recompute a report against the current exact catalog and specification."""

    _validate_ijson_value(report)
    _validate_digest_members(report)
    catalog = catalog or validate_catalog(root)
    _validate_with_schema(
        report,
        _schema_for(catalog, "report"),
        "report",
        registry=_schema_registry(catalog.root),
    )
    validate_subject(report["subject"], catalog)
    suite = report["suite"]
    expected_suite = {
        "suite_id": catalog.suite["suite_id"],
        "suite_version": catalog.suite["suite_version"],
        "protocol_version": catalog.suite["protocol_version"],
        "catalog_sha256": catalog_digest(root),
        "specification_sha256": specification_digest(root),
    }
    if suite != expected_suite:
        raise ConformanceError("report suite or source digest is stale")
    if report["claim_effect"] != "descriptive_only":
        raise ConformanceError("report claim_effect must remain descriptive_only")
    if report["runner"]["runner_artifact_sha256"] != file_digest(
        "ASP-CONFORMANCE-RUNNER-V1", root / "conformance" / "check.py"
    ):
        raise ConformanceError("report runner artifact is stale")
    if (adapter is None) != (probe is None):
        raise ConformanceError("adapter and probe paths must be verified together")
    if adapter is not None and probe is not None:
        if report["runner"]["adapter_artifact_sha256"] != file_digest(
            "ASP-CONFORMANCE-ADAPTER-V1", adapter.expanduser().resolve()
        ):
            raise ConformanceError("report adapter artifact differs from the supplied file")
        if report["runner"]["probe_artifact_sha256"] != file_digest(
            "ASP-CONFORMANCE-PROBE-V1", probe.expanduser().resolve()
        ):
            raise ConformanceError("report probe artifact differs from the supplied file")
    expected_harness_sha256 = harness_digest(report["runner"])
    inventory = report["feature_inventory"]
    _validate_inventory(
        inventory,
        run_id=report["run_id"],
        expected_subject_sha256=subject_digest(report["subject"]),
        expected_harness_sha256=expected_harness_sha256,
        catalog=catalog,
    )
    if inventory["feature_ids"] != report["subject"]["features"]:
        raise ConformanceError("feature inventory differs from the report subject")
    applicable, not_applicable, uncovered_features = applicable_vectors(
        catalog, report["subject"]
    )
    if report["applicability"] != {
        "applicable_vector_ids": applicable,
        "not_applicable": not_applicable,
        "uncovered_feature_ids": uncovered_features,
    }:
        raise ConformanceError("report applicability was not derived from the matrix")

    result_ids = [result["vector_id"] for result in report["results"]]
    if result_ids != applicable:
        raise ConformanceError("report must contain exactly one ordered result per vector")
    observation_ids = [item["observation_id"] for item in report["observations"]]
    if len(observation_ids) != len(set(observation_ids)):
        raise ConformanceError("report contains duplicate observation ids")
    observations = {item["observation_id"]: item for item in report["observations"]}
    referenced_observation_ids: list[str] = []

    recomputed_results: list[dict[str, Any]] = []
    for result in report["results"]:
        vector = catalog.vectors[result["vector_id"]]
        expected_counterpart_digests = _required_counterpart_digests(
            vector, report["subject"]
        )
        if result["vector_sha256"] != vector_digest(vector):
            raise ConformanceError(f"stale vector digest for {vector['vector_id']}")
        if result["requirement_ids"] != vector["requirement_ids"]:
            raise ConformanceError(
                f"result requirement mapping differs for {vector['vector_id']}"
            )
        expected_result = {
            "vector_id": vector["vector_id"],
            "vector_sha256": vector_digest(vector),
            "requirement_ids": vector["requirement_ids"],
        }
        if expected_counterpart_digests is None:
            expected_result.update(
                {
                    "status": "error",
                    "observation_ids": [],
                    "failure_token": "unavailable_probe",
                }
            )
        elif result["status"] == "error":
            if result["observation_ids"]:
                raise ConformanceError("error result must not claim an observation")
            if "failure_token" not in result:
                raise ConformanceError("error result requires failure_token")
            expected_result.update(
                {
                    "status": "error",
                    "observation_ids": [],
                    "failure_token": result["failure_token"],
                }
            )
        else:
            if len(result["observation_ids"]) != 1:
                raise ConformanceError("pass/fail result requires one observation")
            observation_id = result["observation_ids"][0]
            observation = observations.get(observation_id)
            if observation is None:
                raise ConformanceError(f"unknown observation id {observation_id}")
            referenced_observation_ids.append(observation_id)
            if observation["counterpart_sha256s"] != expected_counterpart_digests:
                raise ConformanceError(
                    f"counterpart binding differs for {vector['vector_id']}"
                )
            passed, failure_token = _compare_observation(vector, observation)
            expected_result.update(
                {
                    "status": "pass" if passed else "fail",
                    "observation_ids": [observation_id],
                }
            )
            if failure_token is not None:
                expected_result["failure_token"] = "assertion_failed"
        if result != expected_result:
            raise ConformanceError(
                f"result status was not derived for {vector['vector_id']}"
            )
        recomputed_results.append(expected_result)

    if sorted(referenced_observation_ids) != sorted(observation_ids):
        raise ConformanceError("report contains unreferenced or multiply referenced observations")
    started_at = _parse_timestamp(report["started_at"])
    finished_at = _parse_timestamp(report["finished_at"])
    if finished_at < started_at:
        raise ConformanceError("report finished_at precedes started_at")
    expected_subject_digest = subject_digest(report["subject"])
    inventory_timestamp = _parse_timestamp(inventory["captured_at"])
    if not started_at <= inventory_timestamp <= finished_at:
        raise ConformanceError("feature inventory timestamp is outside the run interval")
    for observation in report["observations"]:
        if (
            observation["run_id"] != report["run_id"]
            or observation["subject_sha256"] != expected_subject_digest
            or observation["harness_sha256"] != expected_harness_sha256
        ):
            raise ConformanceError(
                "observation run, subject, or harness binding differs from the report"
            )
        captured_at = _parse_timestamp(observation["captured_at"])
        if not started_at <= captured_at <= finished_at:
            raise ConformanceError("observation timestamp is outside the run interval")
    if report["summary"] != _summary(
        recomputed_results,
        len(not_applicable),
        uncovered_features=uncovered_features,
        subject_kind=report["subject"]["subject_kind"],
    ):
        raise ConformanceError("report summary or suite verdict was not derived")


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="validate the canonical suite catalog")

    run_parser = subparsers.add_parser("run", help="run a subject through an adapter")
    run_parser.add_argument("--subject", type=Path, required=True)
    run_parser.add_argument("--adapter", type=Path, required=True)
    run_parser.add_argument("--adapter-id", required=True)
    run_parser.add_argument("--adapter-version", required=True)
    run_parser.add_argument("--adapter-configuration-sha256", required=True)
    run_parser.add_argument("--probe", type=Path, required=True)
    run_parser.add_argument("--probe-id", required=True)
    run_parser.add_argument("--probe-version", required=True)
    run_parser.add_argument("--probe-configuration-sha256", required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--timeout", type=int, default=10)

    verify_parser = subparsers.add_parser(
        "verify-report", help="verify a report against the current catalog"
    )
    verify_parser.add_argument("report", type=Path)
    verify_parser.add_argument("--adapter", type=Path)
    verify_parser.add_argument("--probe", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            catalog = validate_catalog(ROOT)
            print(
                "Conformance catalog is valid: "
                f"{len(catalog.profiles)} profiles, "
                f"{len(catalog.requirements)} requirements, "
                f"{len(catalog.vectors)} vectors"
            )
            return 0
        if args.command == "run":
            subject = load_strict_json(args.subject)
            report = run_suite(
                subject=subject,
                adapter=args.adapter,
                probe=args.probe,
                adapter_id=args.adapter_id,
                adapter_version=args.adapter_version,
                adapter_configuration_sha256=args.adapter_configuration_sha256,
                probe_id=args.probe_id,
                probe_version=args.probe_version,
                probe_configuration_sha256=args.probe_configuration_sha256,
                timeout_seconds=args.timeout,
            )
            _write_report(args.output, report)
            print(
                f"Wrote {report['summary']['suite_verdict']} report: {args.output}"
            )
            return 0 if report["summary"]["suite_verdict"] == "pass" else 1
        report = load_strict_json(args.report)
        verify_report(report, adapter=args.adapter, probe=args.probe)
        verdict = report["summary"]["suite_verdict"]
        print(f"Conformance report is valid and current ({verdict}): {args.report}")
        return 0 if verdict == "pass" else 1
    except ConformanceError as error:
        print(f"Conformance validation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
