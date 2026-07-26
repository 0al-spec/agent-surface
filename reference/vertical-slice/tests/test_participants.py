"""Tests for the independent executable vertical-slice participants."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Callable


SLICE = Path(__file__).resolve().parents[1]
RUNTIMES = [SLICE / "runtime_local.py", SLICE / "runtime_remote.py"]
AGENTS = [SLICE / "agent_a.py", SLICE / "agent_b.py"]
RUNTIME_PROFILE = (
    "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1"
)
ADAPTER_PROFILE = (
    "https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1"
)
SUBJECT_PROTOCOL = "asp-reference-subject/1"
AGENT_PROTOCOL = "asp-reference-agent/1"
RUNTIME_PROTOCOL = "asp-reference-runtime/1"
AGENT_SESSION_PROOF = "test-agent-session-proof-at-least-32-bytes"


def base_document() -> dict[str, Any]:
    """Return the bounded semantic inputs needed by both core profiles."""

    return {
        "grant": {
            "status": "active",
            "issuer": "issuer-a",
            "claimed_issuer": "issuer-a",
            "requested_actions": ["comment.create"],
            "issued_actions": ["comment.create"],
            "companion_closure": "closed",
            "revocation_state": "active",
        },
        "execution": {
            "input_hash": "input-a",
            "recorded_input_hash": "input-a",
            "input_schema_hash": "schema-a",
            "recorded_input_schema_hash": "schema-a",
            "normalization": "fixed_point",
            "policy": "allow",
            "outcome_state": "known",
            "retry_key": "same",
        },
        "receipt": {
            "origin": "observed",
        },
        "runtime": {
            "returned_grant_width": "equal",
            "credential_release": "none",
            "revocation_state": "current",
            "remote_path": "known",
            "training_policy": "exact",
            "capability_match": "current",
        },
        "adapter": {
            "credential_input": "none",
            "action_authority": "exact",
            "receipt_evidence": "observed",
            "unknown_outcome_handling": "stop",
        },
    }


def subject_envelope(
    *,
    profile: str,
    operation: str,
    initial_state: list[tuple[str, Any]],
    document: dict[str, Any],
) -> dict[str, Any]:
    return {
        "subject_protocol": SUBJECT_PROTOCOL,
        "case": {
            "profile_id": profile,
            "initial_state": [
                {"state": name, "value": value} for name, value in initial_state
            ],
            "stimulus": {
                "operation": operation,
                "fixture": {"document": document},
            },
        },
    }


def deltas(initial: list[tuple[str, Any]], changed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "state": name,
            "before": before,
            "after": changed.get(name, before),
        }
        for name, before in initial
    ]


def invoke_json(
    program: Path,
    args: list[str],
    value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["ASP_REFERENCE_AGENT_SESSION_PROOF"] = AGENT_SESSION_PROOF
    completed = subprocess.run(
        [str(program), *args],
        env=environment,
        input=(
            None
            if value is None
            else json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        ),
        text=True,
        capture_output=True,
        timeout=8,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"{program.name} exited {completed.returncode}: {completed.stderr!r}"
        )
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(
            f"{program.name} returned invalid JSON: {completed.stdout!r}"
        ) from error
    if not isinstance(output, dict):
        raise AssertionError(f"{program.name} did not return a JSON object")
    return output


class SemanticSubjectTests(unittest.TestCase):
    def test_runtime_mediator_core_vectors(self) -> None:
        cases: list[
            tuple[
                str,
                str,
                Callable[[dict[str, Any]], None],
                list[tuple[str, Any]],
                dict[str, Any],
            ]
        ] = []

        cases.append(
            (
                "ASP-V-RM-001",
                "mediate_action",
                lambda _: None,
                [
                    ("action.dispatch_count", 0),
                    ("runtime.stored_grant_width", 0),
                ],
                {
                    "schema_version": 1,
                    "decision": "accepted",
                    "tokens": [
                        "typed_request_forwarded",
                        "action_accepted",
                        "tuple_checked",
                    ],
                    "changed": {
                        "action.dispatch_count": 1,
                        "runtime.stored_grant_width": 1,
                    },
                },
            )
        )
        cases.append(
            (
                "ASP-V-RM-002",
                "mediate_grant",
                lambda value: value["runtime"].update(
                    returned_grant_width="wider"
                ),
                [
                    ("runtime.stored_grant_width", 0),
                    ("action.dispatch_count", 0),
                ],
                {
                    "schema_version": 1,
                    "decision": "rejected",
                    "tokens": ["grant_rejected", "mediation_stopped"],
                    "asp_error": "integrity_mismatch",
                    "changed": {},
                },
            )
        )
        cases.append(
            (
                "ASP-V-RM-003",
                "mediate_action",
                lambda value: value["runtime"].update(credential_release="raw"),
                [
                    ("runtime.credential_release_count", 0),
                    ("credential.agent_visible_count", 0),
                    ("credential.adapter_retained_count", 0),
                    ("action.dispatch_count", 0),
                ],
                {
                    "schema_version": 1,
                    "decision": "rejected",
                    "tokens": ["local_denial_recorded", "mediation_stopped"],
                    "policy_reason": "local_policy_denied",
                    "changed": {},
                },
            )
        )
        cases.append(
            (
                "ASP-V-RM-004",
                "mediate_action",
                lambda value: value["runtime"].update(revocation_state="unknown"),
                [("grant.lifecycle", "active"), ("action.dispatch_count", 0)],
                {
                    "schema_version": 1,
                    "decision": "stopped",
                    "tokens": ["current_state_checked", "mediation_stopped"],
                    "changed": {"grant.lifecycle": "inactive"},
                },
            )
        )
        cases.append(
            (
                "ASP-V-RM-005",
                "retry_outcome",
                lambda value: value["execution"].update(
                    outcome_state="unknown", retry_key="new"
                ),
                [("runtime.retry_count", 0), ("action.dispatch_count", 1)],
                {
                    "schema_version": 1,
                    "decision": "stopped",
                    "tokens": ["mediation_stopped"],
                    "asp_error": "outcome_unknown",
                    "changed": {},
                },
            )
        )
        cases.append(
            (
                "ASP-V-RM-006",
                "mediate_grant",
                lambda value: value["grant"].update(claimed_issuer="issuer-b"),
                [("runtime.stored_grant_width", 0)],
                {
                    "schema_version": 1,
                    "decision": "rejected",
                    "tokens": [
                        "grant_rejected",
                        "tuple_checked",
                        "mediation_stopped",
                    ],
                    "asp_error": "integrity_mismatch",
                    "changed": {},
                },
            )
        )

        for program in RUNTIMES:
            for vector, operation, mutate, initial, expected in cases:
                with self.subTest(program=program.name, vector=vector):
                    document = base_document()
                    mutate(document)
                    output = invoke_json(
                        program,
                        [],
                        subject_envelope(
                            profile=RUNTIME_PROFILE,
                            operation=operation,
                            initial_state=initial,
                            document=document,
                        ),
                    )
                    changed = expected["changed"]
                    expected_output = {
                        **{
                            name: value
                            for name, value in expected.items()
                            if name != "changed"
                        },
                        "state_deltas": deltas(initial, changed),
                    }
                    self.assertEqual(output, expected_output)

    def test_agent_adapter_core_vectors(self) -> None:
        cases: list[
            tuple[
                str,
                str,
                Callable[[dict[str, Any]], None],
                list[tuple[str, Any]],
                dict[str, Any],
            ]
        ] = []
        cases.append(
            (
                "ASP-V-AA-001",
                "translate_action",
                lambda _: None,
                [
                    ("adapter.forwarded_count", 0),
                    ("adapter.fabricated_evidence_count", 0),
                ],
                {
                    "schema_version": 1,
                    "decision": "accepted",
                    "tokens": ["typed_request_forwarded"],
                    "changed": {"adapter.forwarded_count": 1},
                },
            )
        )
        cases.append(
            (
                "ASP-V-AA-002",
                "translate_action",
                lambda value: value["adapter"].update(credential_input="raw"),
                [
                    ("adapter.forwarded_count", 0),
                    ("credential.agent_visible_count", 0),
                    ("credential.adapter_retained_count", 0),
                ],
                {
                    "schema_version": 1,
                    "decision": "rejected",
                    "tokens": [
                        "adapter_request_rejected",
                        "local_denial_recorded",
                    ],
                    "changed": {},
                },
            )
        )
        cases.append(
            (
                "ASP-V-AA-003",
                "translate_action",
                lambda value: value["adapter"].update(action_authority="stronger"),
                [("adapter.forwarded_count", 0)],
                {
                    "schema_version": 1,
                    "decision": "rejected",
                    "tokens": ["adapter_request_rejected"],
                    "changed": {},
                },
            )
        )
        cases.append(
            (
                "ASP-V-AA-004",
                "translate_action",
                lambda value: (
                    value["adapter"].update(receipt_evidence="fabricated"),
                    value["receipt"].update(origin="fabricated"),
                ),
                [
                    ("adapter.fabricated_evidence_count", 0),
                    ("adapter.forwarded_count", 0),
                ],
                {
                    "schema_version": 1,
                    "decision": "rejected",
                    "tokens": [
                        "adapter_request_rejected",
                        "receipt_rejected",
                    ],
                    "asp_error": "integrity_mismatch",
                    "changed": {},
                },
            )
        )
        cases.append(
            (
                "ASP-V-AA-005",
                "retry_outcome",
                lambda value: (
                    value["execution"].update(outcome_state="unknown"),
                    value["adapter"].update(unknown_outcome_handling="retry"),
                ),
                [("runtime.retry_count", 0), ("adapter.forwarded_count", 0)],
                {
                    "schema_version": 1,
                    "decision": "rejected",
                    "tokens": ["adapter_request_rejected"],
                    "asp_error": "outcome_unknown",
                    "changed": {},
                },
            )
        )

        for program in AGENTS:
            for vector, operation, mutate, initial, expected in cases:
                with self.subTest(program=program.name, vector=vector):
                    document = base_document()
                    mutate(document)
                    output = invoke_json(
                        program,
                        ["subject"],
                        subject_envelope(
                            profile=ADAPTER_PROFILE,
                            operation=operation,
                            initial_state=initial,
                            document=document,
                        ),
                    )
                    changed = expected["changed"]
                    expected_output = {
                        **{
                            name: value
                            for name, value in expected.items()
                            if name != "changed"
                        },
                        "state_deltas": deltas(initial, changed),
                    }
                    self.assertEqual(output, expected_output)


class JsonLineServer:
    """Small deterministic server that captures a bounded number of lines."""

    def __init__(
        self,
        count: int,
        response: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.count = count
        self.response = response
        self.requests: list[dict[str, Any]] = []
        self.error: BaseException | None = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("127.0.0.1", 0))
        self.socket.listen()
        self.socket.settimeout(5)
        host, port = self.socket.getsockname()
        self.address = f"{host}:{port}"
        self.thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> "JsonLineServer":
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.thread.join(timeout=6)
        self.socket.close()
        if self.thread.is_alive():
            raise AssertionError("JSON-lines server did not finish")
        if self.error is not None:
            raise self.error

    def _run(self) -> None:
        try:
            for _ in range(self.count):
                connection, _ = self.socket.accept()
                with connection:
                    connection.settimeout(3)
                    line = connection.makefile("rb").readline(1_048_577)
                    request = json.loads(line)
                    self.requests.append(request)
                    reply = self.response(request)
                    connection.sendall(
                        json.dumps(
                            reply,
                            ensure_ascii=False,
                            allow_nan=False,
                            separators=(",", ":"),
                        ).encode("utf-8")
                        + b"\n"
                    )
        except BaseException as error:  # test-thread handoff
            self.error = error


class RunningRuntime:
    def __init__(
        self,
        program: Path,
        app_address: str,
        *,
        once: bool = True,
        timeout: float = 3,
    ) -> None:
        self.once = once
        self.temp = tempfile.TemporaryDirectory()
        self.config = Path(self.temp.name) / "runtime-private.json"
        self.credential = "application-private-credential"
        self.config.write_text(
            json.dumps(
                {
                    "app_address": app_address,
                    "runtime_id": f"{program.stem}-id",
                    "agent_id": "agent-test",
                    "agent_session_proof": AGENT_SESSION_PROOF,
                    "grant_id": "grant-001",
                    "credential": self.credential,
                },
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        os.chmod(self.config, 0o600)
        arguments = [
            str(program),
            "serve",
            "--config",
            str(self.config),
            "--listen",
            "127.0.0.1:0",
            "--timeout",
            str(timeout),
        ]
        if once:
            arguments.append("--once")
        self.process = subprocess.Popen(
            arguments,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert self.process.stdout is not None
        ready_line = self.process.stdout.readline()
        if not ready_line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise AssertionError(f"runtime did not become ready: {stderr}")
        ready = json.loads(ready_line)
        self.address = ready["address"]

    def __enter__(self) -> "RunningRuntime":
        return self

    def __exit__(self, *exc: object) -> None:
        stderr = ""
        try:
            if not self.once and self.process.poll() is None:
                self.process.terminate()
            self.process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)
            raise AssertionError("runtime did not stop after --once")
        finally:
            self.temp.cleanup()
            if self.process.stderr is not None:
                stderr = self.process.stderr.read()
            if self.process.stdout is not None:
                self.process.stdout.close()
            if self.process.stderr is not None:
                self.process.stderr.close()
        if self.once and self.process.returncode != 0:
            raise AssertionError(
                f"runtime exited {self.process.returncode}: {stderr!r}"
            )


def wire_exchange(address: str, request: dict[str, Any]) -> dict[str, Any]:
    host, port_text = address.rsplit(":", 1)
    with socket.create_connection((host, int(port_text)), timeout=3) as connection:
        connection.settimeout(3)
        connection.sendall(
            json.dumps(request, separators=(",", ":")).encode("utf-8") + b"\n"
        )
        line = connection.makefile("rb").readline(1_048_577)
    return json.loads(line)


def ordinary_request() -> dict[str, Any]:
    return {
        "protocol": AGENT_PROTOCOL,
        "request_id": "request-001",
        "execution_id": "execution-001",
        "agent_id": "agent-test",
        "session_proof": AGENT_SESSION_PROOF,
        "action_id": "comment.create",
        "idempotency_key": "idem-001",
        "input": {"task_id": "task-1", "text": "hello"},
    }


class RuntimeWireTests(unittest.TestCase):
    def test_runtime_rejects_non_terminated_json_line(self) -> None:
        for program in RUNTIMES:
            with self.subTest(program=program.name):
                with RunningRuntime(program, "127.0.0.1:1") as runtime:
                    host, raw_port = runtime.address.rsplit(":", 1)
                    with socket.create_connection(
                        (host, int(raw_port)), timeout=3
                    ) as connection:
                        connection.settimeout(3)
                        connection.sendall(
                            json.dumps(
                                ordinary_request(), separators=(",", ":")
                            ).encode("utf-8")
                        )
                        connection.shutdown(socket.SHUT_WR)
                        line = connection.makefile("rb").readline(1_048_577)
                response = json.loads(line)
                self.assertEqual(response["status"], "rejected")
                self.assertFalse(response["forwarded"])
                self.assertEqual(response["error"]["code"], "request_invalid")

    def test_runtime_adds_private_credential_only_on_application_leg(self) -> None:
        def application_reply(_: dict[str, Any]) -> dict[str, Any]:
            return {
                "protocol": "asp-reference-app-result/1",
                "status": "completed",
                "result": {"comment_id": "comment-001"},
            }

        for program in RUNTIMES:
            with self.subTest(program=program.name):
                with JsonLineServer(1, application_reply) as application:
                    with RunningRuntime(program, application.address) as runtime:
                        response = wire_exchange(runtime.address, ordinary_request())
                        credential = runtime.credential
                self.assertEqual(response["status"], "completed")
                self.assertTrue(response["forwarded"])
                self.assertNotIn(credential, json.dumps(response))
                self.assertNotIn(AGENT_SESSION_PROOF, json.dumps(response))
                self.assertEqual(len(application.requests), 1)
                forwarded = application.requests[0]
                self.assertEqual(forwarded["protocol"], "asp-reference-app/1")
                self.assertEqual(forwarded["execution_id"], "execution-001")
                self.assertEqual(forwarded["credential"], credential)
                self.assertEqual(
                    forwarded["input"], {"task_id": "task-1", "text": "hello"}
                )
                self.assertNotIn("session_proof", forwarded)

    def test_runtime_rejects_agent_credential_before_application_connect(self) -> None:
        for program in RUNTIMES:
            with self.subTest(program=program.name):
                with RunningRuntime(program, "127.0.0.1:1") as runtime:
                    request = ordinary_request()
                    request["credential"] = "agent-supplied"
                    response = wire_exchange(runtime.address, request)
                self.assertEqual(response["status"], "rejected")
                self.assertFalse(response["forwarded"])
                self.assertEqual(response["error"]["code"], "credential_exposed")
                self.assertNotIn("agent-supplied", json.dumps(response))

    def test_runtime_rejects_agent_substitution_before_application_connect(self) -> None:
        for program in RUNTIMES:
            with self.subTest(program=program.name):
                with RunningRuntime(program, "127.0.0.1:1") as runtime:
                    request = ordinary_request()
                    request["agent_id"] = "agent-substituted"
                    response = wire_exchange(runtime.address, request)
                self.assertEqual(response["status"], "rejected")
                self.assertFalse(response["forwarded"])
                self.assertEqual(response["error"]["code"], "request_invalid")

    def test_runtime_rejects_session_impersonation_before_application_connect(self) -> None:
        for program in RUNTIMES:
            with self.subTest(program=program.name):
                with RunningRuntime(program, "127.0.0.1:1") as runtime:
                    request = ordinary_request()
                    request["session_proof"] = "wrong-session-proof-at-least-32-bytes"
                    response = wire_exchange(runtime.address, request)
                self.assertEqual(response["status"], "rejected")
                self.assertFalse(response["forwarded"])
                self.assertEqual(response["error"]["code"], "request_invalid")

    def test_runtime_rejects_session_proof_inside_action_content(self) -> None:
        for program in RUNTIMES:
            with self.subTest(program=program.name):
                with RunningRuntime(program, "127.0.0.1:1") as runtime:
                    request = ordinary_request()
                    request["input"]["text"] = AGENT_SESSION_PROOF
                    response = wire_exchange(runtime.address, request)
                self.assertEqual(response["status"], "rejected")
                self.assertFalse(response["forwarded"])
                self.assertEqual(response["error"]["code"], "request_invalid")

    def test_local_runtime_survives_stalled_client(self) -> None:
        def application_reply(_: dict[str, Any]) -> dict[str, Any]:
            return {"status": "completed"}

        with JsonLineServer(1, application_reply) as application:
            with RunningRuntime(
                RUNTIMES[0],
                application.address,
                once=False,
                timeout=0.1,
            ) as runtime:
                host, raw_port = runtime.address.rsplit(":", 1)
                stalled = socket.create_connection((host, int(raw_port)), timeout=1)
                time.sleep(0.2)
                stalled.close()
                response = wire_exchange(runtime.address, ordinary_request())
                self.assertEqual(response["status"], "completed")
                self.assertTrue(response["forwarded"])


class AgentScenarioTests(unittest.TestCase):
    @staticmethod
    def runtime_reply(request: dict[str, Any]) -> dict[str, Any]:
        return {
            "protocol": RUNTIME_PROTOCOL,
            "request_id": request["request_id"],
            "status": "completed",
            "forwarded": True,
            "result": {"status": "ok"},
        }

    def test_agent_a_create_replay_and_credential_negative(self) -> None:
        with JsonLineServer(4, self.runtime_reply) as runtime:
            output = invoke_json(
                SLICE / "agent_a.py",
                ["scenario", "--runtime", runtime.address],
            )
        self.assertEqual(
            output["scenario"], "agent-a-create-replay-credential-negative"
        )
        self.assertEqual(runtime.requests[0], runtime.requests[1])
        self.assertNotIn("credential", runtime.requests[0])
        self.assertIn("credential", runtime.requests[2])
        self.assertEqual(runtime.requests[3]["input"]["text"], AGENT_SESSION_PROOF)

    def test_agent_b_changed_input_reuses_idempotency_key(self) -> None:
        with JsonLineServer(2, self.runtime_reply) as runtime:
            output = invoke_json(
                SLICE / "agent_b.py",
                ["scenario", "--runtime", runtime.address],
            )
        self.assertEqual(output["scenario"], "agent-b-create-idempotency-conflict")
        self.assertEqual(
            runtime.requests[0]["idempotency_key"],
            runtime.requests[1]["idempotency_key"],
        )
        self.assertNotEqual(
            runtime.requests[0]["input"],
            runtime.requests[1]["input"],
        )
        self.assertNotEqual(
            runtime.requests[0]["request_id"],
            runtime.requests[1]["request_id"],
        )
        self.assertEqual(
            runtime.requests[0]["execution_id"],
            runtime.requests[1]["execution_id"],
        )

    def test_agent_b_one_request_mode_is_exactly_one_request(self) -> None:
        with JsonLineServer(1, self.runtime_reply) as runtime:
            output = invoke_json(
                SLICE / "agent_b.py",
                ["one-request", "--runtime", runtime.address],
            )
        self.assertEqual(output["scenario"], "agent-b-revoked-grant-one-request")
        self.assertEqual([step["name"] for step in output["steps"]], ["one_request"])
        self.assertEqual(len(runtime.requests), 1)

    def test_agents_reject_uncorrelated_runtime_response(self) -> None:
        def uncorrelated_reply(_: dict[str, Any]) -> dict[str, Any]:
            return {
                "protocol": RUNTIME_PROTOCOL,
                "request_id": "substituted-request",
                "status": "completed",
                "forwarded": True,
                "result": {"status": "ok"},
            }

        for program in AGENTS:
            with self.subTest(program=program.name):
                with JsonLineServer(1, uncorrelated_reply) as runtime:
                    environment = dict(os.environ)
                    environment[
                        "ASP_REFERENCE_AGENT_SESSION_PROOF"
                    ] = AGENT_SESSION_PROOF
                    command = (
                        "scenario"
                        if program.name == "agent_a.py"
                        else "one-request"
                    )
                    completed = subprocess.run(
                        [
                            str(program),
                            command,
                            "--runtime",
                            runtime.address,
                        ],
                        env=environment,
                        text=True,
                        capture_output=True,
                        timeout=8,
                        check=False,
                    )
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
