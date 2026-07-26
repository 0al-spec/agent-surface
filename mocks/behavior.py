"""Oracle-independent state machines for the ASP mock participant families.

The evaluator deliberately accepts no vector identifier, input-variant label,
fixture identifier, expected observation, or catalog object. Decisions are a
pure function of the selected role, operation, semantic document, and initial
authoritative state.
"""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

import rfc8785
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


SP = "https://github.com/0al-spec/agent-surface/conformance/surface-publisher/v1"
GI = "https://github.com/0al-spec/agent-surface/conformance/grant-issuer/v1"
AE = "https://github.com/0al-spec/agent-surface/conformance/action-executor/v1"
RP = "https://github.com/0al-spec/agent-surface/conformance/receipt-producer/v1"
RM = "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1"
AA = "https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1"
_IMPACT_AUTHORITY_GUARDS = {
    (GI, "issue_mcp_grant"): (
        ("grant",),
        (
            "grant_rejected",
            "mcp_binding_rejected",
            "asp_authority_retained",
            "credential_withheld",
        ),
    ),
    (GI, "issue_grant"): (
        ("grant",),
        (
            "grant_rejected",
            "impact_simulation_binding_rejected",
            "impact_simulation_authority_rejected",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        ),
    ),
    (GI, "revoke_grant"): (
        ("grant",),
        (
            "grant_rejected",
            "impact_simulation_binding_rejected",
            "impact_simulation_authority_rejected",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        ),
    ),
    (RM, "mediate_grant"): (
        ("grant",),
        (
            "grant_rejected",
            "impact_simulation_binding_rejected",
            "impact_simulation_authority_rejected",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        ),
    ),
    (RM, "mediate_action"): (
        ("grant", "execution"),
        (
            "action_rejected",
            "mediation_stopped",
            "impact_simulation_binding_rejected",
            "impact_simulation_authority_rejected",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        ),
    ),
    (RM, "mediate_mcp_action"): (
        ("grant", "execution"),
        (
            "action_rejected",
            "mediation_stopped",
            "impact_simulation_binding_rejected",
            "impact_simulation_authority_rejected",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        ),
    ),
    (AE, "invoke_action"): (
        ("grant", "execution"),
        (
            "action_rejected",
            "impact_simulation_binding_rejected",
            "impact_simulation_authority_rejected",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        ),
    ),
    (AE, "execute_mcp_action"): (
        ("grant", "execution"),
        (
            "action_rejected",
            "impact_simulation_binding_rejected",
            "impact_simulation_authority_rejected",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        ),
    ),
    (AE, "replay_action"): (
        ("grant", "execution"),
        (
            "action_rejected",
            "impact_simulation_binding_rejected",
            "impact_simulation_authority_rejected",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        ),
    ),
    (AA, "translate_action"): (
        ("execution",),
        (
            "adapter_request_rejected",
            "impact_simulation_binding_rejected",
            "impact_simulation_authority_rejected",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        ),
    ),
    (AA, "translate_ahp_action"): (
        ("execution",),
        (
            "adapter_request_rejected",
            "impact_simulation_binding_rejected",
            "impact_simulation_authority_rejected",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        ),
    ),
}
OPERATIONAL_LIMITS = (
    "https://github.com/0al-spec/agent-surface/profiles/operational-limits/v1"
)
ASP_OVER_AHP = (
    "https://github.com/0al-spec/agent-surface/profiles/asp-over-ahp/v1"
)
ASP_OVER_MCP = (
    "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1"
)
ASP_OVER_MCP_EXTENSION = "io.github.zeroal-spec/asp-over-mcp-v1"
ASP_OVER_MCP_PROTOCOL = "2025-11-25"
HUMAN_ELICITATION = (
    "https://github.com/0al-spec/agent-surface/profiles/human-elicitation/v1"
)
RISK_EXPLANATION = "agent-surface/feature/risk-explanation-ui-hints"
IMPACT_SIMULATION = "agent-surface/feature/impact-simulation"
SAFE_INTEGER = 2**53 - 1
RISK_LANGUAGE_PATTERN = re.compile(
    r"^[a-z]{2,8}(?:-[a-z]{4})?(?:-(?:[a-z]{2}|[0-9]{3}))?"
    r"(?:-(?:[a-z0-9]{5,8}|[0-9][a-z0-9]{3}))*$"
)
IMPACT_DIGEST_PATTERN = re.compile(
    r"^sha-256:[A-Za-z0-9_-]{43}(?![\s\S])"
)
IMPACT_EXTENSION_URI_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9+.-]*:"
    r"(?:[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=-]|%[0-9A-Fa-f]{2})+"
)
IMPACT_RISK_ORDER = {
    name: index
    for index, name in enumerate(
        (
            "read",
            "propose",
            "write",
            "public_side_effect",
            "external_side_effect",
            "financial_side_effect",
            "destructive",
            "privileged",
        )
    )
}
IMPACT_INDETERMINATE_REASONS = frozenset(
    {
        "identity_evidence_profile_unsupported",
        "identity_evidence_status_unavailable",
        "runtime_attestation_unavailable",
        "runtime_identity_unavailable",
        "input_unknown",
    }
)
IMPACT_DEFINITIVE_REASONS = frozenset(
    {
        "action_not_requested",
        "approval_unsupported",
        "adapter_unavailable",
        "capability_missing",
        "data_exposure_unsupported",
        "effect_unsupported",
        "execution_stage_unsupported",
        "identity_evidence_invalid",
        "identity_evidence_missing",
        "policy_denied",
        "recovery_unsupported",
        "remote_processing_unsupported",
        "retention_unsupported",
        "risk_denied",
        "runtime_attestation_unsupported",
        "runtime_identity_invalid",
        "sandbox_unsatisfied",
        "schema_unsupported",
        "scope_unavailable",
        "training_use_unsupported",
    }
)
IMPACT_MODES = frozenset(
    {"read", "dry_run", "propose", "reserve", "commit", "compensate", "revert"}
)
IMPACT_STATE_CHANGING_MODES = frozenset(
    {"reserve", "commit", "compensate", "revert"}
)
IMPACT_REASON_SUBJECT_KINDS = frozenset(
    {
        "candidate",
        "runtime",
        "identity_evidence",
        "capability",
        "adapter",
        "action",
        "scope",
        "approval",
        "effect",
        "recovery",
        "exposure",
        "sandbox",
        "policy",
    }
)
IMPACT_EFFECT_VALUES = {
    "operation": frozenset(
        {
            "create",
            "update",
            "delete",
            "publish",
            "send",
            "execute",
            "transfer",
            "grant",
            "revoke",
            "deploy",
            "reserve",
            "renew",
            "release",
        }
    ),
    "visibility": frozenset({"private", "shared", "public"}),
    "boundary": frozenset({"internal", "external"}),
    "reversibility": frozenset(
        {"reversible", "compensatable", "irreversible", "not_applicable"}
    ),
    "domain": frozenset(
        {
            "data",
            "communication",
            "workflow",
            "financial",
            "security",
            "identity",
            "authorization",
            "deployment",
            "configuration",
        }
    ),
}
IMPACT_CANDIDATE_CHECKS = {
    "adapter": ("adapter_unavailable", "definitive", "adapter"),
    "approval": ("approval_unsupported", "definitive", "approval"),
    "capability": ("capability_missing", "definitive", "capability"),
    "data_exposure": ("data_exposure_unsupported", "definitive", "exposure"),
    "effect": ("effect_unsupported", "definitive", "effect"),
    "execution_stage": (
        "execution_stage_unsupported",
        "definitive",
        "action",
    ),
    "identity_evidence_integrity": (
        "identity_evidence_invalid",
        "definitive",
        "identity_evidence",
    ),
    "identity_evidence_presence": (
        "identity_evidence_missing",
        "definitive",
        "identity_evidence",
    ),
    "identity_evidence_profile": (
        "identity_evidence_profile_unsupported",
        "indeterminate",
        "identity_evidence",
    ),
    "identity_evidence_status": (
        "identity_evidence_status_unavailable",
        "indeterminate",
        "identity_evidence",
    ),
    "policy": ("policy_denied", "definitive", "policy"),
    "recovery": ("recovery_unsupported", "definitive", "recovery"),
    "remote_processing": (
        "remote_processing_unsupported",
        "definitive",
        "policy",
    ),
    "required_input": ("input_unknown", "indeterminate", "policy"),
    "retention": ("retention_unsupported", "definitive", "exposure"),
    "risk": ("risk_denied", "definitive", "action"),
    "runtime_attestation_availability": (
        "runtime_attestation_unavailable",
        "indeterminate",
        "runtime",
    ),
    "runtime_attestation_support": (
        "runtime_attestation_unsupported",
        "definitive",
        "runtime",
    ),
    "runtime_identity_availability": (
        "runtime_identity_unavailable",
        "indeterminate",
        "runtime",
    ),
    "runtime_identity_integrity": (
        "runtime_identity_invalid",
        "definitive",
        "runtime",
    ),
    "sandbox": ("sandbox_unsatisfied", "definitive", "sandbox"),
    "schema": ("schema_unsupported", "definitive", "action"),
    "scope": ("scope_unavailable", "definitive", "scope"),
    "training_use": (
        "training_use_unsupported",
        "definitive",
        "policy",
    ),
}
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
        ASP_OVER_MCP,
        OPERATIONAL_LIMITS,
    ),
    GI: (
        "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
        ASP_OVER_MCP,
    ),
    AE: (
        "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1",
        ASP_OVER_MCP,
        HUMAN_ELICITATION,
        OPERATIONAL_LIMITS,
        "https://github.com/0al-spec/agent-surface/profiles/runtime-attestation/v1",
        "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1",
    ),
    RP: (),
    RM: (
        IMPACT_SIMULATION,
        RISK_EXPLANATION,
        "https://github.com/0al-spec/agent-surface/profiles/agent-training-use/v1",
        ASP_OVER_AHP,
        ASP_OVER_MCP,
        "https://github.com/0al-spec/agent-surface/profiles/capability-match-result/v1",
        HUMAN_ELICITATION,
        OPERATIONAL_LIMITS,
        "https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1",
    ),
    AA: (ASP_OVER_AHP, ASP_OVER_MCP, HUMAN_ELICITATION),
}


class BehaviorError(ValueError):
    """Raised when an invocation is outside the closed mock behavior model."""


