from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


REVIEW_DIR = Path(__file__).resolve().parents[1]
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(REVIEW_DIR))

from build_review import render_rfc  # noqa: E402
from review_data import load_review_payload, validate_review_payload  # noqa: E402


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

    def test_canonical_review_data_is_valid_during_transition(self) -> None:
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
        self.assert_invalid(payload, "Profile dependency cycle")

    def test_review_cycle_fixture_is_rejected(self) -> None:
        self.assert_invalid(
            self.fixture("invalid-review-cycle.json"), "Review dependency cycle"
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
        payload["planning_metadata_mode"] = "required"
        with self.assertRaisesRegex(ValueError, "does not match review-data.schema.json"):
            validate_review_payload(payload, self.heading_ids)

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


if __name__ == "__main__":
    unittest.main()
