"""Shared build topology for the independent reference vertical slice."""

from __future__ import annotations


APPLICATION_PARTICIPANT_BINARIES = {
    "reference-app-control": "asp-reference-app-control",
    "reference-app-executor": "asp-reference-app-executor",
    "reference-app-receipt": "asp-reference-app-receipt",
}
APPLICATION_SERVER_BINARY = "asp-reference-app-server"
APPLICATION_BINARIES = frozenset(
    {
        *APPLICATION_PARTICIPANT_BINARIES.values(),
        APPLICATION_SERVER_BINARY,
    }
)
BUILD_CONFIG_NAME = "asp-reference-build.json"
