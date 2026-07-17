"""Validation and derived planning state for RFC review metadata."""

from __future__ import annotations

import importlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from collections import Counter, deque
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


REVIEW_DIR = Path(__file__).resolve().parent
REPO_ROOT = REVIEW_DIR.parent
DATA_PATH = REVIEW_DIR / "review-data.json"
SCHEMA_PATH = REVIEW_DIR / "review-data.schema.json"
CONFORMANCE_V1_DIR = REPO_ROOT / "conformance" / "v1"
CONFORMANCE_SCHEMAS = {
    Path(f"conformance/v1/{name}.schema.json")
    for name in (
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
}
CONFORMANCE_REGISTRIES = {
    Path("conformance/v1/suite.json"),
    Path("conformance/v1/vectors.json"),
    Path("conformance/v1/fixtures.json"),
    Path("conformance/v1/schema-cases.json"),
}
LINTER_SCHEMAS = {
    Path("tools/asp-manifest-linter/schema/diagnostics.schema.json"),
    Path("tools/asp-manifest-linter/schema/rules.schema.json"),
}
LINTER_REGISTRY = Path("tools/asp-manifest-linter/rules/v1/rules.json")
LINTER_IMPLEMENTATIONS = {
    Path("tools/asp-manifest-linter/src/lib.rs"),
    Path("tools/asp-manifest-linter/src/main.rs"),
}
MOCK_SCHEMA = Path("mocks/v1/manifest.schema.json")
MOCK_REGISTRY = Path("mocks/v1/manifest.json")
MOCK_IMPLEMENTATIONS = {
    Path("mocks/mock_app.py"),
    Path("mocks/mock_runtime.py"),
}
CAPACITY_RECOVERY_IMPLEMENTATIONS = {
    Path("mocks/behavior.py"),
    Path("mocks/mock_runtime.py"),
}
HTTP_CAPACITY_IMPLEMENTATIONS = {
    Path("mocks/behavior.py"),
    Path("mocks/mock_app.py"),
    Path("mocks/mock_runtime.py"),
}
ASP_OVER_AHP_IMPLEMENTATIONS = {
    Path("mocks/behavior.py"),
    Path("mocks/mock_runtime.py"),
}
MACHINE_VALIDATED_REVIEW_BINDINGS = {
    27: {
        "rfc_anchor": {
            "asp-over-ahp-binding-profile",
            "session-authority-and-lifecycle",
            "interoperability-test-suite",
            "reference-mock-participants",
            "runtime-mediator-profile",
            "agent-adapter-profile",
        },
        "schema": {
            "conformance/v1/fixtures.schema.json",
            "conformance/v1/observation.schema.json",
            "conformance/v1/vectors.schema.json",
        },
        "registry": {
            "conformance/v1/suite.json",
            "conformance/v1/vectors.json",
            "conformance/v1/fixtures.json",
        },
        "implementation": {
            path.as_posix() for path in ASP_OVER_AHP_IMPLEMENTATIONS
        },
    },
    53: {
        "rfc_anchor": {
            "required-top-level-fields",
            "example-manifest",
            "actions",
            "events",
            "rate-limits-and-quotas",
            "event-subscription-authority",
            "event-delivery-semantics",
            "retention-and-backpressure",
            "error-model",
            "surface-publisher-profile",
            "action-executor-profile",
            "runtime-mediator-profile",
        },
        "schema": {path.as_posix() for path in CONFORMANCE_SCHEMAS},
        "registry": {path.as_posix() for path in CONFORMANCE_REGISTRIES},
    },
    57: {
        "rfc_anchor": {"reference-manifest-linter"},
        "schema": {path.as_posix() for path in LINTER_SCHEMAS},
        "registry": {LINTER_REGISTRY.as_posix()},
        "implementation": {
            path.as_posix() for path in LINTER_IMPLEMENTATIONS
        },
    },
    58: {
        "rfc_anchor": {"reference-mock-participants"},
        "schema": {MOCK_SCHEMA.as_posix()},
        "registry": {MOCK_REGISTRY.as_posix()},
        "implementation": {
            path.as_posix() for path in MOCK_IMPLEMENTATIONS
        },
    },
    60: {
        "rfc_anchor": {"interoperability-test-suite"},
        "schema": {path.as_posix() for path in CONFORMANCE_SCHEMAS},
        "registry": {path.as_posix() for path in CONFORMANCE_REGISTRIES},
    },
    61: {
        "rfc_anchor": {
            "error-model",
            "runtime-mediator-profile",
            "interoperability-test-suite",
            "reference-mock-participants",
        },
        "schema": {
            "conformance/v1/fixtures.schema.json",
            "conformance/v1/observation.schema.json",
            "conformance/v1/vectors.schema.json",
        },
        "registry": {
            "conformance/v1/suite.json",
            "conformance/v1/vectors.json",
            "conformance/v1/fixtures.json",
        },
        "implementation": {
            path.as_posix() for path in CAPACITY_RECOVERY_IMPLEMENTATIONS
        },
    },
    62: {
        "rfc_anchor": {
            "http-capacity-error-binding",
            "action-executor-profile",
            "runtime-mediator-profile",
            "interoperability-test-suite",
            "reference-mock-participants",
        },
        "schema": {
            "conformance/v1/capacity-error.schema.json",
            "conformance/v1/fixtures.schema.json",
            "conformance/v1/observation.schema.json",
            "conformance/v1/vectors.schema.json",
        },
        "registry": {
            "conformance/v1/suite.json",
            "conformance/v1/vectors.json",
            "conformance/v1/fixtures.json",
        },
        "implementation": {
            path.as_posix() for path in HTTP_CAPACITY_IMPLEMENTATIONS
        },
    },
}
EXACT_MACHINE_VALIDATED_REVIEW_IDS = {27, 53, 57, 58, 61, 62}
MATURITY_ORDER = (
    "proposal",
    "specified",
    "machine_validated",
    "implementation_tested",
    "interop_tested",
    "stable",
)


def load_review_payload(path: Path = DATA_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("review-data.json must contain a JSON object")
    return payload


def validate_review_payload(
    payload: Mapping[str, Any],
    heading_ids: Mapping[str, str],
    *,
    required_planning_mode: str | None = None,
) -> None:
    """Validate the JSON shape and cross-object planning invariants."""

    _validate_schema(payload)
    if (
        required_planning_mode is not None
        and payload["planning_metadata_mode"] != required_planning_mode
    ):
        raise ValueError(
            "Canonical review data must use planning_metadata_mode "
            f"{required_planning_mode!r}"
        )
    profiles = payload["profiles"]
    releases = payload["releases"]
    reviews = payload["reviews"]
    require_planning_metadata = payload["planning_metadata_mode"] == "required"

    profile_ids = _unique_ids(profiles, "profile")
    release_ids = _unique_ids(releases, "release")
    review_ids = _unique_ids(reviews, "review")
    if sorted(review_ids) != list(range(1, len(reviews) + 1)):
        raise ValueError("Review ids must be unique and sequential, starting at 1")

    _validate_dependency_graph(profiles, profile_ids, "profile")
    _validate_dependency_graph(reviews, review_ids, "review")

    actual_anchor_ids = set(heading_ids.values())
    for review in reviews:
        review_id = review["id"]
        if require_planning_metadata:
            missing = {"profile", "depends_on", "target_release", "maturity", "evidence"} - set(review)
            if missing:
                raise ValueError(
                    f"Review #{review_id} is missing planning metadata: {', '.join(sorted(missing))}"
                )

        profile = review.get("profile")
        if profile is not None and profile not in profile_ids:
            raise ValueError(f"Review #{review_id} references unknown profile: {profile}")

        target_release = review.get("target_release")
        if target_release is not None and target_release not in release_ids:
            raise ValueError(f"Review #{review_id} references unknown release: {target_release}")

        review_anchor_ids: set[str] = set()
        anchor_headings: set[str] = set()
        for anchor in review["anchors"]:
            heading = anchor["heading"]
            anchor_id = anchor["anchorId"]
            if heading in anchor_headings:
                raise ValueError(f"Review #{review_id} must have unique anchor headings")
            anchor_headings.add(heading)
            expected_anchor_id = heading_ids.get(heading)
            if expected_anchor_id is None:
                raise ValueError(f"Review #{review_id} references unresolved RFC heading: {heading}")
            if anchor_id != expected_anchor_id:
                raise ValueError(
                    f"Review #{review_id} has stale anchorId for {heading!r}: "
                    f"expected {expected_anchor_id!r}, got {anchor_id!r}"
                )
            review_anchor_ids.add(anchor_id)

        evidence = review.get("evidence", [])
        evidence_keys = [(item["kind"], item["ref"]) for item in evidence]
        duplicate_evidence = sorted(
            {key for key in evidence_keys if evidence_keys.count(key) > 1}
        )
        if duplicate_evidence:
            formatted = ", ".join(f"{kind}:{ref}" for kind, ref in duplicate_evidence)
            raise ValueError(f"Review #{review_id} has duplicate evidence references: {formatted}")
        evidence_kinds = {item["kind"] for item in evidence}
        for item in evidence:
            kind = item["kind"]
            ref = item["ref"]
            if kind == "rfc_anchor":
                if ref not in actual_anchor_ids:
                    raise ValueError(
                        f"Review #{review_id} evidence references unknown RFC anchor: {ref}"
                    )
                if ref not in review_anchor_ids:
                    raise ValueError(
                        f"Review #{review_id} RFC evidence {ref!r} must also be declared in anchors"
                    )
            elif kind == "schema":
                _validate_schema_evidence(review_id, ref)
            elif kind == "registry":
                _validate_registry_evidence(review_id, ref)
            elif kind == "implementation":
                _validate_implementation_evidence(review_id, ref)
            else:
                raise ValueError(
                    f"Review #{review_id} evidence kind {kind!r} is not supported "
                    "until an authoritative resolver is configured"
                )

        maturity = review.get("maturity")
        if maturity is not None:
            if review["status"] in {"partial", "missing"} and maturity != "proposal":
                raise ValueError(
                    f"Review #{review_id} status {review['status']!r} cannot exceed proposal maturity"
                )
            _validate_maturity_evidence(review_id, maturity, evidence)


def normalize_reviews(
    payload: Mapping[str, Any], heading_ids: Mapping[str, str]
) -> list[dict[str, Any]]:
    """Return reviews in stable id order with RFC anchors normalized from headings."""

    normalized: list[dict[str, Any]] = []
    for review in sorted(payload["reviews"], key=lambda item: item["id"]):
        anchors = [
            {"heading": anchor["heading"], "anchorId": heading_ids[anchor["heading"]]}
            for anchor in review["anchors"]
        ]
        normalized.append({**review, "anchors": anchors})
    return derive_review_planning_state(normalized)


def derive_review_planning_state(
    reviews: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Derive reverse dependencies and readiness without persisting either field."""

    reviews_by_id = {review["id"]: review for review in reviews}
    blocks_by_id: dict[int, list[int]] = {review_id: [] for review_id in reviews_by_id}
    for review in reviews:
        for dependency_id in review["depends_on"]:
            blocks_by_id[dependency_id].append(review["id"])

    specified_index = MATURITY_ORDER.index("specified")
    derived: list[dict[str, Any]] = []
    for review in reviews:
        dependencies_ready = all(
            reviews_by_id[dependency_id]["status"] == "present"
            and MATURITY_ORDER.index(reviews_by_id[dependency_id]["maturity"])
            >= specified_index
            for dependency_id in review["depends_on"]
        )
        derived.append(
            {
                **review,
                "blocks": sorted(blocks_by_id[review["id"]]),
                "readiness": "ready" if dependencies_ready else "blocked",
            }
        )
    return derived


def _validate_schema(payload: Mapping[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(payload),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if not errors:
        return
    details = []
    for error in errors:
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path
        )
        details.append(f"{path}: {error.message}")
    raise ValueError("review-data.json does not match review-data.schema.json:\n" + "\n".join(details))


def _unique_ids(items: Sequence[Mapping[str, Any]], label: str) -> set[Any]:
    identifiers = [item["id"] for item in items]
    duplicates = sorted(item_id for item_id, count in Counter(identifiers).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate {label} ids: {', '.join(map(str, duplicates))}")
    return set(identifiers)


def _validate_dependency_graph(
    items: Sequence[Mapping[str, Any]], valid_ids: set[Any], label: str
) -> None:
    graph = {item["id"]: tuple(item.get("depends_on", ())) for item in items}
    for item_id, dependencies in graph.items():
        if item_id in dependencies:
            raise ValueError(f"{label.title()} {item_id!r} cannot depend on itself")
        unknown = sorted(set(dependencies) - valid_ids)
        if unknown:
            raise ValueError(
                f"{label.title()} {item_id!r} references unknown dependencies: "
                f"{', '.join(map(str, unknown))}"
            )

    dependent_ids: dict[Any, list[Any]] = {item_id: [] for item_id in graph}
    remaining_dependencies = {
        item_id: len(dependencies) for item_id, dependencies in graph.items()
    }
    for item_id, dependencies in graph.items():
        for dependency in dependencies:
            dependent_ids[dependency].append(item_id)

    ready = deque(
        sorted(item_id for item_id, count in remaining_dependencies.items() if count == 0)
    )
    visited_count = 0
    while ready:
        item_id = ready.popleft()
        visited_count += 1
        for dependent_id in sorted(dependent_ids[item_id]):
            remaining_dependencies[dependent_id] -= 1
            if remaining_dependencies[dependent_id] == 0:
                ready.append(dependent_id)

    if visited_count != len(graph):
        cyclic_ids = sorted(
            item_id for item_id, count in remaining_dependencies.items() if count > 0
        )
        raise ValueError(
            f"{label.title()} dependency graph is cyclic; unresolved nodes: "
            + ", ".join(map(str, cyclic_ids))
        )


def _validate_maturity_evidence(
    review_id: int, maturity: str, evidence: list[dict[str, str]]
) -> None:
    evidence_kinds = {item["kind"] for item in evidence}
    if maturity not in {"proposal", "specified", "machine_validated"}:
        raise ValueError(
            f"Review #{review_id} maturity {maturity!r} is not supported until "
            "authoritative evidence resolvers are configured"
        )
    if maturity == "specified" and "rfc_anchor" not in evidence_kinds:
        raise ValueError(f"Review #{review_id} maturity {maturity!r} requires rfc_anchor evidence")
    if maturity == "machine_validated":
        binding = MACHINE_VALIDATED_REVIEW_BINDINGS.get(review_id)
        if binding is None:
            raise ValueError(
                f"Review #{review_id} has no authoritative machine-validation binding"
            )
        evidence_refs = {
            kind: {item["ref"] for item in evidence if item["kind"] == kind}
            for kind in {item["kind"] for item in evidence} | set(binding)
        }
        if review_id in EXACT_MACHINE_VALIDATED_REVIEW_IDS:
            expected = {kind: set(refs) for kind, refs in binding.items()}
            actual = {kind: refs for kind, refs in evidence_refs.items() if refs}
            if actual != expected:
                raise ValueError(
                    f"Review #{review_id} maturity {maturity!r} does not match "
                    "its exact authoritative evidence binding"
                )
        missing = {
            kind: sorted(required_refs - evidence_refs[kind])
            for kind, required_refs in binding.items()
            if required_refs - evidence_refs[kind]
        }
        if missing:
            details = "; ".join(
                f"{kind}: {', '.join(refs)}" for kind, refs in sorted(missing.items())
            )
            raise ValueError(
                f"Review #{review_id} maturity {maturity!r} is missing bound evidence: "
                + details
            )


def _resolve_repository_evidence_file(review_id: int, kind: str, ref: str) -> Path:
    """Resolve one evidence ref without permitting paths outside the repository."""

    relative_path = Path(ref)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(
            f"Review #{review_id} {kind} evidence ref must be repository-relative "
            f"and must not contain '..': {ref!r}"
        )
    try:
        resolved_path = (REPO_ROOT / relative_path).resolve(strict=True)
        resolved_path.relative_to(REPO_ROOT)
    except (FileNotFoundError, OSError, ValueError) as error:
        raise ValueError(
            f"Review #{review_id} {kind} evidence ref does not resolve to a repository file: "
            f"{ref!r}"
        ) from error
    if not resolved_path.is_file():
        raise ValueError(
            f"Review #{review_id} {kind} evidence ref is not a regular file: {ref!r}"
        )
    return resolved_path


def _validate_schema_evidence(review_id: int, ref: str) -> None:
    schema_path = _resolve_repository_evidence_file(review_id, "schema", ref)
    relative_path = schema_path.relative_to(REPO_ROOT)
    is_conformance_schema = (
        schema_path.parent == CONFORMANCE_V1_DIR
        and schema_path.name.endswith(".schema.json")
    )
    is_bound_linter_schema = review_id == 57 and relative_path in LINTER_SCHEMAS
    is_bound_mock_schema = review_id == 58 and relative_path == MOCK_SCHEMA
    if (
        not is_conformance_schema
        and not is_bound_linter_schema
        and not is_bound_mock_schema
    ):
        raise ValueError(
            f"Review #{review_id} schema evidence must reference "
            "conformance/v1/*.schema.json or an exact bound tooling schema: "
            f"{ref!r}"
        )
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, json.JSONDecodeError, SchemaError) as error:
        raise ValueError(
            f"Review #{review_id} schema evidence is not a valid Draft 2020-12 schema: "
            f"{ref!r}"
        ) from error


def _validate_registry_evidence(review_id: int, ref: str) -> None:
    registry_path = _resolve_repository_evidence_file(review_id, "registry", ref)
    relative_path = registry_path.relative_to(REPO_ROOT)
    if review_id == 57 and relative_path == LINTER_REGISTRY:
        _validate_linter_bundle_evidence(review_id, "registry", ref)
        return
    if review_id == 58 and relative_path == MOCK_REGISTRY:
        _validate_mock_bundle_evidence(review_id, "registry", ref)
        return
    if relative_path not in CONFORMANCE_REGISTRIES:
        raise ValueError(
            f"Review #{review_id} registry evidence must reference "
            "conformance/v1/suite.json, conformance/v1/vectors.json, or "
            "conformance/v1/fixtures.json, or conformance/v1/schema-cases.json: "
            f"{ref!r}"
        )

    root_is_first = bool(sys.path) and sys.path[0] == str(REPO_ROOT)
    if not root_is_first:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        conformance_check = importlib.import_module("conformance.check")
        module_path = Path(conformance_check.__file__).resolve()
        expected_module_path = REPO_ROOT / "conformance" / "check.py"
        if module_path != expected_module_path:
            raise ValueError(
                f"loaded non-canonical conformance validator: {module_path}"
            )
        validate_catalog = getattr(conformance_check, "validate_catalog")
        validate_catalog(REPO_ROOT)
    except Exception as error:
        raise ValueError(
            f"Review #{review_id} registry evidence failed canonical catalog validation: "
            f"{ref!r}: {error}"
        ) from error
    finally:
        if not root_is_first:
            sys.path.pop(0)


def _validate_implementation_evidence(review_id: int, ref: str) -> None:
    implementation_path = _resolve_repository_evidence_file(
        review_id, "implementation", ref
    )
    relative_path = implementation_path.relative_to(REPO_ROOT)
    if review_id == 57 and relative_path in LINTER_IMPLEMENTATIONS:
        _validate_linter_bundle_evidence(review_id, "implementation", ref)
        return
    if review_id == 58 and relative_path in MOCK_IMPLEMENTATIONS:
        _validate_mock_bundle_evidence(review_id, "implementation", ref)
        return
    if review_id == 61 and relative_path in CAPACITY_RECOVERY_IMPLEMENTATIONS:
        _validate_mock_bundle_evidence(review_id, "implementation", ref)
        return
    if review_id == 62 and relative_path in HTTP_CAPACITY_IMPLEMENTATIONS:
        _validate_mock_bundle_evidence(review_id, "implementation", ref)
        return
    if review_id == 27 and relative_path in ASP_OVER_AHP_IMPLEMENTATIONS:
        _validate_mock_bundle_evidence(review_id, "implementation", ref)
        return
    raise ValueError(
        f"Review #{review_id} implementation evidence must reference an exact "
        f"bound tooling entry point: {ref!r}"
    )


def _validate_linter_bundle_evidence(review_id: int, kind: str, ref: str) -> None:
    try:
        _run_linter_self_check()
    except Exception as error:
        raise ValueError(
            f"Review #{review_id} {kind} evidence failed canonical Rust linter "
            f"self-check: {ref!r}: {error}"
        ) from error


@lru_cache(maxsize=1)
def _run_linter_self_check() -> None:
    cargo_command = _cargo_command()
    environment = dict(os.environ)
    environment["CARGO_TERM_COLOR"] = "never"
    process = subprocess.run(
        [
            *cargo_command,
            "run",
            "--quiet",
            "--locked",
            "-p",
            "asp-manifest-linter",
            "--",
            "self-check",
            "--root",
            str(REPO_ROOT),
        ],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if process.returncode != 0:
        details = process.stderr.strip() or process.stdout.strip() or "unknown error"
        raise ValueError(f"cargo self-check exited {process.returncode}: {details}")


def _cargo_command() -> list[str]:
    override = os.environ.get("CARGO")
    if override is not None:
        command = shlex.split(override)
        if not command:
            raise ValueError("CARGO override is empty")
        return command
    cargo = shutil.which("cargo")
    if cargo is None:
        raise ValueError("cargo is unavailable")
    return [cargo]


def _validate_mock_bundle_evidence(review_id: int, kind: str, ref: str) -> None:
    root_is_first = bool(sys.path) and sys.path[0] == str(REPO_ROOT)
    if not root_is_first:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        mock_check = importlib.import_module("mocks.check")
        module_path = Path(mock_check.__file__).resolve()
        expected_module_path = REPO_ROOT / "mocks" / "check.py"
        if module_path != expected_module_path:
            raise ValueError(f"loaded non-canonical mock validator: {module_path}")
        validate_bundle = getattr(mock_check, "validate_bundle")
        validate_bundle(REPO_ROOT)
    except Exception as error:
        raise ValueError(
            f"Review #{review_id} {kind} evidence failed canonical mock bundle "
            f"validation: {ref!r}: {error}"
        ) from error
    finally:
        if not root_is_first:
            sys.path.pop(0)
