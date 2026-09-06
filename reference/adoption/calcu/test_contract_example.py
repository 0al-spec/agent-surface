"""Checks construction coherence, not manifest conformance or live authority."""
import unittest
from copy import deepcopy

from jsonschema import Draft202012Validator, ValidationError

from contract_example import ACTION, ASP, IDENTITY_DOMAIN, ORIGIN, build_example, object_hash


class ContractExampleTests(unittest.TestCase):
    def setUp(self):
        self.example = build_example()
        self.manifest = self.example["manifest_example"]
        self.request = self.example["semantic_grant_request"]
        self.grant = self.example["grant_example"]
        self.session = self.example["session_record_example"]

    def test_deterministic_independent_examples(self):
        self.assertEqual(self.example, build_example())
        self.grant["credential_binding"]["identity_evidence"]["subject"] = "changed"
        self.assertEqual(self.request["delegate"]["identity_evidence"]["subject"], "synthetic-calcu-adapter")
        self.assertEqual(build_example()["grant_example"]["credential_binding"]["identity_evidence"]["subject"], "synthetic-calcu-adapter")

    def test_hashes_and_self_field_exclusions(self):
        # Fixed RFC vectors avoid checking only the helper against itself.
        self.assertEqual(
            object_hash(ASP + "hash/grant/v1", {"grant_id": "grant_123", "scopes": ["read"]}),
            "sha-256:Xbq37_fP9PBiWI3Bv7Ch0t8TV5ikJGm55MxncSeA38Y",
        )
        self.assertEqual(
            object_hash(ASP + "hash/manifest/v1", {"z": 1, "a": "x"}),
            "sha-256:Mckhl9gi8ePkXnuOJtPFNE1pe9LhilOGu1OgzxsXb8A",
        )
        for value, field, domain in [
            (self.manifest, "surface_hash", "manifest"),
            (self.grant, "grant_hash", "grant"),
        ]:
            view = {k: v for k, v in value.items() if k != field}
            self.assertEqual(value[field], object_hash(ASP + f"hash/{domain}/v1", view))
            changed = deepcopy(view)
            changed["extension-example"] = True
            self.assertNotEqual(value[field], object_hash(ASP + f"hash/{domain}/v1", changed))
        self.assertEqual(self.example["grant_request_hash"], object_hash(ASP + "hash/grant-request/v1", self.request))

    def test_identity_domain_is_not_calcu_legacy_domain(self):
        evidence = self.grant["delegate"]["identity_evidence"]
        self.assertEqual(evidence, self.grant["credential_binding"]["identity_evidence"])
        self.assertEqual(self.session["identity_evidence_hash"], object_hash(IDENTITY_DOMAIN, evidence))
        self.assertNotEqual(self.session["identity_evidence_hash"], object_hash(ASP + "hash/identity-evidence/v1", evidence))

    def test_request_has_no_issuer_outputs_or_credential(self):
        self.assertFalse({"grant_id", "grant_hash", "subject", "credential_binding", "data_exposure"} & self.request.keys())
        self.assertEqual(self.request["constraints"]["credential_release"], {"mode": "deny"})
        self.assertEqual(self.grant["credential_binding"]["method"], "bearer")
        self.assertEqual(self.example["consent_worksheet"]["state"], "not_presented_not_confirmed")
        self.assertTrue(self.example["live_path_status"].startswith("blocked_"))
        self.assertFalse(self.example["publishable"])
        self.assertNotIn("manifest", self.example)

    def test_endpoints_and_authority_are_not_interchangeable(self):
        api = self.manifest["agent_api"]
        self.assertEqual(self.grant["locations"], [ORIGIN + "/agent-actions"])
        self.assertNotIn(api["session_control_url"], self.grant["locations"])
        self.assertNotIn(api["credential_audience"], self.grant["locations"])
        self.assertEqual(api["credential_audience"], ORIGIN + "/agent-api")
        self.assertEqual(self.grant["actions"], [ACTION])
        self.assertEqual(self.manifest["resources"], [])
        self.assertEqual(self.manifest["events"], [])

    def test_exact_exposure_and_session_projection(self):
        self.assertEqual(self.grant["data_exposure"], [{"source": {"kind": "action", "id": ACTION}, **self.manifest["actions"][0]["data_exposure"]}])
        self.assertEqual(self.example["consent_worksheet"]["derived_exposure"], self.grant["data_exposure"])
        for key in ("app_id", "surface_version", "surface_hash"):
            self.assertEqual(self.session[key], self.grant["resource_server"][key])
        for key in ("subject", "grant_id", "grant_hash"):
            self.assertEqual(self.session[key], self.grant[key])
        for key in ("runtime", "agent"):
            self.assertEqual(self.session[key + "_id"], self.grant["delegate"][key])
        self.assertEqual(self.session["session_generation"], 1)
        self.assertEqual(self.session["initiated_by"], "runtime")

    def test_closed_schemas_positive_and_negative_inputs(self):
        for kind in ("input", "output"):
            schema = self.example[kind + "_schema"]
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(self.example["sample_" + kind])
        schema = self.example["input_schema"]
        for bad in [
            {"operator": "sqrt", "left": 111, "right": 2},
            {"operator": "multiply", "left": "240", "right": 0.15},
            {"operator": "multiply", "left": 240, "right": 0.15, "credential": "forbidden-example"},
        ]:
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                Draft202012Validator(schema).validate(bad)
        self.assertEqual(self.manifest["actions"][0]["input_schema_hash"], object_hash(ASP + "hash/action-input-schema/v1", schema))

    def test_numbers_still_require_json_and_runtime_checks(self):
        # JSON Schema is not a raw JSON parser or the arithmetic engine.
        with self.assertRaises(ValueError):
            object_hash(ASP + "hash/action-input/v1", {"left": float("inf")})
        with self.assertRaises(ValueError):
            object_hash(ASP + "hash/action-input/v1", {"nested": [{"left": -0.0}]})
        self.assertIsInstance(object_hash(ASP + "hash/action-input/v1", {"left": 0.0}), str)
        self.assertEqual(self.example["sample_input"]["left"] * self.example["sample_input"]["right"], self.example["sample_output"]["result"])


if __name__ == "__main__":
    unittest.main()
