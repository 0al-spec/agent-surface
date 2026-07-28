#!/usr/bin/env python3
"""Validate and stage non-authoritative ASP assembly candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform as host_platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = Path("publication/assembly/hyperprompt.lock.json")
LOCK_SCHEMA_PATH = Path("publication/assembly/hyperprompt.lock.schema.json")
CANDIDATE_SCHEMA_PATH = Path("publication/assembly/candidate.schema.json")
PLATFORM_REPORT_SCHEMA_PATH = Path(
    "publication/assembly/platform-report.schema.json"
)
CROSS_PLATFORM_REPORT_SCHEMA_PATH = Path(
    "publication/assembly/cross-platform-report.schema.json"
)
CATALOG_PATH = Path("publication/document-set.json")
CANDIDATES_PATH = Path("publication/candidates")

EXPECTED_PLATFORMS = {
    "linux-amd64": ("linux", "x86_64", "static-swift-stdlib"),
    "macos-arm64": ("macos", "arm64", "platform-default"),
}
MEDIA_SUFFIXES = {
    "hypercode": ".hc",
    "markdown": ".md",
    "cascade": ".hcs",
}
ATX_HEADING = re.compile(rb"^( {0,3})(#{1,6})(?=[ \t]|$)")
FENCE_OPEN = re.compile(rb"^( {0,3})(`{3,}|~{3,})(.*)$")
GIT_OBJECT_ID = re.compile(r"^[0-9a-f]{40}$")


class AssemblyError(ValueError):
    """The candidate assembly contract is invalid."""


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AssemblyError(f"duplicate JSON object member: {key!r}")
        result[key] = value
    return result


def loads_strict_json(text: str, *, source: str) -> Any:
    """Load JSON while rejecting duplicate object members."""

    try:
        return json.loads(text, object_pairs_hook=_strict_object)
    except AssemblyError:
        raise
    except json.JSONDecodeError as error:
        raise AssemblyError(f"{source} is not valid JSON: {error}") from error


def _load_json(path: Path) -> Any:
    try:
        return loads_strict_json(path.read_text(encoding="utf-8"), source=str(path))
    except OSError as error:
        raise AssemblyError(f"cannot read {path}: {error}") from error


def _validate_schema(instance: Any, schema: Any, *, label: str) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise AssemblyError(f"{label} schema is invalid: {error.message}") from error

    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise AssemblyError(f"{label} schema violation at {location}: {error.message}")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as error:
        raise AssemblyError(f"cannot read {path}: {error}") from error


def _relative_path(value: Any, *, label: str) -> PurePosixPath:
    if not isinstance(value, str) or "\\" in value:
        raise AssemblyError(f"{label} must be a normalized relative POSIX path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise AssemblyError(f"{label} must be a normalized relative POSIX path")
    return path


def _inside(path: Path, parent: Path, *, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(parent.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise AssemblyError(f"{label} escapes its declared root") from error
    return resolved


def _validate_staged_paths(
    entries: Sequence[tuple[str, PurePosixPath]],
) -> None:
    """Reject file paths that are equal or ancestors of other staged files."""

    for index, (left_label, left) in enumerate(entries):
        for right_label, right in entries[index + 1 :]:
            if left == right or left in right.parents or right in left.parents:
                raise AssemblyError(
                    "staged path collision between "
                    f"{left_label}={left.as_posix()!r} and "
                    f"{right_label}={right.as_posix()!r}"
                )


def validate_lock(root: Path = ROOT) -> Mapping[str, Any]:
    """Validate the exact Hyperprompt release and artifact lock."""

    schema_path = root / LOCK_SCHEMA_PATH
    lock_path = root / LOCK_PATH
    if schema_path.is_symlink() or not schema_path.is_file():
        raise AssemblyError("Hyperprompt lock schema must be a regular file")
    if lock_path.is_symlink() or not lock_path.is_file():
        raise AssemblyError("Hyperprompt lock must be a regular file")
    schema = _load_json(schema_path)
    lock = _load_json(lock_path)
    _validate_schema(lock, schema, label="Hyperprompt lock")
    if not isinstance(lock, Mapping):
        raise AssemblyError("Hyperprompt lock must be a JSON object")

    release = lock["release"]
    if not isinstance(release, Mapping):
        raise AssemblyError("Hyperprompt release must be a JSON object")
    version = release["version"]
    tag = f"v{version}"
    expected_release_url = f"{lock['repository']}/releases/tag/{tag}"
    if release["tag"] != tag:
        raise AssemblyError("Hyperprompt tag does not match the locked version")
    if release["url"] != expected_release_url:
        raise AssemblyError("Hyperprompt release URL does not match the locked tag")

    artifacts = lock["artifacts"]
    if not isinstance(artifacts, Sequence) or isinstance(artifacts, (str, bytes)):
        raise AssemblyError("Hyperprompt artifacts must be an array")
    by_platform: dict[str, Mapping[str, Any]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise AssemblyError("Hyperprompt artifact must be a JSON object")
        platform = artifact["platform"]
        if platform in by_platform:
            raise AssemblyError(f"duplicate Hyperprompt platform: {platform}")
        by_platform[platform] = artifact

    if set(by_platform) != set(EXPECTED_PLATFORMS):
        raise AssemblyError(
            "Hyperprompt lock must pin exactly linux-amd64 and macos-arm64"
        )

    for platform, artifact in by_platform.items():
        os_name, arch, linkage = EXPECTED_PLATFORMS[platform]
        asset = f"hyperprompt-{version}-{platform}.tar.gz"
        archive_root = f"hyperprompt-{version}-{platform}"
        expected_url = f"{lock['repository']}/releases/download/{tag}/{asset}"
        if (
            artifact["os"] != os_name
            or artifact["arch"] != arch
            or artifact["linkage"] != linkage
        ):
            raise AssemblyError(
                f"Hyperprompt metadata does not match platform {platform}"
            )
        if artifact["asset"] != asset or artifact["archive_root"] != archive_root:
            raise AssemblyError(
                f"Hyperprompt archive identity is invalid for {platform}"
            )
        if artifact["url"] != expected_url:
            raise AssemblyError(f"Hyperprompt asset URL is invalid for {platform}")

    return lock


def _load_catalog(root: Path) -> Mapping[str, Any]:
    catalog = _load_json(root / CATALOG_PATH)
    if not isinstance(catalog, Mapping):
        raise AssemblyError("publication catalog must be a JSON object")
    if catalog.get("publication_mode") != "transitional_monolith":
        raise AssemblyError(
            "assembly candidates require transitional_monolith publication mode"
        )
    aggregate = catalog.get("aggregate")
    if not isinstance(aggregate, Mapping) or aggregate.get("generated") is not False:
        raise AssemblyError(
            "the canonical aggregate must remain a non-generated monolith"
        )
    return catalog


def _candidate_directory(root: Path, path: Path, candidate_id: str) -> Path:
    expected = root / CANDIDATES_PATH / candidate_id / "candidate.json"
    if path.is_symlink() or expected.parent.is_symlink():
        raise AssemblyError("candidate descriptor and directory must not be symlinks")
    try:
        if path.resolve(strict=True) != expected.resolve(strict=True):
            raise AssemblyError(
                "candidate descriptor must be publication/candidates/"
                f"{candidate_id}/candidate.json"
            )
    except OSError as error:
        raise AssemblyError(f"cannot resolve candidate descriptor {path}") from error
    return expected.parent


def _canonical_bytes(
    root: Path,
    candidate: Mapping[str, Any],
    catalog: Mapping[str, Any],
) -> bytes:
    canonical = candidate["canonical"]
    aggregate = catalog["aggregate"]
    if not isinstance(canonical, Mapping) or not isinstance(aggregate, Mapping):
        raise AssemblyError("canonical publication metadata is invalid")
    if canonical["path"] != aggregate.get("path") or canonical[
        "sha256"
    ] != aggregate.get("sha256"):
        raise AssemblyError(
            "candidate canonical identity does not match the publication catalog"
        )
    canonical_path = root / _relative_path(
        canonical["path"],
        label="canonical.path",
    )
    try:
        content = canonical_path.read_bytes()
    except OSError as error:
        raise AssemblyError(f"cannot read canonical source {canonical_path}") from error
    actual = _sha256_bytes(content)
    if actual != canonical["sha256"]:
        raise AssemblyError(
            f"canonical source digest mismatch: expected {canonical['sha256']}, "
            f"got {actual}"
        )
    return content


def promote_atx_headings_one_level(content: bytes) -> bytes:
    """Remove one ATX marker outside ordinary CommonMark fences."""

    output: list[bytes] = []
    active_fence: tuple[bytes, int] | None = None
    for line in content.splitlines(keepends=True):
        body = line.rstrip(b"\r\n")
        if active_fence is not None:
            marker, length = active_fence
            stripped = body.lstrip(b" ")
            indent = len(body) - len(stripped)
            count = len(stripped) - len(stripped.lstrip(marker))
            remainder = stripped[count:]
            if (
                indent <= 3
                and count >= length
                and remainder.strip(b" \t") == b""
            ):
                active_fence = None
            output.append(line)
            continue

        opening = FENCE_OPEN.match(body)
        if opening is not None:
            fence = opening.group(2)
            remainder = opening.group(3)
            if fence[:1] == b"~" or b"`" not in remainder:
                active_fence = (fence[:1], len(fence))
            output.append(line)
            continue

        heading = ATX_HEADING.match(body)
        if heading is None:
            output.append(line)
            continue
        hashes = heading.group(2)
        if len(hashes) == 1:
            raise AssemblyError("cannot promote an ATX level-1 heading")
        marker_end = heading.end(2)
        output.append(line[: marker_end - 1] + line[marker_end:])
    return b"".join(output)


def _canonical_derivation_bytes(
    canonical: bytes,
    extraction: Mapping[str, Any],
    *,
    label: str,
) -> bytes:
    if extraction["source_path"] != "drafts/agent-surface.md":
        raise AssemblyError(f"{label} is not bound to the canonical source")
    start = extraction["start_byte"]
    end = extraction["end_byte"]
    if start >= end or end > len(canonical):
        raise AssemblyError(f"{label} has an invalid byte range")
    if start and canonical[start - 1 : start] != b"\n":
        raise AssemblyError(f"{label} does not start on a line boundary")
    if end < len(canonical) and canonical[end - 1 : end] != b"\n":
        raise AssemblyError(f"{label} does not end on a line boundary")

    content = canonical[start:end]
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AssemblyError(f"{label} splits UTF-8 text") from error

    transform = extraction.get("transform", "identity")
    if transform == "promote_atx_headings_one_level":
        transformed = promote_atx_headings_one_level(content)
    elif transform == "identity":
        transformed = content
    else:
        raise AssemblyError(f"{label} uses an unsupported transform")
    if transformed.count(b"\n") != content.count(b"\n"):
        raise AssemblyError(f"{label} transform changed line coverage")
    return transformed


def _source_bytes(
    root: Path,
    candidate_dir: Path,
    candidate: Mapping[str, Any],
    canonical: bytes,
) -> dict[str, bytes]:
    sources = candidate["sources"]
    if not isinstance(sources, Mapping):
        raise AssemblyError("candidate sources must be a JSON object")
    declared = sources["declared"]
    if not isinstance(declared, Sequence) or isinstance(declared, (str, bytes)):
        raise AssemblyError("candidate declared sources must be an array")

    committed_root = candidate_dir / str(sources["committed_root"])
    if committed_root.is_symlink():
        raise AssemblyError("candidate committed source root must not be a symlink")
    try:
        committed_root_resolved = committed_root.resolve(strict=True)
    except OSError as error:
        raise AssemblyError(
            f"candidate committed source root is missing: {committed_root}"
        ) from error
    if not committed_root_resolved.is_dir():
        raise AssemblyError("candidate committed source root must be a directory")

    expected_committed: set[str] = set()
    materialized: dict[str, bytes] = {}
    for index, source in enumerate(declared):
        if not isinstance(source, Mapping):
            raise AssemblyError(f"candidate source {index} must be a JSON object")
        stage_path = _relative_path(
            source["path"], label=f"sources.declared[{index}].path"
        )
        stage_name = stage_path.as_posix()
        if stage_name in materialized:
            raise AssemblyError(f"duplicate staged source path: {stage_name}")

        suffix = MEDIA_SUFFIXES[source["media_type"]]
        if not stage_name.endswith(suffix):
            raise AssemblyError(
                f"source {stage_name!r} does not match media type "
                f"{source['media_type']!r}"
            )

        if source["origin"] == "committed_candidate":
            repository_path = _relative_path(
                source["repository_path"],
                label=f"sources.declared[{index}].repository_path",
            )
            source_path = root / repository_path
            resolved = _inside(
                source_path,
                committed_root_resolved,
                label=f"committed source {repository_path}",
            )
            if source_path.is_symlink() or not resolved.is_file():
                raise AssemblyError(
                    f"committed source must be a regular non-symlink file: "
                    f"{repository_path}"
                )
            expected_committed.add(repository_path.as_posix())
            try:
                content = resolved.read_bytes()
            except OSError as error:
                raise AssemblyError(
                    f"cannot read committed source {source_path}"
                ) from error
            canonical_derivation = source.get("canonical_derivation")
            if canonical_derivation is not None:
                expected = _canonical_derivation_bytes(
                    canonical,
                    canonical_derivation,
                    label=f"committed source {stage_name!r}",
                )
                if content != expected:
                    raise AssemblyError(
                        f"committed source {stage_name!r} is stale relative "
                        "to its canonical derivation"
                    )
        else:
            extraction = source["extraction"]
            if not isinstance(extraction, Mapping):
                raise AssemblyError(f"derived source {stage_name!r} has no extraction")
            content = _canonical_derivation_bytes(
                canonical,
                extraction,
                label=f"derived source {stage_name!r}",
            )

        actual = _sha256_bytes(content)
        if actual != source["sha256"]:
            raise AssemblyError(
                f"source {stage_name!r} digest mismatch: "
                f"expected {source['sha256']}, got {actual}"
            )
        materialized[stage_name] = content

    actual_committed: set[str] = set()
    unexpected_candidate_files: list[str] = []
    for path in candidate_dir.rglob("*"):
        if path.is_symlink():
            raise AssemblyError(f"candidate source tree contains symlink: {path}")
        if path.is_file():
            if path == candidate_dir / "candidate.json":
                continue
            try:
                path.relative_to(committed_root)
            except ValueError:
                unexpected_candidate_files.append(path.relative_to(root).as_posix())
            else:
                actual_committed.add(path.relative_to(root).as_posix())
    if unexpected_candidate_files:
        raise AssemblyError(
            "unexpected files outside the committed source root: "
            + ", ".join(sorted(unexpected_candidate_files))
        )
    undeclared = sorted(actual_committed - expected_committed)
    missing = sorted(expected_committed - actual_committed)
    if undeclared or missing:
        details: list[str] = []
        if undeclared:
            details.append(f"undeclared committed sources: {', '.join(undeclared)}")
        if missing:
            details.append(f"missing committed sources: {', '.join(missing)}")
        raise AssemblyError("; ".join(details))

    entrypoint = _relative_path(sources["entrypoint"], label="sources.entrypoint")
    if entrypoint.as_posix() not in materialized:
        raise AssemblyError("candidate entrypoint is not a declared source")
    entry = next(
        source for source in declared if source["path"] == entrypoint.as_posix()
    )
    if entry["media_type"] != "hypercode":
        raise AssemblyError("candidate entrypoint must be Hypercode")
    return materialized


def validate_candidate(
    root: Path,
    path: Path,
    *,
    lock: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Validate one non-authoritative candidate and its complete source closure."""

    schema = _load_json(root / CANDIDATE_SCHEMA_PATH)
    candidate = _load_json(path)
    _validate_schema(candidate, schema, label=f"assembly candidate {path}")
    if not isinstance(candidate, Mapping):
        raise AssemblyError("assembly candidate must be a JSON object")

    candidate_dir = _candidate_directory(root, path, candidate["candidate_id"])
    catalog = _load_catalog(root)
    active_lock = lock if lock is not None else validate_lock(root)
    lock_path = root / _relative_path(
        candidate["compiler"]["lock_path"],
        label="compiler.lock_path",
    )
    actual_lock_sha = _sha256_file(lock_path)
    if candidate["compiler"]["lock_sha256"] != actual_lock_sha:
        raise AssemblyError(
            "candidate compiler lock digest does not match the locked toolchain"
        )
    if active_lock != _load_json(lock_path):
        raise AssemblyError(
            "candidate compiler lock is not the validated toolchain lock"
        )

    canonical = _canonical_bytes(root, candidate, catalog)
    _source_bytes(root, candidate_dir, candidate, canonical)

    assembly = candidate["assembly"]
    staged_paths = [
        (
            f"sources.declared[{index}].path",
            _relative_path(
                source["path"],
                label=f"sources.declared[{index}].path",
            ),
        )
        for index, source in enumerate(candidate["sources"]["declared"])
    ]
    staged_paths.extend(
        (
            f"assembly.{key}",
            _relative_path(assembly[key], label=f"assembly.{key}"),
        )
        for key in ("output", "manifest", "source_map")
    )
    _validate_staged_paths(staged_paths)
    if candidate["expected"]["aggregate_sha256"] != candidate["canonical"]["sha256"]:
        raise AssemblyError(
            "byte-identical candidate expectation must equal the canonical digest"
        )
    return candidate


