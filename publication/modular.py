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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication.assembly.check import (  # noqa: E402
    LOCK_PATH,
    LOCK_SCHEMA_PATH,
    validate_lock,
    verify_compiler,
)
from publication.aggregate_links import (  # noqa: E402
    AggregateLinkError,
    LINK_POLICY,
    markdown_anchor_ids,
    markdown_link_destinations,
    rebase_aggregate_links,
    validate_aggregate_destinations,
)


CATALOG_PATH = Path("publication/document-set.json")
ENTRYPOINT = Path("publication/modular/root.hc")
SOURCE_DATE_EPOCH = 1_700_000_000


class ModularBuildError(ValueError):
    """The authoritative modular build is incomplete or stale."""


@dataclass(frozen=True)
class _BuildLayout:
    """Validated repository-relative paths used by one catalog snapshot."""

    entrypoint: Path
    sources: tuple[Path, ...]
    output: Path
    manifest: Path
    source_map: Path

    @property
    def artifacts(self) -> tuple[Path, Path, Path]:
        return self.output, self.manifest, self.source_map


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ModularBuildError(f"cannot load {path}: {error}") from error


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _repo_path(
    root: Path,
    value: Any,
    *,
    label: str,
    must_exist: bool,
) -> Path:
    """Return one normalized path after proving repository containment."""

    if not isinstance(value, str) or "\\" in value:
        raise ModularBuildError(
            f"{label} must be a normalized repository-relative POSIX path"
        )
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != value
    ):
        raise ModularBuildError(
            f"{label} must be a normalized repository-relative POSIX path"
        )
    relative = Path(*pure.parts)
    candidate = root / relative
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ModularBuildError(
            f"{label} escapes the repository: {value!r}"
        ) from error
    if must_exist and not resolved.is_file():
        raise ModularBuildError(
            f"{label} does not resolve to a regular file: {value!r}"
        )
    if not must_exist and candidate.exists() and not resolved.is_file():
        raise ModularBuildError(
            f"{label} resolves to a non-file artifact: {value!r}"
        )
    return relative


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _build_layout(
    root: Path,
    catalog: Any,
    *,
    require_artifacts: bool,
    compiler: Path | None = None,
) -> _BuildLayout:
    """Validate every build path before source or toolchain access."""

    if not isinstance(catalog, Mapping):
        raise ModularBuildError("publication catalog must be a JSON object")
    if catalog.get("publication_mode") != "modular":
        raise ModularBuildError("authoritative assembly requires modular mode")
    try:
        documents = catalog["documents"]
        aggregate = catalog["aggregate"]
        assembly = aggregate["assembly"]
        if (
            not isinstance(documents, list)
            or not isinstance(aggregate, Mapping)
            or not isinstance(assembly, Mapping)
        ):
            raise TypeError
        ordered_documents = sorted(
            documents, key=lambda item: item["publication_order"]
        )
    except (KeyError, TypeError) as error:
        raise ModularBuildError(
            "publication catalog lacks a valid modular build layout"
        ) from error

    entrypoint = _repo_path(
        root,
        assembly.get("entrypoint"),
        label="modular entrypoint",
        must_exist=True,
    )
    if entrypoint != ENTRYPOINT:
        raise ModularBuildError(
            f"modular entrypoint must be {ENTRYPOINT.as_posix()!r}"
        )
    sources = tuple(
        _repo_path(
            root,
            document.get("source_path")
            if isinstance(document, Mapping)
            else None,
            label=f"modular source {index}",
            must_exist=True,
        )
        for index, document in enumerate(ordered_documents)
    )
    if len(set(sources)) != len(sources):
        raise ModularBuildError("modular source paths must be unique")

    output = _repo_path(
        root,
        aggregate.get("path"),
        label="modular aggregate output",
        must_exist=require_artifacts,
    )
    manifest = _repo_path(
        root,
        assembly.get("manifest"),
        label="modular manifest output",
        must_exist=require_artifacts,
    )
    source_map = _repo_path(
        root,
        assembly.get("source_map"),
        label="modular source-map output",
        must_exist=require_artifacts,
    )
    artifacts = (output, manifest, source_map)
    artifact_targets = tuple(
        (root / path).resolve(strict=False) for path in artifacts
    )
    if len(set(artifact_targets)) != len(artifact_targets):
        raise ModularBuildError("modular artifact output paths must be distinct")
    for index, left in enumerate(artifact_targets):
        for right in artifact_targets[index + 1 :]:
            if _paths_overlap(left, right):
                raise ModularBuildError(
                    "modular artifact output paths must not contain one another"
                )

    protected = {
        (root / path).resolve(strict=False)
        for path in (
            CATALOG_PATH,
            LOCK_PATH,
            LOCK_SCHEMA_PATH,
            entrypoint,
            *sources,
        )
    }
    if compiler is not None:
        protected.add(compiler.resolve(strict=False))
    collisions = [
        path.as_posix()
        for path, target in zip(artifacts, artifact_targets, strict=True)
        if any(_paths_overlap(target, item) for item in protected)
    ]
    if collisions:
        raise ModularBuildError(
            "modular artifact output collides with an input: "
            + ", ".join(collisions)
        )
    return _BuildLayout(
        entrypoint=entrypoint,
        sources=sources,
        output=output,
        manifest=manifest,
        source_map=source_map,
    )


