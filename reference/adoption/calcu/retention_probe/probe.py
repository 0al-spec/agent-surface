"""Offline interpretation only: no CLI launcher, filesystem scanner or auth access."""

from __future__ import annotations

import json
import sys


FIELDS = {
    "scenario", "baseline_clean", "output_delivered", "terminal_observed",
    "process_stopped", "scan_complete", "write_observation_complete",
    "temporary_write_seen", "retained_after_exit", "retained_after_grace",
}
SCENARIOS = {"success", "cancel_after_tool", "timeout_after_tool"}
MAX_INPUT = 8192


def parse_observation(raw: bytes) -> dict:
    """Accept only a small closed, sanitized observation, never raw logs."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("invalid_observation")
            result[key] = value
        return result

    if len(raw) > MAX_INPUT:
        raise ValueError("invalid_observation")
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("invalid_observation") from None
    if not isinstance(value, dict):
        raise ValueError("invalid_observation")
    return value


def assess(value: object) -> dict:
    """Interpret asserted observations, not certify their collection or provenance."""
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError("invalid_observation")
    if not isinstance(value["scenario"], str) or value["scenario"] not in SCENARIOS:
        raise ValueError("invalid_observation")
    if any(type(value[key]) is not bool for key in FIELDS - {"scenario"}):
        raise ValueError("invalid_observation")
    prerequisites = all(value[key] for key in (
        "baseline_clean", "output_delivered", "terminal_observed", "process_stopped",
    ))
    residue = value["retained_after_exit"] or value["retained_after_grace"]
    if not prerequisites:
        outcome = "inconclusive"
    elif value["temporary_write_seen"] or residue:
        outcome = "observed_persistence"
    elif value["scan_complete"] and value["write_observation_complete"]:
        outcome = "no_residue_observed_in_scope"
    else:
        outcome = "inconclusive"
    return {
        "report_version": 1,
        "scenario": value["scenario"],
        "local_observation": outcome,
        "conformance": "not_established",
        "provider_retention": "unknown",
        "memory_erasure": "not_measured",
        "evidence_authenticity": "not_verified",
    }


def main() -> int:
    try:
        report = assess(parse_observation(sys.stdin.buffer.read(MAX_INPUT + 1)))
    except (ValueError, TypeError):
        print('{"error":"invalid_observation"}')
        return 2
    print(json.dumps(report, sort_keys=True))
    return 1 if report["local_observation"] != "no_residue_observed_in_scope" else 0


if __name__ == "__main__":
    raise SystemExit(main())
