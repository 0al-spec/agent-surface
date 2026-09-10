"""Focused retention vectors over existing projection validators, not live agents."""

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from conformance.check import (
    ConformanceError,
    _impact_candidate_projection,
    _schema_registry,
    validate_impact_simulation,
)
from mocks.behavior import (
    BehaviorError,
    _impact_candidate_projection as mock_candidate,
    _validate_impact_action as mock_action,
)

ROOT = Path(__file__).resolve().parents[2]


class UserManagedRetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cases = json.loads((ROOT / "conformance/v1/schema-cases.json").read_text())
        cls.base = next(c for c in cases["cases"] if c["case_id"] == "ASP-SC-IS-001")
        cls.schema = json.loads((ROOT / "conformance/v1/impact-simulation.schema.json").read_text())
        cls.validator = Draft202012Validator(cls.schema)
        cls.registry = _schema_registry(ROOT)

    def example(self, retention):
        value = json.loads(self.base["instance_json"])
        context = copy.deepcopy(self.base["context"])
        value["examples"][0]["action"]["data_exposure"]["retention"] = copy.deepcopy(retention)
        context["actions"][0]["data_exposure"]["retention"] = copy.deepcopy(retention)
        return value, context

    def validate(self, value, context):
        validate_impact_simulation(value, context, schema=self.schema, registry=self.registry)

    def test_closed_positive_shapes_and_legacy_boolean_choices(self):
        for retention in (
            {"mode": "user_managed"},
            *({"mode": "transient", "delete_on_grant_end": flag} for flag in (True, False)),
            *({"mode": "bounded", "max_seconds": 60, "delete_on_grant_end": flag} for flag in (True, False)),
        ):
            with self.subTest(retention=retention):
                value, context = self.example(retention)
                self.assertTrue(self.validator.is_valid(value))
                self.validate(value, context)
                mock_action(value["examples"][0]["action"])

    def test_negative_shapes_rejected_by_schema_checker_and_independent_mock(self):
        for retention in (
            {}, None, {"mode": None}, {"mode": "unknown"},
            {"mode": []}, {"mode": {}}, {"mode": False},
            {"mode": "user_managed", "delete_on_grant_end": True},
            {"mode": "user_managed", "delete_on_grant_end": False},
            {"mode": "user_managed", "max_seconds": 60},
            {"mode": "user_managed", "extra": True},
            {"mode": "transient"},
            {"mode": "bounded", "delete_on_grant_end": False},
            {"mode": "bounded", "max_seconds": True, "delete_on_grant_end": False},
        ):
            with self.subTest(retention=retention):
                value, context = self.example(retention)
                self.assertFalse(self.validator.is_valid(value))
                with self.assertRaises(ConformanceError):
                    self.validate(value, context)
                with self.assertRaises(BehaviorError):
                    mock_action(value["examples"][0]["action"])

    def test_caller_cannot_replace_pinned_strict_source_projection(self):
        value, context = self.example({"mode": "user_managed"})
        context["actions"][0]["data_exposure"]["retention"] = {
            "mode": "bounded", "max_seconds": 60, "delete_on_grant_end": True,
        }
        with self.assertRaises(ConformanceError):
            self.validate(value, context)

    def test_user_managed_does_not_bypass_candidate_checks(self):
        # Facts are trusted fixture inputs, not claims supplied by the agent.
        # These exercise mapping and projection, not a real inventory resolver.
        for check, outcome, reason in (
            ("schema", "not_covered", "schema_unsupported"),
            ("required_input", "indeterminate", "input_unknown"),
            ("retention", "not_covered", "retention_unsupported"),
            ("policy", "not_covered", "policy_denied"),
            ("remote_processing", "not_covered", "remote_processing_unsupported"),
            ("training_use", "not_covered", "training_use_unsupported"),
            ("scope", "not_covered", "scope_unavailable"),
        ):
            with self.subTest(check=check):
                value, context = self.example({"mode": "user_managed"})
                next(f for f in context["candidate_check_facts"] if f["check_id"] == check)["state"] = "blocking"
                args = (context["candidate_check_facts"], None, context["bindings"])
                self.assertEqual(_impact_candidate_projection(*args), (outcome, [reason]))
                self.assertEqual(mock_candidate(*args), (outcome, [reason]))
                with self.assertRaises(ConformanceError):
                    self.validate(value, context)  # fabricated compatible result
                value["examples"][0].update(outcome=outcome, reasons=[reason])
                self.validate(value, context)

    def test_mode_does_not_hide_stale_surface_binding(self):
        value, context = self.example({"mode": "user_managed"})
        context["current_binding_facts"]["surface"]["surface_version"] = "replacement"
        with self.assertRaises(ConformanceError):
            self.validate(value, context)


if __name__ == "__main__":
    unittest.main()
