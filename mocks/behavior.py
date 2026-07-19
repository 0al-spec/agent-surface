"""Oracle-independent state machines for the ASP mock participant families.

The evaluator deliberately accepts no vector identifier, input-variant label,
fixture identifier, expected observation, or catalog object. Decisions are a
pure function of the selected role, operation, semantic document, and initial
authoritative state.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

import rfc8785
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


SP = "https://github.com/0al-spec/agent-surface/conformance/surface-publisher/v1"
GI = "https://github.com/0al-spec/agent-surface/conformance/grant-issuer/v1"
AE = "https://github.com/0al-spec/agent-surface/conformance/action-executor/v1"
RP = "https://github.com/0al-spec/agent-surface/conformance/receipt-producer/v1"
RM = "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1"
AA = "https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1"
OPERATIONAL_LIMITS = (
    "https://github.com/0al-spec/agent-surface/profiles/operational-limits/v1"
)
ASP_OVER_AHP = (
    "https://github.com/0al-spec/agent-surface/profiles/asp-over-ahp/v1"
)
HUMAN_ELICITATION = (
    "https://github.com/0al-spec/agent-surface/profiles/human-elicitation/v1"
)
RISK_EXPLANATION = "agent-surface/feature/risk-explanation-ui-hints"
SAFE_INTEGER = 2**53 - 1
RISK_LANGUAGE_PATTERN = re.compile(
    r"^[a-z]{2,8}(?:-[a-z]{4})?(?:-(?:[a-z]{2}|[0-9]{3}))?"
    r"(?:-(?:[a-z0-9]{5,8}|[0-9][a-z0-9]{3}))*$"
)
HTTP_MONTHS = {
    name: number
    for number, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        start=1,
    )
}
HTTP_DATE_PATTERNS = (
    (
        re.compile(
            r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), "
            r"(?P<day>[0-9]{2}) (?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
            r"(?P<year>[0-9]{4}) (?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):"
            r"(?P<second>[0-9]{2}) GMT$"
        ),
        False,
    ),
    (
        re.compile(
            r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
            r"(?P<day>[0-9]{2})-(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-"
            r"(?P<year>[0-9]{2}) (?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):"
            r"(?P<second>[0-9]{2}) GMT$"
        ),
        True,
    ),
    (
        re.compile(
            r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) "
            r"(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
            r"(?P<day> [1-9]|[0-9]{2}) (?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):"
            r"(?P<second>[0-9]{2}) (?P<year>[0-9]{4})$"
        ),
        False,
    ),
)

APP_PROFILES = frozenset({SP, GI, AE})
RUNTIME_PROFILES = frozenset({RM, AA})
PRODUCER_ROLES = frozenset({"application", "runtime"})

FEATURE_INVENTORY: dict[str, tuple[str, ...]] = {
    SP: (
        "agent-surface/feature/proposal-only",
        RISK_EXPLANATION,
        OPERATIONAL_LIMITS,
    ),
    GI: (
        "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
    ),
    AE: (
        "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1",
        HUMAN_ELICITATION,
        OPERATIONAL_LIMITS,
        "https://github.com/0al-spec/agent-surface/profiles/runtime-attestation/v1",
        "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1",
    ),
    RP: (),
    RM: (
        RISK_EXPLANATION,
        "https://github.com/0al-spec/agent-surface/profiles/agent-training-use/v1",
        ASP_OVER_AHP,
        "https://github.com/0al-spec/agent-surface/profiles/capability-match-result/v1",
        HUMAN_ELICITATION,
        OPERATIONAL_LIMITS,
        "https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1",
    ),
    AA: (ASP_OVER_AHP, HUMAN_ELICITATION),
}


class BehaviorError(ValueError):
    """Raised when an invocation is outside the closed mock behavior model."""


class _RiskExplanationBindingError(BehaviorError):
    """Raised when otherwise bounded hint data is stale or action-substituted."""


@dataclass(frozen=True)
class BehaviorResult:
    """One deterministic transition and its sanitized observable decision."""

    decision: str
    tokens: tuple[str, ...]
    state_before: dict[str, Any]
    state_after: dict[str, Any]
    asp_error: str | None = None
    policy_reason: str | None = None
    match_reason: str | None = None

    def as_journal_fields(self) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "decision": self.decision,
            "tokens": list(self.tokens),
            "state_before": self.state_before,
            "state_after": self.state_after,
        }
        for name in ("asp_error", "policy_reason", "match_reason"):
            value = getattr(self, name)
            if value is not None:
                fields[name] = value
        return fields


@dataclass(frozen=True)
class _HumanElicitationResult:
    kind: str
    disposition: str
    terminal_replay: bool


def family_for(profile_id: str, producer_role: str | None = None) -> str:
    """Return the only participant family allowed to implement an atomic role."""

    if profile_id in APP_PROFILES or (profile_id == RP and producer_role == "application"):
        return "app"
    if profile_id in RUNTIME_PROFILES or (profile_id == RP and producer_role == "runtime"):
        return "runtime"
    if profile_id == RP:
        raise BehaviorError("Receipt Producer requires application or runtime producer_role")
    raise BehaviorError(f"unsupported mock profile: {profile_id}")


def _section(document: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = document.get(name)
    if not isinstance(value, Mapping):
        raise BehaviorError(f"semantic document requires object section {name!r}")
    return value


def _initial_state(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    state: dict[str, Any] = {}
    if isinstance(items, (str, bytes)):
        raise BehaviorError("initial_state must be an array")
    for index, item in enumerate(items):
        if not isinstance(item, Mapping) or set(item) != {"state", "value"}:
            raise BehaviorError(f"initial_state[{index}] is not the exact closed shape")
        name = item["state"]
        if not isinstance(name, str) or not name or name in state:
            raise BehaviorError("initial_state contains invalid or duplicate state names")
        value = item["value"]
        if isinstance(value, float):
            raise BehaviorError("floating-point state is forbidden")
        state[name] = value
    if not state:
        raise BehaviorError("initial_state must not be empty")
    return state


class _Transition:
    def __init__(self, before: dict[str, Any]) -> None:
        self.before = dict(before)
        self.after = dict(before)

    def set(self, name: str, value: Any) -> None:
        if name not in self.after:
            raise BehaviorError(f"operation requires missing initial state {name!r}")
        self.after[name] = value

    def increment(self, name: str) -> None:
        if name not in self.after:
            raise BehaviorError(f"operation requires missing initial state {name!r}")
        value = self.after[name]
        if isinstance(value, bool) or not isinstance(value, int):
            raise BehaviorError(f"state {name!r} is not an integer counter")
        self.after[name] = value + 1

    def result(
        self,
        decision: str,
        *tokens: str,
        asp_error: str | None = None,
        policy_reason: str | None = None,
        match_reason: str | None = None,
    ) -> BehaviorResult:
        if len(tokens) != len(set(tokens)) or not tokens:
            raise BehaviorError("behavior tokens must be non-empty and unique")
        return BehaviorResult(
            decision=decision,
            tokens=tuple(tokens),
            state_before=self.before,
            state_after=self.after,
            asp_error=asp_error,
            policy_reason=policy_reason,
            match_reason=match_reason,
        )


def _capacity_response_parts(
    document: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any], str, bool]:
    operational = _section(document, "operational")
    response = operational.get("capacity_response")
    if not isinstance(response, Mapping):
        raise BehaviorError("capacity response must be an error envelope")
    code = response.get("code")
    if code not in {
        "rate_limited",
        "capacity_state_unavailable",
        "service_unavailable",
    }:
        raise BehaviorError("capacity response has an unsupported error code")
    retryable = response.get("retryable")
    if not isinstance(retryable, bool):
        raise BehaviorError("capacity response must be retryable or non_retryable")
    if code in {"capacity_state_unavailable", "service_unavailable"} and "limit" in response:
        raise BehaviorError(f"{code} capacity response must omit limit")
    return operational, response, code, retryable


def _retry_after_parts(value: Any) -> tuple[str, int | str] | None:
    if value == "absent":
        return None
    if not isinstance(value, Mapping) or set(value) != {"form", "value"}:
        raise BehaviorError("Retry-After projection is not the exact closed shape")
    form = value.get("form")
    projected = value.get("value")
    if form == "delay_seconds":
        if (
            isinstance(projected, bool)
            or not isinstance(projected, int)
            or projected < 1
            or projected > SAFE_INTEGER
        ):
            raise BehaviorError("Retry-After delay_seconds must be a positive safe integer")
        return form, projected
    if form == "http_date":
        if not isinstance(projected, str) or not _is_rfc9110_http_date(projected):
            raise BehaviorError("Retry-After http_date is not RFC 9110 HTTP-date syntax")
        return form, projected
    raise BehaviorError("Retry-After projection has an unsupported form")


def _is_rfc9110_http_date(value: str) -> bool:
    for pattern, uses_two_digit_year in HTTP_DATE_PATTERNS:
        match = pattern.fullmatch(value)
        if match is None:
            continue
        year = int(match["year"])
        if uses_two_digit_year:
            year += 2000 if year <= 68 else 1900
        try:
            datetime(
                year,
                HTTP_MONTHS[match["month"]],
                int(match["day"]),
                int(match["hour"]),
                int(match["minute"]),
                int(match["second"]),
            )
        except ValueError:
            return False
        return True
    return False


def _bind_http_capacity_response(
    document: Mapping[str, Any], state: _Transition
) -> BehaviorResult:
    operational, response, code, retryable = _capacity_response_parts(document)
    retry_after = _retry_after_parts(
        operational.get("http_retry_after_hint", "absent")
    )
    if retry_after is not None and not retryable:
        raise BehaviorError("non-retryable capacity response cannot carry Retry-After")
    if code == "rate_limited" and retry_after is not None:
        form, value = retry_after
        limit = response.get("limit")
        if (
            form != "delay_seconds"
            or not isinstance(limit, Mapping)
            or limit.get("retry_after_seconds") != value
        ):
            raise BehaviorError(
                "rate_limited Retry-After must be delay_seconds equal to the body hint"
            )
    tokens = [
        "http_capacity_response_bound",
        "http_status_mapped",
        "http_no_store_applied",
    ]
    if retry_after is not None:
        tokens.append("http_retry_after_bound")
    return state.result("rejected", *tokens, asp_error=code)


def _validate_http_capacity_binding(
    document: Mapping[str, Any],
) -> tuple[str, int | str] | None:
    _, response, code, retryable = _capacity_response_parts(document)
    transport = _section(document, "transport")
    if set(transport) != {
        "binding",
        "authentication",
        "status",
        "cache_control_no_store",
        "retry_after",
    }:
        raise BehaviorError("HTTP capacity projection is not the exact closed shape")
    if (
        transport.get("binding") != "http"
        or transport.get("authentication") != "authenticated"
    ):
        raise BehaviorError("HTTP capacity response is outside the authenticated binding")
    required_status = 429 if code == "rate_limited" else 503
    if transport.get("status") != required_status:
        raise BehaviorError("HTTP capacity status does not match the ASP error code")
    if transport.get("cache_control_no_store") is not True:
        raise BehaviorError("HTTP capacity response is missing Cache-Control no-store")
    retry_after = _retry_after_parts(transport.get("retry_after"))
    if retry_after is None:
        return None
    if not retryable:
        raise BehaviorError("non-retryable capacity response cannot carry Retry-After")
    form, value = retry_after
    if code == "rate_limited":
        limit = response.get("limit")
        if (
            form != "delay_seconds"
            or not isinstance(limit, Mapping)
            or limit.get("retry_after_seconds") != value
        ):
            raise BehaviorError(
                "rate_limited Retry-After must be delay_seconds equal to the body hint"
            )
    return retry_after


def _validate_ahp_binding(
    document: Mapping[str, Any], *, control_kind: str, message_type: str
) -> Mapping[str, Any]:
    ahp = _section(document, "ahp")
    if set(ahp) != {
        "profile",
        "negotiated_profile",
        "authentication",
        "ahp_session_id",
        "representation_id",
        "representation_revision",
        "recorded_representation_revision",
        "binding_fingerprint",
        "recorded_binding_fingerprint",
        "control_id",
        "control_kind",
        "asp_message_type",
        "asp_session_id",
        "bound_asp_session_id",
        "asp_session_generation",
        "bound_asp_session_generation",
        "asp_grant_id",
        "bound_asp_grant_id",
        "asp_grant_hash",
        "bound_asp_grant_hash",
        "asp_surface_hash",
        "bound_asp_surface_hash",
        "asp_action_id",
        "bound_asp_action_id",
        "receipt_use",
    }:
        raise BehaviorError("ASP-over-AHP projection is not the exact closed shape")
    if (
        ahp.get("profile") != ASP_OVER_AHP
        or ahp.get("negotiated_profile") != ASP_OVER_AHP
    ):
        raise BehaviorError("ASP-over-AHP profile was not explicitly negotiated")
    if ahp.get("authentication") != "authenticated":
        raise BehaviorError("AHP carrier is not authenticated")
    for current, bound in (
        ("asp_session_id", "bound_asp_session_id"),
        ("asp_session_generation", "bound_asp_session_generation"),
        ("asp_grant_id", "bound_asp_grant_id"),
        ("asp_grant_hash", "bound_asp_grant_hash"),
        ("asp_surface_hash", "bound_asp_surface_hash"),
        ("asp_action_id", "bound_asp_action_id"),
    ):
        if ahp.get(current) != ahp.get(bound):
            raise BehaviorError("AHP carrier changed the bound ASP authority tuple")
    revision = ahp.get("representation_revision")
    recorded_revision = ahp.get("recorded_representation_revision")
    if (
        isinstance(revision, bool)
        or not isinstance(revision, int)
        or isinstance(recorded_revision, bool)
        or not isinstance(recorded_revision, int)
        or revision < recorded_revision
        or (
            revision == recorded_revision
            and ahp.get("binding_fingerprint")
            != ahp.get("recorded_binding_fingerprint")
        )
    ):
        raise BehaviorError("AHP representation revision is stale or conflicting")
    if (
        ahp.get("control_kind") != control_kind
        or ahp.get("asp_message_type") != message_type
    ):
        raise BehaviorError("AHP control does not match its bound ASP message")
    if control_kind == "present" and ahp.get("asp_action_id") != "none":
        raise BehaviorError("AHP presentation unexpectedly carries action authority")
    if control_kind == "invoke" and ahp.get("asp_action_id") == "none":
        raise BehaviorError("AHP invocation lacks an exact ASP action")
    if ahp.get("receipt_use") != "informational":
        raise BehaviorError("AHP receipt projection claims ASP authority")
    return ahp


def _validate_jcs_value(value: Any) -> None:
    if isinstance(value, float):
        if not math.isfinite(value) or (
            value == 0.0 and math.copysign(1.0, value) < 0
        ):
            raise BehaviorError(
                "canonical JSON floats must be finite and must not be negative zero"
            )
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > SAFE_INTEGER:
            raise BehaviorError("canonical JSON integers must be safe integers")
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise BehaviorError(
                "canonical JSON strings must not contain lone surrogates"
            ) from error
        return
    if isinstance(value, list):
        for item in value:
            _validate_jcs_value(item)
        return
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise BehaviorError("canonical JSON object member names must be strings")
        for key, item in value.items():
            _validate_jcs_value(key)
            _validate_jcs_value(item)
        return
    if value is None or isinstance(value, bool):
        return
    raise BehaviorError("value is outside the canonical I-JSON data model")


def _object_hash(domain: str, value: Any) -> str:
    wrapper = {"domain": domain, "object": value}
    _validate_jcs_value(wrapper)
    try:
        content = rfc8785.dumps(wrapper)
    except rfc8785.CanonicalizationError as error:
        raise BehaviorError("value cannot be canonicalized as RFC 8785 JSON") from error
    digest = hashlib.sha256(content).digest()
    return "sha-256:" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _hash_without(domain: str, value: Mapping[str, Any], member: str) -> str:
    hashing_view = copy.deepcopy(dict(value))
    hashing_view.pop(member, None)
    return _object_hash(domain, hashing_view)


def _external_schema_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if (
                key in {"$ref", "$dynamicRef"}
                and isinstance(item, str)
                and not item.startswith("#")
            ):
                refs.append(item)
            refs.extend(_external_schema_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_external_schema_refs(item))
    return refs


def _validate_embedded_schema(
    schema: Any,
    instance: Any,
    *,
    schema_hash: Any | None,
    label: str,
) -> None:
    if not isinstance(schema, Mapping):
        raise BehaviorError(f"{label} must be a JSON Schema object")
    normalized = dict(schema)
    if _external_schema_refs(normalized):
        raise BehaviorError(f"{label} must be self-contained")
    try:
        Draft202012Validator.check_schema(normalized)
    except SchemaError as error:
        raise BehaviorError(f"{label} is not a valid JSON Schema") from error
    if schema_hash is not None:
        canonical_schema_hash = _object_hash(
            "https://github.com/0al-spec/agent-surface/hash/action-input-schema/v1",
            normalized,
        )
        if schema_hash != canonical_schema_hash:
            raise BehaviorError(f"{label} hash is invalid")
    validator = Draft202012Validator(
        normalized,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    try:
        error = next(validator.iter_errors(instance), None)
    except Exception as validation_error:
        raise BehaviorError(f"{label} cannot be evaluated safely") from validation_error
    if error is not None:
        raise BehaviorError(f"value does not validate against {label}")


_JSON_POINTER = re.compile(r"^(?:/(?:[^~/]|~[01])*)*$")
_JSON_PATCH_ARRAY_INDEX = re.compile(r"^(?:0|[1-9][0-9]*)$")


def _editable_paths(value: Any) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(
            not isinstance(item, str) or not _JSON_POINTER.fullmatch(item)
            for item in value
        )
        or len(value) != len(set(value))
    ):
        raise BehaviorError("editable_paths must be unique RFC 6901 JSON Pointers")
    return tuple(value)


def _decode_json_pointer(pointer: Any) -> list[str]:
    if not isinstance(pointer, str) or not _JSON_POINTER.fullmatch(pointer):
        raise BehaviorError("redline path is not an RFC 6901 JSON Pointer")
    if pointer == "":
        return []
    return [
        item.replace("~1", "/").replace("~0", "~")
        for item in pointer[1:].split("/")
    ]


def _path_is_editable(path: str, editable_paths: Sequence[str]) -> bool:
    return any(
        path == allowed or allowed == "" or path.startswith(allowed + "/")
        for allowed in editable_paths
    )


def _json_patch_array_index(
    token: str,
    length: int,
    *,
    allow_end: bool,
) -> int:
    if not _JSON_PATCH_ARRAY_INDEX.fullmatch(token):
        raise IndexError(token)
    index = int(token)
    if index > length or (index == length and not allow_end):
        raise IndexError(index)
    return index


def _changed_json_pointers(before: Any, after: Any, pointer: str = "") -> set[str]:
    if type(before) is not type(after):
        return {pointer}
    if isinstance(before, Mapping):
        changed: set[str] = set()
        for key in set(before) | set(after):
            escaped = key.replace("~", "~0").replace("/", "~1")
            child = f"{pointer}/{escaped}"
            if key not in before or key not in after:
                changed.add(child)
            else:
                changed.update(_changed_json_pointers(before[key], after[key], child))
        return changed
    if isinstance(before, list):
        changed = set()
        for index in range(max(len(before), len(after))):
            child = f"{pointer}/{index}"
            if index >= len(before) or index >= len(after):
                changed.add(child)
            else:
                changed.update(
                    _changed_json_pointers(before[index], after[index], child)
                )
        return changed
    return set() if before == after else {pointer}


def _apply_redline(base: Any, patch: Any) -> Any:
    if not isinstance(patch, list) or not patch:
        raise BehaviorError("redline patch is not a non-empty operation list")
    candidate = copy.deepcopy(base)
    for operation in patch:
        if (
            not isinstance(operation, Mapping)
            or operation.get("op") not in {"add", "remove", "replace"}
            or set(operation)
            != (
                {"op", "path"}
                if operation.get("op") == "remove"
                else {"op", "path", "value"}
            )
        ):
            raise BehaviorError("redline operation is outside the closed patch subset")
        tokens = _decode_json_pointer(operation.get("path"))
        if not tokens:
            if operation["op"] == "remove":
                raise BehaviorError("redline cannot remove the document root")
            candidate = copy.deepcopy(operation["value"])
            continue
        target = candidate
        try:
            for token in tokens[:-1]:
                if isinstance(target, list):
                    index = _json_patch_array_index(
                        token,
                        len(target),
                        allow_end=False,
                    )
                    target = target[index]
                else:
                    target = target[token]
            last = tokens[-1]
            if isinstance(target, list):
                if operation["op"] == "add":
                    if last == "-":
                        target.append(copy.deepcopy(operation["value"]))
                    else:
                        index = _json_patch_array_index(
                            last,
                            len(target),
                            allow_end=True,
                        )
                        target.insert(index, copy.deepcopy(operation["value"]))
                elif operation["op"] == "remove":
                    index = _json_patch_array_index(
                        last,
                        len(target),
                        allow_end=False,
                    )
                    del target[index]
                else:
                    index = _json_patch_array_index(
                        last,
                        len(target),
                        allow_end=False,
                    )
                    target[index] = copy.deepcopy(operation["value"])
            elif isinstance(target, dict):
                if operation["op"] == "remove":
                    del target[last]
                elif operation["op"] == "replace":
                    if last not in target:
                        raise KeyError(last)
                    target[last] = copy.deepcopy(operation["value"])
                else:
                    target[last] = copy.deepcopy(operation["value"])
            else:
                raise TypeError("patch parent is not a container")
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise BehaviorError("redline path is not present in its exact base") from error
    return candidate


def _utc_timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise BehaviorError(f"{label} is not an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise BehaviorError(f"{label} is not an RFC 3339 UTC timestamp") from error
    if parsed.tzinfo != timezone.utc:
        raise BehaviorError(f"{label} is not an RFC 3339 UTC timestamp")
    return parsed


def _validate_human_elicitation(
    document: Mapping[str, Any],
) -> _HumanElicitationResult:
    elicitation = _section(document, "elicitation")
    required_fields = {
        "authentication",
        "authenticated_requester",
        "authenticated_presenter",
        "authenticated_subject",
        "selected_profile",
        "current_session_id",
        "current_session_generation",
        "current_grant_id",
        "current_grant_hash",
        "current_surface_hash",
        "recorded_revision",
        "recorded_request_hash",
        "recorded_response_hash",
        "lifecycle",
        "replay_retention_seconds",
        "evaluation_time",
        "terminal_accepted_at",
        "replay_record_state",
        "candidate_validation",
        "step_up_verification",
        "secret_material",
        "authority_use",
        "request",
        "response",
    }
    allowed_fields = required_fields | {
        "authenticated_verifier",
        "authoritative_step_up_result",
        "authoritative_base",
        "authoritative_input_schema",
        "agent_projection",
    }
    if not required_fields.issubset(elicitation) or not set(elicitation).issubset(
        allowed_fields
    ):
        raise BehaviorError("Human Elicitation projection is not the closed shape")
    request = elicitation["request"]
    response = elicitation["response"]
    if not isinstance(request, Mapping) or not isinstance(response, Mapping):
        raise BehaviorError("Human Elicitation messages must be objects")
    request_fields = {
        "type",
        "profile",
        "elicitation_id",
        "revision",
        "requester",
        "presenter",
        "kind",
        "session_id",
        "session_generation",
        "grant_id",
        "grant_hash",
        "surface_hash",
        "context",
        "context_hash",
        "prompt",
        "request",
        "expires_at",
        "request_hash",
    }
    response_fields = {
        "type",
        "profile",
        "elicitation_id",
        "revision",
        "kind",
        "disposition",
        "responder",
        "session_id",
        "session_generation",
        "grant_id",
        "grant_hash",
        "surface_hash",
        "context_hash",
        "request_hash",
        "resolved_at",
        "response_hash",
    }
    if response.get("disposition") == "answered":
        response_fields.add("response")
    if set(request) != request_fields or set(response) != response_fields:
        raise BehaviorError("Human Elicitation wire message is not the closed shape")
    requester = request.get("requester")
    presenter = request.get("presenter")
    requester_type = (
        requester.get("type") if isinstance(requester, Mapping) else None
    )
    presenter_type = (
        presenter.get("type") if isinstance(presenter, Mapping) else None
    )
    if (
        elicitation["authentication"] != "authenticated"
        or not isinstance(elicitation["authenticated_subject"], str)
        or not elicitation["authenticated_subject"]
        or elicitation["selected_profile"] != HUMAN_ELICITATION
        or request.get("profile") != HUMAN_ELICITATION
        or response.get("profile") != HUMAN_ELICITATION
        or request.get("type") != "elicitation.required"
        or response.get("type") != "elicitation.resolved"
        or request.get("requester") != elicitation["authenticated_requester"]
        or request.get("presenter") != elicitation["authenticated_presenter"]
        or response.get("responder") != elicitation["authenticated_presenter"]
        or requester_type not in {"application", "runtime"}
        or presenter_type not in {"application", "runtime"}
        or requester_type == presenter_type
        or not isinstance(requester.get("id"), str)
        or not requester["id"]
        or not isinstance(presenter.get("id"), str)
        or not presenter["id"]
        or set(requester) != {"type", "id"}
        or set(presenter) != {"type", "id"}
    ):
        raise BehaviorError(
            "Human Elicitation profile or participants are not authenticated"
        )
    repeated = (
        "elicitation_id",
        "revision",
        "kind",
        "session_id",
        "session_generation",
        "grant_id",
        "grant_hash",
        "surface_hash",
        "context_hash",
        "request_hash",
    )
    if any(request.get(field) != response.get(field) for field in repeated):
        raise BehaviorError("Human Elicitation response changed its request binding")
    for message_field, state_field in (
        ("session_id", "current_session_id"),
        ("session_generation", "current_session_generation"),
        ("grant_id", "current_grant_id"),
        ("grant_hash", "current_grant_hash"),
        ("surface_hash", "current_surface_hash"),
    ):
        if request.get(message_field) != elicitation.get(state_field):
            raise BehaviorError("Human Elicitation authority tuple is stale")
    if request.get("context_hash") != _object_hash(
        "https://github.com/0al-spec/agent-surface/hash/"
        "human-elicitation-context/v1",
        request.get("context"),
    ):
        raise BehaviorError("Human Elicitation context hash is invalid")
    if request.get("request_hash") != _hash_without(
        "https://github.com/0al-spec/agent-surface/hash/"
        "human-elicitation-request/v1",
        request,
        "request_hash",
    ):
        raise BehaviorError("Human Elicitation request hash is invalid")
    if response.get("response_hash") != _hash_without(
        "https://github.com/0al-spec/agent-surface/hash/"
        "human-elicitation-response/v1",
        response,
        "response_hash",
    ):
        raise BehaviorError("Human Elicitation response hash is invalid")
    context = request.get("context")
    prompt = request.get("prompt")
    context_fields = {
        "action_id",
        "mode",
        "input_hash",
        "proposal_id",
        "preview_id",
        "expected" + "_effects_hash",
        "reservation_id",
        "execution_hash",
        "policy_decision_hash",
        "approval_id",
    }
    action_binding = {"action_id", "mode", "input_hash"}
    if (
        not isinstance(context, Mapping)
        or not set(context).issubset(context_fields)
        or (set(context) & action_binding and not action_binding.issubset(context))
        or not isinstance(prompt, Mapping)
        or set(prompt) != {"title", "detail"}
        or any(
            not isinstance(prompt.get(field), str) or not prompt[field]
            for field in prompt
        )
    ):
        raise BehaviorError("Human Elicitation context or prompt is invalid")

    resolved_at = _utc_timestamp(response.get("resolved_at"), "resolved_at")
    request_expires_at = _utc_timestamp(request.get("expires_at"), "expires_at")
    evaluation_time = _utc_timestamp(
        elicitation.get("evaluation_time"), "evaluation_time"
    )
    if resolved_at > request_expires_at:
        raise BehaviorError("Human Elicitation response was resolved after expiry")
    if evaluation_time < resolved_at:
        raise BehaviorError("Human Elicitation response is from the future")
    replay_retention_seconds = elicitation.get("replay_retention_seconds")
    if (
        isinstance(replay_retention_seconds, bool)
        or not isinstance(replay_retention_seconds, int)
        or not 1 <= replay_retention_seconds <= SAFE_INTEGER
    ):
        raise BehaviorError("Human Elicitation replay retention is invalid")

    revision = request.get("revision")
    recorded_revision = elicitation.get("recorded_revision")
    if (
        isinstance(revision, bool)
        or not isinstance(revision, int)
        or isinstance(recorded_revision, bool)
        or not isinstance(recorded_revision, int)
        or revision < 1
        or recorded_revision < 0
        or revision < recorded_revision
        or revision > recorded_revision + 1
    ):
        raise BehaviorError("Human Elicitation revision is stale or conflicting")
    exact_replay = revision == recorded_revision
    if exact_replay and (
        request.get("request_hash") != elicitation["recorded_request_hash"]
        or response.get("response_hash") != elicitation["recorded_response_hash"]
    ):
        raise BehaviorError("Human Elicitation revision is stale or conflicting")

    disposition = response.get("disposition")
    if disposition not in {"answered", "declined", "cancelled", "expired"}:
        raise BehaviorError("Human Elicitation response disposition is invalid")
    terminal_state = "resolved" if disposition == "answered" else disposition
    replay_record_state = elicitation.get("replay_record_state")
    terminal_accepted_value = elicitation.get("terminal_accepted_at")
    if exact_replay:
        terminal_accepted_at = _utc_timestamp(
            terminal_accepted_value, "terminal_accepted_at"
        )
        if not resolved_at <= terminal_accepted_at <= evaluation_time:
            raise BehaviorError(
                "Human Elicitation terminal acceptance time is invalid"
            )
        try:
            retained_until = terminal_accepted_at + timedelta(
                seconds=replay_retention_seconds
            )
        except OverflowError as error:
            raise BehaviorError(
                "Human Elicitation replay retention cannot be evaluated"
            ) from error
        if (
            elicitation.get("lifecycle") != terminal_state
            or replay_record_state != "retained"
            or evaluation_time > retained_until
        ):
            raise BehaviorError(
                "Human Elicitation terminal replay record is unavailable"
            )
    elif (
        elicitation.get("lifecycle") != "pending"
        or replay_record_state != "not_applicable"
        or terminal_accepted_value != "absent"
    ):
        raise BehaviorError("Human Elicitation lifecycle is inconsistent")

    if elicitation.get("authority_use") != "informational":
        raise BehaviorError("Human Elicitation cannot create authority")
    if disposition != "answered":
        if "response" in response:
            raise BehaviorError(
                "non-answered Human Elicitation response carries an answer"
            )
        return _HumanElicitationResult(
            kind=str(request.get("kind")),
            disposition=disposition,
            terminal_replay=exact_replay,
        )

    kind = request.get("kind")
    request_body = request.get("request")
    response_body = response.get("response")
    if not isinstance(request_body, Mapping) or not isinstance(response_body, Mapping):
        raise BehaviorError("Human Elicitation kind payload is not an object")
    if kind == "clarify":
        if set(request_body) != {
            "question_id",
            "response_schema",
            "response_schema_hash",
            "max_bytes",
        } or set(response_body) != {"answer"}:
            raise BehaviorError("clarification payload is not the closed shape")
        answer = response_body.get("answer")
        max_bytes = request_body.get("max_bytes")
        if (
            isinstance(max_bytes, bool)
            or not isinstance(max_bytes, int)
            or not 1 <= max_bytes <= SAFE_INTEGER
        ):
            raise BehaviorError("clarification byte bound is invalid")
        _validate_jcs_value(answer)
        try:
            encoded = rfc8785.dumps(answer)
        except rfc8785.CanonicalizationError as error:
            raise BehaviorError(
                "clarification answer cannot be canonicalized"
            ) from error
        if len(encoded) > max_bytes:
            raise BehaviorError("clarification answer exceeds its bound")
        _validate_embedded_schema(
            request_body.get("response_schema"),
            answer,
            schema_hash=request_body.get("response_schema_hash"),
            label="clarification response_schema",
        )
    elif kind == "choose":
        if set(request_body) != {
            "question_id",
            "options",
            "min_selected",
            "max_selected",
        } or set(response_body) != {"option_ids"}:
            raise BehaviorError("choice payload is not the closed shape")
        options = request_body.get("options")
        if (
            not isinstance(options, list)
            or not options
            or any(
                not isinstance(item, Mapping)
                or set(item) != {"option_id", "label", "detail"}
                for item in options
            )
        ):
            raise BehaviorError("choice options are not the closed shape")
        option_ids = [item.get("option_id") for item in options]
        min_selected = request_body.get("min_selected")
        max_selected = request_body.get("max_selected")
        selected = response_body.get("option_ids")
        if (
            any(not isinstance(item, str) or not item for item in option_ids)
            or len(option_ids) != len(set(option_ids))
            or isinstance(min_selected, bool)
            or not isinstance(min_selected, int)
            or isinstance(max_selected, bool)
            or not isinstance(max_selected, int)
            or not 0 <= min_selected <= max_selected <= len(option_ids)
            or not isinstance(selected, list)
            or any(not isinstance(item, str) or not item for item in selected)
            or len(selected) != len(set(selected))
            or not set(selected).issubset(option_ids)
            or not min_selected <= len(selected) <= max_selected
        ):
            raise BehaviorError("choice response is outside the offered option set")
    elif kind == "step_up":
        if set(request_body) != {
            "transaction_text",
            "required_assurance",
            "max_age_seconds",
        } or set(response_body) != {
            "result_ref",
            "verifier",
            "achieved_assurance",
            "authenticated_at",
            "expires_at",
        }:
            raise BehaviorError("step-up payload is not the closed shape")
        authenticated_at = _utc_timestamp(
            response_body.get("authenticated_at"), "authenticated_at"
        )
        step_up_expires_at = _utc_timestamp(
            response_body.get("expires_at"), "step-up expires_at"
        )
        max_age_seconds = request_body.get("max_age_seconds")
        achieved_assurance = response_body.get("achieved_assurance")
        required_assurance = request_body.get("required_assurance")
        verifier = response_body.get("verifier")
        authoritative_result = elicitation.get("authoritative_step_up_result")
        authoritative_fields = {
            "status",
            "result_ref",
            "verifier",
            "audience",
            "subject",
            "elicitation_id",
            "revision",
            "context_hash",
            "achieved_assurance",
            "authenticated_at",
            "expires_at",
        }
        if (
            elicitation.get("step_up_verification") != "verified"
            or elicitation.get("secret_material") != "absent"
            or not isinstance(authoritative_result, Mapping)
            or set(authoritative_result) != authoritative_fields
            or authoritative_result.get("status") != "verified"
            or authoritative_result.get("result_ref")
            != response_body.get("result_ref")
            or authoritative_result.get("verifier") != verifier
            or authoritative_result.get("audience")
            != elicitation.get("authenticated_requester")
            or authoritative_result.get("subject")
            != elicitation.get("authenticated_subject")
            or authoritative_result.get("elicitation_id")
            != request.get("elicitation_id")
            or authoritative_result.get("revision") != request.get("revision")
            or authoritative_result.get("context_hash")
            != request.get("context_hash")
            or authoritative_result.get("achieved_assurance")
            != achieved_assurance
            or authoritative_result.get("authenticated_at")
            != response_body.get("authenticated_at")
            or authoritative_result.get("expires_at")
            != response_body.get("expires_at")
            or not isinstance(response_body.get("result_ref"), str)
            or not response_body["result_ref"]
            or not isinstance(verifier, Mapping)
            or set(verifier) != {"type", "id"}
            or verifier.get("type") not in {"application", "runtime", "external"}
            or not isinstance(verifier.get("id"), str)
            or not verifier["id"]
            or verifier != elicitation.get("authenticated_verifier")
            or not isinstance(required_assurance, list)
            or not required_assurance
            or any(
                not isinstance(item, str) or not item
                for item in required_assurance
            )
            or len(required_assurance) != len(set(required_assurance))
            or not isinstance(achieved_assurance, list)
            or not achieved_assurance
            or any(
                not isinstance(item, str) or not item
                for item in achieved_assurance
            )
            or len(achieved_assurance) != len(set(achieved_assurance))
            or not set(required_assurance).issubset(achieved_assurance)
            or isinstance(max_age_seconds, bool)
            or not isinstance(max_age_seconds, int)
            or not 1 <= max_age_seconds <= SAFE_INTEGER
            or not authenticated_at
            <= resolved_at
            <= evaluation_time
            <= step_up_expires_at
            or (evaluation_time - authenticated_at).total_seconds()
            > max_age_seconds
        ):
            raise BehaviorError("step-up result is unverified or contains a secret")
    elif kind == "edit":
        if set(request_body) != {
            "base",
            "base_hash",
            "input_schema_hash",
            "editable_paths",
        } or set(response_body) != {"candidate", "candidate_hash"}:
            raise BehaviorError("edit payload is not the closed shape")
        base = request_body.get("base")
        candidate = response_body.get("candidate")
        editable_paths = _editable_paths(request_body.get("editable_paths"))
        if (
            elicitation.get("candidate_validation") != "passed"
            or base != elicitation.get("authoritative_base")
            or request_body.get("base_hash")
            != _object_hash(
                "https://github.com/0al-spec/agent-surface/hash/action-input/v1",
                base,
            )
            or request.get("context", {}).get("input_hash")
            != request_body.get("base_hash")
            or response_body.get("candidate_hash")
            != _object_hash(
                "https://github.com/0al-spec/agent-surface/hash/action-input/v1",
                candidate,
            )
        ):
            raise BehaviorError("edited candidate is stale or not rebound")
        if any(
            not _path_is_editable(path, editable_paths)
            for path in _changed_json_pointers(base, candidate)
        ):
            raise BehaviorError("edited candidate changed a forbidden path")
        _validate_embedded_schema(
            elicitation.get("authoritative_input_schema"),
            candidate,
            schema_hash=request_body.get("input_schema_hash"),
            label="authoritative action input schema",
        )
    elif kind == "redline":
        allowed_request_fields = {
            "base_hash",
            "media_type",
            "patch_schema",
            "patch_schema_hash",
        }
        if "editable_paths" in request_body:
            allowed_request_fields.add("editable_paths")
        if set(request_body) != allowed_request_fields or set(response_body) != {
            "base_hash",
            "patch",
            "candidate_hash",
        }:
            raise BehaviorError("redline payload is not the closed shape")
        if request_body.get("media_type") != "application/json-patch+json":
            raise BehaviorError("redline media type is unsupported")
        _validate_embedded_schema(
            request_body.get("patch_schema"),
            response_body.get("patch"),
            schema_hash=request_body.get("patch_schema_hash"),
            label="redline patch_schema",
        )
        editable_paths = (
            _editable_paths(request_body.get("editable_paths"))
            if "editable_paths" in request_body
            else ()
        )
        if editable_paths and any(
            not _path_is_editable(str(operation.get("path")), editable_paths)
            for operation in response_body.get("patch", [])
            if isinstance(operation, Mapping)
        ):
            raise BehaviorError("redline patch targets a forbidden path")
        base = elicitation.get("authoritative_base")
        candidate = _apply_redline(base, response_body.get("patch"))
        if (
            elicitation.get("candidate_validation") != "passed"
            or request_body.get("base_hash")
            != _object_hash(
                "https://github.com/0al-spec/agent-surface/hash/action-input/v1",
                base,
            )
            or request.get("context", {}).get("input_hash")
            != request_body.get("base_hash")
            or response_body.get("base_hash") != request_body.get("base_hash")
            or response_body.get("candidate_hash")
            != _object_hash(
                "https://github.com/0al-spec/agent-surface/hash/action-input/v1",
                candidate,
            )
        ):
            raise BehaviorError("redline base or candidate result is invalid")
        _validate_embedded_schema(
            elicitation.get("authoritative_input_schema"),
            candidate,
            schema_hash=None,
            label="authoritative action input schema",
        )
    else:
        raise BehaviorError("unsupported Human Elicitation kind")
    if kind != "step_up" and (
        elicitation.get("step_up_verification") != "not_applicable"
        or elicitation.get("secret_material") != "absent"
        or "authenticated_verifier" in elicitation
        or "authoritative_step_up_result" in elicitation
    ):
        raise BehaviorError("non-step-up response carries authentication state")
    return _HumanElicitationResult(
        kind=kind,
        disposition=disposition,
        terminal_replay=exact_replay,
    )


def _risk_language(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 63
        or RISK_LANGUAGE_PATTERN.fullmatch(value) is None
    ):
        raise BehaviorError(f"{label} is not a canonical language tag")
    subtags = value.split("-")
    index = 1
    if (
        index < len(subtags)
        and len(subtags[index]) == 4
        and subtags[index].isalpha()
    ):
        index += 1
    if index < len(subtags) and (
        (len(subtags[index]) == 2 and subtags[index].isalpha())
        or (len(subtags[index]) == 3 and subtags[index].isdigit())
    ):
        index += 1
    variants = subtags[index:]
    if len(variants) != len(set(variants)):
        raise BehaviorError(f"{label} repeats a variant subtag")
    return value


def _risk_summary(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 512
        or any(
            ord(character) <= 0x1F
            or 0x7F <= ord(character) <= 0x9F
            or ord(character) in {0x061C, 0x200E, 0x200F}
            or 0x202A <= ord(character) <= 0x202E
            or 0x2066 <= ord(character) <= 0x2069
            for character in value
        )
    ):
        raise BehaviorError(f"{label} is not bounded display prose")
    return value


def _select_risk_localization(
    localizations: Sequence[Mapping[str, Any]],
    preferences: Sequence[Any],
    default_language: str,
) -> Mapping[str, Any]:
    if (
        isinstance(preferences, (str, bytes))
        or not 0 <= len(preferences) <= 16
    ):
        raise BehaviorError("risk language preferences must be a bounded array")
    by_language = {
        localization["language"]: localization for localization in localizations
    }
    for raw_preference in preferences:
        preference = _risk_language(raw_preference, label="risk language preference")
        subtags = preference.split("-")
        while subtags:
            candidate = "-".join(subtags)
            if candidate in by_language:
                return by_language[candidate]
            subtags.pop()
            if subtags and len(subtags[-1]) == 1:
                subtags.pop()
    return by_language[default_language]


def _validate_risk_explanation_hint(
    document: Mapping[str, Any],
) -> tuple[Mapping[str, Any], list[Mapping[str, Any]], str]:
    """Validate publisher-owned hint data independently of Runtime state."""

    projection = _section(document, "risk_explanation")
    publisher_fields = {
        "action_id",
        "hint_action_id",
        "declared_risk",
        "declared_effect_ids",
        "hint_surface_hash",
        "hint",
    }
    if not publisher_fields.issubset(projection):
        raise BehaviorError("risk explanation publisher projection is incomplete")
    action_id = projection.get("action_id")
    hint_action_id = projection.get("hint_action_id")
    if (
        not isinstance(action_id, str)
        or not action_id
        or not isinstance(hint_action_id, str)
        or not hint_action_id
        or hint_action_id != action_id
    ):
        raise _RiskExplanationBindingError(
            "risk explanation action binding is stale or substituted"
        )
    if projection.get("declared_risk") not in {
        "read",
        "propose",
        "write",
        "public_side_effect",
        "external_side_effect",
        "financial_side_effect",
        "destructive",
        "privileged",
    }:
        raise BehaviorError("risk explanation canonical risk is invalid")
    declared_effect_ids = projection.get("declared_effect_ids")
    if (
        not isinstance(declared_effect_ids, list)
        or any(
            not isinstance(effect_id, str) or not effect_id
            for effect_id in declared_effect_ids
        )
        or len(declared_effect_ids) != len(set(declared_effect_ids))
    ):
        raise BehaviorError("risk explanation declared effects are invalid")
    hint = projection.get("hint")
    if not isinstance(hint, Mapping) or set(hint) != {
        "default_language",
        "localizations",
    }:
        raise BehaviorError("risk explanation hint is not the closed shape")
    default_language = _risk_language(
        hint.get("default_language"),
        label="risk default language",
    )
    localizations = hint.get("localizations")
    if (
        not isinstance(localizations, list)
        or not 1 <= len(localizations) <= 16
    ):
        raise BehaviorError("risk explanation localizations are not bounded")
    languages: list[str] = []
    for index, localization in enumerate(localizations):
        if not isinstance(localization, Mapping) or set(localization) != {
            "language",
            "summary",
            "effect_summaries",
        }:
            raise BehaviorError("risk localization is not the closed shape")
        language = _risk_language(
            localization.get("language"),
            label=f"risk localization {index} language",
        )
        languages.append(language)
        _risk_summary(
            localization.get("summary"),
            label=f"risk localization {language} summary",
        )
        effect_summaries = localization.get("effect_summaries")
        if not isinstance(effect_summaries, list):
            raise BehaviorError("risk effect summaries must be an array")
        localized_effect_ids: list[str] = []
        for effect_summary in effect_summaries:
            if not isinstance(effect_summary, Mapping) or set(effect_summary) != {
                "effect_id",
                "summary",
            }:
                raise BehaviorError("risk effect summary is not the closed shape")
            effect_id = effect_summary.get("effect_id")
            if not isinstance(effect_id, str) or not effect_id:
                raise BehaviorError("risk effect summary has an invalid effect id")
            localized_effect_ids.append(effect_id)
            _risk_summary(
                effect_summary.get("summary"),
                label=f"risk effect {effect_id} summary",
            )
        if localized_effect_ids != declared_effect_ids:
            raise BehaviorError(
                "risk effect summaries do not exactly cover declared effects"
            )
    if languages != sorted(languages) or len(languages) != len(set(languages)):
        raise BehaviorError(
            "risk explanation languages must be unique and canonically sorted"
        )
    if default_language not in languages:
        raise BehaviorError("risk default language has no exact localization")
    return projection, localizations, default_language


def _validate_risk_explanation_publisher(
    document: Mapping[str, Any],
) -> None:
    projection, _, _ = _validate_risk_explanation_hint(document)
    surface = _section(document, "surface")
    if projection.get("hint_surface_hash") != surface.get("candidate_hash"):
        raise _RiskExplanationBindingError(
            "risk explanation publisher binding is not the candidate surface"
        )


def _validate_risk_explanation_projection(
    document: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Validate Runtime-owned presentation against the retained Grant surface."""

    projection, localizations, default_language = _validate_risk_explanation_hint(
        document
    )
    runtime_fields = {
        "action_id",
        "hint_action_id",
        "declared_risk",
        "declared_effect_ids",
        "hint_surface_hash",
        "hint",
        "language_preferences",
        "selected_language",
        "rendered_summary",
        "rendered_effect_summaries",
        "rendering",
        "escaped",
        "bidi_isolated",
        "authority_use",
        "agent_projection",
    }
    if set(projection) != runtime_fields:
        raise BehaviorError("risk explanation Runtime projection is not the closed shape")
    surface = _section(document, "surface")
    surface_fields = {
        "status",
        "version",
        "retained_hash",
        "candidate_hash",
        "references",
        "mode",
        "action_semantics",
    }
    if (
        set(surface) != surface_fields
        or surface.get("status") != "current"
        or not isinstance(surface.get("version"), str)
        or not surface.get("version")
        or not isinstance(surface.get("retained_hash"), str)
        or not surface.get("retained_hash")
        or not isinstance(surface.get("candidate_hash"), str)
        or not surface.get("candidate_hash")
        or surface.get("references") != "complete"
        or surface.get("mode") not in {"standard", "proposal_only"}
        or surface.get("action_semantics")
        not in {"closed_read_propose", "state_changing"}
        or (
            surface.get("mode") == "proposal_only"
            and surface.get("action_semantics") != "closed_read_propose"
        )
    ):
        raise _RiskExplanationBindingError(
            "risk explanation Runtime presentation lacks the complete verified "
            "retained manifest projection"
        )
    if projection.get("hint_surface_hash") != surface.get("retained_hash"):
        raise _RiskExplanationBindingError(
            "risk explanation Runtime binding is not the retained surface"
        )

    preferences = projection.get("language_preferences")
    if not isinstance(preferences, list):
        raise BehaviorError("risk language preferences must be an array")
    selected = _select_risk_localization(
        localizations,
        preferences,
        default_language,
    )
    if (
        projection.get("selected_language") != selected["language"]
        or projection.get("rendered_summary") != selected["summary"]
        or projection.get("rendered_effect_summaries")
        != selected["effect_summaries"]
    ):
        raise BehaviorError(
            "rendered risk explanation differs from RFC 4647 Lookup selection"
        )
    if (
        projection.get("rendering") != "literal_with_canonical_facts"
        or projection.get("escaped") is not True
        or projection.get("bidi_isolated") is not True
        or projection.get("authority_use") != "advisory_only"
        or projection.get("agent_projection") != "absent"
    ):
        raise BehaviorError(
            "risk explanation must remain escaped, bidi-isolated, literal, "
            "advisory, and agent-hidden"
        )
    return selected


