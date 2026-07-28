#!/usr/bin/env python3
"""Generate seven standalone non-authoritative RFC module documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication.assembly.check import promote_atx_headings_one_level
from publication.migration.check import (
    MAP_PATH,
    MATERIALIZATION_PATH,
    STANDALONE_PATH,
    _headings,
    _load_json,
    _sha256,
    _validate_sections,
    validate_materialization,
    validate_ownership_map,
)
from review.rfc_toc import slugify


DOCUMENTS_ROOT = Path("publication/migration/documents")
TOC_PATTERN = re.compile(
    rb"<!-- BEGIN GENERATED RFC TOC -->.*?"
    rb"<!-- END GENERATED RFC TOC -->\n?",
    re.DOTALL,
)
FENCE_OPEN = re.compile(rb"^( {0,3})(`{3,}|~{3,})(.*)$")
ATX_HEADING = re.compile(rb"^( {0,3})(#{1,6})(?:[ \t]+|$)")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _document_candidate_path(target_source_path: str) -> Path:
    target = Path(target_source_path)
    relative = target.relative_to("drafts/modules")
    return DOCUMENTS_ROOT / relative


def _demote_atx_headings_one_level(content: bytes) -> bytes:
    output: list[bytes] = []
    active_fence: tuple[bytes, int] | None = None
    for line in content.splitlines(keepends=True):
        body = line.rstrip(b"\r\n")
        if active_fence is not None:
            marker, length = active_fence
            stripped = body.lstrip(b" ")
            count = len(stripped) - len(stripped.lstrip(marker))
            if count >= length and stripped[count:].strip(b" \t") == b"":
                active_fence = None
            output.append(line)
            continue
        opening = FENCE_OPEN.match(body)
        if opening is not None:
            fence = opening.group(2)
            if fence[:1] == b"~" or b"`" not in opening.group(3):
                active_fence = (fence[:1], len(fence))
            output.append(line)
            continue
        heading = ATX_HEADING.match(body)
        if heading is None:
            output.append(line)
            continue
        hashes = heading.group(2)
        if len(hashes) == 6:
            raise ValueError("cannot demote an ATX level-6 heading")
        marker_end = heading.end(2)
        output.append(line[:marker_end] + b"#" + line[marker_end:])
    return b"".join(output)


def _heading_byte_offsets(source: bytes, headings: Sequence[Any]) -> list[int]:
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    return [offsets[heading.line - 1] for heading in headings]


def _fragment_content(
    root: Path,
    source: Mapping[str, Any],
    *,
    first_heading_level: int,
    parent_has_same_owner: bool,
    is_aggregate_root: bool,
    first_h2_offset: int | None,
) -> bytes:
    content = (root / source["repository_path"]).read_bytes()
    if is_aggregate_root:
        if first_h2_offset is None:
            raise ValueError("aggregate root has no level-two content")
        start = source["canonical_derivation"]["start_byte"]
        content = content[first_h2_offset - start :]
        content, replacements = TOC_PATTERN.subn(b"", content)
        if replacements != 1:
            raise ValueError("aggregate root must contain exactly one generated TOC")
    else:
        content = _demote_atx_headings_one_level(content)
        if not parent_has_same_owner and first_heading_level > 2:
            for _ in range(first_heading_level - 2):
                content = promote_atx_headings_one_level(content)
    return content.strip(b"\n") + b"\n"


def _prologue(
    document: Mapping[str, Any],
    references: Sequence[Mapping[str, Any]],
    candidate_paths: Mapping[str, Path],
) -> bytes:
    lines = [
        f"# {document['title']}",
        "",
        "> [!IMPORTANT]",
        "> Non-authoritative modular publication candidate. The canonical source",
        "> remains `drafts/agent-surface.md` until atomic activation.",
        "",
        f"- Document ID: `{document['document_id']}`",
        f"- Exact version: `{document['version']}`",
        f"- Planned canonical path: `{document['target_source_path']}`",
        "",
        "## Exact Normative Dependencies",
        "",
    ]
    if references:
        for reference in references:
            path = candidate_paths[reference["document_id"]].as_posix()
            lines.append(
                f"- `{reference['document_id']}` at `{reference['version']}` "
                f"(candidate `{path}`)"
            )
    else:
        lines.append("- None.")
    lines.extend(["", "{{DOCUMENT_SET_CONTENTS}}", ""])
    return ("\n".join(lines)).encode("utf-8")


def _heading_anchors(markdown: bytes) -> dict[str, list[str]]:
    tokens = MarkdownIt("commonmark", {"html": True}).parse(
        markdown.decode("utf-8")
    )
    occurrences: Counter[str] = Counter()
    result: dict[str, list[str]] = {}
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        title = tokens[index + 1].content.strip()
        base = slugify(title)
        suffix = occurrences[base]
        occurrences[base] += 1
        anchor = base if suffix == 0 else f"{base}-{suffix}"
        result.setdefault(title, []).append(anchor)
    return result


def generate(root: Path) -> dict[Path, bytes]:
    ownership_map = validate_ownership_map(root)
    materialization = validate_materialization(root, ownership_map)
    catalog = _load_json(root / ownership_map["catalog_path"])
    candidate = _load_json(
        root / materialization["candidate"]["descriptor_path"]
    )
    reserved = catalog["reserved_documents"]
    reserved_by_id = {item["document_id"]: item for item in reserved}
    candidate_paths = {
        item["document_id"]: _document_candidate_path(
            item["target_source_path"]
        )
        for item in reserved
    }
    source_by_path = {
        item["path"]: item for item in candidate["sources"]["declared"]
    }

    canonical_path = root / ownership_map["canonical_source"]["path"]
    canonical = canonical_path.read_bytes()
    headings = _headings(canonical_path)
    module_ids = {item["document_id"] for item in ownership_map["modules"]}
    resolved, _ = _validate_sections(ownership_map, headings, module_ids)
    heading_offsets = _heading_byte_offsets(canonical, headings)

    preliminary: dict[str, bytes] = {}
    document_fragments: dict[str, list[str]] = {}
    first_h2_offset = next(
        heading_offsets[index]
        for index, heading in enumerate(headings)
        if heading.level == 2
    )
    for module in materialization["modules"]:
        document_id = module["document_id"]
        document = reserved_by_id[document_id]
        body_parts: list[bytes] = []
        for fragment_path in module["fragments"]:
            source = source_by_path[fragment_path]
            start = source["canonical_derivation"]["start_byte"]
            heading_index = next(
                index
                for index, offset in enumerate(heading_offsets)
                if offset >= start
                and offset < source["canonical_derivation"]["end_byte"]
            )
            heading = headings[heading_index]
            parent_has_same_owner = (
                heading.parent is not None
                and resolved[heading.parent] == document_id
            )
            body_parts.append(
                _fragment_content(
                    root,
                    source,
                    first_heading_level=heading.level,
                    parent_has_same_owner=parent_has_same_owner,
                    is_aggregate_root=start == 0,
                    first_h2_offset=first_h2_offset,
                )
            )
        references = document["normative_dependencies"]
        prologue = _prologue(document, references, candidate_paths)
        preliminary[document_id] = prologue + b"\n".join(body_parts)
        document_fragments[document_id] = list(module["fragments"])

    anchors = {
        document_id: _heading_anchors(content)
        for document_id, content in preliminary.items()
    }
    core = next(item for item in reserved if item["role"] == "core")
    navigation: list[dict[str, Any]] = []
    contents_lines = ["## Document Set Contents", ""]
    heading_occurrences: dict[tuple[str, str], int] = {}
    h2_owners = {
        resolved[index]
        for index, heading in enumerate(headings)
        if heading.level == 2
    }
    fallback_owners: set[str] = set()
    for index, heading in enumerate(headings):
        owner = resolved[index]
        occurrence_key = (owner, heading.title)
        occurrence = heading_occurrences.get(occurrence_key, 0)
        heading_occurrences[occurrence_key] = occurrence + 1
        is_owner_fallback = (
            owner not in h2_owners and owner not in fallback_owners
        )
        if heading.level != 2 and not is_owner_fallback:
            continue
        if is_owner_fallback:
            fallback_owners.add(owner)
        target = reserved_by_id[owner]
        matches = anchors[owner].get(heading.title, [])
        if occurrence >= len(matches):
            raise ValueError(
                f"standalone heading occurrence is missing: {heading.title}"
            )
        anchor = matches[occurrence]
        target_path = candidate_paths[owner]
        relative = PurePosixPath(
            Path(
                Path(target_path).relative_to(DOCUMENTS_ROOT)
            ).as_posix()
        )
        contents_lines.append(
            f"- [{heading.title}]({relative.as_posix()}#{anchor})"
        )
        navigation.append(
            {
                "heading": heading.title,
                "source_document_id": core["document_id"],
                "target_document_id": owner,
                "target_version": target["version"],
                "target_candidate_path": target_path.as_posix(),
                "target_anchor_id": anchor,
            }
        )
    contents = ("\n".join(contents_lines) + "\n").encode("utf-8")
    final_documents = {
        document_id: content.replace(
            b"{{DOCUMENT_SET_CONTENTS}}",
            contents if document_id == core["document_id"] else b"",
        )
        for document_id, content in preliminary.items()
    }

    active = catalog["documents"][0]
    relocation_owner = {
        item["anchor_id"]: item["owner_document_id"]
        for item in ownership_map["public_anchor_assignments"]
    }
    relocations = []
    for anchor in active["public_anchors"]:
        owner = relocation_owner[anchor["anchor_id"]]
        replacement = reserved_by_id[owner]
        anchor_id = anchor["anchor_id"]
        relocations.append(
            {
                "heading": anchor["heading"],
                "previous": {
                    "document_id": active["document_id"],
                    "version": active["version"],
                    "anchor_id": anchor_id,
                },
                "replacement": {
                    "document_id": owner,
                    "version": replacement["version"],
                    "anchor_id": anchor_id,
                },
                "compatibility_aliases": [
                    {
                        "kind": "legacy_aggregate_path_fragment",
                        "value": f"{active['source_path']}#{anchor_id}",
                        "status": "transition_only",
                    },
                    {
                        "kind": "legacy_aggregate_fragment",
                        "value": f"#{anchor_id}",
                        "status": "transition_only",
                    },
                ],
            }
        )

    documents = []
    generated: dict[Path, bytes] = {}
    for document in reserved:
        document_id = document["document_id"]
        path = candidate_paths[document_id]
        content = final_documents[document_id]
        generated[path] = content
        references = [
            {
                "document_id": reference["document_id"],
                "version": reference["version"],
                "candidate_path": candidate_paths[
                    reference["document_id"]
                ].as_posix(),
            }
            for reference in document["normative_dependencies"]
        ]
        documents.append(
            {
                "document_id": document_id,
                "version": document["version"],
                "title": document["title"],
                "target_source_path": document["target_source_path"],
                "candidate_path": path.as_posix(),
                "sha256": _sha256_bytes(content),
                "content_fragments": document_fragments[document_id],
                "normative_references": references,
            }
        )

    contract = {
        "$schema": "./standalone.schema.json",
        "schema_version": 1,
        "standalone_set_id": (
            "https://github.com/0al-spec/agent-surface/"
            "publication/standalone-modules/v1"
        ),
        "authority": "non_authoritative_migration_candidate",
        "publication_mode_required": "transitional_monolith",
        "ownership_map": {
            "path": MAP_PATH.as_posix(),
            "sha256": _sha256(root / MAP_PATH),
        },
        "materialization": {
            "path": MATERIALIZATION_PATH.as_posix(),
            "sha256": _sha256(root / MATERIALIZATION_PATH),
        },
        "generation_policy": {
            "content_order": "canonical_order_within_owner",
            "orphan_heading_policy": "promote_subtree_root_to_h2",
            "aggregate_title": "replace_with_reserved_document_title",
            "aggregate_toc": "replace_with_exact_document_set_navigation",
        },
        "reference_policy": {
            "normative_tuple": "document_id_exact_version",
            "navigation_anchor": "candidate_local_github_slug",
            "public_relocation": "old_tuple_to_new_tuple",
            "implicit_slugs": "non_public_navigation_only",
        },
        "documents": documents,
        "navigation_references": navigation,
        "public_anchor_relocations": relocations,
    }
    generated[STANDALONE_PATH] = _json_bytes(contract)
    return generated


def write_generated(root: Path, generated: Mapping[Path, bytes]) -> None:
    documents_root = root / DOCUMENTS_ROOT
    if documents_root.exists():
        shutil.rmtree(documents_root)
    for relative, content in generated.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def check_generated(root: Path, generated: Mapping[Path, bytes]) -> None:
    expected_documents = {
        path for path in generated if DOCUMENTS_ROOT in path.parents
    }
    actual_documents = {
        path.relative_to(root)
        for path in (root / DOCUMENTS_ROOT).rglob("*")
        if path.is_file()
    }
    if actual_documents != expected_documents:
        raise ValueError(
            "standalone candidate document inventory is stale: "
            f"expected={sorted(expected_documents)}, "
            f"actual={sorted(actual_documents)}"
        )
    for relative, expected in generated.items():
        path = root / relative
        if not path.is_file() or path.read_bytes() != expected:
            raise ValueError(f"standalone candidate is stale: {relative}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "check"))
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    generated = generate(root)
    if args.command == "generate":
        write_generated(root, generated)
    else:
        check_generated(root, generated)
    print(
        (
            "Generated standalone RFC candidates: "
            if args.command == "generate"
            else "Standalone RFC candidates are current: "
        )
        + f"{len(generated) - 1} documents"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
