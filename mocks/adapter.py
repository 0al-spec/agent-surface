#!/usr/bin/env python3
"""Canonical ASP conformance stimulus adapter for the mock participants."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from .behavior import BehaviorError, family_for
    from .participant import ParticipantError, execute, load_request
    from .state import StateError
except ImportError:  # direct executable
    from behavior import BehaviorError, family_for
    from participant import ParticipantError, execute, load_request
    from state import StateError


def main() -> int:
    try:
        request = load_request(sys.stdin)
        subject = request.get("subject", {})
        family = family_for(subject.get("profile_id"), subject.get("producer_role"))
        response = execute(family, request, Path.cwd())
        import json

        json.dump(response, sys.stdout, ensure_ascii=False, separators=(",", ":"))
        return 0
    except (
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        OSError,
        BehaviorError,
        ParticipantError,
        StateError,
    ):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
