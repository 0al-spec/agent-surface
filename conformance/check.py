#!/usr/bin/env python3
"""Validate and execute the ASP v1 conformance catalog."""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import math
import os
import platform
import re
import signal
import shlex
import subprocess
import sys
import tempfile
import unicodedata
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urljoin, urlsplit

try:
    import resource
except ImportError:  # pragma: no cover - the reference runner targets POSIX.
    resource = None

from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for
from referencing import Registry, Resource
import rfc8785


ROOT = Path(__file__).resolve().parents[1]
V1_DIR = ROOT / "conformance" / "v1"
RFC_PATH = ROOT / "drafts" / "agent-surface.md"
SUITE_PATH = V1_DIR / "suite.json"
VECTORS_PATH = V1_DIR / "vectors.json"
FIXTURES_PATH = V1_DIR / "fixtures.json"
SCHEMA_CASES_PATH = V1_DIR / "schema-cases.json"
BUNDLES_PATH = V1_DIR / "bundles.json"
SCHEMA_NAMES = (
    "bundles",
    "capacity-error",
    "fixtures",
    "human-elicitation",
    "impact-simulation",
    "mcp-binding",
    "observation",
    "operational-limits",
    "purpose-task-bound-grant",
    "report",
    "risk-explanation",
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
            "conformance/v1/bundles.json",
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
HTTP_MONTHS = {
    name: number
    for number, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        start=1,
    )
}
HTTP_DATE_PATTERNS = (
    (
        re.compile(
            r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), "
            r"(?P<day>[0-9]{2}) (?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
            r"(?P<year>[0-9]{4}) (?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):"
            r"(?P<second>[0-9]{2}) GMT$"
        ),
        False,
    ),
    (
        re.compile(
            r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
            r"(?P<day>[0-9]{2})-(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-"
            r"(?P<year>[0-9]{2}) (?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):"
            r"(?P<second>[0-9]{2}) GMT$"
        ),
        True,
    ),
    (
        re.compile(
            r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) "
            r"(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
            r"(?P<day> [1-9]|[0-9]{2}) (?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):"
            r"(?P<second>[0-9]{2}) (?P<year>[0-9]{4})$"
        ),
        False,
    ),
)
OPERATIONAL_LIMITS_SCHEMA_ID = SCHEMA_IDS["operational-limits"]
CAPACITY_ERROR_SCHEMA_ID = SCHEMA_IDS["capacity-error"]
HUMAN_ELICITATION_SCHEMA_ID = SCHEMA_IDS["human-elicitation"]
IMPACT_SIMULATION_SCHEMA_ID = SCHEMA_IDS["impact-simulation"]
RISK_EXPLANATION_SCHEMA_ID = SCHEMA_IDS["risk-explanation"]
MCP_BINDING_SCHEMA_ID = SCHEMA_IDS["mcp-binding"]
PURPOSE_TASK_BOUND_GRANT_SCHEMA_ID = SCHEMA_IDS["purpose-task-bound-grant"]
OPERATIONAL_LIMITS_FEATURE_ID = (
    "https://github.com/0al-spec/agent-surface/profiles/operational-limits/v1"
)
ASP_OVER_AHP_FEATURE_ID = (
    "https://github.com/0al-spec/agent-surface/profiles/asp-over-ahp/v1"
)
ASP_OVER_MCP_FEATURE_ID = (
    "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1"
)
PURPOSE_TASK_BOUND_GRANT_FEATURE_ID = (
    "https://github.com/0al-spec/agent-surface/profiles/"
    "purpose-task-bound-grant/v1"
)
ASP_OVER_MCP_EXTENSION_ID = "io.github.zeroal-spec/asp-over-mcp-v1"
ASP_OVER_MCP_PROTOCOL_VERSION = "2025-11-25"
RECEIPT_RESOURCE_REQUEST_PROFILE = (
    "https://github.com/0al-spec/agent-surface/tools/asp-replay/"
    "receipt-resource-request/v1"
)
RECEIPT_RESOURCE_REPORT_PROFILE = (
    "https://github.com/0al-spec/agent-surface/tools/asp-replay/"
    "receipt-resource-report/v1"
)
RECEIPT_RESOURCE_VALIDATION_SCOPE = (
    "local_structure_semantics_hashes_and_correlated_binding"
)
HUMAN_ELICITATION_FEATURE_ID = (
    "https://github.com/0al-spec/agent-surface/profiles/human-elicitation/v1"
)
IMPACT_SIMULATION_FEATURE_ID = "agent-surface/feature/impact-simulation"
RISK_EXPLANATION_FEATURE_ID = "agent-surface/feature/risk-explanation-ui-hints"
IMPACT_RISK_ORDER = {
    name: index
    for index, name in enumerate(
        (
            "read",
            "propose",
            "write",
            "public_side_effect",
            "external_side_effect",
            "financial_side_effect",
            "destructive",
            "privileged",
        )
    )
}
IMPACT_EXTENSION_URI_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9+.-]*:"
    r"(?:[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=-]|%[0-9A-Fa-f]{2})+"
)
IMPACT_INDETERMINATE_REASONS = frozenset(
    {
        "identity_evidence_profile_unsupported",
        "identity_evidence_status_unavailable",
        "runtime_attestation_unavailable",
        "runtime_identity_unavailable",
        "input_unknown",
    }
)
IMPACT_DEFINITIVE_REASONS = frozenset(
    {
        "action_not_requested",
        "approval_unsupported",
        "adapter_unavailable",
        "capability_missing",
        "data_exposure_unsupported",
        "effect_unsupported",
        "execution_stage_unsupported",
        "identity_evidence_invalid",
        "identity_evidence_missing",
        "policy_denied",
        "recovery_unsupported",
        "remote_processing_unsupported",
        "retention_unsupported",
        "risk_denied",
        "runtime_attestation_unsupported",
        "runtime_identity_invalid",
        "sandbox_unsatisfied",
        "schema_unsupported",
        "scope_unavailable",
        "training_use_unsupported",
    }
)
IMPACT_MODES = frozenset(
    {"read", "dry_run", "propose", "reserve", "commit", "compensate", "revert"}
)
IMPACT_STATE_CHANGING_MODES = frozenset(
    {"reserve", "commit", "compensate", "revert"}
)
IMPACT_REASON_SUBJECT_KINDS = frozenset(
    {
        "candidate",
        "runtime",
        "identity_evidence",
        "capability",
        "adapter",
        "action",
        "scope",
        "approval",
        "effect",
        "recovery",
        "exposure",
        "sandbox",
        "policy",
    }
)
IMPACT_EFFECT_VALUES = {
    "operation": frozenset(
        {
            "create",
            "update",
            "delete",
            "publish",
            "send",
            "execute",
            "transfer",
            "grant",
            "revoke",
            "deploy",
            "reserve",
            "renew",
            "release",
        }
    ),
    "visibility": frozenset({"private", "shared", "public"}),
    "boundary": frozenset({"internal", "external"}),
    "reversibility": frozenset(
        {"reversible", "compensatable", "irreversible", "not_applicable"}
    ),
    "domain": frozenset(
        {
            "data",
            "communication",
            "workflow",
            "financial",
            "security",
            "identity",
            "authorization",
            "deployment",
            "configuration",
        }
    ),
}
IMPACT_CANDIDATE_CHECKS = {
    "adapter": ("adapter_unavailable", "definitive", "adapter"),
    "approval": ("approval_unsupported", "definitive", "approval"),
    "capability": ("capability_missing", "definitive", "capability"),
    "data_exposure": ("data_exposure_unsupported", "definitive", "exposure"),
    "effect": ("effect_unsupported", "definitive", "effect"),
    "execution_stage": (
        "execution_stage_unsupported",
        "definitive",
        "action",
    ),
    "identity_evidence_integrity": (
        "identity_evidence_invalid",
        "definitive",
        "identity_evidence",
    ),
    "identity_evidence_presence": (
        "identity_evidence_missing",
        "definitive",
        "identity_evidence",
    ),
    "identity_evidence_profile": (
        "identity_evidence_profile_unsupported",
        "indeterminate",
        "identity_evidence",
    ),
    "identity_evidence_status": (
        "identity_evidence_status_unavailable",
        "indeterminate",
        "identity_evidence",
    ),
    "policy": ("policy_denied", "definitive", "policy"),
    "recovery": ("recovery_unsupported", "definitive", "recovery"),
    "remote_processing": (
        "remote_processing_unsupported",
        "definitive",
        "policy",
    ),
    "required_input": ("input_unknown", "indeterminate", "policy"),
    "retention": ("retention_unsupported", "definitive", "exposure"),
    "risk": ("risk_denied", "definitive", "action"),
    "runtime_attestation_availability": (
        "runtime_attestation_unavailable",
        "indeterminate",
        "runtime",
    ),
    "runtime_attestation_support": (
        "runtime_attestation_unsupported",
        "definitive",
        "runtime",
    ),
    "runtime_identity_availability": (
        "runtime_identity_unavailable",
        "indeterminate",
        "runtime",
    ),
    "runtime_identity_integrity": (
        "runtime_identity_invalid",
        "definitive",
        "runtime",
    ),
    "sandbox": ("sandbox_unsatisfied", "definitive", "sandbox"),
    "schema": ("schema_unsupported", "definitive", "action"),
    "scope": ("scope_unavailable", "definitive", "scope"),
    "training_use": (
        "training_use_unsupported",
        "definitive",
        "policy",
    ),
}
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
RISK_LANGUAGE_PATTERN = re.compile(
    r"^[a-z]{2,8}(?:-[a-z]{4})?(?:-(?:[a-z]{2}|[0-9]{3}))?"
    r"(?:-(?:[a-z0-9]{5,8}|[0-9][a-z0-9]{3}))*$"
)
RISK_RUNTIME_PROJECTION_FIELDS = frozenset(
    {
        "action_id",
        "hint_action_id",
        "declared_risk",
        "declared_effect_ids",
        "hint_surface_hash",
        "hint",
        "language_preferences",
        "selected_language",
        "rendered_summary",
        "rendered_effect_summaries",
        "rendering",
        "escaped",
        "bidi_isolated",
        "authority_use",
        "agent_projection",
    }
)
RISK_RETAINED_SURFACE_FIELDS = frozenset(
    {
        "status",
        "version",
        "retained_hash",
        "candidate_hash",
        "references",
        "mode",
        "action_semantics",
    }
)


class ConformanceError(ValueError):
    """Raised when a suite artifact or report fails closed validation."""


@dataclass(frozen=True)
class Catalog:
    """Validated canonical suite data and derived indexes."""

    root: Path
    snapshot_catalog_sha256: str
    snapshot_specification_sha256: str
    snapshot_memory_sha256: str
    suite: dict[str, Any]
    vector_catalog: dict[str, Any]
    fixture_catalog: dict[str, Any]
    schema_case_catalog: dict[str, Any]
    bundle_registry: dict[str, Any]
    requirements: dict[str, dict[str, Any]]
    vectors: dict[str, dict[str, Any]]
    profiles: dict[str, dict[str, Any]]
    features: dict[str, dict[str, Any]]
    fixtures: dict[str, dict[str, Any]]
    mutations: dict[str, dict[str, Any]]
    bundles: dict[str, dict[str, Any]]


def _reject_float(value: str) -> None:
    raise ConformanceError(f"I-JSON floating-point values are not permitted: {value}")


def _reject_constant(value: str) -> None:
    raise ConformanceError(f"non-finite JSON value is not permitted: {value}")


def _parse_safe_integer(value: str) -> int:
    if value == "-0":
        raise ConformanceError("I-JSON negative zero is not permitted")
    number = int(value)
    if not -SAFE_INTEGER <= number <= SAFE_INTEGER:
        raise ConformanceError(f"JSON integer is outside the I-JSON safe range: {value}")
    return number


def _parse_human_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ConformanceError(
            f"non-finite Human Elicitation number is not permitted: {value}"
        )
    if number == 0 and value.startswith("-"):
        raise ConformanceError("Human Elicitation negative zero is not permitted")
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


