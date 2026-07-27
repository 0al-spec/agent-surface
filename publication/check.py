#!/usr/bin/env python3
"""Validate the ASP specification publication contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = Path("publication/document-set.json")
SCHEMA_PATH = Path("publication/document-set.schema.json")

ROLE_DEPENDENCIES = {
    "monolith": frozenset(),
    "core": frozenset(),
    "authorization": frozenset({"core"}),
    "safe_effects": frozenset({"core", "authorization"}),
    "evidence": frozenset({"core", "authorization", "safe_effects"}),
    "privacy": frozenset({"core", "authorization", "safe_effects", "evidence"}),
    "binding": frozenset(
        {"core", "authorization", "safe_effects", "evidence", "privacy"}
    ),
    "conformance": frozenset(
        {
            "core",
            "authorization",
            "safe_effects",
            "evidence",
            "privacy",
            "binding",
        }
    ),
}

ROLE_REQUIRED_DEPENDENCIES = {
    "monolith": frozenset(),
    "core": frozenset(),
    "authorization": frozenset({"core"}),
    "safe_effects": frozenset({"core", "authorization"}),
    "evidence": frozenset({"core"}),
    "privacy": frozenset({"core"}),
    "binding": frozenset({"core"}),
    "conformance": frozenset({"core"}),
}

KIND_ROLES = {
    "monolith": frozenset({"monolith"}),
    "core": frozenset({"core"}),
    "extension": frozenset(
        {"authorization", "safe_effects", "evidence", "privacy"}
    ),
    "binding": frozenset({"binding"}),
    "conformance": frozenset({"conformance"}),
}

EXPLICIT_ANCHOR_LINE = re.compile(r'^<a id="([^"]+)"></a>$')
HEADING_LINE = re.compile(r"^#{1,6} (?P<title>.+?)\s*$")
ANCHOR_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PublicationError(ValueError):
    """The publication catalog is structurally or semantically invalid."""


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PublicationError(f"duplicate JSON object member: {key!r}")
        result[key] = value
    return result


def loads_strict_json(text: str, *, source: str) -> Any:
    """Load JSON while rejecting duplicate object members."""

    try:
        return json.loads(text, object_pairs_hook=_strict_object)
    except PublicationError:
        raise
    except json.JSONDecodeError as error:
        raise PublicationError(f"{source} is not valid JSON: {error}") from error


def _load_json(path: Path) -> Any:
    try:
        return loads_strict_json(path.read_text(encoding="utf-8"), source=str(path))
    except OSError as error:
        raise PublicationError(f"cannot read {path}: {error}") from error


def _schema_error_path(error: Any) -> str:
    location = ".".join(str(part) for part in error.absolute_path)
    return location or "<root>"


def _validate_schema(catalog: Any, schema: Any) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise PublicationError(f"document-set schema is invalid: {error.message}") from error

    errors = sorted(
        Draft202012Validator(
            schema, format_checker=FormatChecker()
        ).iter_errors(catalog),
        key=lambda item: (tuple(str(part) for part in item.absolute_path), item.message),
    )
    if errors:
        first = errors[0]
        raise PublicationError(
            f"document-set schema violation at {_schema_error_path(first)}: "
            f"{first.message}"
        )


def _repo_file(root: Path, value: str, *, label: str, must_exist: bool) -> Path:
    if "\\" in value:
        raise PublicationError(f"{label} must use repository-relative POSIX syntax")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise PublicationError(
            f"{label} must be a normalized repository-relative path: {value!r}"
        )
    if path.as_posix() != value:
        raise PublicationError(
            f"{label} must use canonical repository-relative syntax: {value!r}"
        )

    root = root.resolve(strict=True)
    candidate = root / Path(*path.parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise PublicationError(f"{label} escapes the repository: {value!r}") from error

    if must_exist and not resolved.is_file():
        raise PublicationError(f"{label} does not resolve to a regular file: {value!r}")
    if not must_exist and os.path.lexists(candidate):
        raise PublicationError(
            f"{label} is reserved but already exists; activate it atomically "
            f"or remove the stale reservation: {value!r}"
        )
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ref(document: Mapping[str, Any]) -> tuple[str, str]:
    return document["document_id"], document["version"]


def _index_documents(
    documents: Sequence[Mapping[str, Any]], *, label: str
) -> dict[tuple[str, str], Mapping[str, Any]]:
    by_ref: dict[tuple[str, str], Mapping[str, Any]] = {}
    ids: set[str] = set()
    paths: set[str] = set()
    expected_order = list(range(len(documents)))
    actual_order = [document["publication_order"] for document in documents]
    if actual_order != expected_order:
        raise PublicationError(
            f"{label} publication_order must be the canonical contiguous order "
            f"{expected_order!r}, got {actual_order!r}"
        )

    for document in documents:
        document_ref = _ref(document)
        if document_ref in by_ref:
            raise PublicationError(f"duplicate {label} document reference: {document_ref!r}")
        if document["document_id"] in ids:
            raise PublicationError(
                f"{label} selects more than one version of document "
                f"{document['document_id']!r}"
            )
        path_key = document.get("source_path", document.get("target_source_path"))
        if path_key in paths:
            raise PublicationError(f"duplicate {label} source path: {path_key!r}")
        ids.add(document["document_id"])
        paths.add(path_key)
        by_ref[document_ref] = document

        allowed_roles = KIND_ROLES[document["kind"]]
        if document["role"] not in allowed_roles:
            raise PublicationError(
                f"{label} document {document['document_id']!r} kind "
                f"{document['kind']!r} cannot have role {document['role']!r}"
            )
    return by_ref


def _validate_dependency_graph(
    documents: Sequence[Mapping[str, Any]],
    by_ref: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    label: str,
) -> None:
    indegree = {_ref(document): 0 for document in documents}
    dependents: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)

    for document in documents:
        current_ref = _ref(document)
        current_order = document["publication_order"]
        allowed_roles = ROLE_DEPENDENCIES[document["role"]]
        required_roles = ROLE_REQUIRED_DEPENDENCIES[document["role"]]
        seen: set[tuple[str, str]] = set()
        selected_roles: set[str] = set()
        for dependency in document["normative_dependencies"]:
            dependency_ref = _ref(dependency)
            if dependency_ref in seen:
                raise PublicationError(
                    f"{label} document {current_ref!r} repeats dependency "
                    f"{dependency_ref!r}"
                )
            seen.add(dependency_ref)
            if dependency_ref == current_ref:
                raise PublicationError(f"{label} document {current_ref!r} depends on itself")
            target = by_ref.get(dependency_ref)
            if target is None:
                raise PublicationError(
                    f"{label} document {current_ref!r} has an unknown or unpinned "
                    f"dependency {dependency_ref!r}"
                )
            if target["role"] not in allowed_roles:
                raise PublicationError(
                    f"{label} role {document['role']!r} cannot depend normatively "
                    f"on role {target['role']!r}"
                )
            selected_roles.add(target["role"])
            if target["publication_order"] >= current_order:
                raise PublicationError(
                    f"{label} dependency {dependency_ref!r} must precede "
                    f"{current_ref!r} in publication_order"
                )
            indegree[current_ref] += 1
            dependents[dependency_ref].append(current_ref)
        missing_roles = sorted(required_roles - selected_roles)
        if missing_roles:
            raise PublicationError(
                f"{label} role {document['role']!r} is missing required normative "
                f"dependencies on roles: {', '.join(missing_roles)}"
            )

    ready = deque(ref for ref, count in indegree.items() if count == 0)
    visited = 0
    while ready:
        current = ready.popleft()
        visited += 1
        for dependent in dependents[current]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if visited != len(documents):
        cyclic = sorted(ref for ref, count in indegree.items() if count)
        raise PublicationError(f"{label} normative dependency graph is cyclic: {cyclic!r}")


def _validate_exports(
    documents: Sequence[Mapping[str, Any]], *, field: str, label: str
) -> None:
    owners: dict[tuple[str, str], tuple[str, str]] = {}
    for document in documents:
        for exported in document[field]:
            export_ref = exported["kind"], exported["id"]
            owner = _ref(document)
            previous = owners.get(export_ref)
            if previous is not None:
                raise PublicationError(
                    f"{label} export {export_ref!r} has multiple owners: "
                    f"{previous!r} and {owner!r}"
                )
            owners[export_ref] = owner


def _validate_active_source_exports(
    documents: Sequence[Mapping[str, Any]],
) -> None:
    for document in documents:
        exports = {(item["kind"], item["id"]) for item in document["exports"]}
        source_export = ("artifact", document["source_path"])
        if source_export not in exports:
            raise PublicationError(
                f"active document {_ref(document)!r} does not own its canonical "
                f"source artifact {document['source_path']!r}"
            )


def _explicit_anchors(source_path: Path) -> dict[str, str]:
    lines = source_path.read_text(encoding="utf-8").splitlines()
    anchors: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.startswith("<a id="):
            index += 1
            continue

        pending: list[str] = []
        while index < len(lines) and lines[index].startswith("<a id="):
            match = EXPLICIT_ANCHOR_LINE.fullmatch(lines[index])
            if match is None or ANCHOR_ID.fullmatch(match.group(1)) is None:
                raise PublicationError(
                    f"malformed explicit anchor in {source_path}: "
                    f"{lines[index]!r}"
                )
            pending.append(match.group(1))
            index += 1
        if index >= len(lines):
            raise PublicationError(
                f"explicit anchor in {source_path} is not followed by a heading"
            )
        heading = HEADING_LINE.fullmatch(lines[index])
        if heading is None:
            raise PublicationError(
                f"explicit anchor in {source_path} must appear immediately before "
                "its heading"
            )
        title = heading.group("title")
        for anchor_id in pending:
            if anchor_id in anchors:
                raise PublicationError(
                    f"duplicate explicit anchor {anchor_id!r} in {source_path}"
                )
            anchors[anchor_id] = title
        index += 1
    return anchors


def _declared_anchor_map(document: Mapping[str, Any]) -> dict[str, str]:
    declared: dict[str, str] = {}
    for anchor in document["public_anchors"]:
        for anchor_id in (anchor["anchor_id"], *anchor["aliases"]):
            if anchor_id in declared:
                raise PublicationError(
                    f"document {_ref(document)!r} repeats public anchor or alias "
                    f"{anchor_id!r}"
                )
            declared[anchor_id] = anchor["heading"]
    return declared


def _validate_public_anchors(
    root: Path, documents: Sequence[Mapping[str, Any]]
) -> None:
    global_owners: dict[str, tuple[str, str]] = {}
    for document in documents:
        source_path = _repo_file(
            root,
            document["source_path"],
            label=f"active document {_ref(document)!r} source_path",
            must_exist=True,
        )
        actual = _explicit_anchors(source_path)
        declared = _declared_anchor_map(document)
        if actual != declared:
            missing = sorted(set(declared) - set(actual))
            undeclared = sorted(set(actual) - set(declared))
            mismatched = sorted(
                anchor_id
                for anchor_id in set(actual) & set(declared)
                if actual[anchor_id] != declared[anchor_id]
            )
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if undeclared:
                details.append("undeclared: " + ", ".join(undeclared))
            if mismatched:
                details.append("heading mismatch: " + ", ".join(mismatched))
            raise PublicationError(
                f"active document {_ref(document)!r} public anchor inventory "
                f"does not match its source ({'; '.join(details)})"
            )
        for anchor_id in declared:
            previous = global_owners.get(anchor_id)
            if previous is not None:
                raise PublicationError(
                    f"public anchor {anchor_id!r} has multiple active owners: "
                    f"{previous!r} and {_ref(document)!r}"
                )
            global_owners[anchor_id] = _ref(document)


def _validate_normative_references(
    documents: Sequence[Mapping[str, Any]],
    active_by_ref: Mapping[tuple[str, str], Mapping[str, Any]],
) -> None:
    for document in documents:
        dependency_refs = {
            _ref(dependency) for dependency in document["normative_dependencies"]
        }
        referenced_targets: set[tuple[str, str]] = set()
        source_anchors = _declared_anchor_map(document)
        for reference in document["normative_references"]:
            source_anchor = reference["source_anchor_id"]
            if source_anchor not in source_anchors:
                raise PublicationError(
                    f"normative reference in {_ref(document)!r} uses undeclared "
                    f"source anchor {source_anchor!r}"
                )
            target_ref = _ref(reference["target_document"])
            if target_ref not in dependency_refs:
                raise PublicationError(
                    f"normative reference from {_ref(document)!r} to {target_ref!r} "
                    "has no exact dependency edge"
                )
            target = active_by_ref.get(target_ref)
            if target is None:
                raise PublicationError(
                    f"normative reference targets inactive document {target_ref!r}"
                )
            referenced_targets.add(target_ref)
            target_kind = reference["target_kind"]
            target_id = reference["target_id"]
            if target_kind == "anchor":
                if target_id not in _declared_anchor_map(target):
                    raise PublicationError(
                        f"normative reference target anchor {target_id!r} is not "
                        f"exported by {target_ref!r}"
                    )
            else:
                target_exports = {
                    (item["kind"], item["id"]) for item in target["exports"]
                }
                if (target_kind, target_id) not in target_exports:
                    raise PublicationError(
                        f"normative reference target {(target_kind, target_id)!r} "
                        f"is not exported by {target_ref!r}"
                    )
        if referenced_targets != dependency_refs:
            missing = sorted(dependency_refs - referenced_targets)
            raise PublicationError(
                f"active document {_ref(document)!r} dependency edges lack "
                f"normative reference records: {missing!r}"
            )


def _validate_registries(
    root: Path,
    registries: Sequence[Mapping[str, Any]],
    active_by_ref: Mapping[tuple[str, str], Mapping[str, Any]],
) -> None:
    ids: set[str] = set()
    paths: set[str] = set()
    resolved_paths: set[Path] = set()
    for registry in registries:
        registry_id = registry["registry_id"]
        if registry_id in ids:
            raise PublicationError(f"duplicate registry id: {registry_id!r}")
        if registry["source_path"] in paths:
            raise PublicationError(
                f"duplicate registry source path: {registry['source_path']!r}"
            )
        ids.add(registry_id)
        paths.add(registry["source_path"])
        registry_path = _repo_file(
            root,
            registry["source_path"],
            label=f"registry {registry_id!r} source_path",
            must_exist=True,
        )
        if registry_path in resolved_paths:
            raise PublicationError(
                f"registry {registry_id!r} resolves to a duplicate source file: "
                f"{registry['source_path']!r}"
            )
        resolved_paths.add(registry_path)
        registry_document = _load_json(registry_path)
        if not isinstance(registry_document, dict):
            raise PublicationError(
                f"registry {registry_id!r} source must contain a JSON object"
            )
        actual_id = registry_document.get(registry["id_member"])
        if actual_id != registry_id:
            raise PublicationError(
                f"registry {registry_id!r} source member {registry['id_member']!r} "
                f"does not match the catalog: {actual_id!r}"
            )
        actual_version = registry_document.get(registry["version_member"])
        if actual_version != registry["version"]:
            raise PublicationError(
                f"registry {registry_id!r} source member "
                f"{registry['version_member']!r} does not match catalog version "
                f"{registry['version']!r}: {actual_version!r}"
            )
        actual_digest = _sha256(registry_path)
        if actual_digest != registry["source_sha256"]:
            raise PublicationError(
                f"registry {registry_id!r} source digest does not match the "
                f"catalog: expected {registry['source_sha256']}, got {actual_digest}"
            )

        owner_ref = _ref(registry["owner"])
        owner = active_by_ref.get(owner_ref)
        if owner is None:
            raise PublicationError(
                f"registry {registry_id!r} owner is not an active exact document: "
                f"{owner_ref!r}"
            )
        owner_exports = {(item["kind"], item["id"]) for item in owner["exports"]}
        if ("registry", registry_id) not in owner_exports:
            raise PublicationError(
                f"registry {registry_id!r} is not declared by its owner {owner_ref!r}"
            )
    exported_registry_ids = {
        item["id"]
        for document in active_by_ref.values()
        for item in document["exports"]
        if item["kind"] == "registry"
    }
    if exported_registry_ids != ids:
        orphaned = sorted(exported_registry_ids - ids)
        unexported = sorted(ids - exported_registry_ids)
        raise PublicationError(
            "active registry exports and catalog entries differ"
            + (f"; orphan exports: {', '.join(orphaned)}" if orphaned else "")
            + (f"; unexported entries: {', '.join(unexported)}" if unexported else "")
        )


def _validate_mode(
    root: Path,
    catalog: Mapping[str, Any],
    active_by_ref: Mapping[tuple[str, str], Mapping[str, Any]],
) -> None:
    documents = catalog["documents"]
    aggregate = catalog["aggregate"]
    aggregate_path = _repo_file(
        root,
        aggregate["path"],
        label="aggregate path",
        must_exist=True,
    )
    aggregate_digest = _sha256(aggregate_path)
    if aggregate_digest != aggregate["sha256"]:
        raise PublicationError(
            "aggregate digest does not match the catalog: "
            f"expected {aggregate['sha256']}, got {aggregate_digest}"
        )

    if catalog["publication_mode"] == "modular":
        raise PublicationError(
            "modular publication mode is unsupported until the Hyperprompt "
            "provenance, source-map, anchor, and atomic-readiness resolver is "
            "implemented"
        )

    if catalog["publication_mode"] == "transitional_monolith":
        if len(documents) != 1 or documents[0]["role"] != "monolith":
            raise PublicationError(
                "transitional_monolith requires exactly one active monolith document"
            )
        source_ref = _ref(aggregate["source_document"])
        source = active_by_ref.get(source_ref)
        if source is None:
            raise PublicationError(
                "transitional aggregate source_document must select the active monolith"
            )
        source_path = _repo_file(
            root,
            source["source_path"],
            label="transitional monolith source_path",
            must_exist=True,
        )
        if aggregate_path != source_path:
            raise PublicationError(
                "transitional aggregate path must be the canonical monolith source_path"
            )
        return


def validate_catalog(
    root: Path = ROOT, catalog_path: Path | None = None
) -> dict[str, Any]:
    """Validate and return the canonical publication catalog."""

    root = root.resolve(strict=True)
    if catalog_path is None:
        catalog_file = _repo_file(
            root,
            CATALOG_PATH.as_posix(),
            label="catalog path",
            must_exist=True,
        )
    else:
        catalog_file = catalog_path.resolve(strict=True)
        try:
            catalog_file.relative_to(root)
        except ValueError as error:
            raise PublicationError(
                f"catalog path escapes the repository: {catalog_path}"
            ) from error
        if not catalog_file.is_file():
            raise PublicationError(
                f"catalog path does not resolve to a regular file: {catalog_path}"
            )
    schema_file = _repo_file(
        root,
        SCHEMA_PATH.as_posix(),
        label="schema path",
        must_exist=True,
    )
    catalog = _load_json(catalog_file)
    schema = _load_json(schema_file)
    _validate_schema(catalog, schema)
    if not isinstance(catalog, dict):
        raise PublicationError("document-set catalog must be a JSON object")

    active = catalog["documents"]
    reserved = catalog["reserved_documents"]
    active_by_ref = _index_documents(active, label="active")
    reserved_by_ref = _index_documents(reserved, label="reserved")
    overlapping_ids = {
        document["document_id"] for document in active
    } & {document["document_id"] for document in reserved}
    if overlapping_ids:
        raise PublicationError(
            "active and reserved document ids overlap: "
            + ", ".join(sorted(overlapping_ids))
        )

    resolved_source_paths: set[Path] = set()
    for document in active:
        source_path = _repo_file(
            root,
            document["source_path"],
            label=f"active document {_ref(document)!r} source_path",
            must_exist=True,
        )
        if source_path in resolved_source_paths:
            raise PublicationError(
                f"active document {_ref(document)!r} resolves to a duplicate "
                f"canonical source: {document['source_path']!r}"
            )
        resolved_source_paths.add(source_path)
        actual_digest = _sha256(source_path)
        if actual_digest != document["source_sha256"]:
            raise PublicationError(
                f"active document {_ref(document)!r} source digest does not match "
                f"the catalog: expected {document['source_sha256']}, "
                f"got {actual_digest}"
            )
    resolved_target_paths: set[Path] = set()
    for document in reserved:
        target_path = _repo_file(
            root,
            document["target_source_path"],
            label=f"reserved document {_ref(document)!r} target_source_path",
            must_exist=False,
        )
        if target_path in resolved_target_paths:
            raise PublicationError(
                f"reserved document {_ref(document)!r} resolves to a duplicate "
                f"target source: {document['target_source_path']!r}"
            )
        resolved_target_paths.add(target_path)

    _validate_dependency_graph(active, active_by_ref, label="active")
    _validate_dependency_graph(reserved, reserved_by_ref, label="reserved")
    _validate_exports(active, field="exports", label="active")
    _validate_exports(reserved, field="planned_exports", label="reserved")
    _validate_active_source_exports(active)
    _validate_public_anchors(root, active)
    _validate_normative_references(active, active_by_ref)
    _validate_registries(root, catalog["registries"], active_by_ref)
    _validate_mode(root, catalog, active_by_ref)
    return catalog


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root containing publication/ (default: repository root)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        catalog = validate_catalog(args.root)
    except (OSError, PublicationError) as error:
        print(f"publication validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "publication validation passed: "
        f"{len(catalog['documents'])} active document, "
        f"{len(catalog['reserved_documents'])} reserved documents, "
        f"{len(catalog['registries'])} registries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