class _RiskExplanationBindingError(BehaviorError):
    """Raised when otherwise bounded hint data is stale or action-substituted."""


class _EmbeddedImpactAuthorityError(BehaviorError):
    """Raised when a consumed closed authority object embeds a supplemental Result."""


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


def _reject_embedded_impact(
    document: Mapping[str, Any],
    consumed_sections: Sequence[str],
) -> None:
    """Reject supplemental Impact Results embedded in consumed authority objects."""

    for section_name in consumed_sections:
        if section_name not in {"grant", "execution"}:
            raise BehaviorError(
                f"unsupported Impact Simulation carrier {section_name!r}"
            )
        if "impact_simulation" in _section(document, section_name):
            raise _EmbeddedImpactAuthorityError(
                f"{section_name} embeds a supplemental Impact Simulation Result"
            )


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


def _validate_mcp_fresh_ordinary_admission(
    document: Mapping[str, Any], action_id: Any
) -> None:
    """Compose ordinary ASP admission checks for a fresh MCP-carried action."""

    surface = _section(document, "surface")
    grant = _section(document, "grant")
    execution = _section(document, "execution")
    if (
        surface.get("status") != "current"
        or surface.get("references") != "complete"
        or surface.get("candidate_hash") != surface.get("retained_hash")
        or grant.get("status") != "active"
        or grant.get("revocation_state") != "active"
        or grant.get("claimed_issuer") != grant.get("issuer")
        or grant.get("passport_status") != "current"
        or grant.get("companion_closure") != "closed"
        or not set(grant.get("issued_actions", ())).issubset(
            grant.get("requested_actions", ())
        )
        or action_id not in grant.get("issued_actions", ())
        or execution.get("input_hash") != execution.get("recorded_input_hash")
        or execution.get("input_schema_hash")
        != execution.get("recorded_input_schema_hash")
        or execution.get("normalization") != "fixed_point"
        or execution.get("execution_hash")
        != execution.get("recorded_execution_hash")
        or execution.get("approval_hash")
        != execution.get("recorded_approval_hash")
        or execution.get("policy") != "allow"
        or execution.get("runtime_identity")
        != execution.get("bound_runtime_identity")
        or execution.get("sender_credential_audience")
        != execution.get("bound_credential_audience")
        or execution.get("proof_session_binding")
        != execution.get("bound_session_binding")
        or execution.get("attestation") != "current"
    ):
        raise BehaviorError(
            "fresh MCP admission failed ordinary ASP authority checks"
        )


