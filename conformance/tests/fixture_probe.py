#!/usr/bin/env python3
"""Oracle-backed runner self-test probe; its subject is always suite_fixture."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def domain_digest(domain: str, value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(domain.encode("ascii") + b"\0" + encoded).digest()
    return "sha-256:" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


invocation = json.load(sys.stdin)
if invocation.get("probe_protocol") != "asp-conformance-probe/1":
    raise SystemExit(2)
suite = json.loads(
    (ROOT / "conformance" / "v1" / "suite.json").read_text(encoding="utf-8")
)
if invocation["operation"] == "inventory":
    requirements = {
        item["requirement_id"]: item for item in suite["requirements"]
    }
    profile_id = invocation["subject_locator"]["profile_id"]
    feature_ids = sorted(
        feature["feature_id"]
        for feature in suite["features"]
        if any(
            requirements[requirement_id]["profile_id"] == profile_id
            for requirement_id in feature["requirement_ids"]
        )
    )
    json.dump(
        {
            "schema_version": 1,
            "run_id": invocation["run_id"],
            "subject_sha256": invocation["subject_sha256"],
            "harness_sha256": invocation["harness_sha256"],
            "captured_at": now(),
            "feature_ids": feature_ids,
        },
        sys.stdout,
        separators=(",", ":"),
    )
    raise SystemExit(0)

executed = json.loads(Path("executed-case.json").read_text(encoding="utf-8"))
if executed["vector_id"] != invocation["vector_id"]:
    raise SystemExit(3)
catalog = json.loads(
    (ROOT / "conformance" / "v1" / "vectors.json").read_text(encoding="utf-8")
)
vector = next(
    item for item in catalog["vectors"] if item["vector_id"] == invocation["vector_id"]
)
subject = executed["subject"]
counterpart_digests = []
for required in vector.get("required_counterparts", []):
    matches = [
        item
        for item in subject["counterparts"]
        if item["kind"] == "implementation"
        and item["profile_id"] == required["profile_id"]
        and item.get("producer_role") == required.get("producer_role")
        and item["boundary_id"] != subject["boundary_id"]
        and item["artifact_sha256"] != subject["implementation"]["artifact_sha256"]
    ]
    if len(matches) != 1:
        raise SystemExit(4)
    counterpart_digests.append(
        domain_digest("ASP-CONFORMANCE-COUNTERPART-V1", matches[0])
    )
observation = {
    "schema_version": 1,
    "run_id": invocation["run_id"],
    "subject_sha256": invocation["subject_sha256"],
    "harness_sha256": invocation["harness_sha256"],
    "counterpart_sha256s": counterpart_digests,
    "observation_id": f"obs-{vector['vector_id']}",
    "vector_id": vector["vector_id"],
    "step_id": "final",
    "tokens": vector["required_observations"],
    "state_deltas": vector["state_deltas"],
    "captured_at": now(),
    "sanitization": "synthetic_or_redacted",
}
for expected_name, observed_name in (
    ("expected_error", "asp_error"),
    ("expected_policy_reason", "policy_reason"),
    ("expected_match_reason", "match_reason"),
):
    if expected_name in vector:
        observation[observed_name] = vector[expected_name]
json.dump(observation, sys.stdout, separators=(",", ":"))
