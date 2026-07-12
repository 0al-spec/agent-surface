"""Validation and derived planning state for RFC review metadata."""

from __future__ import annotations

import json
from collections import Counter, deque
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REVIEW_DIR = Path(__file__).resolve().parent
DATA_PATH = REVIEW_DIR / "review-data.json"
SCHEMA_PATH = REVIEW_DIR / "review-data.schema.json"
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
) -> None:
    """Validate the JSON shape and cross-object planning invariants."""

    _validate_schema(payload)
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
            if item["kind"] != "rfc_anchor":
                raise ValueError(
                    f"Review #{review_id} evidence kind {item['kind']!r} is not supported "
                    "until an authoritative resolver is configured"
                )
            ref = item["ref"]
            if ref not in actual_anchor_ids:
                raise ValueError(f"Review #{review_id} evidence references unknown RFC anchor: {ref}")
            if ref not in review_anchor_ids:
                raise ValueError(
                    f"Review #{review_id} RFC evidence {ref!r} must also be declared in anchors"
                )

        maturity = review.get("maturity")
        if maturity is not None:
            if review["status"] in {"partial", "missing"} and maturity != "proposal":
                raise ValueError(
                    f"Review #{review_id} status {review['status']!r} cannot exceed proposal maturity"
                )
            _validate_maturity_evidence(review_id, maturity, evidence_kinds)


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
    review_id: int, maturity: str, evidence_kinds: set[str]
) -> None:
    if maturity not in {"proposal", "specified"}:
        raise ValueError(
            f"Review #{review_id} maturity {maturity!r} is not supported until "
            "authoritative evidence resolvers are configured"
        )
    if maturity == "specified" and "rfc_anchor" not in evidence_kinds:
        raise ValueError(f"Review #{review_id} maturity {maturity!r} requires rfc_anchor evidence")
