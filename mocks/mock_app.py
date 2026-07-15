#!/usr/bin/env python3
"""Executable Mock App participant family."""

try:
    from .participant import main_for_family
except ImportError:  # direct executable
    from participant import main_for_family


if __name__ == "__main__":
    raise SystemExit(main_for_family("app"))
