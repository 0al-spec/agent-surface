"""Shared Cargo output paths for the independent reference vertical slice."""

from __future__ import annotations

import os
from pathlib import Path


APPLICATION_TARGET_RELATIVE = Path("target/asp-reference-vertical-slice")
APPLICATION_BINARIES = frozenset(
    {
        "asp-reference-app-control",
        "asp-reference-app-executor",
        "asp-reference-app-receipt",
        "asp-reference-app-server",
    }
)


def application_target_dir(root: Path) -> Path:
    """Return the dedicated Cargo target directory forced by the evidence build."""

    return root.resolve() / APPLICATION_TARGET_RELATIVE


def application_binary(root: Path, name: str) -> Path:
    """Return one allowlisted application executable under the forced target."""

    if name not in APPLICATION_BINARIES:
        raise ValueError(f"unknown reference application binary: {name}")
    suffix = ".exe" if os.name == "nt" else ""
    return application_target_dir(root) / "debug" / f"{name}{suffix}"