def discover_candidates(root: Path = ROOT) -> list[Path]:
    """Return candidate descriptors while rejecting undeclared candidate entries."""

    candidates_root = root / CANDIDATES_PATH
    if not candidates_root.exists():
        return []
    if candidates_root.is_symlink() or not candidates_root.is_dir():
        raise AssemblyError("publication/candidates must be a regular directory")

    descriptors: list[Path] = []
    for entry in sorted(candidates_root.iterdir(), key=lambda item: item.name):
        if entry.is_symlink() or not entry.is_dir():
            raise AssemblyError(
                f"unexpected entry in publication/candidates: {entry.name}"
            )
        descriptor = entry / "candidate.json"
        if not descriptor.is_file() or descriptor.is_symlink():
            raise AssemblyError(
                f"candidate directory {entry.name!r} has no regular candidate.json"
            )
        descriptors.append(descriptor)
    return descriptors


def require_empty_staging(path: Path) -> None:
    """Fail unless path is an existing, empty, non-symlink directory."""

    if path.is_symlink() or not path.is_dir():
        raise AssemblyError(f"staging path must be a regular directory: {path}")
    try:
        first_entry = next(path.iterdir(), None)
    except OSError as error:
        raise AssemblyError(f"cannot inspect staging directory {path}") from error
    if first_entry is not None:
        raise AssemblyError(f"staging directory is not empty: {path}")


