#!/usr/bin/env python3
"""Independent remote Runtime Mediator for the bounded ASP vertical slice.

The executable has two deliberately separate entry paths:

* default/``subject`` evaluates one ``asp-reference-subject/1`` case;
* ``serve`` exposes a threaded TCP JSON-lines bridge using a private config.

Only Python's standard library is used.  This file does not import or delegate
semantic decisions to the local runtime, the reference mocks, or the suite
oracle.
"""

from __future__ import annotations

import argparse
import hmac
import json
import math
import os
import socket
import socketserver
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUBJECT_PROTOCOL = "asp-reference-subject/1"
PROFILE_ID = "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1"
AGENT_WIRE = "asp-reference-agent/1"
APP_WIRE = "asp-reference-app/1"
RUNTIME_WIRE = "asp-reference-runtime/1"
LIMIT = 1_048_576
MAX_SAFE_INTEGER = 9_007_199_254_740_991
SECRET_KEYS = {
    "access_token",
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
}


class ContractViolation(ValueError):
    """Closed protocol or semantic input failure."""


def _unique_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ContractViolation("duplicate JSON member")
        result[name] = value
    return result


def _number(text: str) -> float:
    result = float(text)
    if not math.isfinite(result) or (result == 0 and text.startswith("-")):
        raise ContractViolation("invalid binary64 number")
    return result


def _integer(text: str) -> int:
    result = int(text)
    if not -MAX_SAFE_INTEGER <= result <= MAX_SAFE_INTEGER:
        raise ContractViolation("unsafe JSON integer")
    if result == 0 and text.startswith("-"):
        raise ContractViolation("negative zero")
    return result


def _constant(_: str) -> None:
    raise ContractViolation("invalid JSON constant")


def _walk_json(value: Any) -> None:
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str):
            value.encode("utf-8", "strict")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise ContractViolation("unsafe integer")
        return
    if isinstance(value, float):
        if not math.isfinite(value) or (
            value == 0 and math.copysign(1.0, value) < 0
        ):
            raise ContractViolation("invalid binary64 number")
        return
    if isinstance(value, list):
        for member in value:
            _walk_json(member)
        return
    if isinstance(value, dict):
        for name, member in value.items():
            if not isinstance(name, str):
                raise ContractViolation("JSON member name is not a string")
            _walk_json(name)
            _walk_json(member)
        return
    raise ContractViolation("unsupported JSON value")


def strict_json(raw: bytes) -> dict[str, Any]:
    if len(raw) > LIMIT:
        raise ContractViolation("JSON exceeds size limit")
    try:
        result = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_unique_members,
            parse_float=_number,
            parse_int=_integer,
            parse_constant=_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ContractViolation("malformed strict JSON") from error
    _walk_json(result)
    if not isinstance(result, dict):
        raise ContractViolation("JSON root is not an object")
    return result


