"""Deterministic consent policy for one synthetic draft, not a human simulator.

No credentials, HTTP access, model or SpecSpace imports. The driver owns the
operator bridge; app/runtime enforcement remains independent of this policy.
"""
from runtime import READ, PROPOSE, canonical, digest, object_hash

DRAFT_ID = "adoption-draft"
DRAFT_TEXT = "Add a private idea draft panel. Saving a draft must not submit or execute it."


def decision(stage, reason=None):
    # Safe report metadata only: never copy inputs, identity or credentials.
    return {"actor": "mock_user", "stage": stage, "accept": reason is None,
            "reason": reason or "matches_fixture_policy"}


class MockUser:
    """Allow exactly this fixture's scope and text; deny everything else."""

    def grant(self, consent, request, surface_hash):
        try:
            if (consent["workspace_id"] != "asp-draft-demo"
                    or consent["runtime_id"] != "local-runtime"
                    or sorted(consent["actions"]) != sorted([READ, PROPOSE])
                    or consent["credential_profile"] != "compatibility_bearer"
                    or consent["identity"]["agent_id"] != "local-agent"
                    or consent["identity"]["state"] != "active"):
                return decision("grant", "grant_scope_mismatch")
            ttl = request["expires_in"]
            if (type(ttl) is not int or not 1 <= ttl <= 300
                    or type(consent["max_seconds"]) is not int or ttl > consent["max_seconds"]):
                return decision("grant", "grant_lifetime_denied")
            expected = {"surface_hash": surface_hash,
                        "identity_evidence_hash": consent["identity"]["identity_evidence_hash"],
                        "workspace_id": "asp-draft-demo", "runtime_id": "local-runtime",
                        "agent_id": "local-agent", "expires_in": ttl, "accept": True}
            if consent["surface_hash"] != surface_hash or canonical(request) != canonical(expected):
                return decision("grant", "grant_binding_mismatch")
        except (KeyError, TypeError, ValueError):
            return decision("grant", "malformed_view")
        return decision("grant")

    def approve(self, prepared, expected):
        try:
            if (set(prepared) != {"approval_id", "request", "approved"}
                    or prepared["approved"] is not False
                    or set(expected) != {"type", "payload"}
                    or expected["type"] != "action.request"
                    or canonical(prepared["request"]) != canonical(expected["payload"])):
                return decision("draft", "approval_binding_mismatch")
            p = prepared["request"]
            if (set(p) != {"session_id", "session_generation", "trace_id", "span_id", "grant_id",
                          "grant_hash", "surface_hash", "action_id", "input", "input_hash",
                          "execution", "idempotency_key"}
                    or p["action_id"] != PROPOSE
                    or set(p["execution"]) != {"mode", "execution_id"}
                    or p["execution"]["mode"] != "propose"):
                return decision("draft", "draft_action_denied")
            value = p["input"]
            if (set(value) != {"workspace_id", "request_id", "idea_text", "snapshot_hash"}
                    or value["workspace_id"] != "asp-draft-demo"
                    or value["request_id"] != DRAFT_ID or value["idea_text"] != DRAFT_TEXT):
                return decision("draft", "draft_content_denied")
            fingerprint = digest(canonical({k: v for k, v in p.items() if k not in ("trace_id", "span_id")}))
            if (p["input_hash"] != object_hash("action-input", value)
                    or prepared["approval_id"] != fingerprint):
                return decision("draft", "draft_integrity_mismatch")
        except (KeyError, TypeError, ValueError):
            return decision("draft", "malformed_view")
        return decision("draft")
