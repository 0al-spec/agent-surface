"""Carrier structure vectors only; not complete receipt or channel acceptance."""

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from conformance.check import ConformanceError, loads_strict_json


DIRECTORY = Path(__file__).resolve().parents[1] / "receipt-delivery" / "v1"


class InlineReceiptDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((DIRECTORY / "carrier.schema.json").read_text())
        Draft202012Validator.check_schema(cls.schema)
        cls.catalog = loads_strict_json((DIRECTORY / "cases.json").read_text())

    def validator(self, shape):
        return Draft202012Validator({
            "$schema": self.schema["$schema"],
            "$defs": self.schema["$defs"],
            "$ref": f"#/$defs/{shape}",
        })

    def test_positive_and_negative_vectors(self):
        self.assertEqual(self.catalog["scope"], "carrier_structure_only")
        cases = self.catalog["cases"]
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        for shape in ("declaration", "request", "response"):
            self.assertEqual({c["valid"] for c in cases if c["shape"] == shape}, {True, False})
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(self.validator(case["shape"]).is_valid(case["instance"]), case["valid"])

    def test_duplicate_members_fail_before_schema_validation(self):
        for value in (
            '{"profile":"one","profile":"two"}',
            '{"runtime_receipt":{"receipt_id":"one","receipt_id":"two"}}',
            '{"approval_receipts":{"runtime":{},"runtime":{}}}',
        ):
            with self.subTest(value=value), self.assertRaises(ConformanceError):
                loads_strict_json(value)

    def test_request_cannot_supply_application_approval(self):
        request = next(c["instance"] for c in self.catalog["cases"] if c["id"] == "request-role-guard")
        approval = next(c["instance"]["approval_receipts"] for c in self.catalog["cases"] if c["id"] == "response-approval-role-guard")
        self.assertFalse(self.validator("request").is_valid({**request, "approval_receipts": approval}))

    def test_role_guard_is_explicitly_not_complete_receipt_validation(self):
        # This deliberately incomplete receipt passes the carrier type guard.
        # A host MUST still run the existing complete receipt/profile validator.
        request = next(c["instance"] for c in self.catalog["cases"] if c["id"] == "request-role-guard")
        self.assertTrue(self.validator("request").is_valid(request))
        self.assertNotIn("policy_decision", request["runtime_receipt"])
        self.assertIn("complete existing Receipt profile separately", self.schema["$comment"])


if __name__ == "__main__":
    unittest.main()
