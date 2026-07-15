"""Closed participant protocol shared by Mock App and Mock Runtime."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from .behavior import FEATURE_INVENTORY, BehaviorError, evaluate, family_for
    from .state import JournalStore, Scope, StateError
except ImportError:  # pragma: no cover - direct executable fallback
    from behavior import FEATURE_INVENTORY, BehaviorError, evaluate, family_for
    from state import JournalStore, Scope, StateError


PARTICIPANT_PROTOCOL = "asp-mock-participant/1"
SAFE_INTEGER = 2**53 - 1


class ParticipantError(ValueError):
    """Raised when an invocation violates the closed mock participant contract."""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ParticipantError(f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def _reject_number(_: str) -> None:
    raise ParticipantError("floating-point and non-finite JSON numbers are forbidden")


def _parse_safe_integer(value: str) -> int:
    number = int(value)
    if not -SAFE_INTEGER <= number <= SAFE_INTEGER:
        raise ParticipantError("JSON integer is outside the I-JSON safe range")
    return number


def _validate_ijson(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -SAFE_INTEGER <= value <= SAFE_INTEGER:
            raise ParticipantError(f"unsafe JSON integer at {path}")
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeError as error:
            raise ParticipantError(f"invalid Unicode value at {path}") from error
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_ijson(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ParticipantError(f"JSON member name at {path} is not a string")
            _validate_ijson(key, f"{path}.<key>")
            _validate_ijson(item, f"{path}.{key}")
        return
    raise ParticipantError(f"unsupported JSON value at {path}")


def load_request(stream: Any = sys.stdin) -> Mapping[str, Any]:
    """Read one strict I-JSON object from a participant process stream."""

    try:
        value = json.load(
            stream,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_float=_reject_number,
            parse_int=_parse_safe_integer,
            parse_constant=_reject_number,
        )
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ParticipantError("participant input is not strict JSON") from error
    _validate_ijson(value)
    return _object(value, "participant input")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _domain_digest(domain: str, value: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(domain.encode("ascii") + b"\0" + _canonical_bytes(value)).digest()
    return "sha-256:" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ParticipantError(f"{label} must be an object")
    return value


def _family_binding(family: str, profile_id: str, producer_role: str | None) -> None:
    if family not in {"app", "runtime"}:
        raise ParticipantError("unknown mock participant family")
    if family_for(profile_id, producer_role) != family:
        raise ParticipantError("profile is outside the selected mock participant family")


def inventory(family: str, request: Mapping[str, Any]) -> dict[str, Any]:
    if request.get("probe_protocol") != "asp-conformance-probe/1" or request.get(
        "operation"
    ) != "inventory":
        raise ParticipantError("inventory requires asp-conformance-probe/1")
    locator = _object(request.get("subject_locator"), "subject_locator")
    profile_id = locator.get("profile_id")
    producer_role = locator.get("producer_role")
    if not isinstance(profile_id, str):
        raise ParticipantError("subject locator requires profile_id")
    _family_binding(family, profile_id, producer_role if isinstance(producer_role, str) else None)
    return {
        "schema_version": 1,
        "run_id": request["run_id"],
        "subject_sha256": request["subject_sha256"],
        "harness_sha256": request["harness_sha256"],
        "captured_at": _now(),
        "feature_ids": list(FEATURE_INVENTORY[profile_id]),
    }


def _counterpart_digests(
    subject: Mapping[str, Any], required: Any
) -> list[str]:
    if not isinstance(required, list):
        raise ParticipantError("required_counterparts must be an array")
    counterparts = subject.get("counterparts")
    if not isinstance(counterparts, list):
        raise ParticipantError("subject counterparts must be an array")
    subject_implementation = _object(
        subject.get("implementation"), "subject implementation"
    )
    subject_artifact = subject_implementation.get("artifact_sha256")
    if not isinstance(subject_artifact, str):
        raise ParticipantError("subject implementation requires artifact_sha256")
    matched: list[Mapping[str, Any]] = []
    for requirement_value in required:
        requirement = _object(requirement_value, "counterpart requirement")
        candidates = [
            item
            for item in counterparts
            if isinstance(item, Mapping)
            and item.get("kind") == "implementation"
            and item.get("profile_id") == requirement.get("profile_id")
            and item.get("producer_role") == requirement.get("producer_role")
            and item.get("boundary_id") != subject.get("boundary_id")
            and isinstance(item.get("artifact_sha256"), str)
            and item.get("artifact_sha256") != subject_artifact
            and item not in matched
        ]
        if len(candidates) != 1:
            raise ParticipantError("required counterpart topology is unavailable or ambiguous")
        matched.append(candidates[0])
    return [_domain_digest("ASP-CONFORMANCE-COUNTERPART-V1", item) for item in matched]


def execute(
    family: str, request: Mapping[str, Any], store_root: Path | str
) -> dict[str, Any]:
    if request.get("adapter_protocol") != "asp-conformance-adapter/1":
        raise ParticipantError("execute requires asp-conformance-adapter/1")
    subject = _object(request.get("subject"), "subject")
    case = _object(request.get("case"), "case")
    stimulus = _object(case.get("stimulus"), "case stimulus")
    fixture = _object(stimulus.get("fixture"), "resolved fixture")
    document = _object(fixture.get("document"), "semantic document")
    profile_id = subject.get("profile_id")
    producer_role = subject.get("producer_role")
    if subject.get("subject_kind") != "suite_fixture":
        raise ParticipantError("mock participants are suite_fixture_only")
    if not isinstance(profile_id, str) or case.get("profile_id") != profile_id:
        raise ParticipantError("case and subject profile bindings differ")
    role = producer_role if isinstance(producer_role, str) else None
    if case.get("producer_role") != producer_role:
        if producer_role is not None or "producer_role" in case:
            raise ParticipantError("case and subject producer-role bindings differ")
    _family_binding(family, profile_id, role)
    if request.get("vector_id") != case.get("vector_id"):
        raise ParticipantError("case and invocation vector bindings differ")
    operation = stimulus.get("operation")
    if not isinstance(operation, str):
        raise ParticipantError("stimulus requires operation")
    result = evaluate(
        profile_id,
        role,
        operation,
        document,
        case.get("initial_state"),
    )
    boundary_id = subject.get("boundary_id")
    if not isinstance(boundary_id, str):
        raise ParticipantError("subject requires boundary_id")
    scope = Scope(request["run_id"], request["vector_id"], boundary_id)
    journal: dict[str, Any] = {
        "schema_version": 1,
        "participant_protocol": PARTICIPANT_PROTOCOL,
        "run_id": scope.run_id,
        "vector_id": scope.vector_id,
        "boundary_id": scope.boundary_id,
        "subject_sha256": request["subject_sha256"],
        "harness_sha256": request["harness_sha256"],
        "family": family,
        "profile_id": profile_id,
        "operation": operation,
        "counterpart_sha256s": _counterpart_digests(
            subject, case.get("required_counterparts")
        ),
        **result.as_journal_fields(),
    }
    if role is not None:
        journal["producer_role"] = role
    JournalStore(Path(store_root) / family).initialize(scope, journal)
    return {
        "schema_version": 1,
        "run_id": scope.run_id,
        "vector_id": scope.vector_id,
        "status": "completed",
    }


def observe(
    family: str, request: Mapping[str, Any], store_root: Path | str
) -> dict[str, Any]:
    if request.get("probe_protocol") != "asp-conformance-probe/1" or request.get(
        "operation"
    ) != "observe":
        raise ParticipantError("observe requires asp-conformance-probe/1")
    locator = _object(request.get("subject_locator"), "subject_locator")
    profile_id = locator.get("profile_id")
    producer_role = locator.get("producer_role")
    if not isinstance(profile_id, str):
        raise ParticipantError("subject locator requires profile_id")
    role = producer_role if isinstance(producer_role, str) else None
    _family_binding(family, profile_id, role)
    boundary_id = locator.get("boundary_id")
    if not isinstance(boundary_id, str):
        raise ParticipantError("subject locator requires boundary_id")
    scope = Scope(request["run_id"], request["vector_id"], boundary_id)
    journal = JournalStore(Path(store_root) / family).read(scope)
    required_journal = {
        "schema_version",
        "participant_protocol",
        "run_id",
        "vector_id",
        "boundary_id",
        "subject_sha256",
        "harness_sha256",
        "family",
        "profile_id",
        "operation",
        "counterpart_sha256s",
        "decision",
        "tokens",
        "state_before",
        "state_after",
    }
    optional_journal = {
        "producer_role",
        "asp_error",
        "policy_reason",
        "match_reason",
    }
    if not required_journal.issubset(journal) or set(journal) - required_journal - optional_journal:
        raise ParticipantError("authoritative journal is not the exact closed shape")
    if journal.get("schema_version") != 1 or journal.get("participant_protocol") != PARTICIPANT_PROTOCOL:
        raise ParticipantError("authoritative journal protocol binding is invalid")
    tokens = journal.get("tokens")
    counterparts = journal.get("counterpart_sha256s")
    if (
        not isinstance(tokens, list)
        or not tokens
        or len(tokens) != len(set(tokens))
        or any(not isinstance(item, str) or not item for item in tokens)
        or not isinstance(counterparts, list)
        or len(counterparts) != len(set(counterparts))
        or any(not isinstance(item, str) for item in counterparts)
    ):
        raise ParticipantError("authoritative journal observations are invalid")
    for name, expected in (
        ("subject_sha256", request["subject_sha256"]),
        ("harness_sha256", request["harness_sha256"]),
        ("family", family),
        ("profile_id", profile_id),
    ):
        if journal.get(name) != expected:
            raise ParticipantError(f"authoritative journal has stale {name}")
    if journal.get("producer_role") != producer_role:
        if producer_role is not None or "producer_role" in journal:
            raise ParticipantError("authoritative journal has stale producer_role")
    requested_states = request.get("requested_states")
    if (
        not isinstance(requested_states, list)
        or requested_states != sorted(requested_states)
        or len(requested_states) != len(set(requested_states))
    ):
        raise ParticipantError("requested_states must be a canonical unique array")
    before = _object(journal.get("state_before"), "journal state_before")
    after = _object(journal.get("state_after"), "journal state_after")
    if set(requested_states) != set(before) or set(before) != set(after):
        raise ParticipantError("requested states do not exactly cover authoritative state")
    observation: dict[str, Any] = {
        "schema_version": 1,
        "run_id": scope.run_id,
        "subject_sha256": request["subject_sha256"],
        "harness_sha256": request["harness_sha256"],
        "counterpart_sha256s": journal["counterpart_sha256s"],
        "observation_id": f"obs-mock-{scope.vector_id}",
        "vector_id": scope.vector_id,
        "step_id": "final",
        "tokens": journal["tokens"],
        "state_deltas": [
            {"state": name, "before": before[name], "after": after[name]}
            for name in requested_states
        ],
        "captured_at": _now(),
        "sanitization": "synthetic_or_redacted",
    }
    for name in ("asp_error", "policy_reason", "match_reason"):
        if name in journal:
            observation[name] = journal[name]
    return observation


def dispatch(
    family: str, envelope: Mapping[str, Any], store_root: Path | str
) -> dict[str, Any]:
    if set(envelope) != {"participant_protocol", "operation", "request"}:
        raise ParticipantError("participant envelope is not the exact closed shape")
    if envelope.get("participant_protocol") != PARTICIPANT_PROTOCOL:
        raise ParticipantError("unsupported participant protocol")
    operation = envelope.get("operation")
    request = _object(envelope.get("request"), "participant request")
    if operation == "inventory":
        return inventory(family, request)
    if operation == "execute":
        return execute(family, request, store_root)
    if operation == "observe":
        return observe(family, request, store_root)
    raise ParticipantError(f"unknown participant operation: {operation!r}")


def main_for_family(family: str) -> int:
    try:
        envelope = load_request()
        response = dispatch(family, _object(envelope, "participant envelope"), Path.cwd())
        json.dump(response, sys.stdout, ensure_ascii=False, separators=(",", ":"))
        return 0
    except (KeyError, TypeError, ValueError, BehaviorError, StateError, OSError):
        return 2
