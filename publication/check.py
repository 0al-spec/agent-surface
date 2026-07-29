#!/usr/bin/env python3
"""Validate the ASP specification publication contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from html.parser import HTMLParser
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

RAW_HTML_ANCHOR = re.compile(r"<a(?=[\s/>]|$)", re.IGNORECASE)
CLOSING_HTML_ANCHOR = re.compile(r"</\s*a\s*>\s*$", re.IGNORECASE)
HEADING_LINE = re.compile(r"^#{1,6} (?P<title>.+?)\s*$")
ANCHOR_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PublicationError(ValueError):
    """The publication catalog is structurally or semantically invalid."""


class _ExplicitAnchorParser(HTMLParser):
    """Collect the exact structure of one raw HTML anchor line."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[tuple[str, str]] = []
        self.attributes: list[tuple[str, str | None]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.events.append(("start", tag))
        if tag == "a":
            self.attributes = attrs

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        self.events.append(("startend", tag))

    def handle_endtag(self, tag: str) -> None:
        self.events.append(("end", tag))

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.events.append(("data", data))

    def handle_comment(self, data: str) -> None:
        del data
        self.events.append(("comment", ""))

    def handle_decl(self, decl: str) -> None:
        del decl
        self.events.append(("declaration", ""))

    def handle_pi(self, data: str) -> None:
        del data
        self.events.append(("processing-instruction", ""))


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


def _run_git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise PublicationError(f"cannot execute git: {error}") from error


def _run_git_bytes(
    root: Path, *arguments: str
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
        )
    except OSError as error:
        raise PublicationError(f"cannot execute git: {error}") from error


def _historical_repo_path(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or "\\" in value:
        raise PublicationError(
            f"{label} must be a normalized repository-relative POSIX path"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise PublicationError(
            f"{label} must be a normalized repository-relative POSIX path"
        )
    return value


def _historical_blob(
    root: Path,
    revision: str,
    path: Any,
    *,
    label: str,
) -> bytes:
    source_path = _historical_repo_path(path, label=label)
    result = _run_git_bytes(root, "show", f"{revision}:{source_path}")
    if result.returncode != 0:
        raise PublicationError(
            f"{label} {source_path!r} is missing at {revision}"
        )
    return result.stdout


def _validate_historical_catalog_state(
    root: Path,
    revision: str,
    catalog: Mapping[str, Any],
) -> None:
    """Verify that one committed catalog exactly describes its Git tree."""

    blob_cache: dict[str, bytes] = {}

    def artifact(path: Any, *, label: str) -> tuple[str, bytes]:
        source_path = _historical_repo_path(path, label=label)
        if source_path not in blob_cache:
            blob_cache[source_path] = _historical_blob(
                root,
                revision,
                source_path,
                label=label,
            )
        return source_path, blob_cache[source_path]

    def verify_digest(
        path: Any,
        expected: Any,
        *,
        label: str,
    ) -> tuple[str, bytes]:
        if not isinstance(expected, str):
            raise PublicationError(f"{label} digest is invalid at {revision}")
        source_path, content = artifact(path, label=label)
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected:
            raise PublicationError(
                f"{label} digest does not match its Git blob at {revision}: "
                f"expected {expected}, got {actual}"
            )
        return source_path, content

    try:
        documents = catalog["documents"]
        registries = catalog["registries"]
        aggregate = catalog["aggregate"]
        if (
            not isinstance(documents, Sequence)
            or isinstance(documents, (str, bytes))
            or not isinstance(registries, Sequence)
            or isinstance(registries, (str, bytes))
            or not isinstance(aggregate, Mapping)
        ):
            raise TypeError

        active_by_ref: dict[tuple[str, str], Mapping[str, Any]] = {}
        for document in documents:
            if not isinstance(document, Mapping):
                raise TypeError
            document_ref = _ref(document)
            if document_ref in active_by_ref:
                raise PublicationError(
                    f"historical publication catalog at {revision} repeats "
                    f"document reference {document_ref!r}"
                )
            verify_digest(
                document["source_path"],
                document["source_sha256"],
                label=f"historical document {document_ref!r} source",
            )
            active_by_ref[document_ref] = document

        aggregate_path, aggregate_content = verify_digest(
            aggregate["path"],
            aggregate["sha256"],
            label="historical aggregate",
        )
        if catalog.get("publication_mode") == "modular":
            assembly = aggregate.get("assembly")
            if not isinstance(assembly, Mapping):
                raise PublicationError(
                    f"historical modular aggregate at {revision} lacks assembly"
                )
            _, source_map_content = artifact(
                assembly["source_map"],
                label="historical aggregate source map",
            )
            artifact(
                assembly["manifest"],
                label="historical aggregate manifest",
            )
            try:
                source_map = loads_strict_json(
                    source_map_content.decode("utf-8"),
                    source=f"{assembly['source_map']} at {revision}",
                )
            except UnicodeDecodeError as error:
                raise PublicationError(
                    f"historical source map at {revision} is not UTF-8"
                ) from error
            if (
                not isinstance(source_map, Mapping)
                or source_map.get("outputSha256") != aggregate["sha256"]
                or hashlib.sha256(aggregate_content).hexdigest()
                != aggregate["sha256"]
            ):
                raise PublicationError(
                    f"historical modular aggregate provenance is stale at {revision}"
                )
        else:
            source_document_ref = _ref(aggregate["source_document"])
            source_document = active_by_ref.get(source_document_ref)
            if source_document is None:
                raise PublicationError(
                    f"historical aggregate at {revision} references inactive "
                    f"document {source_document_ref!r}"
                )
            if (
                aggregate_path != source_document["source_path"]
                or aggregate["sha256"] != source_document["source_sha256"]
            ):
                raise PublicationError(
                    f"historical aggregate at {revision} is not the exact "
                    f"representation of {source_document_ref!r}"
                )

        for registry in registries:
            if not isinstance(registry, Mapping):
                raise TypeError
            registry_ref = _registry_ref(registry)
            source_path, content = verify_digest(
                registry["source_path"],
                registry["source_sha256"],
                label=f"historical registry {registry_ref!r} source",
            )
            owner_ref = _ref(registry["owner"])
            if owner_ref not in active_by_ref:
                raise PublicationError(
                    f"historical registry {registry_ref!r} at {revision} has "
                    f"inactive owner {owner_ref!r}"
                )
            try:
                registry_document = loads_strict_json(
                    content.decode("utf-8"),
                    source=f"{source_path} at {revision}",
                )
            except UnicodeDecodeError as error:
                raise PublicationError(
                    f"historical registry {source_path!r} at {revision} is not UTF-8"
                ) from error
            if not isinstance(registry_document, Mapping):
                raise PublicationError(
                    f"historical registry {source_path!r} at {revision} "
                    "is not a JSON object"
                )
            if (
                registry_document.get(registry["id_member"]) != registry_ref[0]
                or registry_document.get(registry["version_member"])
                != registry_ref[1]
            ):
                raise PublicationError(
                    f"historical registry {registry_ref!r} identity does not "
                    f"match {source_path!r} at {revision}"
                )
    except (KeyError, TypeError) as error:
        raise PublicationError(
            f"historical publication catalog at {revision} lacks the fields "
            "required to verify its Git tree"
        ) from error


def _historical_catalogs(
    root: Path,
    base_ref: str,
    candidate_ref: str | None = None,
) -> list[tuple[str, Mapping[str, Any]]]:
    shallow = _run_git(root, "rev-parse", "--is-shallow-repository")
    if shallow.returncode != 0 or shallow.stdout.strip() not in {"true", "false"}:
        raise PublicationError("cannot determine whether Git history is shallow")
    if shallow.stdout.strip() == "true":
        raise PublicationError(
            "publication history validation requires a complete Git history"
        )

    verified = _run_git(
        root,
        "rev-parse",
        "--verify",
        "--quiet",
        f"{base_ref}^{{commit}}",
    )
    if verified.returncode != 0:
        raise PublicationError(
            f"cannot resolve publication history base ref {base_ref!r}"
        )

    revision_specs = [base_ref]
    if candidate_ref is not None:
        candidate = _run_git(
            root,
            "rev-parse",
            "--verify",
            "--quiet",
            f"{candidate_ref}^{{commit}}",
        )
        if candidate.returncode != 0:
            raise PublicationError(
                f"cannot resolve publication candidate ref {candidate_ref!r}"
            )
        ancestry = _run_git(
            root,
            "merge-base",
            "--is-ancestor",
            base_ref,
            candidate_ref,
        )
        if ancestry.returncode != 0:
            raise PublicationError(
                f"publication history base {base_ref!r} is not an ancestor of "
                f"candidate {candidate_ref!r}"
            )
        revision_specs.append(f"{base_ref}..{candidate_ref}")

    catalogs: list[tuple[str, Mapping[str, Any]]] = []
    catalog_cache: dict[str, Mapping[str, Any]] = {}
    recorded_blobs: set[str] = set()
    for revision_spec in revision_specs:
        revisions = _run_git(
            root,
            "rev-list",
            "--first-parent",
            "--reverse",
            revision_spec,
        )
        if revisions.returncode != 0:
            raise PublicationError(
                f"cannot enumerate publication catalog history at "
                f"{revision_spec!r}: {revisions.stderr.strip()}"
            )
        for revision in revisions.stdout.splitlines():
            object_name = f"{revision}:{CATALOG_PATH.as_posix()}"
            exists = _run_git(root, "cat-file", "-e", object_name)
            if exists.returncode != 0:
                continue
            blob = _run_git(root, "rev-parse", object_name)
            if blob.returncode != 0:
                raise PublicationError(
                    f"cannot identify historical publication catalog at "
                    f"{revision}: {blob.stderr.strip()}"
                )
            blob_id = blob.stdout.strip()
            catalog = catalog_cache.get(blob_id)
            if catalog is None:
                result = _run_git(root, "show", object_name)
                if result.returncode != 0:
                    raise PublicationError(
                        f"cannot read historical publication catalog at {revision}: "
                        f"{result.stderr.strip()}"
                    )
                loaded = loads_strict_json(
                    result.stdout,
                    source=f"{CATALOG_PATH.as_posix()} at {revision}",
                )
                if not isinstance(loaded, Mapping):
                    raise PublicationError(
                        f"historical publication catalog at {revision} "
                        "is not an object"
                    )
                catalog = loaded
                catalog_cache[blob_id] = catalog
            _validate_historical_catalog_state(root, revision, catalog)
            if blob_id not in recorded_blobs:
                catalogs.append((revision, catalog))
                recorded_blobs.add(blob_id)
    return catalogs


def _registry_ref(registry: Mapping[str, Any]) -> tuple[str, str]:
    try:
        return registry["registry_id"], registry["version"]
    except KeyError as error:
        raise PublicationError(
            f"historical registry lacks {error.args[0]!r}"
        ) from error


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PublicationError(
            f"publication history contains a non-canonical JSON value: {error}"
        ) from error


def validate_catalog_history(
    current: Mapping[str, Any],
    historical: Sequence[tuple[str, Mapping[str, Any]]],
) -> None:
    """Reject reuse of a published version tuple for different content."""

    seen: dict[
        tuple[str, tuple[str, str]],
        tuple[str, bytes],
    ] = {}

    def record(
        kind: str,
        identity: tuple[str, str],
        value: Any,
        revision: str,
        *,
        current_catalog: bool,
    ) -> None:
        key = kind, identity
        encoded = _canonical_json_bytes(value)
        previous = seen.get(key)
        if previous is not None and previous[1] != encoded:
            if current_catalog:
                version_field = {
                    "document": "document version",
                    "registry": "registry version",
                    "document-set": "document_set_version",
                }[kind]
                raise PublicationError(
                    f"published {kind} version {identity!r} changed since "
                    f"{previous[0]}; bump {version_field}"
                )
            raise PublicationError(
                f"published {kind} version {identity!r} conflicts between "
                f"{previous[0]} and {revision}"
            )
        seen.setdefault(key, (revision, encoded))

    def collect(
        catalog: Mapping[str, Any],
        revision: str,
        *,
        current_catalog: bool,
    ) -> None:
        try:
            for document in catalog["documents"]:
                record(
                    "document",
                    _ref(document),
                    document,
                    revision,
                    current_catalog=current_catalog,
                )
            for registry in catalog["registries"]:
                record(
                    "registry",
                    _registry_ref(registry),
                    registry,
                    revision,
                    current_catalog=current_catalog,
                )
            record(
                "document-set",
                (
                    catalog["document_set_id"],
                    catalog["document_set_version"],
                ),
                catalog,
                revision,
                current_catalog=current_catalog,
            )
        except (KeyError, TypeError) as error:
            raise PublicationError(
                f"historical publication catalog at {revision} lacks the "
                "versioned identity fields required for immutability checks"
            ) from error

    for revision, previous in historical:
        collect(previous, revision, current_catalog=False)

    historical_documents: dict[
        tuple[str, str], tuple[str, Mapping[str, Any]]
    ] = {}
    has_transitional_history = False
    for revision, previous in historical:
        has_transitional_history = has_transitional_history or (
            previous.get("publication_mode") == "transitional_monolith"
        )
        for document in previous["documents"]:
            historical_documents.setdefault(_ref(document), (revision, document))
    for relocation in (
        current.get("anchor_relocations", [])
        if has_transitional_history
        else []
    ):
        previous_anchor = relocation["previous"]
        previous_ref = (
            previous_anchor["document_id"],
            previous_anchor["version"],
        )
        historical = historical_documents.get(previous_ref)
        if historical is None:
            raise PublicationError(
                "anchor relocation lacks a published historical source "
                f"document: {previous_ref!r}"
            )
        revision, document = historical
        historical_anchors = _declared_anchor_map(document)
        anchor_id = previous_anchor["anchor_id"]
        if historical_anchors.get(anchor_id) != relocation["heading"]:
            raise PublicationError(
                "anchor relocation historical tuple does not resolve at "
                f"{revision}: {(previous_ref[0], previous_ref[1], anchor_id)!r}"
            )
        expected_aliases = {
            (
                "legacy_aggregate_path_fragment",
                f"{document['source_path']}#{anchor_id}",
            ),
            ("legacy_aggregate_fragment", f"#{anchor_id}"),
        }
        actual_aliases = {
            (item["kind"], item["value"])
            for item in relocation["compatibility_aliases"]
        }
        if actual_aliases != expected_aliases:
            raise PublicationError(
                f"anchor relocation aliases are incomplete for {anchor_id!r}"
            )
    collect(current, "current catalog", current_catalog=True)


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


def _explicit_anchor_id(line: str, source_path: Path, line_number: int) -> str:
    parser = _ExplicitAnchorParser()
    parser.feed(line)
    parser.close()
    if (
        parser.events != [("start", "a"), ("end", "a")]
        or CLOSING_HTML_ANCHOR.search(line) is None
    ):
        raise PublicationError(
            f"malformed explicit anchor in {source_path} at line {line_number}: "
            f"{line!r}"
        )

    ids = [value for name, value in parser.attributes if name == "id"]
    if (
        len(ids) != 1
        or ids[0] is None
        or ANCHOR_ID.fullmatch(ids[0]) is None
    ):
        raise PublicationError(
            f"malformed explicit anchor in {source_path} at line {line_number}: "
            f"{line!r}"
        )
    return ids[0]


def _explicit_anchors(source_path: Path) -> dict[str, str]:
    lines = source_path.read_text(encoding="utf-8").splitlines()
    anchors: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if RAW_HTML_ANCHOR.search(line) is None:
            index += 1
            continue

        pending: list[str] = []
        while index < len(lines) and RAW_HTML_ANCHOR.search(lines[index]):
            pending.append(
                _explicit_anchor_id(lines[index], source_path, index + 1)
            )
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


def _validate_anchor_relocations(
    catalog: Mapping[str, Any],
    active_by_ref: Mapping[tuple[str, str], Mapping[str, Any]],
) -> None:
    relocations = catalog["anchor_relocations"]
    if catalog["publication_mode"] == "transitional_monolith":
        if (
            catalog["anchor_policy"]["move_policy"]
            != "reject_cross_document_move_until_relocation_profile"
            or catalog["anchor_policy"]["cross_document_relocation"]
            != "unsupported_in_schema_v1"
        ):
            raise PublicationError(
                "transitional publication cannot select relocation policy"
            )
        if relocations:
            raise PublicationError(
                "transitional publication cannot activate anchor relocations"
            )
        return
    if not relocations:
        raise PublicationError(
            "modular activation requires explicit anchor relocations"
        )
    if (
        catalog["anchor_policy"]["move_policy"]
        != "validated_cross_document_relocation"
        or catalog["anchor_policy"]["cross_document_relocation"]
        != "exact_old_to_new_tuple_v1"
    ):
        raise PublicationError(
            "modular activation requires the validated relocation policy"
        )
    seen_previous: set[tuple[str, str, str]] = set()
    seen_replacement: set[tuple[str, str, str]] = set()
    seen_aliases: set[tuple[str, str]] = set()
    for relocation in relocations:
        previous = relocation["previous"]
        replacement = relocation["replacement"]
        previous_tuple = (
            previous["document_id"],
            previous["version"],
            previous["anchor_id"],
        )
        replacement_tuple = (
            replacement["document_id"],
            replacement["version"],
            replacement["anchor_id"],
        )
        if previous_tuple in seen_previous:
            raise PublicationError(
                f"duplicate historical anchor relocation: {previous_tuple!r}"
            )
        if replacement_tuple in seen_replacement:
            raise PublicationError(
                f"duplicate replacement anchor relocation: {replacement_tuple!r}"
            )
        seen_previous.add(previous_tuple)
        seen_replacement.add(replacement_tuple)
        target = active_by_ref.get(
            (replacement["document_id"], replacement["version"])
        )
        if target is None:
            raise PublicationError(
                f"anchor relocation target is inactive: {replacement_tuple!r}"
            )
        target_anchors = _declared_anchor_map(target)
        if target_anchors.get(replacement["anchor_id"]) != relocation["heading"]:
            raise PublicationError(
                f"anchor relocation target does not resolve: {replacement_tuple!r}"
            )
        if (
            previous["document_id"]
            == replacement["document_id"]
            and previous["version"] == replacement["version"]
        ):
            raise PublicationError(
                "cross-document relocation must change the document tuple"
            )
        for alias in relocation["compatibility_aliases"]:
            alias_key = alias["kind"], alias["value"]
            if alias_key in seen_aliases:
                raise PublicationError(
                    f"duplicate relocation compatibility alias: {alias_key!r}"
                )
            seen_aliases.add(alias_key)
            if not alias["value"].endswith(
                "#" + previous["anchor_id"]
            ):
                raise PublicationError(
                    "relocation compatibility alias does not preserve the "
                    f"historical fragment {previous['anchor_id']!r}"
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
        if len(documents) < 2 or any(
            document["role"] == "monolith" for document in documents
        ):
            raise PublicationError(
                "modular mode requires multiple active non-monolith documents"
            )
        if catalog["reserved_documents"]:
            raise PublicationError(
                "modular activation cannot retain reserved documents"
            )
        assembly = aggregate["assembly"]
        if assembly["entrypoint"] != "publication/modular/root.hc":
            raise PublicationError(
                "modular aggregate must use the authoritative entrypoint"
            )
        manifest_path = _repo_file(
            root,
            assembly["manifest"],
            label="modular assembly manifest",
            must_exist=True,
        )
        source_map_path = _repo_file(
            root,
            assembly["source_map"],
            label="modular assembly source map",
            must_exist=True,
        )
        manifest = _load_json(manifest_path)
        source_map = _load_json(source_map_path)
        expected_sources = {
            document["source_path"] for document in documents
        }
        if (
            not isinstance(manifest, Mapping)
            or manifest.get("schemaVersion") != 1
            or manifest.get("root") != assembly["entrypoint"]
        ):
            raise PublicationError("modular assembly manifest is invalid")
        dependencies = manifest.get("dependencies")
        if not isinstance(dependencies, list) or {
            item.get("to")
            for item in dependencies
            if isinstance(item, Mapping)
        } != expected_sources:
            raise PublicationError(
                "modular assembly manifest does not select exact active sources"
            )
        if (
            not isinstance(source_map, Mapping)
            or source_map.get("schemaVersion") != 1
            or source_map.get("lineBase") != 1
            or source_map.get("outputSha256") != aggregate["sha256"]
        ):
            raise PublicationError(
                "modular source map does not bind the aggregate digest"
            )
        mappings = source_map.get("mappings")
        if not isinstance(mappings, list) or not mappings:
            raise PublicationError("modular source map has no mappings")
        mapped_sources = {
            item["source"]["path"]
            for item in mappings
            if isinstance(item, Mapping)
            and item.get("kind") == "markdown"
            and isinstance(item.get("source"), Mapping)
        }
        if mapped_sources != expected_sources:
            raise PublicationError(
                "modular source map does not cover exact active sources"
            )
        return

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
    _validate_anchor_relocations(catalog, active_by_ref)
    _validate_registries(root, catalog["registries"], active_by_ref)
    _validate_mode(root, catalog, active_by_ref)
    return catalog


def validate_history(
    root: Path = ROOT,
    base_ref: str = "origin/main",
    candidate_ref: str = "HEAD",
) -> int:
    """Validate immutable identities across base and candidate catalog history."""

    root = root.resolve(strict=True)
    current = validate_catalog(root)
    historical = _historical_catalogs(root, base_ref, candidate_ref)
    validate_catalog_history(current, historical)
    return len(historical)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "validate-history"))
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root containing publication/ (default: repository root)",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help=(
            "Git ref whose complete catalog history is immutable "
            "(default: origin/main)"
        ),
    )
    parser.add_argument(
        "--candidate-ref",
        default="HEAD",
        help=(
            "Git ref whose commits after base-ref are candidate publication "
            "snapshots (default: HEAD)"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-history":
            catalog_count = validate_history(
                args.root,
                args.base_ref,
                args.candidate_ref,
            )
        else:
            catalog = validate_catalog(args.root)
    except (OSError, PublicationError) as error:
        print(f"publication validation failed: {error}", file=sys.stderr)
        return 1
    if args.command == "validate-history":
        print(
            "publication history validation passed: "
            f"{catalog_count} historical catalog snapshots checked"
        )
        return 0
    print(
        "publication validation passed: "
        f"{len(catalog['documents'])} active document, "
        f"{len(catalog['reserved_documents'])} reserved documents, "
        f"{len(catalog['registries'])} registries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