def _surface(operation: str, document: Mapping[str, Any], state: _Transition) -> BehaviorResult:
    if operation != "publish_manifest":
        raise BehaviorError(f"Surface Publisher does not support {operation!r}")
    surface = _section(document, "surface")
    operational = document.get("operational")
    has_risk_explanation = "risk_explanation" in document
    if has_risk_explanation:
        try:
            _validate_risk_explanation_publisher(document)
        except BehaviorError:
            return state.result(
                "rejected",
                "risk_explanation_rejected",
                "manifest_rejected",
                asp_error="surface_incompatible",
            )
    if operational is not None:
        operational = _section(document, "operational")
        if operational.get("declaration") != "valid":
            return state.result(
                "rejected", "manifest_rejected", asp_error="surface_incompatible"
            )
    incompatible = (
        surface.get("references") != "complete"
        or surface.get("candidate_hash") != surface.get("retained_hash")
        or (
            surface.get("mode") == "proposal_only"
            and surface.get("action_semantics") != "closed_read_propose"
        )
    )
    if incompatible:
        return state.result(
            "rejected", "manifest_rejected", asp_error="surface_incompatible"
        )
    state.increment("manifest.accepted_count")
    state.increment("surface.version_binding_count")
    if operational is not None:
        if has_risk_explanation:
            return state.result(
                "accepted",
                "operational_limits_validated",
                "risk_explanation_validated",
                "manifest_published",
            )
        return state.result(
            "accepted", "operational_limits_validated", "manifest_published"
        )
    if has_risk_explanation:
        return state.result(
            "accepted", "risk_explanation_validated", "manifest_published"
        )
    return state.result("accepted", "manifest_published")


