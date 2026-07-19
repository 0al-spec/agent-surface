"""Security and fail-closed tests for the bundled ASP reference mocks."""

from __future__ import annotations

import ast
import base64
import copy
import hashlib
import inspect
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from conformance.check import ConformanceError, _resolved_fixture, run_suite, validate_catalog
from mocks.behavior import (
    AE,
    GI,
    RM,
    RP,
    SP,
    BehaviorError,
    BehaviorResult,
    FEATURE_INVENTORY,
    _apply_redline,
    _hash_without,
    _object_hash,
    _validate_risk_explanation_publisher,
    evaluate,
    family_for,
)
from mocks.participant import ParticipantError, inventory, load_request
from mocks.state import JournalStore, Scope, StateError


ROOT = Path(__file__).resolve().parents[2]
MOCK_ROOT = ROOT / "mocks"


def digest(label: str) -> str:
    value = hashlib.sha256(label.encode("utf-8")).digest()
    return "sha-256:" + base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class MockBehaviorSecurityTests(unittest.TestCase):
    """Exercise semantics without giving the behavior core a catalog oracle."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = validate_catalog(ROOT)

    def evaluate_vector(self, vector_id: str) -> tuple[dict[str, Any], BehaviorResult]:
        vector = self.catalog.vectors[vector_id]
        fixture = _resolved_fixture(self.catalog, vector)
        return vector, self.evaluate_document(vector, fixture["document"])

    def evaluate_document(
        self,
        vector: dict[str, Any],
        document: dict[str, Any],
    ) -> BehaviorResult:
        initial_state = [
            {"state": delta["state"], "value": delta["before"]}
            for delta in vector["state_deltas"]
        ]
        return evaluate(
            profile_id=vector["profile_id"],
            producer_role=vector.get("producer_role"),
            operation=vector["stimulus"]["operation"],
            document=document,
            initial_state=initial_state,
        )

    @staticmethod
    def rehash_elicitation(document: dict[str, Any]) -> None:
        elicitation = document["elicitation"]
        request = elicitation["request"]
        response = elicitation["response"]
        request["context_hash"] = _object_hash(
            "https://github.com/0al-spec/agent-surface/hash/"
            "human-elicitation-context/v1",
            request["context"],
        )
        request["request_hash"] = _hash_without(
            "https://github.com/0al-spec/agent-surface/hash/"
            "human-elicitation-request/v1",
            request,
            "request_hash",
        )
        response["context_hash"] = request["context_hash"]
        response["request_hash"] = request["request_hash"]
        response["response_hash"] = _hash_without(
            "https://github.com/0al-spec/agent-surface/hash/"
            "human-elicitation-response/v1",
            response,
            "response_hash",
        )

    def assert_matches_catalog_oracle(self, vector_id: str) -> BehaviorResult:
        vector, result = self.evaluate_vector(vector_id)
        self.assertEqual(set(result.tokens), set(vector["required_observations"]))
        self.assertEqual(result.asp_error, vector.get("expected_error"))
        self.assertEqual(
            result.policy_reason, vector.get("expected_policy_reason")
        )
        self.assertEqual(result.match_reason, vector.get("expected_match_reason"))
        expected_before = {
            delta["state"]: delta["before"] for delta in vector["state_deltas"]
        }
        expected_after = {
            delta["state"]: delta["after"] for delta in vector["state_deltas"]
        }
        self.assertEqual(dict(result.state_before), expected_before)
        self.assertEqual(dict(result.state_after), expected_after)
        return result

    def test_all_catalog_decisions_are_derived_without_oracle_arguments(self) -> None:
        parameters = set(inspect.signature(evaluate).parameters)
        self.assertEqual(
            parameters,
            {
                "profile_id",
                "producer_role",
                "operation",
                "document",
                "initial_state",
            },
        )
        self.assertFalse(
            parameters
            & {
                "vector_id",
                "expected_error",
                "expected_policy_reason",
                "expected_match_reason",
                "required_observations",
                "forbidden_observations",
                "state_deltas",
            }
        )
        self.assertEqual(len(self.catalog.vectors), 116)
        for vector_id in self.catalog.vectors:
            with self.subTest(vector_id=vector_id):
                self.assert_matches_catalog_oracle(vector_id)

    def test_risk_explanations_are_bound_literal_and_never_authority(self) -> None:
        for vector_id in (
            "ASP-V-SP-007",
            "ASP-V-SP-008",
            "ASP-V-SP-009",
            "ASP-V-RM-043",
            "ASP-V-RM-044",
            "ASP-V-RM-045",
            "ASP-V-RM-046",
            "ASP-V-RM-047",
            "ASP-V-RM-048",
            "ASP-V-RM-049",
            "ASP-V-RM-050",
        ):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertNotIn("risk_explanation_used_as_authority", result.tokens)
                self.assertNotIn("agent_instruction_projected", result.tokens)

        vector = self.catalog.vectors["ASP-V-RM-043"]
        fixture = _resolved_fixture(self.catalog, vector)

        action_substitution = copy.deepcopy(fixture["document"])
        action_substitution["risk_explanation"]["hint_action_id"] = "comment.delete"
        substituted = self.evaluate_document(vector, action_substitution)
        self.assertEqual(substituted.decision, "stopped")
        self.assertIn("risk_explanation_binding_rejected", substituted.tokens)
        self.assertIn("canonical_risk_presented", substituted.tokens)
        self.assertEqual(substituted.state_after, substituted.state_before)

        invalid_present_hint = copy.deepcopy(fixture["document"])
        invalid_present_hint["risk_explanation"]["hint"]["default_language"] = "de"
        fallback = self.evaluate_document(vector, invalid_present_hint)
        self.assertEqual(fallback.decision, "stopped")
        self.assertIn("risk_explanation_suppressed", fallback.tokens)
        self.assertIn("canonical_effects_presented", fallback.tokens)
        self.assertNotIn("risk_explanation_rendered_literal", fallback.tokens)

        defaulted = copy.deepcopy(fixture["document"])
        risk = defaulted["risk_explanation"]
        risk["language_preferences"] = []
        risk["selected_language"] = "en"
        risk["rendered_summary"] = risk["hint"]["localizations"][0]["summary"]
        risk["rendered_effect_summaries"] = risk["hint"]["localizations"][0][
            "effect_summaries"
        ]
        selected_default = self.evaluate_document(vector, defaulted)
        self.assertEqual(selected_default.decision, "accepted")
        self.assertIn("risk_explanation_rendered_literal", selected_default.tokens)

        publisher_vector = self.catalog.vectors["ASP-V-SP-007"]
        publisher_fixture = _resolved_fixture(self.catalog, publisher_vector)
        runtime_owned_noise = copy.deepcopy(publisher_fixture["document"])
        publisher_risk = runtime_owned_noise["risk_explanation"]
        publisher_risk["language_preferences"] = ["not-a-language-tag!"]
        publisher_risk["selected_language"] = "de"
        publisher_risk["rendered_summary"] = "Runtime-owned stale state"
        publisher_risk["rendered_effect_summaries"] = []
        publisher_risk["rendering"] = "not-a-rendering-mode"
        publisher_risk["authority_use"] = "attempted"
        publisher_risk["agent_projection"] = "present"
        publisher_result = self.evaluate_document(
            publisher_vector,
            runtime_owned_noise,
        )
        self.assertEqual(publisher_result.decision, "accepted")
        self.assertIn("risk_explanation_validated", publisher_result.tokens)

        next_manifest = copy.deepcopy(publisher_fixture["document"])
        next_manifest["surface"]["candidate_hash"] = "surface_hash_b"
        next_manifest["risk_explanation"]["hint_surface_hash"] = "surface_hash_b"
        _validate_risk_explanation_publisher(next_manifest)

        retained_snapshot = copy.deepcopy(fixture["document"])
        retained_snapshot["surface"]["candidate_hash"] = "surface_hash_b"
        retained_result = self.evaluate_document(vector, retained_snapshot)
        self.assertEqual(retained_result.decision, "accepted")
        self.assertIn("risk_explanation_rendered_literal", retained_result.tokens)

        incomplete_retained = copy.deepcopy(fixture["document"])
        incomplete_retained["surface"]["references"] = "incomplete"
        incomplete_result = self.evaluate_document(vector, incomplete_retained)
        self.assertEqual(incomplete_result.decision, "stopped")
        self.assertIsNone(incomplete_result.asp_error)
        self.assertIn("risk_explanation_suppressed", incomplete_result.tokens)
        self.assertIn("canonical_risk_presented", incomplete_result.tokens)
        self.assertIn("canonical_effects_presented", incomplete_result.tokens)
        self.assertNotIn(
            "risk_explanation_rendered_literal", incomplete_result.tokens
        )
        self.assertEqual(
            incomplete_result.state_after,
            incomplete_result.state_before,
        )

        for presentation_field in ("escaped", "bidi_isolated"):
            for presentation_value in ("missing", False):
                with self.subTest(
                    presentation_field=presentation_field,
                    presentation_value=presentation_value,
                ):
                    invalid_presentation = copy.deepcopy(fixture["document"])
                    risk_projection = invalid_presentation["risk_explanation"]
                    if presentation_value == "missing":
                        del risk_projection[presentation_field]
                    else:
                        risk_projection[presentation_field] = presentation_value
                    presentation_result = self.evaluate_document(
                        vector,
                        invalid_presentation,
                    )
                    self.assertEqual(presentation_result.decision, "stopped")
                    self.assertIsNone(presentation_result.asp_error)
                    self.assertIn(
                        "risk_explanation_suppressed",
                        presentation_result.tokens,
                    )
                    self.assertIn(
                        "canonical_risk_presented",
                        presentation_result.tokens,
                    )
                    self.assertIn(
                        "canonical_effects_presented",
                        presentation_result.tokens,
                    )
                    self.assertNotIn(
                        "risk_explanation_rendered_literal",
                        presentation_result.tokens,
                    )
                    self.assertEqual(
                        presentation_result.state_after,
                        presentation_result.state_before,
                    )

        for language in ("en-a", "en-12", "de-1901-1901"):
            with self.subTest(language=language):
                malformed = copy.deepcopy(fixture["document"])
                malformed_risk = malformed["risk_explanation"]
                malformed_risk["hint"]["default_language"] = language
                malformed_risk["hint"]["localizations"][0]["language"] = language
                result = self.evaluate_document(vector, malformed)
                self.assertEqual(result.decision, "stopped")
                self.assertIn("risk_explanation_suppressed", result.tokens)

        bidi = copy.deepcopy(fixture["document"])
        bidi_risk = bidi["risk_explanation"]
        bidi_risk["hint"]["localizations"][1]["summary"] = "unsafe\u202esummary"
        bidi_risk["rendered_summary"] = "unsafe\u202esummary"
        result = self.evaluate_document(vector, bidi)
        self.assertEqual(result.decision, "stopped")
        self.assertIn("canonical_risk_presented", result.tokens)

    def test_opaque_case_label_cannot_change_behavior(self) -> None:
        vector = self.catalog.vectors["ASP-V-AE-004"]
        fixture = _resolved_fixture(self.catalog, vector)
        arguments = {
            "profile_id": vector["profile_id"],
            "producer_role": vector.get("producer_role"),
            "operation": vector["stimulus"]["operation"],
            "document": fixture["document"],
            "initial_state": [
                {"state": delta["state"], "value": delta["before"]}
                for delta in vector["state_deltas"]
            ],
        }
        labeled_cases = [
            {"opaque_case_label": label, "arguments": arguments}
            for label in ("case-alpha", "case-omega")
        ]
        results = [evaluate(**case["arguments"]) for case in labeled_cases]
        self.assertEqual(results[0], results[1])

    def test_mock_sources_have_no_catalog_or_expected_oracle_dependency(self) -> None:
        source_names = {
            "participant.py",
            "behavior.py",
            "adapter.py",
            "probe.py",
            "mock_app.py",
            "mock_runtime.py",
        }
        sources = sorted(
            path
            for path in MOCK_ROOT.rglob("*.py")
            if path.name in source_names and "tests" not in path.parts
        )
        self.assertEqual({path.name for path in sources}, source_names)
        forbidden_literals = (
            "vectors.json",
            "suite.json",
            "ASP-V-",
            "expected_",
            "required_observations",
            "forbidden_observations",
        )
        for path in sources:
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                for literal in forbidden_literals:
                    self.assertNotIn(literal, source)
                tree = ast.parse(source, filename=str(path))
                imported_roots = {
                    alias.name.split(".", 1)[0]
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Import)
                    for alias in node.names
                }
                imported_roots.update(
                    node.module.split(".", 1)[0]
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom) and node.module
                )
                self.assertNotIn("conformance", imported_roots)

    def test_raw_credentials_and_authority_widening_fail_without_release(self) -> None:
        for vector_id in ("ASP-V-RM-002", "ASP-V-RM-003", "ASP-V-AA-002"):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertNotIn("action_accepted", result.tokens)
                for state, before in result.state_before.items():
                    if state in {
                        "runtime.credential_release_count",
                        "credential.agent_visible_count",
                        "credential.adapter_retained_count",
                        "runtime.stored_grant_width",
                    }:
                        self.assertEqual(result.state_after[state], before)

    def test_revoked_or_unknown_authority_never_dispatches(self) -> None:
        for vector_id in ("ASP-V-AE-006", "ASP-V-RM-004"):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertNotIn("action_accepted", result.tokens)
                self.assertNotIn("typed_request_forwarded", result.tokens)
                if "action.dispatch_count" in result.state_before:
                    self.assertEqual(
                        result.state_after["action.dispatch_count"],
                        result.state_before["action.dispatch_count"],
                    )

    def test_idempotency_conflicts_have_no_additional_effect(self) -> None:
        for vector_id in (
            "ASP-V-AE-004",
            "ASP-V-AE-005",
            "ASP-V-AE-010",
            "ASP-V-AE-014",
        ):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertEqual(result.asp_error, "idempotency_conflict")
                for state in (
                    "action.dispatch_count",
                    "action.effect_count",
                    "budget.application_charge",
                    "idempotency.record_count",
                    "idempotency.record_version",
                    "receipt.application_count",
                ):
                    self.assertEqual(result.state_after[state], result.state_before[state])

    def test_operational_rejections_fail_closed_before_workload_or_retry(self) -> None:
        for vector_id in (
            "ASP-V-AE-016",
            "ASP-V-AE-017",
            "ASP-V-AE-018",
            "ASP-V-AE-020",
            "ASP-V-AE-023",
            "ASP-V-RM-012",
        ):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertNotIn("action_accepted", result.tokens)
                self.assertNotIn("operational_admission_committed", result.tokens)
                self.assertNotIn("retry_scheduled", result.tokens)
                for state, before in result.state_before.items():
                    if state in {
                        "application.workload_count",
                        "receipt.application_count",
                        "action.dispatch_count",
                        "action.effect_count",
                        "idempotency.record_count",
                        "budget.application_charge",
                        "reservation.active_count",
                        "operational.action.window_count",
                        "operational.action.secondary_window_count",
                        "operational.action.slot_acquisition_count",
                        "operational.action.in_flight_count",
                        "runtime.retry_count",
                    }:
                        self.assertEqual(result.state_after[state], before)

    def test_event_delivery_queues_when_limiter_state_is_unavailable(self) -> None:
        vector = self.catalog.vectors["ASP-V-AE-023"]
        fixture = _resolved_fixture(self.catalog, vector)
        document = copy.deepcopy(fixture["document"])
        document["operational"]["limiter_state"] = "unavailable"
        document["operational"]["event_capacity"] = "available"
        result = evaluate(
            profile_id=vector["profile_id"],
            producer_role=None,
            operation=vector["stimulus"]["operation"],
            document=document,
            initial_state=[
                {"state": delta["state"], "value": delta["before"]}
                for delta in vector["state_deltas"]
            ],
        )
        self.assertEqual(result.decision, "rejected")
        self.assertIn("operational_capacity_rejected", result.tokens)
        self.assertIn("event_delivery_queued", result.tokens)
        self.assertEqual(result.state_after["operational.event.queued_count"], 1)
        self.assertEqual(result.state_after["operational.event.transmission_count"], 0)

    def test_capacity_response_releases_local_slots_and_preserves_guards(self) -> None:
        retryable = self.assert_matches_catalog_oracle("ASP-V-RM-011")
        no_hint = self.assert_matches_catalog_oracle("ASP-V-RM-013")
        stopped = self.assert_matches_catalog_oracle("ASP-V-RM-012")
        for result in (retryable, no_hint, stopped):
            self.assertEqual(result.state_after["runtime.local_window_count"], 0)
            self.assertEqual(result.state_after["runtime.local_in_flight_count"], 0)
            self.assertEqual(
                result.state_after["runtime.runaway_guard_epoch"],
                result.state_before["runtime.runaway_guard_epoch"],
            )

        self.assertEqual(retryable.state_after["runtime.retry_delay_floor_seconds"], 12)
        self.assertEqual(
            no_hint.state_after["runtime.retry_delay_floor_seconds"],
            no_hint.state_before["runtime.retry_delay_floor_seconds"],
        )
        self.assertIn("local_backoff_selected", no_hint.tokens)
        self.assertTrue(retryable.state_after["runtime.retry_wait_pending"])
        self.assertTrue(no_hint.state_after["runtime.retry_wait_pending"])
        self.assertFalse(stopped.state_after["runtime.retry_wait_pending"])
        self.assertEqual(stopped.state_after["runtime.retry_delay_floor_seconds"], 0)

    def test_capacity_recovery_and_service_retry_are_distinct_state_machines(self) -> None:
        deferred = self.assert_matches_catalog_oracle("ASP-V-RM-014")
        recovered = self.assert_matches_catalog_oracle("ASP-V-RM-015")
        recovery_stopped = self.assert_matches_catalog_oracle("ASP-V-RM-016")
        service_retry = self.assert_matches_catalog_oracle("ASP-V-RM-017")
        service_stopped = self.assert_matches_catalog_oracle("ASP-V-RM-018")
        ambiguous = self.assert_matches_catalog_oracle("ASP-V-RM-019")

        self.assertTrue(deferred.state_after["runtime.capacity_recovery_pending"])
        self.assertFalse(deferred.state_after["runtime.retry_wait_pending"])
        self.assertFalse(recovered.state_after["runtime.capacity_recovery_pending"])
        self.assertTrue(recovered.state_after["runtime.retry_wait_pending"])
        self.assertFalse(
            recovery_stopped.state_after["runtime.capacity_recovery_pending"]
        )
        self.assertTrue(
            service_retry.state_after["runtime.capacity_decision_pending"]
        )
        self.assertFalse(
            service_stopped.state_after["runtime.capacity_decision_pending"]
        )
        self.assertEqual(ambiguous.asp_error, "outcome_unknown")
        self.assertIn("outcome_reconciliation_required", ambiguous.tokens)
        self.assertNotIn("capacity_response_validated", ambiguous.tokens)

        for result in (
            deferred,
            recovered,
            recovery_stopped,
            service_retry,
            service_stopped,
        ):
            self.assertEqual(result.state_after["runtime.local_window_count"], 0)
            self.assertEqual(result.state_after["runtime.local_in_flight_count"], 0)
            self.assertEqual(
                result.state_after["runtime.runaway_guard_epoch"],
                result.state_before["runtime.runaway_guard_epoch"],
            )
        self.assertEqual(
            ambiguous.state_after["runtime.local_window_count"],
            ambiguous.state_before["runtime.local_window_count"],
        )
        self.assertEqual(
            ambiguous.state_after["runtime.local_in_flight_count"],
            ambiguous.state_before["runtime.local_in_flight_count"],
        )
        self.assertEqual(
            ambiguous.state_after["runtime.runaway_guard_epoch"],
            ambiguous.state_before["runtime.runaway_guard_epoch"],
        )

    def test_http_capacity_binding_maps_and_rejects_before_slot_release(self) -> None:
        producers = {
            "ASP-V-AE-024": "rate_limited",
            "ASP-V-AE-025": "capacity_state_unavailable",
            "ASP-V-AE-026": "service_unavailable",
        }
        for vector_id, error in producers.items():
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertEqual(result.asp_error, error)
                self.assertIn("http_capacity_response_bound", result.tokens)
                self.assertIn("http_status_mapped", result.tokens)
                self.assertIn("http_no_store_applied", result.tokens)
                self.assertEqual(result.state_after, result.state_before)

        for vector_id in ("ASP-V-RM-020", "ASP-V-RM-024", "ASP-V-RM-026"):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertIn("http_capacity_binding_validated", result.tokens)
                self.assertIn("http_status_mapped", result.tokens)
                self.assertIn("http_no_store_validated", result.tokens)

        for vector_id in (
            "ASP-V-RM-021",
            "ASP-V-RM-022",
            "ASP-V-RM-023",
            "ASP-V-RM-025",
            "ASP-V-RM-027",
        ):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertIn("http_capacity_binding_rejected", result.tokens)
                self.assertIn("retry_suppressed", result.tokens)
                self.assertNotIn("capacity_response_validated", result.tokens)
                self.assertEqual(result.state_after, result.state_before)

        vector = self.catalog.vectors["ASP-V-RM-024"]
        fixture = _resolved_fixture(self.catalog, vector)
        document = copy.deepcopy(fixture["document"])
        document["transport"]["retry_after"] = {
            "form": "http_date",
            "value": "soon",
        }
        initial_state = [
            {"state": delta["state"], "value": delta["before"]}
            for delta in vector["state_deltas"]
        ]
        malformed_date = evaluate(
            profile_id=vector["profile_id"],
            producer_role=vector.get("producer_role"),
            operation=vector["stimulus"]["operation"],
            document=document,
            initial_state=initial_state,
        )
        self.assertIn("http_capacity_binding_rejected", malformed_date.tokens)
        self.assertIn("retry_suppressed", malformed_date.tokens)
        self.assertEqual(malformed_date.state_after, malformed_date.state_before)

    def test_asp_over_ahp_binding_preserves_asp_authority(self) -> None:
        positive_runtime = self.assert_matches_catalog_oracle("ASP-V-RM-028")
        self.assertIn("ahp_ui_state_presented", positive_runtime.tokens)
        self.assertEqual(
            positive_runtime.state_after["action.dispatch_count"],
            positive_runtime.state_before["action.dispatch_count"],
        )
        self.assertEqual(
            positive_runtime.state_after["credential.agent_visible_count"], 0
        )
        self.assertEqual(positive_runtime.state_after["receipt.runtime_count"], 0)

        positive_adapter = self.assert_matches_catalog_oracle("ASP-V-AA-006")
        self.assertIn("ahp_control_translated", positive_adapter.tokens)
        self.assertEqual(
            positive_adapter.state_after["adapter.forwarded_count"],
            positive_adapter.state_before["adapter.forwarded_count"] + 1,
        )
        self.assertEqual(
            positive_adapter.state_after["credential.adapter_retained_count"], 0
        )

        for vector_id in (
            "ASP-V-RM-029",
            "ASP-V-RM-030",
            "ASP-V-RM-031",
            "ASP-V-RM-032",
            "ASP-V-AA-007",
            "ASP-V-AA-008",
        ):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertIn("ahp_binding_rejected", result.tokens)
                self.assertEqual(result.policy_reason, "binding_invalid")
                self.assertEqual(result.state_after, result.state_before)

    def test_human_elicitation_is_typed_input_without_approval_authority(self) -> None:
        for vector_id, required_token in (
            ("ASP-V-RM-033", "elicitation_request_presented"),
            ("ASP-V-RM-034", "elicitation_choice_validated"),
            ("ASP-V-RM-035", "step_up_result_verified"),
            ("ASP-V-AE-027", "elicitation_candidate_revalidated"),
            ("ASP-V-AE-028", "elicitation_redline_applied"),
            ("ASP-V-RM-039", "elicitation_response_accepted"),
            ("ASP-V-AA-009", "elicitation_response_accepted"),
        ):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertIn(required_token, result.tokens)
                self.assertNotIn("action_accepted", result.tokens)
                self.assertEqual(
                    result.state_after["action.dispatch_count"],
                    result.state_before["action.dispatch_count"],
                )
                self.assertEqual(
                    result.state_after["action.effect_count"],
                    result.state_before["action.effect_count"],
                )

        replay = self.assert_matches_catalog_oracle("ASP-V-RM-039")
        self.assertNotIn("elicitation_request_presented", replay.tokens)
        self.assertEqual(replay.state_after, replay.state_before)

        for vector_id in (
            "ASP-V-RM-036",
            "ASP-V-RM-037",
            "ASP-V-RM-038",
            "ASP-V-RM-040",
            "ASP-V-AE-029",
            "ASP-V-AE-030",
            "ASP-V-AA-010",
            "ASP-V-AA-011",
        ):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertEqual(result.asp_error, "elicitation_invalid")
                self.assertIn("elicitation_binding_rejected", result.tokens)
                self.assertEqual(result.state_after, result.state_before)

    def test_human_elicitation_semantics_are_executed_not_trusted(self) -> None:
        def fixture_document(vector_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
            vector = self.catalog.vectors[vector_id]
            fixture = _resolved_fixture(self.catalog, vector)
            return vector, copy.deepcopy(fixture["document"])

        vector, same_role = fixture_document("ASP-V-RM-033")
        same_role["elicitation"]["authenticated_requester"]["type"] = "runtime"
        same_role["elicitation"]["request"]["requester"]["type"] = "runtime"
        self.rehash_elicitation(same_role)
        result = self.evaluate_document(vector, same_role)
        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.state_after, result.state_before)

        vector, unselected = fixture_document("ASP-V-RM-033")
        unselected["elicitation"]["selected_profile"] = "none"
        result = self.evaluate_document(vector, unselected)
        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.state_after, result.state_before)

        vector, premature_terminal_record = fixture_document("ASP-V-RM-033")
        premature_terminal_record["elicitation"][
            "terminal_accepted_at"
        ] = "2026-07-18T13:05:00Z"
        result = self.evaluate_document(vector, premature_terminal_record)
        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.state_after, result.state_before)

        replay_vector, tombstone = fixture_document("ASP-V-RM-039")
        tombstone["elicitation"]["replay_record_state"] = "tombstone"
        result = self.evaluate_document(replay_vector, tombstone)
        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.state_after, result.state_before)

        replay_vector, delayed_acceptance = fixture_document("ASP-V-RM-039")
        delayed_acceptance["elicitation"][
            "terminal_accepted_at"
        ] = "2026-07-18T13:05:30Z"
        delayed_acceptance["elicitation"][
            "evaluation_time"
        ] = "2026-07-18T14:05:15Z"
        result = self.evaluate_document(replay_vector, delayed_acceptance)
        self.assertEqual(result.decision, "accepted")
        self.assertEqual(result.state_after, result.state_before)

        replay_vector, expired_replay = fixture_document("ASP-V-RM-039")
        expired_replay["elicitation"]["evaluation_time"] = "2026-07-18T14:06:01Z"
        result = self.evaluate_document(replay_vector, expired_replay)
        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.state_after, result.state_before)

        vector, invalid_answer = fixture_document("ASP-V-RM-033")
        invalid_answer["elicitation"]["response"]["response"]["answer"] = 42
        self.rehash_elicitation(invalid_answer)
        result = self.evaluate_document(vector, invalid_answer)
        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.asp_error, "elicitation_invalid")

        vector, external_schema = fixture_document("ASP-V-RM-033")
        request_body = external_schema["elicitation"]["request"]["request"]
        request_body["response_schema"] = {
            "$ref": "https://example.com/external.schema.json"
        }
        request_body["response_schema_hash"] = _object_hash(
            "https://github.com/0al-spec/agent-surface/hash/"
            "action-input-schema/v1",
            request_body["response_schema"],
        )
        self.rehash_elicitation(external_schema)
        result = self.evaluate_document(vector, external_schema)
        self.assertEqual(result.decision, "rejected")

        vector, forbidden_edit = fixture_document("ASP-V-AE-027")
        response_body = forbidden_edit["elicitation"]["response"]["response"]
        response_body["candidate"]["metadata"] = "changed"
        response_body["candidate_hash"] = _object_hash(
            "https://github.com/0al-spec/agent-surface/hash/action-input/v1",
            response_body["candidate"],
        )
        self.rehash_elicitation(forbidden_edit)
        result = self.evaluate_document(vector, forbidden_edit)
        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.state_after, result.state_before)

        vector, forbidden_redline = fixture_document("ASP-V-AE-028")
        response_body = forbidden_redline["elicitation"]["response"]["response"]
        response_body["patch"] = [
            {"op": "replace", "path": "/metadata", "value": "changed"}
        ]
        candidate = copy.deepcopy(
            forbidden_redline["elicitation"]["authoritative_base"]
        )
        candidate["metadata"] = "changed"
        response_body["candidate_hash"] = _object_hash(
            "https://github.com/0al-spec/agent-surface/hash/action-input/v1",
            candidate,
        )
        self.rehash_elicitation(forbidden_redline)
        result = self.evaluate_document(vector, forbidden_redline)
        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.state_after, result.state_before)

        for vector_id in ("ASP-V-AE-027", "ASP-V-AE-028"):
            with self.subTest(runtime_revalidation=vector_id):
                _, candidate_document = fixture_document(vector_id)
                result = evaluate(
                    profile_id=RM,
                    producer_role=None,
                    operation="mediate_human_elicitation",
                    document=candidate_document,
                    initial_state=[
                        {"state": "runtime.elicitation_revision", "value": 0},
                        {"state": "runtime.elicitation_response_count", "value": 0},
                        {"state": "action.dispatch_count", "value": 0},
                        {"state": "action.effect_count", "value": 0},
                    ],
                )
                self.assertEqual(result.decision, "accepted")
                self.assertEqual(result.state_after["runtime.elicitation_revision"], 1)
                self.assertEqual(
                    result.state_after["runtime.elicitation_response_count"], 1
                )
                self.assertEqual(result.state_after["action.dispatch_count"], 0)
                self.assertEqual(result.state_after["action.effect_count"], 0)

        vector, stale_step_up = fixture_document("ASP-V-RM-035")
        stale_step_up["elicitation"]["response"]["response"][
            "authenticated_at"
        ] = "2026-07-18T12:00:00Z"
        self.rehash_elicitation(stale_step_up)
        result = self.evaluate_document(vector, stale_step_up)
        self.assertEqual(result.decision, "rejected")
        self.assertIn("human_secret_withheld", result.tokens)

        _, external_step_up = fixture_document("ASP-V-RM-035")
        self.assertEqual(
            external_step_up["elicitation"]["authenticated_verifier"]["type"],
            "external",
        )
        self.assertEqual(
            external_step_up["elicitation"]["authoritative_step_up_result"][
                "verifier"
            ],
            external_step_up["elicitation"]["response"]["response"]["verifier"],
        )
        self.assertEqual(
            external_step_up["elicitation"]["authoritative_step_up_result"][
                "audience"
            ],
            external_step_up["elicitation"]["authenticated_requester"],
        )

    def test_external_dynamic_schema_references_fail_closed(self) -> None:
        vector = self.catalog.vectors["ASP-V-RM-033"]
        fixture = _resolved_fixture(self.catalog, vector)
        document = copy.deepcopy(fixture["document"])
        request_body = document["elicitation"]["request"]["request"]
        request_body["response_schema"] = {
            "$dynamicRef": "https://example.com/external.schema.json#answer"
        }
        request_body["response_schema_hash"] = _object_hash(
            "https://github.com/0al-spec/agent-surface/hash/"
            "action-input-schema/v1",
            request_body["response_schema"],
        )
        self.rehash_elicitation(document)

        result = self.evaluate_document(vector, document)

        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.asp_error, "elicitation_invalid")
        self.assertEqual(result.state_after, result.state_before)

    def test_json_patch_array_indexes_follow_rfc6902(self) -> None:
        base = {"items": ["zero", "one"]}
        invalid_patches = (
            [{"op": "add", "path": "/items/-1", "value": "bad"}],
            [{"op": "add", "path": "/items/999", "value": "bad"}],
            [{"op": "remove", "path": "/items/-1"}],
            [{"op": "replace", "path": "/items/2", "value": "bad"}],
            [{"op": "replace", "path": "/items/01", "value": "bad"}],
        )
        for patch in invalid_patches:
            with self.subTest(patch=patch):
                with self.assertRaisesRegex(
                    BehaviorError,
                    "redline path is not present in its exact base",
                ):
                    _apply_redline(base, patch)

        self.assertEqual(
            _apply_redline(
                base,
                [{"op": "add", "path": "/items/2", "value": "two"}],
            ),
            {"items": ["zero", "one", "two"]},
        )
        self.assertEqual(
            _apply_redline(
                base,
                [{"op": "add", "path": "/items/-", "value": "two"}],
            ),
            {"items": ["zero", "one", "two"]},
        )

    def test_future_human_elicitation_resolution_fails_closed(self) -> None:
        vector = self.catalog.vectors["ASP-V-RM-033"]
        fixture = _resolved_fixture(self.catalog, vector)
        document = copy.deepcopy(fixture["document"])
        document["elicitation"]["response"][
            "resolved_at"
        ] = "2026-07-18T13:07:00Z"
        self.rehash_elicitation(document)

        result = self.evaluate_document(vector, document)

        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.asp_error, "elicitation_invalid")
        self.assertEqual(result.state_after, result.state_before)

    def test_canonical_hash_uses_rfc8785_utf16_order_and_rejects_unsafe_values(
        self,
    ) -> None:
        canonical = (
            '{"domain":"test","object":{"𐀀":1,"\ue000":2}}'.encode("utf-8")
        )
        digest_bytes = hashlib.sha256(canonical).digest()
        expected = (
            "sha-256:"
            + base64.urlsafe_b64encode(digest_bytes).rstrip(b"=").decode("ascii")
        )
        self.assertEqual(_object_hash("test", {"\ue000": 2, "𐀀": 1}), expected)
        self.assertIsInstance(_object_hash("test", {"value": 1.5}), str)
        for value in (-0.0, float("inf"), float("nan"), "\ud800"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(BehaviorError):
                    _object_hash("test", {"value": value})

    def test_non_rate_capacity_envelopes_with_limit_fail_closed(self) -> None:
        for vector_id in ("ASP-V-RM-014", "ASP-V-RM-017"):
            with self.subTest(vector_id=vector_id):
                vector = self.catalog.vectors[vector_id]
                fixture = _resolved_fixture(self.catalog, vector)
                document = copy.deepcopy(fixture["document"])
                document["operational"]["capacity_response"]["limit"] = {
                    "retry_after_seconds": 1
                }
                with self.assertRaisesRegex(BehaviorError, "must omit limit"):
                    evaluate(
                        profile_id=vector["profile_id"],
                        producer_role=None,
                        operation=vector["stimulus"]["operation"],
                        document=document,
                        initial_state=[
                            {"state": delta["state"], "value": delta["before"]}
                            for delta in vector["state_deltas"]
                        ],
                    )

    def test_replay_and_retransmission_do_not_consume_first_admission_again(self) -> None:
        for vector_id in ("ASP-V-AE-019", "ASP-V-AE-022"):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                for state, before in result.state_before.items():
                    if state != "operational.event.transmission_count":
                        self.assertEqual(result.state_after[state], before)

    def test_receipt_role_forgery_never_creates_authoritative_evidence(self) -> None:
        for vector_id in (
            "ASP-V-RP-003",
            "ASP-V-RP-004",
            "ASP-V-RP-007",
            "ASP-V-RP-008",
            "ASP-V-AA-004",
        ):
            with self.subTest(vector_id=vector_id):
                result = self.assert_matches_catalog_oracle(vector_id)
                self.assertNotIn("action_accepted", result.tokens)
                for state, before in result.state_before.items():
                    if (
                        state.startswith("receipt.")
                        or state == "adapter.fabricated_evidence_count"
                    ):
                        self.assertEqual(result.state_after[state], before)


class MockStateSecurityTests(unittest.TestCase):
    def journal(self, scope: Scope, *, marker: str = "original") -> dict[str, Any]:
        return {
            "run_id": scope.run_id,
            "vector_id": scope.vector_id,
            "boundary_id": scope.boundary_id,
            "marker": marker,
        }

    def test_journal_scope_is_initialized_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JournalStore(directory)
            scope = Scope("run-a", "vector-a", "boundary-a")
            journal = self.journal(scope)
            path = store.initialize(scope, journal)
            self.assertEqual(store.read(scope), journal)
            self.assertEqual(path.name, "journal.json")
            with self.assertRaisesRegex(StateError, "already initialized"):
                store.initialize(scope, journal)

    def test_initialize_rejects_non_ijson_before_creating_scope(self) -> None:
        invalid_values = (1.5, 2**53, "\ud800")
        for value in invalid_values:
            with self.subTest(value=repr(value)), tempfile.TemporaryDirectory() as directory:
                store = JournalStore(directory)
                scope = Scope("run-a", "vector-a", "boundary-a")
                journal = self.journal(scope)
                journal["invalid"] = value
                with self.assertRaises(StateError):
                    store.initialize(scope, journal)
                self.assertFalse((store.root / scope.key).exists())

    def test_family_boundary_run_and_vector_namespaces_are_disjoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app_store = JournalStore(root / "app")
            runtime_store = JournalStore(root / "runtime")
            scopes = (
                Scope("run-a", "vector-a", "boundary-a"),
                Scope("run-b", "vector-a", "boundary-a"),
                Scope("run-a", "vector-b", "boundary-a"),
                Scope("run-a", "vector-a", "boundary-b"),
            )
            paths = []
            for index, scope in enumerate(scopes):
                marker = f"app-{index}"
                paths.append(app_store.initialize(scope, self.journal(scope, marker=marker)))
                self.assertEqual(app_store.read(scope)["marker"], marker)
            self.assertEqual(len({path.parent for path in paths}), len(scopes))

            runtime_path = runtime_store.initialize(
                scopes[0], self.journal(scopes[0], marker="runtime")
            )
            self.assertNotEqual(runtime_path.parent, paths[0].parent)
            self.assertEqual(app_store.read(scopes[0])["marker"], "app-0")
            self.assertEqual(runtime_store.read(scopes[0])["marker"], "runtime")

    def test_scope_binding_conflicts_and_stale_binding_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JournalStore(directory)
            scope = Scope("run-a", "vector-a", "boundary-a")
            wrong = self.journal(scope)
            wrong["boundary_id"] = "boundary-b"
            with self.assertRaisesRegex(StateError, "conflicts"):
                store.initialize(scope, wrong)

            path = store.initialize(scope, self.journal(scope))
            value = json.loads(path.read_text(encoding="utf-8"))
            value["run_id"] = "stale-run"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "stale run_id"):
                store.read(scope)

    def test_truncated_duplicate_and_incomplete_journals_fail_closed(self) -> None:
        corrupt_payloads = (
            "{",
            '{"run_id":"run-a","run_id":"run-a","vector_id":"vector-a",'
            '"boundary_id":"boundary-a"}',
            '{"run_id":"run-a","vector_id":"vector-a",'
            '"boundary_id":"boundary-a","counter":1.5}',
            '{"run_id":"run-a","vector_id":"vector-a",'
            '"boundary_id":"boundary-a","counter":9007199254740992}',
            '{"run_id":"run-a","vector_id":"vector-a",'
            '"boundary_id":"boundary-a","text":"\\ud800"}',
        )
        for payload in corrupt_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                store = JournalStore(directory)
                scope = Scope("run-a", "vector-a", "boundary-a")
                path = store.initialize(scope, self.journal(scope))
                path.write_text(payload, encoding="utf-8")
                with self.assertRaisesRegex(StateError, "corrupt"):
                    store.read(scope)

        with tempfile.TemporaryDirectory() as directory:
            store = JournalStore(directory)
            scope = Scope("run-a", "vector-a", "boundary-a")
            path = store.initialize(scope, self.journal(scope))
            (path.parent / "journal.json.tmp").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(StateError, "absent or incomplete"):
                store.read(scope)

    def test_scope_directory_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = JournalStore(root / "store")
            scope = Scope("run-a", "vector-a", "boundary-a")
            external = root / "external"
            external.mkdir()
            (external / "journal.json").write_text(
                json.dumps(self.journal(scope)), encoding="utf-8"
            )
            store.root.mkdir(parents=True)
            (store.root / scope.key).symlink_to(external, target_is_directory=True)
            with self.assertRaises(StateError):
                store.read(scope)

    def test_participant_input_accepts_finite_binary64_and_rejects_unsafe_json(
        self,
    ) -> None:
        with self.assertRaisesRegex(ParticipantError, "duplicate JSON"):
            load_request(io.StringIO('{"operation":"a","operation":"b"}'))
        parsed = load_request(io.StringIO('{"payload":{"answer":1.5}}'))
        self.assertEqual(parsed["payload"]["answer"], 1.5)
        for payload in (
            '{"payload":{"answer":-0}}',
            '{"payload":{"answer":-0.0}}',
            '{"payload":{"answer":1e400}}',
            '{"payload":{"answer":NaN}}',
            '{"payload":{"answer":Infinity}}',
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ParticipantError):
                    load_request(io.StringIO(payload))
        with self.assertRaisesRegex(ParticipantError, "safe range"):
            load_request(io.StringIO('{"operation":9007199254740992}'))
        with self.assertRaisesRegex(ParticipantError, "invalid Unicode"):
            load_request(io.StringIO('{"operation":"\\ud800"}'))

    def test_journal_rejects_invalid_unicode_member_names_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JournalStore(directory)
            scope = Scope("run-a", "vector-a", "boundary-a")
            journal = self.journal(scope)
            journal["\ud800"] = "value"
            with self.assertRaisesRegex(StateError, "invalid Unicode"):
                store.initialize(scope, journal)
            self.assertFalse(store._directory(scope).exists())


class MockParticipantSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = validate_catalog(ROOT)

    def inventory_request(self, profile_id: str, producer_role: str | None = None) -> dict:
        locator: dict[str, Any] = {
            "profile_id": profile_id,
            "boundary_id": "test/boundary",
        }
        if producer_role is not None:
            locator["producer_role"] = producer_role
        return {
            "probe_protocol": "asp-conformance-probe/1",
            "operation": "inventory",
            "run_id": "run-role-ownership",
            "subject_sha256": digest("subject"),
            "harness_sha256": digest("harness"),
            "subject_locator": locator,
        }

    def subject(self, *, subject_kind: str = "suite_fixture") -> dict[str, Any]:
        counterparts: list[dict[str, Any]] = []
        for index, (profile_id, producer_role) in enumerate(
            (
                (RM, None),
                (GI, None),
                (RP, "runtime"),
            ),
            start=1,
        ):
            counterpart = {
                "kind": "suite_fixture",
                "boundary_id": f"mock/counterpart-{index}",
                "profile_id": profile_id,
                "artifact_sha256": digest(f"counterpart-artifact-{index}"),
                "configuration_sha256": digest(f"counterpart-config-{index}"),
            }
            if producer_role is not None:
                counterpart["producer_role"] = producer_role
            counterparts.append(counterpart)
        return {
            "schema_version": 1,
            "subject_kind": subject_kind,
            "subject_id": "mock-action-executor",
            "boundary_id": "mock/app",
            "implementation": {
                "name": "reference-mock-app",
                "version": "1.0.0",
                "artifact_sha256": digest("mock-app-artifact"),
                "configuration_sha256": digest("mock-app-configuration"),
            },
            "profile_id": AE,
            "protocol_version": "agent-surface/0.1",
            "features": list(FEATURE_INVENTORY[AE]),
            "counterparts": counterparts,
        }

    def run_subject(
        self,
        subject: dict[str, Any],
        *,
        adapter: Path | None = None,
        probe: Path | None = None,
    ) -> dict[str, Any]:
        return run_suite(
            subject=subject,
            adapter=adapter or MOCK_ROOT / "adapter.py",
            probe=probe or MOCK_ROOT / "probe.py",
            adapter_id="reference-mock-adapter",
            adapter_version="1.0.0",
            adapter_configuration_sha256=digest("mock-adapter-configuration"),
            probe_id="reference-mock-probe",
            probe_version="1.0.0",
            probe_configuration_sha256=digest("mock-probe-configuration"),
            root=ROOT,
        )

    def test_app_and_runtime_role_ownership_is_closed(self) -> None:
        self.assertEqual(family_for(SP), "app")
        self.assertEqual(family_for(GI), "app")
        self.assertEqual(family_for(AE), "app")
        self.assertEqual(family_for(RP, "application"), "app")
        self.assertEqual(family_for(RM), "runtime")
        self.assertEqual(family_for(RP, "runtime"), "runtime")

        self.assertEqual(inventory("app", self.inventory_request(SP))["feature_ids"], list(FEATURE_INVENTORY[SP]))
        self.assertEqual(inventory("runtime", self.inventory_request(RM))["feature_ids"], list(FEATURE_INVENTORY[RM]))
        with self.assertRaisesRegex(ParticipantError, "outside"):
            inventory("runtime", self.inventory_request(SP))
        with self.assertRaisesRegex(ParticipantError, "outside"):
            inventory("app", self.inventory_request(RM))

    def test_feature_inventory_is_lexicographically_canonical(self) -> None:
        for profile_id, feature_ids in FEATURE_INVENTORY.items():
            with self.subTest(profile_id=profile_id):
                self.assertEqual(list(feature_ids), sorted(feature_ids))

    def test_canonical_bundle_binds_the_security_test_artifact(self) -> None:
        manifest = json.loads(
            (MOCK_ROOT / "v1" / "manifest.json").read_text(encoding="utf-8")
        )
        artifact_paths = [item["path"] for item in manifest["artifacts"]]
        self.assertIn("mocks/tests/test_mocks.py", artifact_paths)

    def test_suite_fixture_counterparts_leave_interop_unavailable_and_incomplete(self) -> None:
        report = self.run_subject(self.subject())
        interop_results = [
            result
            for result in report["results"]
            if self.catalog.vectors[result["vector_id"]]["execution_class"] == "interop"
        ]
        behavioral_results = [
            result
            for result in report["results"]
            if self.catalog.vectors[result["vector_id"]]["execution_class"] != "interop"
        ]
        self.assertTrue(interop_results)
        self.assertTrue(behavioral_results)
        self.assertTrue(
            all(
                result["status"] == "error"
                and result["failure_token"] == "unavailable_probe"
                and not result["observation_ids"]
                for result in interop_results
            )
        )
        self.assertTrue(all(result["status"] == "pass" for result in behavioral_results))
        self.assertEqual(report["summary"]["suite_verdict"], "incomplete")
        self.assertEqual(
            report["summary"]["incomplete_reasons"],
            ["execution_error", "suite_fixture"],
        )

    def test_metadata_only_implementation_counterparts_cannot_enable_interop(self) -> None:
        subject = self.subject()
        for counterpart in subject["counterparts"]:
            counterpart["kind"] = "implementation"
        report = self.run_subject(subject)
        interop_results = [
            result
            for result in report["results"]
            if self.catalog.vectors[result["vector_id"]]["execution_class"]
            == "interop"
        ]
        self.assertTrue(interop_results)
        self.assertTrue(
            all(
                result["status"] == "error"
                and result["failure_token"]
                in {"adapter_error", "unavailable_probe"}
                and not result["observation_ids"]
                for result in interop_results
            )
        )
        self.assertTrue(
            any(
                result["failure_token"] == "adapter_error"
                for result in interop_results
            )
        )
        self.assertEqual(report["summary"]["suite_verdict"], "incomplete")
        self.assertEqual(
            report["summary"]["incomplete_reasons"],
            ["execution_error", "suite_fixture"],
        )

    def test_bundled_or_byte_identical_mocks_cannot_claim_implementation(self) -> None:
        subject = self.subject(subject_kind="implementation")
        with self.assertRaisesRegex(ConformanceError, "reference fixtures"):
            self.run_subject(subject)

        with tempfile.TemporaryDirectory() as directory:
            adapter = Path(directory) / "renamed-adapter.py"
            probe = Path(directory) / "renamed-probe.py"
            shutil.copy2(MOCK_ROOT / "adapter.py", adapter)
            shutil.copy2(MOCK_ROOT / "probe.py", probe)
            with self.assertRaisesRegex(ConformanceError, "reference fixtures"):
                self.run_subject(subject, adapter=adapter, probe=probe)

if __name__ == "__main__":
    unittest.main()
