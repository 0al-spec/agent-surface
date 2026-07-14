from __future__ import annotations

import copy
import json
import sys
import unittest
from collections import Counter
from pathlib import Path


REVIEW_DIR = Path(__file__).resolve().parents[1]
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(REVIEW_DIR))

from build_review import (  # noqa: E402
    load_dashboard_data,
    replace_placeholders,
    render_rfc,
    serialize_inline_json,
)
from review_data import (  # noqa: E402
    load_review_payload,
    normalize_reviews,
    validate_review_payload,
)


class ReviewDataValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, cls.heading_ids = render_rfc()

    def fixture(self, name: str) -> dict[str, object]:
        return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def valid_payload(self) -> dict[str, object]:
        return self.fixture("valid-minimal-v2.json")

    def assert_invalid(self, payload: dict[str, object], message: str) -> None:
        with self.assertRaisesRegex(ValueError, message):
            validate_review_payload(payload, self.heading_ids)

    def test_canonical_review_data_is_valid(self) -> None:
        validate_review_payload(load_review_payload(), self.heading_ids)

    def test_valid_v2_planning_bundle_is_accepted(self) -> None:
        validate_review_payload(self.valid_payload(), self.heading_ids)

    def test_invalid_schema_version_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["schema_version"] = 1
        self.assert_invalid(payload, "does not match review-data.schema.json")

    def test_missing_required_field_is_rejected(self) -> None:
        payload = self.valid_payload()
        del payload["reviews"][0]["title"]
        self.assert_invalid(payload, "does not match review-data.schema.json")

    def test_persisted_derived_blocks_are_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["blocks"] = []
        self.assert_invalid(payload, "does not match review-data.schema.json")

    def test_half_migrated_planning_bundle_fixture_is_rejected(self) -> None:
        self.assert_invalid(
            self.fixture("invalid-partial-metadata.json"),
            "does not match review-data.schema.json",
        )

    def test_duplicate_profile_id_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["profiles"].append(copy.deepcopy(payload["profiles"][0]))
        self.assert_invalid(payload, "Duplicate profile ids")

    def test_duplicate_release_id_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["releases"].append(copy.deepcopy(payload["releases"][0]))
        self.assert_invalid(payload, "Duplicate release ids")

    def test_duplicate_review_id_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"].append(copy.deepcopy(payload["reviews"][0]))
        self.assert_invalid(payload, "Duplicate review ids")

    def test_unknown_profile_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["profile"] = "unknown"
        self.assert_invalid(payload, "references unknown profile")

    def test_unknown_release_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["target_release"] = "9.9"
        self.assert_invalid(payload, "references unknown release")

    def test_unknown_review_dependency_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["depends_on"] = [99]
        self.assert_invalid(payload, "references unknown dependencies")

    def test_self_dependency_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["depends_on"] = [1]
        self.assert_invalid(payload, "cannot depend on itself")

    def test_profile_cycle_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["profiles"].extend(
            [
                {"id": "one", "title": "One", "depends_on": ["two"]},
                {"id": "two", "title": "Two", "depends_on": ["one"]},
            ]
        )
        self.assert_invalid(payload, "Profile dependency graph is cyclic")

    def test_review_cycle_fixture_is_rejected(self) -> None:
        self.assert_invalid(
            self.fixture("invalid-review-cycle.json"), "Review dependency graph is cyclic"
        )

    def test_stale_anchor_fixture_is_rejected(self) -> None:
        self.assert_invalid(self.fixture("invalid-stale-anchor.json"), "stale anchorId")

    def test_unknown_rfc_evidence_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["evidence"] = [
            {"kind": "rfc_anchor", "ref": "unknown-anchor"}
        ]
        self.assert_invalid(payload, "evidence references unknown RFC anchor")

    def test_duplicate_evidence_identity_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["evidence"] = [
            {"kind": "rfc_anchor", "ref": "abstract", "description": "one"},
            {"kind": "rfc_anchor", "ref": "abstract", "description": "two"},
        ]
        self.assert_invalid(payload, "duplicate evidence references")

    def test_specified_maturity_requires_rfc_evidence(self) -> None:
        payload = self.valid_payload()
        review = payload["reviews"][0]
        review["status"] = "present"
        review["maturity"] = "specified"
        review["evidence"] = []
        self.assert_invalid(payload, "requires rfc_anchor evidence")

    def test_unresolved_evidence_kind_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["evidence"].append(
            {"kind": "schema", "ref": "does-not-exist.schema.json"}
        )
        self.assert_invalid(payload, "authoritative resolver")

    def test_unverifiable_maturity_levels_are_rejected(self) -> None:
        payload = self.valid_payload()
        review = payload["reviews"][0]
        review["status"] = "present"
        for maturity in (
            "machine_validated",
            "implementation_tested",
            "interop_tested",
            "stable",
        ):
            with self.subTest(maturity=maturity):
                review["maturity"] = maturity
                self.assert_invalid(payload, "authoritative evidence resolvers")

    def test_partial_specified_fixture_is_rejected(self) -> None:
        self.assert_invalid(
            self.fixture("invalid-partial-specified.json"), "cannot exceed proposal maturity"
        )

    def test_present_coverage_may_remain_a_proposal(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["status"] = "present"
        validate_review_payload(payload, self.heading_ids)

    def test_required_planning_metadata_rejects_legacy_card(self) -> None:
        payload = load_review_payload()
        for field in ("profile", "depends_on", "target_release", "maturity", "evidence"):
            del payload["reviews"][0][field]
        with self.assertRaisesRegex(ValueError, "does not match review-data.schema.json"):
            validate_review_payload(payload, self.heading_ids)

    def test_canonical_gate_rejects_transitional_mode(self) -> None:
        payload = load_review_payload()
        payload["planning_metadata_mode"] = "transitional"
        for field in ("profile", "depends_on", "target_release", "maturity", "evidence"):
            del payload["reviews"][0][field]
        validate_review_payload(payload, self.heading_ids)
        with self.assertRaisesRegex(ValueError, "must use planning_metadata_mode 'required'"):
            validate_review_payload(
                payload,
                self.heading_ids,
                required_planning_mode="required",
            )

    def test_long_reverse_order_dependency_chain_is_valid(self) -> None:
        payload = self.valid_payload()
        template = payload["reviews"][0]
        reviews = []
        for review_id in range(1100, 0, -1):
            review = copy.deepcopy(template)
            review["id"] = review_id
            review["title"] = f"Review {review_id}"
            review["depends_on"] = [] if review_id == 1 else [review_id - 1]
            reviews.append(review)
        payload["reviews"] = reviews
        validate_review_payload(payload, self.heading_ids)

    def test_canonical_migration_counts_and_defaults(self) -> None:
        payload = load_review_payload()
        reviews = payload["reviews"]
        self.assertEqual(len(reviews), 60)
        self.assertEqual(
            Counter(review["maturity"] for review in reviews),
            Counter({"specified": 41, "proposal": 19}),
        )
        self.assertEqual(
            Counter(review["status"] for review in reviews),
            Counter({"present": 41, "partial": 9, "missing": 10}),
        )
        self.assertEqual(sum(len(review["depends_on"]) for review in reviews), 119)
        self.assertTrue(all(review["target_release"] is None for review in reviews))
        self.assertEqual(
            Counter(review["profile"] for review in reviews),
            Counter(
                {
                    "core": 4,
                    "oauth-grants": 8,
                    "manifest": 6,
                    "action-execution": 6,
                    "events-sessions": 5,
                    "receipts-provenance": 6,
                    "privacy-consent": 10,
                    "identity-passport": 5,
                    "operations-safety": 5,
                    "conformance-tooling": 5,
                }
            ),
        )
        self.assertEqual(sum(len(review["evidence"]) for review in reviews), 224)
        for review in reviews:
            if review["status"] == "missing":
                self.assertEqual(review["evidence"], [])
            else:
                self.assertEqual(
                    [item["ref"] for item in review["evidence"]],
                    [anchor["anchorId"] for anchor in review["anchors"]],
                )

    def test_canonical_readiness_and_reverse_dependencies(self) -> None:
        payload = load_review_payload()
        reviews = normalize_reviews(payload, self.heading_ids)
        reviews_by_id = {review["id"]: review for review in reviews}
        ready_ids = {review["id"] for review in reviews if review["readiness"] == "ready"}
        blocked_ids = set(reviews_by_id) - ready_ids
        self.assertEqual(
            blocked_ids,
            {17, 44, 58, 60},
        )
        self.assertEqual(len(ready_ids), 56)
        self.assertEqual(reviews_by_id[26]["readiness"], "ready")
        self.assertEqual(reviews_by_id[36]["readiness"], "ready")
        self.assertEqual(reviews_by_id[25]["status"], "present")
        self.assertEqual(reviews_by_id[25]["readiness"], "ready")
        self.assertEqual(reviews_by_id[21]["maturity"], "specified")
        self.assertEqual(reviews_by_id[41]["maturity"], "specified")
        self.assertEqual(reviews_by_id[51]["maturity"], "specified")
        self.assertEqual(reviews_by_id[52]["maturity"], "specified")
        self.assertEqual(reviews_by_id[54]["maturity"], "specified")
        for review in reviews:
            for dependency_id in review["depends_on"]:
                self.assertIn(review["id"], reviews_by_id[dependency_id]["blocks"])

    def test_derived_planning_fields_are_not_persisted(self) -> None:
        for review in load_review_payload()["reviews"]:
            self.assertNotIn("blocks", review)
            self.assertNotIn("readiness", review)

    def test_dashboard_payload_contains_registries_and_derived_state(self) -> None:
        dashboard_data = load_dashboard_data(self.heading_ids)
        self.assertEqual(dashboard_data["schema_version"], 2)
        self.assertEqual(len(dashboard_data["profiles"]), 10)
        self.assertEqual(len(dashboard_data["releases"]), 1)
        self.assertEqual(len(dashboard_data["maturity_order"]), 6)
        self.assertEqual(len(dashboard_data["reviews"]), 60)
        self.assertIn("blocks", dashboard_data["reviews"][0])
        self.assertIn("readiness", dashboard_data["reviews"][0])

    def test_inline_json_escapes_script_breakout_characters(self) -> None:
        value = {"text": "</script><tag>&\u2028\u2029"}
        serialized = serialize_inline_json(value)
        for unsafe in ("</script>", "<", ">", "&", "\u2028", "\u2029"):
            self.assertNotIn(unsafe, serialized)
        self.assertEqual(json.loads(serialized), value)

    def test_placeholder_replacement_requires_exactly_one_marker(self) -> None:
        self.assertEqual(
            replace_placeholders("before __ONE__ after", {"__ONE__": "value"}),
            "before value after",
        )
        self.assertEqual(
            replace_placeholders(
                "__ONE__ then __TWO__",
                {"__ONE__": "literal __TWO__", "__TWO__": "second"},
            ),
            "literal __TWO__ then second",
        )
        for template in ("marker missing", "__ONE__ and __ONE__"):
            with self.subTest(template=template):
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    replace_placeholders(template, {"__ONE__": "value"})

    def test_filter_sentinel_registry_ids_are_rejected(self) -> None:
        profile_payload = self.valid_payload()
        profile_payload["profiles"][0]["id"] = "all"
        profile_payload["reviews"][0]["profile"] = "all"
        self.assert_invalid(profile_payload, "does not match review-data.schema.json")

        release_payload = self.valid_payload()
        release_payload["releases"][0]["id"] = "__unassigned__"
        self.assert_invalid(release_payload, "does not match review-data.schema.json")


if __name__ == "__main__":
    unittest.main()