def _validate_human_json_value(value: Any, path: str = "$") -> None:
    """Validate the RFC 8785 JSON data model used inside Human messages."""

    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -SAFE_INTEGER <= value <= SAFE_INTEGER:
            raise ConformanceError(
                f"JSON integer is outside the I-JSON safe range at {path}"
            )
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ConformanceError(
                f"Human Elicitation number is not finite at {path}"
            )
        if value == 0 and math.copysign(1.0, value) < 0:
            raise ConformanceError(
                f"Human Elicitation negative zero is not permitted at {path}"
            )
        return
    if isinstance(value, str):
        _validate_unicode(value, path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_human_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ConformanceError(f"JSON object key is not a string at {path}")
            _validate_unicode(key, f"{path}.<key>")
            _validate_human_json_value(item, f"{path}.{key}")
        return
    raise ConformanceError(
        f"value at {path} is not representable as Human Elicitation JSON"
    )


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


def load_schema_case_json(path: Path) -> Any:
    """Load schema cases while permitting Human message binary64 instances."""

    try:
        document = path.read_text(encoding="utf-8")
        value = json.loads(
            document,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_parse_human_float,
            parse_int=_parse_safe_integer,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ConformanceError) as error:
        raise ConformanceError(f"{path} is not Human-compatible JSON: {error}") from error
    _validate_unicode(value)
    _validate_human_json_value(value)
    return value


def loads_human_json(document: str, *, source: str = "Human JSON input") -> Any:
    """Parse RFC 8785-compatible Human message JSON without lossy numbers."""

    try:
        value = json.loads(
            document,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_parse_human_float,
            parse_int=_parse_safe_integer,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ConformanceError) as error:
        raise ConformanceError(f"{source} is not Human-compatible JSON: {error}") from error
    _validate_unicode(value)
    _validate_human_json_value(value)
    return value


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
            if (
                key in {"$ref", "$dynamicRef"}
                and isinstance(item, str)
                and not item.startswith("#")
            ):
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


def _validate_risk_language_tag(value: str) -> None:
    if len(value) > 63 or RISK_LANGUAGE_PATTERN.fullmatch(value) is None:
        raise ConformanceError("risk explanation language tag is not canonical")
    subtags = value.split("-")
    index = 1
    if (
        index < len(subtags)
        and len(subtags[index]) == 4
        and subtags[index].isalpha()
    ):
        index += 1
    if index < len(subtags) and (
        (len(subtags[index]) == 2 and subtags[index].isalpha())
        or (len(subtags[index]) == 3 and subtags[index].isdigit())
    ):
        index += 1
    variants = subtags[index:]
    if len(variants) != len(set(variants)):
        raise ConformanceError(
            "risk explanation language tag repeats a variant subtag"
        )


def validate_risk_explanation(
    value: Any,
    context: dict[str, Any],
    *,
    root: Path = ROOT,
    registry: Registry | None = None,
    schema: dict[str, Any] | None = None,
) -> None:
    """Validate one closed hint and its exact parent action-effect binding."""

    _validate_ijson_value(value)
    _validate_with_schema(
        value,
        schema
        or load_strict_json(
            root / "conformance" / "v1" / "risk-explanation.schema.json"
        ),
        "risk explanation",
        registry=registry or _schema_registry(root),
    )
    if set(context) != {"effect_ids"}:
        raise ConformanceError(
            "risk explanation context must contain exactly effect_ids"
        )
    effect_ids = context["effect_ids"]
    if (
        not isinstance(effect_ids, list)
        or any(not isinstance(item, str) or not item for item in effect_ids)
        or len(effect_ids) != len(set(effect_ids))
    ):
        raise ConformanceError(
            "risk explanation context effect_ids must be unique non-empty strings"
        )

    languages = [item["language"] for item in value["localizations"]]
    _validate_risk_language_tag(value["default_language"])
    for language in languages:
        _validate_risk_language_tag(language)
    if languages != sorted(languages):
        raise ConformanceError(
            "risk explanation localizations must be sorted by language"
        )
    if len(languages) != len(set(languages)):
        raise ConformanceError("risk explanation repeats a language")
    if value["default_language"] not in languages:
        raise ConformanceError(
            "risk explanation default_language has no exact localization"
        )
    for localization in value["localizations"]:
        localized_effect_ids = [
            item["effect_id"] for item in localization["effect_summaries"]
        ]
        if localized_effect_ids != effect_ids:
            raise ConformanceError(
                "risk explanation effect_summaries must exactly cover the "
                "parent action effects in declaration order"
            )


def select_risk_explanation_localization(
    value: dict[str, Any], language_preferences: list[str]
) -> dict[str, Any]:
    """Select exactly one localization using RFC 4647 Lookup and defaulting."""

    if (
        not isinstance(language_preferences, list)
        or len(language_preferences) > 16
        or any(
            not isinstance(item, str)
            or len(item) > 63
            for item in language_preferences
        )
    ):
        raise ConformanceError(
            "risk explanation language preferences must be canonical tags"
        )
    for preference in language_preferences:
        _validate_risk_language_tag(preference)
    localizations = {
        item["language"]: item for item in value["localizations"]
    }
    for preference in language_preferences:
        subtags = preference.split("-")
        while subtags:
            candidate = "-".join(subtags)
            if candidate in localizations:
                return localizations[candidate]
            subtags.pop()
            if subtags and len(subtags[-1]) == 1:
                subtags.pop()
    return localizations[value["default_language"]]


def _validate_risk_explanation_hint_projection(
    projection: Any,
    *,
    root: Path = ROOT,
) -> None:
    """Validate publisher-owned hint content and exact action binding."""

    if not isinstance(projection, dict):
        raise ConformanceError("risk explanation projection must be an object")
    validate_risk_explanation(
        projection["hint"],
        {"effect_ids": projection["declared_effect_ids"]},
        root=root,
    )
    if projection["hint_action_id"] != projection["action_id"]:
        raise ConformanceError(
            "risk explanation projection is not bound to its authoritative action"
        )


def validate_risk_explanation_publisher_projection(
    projection: Any,
    surface: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    """Validate only publisher-owned hint state against the candidate manifest."""

    _validate_risk_explanation_hint_projection(projection, root=root)
    if projection["hint_surface_hash"] != surface["candidate_hash"]:
        raise ConformanceError(
            "risk explanation publisher projection is not bound to the candidate surface"
        )


def validate_risk_explanation_projection(
    projection: Any,
    surface: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    """Validate Runtime presentation against the exact retained surface."""

    if not isinstance(projection, dict) or set(projection) != set(
        RISK_RUNTIME_PROJECTION_FIELDS
    ):
        raise ConformanceError(
            "risk explanation Runtime projection must be a closed presentation"
        )
    if (
        not isinstance(surface, dict)
        or set(surface) != set(RISK_RETAINED_SURFACE_FIELDS)
        or surface["status"] != "current"
        or not isinstance(surface["version"], str)
        or not surface["version"]
        or not isinstance(surface["retained_hash"], str)
        or not surface["retained_hash"]
        or not isinstance(surface["candidate_hash"], str)
        or not surface["candidate_hash"]
        or surface["references"] != "complete"
        or surface["mode"] not in {"standard", "proposal_only"}
        or surface["action_semantics"] not in {
            "closed_read_propose",
            "state_changing",
        }
        or (
            surface["mode"] == "proposal_only"
            and surface["action_semantics"] != "closed_read_propose"
        )
    ):
        raise ConformanceError(
            "risk explanation Runtime presentation lacks the complete verified "
            "retained manifest projection"
        )
    _validate_risk_explanation_hint_projection(projection, root=root)
    if projection["hint_surface_hash"] != surface["retained_hash"]:
        raise ConformanceError(
            "risk explanation Runtime projection is not bound to the retained surface"
        )
    selected = select_risk_explanation_localization(
        projection["hint"], projection["language_preferences"]
    )
    if (
        projection["selected_language"] != selected["language"]
        or projection["rendered_summary"] != selected["summary"]
        or projection["rendered_effect_summaries"]
        != selected["effect_summaries"]
    ):
        raise ConformanceError(
            "risk explanation rendered projection differs from RFC 4647 selection"
        )
    if (
        projection["rendering"] != "literal_with_canonical_facts"
        or projection["escaped"] is not True
        or projection["bidi_isolated"] is not True
        or projection["authority_use"] != "advisory_only"
        or projection["agent_projection"] != "absent"
    ):
        raise ConformanceError(
            "risk explanation prose must remain escaped, bidi-isolated, literal, "
            "advisory, and agent-hidden"
        )


def _impact_sorted_unique(values: Any, label: str) -> list[str]:
    if (
        not isinstance(values, list)
        or any(not isinstance(item, str) or not item for item in values)
        or values != sorted(values, key=lambda item: item.encode("utf-8"))
        or len(values) != len(set(values))
    ):
        raise ConformanceError(
            f"impact simulation {label} must be sorted unique non-empty strings"
        )
    return values


def _validate_impact_action(action: dict[str, Any]) -> None:
    _impact_sorted_unique(
        action["required_companion_action_ids"],
        "required_companion_action_ids",
    )
    exposure = action["data_exposure"]
    _impact_sorted_unique(exposure["classes"], "data_exposure.classes")
    recovery = action["recovery"]
    _impact_sorted_unique(
        recovery["available_action_ids"], "recovery.available_action_ids"
    )
    limitations = _impact_sorted_unique(
        recovery["limitations"], "recovery.limitations"
    )
    for limitation in limitations:
        if ":" in limitation and IMPACT_EXTENSION_URI_PATTERN.fullmatch(
            limitation
        ) is None:
            raise ConformanceError(
                "impact simulation recovery limitation URI is not ASCII RFC 3986"
            )
    if action["risk"] not in IMPACT_RISK_ORDER:
        raise ConformanceError(
            "impact simulation executable core does not support the action risk mapping"
        )
    mode = action["mode"]
    effects = action["maximum_effects"]
    if mode not in IMPACT_MODES:
        raise ConformanceError("impact simulation action mode is invalid")
    if mode in IMPACT_STATE_CHANGING_MODES and not effects:
        raise ConformanceError(
            "impact simulation state-changing action requires maximum effects"
        )
    if mode not in IMPACT_STATE_CHANGING_MODES and (
        effects
        or recovery["available_action_ids"]
        or recovery["limitations"]
    ):
        raise ConformanceError(
            "impact simulation non-state-changing action projects effects or recovery"
        )


def _impact_candidate_projection(
    candidate_check_facts: Any,
    matched_candidate: Any,
    bindings: dict[str, Any],
) -> tuple[str, list[str]]:
    """Derive the candidate-wide decision from runner-owned normalized facts."""

    if (
        not isinstance(candidate_check_facts, list)
        or not 24 <= len(candidate_check_facts) <= 64
    ):
        raise ConformanceError(
            "impact simulation candidate check facts are not a bounded array"
        )
    check_ids: list[str] = []
    reasons: list[dict[str, Any]] = []
    reason_classifications: dict[str, str] = {}
    for fact in candidate_check_facts:
        if (
            not isinstance(fact, dict)
            or set(fact) != {"check_id", "state", "subject"}
            or not isinstance(fact["check_id"], str)
            or not fact["check_id"]
            or fact["state"]
            not in {"satisfied", "blocking", "advisory"}
            or not isinstance(fact["subject"], dict)
            or set(fact["subject"]) != {"kind", "id"}
            or fact["subject"]["kind"] not in IMPACT_REASON_SUBJECT_KINDS
            or not isinstance(fact["subject"]["id"], str)
            or not fact["subject"]["id"]
        ):
            raise ConformanceError("impact simulation candidate check fact is invalid")
        check_id = fact["check_id"]
        check_ids.append(check_id)
        mapping = IMPACT_CANDIDATE_CHECKS.get(check_id)
        if mapping is None:
            if IMPACT_EXTENSION_URI_PATTERN.fullmatch(check_id) is None:
                raise ConformanceError(
                    "impact simulation candidate check identifier is neither "
                    "core nor an ASCII RFC 3986 URI"
                )
            code = check_id
            classification = "indeterminate"
        else:
            code, classification, required_subject_kind = mapping
            if fact["subject"]["kind"] != required_subject_kind:
                raise ConformanceError(
                    f"impact simulation candidate check {check_id} uses the "
                    "wrong subject kind"
                )
        state = fact["state"]
        if state != "satisfied":
            reason_classifications[code] = classification
            reasons.append(
                {
                    "code": code,
                    "severity": state,
                    "subject": fact["subject"],
                }
            )
    if (
        check_ids != sorted(check_ids, key=lambda item: item.encode("utf-8"))
        or len(check_ids) != len(set(check_ids))
        or not set(IMPACT_CANDIDATE_CHECKS).issubset(check_ids)
    ):
        raise ConformanceError(
            "impact simulation candidate checks are not canonical, unique, "
            "and complete for the core set"
        )
    reasons.sort(
        key=lambda reason: (
            0 if reason["severity"] == "blocking" else 1,
            reason["code"].encode("utf-8"),
            reason["subject"]["kind"].encode("utf-8"),
            reason["subject"]["id"].encode("utf-8"),
        )
    )
    definitive_codes = {
        reason["code"]
        for reason in reasons
        if reason["severity"] == "blocking"
        and reason_classifications[reason["code"]] == "definitive"
    }
    indeterminate_codes = {
        reason["code"]
        for reason in reasons
        if reason["severity"] == "blocking"
        and reason_classifications[reason["code"]] == "indeterminate"
    }
    if definitive_codes:
        derived_status = "incompatible"
        outcome = "not_covered"
        projected_codes = definitive_codes
    elif indeterminate_codes:
        derived_status = "indeterminate"
        outcome = "indeterminate"
        projected_codes = indeterminate_codes
    else:
        derived_status = "compatible"
        outcome = "covered"
        projected_codes = set()
    derived_decision = {"status": derived_status, "reasons": reasons}

    capability_match = bindings["capability_match"]
    if capability_match is None:
        if matched_candidate is not None:
            raise ConformanceError(
                "impact simulation has a retained candidate without a match binding"
            )
    else:
        matched_fields = {
            "bindings",
            "agent_id",
            "identity_evidence_hash",
            "grant_request_hash",
            "status",
            "reasons",
        }
        delegate = bindings["delegate"]
        if (
            not isinstance(matched_candidate, dict)
            or set(matched_candidate) != matched_fields
            or matched_candidate["bindings"] != bindings
            or matched_candidate["agent_id"] != delegate["agent_id"]
            or matched_candidate["identity_evidence_hash"]
            != delegate["identity_evidence_hash"]
            or matched_candidate["grant_request_hash"]
            != bindings["grant_request_hash"]
            or {
                "status": matched_candidate["status"],
                "reasons": matched_candidate["reasons"],
            }
            != derived_decision
        ):
            raise ConformanceError(
                "impact simulation retained match candidate is not the exact "
                "delegate, request, and recomputed decision"
            )
    return outcome, sorted(projected_codes, key=lambda item: item.encode("utf-8"))


def _derive_impact_actions(
    entries: Any,
    requested_ids: list[str],
    *,
    root: Path,
    registry: Registry,
) -> dict[str, dict[str, Any]]:
    """Derive action projections from normalized retained manifest declarations."""

    if not isinstance(entries, list) or not entries:
        raise ConformanceError(
            "impact simulation manifest declarations must be a non-empty array"
        )
    declaration_fields = {
        "action_id",
        "scope",
        "operation_id",
        "mode",
        "risk",
        "approval",
        "required_companion_action_ids",
        "effects",
        "data_exposure",
        "recovery_actions",
        "recovery_targets",
    }
    declarations: dict[str, dict[str, Any]] = {}
    for index, declaration in enumerate(entries):
        if not isinstance(declaration, dict) or set(declaration) != declaration_fields:
            raise ConformanceError(
                f"impact simulation actions[{index}] is not a manifest declaration"
            )
        for field in ("action_id", "scope", "operation_id"):
            if (
                not isinstance(declaration[field], str)
                or not declaration[field]
            ):
                raise ConformanceError(
                    f"impact simulation actions[{index}].{field} is invalid"
                )
        action_id = declaration["action_id"]
        if action_id in declarations:
            raise ConformanceError(
                "impact simulation repeats a manifest action declaration"
            )
        if declaration["mode"] not in IMPACT_MODES:
            raise ConformanceError("impact simulation declaration mode is invalid")
        if declaration["risk"] not in IMPACT_RISK_ORDER:
            raise ConformanceError(
                "impact simulation declaration risk mapping is unsupported"
            )
        if declaration["approval"] not in {
            "none",
            "runtime",
            "app",
            "user_or_app",
            "runtime_and_app",
        }:
            raise ConformanceError(
                "impact simulation declaration approval is invalid"
            )
        companions = _impact_sorted_unique(
            declaration["required_companion_action_ids"],
            "direct required companion action ids",
        )
        if action_id in companions:
            raise ConformanceError(
                "impact simulation action requires itself as a companion"
            )
        effects = declaration["effects"]
        relationships = declaration["recovery_actions"]
        recovery_targets = declaration["recovery_targets"]
        if (
            not isinstance(effects, list)
            or not isinstance(relationships, list)
            or not isinstance(recovery_targets, list)
        ):
            raise ConformanceError(
                "impact simulation declaration effects and recovery must be arrays"
            )
        state_changing = declaration["mode"] in IMPACT_STATE_CHANGING_MODES
        if state_changing != bool(effects):
            raise ConformanceError(
                "impact simulation declaration mode and effect envelope conflict"
            )
        if declaration["mode"] != "commit" and relationships:
            raise ConformanceError(
                "impact simulation non-commit action declares outbound recovery"
            )
        if (
            declaration["mode"] in {"compensate", "revert"}
        ) != bool(recovery_targets):
            raise ConformanceError(
                "impact simulation recovery-stage target declarations are inconsistent"
            )
        effect_ids: list[str] = []
        for effect in effects:
            effect_fields = {
                "effect_id",
                "operation",
                "resource_type",
                "visibility",
                "boundary",
                "reversibility",
                "domain",
            }
            if (
                not isinstance(effect, dict)
                or not effect_fields.issubset(effect)
                or any(
                    field not in effect_fields
                    and IMPACT_EXTENSION_URI_PATTERN.fullmatch(field) is None
                    for field in effect
                )
                or not isinstance(effect.get("effect_id"), str)
                or not effect["effect_id"]
                or not isinstance(effect.get("resource_type"), str)
                or not effect["resource_type"]
                or any(
                    effect.get(field) not in allowed
                    for field, allowed in IMPACT_EFFECT_VALUES.items()
                )
            ):
                raise ConformanceError(
                    "impact simulation declaration contains an invalid or "
                    "unsupported effect mapping"
                )
            effect_ids.append(effect["effect_id"])
        if len(effect_ids) != len(set(effect_ids)):
            raise ConformanceError(
                "impact simulation declaration repeats an effect identifier"
            )
        required_risk = "write" if state_changing else "read"
        for effect in effects:
            floors = [required_risk]
            if effect["visibility"] == "public":
                floors.append("public_side_effect")
            if effect["boundary"] == "external":
                floors.append("external_side_effect")
            if effect["domain"] == "financial":
                floors.append("financial_side_effect")
            if effect["domain"] in {
                "security",
                "identity",
                "authorization",
            }:
                floors.append("privileged")
            if (
                effect["operation"] in {"delete", "revoke"}
                and effect["reversibility"] == "irreversible"
            ):
                floors.append("destructive")
            required_risk = max(
                floors, key=lambda risk: IMPACT_RISK_ORDER[risk]
            )
        if (
            IMPACT_RISK_ORDER[declaration["risk"]]
            < IMPACT_RISK_ORDER[required_risk]
        ):
            raise ConformanceError(
                "impact simulation declaration risk is below its effect floor"
            )
        normalized_relationships: list[dict[str, Any]] = []
        for relationship in relationships:
            if (
                not isinstance(relationship, dict)
                or set(relationship)
                != {
                    "mode",
                    "action_id",
                    "effect_ids",
                    "recovery_window_seconds",
                }
                or relationship["mode"] not in {"compensate", "revert"}
                or not isinstance(relationship["action_id"], str)
                or not relationship["action_id"]
                or relationship["action_id"] == action_id
                or isinstance(relationship["recovery_window_seconds"], bool)
                or not isinstance(
                    relationship["recovery_window_seconds"], int
                )
                or not 1
                <= relationship["recovery_window_seconds"]
                <= SAFE_INTEGER
            ):
                raise ConformanceError(
                    "impact simulation declaration has an invalid recovery relationship"
                )
            relationship_effect_ids = _impact_sorted_unique(
                relationship["effect_ids"], "recovery relationship effect ids"
            )
            if not relationship_effect_ids or not set(
                relationship_effect_ids
            ).issubset(effect_ids):
                raise ConformanceError(
                    "impact simulation recovery relationship names unknown effects"
                )
            normalized_relationships.append(relationship)
        if len(
            {
                (
                    relationship["mode"],
                    relationship["action_id"],
                    tuple(relationship["effect_ids"]),
                    relationship["recovery_window_seconds"],
                )
                for relationship in normalized_relationships
            }
        ) != len(normalized_relationships):
            raise ConformanceError(
                "impact simulation declaration repeats a recovery relationship"
            )
        recovery_target_keys: set[tuple[Any, ...]] = set()
        for target in recovery_targets:
            if (
                not isinstance(target, dict)
                or set(target)
                != {
                    "action_id",
                    "effect_ids",
                    "recovery_window_seconds",
                }
                or not isinstance(target["action_id"], str)
                or not target["action_id"]
                or target["action_id"] == action_id
                or isinstance(target["recovery_window_seconds"], bool)
                or not isinstance(target["recovery_window_seconds"], int)
                or not 1
                <= target["recovery_window_seconds"]
                <= SAFE_INTEGER
            ):
                raise ConformanceError(
                    "impact simulation recovery target declaration is invalid"
                )
            target_effect_ids = _impact_sorted_unique(
                target["effect_ids"], "recovery target effect ids"
            )
            if not target_effect_ids:
                raise ConformanceError(
                    "impact simulation recovery target has no effects"
                )
            target_key = (
                target["action_id"],
                tuple(target_effect_ids),
                target["recovery_window_seconds"],
            )
            if target_key in recovery_target_keys:
                raise ConformanceError(
                    "impact simulation repeats a recovery target"
                )
            recovery_target_keys.add(target_key)
        declarations[action_id] = declaration

    for action_id, declaration in declarations.items():
        if any(
            companion not in declarations
            or declarations[companion]["operation_id"]
            != declaration["operation_id"]
            for companion in declaration["required_companion_action_ids"]
        ):
            raise ConformanceError(
                "impact simulation declaration has an unresolved or cross-operation "
                "companion"
            )
        effects_by_id = {
            effect["effect_id"]: effect for effect in declaration["effects"]
        }
        covered_reversible: set[str] = set()
        covered_compensatable: set[str] = set()
        for relationship in declaration["recovery_actions"]:
            target = declarations.get(relationship["action_id"])
            reciprocal = {
                "action_id": action_id,
                "effect_ids": relationship["effect_ids"],
                "recovery_window_seconds": relationship[
                    "recovery_window_seconds"
                ],
            }
            if (
                target is None
                or target["mode"] != relationship["mode"]
                or target["operation_id"] != declaration["operation_id"]
                or reciprocal not in target["recovery_targets"]
            ):
                raise ConformanceError(
                    "impact simulation recovery relationship target is inconsistent"
                )
            for effect_id in relationship["effect_ids"]:
                effect = effects_by_id[effect_id]
                if relationship["mode"] == "revert":
                    if (
                        effect["reversibility"] != "reversible"
                        or effect["boundary"] != "internal"
                    ):
                        raise ConformanceError(
                            "impact simulation revert relationship is not valid"
                        )
                    covered_reversible.add(effect_id)
                else:
                    if effect["reversibility"] != "compensatable":
                        raise ConformanceError(
                            "impact simulation compensation relationship is not valid"
                        )
                    covered_compensatable.add(effect_id)
        if declaration["mode"] == "commit":
            reversible = {
                effect_id
                for effect_id, effect in effects_by_id.items()
                if effect["reversibility"] == "reversible"
            }
            compensatable = {
                effect_id
                for effect_id, effect in effects_by_id.items()
                if effect["reversibility"] == "compensatable"
            }
            if (
                reversible != covered_reversible
                or compensatable != covered_compensatable
            ):
                raise ConformanceError(
                    "impact simulation commit recovery coverage is inconsistent"
                )
        for target in declaration["recovery_targets"]:
            source = declarations.get(target["action_id"])
            outbound = (
                {
                    "mode": declaration["mode"],
                    "action_id": action_id,
                    "effect_ids": target["effect_ids"],
                    "recovery_window_seconds": target[
                        "recovery_window_seconds"
                    ],
                }
                if source is not None
                else None
            )
            if (
                source is None
                or source["mode"] != "commit"
                or source["operation_id"] != declaration["operation_id"]
                or outbound not in source["recovery_actions"]
            ):
                raise ConformanceError(
                    "impact simulation recovery target lacks an exact reciprocal"
                )

    closure_cache: dict[str, list[str]] = {}

    def companion_closure(action_id: str) -> list[str]:
        if action_id in closure_cache:
            return closure_cache[action_id]
        closure: set[str] = set()
        pending = list(declarations[action_id]["required_companion_action_ids"])
        while pending:
            companion = pending.pop()
            if companion == action_id or companion in closure:
                continue
            closure.add(companion)
            pending.extend(
                declarations[companion]["required_companion_action_ids"]
            )
        ordered = sorted(closure, key=lambda item: item.encode("utf-8"))
        closure_cache[action_id] = ordered
        return ordered

    requested_set = set(requested_ids)
    action_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": (
            "https://github.com/0al-spec/agent-surface/"
            "conformance/schemas/impact-simulation/v1#/$defs/action"
        ),
    }
    derived: dict[str, dict[str, Any]] = {}
    for action_id, declaration in declarations.items():
        effects = declaration["effects"]
        relationships = declaration["recovery_actions"]
        limitations: set[str] = set()
        if any(
            effect["reversibility"] == "irreversible" for effect in effects
        ):
            limitations.add("irreversible")
        if any(effect["boundary"] == "external" for effect in effects):
            limitations.add("external_outcome_may_be_unknown")
        if relationships:
            limitations.add("recovery_window_limited")
        elif declaration["mode"] == "commit" and effects:
            limitations.add("no_recovery_action")
        action = {
            "action_id": action_id,
            "scope": declaration["scope"],
            "mode": declaration["mode"],
            "risk": declaration["risk"],
            "approval": declaration["approval"],
            "required_companion_action_ids": companion_closure(action_id),
            "maximum_effects": effects,
            "data_exposure": declaration["data_exposure"],
            "recovery": {
                "available_action_ids": sorted(
                    {
                        relationship["action_id"]
                        for relationship in relationships
                        if relationship["action_id"] in requested_set
                    },
                    key=lambda item: item.encode("utf-8"),
                ),
                "limitations": sorted(
                    limitations, key=lambda item: item.encode("utf-8")
                ),
            },
        }
        _validate_with_schema(
            action,
            action_schema,
            f"impact simulation derived action {action_id}",
            registry=registry,
        )
        _validate_impact_action(action)
        derived[action_id] = action
    return derived


def validate_impact_simulation(
    value: Any,
    context: dict[str, Any],
    *,
    root: Path = ROOT,
    registry: Registry | None = None,
    schema: dict[str, Any] | None = None,
) -> None:
    """Validate one exact, deterministic Runtime-owned Impact Simulation Result."""

    _validate_ijson_value(value)
    schema_registry = registry or _schema_registry(root)
    _validate_with_schema(
        value,
        schema
        or load_strict_json(
            root / "conformance" / "v1" / "impact-simulation.schema.json"
        ),
        "impact simulation",
        registry=schema_registry,
    )
    if set(context) != {
        "evaluation_time",
        "bindings",
        "requested_action_ids",
        "requested_scope_ids",
        "candidate_check_facts",
        "matched_candidate",
        "actions",
        "freshness_deadlines",
        "current_binding_facts",
    }:
        raise ConformanceError(
            "impact simulation context must contain exactly evaluation_time, "
            "bindings, requested_action_ids, requested_scope_ids, "
            "candidate_check_facts, matched_candidate, actions, "
            "freshness_deadlines, and current_binding_facts"
        )
    if value["feature"] != IMPACT_SIMULATION_FEATURE_ID:
        raise ConformanceError("impact simulation uses the wrong feature identifier")
    if value["bindings"] != context["bindings"]:
        raise ConformanceError(
            "impact simulation bindings differ from authoritative current inputs"
        )
    current_binding_facts = context["current_binding_facts"]
    if (
        not isinstance(current_binding_facts, dict)
        or current_binding_facts != value["bindings"]
    ):
        raise ConformanceError(
            "impact simulation bindings differ from runner-owned current facts"
        )
    _validate_digest(value["bindings"]["surface"]["surface_hash"], "surface_hash")
    _validate_digest(value["bindings"]["grant_request_hash"], "grant_request_hash")
    _validate_digest(
        value["bindings"]["delegate"]["identity_evidence_hash"],
        "delegate.identity_evidence_hash",
    )

    evaluated_at = _parse_timestamp(value["evaluated_at"])
    valid_until = _parse_timestamp(value["valid_until"])
    evaluation_time = _parse_timestamp(context["evaluation_time"])
    if not evaluated_at < valid_until:
        raise ConformanceError(
            "impact simulation evaluated_at must precede valid_until"
        )
    if evaluation_time < evaluated_at or evaluation_time >= valid_until:
        raise ConformanceError(
            "impact simulation is not current at the evaluation time"
        )
    freshness_deadlines = context["freshness_deadlines"]
    deadline_fields = {
        "identity_evidence_status",
        "capability_match",
        "agent_inventory",
        "adapter_inventory",
        "local_policy",
        "enterprise_policy",
        "user_preferences",
        "runtime_identity",
        "runtime_attestation",
        "local_maximum",
    }
    if not isinstance(freshness_deadlines, dict) or set(
        freshness_deadlines
    ) != deadline_fields:
        raise ConformanceError(
            "impact simulation freshness deadlines are not the exact closed set"
        )
    parsed_deadlines: dict[str, datetime | None] = {}
    for name, deadline in freshness_deadlines.items():
        if deadline is None:
            parsed_deadlines[name] = None
            continue
        parsed = _parse_timestamp(deadline)
        if parsed <= evaluated_at:
            raise ConformanceError(
                f"impact simulation freshness deadline {name} is not after "
                "evaluated_at"
            )
        parsed_deadlines[name] = parsed
    for required_deadline in {
        "identity_evidence_status",
        "agent_inventory",
        "adapter_inventory",
        "local_policy",
        "local_maximum",
    }:
        if parsed_deadlines[required_deadline] is None:
            raise ConformanceError(
                f"impact simulation required freshness deadline "
                f"{required_deadline} is absent"
            )
    if valid_until > min(
        deadline
        for deadline in parsed_deadlines.values()
        if deadline is not None
    ):
        raise ConformanceError(
            "impact simulation valid_until exceeds an authoritative deadline"
        )
    capability_match = value["bindings"]["capability_match"]
    if capability_match is None:
        if freshness_deadlines["capability_match"] is not None:
            raise ConformanceError(
                "impact simulation has a capability deadline without a match"
            )
    else:
        if (
            freshness_deadlines["capability_match"]
            != capability_match["valid_until"]
        ):
            raise ConformanceError(
                "impact simulation capability deadline differs from its binding"
            )
        match_evaluated_at = _parse_timestamp(capability_match["evaluated_at"])
        match_valid_until = _parse_timestamp(capability_match["valid_until"])
        if (
            not match_evaluated_at < match_valid_until
            or match_evaluated_at > evaluated_at
            or evaluation_time < match_evaluated_at
            or evaluation_time >= match_valid_until
            or valid_until > match_valid_until
        ):
            raise ConformanceError(
                "impact simulation has a stale or overlong capability-match binding"
            )
    for revision_name, deadline_name in (
        ("enterprise_policy_revision", "enterprise_policy"),
        ("user_preferences_revision", "user_preferences"),
    ):
        if (value["bindings"][revision_name] is None) != (
            freshness_deadlines[deadline_name] is None
        ):
            raise ConformanceError(
                f"impact simulation {deadline_name} deadline presence differs "
                "from its revision"
            )

    requested_ids = _impact_sorted_unique(
        context["requested_action_ids"], "requested_action_ids"
    )
    requested_scope_ids = set(
        _impact_sorted_unique(
            context["requested_scope_ids"], "requested_scope_ids"
        )
    )
    if not requested_ids or len(requested_ids) > 64:
        raise ConformanceError(
            "impact simulation requires one through 64 requested actions"
        )
    authoritative = _derive_impact_actions(
        context["actions"],
        requested_ids,
        root=root,
        registry=schema_registry,
    )
    requested_outcome, requested_reasons = _impact_candidate_projection(
        context["candidate_check_facts"],
        context["matched_candidate"],
        value["bindings"],
    )
    check_facts_by_id = {
        fact["check_id"]: fact for fact in context["candidate_check_facts"]
    }
    for availability_check, deadline_name in (
        ("runtime_identity_availability", "runtime_identity"),
        ("runtime_attestation_availability", "runtime_attestation"),
    ):
        unavailable = (
            check_facts_by_id[availability_check]["state"] == "blocking"
        )
        if unavailable != (freshness_deadlines[deadline_name] is None):
            raise ConformanceError(
                f"impact simulation {deadline_name} deadline presence differs "
                "from its availability check"
            )
    if any(action_id not in authoritative for action_id in requested_ids):
        raise ConformanceError(
            "impact simulation request references an unknown authoritative action"
        )
    for action_id in requested_ids:
        action = authoritative[action_id]
        if (
            action["scope"] not in requested_scope_ids
            or not set(action["required_companion_action_ids"]).issubset(
                requested_ids
            )
        ):
            raise ConformanceError(
                "impact simulation request has an unavailable scope or unclosed "
                "required companion set"
            )

    requested_set = set(requested_ids)
    unrequested_ids = [
        action_id for action_id in authoritative if action_id not in requested_set
    ]
    selected_unrequested = sorted(
        unrequested_ids,
        key=lambda action_id: (
            -IMPACT_RISK_ORDER[authoritative[action_id]["risk"]],
            action_id.encode("utf-8"),
        ),
    )[:8]
    expected_ids = requested_ids + selected_unrequested
    examples = value["examples"]
    actual_ids = [example["action"]["action_id"] for example in examples]
    if actual_ids != expected_ids:
        raise ConformanceError(
            "impact simulation examples do not use the deterministic complete order"
        )

    requested_coverage = value["coverage"]["requested"]
    unrequested_coverage = value["coverage"]["unrequested"]
    if requested_coverage != {
        "total": len(requested_ids),
        "included": len(requested_ids),
        "complete": True,
    }:
        raise ConformanceError(
            "impact simulation requested coverage is not exact and complete"
        )
    if unrequested_coverage != {
        "total": len(unrequested_ids),
        "included": len(selected_unrequested),
        "truncated": len(unrequested_ids) > len(selected_unrequested),
    }:
        raise ConformanceError(
            "impact simulation unrequested coverage metadata is not exact"
        )

    for example, action_id in zip(examples, expected_ids, strict=True):
        relation = "requested" if action_id in requested_set else "unrequested"
        derived_outcome = (
            requested_outcome if relation == "requested" else "not_covered"
        )
        derived_reasons = (
            requested_reasons
            if relation == "requested"
            else ["action_not_requested"]
        )
        if (
            example["request_relation"] != relation
            or example["action"] != authoritative[action_id]
            or example["outcome"] != derived_outcome
            or example["reasons"] != derived_reasons
        ):
            raise ConformanceError(
                "impact simulation example differs from independently derived inputs"
            )
        reasons = _impact_sorted_unique(example["reasons"], "example reasons")
        outcome = example["outcome"]
        if relation == "unrequested" and (
            outcome != "not_covered" or reasons != ["action_not_requested"]
        ):
            raise ConformanceError(
                "impact simulation unrequested reasons are not the exact singleton"
            )
        if outcome == "covered" and reasons:
            raise ConformanceError(
                "impact simulation covered action must have no blocking reasons"
            )


def validate_impact_simulation_projection(
    projection: Any,
    surface: dict[str, Any],
    grant: dict[str, Any],
    execution: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    """Validate the fixture-only Runtime projection and its no-authority boundary."""

    if not isinstance(projection, dict) or set(projection) != {
        "phase",
        "evaluation_time",
        "authority_use",
        "current_binding_facts",
        "source",
        "result",
    }:
        raise ConformanceError(
            "impact simulation fixture projection must have the exact closed shape"
        )
    if (
        not isinstance(grant, dict)
        or not isinstance(execution, dict)
        or "impact_simulation" in grant
        or "impact_simulation" in execution
    ):
        raise ConformanceError(
            "impact simulation Result must be absent from closed Grant and Action objects"
        )
    if (
        projection["phase"] != "pre_issuance"
        or projection["authority_use"] != "none"
    ):
        raise ConformanceError(
            "impact simulation must remain pre-issuance and non-authoritative"
        )
    if (
        not isinstance(surface, dict)
        or surface.get("status") != "current"
        or surface.get("references") != "complete"
    ):
        raise ConformanceError(
            "impact simulation requires the complete current retained surface"
        )
    source = projection["source"]
    if not isinstance(source, dict) or set(source) != {
        "bindings",
        "requested_action_ids",
        "requested_scope_ids",
        "candidate_check_facts",
        "matched_candidate",
        "actions",
        "freshness_deadlines",
    }:
        raise ConformanceError(
            "impact simulation fixture source must contain exact authoritative inputs"
        )
    result = projection["result"]
    if (
        result["bindings"]["surface"]["surface_version"] != surface.get("version")
        or result["bindings"]["surface"]["surface_hash"]
        != surface.get("retained_hash")
        or source["requested_action_ids"] != grant.get("requested_actions")
        or source["requested_scope_ids"] != grant.get("requested_scopes")
        or grant.get("status") != "proposed"
        or grant.get("issued_actions") != []
        or grant.get("companion_closure") != "closed"
    ):
        raise ConformanceError(
            "impact simulation is detached from its retained surface or Grant request"
        )
    validate_impact_simulation(
        result,
        {
            "evaluation_time": projection["evaluation_time"],
            "current_binding_facts": projection["current_binding_facts"],
            **source,
        },
        root=root,
    )


def _canonical_json_rfc8785(value: Any) -> bytes:
    """Serialize Human profile JSON with the RFC 8785 reference implementation."""

    _validate_human_json_value(value)
    try:
        return rfc8785.dumps(value)
    except (rfc8785.CanonicalizationError, UnicodeError) as error:
        raise ConformanceError("value is not RFC 8785 canonicalizable") from error


def _canonical_object_hash(domain: str, value: Any) -> str:
    wrapper = {"domain": domain, "object": value}
    content = _canonical_json_rfc8785(wrapper)
    digest = hashlib.sha256(content).digest()
    return "sha-256:" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


@lru_cache(maxsize=1)
def _receipt_resource_oracle_binary() -> Path:
    """Build the pinned local receipt oracle once per conformance process."""

    cargo = shlex.split(os.environ.get("CARGO", "cargo"))
    if not cargo:
        raise ConformanceError("receipt resource oracle CARGO command is empty")
    try:
        completed = subprocess.run(
            [
                *cargo,
                "build",
                "--locked",
                "-p",
                "asp-replay-tool",
                "--bin",
                "asp-replay",
                "--message-format=json-render-diagnostics",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ConformanceError("receipt resource oracle is unavailable") from error
    if completed.returncode != 0:
        raise ConformanceError("receipt resource oracle could not be built")
    executable: Path | None = None
    for line in completed.stdout.splitlines():
        try:
            message = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if (
            message.get("reason") == "compiler-artifact"
            and message.get("target", {}).get("name") == "asp-replay"
            and isinstance(message.get("executable"), str)
        ):
            executable = Path(message["executable"])
    if executable is None:
        raise ConformanceError("receipt resource oracle build omitted its executable")
    if not executable.is_file():
        raise ConformanceError("receipt resource oracle binary is absent after build")
    return executable


@lru_cache(maxsize=128)
def _validate_receipt_resource_batch(request_bytes: bytes) -> None:
    """Require a valid receipt-local report without upgrading signature assurance."""

    try:
        request_text = request_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ConformanceError("receipt resource oracle request is not UTF-8") from error
    request = loads_strict_json(
        request_text, source="receipt resource oracle request"
    )
    expected_count = (
        len(request.get("resources", [])) if isinstance(request, dict) else -1
    )
    try:
        completed = subprocess.run(
            [str(_receipt_resource_oracle_binary()), "validate-receipts", "-"],
            cwd=ROOT,
            input=request_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ConformanceError("receipt resource oracle is unavailable") from error
    if completed.returncode not in {0, 1}:
        raise ConformanceError("receipt resource oracle failed before evaluation")
    try:
        report = loads_strict_json(
            completed.stdout.decode("utf-8"),
            source="receipt resource oracle report",
        )
    except (UnicodeDecodeError, ConformanceError) as error:
        raise ConformanceError("receipt resource oracle emitted an invalid report") from error
    if (
        not isinstance(report, dict)
        or set(report)
        != {
            "profile",
            "validation_scope",
            "verdict",
            "resources",
            "signatures_verified",
            "diagnostics",
        }
        or report.get("profile") != RECEIPT_RESOURCE_REPORT_PROFILE
        or report.get("validation_scope") != RECEIPT_RESOURCE_VALIDATION_SCOPE
        or report.get("signatures_verified") is not False
        or report.get("verdict") not in {"valid", "invalid"}
        or report.get("resources") != expected_count
        or not isinstance(report.get("diagnostics"), list)
        or len(report["diagnostics"]) > 256
        or any(
            not isinstance(item, dict)
            or set(item) != {"check_id", "severity", "path", "message"}
            or item.get("severity") != "error"
            or not all(
                isinstance(item.get(name), str)
                for name in ("check_id", "path", "message")
            )
            for item in report.get("diagnostics", [])
        )
        or (report.get("verdict") == "valid" and report.get("diagnostics") != [])
        or (completed.returncode == 0) != (report.get("verdict") == "valid")
    ):
        raise ConformanceError("receipt resource oracle report contract is invalid")
    if report["verdict"] != "valid":
        diagnostic = next(iter(report.get("diagnostics", [])), {})
        detail = diagnostic.get("message", "receipt resource is invalid")
        raise ConformanceError(f"receipt resource oracle rejected evidence: {detail}")


def _validate_mcp_receipt_resource_set(
    *,
    inner_type: str,
    payload: dict[str, Any],
    linked_uris: list[str],
    expected_records: Any,
) -> None:
    """Bind every response receipt reference to one exact authenticated resource."""

    references_present = (
        "receipt_id" in payload
        or "approval_receipt_id" in payload
        or "approval_receipt_hashes" in payload
    )
    if not references_present:
        if expected_records not in (None, []):
            raise ConformanceError(
                "action response exposes authenticated receipts without receipt identity"
            )
        return
    if not isinstance(expected_records, list) or not expected_records:
        raise ConformanceError(
            "action response receipt identities lack authenticated receipt resources"
        )
    if any(
        not isinstance(record, dict)
        or set(record) != {"uri", "receipt", "expected"}
        or not isinstance(record.get("uri"), str)
        or not isinstance(record.get("receipt"), dict)
        or not isinstance(record.get("expected"), dict)
        for record in expected_records
    ):
        raise ConformanceError("authenticated receipt resource record is invalid")
    expected_uris = [record["uri"] for record in expected_records]
    if expected_uris != linked_uris or len(expected_uris) != len(set(expected_uris)):
        raise ConformanceError(
            "authenticated receipt resources are not the exact one-to-one ResourceLink list"
        )

    referenced_indexes: set[int] = set()

    def require_one(*, receipt_id: Any, receipt_hash: Any, receipt_type: str,
                    approval_role: str | None) -> dict[str, Any]:
        matches = [
            (index, record)
            for index, record in enumerate(expected_records)
            if record["expected"].get("receipt_id") == receipt_id
            and record["expected"].get("receipt_hash") == receipt_hash
            and record["expected"].get("receipt_type") == receipt_type
            and record["expected"].get("approval_role") == approval_role
        ]
        if len(matches) != 1:
            raise ConformanceError(
                "receipt response reference does not resolve to exactly one authenticated resource"
            )
        index, record = matches[0]
        referenced_indexes.add(index)
        return record

    app_record: dict[str, Any] | None = None
    if "receipt_id" in payload:
        app_record = require_one(
            receipt_id=payload["receipt_id"],
            receipt_hash=payload["receipt_hash"],
            receipt_type="app",
            approval_role=None,
        )
    if "approval_receipt_id" in payload:
        require_one(
            receipt_id=payload["approval_receipt_id"],
            receipt_hash=payload["approval_receipt_hash"],
            receipt_type="approval",
            approval_role="application",
        )
    approval_hashes = payload.get("approval_receipt_hashes", {})
    if isinstance(approval_hashes, dict):
        for role, receipt_hash in approval_hashes.items():
            matches = [
                (index, record)
                for index, record in enumerate(expected_records)
                if record["expected"].get("receipt_hash") == receipt_hash
                and record["expected"].get("receipt_type") == "approval"
                and record["expected"].get("approval_role") == role
            ]
            if len(matches) != 1:
                raise ConformanceError(
                    "approval role/hash does not resolve to exactly one authenticated resource"
                )
            referenced_indexes.add(matches[0][0])
    if referenced_indexes != set(range(len(expected_records))):
        raise ConformanceError(
            "receipt ResourceLink list contains an unreferenced or substituted resource"
        )

    if app_record is not None:
        receipt = app_record["receipt"]
        for member in (
            "execution",
            "execution_hash",
            "approval_receipt_hashes",
            "effect_outcome",
            "actual_effects",
            "actual_effects_hash",
        ):
            if receipt.get(member) != payload.get(member) or (
                (member in receipt) != (member in payload)
            ):
                raise ConformanceError(
                    f"application receipt {member} differs from the action response"
                )
        if inner_type == "action.result":
            if receipt.get("result") != payload.get("result"):
                raise ConformanceError(
                    "application receipt result differs from the action response"
                )
            policy_decision = receipt.get("policy_decision")
            if (
                payload.get("result") == "success"
                and (
                    not isinstance(policy_decision, dict)
                    or policy_decision.get("outcome") != "allow"
                    or policy_decision.get("reason_code")
                    not in {"policy_allowed", "approval_satisfied"}
                )
            ):
                raise ConformanceError(
                    "successful action receipt conflicts with its Policy Decision"
                )
            if receipt.get("output_hash") != _canonical_object_hash(
                MCP_ACTION_OUTPUT_HASH_DOMAIN, payload.get("output")
            ):
                raise ConformanceError(
                    "application receipt output_hash differs from the exact action output"
                )
        else:
            error = receipt.get("error")
            if (
                not isinstance(error, dict)
                or _canonical_json_rfc8785(error)
                != _canonical_json_rfc8785(payload.get("error"))
            ):
                raise ConformanceError(
                    "application failure receipt error differs from the action response"
                )
            if receipt.get("result") == "success" or "output_hash" in receipt:
                raise ConformanceError(
                    "application failure receipt claims success or output evidence"
                )

    request = {
        "profile": RECEIPT_RESOURCE_REQUEST_PROFILE,
        "resources": expected_records,
    }
    _validate_receipt_resource_batch(_canonical_json_rfc8785(request))


def _hash_without_member(domain: str, value: dict[str, Any], member: str) -> str:
    hashing_view = copy.deepcopy(value)
    hashing_view.pop(member, None)
    return _canonical_object_hash(domain, hashing_view)


def _validate_embedded_schema(
    schema: Any, *, label: str, registry: Registry | None = None
) -> None:
    if not isinstance(schema, dict):
        raise ConformanceError(f"{label} must be a JSON Schema object")
    external_refs = [
        ref for ref in _external_schema_refs(schema) if not ref.startswith("#")
    ]
    if external_refs:
        raise ConformanceError(f"{label} must be self-contained")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise ConformanceError(f"{label} is not a valid JSON Schema") from error


def validate_human_elicitation(
    value: Any,
    context: dict[str, Any],
    *,
    root: Path = ROOT,
    registry: Registry | None = None,
    schema: dict[str, Any] | None = None,
) -> None:
    """Validate one standalone Human Elicitation profile message."""

    _validate_human_json_value(value)
    selected_registry = registry or _schema_registry(root)
    _validate_with_schema(
        value,
        schema
        or load_strict_json(
            root / "conformance" / "v1" / "human-elicitation.schema.json"
        ),
        "Human Elicitation message",
        registry=selected_registry,
    )
    if context != {}:
        raise ConformanceError("Human Elicitation schema context must be empty")

    if value["type"] == "elicitation.required":
        if value["requester"]["type"] == value["presenter"]["type"]:
            raise ConformanceError(
                "Human Elicitation requester.type and presenter.type must differ"
            )
        expected_context_hash = _canonical_object_hash(
            "https://github.com/0al-spec/agent-surface/hash/"
            "human-elicitation-context/v1",
            value["context"],
        )
        if value["context_hash"] != expected_context_hash:
            raise ConformanceError("Human Elicitation context_hash is invalid")
        expected_request_hash = _hash_without_member(
            "https://github.com/0al-spec/agent-surface/hash/"
            "human-elicitation-request/v1",
            value,
            "request_hash",
        )
        if value["request_hash"] != expected_request_hash:
            raise ConformanceError("Human Elicitation request_hash is invalid")

        kind = value["kind"]
        request = value["request"]
        if kind == "clarify":
            embedded = request["response_schema"]
            _validate_embedded_schema(
                embedded, label="clarification response_schema"
            )
            expected_schema_hash = _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/"
                "action-input-schema/v1",
                embedded,
            )
            if request["response_schema_hash"] != expected_schema_hash:
                raise ConformanceError(
                    "clarification response_schema_hash is invalid"
                )
        elif kind == "choose":
            option_ids = [item["option_id"] for item in request["options"]]
            if len(option_ids) != len(set(option_ids)):
                raise ConformanceError("Human Elicitation repeats an option_id")
            if not (
                request["min_selected"]
                <= request["max_selected"]
                <= len(option_ids)
            ):
                raise ConformanceError(
                    "Human Elicitation selection bounds exceed the option set"
                )
        elif kind == "redline":
            embedded = request["patch_schema"]
            _validate_embedded_schema(embedded, label="redline patch_schema")
            expected_schema_hash = _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/"
                "action-input-schema/v1",
                embedded,
            )
            if request["patch_schema_hash"] != expected_schema_hash:
                raise ConformanceError("redline patch_schema_hash is invalid")
    else:
        expected_response_hash = _hash_without_member(
            "https://github.com/0al-spec/agent-surface/hash/"
            "human-elicitation-response/v1",
            value,
            "response_hash",
        )
        if value["response_hash"] != expected_response_hash:
            raise ConformanceError("Human Elicitation response_hash is invalid")


def _decode_json_pointer(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ConformanceError("JSON Pointer must be empty or begin with '/'")
    return [
        token.replace("~1", "/").replace("~0", "~")
        for token in pointer[1:].split("/")
    ]


def _json_patch_array_index(
    token: str, *, length: int, allow_end: bool = False
) -> int:
    if re.fullmatch(r"0|[1-9][0-9]*", token) is None:
        raise ConformanceError("JSON Patch array index is invalid")
    try:
        index = int(token)
    except ValueError as error:
        raise ConformanceError("JSON Patch array index is invalid") from error
    maximum = length if allow_end else length - 1
    if index > maximum:
        raise ConformanceError("JSON Patch array index is invalid")
    return index


def _apply_json_patch(document: Any, operations: list[dict[str, Any]]) -> Any:
    candidate = copy.deepcopy(document)
    for operation in operations:
        if not isinstance(operation, dict) or operation.get("op") not in {
            "add",
            "remove",
            "replace",
        }:
            raise ConformanceError(
                "Human Elicitation redline uses an unsupported JSON Patch operation"
            )
        tokens = _decode_json_pointer(operation.get("path", ""))
        if not tokens:
            if operation["op"] == "remove":
                raise ConformanceError("Human Elicitation redline cannot remove the root")
            if "value" not in operation:
                raise ConformanceError("JSON Patch replacement lacks value")
            candidate = copy.deepcopy(operation["value"])
            continue
        parent = candidate
        for token in tokens[:-1]:
            try:
                parent = (
                    parent[
                        _json_patch_array_index(token, length=len(parent))
                    ]
                    if isinstance(parent, list)
                    else parent[token]
                )
            except ConformanceError:
                raise
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise ConformanceError(
                    "Human Elicitation redline path does not exist in its base"
                ) from error
        token = tokens[-1]
        try:
            if isinstance(parent, list):
                if operation["op"] == "add":
                    if token == "-":
                        parent.append(copy.deepcopy(operation["value"]))
                    else:
                        index = _json_patch_array_index(
                            token, length=len(parent), allow_end=True
                        )
                        parent.insert(index, copy.deepcopy(operation["value"]))
                elif operation["op"] == "remove":
                    del parent[
                        _json_patch_array_index(token, length=len(parent))
                    ]
                else:
                    parent[
                        _json_patch_array_index(token, length=len(parent))
                    ] = copy.deepcopy(operation["value"])
            elif isinstance(parent, dict):
                if operation["op"] == "remove":
                    del parent[token]
                else:
                    if operation["op"] == "replace" and token not in parent:
                        raise KeyError(token)
                    parent[token] = copy.deepcopy(operation["value"])
            else:
                raise TypeError("patch parent is not a container")
        except ConformanceError:
            raise
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ConformanceError(
                "Human Elicitation redline operation is invalid for its base"
            ) from error
    return candidate


def _changed_json_pointers(before: Any, after: Any, pointer: str = "") -> set[str]:
    if type(before) is not type(after):
        return {pointer}
    if isinstance(before, dict):
        changed: set[str] = set()
        for key in set(before) | set(after):
            escaped = key.replace("~", "~0").replace("/", "~1")
            child = f"{pointer}/{escaped}"
            if key not in before or key not in after:
                changed.add(child)
            else:
                changed.update(_changed_json_pointers(before[key], after[key], child))
        return changed
    if isinstance(before, list):
        if len(before) != len(after):
            return {pointer}
        changed = set()
        for index, (left, right) in enumerate(zip(before, after, strict=True)):
            changed.update(
                _changed_json_pointers(left, right, f"{pointer}/{index}")
            )
        return changed
    return set() if before == after else {pointer}


def validate_human_elicitation_projection(
    elicitation: Any,
    *,
    root: Path = ROOT,
    registry: Registry | None = None,
    schema: dict[str, Any] | None = None,
) -> None:
    """Validate one normalized request/response pair against authoritative state."""

    if not isinstance(elicitation, dict):
        raise ConformanceError("Human Elicitation projection must be an object")
    selected_registry = registry or _schema_registry(root)
    human_schema = schema or load_strict_json(
        root / "conformance" / "v1" / "human-elicitation.schema.json"
    )
    request = elicitation["request"]
    response = elicitation["response"]
    validate_human_elicitation(
        request,
        {},
        root=root,
        registry=selected_registry,
        schema=human_schema,
    )
    validate_human_elicitation(
        response,
        {},
        root=root,
        registry=selected_registry,
        schema=human_schema,
    )

    if (
        elicitation["authentication"] != "authenticated"
        or elicitation["selected_profile"] != HUMAN_ELICITATION_FEATURE_ID
        or request["requester"] != elicitation["authenticated_requester"]
        or request["presenter"] != elicitation["authenticated_presenter"]
        or response["responder"] != elicitation["authenticated_presenter"]
    ):
        raise ConformanceError(
            "Human Elicitation participant roles do not match authenticated state"
        )
    repeated_fields = (
        "elicitation_id",
        "revision",
        "kind",
        "session_id",
        "session_generation",
        "grant_id",
        "grant_hash",
        "surface_hash",
        "context_hash",
        "request_hash",
    )
    if any(request[field] != response[field] for field in repeated_fields):
        raise ConformanceError(
            "Human Elicitation response does not repeat the exact request binding"
        )
    authoritative_pairs = (
        ("session_id", "current_session_id"),
        ("session_generation", "current_session_generation"),
        ("grant_id", "current_grant_id"),
        ("grant_hash", "current_grant_hash"),
        ("surface_hash", "current_surface_hash"),
    )
    if any(
        request[message_field] != elicitation[state_field]
        for message_field, state_field in authoritative_pairs
    ):
        raise ConformanceError(
            "Human Elicitation tuple differs from authoritative current state"
        )

    revision = request["revision"]
    recorded_revision = elicitation["recorded_revision"]
    if revision < recorded_revision or revision > recorded_revision + 1:
        raise ConformanceError("Human Elicitation revision is stale or skipped")
    exact_terminal_replay = (
        elicitation["lifecycle"] == "resolved"
        and revision == recorded_revision
        and request["request_hash"] == elicitation["recorded_request_hash"]
        and response["response_hash"] == elicitation["recorded_response_hash"]
    )
    evaluation_time = datetime.fromisoformat(
        elicitation["evaluation_time"].replace("Z", "+00:00")
    )
    terminal_accepted_at = elicitation["terminal_accepted_at"]
    if exact_terminal_replay:
        if terminal_accepted_at == "absent":
            raise ConformanceError(
                "Human Elicitation terminal replay lacks terminal_accepted_at"
            )
        accepted_at = datetime.fromisoformat(
            terminal_accepted_at.replace("Z", "+00:00")
        )
        resolved_at_for_replay = datetime.fromisoformat(
            response["resolved_at"].replace("Z", "+00:00")
        )
        if not resolved_at_for_replay <= accepted_at <= evaluation_time:
            raise ConformanceError(
                "Human Elicitation terminal_accepted_at is not current"
            )
        replay_retained_until = accepted_at + timedelta(
            seconds=elicitation["replay_retention_seconds"]
        )
    else:
        replay_retained_until = evaluation_time
    if exact_terminal_replay and (
        elicitation["replay_record_state"] != "retained"
        or evaluation_time > replay_retained_until
    ):
        raise ConformanceError(
            "Human Elicitation terminal replay record is unavailable or expired"
        )
    if not exact_terminal_replay and (
        elicitation["replay_record_state"] != "not_applicable"
        or terminal_accepted_at != "absent"
    ):
        raise ConformanceError(
            "Human Elicitation non-replay baseline carries terminal replay state"
        )
    if revision == recorded_revision and not exact_terminal_replay:
        raise ConformanceError(
            "Human Elicitation revision conflicts with an immutable replay record"
        )
    if (
        elicitation["lifecycle"] not in {"pending", "resolved"}
        or response["disposition"] != "answered"
        or elicitation["authority_use"] != "informational"
    ):
        raise ConformanceError(
            "Human Elicitation baseline must resolve or exactly replay "
            "one informational request"
        )
    if elicitation["lifecycle"] == "resolved" and not exact_terminal_replay:
        raise ConformanceError(
            "Human Elicitation terminal state permits only an exact immutable replay"
        )
    resolved_at = datetime.fromisoformat(response["resolved_at"].replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(request["expires_at"].replace("Z", "+00:00"))
    if resolved_at > evaluation_time:
        raise ConformanceError(
            "Human Elicitation response was resolved after evaluation_time"
        )
    if resolved_at > expires_at:
        raise ConformanceError("Human Elicitation response was resolved after expiry")

    kind = request["kind"]
    request_body = request["request"]
    response_body = response["response"]
    if kind == "clarify":
        encoded = _canonical_json_rfc8785(response_body["answer"])
        if len(encoded) > request_body["max_bytes"]:
            raise ConformanceError("clarification answer exceeds max_bytes")
        _validate_with_schema(
            response_body["answer"],
            request_body["response_schema"],
            "clarification answer",
        )
    elif kind == "choose":
        selected = response_body["option_ids"]
        offered = {item["option_id"] for item in request_body["options"]}
        if (
            not set(selected).issubset(offered)
            or not request_body["min_selected"]
            <= len(selected)
            <= request_body["max_selected"]
        ):
            raise ConformanceError(
                "Human Elicitation response selects an unoffered or invalid option set"
            )
    elif kind == "step_up":
        authoritative_result = elicitation.get("authoritative_step_up_result")
        expected_authoritative_result = {
            "status": "verified",
            "result_ref": response_body["result_ref"],
            "verifier": response_body["verifier"],
            "audience": elicitation["authenticated_requester"],
            "subject": elicitation["authenticated_subject"],
            "elicitation_id": request["elicitation_id"],
            "revision": request["revision"],
            "context_hash": request["context_hash"],
            "achieved_assurance": response_body["achieved_assurance"],
            "authenticated_at": response_body["authenticated_at"],
            "expires_at": response_body["expires_at"],
        }
        if (
            elicitation["step_up_verification"] != "verified"
            or elicitation["secret_material"] != "absent"
            or response_body["verifier"]
            != elicitation.get("authenticated_verifier")
            or authoritative_result != expected_authoritative_result
            or not set(request_body["required_assurance"]).issubset(
                response_body["achieved_assurance"]
            )
        ):
            raise ConformanceError(
                "Human Elicitation step-up verifier binding is invalid, "
                "unverified, or exposes secret material"
            )
        authenticated_at = datetime.fromisoformat(
            response_body["authenticated_at"].replace("Z", "+00:00")
        )
        step_up_expires_at = datetime.fromisoformat(
            response_body["expires_at"].replace("Z", "+00:00")
        )
        maximum_age = timedelta(seconds=request_body["max_age_seconds"])
        if (
            not authenticated_at
            <= resolved_at
            <= evaluation_time
            <= step_up_expires_at
            or evaluation_time - authenticated_at > maximum_age
        ):
            raise ConformanceError(
                "Human Elicitation step-up timestamps exceed max_age_seconds "
                "or are not current"
            )
    elif kind == "edit":
        base = elicitation.get("authoritative_base")
        input_schema = elicitation.get("authoritative_input_schema")
        if (
            elicitation["candidate_validation"] != "passed"
            or request_body["base"] != base
            or request_body["base_hash"]
            != _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/action-input/v1",
                base,
            )
            or request_body["input_schema_hash"]
            != _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/"
                "action-input-schema/v1",
                input_schema,
            )
            or request["context"].get("input_hash") != request_body["base_hash"]
            or response_body["candidate_hash"]
            != _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/action-input/v1",
                response_body["candidate"],
            )
        ):
            raise ConformanceError(
                "Human Elicitation edit candidate is stale or not rebound"
            )
        _validate_embedded_schema(
            input_schema,
            label="authoritative action input schema",
        )
        _validate_with_schema(
            response_body["candidate"],
            input_schema,
            "Human Elicitation edit candidate",
        )
        changed = _changed_json_pointers(base, response_body["candidate"])
        editable = request_body["editable_paths"]
        if any(
            not any(path == allowed or path.startswith(allowed + "/") for allowed in editable)
            for path in changed
        ):
            raise ConformanceError("Human Elicitation edit changed a forbidden path")
    elif kind == "redline":
        base = elicitation.get("authoritative_base")
        candidate = _apply_json_patch(base, response_body["patch"])
        input_schema = elicitation.get("authoritative_input_schema")
        _validate_with_schema(
            response_body["patch"],
            request_body["patch_schema"],
            "Human Elicitation redline patch",
        )
        _validate_embedded_schema(
            input_schema,
            label="authoritative action input schema",
        )
        _validate_with_schema(
            candidate,
            input_schema,
            "Human Elicitation redline candidate",
        )
        if (
            elicitation["candidate_validation"] != "passed"
            or request_body["base_hash"]
            != _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/action-input/v1",
                base,
            )
            or request["context"].get("input_hash") != request_body["base_hash"]
            or response_body["base_hash"] != request_body["base_hash"]
            or response_body["candidate_hash"]
            != _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/action-input/v1",
                candidate,
            )
        ):
            raise ConformanceError(
                "Human Elicitation redline base or result binding is invalid"
            )
        changed = _changed_json_pointers(base, candidate)
        editable = request_body.get("editable_paths", [])
        if editable and any(
            not any(
                path == allowed or path.startswith(allowed + "/")
                for allowed in editable
            )
            for path in changed
        ):
            raise ConformanceError(
                "Human Elicitation redline changed a forbidden path"
            )
    if kind != "step_up" and (
        elicitation["step_up_verification"] != "not_applicable"
        or elicitation["secret_material"] != "absent"
        or "authenticated_verifier" in elicitation
        or "authoritative_step_up_result" in elicitation
    ):
        raise ConformanceError(
            "non-step-up Human Elicitation carries authentication state"
        )


