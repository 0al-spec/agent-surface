from __future__ import annotations

import copy
import json
import os
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock


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
    _cargo_command,
    _run_replay_self_check,
    _validate_canonical_conformance_catalog,
    _validate_canonical_mock_bundle,
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

    def machine_validated_payload(self) -> dict[str, object]:
        return copy.deepcopy(load_review_payload())

    def assert_invalid(self, payload: dict[str, object], message: str) -> None:
        with self.assertRaisesRegex(ValueError, message):
            validate_review_payload(payload, self.heading_ids)

    def test_canonical_review_data_is_valid(self) -> None:
        validate_review_payload(load_review_payload(), self.heading_ids)

    def test_canonical_bundle_validation_is_deduplicated_per_process(self) -> None:
        _validate_canonical_conformance_catalog.cache_clear()
        _validate_canonical_mock_bundle.cache_clear()
        try:
            with (
                mock.patch("conformance.check.validate_catalog") as validate_catalog,
                mock.patch("mocks.check.validate_bundle") as validate_bundle,
            ):
                validate_review_payload(load_review_payload(), self.heading_ids)
                self.assertEqual(validate_catalog.call_count, 1)
                self.assertEqual(validate_bundle.call_count, 1)
        finally:
            _validate_canonical_conformance_catalog.cache_clear()
            _validate_canonical_mock_bundle.cache_clear()

    def test_linter_self_check_honors_cargo_override(self) -> None:
        previous = os.environ.get("CARGO")
        try:
            os.environ["CARGO"] = 'cargo-wrapper --channel "pinned toolchain"'
            self.assertEqual(
                _cargo_command(),
                ["cargo-wrapper", "--channel", "pinned toolchain"],
            )
        finally:
            if previous is None:
                os.environ.pop("CARGO", None)
            else:
                os.environ["CARGO"] = previous

    def test_replay_self_check_is_cached_and_uses_the_bound_package(self) -> None:
        _run_replay_self_check.cache_clear()
        try:
            completed = mock.Mock(returncode=0, stdout="", stderr="")
            with mock.patch("review_data.subprocess.run", return_value=completed) as run:
                _run_replay_self_check()
                _run_replay_self_check()
            self.assertEqual(run.call_count, 1)
            command = run.call_args.args[0]
            self.assertEqual(
                command[-8:],
                [
                    "--quiet",
                    "--locked",
                    "-p",
                    "asp-replay-tool",
                    "--",
                    "self-check",
                    "--root",
                    str(REVIEW_DIR.parent),
                ],
            )
            self.assertEqual(run.call_args.kwargs["cwd"], REVIEW_DIR.parent)
        finally:
            _run_replay_self_check.cache_clear()

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
            {"kind": "test", "ref": "conformance/tests/test_conformance.py"}
        )
        self.assert_invalid(payload, "authoritative resolver")

    def test_machine_validated_evidence_is_accepted(self) -> None:
        validate_review_payload(self.machine_validated_payload(), self.heading_ids)

    def test_machine_validated_requires_all_authoritative_evidence_kinds(self) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 60)
                review["evidence"] = [
                    item for item in review["evidence"] if item["kind"] != missing_kind
                ]
                self.assert_invalid(payload, "missing bound evidence")

    def test_api_importer_machine_validation_requires_exact_evidence(self) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry", "implementation"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 17)
                removed = False
                retained = []
                for item in review["evidence"]:
                    if item["kind"] == missing_kind and not removed:
                        removed = True
                        continue
                    retained.append(item)
                review["evidence"] = retained
                self.assertTrue(removed)
                self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_api_importer_machine_validation_rejects_extra_evidence(self) -> None:
        payload = self.machine_validated_payload()
        review = next(item for item in payload["reviews"] if item["id"] == 17)
        review["anchors"].append(
            {
                "heading": "Conceptual Architecture",
                "anchorId": "conceptual-architecture",
            }
        )
        review["evidence"].append(
            {"kind": "rfc_anchor", "ref": "conceptual-architecture"}
        )
        self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_other_review_cannot_borrow_api_importer_evidence(self) -> None:
        cases = (
            (
                "schema",
                "tools/asp-api-importer/schema/annotation.schema.json",
                "exact bound tooling schema",
            ),
            (
                "registry",
                "tools/asp-api-importer/cases/v1/cases.json",
                "conformance/v1/suite.json",
            ),
            (
                "implementation",
                "tools/asp-api-importer/src/main.rs",
                "exact bound tooling entry point",
            ),
        )
        for kind, ref, message in cases:
            with self.subTest(kind=kind):
                payload = self.machine_validated_payload()
                review = payload["reviews"][0]
                review["evidence"].append({"kind": kind, "ref": ref})
                self.assert_invalid(payload, message)

    def test_linter_machine_validation_requires_the_exact_bound_evidence(self) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry", "implementation"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 57)
                removed = False
                retained = []
                for item in review["evidence"]:
                    if item["kind"] == missing_kind and not removed:
                        removed = True
                        continue
                    retained.append(item)
                review["evidence"] = retained
                self.assertTrue(removed)
                self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_linter_machine_validation_rejects_extra_evidence(self) -> None:
        payload = self.machine_validated_payload()
        review = next(item for item in payload["reviews"] if item["id"] == 57)
        review["anchors"].append(
            {
                "heading": "Conceptual Architecture",
                "anchorId": "conceptual-architecture",
            }
        )
        review["evidence"].append(
            {"kind": "rfc_anchor", "ref": "conceptual-architecture"}
        )
        self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_other_review_cannot_borrow_linter_evidence(self) -> None:
        cases = (
            (
                "schema",
                "tools/asp-manifest-linter/schema/rules.schema.json",
                "exact bound tooling schema",
            ),
            (
                "registry",
                "tools/asp-manifest-linter/rules/v1/rules.json",
                "conformance/v1/suite.json",
            ),
            (
                "implementation",
                "tools/asp-manifest-linter/src/main.rs",
                "exact bound tooling entry point",
            ),
        )
        for kind, ref, message in cases:
            with self.subTest(kind=kind):
                payload = self.machine_validated_payload()
                review = payload["reviews"][0]
                review["evidence"].append({"kind": kind, "ref": ref})
                self.assert_invalid(payload, message)

    @mock.patch("review_data._run_replay_self_check")
    def test_replay_machine_validation_requires_the_exact_bound_evidence(
        self, _replay_self_check: mock.Mock
    ) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry", "implementation"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 59)
                removed = False
                retained = []
                for item in review["evidence"]:
                    if item["kind"] == missing_kind and not removed:
                        removed = True
                        continue
                    retained.append(item)
                review["evidence"] = retained
                self.assertTrue(removed)
                self.assert_invalid(payload, "exact authoritative evidence binding")

    @mock.patch("review_data._run_replay_self_check")
    def test_replay_machine_validation_rejects_extra_evidence(
        self, _replay_self_check: mock.Mock
    ) -> None:
        payload = self.machine_validated_payload()
        review = next(item for item in payload["reviews"] if item["id"] == 59)
        review["anchors"].append(
            {
                "heading": "Conceptual Architecture",
                "anchorId": "conceptual-architecture",
            }
        )
        review["evidence"].append(
            {"kind": "rfc_anchor", "ref": "conceptual-architecture"}
        )
        self.assert_invalid(payload, "exact authoritative evidence binding")

    @mock.patch("review_data._run_replay_self_check")
    def test_other_review_cannot_borrow_replay_evidence(
        self, _replay_self_check: mock.Mock
    ) -> None:
        cases = (
            (
                "schema",
                "tools/asp-replay/schema/bundle.schema.json",
                "exact bound tooling schema",
            ),
            (
                "registry",
                "tools/asp-replay/cases/v1/cases.json",
                "conformance/v1/suite.json",
            ),
            (
                "implementation",
                "tools/asp-replay/src/main.rs",
                "exact bound tooling entry point",
            ),
        )
        for kind, ref, message in cases:
            with self.subTest(kind=kind):
                payload = self.machine_validated_payload()
                review = payload["reviews"][0]
                review["evidence"].append({"kind": kind, "ref": ref})
                self.assert_invalid(payload, message)

    def test_mock_machine_validation_requires_the_exact_bound_evidence(self) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry", "implementation"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 58)
                removed = False
                retained = []
                for item in review["evidence"]:
                    if item["kind"] == missing_kind and not removed:
                        removed = True
                        continue
                    retained.append(item)
                review["evidence"] = retained
                self.assertTrue(removed)
                self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_mock_machine_validation_rejects_extra_evidence(self) -> None:
        payload = self.machine_validated_payload()
        review = next(item for item in payload["reviews"] if item["id"] == 58)
        review["anchors"].append(
            {
                "heading": "Conceptual Architecture",
                "anchorId": "conceptual-architecture",
            }
        )
        review["evidence"].append(
            {"kind": "rfc_anchor", "ref": "conceptual-architecture"}
        )
        self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_other_review_cannot_borrow_mock_bundle_evidence(self) -> None:
        cases = (
            (
                "schema",
                "mocks/v1/manifest.schema.json",
                "exact bound tooling schema",
            ),
            ("registry", "mocks/v1/manifest.json", "conformance/v1/suite.json"),
            (
                "implementation",
                "mocks/mock_app.py",
                "exact bound tooling entry point",
            ),
        )
        for kind, ref, message in cases:
            with self.subTest(kind=kind):
                payload = self.machine_validated_payload()
                review = payload["reviews"][0]
                review["evidence"].append({"kind": kind, "ref": ref})
                self.assert_invalid(payload, message)

    def test_unbound_review_cannot_borrow_conformance_evidence(self) -> None:
        payload = self.machine_validated_payload()
        source = next(item for item in payload["reviews"] if item["id"] == 60)
        review = payload["reviews"][0]
        review["status"] = "present"
        review["maturity"] = "machine_validated"
        review["evidence"] = [
            *review["evidence"],
            *(item for item in source["evidence"] if item["kind"] != "rfc_anchor"),
        ]
        self.assert_invalid(payload, "no authoritative machine-validation binding")

    def test_capacity_recovery_requires_the_exact_bound_evidence(self) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry", "implementation"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 61)
                review["evidence"] = [
                    item for item in review["evidence"] if item["kind"] != missing_kind
                ]
                self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_http_capacity_binding_requires_the_exact_bound_evidence(self) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry", "implementation"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 62)
                review["evidence"] = [
                    item for item in review["evidence"] if item["kind"] != missing_kind
                ]
                self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_asp_over_ahp_binding_requires_the_exact_bound_evidence(self) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry", "implementation"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 27)
                review["evidence"] = [
                    item for item in review["evidence"] if item["kind"] != missing_kind
                ]
                self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_human_elicitation_requires_the_exact_bound_evidence(self) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry", "implementation"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 29)
                review["evidence"] = [
                    item for item in review["evidence"] if item["kind"] != missing_kind
                ]
                self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_impact_simulation_requires_the_exact_bound_evidence(self) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry", "implementation"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 47)
                removed = False
                retained = []
                for item in review["evidence"]:
                    if item["kind"] == missing_kind and not removed:
                        removed = True
                        continue
                    retained.append(item)
                review["evidence"] = retained
                self.assertTrue(removed)
                self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_impact_simulation_rejects_extra_evidence(self) -> None:
        payload = self.machine_validated_payload()
        review = next(item for item in payload["reviews"] if item["id"] == 47)
        review["anchors"].append(
            {
                "heading": "Conceptual Architecture",
                "anchorId": "conceptual-architecture",
            }
        )
        review["evidence"].append(
            {"kind": "rfc_anchor", "ref": "conceptual-architecture"}
        )
        self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_risk_explanation_requires_the_exact_bound_evidence(self) -> None:
        for missing_kind in ("rfc_anchor", "schema", "registry", "implementation"):
            with self.subTest(missing_kind=missing_kind):
                payload = self.machine_validated_payload()
                review = next(item for item in payload["reviews"] if item["id"] == 48)
                removed = False
                retained = []
                for item in review["evidence"]:
                    if item["kind"] == missing_kind and not removed:
                        removed = True
                        continue
                    retained.append(item)
                review["evidence"] = retained
                self.assertTrue(removed)
                self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_risk_explanation_rejects_extra_evidence(self) -> None:
        payload = self.machine_validated_payload()
        review = next(item for item in payload["reviews"] if item["id"] == 48)
        review["anchors"].append(
            {
                "heading": "Conceptual Architecture",
                "anchorId": "conceptual-architecture",
            }
        )
        review["evidence"].append(
            {"kind": "rfc_anchor", "ref": "conceptual-architecture"}
        )
        self.assert_invalid(payload, "exact authoritative evidence binding")

    def test_interop_suite_requires_the_current_canonical_schema_set(self) -> None:
        payload = self.machine_validated_payload()
        review = next(item for item in payload["reviews"] if item["id"] == 60)
        review["evidence"] = [
            item
            for item in review["evidence"]
            if item["ref"] != "conformance/v1/impact-simulation.schema.json"
        ]
        self.assert_invalid(payload, "missing bound evidence")

    def test_missing_schema_evidence_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["evidence"].append(
            {"kind": "schema", "ref": "conformance/v1/missing.schema.json"}
        )
        self.assert_invalid(payload, "does not resolve to a repository file")

    def test_escaping_schema_evidence_is_rejected(self) -> None:
        for ref in ("../outside.schema.json", "/tmp/outside.schema.json"):
            with self.subTest(ref=ref):
                payload = self.valid_payload()
                payload["reviews"][0]["evidence"].append({"kind": "schema", "ref": ref})
                self.assert_invalid(payload, "must be repository-relative")

    def test_schema_evidence_outside_conformance_v1_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["evidence"].append(
            {"kind": "schema", "ref": "review/review-data.schema.json"}
        )
        self.assert_invalid(payload, r"conformance/v1/\*\.schema\.json")

    def test_registry_evidence_outside_canonical_catalog_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["reviews"][0]["evidence"].append(
            {"kind": "registry", "ref": "review/review-data.json"}
        )
        self.assert_invalid(payload, "conformance/v1/suite.json")

    def test_unverifiable_higher_maturity_levels_are_rejected(self) -> None:
        for maturity in (
            "implementation_tested",
            "interop_tested",
            "stable",
        ):
            with self.subTest(maturity=maturity):
                payload = self.machine_validated_payload()
                review = next(
                    item
                    for item in payload["reviews"]
                    if item["maturity"] == "machine_validated"
                )
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
        self.assertEqual(len(reviews), 77)
        self.assertEqual(sum(len(review["evidence"]) for review in reviews), 500)
        self.assertEqual(
            Counter(review["maturity"] for review in reviews),
            Counter({"specified": 50, "machine_validated": 12, "proposal": 15}),
        )
        self.assertEqual(
            Counter(review["status"] for review in reviews),
            Counter({"present": 63, "partial": 6, "missing": 8}),
        )
        self.assertEqual(sum(len(review["depends_on"]) for review in reviews), 224)
        self.assertTrue(all(review["target_release"] is None for review in reviews))
        self.assertEqual(
            [
                review["id"]
                for review in reviews
                if review["priority"] in {"P0", "P1"}
                and review["status"] != "present"
            ],
            [63, 65, 69, 76],
        )
        self.assertEqual(
            Counter(review["profile"] for review in reviews),
            Counter(
                {
                    "core": 4,
                    "oauth-grants": 9,
                    "manifest": 8,
                    "action-execution": 7,
                    "events-sessions": 5,
                    "receipts-provenance": 6,
                    "privacy-consent": 10,
                    "identity-passport": 7,
                    "operations-safety": 5,
                    "conformance-tooling": 16,
                }
            ),
        )
        for review in reviews:
            if review["status"] == "missing":
                self.assertEqual(review["evidence"], [])
            else:
                self.assertEqual(
                    [
                        item["ref"]
                        for item in review["evidence"]
                        if item["kind"] == "rfc_anchor"
                    ],
                    [anchor["anchorId"] for anchor in review["anchors"]],
                )

    def test_canonical_readiness_and_reverse_dependencies(self) -> None:
        payload = load_review_payload()
        reviews = normalize_reviews(payload, self.heading_ids)
        reviews_by_id = {review["id"]: review for review in reviews}
        ready_ids = {review["id"] for review in reviews if review["readiness"] == "ready"}
        blocked_ids = set(reviews_by_id) - ready_ids
        self.assertEqual(blocked_ids, {70, 73, 74, 77})
        self.assertEqual(len(ready_ids), 73)
        self.assertEqual(reviews_by_id[16]["status"], "present")
        self.assertEqual(reviews_by_id[16]["maturity"], "specified")
        self.assertEqual(reviews_by_id[16]["readiness"], "ready")
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[16]["anchors"]],
            [
                "non-goals",
                "agent-surface",
                "curated-surface-boundary",
                "model-context-protocol",
                "grant-verification",
                "versioning-and-compatibility",
                "surface-publisher-profile",
                "application-mvp-mapping",
            ],
        )
        self.assertEqual(reviews_by_id[17]["status"], "present")
        self.assertEqual(reviews_by_id[17]["maturity"], "machine_validated")
        self.assertEqual(reviews_by_id[17]["depends_on"], [16, 57])
        self.assertEqual(reviews_by_id[17]["readiness"], "ready")
        self.assertEqual(len(reviews_by_id[17]["evidence"]), 17)
        self.assertEqual(
            Counter(item["kind"] for item in reviews_by_id[17]["evidence"]),
            Counter(
                {
                    "rfc_anchor": 12,
                    "schema": 2,
                    "registry": 1,
                    "implementation": 2,
                }
            ),
        )
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[17]["anchors"]],
            [
                "curated-surface-boundary",
                "openapi-and-asyncapi-import-profile",
                "canonical-object-hash-profile",
                "required-top-level-fields",
                "surface-hash",
                "resources",
                "actions",
                "events",
                "versioning-and-compatibility",
                "reference-api-importer",
                "surface-publisher-profile",
                "application-mvp-mapping",
            ],
        )
        self.assertEqual(reviews_by_id[26]["readiness"], "ready")
        self.assertEqual(reviews_by_id[27]["status"], "present")
        self.assertEqual(reviews_by_id[27]["maturity"], "machine_validated")
        self.assertEqual(reviews_by_id[27]["depends_on"], [26, 28, 30])
        self.assertEqual(reviews_by_id[27]["readiness"], "ready")
        self.assertEqual(len(reviews_by_id[27]["evidence"]), 14)
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[27]["anchors"]],
            [
                "asp-over-ahp-binding-profile",
                "session-authority-and-lifecycle",
                "interoperability-test-suite",
                "reference-mock-participants",
                "runtime-mediator-profile",
                "agent-adapter-profile",
            ],
        )
        self.assertEqual(reviews_by_id[29]["status"], "present")
        self.assertEqual(reviews_by_id[29]["maturity"], "machine_validated")
        self.assertEqual(reviews_by_id[29]["depends_on"], [28, 35])
        self.assertEqual(reviews_by_id[29]["readiness"], "ready")
        self.assertEqual(len(reviews_by_id[29]["evidence"]), 22)
        self.assertEqual(
            Counter(item["kind"] for item in reviews_by_id[29]["evidence"]),
            Counter(
                {
                    "rfc_anchor": 11,
                    "schema": 4,
                    "registry": 4,
                    "implementation": 3,
                }
            ),
        )
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[29]["anchors"]],
            [
                "human-elicitation-events-profile",
                "3-runtime-bridge-protocol",
                "canonical-object-hash-profile",
                "example-manifest",
                "approval-receipt-profile",
                "error-model",
                "interoperability-test-suite",
                "reference-mock-participants",
                "action-executor-profile",
                "runtime-mediator-profile",
                "agent-adapter-profile",
            ],
        )
        self.assertEqual(reviews_by_id[36]["readiness"], "ready")
        self.assertEqual(reviews_by_id[18]["status"], "present")
        self.assertEqual(reviews_by_id[18]["maturity"], "specified")
        self.assertEqual(reviews_by_id[18]["depends_on"], [4, 15, 19, 46])
        self.assertEqual(reviews_by_id[18]["readiness"], "ready")
        self.assertEqual(reviews_by_id[37]["status"], "present")
        self.assertEqual(reviews_by_id[37]["maturity"], "specified")
        self.assertEqual(reviews_by_id[37]["depends_on"], [36, 38])
        self.assertEqual(reviews_by_id[25]["status"], "present")
        self.assertEqual(reviews_by_id[25]["readiness"], "ready")
        self.assertEqual(reviews_by_id[31]["status"], "present")
        self.assertEqual(reviews_by_id[31]["maturity"], "specified")
        self.assertEqual(reviews_by_id[31]["depends_on"], [30, 35])
        self.assertEqual(reviews_by_id[21]["maturity"], "specified")
        self.assertEqual(reviews_by_id[38]["status"], "present")
        self.assertEqual(reviews_by_id[38]["maturity"], "specified")
        self.assertEqual(reviews_by_id[38]["depends_on"], [36, 41])
        self.assertEqual(reviews_by_id[41]["maturity"], "specified")
        self.assertEqual(reviews_by_id[42]["maturity"], "specified")
        self.assertEqual(reviews_by_id[44]["maturity"], "specified")
        self.assertEqual(reviews_by_id[45]["status"], "present")
        self.assertEqual(reviews_by_id[45]["maturity"], "specified")
        self.assertEqual(reviews_by_id[47]["status"], "present")
        self.assertEqual(reviews_by_id[47]["maturity"], "machine_validated")
        self.assertEqual(reviews_by_id[47]["depends_on"], [22, 44, 46])
        self.assertEqual(reviews_by_id[47]["readiness"], "ready")
        self.assertEqual(len(reviews_by_id[47]["evidence"]), 24)
        self.assertEqual(
            Counter(item["kind"] for item in reviews_by_id[47]["evidence"]),
            Counter(
                {
                    "rfc_anchor": 14,
                    "schema": 4,
                    "registry": 4,
                    "implementation": 2,
                }
            ),
        )
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[47]["anchors"]],
            [
                "impact-simulation",
                "actions",
                "preconditions-and-effect-preview",
                "effect-model",
                "approval-semantics",
                "consent-preview-contract",
                "risk-explanation-ui-hints",
                "capability-matching",
                "versioning-and-compatibility",
                "privacy-considerations",
                "interoperability-test-suite",
                "reference-mock-participants",
                "runtime-mediator-profile",
                "example-end-to-end-flow",
            ],
        )
        self.assertEqual(reviews_by_id[48]["status"], "present")
        self.assertEqual(reviews_by_id[48]["maturity"], "machine_validated")
        self.assertEqual(reviews_by_id[48]["depends_on"], [20, 46])
        self.assertEqual(reviews_by_id[48]["readiness"], "ready")
        self.assertEqual(len(reviews_by_id[48]["evidence"]), 24)
        self.assertEqual(
            Counter(item["kind"] for item in reviews_by_id[48]["evidence"]),
            Counter(
                {
                    "rfc_anchor": 13,
                    "schema": 4,
                    "registry": 4,
                    "implementation": 3,
                }
            ),
        )
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[48]["anchors"]],
            [
                "risk-explanation-ui-hints",
                "actions",
                "risk-taxonomy",
                "effect-model",
                "approval-semantics",
                "consent-preview-contract",
                "capability-matching",
                "human-elicitation-events-profile",
                "versioning-and-compatibility",
                "interoperability-test-suite",
                "reference-mock-participants",
                "surface-publisher-profile",
                "runtime-mediator-profile",
            ],
        )
        self.assertEqual(reviews_by_id[51]["maturity"], "specified")
        self.assertEqual(reviews_by_id[52]["maturity"], "specified")
        self.assertEqual(reviews_by_id[53]["status"], "present")
        self.assertEqual(reviews_by_id[53]["maturity"], "machine_validated")
        self.assertEqual(len(reviews_by_id[53]["evidence"]), 25)
        self.assertEqual(
            Counter(item["kind"] for item in reviews_by_id[53]["evidence"]),
            Counter({"rfc_anchor": 12, "schema": 9, "registry": 4}),
        )
        self.assertEqual(
            reviews_by_id[53]["depends_on"],
            [13, 21, 26, 30, 51, 54],
        )
        self.assertEqual(reviews_by_id[53]["readiness"], "ready")
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[53]["anchors"]],
            [
                "required-top-level-fields",
                "example-manifest",
                "actions",
                "events",
                "rate-limits-and-quotas",
                "event-subscription-authority",
                "event-delivery-semantics",
                "retention-and-backpressure",
                "error-model",
                "surface-publisher-profile",
                "action-executor-profile",
                "runtime-mediator-profile",
            ],
        )
        self.assertEqual(reviews_by_id[54]["maturity"], "specified")
        self.assertEqual(reviews_by_id[56]["status"], "present")
        self.assertEqual(reviews_by_id[56]["maturity"], "specified")
        self.assertEqual(reviews_by_id[56]["depends_on"], [1, 6, 30])
        self.assertEqual(reviews_by_id[56]["readiness"], "ready")
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[56]["anchors"]],
            [
                "conformance",
                "conformance-claim-and-composition-rules",
                "surface-publisher-profile",
                "grant-issuer-profile",
                "action-executor-profile",
                "receipt-producer-profile",
                "runtime-mediator-profile",
                "agent-adapter-profile",
            ],
        )
        self.assertEqual(reviews_by_id[57]["status"], "present")
        self.assertEqual(reviews_by_id[57]["maturity"], "machine_validated")
        self.assertEqual(reviews_by_id[57]["depends_on"], [13, 15, 19, 20])
        self.assertEqual(reviews_by_id[57]["readiness"], "ready")
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[57]["anchors"]],
            ["reference-manifest-linter"],
        )
        self.assertEqual(reviews_by_id[58]["status"], "present")
        self.assertEqual(reviews_by_id[58]["maturity"], "machine_validated")
        self.assertEqual(reviews_by_id[58]["depends_on"], [13, 19, 28, 30, 56, 60])
        self.assertEqual(reviews_by_id[58]["readiness"], "ready")
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[58]["anchors"]],
            ["reference-mock-participants"],
        )
        self.assertEqual(reviews_by_id[59]["status"], "present")
        self.assertEqual(reviews_by_id[59]["maturity"], "machine_validated")
        self.assertEqual(reviews_by_id[59]["profile"], "conformance-tooling")
        self.assertEqual(reviews_by_id[59]["depends_on"], [25, 26, 28, 30, 32, 55])
        self.assertEqual(reviews_by_id[59]["readiness"], "ready")
        self.assertEqual(len(reviews_by_id[59]["evidence"]), 20)
        self.assertEqual(
            Counter(item["kind"] for item in reviews_by_id[59]["evidence"]),
            Counter(
                {
                    "rfc_anchor": 12,
                    "schema": 4,
                    "registry": 2,
                    "implementation": 2,
                }
            ),
        )
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[59]["anchors"]],
            [
                "portable-replay-bundle-profile",
                "bundle-scope-and-historical-context",
                "replay-record-object",
                "deterministic-replay-and-ordering",
                "integrity-completeness-and-validation-report",
                "failure-privacy-and-non-authority-rules",
                "canonical-object-hash-profile",
                "replay-cursors-and-gaps",
                "session-authority-and-lifecycle",
                "receipt-hash-chain",
                "reference-replay-tool",
                "application-mvp-mapping",
            ],
        )
        self.assertEqual(reviews_by_id[60]["readiness"], "ready")
        self.assertEqual(len(reviews_by_id[60]["evidence"]), 21)
        self.assertEqual(reviews_by_id[61]["status"], "present")
        self.assertEqual(reviews_by_id[61]["maturity"], "machine_validated")
        self.assertEqual(reviews_by_id[61]["depends_on"], [53, 58, 60])
        self.assertEqual(reviews_by_id[61]["readiness"], "ready")
        self.assertEqual(len(reviews_by_id[61]["evidence"]), 12)
        self.assertEqual(reviews_by_id[62]["status"], "present")
        self.assertEqual(reviews_by_id[62]["maturity"], "machine_validated")
        self.assertEqual(reviews_by_id[62]["depends_on"], [53, 58, 60, 61])
        self.assertEqual(reviews_by_id[62]["readiness"], "ready")
        self.assertEqual(len(reviews_by_id[62]["evidence"]), 15)
        self.assertEqual(
            [anchor["anchorId"] for anchor in reviews_by_id[62]["anchors"]],
            [
                "http-capacity-error-binding",
                "action-executor-profile",
                "runtime-mediator-profile",
                "interoperability-test-suite",
                "reference-mock-participants",
            ],
        )
        self.assertEqual(reviews_by_id[63]["status"], "partial")
        self.assertEqual(reviews_by_id[63]["depends_on"], [14, 15, 16, 36])
        self.assertEqual(reviews_by_id[63]["readiness"], "ready")
        self.assertEqual(reviews_by_id[64]["status"], "partial")
        self.assertEqual(
            reviews_by_id[64]["depends_on"], [2, 5, 6, 10, 28, 35, 46]
        )
        self.assertEqual(reviews_by_id[64]["readiness"], "ready")
        self.assertEqual(reviews_by_id[65]["status"], "partial")
        self.assertEqual(reviews_by_id[65]["readiness"], "ready")
        self.assertEqual(reviews_by_id[66]["status"], "partial")
        self.assertEqual(reviews_by_id[66]["readiness"], "ready")
        self.assertEqual(reviews_by_id[67]["status"], "missing")
        self.assertEqual(reviews_by_id[67]["readiness"], "ready")
        self.assertEqual(reviews_by_id[68]["status"], "missing")
        self.assertEqual(reviews_by_id[68]["readiness"], "ready")
        self.assertEqual(reviews_by_id[69]["status"], "missing")
        self.assertEqual(reviews_by_id[69]["readiness"], "ready")
        self.assertEqual(
            reviews_by_id[70]["depends_on"],
            [6, 13, 14, 15, 16, 19, 36, 46, 63, 69],
        )
        self.assertEqual(reviews_by_id[70]["readiness"], "blocked")
        self.assertEqual(reviews_by_id[71]["readiness"], "ready")
        self.assertEqual(reviews_by_id[72]["readiness"], "ready")
        self.assertEqual(reviews_by_id[73]["depends_on"], [2, 5, 41, 44, 76])
        self.assertEqual(reviews_by_id[73]["readiness"], "blocked")
        self.assertEqual(reviews_by_id[74]["status"], "present")
        self.assertEqual(reviews_by_id[74]["maturity"], "proposal")
        self.assertEqual(reviews_by_id[74]["depends_on"], [56, 58, 60, 65])
        self.assertEqual(reviews_by_id[74]["readiness"], "blocked")
        self.assertEqual(reviews_by_id[75]["status"], "partial")
        self.assertEqual(
            reviews_by_id[75]["depends_on"], [17, 19, 20, 22, 56, 60]
        )
        self.assertEqual(reviews_by_id[75]["readiness"], "ready")
        self.assertEqual(reviews_by_id[76]["status"], "partial")
        self.assertEqual(reviews_by_id[76]["depends_on"], [2, 41, 42, 43, 44])
        self.assertEqual(reviews_by_id[76]["readiness"], "ready")
        self.assertEqual(
            reviews_by_id[77]["depends_on"],
            [67, 68, 69, 70, 71, 72, 73, 75],
        )
        self.assertEqual(reviews_by_id[77]["readiness"], "blocked")
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
        self.assertEqual(len(dashboard_data["reviews"]), 77)
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