def _grant(operation: str, document: Mapping[str, Any], state: _Transition) -> BehaviorResult:
    surface = _section(document, "surface")
    grant = _section(document, "grant")
    if operation == "issue_grant":
        if surface.get("status") != "current":
            return state.result("rejected", "grant_rejected", "current_state_checked")
        requested = grant.get("requested_actions")
        issued = grant.get("issued_actions")
        if not isinstance(requested, list) or not isinstance(issued, list):
            raise BehaviorError("Grant actions must be arrays")
        if not set(issued).issubset(set(requested)):
            return state.result("rejected", "grant_rejected")
        if grant.get("companion_closure") != "closed":
            return state.result("rejected", "grant_rejected")
        if grant.get("passport_status") != "current":
            return state.result("rejected", "grant_rejected", "current_state_checked")
        state.increment("grant.issued_count")
        state.increment("credential.issued_count")
        return state.result("accepted", "grant_issued", "tuple_checked")
    if operation != "revoke_grant":
        raise BehaviorError(f"Grant Issuer does not support {operation!r}")
    if grant.get("revocation_request_hash") != grant.get("recorded_revocation_request_hash"):
        raise BehaviorError("mock revocation request does not match its authoritative record")
    if grant.get("status") == "revoked" or grant.get("revocation_state") == "revoked":
        return state.result(
            "replayed",
            "grant_revoked",
            "original_revocation_replayed",
            "revocation_confirmed",
        )
    state.set("grant.lifecycle", "revoked")
    for name in (
        "grant.child_active_count",
        "credential.active_count",
        "proof_session.active_count",
        "execution_token.active_count",
        "reservation.active_count",
    ):
        state.set(name, 0)
    for name in (
        "control_event.emitted_count",
        "revocation.effective_count",
        "revocation.confirmed_count",
        "revocation.fence_count",
    ):
        state.increment(name)
    state.set("revocation.confirmed_after_effective", True)
    return state.result(
        "accepted",
        "grant_revoked",
        "child_grant_revoked",
        "credential_invalidated",
        "proof_session_invalidated",
        "execution_token_invalidated",
        "reservation_invalidated",
        "control_event_emitted",
        "revocation_fence_established",
        "revocation_confirmed",
    )


