"""Oracle-independent state machines for the ASP mock participant families.

The evaluator deliberately accepts no vector identifier, input-variant label,
fixture identifier, expected observation, or catalog object. Decisions are a
pure function of the selected role, operation, semantic document, and initial
authoritative state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence


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
SAFE_INTEGER = 2**53 - 1
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
    SP: ("agent-surface/feature/proposal-only", OPERATIONAL_LIMITS),
    GI: (
        "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
    ),
    AE: (
        "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1",
        OPERATIONAL_LIMITS,
        "https://github.com/0al-spec/agent-surface/profiles/runtime-attestation/v1",
        "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1",
    ),
    RP: (),
    RM: (
        "https://github.com/0al-spec/agent-surface/profiles/agent-training-use/v1",
        "https://github.com/0al-spec/agent-surface/profiles/capability-match-result/v1",
        ASP_OVER_AHP,
        OPERATIONAL_LIMITS,
        "https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1",
    ),
    AA: (ASP_OVER_AHP,),
}


class BehaviorError(ValueError):
    """Raised when an invocation is outside the closed mock behavior model."""


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


def _surface(operation: str, document: Mapping[str, Any], state: _Transition) -> BehaviorResult:
    if operation != "publish_manifest":
        raise BehaviorError(f"Surface Publisher does not support {operation!r}")
    surface = _section(document, "surface")
    operational = document.get("operational")
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
        return state.result(
            "accepted", "operational_limits_validated", "manifest_published"
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


def _adapter(operation: str, document: Mapping[str, Any], state: _Transition) -> BehaviorResult:
    execution = _section(document, "execution")
    adapter = _section(document, "adapter")
    receipt = _section(document, "receipt")
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
