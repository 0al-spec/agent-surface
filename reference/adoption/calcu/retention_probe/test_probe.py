"""Synthetic observations only; never starts Codex or reads user state."""

import json
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from probe import assess, main, parse_observation


def observation(**changes):
    return {
        "scenario": "success", "baseline_clean": True, "output_delivered": True,
        "terminal_observed": True, "process_stopped": True, "scan_complete": True,
        "write_observation_complete": True, "temporary_write_seen": False,
        "retained_after_exit": False, "retained_after_grace": False, **changes,
    }


class ProbeTests(unittest.TestCase):
    def test_no_residue_never_means_conformance(self):
        report = assess(observation())
        self.assertEqual(report["local_observation"], "no_residue_observed_in_scope")
        self.assertEqual(report["conformance"], "not_established")
        self.assertEqual(report["provider_retention"], "unknown")
        self.assertEqual(report["memory_erasure"], "not_measured")

    def test_each_persistence_signal_survives_later_cleanup(self):
        for key in ("temporary_write_seen", "retained_after_exit", "retained_after_grace"):
            with self.subTest(key=key):
                self.assertEqual(assess(observation(**{key: True}))["local_observation"],
                                 "observed_persistence")

    def test_missing_evidence_cannot_pass(self):
        for key in ("baseline_clean", "output_delivered", "terminal_observed",
                    "process_stopped", "scan_complete", "write_observation_complete"):
            with self.subTest(key=key):
                self.assertEqual(assess(observation(**{key: False}))["local_observation"],
                                 "inconclusive")

    def test_incomplete_scan_does_not_hide_positive_finding(self):
        self.assertEqual(assess(observation(scan_complete=False, retained_after_exit=True))[
            "local_observation"], "observed_persistence")

    def test_failed_delivery_cannot_attribute_marker(self):
        self.assertEqual(assess(observation(output_delivered=False, retained_after_exit=True))[
            "local_observation"], "inconclusive")

    def test_all_terminal_scenarios(self):
        for scenario in ("success", "cancel_after_tool", "timeout_after_tool"):
            self.assertEqual(assess(observation(scenario=scenario))["scenario"], scenario)

    def test_closed_input_and_exact_booleans(self):
        values = [observation(raw_log="do-not-echo"), observation(process_stopped=1),
                  observation(scenario="unknown"), [], observation(scenario=[])]
        missing = observation()
        del missing["baseline_clean"]
        for value in [*values, missing]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                assess(value)

    def test_duplicate_and_malformed_json(self):
        for raw in (b'{"scenario":"success","scenario":"success"}', b'\xff', b'{',
                    b' ' * 8193, b'[' * 3000 + b']' * 3000):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                parse_observation(raw)

    def test_report_contains_no_input_payload(self):
        value = observation()
        report = assess(parse_observation(json.dumps(value).encode()))
        self.assertEqual(set(report), {"report_version", "scenario", "local_observation",
                         "conformance", "provider_retention", "memory_erasure",
                         "evidence_authenticity"})

    def test_cli_exit_codes_and_safe_errors(self):
        cases = [(json.dumps(observation()).encode(), 0),
                 (json.dumps(observation(retained_after_exit=True)).encode(), 1),
                 (json.dumps(observation(scan_complete=False)).encode(), 1),
                 (b'{"raw_log":"secret-marker"}', 2),
                 (b'x' * 8193, 2)]
        for raw, expected in cases:
            with self.subTest(expected=expected):
                output = io.StringIO()
                with patch("sys.stdin", SimpleNamespace(buffer=io.BytesIO(raw))), \
                        patch("sys.stdout", output):
                    self.assertEqual(main(), expected)
                self.assertNotIn("secret-marker", output.getvalue())
                report = json.loads(output.getvalue())
                if expected == 2:
                    self.assertEqual(report, {"error": "invalid_observation"})


if __name__ == "__main__":
    unittest.main()
