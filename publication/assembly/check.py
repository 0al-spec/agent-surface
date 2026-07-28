#!/usr/bin/env python3
"""Validate and stage non-authoritative ASP assembly candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = Path("publication/assembly/hyperprompt.lock.json")
LOCK_SCHEMA_PATH = Path("publication/assembly/hyperprompt.lock.schema.json")
CANDIDATE_SCHEMA_PATH = Path("publication/assembly/candidate.schema.json")
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
        else:
            extraction = source["extraction"]
            if not isinstance(extraction, Mapping):
                raise AssemblyError(f"derived source {stage_name!r} has no extraction")
            if extraction["source_path"] != candidate["canonical"]["path"]:
                raise AssemblyError(
                    f"derived source {stage_name!r} is not bound to the canonical source"
                )
            start = extraction["start_byte"]
            end = extraction["end_byte"]
            if start >= end or end > len(canonical):
                raise AssemblyError(
                    f"derived source {stage_name!r} has an invalid byte range"
                )
            content = canonical[start:end]
            try:
                content.decode("utf-8")
            except UnicodeDecodeError as error:
                raise AssemblyError(
                    f"derived source {stage_name!r} splits UTF-8 text"
                ) from error

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


def verify_archive(
    archive_path: Path,
    platform: str,
    *,
    root: Path = ROOT,
) -> None:
    """Verify a downloaded Hyperprompt release archive without extracting it."""

    lock = validate_lock(root)
    artifact = next(
        (item for item in lock["artifacts"] if item["platform"] == platform),
        None,
    )
    if artifact is None:
        raise AssemblyError(f"platform is not locked: {platform}")
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


def validate_repository(root: Path = ROOT) -> list[Path]:
    """Validate the 78A foundation and every materialized candidate descriptor."""

    return _check_repository(root)


def _check_repository(root: Path) -> list[Path]:
    lock = validate_lock(root)
    candidate_schema = _load_json(root / CANDIDATE_SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(candidate_schema)
    except SchemaError as error:
        raise AssemblyError(f"candidate schema is invalid: {error.message}") from error
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
        else:
            verify_archive(
                args.archive.resolve(),
                args.platform,
                root=args.root.resolve(),
            )
            print(f"Hyperprompt archive is valid for {args.platform}")
    except AssemblyError as error:
        print(f"publication assembly error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