def _action(operation: str, document: Mapping[str, Any], state: _Transition) -> BehaviorResult:
    grant = _section(document, "grant")
    execution = _section(document, "execution")
    operational = document.get("operational")
    if operation == "apply_human_elicitation_candidate":
        try:
            elicitation_result = _validate_human_elicitation(document)
            if elicitation_result.kind not in {"edit", "redline"}:
                raise BehaviorError(
                    "Action Executor accepts only edited or redlined candidates"
                )
            if elicitation_result.disposition != "answered":
                raise BehaviorError(
                    "Action Executor requires an answered candidate response"
                )
        except BehaviorError:
            return state.result(
                "rejected",
                "elicitation_binding_rejected",
                "elicitation_candidate_rejected",
                "elicitation_authority_retained",
                "action_dispatch_suppressed",
                asp_error="elicitation_invalid",
            )
        if elicitation_result.terminal_replay:
            return state.result(
                "accepted",
                "elicitation_binding_validated",
                "elicitation_response_accepted",
                "elicitation_authority_unchanged",
            )
        state.increment("application.proposal_revision")
        state.increment("application.proposal_update_count")
        kind_token = (
            "elicitation_candidate_revalidated"
            if elicitation_result.kind == "edit"
            else "elicitation_redline_applied"
        )
        return state.result(
            "accepted",
            "elicitation_binding_validated",
            kind_token,
            "elicitation_prior_authority_invalidated",
            "elicitation_authority_unchanged",
        )
    if operation == "bind_http_capacity_response":
        return _bind_http_capacity_response(document, state)
    if operation in {"deliver_event", "retransmit_event"}:
        operational = _section(document, "operational")
        if operation == "retransmit_event":
            state.increment("operational.event.transmission_count")
            return state.result(
                "accepted",
                "event_delivery_retransmitted",
                "event_identity_reused",
                "event_transmitted",
            )
        if (
            operational.get("limiter_state") != "available"
            or operational.get("event_capacity") != "available"
        ):
            state.increment("operational.event.queued_count")
            return state.result(
                "rejected",
                "operational_capacity_rejected",
                "event_delivery_queued",
            )
        for name in (
            "operational.event.delivery_record_count",
            "operational.event.delivery_identity_count",
            "operational.event.first_delivery_count",
            "operational.event.in_flight_count",
            "operational.event.transmission_count",
            "event.cursor_advance_count",
        ):
            state.increment(name)
        return state.result(
            "accepted", "event_first_delivery_admitted", "event_transmitted"
        )
    if operation == "replay_action":
        if execution.get("input_schema_hash") != execution.get("recorded_input_schema_hash"):
            return state.result(
                "rejected",
                "input_schema_checked",
                "normalization_checked",
                "action_rejected",
                "approval_not_reopened",
                asp_error="idempotency_conflict",
            )
        if execution.get("normalization") != "fixed_point":
            return state.result(
                "rejected",
                "input_schema_checked",
                "normalization_checked",
                "action_rejected",
                asp_error="input_not_normalized",
            )
        if any(
            execution.get(current) != execution.get(recorded)
            for current, recorded in (
                ("input_hash", "recorded_input_hash"),
                ("execution_hash", "recorded_execution_hash"),
                ("approval_hash", "recorded_approval_hash"),
            )
        ):
            if operational is not None:
                return state.result(
                    "rejected", "action_rejected", asp_error="idempotency_conflict"
                )
            return state.result(
                "rejected",
                "action_rejected",
                "approval_not_reopened",
                asp_error="idempotency_conflict",
            )
        if operational is not None:
            return state.result(
                "replayed", "original_result_replayed", "operational_identity_reused"
            )
        return state.result("replayed", "original_result_replayed", "same_receipt_replayed")
    if operation != "invoke_action":
        raise BehaviorError(f"Action Executor does not support {operation!r}")
    if execution.get("normalization") != "fixed_point":
        return state.result(
            "rejected",
            "input_schema_checked",
            "normalization_checked",
            "action_rejected",
            asp_error="input_not_normalized",
        )
    if execution.get("sender_credential_audience") != execution.get("bound_credential_audience"):
        return state.result(
            "rejected",
            "credential_rejected",
            "tuple_checked",
            "action_rejected",
            asp_error="grant_proof_invalid",
        )
    if execution.get("proof_session_binding") != execution.get("bound_session_binding"):
        return state.result(
            "rejected",
            "proof_rejected",
            "tuple_checked",
            "action_rejected",
            asp_error="grant_proof_invalid",
        )
    if grant.get("claimed_issuer") != grant.get("issuer"):
        return state.result(
            "rejected", "action_rejected", "tuple_checked", asp_error="integrity_mismatch"
        )
    if grant.get("status") != "active" or grant.get("revocation_state") == "revoked":
        return state.result(
            "rejected", "action_rejected", "current_state_checked", asp_error="grant_revoked"
        )
    if execution.get("runtime_identity") != execution.get("bound_runtime_identity"):
        return state.result(
            "rejected", "action_rejected", "current_state_checked", asp_error="runtime_untrusted"
        )
    if execution.get("attestation") != "current":
        return state.result(
            "rejected", "action_rejected", "current_state_checked", asp_error="runtime_untrusted"
        )
    if execution.get("policy") != "allow":
        state.increment("receipt.application_count")
        return state.result(
            "rejected",
            "action_rejected",
            "denial_recorded",
            "application_receipt_emitted",
            asp_error="risk_denied",
        )
    if operational is not None:
        operational = _section(document, "operational")
        if operational.get("limiter_state") != "available":
            return state.result(
                "rejected",
                "operational_capacity_rejected",
                "operational_state_retained",
                asp_error="capacity_state_unavailable",
            )
        if operational.get("action_capacity") != "available":
            return state.result(
                "rejected",
                "operational_limits_checked",
                "operational_capacity_rejected",
                asp_error="rate_limited",
            )
        for name in (
            "operational.action.window_count",
            "operational.action.secondary_window_count",
            "operational.action.slot_acquisition_count",
            "application.workload_count",
            "receipt.application_count",
            "action.dispatch_count",
            "action.effect_count",
            "idempotency.record_count",
            "budget.application_charge",
        ):
            state.increment(name)
        return state.result(
            "accepted",
            "operational_limits_checked",
            "operational_admission_committed",
            "action_accepted",
            "application_receipt_emitted",
        )
    for name in (
        "action.dispatch_count",
        "action.effect_count",
        "idempotency.record_count",
        "budget.application_charge",
        "receipt.application_count",
    ):
        state.increment(name)
    return state.result(
        "accepted",
        "action_accepted",
        "tuple_checked",
        "current_state_checked",
        "application_receipt_emitted",
    )


