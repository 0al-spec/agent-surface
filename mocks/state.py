"""Fail-closed, exact-once authoritative journals for mock participants."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class StateError(RuntimeError):
    """Raised for stale, conflicting, corrupt, or incomplete mock state."""


@dataclass(frozen=True)
class Scope:
    run_id: str
    vector_id: str
    boundary_id: str

    def __post_init__(self) -> None:
        for name, value in (
            ("run_id", self.run_id),
            ("vector_id", self.vector_id),
            ("boundary_id", self.boundary_id),
        ):
            if not isinstance(value, str) or not value or len(value) > 512:
                raise StateError(f"invalid scope {name}")

    @property
    def key(self) -> str:
        encoded = "\0".join((self.run_id, self.vector_id, self.boundary_id)).encode(
            "utf-8"
        )
        return hashlib.sha256(encoded).hexdigest()


def _strict_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StateError(f"duplicate journal member {key!r}")
        result[key] = value
    return result


def _reject_float(_: str) -> None:
    raise StateError("floating-point journal values are forbidden")


def _validate_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -(2**53 - 1) <= value <= 2**53 - 1:
            raise StateError(f"unsafe integer journal value at {path}")
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeError as error:
            raise StateError(f"invalid Unicode journal value at {path}") from error
        return
    if isinstance(value, float):
        raise StateError(f"floating-point journal value at {path} is forbidden")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_value(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise StateError(f"journal member name at {path} is not a string")
            _validate_value(key, f"{path}.<key>")
            _validate_value(item, f"{path}.{key}")
        return
    raise StateError(f"unsupported journal value at {path}")


class JournalStore:
    """One journal per run/vector/boundary scope, initialized exactly once."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve() / ".asp-mock-state"

    def _directory(self, scope: Scope) -> Path:
        return self.root / scope.key

    def initialize(self, scope: Scope, journal: Mapping[str, Any]) -> Path:
        if not isinstance(journal, Mapping):
            raise StateError("journal must be an object")
        value = dict(journal)
        expected_scope = {
            "run_id": scope.run_id,
            "vector_id": scope.vector_id,
            "boundary_id": scope.boundary_id,
        }
        for name, expected in expected_scope.items():
            if value.get(name) != expected:
                raise StateError(f"journal {name} conflicts with its storage scope")
        _validate_value(value)
        try:
            payload = json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as error:
            raise StateError("journal cannot be encoded as strict JSON") from error
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory = self._directory(scope)
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError as error:
            raise StateError("mock state scope was already initialized") from error
        temporary = directory / "journal.json.tmp"
        final = directory / "journal.json"
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, final)
            directory_descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except Exception as error:
            try:
                temporary.unlink()
            except OSError:
                pass
            raise StateError("failed to initialize authoritative mock journal") from error
        return final

    def read(self, scope: Scope) -> dict[str, Any]:
        directory = self._directory(scope)
        final = directory / "journal.json"
        temporary = directory / "journal.json.tmp"
        if directory.is_symlink():
            raise StateError("authoritative mock journal is absent or incomplete")
        try:
            entries = {item.name for item in directory.iterdir()}
        except OSError as error:
            raise StateError("authoritative mock journal is absent or incomplete") from error
        if (
            temporary.exists()
            or not directory.is_dir()
            or final.is_symlink()
            or not final.is_file()
            or entries != {"journal.json"}
        ):
            raise StateError("authoritative mock journal is absent or incomplete")
        try:
            value = json.loads(
                final.read_text(encoding="utf-8"),
                object_pairs_hook=_strict_object_pairs,
                parse_float=_reject_float,
                parse_constant=_reject_float,
            )
        except (OSError, UnicodeError, json.JSONDecodeError, StateError) as error:
            raise StateError("authoritative mock journal is corrupt") from error
        if not isinstance(value, dict):
            raise StateError("authoritative mock journal is not an object")
        try:
            _validate_value(value)
        except StateError as error:
            raise StateError("authoritative mock journal is corrupt") from error
        for name, expected in (
            ("run_id", scope.run_id),
            ("vector_id", scope.vector_id),
            ("boundary_id", scope.boundary_id),
        ):
            if value.get(name) != expected:
                raise StateError(f"authoritative mock journal has stale {name}")
        return value