def _compact_source_map(content: bytes, *, output_sha256: str) -> bytes:
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
        "outputSha256": output_sha256,
        "mappings": ranges,
    }
    return (
        json.dumps(compact, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _compile(
    root: Path,
    compiler: Path,
    *,
    catalog: Any | None = None,
    layout: _BuildLayout | None = None,
) -> tuple[bytes, bytes, bytes]:
    if catalog is None:
        catalog = _json(root / CATALOG_PATH)
    if layout is None:
        layout = _build_layout(
            root,
            catalog,
            require_artifacts=False,
            compiler=compiler,
        )
    expected_root = "\n".join(
        f'{"    " if index else ""}"{path.as_posix()}"'
        for index, path in enumerate(layout.sources)
    ) + "\n"
    actual_root = (root / layout.entrypoint).read_text(encoding="utf-8")
    if actual_root != expected_root:
        raise ModularBuildError(
            "Hyperprompt entrypoint does not exactly match catalog order"
        )

    with tempfile.TemporaryDirectory(prefix="asp-modular-publication-") as name:
        staging = Path(name)
        staged_entrypoint = staging / layout.entrypoint
        staged_entrypoint.parent.mkdir(parents=True)
        staged_entrypoint.write_text(actual_root, encoding="utf-8")
        for source in layout.sources:
            destination = staging / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / source, destination)

        for artifact in layout.artifacts:
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
            layout.entrypoint.as_posix(),
            "--root",
            str(staging),
            "--output",
            layout.output.as_posix(),
            "--manifest",
            layout.manifest.as_posix(),
            "--source-map",
            layout.source_map.as_posix(),
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
        raw_output = (staging / layout.output).read_bytes()
        raw_source_map_content = (staging / layout.source_map).read_bytes()
        raw_source_map = json.loads(raw_source_map_content)
        policy = catalog.get("assembly_policy", {}).get(
            "aggregate_links"
        )
        if policy != LINK_POLICY:
            raise ModularBuildError(
                f"unsupported aggregate link policy: {policy!r}"
            )
        source_contents = {
            path.as_posix(): (staging / path).read_bytes()
            for path in layout.sources
        }
        try:
            output = rebase_aggregate_links(
                raw_output,
                raw_source_map,
                source_contents,
                output_path=layout.output.as_posix(),
            )
            validate_aggregate_destinations(
                output,
                source_contents,
                source_order=[
                    path.as_posix() for path in layout.sources
                ],
                output_path=layout.output.as_posix(),
            )
        except (AggregateLinkError, UnicodeDecodeError) as error:
            raise ModularBuildError(
                f"aggregate link transform failed: {error}"
            ) from error
        return (
            output,
            (staging / layout.manifest).read_bytes(),
            _compact_source_map(
                raw_source_map_content,
                output_sha256=_sha256(output),
            ),
        )


def _verify_compiler(root: Path, compiler: Path) -> str:
    lock = validate_lock(root)
    verify_compiler(compiler, root=root)
    return lock["release"]["commit"]


def _validate_local_link_targets(
    root: Path,
    layout: _BuildLayout,
    output: bytes,
) -> None:
    output_parent = (root / layout.output).parent
    try:
        destinations = markdown_link_destinations(output)
    except (AggregateLinkError, UnicodeDecodeError) as error:
        raise ModularBuildError(
            f"aggregate link validation failed: {error}"
        ) from error
    anchor_cache: dict[Path, set[str]] = {}
    for destination in destinations:
        try:
            parsed = urlsplit(destination)
        except ValueError as error:
            raise ModularBuildError(
                f"invalid aggregate Markdown link: {destination!r}"
            ) from error
        if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
            continue
        link_path = unquote(parsed.path)
        target = (
            (output_parent / link_path).resolve(strict=False)
            if link_path
            else root / layout.output
        )
        try:
            target.relative_to(root)
        except ValueError as error:
            raise ModularBuildError(
                f"aggregate Markdown link escapes the repository: {link_path!r}"
            ) from error
        if not target.is_file():
            raise ModularBuildError(
                f"aggregate Markdown link target does not exist: {link_path!r}"
            )
        if parsed.fragment:
            anchors = anchor_cache.get(target)
            if anchors is None:
                try:
                    anchors = markdown_anchor_ids(target.read_bytes())
                except AggregateLinkError as error:
                    raise ModularBuildError(
                        f"cannot validate aggregate Markdown fragment: {error}"
                    ) from error
                anchor_cache[target] = anchors
            fragment = unquote(parsed.fragment)
            if fragment not in anchors:
                raise ModularBuildError(
                    "aggregate Markdown link fragment does not exist: "
                    f"{destination!r}"
                )


def build(root: Path, compiler: Path) -> None:
    """Regenerate the aggregate and its committed provenance sidecars."""

    root = root.resolve(strict=True)
    catalog = _json(root / CATALOG_PATH)
    layout = _build_layout(
        root,
        catalog,
        require_artifacts=False,
        compiler=compiler,
    )
    _verify_compiler(root, compiler)
    generated = _compile(
        root,
        compiler,
        catalog=catalog,
        layout=layout,
    )
    _validate_local_link_targets(root, layout, generated[0])
    for path, content in zip(layout.artifacts, generated, strict=True):
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def check(root: Path, compiler: Path) -> None:
    """Rebuild twice and compare every authoritative generated artifact."""

    root = root.resolve(strict=True)
    catalog = _json(root / CATALOG_PATH)
    layout = _build_layout(
        root,
        catalog,
        require_artifacts=True,
        compiler=compiler,
    )
    revision = _verify_compiler(root, compiler)
    first = _compile(root, compiler, catalog=catalog, layout=layout)
    second = _compile(root, compiler, catalog=catalog, layout=layout)
    if first != second:
        raise ModularBuildError(
            "two clean Hyperprompt builds are not byte-identical"
        )
    aggregate = catalog["aggregate"]
    expected = tuple((root / path).read_bytes() for path in layout.artifacts)
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
    selected_sources = {path.as_posix() for path in layout.sources}
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
    _validate_local_link_targets(root, layout, first[0])


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
