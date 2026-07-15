#!/usr/bin/env python3
"""Return one schema-valid but contradictory observation for runner tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


fixture_probe = Path(__file__).with_name("fixture_probe.py")
completed = subprocess.run(
    [str(fixture_probe)],
    input=sys.stdin.buffer.read(),
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    check=False,
)
if completed.returncode != 0:
    raise SystemExit(completed.returncode)
response = json.loads(completed.stdout)
if "state_deltas" in response:
    delta = response["state_deltas"][0]
    delta["after"] = delta["before"]
json.dump(response, sys.stdout, separators=(",", ":"))