def exact(
    value: Any,
    required: set[str],
    *,
    optional: set[str] | None = None,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractViolation(f"{name} is not an object")
    allowed = required | (optional or set())
    if set(value) != required and (
        not required.issubset(value) or not set(value).issubset(allowed)
    ):
        raise ContractViolation(f"{name} is not closed")
    return value


@dataclass
class Transition:
    names: list[str]
    original: dict[str, Any]
    current: dict[str, Any]

    @classmethod
    def from_wire(cls, value: Any) -> "Transition":
        if not isinstance(value, list) or not value:
            raise ContractViolation("initial_state is not a non-empty array")
        names: list[str] = []
        state: dict[str, Any] = {}
        for raw in value:
            entry = exact(raw, {"state", "value"}, name="state entry")
            key = entry["state"]
            if not isinstance(key, str) or not key or key in state:
                raise ContractViolation("state name is invalid or repeated")
            names.append(key)
            state[key] = entry["value"]
        return cls(names, dict(state), state)

    def assign(self, key: str, value: Any) -> None:
        if key not in self.current:
            raise ContractViolation(f"mutable state {key} was not initialized")
        self.current[key] = value

    def add_one(self, key: str) -> None:
        value = self.current.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ContractViolation(f"counter {key} was not initialized")
        self.current[key] = value + 1

    def report(
        self,
        decision: str,
        tokens: list[str],
        **details: str | None,
    ) -> dict[str, Any]:
        if len(tokens) != len(set(tokens)):
            raise ContractViolation("duplicate participant token")
        output: dict[str, Any] = {
            "schema_version": 1,
            "decision": decision,
            "tokens": tokens,
            "state_deltas": [
                {
                    "state": key,
                    "before": self.original[key],
                    "after": self.current[key],
                }
                for key in self.names
            ],
        }
        output.update({key: value for key, value in details.items() if value is not None})
        return output


def _dict_member(document: dict[str, Any], key: str) -> dict[str, Any]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise ContractViolation(f"missing semantic section {key}")
    return value


def mediate(case_operation: str, document: dict[str, Any], tx: Transition) -> dict[str, Any]:
    grant = _dict_member(document, "grant")
    execution = _dict_member(document, "execution")
    runtime = _dict_member(document, "runtime")

    if case_operation == "mediate_grant":
        issuer_matches = grant.get("issuer") == grant.get("claimed_issuer")
        width_matches = runtime.get("returned_grant_width") == "equal"
        if not issuer_matches:
            return tx.report(
                "rejected",
                ["grant_rejected", "tuple_checked", "mediation_stopped"],
                asp_error="integrity_mismatch",
            )
        if not width_matches:
            return tx.report(
                "rejected",
                ["grant_rejected", "mediation_stopped"],
                asp_error="integrity_mismatch",
            )
        if runtime.get("capability_match") != "current":
            return tx.report(
                "rejected",
                ["mediation_stopped"],
                match_reason="input_unknown",
            )
        tx.add_one("runtime.stored_grant_width")
        return tx.report("accepted", ["tuple_checked"])

    if case_operation == "retry_outcome":
        blind_retry = (
            execution.get("outcome_state") == "unknown"
            and execution.get("retry_key") == "new"
        )
        if not blind_retry:
            raise ContractViolation("retry case is not an unknown-outcome new-key retry")
        return tx.report(
            "stopped",
            ["mediation_stopped"],
            asp_error="outcome_unknown",
        )

    if case_operation != "mediate_action":
        raise ContractViolation("unsupported Runtime Mediator operation")

    if runtime.get("credential_release") != "none":
        return tx.report(
            "rejected",
            ["local_denial_recorded", "mediation_stopped"],
            policy_reason="local_policy_denied",
        )

    current_revocation = (
        runtime.get("revocation_state") == "current"
        and grant.get("revocation_state") != "unknown"
    )
    if not current_revocation:
        tx.assign("grant.lifecycle", "inactive")
        return tx.report(
            "stopped",
            ["current_state_checked", "mediation_stopped"],
        )

    if runtime.get("remote_path") != "known":
        return tx.report(
            "stopped",
            ["current_state_checked", "mediation_stopped"],
            match_reason="input_unknown",
        )
    if runtime.get("training_policy") != "exact":
        return tx.report(
            "rejected",
            ["local_denial_recorded", "mediation_stopped"],
            asp_error="training_use_denied",
        )

    requested = grant.get("requested_actions")
    issued = grant.get("issued_actions")
    fixed_point = (
        grant.get("status") == "active"
        and isinstance(requested, list)
        and isinstance(issued, list)
        and set(issued).issubset(set(requested))
        and grant.get("issuer") == grant.get("claimed_issuer")
        and grant.get("companion_closure") == "closed"
        and execution.get("input_hash") == execution.get("recorded_input_hash")
        and execution.get("input_schema_hash")
        == execution.get("recorded_input_schema_hash")
        and execution.get("normalization") == "fixed_point"
        and execution.get("policy") == "allow"
    )
    if not fixed_point:
        return tx.report(
            "stopped",
            ["current_state_checked", "mediation_stopped"],
            asp_error="integrity_mismatch",
        )

    tx.add_one("action.dispatch_count")
    tx.add_one("runtime.stored_grant_width")
    return tx.report(
        "accepted",
        ["typed_request_forwarded", "action_accepted", "tuple_checked"],
    )


def subject(value: dict[str, Any]) -> dict[str, Any]:
    root = exact(value, {"subject_protocol", "case"}, name="subject envelope")
    if root["subject_protocol"] != SUBJECT_PROTOCOL:
        raise ContractViolation("wrong subject protocol")
    case = exact(
        root["case"],
        {"profile_id", "initial_state", "stimulus"},
        optional={"producer_role"},
        name="case",
    )
    if case["profile_id"] != PROFILE_ID or case.get("producer_role") is not None:
        raise ContractViolation("wrong role profile")
    stimulus = exact(
        case["stimulus"], {"operation", "fixture"}, name="case stimulus"
    )
    fixture = exact(stimulus["fixture"], {"document"}, name="case fixture")
    operation = stimulus["operation"]
    document = fixture["document"]
    if not isinstance(operation, str) or not isinstance(document, dict):
        raise ContractViolation("case operation or document is invalid")
    return mediate(operation, document, Transition.from_wire(case["initial_state"]))


def split_address(raw: Any, label: str) -> tuple[str, int]:
    if not isinstance(raw, str) or ":" not in raw:
        raise ContractViolation(f"{label} is not host:port")
    host, port_text = raw.rsplit(":", 1)
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        port = int(port_text)
    except ValueError as error:
        raise ContractViolation(f"{label} port is invalid") from error
    if not host or port < 0 or port > 65535:
        raise ContractViolation(f"{label} is invalid")
    return host, port


def private_config(path: Path) -> dict[str, str]:
    try:
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode) or path.is_symlink():
            raise ContractViolation("private config is not a regular file")
        if os.name == "posix" and stat.S_IMODE(mode) != 0o600:
            raise ContractViolation("private config mode is not 0600")
        value = strict_json(path.read_bytes())
    except OSError as error:
        raise ContractViolation("private config is unavailable") from error
    config = exact(
        value,
        {
            "app_address",
            "runtime_id",
            "agent_id",
            "agent_session_proof",
            "grant_id",
            "credential",
        },
        name="private config",
    )
    for key in (
        "runtime_id",
        "agent_id",
        "agent_session_proof",
        "grant_id",
        "credential",
    ):
        if not isinstance(config[key], str) or not config[key]:
            raise ContractViolation(f"private config member {key} is invalid")
    split_address(config["app_address"], "app_address")
    return config  # type: ignore[return-value]


