#!/usr/bin/env python3
"""Build and verify the authoritative modular ASP aggregate."""

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
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication.assembly.check import validate_lock, verify_compiler


CATALOG_PATH = Path("publication/document-set.json")
ENTRYPOINT = Path("publication/modular/root.hc")
SOURCE_DATE_EPOCH = 1_700_000_000


class ModularBuildError(ValueError):
    """The authoritative modular build is incomplete or stale."""


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ModularBuildError(f"cannot load {path}: {error}") from error


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _compact_source_map(content: bytes) -> bytes:
    """Merge adjacent one-line mappings into lossless contiguous ranges."""

    raw = json.loads(content)
    ranges: list[dict[str, Any]] = []
    for mapping in raw["mappings"]:
        source = mapping.get("source")
        if mapping.get("kind") == "generated_separator" and source is None:
            generated_line = mapping["generatedLine"]
            if (
                ranges
                and ranges[-1]["kind"] == "generated_separator"
                and ranges[-1]["generatedEndLine"] + 1 == generated_line
            ):
                ranges[-1]["generatedEndLine"] = generated_line
            else:
                ranges.append(
                    {
                        "generatedStartLine": generated_line,
                        "generatedEndLine": generated_line,
                        "kind": "generated_separator",
                        "source": None,
                    }
                )
            continue
        if (
            mapping.get("kind") != "markdown"
            or not isinstance(source, dict)
            or source.get("startLine") != source.get("endLine")
        ):
            raise ModularBuildError(
                "Hyperprompt emitted unsupported source-map mapping"
            )
        generated_line = mapping["generatedLine"]
        if (
            ranges
            and ranges[-1]["kind"] == mapping["kind"]
            and ranges[-1]["generatedEndLine"] + 1 == generated_line
            and ranges[-1]["source"]["path"] == source["path"]
            and ranges[-1]["source"]["endLine"] + 1 == source["startLine"]
        ):
            ranges[-1]["generatedEndLine"] = generated_line
            ranges[-1]["source"]["endLine"] = source["endLine"]
            continue
        ranges.append(
            {
                "generatedStartLine": generated_line,
                "generatedEndLine": generated_line,
                "kind": mapping["kind"],
                "source": {
                    "path": source["path"],
                    "startLine": source["startLine"],
                    "endLine": source["endLine"],
                },
            }
        )
    compact = {
        "schemaVersion": 2,
        "lineBase": raw["lineBase"],
        "outputSha256": raw["outputSha256"],
        "mappings": ranges,
    }
    return (
        json.dumps(compact, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _compile(
    root: Path, compiler: Path
) -> tuple[bytes, bytes, bytes]:
    catalog = _json(root / CATALOG_PATH)
    if catalog.get("publication_mode") != "modular":
        raise ModularBuildError("authoritative assembly requires modular mode")
    documents = sorted(
        catalog["documents"], key=lambda item: item["publication_order"]
    )
    sources = [Path(item["source_path"]) for item in documents]
    expected_root = "\n".join(
        f'{"    " if index else ""}"{path.as_posix()}"'
        for index, path in enumerate(sources)
    ) + "\n"
    actual_root = (root / ENTRYPOINT).read_text(encoding="utf-8")
    if actual_root != expected_root:
        raise ModularBuildError(
            "Hyperprompt entrypoint does not exactly match catalog order"
        )

    with tempfile.TemporaryDirectory(prefix="asp-modular-publication-") as name:
        staging = Path(name)
        staged_entrypoint = staging / ENTRYPOINT
        staged_entrypoint.parent.mkdir(parents=True)
        staged_entrypoint.write_text(actual_root, encoding="utf-8")
        for source in sources:
            destination = staging / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / source, destination)

        output = Path(catalog["aggregate"]["path"])
        manifest = Path(catalog["aggregate"]["assembly"]["manifest"])
        source_map = Path(catalog["aggregate"]["assembly"]["source_map"])
        for artifact in (output, manifest, source_map):
            (staging / artifact).parent.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        environment.update(
            {
                "SOURCE_DATE_EPOCH": str(SOURCE_DATE_EPOCH),
                "LC_ALL": "C",
                "TZ": "UTC",
            }
        )
        command = [
            str(compiler.resolve()),
            "compile",
            ENTRYPOINT.as_posix(),
            "--root",
            str(staging),
            "--output",
            output.as_posix(),
            "--manifest",
            manifest.as_posix(),
            "--source-map",
            source_map.as_posix(),
        ]
        result = subprocess.run(
            command,
            cwd=staging,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise ModularBuildError(
                "Hyperprompt build failed: "
                + (result.stderr.strip() or result.stdout.strip())
            )
        return (
            (staging / output).read_bytes(),
            (staging / manifest).read_bytes(),
            _compact_source_map((staging / source_map).read_bytes()),
        )


def _verify_compiler(root: Path, compiler: Path) -> str:
    lock = validate_lock(root)
    verify_compiler(compiler, root=root)
    return lock["release"]["commit"]


def build(root: Path, compiler: Path) -> None:
    """Regenerate the aggregate and its committed provenance sidecars."""

    root = root.resolve(strict=True)
    _verify_compiler(root, compiler)
    output, manifest, source_map = _compile(root, compiler)
    catalog = _json(root / CATALOG_PATH)
    aggregate = catalog["aggregate"]
    artifacts = (
        (Path(aggregate["path"]), output),
        (Path(aggregate["assembly"]["manifest"]), manifest),
        (Path(aggregate["assembly"]["source_map"]), source_map),
    )
    for path, content in artifacts:
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def check(root: Path, compiler: Path) -> None:
    """Rebuild twice and compare every authoritative generated artifact."""

    root = root.resolve(strict=True)
    revision = _verify_compiler(root, compiler)
    first = _compile(root, compiler)
    second = _compile(root, compiler)
    if first != second:
        raise ModularBuildError(
            "two clean Hyperprompt builds are not byte-identical"
        )
    catalog = _json(root / CATALOG_PATH)
    aggregate = catalog["aggregate"]
    expected = (
        (root / aggregate["path"]).read_bytes(),
        (root / aggregate["assembly"]["manifest"]).read_bytes(),
        (root / aggregate["assembly"]["source_map"]).read_bytes(),
    )
    if first != expected:
        raise ModularBuildError(
            "generated aggregate, manifest, or source map is stale"
        )
    if aggregate["assembly"]["compiler_revision"] != revision:
        raise ModularBuildError("catalog compiler revision does not match lock")
    if _sha256(first[0]) != aggregate["sha256"]:
        raise ModularBuildError("catalog aggregate digest is stale")
    source_map = json.loads(first[2])
    if source_map.get("outputSha256") != aggregate["sha256"]:
        raise ModularBuildError("source-map output digest is stale")
    mappings = source_map.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ModularBuildError("source map has no output coverage")
    next_line = 1
    for mapping in mappings:
        start = mapping.get("generatedStartLine")
        end = mapping.get("generatedEndLine")
        if start != next_line or not isinstance(end, int) or end < start:
            raise ModularBuildError(
                "source-map output coverage is not contiguous"
            )
        next_line = end + 1
    if next_line - 1 != len(first[0].splitlines()):
        raise ModularBuildError(
            "source-map output coverage does not match aggregate lines"
        )
    selected_sources = {
        item["source_path"] for item in catalog["documents"]
    }
    mapped_sources = {
        item["source"]["path"]
        for item in mappings
        if item.get("kind") == "markdown"
        and isinstance(item.get("source"), dict)
    }
    if mapped_sources != selected_sources:
        raise ModularBuildError(
            "source map does not cover exactly the selected module sources"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "check"))
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
    compiler = (
        args.compiler
        if args.compiler.is_absolute()
        else root / args.compiler
    )
    try:
        if args.command == "build":
            build(root, compiler)
            print("authoritative modular aggregate regenerated")
        else:
            check(root, compiler)
            print("authoritative modular aggregate is reproducible and current")
    except (ModularBuildError, OSError, subprocess.TimeoutExpired) as error:
        print(f"modular publication error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
