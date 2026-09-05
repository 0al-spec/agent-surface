#!/usr/bin/env python3
"""One bounded local runtime worker. No imports from SpecSpace; not an SDK.

Its stdin is a private runtime channel, never agent-visible. stdout is the
validated app response. The driver alone handles operator credentials/consent.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import re
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

ASP = "https://github.com/0al-spec/agent-surface/"
READ = "specspace.raw-idea.read"
PROPOSE = "specspace.raw-idea.propose"


def canonical(value):
    # Deliberately restricted experiment: no floating point schema members.
    if isinstance(value, dict):
        keys = sorted(value, key=lambda key: key.encode("utf-16-be"))
        return b"{" + b",".join(canonical(k) + b":" + canonical(value[k]) for k in keys) + b"}"
    if isinstance(value, list):
        return b"[" + b",".join(canonical(item) for item in value) + b"]"
    if type(value) is float or (type(value) is int and abs(value) > 9007199254740991):
        raise ValueError("Unsupported number")
    if isinstance(value, str) and any(0xD800 <= ord(c) <= 0xDFFF or 0xFDD0 <= ord(c) <= 0xFDEF
                                    or ord(c) & 0xFFFF in (0xFFFE, 0xFFFF) for c in value):
        raise ValueError("Invalid Unicode")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return "sha-256:" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")


def object_hash(kind, value):
    omit = {"manifest": {"surface_hash"}, "grant": {"grant_hash", "type"}}.get(kind, set())
    view = {key: item for key, item in value.items() if key not in omit}
    return digest(canonical({"domain": ASP + "hash/" + kind + "/v1", "object": view}))


def loads(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("Duplicate JSON member")
            result[k] = v
        return result
    def number(value):
        if value == "-0":
            raise ValueError("Negative zero")
        return int(value)
    def unsupported(_):
        raise ValueError("Unsupported number")
    value = json.loads(raw, object_pairs_hook=pairs, parse_int=number,
                       parse_float=unsupported, parse_constant=unsupported)
    canonical(value)
    return value


def request(origin, ca_file, path, *, token=None, operator=None, body=None, extra=None, lose_response=False):
    url = urlsplit(origin)
    if url.scheme != "https" or url.hostname != "127.0.0.1" or url.path or url.query or url.username:
        raise ValueError("Only an exact loopback HTTPS origin is supported")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if operator:
        headers.update(Authorization="Basic " + base64.b64encode(operator.encode()).decode(), Origin=origin)
    if body is not None:
        headers["Content-Type"] = "application/json"
    headers.update(extra or {})
    connection = http.client.HTTPSConnection(url.hostname, url.port, timeout=10,
                                             context=ssl.create_default_context(cafile=ca_file))
    try:
        connection.request("POST" if body is not None else "GET", path,
                           body=canonical(body) if body is not None else None, headers=headers)
        if lose_response:
            # Test fault at the client, no server-only bypass: see a first byte
            # but discard the entire status/body. The operation is ambiguous.
            if not connection.sock.recv(1):
                raise ValueError("No response before injected loss")
            return 0, {"outcome": "unknown"}, {}
        response = connection.getresponse()
        data = response.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024 or response.getheader("Cache-Control") != "no-store":
            raise ValueError("Invalid response boundary")
        if response.getheader("Content-Type", "").split(";")[0] != "application/json":
            raise ValueError("Unexpected content type")
        # http.client does not follow redirects and never forwards credentials.
        return response.status, loads(data), dict(response.getheaders())
    finally:
        connection.close()


def verify_identity(config, grant):
    artifact = loads(Path(config["identity_artifact"]).read_bytes())
    statement = artifact["statement"]
    if set(artifact) != {"statement", "signature"} or set(statement) != {
            "issuer", "subject", "issued_at", "expires_at", "public_key_der"}:
        raise ValueError("Identity format mismatch")
    if not statement["issued_at"] <= time.time() < statement["expires_at"] <= statement["issued_at"] + 3600:
        raise ValueError("Identity stale")
    evidence = grant["delegate"]["identity_evidence"]
    key = base64.b64decode(statement["public_key_der"], validate=True)
    if len(key) != 44 or key[:12] != bytes.fromhex("302a300506032b6570032100"):
        raise ValueError("Unsupported subject key")
    if (evidence["issuer"] != statement["issuer"] or evidence["subject"] != statement["subject"] or
            evidence["artifact_digest"]["value"] != digest(canonical(artifact)) or evidence["key_binding"]["value"] != digest(key)):
        raise ValueError("Identity binding mismatch")
    with tempfile.TemporaryDirectory(prefix="asp-runtime-verifier-") as directory:
        data, signature = Path(directory) / "statement", Path(directory) / "signature"
        data.write_bytes(b"specspace-asp-draft-identity-v1\0" + canonical(statement))
        signature.write_bytes(base64.b64decode(artifact["signature"], validate=True))
        result = subprocess.run(["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", config["issuer_public_key"],
                                 "-in", str(data), "-sigfile", str(signature)], capture_output=True, timeout=5)
        if result.returncode:
            raise ValueError("Unverified identity")


def validate(schema, value):
    """Exactly the schema vocabulary used by this experiment; fail on others."""
    if set(schema) - {"$schema", "type", "additionalProperties", "properties", "required", "items", "const", "pattern", "minLength", "maxLength"}:
        raise ValueError("Unsupported schema vocabulary")
    if "const" in schema and value != schema["const"]:
        raise ValueError("Constant mismatch")
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict) or schema["additionalProperties"] is not False or set(value) != set(schema["required"]):
            raise ValueError("Object schema mismatch")
        for key, item in value.items():
            validate(schema["properties"][key], item)
    elif kind == "array":
        if not isinstance(value, list):
            raise ValueError("Array schema mismatch")
        for item in value:
            validate(schema["items"], item)
    elif kind == "string":
        if not isinstance(value, str) or not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 65536):
            raise ValueError("String schema mismatch")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ValueError("String pattern mismatch")
    elif kind is not None or "const" not in schema:
        raise ValueError("Unsupported schema type")


def forward(config, path, body, *, lose_response=False):
    grant, origin = config["grant"], config["origin"]
    def get(endpoint):
        status, value, _ = request(origin, config["ca_file"], endpoint, token=config["credential"])
        if status != 200:
            raise ValueError("Authority check failed")
        return value
    manifest = get("/.well-known/agent-surface.json")
    if manifest["protocol"] != "agent-surface/0.1" or manifest["surface_hash"] != object_hash("manifest", manifest):
        raise ValueError("Invalid manifest")
    if manifest["surface_mode"] != "proposal_only" or {a["id"] for a in manifest["actions"]} != {READ, PROPOSE}:
        raise ValueError("Unexpected surface inventory")
    if grant["grant_hash"] != object_hash("grant", grant) or grant["resource_server"]["surface_hash"] != manifest["surface_hash"]:
        raise ValueError("Grant/surface mismatch")
    if datetime.now(timezone.utc) >= datetime.fromisoformat(grant["constraints"]["expires_at"].replace("Z", "+00:00")):
        raise ValueError("Grant expired")
    if (grant["credential_profile"] != "compatibility_bearer" or grant["constraints"]["credential_release"] != {"mode": "deny"} or
            grant["credential_binding"] != {"method": "bearer", "runtime_id": grant["delegate"]["runtime"],
                                            "agent_id": grant["delegate"]["agent"], "identity_evidence": grant["delegate"]["identity_evidence"]}):
        raise ValueError("Credential binding mismatch")
    if grant["locations"] != [origin + "/asp/actions"] or manifest["agent_api"]["credential_audience"] != origin + "/asp":
        raise ValueError("Audience mismatch")
    schemas = {}
    for action in manifest["actions"]:
        if action["side_effect"] is not False or "effects" in action or action["execution"]["mode"] not in ("read", "propose"):
            raise ValueError("Proposal-only bound violated")
        expected = "read" if action["id"] == READ else "propose"
        if action["input_schema"] != origin + "/asp/schemas/" + expected + "-input":
            raise ValueError("Unpinned schema endpoint")
        schema = get("/asp/schemas/" + expected + "-input")
        schemas[action["id"]] = schema
        if action["input_schema_hash"] != object_hash("action-input-schema", schema):
            raise ValueError("Schema hash mismatch")
    verify_identity(config, grant)
    introspection = get("/asp/grant")
    status = introspection["identity_status"]
    if (introspection["grant"] != grant or status["identity_evidence"] != grant["delegate"]["identity_evidence"] or
            status["state"] != "active" or status["valid_until"] < int(time.time())):
        raise ValueError("Stale current authority")
    if path not in ("/asp/sessions", "/asp/actions", "/asp/approval-request"):
        raise ValueError("Out-of-scope endpoint")
    p = body["payload"]
    if (p["grant_id"], p["grant_hash"]) != (grant["grant_id"], grant["grant_hash"]):
        raise ValueError("Request tuple mismatch")
    if body["type"] == "action.request":
        action_id = p["action_id"]
        if action_id not in grant["actions"] or action_id not in grant["scopes"]:
            raise ValueError("Action not granted")
        if p["input"]["workspace_id"] != grant["constraints"]["workspace_id"]:
            raise ValueError("Workspace not granted")
        if p["input_hash"] != object_hash("action-input", p["input"]):
            raise ValueError("Input changed")
        validate(schemas[action_id], p["input"])
        if p["execution"]["mode"] != ("read" if action_id == READ else "propose"):
            raise ValueError("Mode changed")
        if action_id == PROPOSE and (not isinstance(p.get("idempotency_key"), str)
                                      or not p["idempotency_key"]):
            raise ValueError("Invalid request idempotency key")
    headers = {}
    if "trace_id" in p:
        headers["traceparent"] = "00-" + p["trace_id"] + "-" + p["span_id"] + "-00"
    if "idempotency_key" in p:
        headers["Idempotency-Key"] = p["idempotency_key"]
    code, result, response_headers = request(origin, config["ca_file"], path, token=config["credential"], body=body,
                                             extra=headers, lose_response=lose_response)
    if code == 200 and path == "/asp/actions":
        r = result["payload"]
        mode = "read" if p["action_id"] == READ else "propose"
        declaration = next(action for action in manifest["actions"] if action["id"] == p["action_id"])
        if declaration["output_schema"] != origin + "/asp/schemas/" + mode + "-output":
            raise ValueError("Output schema endpoint changed")
        validate(get("/asp/schemas/" + mode + "-output"), r["output"])
        for key in ("session_id", "session_generation", "grant_id", "grant_hash", "surface_hash", "action_id", "execution", "input_hash"):
            if r[key] != p[key]:
                raise ValueError("App response binding mismatch")
        if p["action_id"] == PROPOSE and (not isinstance(p.get("idempotency_key"), str)
                                           or not p["idempotency_key"]
                                           or r.get("idempotency_key") != p["idempotency_key"]):
            raise ValueError("App response idempotency binding mismatch")
        if response_headers.get("traceparent") != "00-" + r["trace_id"] + "-" + r["span_id"] + "-00":
            raise ValueError("Trace binding mismatch")
    return {"status": code, "body": result}


def agent_proposal(config, read_output, text, request_id):
    verify_identity(config, config["grant"])
    challenge = secrets.token_urlsafe(32)
    agent_input = {"challenge": challenge, "read_output": read_output, "text": text, "request_id": request_id}
    child = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("draft_agent.py")), config["agent_key"]],
                           input=canonical(agent_input), capture_output=True, timeout=10,
                           env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    if child.returncode or len(child.stdout) > 65536:
        raise ValueError("Agent failed")
    result = loads(child.stdout)
    if not isinstance(result, dict) or set(result) != {"input", "signature"} or not isinstance(result["input"], dict):
        raise ValueError("Malformed agent result")
    if set(result["input"]) != {"workspace_id", "snapshot_hash", "request_id", "idea_text"}:
        raise ValueError("Unexpected agent input shape")
    artifact = loads(Path(config["identity_artifact"]).read_bytes())
    with tempfile.TemporaryDirectory(prefix="asp-agent-verification-") as directory:
        root = Path(directory)
        key, signed, sig = root / "subject.der", root / "signed", root / "signature"
        key.write_bytes(base64.b64decode(artifact["statement"]["public_key_der"], validate=True))
        signed.write_bytes(canonical({"challenge": challenge, "input": result["input"]}))
        sig.write_bytes(base64.b64decode(result["signature"], validate=True))
        verification = subprocess.run(["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-keyform", "DER",
            "-inkey", str(key), "-in", str(signed), "-sigfile", str(sig)], capture_output=True, timeout=5)
        if verification.returncode:
            raise ValueError("Agent key possession failed")
    return result["input"]


if __name__ == "__main__":
    try:
        work = loads(sys.stdin.buffer.read(131073))
        if work.get("operation") == "agent_proposal":
            result = agent_proposal(work["config"], work["read_output"], work["text"], work["request_id"])
        else:
            result = forward(work["config"], work["path"], work["body"], lose_response=work.get("lose_response", False))
        sys.stdout.buffer.write(canonical(result))
    except Exception:
        # Never include stdin, credentials, paths or private application data.
        sys.stderr.write("Runtime validation or transport failed\n")
        raise SystemExit(1)
