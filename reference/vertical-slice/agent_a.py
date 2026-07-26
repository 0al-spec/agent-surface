#!/usr/bin/env python3
"""Independent Agent A and bounded Agent Adapter subject.

Default/``subject`` mode evaluates the five core Agent Adapter semantic paths
using ``asp-reference-subject/1``.  ``scenario`` performs a positive
``comment.create``, an exact replay, and a synthetic credential-injection
attempt against a scenario runtime.  No application credential is accepted by
the scenario CLI or retained by this process.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import socket
import sys
from typing import Any


SUBJECT_PROTOCOL = "asp-reference-subject/1"
ADAPTER_PROFILE = (
    "https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1"
)
AGENT_PROTOCOL = "asp-reference-agent/1"
RUNTIME_PROTOCOL = "asp-reference-runtime/1"
SCENARIO_PROTOCOL = "asp-reference-agent-scenario/1"
MAX_JSON_BYTES = 1_048_576
SAFE_INTEGER = 2**53 - 1


class AgentContractError(ValueError):
    """Closed stdin or scenario-wire contract failure."""


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise AgentContractError(f"duplicate JSON member {name!r}")
        result[name] = value
    return result


def _float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or (value == 0.0 and text.startswith("-")):
        raise AgentContractError("invalid JSON number")
    return value


def _int(text: str) -> int:
    value = int(text)
    if not -SAFE_INTEGER <= value <= SAFE_INTEGER or (
        value == 0 and text.startswith("-")
    ):
        raise AgentContractError("unsafe JSON integer")
    return value


def _constant(_: str) -> None:
    raise AgentContractError("invalid JSON constant")


def _validate(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -SAFE_INTEGER <= value <= SAFE_INTEGER:
            raise AgentContractError("unsafe JSON integer")
        return
    if isinstance(value, float):
        if not math.isfinite(value) or (
            value == 0 and math.copysign(1.0, value) < 0
        ):
            raise AgentContractError("invalid JSON number")
        return
    if isinstance(value, str):
        value.encode("utf-8", "strict")
        return
    if isinstance(value, list):
        for member in value:
            _validate(member)
        return
    if isinstance(value, dict):
        for name, member in value.items():
            if not isinstance(name, str):
                raise AgentContractError("non-string JSON member")
            _validate(name)
            _validate(member)
        return
    raise AgentContractError("unsupported JSON value")


def _load(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_JSON_BYTES:
        raise AgentContractError("JSON exceeds size limit")
    try:
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_float=_float,
            parse_int=_int,
            parse_constant=_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as error:
        raise AgentContractError("malformed strict JSON") from error
    _validate(value)
    if not isinstance(value, dict):
        raise AgentContractError("JSON root must be an object")
    return value


def _closed(
    value: Any,
    required: set[str],
    *,
    optional: set[str] | None = None,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AgentContractError(f"{label} must be an object")
    allowed = required | (optional or set())
    if not required.issubset(value) or not set(value).issubset(allowed):
        raise AgentContractError(f"{label} is not the exact closed shape")
    return value


class AdapterState:
    def __init__(self, initial: Any) -> None:
        if not isinstance(initial, list) or not initial:
            raise AgentContractError("initial_state must be a non-empty array")
        self.names: list[str] = []
        self.before: dict[str, Any] = {}
        self.after: dict[str, Any] = {}
        for raw in initial:
            entry = _closed(raw, {"state", "value"}, label="state entry")
            name = entry["state"]
            if not isinstance(name, str) or not name or name in self.before:
                raise AgentContractError("invalid or duplicate state name")
            self.names.append(name)
            self.before[name] = entry["value"]
            self.after[name] = entry["value"]

    def increment(self, name: str) -> None:
        current = self.after.get(name)
        if isinstance(current, bool) or not isinstance(current, int):
            raise AgentContractError(f"counter {name!r} was not initialized")
        self.after[name] = current + 1

    def result(
        self,
        decision: str,
        tokens: list[str],
        *,
        asp_error: str | None = None,
        policy_reason: str | None = None,
        match_reason: str | None = None,
    ) -> dict[str, Any]:
        if len(tokens) != len(set(tokens)):
            raise AgentContractError("duplicate participant token")
        output: dict[str, Any] = {
            "schema_version": 1,
            "decision": decision,
            "tokens": tokens,
            "state_deltas": [
                {
                    "state": name,
                    "before": self.before[name],
                    "after": self.after[name],
                }
                for name in self.names
            ],
        }
        if asp_error is not None:
            output["asp_error"] = asp_error
        if policy_reason is not None:
            output["policy_reason"] = policy_reason
        if match_reason is not None:
            output["match_reason"] = match_reason
        return output


def _section(document: dict[str, Any], name: str) -> dict[str, Any]:
    value = document.get(name)
    if not isinstance(value, dict):
        raise AgentContractError(f"semantic document lacks {name!r}")
    return value


def _evaluate_adapter(
    operation: str, document: dict[str, Any], state: AdapterState
) -> dict[str, Any]:
    execution = _section(document, "execution")
    adapter = _section(document, "adapter")
    receipt = _section(document, "receipt")

    if operation == "retry_outcome":
        if (
            execution.get("outcome_state") == "unknown"
            and adapter.get("unknown_outcome_handling") == "retry"
        ):
            return state.result(
                "rejected",
                ["adapter_request_rejected"],
                asp_error="outcome_unknown",
            )
        raise AgentContractError("retry_outcome is not an unknown-outcome retry")

    if operation != "translate_action":
        raise AgentContractError(f"unsupported Agent Adapter operation {operation!r}")
    if adapter.get("credential_input") != "none":
        return state.result(
            "rejected",
            ["adapter_request_rejected", "local_denial_recorded"],
        )
    if adapter.get("action_authority") != "exact":
        return state.result("rejected", ["adapter_request_rejected"])
    if (
        adapter.get("receipt_evidence") != "observed"
        or receipt.get("origin") != "observed"
    ):
        return state.result(
            "rejected",
            ["adapter_request_rejected", "receipt_rejected"],
            asp_error="integrity_mismatch",
        )
    state.increment("adapter.forwarded_count")
    return state.result("accepted", ["typed_request_forwarded"])


def evaluate_subject(value: dict[str, Any]) -> dict[str, Any]:
    envelope = _closed(
        value, {"subject_protocol", "case"}, label="subject envelope"
    )
    if envelope["subject_protocol"] != SUBJECT_PROTOCOL:
        raise AgentContractError("unsupported subject protocol")
    case = _closed(
        envelope["case"],
        {"profile_id", "initial_state", "stimulus"},
        optional={"producer_role"},
        label="subject case",
    )
    if case["profile_id"] != ADAPTER_PROFILE or case.get("producer_role") is not None:
        raise AgentContractError("case does not select Agent Adapter")
    stimulus = _closed(
        case["stimulus"], {"operation", "fixture"}, label="case stimulus"
    )
    fixture = _closed(
        stimulus["fixture"], {"document"}, label="case fixture"
    )
    operation = stimulus["operation"]
    document = fixture["document"]
    if not isinstance(operation, str) or not isinstance(document, dict):
        raise AgentContractError("case operation or document is invalid")
    return _evaluate_adapter(operation, document, AdapterState(case["initial_state"]))


def _address(value: str) -> tuple[str, int]:
    if ":" not in value:
        raise AgentContractError("runtime address must be host:port")
    host, raw_port = value.rsplit(":", 1)
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        port = int(raw_port)
    except ValueError as error:
        raise AgentContractError("runtime port is invalid") from error
    if not host or not 1 <= port <= 65535:
        raise AgentContractError("runtime address is invalid")
    return host, port


def _exchange(address: tuple[str, int], request: dict[str, Any], timeout: float) -> dict[str, Any]:
    payload = json.dumps(
        request, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    with socket.create_connection(address, timeout=timeout) as connection:
        connection.settimeout(timeout)
        connection.sendall(payload)
        line = connection.makefile("rb").readline(MAX_JSON_BYTES + 1)
    if not line or len(line) > MAX_JSON_BYTES or not line.endswith(b"\n"):
        raise AgentContractError("runtime did not return one bounded JSON line")
    response = _load(line)
    if response.get("protocol") != RUNTIME_PROTOCOL:
        raise AgentContractError("runtime response protocol is invalid")
    if response.get("request_id") != request["request_id"]:
        raise AgentContractError("runtime response request_id is not correlated")
    return response


def _action_request(
    *,
    request_id: str,
    execution_id: str,
    agent_id: str,
    session_proof: str,
    idempotency_key: str,
    text: str,
) -> dict[str, Any]:
    return {
        "protocol": AGENT_PROTOCOL,
        "request_id": request_id,
        "execution_id": execution_id,
        "agent_id": agent_id,
        "session_proof": session_proof,
        "action_id": "comment.create",
        "idempotency_key": idempotency_key,
        "input": {"task_id": "task-1", "text": text},
    }


def run_scenario(args: argparse.Namespace) -> int:
    runtime = _address(args.runtime)
    session_proof = os.environ.get("ASP_REFERENCE_AGENT_SESSION_PROOF", "")
    if len(session_proof) < 32:
        raise AgentContractError("agent session proof is unavailable")
    request = _action_request(
        request_id=args.request_id,
        execution_id=args.execution_id,
        agent_id=args.agent_id,
        session_proof=session_proof,
        idempotency_key=args.idempotency_key,
        text=args.text,
    )
    replay = json.loads(json.dumps(request))
    injected = _action_request(
        request_id=f"{args.request_id}-credential-negative",
        execution_id=f"{args.execution_id}-credential-negative",
        agent_id=args.agent_id,
        session_proof=session_proof,
        idempotency_key=f"{args.idempotency_key}-credential-negative",
        text=args.text,
    )
    injected["credential"] = "synthetic-agent-supplied-credential"
    nested_session_proof = _action_request(
        request_id=f"{args.request_id}-session-proof-negative",
        execution_id=f"{args.execution_id}-session-proof-negative",
        agent_id=args.agent_id,
        session_proof=session_proof,
        idempotency_key=f"{args.idempotency_key}-session-proof-negative",
        text=session_proof,
    )
    steps = []
    for name, current in (
        ("create", request),
        ("exact_replay", replay),
        ("credential_injection_negative", injected),
        ("session_proof_injection_negative", nested_session_proof),
    ):
        steps.append(
            {
                "name": name,
                "response": _exchange(runtime, current, args.timeout),
            }
        )
    output = {
        "protocol": SCENARIO_PROTOCOL,
        "schema_version": 1,
        "agent_id": args.agent_id,
        "scenario": "agent-a-create-replay-credential-negative",
        "status": "completed",
        "steps": steps,
    }
    json.dump(output, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command")
    commands.add_parser("subject", help="evaluate one Agent Adapter case from stdin")
    scenario = commands.add_parser("scenario", help="run Agent A's four-step scenario")
    scenario.add_argument("--runtime", required=True)
    scenario.add_argument("--agent-id", default="agent-a")
    scenario.add_argument("--request-id", default="agent-a-comment-create")
    scenario.add_argument("--execution-id", default="execution-agent-a-comment-create")
    scenario.add_argument("--idempotency-key", default="idem-agent-a-comment-001")
    scenario.add_argument("--text", default="Agent A deterministic comment")
    scenario.add_argument("--timeout", type=float, default=5.0)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in (None, "subject"):
            raw = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
            json.dump(
                evaluate_subject(_load(raw)),
                sys.stdout,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            return 0
        if args.command == "scenario":
            if args.timeout <= 0:
                raise AgentContractError("timeout must be positive")
            return run_scenario(args)
        raise AgentContractError("unknown command")
    except (
        AgentContractError,
        OSError,
        TimeoutError,
        UnicodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
