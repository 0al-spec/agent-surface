#!/usr/bin/env python3
"""Run the two-lane task/comment reference scenario over real process boundaries."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import selectors
import secrets
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

MAX_LINE = 1_048_576


class SliceError(ValueError):
    """Raised when the executable scenario violates its closed expectations."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def domain_digest(domain: str, content: bytes) -> str:
    digest = hashlib.sha256(domain.encode("ascii") + b"\0" + content).digest()
    return "sha-256:" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def exchange(address: str, request: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
    if ":" not in address:
        raise SliceError(f"invalid scenario address: {address}")
    host, raw_port = address.rsplit(":", 1)
    payload = json.dumps(
        request,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    try:
        with socket.create_connection((host, int(raw_port)), timeout=timeout) as connection:
            connection.settimeout(timeout)
            connection.sendall(payload)
            line = connection.makefile("rb").readline(MAX_LINE + 1)
    except (OSError, ValueError) as error:
        raise SliceError(f"scenario exchange failed: {error}") from error
    if not line or len(line) > MAX_LINE or not line.endswith(b"\n"):
        raise SliceError("scenario participant returned no bounded JSON line")
    try:
        value = json.loads(line)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SliceError("scenario participant returned invalid JSON") from error
    if not isinstance(value, dict):
        raise SliceError("scenario response must be an object")
    return value


def wait_file(path: Path, process: subprocess.Popen, timeout: float = 5.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr is not None else ""
            raise SliceError(f"scenario process exited before readiness: {stderr.strip()}")
        time.sleep(0.02)
    raise SliceError(f"scenario process did not publish readiness: {path}")


def wait_stdout_json(process: subprocess.Popen, timeout: float = 5.0) -> dict[str, Any]:
    if process.stdout is None:
        raise SliceError("scenario runtime stdout is unavailable")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        events = selector.select(timeout)
    finally:
        selector.close()
    if not events:
        raise SliceError("scenario runtime did not publish a listening record")
    line = process.stdout.readline()
    try:
        value = json.loads(line)
    except json.JSONDecodeError as error:
        raise SliceError("scenario runtime readiness is invalid JSON") from error
    if not isinstance(value, dict) or value.get("status") != "listening":
        raise SliceError("scenario runtime did not enter the listening state")
    return value


def private_config(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    path.chmod(0o600)


def private_secret(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8")
    path.chmod(0o600)


def run_agent(
    script: Path, arguments: list[str], *, session_proof: str
) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["ASP_REFERENCE_AGENT_SESSION_PROOF"] = session_proof
    completed = subprocess.run(
        [str(script), *arguments],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        raise SliceError(
            f"agent {script.name} failed: {completed.stderr.strip() or completed.stdout.strip()}"
        )
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SliceError(f"agent {script.name} returned invalid JSON") from error
    if (
        not isinstance(output, dict)
        or output.get("protocol") != "asp-reference-agent-scenario/1"
        or output.get("status") != "completed"
    ):
        raise SliceError(f"agent {script.name} returned an invalid scenario report")
    return output


def step(agent_output: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [
        item
        for item in agent_output.get("steps", [])
        if isinstance(item, dict) and item.get("name") == name
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("response"), dict):
        raise SliceError(f"scenario step {name!r} is missing or duplicated")
    return matches[0]["response"]


def app_envelope(runtime_response: dict[str, Any]) -> dict[str, Any]:
    if (
        runtime_response.get("protocol") != "asp-reference-runtime/1"
        or runtime_response.get("status") != "completed"
        or runtime_response.get("forwarded") is not True
        or not isinstance(runtime_response.get("result"), dict)
    ):
        raise SliceError("runtime did not return a completed forwarded application result")
    return runtime_response["result"]


def require_app_success(runtime_response: dict[str, Any]) -> dict[str, Any]:
    envelope = app_envelope(runtime_response)
    if envelope.get("ok") is not True or not isinstance(envelope.get("result"), dict):
        raise SliceError("application did not return a successful result")
    return envelope["result"]


def require_app_error(runtime_response: dict[str, Any], code: str) -> None:
    envelope = app_envelope(runtime_response)
    if envelope != {"schema_version": 1, "ok": False, "error": code}:
        raise SliceError(f"application error differs from {code}")


def require_runtime_rejection(runtime_response: dict[str, Any], code: str) -> None:
    if (
        runtime_response.get("protocol") != "asp-reference-runtime/1"
        or runtime_response.get("status") != "rejected"
        or runtime_response.get("forwarded") is not False
        or runtime_response.get("error", {}).get("code") != code
    ):
        raise SliceError(f"runtime rejection differs from {code}")


def terminate(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


def run_scenario(root: Path) -> dict[str, Any]:
    app_binary = root / "target" / "debug" / "asp-reference-app-server"
    local_runtime = root / "reference" / "vertical-slice" / "runtime_local.py"
    remote_runtime = root / "reference" / "vertical-slice" / "runtime_remote.py"
    agent_a = root / "reference" / "vertical-slice" / "agent_a.py"
    agent_b = root / "reference" / "vertical-slice" / "agent_b.py"
    for path in (app_binary, local_runtime, remote_runtime, agent_a, agent_b):
        if not path.is_file() or not os.access(path, os.X_OK):
            raise SliceError(f"scenario executable is unavailable: {path}")

    processes: list[subprocess.Popen] = []
    with tempfile.TemporaryDirectory(prefix="asp-reference-scenario-") as directory:
        work = Path(directory)
        app_ready = work / "app.ready"
        app_state = work / "app-state.json"
        control_secret_file = work / "app-control-secret"
        control_credential = secrets.token_urlsafe(32)
        private_secret(control_secret_file, control_credential)
        app = subprocess.Popen(
            [
                str(app_binary),
                "--listen",
                "127.0.0.1:0",
                "--ready-file",
                str(app_ready),
                "--state-file",
                str(app_state),
                "--control-secret-file",
                str(control_secret_file),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        processes.append(app)
        try:
            app_address = wait_file(app_ready, app)
            manifest_response = exchange(app_address, {"operation": "manifest"})
            if (
                manifest_response.get("ok") is not True
                or manifest_response.get("result", {}).get("boundary_id")
                != "reference/application"
            ):
                raise SliceError("reference application did not publish its task surface")

            unauthorized_control = exchange(
                app_address,
                {
                    "operation": "issue_grant",
                    "runtime_id": "reference/runtime/unauthorized",
                    "agent_id": "agent-unauthorized",
                    "actions": ["comment.create"],
                },
            )
            if unauthorized_control != {
                "schema_version": 1,
                "ok": False,
                "error": "control_unauthorized",
            }:
                raise SliceError("application control plane did not fail closed")

            grants: dict[str, dict[str, Any]] = {}
            for lane, runtime_id, agent_id in (
                ("local", "reference/runtime/local", "agent-a"),
                ("remote", "reference/runtime/remote", "agent-b"),
            ):
                response = exchange(
                    app_address,
                    {
                        "operation": "issue_grant",
                        "control_credential": control_credential,
                        "runtime_id": runtime_id,
                        "agent_id": agent_id,
                        "actions": ["task.read", "comment.create"],
                    },
                )
                if response.get("ok") is not True or not isinstance(
                    response.get("result"), dict
                ):
                    raise SliceError(f"cannot issue {lane} scenario Grant")
                grants[lane] = response["result"]

            runtime_processes: dict[str, subprocess.Popen] = {}
            runtime_addresses: dict[str, str] = {}
            agent_session_proofs = {
                "local": secrets.token_urlsafe(32),
                "remote": secrets.token_urlsafe(32),
            }
            for lane, script, runtime_id in (
                ("local", local_runtime, "reference/runtime/local"),
                ("remote", remote_runtime, "reference/runtime/remote"),
            ):
                config_path = work / f"{lane}-runtime-private.json"
                private_config(
                    config_path,
                    {
                        "app_address": app_address,
                        "runtime_id": runtime_id,
                        "agent_id": "agent-a" if lane == "local" else "agent-b",
                        "agent_session_proof": agent_session_proofs[lane],
                        "grant_id": grants[lane]["grant_id"],
                        "credential": grants[lane]["credential"],
                    },
                )
                process = subprocess.Popen(
                    [
                        str(script),
                        "serve",
                        "--config",
                        str(config_path),
                        "--listen",
                        "127.0.0.1:0",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                processes.append(process)
                runtime_processes[lane] = process
                listening = wait_stdout_json(process)
                runtime_addresses[lane] = listening["address"]

            if len({process.pid for process in processes}) != len(processes):
                raise SliceError("scenario participants did not use distinct process boundaries")

            agent_a_output = run_agent(
                agent_a,
                ["scenario", "--runtime", runtime_addresses["local"]],
                session_proof=agent_session_proofs["local"],
            )
            agent_b_output = run_agent(
                agent_b,
                ["scenario", "--runtime", runtime_addresses["remote"]],
                session_proof=agent_session_proofs["remote"],
            )

            a_created = require_app_success(step(agent_a_output, "create"))
            a_replayed = require_app_success(step(agent_a_output, "exact_replay"))
            if a_created != a_replayed:
                raise SliceError(
                    "Agent A replay did not preserve the immutable result and receipt"
                )
            injected = step(agent_a_output, "credential_injection_negative")
            if (
                injected.get("status") != "rejected"
                or injected.get("forwarded") is not False
                or injected.get("error", {}).get("code") != "credential_exposed"
            ):
                raise SliceError("Agent A credential injection was not fenced pre-dispatch")
            require_runtime_rejection(
                step(agent_a_output, "session_proof_injection_negative"),
                "request_invalid",
            )

            b_created = require_app_success(step(agent_b_output, "create"))
            require_app_error(
                step(agent_b_output, "changed_input_idempotency_conflict"),
                "idempotency_conflict",
            )
            agent_b_impersonation = run_agent(
                agent_b,
                [
                    "one-request",
                    "--runtime",
                    runtime_addresses["remote"],
                    "--request-id",
                    "agent-b-impersonation-request",
                    "--idempotency-key",
                    "idem-agent-b-impersonation",
                ],
                session_proof=secrets.token_urlsafe(32),
            )
            require_runtime_rejection(
                step(agent_b_impersonation, "one_request"), "request_invalid"
            )
            agent_b_substitution = run_agent(
                agent_b,
                [
                    "one-request",
                    "--runtime",
                    runtime_addresses["remote"],
                    "--agent-id",
                    "agent-a",
                    "--request-id",
                    "agent-b-substitution-request",
                    "--idempotency-key",
                    "idem-agent-b-substitution",
                ],
                session_proof=agent_session_proofs["remote"],
            )
            require_runtime_rejection(
                step(agent_b_substitution, "one_request"), "request_invalid"
            )
            app_delegate_substitution = exchange(
                app_address,
                {
                    "operation": "invoke",
                    "protocol": "asp-reference-app/1",
                    "request_id": "direct-delegate-substitution",
                    "execution_id": "execution-direct-delegate-substitution",
                    "runtime_id": "reference/runtime/remote",
                    "agent_id": "agent-a",
                    "grant_id": grants["remote"]["grant_id"],
                    "credential": grants["remote"]["credential"],
                    "action_id": "comment.create",
                    "idempotency_key": "idem-direct-delegate-substitution",
                    "input": {"task_id": "task-1", "text": "substitution"},
                },
            )
            if app_delegate_substitution != {
                "schema_version": 1,
                "ok": False,
                "error": "grant_delegate_invalid",
            }:
                raise SliceError("application did not reject delegate substitution")
            overparameterized_input = exchange(
                app_address,
                {
                    "operation": "invoke",
                    "protocol": "asp-reference-app/1",
                    "request_id": "direct-overparameterized-input",
                    "execution_id": "execution-direct-overparameterized-input",
                    "runtime_id": "reference/runtime/remote",
                    "agent_id": "agent-b",
                    "grant_id": grants["remote"]["grant_id"],
                    "credential": grants["remote"]["credential"],
                    "action_id": "comment.create",
                    "idempotency_key": "idem-direct-overparameterized-input",
                    "input": {
                        "task_id": "task-1",
                        "text": "overparameterized",
                        "admin": True,
                    },
                },
            )
            if overparameterized_input != {
                "schema_version": 1,
                "ok": False,
                "error": "input_schema_invalid",
            }:
                raise SliceError("application accepted overparameterized input")
            revoked = exchange(
                app_address,
                {
                    "operation": "revoke",
                    "control_credential": control_credential,
                    "grant_id": grants["remote"]["grant_id"],
                },
            )
            if revoked.get("result", {}).get("revocation_fence") != "established":
                raise SliceError("remote Grant revocation did not establish a fence")
            agent_b_revoked = run_agent(
                agent_b,
                ["one-request", "--runtime", runtime_addresses["remote"]],
                session_proof=agent_session_proofs["remote"],
            )
            require_app_error(step(agent_b_revoked, "one_request"), "grant_revoked")

            state_response = exchange(
                app_address,
                {
                    "operation": "state",
                    "control_credential": control_credential,
                },
            )
            state = state_response.get("result")
            if not isinstance(state, dict):
                raise SliceError("application state report is unavailable")
            if state.get("effect_count") != 2 or state.get("receipt_count") != 2:
                raise SliceError("negative paths or replay repeated an application effect")
            if len(state.get("comments", [])) != 2 or len(state.get("receipts", [])) != 2:
                raise SliceError("application evidence counts are internally inconsistent")

            transcript = {
                "manifest": manifest_response,
                "agent_a": agent_a_output,
                "agent_b": agent_b_output,
                "agent_b_impersonation": agent_b_impersonation,
                "agent_b_substitution": agent_b_substitution,
                "app_delegate_substitution": app_delegate_substitution,
                "overparameterized_input": overparameterized_input,
                "agent_b_revoked": agent_b_revoked,
                "unauthorized_control": unauthorized_control,
                "revocation": revoked,
                "state": state_response,
            }
            encoded_transcript = canonical_bytes(transcript)
            for grant in grants.values():
                if grant["credential"].encode("utf-8") in encoded_transcript:
                    raise SliceError("private Grant Credential leaked into retained evidence")
            if control_credential.encode("utf-8") in encoded_transcript:
                raise SliceError("private control credential leaked into retained evidence")
            for session_proof in agent_session_proofs.values():
                if session_proof.encode("utf-8") in encoded_transcript:
                    raise SliceError("runtime-scoped agent session proof leaked into evidence")

            exchange(
                app_address,
                {
                    "operation": "shutdown",
                    "control_credential": control_credential,
                },
            )
            app.wait(timeout=3)
            report = {
                "schema_version": 1,
                "scenario_id": "card-74-task-comments",
                "verdict": "pass",
                "transport": "tcp-json-lines",
                "lanes": [
                    {
                        "lane_id": "local",
                        "runtime_participant_id": "reference-runtime-local",
                        "agent_participant_id": "reference-agent-a",
                        "positive": ["comment_create", "exact_idempotent_replay"],
                        "negative": [
                            "agent_credential_injection",
                            "session_proof_content_injection",
                        ],
                    },
                    {
                        "lane_id": "remote",
                        "runtime_participant_id": "reference-runtime-remote",
                        "agent_participant_id": "reference-agent-b",
                        "positive": ["comment_create", "grant_revocation_fence"],
                        "negative": [
                            "changed_input_idempotency_conflict",
                            "runtime_session_impersonation_rejected",
                            "runtime_agent_substitution_rejected",
                            "application_delegate_substitution_rejected",
                            "overparameterized_input_rejected",
                            "revoked_grant_rejected",
                        ],
                    },
                ],
                "effect_count": state["effect_count"],
                "receipt_count": state["receipt_count"],
                "credentials_exposed": False,
                "transcript_sha256": domain_digest(
                    "ASP-REFERENCE-SCENARIO-TRANSCRIPT-V1", encoded_transcript
                ),
            }
            return report
        finally:
            for process in reversed(processes):
                terminate(process)