def validate_agent_human_elicitation_projection(elicitation: Any) -> None:
    """Validate the minimized, purpose-bound Human answer exposed to an agent."""

    projection = elicitation.get("agent_projection")
    if not isinstance(projection, dict):
        raise ConformanceError(
            "Agent Adapter Human Elicitation projection is absent"
        )
    request = elicitation["request"]
    response = elicitation["response"]
    expected_binding = {
        "session_id": request["session_id"],
        "session_generation": request["session_generation"],
        "grant_id": request["grant_id"],
        "grant_hash": request["grant_hash"],
        "surface_hash": request["surface_hash"],
        "context_hash": request["context_hash"],
        "request_hash": request["request_hash"],
    }
    kind = request["kind"]
    expected_values = {
        "clarify": {
            "kind": "clarify",
            "answer": response.get("response", {}).get("answer"),
        },
        "choose": {
            "kind": "choose",
            "option_ids": response.get("response", {}).get("option_ids"),
        },
    }
    if (
        projection["origin"] != "presenter"
        or projection["purpose_binding"] != expected_binding
        or projection["exposure"] != "minimized"
        or projection["secret_material"] != "absent"
        or kind not in expected_values
        or projection["value"] != expected_values[kind]
    ):
        raise ConformanceError(
            "Agent Adapter Human answer is originated, unbound, "
            "overbroad, or secret-bearing"
        )