@contextmanager
def disposable_staging(parent: Path | None = None) -> Iterator[Path]:
    """Yield a fresh staging directory and remove it on every exit path."""

    parent_text = str(parent) if parent is not None else None
    try:
        path = Path(
            tempfile.mkdtemp(
                prefix="asp-publication-assembly-",
                dir=parent_text,
            )
        )
    except OSError as error:
        raise AssemblyError("cannot create disposable staging directory") from error
    try:
        require_empty_staging(path)
        yield path
    finally:
        try:
            shutil.rmtree(path)
        except OSError as error:
            raise AssemblyError(
                f"cannot remove disposable staging directory {path}"
            ) from error


def materialize_candidate(
    root: Path,
    candidate_path: Path,
    staging: Path,
) -> Mapping[str, Any]:
    """Copy or derive every declared input into a verified empty staging root."""

    require_empty_staging(staging)
    candidate = validate_candidate(root, candidate_path)
    canonical = _canonical_bytes(root, candidate, _load_catalog(root))
    candidate_dir = candidate_path.parent
    sources = _source_bytes(root, candidate_dir, candidate, canonical)
    for relative, content in sources.items():
        destination = staging / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    return candidate


def _artifact_for_platform(
    lock: Mapping[str, Any],
    platform_name: str,
) -> Mapping[str, Any]:
    artifact = next(
        (item for item in lock["artifacts"] if item["platform"] == platform_name),
        None,
    )
    if artifact is None:
        raise AssemblyError(f"platform is not locked: {platform_name}")
    return artifact


