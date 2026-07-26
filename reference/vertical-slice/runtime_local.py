#!/usr/bin/env python3
"""Independent local Runtime Mediator for the bounded ASP vertical slice.

With no arguments (or with ``subject``), this executable evaluates one
``asp-reference-subject/1`` semantic case from standard input.  ``serve`` runs
the scenario-facing TCP JSON-lines bridge.  The implementation is deliberately
stdlib-only and does not import the repository mocks or conformance oracle.
"""

from __future__ import annotations

import argparse
import hmac
import json
import math
import os
import socket
import stat
import sys
from pathlib import Path
from typing import Any


SUBJECT_PROTOCOL = "asp-reference-subject/1"
RUNTIME_PROFILE = (
    "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1"
)
AGENT_PROTOCOL = "asp-reference-agent/1"
APP_PROTOCOL = "asp-reference-app/1"
RUNTIME_PROTOCOL = "asp-reference-runtime/1"
MAX_JSON_BYTES = 1_048_576
SAFE_INTEGER = 2**53 - 1
SENSITIVE_NAMES = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "credential",
        "dpop",
        "grant_credential",
        "password",
        "private_key",
        "secret",
        "token",
        "access_token",
    }
)


class ProtocolError(ValueError):
    """Raised when an input does not satisfy the closed participant contract."""


def _object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ProtocolError(f"duplicate JSON member {key!r}")
        value[key] = item
    return value


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or (value == 0.0 and text.startswith("-")):
        raise ProtocolError("non-finite or negative-zero JSON number")
    return value


def _safe_integer(text: str) -> int:
    value = int(text)
    if (value == 0 and text.startswith("-")) or not -SAFE_INTEGER <= value <= SAFE_INTEGER:
        raise ProtocolError("JSON integer is outside the I-JSON safe range")
    return value


def _reject_constant(_: str) -> None:
    raise ProtocolError("non-finite JSON number")