def _retry_after_projection(
    value: Any, *, label: str
) -> tuple[str, int | str] | None:
    if value == "absent":
        return None
    if not isinstance(value, dict) or set(value) != {"form", "value"}:
        raise ConformanceError(f"{label} is not the exact Retry-After projection")
    form = value["form"]
    projected = value["value"]
    if form == "delay_seconds":
        if (
            isinstance(projected, bool)
            or not isinstance(projected, int)
            or not 1 <= projected <= SAFE_INTEGER
        ):
            raise ConformanceError(
                f"{label} delay_seconds must be a positive I-JSON safe integer"
            )
        return form, projected
    if form == "http_date":
        if isinstance(projected, str) and _is_rfc9110_http_date(projected):
            return form, projected
        raise ConformanceError(f"{label} http_date is not RFC 9110 HTTP-date syntax")
    raise ConformanceError(f"{label} has an invalid normalized form or value")


def _is_rfc9110_http_date(value: str) -> bool:
    for pattern, uses_two_digit_year in HTTP_DATE_PATTERNS:
        match = pattern.fullmatch(value)
        if match is None:
            continue
        year = int(match["year"])
        if uses_two_digit_year:
            year += 2000 if year <= 68 else 1900
        try:
            datetime(
                year,
                HTTP_MONTHS[match["month"]],
                int(match["day"]),
                int(match["hour"]),
                int(match["minute"]),
                int(match["second"]),
            )
        except ValueError:
            return False
        return True
    return False


def validate_http_capacity_projection(
    transport: Any, response: dict[str, Any]
) -> None:
    """Validate one normalized authenticated HTTP capacity response projection."""

    if not isinstance(transport, dict) or set(transport) != {
        "binding",
        "authentication",
        "status",
        "cache_control_no_store",
        "retry_after",
    }:
        raise ConformanceError(
            "HTTP capacity projection must contain the exact normalized fields"
        )
    if (
        transport["binding"] != "http"
        or transport["authentication"] != "authenticated"
    ):
        raise ConformanceError(
            "HTTP capacity projection must select an authenticated HTTP binding"
        )
    code = response["code"]
    expected_status = 429 if code == "rate_limited" else 503
    if transport["status"] != expected_status:
        raise ConformanceError("HTTP capacity status does not match its ASP error code")
    if transport["cache_control_no_store"] is not True:
        raise ConformanceError(
            "HTTP capacity projection must contain the normalized no-store directive"
        )
    retry_after = _retry_after_projection(
        transport["retry_after"], label="HTTP capacity Retry-After"
    )
    if retry_after is None:
        return
    if response["retryable"] is not True:
        raise ConformanceError(
            "non-retryable HTTP capacity response cannot carry Retry-After"
        )
    form, value = retry_after
    if code == "rate_limited":
        limit = response.get("limit")
        if (
            form != "delay_seconds"
            or not isinstance(limit, dict)
            or limit.get("retry_after_seconds") != value
        ):
            raise ConformanceError(
                "HTTP 429 Retry-After must be delay_seconds equal to the body hint"
            )


def validate_ahp_binding_projection(ahp: Any) -> None:
    """Validate one normalized ASP-over-AHP binding projection."""

    exact_fields = {
        "profile",
        "negotiated_profile",
        "authentication",
        "ahp_session_id",
        "representation_id",
        "representation_revision",
        "recorded_representation_revision",
        "binding_fingerprint",
        "recorded_binding_fingerprint",
        "control_id",
        "control_kind",
        "asp_message_type",
        "asp_session_id",
        "bound_asp_session_id",
        "asp_session_generation",
        "bound_asp_session_generation",
        "asp_grant_id",
        "bound_asp_grant_id",
        "asp_grant_hash",
        "bound_asp_grant_hash",
        "asp_surface_hash",
        "bound_asp_surface_hash",
        "asp_action_id",
        "bound_asp_action_id",
        "receipt_use",
    }
    if not isinstance(ahp, dict) or set(ahp) != exact_fields:
        raise ConformanceError(
            "ASP-over-AHP projection must contain the exact normalized fields"
        )
    if (
        ahp["profile"] != ASP_OVER_AHP_FEATURE_ID
        or ahp["negotiated_profile"] != ASP_OVER_AHP_FEATURE_ID
    ):
        raise ConformanceError(
            "ASP-over-AHP projection must retain the explicitly negotiated profile"
        )
    if ahp["authentication"] != "authenticated":
        raise ConformanceError(
            "ASP-over-AHP projection must use an authenticated AHP carrier"
        )
    tuple_pairs = (
        ("asp_session_id", "bound_asp_session_id"),
        ("asp_session_generation", "bound_asp_session_generation"),
        ("asp_grant_id", "bound_asp_grant_id"),
        ("asp_grant_hash", "bound_asp_grant_hash"),
        ("asp_surface_hash", "bound_asp_surface_hash"),
        ("asp_action_id", "bound_asp_action_id"),
    )
    if any(ahp[current] != ahp[bound] for current, bound in tuple_pairs):
        raise ConformanceError(
            "ASP-over-AHP projection does not match its bound ASP authority tuple"
        )
    revision = ahp["representation_revision"]
    recorded_revision = ahp["recorded_representation_revision"]
    if revision < recorded_revision or (
        revision == recorded_revision
        and ahp["binding_fingerprint"] != ahp["recorded_binding_fingerprint"]
    ):
        raise ConformanceError(
            "ASP-over-AHP projection is stale or conflicts with a recorded revision"
        )
    if ahp["control_kind"] == "present":
        if ahp["asp_message_type"] != "session.state" or ahp["asp_action_id"] != "none":
            raise ConformanceError(
                "AHP presentation control must bind session.state without an action"
            )
    elif (
        ahp["control_kind"] != "invoke"
        or ahp["asp_message_type"] != "action.request"
        or ahp["asp_action_id"] == "none"
    ):
        raise ConformanceError(
            "AHP invocation control must bind one exact ASP action.request"
        )
    if ahp["receipt_use"] != "informational":
        raise ConformanceError("AHP receipt projection cannot carry ASP authority")


def _validate_mcp_fresh_ordinary_admission(
    document: dict[str, Any], action_id: str
) -> None:
    """Compose the ordinary ASP admission invariants used by MCP carriers."""

    surface = document["surface"]
    grant = document["grant"]
    execution = document["execution"]
    if (
        surface["status"] != "current"
        or surface["references"] != "complete"
        or surface["candidate_hash"] != surface["retained_hash"]
        or grant["status"] != "active"
        or grant["revocation_state"] != "active"
        or grant["claimed_issuer"] != grant["issuer"]
        or grant["passport_status"] != "current"
        or grant["companion_closure"] != "closed"
        or not set(grant["issued_actions"]).issubset(grant["requested_actions"])
        or action_id not in grant["issued_actions"]
        or execution["input_hash"] != execution["recorded_input_hash"]
        or execution["input_schema_hash"]
        != execution["recorded_input_schema_hash"]
        or execution["normalization"] != "fixed_point"
        or execution["execution_hash"] != execution["recorded_execution_hash"]
        or execution["approval_hash"] != execution["recorded_approval_hash"]
        or execution["policy"] != "allow"
        or execution["runtime_identity"] != execution["bound_runtime_identity"]
        or execution["sender_credential_audience"]
        != execution["bound_credential_audience"]
        or execution["proof_session_binding"]
        != execution["bound_session_binding"]
        or execution["attestation"] != "current"
    ):
        raise ConformanceError(
            "fresh ASP-over-MCP admission failed ordinary ASP authority checks"
        )


def validate_mcp_binding_projection(
    mcp: Any,
    document: dict[str, Any],
    operation: str,
) -> None:
    """Validate one normalized ASP-over-MCP binding projection."""

    authority = document.get("mcp_authority")
    if not isinstance(authority, dict):
        raise ConformanceError(
            "ASP-over-MCP projection lacks an independent manifest/Grant authority record"
        )
    if operation == "issue_mcp_grant":
        grant = document["grant"]
        endpoint = authority.get("manifest_binding_endpoint")
        endpoint_parts = urlsplit(endpoint) if isinstance(endpoint, str) else None
        authorization_mode = authority.get("authorization_mode")
        authorization_composition = authority.get("authorization_composition")
        credential_binding = authority.get("credential_binding")
        credential_audience = authority.get("manifest_credential_audience")
        credential_audience_parts = (
            urlsplit(credential_audience)
            if isinstance(credential_audience, str)
            else None
        )
        if (
            credential_audience_parts is None
            or credential_audience_parts.scheme != "https"
            or not credential_audience_parts.netloc
        ):
            raise ConformanceError(
                "ASP-over-MCP credential audience is not an absolute HTTPS URI"
            )
        valid_authorization = (
            authorization_mode == "asp_native"
            and authorization_composition == "asp-native"
            and credential_binding in {"dpop", "compatibility_bearer", "mtls"}
            and isinstance(credential_audience, str)
        ) or (
            authorization_mode == "mcp_oauth_dual_use"
            and authorization_composition == "mcp-oauth-dual-use"
            and credential_binding
            in {"compatibility_bearer", "mtls_bound_bearer"}
            and credential_audience == endpoint
        )
        if (
            endpoint_parts is None
            or endpoint_parts.scheme != "https"
            or not endpoint_parts.netloc
            or "?" in endpoint
            or "#" in endpoint
            or endpoint_parts.query
            or endpoint_parts.fragment
            or endpoint_parts.username is not None
            or endpoint_parts.password is not None
            or document["surface"]["status"] != "current"
            or grant["passport_status"] != "current"
            or grant["companion_closure"] != "closed"
            or not set(grant["issued_actions"]).issubset(grant["requested_actions"])
            or authority.get("requested_locations") != [endpoint]
            or authority.get("issued_locations") != authority.get("requested_locations")
            or not valid_authorization
        ):
            raise ConformanceError(
                "pre-channel MCP Grant location or authorization selection is invalid"
            )
        return

    exact_fields = {
        "profile",
        "negotiated_profile",
        "extension_id",
        "negotiated_extension",
        "capability_container",
        "protocol_version",
        "negotiated_protocol_version",
        "protocol_header",
        "initialization_state",
        "bootstrap_manifest_state",
        "bootstrap_binding_declaration",
        "binding_endpoint",
        "grant_location_binding",
        "endpoint_redirect_policy",
        "http_origin_check",
        "post_media_negotiation",
        "listener_authentication",
        "mcp_session_id_source",
        "session_header_use",
        "session_binding",
        "asp_session_id",
        "asp_session_generation",
        "request_trace_id",
        "request_span_id",
        "result_trace_id",
        "result_span_id",
        "listener_state",
        "listener_response",
        "stream_state",
        "stream_recovery",
        "asp_session_state",
        "transport_lifecycle_event",
        "fresh_initialize_authority",
        "session_generation_transition",
        "session_lookup_outcome",
        "interruption_authority",
        "session_binding_persistence",
        "active_mcp_session_cardinality",
        "generation_drain_state",
        "old_record_generation_binding",
        "core_resume_outcome",
        "transport",
        "authentication",
        "authorization_mode",
        "authorization_composition",
        "credential_binding",
        "transport_credential_scheme",
        "canonical_mcp_server_uri",
        "token_audience",
        "bound_token_audience",
        "credential_proof_target_uri",
        "credential_custody",
        "token_forwarding",
        "execution_token_handling",
        "outer_idempotency_header",
        "discovery_kind",
        "manifest_resource_uri",
        "manifest_content_uri",
        "manifest_content_kind",
        "manifest_content_mime",
        "manifest_content_ijson",
        "manifest_content_meta",
        "manifest_uri_binding",
        "manifest_subscription",
        "resource_update_state",
        "binding_view_id",
        "current_binding_view_id",
        "tool_list_state",
        "tools_changed_state",
        "binding_view_tool_set",
        "page_tool_binding_records",
        "authorized_projection_state",
        "authorized_projection_binding",
        "manifest_schema_dialect",
        "mapped_input_schema_dialect",
        "mapped_output_schema_dialect",
        "binding_input_schema_hash",
        "current_binding_input_schema_hash",
        "binding_output_schema_hash",
        "current_binding_output_schema_hash",
        "schema_snapshot_state",
        "schema_reference_closure",
        "binding_view_use",
        "completed_record_state",
        "replay_materialization",
        "retained_snapshot_state",
        "rotation_cause",
        "replay_disclosure_authorization",
        "initialize_display_metadata",
        "tool_display_metadata",
        "resource_link_display_metadata",
        "manifest_action_ids",
        "tool_name",
        "action_id",
        "mapped_action_id",
        "action_mode",
        "mapped_action_mode",
        "grant_id",
        "bound_grant_id",
        "grant_hash",
        "bound_grant_hash",
        "idempotency_key",
        "bound_idempotency_key",
        "idempotency_requirement",
        "surface_version",
        "surface_hash",
        "bound_surface_hash",
        "arguments_input_hash",
        "bound_input_hash",
        "asp_grant_proof",
        "mcp_oauth_use",
        "annotations_use",
        "agent_request_projection",
        "agent_meta_access",
        "agent_credential_access",
        "agent_result_projection",
        "agent_transport_result_access",
        "agent_transport_authority_use",
        "result_channel",
        "result_text_consistency",
        "result_surface_version",
        "result_surface_hash",
        "result_action_id",
        "result_input_hash",
        "result_grant_id",
        "result_grant_hash",
        "result_idempotency_key",
        "result_integrity",
        "result_output_schema",
        "result_is_error_consistency",
        "result_delivery_boundary",
        "error_mapping",
        "binding_error_semantics",
        "action_error_semantics",
        "capacity_error_carrier",
        "transport_status_semantics",
        "task_support",
        "progress_use",
        "progress_token_source",
        "progress_token_echo",
        "progress_payload",
        "progress_stream",
        "cancellation_phase",
        "cancellation_use",
        "retry_behavior",
        "receipt_channel",
        "receipt_requirement",
        "receipt_resource_authentication",
        "receipt_integrity",
        "receipt_link_binding",
        "receipt_persistence",
        "receipt_rematerialization",
        "transport_error_exposure",
    }
    if not isinstance(mcp, dict) or set(mcp) != exact_fields:
        raise ConformanceError(
            "ASP-over-MCP projection must contain the exact normalized fields"
        )
    if (
        mcp["profile"] != ASP_OVER_MCP_FEATURE_ID
        or mcp["negotiated_profile"] != ASP_OVER_MCP_FEATURE_ID
        or mcp["extension_id"] != ASP_OVER_MCP_EXTENSION_ID
        or mcp["negotiated_extension"] != ASP_OVER_MCP_EXTENSION_ID
        or mcp["capability_container"] != "experimental"
    ):
        raise ConformanceError(
            "ASP-over-MCP projection must retain the negotiated experimental capability"
        )
    if any(
        mcp[field] != ASP_OVER_MCP_PROTOCOL_VERSION
        for field in (
            "protocol_version",
            "negotiated_protocol_version",
            "protocol_header",
        )
    ):
        raise ConformanceError("ASP-over-MCP projection must pin MCP 2025-11-25")
    if mcp["initialization_state"] != "initialized_notified":
        raise ConformanceError(
            "ASP-over-MCP use must follow notifications/initialized"
        )
    if (
        mcp["bootstrap_manifest_state"] != "verified_before_mcp"
        or mcp["bootstrap_binding_declaration"] != "exact"
        or mcp["binding_endpoint"] != mcp["canonical_mcp_server_uri"]
        or mcp["binding_endpoint"] != authority["manifest_binding_endpoint"]
        or mcp["manifest_resource_uri"] != authority["manifest_resource_uri"]
        or mcp["grant_location_binding"] != "verified"
        or mcp["endpoint_redirect_policy"] != "no_endpoint_changes"
        or mcp["http_origin_check"] != "allowed_before_asp"
        or mcp["post_media_negotiation"] != "json_and_event_stream"
        or mcp["listener_authentication"] != "selected"
        or mcp["mcp_session_id_source"] != "server_secure"
        or mcp["session_header_use"] != "all_post_get_delete"
        or mcp["session_binding"] != "exact"
        or mcp["listener_state"] != "open_before_subscribe"
        or mcp["listener_response"] != "text_event_stream"
        or mcp["stream_state"] != "current"
        or mcp["stream_recovery"] != "refetch_or_fresh_initialize"
    ):
        raise ConformanceError("ASP-over-MCP bootstrap endpoint is not pinned")
    if (
        mcp["discovery_kind"] != "complete_authorized_snapshot"
        or mcp["manifest_subscription"] != "active"
        or mcp["tool_list_state"] != "complete"
        or mcp["manifest_uri_binding"] != "verified"
        or mcp["manifest_content_uri"] != mcp["manifest_resource_uri"]
        or mcp["manifest_content_kind"] != "text_resource_contents"
        or mcp["manifest_content_mime"] != "application/json"
        or mcp["manifest_content_ijson"] != "valid"
        or mcp["manifest_content_meta"] != "omitted"
        or mcp["mapped_input_schema_dialect"] != mcp["manifest_schema_dialect"]
        or mcp["mapped_output_schema_dialect"] != mcp["manifest_schema_dialect"]
        or mcp["initialize_display_metadata"] != "omitted"
        or mcp["tool_display_metadata"] != "omitted"
        or mcp["resource_link_display_metadata"] != "omitted"
        or mcp["binding_view_tool_set"] != "asp_mapped_only"
        or mcp["page_tool_binding_records"] != "identical"
        or mcp["authorized_projection_binding"] != "absent_or_exact"
        or mcp["authorized_projection_state"] not in {"absent", "exact"}
        or mcp["schema_reference_closure"] != "self_contained"
    ):
        raise ConformanceError("ASP-over-MCP discovery snapshot is incomplete or stale")

    if (
        mcp["manifest_action_ids"] != authority["manifest_action_ids"]
        or mcp["authorized_projection_state"]
        != authority["authorized_projection_state"]
        or mcp["authorized_projection_binding"]
        != authority["authorized_projection_binding"]
        or mcp["surface_version"] != authority["surface_version"]
        or mcp["surface_hash"] != authority["surface_hash"]
    ):
        raise ConformanceError(
            "ASP-over-MCP view differs from independent manifest authority"
        )

    current_view = (
        mcp["binding_view_use"] == "current_admission"
        and mcp["resource_update_state"] == "current"
        and mcp["binding_view_id"] == mcp["current_binding_view_id"]
        and mcp["tools_changed_state"] == "stable"
        and mcp["binding_input_schema_hash"]
        == mcp["current_binding_input_schema_hash"]
        and mcp["binding_output_schema_hash"]
        == mcp["current_binding_output_schema_hash"]
        and mcp["schema_snapshot_state"] == "current"
        and mcp["completed_record_state"] == "not_applicable"
        and mcp["replay_materialization"] == "not_applicable"
        and mcp["retained_snapshot_state"] == "not_applicable"
        and mcp["replay_disclosure_authorization"] == "not_applicable"
    )
    current_completed_replay = (
        mcp["binding_view_use"] == "current_completed_replay"
        and operation in {"execute_mcp_action", "mediate_mcp_action"}
        and mcp["resource_update_state"] == "current"
        and mcp["binding_view_id"] == mcp["current_binding_view_id"]
        and mcp["tools_changed_state"] == "stable"
        and mcp["binding_input_schema_hash"]
        == mcp["current_binding_input_schema_hash"]
        and mcp["binding_output_schema_hash"]
        == mcp["current_binding_output_schema_hash"]
        and mcp["schema_snapshot_state"] == "current"
        and mcp["completed_record_state"] == "exact_authenticated"
        and mcp["replay_materialization"] == "exact_persisted_result_and_receipt"
        and mcp["retained_snapshot_state"] == "persisted_across_restart"
        and mcp["rotation_cause"] == "none"
        and mcp["replay_disclosure_authorization"] == "allowed"
        and mcp["idempotency_requirement"] == "required"
        and mcp["idempotency_key"] != "none"
    )
    retained_completed_replay = (
        mcp["binding_view_use"] == "retained_completed_replay"
        and operation in {"execute_mcp_action", "mediate_mcp_action"}
        and mcp["binding_view_id"] != mcp["current_binding_view_id"]
        and mcp["tools_changed_state"] == "changed_after_snapshot"
        and mcp["schema_snapshot_state"] == "retained"
        and mcp["completed_record_state"] == "exact_authenticated"
        and mcp["replay_materialization"]
        == "exact_persisted_result_and_receipt"
        and mcp["retained_snapshot_state"] == "persisted_across_restart"
        and mcp["replay_disclosure_authorization"] == "allowed"
        and mcp["idempotency_requirement"] == "required"
        and mcp["idempotency_key"] != "none"
        and (
            (
                mcp["rotation_cause"] == "manifest"
                and mcp["resource_update_state"] == "updated"
            )
            or (
                mcp["rotation_cause"] == "input_schema"
                and mcp["binding_input_schema_hash"]
                != mcp["current_binding_input_schema_hash"]
            )
            or (
                mcp["rotation_cause"] == "output_schema"
                and mcp["binding_output_schema_hash"]
                != mcp["current_binding_output_schema_hash"]
            )
            or mcp["rotation_cause"] == "view_context"
        )
    )
    if not current_view and not current_completed_replay and not retained_completed_replay:
        raise ConformanceError(
            "ASP-over-MCP view is neither current nor an exact retained completed replay"
        )
    active_session = (
        mcp["asp_session_state"] == "active"
        and mcp["session_generation_transition"] == "unchanged"
        and mcp["session_lookup_outcome"] == "bound"
        and mcp["interruption_authority"] == "not_applicable"
        and mcp["generation_drain_state"] == "not_applicable"
        and mcp["core_resume_outcome"] == "not_applicable"
        and (
            (
                mcp["transport_lifecycle_event"] == "none"
                and mcp["fresh_initialize_authority"] == "not_applicable"
            )
            or (
                mcp["transport_lifecycle_event"]
                == "call_or_listener_loss_recovered"
                and mcp["fresh_initialize_authority"] == "transport_only"
            )
        )
    )
    resumed_session = (
        mcp["asp_session_state"] == "active"
        and mcp["transport_lifecycle_event"] == "session_terminated"
        and mcp["fresh_initialize_authority"] == "no_asp_reactivation"
        and mcp["session_generation_transition"] == "incremented"
        and mcp["session_lookup_outcome"] == "bound"
        and mcp["interruption_authority"] == "server_or_authenticated_owner"
        and mcp["generation_drain_state"] == "drained"
        and mcp["core_resume_outcome"] == "accepted"
    )
    nonmutating_session_lookup_404 = (
        operation == "publish_mcp_surface"
        and current_view
        and mcp["asp_session_state"] == "active"
        and mcp["transport_lifecycle_event"] == "session_lookup_404_recovered"
        and mcp["fresh_initialize_authority"] == "transport_only"
        and mcp["session_generation_transition"] == "unchanged"
        and mcp["session_lookup_outcome"]
        in {"unknown_404_no_mutation", "auth_mismatch_404_no_mutation"}
        and mcp["interruption_authority"] == "not_applicable"
        and mcp["generation_drain_state"] == "not_applicable"
        and mcp["core_resume_outcome"] == "not_applicable"
    )
    interrupted_closed_path = (
        (current_completed_replay or retained_completed_replay)
        and mcp["asp_session_state"] == "interrupted"
        and mcp["transport_lifecycle_event"] == "session_terminated"
        and mcp["fresh_initialize_authority"] == "no_asp_reactivation"
        and mcp["session_generation_transition"] == "unchanged"
        and mcp["session_lookup_outcome"] == "bound"
        and mcp["interruption_authority"] == "server_or_authenticated_owner"
        and mcp["generation_drain_state"] == "closed_path_in_progress"
        and mcp["core_resume_outcome"] == "not_applicable"
    )
    if (
        mcp["session_binding_persistence"] != "durable"
        or mcp["active_mcp_session_cardinality"] != "one"
        or mcp["old_record_generation_binding"] != "original_generation"
    ):
        raise ConformanceError("ASP-over-MCP session-generation binding is not durable")
    if (
        not active_session
        and not resumed_session
        and not nonmutating_session_lookup_404
        and not interrupted_closed_path
    ):
        raise ConformanceError(
            "ASP-over-MCP transport lifecycle did not preserve or explicitly resume the ASP session"
        )
    manifest_uri = urlsplit(mcp["manifest_resource_uri"])
    if not manifest_uri.scheme:
        raise ConformanceError("ASP-over-MCP manifest resource URI is not absolute")
    endpoint_value = mcp["canonical_mcp_server_uri"]
    endpoint = urlsplit(endpoint_value)
    if (
        endpoint.scheme != "https"
        or not endpoint.netloc
        or "?" in endpoint_value
        or "#" in endpoint_value
        or endpoint.query
        or endpoint.fragment
        or endpoint.username is not None
        or endpoint.password is not None
    ):
        raise ConformanceError(
            "ASP-over-MCP canonical endpoint is not credential-free fragmentless HTTPS"
        )

    credential_audience = authority["manifest_credential_audience"]
    credential_audience_parts = urlsplit(credential_audience)
    if (
        credential_audience_parts.scheme != "https"
        or not credential_audience_parts.netloc
    ):
        raise ConformanceError(
            "ASP-over-MCP credential audience is not an absolute HTTPS URI"
        )
    if (
        authority["issued_locations"] != authority["requested_locations"]
        or endpoint_value not in authority["issued_locations"]
    ):
        raise ConformanceError(
            "ASP-over-MCP endpoint is outside independent Grant locations"
        )

    action_id = mcp["action_id"]
    expected_tool_name = "asp.action." + hashlib.sha256(
        action_id.encode("utf-8")
    ).hexdigest()
    if (
        action_id != mcp["mapped_action_id"]
        or action_id != authority["selected_action_id"]
        or mcp["tool_name"] != expected_tool_name
        or mcp["action_mode"] != mcp["mapped_action_mode"]
        or mcp["action_mode"] != authority["selected_action_mode"]
        or mcp["manifest_schema_dialect"] != authority["schema_dialect"]
        or mcp["mapped_input_schema_dialect"] != authority["schema_dialect"]
        or mcp["mapped_output_schema_dialect"] != authority["schema_dialect"]
        or mcp["binding_input_schema_hash"] != authority["input_schema_hash"]
        or mcp["binding_output_schema_hash"] != authority["output_schema_hash"]
        or mcp["action_mode"]
        not in {"read", "dry_run", "propose", "reserve", "commit", "compensate", "revert"}
        or not isinstance(mcp["manifest_action_ids"], list)
        or mcp["manifest_action_ids"]
        != sorted(set(mcp["manifest_action_ids"]), key=lambda item: item.encode("utf-8"))
        or action_id not in mcp["manifest_action_ids"]
    ):
        raise ConformanceError("MCP tool does not map to one exact manifest ASP action")

    if (
        mcp["transport"] != "streamable_http"
        or mcp["authentication"] != "authenticated"
        or mcp["token_audience"] != mcp["bound_token_audience"]
        or mcp["token_audience"] != authority["manifest_credential_audience"]
        or mcp["credential_proof_target_uri"]
        != authority["credential_proof_target_uri"]
        or mcp["credential_proof_target_uri"]
        != mcp["canonical_mcp_server_uri"]
        or mcp["authorization_mode"] != authority["authorization_mode"]
        or mcp["authorization_composition"] != authority["authorization_composition"]
        or mcp["credential_custody"] != "runtime"
        or mcp["token_forwarding"] != "prohibited"
        or mcp["execution_token_handling"] != "runtime_injected_meta_only"
        or mcp["outer_idempotency_header"] != "omitted"
    ):
        raise ConformanceError(
            "ASP-over-MCP credential or execution-token custody is invalid"
        )
    if mcp["authorization_mode"] == "asp_native":
        valid_auth = (
            mcp["authorization_composition"] == "asp-native"
            and mcp["mcp_oauth_use"] == "not_selected"
            and (
                (
                    mcp["credential_binding"] == "dpop"
                    and mcp["transport_credential_scheme"] == "dpop"
                )
                or (
                    mcp["credential_binding"] == "compatibility_bearer"
                    and mcp["transport_credential_scheme"] == "bearer"
                )
                or (
                    mcp["credential_binding"] == "mtls"
                    and mcp["transport_credential_scheme"] == "mtls"
                )
            )
        )
    elif mcp["authorization_mode"] == "mcp_oauth_dual_use":
        valid_auth = (
            mcp["authorization_composition"] == "mcp-oauth-dual-use"
            and mcp["mcp_oauth_use"] == "dual_use_verified"
            and mcp["transport_credential_scheme"] == "bearer"
            and mcp["token_audience"] == mcp["canonical_mcp_server_uri"]
            and mcp["credential_binding"]
            in {"compatibility_bearer", "mtls_bound_bearer"}
        )
    else:
        valid_auth = False
    if not valid_auth:
        raise ConformanceError("ASP-over-MCP authorization composition is invalid")

    if current_view and (
        document["surface"]["status"] != "current"
        or document["surface"]["references"] != "complete"
        or document["surface"]["candidate_hash"]
        != document["surface"]["retained_hash"]
        or mcp["surface_version"] != document["surface"]["version"]
        or mcp["surface_hash"] != document["surface"]["retained_hash"]
    ):
        raise ConformanceError(
            "ASP-over-MCP current view differs from the authoritative surface"
        )

    if operation == "publish_mcp_surface":
        if not current_view:
            raise ConformanceError("surface publication cannot use a retained MCP view")
        return

    if operation == "adapt_mcp_action":
        if not current_view:
            raise ConformanceError("Agent Adapter cannot consume a retained MCP view")
        if (
            mcp["agent_request_projection"] != "tool_and_arguments_only"
            or mcp["agent_meta_access"] != "none"
            or mcp["agent_credential_access"] != "none"
            or mcp["agent_result_projection"] != "purpose_minimized_output"
            or mcp["agent_transport_result_access"] != "none"
            or mcp["agent_transport_authority_use"] != "none"
        ):
            raise ConformanceError(
                "Agent Adapter crossed the ASP-over-MCP authority boundary"
            )
        return

    if operation not in {"execute_mcp_action", "mediate_mcp_action"}:
        raise ConformanceError(f"unknown ASP-over-MCP operation {operation!r}")

    if action_id not in document["grant"]["issued_actions"]:
        raise ConformanceError("MCP execution is outside the issued ASP Grant")

    pair_fields = (
        ("grant_id", "bound_grant_id"),
        ("grant_hash", "bound_grant_hash"),
        ("idempotency_key", "bound_idempotency_key"),
        ("surface_hash", "bound_surface_hash"),
        ("arguments_input_hash", "bound_input_hash"),
    )
    if any(mcp[current] != mcp[bound] for current, bound in pair_fields):
        raise ConformanceError("ASP-over-MCP request authority tuple is detached")
    if (
        mcp["grant_id"] != authority["grant_id"]
        or mcp["grant_hash"] != authority["grant_hash"]
        or mcp["idempotency_key"] != authority["idempotency_key"]
        or mcp["asp_session_id"] != authority["asp_session_id"]
        or mcp["asp_session_generation"] != authority["asp_session_generation"]
        or mcp["request_trace_id"] != authority["trace_id"]
        or mcp["request_span_id"] != authority["request_span_id"]
        or mcp["result_trace_id"] != authority["trace_id"]
        or mcp["result_span_id"] != authority["result_span_id"]
        or mcp["result_span_id"] == mcp["request_span_id"]
    ):
        raise ConformanceError(
            "ASP-over-MCP request/result tuple differs from independent authority"
        )
    if (current_view or current_completed_replay) and (
        mcp["surface_version"] != document["surface"]["version"]
        or mcp["surface_hash"] != document["surface"]["retained_hash"]
        or mcp["arguments_input_hash"] != document["execution"]["input_hash"]
    ):
        raise ConformanceError("ASP-over-MCP request differs from authoritative ASP state")

    if mcp["asp_grant_proof"] != "verified" or mcp["task_support"] != "forbidden":
        raise ConformanceError("MCP transport state did not establish ASP authority")

    if not (current_completed_replay or retained_completed_replay):
        _validate_mcp_fresh_ordinary_admission(document, action_id)
        if (
            mcp["binding_input_schema_hash"]
            != document["execution"]["input_schema_hash"]
        ):
            raise ConformanceError(
                "fresh ASP-over-MCP binding schema differs from ordinary ASP admission"
            )

    result_pairs = (
        ("result_surface_version", "surface_version"),
        ("result_surface_hash", "surface_hash"),
        ("result_action_id", "action_id"),
        ("result_input_hash", "arguments_input_hash"),
        ("result_grant_id", "grant_id"),
        ("result_grant_hash", "grant_hash"),
        ("result_idempotency_key", "idempotency_key"),
    )
    if any(mcp[result] != mcp[request] for result, request in result_pairs):
        raise ConformanceError("ASP-over-MCP result tuple differs from its request")
    if (
        mcp["annotations_use"] != "omitted"
        or mcp["result_channel"] != "structured_content"
        or mcp["result_text_consistency"] != "deep_equal"
        or mcp["result_integrity"] != "valid"
        or mcp["result_output_schema"] != "valid"
        or mcp["result_is_error_consistency"] != "matched"
        or mcp["result_delivery_boundary"] != "runtime_only"
        or mcp["error_mapping"] != "layered"
        or mcp["binding_error_semantics"] != "closed_pre_effect_non_authoritative"
        or mcp["action_error_semantics"] != "closed_asp_error"
        or mcp["capacity_error_carrier"] != "tool_result"
        or mcp["transport_status_semantics"] != "mcp_http_success"
        or mcp["progress_use"] != "advisory"
        or mcp["progress_token_source"] != "runtime"
        or mcp["progress_token_echo"] != "matched"
        or mcp["progress_payload"] != "bounded_numeric_only"
        or mcp["progress_stream"] != "call_post_sse"
        or mcp["receipt_link_binding"] != "exact_one_to_one"
        or mcp["transport_error_exposure"] != "internal_safe_classification_only"
    ):
        raise ConformanceError("ASP-over-MCP transport semantics weaken ASP authority")
    if mcp["cancellation_phase"] == "after_dispatch_ambiguous":
        if (
            mcp["cancellation_use"] != "wait_only"
            or mcp["retry_behavior"] != "reconcile_same_key"
        ):
            raise ConformanceError(
                "post-dispatch MCP cancellation must reconcile with the same key"
            )
    elif (
        mcp["cancellation_phase"] != "pre_admission_proven"
        or mcp["cancellation_use"] != "honored_pre_admission"
        or mcp["retry_behavior"] != "not_applicable"
    ):
        raise ConformanceError("MCP cancellation state is not fail-closed")
    if mcp["idempotency_requirement"] == "required":
        if mcp["idempotency_key"] == "none":
            raise ConformanceError("MCP action lacks required idempotency identity")
    elif mcp["idempotency_requirement"] != "optional":
        raise ConformanceError("MCP action has an invalid idempotency requirement")
    if mcp["receipt_requirement"] == "required":
        if (
            mcp["receipt_channel"] != "authenticated_resource"
            or mcp["receipt_resource_authentication"] != "authenticated"
            or mcp["receipt_integrity"] != "verified"
            or mcp["receipt_persistence"] != "immutable_before_result"
            or mcp["receipt_rematerialization"] != "exact_after_fresh_session"
        ):
            raise ConformanceError("ASP-over-MCP receipt evidence is not authenticated")
    elif mcp["receipt_requirement"] != "not_required" or (
        mcp["receipt_channel"] != "not_applicable"
        or mcp["receipt_resource_authentication"] != "not_applicable"
        or mcp["receipt_integrity"] != "not_applicable"
        or mcp["receipt_persistence"] != "not_applicable"
        or mcp["receipt_rematerialization"] != "not_applicable"
    ):
        raise ConformanceError("MCP action receipt handling differs from policy")