def _host_platform() -> str:
    system = host_platform.system().lower()
    machine = host_platform.machine().lower()
    if system == "darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm64"
    if system == "linux" and machine in {"x86_64", "amd64"}:
        return "linux-amd64"
    raise AssemblyError(f"unsupported Hyperprompt host: {system}-{machine}")


def verify_archive(
    archive_path: Path,
    platform: str,
    *,
    root: Path = ROOT,
) -> bytes:
    """Verify a downloaded Hyperprompt release archive without extracting it."""

    lock = validate_lock(root)
    artifact = _artifact_for_platform(lock, platform)
    try:
        actual_size = archive_path.stat().st_size
    except OSError as error:
        raise AssemblyError(f"cannot inspect {archive_path}: {error}") from error
    if actual_size != artifact["size"]:
        raise AssemblyError(
            f"Hyperprompt archive size mismatch for {platform}: "
            f"expected {artifact['size']}, got {actual_size}"
        )
    actual_sha = _sha256_file(archive_path)
    if actual_sha != artifact["sha256"]:
        raise AssemblyError(
            f"Hyperprompt archive digest mismatch for {platform}: "
            f"expected {artifact['sha256']}, got {actual_sha}"
        )

    required_files = {
        "hyperprompt",
        "README.md",
        "LICENSE",
        "hyperprompt-artifact.json",
    }
    archive_root = PurePosixPath(artifact["archive_root"])
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            files: dict[str, tarfile.TarInfo] = {}
            directories: set[str] = set()
            for member in archive.getmembers():
                member_path = PurePosixPath(member.name)
                normalized_name = (
                    member.name.rstrip("/") if member.isdir() else member.name
                )
                if (
                    member_path.is_absolute()
                    or any(part in {"", ".", ".."} for part in member_path.parts)
                    or member_path.as_posix() != normalized_name
                    or not member_path.is_relative_to(archive_root)
                    or member.issym()
                    or member.islnk()
                ):
                    raise AssemblyError(
                        f"unsafe Hyperprompt archive member: {member.name}"
                    )
                if not member.isfile() and not member.isdir():
                    raise AssemblyError(
                        f"unsupported Hyperprompt archive member: {member.name}"
                    )
                if member.isfile():
                    relative = member_path.relative_to(archive_root).as_posix()
                    if relative in files:
                        raise AssemblyError(
                            f"duplicate Hyperprompt archive member: {member.name}"
                        )
                    files[relative] = member
                else:
                    relative = member_path.relative_to(archive_root).as_posix()
                    if relative in directories:
                        raise AssemblyError(
                            f"duplicate Hyperprompt archive member: {member.name}"
                        )
                    directories.add(relative)

            if set(files) != required_files:
                raise AssemblyError(
                    "Hyperprompt archive file set is not the locked release layout"
                )
            if directories != {"."}:
                raise AssemblyError(
                    "Hyperprompt archive directory set is not the locked release layout"
                )
            if not files["hyperprompt"].mode & 0o111:
                raise AssemblyError("Hyperprompt archive binary is not executable")

            binary_file = archive.extractfile(files["hyperprompt"])
            if binary_file is None:
                raise AssemblyError("cannot read Hyperprompt binary")
            binary = binary_file.read()
            actual_binary_sha = _sha256_bytes(binary)
            if actual_binary_sha != artifact["binary_sha256"]:
                raise AssemblyError(
                    f"Hyperprompt binary digest mismatch for {platform}: "
                    f"expected {artifact['binary_sha256']}, got {actual_binary_sha}"
                )

            metadata_file = archive.extractfile(files["hyperprompt-artifact.json"])
            if metadata_file is None:
                raise AssemblyError("cannot read Hyperprompt artifact metadata")
            metadata = loads_strict_json(
                metadata_file.read().decode("utf-8"),
                source="hyperprompt-artifact.json",
            )
    except (OSError, tarfile.TarError, UnicodeDecodeError) as error:
        raise AssemblyError(f"cannot validate Hyperprompt archive: {error}") from error

    expected_metadata = {
        "artifact_kind": "hyperprompt_release_binary",
        "schema_version": 1,
        "binary": "hyperprompt",
        "compiler_version": lock["release"]["version"],
        "os": artifact["os"],
        "arch": artifact["arch"],
        "linkage": artifact["linkage"],
        "source_repository": "0al-spec/Hyperprompt",
        "source_commit": lock["release"]["commit"],
        "source_tag": lock["release"]["tag"],
    }
    if not isinstance(metadata, Mapping):
        raise AssemblyError("Hyperprompt artifact metadata must be a JSON object")
    for key, expected in expected_metadata.items():
        if metadata.get(key) != expected:
            raise AssemblyError(
                f"Hyperprompt artifact metadata {key!r} does not match the lock"
            )
    if set(metadata) != set(expected_metadata) | {"workflow_run_id"}:
        raise AssemblyError("Hyperprompt artifact metadata has an unexpected shape")
    if (
        not isinstance(metadata["workflow_run_id"], str)
        or not metadata["workflow_run_id"].isdigit()
    ):
        raise AssemblyError("Hyperprompt workflow_run_id must be a decimal string")
    return binary