def _receipt(
    operation: str,
    document: Mapping[str, Any],
    state: _Transition,
    producer_role: str | None,
) -> BehaviorResult:
    if producer_role not in PRODUCER_ROLES:
        raise BehaviorError("Receipt Producer requires a producer_role")
    receipt = _section(document, "receipt")
    if operation == "verify_receipt":
        if receipt.get("integrity") != "valid":
            return state.result(
                "rejected", "receipt_rejected", asp_error="integrity_mismatch"
            )
        return state.result("accepted", "receipt_verified")
    if operation != "produce_receipt":
        raise BehaviorError(f"Receipt Producer does not support {operation!r}")
    if receipt.get("authority_use") != "prohibited":
        return state.result("rejected", "receipt_rejected")
    role_observation = (
        "application_effect" if producer_role == "application" else "runtime_observation"
    )
    if (
        receipt.get("claimed_observation") != role_observation
        or receipt.get("integrity") != "valid"
        or receipt.get("origin") != "observed"
    ):
        return state.result(
            "rejected", "receipt_rejected", asp_error="integrity_mismatch"
        )
    state_name = (
        "receipt.application_count" if producer_role == "application" else "receipt.runtime_count"
    )
    state.increment(state_name)
    emitted = (
        "application_receipt_emitted"
        if producer_role == "application"
        else "runtime_receipt_emitted"
    )
    return state.result("accepted", emitted, "receipt_verified")


