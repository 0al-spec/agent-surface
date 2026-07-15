#!/usr/bin/env python3
"""Report one selected feature to exercise inventory mismatch detection."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone


invocation = json.load(sys.stdin)
json.dump(
    {
        "schema_version": 1,
        "run_id": invocation["run_id"],
        "subject_sha256": invocation["subject_sha256"],
        "harness_sha256": invocation["harness_sha256"],
        "captured_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "feature_ids": ["agent-surface/feature/proposal-only"],
    },
    sys.stdout,
    separators=(",", ":"),
)
