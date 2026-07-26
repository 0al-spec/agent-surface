#!/usr/bin/env python3
"""State probe for the independently executable reference participants."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


KNOWN_SUBJECTS = {
    "reference-app-control",
    "reference-app-executor",
    "reference-app-receipt",
    "reference-runtime-local",
    "reference-runtime-remote",
    "reference-agent-a",
    "reference-agent-b",
}


def fail(message: str) -> "None":
    print(message, file=sys.stderr)
    raise SystemExit(2)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def domain_digest(domain: str, value: object) -> str:
    digest = hashlib.sha256(domain.encode("ascii") + b"\0" + canonical_bytes(value)).digest()
    return "sha-256:" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


try:
    invocation = json.load(sys.stdin)
except (UnicodeError, json.JSONDecodeError) as error:
    fail(f"invalid JSON: {error}")
if not isinstance(invocation, dict) or invocation.get("probe_protocol") != "asp-conformance-probe/1":
    fail("unsupported probe invocation")
locator = invocation.get("subject_locator")
if not isinstance(locator, dict) or locator.get("subject_id") not in KNOWN_SUBJECTS:
    fail("unknown subject locator")

if invocation.get("operation") == "inventory":
    json.dump(
        {
            "schema_version": 1,
            "run_id": invocation["run_id"],
            "subject_sha256": invocation["subject_sha256"],
            "harness_sha256": invocation["harness_sha256"],
            "captured_at": now(),
            "feature_ids": [],
        },
        sys.stdout,
        separators=(",", ":"),
    )
    raise SystemExit(0)

if invocation.get("operation") != "observe":
    fail("unsupported probe operation")
try:
    execution = json.loads(Path("reference-execution.json").read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as error:
    fail(f"execution evidence is unavailable: {error}")
adapter_invocation = execution.get("invocation")
result = execution.get("result")
if not isinstance(adapter_invocation, dict) or not isinstance(result, dict):
    fail("execution evidence is malformed")
if (
    adapter_invocation.get("run_id") != invocation.get("run_id")
    or adapter_invocation.get("vector_id") != invocation.get("vector_id")
):
    fail("execution evidence binding is stale")
subject = adapter_invocation.get("subject")
case = adapter_invocation.get("case")
if not isinstance(subject, dict) or not isinstance(case, dict):
    fail("subject execution binding is absent")

counterpart_digests = []
matched = []
for requirement in case.get("required_counterparts", []):
    candidates = [
        item
        for item in subject.get("counterparts", [])
        if item.get("kind") == "implementation"
        and item.get("profile_id") == requirement.get("profile_id")
        and item.get("producer_role") == requirement.get("producer_role")
        and item.get("boundary_id") != subject.get("boundary_id")
        and item.get("artifact_sha256")
        != subject.get("implementation", {}).get("artifact_sha256")
        and item not in matched
    ]
    if len(candidates) != 1:
        fail("required counterpart is not exact")
    matched.append(candidates[0])
    counterpart_digests.append(
        domain_digest("ASP-CONFORMANCE-COUNTERPART-V1", candidates[0])
    )

observation = {
    "schema_version": 1,
    "run_id": invocation["run_id"],
    "subject_sha256": invocation["subject_sha256"],
    "harness_sha256": invocation["harness_sha256"],
    "counterpart_sha256s": counterpart_digests,
    "observation_id": f"obs-reference-{invocation['vector_id']}",
    "vector_id": invocation["vector_id"],
    "step_id": "final",
    "tokens": result["tokens"],
    "state_deltas": result["state_deltas"],
    "captured_at": now(),
    "sanitization": "synthetic_or_redacted",
}
for member in ("asp_error", "policy_reason", "match_reason"):
    if member in result:
        observation[member] = result[member]
json.dump(observation, sys.stdout, ensure_ascii=False, separators=(",", ":"))
