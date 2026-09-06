"""Offline construction example, NOT an issuer, verifier, transport or SDK.

All identity material is synthetic and unusable as verified evidence. Printing
these objects does not confirm consent or create an application session.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
from copy import deepcopy

import rfc8785

ASP = "https://github.com/0al-spec/agent-surface/"
ORIGIN = "https://127.0.0.1:7443"
ACTION = "calculation.propose"
PROFILE_ROOT = "https://calcu.example.invalid/profiles/"
IDENTITY_DOMAIN = ASP + "hash/agent-identity-evidence/v1"


def digest(value: bytes) -> str:
    return "sha-256:" + base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode()


def object_hash(domain: str, value: dict) -> str:
    # Reuse the repository's RFC 8785 dependency, not a new canonicalizer.
    # These are constructed values, not untrusted raw JSON (which needs its
    # own duplicate-member and lexical-number rejection before construction).
    def reject_negative_zero(item):
        if isinstance(item, float) and item == 0 and math.copysign(1, item) < 0:
            raise ValueError("ASP rejects negative zero")
        if isinstance(item, dict):
            for child in item.values():
                reject_negative_zero(child)
        elif isinstance(item, list):
            for child in item:
                reject_negative_zero(child)

    reject_negative_zero(value)
    return digest(rfc8785.dumps({"domain": domain, "object": value}))


def build_example() -> dict:
    input_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": ORIGIN + "/schemas/calculation-input.json",
        "type": "object",
        "properties": {
            "operator": {"enum": ["add", "subtract", "multiply", "divide"]},
            "left": {"type": "number"},
            "right": {"type": "number"},
        },
        "required": ["operator", "left", "right"],
        "additionalProperties": False,
    }
    output_schema = deepcopy(input_schema)
    output_schema["$id"] = ORIGIN + "/schemas/calculation-output.json"
    output_schema["properties"]["result"] = {"type": "number"}
    output_schema["required"].append("result")
    # This is deliberately NOT an Agent Passport or a signature/key fixture.
    # Digests are well-formed; no verifier may infer identity from them.
    synthetic_artifact = b"calcu offline example: NOT A SIGNED AGENT PASSPORT\n"
    identity = {
        "profile": ASP + "profiles/agent-identity-evidence/v1",
        "format_profile": ASP + "profiles/agent-passport-minimal/v1",
        "artifact_digest": {
            "profile": ASP + "hash/agent-passport-artifact/v1",
            "value": digest(b"ASP agent-passport artifact v1\0" + synthetic_artifact),
        },
        "issuer": "https://calcu.example.invalid/identity-issuer",
        "subject": "synthetic-calcu-adapter",
        "verification_profile": PROFILE_ROOT + "unimplemented-verification/v1",
        "key_binding": {
            "profile": PROFILE_ROOT + "unimplemented-key-binding/v1",
            "value": digest(b"NOT A PUBLIC KEY"),
        },
        "lifecycle": {
            "freshness_profile": PROFILE_ROOT + "unimplemented-freshness/v1",
            "status_profile": PROFILE_ROOT + "unimplemented-status/v1",
            "status_ref": "synthetic-unresolved-status",
        },
    }
    exposure = {
        "classes": ["calculation.sample"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": True},
    }
    manifest = {
        "protocol": "agent-surface/0.1",
        "app_id": "calcu.offline-example",
        "issuer": ORIGIN,
        "surface_url": ORIGIN + "/.well-known/agent-surface.json",
        "surface_version": "offline-example-2026-09-06",
        "surface_mode": "proposal_only",
        "auth": {},  # App-issued endpoint binding; no OAuth mechanism advertised.
        "audit": {},  # No optional receipt producer/signing requirement selected.
        "compatibility": {
            "min_runtime": "application-runtime/0.1",
            "schema_dialect": input_schema["$schema"],
            "agent_identity_evidence_profiles": [{
                "profile": identity["profile"],
                "format_profile": identity["format_profile"],
                "artifact_digest_profile": identity["artifact_digest"]["profile"],
                "verification_profiles": [identity["verification_profile"]],
                "key_binding_profiles": [identity["key_binding"]["profile"]],
                "freshness_profiles": [identity["lifecycle"]["freshness_profile"]],
                "status_profiles": [identity["lifecycle"]["status_profile"]],
                "migration_profiles": [],
                "max_artifact_bytes": 262144,
            }],
        },
        "agent_api": {
            "credential_audience": ORIGIN + "/agent-api",
            "grant_request_url": ORIGIN + "/agent-grants/request",
            "grant_introspection_url": ORIGIN + "/agent-grants/introspect",
            "grant_revocation_url": ORIGIN + "/agent-grants/revoke",
            "action_url": ORIGIN + "/agent-actions",
            "session_control_url": ORIGIN + "/agent-sessions/control",
        },
        "revocation": {
            "grant_management_url": ORIGIN + "/settings/agent-grants",
            "grant_revocation_url": ORIGIN + "/agent-grants/revoke",
        },
        "scopes": [{"id": ACTION, "description": "Return a non-persisted calculation artifact."}],
        "data_classes": [{
            "id": "calculation.sample",
            "classification": "private",
            "label": "Offline calculation sample",
            "description": "Conservative handling of this fixed synthetic example, not arbitrary user numbers.",
        }],
        "resources": [],
        "actions": [{
            "id": ACTION,
            "scope": ACTION,
            "risk": "propose",
            "side_effect": False,
            "approval": "none",
            "execution": {"mode": "propose", "operation_id": "calculation.evaluate", "persisted": False},
            "input_schema": input_schema["$id"],
            "input_schema_hash": object_hash(ASP + "hash/action-input-schema/v1", input_schema),
            "output_schema": output_schema["$id"],
            "data_exposure": exposure,
        }],
        "events": [],
    }
    manifest["surface_hash"] = object_hash(ASP + "hash/manifest/v1", manifest)
    request = {
        "delegate": {"runtime": "calcu-runtime-example", "agent": "calcu-adapter-example", "identity_evidence": deepcopy(identity)},
        "resource_server": {key: manifest[key] for key in ("app_id", "issuer", "surface_version", "surface_hash")},
        "locations": [manifest["agent_api"]["action_url"]],
        "actions": [ACTION],
        "scopes": [ACTION],
        "constraints": {
            "expires_at": "2026-09-06T00:01:00Z",
            "credential_release": {"mode": "deny"},
        },
        "credential_profile": "compatibility_bearer",
        "audit": {},  # Required container, without optional receipt requirements.
    }
    projection = [{"source": {"kind": "action", "id": ACTION}, **deepcopy(exposure)}]
    grant = {
        **deepcopy(request),
        "grant_id": "calcu-grant-example",
        "subject": {"user": "calcu-example-user"},
        "credential_binding": {
            "method": "bearer",
            "runtime_id": request["delegate"]["runtime"],
            "agent_id": request["delegate"]["agent"],
            "identity_evidence": deepcopy(identity),
        },
        "data_exposure": projection,
    }
    grant["grant_hash"] = object_hash(ASP + "hash/grant/v1", grant)
    session_record = {
        "session_id": "calcu-session-example",
        "session_generation": 1,
        "subject": deepcopy(grant["subject"]),
        "grant_id": grant["grant_id"],
        "grant_hash": grant["grant_hash"],
        "runtime_id": request["delegate"]["runtime"],
        "agent_id": request["delegate"]["agent"],
        "identity_evidence_hash": object_hash(IDENTITY_DOMAIN, identity),
        "app_id": manifest["app_id"],
        "surface_version": manifest["surface_version"],
        "surface_hash": manifest["surface_hash"],
        "initiated_by": "runtime",
        "state": "active",
        "transition_reason": "start_accepted",
    }
    return {
        "notice": "OFFLINE, SYNTHETIC, EXPIRED, NOT PUBLISHABLE. No identity verification, consent, issuance or session activation occurred.",
        "publishable": False,
        "normative_baseline": "aa1db9926ef9c17bc440b3a2d76a81bdc95ddfbe",
        "example_clock": "2026-09-06T00:00:00Z",
        "live_path_status": "blocked_pending_identity_consent_retention_and_safety_implementation",
        "input_schema": input_schema,
        "output_schema": output_schema,
        "manifest_example": manifest,
        "semantic_grant_request": request,
        "grant_request_hash": object_hash(ASP + "hash/grant-request/v1", request),
        "grant_example": grant,
        "session_record_example": session_record,
        # This is a local worksheet, NOT a standardized preview wire object.
        "consent_worksheet": {
            "state": "not_presented_not_confirmed",
            "request_hash": object_hash(ASP + "hash/grant-request/v1", request),
            "surface_hash": manifest["surface_hash"],
            "identity_evidence_hash": session_record["identity_evidence_hash"],
            "derived_exposure": deepcopy(projection),
            "credential_audience": manifest["agent_api"]["credential_audience"],
            "proposed_lifetime_seconds": 60,
        },
        "sample_input": {"operator": "multiply", "left": 240, "right": 0.15},
        "sample_output": {"operator": "multiply", "left": 240, "right": 0.15, "result": 36},
    }


if __name__ == "__main__":
    print(json.dumps(build_example(), indent=2, ensure_ascii=False, allow_nan=False))
