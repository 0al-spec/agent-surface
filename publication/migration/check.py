#!/usr/bin/env python3
"""Validate the closed transitional ownership map for modular RFC migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator
from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MAP_PATH = Path("publication/migration/module-ownership.json")
SCHEMA_PATH = Path("publication/migration/module-ownership.schema.json")
MATERIALIZATION_PATH = Path("publication/migration/materialization.json")
MATERIALIZATION_SCHEMA_PATH = Path(
    "publication/migration/materialization.schema.json"
)


class OwnershipError(ValueError):
    """The ownership map is incomplete, ambiguous, or stale."""


@dataclass(frozen=True)
class Heading:
    line: int
    level: int
    title: str
    parent: int | None


@dataclass(frozen=True)
class MaterializationFragment:
    """One maximal canonical byte range with a single future document owner."""

    owner_document_id: str
    start_byte: int
    end_byte: int
    canonical_end_byte: int
    transform: str


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OwnershipError(f"duplicate JSON object member: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
        )
    except (OSError, json.JSONDecodeError) as error:
        raise OwnershipError(f"cannot load {path}: {error}") from error


def _schema_path(error: Any) -> str:
    return ".".join(str(member) for member in error.absolute_path) or "$"


def _validate_schema(instance: Any, schema: Any) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        error = errors[0]
        raise OwnershipError(
            f"module ownership schema violation at {_schema_path(error)}: "
            f"{error.message}"
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _headings(path: Path) -> list[Heading]:
    tokens = MarkdownIt("commonmark", {"html": True}).parse(
        path.read_text(encoding="utf-8")
    )
    headings: list[Heading] = []
    stack: list[int] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        level = int(token.tag[1:])
        while stack and headings[stack[-1]].level >= level:
            stack.pop()
        parent = stack[-1] if stack else None
        headings.append(
            Heading(
                line=token.map[0] + 1,
                level=level,
                title=tokens[index + 1].content.strip(),
                parent=parent,
            )
        )
        stack.append(len(headings) - 1)
    if not headings:
        raise OwnershipError(f"canonical source has no headings: {path}")
    return headings


def materialization_fragments(
    root: Path,
    ownership_map: Mapping[str, Any],
) -> list[MaterializationFragment]:
    """Partition the canonical RFC into maximal consecutive ownership runs."""

    source_path = root / ownership_map["canonical_source"]["path"]
    canonical = source_path.read_bytes()
    headings = _headings(source_path)
    module_ids = {item["document_id"] for item in ownership_map["modules"]}
    resolved, _ = _validate_sections(ownership_map, headings, module_ids)

    lines = canonical.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    if offsets[-1] != len(canonical):
        raise OwnershipError("canonical source line offsets are incomplete")

    runs: list[tuple[int, int, str]] = []
    for index, heading in enumerate(headings):
        start = offsets[heading.line - 1]
        end = (
            offsets[headings[index + 1].line - 1]
            if index + 1 < len(headings)
            else len(canonical)
        )
        owner = resolved[index]
        if runs and runs[-1][2] == owner:
            runs[-1] = (runs[-1][0], end, owner)
        else:
            runs.append((start, end, owner))

    fragments: list[MaterializationFragment] = []
    for index, (start, canonical_end, owner) in enumerate(runs):
        if index == 1:
            start -= 1
        end = canonical_end
        if index < len(runs) - 1:
            if canonical[end - 2 : end] != b"\n\n":
                raise OwnershipError(
                    "module boundary lacks the canonical blank line required "
                    "for deterministic Hyperprompt separator replacement"
                )
            end -= 1
        fragments.append(
            MaterializationFragment(
                owner_document_id=owner,
                start_byte=start,
                end_byte=end,
                canonical_end_byte=canonical_end,
                transform=(
                    "identity"
                    if index == 0
                    else "promote_atx_headings_one_level"
                ),
            )
        )
    if not fragments or fragments[0].start_byte != 0:
        raise OwnershipError("module materialization does not start at byte zero")
    if fragments[-1].canonical_end_byte != len(canonical):
        raise OwnershipError("module materialization does not reach canonical EOF")
    return fragments


def _active_document(catalog: Mapping[str, Any]) -> Mapping[str, Any]:
    documents = catalog["documents"]
    if len(documents) != 1:
        raise OwnershipError(
            "ownership map v1 requires exactly one transitional active document"
        )
    return documents[0]


def _validate_modules(
    ownership_map: Mapping[str, Any],
    catalog: Mapping[str, Any],
) -> set[str]:
    reserved = catalog["reserved_documents"]
    expected = [document["document_id"] for document in reserved]
    actual = [module["document_id"] for module in ownership_map["modules"]]
    if actual != expected:
        raise OwnershipError(
            "modules must exactly match reserved_documents in publication order"
        )
    if len(actual) != len(set(actual)):
        raise OwnershipError("module list contains duplicate document_id values")
    return set(actual)


def _validate_sections(
    ownership_map: Mapping[str, Any],
    headings: Sequence[Heading],
    module_ids: set[str],
) -> tuple[dict[int, str], dict[str, set[int]]]:
    by_line = {heading.line: index for index, heading in enumerate(headings)}
    if len(by_line) != len(headings):
        raise OwnershipError("canonical source contains multiple headings on one line")

    assignments = ownership_map["section_assignments"]
    assignment_lines = [assignment["source_line"] for assignment in assignments]
    if assignment_lines != sorted(assignment_lines):
        raise OwnershipError("section_assignments must be sorted by source_line")
    if len(assignment_lines) != len(set(assignment_lines)):
        raise OwnershipError("a heading has multiple explicit owners")

    explicit: dict[int, str] = {}
    for assignment in assignments:
        line = assignment["source_line"]
        if line not in by_line:
            raise OwnershipError(
                f"section assignment line {line} does not identify a heading"
            )
        heading_index = by_line[line]
        heading = headings[heading_index]
        if (
            assignment["level"] != heading.level
            or assignment["heading"] != heading.title
        ):
            raise OwnershipError(
                f"stale section assignment at line {line}: expected "
                f"h{heading.level} {heading.title!r}"
            )
        owner = assignment["owner_document_id"]
        if owner not in module_ids:
            raise OwnershipError(
                f"section assignment at line {line} has non-reserved owner {owner}"
            )
        explicit[heading_index] = owner

    required = {
        index for index, heading in enumerate(headings) if heading.level in (1, 2)
    }
    missing = sorted(required - explicit.keys(), key=lambda index: headings[index].line)
    if missing:
        heading = headings[missing[0]]
        raise OwnershipError(
            f"top-level section has no explicit owner at line {heading.line}: "
            f"{heading.title}"
        )

    resolved: dict[int, str] = {}
    owned: dict[str, set[int]] = {module_id: set() for module_id in module_ids}
    for index, heading in enumerate(headings):
        cursor: int | None = index
        while cursor is not None and cursor not in explicit:
            cursor = headings[cursor].parent
        if cursor is None:
            raise OwnershipError(
                f"heading has no owner at line {heading.line}: {heading.title}"
            )
        owner = explicit[cursor]
        resolved[index] = owner
        owned[owner].add(index)
        if (
            index in explicit
            and heading.level > 2
            and heading.parent is not None
            and resolved[heading.parent] == owner
        ):
            raise OwnershipError(
                f"redundant nested assignment at line {heading.line}: {heading.title}"
            )

    empty = sorted(module_id for module_id, members in owned.items() if not members)
    if empty:
        raise OwnershipError(f"reserved module owns no RFC content: {empty[0]}")
    return resolved, owned


def _validate_exports(
    ownership_map: Mapping[str, Any],
    active: Mapping[str, Any],
    module_ids: set[str],
) -> None:
    expected_artifacts = [
        (item["kind"], item["id"])
        for item in active["exports"]
        if item["kind"] == "artifact"
    ]
    expected = {
        (item["kind"], item["id"])
        for item in active["exports"]
        if item["kind"] != "artifact"
    }
    assignments = ownership_map["export_assignments"]
    actual = [(item["kind"], item["id"]) for item in assignments]
    if len(actual) != len(set(actual)):
        raise OwnershipError("an active export has multiple future owners")
    if set(actual) != expected:
        missing = sorted(expected - set(actual))
        extra = sorted(set(actual) - expected)
        raise OwnershipError(
            f"export ownership is not closed; missing={missing}, extra={extra}"
        )
    for assignment in assignments:
        if assignment["owner_document_id"] not in module_ids:
            raise OwnershipError(
                f"export has non-reserved owner: {assignment['id']}"
            )

    artifact = ownership_map["aggregate_artifact"]
    if expected_artifacts != [("artifact", artifact["id"])]:
        raise OwnershipError(
            "aggregate_artifact must identify the active transitional artifact"
        )


def _validate_public_anchors(
    ownership_map: Mapping[str, Any],
    active: Mapping[str, Any],
    headings: Sequence[Heading],
    resolved: Mapping[int, str],
) -> None:
    declared = active["public_anchors"]
    expected = {(item["anchor_id"], item["heading"]) for item in declared}
    assignments = ownership_map["public_anchor_assignments"]
    actual = [(item["anchor_id"], item["heading"]) for item in assignments]
    if len(actual) != len(set(actual)):
        raise OwnershipError("a public anchor has multiple future owners")
    if set(actual) != expected:
        raise OwnershipError(
            "public_anchor_assignments must exactly cover active public_anchors"
        )

    title_indexes: dict[str, list[int]] = {}
    for index, heading in enumerate(headings):
        title_indexes.setdefault(heading.title, []).append(index)
    for assignment in assignments:
        matches = title_indexes.get(assignment["heading"], [])
        if len(matches) != 1:
            raise OwnershipError(
                f"public anchor heading must resolve uniquely: "
                f"{assignment['heading']!r}"
            )
        expected_owner = resolved[matches[0]]
        if assignment["owner_document_id"] != expected_owner:
            raise OwnershipError(
                f"public anchor {assignment['anchor_id']} owner conflicts with "
                "its section owner"
            )


def validate_ownership_map(root: Path = ROOT) -> Mapping[str, Any]:
    map_path = root / MAP_PATH
    ownership_map = _load_json(map_path)
    schema = _load_json(root / SCHEMA_PATH)
    _validate_schema(ownership_map, schema)

    catalog = _load_json(root / ownership_map["catalog_path"])
    if catalog["publication_mode"] != ownership_map["required_publication_mode"]:
        raise OwnershipError(
            "ownership map is valid only during transitional_monolith mode"
        )
    active = _active_document(catalog)
    source = ownership_map["canonical_source"]
    if active["source_path"] != source["path"]:
        raise OwnershipError("canonical source path disagrees with active document")
    source_path = root / source["path"]
    digest = _sha256(source_path)
    if digest != source["sha256"] or digest != active["source_sha256"]:
        raise OwnershipError(
            "canonical source digest is stale in ownership map or document catalog"
        )

    module_ids = _validate_modules(ownership_map, catalog)
    headings = _headings(source_path)
    resolved, _ = _validate_sections(ownership_map, headings, module_ids)
    _validate_exports(ownership_map, active, module_ids)
    _validate_public_anchors(ownership_map, active, headings, resolved)
    return ownership_map


def _module_fragment_path(
    target_source_path: str,
    sequence: int,
) -> str:
    target = Path(target_source_path)
    try:
        relative = target.relative_to("drafts/modules")
    except ValueError as error:
        raise OwnershipError(
            f"reserved target is outside drafts/modules: {target_source_path}"
        ) from error
    module = relative.with_suffix("").as_posix()
    return f"modules/{module}/part-{sequence:02d}.md"


def validate_materialization(
    root: Path = ROOT,
    ownership_map: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Validate the complete seven-module candidate against the ownership map."""

    active_map = (
        ownership_map
        if ownership_map is not None
        else validate_ownership_map(root)
    )
    materialization = _load_json(root / MATERIALIZATION_PATH)
    schema = _load_json(root / MATERIALIZATION_SCHEMA_PATH)
    _validate_schema(materialization, schema)

    catalog = _load_json(root / active_map["catalog_path"])
    if (
        catalog["publication_mode"]
        != materialization["publication_mode_required"]
    ):
        raise OwnershipError(
            "module materialization is valid only during transitional_monolith mode"
        )
    ownership_ref = materialization["ownership_map"]
    if ownership_ref["path"] != MAP_PATH.as_posix():
        raise OwnershipError("materialization references an unexpected ownership map")
    if _sha256(root / MAP_PATH) != ownership_ref["sha256"]:
        raise OwnershipError("materialization ownership-map digest is stale")

    candidate_ref = materialization["candidate"]
    descriptor_path = root / candidate_ref["descriptor_path"]
    try:
        from publication.assembly.check import (
            AssemblyError,
            validate_candidate,
        )

        candidate = validate_candidate(root, descriptor_path)
    except AssemblyError as error:
        raise OwnershipError(
            f"modular candidate is invalid: {error}"
        ) from error
    if candidate["candidate_id"] != candidate_ref["candidate_id"]:
        raise OwnershipError("materialization candidate identity is inconsistent")
    if candidate["canonical"] != active_map["canonical_source"]:
        raise OwnershipError(
            "materialization candidate does not bind the ownership-map source"
        )

    reserved = catalog["reserved_documents"]
    reserved_by_id = {item["document_id"]: item for item in reserved}
    fragments = materialization_fragments(root, active_map)
    counters: dict[str, int] = {}
    expected_paths: list[str] = []
    expected_by_owner: dict[str, list[str]] = {
        item["document_id"]: [] for item in reserved
    }
    for fragment in fragments:
        document = reserved_by_id[fragment.owner_document_id]
        target = document["target_source_path"]
        counters[target] = counters.get(target, 0) + 1
        path = _module_fragment_path(target, counters[target])
        expected_paths.append(path)
        expected_by_owner[fragment.owner_document_id].append(path)

    declared = candidate["sources"]["declared"]
    if not declared or declared[0]["path"] != "root.hc":
        raise OwnershipError("modular candidate must declare root.hc first")
    markdown_sources = declared[1:]
    actual_paths = [item["path"] for item in markdown_sources]
    if actual_paths != expected_paths:
        raise OwnershipError(
            "candidate fragment order does not match canonical ownership runs"
        )
    if len(markdown_sources) != len(fragments):
        raise OwnershipError("candidate fragment closure is incomplete")

    candidate_root = Path(candidate_ref["descriptor_path"]).parent
    root_lines = []
    for index, (source, fragment) in enumerate(
        zip(markdown_sources, fragments, strict=True)
    ):
        expected_derivation = {
            "method": "byte_range",
            "source_path": "drafts/agent-surface.md",
            "start_byte": fragment.start_byte,
            "end_byte": fragment.end_byte,
            "transform": fragment.transform,
        }
        if source.get("canonical_derivation") != expected_derivation:
            raise OwnershipError(
                f"candidate fragment derivation is stale: {source['path']}"
            )
        expected_repository_path = (
            candidate_root / "sources" / source["path"]
        ).as_posix()
        if source.get("repository_path") != expected_repository_path:
            raise OwnershipError(
                f"candidate fragment repository path is stale: {source['path']}"
            )
        root_lines.append(f'{"    " if index else ""}"{source["path"]}"')

    expected_root = ("\n".join(root_lines) + "\n").encode("utf-8")
    root_source = declared[0]
    root_path = root / root_source["repository_path"]
    if root_path.read_bytes() != expected_root:
        raise OwnershipError(
            "modular candidate root does not preserve canonical fragment order"
        )

    actual_modules = materialization["modules"]
    if len(actual_modules) != len(reserved):
        raise OwnershipError(
            "materialization must contain every reserved document exactly once"
        )
    for actual, document in zip(actual_modules, reserved, strict=True):
        expected_module = {
            "document_id": document["document_id"],
            "version": document["version"],
            "target_source_path": document["target_source_path"],
            "fragments": expected_by_owner[document["document_id"]],
        }
        if actual != expected_module:
            raise OwnershipError(
                "materialized module metadata or fragment ownership is stale: "
                f"{document['document_id']}"
            )
        target = root / document["target_source_path"]
        if target.exists() or target.is_symlink():
            raise OwnershipError(
                f"reserved canonical module path must remain absent in 79B: {target}"
            )
    return materialization


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        ownership_map = validate_ownership_map(args.root.resolve())
        materialization = validate_materialization(
            args.root.resolve(),
            ownership_map,
        )
    except OwnershipError as error:
        print(f"module ownership validation failed: {error}")
        return 1
    print(
        "Validated transitional module ownership and materialization: "
        f"{len(ownership_map['modules'])} modules, "
        f"{len(ownership_map['section_assignments'])} section assignments, "
        f"{sum(len(item['fragments']) for item in materialization['modules'])} "
        "candidate fragments"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