MCP_SCHEMA_HASH_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/asp-over-mcp-schema/v1"
)
MCP_ACTION_INPUT_HASH_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/action-input/v1"
)
MCP_ACTION_EXECUTION_HASH_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/action-execution/v1"
)
MCP_ACTION_OUTPUT_HASH_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/action-output/v1"
)
MCP_ACTION_INPUT_SCHEMA_HASH_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/action-input-schema/v1"
)
MCP_ACTUAL_EFFECTS_HASH_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/actual-effects/v1"
)
MCP_PRECONDITIONS_HASH_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/action-preconditions/v1"
)
MCP_EXPECTED_EFFECTS_HASH_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/expected-effects/v1"
)
MCP_RECEIPT_HASH_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/receipt/v1"
)
MCP_EFFECT_MODES = {"reserve", "commit", "compensate", "revert"}
MCP_REQUEST_CORE_MEMBERS = {
    "session_id",
    "session_generation",
    "trace_id",
    "span_id",
    "grant_id",
    "grant_hash",
    "surface_hash",
    "action_id",
    "idempotency_key",
    "parent_receipt_hash",
    "approval_receipt_hashes",
    "input_hash",
    "execution",
    "execution_hash",
}
MCP_EXECUTION_CORE_MEMBERS = {
    "mode",
    "execution_id",
    "preview_id",
    "execution_token",
    "execution_token_hash",
    "preconditions_hash",
    "expected_effects_hash",
    "reservation_id",
    "target_receipt_hash",
}
MCP_RESPONSE_CORE_MEMBERS = {
    "session_id",
    "session_generation",
    "trace_id",
    "span_id",
    "grant_id",
    "grant_hash",
    "surface_hash",
    "action_id",
    "idempotency_key",
    "execution",
    "execution_hash",
    "approval_receipt_hashes",
    "result",
    "proposal_id",
    "proposal",
    "preview",
    "preconditions",
    "preconditions_hash",
    "expected_effects",
    "expected_effects_hash",
    "reservation_result",
    "target_receipt_hash",
    "revert_evidence",
    "effect_outcome",
    "actual_effects",
    "actual_effects_hash",
    "output",
    "approval_receipt_id",
    "approval_receipt_hash",
    "receipt_id",
    "receipt_hash",
    "error",
}


def _validate_mcp_w3c_id(value: Any, *, width: int, label: str) -> None:
    if (
        not isinstance(value, str)
        or re.fullmatch(f"[0-9a-f]{{{width}}}", value) is None
        or set(value) == {"0"}
    ):
        raise ConformanceError(f"{label} is not a valid W3C identifier")


def _validate_mcp_credential_free_uri(
    value: str,
    *,
    label: str,
    forbidden_credential_values: frozenset[str] = frozenset(),
) -> None:
    parsed = urlsplit(value)
    sensitive_query_names = {
        "access_token",
        "authorization",
        "bearer_token",
        "client_secret",
        "credential",
        "dpop",
        "execution_token",
        "grant_credential",
        "private_key",
        "refresh_token",
    }
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    query_names = {
        key.lower().replace("-", "_")
        for key, _ in query_pairs
    }
    def fully_unquote(member: str) -> str:
        decoded = member
        for _ in range(3):
            next_value = unquote(decoded)
            if next_value == decoded:
                break
            decoded = next_value
        return decoded

    decoded_path = fully_unquote(parsed.path)
    decoded_fragment = fully_unquote(parsed.fragment)
    decoded_query_values = [fully_unquote(value) for _, value in query_pairs]
    known_credential_present = any(
        credential in decoded_path for credential in forbidden_credential_values
    ) or any(
        credential in query_value
        for credential in forbidden_credential_values
        for query_value in decoded_query_values
    ) or any(
        credential in decoded_fragment for credential in forbidden_credential_values
    )
    if (
        parsed.username is not None
        or parsed.password is not None
        or query_names.intersection(sensitive_query_names)
        or known_credential_present
    ):
        raise ConformanceError(f"{label} carries credential material")


def _mcp_contains_forbidden_credential(
    value: Any,
    *,
    allow_execution_token: bool = False,
    allow_preview_execution_token: bool = False,
    forbidden_credential_values: frozenset[str] = frozenset(),
    path: tuple[str, ...] = (),
) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = key.lower().replace("-", "_")
            if lowered == "execution_token":
                if (
                    (allow_execution_token and path == ("execution",))
                    or (allow_preview_execution_token and path == ("preview",))
                ):
                    continue
                return True
            if _mcp_contains_forbidden_credential(
                item,
                allow_execution_token=allow_execution_token,
                allow_preview_execution_token=allow_preview_execution_token,
                forbidden_credential_values=forbidden_credential_values,
                path=(*path, key),
            ):
                return True
    elif isinstance(value, list):
        return any(
            _mcp_contains_forbidden_credential(
                item,
                allow_execution_token=allow_execution_token,
                allow_preview_execution_token=allow_preview_execution_token,
                forbidden_credential_values=forbidden_credential_values,
                path=path,
            )
            for item in value
        )
    elif isinstance(value, str) and any(
        credential in value for credential in forbidden_credential_values
    ):
        return True
    return False


def _resolve_mcp_local_schema_ref(
    root: Any,
    reference: str,
    *,
    retrieval_uri: str | None = None,
    base_uri: str | None = None,
) -> None:
    try:
        resource = Resource.from_contents(root)
        root_base_uri = (
            resource.id()
            or retrieval_uri
            or "urn:asp:conformance:mcp-binding-schema"
        )
        registry = Registry().with_resource(root_base_uri, resource).crawl()
        registry.resolver(base_uri=base_uri or root_base_uri).lookup(reference)
    except Exception as error:
        raise ConformanceError(
            "MCP Tool schema reference leaves its self-contained document"
        ) from error


def _validate_mcp_schema_closure(
    schema: Any, *, retrieval_uri: str | None = None
) -> None:
    if not isinstance(schema, dict):
        raise ConformanceError("MCP Tool schema must be a JSON object")

    allowed_vocabularies = {
        "https://json-schema.org/draft/2020-12/vocab/core",
        "https://json-schema.org/draft/2020-12/vocab/applicator",
        "https://json-schema.org/draft/2020-12/vocab/unevaluated",
        "https://json-schema.org/draft/2020-12/vocab/validation",
        "https://json-schema.org/draft/2020-12/vocab/meta-data",
        "https://json-schema.org/draft/2020-12/vocab/format-annotation",
        "https://json-schema.org/draft/2020-12/vocab/content",
    }

    singleton_schema_keywords = {
        "additionalItems", "additionalProperties", "contains", "contentSchema",
        "else", "if", "items", "not", "propertyNames", "then",
        "unevaluatedItems", "unevaluatedProperties",
    }
    array_schema_keywords = {"allOf", "anyOf", "oneOf", "prefixItems"}
    map_schema_keywords = {
        "$defs", "definitions", "dependentSchemas", "patternProperties", "properties"
    }

    try:
        root_resource = Resource.from_contents(schema)
        root_base_uri = (
            root_resource.id()
            or retrieval_uri
            or "urn:asp:conformance:mcp-binding-schema"
        )
    except Exception as error:
        raise ConformanceError("MCP Tool schema dialect is invalid") from error

    def walk_schema(value: Any, current_base_uri: str) -> None:
        if not isinstance(value, dict):
            return
        effective_base_uri = current_base_uri
        schema_id = value.get("$id")
        if isinstance(schema_id, str):
            effective_base_uri = urljoin(current_base_uri, schema_id)
        for key in ("$ref", "$dynamicRef", "$recursiveRef"):
            if key in value:
                reference = value[key]
                if not isinstance(reference, str):
                    raise ConformanceError("MCP Tool schema reference is not a string")
                _resolve_mcp_local_schema_ref(
                    schema,
                    reference,
                    retrieval_uri=retrieval_uri,
                    base_uri=effective_base_uri,
                )
        vocabulary = value.get("$vocabulary")
        if vocabulary is not None and (
            not isinstance(vocabulary, dict)
            or any(
                required is True and uri not in allowed_vocabularies
                for uri, required in vocabulary.items()
            )
        ):
            raise ConformanceError(
                "MCP Tool schema requires an unsupported vocabulary"
            )
        for key in singleton_schema_keywords:
            child = value.get(key)
            if isinstance(child, dict):
                walk_schema(child, effective_base_uri)
            elif key == "items" and isinstance(child, list):
                for item in child:
                    walk_schema(item, effective_base_uri)
        for key in array_schema_keywords:
            children = value.get(key)
            if isinstance(children, list):
                for child in children:
                    walk_schema(child, effective_base_uri)
        for key in map_schema_keywords:
            children = value.get(key)
            if isinstance(children, dict):
                for child in children.values():
                    walk_schema(child, effective_base_uri)
        dependencies = value.get("dependencies")
        if isinstance(dependencies, dict):
            for child in dependencies.values():
                if isinstance(child, dict):
                    walk_schema(child, effective_base_uri)

    walk_schema(schema, root_base_uri)

    validator_class = validator_for(schema, default=None)
    if validator_class is None:
        raise ConformanceError("MCP Tool schema selects an unsupported dialect")
    try:
        validator_class.check_schema(schema)
    except Exception as error:
        raise ConformanceError("MCP Tool schema is invalid for its dialect") from error


def _validate_mcp_schema_instance(
    value: Any,
    schema: dict[str, Any],
    label: str,
    *,
    retrieval_uri: str | None = None,
) -> None:
    """Validate one value with the dialect selected by a self-contained schema."""

    _validate_mcp_schema_closure(schema, retrieval_uri=retrieval_uri)
    validator_class = validator_for(schema, default=None)
    if validator_class is None:  # Kept explicit for type checkers and future registries.
        raise ConformanceError(f"{label} selects an unsupported schema dialect")
    try:
        resource = Resource.from_contents(schema)
        base_uri = (
            resource.id()
            or retrieval_uri
            or "urn:asp:conformance:mcp-binding-schema"
        )
        registry = Registry().with_resource(base_uri, resource).crawl()
        validator = validator_class(
            schema,
            registry=registry,
        )
        details = _format_schema_errors(validator, value)
    except Exception as error:
        raise ConformanceError(f"{label} schema could not be evaluated") from error
    if details:
        raise ConformanceError(f"{label} does not match its schema:\n{details}")


def _validate_mcp_execution_token_pair(
    token: Any, token_hash_value: Any, *, label: str
) -> None:
    if (
        not isinstance(token, str)
        or re.fullmatch(r"[A-Za-z0-9_-]+", token) is None
    ):
        raise ConformanceError(f"{label} execution_token is not unpadded base64url")
    try:
        decoded = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    except (binascii.Error, ValueError) as error:
        raise ConformanceError(f"{label} execution_token is not valid base64url") from error
    if len(decoded) < 16:
        raise ConformanceError(
            f"{label} execution_token contains fewer than 16 decoded octets"
        )
    canonical_token = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
    if canonical_token != token:
        raise ConformanceError(f"{label} execution_token is not canonical base64url")
    token_hash = "sha-256:" + base64.urlsafe_b64encode(
        hashlib.sha256(decoded).digest()
    ).rstrip(b"=").decode("ascii")
    if token_hash_value != token_hash:
        raise ConformanceError(f"{label} execution_token_hash does not match token")


def _validate_mcp_execution_context(
    execution: Any, *, label: str, sanitized: bool = False
) -> dict[str, Any]:
    if (
        not isinstance(execution, dict)
        or not {"mode", "execution_id"}.issubset(execution)
        or execution["mode"]
        not in {
            "read",
            "dry_run",
            "propose",
            "reserve",
            "commit",
            "compensate",
            "revert",
        }
        or not isinstance(execution["execution_id"], str)
        or not execution["execution_id"]
    ):
        raise ConformanceError(f"{label} execution context is invalid")
    unknown_members = set(execution) - MCP_EXECUTION_CORE_MEMBERS
    if any(not urlsplit(member).scheme for member in unknown_members):
        raise ConformanceError(
            f"{label} execution contains a non-core, non-URI extension member"
        )
    for identifier in ("preview_id", "reservation_id"):
        if identifier in execution and (
            not isinstance(execution[identifier], str) or not execution[identifier]
        ):
            raise ConformanceError(f"{label} execution {identifier} is empty")
    for digest_member in (
        "execution_token_hash",
        "preconditions_hash",
        "expected_effects_hash",
        "target_receipt_hash",
    ):
        if digest_member in execution:
            _validate_digest(execution[digest_member], f"{label}.execution.{digest_member}")

    if sanitized and "execution_token" in execution:
        raise ConformanceError(f"{label} leaks execution_token")

    preview_members = {
        "preview_id",
        "execution_token_hash",
        "preconditions_hash",
        "expected_effects_hash",
    }
    if not sanitized:
        preview_members.add("execution_token")
    if preview_members.intersection(execution) and not preview_members.issubset(execution):
        raise ConformanceError(
            f"{label} carries an incomplete preview-bound execution context"
        )
    if preview_members.issubset(execution) and execution["mode"] != "commit":
        raise ConformanceError(
            f"{label} carries preview-bound evidence outside commit mode"
        )

    if "execution_token" in execution:
        _validate_mcp_execution_token_pair(
            execution["execution_token"],
            execution.get("execution_token_hash"),
            label=label,
        )

    if "reservation_id" in execution and execution["mode"] not in {"reserve", "commit"}:
        raise ConformanceError(
            f"{label} reservation_id is not valid for the selected mode"
        )
    if execution["mode"] in {"compensate", "revert"}:
        if "target_receipt_hash" not in execution:
            raise ConformanceError(
                f"{label} recovery execution lacks target_receipt_hash"
            )
    elif "target_receipt_hash" in execution:
        raise ConformanceError(
            f"{label} target_receipt_hash is only valid for recovery modes"
        )
    return execution


def _validate_mcp_tuple_base(payload: Any, *, label: str) -> None:
    required = {
        "session_id",
        "session_generation",
        "trace_id",
        "span_id",
        "grant_id",
        "grant_hash",
        "surface_hash",
        "action_id",
    }
    if not isinstance(payload, dict) or not required.issubset(payload):
        raise ConformanceError(f"{label} lacks the complete ordinary ASP tuple")
    if (
        not isinstance(payload["session_id"], str)
        or not payload["session_id"]
        or not isinstance(payload["session_generation"], int)
        or isinstance(payload["session_generation"], bool)
        or not 1 <= payload["session_generation"] <= SAFE_INTEGER
        or not isinstance(payload["grant_id"], str)
        or not payload["grant_id"]
        or not isinstance(payload["action_id"], str)
        or not payload["action_id"]
    ):
        raise ConformanceError(f"{label} contains an invalid ordinary ASP tuple")
    _validate_mcp_w3c_id(payload["trace_id"], width=32, label=f"{label} trace_id")
    _validate_mcp_w3c_id(payload["span_id"], width=16, label=f"{label} span_id")
    _validate_digest(payload["grant_hash"], f"{label}.grant_hash")
    _validate_digest(payload["surface_hash"], f"{label}.surface_hash")


