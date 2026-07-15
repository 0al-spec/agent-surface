#!/usr/bin/env python3
"""Return valid inventory and oversized vector output for resource-limit tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


invocation = json.loads(sys.stdin.buffer.read())
if invocation.get("operation") == "inventory":
    completed = subprocess.run(
        [str(Path(__file__).with_name("fixture_probe.py"))],
        input=json.dumps(invocation).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    sys.stdout.buffer.write(completed.stdout)
    raise SystemExit(completed.returncode)
sys.stdout.buffer.write(b"x" * (1024 * 1024 + 1))
