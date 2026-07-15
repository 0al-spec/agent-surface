#!/usr/bin/env python3
"""Canonical authoritative conformance probe for the mock participants."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from .behavior import BehaviorError, family_for
    from .participant import ParticipantError, inventory, load_request, observe
    from .state import StateError
except ImportError:  # direct executable
    from behavior import BehaviorError, family_for
    from participant import ParticipantError, inventory, load_request, observe
    from state import StateError


def main() -> int:
    try:
        request = load_request(sys.stdin)
        locator = request.get("subject_locator", {})
        family = family_for(locator.get("profile_id"), locator.get("producer_role"))
        if request.get("operation") == "inventory":
            response = inventory(family, request)
        elif request.get("operation") == "observe":
            response = observe(family, request, Path.cwd())
        else:
            raise ParticipantError("unknown probe operation")
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
