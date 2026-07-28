#!/usr/bin/env python3
"""Generate the complete non-authoritative seven-module RFC candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication.assembly.check import (
    promote_atx_headings_one_level,
    verify_compiler,
)
from publication.migration.check import (
    MAP_PATH,
    MATERIALIZATION_PATH,
    _load_json,
    materialization_fragments,
    validate_ownership_map,
)


CANDIDATE_ID = "modular-document-set"
CANDIDATE_DIRECTORY = Path("publication/candidates") / CANDIDATE_ID
LOCK_PATH = Path("publication/assembly/hyperprompt.lock.json")
SOURCE_DATE_EPOCH = 1700000000


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _module_relative_path(target_source_path: str) -> str:
    target = Path(target_source_path)
    modules_root = Path("drafts/modules")
    try:
        relative = target.relative_to(modules_root)
    except ValueError as error:
        raise ValueError(
            f"reserved target is outside drafts/modules: {target_source_path}"
        ) from error
    return relative.with_suffix("").as_posix()


def _compile(
    compiler: Path,
    sources: Mapping[str, bytes],
    entrypoint: str,
) -> tuple[bytes, bytes, bytes, list[int]]:
    with tempfile.TemporaryDirectory(prefix="asp-79b-materialize-") as temporary:
        staging = Path(temporary)
        for relative, content in sources.items():
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        output = staging / "artifacts/agent-surface.md"
        manifest = staging / "artifacts/agent-surface.manifest.json"
        source_map = staging / "artifacts/agent-surface.source-map.json"
        output.parent.mkdir(parents=True)
        environment = os.environ.copy()
        environment.update(
            {
                "SOURCE_DATE_EPOCH": str(SOURCE_DATE_EPOCH),
                "LC_ALL": "C",
                "TZ": "UTC",
            }
        )
        result = subprocess.run(
            [
                str(compiler.resolve()),
                "compile",
                entrypoint,
                "--root",
                str(staging),
                "--output",
                output.relative_to(staging).as_posix(),
                "--manifest",
                manifest.relative_to(staging).as_posix(),
                "--source-map",
                source_map.relative_to(staging).as_posix(),
            ],
            cwd=staging,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Hyperprompt materialization failed: "
                + (result.stderr.strip() or result.stdout.strip())
            )
        source_map_value = json.loads(source_map.read_text(encoding="utf-8"))
        separators = [
            item["generatedLine"]
            for item in source_map_value["mappings"]
            if item["kind"] == "generated_separator"
        ]
        return (
            output.read_bytes(),
            manifest.read_bytes(),
            source_map.read_bytes(),
            separators,
        )


def generate(root: Path, compiler: Path) -> dict[Path, bytes]:
    verify_compiler(compiler, root=root)
    ownership_map = validate_ownership_map(root)
    catalog = _load_json(root / ownership_map["catalog_path"])
    canonical_path = root / ownership_map["canonical_source"]["path"]
    canonical = canonical_path.read_bytes()
    fragments = materialization_fragments(root, ownership_map)

    root_lines: list[str] = []
    sources: dict[str, bytes] = {}
    module_fragments: dict[str, list[str]] = {
        item["document_id"]: [] for item in ownership_map["modules"]
    }
    declared: list[dict[str, Any]] = []
    counters: dict[str, int] = {}
    reserved_by_id = {
        item["document_id"]: item for item in catalog["reserved_documents"]
    }

    for index, fragment in enumerate(fragments):
        reserved = reserved_by_id[fragment.owner_document_id]
        module_name = _module_relative_path(reserved["target_source_path"])
        counters[module_name] = counters.get(module_name, 0) + 1
        relative = (
            f"modules/{module_name}/part-{counters[module_name]:02d}.md"
        )
        transform = fragment.transform
        canonical_content = canonical[fragment.start_byte : fragment.end_byte]
        content = (
            canonical_content
            if transform == "identity"
            else promote_atx_headings_one_level(canonical_content)
        )
        sources[relative] = content
        module_fragments[fragment.owner_document_id].append(relative)
        root_lines.append(
            f'{"    " if index else ""}"{relative}"'
        )
        declared.append(
            {
                "path": relative,
                "media_type": "markdown",
                "origin": "committed_candidate",
                "sha256": _sha256_bytes(content),
                "repository_path": (
                    CANDIDATE_DIRECTORY / "sources" / relative
                ).as_posix(),
                "canonical_derivation": {
                    "method": "byte_range",
                    "source_path": "drafts/agent-surface.md",
                    "start_byte": fragment.start_byte,
                    "end_byte": fragment.end_byte,
                    "transform": transform,
                },
            }
        )

    entrypoint = "root.hc"
    root_content = ("\n".join(root_lines) + "\n").encode("utf-8")
    sources[entrypoint] = root_content
    declared.insert(
        0,
        {
            "path": entrypoint,
            "media_type": "hypercode",
            "origin": "committed_candidate",
            "sha256": _sha256_bytes(root_content),
            "repository_path": (
                CANDIDATE_DIRECTORY / "sources" / entrypoint
            ).as_posix(),
        },
    )

    output, manifest, source_map, separators = _compile(
        compiler,
        sources,
        entrypoint,
    )
    if output != canonical:
        mismatch = next(
            (
                index
                for index, (actual, expected) in enumerate(
                    zip(output, canonical, strict=False)
                )
                if actual != expected
            ),
            min(len(output), len(canonical)),
        )
        raise RuntimeError(
            "generated modular candidate is not byte-identical to the canonical RFC: "
            f"first mismatch at byte {mismatch}, "
            f"generated={len(output)}, canonical={len(canonical)}"
        )

    lock_sha256 = hashlib.sha256((root / LOCK_PATH).read_bytes()).hexdigest()
    candidate = {
        "$schema": "../../assembly/candidate.schema.json",
        "schema_version": 1,
        "candidate_stage": "executable",
        "candidate_id": CANDIDATE_ID,
        "description": (
            "Non-authoritative seven-module source closure proving byte-identical "
            "assembly of every RFC section under the 79A ownership map."
        ),
        "authority": "non_authoritative",
        "publication_mode_required": "transitional_monolith",
        "compiler": {
            "lock_path": LOCK_PATH.as_posix(),
            "lock_sha256": lock_sha256,
        },
        "canonical": {
            "path": ownership_map["canonical_source"]["path"],
            "sha256": ownership_map["canonical_source"]["sha256"],
        },
        "sources": {
            "committed_root": "sources",
            "entrypoint": entrypoint,
            "declared": declared,
        },
        "assembly": {
            "staging_policy": "disposable_empty_directory",
            "source_date_epoch": SOURCE_DATE_EPOCH,
            "output": "artifacts/agent-surface.md",
            "manifest": "artifacts/agent-surface.manifest.json",
            "source_map": "artifacts/agent-surface.source-map.json",
        },
        "expected": {
            "equivalence": "byte_identical_to_canonical",
            "aggregate_sha256": _sha256_bytes(output),
            "manifest_sha256": _sha256_bytes(manifest),
            "source_map_sha256": _sha256_bytes(source_map),
            "generated_separator_lines": separators,
        },
    }
    materialization = {
        "$schema": "./materialization.schema.json",
        "schema_version": 1,
        "materialization_id": (
            "https://github.com/0al-spec/agent-surface/"
            "publication/module-materialization/v1"
        ),
        "authority": "non_authoritative_migration_candidate",
        "publication_mode_required": "transitional_monolith",
        "ownership_map": {
            "path": MAP_PATH.as_posix(),
            "sha256": hashlib.sha256((root / MAP_PATH).read_bytes()).hexdigest(),
        },
        "candidate": {
            "candidate_id": CANDIDATE_ID,
            "descriptor_path": (
                CANDIDATE_DIRECTORY / "candidate.json"
            ).as_posix(),
        },
        "partition_policy": "maximal_consecutive_heading_ownership",
        "separator_policy": (
            "hyperprompt_sibling_separator_replaces_canonical_lf"
        ),
        "modules": [
            {
                "document_id": item["document_id"],
                "version": reserved_by_id[item["document_id"]]["version"],
                "target_source_path": reserved_by_id[item["document_id"]][
                    "target_source_path"
                ],
                "fragments": module_fragments[item["document_id"]],
            }
            for item in ownership_map["modules"]
        ],
    }

    generated: dict[Path, bytes] = {
        CANDIDATE_DIRECTORY / "candidate.json": _json_bytes(candidate),
        CANDIDATE_DIRECTORY / "sources" / entrypoint: root_content,
        MATERIALIZATION_PATH: _json_bytes(materialization),
    }
    generated.update(
        {
            CANDIDATE_DIRECTORY / "sources" / relative: content
            for relative, content in sources.items()
            if relative != entrypoint
        }
    )
    return generated


def write_generated(root: Path, generated: Mapping[Path, bytes]) -> None:
    candidate_root = root / CANDIDATE_DIRECTORY
    if candidate_root.exists():
        shutil.rmtree(candidate_root)
    for relative, content in generated.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def check_generated(root: Path, generated: Mapping[Path, bytes]) -> None:
    expected_candidate_files = {
        path
        for path in generated
        if path == CANDIDATE_DIRECTORY / "candidate.json"
        or CANDIDATE_DIRECTORY / "sources" in path.parents
    }
    candidate_root = root / CANDIDATE_DIRECTORY
    actual_candidate_files = {
        path.relative_to(root)
        for path in candidate_root.rglob("*")
        if path.is_file()
    }
    if actual_candidate_files != expected_candidate_files:
        missing = sorted(expected_candidate_files - actual_candidate_files)
        extra = sorted(actual_candidate_files - expected_candidate_files)
        raise RuntimeError(
            f"materialized candidate inventory is stale; missing={missing}, "
            f"extra={extra}"
        )
    for relative, expected in generated.items():
        path = root / relative
        if not path.is_file() or path.read_bytes() != expected:
            raise RuntimeError(f"materialized candidate is stale: {relative}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "check"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--compiler",
        type=Path,
        default=Path(".tools/hyperprompt/hyperprompt"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    compiler = args.compiler
    if not compiler.is_absolute():
        compiler = root / compiler
    generated = generate(root, compiler)
    if args.command == "generate":
        write_generated(root, generated)
    else:
        check_generated(root, generated)
    print(
        (
            "Materialized seven-module RFC candidate: "
            if args.command == "generate"
            else "Seven-module RFC candidate is current: "
        )
        + f"{len(generated) - 3} Markdown fragments"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
