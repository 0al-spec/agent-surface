#!/usr/bin/env python3
"""Reproduce the isolated SpecSpace HTTPS draft scenario with real processes.

--mock-user is for automated verification, never a human-use claim.
The default prompts separately for Grant consent and exact draft approval.
"""
from __future__ import annotations

import argparse
import base64
import copy
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time

from runtime import READ, PROPOSE, canonical, loads, object_hash, request
from mock_user import DRAFT_ID, DRAFT_TEXT, MockUser


def write(path, value):
    path.write_bytes(canonical(value))
    path.chmod(0o600)


def openssl(*args):
    return subprocess.run(["openssl", *map(str, args)], capture_output=True, check=True, timeout=10).stdout


def generate(root):
    openssl("req", "-x509", "-newkey", "ed25519", "-nodes", "-keyout", root / "tls.key", "-out", root / "tls.crt",
            "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1", "-days", "1")
    for name in ("issuer", "agent"):
        openssl("genpkey", "-algorithm", "ED25519", "-out", root / (name + ".key"))
        openssl("pkey", "-in", root / (name + ".key"), "-pubout", "-out", root / (name + ".pub"))
    public = openssl("pkey", "-in", root / "agent.key", "-pubout", "-outform", "DER")
    now = int(time.time())
    statement = {"issuer": "specspace-local-experiment", "subject": "registered-demo-agent",
                 "issued_at": now, "expires_at": now + 3600, "public_key_der": base64.b64encode(public).decode()}
    (root / "statement").write_bytes(b"specspace-asp-draft-identity-v1\0" + canonical(statement))
    signature = openssl("pkeyutl", "-sign", "-rawin", "-inkey", root / "issuer.key", "-in", root / "statement")
    write(root / "identity.json", {"statement": statement, "signature": base64.b64encode(signature).decode()})
    # The application and runtime verify with public keys, not the issuer key.
    (root / "issuer.key").unlink()
    for item in root.iterdir():
        item.chmod(0o600)


def runtime(work):
    process = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("runtime.py"))],
                             input=canonical(work), capture_output=True, timeout=30,
                             env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    if process.returncode:
        raise RuntimeError("Separate runtime worker failed (private input withheld)")
    return loads(process.stdout)


