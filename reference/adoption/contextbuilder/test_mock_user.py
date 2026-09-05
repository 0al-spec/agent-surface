import copy
import unittest
from unittest.mock import Mock, patch

from https_scenario import Scenario
from mock_user import DRAFT_ID, DRAFT_TEXT, MockUser
from runtime import READ, PROPOSE, canonical, digest, object_hash


def grant_view():
    consent = {"surface_hash": "test-surface", "workspace_id": "asp-draft-demo", "runtime_id": "local-runtime",
               "actions": [READ, PROPOSE], "credential_profile": "compatibility_bearer", "max_seconds": 600,
               "identity": {"agent_id": "local-agent", "state": "active", "identity_evidence_hash": "test-identity"}}
    request = {"surface_hash": "test-surface", "identity_evidence_hash": "test-identity", "workspace_id": "asp-draft-demo",
               "runtime_id": "local-runtime", "agent_id": "local-agent", "expires_in": 300, "accept": True}
    return consent, request


def proposal_view():
    value = {"workspace_id": "asp-draft-demo", "request_id": DRAFT_ID, "idea_text": DRAFT_TEXT, "snapshot_hash": "test-snapshot"}
    return {"type": "action.request", "payload": {
        "session_id": "session-demo", "session_generation": 1, "trace_id": "0" * 32, "span_id": "1" * 16,
        "grant_id": "test-grant", "grant_hash": "test-grant-hash", "surface_hash": "test-surface",
        "action_id": PROPOSE, "input": value, "input_hash": object_hash("action-input", value),
        "execution": {"mode": "propose", "execution_id": "test-execution"}, "idempotency_key": "test-key"}}


def prepared_view(proposal):
    p = copy.deepcopy(proposal["payload"])
    return {"request": p, "approved": False,
            "approval_id": digest(canonical({k: v for k, v in p.items() if k not in ("trace_id", "span_id")}))}