def _validate_mcp_binding(
    document: Mapping[str, Any],
    *,
    phase: str,
) -> Mapping[str, Any]:
    """Validate a closed MCP harness projection without treating MCP as authority."""

    mcp = _section(document, "mcp")
    authority = _section(document, "mcp_authority")
    if phase == "issuance":
        endpoint = authority.get("manifest_binding_endpoint")
        endpoint_parts = urlsplit(str(endpoint))
        grant = _section(document, "grant")
        surface = _section(document, "surface")
        authorization_mode = authority.get("authorization_mode")
        authorization_composition = authority.get("authorization_composition")
        credential_binding = authority.get("credential_binding")
        credential_audience = authority.get("manifest_credential_audience")
        credential_audience_parts = urlsplit(str(credential_audience))
        if (
            credential_audience_parts.scheme != "https"
            or not credential_audience_parts.netloc
        ):
            raise BehaviorError("MCP credential audience is not an absolute HTTPS URI")
        valid_authorization = (
            authorization_mode == "asp_native"
            and authorization_composition == "asp-native"
            and credential_binding in {"dpop", "compatibility_bearer", "mtls"}
            and isinstance(credential_audience, str)
        ) or (
            authorization_mode == "mcp_oauth_dual_use"
            and authorization_composition == "mcp-oauth-dual-use"
            and credential_binding
            in {"compatibility_bearer", "mtls_bound_bearer"}
            and credential_audience == endpoint
        )
        if (
            endpoint_parts.scheme != "https"
            or not endpoint_parts.netloc
            or "?" in str(endpoint)
            or "#" in str(endpoint)
            or endpoint_parts.query
            or endpoint_parts.fragment
            or endpoint_parts.username is not None
            or endpoint_parts.password is not None
            or surface.get("status") != "current"
            or grant.get("passport_status") != "current"
            or grant.get("companion_closure") != "closed"
            or not set(grant.get("issued_actions", ())).issubset(
                grant.get("requested_actions", ())
            )
            or authority.get("requested_locations") != [endpoint]
            or authority.get("issued_locations")
            != authority.get("requested_locations")
            or not valid_authorization
        ):
            raise BehaviorError(
                "pre-channel MCP Grant location or authorization selection is invalid"
            )
        return mcp
    exact_fields = {
        "profile",
        "negotiated_profile",
        "extension_id",
        "negotiated_extension",
        "capability_container",
        "protocol_version",
        "negotiated_protocol_version",
        "protocol_header",
        "initialization_state",
        "bootstrap_manifest_state",
        "bootstrap_binding_declaration",
        "binding_endpoint",
        "grant_location_binding",
        "endpoint_redirect_policy",
        "http_origin_check",
        "post_media_negotiation",
        "listener_authentication",
        "mcp_session_id_source",
        "session_header_use",
        "session_binding",
        "asp_session_id",
        "asp_session_generation",
        "request_trace_id",
        "request_span_id",
        "result_trace_id",
        "result_span_id",
        "listener_state",
        "listener_response",
        "stream_state",
        "stream_recovery",
        "asp_session_state",
        "transport_lifecycle_event",
        "fresh_initialize_authority",
        "session_generation_transition",
        "session_lookup_outcome",
        "interruption_authority",
        "session_binding_persistence",
        "active_mcp_session_cardinality",
        "generation_drain_state",
        "old_record_generation_binding",
        "core_resume_outcome",
        "transport",
        "authentication",
        "authorization_mode",
        "authorization_composition",
        "credential_binding",
        "transport_credential_scheme",
        "canonical_mcp_server_uri",
        "token_audience",
        "bound_token_audience",
        "credential_proof_target_uri",
        "credential_custody",
        "token_forwarding",
        "execution_token_handling",
        "outer_idempotency_header",
        "discovery_kind",
        "manifest_resource_uri",
        "manifest_content_uri",
        "manifest_content_kind",
        "manifest_content_mime",
        "manifest_content_ijson",
        "manifest_content_meta",
        "manifest_uri_binding",
        "manifest_subscription",
        "resource_update_state",
        "binding_view_id",
        "current_binding_view_id",
        "tool_list_state",
        "tools_changed_state",
        "binding_view_tool_set",
        "page_tool_binding_records",
        "authorized_projection_state",
        "authorized_projection_binding",
        "binding_input_schema_hash",
        "current_binding_input_schema_hash",
        "binding_output_schema_hash",
        "current_binding_output_schema_hash",
        "schema_snapshot_state",
        "schema_reference_closure",
        "binding_view_use",
        "completed_record_state",
        "replay_materialization",
        "retained_snapshot_state",
        "rotation_cause",
        "replay_disclosure_authorization",
        "manifest_schema_dialect",
        "mapped_input_schema_dialect",
        "mapped_output_schema_dialect",
        "initialize_display_metadata",
        "tool_display_metadata",
        "resource_link_display_metadata",
        "manifest_action_ids",
        "tool_name",
        "action_id",
        "mapped_action_id",
        "action_mode",
        "mapped_action_mode",
        "grant_id",
        "bound_grant_id",
        "grant_hash",
        "bound_grant_hash",
        "idempotency_key",
        "bound_idempotency_key",
        "idempotency_requirement",
        "surface_version",
        "surface_hash",
        "bound_surface_hash",
        "arguments_input_hash",
        "bound_input_hash",
        "asp_grant_proof",
        "mcp_oauth_use",
        "annotations_use",
        "agent_request_projection",
        "agent_meta_access",
        "agent_credential_access",
        "agent_result_projection",
        "agent_transport_result_access",
        "agent_transport_authority_use",
        "result_channel",
        "result_text_consistency",
        "result_surface_version",
        "result_surface_hash",
        "result_action_id",
        "result_input_hash",
        "result_grant_id",
        "result_grant_hash",
        "result_idempotency_key",
        "result_integrity",
        "result_output_schema",
        "result_is_error_consistency",
        "result_delivery_boundary",
        "error_mapping",
        "binding_error_semantics",
        "action_error_semantics",
        "capacity_error_carrier",
        "transport_status_semantics",
        "task_support",
        "progress_use",
        "progress_token_source",
        "progress_token_echo",
        "progress_payload",
        "progress_stream",
        "cancellation_phase",
        "cancellation_use",
        "retry_behavior",
        "receipt_channel",
        "receipt_requirement",
        "receipt_resource_authentication",
        "receipt_integrity",
        "receipt_link_binding",
        "receipt_persistence",
        "receipt_rematerialization",
        "transport_error_exposure",
    }
    if set(mcp) != exact_fields:
        raise BehaviorError("ASP-over-MCP projection is not the exact closed shape")
    if (
        mcp.get("profile") != ASP_OVER_MCP
        or mcp.get("negotiated_profile") != ASP_OVER_MCP
        or mcp.get("extension_id") != ASP_OVER_MCP_EXTENSION
        or mcp.get("negotiated_extension") != ASP_OVER_MCP_EXTENSION
        or mcp.get("capability_container") != "experimental"
    ):
        raise BehaviorError("ASP-over-MCP experimental capability was not negotiated")
    if any(
        mcp.get(field) != ASP_OVER_MCP_PROTOCOL
        for field in (
            "protocol_version",
            "negotiated_protocol_version",
            "protocol_header",
        )
    ):
        raise BehaviorError("ASP-over-MCP protocol revision was not pinned")
    if mcp.get("initialization_state") != "initialized_notified":
        raise BehaviorError("MCP initialization lifecycle is incomplete")
    if (
        mcp.get("bootstrap_manifest_state") != "verified_before_mcp"
        or mcp.get("bootstrap_binding_declaration") != "exact"
        or mcp.get("binding_endpoint") != mcp.get("canonical_mcp_server_uri")
        or mcp.get("binding_endpoint") != authority.get("manifest_binding_endpoint")
        or mcp.get("manifest_resource_uri") != authority.get("manifest_resource_uri")
        or mcp.get("grant_location_binding") != "verified"
        or mcp.get("endpoint_redirect_policy") != "no_endpoint_changes"
        or mcp.get("http_origin_check") != "allowed_before_asp"
        or mcp.get("post_media_negotiation") != "json_and_event_stream"
        or mcp.get("listener_authentication") != "selected"
        or mcp.get("mcp_session_id_source") != "server_secure"
        or mcp.get("session_header_use") != "all_post_get_delete"
        or mcp.get("session_binding") != "exact"
        or mcp.get("listener_state") != "open_before_subscribe"
        or mcp.get("listener_response") != "text_event_stream"
        or mcp.get("stream_state") != "current"
        or mcp.get("stream_recovery") != "refetch_or_fresh_initialize"
    ):
        raise BehaviorError("MCP bootstrap endpoint or Grant location is unpinned")
    if (
        mcp.get("discovery_kind") != "complete_authorized_snapshot"
        or mcp.get("manifest_subscription") != "active"
        or mcp.get("tool_list_state") != "complete"
        or mcp.get("manifest_uri_binding") != "verified"
        or mcp.get("manifest_content_uri") != mcp.get("manifest_resource_uri")
        or mcp.get("manifest_content_kind") != "text_resource_contents"
        or mcp.get("manifest_content_mime") != "application/json"
        or mcp.get("manifest_content_ijson") != "valid"
        or mcp.get("manifest_content_meta") != "omitted"
        or mcp.get("mapped_input_schema_dialect")
        != mcp.get("manifest_schema_dialect")
        or mcp.get("mapped_output_schema_dialect")
        != mcp.get("manifest_schema_dialect")
        or mcp.get("initialize_display_metadata") != "omitted"
        or mcp.get("tool_display_metadata") != "omitted"
        or mcp.get("resource_link_display_metadata") != "omitted"
        or mcp.get("binding_view_tool_set") != "asp_mapped_only"
        or mcp.get("page_tool_binding_records") != "identical"
        or mcp.get("authorized_projection_binding") != "absent_or_exact"
        or mcp.get("authorized_projection_state") not in {"absent", "exact"}
        or mcp.get("schema_reference_closure") != "self_contained"
    ):
        raise BehaviorError("MCP discovery snapshot is incomplete or stale")
    if (
        mcp.get("manifest_action_ids") != authority.get("manifest_action_ids")
        or mcp.get("authorized_projection_state")
        != authority.get("authorized_projection_state")
        or mcp.get("authorized_projection_binding")
        != authority.get("authorized_projection_binding")
        or mcp.get("surface_version") != authority.get("surface_version")
        or mcp.get("surface_hash") != authority.get("surface_hash")
    ):
        raise BehaviorError("MCP view differs from independent manifest authority")
    current_view = (
        mcp.get("binding_view_use") == "current_admission"
        and mcp.get("resource_update_state") == "current"
        and mcp.get("binding_view_id") == mcp.get("current_binding_view_id")
        and mcp.get("tools_changed_state") == "stable"
        and mcp.get("binding_input_schema_hash")
        == mcp.get("current_binding_input_schema_hash")
        and mcp.get("binding_output_schema_hash")
        == mcp.get("current_binding_output_schema_hash")
        and mcp.get("schema_snapshot_state") == "current"
        and mcp.get("completed_record_state") == "not_applicable"
        and mcp.get("replay_materialization") == "not_applicable"
        and mcp.get("retained_snapshot_state") == "not_applicable"
        and mcp.get("replay_disclosure_authorization") == "not_applicable"
    )
    current_completed_replay = (
        mcp.get("binding_view_use") == "current_completed_replay"
        and phase in {"pre_dispatch", "application_admission", "result"}
        and mcp.get("resource_update_state") == "current"
        and mcp.get("binding_view_id") == mcp.get("current_binding_view_id")
        and mcp.get("tools_changed_state") == "stable"
        and mcp.get("binding_input_schema_hash")
        == mcp.get("current_binding_input_schema_hash")
        and mcp.get("binding_output_schema_hash")
        == mcp.get("current_binding_output_schema_hash")
        and mcp.get("schema_snapshot_state") == "current"
        and mcp.get("completed_record_state") == "exact_authenticated"
        and mcp.get("replay_materialization")
        == "exact_persisted_result_and_receipt"
        and mcp.get("retained_snapshot_state") == "persisted_across_restart"
        and mcp.get("rotation_cause") == "none"
        and mcp.get("replay_disclosure_authorization") == "allowed"
        and mcp.get("idempotency_requirement") == "required"
        and mcp.get("idempotency_key") != "none"
    )
    retained_completed_replay = (
        mcp.get("binding_view_use") == "retained_completed_replay"
        and phase in {"pre_dispatch", "application_admission", "result"}
        and mcp.get("binding_view_id") != mcp.get("current_binding_view_id")
        and mcp.get("tools_changed_state") == "changed_after_snapshot"
        and mcp.get("schema_snapshot_state") == "retained"
        and mcp.get("completed_record_state") == "exact_authenticated"
        and mcp.get("replay_materialization")
        == "exact_persisted_result_and_receipt"
        and mcp.get("retained_snapshot_state") == "persisted_across_restart"
        and mcp.get("replay_disclosure_authorization") == "allowed"
        and mcp.get("idempotency_requirement") == "required"
        and mcp.get("idempotency_key") != "none"
        and (
            (
                mcp.get("rotation_cause") == "manifest"
                and mcp.get("resource_update_state") == "updated"
            )
            or (
                mcp.get("rotation_cause") == "input_schema"
                and mcp.get("binding_input_schema_hash")
                != mcp.get("current_binding_input_schema_hash")
            )
            or (
                mcp.get("rotation_cause") == "output_schema"
                and mcp.get("binding_output_schema_hash")
                != mcp.get("current_binding_output_schema_hash")
            )
            or mcp.get("rotation_cause") == "view_context"
        )
    )
    if not current_view and not current_completed_replay and not retained_completed_replay:
        raise BehaviorError(
            "MCP view is neither current nor an exact retained completed replay"
        )
    active_session = (
        mcp.get("asp_session_state") == "active"
        and mcp.get("session_generation_transition") == "unchanged"
        and mcp.get("session_lookup_outcome") == "bound"
        and mcp.get("interruption_authority") == "not_applicable"
        and mcp.get("generation_drain_state") == "not_applicable"
        and mcp.get("core_resume_outcome") == "not_applicable"
        and (
            (
                mcp.get("transport_lifecycle_event") == "none"
                and mcp.get("fresh_initialize_authority") == "not_applicable"
            )
            or (
                mcp.get("transport_lifecycle_event")
                == "call_or_listener_loss_recovered"
                and mcp.get("fresh_initialize_authority") == "transport_only"
            )
        )
    )
    resumed_session = (
        mcp.get("asp_session_state") == "active"
        and mcp.get("transport_lifecycle_event") == "session_terminated"
        and mcp.get("fresh_initialize_authority") == "no_asp_reactivation"
        and mcp.get("session_generation_transition") == "incremented"
        and mcp.get("session_lookup_outcome") == "bound"
        and mcp.get("interruption_authority") == "server_or_authenticated_owner"
        and mcp.get("generation_drain_state") == "drained"
        and mcp.get("core_resume_outcome") == "accepted"
    )
    nonmutating_session_lookup_404 = (
        phase == "discovery"
        and current_view
        and mcp.get("asp_session_state") == "active"
        and mcp.get("transport_lifecycle_event") == "session_lookup_404_recovered"
        and mcp.get("fresh_initialize_authority") == "transport_only"
        and mcp.get("session_generation_transition") == "unchanged"
        and mcp.get("session_lookup_outcome")
        in {"unknown_404_no_mutation", "auth_mismatch_404_no_mutation"}
        and mcp.get("interruption_authority") == "not_applicable"
        and mcp.get("generation_drain_state") == "not_applicable"
        and mcp.get("core_resume_outcome") == "not_applicable"
    )
    interrupted_closed_path = (
        (current_completed_replay or retained_completed_replay)
        and mcp.get("asp_session_state") == "interrupted"
        and mcp.get("transport_lifecycle_event") == "session_terminated"
        and mcp.get("fresh_initialize_authority") == "no_asp_reactivation"
        and mcp.get("session_generation_transition") == "unchanged"
        and mcp.get("session_lookup_outcome") == "bound"
        and mcp.get("interruption_authority") == "server_or_authenticated_owner"
        and mcp.get("generation_drain_state") == "closed_path_in_progress"
        and mcp.get("core_resume_outcome") == "not_applicable"
    )
    if (
        mcp.get("session_binding_persistence") != "durable"
        or mcp.get("active_mcp_session_cardinality") != "one"
        or mcp.get("old_record_generation_binding") != "original_generation"
    ):
        raise BehaviorError("MCP session-generation binding is not durable")
    if (
        not active_session
        and not resumed_session
        and not nonmutating_session_lookup_404
        and not interrupted_closed_path
    ):
        raise BehaviorError(
            "MCP transport lifecycle did not preserve or explicitly resume the ASP session"
        )
    manifest_uri = urlsplit(str(mcp.get("manifest_resource_uri", "")))
    if not manifest_uri.scheme:
        raise BehaviorError("MCP manifest resource URI is not absolute")
    endpoint_value = str(mcp.get("canonical_mcp_server_uri", ""))
    endpoint = urlsplit(endpoint_value)
    if (
        endpoint.scheme != "https"
        or not endpoint.netloc
        or "?" in endpoint_value
        or "#" in endpoint_value
        or endpoint.query
        or endpoint.fragment
        or endpoint.username is not None
        or endpoint.password is not None
    ):
        raise BehaviorError(
            "MCP canonical endpoint is not credential-free fragmentless HTTPS"
        )
    credential_audience = str(authority.get("manifest_credential_audience", ""))
    credential_audience_parts = urlsplit(credential_audience)
    if (
        credential_audience_parts.scheme != "https"
        or not credential_audience_parts.netloc
    ):
        raise BehaviorError("MCP credential audience is not an absolute HTTPS URI")
    if (
        authority.get("issued_locations") != authority.get("requested_locations")
        or endpoint_value not in authority.get("issued_locations", ())
    ):
        raise BehaviorError("MCP endpoint is outside independent Grant locations")

    surface = _section(document, "surface")
    grant = _section(document, "grant")
    execution = _section(document, "execution")
    action_id = mcp.get("action_id")
    derived_tool = "asp.action." + hashlib.sha256(
        str(action_id).encode("utf-8")
    ).hexdigest()
    if (
        action_id != mcp.get("mapped_action_id")
        or action_id != authority.get("selected_action_id")
        or mcp.get("tool_name") != derived_tool
        or mcp.get("action_mode") != mcp.get("mapped_action_mode")
        or mcp.get("action_mode") != authority.get("selected_action_mode")
        or mcp.get("manifest_schema_dialect") != authority.get("schema_dialect")
        or mcp.get("binding_input_schema_hash") != authority.get("input_schema_hash")
        or mcp.get("binding_output_schema_hash") != authority.get("output_schema_hash")
        or mcp.get("action_mode")
        not in {"read", "dry_run", "propose", "reserve", "commit", "compensate", "revert"}
        or not isinstance(mcp.get("manifest_action_ids"), list)
        or mcp.get("manifest_action_ids")
        != sorted(
            set(mcp.get("manifest_action_ids", ())),
            key=lambda item: item.encode("utf-8"),
        )
        or action_id not in mcp.get("manifest_action_ids", ())
    ):
        raise BehaviorError("MCP tool does not map to one exact manifest ASP action")
    if (
        mcp.get("transport") != "streamable_http"
        or mcp.get("authentication") != "authenticated"
        or mcp.get("token_audience") != mcp.get("bound_token_audience")
        or mcp.get("token_audience") != authority.get("manifest_credential_audience")
        or mcp.get("credential_proof_target_uri")
        != authority.get("credential_proof_target_uri")
        or mcp.get("credential_proof_target_uri")
        != mcp.get("canonical_mcp_server_uri")
        or mcp.get("authorization_mode") != authority.get("authorization_mode")
        or mcp.get("authorization_composition")
        != authority.get("authorization_composition")
        or mcp.get("credential_custody") != "runtime"
        or mcp.get("token_forwarding") != "prohibited"
        or mcp.get("execution_token_handling") != "runtime_injected_meta_only"
        or mcp.get("outer_idempotency_header") != "omitted"
    ):
        raise BehaviorError("MCP carrier released or misbound credential material")
    if mcp.get("authorization_mode") == "asp_native":
        valid_auth = (
            mcp.get("authorization_composition") == "asp-native"
            and mcp.get("mcp_oauth_use") == "not_selected"
            and (
            (mcp.get("credential_binding"), mcp.get("transport_credential_scheme"))
            in {("dpop", "dpop"), ("compatibility_bearer", "bearer"), ("mtls", "mtls")}
            )
        )
    elif mcp.get("authorization_mode") == "mcp_oauth_dual_use":
        valid_auth = (
            mcp.get("authorization_composition") == "mcp-oauth-dual-use"
            and mcp.get("mcp_oauth_use") == "dual_use_verified"
            and mcp.get("transport_credential_scheme") == "bearer"
            and mcp.get("token_audience") == mcp.get("canonical_mcp_server_uri")
            and mcp.get("credential_binding")
            in {"compatibility_bearer", "mtls_bound_bearer"}
        )
    else:
        valid_auth = False
    if not valid_auth:
        raise BehaviorError("MCP authorization composition is invalid")
    if current_view and (
        surface.get("status") != "current"
        or surface.get("references") != "complete"
        or surface.get("candidate_hash") != surface.get("retained_hash")
        or mcp.get("surface_version") != surface.get("version")
        or mcp.get("surface_hash") != surface.get("retained_hash")
    ):
        raise BehaviorError(
            "MCP current view differs from the authoritative surface"
        )
    if phase == "discovery":
        if not current_view:
            raise BehaviorError("MCP discovery or issuance used a retained view")
        return mcp
    if phase == "adapter":
        if not current_view:
            raise BehaviorError("Agent Adapter consumed a retained MCP view")
        if (
            mcp.get("agent_request_projection") != "tool_and_arguments_only"
            or mcp.get("agent_meta_access") != "none"
            or mcp.get("agent_credential_access") != "none"
            or mcp.get("agent_result_projection") != "purpose_minimized_output"
            or mcp.get("agent_transport_result_access") != "none"
            or mcp.get("agent_transport_authority_use") != "none"
        ):
            raise BehaviorError("Agent Adapter crossed the MCP authority boundary")
        return mcp
    if phase not in {"pre_dispatch", "application_admission", "result"}:
        raise BehaviorError(f"unknown MCP validation phase {phase!r}")
    if phase in {"pre_dispatch", "application_admission"} and not (
        current_completed_replay or retained_completed_replay
    ):
        _validate_mcp_fresh_ordinary_admission(document, action_id)
        if mcp.get("binding_input_schema_hash") != execution.get(
            "input_schema_hash"
        ):
            raise BehaviorError(
                "fresh MCP binding schema differs from ordinary ASP admission"
            )
    pair_fields = (
        ("grant_id", "bound_grant_id"),
        ("grant_hash", "bound_grant_hash"),
        ("idempotency_key", "bound_idempotency_key"),
        ("surface_hash", "bound_surface_hash"),
        ("arguments_input_hash", "bound_input_hash"),
    )
    if any(mcp.get(current) != mcp.get(bound) for current, bound in pair_fields):
        raise BehaviorError("MCP action request is detached from the ASP tuple")
    if (
        mcp.get("grant_id") != authority.get("grant_id")
        or mcp.get("grant_hash") != authority.get("grant_hash")
        or mcp.get("idempotency_key") != authority.get("idempotency_key")
        or mcp.get("asp_session_id") != authority.get("asp_session_id")
        or mcp.get("asp_session_generation")
        != authority.get("asp_session_generation")
        or mcp.get("request_trace_id") != authority.get("trace_id")
        or mcp.get("request_span_id") != authority.get("request_span_id")
        or mcp.get("result_trace_id") != authority.get("trace_id")
        or mcp.get("result_span_id") != authority.get("result_span_id")
        or mcp.get("result_span_id") == mcp.get("request_span_id")
    ):
        raise BehaviorError("MCP tuple differs from independent authority")
    if (current_view or current_completed_replay) and (
        mcp.get("surface_version") != surface.get("version")
        or mcp.get("surface_hash") != surface.get("retained_hash")
        or mcp.get("arguments_input_hash") != execution.get("input_hash")
    ):
        raise BehaviorError("MCP action request differs from authoritative ASP state")
    if mcp.get("asp_grant_proof") != "verified" or mcp.get("task_support") != "forbidden":
        raise BehaviorError("MCP request lacks exact ASP proof or enables tasks")
    if phase != "result" and mcp.get("annotations_use") != "omitted":
        raise BehaviorError("MCP Tool annotations cannot carry ASP authority")
    if phase != "result":
        return mcp
    result_pairs = (
        ("result_surface_version", "surface_version"),
        ("result_surface_hash", "surface_hash"),
        ("result_action_id", "action_id"),
        ("result_input_hash", "arguments_input_hash"),
        ("result_grant_id", "grant_id"),
        ("result_grant_hash", "grant_hash"),
        ("result_idempotency_key", "idempotency_key"),
    )
    if any(mcp.get(result) != mcp.get(request) for result, request in result_pairs):
        raise BehaviorError("MCP structured result is detached from the ASP request")
    if (
        mcp.get("result_channel") != "structured_content"
        or mcp.get("result_text_consistency") != "deep_equal"
        or mcp.get("result_integrity") != "valid"
        or mcp.get("result_output_schema") != "valid"
        or mcp.get("result_is_error_consistency") != "matched"
        or mcp.get("result_delivery_boundary") != "runtime_only"
        or mcp.get("error_mapping") != "layered"
        or mcp.get("binding_error_semantics")
        != "closed_pre_effect_non_authoritative"
        or mcp.get("action_error_semantics") != "closed_asp_error"
        or mcp.get("capacity_error_carrier") != "tool_result"
        or mcp.get("transport_status_semantics") != "mcp_http_success"
        or mcp.get("progress_use") != "advisory"
        or mcp.get("progress_token_source") != "runtime"
        or mcp.get("progress_token_echo") != "matched"
        or mcp.get("progress_payload") != "bounded_numeric_only"
        or mcp.get("progress_stream") != "call_post_sse"
        or mcp.get("receipt_link_binding") != "exact_one_to_one"
        or mcp.get("transport_error_exposure")
        != "internal_safe_classification_only"
    ):
        raise BehaviorError("MCP transport semantics weakened ASP authority")
    if mcp.get("cancellation_phase") == "after_dispatch_ambiguous":
        if (
            mcp.get("cancellation_use") != "wait_only"
            or mcp.get("retry_behavior") != "reconcile_same_key"
        ):
            raise BehaviorError("post-dispatch cancellation bypassed reconciliation")
    elif (
        mcp.get("cancellation_phase") != "pre_admission_proven"
        or mcp.get("cancellation_use") != "honored_pre_admission"
        or mcp.get("retry_behavior") != "not_applicable"
    ):
        raise BehaviorError("MCP cancellation state is not fail-closed")
    if mcp.get("idempotency_requirement") == "required":
        if mcp.get("idempotency_key") == "none":
            raise BehaviorError("MCP action lacks required idempotency identity")
    elif mcp.get("idempotency_requirement") != "optional":
        raise BehaviorError("MCP idempotency requirement is invalid")
    if mcp.get("receipt_requirement") == "required":
        if (
            mcp.get("receipt_channel") != "authenticated_resource"
            or mcp.get("receipt_resource_authentication") != "authenticated"
            or mcp.get("receipt_integrity") != "verified"
            or mcp.get("receipt_persistence") != "immutable_before_result"
            or mcp.get("receipt_rematerialization")
            != "exact_after_fresh_session"
        ):
            raise BehaviorError("MCP receipt resource is not authenticated and verified")
    elif mcp.get("receipt_requirement") != "not_required" or (
        mcp.get("receipt_channel") != "not_applicable"
        or mcp.get("receipt_resource_authentication") != "not_applicable"
        or mcp.get("receipt_integrity") != "not_applicable"
        or mcp.get("receipt_persistence") != "not_applicable"
        or mcp.get("receipt_rematerialization") != "not_applicable"
    ):
        raise BehaviorError("MCP receipt handling differs from action policy")
    return mcp


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


