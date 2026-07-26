#!/usr/bin/env python3
"""Stimulus adapter for the independently executable reference participants."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


BUILD_CONFIG_NAME = "asp-reference-build.json"
APP_PARTICIPANTS = {
    "reference-app-control",
    "reference-app-executor",
    "reference-app-receipt",
}


def fail(message: str) -> "None":
    print(message, file=sys.stderr)
    raise SystemExit(2)


def load_build_config() -> tuple[Path, dict[str, Path]]:
    path = Path(__file__).with_name(BUILD_CONFIG_NAME)
    if not path.is_file() or path.is_symlink():
        fail("run-scoped build configuration is unavailable")

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for name, value in pairs:
            if name in result:
                fail(f"duplicate build configuration member: {name}")
            result[name] = value
        return result

    try:
        config = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        fail("run-scoped build configuration is invalid")
    if (
        not isinstance(config, dict)
        or set(config) != {"schema_version", "repository_root", "entrypoints"}
        or config.get("schema_version") != 1
        or not isinstance(config.get("repository_root"), str)
        or not isinstance(config.get("entrypoints"), dict)
        or set(config["entrypoints"]) != APP_PARTICIPANTS
    ):
        fail("run-scoped build configuration has the wrong shape")
    try:
        root = Path(config["repository_root"]).resolve(strict=True)
    except OSError:
        fail("run-scoped repository root is unavailable")
    if not root.is_dir():
        fail("run-scoped repository root is invalid")
    entrypoints: dict[str, Path] = {}
    for participant_id, raw_entrypoint in config["entrypoints"].items():
        if not isinstance(raw_entrypoint, str):
            fail("run-scoped application entry point is invalid")
        candidate = Path(raw_entrypoint)
        if not candidate.is_absolute() or candidate.is_symlink():
            fail("run-scoped application entry point is invalid")
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            fail("run-scoped application entry point is unavailable")
        if not resolved.is_file() or not os.access(resolved, os.X_OK):
            fail("run-scoped application entry point is unavailable")
        entrypoints[participant_id] = resolved
    return root, entrypoints


ROOT, APP_ENTRYPOINTS = load_build_config()

ENTRYPOINTS = {
    **APP_ENTRYPOINTS,
    "reference-runtime-local": ROOT / "reference" / "vertical-slice" / "runtime_local.py",
    "reference-runtime-remote": ROOT / "reference" / "vertical-slice" / "runtime_remote.py",
    "reference-agent-a": ROOT / "reference" / "vertical-slice" / "agent_a.py",
    "reference-agent-b": ROOT / "reference" / "vertical-slice" / "agent_b.py",
}
ALLOWED_PROFILES = {
    "reference-app-control": {
        "https://github.com/0al-spec/agent-surface/conformance/surface-publisher/v1",
        "https://github.com/0al-spec/agent-surface/conformance/grant-issuer/v1",
    },
    "reference-app-executor": {
        "https://github.com/0al-spec/agent-surface/conformance/action-executor/v1"
    },
    "reference-app-receipt": {
        "https://github.com/0al-spec/agent-surface/conformance/receipt-producer/v1"
    },
    "reference-runtime-local": {
        "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1"
    },
    "reference-runtime-remote": {
        "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1"
    },
    "reference-agent-a": {
        "https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1"
    },
    "reference-agent-b": {
        "https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1"
    },
}


def load_object(stream) -> dict:
    try:
        value = json.load(stream)
    except (UnicodeError, json.JSONDecodeError) as error:
        fail(f"invalid JSON: {error}")
    if not isinstance(value, dict):
        fail("input must be a JSON object")
    return value


invocation = load_object(sys.stdin)
if invocation.get("adapter_protocol") != "asp-conformance-adapter/1":
    fail("unsupported adapter protocol")
subject = invocation.get("subject")
case = invocation.get("case")
if not isinstance(subject, dict) or not isinstance(case, dict):
    fail("subject and case are required")
subject_id = subject.get("subject_id")
profile_id = subject.get("profile_id")
if subject_id not in ENTRYPOINTS or profile_id not in ALLOWED_PROFILES[subject_id]:
    fail("subject is not bound to an allowed reference entry point")
entrypoint = ENTRYPOINTS[subject_id]
if not entrypoint.is_file():
    fail(f"subject entry point is unavailable: {entrypoint}")

stimulus = case.get("stimulus")
fixture = stimulus.get("fixture") if isinstance(stimulus, dict) else None
if (
    not isinstance(stimulus, dict)
    or not isinstance(fixture, dict)
    or "operation" not in stimulus
    or "document" not in fixture
):
    fail("case stimulus is incomplete")
normalized_case = {
    "profile_id": case["profile_id"],
    "initial_state": case["initial_state"],
    "stimulus": {
        "operation": stimulus["operation"],
        "fixture": {"document": fixture["document"]},
    },
}
if "producer_role" in case:
    normalized_case["producer_role"] = case["producer_role"]
payload = {
    "subject_protocol": "asp-reference-subject/1",
    "case": normalized_case,
}
completed = subprocess.run(
    [str(entrypoint)],
    input=json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ),
    text=True,
    capture_output=True,
    timeout=8,
    cwd=Path.cwd(),
    check=False,
)
if completed.returncode != 0:
    fail("subject execution failed")
try:
    result = json.loads(completed.stdout)
except json.JSONDecodeError:
    fail("subject returned invalid JSON")
if not isinstance(result, dict):
    fail("subject result must be an object")
required = {"schema_version", "decision", "tokens", "state_deltas"}
optional = {"asp_error", "policy_reason", "match_reason"}
if set(result) - required - optional or not required.issubset(result):
    fail("subject result is not the closed shape")
if (
    result["schema_version"] != 1
    or not isinstance(result["decision"], str)
    or not isinstance(result["tokens"], list)
    or len(result["tokens"]) != len(set(result["tokens"]))
    or not all(isinstance(item, str) for item in result["tokens"])
    or not isinstance(result["state_deltas"], list)
):
    fail("subject result members are invalid")

Path("reference-execution.json").write_text(
    json.dumps(
        {"invocation": invocation, "result": result},
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ),
    encoding="utf-8",
)
json.dump(
    {
        "schema_version": 1,
        "run_id": invocation["run_id"],
        "vector_id": invocation["vector_id"],
        "status": "completed",
    },
    sys.stdout,
    separators=(",", ":"),
)
