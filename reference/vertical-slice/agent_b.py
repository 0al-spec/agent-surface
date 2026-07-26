#!/usr/bin/env python3
"""Independent Agent B and bounded Agent Adapter subject.

Default/``subject`` mode evaluates the five core Agent Adapter semantic paths
using ``asp-reference-subject/1``.  ``scenario`` sends a positive
``comment.create`` followed by the same idempotency key with changed input.
``one-request`` sends exactly one ordinary request, which lets the scenario
driver exercise a request after revocation without giving Agent B credentials.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import socket
import sys
from dataclasses import dataclass
from typing import Any


SUBJECT_PROTOCOL = "asp-reference-subject/1"
PROFILE_ID = "https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1"
AGENT_WIRE = "asp-reference-agent/1"
RUNTIME_WIRE = "asp-reference-runtime/1"
SCENARIO_WIRE = "asp-reference-agent-scenario/1"
BYTE_LIMIT = 1_048_576
MAX_SAFE_INTEGER = 9_007_199_254_740_991


class ContractViolation(ValueError):
    """Raised for a closed protocol or semantic contract violation."""


def _members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractViolation("duplicate JSON member")
        result[key] = value
    return result


def _parse_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or (value == 0 and text.startswith("-")):
        raise ContractViolation("invalid binary64 number")
    return value


def _parse_int(text: str) -> int:
    value = int(text)
    if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
        raise ContractViolation("unsafe JSON integer")
    if value == 0 and text.startswith("-"):
        raise ContractViolation("negative zero")
    return value


def _reject_constant(_: str) -> None:
    raise ContractViolation("invalid JSON constant")


def _walk(value: Any) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if item is None or isinstance(item, bool):
            continue
        if isinstance(item, int):
            if not -MAX_SAFE_INTEGER <= item <= MAX_SAFE_INTEGER:
                raise ContractViolation("unsafe JSON integer")
            continue
        if isinstance(item, float):
            if not math.isfinite(item) or (
                item == 0 and math.copysign(1.0, item) < 0
            ):
                raise ContractViolation("invalid binary64 number")
            continue
        if isinstance(item, str):
            item.encode("utf-8", "strict")
            continue
        if isinstance(item, list):
            pending.extend(item)
            continue
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ContractViolation("non-string JSON member")
                key.encode("utf-8", "strict")
                pending.append(child)
            continue
        raise ContractViolation("unsupported JSON value")


def decode(raw: bytes) -> dict[str, Any]:
    if len(raw) > BYTE_LIMIT:
        raise ContractViolation("JSON exceeds the bounded size")
    try:
        result = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_members,
            parse_float=_parse_float,
            parse_int=_parse_int,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ContractViolation("malformed strict JSON") from error
    _walk(result)
    if not isinstance(result, dict):
        raise ContractViolation("JSON root must be an object")
    return result


def closed(
    value: Any,
    required: set[str],
    *,
    optional: set[str] | None = None,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractViolation(f"{name} must be an object")
    allowed = required | (optional or set())
    if not required.issubset(value) or not set(value).issubset(allowed):
        raise ContractViolation(f"{name} is not the exact closed shape")
    return value


@dataclass
class State:
    order: list[str]
    before: dict[str, Any]
    after: dict[str, Any]

    @classmethod
    def from_case(cls, value: Any) -> "State":
        if not isinstance(value, list) or not value:
            raise ContractViolation("initial_state must be a non-empty array")
        order: list[str] = []
        before: dict[str, Any] = {}
        for raw in value:
            entry = closed(raw, {"state", "value"}, name="state entry")
            name = entry["state"]
            if not isinstance(name, str) or not name or name in before:
                raise ContractViolation("invalid or duplicate state name")
            order.append(name)
            before[name] = entry["value"]
        return cls(order, before, dict(before))

    def increment(self, name: str) -> None:
        value = self.after.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ContractViolation(f"counter {name} was not initialized")
        self.after[name] = value + 1

    def output(
        self,
        decision: str,
        tokens: list[str],
        **details: str | None,
    ) -> dict[str, Any]:
        if len(tokens) != len(set(tokens)):
            raise ContractViolation("duplicate observation token")
        result: dict[str, Any] = {
            "schema_version": 1,
            "decision": decision,
            "tokens": tokens,
            "state_deltas": [
                {
                    "state": name,
                    "before": self.before[name],
                    "after": self.after[name],
                }
                for name in self.order
            ],
        }
        result.update(
            {name: value for name, value in details.items() if value is not None}
        )
        return result


def _section(document: dict[str, Any], name: str) -> dict[str, Any]:
    value = document.get(name)
    if not isinstance(value, dict):
        raise ContractViolation(f"semantic document requires section {name}")
    return value


def translate(
    operation: str, document: dict[str, Any], state: State
) -> dict[str, Any]:
    execution = _section(document, "execution")
    adapter = _section(document, "adapter")
    receipt = _section(document, "receipt")

    if operation == "retry_outcome":
        unknown_retry = (
            execution.get("outcome_state") == "unknown"
            and adapter.get("unknown_outcome_handling") == "retry"
        )
        if not unknown_retry:
            raise ContractViolation("retry case is not an unknown-outcome retry")
        return state.output(
            "rejected",
            ["adapter_request_rejected"],
            asp_error="outcome_unknown",
        )

    if operation != "translate_action":
        raise ContractViolation("unsupported Agent Adapter operation")
    if adapter.get("credential_input") != "none":
        return state.output(
            "rejected",
            ["adapter_request_rejected", "local_denial_recorded"],
        )
    if adapter.get("action_authority") != "exact":
        return state.output("rejected", ["adapter_request_rejected"])
    observed_receipt = (
        adapter.get("receipt_evidence") == "observed"
        and receipt.get("origin") == "observed"
    )
    if not observed_receipt:
        return state.output(
            "rejected",
            ["adapter_request_rejected", "receipt_rejected"],
            asp_error="integrity_mismatch",
        )
    state.increment("adapter.forwarded_count")
    return state.output("accepted", ["typed_request_forwarded"])


def subject(value: dict[str, Any]) -> dict[str, Any]:
    envelope = closed(
        value, {"subject_protocol", "case"}, name="subject envelope"
    )
    if envelope["subject_protocol"] != SUBJECT_PROTOCOL:
        raise ContractViolation("unsupported subject protocol")
    case = closed(
        envelope["case"],
        {"profile_id", "initial_state", "stimulus"},
        optional={"producer_role"},
        name="case",
    )
    if case["profile_id"] != PROFILE_ID or case.get("producer_role") is not None:
        raise ContractViolation("case does not select Agent Adapter")
    stimulus = closed(
        case["stimulus"], {"operation", "fixture"}, name="case stimulus"
    )
    fixture = closed(stimulus["fixture"], {"document"}, name="case fixture")
    operation = stimulus["operation"]
    document = fixture["document"]
    if not isinstance(operation, str) or not isinstance(document, dict):
        raise ContractViolation("case operation or semantic document is invalid")
    return translate(operation, document, State.from_case(case["initial_state"]))


def address(raw: str) -> tuple[str, int]:
    if ":" not in raw:
        raise ContractViolation("runtime address must be host:port")
    host, port_text = raw.rsplit(":", 1)
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        port = int(port_text)
    except ValueError as error:
        raise ContractViolation("runtime port is invalid") from error
    if not host or not 1 <= port <= 65535:
        raise ContractViolation("runtime address is invalid")
    return host, port


def exchange(
    destination: tuple[str, int],
    request: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    wire = json.dumps(
        request, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    with socket.create_connection(destination, timeout=timeout) as connection:
        connection.settimeout(timeout)
        connection.sendall(wire)
        line = connection.makefile("rb").readline(BYTE_LIMIT + 1)
    if not line or len(line) > BYTE_LIMIT or not line.endswith(b"\n"):
        raise ContractViolation("runtime did not return one bounded JSON line")
    response = decode(line)
    if response.get("protocol") != RUNTIME_WIRE:
        raise ContractViolation("runtime response protocol is invalid")
    if response.get("request_id") != request["request_id"]:
        raise ContractViolation("runtime response request_id is not correlated")
    return response


def action_request(
    *,
    request_id: str,
    execution_id: str,
    agent_id: str,
    session_proof: str,
    idempotency_key: str,
    text: str,
) -> dict[str, Any]:
    return {
        "protocol": AGENT_WIRE,
        "request_id": request_id,
        "execution_id": execution_id,
        "agent_id": agent_id,
        "session_proof": session_proof,
        "action_id": "comment.create",
        "idempotency_key": idempotency_key,
        "input": {"task_id": "task-1", "text": text},
    }


def _scenario_output(
    agent_id: str,
    scenario: str,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "protocol": SCENARIO_WIRE,
        "schema_version": 1,
        "agent_id": agent_id,
        "scenario": scenario,
        "status": "completed",
        "steps": steps,
    }


def run_scenario(args: argparse.Namespace) -> int:
    destination = address(args.runtime)
    session_proof = os.environ.get("ASP_REFERENCE_AGENT_SESSION_PROOF", "")
    if len(session_proof) < 32:
        raise ContractViolation("agent session proof is unavailable")
    first = action_request(
        request_id=args.request_id,
        execution_id=args.execution_id,
        agent_id=args.agent_id,
        session_proof=session_proof,
        idempotency_key=args.idempotency_key,
        text=args.text,
    )
    changed = action_request(
        request_id=f"{args.request_id}-changed-input",
        execution_id=args.execution_id,
        agent_id=args.agent_id,
        session_proof=session_proof,
        idempotency_key=args.idempotency_key,
        text=args.changed_text,
    )
    output = _scenario_output(
        args.agent_id,
        "agent-b-create-idempotency-conflict",
        [
            {
                "name": "create",
                "response": exchange(destination, first, args.timeout),
            },
            {
                "name": "changed_input_idempotency_conflict",
                "response": exchange(destination, changed, args.timeout),
            },
        ],
    )
    json.dump(output, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    return 0


def run_one_request(args: argparse.Namespace) -> int:
    session_proof = os.environ.get("ASP_REFERENCE_AGENT_SESSION_PROOF", "")
    if len(session_proof) < 32:
        raise ContractViolation("agent session proof is unavailable")
    request = action_request(
        request_id=args.request_id,
        execution_id=args.execution_id,
        agent_id=args.agent_id,
        session_proof=session_proof,
        idempotency_key=args.idempotency_key,
        text=args.text,
    )
    output = _scenario_output(
        args.agent_id,
        "agent-b-revoked-grant-one-request",
        [
            {
                "name": "one_request",
                "response": exchange(address(args.runtime), request, args.timeout),
            }
        ],
    )
    json.dump(output, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command")
    commands.add_parser("subject", help="evaluate one Agent Adapter case from stdin")

    scenario = commands.add_parser(
        "scenario", help="run Agent B's changed-input idempotency scenario"
    )
    scenario.add_argument("--runtime", required=True)
    scenario.add_argument("--agent-id", default="agent-b")
    scenario.add_argument("--request-id", default="agent-b-comment-create")
    scenario.add_argument("--execution-id", default="execution-agent-b-comment-create")
    scenario.add_argument("--idempotency-key", default="idem-agent-b-comment-001")
    scenario.add_argument("--text", default="Agent B deterministic comment")
    scenario.add_argument(
        "--changed-text", default="Agent B changed-input comment"
    )
    scenario.add_argument("--timeout", type=float, default=5.0)

    one = commands.add_parser(
        "one-request", help="send exactly one request for the revoked-grant step"
    )
    one.add_argument("--runtime", required=True)
    one.add_argument("--agent-id", default="agent-b")
    one.add_argument("--request-id", default="agent-b-revoked-request")
    one.add_argument("--execution-id", default="execution-agent-b-one-request")
    one.add_argument("--idempotency-key", default="idem-agent-b-revoked-001")
    one.add_argument("--text", default="Agent B revoked-grant probe")
    one.add_argument("--timeout", type=float, default=5.0)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in (None, "subject"):
            raw = sys.stdin.buffer.read(BYTE_LIMIT + 1)
            json.dump(
                subject(decode(raw)),
                sys.stdout,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            return 0
        if args.command in {"scenario", "one-request"} and args.timeout <= 0:
            raise ContractViolation("timeout must be positive")
        if args.command == "scenario":
            return run_scenario(args)
        if args.command == "one-request":
            return run_one_request(args)
        raise ContractViolation("unknown command")
    except (
        ContractViolation,
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