def _impact_sorted_unique(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item for item in value)
        or value != sorted(value, key=lambda item: item.encode("utf-8"))
        or len(value) != len(set(value))
    ):
        raise BehaviorError(
            f"impact simulation {label} must be sorted unique strings"
        )
    return value


def _impact_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or IMPACT_DIGEST_PATTERN.fullmatch(value) is None:
        raise BehaviorError(f"impact simulation {label} is not a SHA-256 digest")
    encoded = value.removeprefix("sha-256:")
    try:
        raw = base64.urlsafe_b64decode(encoded + "=")
    except (ValueError, TypeError, binascii.Error) as error:
        raise BehaviorError(
            f"impact simulation {label} is not canonical base64url"
        ) from error
    canonical = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if len(raw) != 32 or encoded != canonical:
        raise BehaviorError(
            f"impact simulation {label} is not canonical base64url"
        )
    return value


def _validate_impact_action(action: Any) -> Mapping[str, Any]:
    if not isinstance(action, Mapping) or set(action) != {
        "action_id",
        "scope",
        "mode",
        "risk",
        "approval",
        "required_companion_action_ids",
        "maximum_effects",
        "data_exposure",
        "recovery",
    }:
        raise BehaviorError("impact simulation action is not the closed shape")
    for name in ("action_id", "scope"):
        if not isinstance(action.get(name), str) or not action[name]:
            raise BehaviorError(f"impact simulation action {name} is invalid")
    if action.get("mode") not in IMPACT_MODES:
        raise BehaviorError("impact simulation action mode is invalid")
    if action.get("risk") not in IMPACT_RISK_ORDER:
        raise BehaviorError("impact simulation action risk mapping is unsupported")
    if action.get("approval") not in {
        "none",
        "runtime",
        "app",
        "user_or_app",
        "runtime_and_app",
    }:
        raise BehaviorError("impact simulation action approval is invalid")
    _impact_sorted_unique(
        action.get("required_companion_action_ids"),
        "required_companion_action_ids",
    )
    effects = action.get("maximum_effects")
    if not isinstance(effects, list):
        raise BehaviorError("impact simulation maximum_effects must be an array")
    for effect in effects:
        if not isinstance(effect, Mapping):
            raise BehaviorError("impact simulation effect must be an object")
        required = {
            "effect_id",
            "operation",
            "resource_type",
            "visibility",
            "boundary",
            "reversibility",
            "domain",
        }
        if not required.issubset(effect) or any(
            key not in required
            and IMPACT_EXTENSION_URI_PATTERN.fullmatch(key) is None
            for key in effect
        ) or (
            not isinstance(effect.get("effect_id"), str)
            or not effect["effect_id"]
            or not isinstance(effect.get("resource_type"), str)
            or not effect["resource_type"]
            or any(
                effect.get(field) not in allowed
                for field, allowed in IMPACT_EFFECT_VALUES.items()
            )
        ):
            raise BehaviorError("impact simulation effect is not the closed shape")
    exposure = action.get("data_exposure")
    if not isinstance(exposure, Mapping) or set(exposure) != {
        "classes",
        "redaction",
        "retention",
    }:
        raise BehaviorError(
            "impact simulation data_exposure is not the action contract"
        )
    _impact_sorted_unique(exposure.get("classes"), "data_exposure.classes")
    redaction = exposure.get("redaction")
    if not isinstance(redaction, Mapping) or redaction.get("mode") not in {
        "none",
        "policy",
    }:
        raise BehaviorError("impact simulation redaction contract is invalid")
    required_redaction_fields = (
        {"mode"}
        if redaction.get("mode") == "none"
        else {"mode", "policy_id", "summary"}
    )
    if set(redaction) != required_redaction_fields or any(
        name != "mode"
        and (not isinstance(redaction[name], str) or not redaction[name])
        for name in redaction
    ):
        raise BehaviorError("impact simulation redaction contract is invalid")
    retention = exposure.get("retention")
    if not isinstance(retention, Mapping) or retention.get("mode") not in {
        "transient",
        "bounded",
    }:
        raise BehaviorError("impact simulation retention contract is invalid")
    required_retention_fields = (
        {"mode", "delete_on_grant_end"}
        if retention.get("mode") == "transient"
        else {"mode", "max_seconds", "delete_on_grant_end"}
    )
    if (
        set(retention) != required_retention_fields
        or not isinstance(retention.get("delete_on_grant_end"), bool)
        or (
            retention.get("mode") == "bounded"
            and (
                isinstance(retention.get("max_seconds"), bool)
                or not isinstance(retention.get("max_seconds"), int)
                or not 1 <= retention["max_seconds"] <= SAFE_INTEGER
            )
        )
    ):
        raise BehaviorError("impact simulation retention contract is invalid")
    recovery = action.get("recovery")
    if not isinstance(recovery, Mapping) or set(recovery) != {
        "available_action_ids",
        "limitations",
    }:
        raise BehaviorError("impact simulation recovery is not the closed shape")
    _impact_sorted_unique(
        recovery.get("available_action_ids"), "recovery.available_action_ids"
    )
    limitations = _impact_sorted_unique(
        recovery.get("limitations"), "recovery.limitations"
    )
    core_limitations = {
        "irreversible",
        "external_outcome_may_be_unknown",
        "recovery_window_limited",
        "no_recovery_action",
    }
    if any(
        limitation not in core_limitations
        and IMPACT_EXTENSION_URI_PATTERN.fullmatch(limitation) is None
        for limitation in limitations
    ):
        raise BehaviorError("impact simulation recovery limitation is invalid")
    state_changing = action["mode"] in IMPACT_STATE_CHANGING_MODES
    if state_changing != bool(effects):
        raise BehaviorError(
            "impact simulation action mode and effect envelope conflict"
        )
    if not state_changing and (
        recovery["available_action_ids"] or recovery["limitations"]
    ):
        raise BehaviorError(
            "impact simulation non-state action projects recovery"
        )
    return action