def secret_name(name: str) -> bool:
    candidate = name.lower().strip().replace("-", "_")
    return candidate in SECRET_KEYS or candidate.endswith("_credential")


def exposes_secret(value: Any, credential: str) -> bool:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str) and item == credential:
            return True
        if isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, dict):
            for name, child in item.items():
                if secret_name(name):
                    return True
                pending.append(child)
    return False


def validated_agent_request(
    value: dict[str, Any],
    credential: str,
    bound_agent_id: str,
    bound_session_proof: str,
) -> dict[str, Any]:
    if exposes_secret(value, credential):
        raise ContractViolation("agent-visible credential")
    payload_without_session_proof = {
        name: item for name, item in value.items() if name != "session_proof"
    }
    if exposes_secret(payload_without_session_proof, bound_session_proof):
        raise ContractViolation("agent session proof appears in action content")
    request = exact(
        value,
        {
            "protocol",
            "request_id",
            "execution_id",
            "agent_id",
            "session_proof",
            "action_id",
            "idempotency_key",
            "input",
        },
        name="agent request",
    )
    if request["protocol"] != AGENT_WIRE:
        raise ContractViolation("wrong agent protocol")
    for name in (
        "request_id",
        "execution_id",
        "agent_id",
        "session_proof",
        "action_id",
        "idempotency_key",
    ):
        member = request[name]
        if not isinstance(member, str) or not member or len(member) > 256:
            raise ContractViolation(f"invalid agent request member {name}")
    if not isinstance(request["input"], dict):
        raise ContractViolation("agent request input is not an object")
    if request["agent_id"] != bound_agent_id:
        raise ContractViolation("agent identity does not match private Grant binding")
    if not hmac.compare_digest(request["session_proof"], bound_session_proof):
        raise ContractViolation("agent session proof does not match private binding")
    return request