class Scenario:
    def __init__(self, root, checkout, python, mock_user):
        self.root, self.checkout, self.python = root, checkout, python
        self.user = MockUser() if mock_user else None
        self.user_decisions = []
        generate(root)
        (root / "state").mkdir(mode=0o700)
        (root / "dialogs").mkdir(mode=0o700)
        self.password = secrets.token_urlsafe(36)
        (root / "operator-password").write_text(self.password)
        (root / "operator-password").chmod(0o600)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.origin = "https://127.0.0.1:" + str(self.port)
        self.config = {"tls_cert": str(root / "tls.crt"), "tls_key": str(root / "tls.key"),
                       "issuer_public_key": str(root / "issuer.pub"), "identity_artifact": str(root / "identity.json"),
                       "workspace_id": "asp-draft-demo", "runtime_id": "local-runtime", "agent_id": "local-agent"}
        write(root / "app-config.json", self.config)
        self.process = None
        self.log = (root / "server.log").open("wb")

    def start(self):
        self.process = subprocess.Popen([str(self.python), "-B", "-m", "viewer.server", "--host", "127.0.0.1",
            "--port", str(self.port), "--dialog-dir", str(self.root / "dialogs"),
            "--specspace-state-dir", str(self.root / "state"), "--enable-operator-auth",
            "--operator-auth-password-file", str(self.root / "operator-password"),
            "--operator-auth-allowed-origin", self.origin,
            "--asp-draft-config", str(self.root / "app-config.json")], cwd=self.checkout,
            stdout=self.log, stderr=self.log, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("SpecSpace startup failed; inspect the run-local server.log")
            try:
                code, result, _ = self.http("/.well-known/agent-surface.json")
                if code == 200:
                    self.manifest = result
                    return
            except (OSError, ValueError):
                pass
            time.sleep(0.05)
        raise RuntimeError("SpecSpace startup timed out")

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None

    def http(self, path, *, body=None, operator=False, token=None, extra=None):
        return request(self.origin, str(self.root / "tls.crt"), path,
                       operator="operator:" + self.password if operator else None,
                       token=token, body=body, extra=extra)

    def consent(self):
        code, consent, _ = self.http("/asp/operator/consent", operator=True)
        assert code == 200
        if self.user is None:
            print("Local synthetic workspace; Compatibility Bearer; 600-second maximum; no code identity attestation.")
            print(canonical(consent).decode(), flush=True)
            if input("Issue the displayed read/propose Grant? Type GRANT: ") != "GRANT":
                raise RuntimeError("Grant consent declined")
        return consent

    def issue(self, consent, ttl=300):
        body = {"surface_hash": consent["surface_hash"], "identity_evidence_hash": consent["identity"]["identity_evidence_hash"],
                "workspace_id": "asp-draft-demo", "runtime_id": "local-runtime", "agent_id": "local-agent",
                "expires_in": ttl, "accept": True}
        if self.user is not None:
            self.require_decision(self.user.grant(consent, body, self.manifest["surface_hash"]))
        code, issued, _ = self.http("/asp/operator/grant", operator=True, body=body)
        assert code == 200, issued
        config = {"origin": self.origin, "ca_file": str(self.root / "tls.crt"),
                  "issuer_public_key": str(self.root / "issuer.pub"), "identity_artifact": str(self.root / "identity.json"),
                  "agent_key": str(self.root / "agent.key"), "grant": issued["grant"], "credential": issued["credential"]}
        return config

    def require_decision(self, decision):
        self.user_decisions.append(decision)
        if decision["accept"] is not True:
            raise RuntimeError("Mock user declined " + decision["stage"] + ": " + decision["reason"])

    def session(self, config, session_id):
        grant = config["grant"]
        self.session_id = session_id
        p = {"session_id": session_id, "session_generation": 1, "trace_id": secrets.token_hex(16), "span_id": secrets.token_hex(8),
             "grant_id": grant["grant_id"], "grant_hash": grant["grant_hash"], "runtime_id": "local-runtime", "agent_id": "local-agent",
             "identity_evidence_hash": object_hash("agent-identity-evidence", grant["delegate"]["identity_evidence"]),
             "initiated_by": "runtime", "surface": {k: self.manifest[k] for k in ("app_id", "surface_version", "surface_hash")},
             "task": {"kind": "raw-idea.draft", "goal": "Prepare a private idea draft", "inputs": {"workspace_id": "asp-draft-demo"}}}
        result = runtime({"config": config, "path": "/asp/sessions", "body": {"type": "session.start", "payload": p}})
        assert result["status"] == 200 and result["body"]["payload"]["state"] == "active"

    def action(self, config, action, value):
        grant = config["grant"]
        p = {"session_id": self.session_id, "session_generation": 1, "trace_id": secrets.token_hex(16), "span_id": secrets.token_hex(8),
             "grant_id": grant["grant_id"], "grant_hash": grant["grant_hash"], "surface_hash": self.manifest["surface_hash"],
             "action_id": action, "input": value, "input_hash": object_hash("action-input", value),
             "execution": {"mode": "read" if action == READ else "propose", "execution_id": "exec-" + secrets.token_hex(16)}}
        if action == PROPOSE:
            p["idempotency_key"] = "idem-" + secrets.token_hex(16)
        return {"type": "action.request", "payload": p}

    def send(self, config, body, **options):
        return runtime({"config": config, "path": "/asp/actions", "body": body, **options})

    def raw_action(self, config, body):
        p = body["payload"]
        headers = {"traceparent": "00-" + p["trace_id"] + "-" + p["span_id"] + "-00"}
        if "idempotency_key" in p:
            headers["Idempotency-Key"] = p["idempotency_key"]
        return self.http("/asp/actions", body=body, token=config["credential"], extra=headers)

    def approve(self, config, proposal):
        prepared = runtime({"config": config, "path": "/asp/approval-request", "body": proposal})
        assert prepared["status"] == 200
        if self.user is not None:
            self.require_decision(self.user.approve(prepared["body"], proposal))
        else:
            print("Persist this exact private draft? This does not submit or execute it:")
            print(canonical(prepared["body"]).decode(), flush=True)
            if input("Type APPROVE: ") != "APPROVE":
                raise RuntimeError("Draft approval declined")
        code, result, _ = self.http("/asp/operator/approve", operator=True, body={"approval_id": prepared["body"]["approval_id"],
            "input_hash": proposal["payload"]["input_hash"], "accept": True})
        assert code == 200, result

    def native_save(self, request_id, text, workspace="asp-draft-demo"):
        code, result, _ = self.http("/api/v1/real-idea-entry-requests?workspace=" + workspace, operator=True,
            body={"workspace_id": workspace, "request_id": request_id, "idea_text": text, "status": "draft"})
        assert code == 200, result

    def run(self):
        self.start()
        consent = self.consent()
        config = self.issue(consent)
        self.session(config, "session-demo")
        self.native_save("foreign-draft", "foreign-workspace-secret", "other-workspace")
        read_request = self.action(config, READ, {"workspace_id": "asp-draft-demo"})
        read = self.send(config, read_request)
        assert read["status"] == 200 and read["body"]["payload"]["output"]["drafts"] == []
        proposed_input = runtime({"operation": "agent_proposal", "config": config,
            "read_output": read["body"]["payload"]["output"], "request_id": DRAFT_ID,
            "text": DRAFT_TEXT})
        proposal = self.action(config, PROPOSE, proposed_input)
        assert self.send(config, proposal)["body"]["payload"]["code"] == "approval_required"
        self.approve(config, proposal)
        # Response loss happens on the real HTTPS socket, not by mocking save.
        ambiguous = self.send(config, proposal, lose_response=True)
        assert ambiguous == {"status": 0, "body": {"outcome": "unknown"}}
        first = self.send(config, proposal)
        assert first["status"] == 200 and first["body"]["payload"]["output"] == {
            "workspace_id": "asp-draft-demo", "request_id": "adoption-draft", "idea_text": proposed_input["idea_text"], "status": "draft"}
        self.native_save("adoption-draft", "Scripted native edit after ASP persistence")
        assert self.send(config, proposal) == first
        code, native, _ = self.http("/api/v1/real-idea-entry-requests?workspace=asp-draft-demo", operator=True)
        assert code == 200 and len(native["requests"]) == 1
        assert native["requests"][0]["idea_text"] == "Scripted native edit after ASP persistence"
        negative = copy.deepcopy(proposal)
        negative["payload"]["input"]["idea_text"] = "Changed by caller"
        assert self.raw_action(config, negative)[1]["payload"]["code"] == "integrity_mismatch"
        negative["payload"]["input_hash"] = object_hash("action-input", negative["payload"]["input"])
        assert self.raw_action(config, negative)[1]["payload"]["code"] == "idempotency_conflict"
        wrong_workspace = copy.deepcopy(read_request)
        wrong_workspace["payload"]["input"]["workspace_id"] = "other-workspace"
        wrong_workspace["payload"]["input_hash"] = object_hash("action-input", wrong_workspace["payload"]["input"])
        assert self.raw_action(config, wrong_workspace)[1]["payload"]["code"] == "scope_denied"
        # Real process restart preserves original output and cannot resurrect authority.
        self.stop()
        self.start()
        assert self.send(config, proposal) == first
        code, _, _ = self.http("/asp/operator/revoke", operator=True, body={"grant_id": config["grant"]["grant_id"]})
        assert code == 200 and self.raw_action(config, proposal)[1]["payload"]["code"] == "grant_revoked"
        if self.user is not None:
            expiring = self.issue(self.consent(), ttl=1)
            time.sleep(1.05)
            assert self.http("/asp/grant", token=expiring["credential"])[1]["payload"]["code"] == "grant_expired"
        return {"approval": "mock_user" if self.user is not None else "human_cli",
                "user_decisions": self.user_decisions,
                "transport": "direct_https_loopback", "credential_profile": "compatibility_bearer",
                "storage": "sqlite_shared_native_transaction", "saved_status": "draft",
                "checks": ["independent_runtime_process", "agent_key_possession", "scoped_read", "app_approval",
                           "transport_response_loss", "exact_retry", "native_edit_preserved", "process_restart",
                           "changed_input_denied", "foreign_workspace_denied", "revocation_before_retry"],
                "conformance_claim": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--specspace-python", type=Path, required=True)
    parser.add_argument("--mock-user", "--synthetic-approval", dest="mock_user", action="store_true",
                        help="Use a deterministic consent policy; --synthetic-approval is a compatibility alias")
    parser.add_argument("--expected-commit", help="Require this exact clean trusted SpecSpace commit")
    args = parser.parse_args()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=args.checkout, capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=args.checkout, capture_output=True, text=True, check=True).stdout
    if dirty or (args.expected_commit is not None and revision != args.expected_commit):
        raise SystemExit("Use the selected clean SpecSpace checkout; do not reset or clean another task's changes.")
    version = openssl("version").decode()
    if not version.startswith("OpenSSL 3."):
        raise SystemExit("This experiment requires OpenSSL 3.x on PATH (not macOS LibreSSL).")
    old_mask = os.umask(0o077)
    try:
        with tempfile.TemporaryDirectory(prefix="asp-https-draft-") as directory:
            demo = Scenario(Path(directory), args.checkout.resolve(), args.specspace_python.absolute(), args.mock_user)
            try:
                report = demo.run()
                print(canonical(report).decode())
            finally:
                demo.stop()
                demo.log.close()
    finally:
        os.umask(old_mask)


if __name__ == "__main__":
    main()