def _validate_impact_bindings(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "surface",
        "grant_request_hash",
        "delegate",
        "capability_match",
        "agent_inventory_revision",
        "adapter_inventory_revision",
        "local_policy_revision",
        "enterprise_policy_revision",
        "user_preferences_revision",
    }:
        raise BehaviorError("impact simulation bindings are not the closed shape")
    surface = value.get("surface")
    if not isinstance(surface, Mapping) or set(surface) != {
        "issuer",
        "app_id",
        "surface_version",
        "surface_hash",
    }:
        raise BehaviorError("impact simulation surface binding is invalid")
    for name in ("issuer", "app_id", "surface_version"):
        if not isinstance(surface.get(name), str) or not surface[name]:
            raise BehaviorError("impact simulation surface binding is invalid")
    _impact_digest(surface.get("surface_hash"), "surface_hash")
    _impact_digest(value.get("grant_request_hash"), "grant_request_hash")
    delegate = value.get("delegate")
    if not isinstance(delegate, Mapping) or set(delegate) != {
        "runtime_id",
        "agent_id",
        "identity_evidence_hash",
    }:
        raise BehaviorError("impact simulation delegate binding is invalid")
    for name in delegate:
        if not isinstance(delegate[name], str) or not delegate[name]:
            raise BehaviorError("impact simulation delegate binding is invalid")
    _impact_digest(delegate.get("identity_evidence_hash"), "identity_evidence_hash")
    capability_match = value.get("capability_match")
    if capability_match is not None and (
        not isinstance(capability_match, Mapping)
        or set(capability_match) != {"match_id", "evaluated_at", "valid_until"}
        or not isinstance(capability_match.get("match_id"), str)
        or not capability_match["match_id"]
    ):
        raise BehaviorError("impact simulation capability_match binding is invalid")
    for name in (
        "agent_inventory_revision",
        "adapter_inventory_revision",
        "local_policy_revision",
    ):
        if not isinstance(value.get(name), str) or not value[name]:
            raise BehaviorError("impact simulation required revision is invalid")
    for name in ("enterprise_policy_revision", "user_preferences_revision"):
        revision = value.get(name)
        if revision is not None and (
            not isinstance(revision, str) or not revision
        ):
            raise BehaviorError("impact simulation nullable revision is invalid")
    return value


def _impact_candidate_projection(
    candidate_check_facts: Any,
    matched_candidate: Any,
    bindings: Mapping[str, Any],
) -> tuple[str, list[str]]:
    if (
        not isinstance(candidate_check_facts, list)
        or not 24 <= len(candidate_check_facts) <= 64
    ):
        raise BehaviorError("impact simulation candidate check facts are unbounded")
    check_ids: list[str] = []
    reasons: list[Mapping[str, Any]] = []
    reason_classifications: dict[str, str] = {}
    for fact in candidate_check_facts:
        if (
            not isinstance(fact, Mapping)
            or set(fact) != {"check_id", "state", "subject"}
            or not isinstance(fact.get("check_id"), str)
            or not fact["check_id"]
            or fact.get("state") not in {"satisfied", "blocking", "advisory"}
            or not isinstance(fact.get("subject"), Mapping)
            or set(fact["subject"]) != {"kind", "id"}
            or fact["subject"].get("kind") not in IMPACT_REASON_SUBJECT_KINDS
            or not isinstance(fact["subject"].get("id"), str)
            or not fact["subject"]["id"]
        ):
            raise BehaviorError("impact simulation candidate check fact is invalid")
        check_id = fact["check_id"]
        check_ids.append(check_id)
        mapping = IMPACT_CANDIDATE_CHECKS.get(check_id)
        if mapping is None:
            if IMPACT_EXTENSION_URI_PATTERN.fullmatch(check_id) is None:
                raise BehaviorError(
                    "impact simulation candidate check identifier is invalid"
                )
            code = check_id
            classification = "indeterminate"
        else:
            code, classification, required_subject_kind = mapping
            if fact["subject"]["kind"] != required_subject_kind:
                raise BehaviorError(
                    f"impact simulation candidate check {check_id} has the "
                    "wrong subject kind"
                )
        state = fact["state"]
        if state != "satisfied":
            reason_classifications[code] = classification
            reasons.append(
                {
                    "code": code,
                    "severity": state,
                    "subject": fact["subject"],
                }
            )
    if (
        check_ids != sorted(check_ids, key=lambda item: item.encode("utf-8"))
        or len(check_ids) != len(set(check_ids))
        or not set(IMPACT_CANDIDATE_CHECKS).issubset(check_ids)
    ):
        raise BehaviorError(
            "impact simulation candidate checks are not canonical and complete"
        )
    reasons.sort(
        key=lambda reason: (
            0 if reason["severity"] == "blocking" else 1,
            reason["code"].encode("utf-8"),
            reason["subject"]["kind"].encode("utf-8"),
            reason["subject"]["id"].encode("utf-8"),
        )
    )
    definitive_codes = {
        reason["code"]
        for reason in reasons
        if reason["severity"] == "blocking"
        and reason_classifications[reason["code"]] == "definitive"
    }
    indeterminate_codes = {
        reason["code"]
        for reason in reasons
        if reason["severity"] == "blocking"
        and reason_classifications[reason["code"]] == "indeterminate"
    }
    if definitive_codes:
        derived_status = "incompatible"
        outcome = "not_covered"
        projected_codes = definitive_codes
    elif indeterminate_codes:
        derived_status = "indeterminate"
        outcome = "indeterminate"
        projected_codes = indeterminate_codes
    else:
        derived_status = "compatible"
        outcome = "covered"
        projected_codes = set()
    derived_decision = {"status": derived_status, "reasons": reasons}
    capability_match = bindings["capability_match"]
    if capability_match is None:
        if matched_candidate is not None:
            raise BehaviorError(
                "impact simulation retained candidate lacks a match binding"
            )
    else:
        matched_fields = {
            "bindings",
            "agent_id",
            "identity_evidence_hash",
            "grant_request_hash",
            "status",
            "reasons",
        }
        delegate = bindings["delegate"]
        if (
            not isinstance(matched_candidate, Mapping)
            or set(matched_candidate) != matched_fields
            or matched_candidate["bindings"] != bindings
            or matched_candidate["agent_id"] != delegate["agent_id"]
            or matched_candidate["identity_evidence_hash"]
            != delegate["identity_evidence_hash"]
            or matched_candidate["grant_request_hash"]
            != bindings["grant_request_hash"]
            or {
                "status": matched_candidate["status"],
                "reasons": matched_candidate["reasons"],
            }
            != derived_decision
        ):
            raise BehaviorError(
                "impact simulation retained match candidate is not exact"
            )
    return outcome, sorted(projected_codes, key=lambda item: item.encode("utf-8"))