def _runtime(operation: str, document: Mapping[str, Any], state: _Transition) -> BehaviorResult:
    grant = _section(document, "grant")
    execution = _section(document, "execution")
    runtime = _section(document, "runtime")
    operational = document.get("operational")
    if operation == "render_risk_explanation":
        try:
            _validate_risk_explanation_projection(document)
        except BehaviorError:
            return state.result(
                "stopped",
                "risk_explanation_binding_rejected",
                "risk_explanation_suppressed",
                "canonical_risk_presented",
                "canonical_effects_presented",
                "risk_explanation_authority_unchanged",
                "agent_instruction_suppressed",
            )
        state.increment("runtime.risk_explanation_presentation_count")
        return state.result(
            "accepted",
            "risk_explanation_selected",
            "risk_explanation_rendered_literal",
            "canonical_risk_presented",
            "canonical_effects_presented",
            "risk_explanation_authority_unchanged",
            "agent_instruction_suppressed",
        )
    if operation == "mediate_human_elicitation":
        raw_elicitation = document.get("elicitation")
        raw_request = (
            raw_elicitation.get("request")
            if isinstance(raw_elicitation, Mapping)
            else None
        )
        kind = raw_request.get("kind") if isinstance(raw_request, Mapping) else None
        try:
            elicitation_result = _validate_human_elicitation(document)
        except BehaviorError:
            if kind == "step_up":
                return state.result(
                    "rejected",
                    "elicitation_binding_rejected",
                    "step_up_result_rejected",
                    "human_secret_withheld",
                    "elicitation_authority_retained",
                    asp_error="elicitation_invalid",
                )
            return state.result(
                "rejected",
                "elicitation_binding_rejected",
                "elicitation_response_suppressed",
                "elicitation_authority_retained",
                "action_dispatch_suppressed",
                asp_error="elicitation_invalid",
            )
        elicitation = _section(document, "elicitation")
        request = _section(elicitation, "request")
        if elicitation_result.terminal_replay:
            return state.result(
                "accepted",
                "elicitation_binding_validated",
                "elicitation_response_accepted",
                "elicitation_authority_unchanged",
            )
        state.set("runtime.elicitation_revision", request["revision"])
        state.increment("runtime.elicitation_response_count")
        if elicitation_result.disposition != "answered":
            return state.result(
                "accepted",
                "elicitation_binding_validated",
                "elicitation_response_accepted",
                "elicitation_authority_unchanged",
            )
        if elicitation_result.kind == "clarify":
            return state.result(
                "accepted",
                "elicitation_binding_validated",
                "elicitation_request_presented",
                "elicitation_response_accepted",
                "elicitation_authority_unchanged",
            )
        if elicitation_result.kind == "choose":
            return state.result(
                "accepted",
                "elicitation_binding_validated",
                "elicitation_choice_validated",
                "elicitation_response_accepted",
                "elicitation_authority_unchanged",
            )
        if elicitation_result.kind in {"edit", "redline"}:
            return state.result(
                "accepted",
                "elicitation_binding_validated",
                "elicitation_response_accepted",
                "elicitation_authority_unchanged",
            )
        state.increment("runtime.step_up_verified_count")
        return state.result(
            "accepted",
            "elicitation_binding_validated",
            "step_up_result_verified",
            "human_secret_withheld",
            "elicitation_authority_unchanged",
        )
    if operation == "present_ahp_session":
        try:
            ahp = _validate_ahp_binding(
                document,
                control_kind="present",
                message_type="session.state",
            )
        except BehaviorError:
            return state.result(
                "rejected",
                "ahp_binding_rejected",
                "ahp_ui_update_suppressed",
                "asp_authority_retained",
                "action_dispatch_suppressed",
                policy_reason="binding_invalid",
            )
        state.set(
            "runtime.ahp_representation_revision",
            ahp["representation_revision"],
        )
        state.increment("runtime.ahp_presentation_count")
        return state.result(
            "accepted",
            "ahp_binding_validated",
            "asp_tuple_validated",
            "ahp_ui_state_presented",
            "asp_authority_unchanged",
        )
    if operation == "handle_http_capacity_response":
        try:
            retry_after = _validate_http_capacity_binding(document)
        except BehaviorError:
            return state.result(
                "stopped",
                "http_capacity_binding_rejected",
                "capacity_response_rejected",
                "operational_state_retained",
                "retry_suppressed",
            )
        result = _runtime("handle_capacity_response", document, state)
        binding_tokens = [
            "http_capacity_binding_validated",
            "http_status_mapped",
            "http_no_store_validated",
        ]
        if retry_after is not None:
            binding_tokens.append("http_retry_after_validated")
        return BehaviorResult(
            decision=result.decision,
            tokens=tuple(binding_tokens) + result.tokens,
            state_before=result.state_before,
            state_after=result.state_after,
            asp_error=result.asp_error,
            policy_reason=result.policy_reason,
            match_reason=result.match_reason,
        )
    if operation == "handle_capacity_response":
        operational, response, code, retryable = _capacity_response_parts(document)
        if code == "service_unavailable" and execution.get("outcome_state") != "known":
            return state.result(
                "stopped",
                "capacity_response_rejected",
                "outcome_reconciliation_required",
                "retry_suppressed",
                asp_error="outcome_unknown",
            )

        state.set("runtime.local_window_count", 0)
        state.set("runtime.local_in_flight_count", 0)

        if code == "capacity_state_unavailable":
            if retryable is False:
                state.set("runtime.capacity_recovery_pending", False)
                return state.result(
                    "stopped",
                    "capacity_response_validated",
                    "operational_state_retained",
                    "retry_suppressed",
                )
            if operational.get("limiter_state") != "available":
                state.set("runtime.capacity_recovery_pending", True)
                return state.result(
                    "deferred",
                    "capacity_response_validated",
                    "authoritative_capacity_recovery_required",
                    "operational_state_retained",
                    "retry_deferred",
                )
            state.set("runtime.capacity_recovery_pending", False)
            state.increment("runtime.retry_count")
            state.set("runtime.retry_wait_pending", True)
            return state.result(
                "accepted",
                "capacity_response_validated",
                "authoritative_capacity_recovery_confirmed",
                "operational_state_retained",
                "local_backoff_selected",
                "semantic_identity_reused",
                "per_attempt_authentication_applied",
                "retry_scheduled",
            )

        if code == "service_unavailable":
            if retryable is False:
                state.set("runtime.capacity_decision_pending", False)
                return state.result(
                    "stopped",
                    "capacity_response_validated",
                    "retry_suppressed",
                )
            state.set("runtime.capacity_decision_pending", True)
            state.increment("runtime.retry_count")
            state.set("runtime.retry_wait_pending", True)
            return state.result(
                "accepted",
                "capacity_response_validated",
                "capacity_decision_required",
                "local_backoff_selected",
                "semantic_identity_reused",
                "per_attempt_authentication_applied",
                "retry_scheduled",
            )

        if retryable is True:
            limit = response.get("limit")
            if limit is not None and not isinstance(limit, Mapping):
                raise BehaviorError("capacity response limit must be an object")
            retry_after = (
                limit.get("retry_after_seconds") if limit is not None else None
            )
            if retry_after is not None:
                if (
                    isinstance(retry_after, bool)
                    or not isinstance(retry_after, int)
                    or retry_after < 1
                ):
                    raise BehaviorError(
                        "capacity response retry delay must be a positive integer"
                    )
                state.set("runtime.retry_delay_floor_seconds", retry_after)
            state.increment("runtime.retry_count")
            state.set("runtime.retry_wait_pending", True)
            delay_observation = (
                "retry_delay_floor_satisfied"
                if retry_after is not None
                else "local_backoff_selected"
            )
            return state.result(
                "accepted",
                "capacity_response_validated",
                delay_observation,
                "semantic_identity_reused",
                "per_attempt_authentication_applied",
                "retry_scheduled",
            )
        if retryable is False:
            return state.result(
                "stopped",
                "capacity_response_validated",
                "retry_suppressed",
            )
        raise BehaviorError("unreachable capacity response state")
    if operation == "mediate_grant":
        if grant.get("claimed_issuer") != grant.get("issuer"):
            return state.result(
                "rejected",
                "grant_rejected",
                "tuple_checked",
                "mediation_stopped",
                asp_error="integrity_mismatch",
            )
        if runtime.get("returned_grant_width") != "equal":
            return state.result(
                "rejected",
                "grant_rejected",
                "mediation_stopped",
                asp_error="integrity_mismatch",
            )
        if runtime.get("capability_match") != "current":
            return state.result(
                "rejected", "mediation_stopped", match_reason="input_unknown"
            )
        state.increment("runtime.stored_grant_width")
        return state.result("accepted", "tuple_checked")
    if operation == "retry_outcome":
        if execution.get("outcome_state") == "unknown" and execution.get("retry_key") == "new":
            return state.result(
                "stopped", "mediation_stopped", asp_error="outcome_unknown"
            )
        raise BehaviorError("retry_outcome requires an unknown outcome and a new key")
    if operation != "mediate_action":
        raise BehaviorError(f"Runtime Mediator does not support {operation!r}")
    if runtime.get("credential_release") != "none":
        return state.result(
            "rejected",
            "local_denial_recorded",
            "mediation_stopped",
            policy_reason="local_policy_denied",
        )
    if runtime.get("revocation_state") != "current" or grant.get("revocation_state") == "unknown":
        state.set("grant.lifecycle", "inactive")
        return state.result("stopped", "current_state_checked", "mediation_stopped")
    if runtime.get("remote_path") != "known":
        return state.result(
            "stopped",
            "current_state_checked",
            "mediation_stopped",
            match_reason="input_unknown",
        )
    if runtime.get("training_policy") != "exact":
        return state.result(
            "rejected",
            "local_denial_recorded",
            "mediation_stopped",
            asp_error="training_use_denied",
        )
    if operational is not None:
        for name in (
            "runtime.local_window_count",
            "runtime.local_in_flight_count",
        ):
            state.increment(name)
        return state.result(
            "accepted", "operational_limits_checked", "operational_planning_reserved"
        )
    state.increment("action.dispatch_count")
    state.increment("runtime.stored_grant_width")
    return state.result(
        "accepted", "typed_request_forwarded", "action_accepted", "tuple_checked"
    )