def application_exchange(
    config: dict[str, str], request: dict[str, Any], timeout: float
) -> dict[str, Any]:
    destination = split_address(config["app_address"], "app_address")
    message = {
        "protocol": APP_WIRE,
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
    wire = json.dumps(
        message, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode() + b"\n"
    with socket.create_connection(destination, timeout=timeout) as connection:
        connection.settimeout(timeout)
        connection.sendall(wire)
        line = connection.makefile("rb").readline(LIMIT + 1)
    if not line or len(line) > LIMIT or not line.endswith(b"\n"):
        raise ContractViolation("application response is not one bounded line")
    response = strict_json(line)
    if exposes_secret(response, config["credential"]):
        raise ContractViolation("application response exposes credential")
    return response


def error_message(
    request_id: Any,
    code: str,
    description: str,
    *,
    forwarded: bool,
) -> dict[str, Any]:
    return {
        "protocol": RUNTIME_WIRE,
        "request_id": request_id if isinstance(request_id, str) else "unknown",
        "status": "error" if forwarded else "rejected",
        "forwarded": forwarded,
        "error": {
            "code": code,
            "description": description,
            "retryable": False,
        },
    }


def process_agent_line(
    raw: bytes, config: dict[str, str], timeout: float
) -> dict[str, Any]:
    request_id: Any = "unknown"
    forwarded = False
    try:
        decoded = strict_json(raw)
        request_id = decoded.get("request_id")
        request = validated_agent_request(
            decoded,
            config["credential"],
            config["agent_id"],
            config["agent_session_proof"],
        )
        forwarded = True
        response = application_exchange(config, request, timeout)
        return {
            "protocol": RUNTIME_WIRE,
            "request_id": request["request_id"],
            "status": "completed",
            "forwarded": True,
            "result": response,
        }
    except ContractViolation as error:
        credential_problem = "credential" in str(error)
        return error_message(
            request_id,
            "credential_exposed" if credential_problem else "request_invalid",
            (
                "Agent-visible credential material is forbidden."
                if credential_problem
                else "The agent request or application response was invalid."
            ),
            forwarded=forwarded,
        )
    except (OSError, TimeoutError):
        return error_message(
            request_id,
            "service_unavailable",
            "The application is unavailable.",
            forwarded=True,
        )


class RemoteRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.connection.settimeout(  # type: ignore[attr-defined]
            self.server.request_timeout  # type: ignore[attr-defined]
        )
        line = self.rfile.readline(LIMIT + 1)
        if not line or len(line) > LIMIT or not line.endswith(b"\n"):
            response = error_message(
                "unknown",
                "request_invalid",
                "The agent request must be one bounded JSON line.",
                forwarded=False,
            )
        else:
            response = process_agent_line(
                line,
                self.server.private_config,  # type: ignore[attr-defined]
                self.server.request_timeout,  # type: ignore[attr-defined]
            )
        self.wfile.write(
            json.dumps(
                response,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode()
            + b"\n"
        )


class RemoteServer(socketserver.TCPServer):
    allow_reuse_address = True
    request_queue_size = 16


def serve(args: argparse.Namespace) -> int:
    config = private_config(args.config)
    address = split_address(args.listen, "listen")
    with RemoteServer(address, RemoteRequestHandler) as server:
        server.private_config = config  # type: ignore[attr-defined]
        server.request_timeout = args.timeout  # type: ignore[attr-defined]
        actual_host, actual_port = server.server_address[:2]
        print(
            json.dumps(
                {
                    "protocol": RUNTIME_WIRE,
                    "status": "listening",
                    "address": f"{actual_host}:{actual_port}",
                    "runtime_id": config["runtime_id"],
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
        if args.once:
            server.handle_request()
            return 0
        server.serve_forever(poll_interval=0.25)
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command")
    commands.add_parser("subject", help="evaluate one subject case from stdin")
    server = commands.add_parser("serve", help="serve the remote TCP bridge")
    server.add_argument("--config", type=Path, required=True)
    server.add_argument("--listen", required=True)
    server.add_argument("--timeout", type=float, default=5.0)
    server.add_argument("--once", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in (None, "subject"):
            raw = sys.stdin.buffer.read(LIMIT + 1)
            json.dump(
                subject(strict_json(raw)),
                sys.stdout,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            return 0
        if args.command == "serve":
            if args.timeout <= 0:
                raise ContractViolation("timeout must be positive")
            return serve(args)
        raise ContractViolation("unknown command")
    except (ContractViolation, OSError, UnicodeError, KeyError, TypeError, ValueError):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