def _validate_json(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -SAFE_INTEGER <= value <= SAFE_INTEGER:
            raise ProtocolError(f"unsafe integer at {path}")
        return
    if isinstance(value, float):
        if not math.isfinite(value) or (
            value == 0.0 and math.copysign(1.0, value) < 0
        ):
            raise ProtocolError(f"invalid binary64 value at {path}")
        return
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProtocolError(f"non-string member name at {path}")
            _validate_json(key, f"{path}.<key>")
            _validate_json(item, f"{path}.{key}")
        return
    raise ProtocolError(f"unsupported JSON value at {path}")


def _loads_strict(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_JSON_BYTES:
        raise ProtocolError("JSON input exceeds the bounded size")
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_object_from_pairs,
            parse_float=_finite_float,
            parse_int=_safe_integer,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ProtocolError("input is not strict JSON") from error
    _validate_json(value)
    if not isinstance(value, dict):
        raise ProtocolError("input root must be an object")
    return value


def _closed_object(
    value: Any,
    *,
    required: set[str],
    optional: set[str] = frozenset(),
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError(f"{label} must be an object")
    if not required.issubset(value) or set(value) - required - set(optional):
        raise ProtocolError(f"{label} is not the exact closed shape")
    return value


class State:
    """Small exact state transition over the runner-supplied initial state."""

    def __init__(self, initial_state: Any) -> None:
        if not isinstance(initial_state, list) or not initial_state:
            raise ProtocolError("case.initial_state must be a non-empty array")
        self.order: list[str] = []
        self.before: dict[str, Any] = {}
        self.after: dict[str, Any] = {}
        for entry in initial_state:
            item = _closed_object(
                entry,
                required={"state", "value"},
                label="initial-state entry",
            )
            name = item["state"]
            if not isinstance(name, str) or not name or name in self.before:
                raise ProtocolError("initial-state names must be unique strings")
            self.order.append(name)
            self.before[name] = item["value"]
            self.after[name] = item["value"]

    def set(self, name: str, value: Any) -> None:
        if name not in self.after:
            raise ProtocolError(f"initial state omits mutable state {name!r}")
        self.after[name] = value

    def increment(self, name: str) -> None:
        current = self.after.get(name)
        if isinstance(current, bool) or not isinstance(current, int):
            raise ProtocolError(f"state {name!r} is not an integer counter")
        self.after[name] = current + 1

    def deltas(self) -> list[dict[str, Any]]:
        return [
            {
                "state": name,
                "before": self.before[name],
                "after": self.after[name],
            }
            for name in self.order
        ]


def _section(document: dict[str, Any], name: str) -> dict[str, Any]:
    value = document.get(name)
    if not isinstance(value, dict):
        raise ProtocolError(f"semantic document requires object section {name!r}")
    return value


def _result(
    state: State,
    decision: str,
    *tokens: str,
    asp_error: str | None = None,
    policy_reason: str | None = None,
    match_reason: str | None = None,
) -> dict[str, Any]:
    if len(tokens) != len(set(tokens)):
        raise ProtocolError("participant generated duplicate observation tokens")
    result: dict[str, Any] = {
        "schema_version": 1,
        "decision": decision,
        "tokens": list(tokens),
        "state_deltas": state.deltas(),
    }
    if asp_error is not None:
        result["asp_error"] = asp_error
    if policy_reason is not None:
        result["policy_reason"] = policy_reason
    if match_reason is not None:
        result["match_reason"] = match_reason
    return result


def _evaluate_runtime(
    operation: str, document: dict[str, Any], state: State
) -> dict[str, Any]:
    grant = _section(document, "grant")
    execution = _section(document, "execution")
    runtime = _section(document, "runtime")

    if operation == "mediate_grant":
        if grant.get("claimed_issuer") != grant.get("issuer"):
            return _result(
                state,
                "rejected",
                "grant_rejected",
                "tuple_checked",
                "mediation_stopped",
                asp_error="integrity_mismatch",
            )
        if runtime.get("returned_grant_width") != "equal":
            return _result(
                state,
                "rejected",
                "grant_rejected",
                "mediation_stopped",
                asp_error="integrity_mismatch",
            )
        if runtime.get("capability_match") != "current":
            return _result(
                state,
                "rejected",
                "mediation_stopped",
                match_reason="input_unknown",
            )
        state.increment("runtime.stored_grant_width")
        return _result(state, "accepted", "tuple_checked")

    if operation == "retry_outcome":
        if (
            execution.get("outcome_state") == "unknown"
            and execution.get("retry_key") == "new"
        ):
            return _result(
                state,
                "stopped",
                "mediation_stopped",
                asp_error="outcome_unknown",
            )
        raise ProtocolError("retry_outcome requires unknown outcome with a new key")

    if operation != "mediate_action":
        raise ProtocolError(f"unsupported Runtime Mediator operation {operation!r}")

    if runtime.get("credential_release") != "none":
        return _result(
            state,
            "rejected",
            "local_denial_recorded",
            "mediation_stopped",
            policy_reason="local_policy_denied",
        )
    if (
        runtime.get("revocation_state") != "current"
        or grant.get("revocation_state") == "unknown"
    ):
        state.set("grant.lifecycle", "inactive")
        return _result(
            state,
            "stopped",
            "current_state_checked",
            "mediation_stopped",
        )
    if runtime.get("remote_path") != "known":
        return _result(
            state,
            "stopped",
            "current_state_checked",
            "mediation_stopped",
            match_reason="input_unknown",
        )
    if runtime.get("training_policy") != "exact":
        return _result(
            state,
            "rejected",
            "local_denial_recorded",
            "mediation_stopped",
            asp_error="training_use_denied",
        )

    requested = grant.get("requested_actions")
    issued = grant.get("issued_actions")
    ordinary_tuple_valid = (
        grant.get("status") == "active"
        and grant.get("claimed_issuer") == grant.get("issuer")
        and isinstance(requested, list)
        and isinstance(issued, list)
        and set(issued).issubset(requested)
        and grant.get("companion_closure") == "closed"
        and execution.get("input_hash") == execution.get("recorded_input_hash")
        and execution.get("input_schema_hash")
        == execution.get("recorded_input_schema_hash")
        and execution.get("normalization") == "fixed_point"
        and execution.get("policy") == "allow"
    )
    if not ordinary_tuple_valid:
        return _result(
            state,
            "stopped",
            "current_state_checked",
            "mediation_stopped",
            asp_error="integrity_mismatch",
        )
    state.increment("action.dispatch_count")
    state.increment("runtime.stored_grant_width")
    return _result(
        state,
        "accepted",
        "typed_request_forwarded",
        "action_accepted",
        "tuple_checked",
    )


def evaluate_subject(value: dict[str, Any]) -> dict[str, Any]:
    envelope = _closed_object(
        value,
        required={"subject_protocol", "case"},
        label="subject envelope",
    )
    if envelope["subject_protocol"] != SUBJECT_PROTOCOL:
        raise ProtocolError("unsupported subject protocol")
    case = _closed_object(
        envelope["case"],
        required={"profile_id", "initial_state", "stimulus"},
        optional={"producer_role"},
        label="subject case",
    )
    if case["profile_id"] != RUNTIME_PROFILE or case.get("producer_role") is not None:
        raise ProtocolError("case does not select the Runtime Mediator profile")
    stimulus = _closed_object(
        case["stimulus"],
        required={"operation", "fixture"},
        label="case stimulus",
    )
    fixture = _closed_object(
        stimulus["fixture"],
        required={"document"},
        label="case fixture",
    )
    operation = stimulus["operation"]
    document = fixture["document"]
    if not isinstance(operation, str) or not isinstance(document, dict):
        raise ProtocolError("case operation and semantic document are required")
    return _evaluate_runtime(operation, document, State(case["initial_state"]))


def _is_sensitive_name(name: str) -> bool:
    normalized = name.strip().lower().replace("-", "_")
    return normalized in SENSITIVE_NAMES or normalized.endswith("_credential")


def _contains_credential(value: Any, private_credential: str) -> bool:
    if isinstance(value, str):
        return bool(private_credential) and value == private_credential
    if isinstance(value, list):
        return any(_contains_credential(item, private_credential) for item in value)
    if isinstance(value, dict):
        return any(
            _is_sensitive_name(key)
            or _contains_credential(item, private_credential)
            for key, item in value.items()
        )
    return False


def _address(value: Any, label: str) -> tuple[str, int]:
    if not isinstance(value, str) or ":" not in value:
        raise ProtocolError(f"{label} must be host:port")
    host, raw_port = value.rsplit(":", 1)
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ProtocolError(f"{label} has an invalid port") from error
    if not host or not 0 <= port <= 65535:
        raise ProtocolError(f"{label} has an invalid address")
    return host, port


def _load_private_config(path: Path) -> dict[str, str]:
    try:
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode) or path.is_symlink():
            raise ProtocolError("private runtime config must be a regular file")
        if os.name == "posix" and stat.S_IMODE(mode) != 0o600:
            raise ProtocolError("private runtime config mode must be 0600")
        config = _loads_strict(path.read_bytes())
    except OSError as error:
        raise ProtocolError("cannot read private runtime config") from error
    config = _closed_object(
        config,
        required={
            "app_address",
            "runtime_id",
            "agent_id",
            "agent_session_proof",
            "grant_id",
            "credential",
        },
        label="private runtime config",
    )
    for name in (
        "runtime_id",
        "agent_id",
        "agent_session_proof",
        "grant_id",
        "credential",
    ):
        if not isinstance(config[name], str) or not config[name]:
            raise ProtocolError(f"private runtime config requires non-empty {name}")
    _address(config["app_address"], "app_address")
    return config  # type: ignore[return-value]


def _agent_request(
    value: dict[str, Any],
    credential: str,
    bound_agent_id: str,
    bound_session_proof: str,
) -> dict[str, Any]:
    if _contains_credential(value, credential):
        raise ProtocolError("agent-visible credential material is forbidden")
    payload_without_session_proof = {
        name: item for name, item in value.items() if name != "session_proof"
    }
    if _contains_credential(payload_without_session_proof, bound_session_proof):
        raise ProtocolError("agent session proof cannot appear in action content")
    request = _closed_object(
        value,
        required={
            "protocol",
            "request_id",
            "execution_id",
            "agent_id",
            "session_proof",
            "action_id",
            "idempotency_key",
            "input",
        },
        label="agent request",
    )
    if request["protocol"] != AGENT_PROTOCOL:
        raise ProtocolError("unsupported agent wire protocol")
    for name in (
        "request_id",
        "execution_id",
        "agent_id",
        "session_proof",
        "action_id",
        "idempotency_key",
    ):
        if not isinstance(request[name], str) or not request[name] or len(request[name]) > 256:
            raise ProtocolError(f"agent request requires bounded string {name}")
    if not isinstance(request["input"], dict):
        raise ProtocolError("agent action input must be an object")
    if request["agent_id"] != bound_agent_id:
        raise ProtocolError("agent identity does not match the private Grant binding")
    if not hmac.compare_digest(request["session_proof"], bound_session_proof):
        raise ProtocolError("agent session proof does not match the private binding")
    return request


def _send_to_app(
    config: dict[str, str], request: dict[str, Any], timeout: float
) -> dict[str, Any]:
    host, port = _address(config["app_address"], "app_address")
    outbound = {
        "protocol": APP_PROTOCOL,
        "request_id": request["request_id"],
        "execution_id": request["execution_id"],
        "runtime_id": config["runtime_id"],
        "grant_id": config["grant_id"],
        "credential": config["credential"],
        "agent_id": request["agent_id"],
        "action_id": request["action_id"],
        "idempotency_key": request["idempotency_key"],
        "input": request["input"],
    }
    payload = json.dumps(
        outbound, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    with socket.create_connection((host, port), timeout=timeout) as connection:
        connection.settimeout(timeout)
        connection.sendall(payload)
        reader = connection.makefile("rb")
        line = reader.readline(MAX_JSON_BYTES + 1)
        if not line or len(line) > MAX_JSON_BYTES or not line.endswith(b"\n"):
            raise ProtocolError("application returned no bounded JSON line")
    response = _loads_strict(line)
    if _contains_credential(response, config["credential"]):
        raise ProtocolError("application response contains credential material")
    return response


def _wire_error(
    request_id: Any, code: str, description: str, *, forwarded: bool
) -> dict[str, Any]:
    return {
        "protocol": RUNTIME_PROTOCOL,
        "request_id": request_id if isinstance(request_id, str) else "unknown",
        "status": "rejected" if not forwarded else "error",
        "forwarded": forwarded,
        "error": {
            "code": code,
            "description": description,
            "retryable": False,
        },
    }


def _handle_wire_line(
    line: bytes, config: dict[str, str], timeout: float
) -> dict[str, Any]:
    request_id: Any = "unknown"
    forwarded = False
    try:
        raw = _loads_strict(line)
        request_id = raw.get("request_id")
        request = _agent_request(
            raw,
            config["credential"],
            config["agent_id"],
            config["agent_session_proof"],
        )
        forwarded = True
        app_response = _send_to_app(config, request, timeout)
        return {
            "protocol": RUNTIME_PROTOCOL,
            "request_id": request["request_id"],
            "status": "completed",
            "forwarded": True,
            "result": app_response,
        }
    except ProtocolError as error:
        credential_failure = "credential" in str(error)
        return _wire_error(
            request_id,
            "credential_exposed" if credential_failure else "request_invalid",
            (
                "Agent-visible credential material is forbidden."
                if credential_failure
                else "The agent request or application response was invalid."
            ),
            forwarded=forwarded,
        )
    except (OSError, TimeoutError):
        return _wire_error(
            request_id,
            "service_unavailable",
            "The application is unavailable.",
            forwarded=True,
        )


def _serve(args: argparse.Namespace) -> int:
    config = _load_private_config(args.config)
    host, port = _address(args.listen, "listen")
    served = 0
    with socket.create_server((host, port)) as listener:
        listener.settimeout(0.5)
        actual_host, actual_port = listener.getsockname()[:2]
        print(
            json.dumps(
                {
                    "protocol": RUNTIME_PROTOCOL,
                    "status": "listening",
                    "address": f"{actual_host}:{actual_port}",
                    "runtime_id": config["runtime_id"],
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
        while True:
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            try:
                with connection:
                    connection.settimeout(args.timeout)
                    reader = connection.makefile("rb")
                    line = reader.readline(MAX_JSON_BYTES + 1)
                    if (
                        not line
                        or len(line) > MAX_JSON_BYTES
                        or not line.endswith(b"\n")
                    ):
                        response = _wire_error(
                            "unknown",
                            "request_invalid",
                            "The agent request must be one bounded JSON line.",
                            forwarded=False,
                        )
                    else:
                        response = _handle_wire_line(line, config, args.timeout)
                    connection.sendall(
                        json.dumps(
                            response,
                            ensure_ascii=False,
                            allow_nan=False,
                            separators=(",", ":"),
                        ).encode("utf-8")
                        + b"\n"
                    )
            except (OSError, TimeoutError):
                continue
            served += 1
            if args.once and served >= 1:
                return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("subject", help="evaluate one subject case from stdin")
    serve = subparsers.add_parser("serve", help="serve the TCP JSON-lines runtime bridge")
    serve.add_argument("--config", required=True, type=Path)
    serve.add_argument("--listen", required=True)
    serve.add_argument("--timeout", type=float, default=5.0)
    serve.add_argument("--once", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command in (None, "subject"):
            data = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
            result = evaluate_subject(_loads_strict(data))
            json.dump(
                result,
                sys.stdout,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            return 0
        if args.command == "serve":
            if args.timeout <= 0:
                raise ProtocolError("timeout must be positive")
            return _serve(args)
        raise ProtocolError("unknown command")
    except (ProtocolError, OSError, UnicodeError, KeyError, TypeError, ValueError):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