def _validate_agent_elicitation_projection(
    document: Mapping[str, Any],
) -> _HumanElicitationResult:
    result = _validate_human_elicitation(document)
    if result.disposition != "answered":
        raise BehaviorError("Agent Adapter cannot project an unanswered elicitation")
    elicitation = _section(document, "elicitation")
    request = _section(elicitation, "request")
    response = _section(elicitation, "response")
    projection = elicitation.get("agent_projection")
    if not isinstance(projection, Mapping) or set(projection) != {
        "origin",
        "exposure",
        "purpose_binding",
        "value",
        "secret_material",
    }:
        raise BehaviorError("agent elicitation projection is not the closed shape")
    if (
        projection.get("origin") != "presenter"
        or projection.get("exposure") != "minimized"
        or projection.get("secret_material") != "absent"
    ):
        raise BehaviorError("agent elicitation projection is not presenter-authored")
    purpose_binding = projection.get("purpose_binding")
    purpose_fields = (
        "session_id",
        "session_generation",
        "grant_id",
        "grant_hash",
        "surface_hash",
        "context_hash",
        "request_hash",
    )
    if (
        not isinstance(purpose_binding, Mapping)
        or set(purpose_binding) != set(purpose_fields)
        or any(
            purpose_binding.get(field) != request.get(field)
            for field in purpose_fields
        )
    ):
        raise BehaviorError("agent elicitation projection is not purpose-bound")
    value = projection.get("value")
    response_body = response.get("response")
    if not isinstance(value, Mapping) or not isinstance(response_body, Mapping):
        raise BehaviorError("agent elicitation projection value is invalid")
    minimized_values: dict[str, Mapping[str, Any]] = {
        "clarify": {
            "kind": "clarify",
            "answer": response_body.get("answer"),
        },
        "choose": {
            "kind": "choose",
            "option_ids": response_body.get("option_ids"),
        },
        "edit": {
            "kind": "edit",
            "candidate": response_body.get("candidate"),
            "candidate_hash": response_body.get("candidate_hash"),
        },
        "redline": {
            "kind": "redline",
            "base_hash": response_body.get("base_hash"),
            "patch": response_body.get("patch"),
            "candidate_hash": response_body.get("candidate_hash"),
        },
    }
    if result.kind == "step_up" or value != minimized_values.get(result.kind):
        raise BehaviorError(
            "agent elicitation projection is not the minimized kind-specific answer"
        )
    return result


