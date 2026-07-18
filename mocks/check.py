#!/usr/bin/env python3
"""Validate the closed ASP Mock App / Mock Runtime bundle."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

try:
    from .behavior import AA, AE, GI, RM, RP, SP, FEATURE_INVENTORY
except ImportError:  # direct executable
    from behavior import AA, AE, GI, RM, RP, SP, FEATURE_INVENTORY


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = Path("mocks/v1/manifest.json")
SCHEMA_PATH = Path("mocks/v1/manifest.schema.json")
ARTIFACT_PATHS = (
    "mocks/README.md",
    "mocks/__init__.py",
    "mocks/adapter.py",
    "mocks/behavior.py",
    "mocks/check.py",
    "mocks/mock_app.py",
    "mocks/mock_runtime.py",
    "mocks/participant.py",
    "mocks/probe.py",
    "mocks/state.py",
    "mocks/tests/test_mocks.py",
    "mocks/v1/manifest.schema.json",
)
ENTRYPOINTS = {
    "mock_app": "mocks/mock_app.py",
    "mock_runtime": "mocks/mock_runtime.py",
    "adapter": "mocks/adapter.py",
    "probe": "mocks/probe.py",
    "validator": "mocks/check.py",
}
FAMILY_ROLES = {
    "app": [
        {"boundary_id": "mock-app/surface", "profile_id": SP},
        {"boundary_id": "mock-app/grant", "profile_id": GI},
        {"boundary_id": "mock-app/action", "profile_id": AE},
        {
            "boundary_id": "mock-app/receipt",
            "profile_id": RP,
            "producer_role": "application",
        },
    ],
    "runtime": [
        {"boundary_id": "mock-runtime/mediator", "profile_id": RM},
        {"boundary_id": "mock-runtime/adapter", "profile_id": AA},
        {
            "boundary_id": "mock-runtime/receipt",
            "profile_id": RP,
            "producer_role": "runtime",
        },
    ],
}


class BundleError(ValueError):
    """Raised when the mock bundle is stale, incomplete, or inconsistent."""


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise BundleError(f"duplicate JSON member {key!r}")
        value[key] = item
    return value


def _number(_: str) -> None:
    raise BundleError("floating-point JSON values are forbidden")


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs,
            parse_float=_number,
            parse_constant=_number,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BundleError(f"cannot load {path}") from error
    if not isinstance(value, dict):
        raise BundleError(f"{path} must contain an object")
    return value


def _digest(path: Path) -> str:
    raw = hashlib.sha256(path.read_bytes()).digest()
    return "sha-256:" + base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def validate_bundle(root: Path | None = None) -> dict[str, Any]:
    """Validate manifest shape, semantic closure, modes, and raw-byte digests."""

    repository = (root or ROOT).resolve()
    manifest = _load(repository / MANIFEST_PATH)
    schema = _load(repository / SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise BundleError("mock manifest schema is invalid") from error
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        raise BundleError("mock manifest schema validation failed: " + errors[0].message)
    if manifest["claim_effect"] != "suite_fixture_only":
        raise BundleError("mock bundle must remain suite_fixture_only")
    if manifest["entrypoints"] != ENTRYPOINTS:
        raise BundleError("mock entrypoint closure differs from the canonical bundle")
    families = {item["family_id"]: item for item in manifest["families"]}
    if set(families) != set(FAMILY_ROLES):
        raise BundleError("mock family set is incomplete")
    expected_participants = {
        "app": "asp-reference-mock-app",
        "runtime": "asp-reference-mock-runtime",
    }
    boundaries: set[str] = set()
    for family_id, roles in FAMILY_ROLES.items():
        family = families[family_id]
        if family["participant_id"] != expected_participants[family_id]:
            raise BundleError(f"mock {family_id} participant binding is invalid")
        if family["roles"] != roles:
            raise BundleError(f"mock {family_id} role/boundary closure is invalid")
        for role in roles:
            boundary = role["boundary_id"]
            if boundary in boundaries:
                raise BundleError("mock role boundaries must be unique")
            boundaries.add(boundary)
    feature_inventory = {
        item["profile_id"]: item["feature_ids"]
        for item in manifest["feature_inventory"]
    }
    expected_features = {
        profile_id: list(feature_ids)
        for profile_id, feature_ids in FEATURE_INVENTORY.items()
    }
    if any(
        feature_ids != sorted(feature_ids)
        for feature_ids in expected_features.values()
    ):
        raise BundleError("mock behavior feature inventory is not canonical")
    if feature_inventory != expected_features or len(feature_inventory) != len(
        manifest["feature_inventory"]
    ):
        raise BundleError("mock feature inventory differs from behavior capabilities")
    artifacts = manifest["artifacts"]
    if [item["path"] for item in artifacts] != list(ARTIFACT_PATHS):
        raise BundleError("mock artifacts must be the exact canonical sorted set")
    for item in artifacts:
        relative = Path(item["path"])
        path = (repository / relative).resolve()
        try:
            path.relative_to(repository)
        except ValueError as error:
            raise BundleError(f"mock artifact escapes repository: {relative}") from error
        if path.is_symlink() or not path.is_file():
            raise BundleError(f"mock artifact is not a regular file: {relative}")
        if _digest(path) != item["sha256"]:
            raise BundleError(f"mock artifact digest is stale: {relative}")
    for relative in ENTRYPOINTS.values():
        path = repository / relative
        if not os.access(path, os.X_OK):
            raise BundleError(f"mock entrypoint is not executable: {relative}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",), nargs="?", default="validate")
    parser.parse_args(argv)
    try:
        manifest = validate_bundle()
    except BundleError as error:
        print(f"mock bundle invalid: {error}", file=sys.stderr)
        return 1
    role_count = sum(len(item["roles"]) for item in manifest["families"])
    print(
        f"mock bundle valid: {len(manifest['families'])} families, "
        f"{role_count} atomic roles, {len(manifest['artifacts'])} artifacts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