def verify_compiler(
    compiler: Path,
    *,
    root: Path = ROOT,
    platform_name: str | None = None,
) -> Mapping[str, Any]:
    """Verify the installed binary identity and reported version."""

    if compiler.is_symlink() or not compiler.is_file():
        raise AssemblyError(f"Hyperprompt compiler must be a regular file: {compiler}")
    lock = validate_lock(root)
    platform_value = platform_name or _host_platform()
    artifact = _artifact_for_platform(lock, platform_value)
    actual = _sha256_file(compiler)
    if actual != artifact["binary_sha256"]:
        raise AssemblyError(
            f"Hyperprompt compiler digest mismatch for {platform_value}: "
            f"expected {artifact['binary_sha256']}, got {actual}"
        )
    try:
        result = subprocess.run(
            [str(compiler), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AssemblyError(f"cannot execute Hyperprompt compiler: {error}") from error
    if result.returncode != 0 or result.stdout.strip() != lock["release"]["version"]:
        raise AssemblyError(
            "Hyperprompt compiler version does not match the locked release"
        )
    return artifact


def install_toolchain(
    root: Path,
    destination: Path,
    *,
    platform_name: str | None = None,
) -> Path:
    """Download, verify, and atomically install the exact locked compiler."""

    platform_value = platform_name or _host_platform()
    lock = validate_lock(root)
    artifact = _artifact_for_platform(lock, platform_value)
    if destination.exists():
        verify_compiler(
            destination,
            root=root,
            platform_name=platform_value,
        )
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="hyperprompt-download-",
        dir=destination.parent,
    ) as temporary:
        archive_path = Path(temporary) / artifact["asset"]
        try:
            request = urllib.request.Request(
                artifact["url"],
                headers={"User-Agent": "agent-surface-publication-assembly/1"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                if not response.geturl().startswith("https://"):
                    raise AssemblyError("Hyperprompt download was redirected off HTTPS")
                content = response.read(artifact["size"] + 1)
        except (OSError, TimeoutError) as error:
            raise AssemblyError(f"cannot download Hyperprompt: {error}") from error
        if len(content) != artifact["size"]:
            raise AssemblyError(
                "downloaded Hyperprompt archive does not have the locked size"
            )
        archive_path.write_bytes(content)
        binary = verify_archive(archive_path, platform_value, root=root)
        temporary_binary = destination.with_name(destination.name + ".tmp")
        temporary_binary.write_bytes(binary)
        temporary_binary.chmod(0o755)
        os.replace(temporary_binary, destination)

    try:
        verify_compiler(
            destination,
            root=root,
            platform_name=platform_value,
        )
    except AssemblyError:
        destination.unlink(missing_ok=True)
        raise
    return destination


def _load_artifact_json(path: Path, *, label: str) -> Mapping[str, Any]:
    value = _load_json(path)
    if not isinstance(value, Mapping):
        raise AssemblyError(f"{label} must be a JSON object")
    return value


def _load_checked_schema(root: Path, relative: Path, *, label: str) -> Mapping[str, Any]:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise AssemblyError(f"{label} must be a regular file")
    schema = _load_json(path)
    if not isinstance(schema, Mapping):
        raise AssemblyError(f"{label} must be a JSON object")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise AssemblyError(f"{label} is invalid: {error.message}") from error
    return schema


def _run_git(root: Path, arguments: Sequence[str], *, label: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AssemblyError(f"cannot inspect {label}: {error}") from error
    if result.returncode != 0:
        raise AssemblyError(
            f"cannot inspect {label}: "
            + (result.stderr.strip() or result.stdout.strip())
        )
    return result.stdout.strip()


def require_clean_checkout(root: Path, source_revision: str) -> None:
    """Require an exact clean Git checkout at one immutable revision."""

    if GIT_OBJECT_ID.fullmatch(source_revision) is None:
        raise AssemblyError("source revision must be a lowercase 40-character Git id")
    top_level = Path(
        _run_git(root, ["rev-parse", "--show-toplevel"], label="Git checkout root")
    )
    try:
        if top_level.resolve(strict=True) != root.resolve(strict=True):
            raise AssemblyError("assembly root is not the Git checkout root")
    except OSError as error:
        raise AssemblyError("cannot resolve the Git checkout root") from error
    head = _run_git(root, ["rev-parse", "HEAD"], label="Git HEAD")
    if head != source_revision:
        raise AssemblyError(
            f"clean-checkout revision mismatch: expected {source_revision}, got {head}"
        )
    status = _run_git(
        root,
        ["status", "--porcelain=v1", "--untracked-files=all"],
        label="Git worktree",
    )
    if status:
        raise AssemblyError("assembly evidence requires a clean Git worktree")


def _write_new_report(root: Path, path: Path, report: Mapping[str, Any]) -> bytes:
    """Write one deterministic report outside the checkout without overwriting."""

    try:
        path.resolve().relative_to(root.resolve(strict=True))
    except ValueError:
        pass
    else:
        raise AssemblyError("assembly evidence reports must be written outside the checkout")
    if path.exists() or path.is_symlink():
        raise AssemblyError(f"assembly evidence report already exists: {path}")
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise AssemblyError("assembly evidence report parent must be a regular directory")
    content = (
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists() or temporary.is_symlink():
        raise AssemblyError(f"stale temporary report exists: {temporary}")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise AssemblyError(f"cannot write assembly evidence report: {error}") from error
    return content


def _validate_manifest(
    manifest_path: Path,
    *,
    candidate: Mapping[str, Any],
    staged_sources: Mapping[str, bytes],
    compiler_version: str,
) -> bytes:
    content = manifest_path.read_bytes()
    manifest = _load_artifact_json(manifest_path, label="assembly manifest")
    required_keys = {
        "dependencies",
        "root",
        "schemaVersion",
        "sources",
        "timestamp",
        "version",
    }
    if set(manifest) != required_keys:
        raise AssemblyError("assembly manifest has an unexpected shape")
    if manifest["schemaVersion"] != 1:
        raise AssemblyError("assembly manifest schemaVersion must be 1")
    if manifest["root"] != candidate["sources"]["entrypoint"]:
        raise AssemblyError("assembly manifest root does not match the entrypoint")
    if manifest["version"] != compiler_version:
        raise AssemblyError("assembly manifest compiler version does not match the lock")
    expected_timestamp = datetime.fromtimestamp(
        candidate["assembly"]["source_date_epoch"],
        tz=UTC,
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    if manifest["timestamp"] != expected_timestamp:
        raise AssemblyError("assembly manifest timestamp is not reproducible")

    expected_types = {
        source["path"]: source["media_type"]
        for source in candidate["sources"]["declared"]
    }
    expected_entries = [
        {
            "path": path,
            "sha256": _sha256_bytes(staged_sources[path]),
            "size": len(staged_sources[path]),
            "type": expected_types[path],
        }
        for path in sorted(staged_sources)
    ]
    if manifest["sources"] != expected_entries:
        raise AssemblyError(
            "assembly manifest does not describe the exact staged source closure"
        )

    dependencies = manifest["dependencies"]
    if not isinstance(dependencies, list):
        raise AssemblyError("assembly manifest dependencies must be an array")
    normalized_edges: list[tuple[str, str]] = []
    for edge in dependencies:
        if not isinstance(edge, Mapping) or set(edge) != {"from", "to"}:
            raise AssemblyError("assembly manifest dependency has an unexpected shape")
        pair = (edge["from"], edge["to"])
        if pair[0] not in staged_sources or pair[1] not in staged_sources:
            raise AssemblyError("assembly manifest dependency leaves the source closure")
        normalized_edges.append(pair)
    if normalized_edges != sorted(set(normalized_edges)):
        raise AssemblyError(
            "assembly manifest dependencies must be unique and deterministically sorted"
        )

    entrypoint = candidate["sources"]["entrypoint"]
    reachable = {entrypoint}
    changed = True
    while changed:
        changed = False
        for source, target in normalized_edges:
            if source in reachable and target not in reachable:
                reachable.add(target)
                changed = True
    if reachable != set(staged_sources):
        raise AssemblyError("assembly manifest dependency graph is not a closed build graph")
    if _sha256_bytes(content) != candidate["expected"]["manifest_sha256"]:
        raise AssemblyError("assembly manifest digest does not match the candidate")
    return content


def _validate_source_map(
    source_map_path: Path,
    *,
    candidate: Mapping[str, Any],
    staged_sources: Mapping[str, bytes],
    output: bytes,
) -> bytes:
    content = source_map_path.read_bytes()
    source_map = _load_artifact_json(source_map_path, label="assembly source map")
    if set(source_map) != {
        "lineBase",
        "mappings",
        "outputSha256",
        "schemaVersion",
    }:
        raise AssemblyError("assembly source map has an unexpected shape")
    if source_map["schemaVersion"] != 1 or source_map["lineBase"] != 1:
        raise AssemblyError("assembly source map version or line base is unsupported")
    if source_map["outputSha256"] != _sha256_bytes(output):
        raise AssemblyError("assembly source map output digest is stale")
    mappings = source_map["mappings"]
    expected_lines = len(output.splitlines())
    if not isinstance(mappings, list) or len(mappings) != expected_lines:
        raise AssemblyError("assembly source map does not cover every output line")

    line_counts = {
        path: len(source.splitlines())
        for path, source in staged_sources.items()
    }
    observed_sources: set[str] = set()
    observed_lines: dict[str, list[int]] = {}
    separator_lines: list[int] = []
    allowed_kinds = {"markdown", "hypercode_heading", "generated_separator"}
    for index, mapping in enumerate(mappings, start=1):
        if not isinstance(mapping, Mapping) or set(mapping) != {
            "generatedLine",
            "kind",
            "source",
        }:
            raise AssemblyError("assembly source map mapping has an unexpected shape")
        if mapping["generatedLine"] != index or mapping["kind"] not in allowed_kinds:
            raise AssemblyError("assembly source map line coverage is not contiguous")
        source = mapping["source"]
        if mapping["kind"] == "generated_separator":
            if source is not None:
                raise AssemblyError("generated source-map separator has a source")
            separator_lines.append(index)
            continue
        if not isinstance(source, Mapping) or set(source) != {
            "path",
            "startLine",
            "endLine",
        }:
            raise AssemblyError("assembly source map span has an unexpected shape")
        path = source["path"]
        if path not in staged_sources:
            raise AssemblyError("assembly source map references an undeclared source")
        if (
            not isinstance(source["startLine"], int)
            or not isinstance(source["endLine"], int)
            or source["startLine"] < 1
            or source["endLine"] < source["startLine"]
            or source["endLine"] > line_counts[path]
        ):
            raise AssemblyError("assembly source map has an invalid source span")
        if mapping["kind"] != "markdown" or source["startLine"] != source["endLine"]:
            raise AssemblyError(
                "this assembly candidate requires one-to-one Markdown provenance"
            )
        observed_sources.add(path)
        observed_lines.setdefault(path, []).append(source["startLine"])

    expected_markdown = {
        source["path"]
        for source in candidate["sources"]["declared"]
        if source["media_type"] == "markdown"
    }
    if not expected_markdown.issubset(observed_sources):
        raise AssemblyError("assembly source map omits an emitted Markdown source")
    for path in expected_markdown:
        if observed_lines.get(path) != list(range(1, line_counts[path] + 1)):
            raise AssemblyError(
                f"assembly source map does not cover {path!r} exactly once"
            )
    if separator_lines != candidate["expected"]["generated_separator_lines"]:
        raise AssemblyError("assembly source map generated separators are unexpected")
    if _sha256_bytes(content) != candidate["expected"]["source_map_sha256"]:
        raise AssemblyError("assembly source map digest does not match the candidate")
    return content


def _assert_exact_staging_inventory(
    staging: Path,
    expected: set[str],
) -> None:
    actual: set[str] = set()
    for path in staging.rglob("*"):
        if path.is_symlink():
            raise AssemblyError(f"assembly staging contains a symlink: {path}")
        if path.is_file():
            actual.add(path.relative_to(staging).as_posix())
    if actual != expected:
        raise AssemblyError(
            "assembly staging inventory mismatch: "
            f"expected {sorted(expected)}, got {sorted(actual)}"
        )


def run_candidate_build(
    root: Path,
    candidate_path: Path,
    compiler: Path,
) -> tuple[bytes, bytes, bytes]:
    """Build and validate one executable candidate in disposable staging."""

    candidate = validate_candidate(root, candidate_path)
    if candidate["candidate_stage"] != "executable":
        raise AssemblyError("only executable candidates can be built")
    lock = validate_lock(root)
    verify_compiler(compiler, root=root)

    with disposable_staging() as staging:
        canonical = _canonical_bytes(root, candidate, _load_catalog(root))
        staged_sources = _source_bytes(
            root,
            candidate_path.parent,
            candidate,
            canonical,
        )
        for relative, content in staged_sources.items():
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)

        assembly = candidate["assembly"]
        output_path = staging / assembly["output"]
        manifest_path = staging / assembly["manifest"]
        source_map_path = staging / assembly["source_map"]
        for artifact_path in (output_path, manifest_path, source_map_path):
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        environment.update(
            {
                "SOURCE_DATE_EPOCH": str(assembly["source_date_epoch"]),
                "LC_ALL": "C",
                "TZ": "UTC",
            }
        )
        command = [
            str(compiler.resolve()),
            "compile",
            candidate["sources"]["entrypoint"],
            "--root",
            str(staging),
            "--output",
            assembly["output"],
            "--manifest",
            assembly["manifest"],
            "--source-map",
            assembly["source_map"],
        ]
        try:
            result = subprocess.run(
                command,
                cwd=staging,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise AssemblyError(f"Hyperprompt candidate build failed: {error}") from error
        if result.returncode != 0:
            raise AssemblyError(
                "Hyperprompt candidate build exited non-zero: "
                + (result.stderr.strip() or result.stdout.strip())
            )

        expected_inventory = set(staged_sources) | {
            assembly["output"],
            assembly["manifest"],
            assembly["source_map"],
        }
        _assert_exact_staging_inventory(staging, expected_inventory)
        try:
            output = output_path.read_bytes()
        except OSError as error:
            raise AssemblyError(f"cannot read generated RFC candidate: {error}") from error
        if output != canonical:
            raise AssemblyError(
                "generated RFC candidate is not byte-identical to the canonical RFC"
            )
        if _sha256_bytes(output) != candidate["expected"]["aggregate_sha256"]:
            raise AssemblyError("generated RFC candidate digest does not match expected")
        manifest = _validate_manifest(
            manifest_path,
            candidate=candidate,
            staged_sources=staged_sources,
            compiler_version=lock["release"]["version"],
        )
        source_map = _validate_source_map(
            source_map_path,
            candidate=candidate,
            staged_sources=staged_sources,
            output=output,
        )
        return output, manifest, source_map


def _expected_candidate_evidence(
    root: Path,
    descriptor: Path,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    canonical = _canonical_bytes(root, candidate, _load_catalog(root))
    return {
        "candidate_id": candidate["candidate_id"],
        "descriptor_sha256": _sha256_file(descriptor),
        "canonical_sha256": candidate["canonical"]["sha256"],
        "aggregate_sha256": candidate["expected"]["aggregate_sha256"],
        "aggregate_size": len(canonical),
        "manifest_sha256": candidate["expected"]["manifest_sha256"],
        "source_map_sha256": candidate["expected"]["source_map_sha256"],
    }


def _expected_candidate_evidence_set(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for descriptor in discover_candidates(root):
        candidate = validate_candidate(root, descriptor)
        if candidate["candidate_stage"] != "executable":
            continue
        entries.append(_expected_candidate_evidence(root, descriptor, candidate))
    return sorted(entries, key=lambda entry: entry["candidate_id"])


def validate_platform_report_data(
    root: Path,
    report: Mapping[str, Any],
    *,
    expected_source_revision: str | None = None,
) -> Mapping[str, Any]:
    """Validate one platform report against the current locked repository."""

    schema = _load_checked_schema(
        root,
        PLATFORM_REPORT_SCHEMA_PATH,
        label="assembly platform report schema",
    )
    _validate_schema(report, schema, label="assembly platform report")
    if (
        expected_source_revision is not None
        and report["source_revision"] != expected_source_revision
    ):
        raise AssemblyError("assembly platform report source revision mismatch")

    lock = validate_lock(root)
    artifact = _artifact_for_platform(lock, report["platform"])
    expected_toolchain = {
        "version": lock["release"]["version"],
        "release_commit": lock["release"]["commit"],
        "lock_sha256": _sha256_file(root / LOCK_PATH),
        "binary_sha256": artifact["binary_sha256"],
    }
    if report["toolchain"] != expected_toolchain:
        raise AssemblyError("assembly platform report toolchain does not match the lock")
    if report["candidates"] != _expected_candidate_evidence_set(root):
        raise AssemblyError(
            "assembly platform report candidates do not match the repository"
        )
    return report


def validate_platform_report(
    root: Path,
    path: Path,
    *,
    expected_source_revision: str | None = None,
) -> Mapping[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise AssemblyError(f"assembly platform report must be a regular file: {path}")
    report = _load_artifact_json(path, label="assembly platform report")
    return validate_platform_report_data(
        root,
        report,
        expected_source_revision=expected_source_revision,
    )


def _build_platform_report(
    root: Path,
    *,
    platform_name: str,
    source_revision: str,
    compiler_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    lock = validate_lock(root)
    return {
        "$schema": (
            "https://github.com/0al-spec/agent-surface/publication/"
            "schemas/assembly-platform-report/v1"
        ),
        "schema_version": 1,
        "report_kind": "asp_rfc_assembly_platform",
        "authority": "provenance_only",
        "source_revision": source_revision,
        "checkout": "clean_before_and_after",
        "platform": platform_name,
        "toolchain": {
            "version": lock["release"]["version"],
            "release_commit": lock["release"]["commit"],
            "lock_sha256": _sha256_file(root / LOCK_PATH),
            "binary_sha256": compiler_artifact["binary_sha256"],
        },
        "candidates": _expected_candidate_evidence_set(root),
        "repetitions": 2,
        "result": "reproducible",
    }


def build_repository(
    root: Path,
    compiler: Path,
    *,
    platform_name: str | None = None,
    source_revision: str | None = None,
    report_path: Path | None = None,
) -> int:
    """Build every executable candidate twice and optionally emit clean evidence."""

    platform_value = platform_name or _host_platform()
    if platform_value != _host_platform():
        raise AssemblyError(
            f"declared platform {platform_value} does not match this host"
        )
    if (source_revision is None) != (report_path is None):
        raise AssemblyError(
            "source revision and report path must be supplied together"
        )
    if source_revision is not None:
        require_clean_checkout(root, source_revision)
    compiler_artifact = verify_compiler(
        compiler,
        root=root,
        platform_name=platform_value,
    )

    count = 0
    for descriptor in discover_candidates(root):
        candidate = validate_candidate(root, descriptor)
        if candidate["candidate_stage"] != "executable":
            continue
        first = run_candidate_build(root, descriptor, compiler)
        second = run_candidate_build(root, descriptor, compiler)
        if first != second:
            raise AssemblyError(
                f"candidate {candidate['candidate_id']!r} is not reproducible"
            )
        count += 1
    if count == 0:
        raise AssemblyError("repository has no executable assembly candidate")
    if source_revision is not None and report_path is not None:
        require_clean_checkout(root, source_revision)
        report = _build_platform_report(
            root,
            platform_name=platform_value,
            source_revision=source_revision,
            compiler_artifact=compiler_artifact,
        )
        validate_platform_report_data(
            root,
            report,
            expected_source_revision=source_revision,
        )
        _write_new_report(root, report_path, report)
    return count


def validate_cross_platform_report_data(
    root: Path,
    report: Mapping[str, Any],
    *,
    expected_source_revision: str | None = None,
) -> Mapping[str, Any]:
    schema = _load_checked_schema(
        root,
        CROSS_PLATFORM_REPORT_SCHEMA_PATH,
        label="assembly cross-platform report schema",
    )
    _validate_schema(report, schema, label="assembly cross-platform report")
    if (
        expected_source_revision is not None
        and report["source_revision"] != expected_source_revision
    ):
        raise AssemblyError("assembly cross-platform report source revision mismatch")
    lock = validate_lock(root)
    expected_toolchain = {
        "version": lock["release"]["version"],
        "release_commit": lock["release"]["commit"],
        "lock_sha256": _sha256_file(root / LOCK_PATH),
    }
    if report["toolchain"] != expected_toolchain:
        raise AssemblyError(
            "assembly cross-platform report toolchain does not match the lock"
        )
    if report["candidates"] != _expected_candidate_evidence_set(root):
        raise AssemblyError(
            "assembly cross-platform report candidates do not match the repository"
        )
    return report


def compare_platform_reports(
    root: Path,
    report_paths: Sequence[Path],
    *,
    source_revision: str,
    output_path: Path,
) -> Mapping[str, Any]:
    """Compare the exact Linux/macOS evidence set and emit one summary."""

    if len(report_paths) != len(EXPECTED_PLATFORMS):
        raise AssemblyError("cross-platform comparison requires exactly two reports")
    try:
        resolved = [path.resolve(strict=True) for path in report_paths]
    except OSError as error:
        raise AssemblyError(f"cannot resolve assembly platform report: {error}") from error
    if len(set(resolved)) != len(resolved):
        raise AssemblyError("cross-platform comparison received duplicate reports")
    reports = [
        validate_platform_report(
            root,
            path,
            expected_source_revision=source_revision,
        )
        for path in report_paths
    ]
    by_platform = {report["platform"]: report for report in reports}
    path_by_platform = {
        report["platform"]: path
        for report, path in zip(reports, report_paths, strict=True)
    }
    if set(by_platform) != set(EXPECTED_PLATFORMS):
        raise AssemblyError(
            "cross-platform comparison requires linux-amd64 and macos-arm64"
        )
    if len(by_platform) != len(reports):
        raise AssemblyError("cross-platform comparison has duplicate platforms")

    linux = by_platform["linux-amd64"]
    macos = by_platform["macos-arm64"]
    if linux["candidates"] != macos["candidates"]:
        raise AssemblyError("cross-platform candidate artifacts are not identical")
    common_toolchain_keys = ("version", "release_commit", "lock_sha256")
    linux_toolchain = {
        key: linux["toolchain"][key] for key in common_toolchain_keys
    }
    macos_toolchain = {
        key: macos["toolchain"][key] for key in common_toolchain_keys
    }
    if linux_toolchain != macos_toolchain:
        raise AssemblyError("cross-platform reports use different toolchain locks")

    report = {
        "$schema": (
            "https://github.com/0al-spec/agent-surface/publication/"
            "schemas/assembly-cross-platform-report/v1"
        ),
        "schema_version": 1,
        "report_kind": "asp_rfc_assembly_cross_platform",
        "authority": "provenance_only",
        "source_revision": source_revision,
        "platforms": ["linux-amd64", "macos-arm64"],
        "platform_report_sha256": {
            platform: _sha256_file(path_by_platform[platform])
            for platform in ("linux-amd64", "macos-arm64")
        },
        "toolchain": linux_toolchain,
        "candidates": linux["candidates"],
        "result": "cross_platform_reproducible",
    }
    validate_cross_platform_report_data(
        root,
        report,
        expected_source_revision=source_revision,
    )
    _write_new_report(root, output_path, report)
    return report


def validate_repository(root: Path = ROOT) -> list[Path]:
    """Validate the 78A foundation and every materialized candidate descriptor."""

    return _check_repository(root)


def _check_repository(root: Path) -> list[Path]:
    lock = validate_lock(root)
    for relative, label in (
        (CANDIDATE_SCHEMA_PATH, "candidate schema"),
        (PLATFORM_REPORT_SCHEMA_PATH, "assembly platform report schema"),
        (
            CROSS_PLATFORM_REPORT_SCHEMA_PATH,
            "assembly cross-platform report schema",
        ),
    ):
        _load_checked_schema(root, relative, label=label)
    _load_catalog(root)
    candidates = discover_candidates(root)
    for descriptor in candidates:
        validate_candidate(root, descriptor, lock=lock)
    with disposable_staging() as staging:
        require_empty_staging(staging)
    return candidates


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--root", type=Path, default=ROOT)

    verify = subparsers.add_parser("verify-archive")
    verify.add_argument("--root", type=Path, default=ROOT)
    verify.add_argument("--platform", required=True, choices=sorted(EXPECTED_PLATFORMS))
    verify.add_argument("--archive", required=True, type=Path)

    install = subparsers.add_parser("install-toolchain")
    install.add_argument("--root", type=Path, default=ROOT)
    install.add_argument(
        "--destination",
        type=Path,
        default=Path(".tools/hyperprompt/hyperprompt"),
    )
    install.add_argument("--platform", choices=sorted(EXPECTED_PLATFORMS))

    build = subparsers.add_parser("build")
    build.add_argument("--root", type=Path, default=ROOT)
    build.add_argument("--compiler", required=True, type=Path)
    build.add_argument("--platform", choices=sorted(EXPECTED_PLATFORMS))
    build.add_argument("--source-revision")
    build.add_argument("--report", type=Path)

    validate_report = subparsers.add_parser("validate-report")
    validate_report.add_argument("--root", type=Path, default=ROOT)
    validate_report.add_argument("--report", required=True, type=Path)
    validate_report.add_argument("--source-revision")

    compare = subparsers.add_parser("compare-reports")
    compare.add_argument("--root", type=Path, default=ROOT)
    compare.add_argument(
        "--report",
        required=True,
        action="append",
        dest="reports",
        type=Path,
    )
    compare.add_argument("--source-revision", required=True)
    compare.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            candidates = _check_repository(args.root.resolve())
            print(
                "publication assembly foundation is valid "
                f"({len(candidates)} candidate descriptors)"
            )
        elif args.command == "verify-archive":
            verify_archive(
                args.archive.resolve(),
                args.platform,
                root=args.root.resolve(),
            )
            print(f"Hyperprompt archive is valid for {args.platform}")
        elif args.command == "install-toolchain":
            installed = install_toolchain(
                args.root.resolve(),
                args.destination.resolve(),
                platform_name=args.platform,
            )
            print(f"installed locked Hyperprompt compiler at {installed}")
        elif args.command == "build":
            count = build_repository(
                args.root.resolve(),
                args.compiler.resolve(),
                platform_name=args.platform,
                source_revision=args.source_revision,
                report_path=args.report.resolve() if args.report is not None else None,
            )
            print(f"publication assembly is reproducible ({count} candidates)")
        elif args.command == "validate-report":
            report = validate_platform_report(
                args.root.resolve(),
                args.report.resolve(),
                expected_source_revision=args.source_revision,
            )
            print(
                "publication assembly platform report is valid "
                f"({report['platform']})"
            )
        else:
            report = compare_platform_reports(
                args.root.resolve(),
                [path.resolve() for path in args.reports],
                source_revision=args.source_revision,
                output_path=args.output.resolve(),
            )
            print(
                "publication assembly is cross-platform reproducible "
                f"({', '.join(report['platforms'])})"
            )
    except AssemblyError as error:
        print(f"publication assembly error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