def validate_mcp_wire_semantics(
    message: Any,
    *,
    requested_resource_uri: str | None = None,
    resource_kind: str | None = None,
    expected_resource: Any = None,
    resource_hash_domain: str | None = None,
    expected_resource_hash: str | None = None,
    expected_receipt_type: str | None = None,
    expected_receipt_semantics: Any = None,
    expected_authorized_projection: Any = None,
    authorized_projection_expected: bool | None = None,
    expected_binding_record: Any = None,
    expected_tool_records: Any = None,
    expected_surface_hash: str | None = None,
    expected_request_payload: Any = None,
    expected_schema_dialect: str | None = None,
    expected_input_schema: Any = None,
    expected_input_schema_uri: str | None = None,
    expected_output_schema: Any = None,
    expected_output_schema_uri: str | None = None,
    expected_output_schema_hash: str | None = None,
    expected_actual_effects: Any = None,
    expected_preview: Any = None,
    expected_preview_preconditions: Any = None,
    expected_preview_effects: Any = None,
    expected_revert_evidence: Any = None,
    evaluation_time: str | None = None,
    expected_final_approval_receipt_hashes: Any = None,
    expected_authenticated_approval_receipts: Any = None,
    expected_authenticated_receipt_resources: Any = None,
    expected_receipt_resource_uris: Any = None,
    prior_tool_names: list[str] | None = None,
    prior_action_ids: list[str] | None = None,
    action_mode: str | None = None,
    expected_result: str | None = None,
    idempotency_required: bool | None = None,
    receipt_required: bool | None = None,
    expected_credential_audience: str | None = None,
    expected_endpoint: str | None = None,
    expected_proof_target_uri: str | None = None,
    expected_manifest_resource_uri: str | None = None,
    expected_authorization_composition: str | None = None,
    expected_request_id: str | int | None = None,
    expected_progress_token: str | int | None = None,
    expected_cancelled_request_id: str | int | None = None,
    expected_cursor: str | None = None,
    prior_request_ids: list[str | int] | None = None,
    prior_cursors: list[str] | None = None,
    tools_list_first_page: bool | None = None,
    forbidden_credential_values: list[str] | None = None,
    capacity_declared_limit_ids: list[str] | None = None,
    capacity_disclosable_limit_ids: list[str] | None = None,
) -> None:
    """Validate ASP-over-MCP relationships that JSON Schema cannot express."""

    if not isinstance(message, dict):
        raise ConformanceError("ASP-over-MCP wire message must be an object")
    forbidden_credentials = frozenset(forbidden_credential_values or ())
    if (
        isinstance(message.get("error"), dict)
        and _mcp_contains_forbidden_credential(
            message["error"].get("message"),
            forbidden_credential_values=forbidden_credentials,
        )
    ):
        raise ConformanceError("MCP JSON-RPC error exposes credential material")
    if expected_request_id is not None and message.get("id") != expected_request_id:
        raise ConformanceError("MCP JSON-RPC id differs from its correlated request")
    method = message.get("method")
    if (
        method is not None
        and "id" in message
        and message["id"] in (prior_request_ids or ())
    ):
        raise ConformanceError("MCP JSON-RPC request id was already used in this session")
    if method == "initialize":
        client_binding = message["params"]["capabilities"]["experimental"][
            ASP_OVER_MCP_EXTENSION_ID
        ]
        if (
            expected_authorization_composition is not None
            and client_binding["authorization_composition"]
            != expected_authorization_composition
        ):
            raise ConformanceError(
                "MCP initialize offer differs from manifest authorization composition"
            )
    if method in {"resources/read", "resources/subscribe"}:
        selected_uri = requested_resource_uri or expected_manifest_resource_uri
        request_uri = message["params"]["uri"]
        _validate_mcp_credential_free_uri(
            request_uri,
            label=f"MCP {method} URI",
            forbidden_credential_values=forbidden_credentials,
        )
        if selected_uri is not None and request_uri != selected_uri:
            raise ConformanceError(f"MCP {method} URI differs from the selected resource")
    if method == "notifications/resources/updated":
        updated_uri = message["params"]["uri"]
        _validate_mcp_credential_free_uri(
            updated_uri,
            label="MCP resources/updated URI",
            forbidden_credential_values=forbidden_credentials,
        )
        if (
            expected_manifest_resource_uri is not None
            and updated_uri != expected_manifest_resource_uri
        ):
            raise ConformanceError(
                "MCP resources/updated URI differs from the subscribed manifest"
            )
    if method == "tools/list":
        request_cursor = message.get("params", {}).get("cursor")
        if tools_list_first_page is True and "params" in message:
            raise ConformanceError("first MCP tools/list request must omit params")
        if expected_cursor is not None and request_cursor != expected_cursor:
            raise ConformanceError("MCP tools/list cursor differs from page lineage")
        if request_cursor is not None and request_cursor in (prior_cursors or ()):
            raise ConformanceError("MCP tools/list cursor was already consumed")
    if method == "notifications/cancelled" and (
        expected_cancelled_request_id is not None
        and message["params"]["requestId"] != expected_cancelled_request_id
    ):
        raise ConformanceError("MCP cancellation requestId differs from the outstanding call")
    result = message.get("result")
    if (
        isinstance(result, dict)
        and "serverInfo" in result
        and "capabilities" in result
    ):
        server_binding = result["capabilities"]["experimental"][
            ASP_OVER_MCP_EXTENSION_ID
        ]
        _validate_mcp_credential_free_uri(
            server_binding["manifest_resource_uri"],
            label="MCP initialize manifest resource URI",
            forbidden_credential_values=forbidden_credentials,
        )
        if (
            expected_manifest_resource_uri is not None
            and server_binding["manifest_resource_uri"]
            != expected_manifest_resource_uri
        ):
            raise ConformanceError(
                "MCP initialize result substitutes the selected manifest URI"
            )
        if (
            expected_authorization_composition is not None
            and server_binding["authorization_composition"]
            != expected_authorization_composition
        ):
            raise ConformanceError(
                "MCP initialize result substitutes authorization composition"
            )
    if isinstance(result, dict) and "contents" in result:
        for item in result["contents"]:
            _validate_mcp_credential_free_uri(
                item["uri"],
                label="MCP resource content URI",
                forbidden_credential_values=forbidden_credentials,
            )
        if requested_resource_uri is not None and any(
            item.get("uri") != requested_resource_uri
            for item in result["contents"]
        ):
            raise ConformanceError(
                "MCP resource result URI differs from its exact read request"
            )
        resource = loads_human_json(
            result["contents"][0]["text"],
            source="ASP-over-MCP TextResourceContents",
        )
        if not isinstance(resource, dict):
            raise ConformanceError("MCP resource text must encode one JSON object")
        if expected_resource is not None and (
            _canonical_json_rfc8785(resource)
            != _canonical_json_rfc8785(expected_resource)
        ):
            raise ConformanceError("MCP resource differs from the expected retained object")
        if resource_kind is not None and resource_kind not in {"manifest", "receipt"}:
            raise ConformanceError("unknown ASP-over-MCP resource kind")
        hashing_resource = resource
        if resource_kind == "manifest":
            if (
                not isinstance(resource.get("surface_hash"), str)
                or resource["surface_hash"] != expected_resource_hash
            ):
                raise ConformanceError(
                    "MCP manifest resource surface_hash differs from its identity"
                )
            hashing_resource = copy.deepcopy(resource)
            hashing_resource.pop("surface_hash", None)
        if resource_kind == "receipt":
            receipt_type = resource.get("receipt_type")
            ordinary_required = {
                "receipt_id", "receipt_type", "receipt_hash", "grant_id",
                "grant_hash", "session_id", "session_generation", "trace_id",
                "span_id", "action_id", "app_id", "surface_version",
                "surface_hash", "runtime", "actor_agent", "subject",
                "input_hash", "policy_decision_hash", "policy_decision",
                "timestamp", "result",
            }
            app_required = ordinary_required
            runtime_required = ordinary_required
            approval_required = ordinary_required | {
                "idempotency_key", "execution", "execution_hash", "approval"
            }
            required_by_type = {
                "app": app_required,
                "runtime": runtime_required,
                "approval": approval_required,
            }
            if (
                not {"receipt_id", "receipt_hash", "receipt_type"}.issubset(resource)
                or receipt_type not in required_by_type
                or not required_by_type.get(receipt_type, set()).issubset(resource)
                or (
                    expected_receipt_type is not None
                    and receipt_type != expected_receipt_type
                )
                or (
                    receipt_type == "approval"
                    and (
                        not isinstance(resource.get("approval"), dict)
                        or resource["approval"].get("role")
                        not in {"runtime", "application"}
                    )
                )
                or resource.get("receipt_hash") != expected_resource_hash
            ):
                raise ConformanceError(
                    "MCP receipt resource lacks its exact receipt type and identity"
                )
            _validate_mcp_tuple_base(resource, label="MCP receipt resource")
            _validate_digest(resource["input_hash"], "receipt.input_hash")
            _validate_digest(
                resource["policy_decision_hash"], "receipt.policy_decision_hash"
            )
            if ("execution" in resource) != ("execution_hash" in resource):
                raise ConformanceError(
                    "MCP receipt resource must pair execution with execution_hash"
                )
            if "execution" in resource:
                _validate_digest(resource["execution_hash"], "receipt.execution_hash")
                receipt_execution = _validate_mcp_execution_context(
                    resource["execution"],
                    label="receipt.execution",
                    sanitized=True,
                )
                if resource["execution_hash"] != _canonical_object_hash(
                    MCP_ACTION_EXECUTION_HASH_DOMAIN, receipt_execution
                ):
                    raise ConformanceError(
                        "MCP receipt execution_hash differs from sanitized execution"
                    )
            effect_members = {
                "effect_outcome", "actual_effects", "actual_effects_hash"
            }
            if effect_members.intersection(resource) and not effect_members.issubset(resource):
                raise ConformanceError(
                    "MCP receipt resource carries incomplete effect evidence"
                )
            if effect_members.issubset(resource):
                _validate_digest(
                    resource["actual_effects_hash"], "receipt.actual_effects_hash"
                )
                if resource["actual_effects_hash"] != _canonical_object_hash(
                    MCP_ACTUAL_EFFECTS_HASH_DOMAIN, resource["actual_effects"]
                ):
                    raise ConformanceError(
                        "MCP receipt actual_effects_hash differs from actual_effects"
                    )
            for digest_member in ("parent_receipt_hash", "output_hash"):
                if digest_member in resource:
                    _validate_digest(resource[digest_member], f"receipt.{digest_member}")
            semantic_members = {
                "result",
                "error",
                "output_hash",
                "actual_effects",
                "actual_effects_hash",
                "effect_outcome",
                "resource",
            }
            if (
                not isinstance(expected_receipt_semantics, dict)
                or set(expected_receipt_semantics) != semantic_members
            ):
                raise ConformanceError(
                    "MCP receipt read lacks exact authoritative result and effect semantics"
                )
            for member_name in semantic_members:
                expected_value = expected_receipt_semantics[member_name]
                if expected_value is None:
                    if member_name in resource:
                        raise ConformanceError(
                            f"MCP receipt {member_name} is absent from authoritative semantics"
                        )
                elif (
                    member_name not in resource
                    or _canonical_json_rfc8785(resource[member_name])
                    != _canonical_json_rfc8785(expected_value)
                ):
                    raise ConformanceError(
                        f"MCP receipt {member_name} differs from authoritative semantics"
                    )
            hashing_resource = copy.deepcopy(resource)
            hashing_resource.pop("receipt_hash", None)
            hashing_resource.pop("receipt_signatures", None)
        if (
            expected_resource_hash is not None
            and resource_hash_domain is not None
            and _canonical_object_hash(resource_hash_domain, hashing_resource)
            != expected_resource_hash
        ):
            raise ConformanceError("MCP resource hash differs from the expected object")
        if resource_kind == "receipt":
            record = (
                expected_authenticated_receipt_resources[0]
                if isinstance(expected_authenticated_receipt_resources, list)
                and len(expected_authenticated_receipt_resources) == 1
                else None
            )
            if (
                not isinstance(record, dict)
                or set(record) != {"uri", "receipt", "expected"}
                or record.get("uri") != requested_resource_uri
                or record.get("receipt") != resource
                or not isinstance(record.get("expected"), dict)
            ):
                raise ConformanceError(
                    "MCP receipt read lacks its exact authenticated resource record"
                )
            _validate_receipt_resource_batch(
                _canonical_json_rfc8785(
                    {
                        "profile": RECEIPT_RESOURCE_REQUEST_PROFILE,
                        "resources": expected_authenticated_receipt_resources,
                    }
                )
            )

    if isinstance(result, dict) and "tools" in result:
        next_cursor = result.get("nextCursor")
        if next_cursor is not None and next_cursor in (prior_cursors or ()):
            raise ConformanceError("MCP tools/list response repeats a cursor lineage")
        if next_cursor is not None and not result["tools"]:
            raise ConformanceError("MCP tools/list empty page cannot continue pagination")
        page_binding = result["_meta"][ASP_OVER_MCP_EXTENSION_ID]
        _validate_mcp_credential_free_uri(
            page_binding["manifest_resource_uri"],
            label="MCP manifest resource URI",
            forbidden_credential_values=forbidden_credentials,
        )
        if expected_binding_record is not None:
            if (
                not isinstance(expected_binding_record, dict)
                or _canonical_json_rfc8785(page_binding)
                != _canonical_json_rfc8785(expected_binding_record)
            ):
                raise ConformanceError(
                    "MCP Tool page differs from the manifest-selected binding record"
                )
        projection_present = "authorized_projection" in page_binding
        if (
            authorized_projection_expected is not None
            and projection_present != authorized_projection_expected
        ):
            raise ConformanceError(
                "MCP Tool page authorized projection presence differs from selection"
            )
        if (
            expected_authorized_projection is not None
            and page_binding.get("authorized_projection")
            != expected_authorized_projection
        ):
            raise ConformanceError(
                "MCP Tool page authorized projection differs from the selected view"
            )
        shared_fields = {
            "profile",
            "mcp_protocol_version",
            "binding_view_id",
            "manifest_resource_uri",
            "surface_version",
            "surface_hash",
            "authorization_composition",
            "authorized_projection",
        }
        tool_names = set(prior_tool_names or ())
        action_ids = set(prior_action_ids or ())
        if expected_tool_records is not None and (
            not isinstance(expected_tool_records, list)
            or len(expected_tool_records) != len(result["tools"])
        ):
            raise ConformanceError("MCP Tool page differs from the manifest action set")
        for index, tool in enumerate(result["tools"]):
            tool_binding = tool["_meta"][ASP_OVER_MCP_EXTENSION_ID]
            for uri_member in ("manifest_resource_uri", "input_schema", "output_schema"):
                _validate_mcp_credential_free_uri(
                    tool_binding[uri_member],
                    label=f"MCP Tool {uri_member}",
                    forbidden_credential_values=forbidden_credentials,
                )
            if expected_tool_records is not None:
                expected_tool = expected_tool_records[index]
                if not isinstance(expected_tool, dict):
                    raise ConformanceError("expected MCP Tool record is invalid")
                expected_input = expected_tool.get("inputSchema")
                expected_binding = expected_tool.get("binding")
                expected_name = expected_tool.get("name")
                allowed_expected_members = {
                    "name", "inputSchema", "binding", "outputSchema",
                    "outputSchemaHash", "schemaDialect",
                }
                if (
                    not {"name", "inputSchema", "binding"}.issubset(expected_tool)
                    or set(expected_tool) - allowed_expected_members
                    or expected_name != tool["name"]
                    or _canonical_json_rfc8785(expected_input)
                    != _canonical_json_rfc8785(tool["inputSchema"])
                    or not isinstance(expected_binding, dict)
                    or _canonical_json_rfc8785(tool_binding)
                    != _canonical_json_rfc8785(expected_binding)
                ):
                    raise ConformanceError(
                        "MCP Tool differs from its manifest action declaration"
                    )
            if tool["name"] in tool_names:
                raise ConformanceError("MCP binding view repeats a Tool name")
            if tool_binding["action_id"] in action_ids:
                raise ConformanceError("MCP binding view repeats a mapped ASP action")
            tool_names.add(tool["name"])
            action_ids.add(tool_binding["action_id"])
            if any(
                tool_binding.get(field) != page_binding.get(field)
                for field in shared_fields
            ):
                raise ConformanceError(
                    "MCP page and Tool carry different binding-view records"
                )
            derived_name = "asp.action." + hashlib.sha256(
                tool_binding["action_id"].encode("utf-8")
            ).hexdigest()
            if tool["name"] != derived_name:
                raise ConformanceError(
                    "MCP Tool name is not the deterministic ASP action mapping"
                )
            tool_schema_dialect = (
                expected_tool.get("schemaDialect")
                if expected_tool_records is not None
                else expected_schema_dialect
            )
            if (
                tool_schema_dialect is not None
                and tool["inputSchema"].get("$schema") != tool_schema_dialect
            ):
                raise ConformanceError(
                    "MCP Tool input schema dialect differs from the manifest"
                )
            _validate_mcp_schema_closure(
                tool["inputSchema"], retrieval_uri=tool_binding["input_schema"]
            )
            if _canonical_object_hash(
                MCP_SCHEMA_HASH_DOMAIN, tool["inputSchema"]
            ) != tool_binding["binding_input_schema_hash"]:
                raise ConformanceError(
                    "MCP Tool input schema differs from its binding-local hash"
                )
            if (
                "input_schema_hash" in tool_binding
                and _canonical_object_hash(
                    MCP_ACTION_INPUT_SCHEMA_HASH_DOMAIN, tool["inputSchema"]
                )
                != tool_binding["input_schema_hash"]
            ):
                raise ConformanceError(
                    "MCP Tool input schema differs from its manifest input_schema_hash"
                )
            tool_output_schema = (
                expected_tool.get("outputSchema")
                if expected_tool_records is not None
                and "outputSchema" in expected_tool
                else expected_output_schema
            )
            tool_output_schema_hash = (
                expected_tool.get("outputSchemaHash")
                if expected_tool_records is not None
                and "outputSchemaHash" in expected_tool
                else expected_output_schema_hash
            )
            if tool_output_schema is not None:
                _validate_mcp_schema_closure(
                    tool_output_schema,
                    retrieval_uri=tool_binding["output_schema"],
                )
                if (
                    tool_schema_dialect is not None
                    and tool_output_schema.get("$schema") != tool_schema_dialect
                ):
                    raise ConformanceError(
                        "MCP output schema dialect differs from the manifest"
                    )
                computed_output_hash = _canonical_object_hash(
                    MCP_SCHEMA_HASH_DOMAIN, tool_output_schema
                )
                if (
                    computed_output_hash != tool_binding["binding_output_schema_hash"]
                    or (
                        tool_output_schema_hash is not None
                        and computed_output_hash != tool_output_schema_hash
                    )
                ):
                    raise ConformanceError(
                        "MCP output schema differs from its binding-local hash"
                    )

    if message.get("method") == "tools/call":
        params = message["params"]
        call_binding = params["_meta"][ASP_OVER_MCP_EXTENSION_ID]
        call_projection_present = "authorized_projection" in call_binding
        if (
            authorized_projection_expected is not None
            and call_projection_present != authorized_projection_expected
        ):
            raise ConformanceError(
                "MCP call authorized projection presence differs from selection"
            )
        action_payload = call_binding["action_request"]["payload"]
        _validate_mcp_tuple_base(action_payload, label="action.request")
        if expected_binding_record is not None and (
            not isinstance(expected_binding_record, dict)
            or _canonical_json_rfc8785(call_binding)
            != _canonical_json_rfc8785(expected_binding_record)
        ):
            raise ConformanceError(
                "MCP call differs from the selected binding-view record"
            )
        if expected_request_payload is not None and (
            not isinstance(expected_request_payload, dict)
            or _canonical_json_rfc8785(action_payload)
            != _canonical_json_rfc8785(expected_request_payload)
        ):
            raise ConformanceError(
                "MCP call ordinary request differs from runtime-owned request fields"
            )
        if action_payload["surface_hash"] != call_binding["surface_hash"]:
            raise ConformanceError(
                "MCP call binding surface differs from its ordinary ASP request"
            )
        if (
            expected_surface_hash is not None
            and action_payload["surface_hash"] != expected_surface_hash
        ):
            raise ConformanceError(
                "MCP action request surface differs from the selected binding view"
            )
        if "input" in action_payload:
            raise ConformanceError(
                "MCP call action.request payload must omit input before argument insertion"
            )
        unknown_request_members = set(action_payload) - MCP_REQUEST_CORE_MEMBERS
        if any(not urlsplit(member).scheme for member in unknown_request_members):
            raise ConformanceError(
                "MCP action.request contains a non-core, non-URI extension member"
            )
        if _mcp_contains_forbidden_credential(
            action_payload,
            allow_execution_token=True,
            forbidden_credential_values=forbidden_credentials,
        ) or _mcp_contains_forbidden_credential(
            params["arguments"], forbidden_credential_values=forbidden_credentials
        ):
            raise ConformanceError("MCP action.request carries credential material")
        execution = _validate_mcp_execution_context(
            action_payload.get("execution"), label="action.request"
        )
        if action_mode is not None and execution["mode"] != action_mode:
            raise ConformanceError("MCP action.request mode differs from its mapped Tool")
        requires_idempotency = idempotency_required is True
        if requires_idempotency and (
            not isinstance(action_payload.get("idempotency_key"), str)
            or not action_payload["idempotency_key"]
        ):
            raise ConformanceError("MCP action.request lacks required idempotency key")
        if "idempotency_key" in action_payload and (
            not isinstance(action_payload["idempotency_key"], str)
            or not action_payload["idempotency_key"]
        ):
            raise ConformanceError("MCP action.request has an empty idempotency key")
        requires_input_hash = (
            requires_idempotency
            or receipt_required is True
            or execution["mode"] in MCP_EFFECT_MODES
            or execution["mode"] == "dry_run"
        )
        if requires_input_hash:
            if "input_hash" not in action_payload:
                raise ConformanceError("MCP action.request lacks required input hash")
        if "input_hash" in action_payload:
            _validate_digest(action_payload["input_hash"], "action.request.input_hash")
            computed_input_hash = _canonical_object_hash(
                MCP_ACTION_INPUT_HASH_DOMAIN, params["arguments"]
            )
            if action_payload["input_hash"] != computed_input_hash:
                raise ConformanceError(
                    "MCP action.request input_hash differs from exact arguments"
                )
        if expected_input_schema is not None:
            if (
                expected_schema_dialect is not None
                and expected_input_schema.get("$schema") != expected_schema_dialect
            ):
                raise ConformanceError(
                    "MCP call input schema dialect differs from the manifest"
                )
            _validate_mcp_schema_instance(
                params["arguments"],
                expected_input_schema,
                "MCP call arguments",
                retrieval_uri=expected_input_schema_uri,
            )
        for member in ("parent_receipt_hash", "execution_hash"):
            if member in action_payload:
                _validate_digest(action_payload[member], f"action.request.{member}")
        if execution["mode"] in MCP_EFFECT_MODES and "execution_hash" not in action_payload:
            raise ConformanceError("effect-capable MCP request lacks execution hash")
        if "execution_hash" in action_payload:
            sanitized_execution = copy.deepcopy(execution)
            sanitized_execution.pop("execution_token", None)
            if action_payload["execution_hash"] != _canonical_object_hash(
                MCP_ACTION_EXECUTION_HASH_DOMAIN, sanitized_execution
            ):
                raise ConformanceError(
                    "MCP action.request execution_hash differs from sanitized execution"
                )
        approval_hashes = action_payload.get("approval_receipt_hashes")
        if approval_hashes is not None:
            if not isinstance(approval_hashes, dict) or set(approval_hashes) != {"runtime"}:
                raise ConformanceError("MCP request approval receipt map is not closed")
            _validate_digest(approval_hashes["runtime"], "action.request.approval_receipt_hashes.runtime")
        action_id = action_payload.get("action_id")
        if not isinstance(action_id, str):
            raise ConformanceError("MCP call lacks its ASP action identifier")
        derived_name = "asp.action." + hashlib.sha256(
            action_id.encode("utf-8")
        ).hexdigest()
        if params["name"] != derived_name:
            raise ConformanceError(
                "MCP call Tool name differs from its ASP action request"
            )
        if (
            expected_authorized_projection is not None
            and call_binding.get("authorized_projection")
            != expected_authorized_projection
        ):
            raise ConformanceError(
                "MCP call authorized projection differs from its selected view"
            )

    if message.get("method") == "notifications/progress":
        params = message["params"]
        if (
            expected_progress_token is not None
            and params["progressToken"] != expected_progress_token
        ):
            raise ConformanceError("MCP progress token differs from its tools/call token")
        if "total" in params and params["total"] < params["progress"]:
            raise ConformanceError("MCP progress total is smaller than progress")

    if isinstance(result, dict) and "structuredContent" in result:
        structured = result["structuredContent"]
        if expected_binding_record is not None:
            expected_envelope = {
                field: structured[field]
                for field in ("profile", "mcp_protocol_version", "binding_view_id")
            }
            if (
                not isinstance(expected_binding_record, dict)
                or expected_envelope != expected_binding_record
            ):
                raise ConformanceError(
                    "MCP structured result differs from the selected binding view"
                )
        parsed_text = loads_human_json(
            result["content"][0]["text"],
            source="ASP-over-MCP TextContent",
        )
        _validate_human_json_value(structured)
        if _canonical_json_rfc8785(parsed_text) != _canonical_json_rfc8785(structured):
            raise ConformanceError(
                "MCP TextContent is not deeply equal to structuredContent"
            )
        linked_uris = [item["uri"] for item in result["content"][1:]]
        for linked_uri in linked_uris:
            _validate_mcp_credential_free_uri(
                linked_uri,
                label="MCP receipt ResourceLink URI",
                forbidden_credential_values=forbidden_credentials,
            )
        declared_uris = structured.get("receipt_resource_uris", [])
        if linked_uris != declared_uris:
            raise ConformanceError(
                "MCP receipt ResourceLinks are not the exact one-to-one URI list"
            )
        inner = structured["message"]
        if inner["type"] == "binding.error" and _mcp_contains_forbidden_credential(
            inner["payload"], forbidden_credential_values=forbidden_credentials
        ):
            raise ConformanceError("MCP binding.error exposes credential material")
        if inner["type"] in {"action.result", "action.error"}:
            payload = inner["payload"]
            response_error_code = (
                payload["error"]["code"]
                if inner["type"] == "action.error"
                else None
            )
            pre_admission_capacity_error = response_error_code in {
                "rate_limited", "capacity_state_unavailable", "service_unavailable"
            }
            _validate_mcp_tuple_base(payload, label=inner["type"])
            if (
                expected_surface_hash is not None
                and payload["surface_hash"] != expected_surface_hash
            ):
                raise ConformanceError(
                    "MCP action response surface differs from the selected binding view"
                )
            unknown_response_members = set(payload) - MCP_RESPONSE_CORE_MEMBERS
            if any(not urlsplit(member).scheme for member in unknown_response_members):
                raise ConformanceError(
                    f"{inner['type']} contains a non-core, non-URI extension member"
                )
            allow_preview_token = (
                inner["type"] == "action.result" and action_mode == "dry_run"
            )
            if _mcp_contains_forbidden_credential(
                payload,
                allow_preview_execution_token=allow_preview_token,
                forbidden_credential_values=forbidden_credentials,
            ):
                raise ConformanceError("MCP action response carries credential material")
            if expected_request_payload is not None:
                if not isinstance(expected_request_payload, dict):
                    raise ConformanceError("expected MCP request payload is not an object")
                repeat_members = {
                    "session_id",
                    "session_generation",
                    "trace_id",
                    "grant_id",
                    "grant_hash",
                    "surface_hash",
                    "action_id",
                    "idempotency_key",
                    "execution_hash",
                }
                for member in repeat_members.intersection(expected_request_payload):
                    if payload.get(member) != expected_request_payload[member]:
                        raise ConformanceError(
                            f"{inner['type']} does not repeat request {member} exactly"
                        )
                if (
                    "span_id" in expected_request_payload
                    and payload["span_id"] == expected_request_payload["span_id"]
                ):
                    raise ConformanceError(
                        f"{inner['type']} reuses the request producer span_id"
                    )
                expected_execution = expected_request_payload.get("execution")
                if expected_execution is not None:
                    expected_sanitized = copy.deepcopy(expected_execution)
                    expected_sanitized.pop("execution_token", None)
                    if payload.get("execution") != expected_sanitized:
                        raise ConformanceError(
                            f"{inner['type']} does not repeat sanitized execution exactly"
                        )
            execution = payload.get("execution")
            if ("execution" in payload) != ("execution_hash" in payload):
                raise ConformanceError(
                    "MCP action response must pair execution with execution_hash"
                )
            if "execution_hash" in payload:
                _validate_digest(payload["execution_hash"], f"{inner['type']}.execution_hash")
                execution = _validate_mcp_execution_context(
                    execution, label=inner["type"], sanitized=True
                )
                if payload["execution_hash"] != _canonical_object_hash(
                    MCP_ACTION_EXECUTION_HASH_DOMAIN, execution
                ):
                    raise ConformanceError(
                        f"{inner['type']} execution_hash differs from sanitized execution"
                    )
                if action_mode is not None and execution["mode"] != action_mode:
                    raise ConformanceError(
                        f"{inner['type']} mode differs from its mapped Tool"
                    )
            if (
                action_mode in MCP_EFFECT_MODES
                and "execution" not in payload
                and not pre_admission_capacity_error
            ):
                raise ConformanceError(
                    "effect-capable MCP response lacks execution context and hash"
                )
            if idempotency_required is True and (
                not isinstance(payload.get("idempotency_key"), str)
                or not payload["idempotency_key"]
            ):
                raise ConformanceError("MCP action response lacks idempotency identity")
            if "idempotency_key" in payload and (
                not isinstance(payload["idempotency_key"], str)
                or not payload["idempotency_key"]
            ):
                raise ConformanceError("MCP action response has an empty idempotency key")
            if inner["type"] == "action.result" and not {"result", "output"}.issubset(payload):
                raise ConformanceError("action.result lacks result or output")
            if inner["type"] == "action.result":
                if any(
                    member in payload
                    for member in ("error", "approval_receipt_id", "approval_receipt_hash")
                ):
                    raise ConformanceError(
                        "action.result carries an action.error-only member"
                    )
                if not isinstance(payload["result"], str) or not payload["result"]:
                    raise ConformanceError("action.result has an empty or unregistered result")
                if expected_result is not None and payload["result"] != expected_result:
                    raise ConformanceError(
                        "action.result value differs from the selected mode result"
                    )
                if expected_output_schema is not None:
                    if (
                        expected_schema_dialect is not None
                        and expected_output_schema.get("$schema")
                        != expected_schema_dialect
                    ):
                        raise ConformanceError(
                            "MCP result output schema dialect differs from the manifest"
                        )
                    _validate_mcp_schema_instance(
                        payload["output"],
                        expected_output_schema,
                        "MCP action.result output",
                        retrieval_uri=expected_output_schema_uri,
                    )
                if action_mode == "dry_run":
                    if payload["result"] != "preview":
                        raise ConformanceError(
                            "dry_run action.result must report result=preview"
                        )
                    preview = payload.get("preview")
                    required_preview_members = {
                        "preview_id", "commit_action_id", "execution_token",
                        "execution_token_hash", "expires_at",
                    }
                    if (
                        not isinstance(preview, dict)
                        or set(preview) != required_preview_members
                        or not isinstance(preview["preview_id"], str)
                        or not preview["preview_id"]
                        or not isinstance(preview["commit_action_id"], str)
                        or not preview["commit_action_id"]
                    ):
                        raise ConformanceError(
                            "dry_run action.result lacks its closed preview token bundle"
                        )
                    _validate_mcp_execution_token_pair(
                        preview["execution_token"],
                        preview["execution_token_hash"],
                        label="action.result.preview",
                    )
                    if (
                        not isinstance(preview["expires_at"], str)
                        or re.fullmatch(
                            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z",
                            preview["expires_at"],
                        )
                        is None
                    ):
                        raise ConformanceError(
                            "dry_run preview expires_at is not exact UTC RFC 3339"
                        )
                    try:
                        expires_at = datetime.fromisoformat(
                            preview["expires_at"].replace("Z", "+00:00")
                        )
                    except (AttributeError, ValueError) as error:
                        raise ConformanceError(
                            "dry_run preview expires_at is not an RFC 3339 timestamp"
                        ) from error
                    if evaluation_time is None:
                        raise ConformanceError(
                            "dry_run preview lacks authoritative evaluation_time context"
                        )
                    try:
                        evaluated_at = datetime.fromisoformat(
                            evaluation_time.replace("Z", "+00:00")
                        )
                    except (AttributeError, ValueError) as error:
                        raise ConformanceError(
                            "dry_run evaluation_time is not RFC 3339"
                        ) from error
                    if evaluated_at.tzinfo is None or expires_at <= evaluated_at:
                        raise ConformanceError("dry_run preview token is expired")
                    if not {
                        "preconditions", "preconditions_hash",
                        "expected_effects", "expected_effects_hash",
                    }.issubset(payload):
                        raise ConformanceError(
                            "dry_run action.result lacks complete preview evidence"
                        )
                    _validate_digest(
                        payload["preconditions_hash"],
                        "action.result.preconditions_hash",
                    )
                    _validate_digest(
                        payload["expected_effects_hash"],
                        "action.result.expected_effects_hash",
                    )
                    if payload["preconditions_hash"] != _canonical_object_hash(
                        MCP_PRECONDITIONS_HASH_DOMAIN, payload["preconditions"]
                    ):
                        raise ConformanceError(
                            "dry_run preconditions_hash differs from preconditions"
                        )
                    if payload["expected_effects_hash"] != _canonical_object_hash(
                        MCP_EXPECTED_EFFECTS_HASH_DOMAIN, payload["expected_effects"]
                    ):
                        raise ConformanceError(
                            "dry_run expected_effects_hash differs from expected_effects"
                        )
                    if expected_preview_preconditions is None or (
                        _canonical_json_rfc8785(payload["preconditions"])
                        != _canonical_json_rfc8785(expected_preview_preconditions)
                    ):
                        raise ConformanceError(
                            "dry_run preconditions differ from the authoritative schema-valid record"
                        )
                    if expected_preview_effects is None or (
                        _canonical_json_rfc8785(payload["expected_effects"])
                        != _canonical_json_rfc8785(expected_preview_effects)
                    ):
                        raise ConformanceError(
                            "dry_run expected effects differ from the authoritative schema-valid record"
                        )
                    if expected_preview is not None and (
                        _canonical_json_rfc8785(preview)
                        != _canonical_json_rfc8785(expected_preview)
                    ):
                        raise ConformanceError(
                            "dry_run preview differs from the authoritative preview record"
                        )
                elif "preview" in payload:
                    raise ConformanceError(
                        "non-dry_run action.result carries a preview token bundle"
                    )
                if action_mode != "dry_run" and {
                    "preconditions", "preconditions_hash",
                    "expected_effects", "expected_effects_hash",
                }.intersection(payload):
                    raise ConformanceError(
                        "non-dry_run action.result carries dry_run preview evidence"
                    )
                proposal_members = {"proposal_id", "proposal"}
                present_proposal_members = proposal_members.intersection(payload)
                if action_mode == "propose":
                    if present_proposal_members != proposal_members:
                        raise ConformanceError(
                            "propose action.result lacks its complete proposal artifact"
                        )
                elif present_proposal_members:
                    raise ConformanceError(
                        "non-propose action.result carries proposal members"
                    )
                if action_mode == "reserve":
                    if "reservation_result" not in payload:
                        raise ConformanceError(
                            "reserve action.result lacks reservation_result"
                        )
                elif "reservation_result" in payload:
                    raise ConformanceError(
                        "non-reserve action.result carries reservation_result"
                    )
                if "revert_evidence" in payload:
                    if expected_revert_evidence is None or (
                        _canonical_json_rfc8785(payload["revert_evidence"])
                        != _canonical_json_rfc8785(expected_revert_evidence)
                    ):
                        raise ConformanceError(
                            "action.result carries unexpected revert_evidence"
                        )
            effect_members = {
                "effect_outcome",
                "actual_effects",
                "actual_effects_hash",
            }
            present_effect_members = effect_members.intersection(payload)
            if len(present_effect_members) not in {0, 3}:
                raise ConformanceError(
                    f"{inner['type']} effect outcome/effects/hash must be all present or all absent"
                )
            if present_effect_members:
                if payload["effect_outcome"] not in {
                    "not_applied",
                    "applied",
                    "partially_applied",
                    "unknown",
                }:
                    raise ConformanceError(f"{inner['type']} effect_outcome is invalid")
                if not isinstance(payload["actual_effects"], list):
                    raise ConformanceError(f"{inner['type']} actual_effects is not an array")
                _validate_digest(
                    payload["actual_effects_hash"],
                    f"{inner['type']}.actual_effects_hash",
                )
                if payload["actual_effects_hash"] != _canonical_object_hash(
                    MCP_ACTUAL_EFFECTS_HASH_DOMAIN, payload["actual_effects"]
                ):
                    raise ConformanceError(
                        f"{inner['type']} actual_effects_hash differs from actual_effects"
                    )
                if expected_actual_effects is not None and (
                    _canonical_json_rfc8785(payload["actual_effects"])
                    != _canonical_json_rfc8785(expected_actual_effects)
                ):
                    raise ConformanceError(
                        f"{inner['type']} actual effects differ from the expected effect record"
                    )
            if (
                inner["type"] == "action.result"
                and action_mode in MCP_EFFECT_MODES
                and not present_effect_members
            ):
                raise ConformanceError(
                    "effect-capable action.result lacks complete effect evidence"
                )
            if action_mode in {"read", "dry_run"} and present_effect_members:
                raise ConformanceError(
                    f"{action_mode} action.result cannot claim attempted effects"
                )
            if action_mode == "dry_run" and {
                "receipt_id", "receipt_hash", "approval_receipt_id",
                "approval_receipt_hash",
            }.intersection(payload):
                raise ConformanceError(
                    "dry_run action.result cannot create receipt-side coordination state"
                )
            approval_hashes = payload.get("approval_receipt_hashes")
            if approval_hashes is not None:
                if not isinstance(approval_hashes, dict) or not approval_hashes:
                    raise ConformanceError(
                        f"{inner['type']} approval receipt map is empty or invalid"
                    )
                if any(role not in {"runtime", "application"} for role in approval_hashes):
                    raise ConformanceError(
                        f"{inner['type']} approval receipt map is not closed"
                    )
                for role, digest in approval_hashes.items():
                    _validate_digest(
                        digest, f"{inner['type']}.approval_receipt_hashes.{role}"
                    )
                if action_mode not in MCP_EFFECT_MODES:
                    raise ConformanceError(
                        f"{action_mode} action response cannot claim approval receipts"
                    )
            request_approval_hashes = (
                expected_request_payload.get("approval_receipt_hashes")
                if isinstance(expected_request_payload, dict)
                else None
            )
            if (
                request_approval_hashes is not None
                and not pre_admission_capacity_error
                and (
                not isinstance(approval_hashes, dict)
                or any(
                    approval_hashes.get(role) != digest
                    for role, digest in request_approval_hashes.items()
                )
                )
            ):
                raise ConformanceError(
                    f"{inner['type']} does not preserve request approval receipt hashes"
                )
            if (
                request_approval_hashes is not None
                and expected_final_approval_receipt_hashes is None
                and not pre_admission_capacity_error
                and approval_hashes != request_approval_hashes
            ):
                raise ConformanceError(
                    f"{inner['type']} adds an approval receipt without final policy"
                )
            if (
                expected_final_approval_receipt_hashes is not None
                and not pre_admission_capacity_error
                and (
                approval_hashes != expected_final_approval_receipt_hashes
                )
            ):
                raise ConformanceError(
                    f"{inner['type']} final approval receipt map differs from policy"
                )
            if expected_authenticated_approval_receipts is not None:
                raise ConformanceError(
                    "legacy approval-only receipt context is not authoritative"
                )
            if receipt_required is True and not pre_admission_capacity_error and not {
                "receipt_id",
                "receipt_hash",
            }.issubset(payload):
                raise ConformanceError("MCP action response lacks required receipt identity")
            for left, right in (
                ("approval_receipt_id", "approval_receipt_hash"),
                ("receipt_id", "receipt_hash"),
            ):
                if (left in payload) != (right in payload):
                    raise ConformanceError(
                        f"{inner['type']} must pair {left} with {right}"
                    )
            for member in (
                "actual_effects_hash",
                "approval_receipt_hash",
                "receipt_hash",
            ):
                if member in payload:
                    _validate_digest(payload[member], f"{inner['type']}.{member}")
            referenced_receipt = any(
                member in payload
                for member in ("receipt_id", "approval_receipt_id")
            ) or approval_hashes is not None
            if referenced_receipt and not structured.get("receipt_resource_uris"):
                raise ConformanceError(
                    "action response receipt identifiers lack authenticated ResourceLinks"
                )
            if expected_receipt_resource_uris is not None and (
                structured.get("receipt_resource_uris", [])
                != expected_receipt_resource_uris
            ):
                raise ConformanceError(
                    "action response receipt ResourceLinks differ from expected receipts"
                )
            if not referenced_receipt and structured.get("receipt_resource_uris"):
                raise ConformanceError(
                    "action response exposes receipt ResourceLinks without receipt identity"
                )
            _validate_mcp_receipt_resource_set(
                inner_type=inner["type"],
                payload=payload,
                linked_uris=linked_uris,
                expected_records=expected_authenticated_receipt_resources,
            )
        if inner["type"] == "action.error":
            for left, right in (
                ("approval_receipt_id", "approval_receipt_hash"),
                ("receipt_id", "receipt_hash"),
            ):
                if (left in payload) != (right in payload):
                    raise ConformanceError(
                        f"action.error must pair {left} with {right}"
                    )
            error_code = payload["error"]["code"]
            if error_code in {
                "rate_limited",
                "capacity_state_unavailable",
                "service_unavailable",
            }:
                if (
                    capacity_declared_limit_ids is None
                    or capacity_disclosable_limit_ids is None
                ):
                    raise ConformanceError(
                        "MCP capacity action.error lacks authoritative limit context"
                    )
                validate_capacity_error(
                    payload["error"],
                    {
                        "declared_limit_ids": capacity_declared_limit_ids,
                        "disclosable_limit_ids": capacity_disclosable_limit_ids,
                    },
                )
                forbidden_capacity_members = effect_members | {
                    "approval_receipt_id", "approval_receipt_hash",
                    "approval_receipt_hashes", "receipt_id", "receipt_hash",
                }
                if forbidden_capacity_members.intersection(payload):
                    raise ConformanceError(
                        "pre-admission capacity action.error claims effects or receipts"
                    )
            approval_present = "approval_receipt_id" in payload
            if (error_code == "approval_denied") != approval_present:
                raise ConformanceError(
                    "action.error approval receipt presence does not match approval_denied"
                )
            if error_code == "approval_denied" and effect_members.intersection(payload):
                raise ConformanceError(
                    "approval_denied claims action effects"
                )

    if message.get("kind") == "streamable_http_binding":
        endpoint_value = message["endpoint"]
        endpoint = urlsplit(endpoint_value)
        if (
            "?" in endpoint_value.split("#", 1)[0]
            or "#" in endpoint_value
            or endpoint.fragment
            or endpoint.query
            or endpoint.username is not None
            or endpoint.password is not None
        ):
            raise ConformanceError(
                "MCP endpoint must omit fragments and URL credential material"
            )
        _validate_mcp_credential_free_uri(
            message["endpoint"],
            label="MCP endpoint",
            forbidden_credential_values=forbidden_credentials,
        )
        if expected_endpoint is not None and message["endpoint"] != expected_endpoint:
            raise ConformanceError("MCP endpoint differs from the manifest binding")
        authorization = message["authorization"]
        request_authorizations = authorization.get("request_authorizations")
        expected_request_methods = {
            "initialize": "POST",
            "post": "POST",
            "listener": "GET",
            "termination": "DELETE",
        }
        if not isinstance(request_authorizations, list) or len(request_authorizations) != 4:
            raise ConformanceError(
                "MCP authorization evidence does not cover the closed request lifecycle"
            )
        request_records = {
            item.get("request_class"): item
            for item in request_authorizations
            if isinstance(item, dict)
        }
        expected_binding_kind = {
            "dpop": "dpop_htu_htm",
            "mtls": "mtls_channel",
            "mtls_bound_bearer": "mtls_channel",
            "compatibility_bearer": "bearer_transport",
        }.get(authorization.get("asp_credential_profile"))
        exact_target = expected_proof_target_uri or endpoint_value
        if (
            set(request_records) != set(expected_request_methods)
            or expected_binding_kind is None
            or any(
                record.get("method") != expected_request_methods[request_class]
                or record.get("target_uri") != endpoint_value
                or record.get("target_uri") != exact_target
                or record.get("authorization_applied") is not True
                or record.get("binding_kind") != expected_binding_kind
                or record.get("binding_verified") is not True
                for request_class, record in request_records.items()
            )
        ):
            raise ConformanceError(
                "MCP authorization evidence is not bound to every exact request target"
            )
        if (
            authorization["composition"] == "mcp_oauth_dual_use"
            and authorization["audience"] != message["endpoint"]
        ):
            raise ConformanceError(
                "dual-use MCP OAuth audience differs from the canonical endpoint"
            )
        if (
            expected_credential_audience is not None
            and authorization["audience"] != expected_credential_audience
        ):
            raise ConformanceError(
                "MCP transport credential audience differs from the manifest"
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
        HUMAN_ELICITATION_SCHEMA_ID: set(),
        IMPACT_SIMULATION_SCHEMA_ID: set(),
        RISK_EXPLANATION_SCHEMA_ID: set(),
        MCP_BINDING_SCHEMA_ID: set(),
        PURPOSE_TASK_BOUND_GRANT_SCHEMA_ID: set(),
    }
    for case in catalog["cases"]:
        schema_id = case["schema_id"]
        expected_prefix = {
            OPERATIONAL_LIMITS_SCHEMA_ID: "ASP-SC-OL-",
            CAPACITY_ERROR_SCHEMA_ID: "ASP-SC-CE-",
            HUMAN_ELICITATION_SCHEMA_ID: "ASP-SC-HE-",
            IMPACT_SIMULATION_SCHEMA_ID: "ASP-SC-IS-",
            RISK_EXPLANATION_SCHEMA_ID: "ASP-SC-RE-",
            MCP_BINDING_SCHEMA_ID: "ASP-SC-MB-",
            PURPOSE_TASK_BOUND_GRANT_SCHEMA_ID: "ASP-SC-PB-",
        }[schema_id]
        if not case["case_id"].startswith(expected_prefix):
            raise ConformanceError(
                f"schema case {case['case_id']} has a mismatched schema prefix"
            )
        polarities[schema_id].add(case["polarity"])

        error: ConformanceError | None = None
        try:
            parser = (
                loads_human_json
                if schema_id in {HUMAN_ELICITATION_SCHEMA_ID, MCP_BINDING_SCHEMA_ID}
                else loads_strict_json
            )
            instance = parser(
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
            elif schema_id == CAPACITY_ERROR_SCHEMA_ID:
                validate_capacity_error(
                    instance,
                    case["context"],
                    root=root,
                    registry=registry,
                    schema=schemas["capacity-error"],
                )
            elif schema_id == HUMAN_ELICITATION_SCHEMA_ID:
                validate_human_elicitation(
                    instance,
                    case["context"],
                    root=root,
                    registry=registry,
                    schema=schemas["human-elicitation"],
                )
            elif schema_id == IMPACT_SIMULATION_SCHEMA_ID:
                validate_impact_simulation(
                    instance,
                    case["context"],
                    root=root,
                    registry=registry,
                    schema=schemas["impact-simulation"],
                )
            elif schema_id == MCP_BINDING_SCHEMA_ID:
                _validate_with_schema(
                    instance,
                    schemas["mcp-binding"],
                    "ASP-over-MCP wire case",
                    registry=registry,
                )
                validate_mcp_wire_semantics(instance, **case["context"])
            elif schema_id == PURPOSE_TASK_BOUND_GRANT_SCHEMA_ID:
                _validate_with_schema(
                    instance,
                    schemas["purpose-task-bound-grant"],
                    "Purpose Binding case",
                    registry=registry,
                )
            else:
                validate_risk_explanation(
                    instance,
                    case["context"],
                    root=root,
                    registry=registry,
                    schema=schemas["risk-explanation"],
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


def validate_purpose_task_bound_grant_projection(
    projection: dict[str, Any],
    *,
    root: Path = ROOT,
    registry: Registry | None = None,
) -> None:
    registry = registry or _schema_registry(root)
    binding_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": PURPOSE_TASK_BOUND_GRANT_SCHEMA_ID,
    }
    bindings: dict[str, dict[str, Any]] = {}
    for member in ("request", "consent", "grant", "returned", "session", "parent"):
        binding = projection[member]
        _validate_with_schema(
            binding,
            binding_schema,
            f"Purpose Binding projection member {member}",
            registry=registry,
        )
        bindings[member] = binding
    if any(
        bindings[member] != bindings["request"]
        for member in ("consent", "grant", "returned", "session")
    ):
        raise ConformanceError(
            "Purpose Binding baseline does not preserve exact request, consent, "
            "Grant, returned, and session objects"
        )
    if (
        projection["advertised_profile"] is not True
        or projection["enforcement_ready"] is not True
        or projection["expiry_within_lifetime"] is not True
        or projection["lifecycle_linked"] is not True
        or projection["goal_authority_use"] != "informational_only"
    ):
        raise ConformanceError(
            "Purpose Binding baseline does not represent complete fail-closed enforcement"
        )
    if projection["authenticated_scope"] != projection["authoritative"]["scope"]:
        raise ConformanceError(
            "Purpose Binding baseline crosses its authenticated namespace"
        )
    purpose_ref = bindings["grant"]["purpose"]
    purpose_record = projection["authoritative"]["purpose"]
    if (
        purpose_ref
        != {"id": purpose_record["id"], "revision": purpose_record["revision"]}
        or purpose_record["state"] != "active"
        or purpose_record["policy"] != "allow"
    ):
        raise ConformanceError(
            "Purpose Binding baseline lacks an exact active allowed purpose record"
        )
    task_ref = bindings["grant"].get("task")
    task_record = projection["authoritative"]["task"]
    if task_ref is None:
        if task_record is not None:
            raise ConformanceError(
                "purpose-only baseline resolves an unexpected task record"
            )
    elif (
        task_record is None
        or task_ref
        != {"id": task_record["id"], "revision": task_record["revision"]}
        or task_record["parent"] != purpose_ref
        or task_record["state"] != "active"
        or task_record["policy"] != "allow"
    ):
        raise ConformanceError(
            "task-bound baseline lacks its exact active parent relationship"
        )
    parent = bindings["parent"]
    expected_relation = (
        "equal"
        if parent == bindings["grant"]
        else (
            "narrower"
            if parent["purpose"] == purpose_ref
            and "task" not in parent
            and task_ref is not None
            else "wider"
        )
    )
    if (
        projection["attenuation"] != expected_relation
        or expected_relation == "wider"
    ):
        raise ConformanceError(
            "Purpose Binding baseline violates the portable attenuation order"
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
    bundle_registry: dict[str, Any],
    *,
    snapshot_catalog_sha256: str,
    snapshot_specification_sha256: str,
) -> Catalog:
    if (
        suite["suite_id"] != SUITE_ID
        or vector_catalog["suite_id"] != SUITE_ID
        or fixture_catalog["suite_id"] != SUITE_ID
        or schema_case_catalog["suite_id"] != SUITE_ID
        or bundle_registry["suite_id"] != SUITE_ID
    ):
        raise ConformanceError("catalog suite_id must be the exact ASP v1 suite identifier")
    if len(
        {
            suite["suite_version"],
            vector_catalog["suite_version"],
            fixture_catalog["suite_version"],
            schema_case_catalog["suite_version"],
            bundle_registry["suite_version"],
        }
    ) != 1:
        raise ConformanceError("suite, vector, fixture, case, and bundle versions differ")
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
        operation = vector["stimulus"]["operation"]
        selects_http_capacity = "http_capacity_binding_selected" in vector["setup"]
        is_http_capacity_operation = operation in {
            "bind_http_capacity_response",
            "handle_http_capacity_response",
        }
        if selects_http_capacity != is_http_capacity_operation:
            raise ConformanceError(
                f"vector {vector_id} HTTP capacity setup and operation differ"
            )
        has_transport = "transport" in fixture["document"]
        if operation == "handle_http_capacity_response":
            if not has_transport or not isinstance(capacity_response, dict):
                raise ConformanceError(
                    f"HTTP capacity consumer vector {vector_id} lacks its projection"
                )
            validate_http_capacity_projection(
                fixture["document"]["transport"], capacity_response
            )
        elif has_transport:
            raise ConformanceError(
                f"non-consumer vector {vector_id} carries an HTTP response projection"
            )
        if operation == "bind_http_capacity_response":
            if not isinstance(capacity_response, dict):
                raise ConformanceError(
                    f"HTTP capacity producer vector {vector_id} lacks an error envelope"
                )
            hint = operational_state.get("http_retry_after_hint", "absent")
            validate_http_capacity_projection(
                {
                    "binding": "http",
                    "authentication": "authenticated",
                    "status": 429
                    if capacity_response["code"] == "rate_limited"
                    else 503,
                    "cache_control_no_store": True,
                    "retry_after": hint,
                },
                capacity_response,
            )
        elif has_operational_feature and "http_retry_after_hint" in operational_state:
            raise ConformanceError(
                f"non-producer vector {vector_id} carries an HTTP retry hint"
            )
        selects_ahp = "asp_over_ahp_selected" in vector["setup"]
        is_ahp_operation = operation in {
            "present_ahp_session",
            "translate_ahp_action",
        }
        if selects_ahp != is_ahp_operation:
            raise ConformanceError(
                f"vector {vector_id} ASP-over-AHP setup and operation differ"
            )
        has_ahp_feature = ASP_OVER_AHP_FEATURE_ID in vector["features"]
        if has_ahp_feature != is_ahp_operation:
            raise ConformanceError(
                f"vector {vector_id} ASP-over-AHP feature and operation differ"
            )
        has_ahp_projection = "ahp" in fixture["document"]
        if is_ahp_operation:
            if (
                not has_ahp_projection
                or "authenticated_ahp_channel" not in vector["setup"]
            ):
                raise ConformanceError(
                    f"ASP-over-AHP vector {vector_id} lacks its authenticated projection"
                )
            validate_ahp_binding_projection(fixture["document"]["ahp"])
        elif has_ahp_projection:
            raise ConformanceError(
                f"non-AHP vector {vector_id} carries an ASP-over-AHP projection"
            )
        selects_mcp = "asp_over_mcp_selected" in vector["setup"]
        is_mcp_operation = operation in {
            "issue_mcp_grant",
            "publish_mcp_surface",
            "execute_mcp_action",
            "mediate_mcp_action",
            "adapt_mcp_action",
        }
        if selects_mcp != is_mcp_operation:
            raise ConformanceError(
                f"vector {vector_id} ASP-over-MCP setup and operation differ"
            )
        has_mcp_feature = ASP_OVER_MCP_FEATURE_ID in vector["features"]
        if has_mcp_feature != is_mcp_operation:
            raise ConformanceError(
                f"vector {vector_id} ASP-over-MCP feature and operation differ"
            )
        has_mcp_projection = "mcp" in fixture["document"]
        if is_mcp_operation:
            prechannel_grant = operation == "issue_mcp_grant"
            has_authenticated_channel = "authenticated_mcp_channel" in vector["setup"]
            if not has_mcp_projection or (
                prechannel_grant == has_authenticated_channel
            ):
                raise ConformanceError(
                    f"ASP-over-MCP vector {vector_id} has invalid pre/post-channel setup"
                )
            validate_mcp_binding_projection(
                fixture["document"]["mcp"],
                fixture["document"],
                operation,
            )
        elif has_mcp_projection:
            raise ConformanceError(
                f"non-MCP vector {vector_id} carries an ASP-over-MCP projection"
            )
        selects_elicitation = "human_elicitation_selected" in vector["setup"]
        is_elicitation_operation = operation in {
            "mediate_human_elicitation",
            "apply_human_elicitation_candidate",
            "project_human_elicitation_answer",
        }
        if selects_elicitation != is_elicitation_operation:
            raise ConformanceError(
                f"vector {vector_id} Human Elicitation setup and operation differ"
            )
        has_elicitation_feature = (
            HUMAN_ELICITATION_FEATURE_ID in vector["features"]
        )
        if has_elicitation_feature != is_elicitation_operation:
            raise ConformanceError(
                f"vector {vector_id} Human Elicitation feature and operation differ"
            )
        has_elicitation_projection = "elicitation" in fixture["document"]
        if is_elicitation_operation:
            if (
                not has_elicitation_projection
                or "authenticated_human_channel" not in vector["setup"]
            ):
                raise ConformanceError(
                    f"Human Elicitation vector {vector_id} lacks its "
                    "authenticated projection"
                )
            validate_human_elicitation_projection(
                fixture["document"]["elicitation"],
                root=root,
            )
            if operation == "project_human_elicitation_answer":
                validate_agent_human_elicitation_projection(
                    fixture["document"]["elicitation"]
                )
            elif "agent_projection" in fixture["document"]["elicitation"]:
                raise ConformanceError(
                    f"non-Agent Adapter vector {vector_id} carries an "
                    "agent-facing Human Elicitation projection"
                )
        elif has_elicitation_projection:
            raise ConformanceError(
                f"non-elicitation vector {vector_id} carries a Human "
                "Elicitation projection"
            )
        has_risk_explanation_feature = (
            RISK_EXPLANATION_FEATURE_ID in vector["features"]
        )
        has_risk_explanation_projection = (
            "risk_explanation" in fixture["document"]
        )
        if has_risk_explanation_feature != has_risk_explanation_projection:
            raise ConformanceError(
                f"Risk Explanation vector {vector_id} feature selection and "
                "fixture state differ"
            )
        renders_risk_explanation = operation == "render_risk_explanation"
        selects_risk_explanation = "risk_explanation_present" in vector["setup"]
        if renders_risk_explanation != selects_risk_explanation:
            raise ConformanceError(
                f"Risk Explanation vector {vector_id} setup and operation differ"
            )
        if has_risk_explanation_feature:
            if operation not in {"publish_manifest", "render_risk_explanation"}:
                raise ConformanceError(
                    f"Risk Explanation vector {vector_id} uses an invalid operation"
                )
            if (
                operation == "publish_manifest"
                and profile_id
                != "https://github.com/0al-spec/agent-surface/conformance/surface-publisher/v1"
            ) or (
                operation == "render_risk_explanation"
                and profile_id
                != "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1"
            ):
                raise ConformanceError(
                    f"Risk Explanation vector {vector_id} targets the wrong role"
                )
            validator = (
                validate_risk_explanation_publisher_projection
                if operation == "publish_manifest"
                else validate_risk_explanation_projection
            )
            validator(
                fixture["document"]["risk_explanation"],
                fixture["document"]["surface"],
                root=root,
            )
        elif selects_risk_explanation:
            raise ConformanceError(
                f"non-Risk-Explanation vector {vector_id} selects hint rendering"
            )
        has_impact_simulation_feature = (
            IMPACT_SIMULATION_FEATURE_ID in vector["features"]
        )
        has_impact_simulation_projection = (
            "impact_simulation" in fixture["document"]
        )
        simulates_impact = operation == "simulate_impact"
        embedded_impact_carriers = {
            patch_operation["path"]
            for patch_operation in mutation["patch"]
            if patch_operation["op"] == "copy"
            and patch_operation.get("from") == "/impact_simulation/result"
        }
        rejects_embedded_impact = (
            operation in {"mediate_grant", "mediate_action"}
            and bool(embedded_impact_carriers)
        )
        exercises_impact = simulates_impact or rejects_embedded_impact
        selects_impact_simulation = "impact_simulation_selected" in vector["setup"]
        if (
            has_impact_simulation_feature
            != has_impact_simulation_projection
            or exercises_impact != selects_impact_simulation
            or has_impact_simulation_feature != exercises_impact
        ):
            raise ConformanceError(
                f"Impact Simulation vector {vector_id} feature, setup, operation, "
                "and fixture state differ"
            )
        if has_impact_simulation_feature:
            if profile_id != (
                "https://github.com/0al-spec/agent-surface/"
                "conformance/runtime-mediator/v1"
            ):
                raise ConformanceError(
                    f"Impact Simulation vector {vector_id} targets the wrong role"
                )
            validate_impact_simulation_projection(
                fixture["document"]["impact_simulation"],
                fixture["document"]["surface"],
                fixture["document"]["grant"],
                fixture["document"]["execution"],
                root=root,
            )
        has_purpose_binding_feature = (
            PURPOSE_TASK_BOUND_GRANT_FEATURE_ID in vector["features"]
        )
        has_purpose_binding_projection = (
            "purpose_binding" in fixture["document"]
        )
        selects_purpose_binding = (
            "purpose_task_binding_selected" in vector["setup"]
        )
        if (
            has_purpose_binding_feature
            != has_purpose_binding_projection
            or has_purpose_binding_feature != selects_purpose_binding
        ):
            raise ConformanceError(
                f"Purpose Binding vector {vector_id} feature, setup, and fixture "
                "state differ"
            )
        if has_purpose_binding_feature:
            allowed_operations = {
                "https://github.com/0al-spec/agent-surface/conformance/"
                "surface-publisher/v1": {"publish_manifest"},
                "https://github.com/0al-spec/agent-surface/conformance/"
                "grant-issuer/v1": {"issue_grant"},
                "https://github.com/0al-spec/agent-surface/conformance/"
                "action-executor/v1": {"invoke_action", "replay_action"},
                "https://github.com/0al-spec/agent-surface/conformance/"
                "runtime-mediator/v1": {"mediate_grant"},
            }
            if (
                profile_id not in allowed_operations
                or operation not in allowed_operations[profile_id]
                or "authenticated_purpose_records" not in vector["setup"]
            ):
                raise ConformanceError(
                    f"Purpose Binding vector {vector_id} targets an invalid role, "
                    "operation, or record source"
                )
            validate_purpose_task_bound_grant_projection(
                fixture["document"]["purpose_binding"],
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

    if bundle_registry["protocol_version"] != PROTOCOL_VERSION:
        raise ConformanceError(
            "bundle registry protocol_version must be exactly agent-surface/0.1"
        )
    if bundle_registry["claim_effect"] != "descriptive_only":
        raise ConformanceError("bundle registry claim_effect must remain descriptive_only")
    bundles = _unique_index(bundle_registry["bundles"], "bundle_id", "bundle")
    if list(bundles) != sorted(bundles):
        raise ConformanceError("bundle ids must use canonical lexicographic order")
    profile_order = {profile_id: index for index, profile_id in enumerate(profiles)}
    bundle_shapes: set[str] = set()
    bundle_kinds: set[str] = set()
    for bundle_id, bundle in bundles.items():
        bundle_kinds.add(bundle["kind"])
        claim_keys: list[tuple[str, str]] = []
        for claim in bundle["claims"]:
            profile_id = claim["profile_id"]
            if profile_id not in profiles:
                raise ConformanceError(
                    f"bundle {bundle_id} references unknown profile {profile_id}"
                )
            producer_role = claim.get("producer_role", "")
            claim_key = (profile_id, producer_role)
            if claim_key in claim_keys:
                raise ConformanceError(f"bundle {bundle_id} repeats a role claim")
            claim_keys.append(claim_key)
            if claim["feature_ids"] != sorted(claim["feature_ids"]):
                raise ConformanceError(
                    f"bundle {bundle_id} feature ids are not canonical"
                )
            unknown_features = set(claim["feature_ids"]) - set(features)
            if unknown_features:
                raise ConformanceError(
                    f"bundle {bundle_id} references unknown features: "
                    + ", ".join(sorted(unknown_features))
                )

            expected_requirement_ids: list[str] = []
            covered_feature_ids: set[str] = set()
            for requirement_id in profiles[profile_id]["requirement_ids"]:
                requirement = requirements[requirement_id]
                applicability = requirement["applicability"]
                applies = applicability["kind"] == "always"
                if applicability["kind"] == "feature":
                    feature_id = applicability["feature_id"]
                    applies = feature_id in claim["feature_ids"]
                    if applies:
                        covered_feature_ids.add(feature_id)
                elif applicability["kind"] == "producer_role":
                    applies = applicability["producer_role"] == producer_role
                if applies:
                    expected_requirement_ids.append(requirement_id)
            uncovered_features = set(claim["feature_ids"]) - covered_feature_ids
            if uncovered_features:
                raise ConformanceError(
                    f"bundle {bundle_id} selects features without matrix coverage for "
                    f"{profile_id}: " + ", ".join(sorted(uncovered_features))
                )
            if claim["requirement_ids"] != expected_requirement_ids:
                raise ConformanceError(
                    f"bundle {bundle_id} omits or reorders applicable requirements for "
                    f"{profile_id}"
                )
            expected_vector_ids: list[str] = []
            for requirement_id in expected_requirement_ids:
                for vector_id in requirements[requirement_id]["vector_ids"]:
                    if vector_id not in expected_vector_ids:
                        expected_vector_ids.append(vector_id)
            if claim["vector_ids"] != expected_vector_ids:
                raise ConformanceError(
                    f"bundle {bundle_id} omits or reorders executable vectors for "
                    f"{profile_id}"
                )
            claim_polarities = {
                vectors[vector_id]["polarity"] for vector_id in expected_vector_ids
            }
            if claim_polarities != {"positive", "negative"}:
                raise ConformanceError(
                    f"bundle {bundle_id} claim {profile_id} requires positive and "
                    "negative vectors"
                )

        expected_claim_order = sorted(
            claim_keys,
            key=lambda item: (
                profile_order[item[0]],
                {"": 0, "application": 1, "runtime": 2}[item[1]],
            ),
        )
        if claim_keys != expected_claim_order:
            raise ConformanceError(f"bundle {bundle_id} claims are not canonically ordered")
        shape = json.dumps(bundle["claims"], sort_keys=True, separators=(",", ":"))
        if shape in bundle_shapes:
            raise ConformanceError(f"bundle {bundle_id} duplicates another bundle")
        bundle_shapes.add(shape)
    if bundle_kinds != {"foundation", "feature_overlay"}:
        raise ConformanceError(
            "bundle registry requires both foundation and feature_overlay entries"
        )
    if used_fixtures != set(fixtures):
        raise ConformanceError("fixture catalog contains unused or unreferenced fixtures")
    if used_mutations != set(mutations):
        raise ConformanceError("fixture catalog contains unused or unreferenced mutations")

    return Catalog(
        root=root,
        snapshot_catalog_sha256=snapshot_catalog_sha256,
        snapshot_specification_sha256=snapshot_specification_sha256,
        snapshot_memory_sha256=_catalog_memory_digest_values(
            suite=suite,
            vector_catalog=vector_catalog,
            fixture_catalog=fixture_catalog,
            schema_case_catalog=schema_case_catalog,
            bundle_registry=bundle_registry,
            requirements=requirements,
            vectors=vectors,
            profiles=profiles,
            features=features,
            fixtures=fixtures,
            mutations=mutations,
            bundles=bundles,
        ),
        suite=suite,
        vector_catalog=vector_catalog,
        fixture_catalog=fixture_catalog,
        schema_case_catalog=schema_case_catalog,
        bundle_registry=bundle_registry,
        requirements=requirements,
        vectors=vectors,
        profiles=profiles,
        features=features,
        fixtures=fixtures,
        mutations=mutations,
        bundles=bundles,
    )


def validate_catalog(root: Path = ROOT) -> Catalog:
    """Validate JSON Schemas, catalog shapes, RFC anchors, and matrix closure."""

    root = root.resolve()
    (
        snapshot_catalog_sha256,
        snapshot_specification_sha256,
    ) = _snapshot_source_digests(root)
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
    schema_case_catalog = load_schema_case_json(v1_dir / "schema-cases.json")
    bundle_registry = load_strict_json(v1_dir / "bundles.json")
    registry = _schema_registry(root)
    _validate_schema_ref_closure(schemas, registry)
    _validate_with_schema(suite, schemas["suite"], "suite.json", registry=registry)
    _validate_with_schema(
        vector_catalog, schemas["vectors"], "vectors.json", registry=registry
    )
    _validate_with_schema(
        bundle_registry,
        schemas["bundles"],
        "bundles.json",
        registry=registry,
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
    catalog = _semantic_validate_catalog(
        root,
        suite,
        vector_catalog,
        fixture_catalog,
        schema_case_catalog,
        bundle_registry,
        snapshot_catalog_sha256=snapshot_catalog_sha256,
        snapshot_specification_sha256=snapshot_specification_sha256,
    )
    if _snapshot_source_digests(root) != (
        snapshot_catalog_sha256,
        snapshot_specification_sha256,
    ):
        raise ConformanceError("catalog or specification changed during validation")
    return catalog


def _resolve_catalog(
    root: Path, catalog: Catalog | None
) -> tuple[Path, Catalog]:
    """Return a fresh or explicitly prevalidated catalog for one exact root.

    Explicit reuse is snapshot-scoped. Source and in-memory fingerprints are
    checked before every reuse. The default path always validates fresh.
    """

    root = root.resolve()
    if catalog is None:
        return root, validate_catalog(root)
    if catalog.root != root:
        raise ConformanceError(
            "prevalidated catalog root does not match the requested root"
        )
    current_catalog_sha256, current_specification_sha256 = (
        _snapshot_source_digests(root)
    )
    if current_catalog_sha256 != catalog.snapshot_catalog_sha256:
        raise ConformanceError(
            "prevalidated catalog snapshot is stale: catalog source files changed"
        )
    if current_specification_sha256 != catalog.snapshot_specification_sha256:
        raise ConformanceError(
            "prevalidated catalog snapshot is stale: specification source changed"
        )
    try:
        current_memory_sha256 = _catalog_memory_digest(catalog)
    except (ConformanceError, TypeError, ValueError) as error:
        raise ConformanceError(
            "prevalidated catalog snapshot was mutated in memory"
        ) from error
    if current_memory_sha256 != catalog.snapshot_memory_sha256:
        raise ConformanceError(
            "prevalidated catalog snapshot was mutated in memory"
        )
    return root, catalog


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


def _snapshot_source_digests(root: Path) -> tuple[str, str]:
    try:
        return catalog_digest(root), specification_digest(root)
    except OSError as error:
        raise ConformanceError(
            "catalog or specification snapshot source files are unavailable"
        ) from error


def _type_tagged_json(value: Any, path: str = "$") -> dict[str, Any]:
    """Represent JSON-compatible values without collapsing scalar types."""

    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ConformanceError(
                f"non-finite catalog fingerprint value at {path}"
            )
        return {"type": "float64", "value": value.hex()}
    if isinstance(value, str):
        _validate_unicode(value, path)
        return {"type": "string", "value": value}
    if isinstance(value, list):
        return {
            "type": "array",
            "value": [
                _type_tagged_json(item, f"{path}[{index}]")
                for index, item in enumerate(value)
            ],
        }
    if isinstance(value, dict):
        tagged: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ConformanceError(
                    f"catalog fingerprint object key is not a string at {path}"
                )
            _validate_unicode(key, f"{path}.<key>")
            tagged[key] = _type_tagged_json(item, f"{path}.{key}")
        return {"type": "object", "value": tagged}
    raise ConformanceError(
        f"catalog fingerprint value at {path} is not JSON-compatible"
    )


def _catalog_memory_digest_values(
    *,
    suite: dict[str, Any],
    vector_catalog: dict[str, Any],
    fixture_catalog: dict[str, Any],
    schema_case_catalog: dict[str, Any],
    bundle_registry: dict[str, Any],
    requirements: dict[str, dict[str, Any]],
    vectors: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    features: dict[str, dict[str, Any]],
    fixtures: dict[str, dict[str, Any]],
    mutations: dict[str, dict[str, Any]],
    bundles: dict[str, dict[str, Any]],
) -> str:
    """Bind a validated Catalog to both raw documents and derived indexes."""

    payload = {
        "suite": suite,
        "vector_catalog": vector_catalog,
        "fixture_catalog": fixture_catalog,
        "schema_case_catalog": schema_case_catalog,
        "bundle_registry": bundle_registry,
        "requirements": requirements,
        "vectors": vectors,
        "profiles": profiles,
        "features": features,
        "fixtures": fixtures,
        "mutations": mutations,
        "bundles": bundles,
    }
    return _domain_digest(
        "ASP-CONFORMANCE-CATALOG-MEMORY-V1",
        _canonical_json_rfc8785(_type_tagged_json(payload)),
    )


def _catalog_memory_digest(catalog: Catalog) -> str:
    return _catalog_memory_digest_values(
        suite=catalog.suite,
        vector_catalog=catalog.vector_catalog,
        fixture_catalog=catalog.fixture_catalog,
        schema_case_catalog=catalog.schema_case_catalog,
        bundle_registry=catalog.bundle_registry,
        requirements=catalog.requirements,
        vectors=catalog.vectors,
        profiles=catalog.profiles,
        features=catalog.features,
        fixtures=catalog.fixtures,
        mutations=catalog.mutations,
        bundles=catalog.bundles,
    )


def _canonical_json_bytes(value: dict[str, Any]) -> bytes:
    _validate_ijson_value(value)
    return _canonical_json_rfc8785(value)


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
        # Keep lookup closed while allowing env-based Python entry points to
        # use the exact dependency environment that runs this harness.
        "PATH": os.pathsep.join(
            (str(Path(sys.executable).parent), "/usr/bin", "/bin")
        ),
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
        if operation["op"] == "copy":
            if (
                operation.get("from") != "/impact_simulation/result"
                or operation["path"]
                not in {"/grant/impact_simulation", "/execution/impact_simulation"}
            ):
                raise ConformanceError(
                    "v1 fixture runner rejects an unallowlisted copy patch"
                )
            source: Any = document
            try:
                for part in _decode_json_pointer(operation["from"]):
                    source = (
                        source[int(part)] if isinstance(source, list) else source[part]
                    )
                target: Any = document
                parts = _decode_json_pointer(operation["path"])
                for part in parts[:-1]:
                    target = (
                        target[int(part)] if isinstance(target, list) else target[part]
                    )
                if not isinstance(target, dict) or parts[-1] in target:
                    raise KeyError(parts[-1])
                target[parts[-1]] = copy.deepcopy(source)
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise ConformanceError(
                    "fixture copy mutation is invalid for its baseline"
                ) from error
            continue
        if operation["op"] != "replace":
            raise ConformanceError("v1 fixture runner supports only closed patches")
        parts = _decode_json_pointer(operation["path"])
        if not parts:
            raise ConformanceError("fixture mutation cannot replace the document root")
        target: Any = document
        try:
            for part in parts[:-1]:
                target = target[int(part)] if isinstance(target, list) else target[part]
            final = parts[-1]
            if isinstance(target, list):
                index = int(final)
                if target[index] == operation["value"]:
                    raise ConformanceError(
                        "fixture mutation must change its baseline value"
                    )
                target[index] = operation["value"]
            else:
                if final not in target:
                    raise KeyError(final)
                if target[final] == operation["value"]:
                    raise ConformanceError(
                        "fixture mutation must change its baseline value"
                    )
                target[final] = operation["value"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ConformanceError(
                "fixture mutation path is not present in its baseline"
            ) from error
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
    catalog: Catalog | None = None,
) -> dict[str, Any]:
    """Execute vectors, optionally reusing a snapshot-scoped validated catalog."""

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
    root, catalog = _resolve_catalog(root, catalog)
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
        "runner_version": "1.10.0",
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
            "catalog_sha256": catalog.snapshot_catalog_sha256,
            "specification_sha256": catalog.snapshot_specification_sha256,
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
    """Verify a report against a fresh or explicitly prevalidated exact catalog."""

    _validate_ijson_value(report)
    _validate_digest_members(report)
    root, catalog = _resolve_catalog(root, catalog)
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
        "catalog_sha256": catalog.snapshot_catalog_sha256,
        "specification_sha256": catalog.snapshot_specification_sha256,
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
                f"{len(catalog.bundles)} bundles, "
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
