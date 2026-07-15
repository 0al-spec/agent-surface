#!/usr/bin/env python3
"""Stimulus-only suite plumbing fixture; never use as implementation evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path


invocation = json.load(sys.stdin)
if invocation.get("adapter_protocol") != "asp-conformance-adapter/1":
    raise SystemExit(2)
case = invocation.get("case", {})
for forbidden in (
    "expected_error",
    "expected_policy_reason",
    "expected_match_reason",
    "required_observations",
    "forbidden_observations",
    "state_deltas",
):
    if forbidden in case:
        raise SystemExit(3)
Path("executed-case.json").write_text(
    json.dumps(invocation, separators=(",", ":")), encoding="utf-8"
)
json.dump(
    {
        "schema_version": 1,
        "run_id": invocation["run_id"],
        "vector_id": invocation["vector_id"],
        "status": "completed",
    },
    sys.stdout,
    separators=(",", ":"),
)
