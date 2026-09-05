import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import runtime
from runtime import canonical, loads, object_hash, validate

_MISSING = object()
_OMIT = object()


class RuntimePrimitiveTests(unittest.TestCase):
    def test_normative_hash_vectors(self):
        self.assertEqual(object_hash("grant", {"grant_id": "grant_123", "scopes": ["read"]}),
                         "sha-256:Xbq37_fP9PBiWI3Bv7Ch0t8TV5ikJGm55MxncSeA38Y")
        self.assertEqual(object_hash("manifest", {"a": "x", "z": 1, "surface_hash": "omitted"}),
                         "sha-256:Mckhl9gi8ePkXnuOJtPFNE1pe9LhilOGu1OgzxsXb8A")
        self.assertEqual(canonical({"\ue000": 1, "😀": 2}), '{"😀":2,"\ue000":1}'.encode())

    def test_invalid_json_is_not_repaired(self):
        for raw in ('{"a":1,"a":2}', '-0', '1e400', 'NaN', '1.5', '"\\ud800"', '"\\uffff"', '9007199254740992'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                loads(raw)

    def test_bounded_schema_checks_reject_unknown_shape(self):
        schema = {"type": "object", "additionalProperties": False, "required": ["value"],
                  "properties": {"value": {"type": "string", "maxLength": 3}}}
        validate(schema, {"value": "yes"})
        for value in ({}, {"value": "long"}, {"value": 1}, {"value": "yes", "commit": True}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate(schema, value)
        with self.assertRaises(ValueError):
            validate({"$ref": "https://other.invalid/schema"}, {})


class ForwardResponseBindingTests(unittest.TestCase):
    """Exercise response binding after all forward() authority checks."""

    def setUp(self):
        self.origin = "https://127.0.0.1:9443"
        output_schema = {"type": "object", "additionalProperties": False,
                         "required": ["value"], "properties": {"value": {"type": "string"}}}
        input_schema = {"type": "object", "additionalProperties": False,
                        "required": ["workspace_id"], "properties": {"workspace_id": {"type": "string"}}}
        self.manifest = {
            "protocol": "agent-surface/0.1", "surface_mode": "proposal_only",
            "agent_api": {"credential_audience": self.origin + "/asp"},
            "actions": [
                {"id": runtime.READ, "side_effect": False, "execution": {"mode": "read"},
                 "input_schema": self.origin + "/asp/schemas/read-input",
                 "input_schema_hash": object_hash("action-input-schema", input_schema),
                 "output_schema": self.origin + "/asp/schemas/read-output"},
                {"id": runtime.PROPOSE, "side_effect": False, "execution": {"mode": "propose", "persisted": True},
                 "idempotency": "required",
                 "input_schema": self.origin + "/asp/schemas/propose-input",
                 "input_schema_hash": object_hash("action-input-schema", input_schema),
                 "output_schema": self.origin + "/asp/schemas/propose-output"},
            ],
        }
        self.manifest["surface_hash"] = object_hash("manifest", self.manifest)
        evidence = {"issuer": "issuer", "subject": "subject"}
        self.grant = {
            "grant_id": "grant", "resource_server": {"surface_hash": self.manifest["surface_hash"]},
            "credential_profile": "compatibility_bearer", "constraints": {
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                "credential_release": {"mode": "deny"}, "workspace_id": "workspace"},
            "credential_binding": {"method": "bearer", "runtime_id": "runtime", "agent_id": "agent",
                                   "identity_evidence": evidence},
            "delegate": {"runtime": "runtime", "agent": "agent", "identity_evidence": evidence},
            "locations": [self.origin + "/asp/actions"], "actions": [runtime.READ, runtime.PROPOSE],
            "scopes": [runtime.READ, runtime.PROPOSE],
        }
        self.grant["grant_hash"] = object_hash("grant", self.grant)
        self.config = {"grant": self.grant, "origin": self.origin, "ca_file": "unused", "credential": "token",
                       "identity_artifact": "unused", "issuer_public_key": "unused"}

    def _case(self, action, response_key=_MISSING, request_key=_MISSING):
        self.action_calls = []
        value = {"workspace_id": "workspace"}
        key = "idem-test" if action == runtime.PROPOSE else None
        if request_key is _OMIT:
            key = None
        elif request_key is not _MISSING:
            key = request_key
        payload = {"session_id": "session", "session_generation": 1, "trace_id": "a" * 32,
                   "span_id": "b" * 16, "grant_id": self.grant["grant_id"],
                   "grant_hash": self.grant["grant_hash"], "surface_hash": self.manifest["surface_hash"],
                   "action_id": action, "input": value, "input_hash": object_hash("action-input", value),
                   "execution": {"mode": "read" if action == runtime.READ else "propose", "execution_id": "exec"}}
        if key is not None or request_key is None:
            payload["idempotency_key"] = key
        response = dict(payload)
        response["output"] = {"value": "ok"}
        if response_key is not _MISSING:
            response.pop("idempotency_key", None)
            if response_key is not _OMIT:
                response["idempotency_key"] = response_key
        body = {"type": "action.request", "payload": payload}
        responses = {
            "/.well-known/agent-surface.json": (200, self.manifest, {}),
            "/asp/schemas/read-input": (200, self._input_schema(), {}),
            "/asp/schemas/propose-input": (200, self._input_schema(), {}),
            "/asp/schemas/read-output": (200, self._output_schema(), {}),
            "/asp/schemas/propose-output": (200, self._output_schema(), {}),
            "/asp/grant": (200, {"grant": self.grant, "identity_status": {
                "identity_evidence": self.grant["delegate"]["identity_evidence"], "state": "active",
                "valid_until": 2 ** 31}}, {}),
            "/asp/actions": (200, {"type": "action.result", "payload": response},
                              {"traceparent": "00-" + response["trace_id"] + "-" + response["span_id"] + "-00"}),
        }
        def fake_request(_origin, _ca_file, path, **kwargs):
            if path == "/asp/actions":
                self.action_calls.append(kwargs)
            return responses[path]
        return body, fake_request

    @staticmethod
    def _input_schema():
        return {"type": "object", "additionalProperties": False, "required": ["workspace_id"],
                "properties": {"workspace_id": {"type": "string"}}}

    @staticmethod
    def _output_schema():
        return {"type": "object", "additionalProperties": False, "required": ["value"],
                "properties": {"value": {"type": "string"}}}

    def test_propose_matching_idempotency_key_is_accepted(self):
        body, fake = self._case(runtime.PROPOSE)
        with patch.object(runtime, "request", side_effect=fake), patch.object(runtime, "verify_identity"):
            self.assertEqual(runtime.forward(self.config, "/asp/actions", body)["status"], 200)
        self.assertEqual(self.action_calls[0]["extra"]["Idempotency-Key"], "idem-test")

    def test_propose_missing_or_mismatching_idempotency_key_is_rejected(self):
        for response_key in (_OMIT, "idem-other"):
            with self.subTest(response_key=response_key):
                body, fake = self._case(runtime.PROPOSE, response_key)
                with patch.object(runtime, "request", side_effect=fake), patch.object(runtime, "verify_identity"), self.assertRaisesRegex(ValueError, "idempotency binding"):
                    runtime.forward(self.config, "/asp/actions", body)
                self.assertEqual(len(self.action_calls), 1)

    def test_propose_invalid_request_idempotency_key_is_rejected_before_post(self):
        for request_key in (_OMIT, None, "", 7):
            with self.subTest(request_key=request_key):
                body, fake = self._case(runtime.PROPOSE, response_key="idem-response", request_key=request_key)
                with patch.object(runtime, "request", side_effect=fake), patch.object(runtime, "verify_identity"), self.assertRaisesRegex(ValueError, "request idempotency key"):
                    runtime.forward(self.config, "/asp/actions", body)
                self.assertEqual(self.action_calls, [])

    def test_read_response_does_not_require_idempotency_key(self):
        body, fake = self._case(runtime.READ, None)
        with patch.object(runtime, "request", side_effect=fake), patch.object(runtime, "verify_identity"):
            self.assertEqual(runtime.forward(self.config, "/asp/actions", body)["status"], 200)