def _derive_impact_actions(
    entries: Any,
    requested_ids: list[str],
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(entries, list) or not entries:
        raise BehaviorError("impact simulation manifest declarations are absent")
    declaration_fields = {
        "action_id",
        "scope",
        "operation_id",
        "mode",
        "risk",
        "approval",
        "required_companion_action_ids",
        "effects",
        "data_exposure",
        "recovery_actions",
        "recovery_targets",
    }
    declarations: dict[str, Mapping[str, Any]] = {}
    for declaration in entries:
        if (
            not isinstance(declaration, Mapping)
            or set(declaration) != declaration_fields
        ):
            raise BehaviorError(
                "impact simulation source is not a manifest declaration"
            )
        for field in ("action_id", "scope", "operation_id"):
            if (
                not isinstance(declaration.get(field), str)
                or not declaration[field]
            ):
                raise BehaviorError(
                    f"impact simulation declaration {field} is invalid"
                )
        action_id = declaration["action_id"]
        if action_id in declarations:
            raise BehaviorError(
                "impact simulation repeats a manifest action declaration"
            )
        if declaration.get("mode") not in IMPACT_MODES:
            raise BehaviorError("impact simulation declaration mode is invalid")
        if declaration.get("risk") not in IMPACT_RISK_ORDER:
            raise BehaviorError(
                "impact simulation declaration risk mapping is unsupported"
            )
        if declaration.get("approval") not in {
            "none",
            "runtime",
            "app",
            "user_or_app",
            "runtime_and_app",
        }:
            raise BehaviorError("impact simulation declaration approval is invalid")
        companions = _impact_sorted_unique(
            declaration.get("required_companion_action_ids"),
            "direct required companion action ids",
        )
        if action_id in companions:
            raise BehaviorError(
                "impact simulation action requires itself as a companion"
            )
        effects = declaration.get("effects")
        relationships = declaration.get("recovery_actions")
        recovery_targets = declaration.get("recovery_targets")
        if (
            not isinstance(effects, list)
            or not isinstance(relationships, list)
            or not isinstance(recovery_targets, list)
        ):
            raise BehaviorError(
                "impact simulation declaration effects and recovery are invalid"
            )
        state_changing = declaration["mode"] in IMPACT_STATE_CHANGING_MODES
        if state_changing != bool(effects):
            raise BehaviorError(
                "impact simulation declaration mode and effects conflict"
            )
        if declaration["mode"] != "commit" and relationships:
            raise BehaviorError(
                "impact simulation non-commit declares outbound recovery"
            )
        if (
            declaration["mode"] in {"compensate", "revert"}
        ) != bool(recovery_targets):
            raise BehaviorError(
                "impact simulation recovery-stage targets are inconsistent"
            )
        effect_ids: list[str] = []
        for effect in effects:
            required_effect_fields = {
                "effect_id",
                "operation",
                "resource_type",
                "visibility",
                "boundary",
                "reversibility",
                "domain",
            }
            if (
                not isinstance(effect, Mapping)
                or not required_effect_fields.issubset(effect)
                or any(
                    field not in required_effect_fields
                    and IMPACT_EXTENSION_URI_PATTERN.fullmatch(field) is None
                    for field in effect
                )
                or not isinstance(effect.get("effect_id"), str)
                or not effect["effect_id"]
                or not isinstance(effect.get("resource_type"), str)
                or not effect["resource_type"]
                or any(
                    effect.get(field) not in allowed
                    for field, allowed in IMPACT_EFFECT_VALUES.items()
                )
            ):
                raise BehaviorError(
                    "impact simulation declaration effect mapping is unsupported"
                )
            effect_ids.append(effect["effect_id"])
        if len(effect_ids) != len(set(effect_ids)):
            raise BehaviorError(
                "impact simulation declaration repeats an effect identifier"
            )
        required_risk = "write" if state_changing else "read"
        for effect in effects:
            floors = [required_risk]
            if effect["visibility"] == "public":
                floors.append("public_side_effect")
            if effect["boundary"] == "external":
                floors.append("external_side_effect")
            if effect["domain"] == "financial":
                floors.append("financial_side_effect")
            if effect["domain"] in {
                "security",
                "identity",
                "authorization",
            }:
                floors.append("privileged")
            if (
                effect["operation"] in {"delete", "revoke"}
                and effect["reversibility"] == "irreversible"
            ):
                floors.append("destructive")
            required_risk = max(
                floors, key=lambda risk: IMPACT_RISK_ORDER[risk]
            )
        if (
            IMPACT_RISK_ORDER[declaration["risk"]]
            < IMPACT_RISK_ORDER[required_risk]
        ):
            raise BehaviorError(
                "impact simulation declaration risk is below its effect floor"
            )
        relationship_keys: set[tuple[Any, ...]] = set()
        for relationship in relationships:
            if (
                not isinstance(relationship, Mapping)
                or set(relationship)
                != {
                    "mode",
                    "action_id",
                    "effect_ids",
                    "recovery_window_seconds",
                }
                or relationship.get("mode") not in {"compensate", "revert"}
                or not isinstance(relationship.get("action_id"), str)
                or not relationship["action_id"]
                or relationship["action_id"] == action_id
                or isinstance(relationship.get("recovery_window_seconds"), bool)
                or not isinstance(
                    relationship.get("recovery_window_seconds"), int
                )
                or not 1
                <= relationship["recovery_window_seconds"]
                <= SAFE_INTEGER
            ):
                raise BehaviorError(
                    "impact simulation recovery relationship is invalid"
                )
            relationship_effects = _impact_sorted_unique(
                relationship.get("effect_ids"),
                "recovery relationship effect ids",
            )
            if not relationship_effects or not set(
                relationship_effects
            ).issubset(effect_ids):
                raise BehaviorError(
                    "impact simulation recovery relationship names unknown effects"
                )
            relationship_key = (
                relationship["mode"],
                relationship["action_id"],
                tuple(relationship_effects),
                relationship["recovery_window_seconds"],
            )
            if relationship_key in relationship_keys:
                raise BehaviorError(
                    "impact simulation repeats a recovery relationship"
                )
            relationship_keys.add(relationship_key)
        recovery_target_keys: set[tuple[Any, ...]] = set()
        for target in recovery_targets:
            if (
                not isinstance(target, Mapping)
                or set(target)
                != {
                    "action_id",
                    "effect_ids",
                    "recovery_window_seconds",
                }
                or not isinstance(target.get("action_id"), str)
                or not target["action_id"]
                or target["action_id"] == action_id
                or isinstance(target.get("recovery_window_seconds"), bool)
                or not isinstance(target.get("recovery_window_seconds"), int)
                or not 1
                <= target["recovery_window_seconds"]
                <= SAFE_INTEGER
            ):
                raise BehaviorError(
                    "impact simulation recovery target is invalid"
                )
            target_effect_ids = _impact_sorted_unique(
                target.get("effect_ids"), "recovery target effect ids"
            )
            if not target_effect_ids:
                raise BehaviorError(
                    "impact simulation recovery target has no effects"
                )
            target_key = (
                target["action_id"],
                tuple(target_effect_ids),
                target["recovery_window_seconds"],
            )
            if target_key in recovery_target_keys:
                raise BehaviorError(
                    "impact simulation repeats a recovery target"
                )
            recovery_target_keys.add(target_key)
        declarations[action_id] = declaration

    for action_id, declaration in declarations.items():
        if any(
            companion not in declarations
            or declarations[companion]["operation_id"]
            != declaration["operation_id"]
            for companion in declaration["required_companion_action_ids"]
        ):
            raise BehaviorError(
                "impact simulation declaration has an invalid companion"
            )
        effects_by_id = {
            effect["effect_id"]: effect for effect in declaration["effects"]
        }
        covered_reversible: set[str] = set()
        covered_compensatable: set[str] = set()
        for relationship in declaration["recovery_actions"]:
            target = declarations.get(relationship["action_id"])
            reciprocal = {
                "action_id": action_id,
                "effect_ids": relationship["effect_ids"],
                "recovery_window_seconds": relationship[
                    "recovery_window_seconds"
                ],
            }
            if (
                target is None
                or target["mode"] != relationship["mode"]
                or target["operation_id"] != declaration["operation_id"]
                or reciprocal not in target["recovery_targets"]
            ):
                raise BehaviorError(
                    "impact simulation recovery target is inconsistent"
                )
            for effect_id in relationship["effect_ids"]:
                effect = effects_by_id[effect_id]
                if relationship["mode"] == "revert":
                    if (
                        effect["reversibility"] != "reversible"
                        or effect["boundary"] != "internal"
                    ):
                        raise BehaviorError(
                            "impact simulation revert relationship is invalid"
                        )
                    covered_reversible.add(effect_id)
                else:
                    if effect["reversibility"] != "compensatable":
                        raise BehaviorError(
                            "impact simulation compensation relationship is invalid"
                        )
                    covered_compensatable.add(effect_id)
        if declaration["mode"] == "commit":
            reversible = {
                effect_id
                for effect_id, effect in effects_by_id.items()
                if effect["reversibility"] == "reversible"
            }
            compensatable = {
                effect_id
                for effect_id, effect in effects_by_id.items()
                if effect["reversibility"] == "compensatable"
            }
            if (
                reversible != covered_reversible
                or compensatable != covered_compensatable
            ):
                raise BehaviorError(
                    "impact simulation commit recovery coverage is inconsistent"
                )
        for target in declaration["recovery_targets"]:
            source = declarations.get(target["action_id"])
            outbound = (
                {
                    "mode": declaration["mode"],
                    "action_id": action_id,
                    "effect_ids": target["effect_ids"],
                    "recovery_window_seconds": target[
                        "recovery_window_seconds"
                    ],
                }
                if source is not None
                else None
            )
            if (
                source is None
                or source["mode"] != "commit"
                or source["operation_id"] != declaration["operation_id"]
                or outbound not in source["recovery_actions"]
            ):
                raise BehaviorError(
                    "impact simulation recovery target lacks a reciprocal"
                )

    closure_cache: dict[str, list[str]] = {}

    def companion_closure(action_id: str) -> list[str]:
        if action_id in closure_cache:
            return closure_cache[action_id]
        closure: set[str] = set()
        pending = list(declarations[action_id]["required_companion_action_ids"])
        while pending:
            companion = pending.pop()
            if companion == action_id or companion in closure:
                continue
            closure.add(companion)
            pending.extend(
                declarations[companion]["required_companion_action_ids"]
            )
        ordered = sorted(closure, key=lambda item: item.encode("utf-8"))
        closure_cache[action_id] = ordered
        return ordered

    requested_set = set(requested_ids)
    derived: dict[str, Mapping[str, Any]] = {}
    for action_id, declaration in declarations.items():
        effects = declaration["effects"]
        relationships = declaration["recovery_actions"]
        limitations: set[str] = set()
        if any(
            effect["reversibility"] == "irreversible" for effect in effects
        ):
            limitations.add("irreversible")
        if any(effect["boundary"] == "external" for effect in effects):
            limitations.add("external_outcome_may_be_unknown")
        if relationships:
            limitations.add("recovery_window_limited")
        elif declaration["mode"] == "commit" and effects:
            limitations.add("no_recovery_action")
        action: Mapping[str, Any] = {
            "action_id": action_id,
            "scope": declaration["scope"],
            "mode": declaration["mode"],
            "risk": declaration["risk"],
            "approval": declaration["approval"],
            "required_companion_action_ids": companion_closure(action_id),
            "maximum_effects": effects,
            "data_exposure": declaration["data_exposure"],
            "recovery": {
                "available_action_ids": sorted(
                    {
                        relationship["action_id"]
                        for relationship in relationships
                        if relationship["action_id"] in requested_set
                    },
                    key=lambda item: item.encode("utf-8"),
                ),
                "limitations": sorted(
                    limitations, key=lambda item: item.encode("utf-8")
                ),
            },
        }
        _validate_impact_action(action)
        derived[action_id] = action
    return derived


def _validate_impact_simulation(document: Mapping[str, Any]) -> None:
    _reject_embedded_impact(document, ("grant", "execution"))
    projection = _section(document, "impact_simulation")
    if set(projection) != {
        "phase",
        "evaluation_time",
        "authority_use",
        "current_binding_facts",
        "source",
        "result",
    }:
        raise BehaviorError("impact simulation fixture projection is not closed")
    if (
        projection.get("phase") != "pre_issuance"
        or projection.get("authority_use") != "none"
    ):
        raise BehaviorError("impact simulation is not pre-issuance and local")
    surface = _section(document, "surface")
    grant = _section(document, "grant")
    if (
        surface.get("status") != "current"
        or surface.get("references") != "complete"
    ):
        raise BehaviorError("impact simulation retained surface is stale")
    source = projection.get("source")
    result = projection.get("result")
    if not isinstance(source, Mapping) or set(source) != {
        "bindings",
        "requested_action_ids",
        "requested_scope_ids",
        "candidate_check_facts",
        "matched_candidate",
        "actions",
        "freshness_deadlines",
    }:
        raise BehaviorError("impact simulation authoritative source is not closed")
    if not isinstance(result, Mapping) or set(result) != {
        "feature",
        "evaluated_at",
        "valid_until",
        "bindings",
        "coverage",
        "examples",
    }:
        raise BehaviorError("impact simulation result is not the closed shape")
    if result.get("feature") != IMPACT_SIMULATION:
        raise BehaviorError("impact simulation feature identifier is invalid")
    source_bindings = _validate_impact_bindings(source.get("bindings"))
    result_bindings = _validate_impact_bindings(result.get("bindings"))
    if result_bindings != source_bindings:
        raise BehaviorError("impact simulation bindings are not authoritative")
    current_binding_facts = projection.get("current_binding_facts")
    if (
        not isinstance(current_binding_facts, Mapping)
        or current_binding_facts != result_bindings
    ):
        raise BehaviorError(
            "impact simulation bindings differ from runner-owned current facts"
        )
    result_surface = result_bindings["surface"]
    if (
        result_surface["surface_version"] != surface.get("version")
        or result_surface["surface_hash"] != surface.get("retained_hash")
    ):
        raise BehaviorError("impact simulation is detached from the retained surface")
    requested_ids = _impact_sorted_unique(
        source.get("requested_action_ids"), "requested_action_ids"
    )
    requested_scope_ids = set(
        _impact_sorted_unique(
            source.get("requested_scope_ids"), "requested_scope_ids"
        )
    )
    if not 1 <= len(requested_ids) <= 64:
        raise BehaviorError("impact simulation requested coverage is out of bounds")
    if (
        requested_ids != grant.get("requested_actions")
        or source.get("requested_scope_ids") != grant.get("requested_scopes")
        or grant.get("status") != "proposed"
        or grant.get("issued_actions") != []
        or grant.get("companion_closure") != "closed"
    ):
        raise BehaviorError("impact simulation is detached from the Grant request")

    evaluated_at = _utc_timestamp(result.get("evaluated_at"), "impact evaluated_at")
    valid_until = _utc_timestamp(result.get("valid_until"), "impact valid_until")
    evaluation_time = _utc_timestamp(
        projection.get("evaluation_time"), "impact evaluation_time"
    )
    if (
        not evaluated_at < valid_until
        or evaluation_time < evaluated_at
        or evaluation_time >= valid_until
    ):
        raise BehaviorError("impact simulation freshness interval is invalid")
    freshness_deadlines = source.get("freshness_deadlines")
    deadline_fields = {
        "identity_evidence_status",
        "capability_match",
        "agent_inventory",
        "adapter_inventory",
        "local_policy",
        "enterprise_policy",
        "user_preferences",
        "runtime_identity",
        "runtime_attestation",
        "local_maximum",
    }
    if not isinstance(freshness_deadlines, Mapping) or set(
        freshness_deadlines
    ) != deadline_fields:
        raise BehaviorError("impact simulation freshness deadlines are not closed")
    parsed_deadlines: dict[str, datetime | None] = {}
    for name, deadline in freshness_deadlines.items():
        if deadline is None:
            parsed_deadlines[name] = None
            continue
        parsed = _utc_timestamp(deadline, f"impact {name} freshness deadline")
        if parsed <= evaluated_at:
            raise BehaviorError(
                f"impact simulation freshness deadline {name} is not future"
            )
        parsed_deadlines[name] = parsed
    for required_deadline in {
        "identity_evidence_status",
        "agent_inventory",
        "adapter_inventory",
        "local_policy",
        "local_maximum",
    }:
        if parsed_deadlines[required_deadline] is None:
            raise BehaviorError(
                f"impact simulation required deadline {required_deadline} is absent"
            )
    if valid_until > min(
        deadline
        for deadline in parsed_deadlines.values()
        if deadline is not None
    ):
        raise BehaviorError(
            "impact simulation valid_until exceeds an authoritative deadline"
        )
    capability_match = result_bindings["capability_match"]
    if capability_match is None:
        if freshness_deadlines["capability_match"] is not None:
            raise BehaviorError(
                "impact simulation capability deadline lacks a match"
            )
    else:
        if (
            freshness_deadlines["capability_match"]
            != capability_match["valid_until"]
        ):
            raise BehaviorError(
                "impact simulation capability deadline differs from binding"
            )
        match_evaluated = _utc_timestamp(
            capability_match["evaluated_at"], "impact match evaluated_at"
        )
        match_valid = _utc_timestamp(
            capability_match["valid_until"], "impact match valid_until"
        )
        if (
            not match_evaluated < match_valid
            or match_evaluated > evaluated_at
            or evaluation_time < match_evaluated
            or evaluation_time >= match_valid
            or valid_until > match_valid
        ):
            raise BehaviorError("impact simulation capability match is stale")
    for revision_name, deadline_name in (
        ("enterprise_policy_revision", "enterprise_policy"),
        ("user_preferences_revision", "user_preferences"),
    ):
        if (result_bindings[revision_name] is None) != (
            freshness_deadlines[deadline_name] is None
        ):
            raise BehaviorError(
                f"impact simulation {deadline_name} deadline differs from revision"
            )

    authoritative = _derive_impact_actions(source.get("actions"), requested_ids)
    requested_outcome, requested_reasons = _impact_candidate_projection(
        source.get("candidate_check_facts"),
        source.get("matched_candidate"),
        result_bindings,
    )
    check_facts_by_id = {
        fact["check_id"]: fact for fact in source["candidate_check_facts"]
    }
    for availability_check, deadline_name in (
        ("runtime_identity_availability", "runtime_identity"),
        ("runtime_attestation_availability", "runtime_attestation"),
    ):
        unavailable = (
            check_facts_by_id[availability_check]["state"] == "blocking"
        )
        if unavailable != (freshness_deadlines[deadline_name] is None):
            raise BehaviorError(
                f"impact simulation {deadline_name} deadline differs from "
                "availability"
            )
    if any(action_id not in authoritative for action_id in requested_ids):
        raise BehaviorError("impact simulation requested action is unresolved")
    for action_id in requested_ids:
        action = authoritative[action_id]
        if (
            action["scope"] not in requested_scope_ids
            or not set(action["required_companion_action_ids"]).issubset(
                requested_ids
            )
        ):
            raise BehaviorError(
                "impact simulation request has an unavailable scope or "
                "unclosed companion set"
            )
    requested_set = set(requested_ids)
    unrequested_ids = [
        action_id for action_id in authoritative if action_id not in requested_set
    ]
    selected_unrequested = sorted(
        unrequested_ids,
        key=lambda action_id: (
            -IMPACT_RISK_ORDER[authoritative[action_id]["risk"]],
            action_id.encode("utf-8"),
        ),
    )[:8]
    selected_action_ids = requested_ids + selected_unrequested
    examples = result.get("examples")
    if (
        not isinstance(examples, list)
        or not 1 <= len(examples) <= 72
        or any(
            not isinstance(example, Mapping)
            or set(example)
            != {"request_relation", "outcome", "reasons", "action"}
            for example in examples
        )
    ):
        raise BehaviorError("impact simulation examples are not closed")
    actual_ids = [example["action"].get("action_id") for example in examples]
    if actual_ids != selected_action_ids:
        raise BehaviorError("impact simulation selection order is not deterministic")
    coverage = result.get("coverage")
    if not isinstance(coverage, Mapping) or set(coverage) != {
        "requested",
        "unrequested",
        "selection_algorithm",
    }:
        raise BehaviorError("impact simulation coverage is not closed")
    if (
        coverage.get("selection_algorithm")
        != "highest-risk-then-action-id-v1"
        or coverage.get("requested")
        != {
            "total": len(requested_ids),
            "included": len(requested_ids),
            "complete": True,
        }
        or coverage.get("unrequested")
        != {
            "total": len(unrequested_ids),
            "included": len(selected_unrequested),
            "truncated": len(unrequested_ids) > len(selected_unrequested),
        }
    ):
        raise BehaviorError("impact simulation coverage metadata is not exact")
    for example, action_id in zip(examples, selected_action_ids, strict=True):
        action = _validate_impact_action(example["action"])
        relation = "requested" if action_id in requested_set else "unrequested"
        reasons = _impact_sorted_unique(example.get("reasons"), "example reasons")
        derived_outcome = (
            requested_outcome if relation == "requested" else "not_covered"
        )
        derived_reasons = (
            requested_reasons
            if relation == "requested"
            else ["action_not_requested"]
        )
        if (
            action != authoritative[action_id]
            or example.get("request_relation") != relation
            or example.get("outcome") != derived_outcome
            or reasons != derived_reasons
        ):
            raise BehaviorError(
                "impact simulation example is not independently derived"
            )
        outcome = example.get("outcome")
        if relation == "unrequested" and (
            outcome != "not_covered" or reasons != ["action_not_requested"]
        ):
            raise BehaviorError(
                "impact simulation unrequested reasons are not the exact singleton"
            )
        if outcome == "covered" and reasons:
            raise BehaviorError("impact simulation covered action has a reason")


def _surface(operation: str, document: Mapping[str, Any], state: _Transition) -> BehaviorResult:
    if operation == "publish_mcp_surface":
        try:
            _validate_mcp_binding(
                document,
                phase="discovery",
            )
        except BehaviorError:
            return state.result(
                "rejected",
                "mcp_binding_rejected",
                "mcp_discovery_suppressed",
                "asp_authority_retained",
                "action_dispatch_suppressed",
                asp_error="surface_incompatible",
            )
        state.increment("manifest.accepted_count")
        state.increment("surface.version_binding_count")
        return state.result(
            "accepted",
            "mcp_binding_validated",
            "mcp_surface_published",
            "mcp_tools_published",
            "asp_authority_unchanged",
        )
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
    if operation == "issue_mcp_grant":
        try:
            _validate_mcp_binding(document, phase="issuance")
        except BehaviorError:
            return state.result(
                "rejected",
                "grant_rejected",
                "mcp_binding_rejected",
                "asp_authority_retained",
                "credential_withheld",
                policy_reason="binding_invalid",
            )
        if (
            surface.get("status") != "current"
            or grant.get("passport_status") != "current"
            or grant.get("companion_closure") != "closed"
            or not set(grant.get("issued_actions", ())).issubset(
                grant.get("requested_actions", ())
            )
        ):
            return state.result(
                "rejected",
                "grant_rejected",
                "mcp_binding_rejected",
                "asp_authority_retained",
                "credential_withheld",
                policy_reason="binding_invalid",
            )
        state.increment("grant.issued_count")
        state.increment("credential.issued_count")
        return state.result(
            "accepted",
            "mcp_binding_validated",
            "grant_location_bound",
            "grant_issued",
            "tuple_checked",
            "credential_withheld",
        )
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
    if operation == "execute_mcp_action":
        try:
            mcp = _validate_mcp_binding(document, phase="application_admission")
        except BehaviorError:
            return state.result(
                "rejected",
                "mcp_binding_rejected",
                "action_rejected",
                "mcp_result_suppressed",
                "asp_authority_retained",
                "credential_withheld",
                policy_reason="binding_invalid",
            )
        if mcp.get("binding_view_use") == "retained_completed_replay":
            try:
                _validate_mcp_binding(document, phase="result")
            except BehaviorError:
                return state.result(
                    "stopped",
                    "mcp_binding_rejected",
                    "mcp_result_suppressed",
                    "outcome_reconciliation_required",
                    "asp_authority_retained",
                    "credential_withheld",
                    "retry_suppressed",
                    policy_reason="binding_invalid",
                )
            return state.result(
                "accepted",
                "mcp_binding_validated",
                "mcp_structured_result_emitted",
                "receipt_verified",
                "asp_authority_unchanged",
            )
        for name in (
            "action.dispatch_count",
            "action.effect_count",
            "idempotency.record_count",
            "budget.application_charge",
            "receipt.application_count",
        ):
            state.increment(name)
        try:
            _validate_mcp_binding(document, phase="result")
        except BehaviorError:
            return state.result(
                "stopped",
                "mcp_binding_rejected",
                "action_accepted",
                "application_receipt_emitted",
                "mcp_result_suppressed",
                "outcome_reconciliation_required",
                "asp_authority_retained",
                "credential_withheld",
                "retry_suppressed",
                policy_reason="binding_invalid",
            )
        return state.result(
            "accepted",
            "mcp_binding_validated",
            "asp_tuple_validated",
            "action_accepted",
            "application_receipt_emitted",
            "mcp_structured_result_emitted",
        )
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
    if operation == "mediate_mcp_action":
        try:
            mcp = _validate_mcp_binding(document, phase="pre_dispatch")
        except BehaviorError:
            return state.result(
                "rejected",
                "mcp_binding_rejected",
                "mediation_stopped",
                "mcp_result_suppressed",
                "asp_authority_retained",
                "credential_withheld",
                "retry_suppressed",
                policy_reason="binding_invalid",
            )
        if mcp.get("binding_view_use") == "retained_completed_replay":
            try:
                _validate_mcp_binding(document, phase="result")
            except BehaviorError:
                return state.result(
                    "stopped",
                    "mcp_binding_rejected",
                    "mcp_result_suppressed",
                    "outcome_reconciliation_required",
                    "asp_authority_retained",
                    "credential_withheld",
                    "retry_suppressed",
                    policy_reason="binding_invalid",
                )
            return state.result(
                "accepted",
                "mcp_binding_validated",
                "mcp_structured_result_validated",
                "receipt_verified",
                "credential_withheld",
                "asp_authority_unchanged",
            )
        state.increment("action.dispatch_count")
        state.increment("runtime.stored_grant_width")
        try:
            _validate_mcp_binding(document, phase="result")
        except BehaviorError:
            return state.result(
                "stopped",
                "mcp_binding_rejected",
                "mediation_stopped",
                "typed_request_forwarded",
                "mcp_result_suppressed",
                "outcome_reconciliation_required",
                "asp_authority_retained",
                "credential_withheld",
                "retry_suppressed",
                policy_reason="binding_invalid",
            )
        return state.result(
            "accepted",
            "mcp_binding_validated",
            "asp_tuple_validated",
            "typed_request_forwarded",
            "mcp_structured_result_validated",
            "credential_withheld",
            "cancellation_advisory",
            "asp_authority_unchanged",
        )
    if operation == "simulate_impact":
        try:
            _validate_impact_simulation(document)
        except BehaviorError:
            return state.result(
                "stopped",
                "impact_simulation_binding_rejected",
                "impact_simulation_suppressed",
                "consent_preview_retained",
                "impact_simulation_authority_unchanged",
                "application_dry_run_suppressed",
                "impact_simulation_agent_projection_suppressed",
            )
        state.increment("runtime.impact_simulation_presentation_count")
        return state.result(
            "accepted",
            "impact_simulation_validated",
            "impact_simulation_presented",
            "consent_preview_retained",
            "impact_simulation_authority_unchanged",
            "application_dry_run_suppressed",
            "impact_simulation_agent_projection_suppressed",
        )
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
    if operation == "adapt_mcp_action":
        try:
            _validate_mcp_binding(document, phase="adapter")
        except BehaviorError:
            return state.result(
                "rejected",
                "mcp_binding_rejected",
                "adapter_request_rejected",
                "mcp_result_suppressed",
                "asp_authority_retained",
                "credential_withheld",
                policy_reason="binding_invalid",
            )
        state.increment("adapter.forwarded_count")
        return state.result(
            "accepted",
            "mcp_binding_validated",
            "typed_request_forwarded",
            "credential_withheld",
            "asp_authority_unchanged",
        )
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
    impact_guard = _IMPACT_AUTHORITY_GUARDS.get((profile_id, operation))
    if impact_guard is not None:
        consumed_sections, rejection_tokens = impact_guard
        try:
            _reject_embedded_impact(document, consumed_sections)
        except _EmbeddedImpactAuthorityError:
            return transition.result("rejected", *rejection_tokens)
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