def _adapter(operation: str, document: Mapping[str, Any], state: _Transition) -> BehaviorResult:
    execution = _section(document, "execution")
    adapter = _section(document, "adapter")
    receipt = _section(document, "receipt")
    if operation == "project_human_elicitation_answer":
        raw_elicitation = document.get("elicitation")
        raw_projection = (
            raw_elicitation.get("agent_projection")
            if isinstance(raw_elicitation, Mapping)
            else None
        )
        secret_failure = isinstance(raw_projection, Mapping) and (
            raw_projection.get("secret_material") != "absent"
            or raw_projection.get("exposure") == "full_step_up_response"
        )
        try:
            elicitation_result = _validate_agent_elicitation_projection(document)
        except BehaviorError:
            tokens = [
                "elicitation_binding_rejected",
                "elicitation_response_suppressed",
            ]
            if secret_failure:
                tokens.append("human_secret_withheld")
            tokens.append("elicitation_authority_retained")
            if not secret_failure:
                tokens.append("action_dispatch_suppressed")
            return state.result(
                "rejected",
                *tokens,
                asp_error="elicitation_invalid",
            )
        if not elicitation_result.terminal_replay:
            state.increment("adapter.forwarded_count")
        return state.result(
            "accepted",
            "elicitation_binding_validated",
            "elicitation_response_accepted",
            "human_secret_withheld",
            "elicitation_authority_unchanged",
        )
    if operation == "translate_ahp_action":
        try:
            _validate_ahp_binding(
                document,
                control_kind="invoke",
                message_type="action.request",
            )
        except BehaviorError:
            return state.result(
                "rejected",
                "ahp_binding_rejected",
                "adapter_request_rejected",
                "asp_authority_retained",
                "credential_withheld",
                policy_reason="binding_invalid",
            )
        state.increment("adapter.forwarded_count")
        return state.result(
            "accepted",
            "ahp_binding_validated",
            "asp_tuple_validated",
            "ahp_control_translated",
            "typed_request_forwarded",
            "asp_authority_unchanged",
        )
    if operation == "retry_outcome":
        if (
            execution.get("outcome_state") == "unknown"
            and adapter.get("unknown_outcome_handling") == "retry"
        ):
            return state.result(
                "stopped", "adapter_request_rejected", asp_error="outcome_unknown"
            )
        raise BehaviorError("retry_outcome requires an unknown outcome retry")
    if operation != "translate_action":
        raise BehaviorError(f"Agent Adapter does not support {operation!r}")
    if adapter.get("credential_input") != "none":
        return state.result(
            "rejected", "adapter_request_rejected", "local_denial_recorded"
        )
    if adapter.get("action_authority") != "exact":
        return state.result("rejected", "adapter_request_rejected")
    if adapter.get("receipt_evidence") != "observed" or receipt.get("origin") != "observed":
        return state.result(
            "rejected",
            "adapter_request_rejected",
            "receipt_rejected",
            asp_error="integrity_mismatch",
        )
    state.increment("adapter.forwarded_count")
    return state.result("accepted", "typed_request_forwarded")


def evaluate(
    profile_id: str,
    producer_role: str | None,
    operation: str,
    document: Mapping[str, Any],
    initial_state: Sequence[Mapping[str, Any]],
) -> BehaviorResult:
    """Evaluate one closed mock transition without consulting a test oracle."""

    if not isinstance(profile_id, str) or not isinstance(operation, str):
        raise BehaviorError("profile_id and operation must be strings")
    if not isinstance(document, Mapping):
        raise BehaviorError("semantic document must be an object")
    family_for(profile_id, producer_role)
    transition = _Transition(_initial_state(initial_state))
    if profile_id == SP:
        return _surface(operation, document, transition)
    if profile_id == GI:
        return _grant(operation, document, transition)
    if profile_id == AE:
        return _action(operation, document, transition)
    if profile_id == RP:
        return _receipt(operation, document, transition, producer_role)
    if profile_id == RM:
        return _runtime(operation, document, transition)
    if profile_id == AA:
        return _adapter(operation, document, transition)
    raise BehaviorError(f"unsupported mock profile: {profile_id}")