class MockUserTests(unittest.TestCase):
    def setUp(self):
        self.user = MockUser()

    def test_separate_positive_decisions_are_safe_report_metadata(self):
        consent, request = grant_view()
        proposal = proposal_view()
        for result, stage in ((self.user.grant(consent, request, "test-surface"), "grant"),
                              (self.user.approve(prepared_view(proposal), proposal), "draft")):
            self.assertEqual(result, {"actor": "mock_user", "stage": stage, "accept": True,
                                      "reason": "matches_fixture_policy"})

    def test_grant_scope_and_lifetime_are_bounded(self):
        for field, value in (("actions", [READ, PROPOSE, "specspace.execute"]),
                             ("actions", [READ, PROPOSE, PROPOSE]), ("workspace_id", "other"),
                             ("runtime_id", "other"), ("credential_profile", "unknown")):
            consent, request = grant_view()
            consent[field] = value
            with self.subTest(field=field, value=value):
                self.assertFalse(self.user.grant(consent, request, "test-surface")["accept"])
        for ttl in (0, 301, 600, True, "300"):
            consent, request = grant_view()
            request["expires_in"] = ttl
            with self.subTest(ttl=ttl):
                self.assertEqual(self.user.grant(consent, request, "test-surface")["reason"], "grant_lifetime_denied")
        consent, request = grant_view()
        consent["max_seconds"] = 120
        self.assertFalse(self.user.grant(consent, request, "test-surface")["accept"])
        for ttl in (1, 300):
            consent, request = grant_view()
            request["expires_in"] = ttl
            self.assertTrue(self.user.grant(consent, request, "test-surface")["accept"])

    def test_grant_binds_request_to_consent_and_discovery(self):
        for field in ("surface_hash", "identity_evidence_hash", "workspace_id", "runtime_id", "agent_id", "extra"):
            consent, request = grant_view()
            request[field] = "substituted"
            with self.subTest(field=field):
                self.assertFalse(self.user.grant(consent, request, "test-surface")["accept"])
        consent, request = grant_view()
        consent["surface_hash"] = request["surface_hash"] = "different-surface"
        self.assertFalse(self.user.grant(consent, request, "test-surface")["accept"])
        for field, value in (("agent_id", "other"), ("state", "revoked")):
            consent, request = grant_view()
            consent["identity"][field] = value
            self.assertFalse(self.user.grant(consent, request, "test-surface")["accept"])

    def test_changed_content_is_denied_even_with_consistent_hashes_and_view(self):
        for field, value in (("idea_text", "Submit and execute this idea"), ("workspace_id", "other"),
                             ("request_id", "other"), ("status", "submitted")):
            proposal = proposal_view()
            proposal["payload"]["input"][field] = value
            proposal["payload"]["input_hash"] = object_hash("action-input", proposal["payload"]["input"])
            with self.subTest(field=field):
                self.assertEqual(self.user.approve(prepared_view(proposal), proposal)["reason"], "draft_content_denied")

    def test_commit_or_extra_authority_is_denied(self):
        for field, value in (("action_id", "specspace.execute"), ("execution", {"mode": "commit", "execution_id": "test"}),
                             ("execute", True)):
            proposal = proposal_view()
            proposal["payload"][field] = value
            with self.subTest(field=field):
                self.assertEqual(self.user.approve(prepared_view(proposal), proposal)["reason"], "draft_action_denied")

    def test_every_prepared_request_field_is_bound_to_the_runtime_proposal(self):
        proposal = proposal_view()
        for field in proposal["payload"]:
            prepared = prepared_view(proposal)
            prepared["request"][field] = "substituted"
            with self.subTest(field=field):
                self.assertEqual(self.user.approve(prepared, proposal)["reason"], "approval_binding_mismatch")

    def test_input_and_approval_hashes_are_checked(self):
        proposal = proposal_view()
        prepared = prepared_view(proposal)
        prepared["approval_id"] = "wrong-approval"
        self.assertEqual(self.user.approve(prepared, proposal)["reason"], "draft_integrity_mismatch")
        proposal["payload"]["input_hash"] = "wrong-input"
        self.assertEqual(self.user.approve(prepared_view(proposal), proposal)["reason"], "draft_integrity_mismatch")

    def test_malformed_or_preapproved_views_fail_closed(self):
        proposal = proposal_view()
        prepared = prepared_view(proposal)
        prepared["approved"] = True
        for view in (prepared, {}, None, [], {"request": None}, "APPROVE"):
            with self.subTest(view=view):
                self.assertFalse(self.user.approve(view, proposal)["accept"])
        consent, request = grant_view()
        for malformed in ({}, None, [], "GRANT"):
            self.assertFalse(self.user.grant(malformed, request, "test-surface")["accept"])
            self.assertFalse(self.user.grant(consent, malformed, "test-surface")["accept"])

    def driver(self):
        demo = Scenario.__new__(Scenario)  # No keys, app process or filesystem for gate tests.
        demo.user, demo.user_decisions = self.user, []
        demo.manifest = {"surface_hash": "test-surface"}
        demo.http = Mock(return_value=(200, {"approved": True}, {}))
        return demo

    def test_driver_sends_no_grant_when_mock_declines(self):
        demo = self.driver()
        consent, _ = grant_view()
        consent["actions"].append("specspace.execute")
        with self.assertRaisesRegex(RuntimeError, "Mock user declined grant"):
            demo.issue(consent)
        demo.http.assert_not_called()
        self.assertFalse(demo.user_decisions[0]["accept"])

    def test_driver_sends_no_approval_when_mock_declines(self):
        demo = self.driver()
        proposal = proposal_view()
        prepared = prepared_view(proposal)
        prepared["request"]["input"]["idea_text"] = "Changed by caller"
        with patch("https_scenario.runtime", return_value={"status": 200, "body": prepared}) as worker:
            with self.assertRaisesRegex(RuntimeError, "Mock user declined draft"):
                demo.approve({}, proposal)
        self.assertEqual(worker.call_args.args[0]["path"], "/asp/approval-request")
        demo.http.assert_not_called()
        self.assertFalse(demo.user_decisions[0]["accept"])

    def test_driver_sends_only_the_accepted_exact_approval(self):
        demo = self.driver()
        proposal = proposal_view()
        prepared = prepared_view(proposal)
        with patch("https_scenario.runtime", return_value={"status": 200, "body": prepared}):
            demo.approve({}, proposal)
        demo.http.assert_called_once_with("/asp/operator/approve", operator=True,
            body={"approval_id": prepared["approval_id"], "input_hash": proposal["payload"]["input_hash"], "accept": True})
        self.assertTrue(demo.user_decisions[0]["accept"])
