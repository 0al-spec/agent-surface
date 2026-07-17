from __future__ import annotations

import copy
import base64
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from conformance.check import (
    ConformanceError,
    PROFILE_ROLES,
    RECEIPT_PROFILE,
    applicable_vectors,
    catalog_digest,
    loads_strict_json,
    main,
    run_suite,
    validate_catalog,
    validate_subject,
    verify_report,
)


ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = Path(__file__).resolve().parent

def digest(label: str) -> str:
    value = hashlib.sha256(label.encode("utf-8")).digest()
    return "sha-256:" + base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


DIGEST_A = digest("target-artifact")
DIGEST_B = digest("target-configuration")
DIGEST_C = digest("replacement-artifact")


class ConformanceSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = validate_catalog(ROOT)

    def subject(self, profile_id: str, *, producer_role: str | None = None) -> dict:
        features = sorted(
            feature_id
            for feature_id, feature in self.catalog.features.items()
            if any(
                self.catalog.requirements[requirement_id]["profile_id"] == profile_id
                for requirement_id in feature["requirement_ids"]
            )
        )
        subject = {
            "schema_version": 1,
            "subject_kind": "suite_fixture",
            "subject_id": "test-subject",
            "boundary_id": "test/target-boundary",
            "implementation": {
                "name": "target-implementation",
                "version": "1.0.0",
                "artifact_sha256": DIGEST_A,
                "configuration_sha256": DIGEST_B,
            },
            "profile_id": profile_id,
            "protocol_version": "agent-surface/0.1",
            "features": features,
            "counterparts": [],
        }
        counterpart_number = 0
        for counterpart_profile in PROFILE_ROLES:
            roles = (
                ("application", "runtime")
                if counterpart_profile == RECEIPT_PROFILE
                else (None,)
            )
            for counterpart_role in roles:
                counterpart_number += 1
                counterpart = {
                    "kind": "implementation",
                    "boundary_id": f"test/counterpart-{counterpart_number}",
                    "profile_id": counterpart_profile,
                    "artifact_sha256": digest(
                        f"counterpart:{counterpart_profile}:{counterpart_role}"
                    ),
                    "configuration_sha256": digest(
                        f"configuration:{counterpart_profile}:{counterpart_role}"
                    ),
                }
                if counterpart_role is not None:
                    counterpart["producer_role"] = counterpart_role
                subject["counterparts"].append(counterpart)
        if producer_role is not None:
            subject["producer_role"] = producer_role
        return subject

    def catalog_copy(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / "conformance" / "v1", root / "conformance" / "v1")
        shutil.copytree(ROOT / "drafts", root / "drafts")
        return root

    def run_subject(
        self,
        subject: dict,
        adapter_name: str = "fixture_adapter.py",
        probe_name: str = "fixture_probe.py",
        timeout_seconds: int = 10,
    ) -> dict:
        return run_suite(
            subject=subject,
            adapter=TEST_DIR / adapter_name,
            probe=TEST_DIR / probe_name,
            adapter_id="suite-self-test-adapter",
            adapter_version="1.0.0",
            adapter_configuration_sha256=digest("fixture-adapter-configuration"),
            probe_id="suite-self-test-probe",
            probe_version="1.0.0",
            probe_configuration_sha256=digest("fixture-probe-configuration"),
            timeout_seconds=timeout_seconds,
            root=ROOT,
        )

    def test_catalog_is_closed_and_covers_six_roles(self) -> None:
        self.assertEqual(set(self.catalog.profiles), set(PROFILE_ROLES))
        self.assertEqual(self.catalog.suite["suite_version"], "1.4.0")
        self.assertEqual(len(self.catalog.features), 10)
        self.assertEqual(len(self.catalog.requirements), 40)
        self.assertEqual(len(self.catalog.vectors), 87)
        self.assertEqual(len(self.catalog.fixtures), 29)
        self.assertEqual(len(self.catalog.mutations), 59)
        self.assertEqual(len(self.catalog.schema_case_catalog["cases"]), 36)
        self.assertRegex(catalog_digest(ROOT), r"^sha-256:[A-Za-z0-9_-]{43}$")

    def test_schema_case_polarities_are_executable_and_fail_closed(self) -> None:
        cases = self.catalog.schema_case_catalog["cases"]
        for schema_id in {
            "https://github.com/0al-spec/agent-surface/conformance/schemas/operational-limits/v1",
            "https://github.com/0al-spec/agent-surface/conformance/schemas/capacity-error/v1",
        }:
            self.assertEqual(
                {case["polarity"] for case in cases if case["schema_id"] == schema_id},
                {"positive", "negative"},
            )

        root = self.catalog_copy()
        path = root / "conformance" / "v1" / "schema-cases.json"
        corpus = json.loads(path.read_text(encoding="utf-8"))
        positive = next(case for case in corpus["cases"] if case["polarity"] == "positive")
        negative = next(
            case
            for case in corpus["cases"]
            if case["polarity"] == "negative"
            and case["schema_id"] == positive["schema_id"]
        )
        negative["instance_json"] = positive["instance_json"]
        negative["context"] = positive["context"]
        path.write_text(json.dumps(corpus), encoding="utf-8")
        with self.assertRaisesRegex(ConformanceError, "negative schema case .* passed"):
            validate_catalog(root)

    def test_http_capacity_baselines_are_semantically_bound(self) -> None:
        http_vectors = {
            "ASP-V-AE-024",
            "ASP-V-AE-025",
            "ASP-V-AE-026",
            "ASP-V-RM-020",
            "ASP-V-RM-021",
            "ASP-V-RM-022",
            "ASP-V-RM-023",
            "ASP-V-RM-024",
            "ASP-V-RM-025",
            "ASP-V-RM-026",
            "ASP-V-RM-027",
        }
        self.assertEqual(
            {
                vector_id
                for vector_id, vector in self.catalog.vectors.items()
                if "http_capacity_binding_selected" in vector["setup"]
            },
            http_vectors,
        )

        root = self.catalog_copy()
        path = root / "conformance" / "v1" / "fixtures.json"
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        baseline = next(
            item
            for item in fixtures["fixtures"]
            if item["fixture_id"] == "ASP-F-RM-020"
        )
        baseline["document"]["transport"]["status"] = 503
        path.write_text(json.dumps(fixtures), encoding="utf-8")
        with self.assertRaisesRegex(
            ConformanceError, "HTTP capacity status does not match"
        ):
            validate_catalog(root)

        root = self.catalog_copy()
        path = root / "conformance" / "v1" / "fixtures.json"
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        baseline = next(
            item
            for item in fixtures["fixtures"]
            if item["fixture_id"] == "ASP-F-RM-024"
        )
        baseline["document"]["transport"]["retry_after"] = {
            "form": "http_date",
            "value": "soon",
        }
        path.write_text(json.dumps(fixtures), encoding="utf-8")
        with self.assertRaisesRegex(
            ConformanceError, "http_date is not RFC 9110 HTTP-date syntax"
        ):
            validate_catalog(root)

    def test_asp_over_ahp_baselines_are_semantically_bound(self) -> None:
        ahp_vectors = {
            "ASP-V-RM-028",
            "ASP-V-RM-029",
            "ASP-V-RM-030",
            "ASP-V-RM-031",
            "ASP-V-RM-032",
            "ASP-V-AA-006",
            "ASP-V-AA-007",
            "ASP-V-AA-008",
        }
        self.assertEqual(
            {
                vector_id
                for vector_id, vector in self.catalog.vectors.items()
                if "asp_over_ahp_selected" in vector["setup"]
            },
            ahp_vectors,
        )

        root = self.catalog_copy()
        path = root / "conformance" / "v1" / "fixtures.json"
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        baseline = next(
            item
            for item in fixtures["fixtures"]
            if item["fixture_id"] == "ASP-F-RM-028"
        )
        baseline["document"]["ahp"]["asp_session_generation"] = 2
        path.write_text(json.dumps(fixtures), encoding="utf-8")
        with self.assertRaisesRegex(
            ConformanceError, "does not match its bound ASP authority tuple"
        ):
            validate_catalog(root)

    def test_every_role_has_positive_and_negative_vectors(self) -> None:
        for profile_id in PROFILE_ROLES:
            polarities = {
                vector["polarity"]
                for vector in self.catalog.vectors.values()
                if vector["profile_id"] == profile_id
            }
            self.assertEqual(polarities, {"positive", "negative"})

    def test_catalog_rejects_stale_feature_anchor_and_external_schema_ref(self) -> None:
        root = self.catalog_copy()
        suite_path = root / "conformance" / "v1" / "suite.json"
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
        suite["features"][0]["rfc_anchor"] = "does-not-exist"
        suite_path.write_text(json.dumps(suite), encoding="utf-8")
        with self.assertRaisesRegex(ConformanceError, "feature .* unknown RFC anchor"):
            validate_catalog(root)

        root = self.catalog_copy()
        report_schema_path = root / "conformance" / "v1" / "report.schema.json"
        report_schema = json.loads(report_schema_path.read_text(encoding="utf-8"))
        report_schema["properties"]["subject"]["$ref"] = (
            "https://example.invalid/missing-schema"
        )
        report_schema_path.write_text(json.dumps(report_schema), encoding="utf-8")
        with self.assertRaisesRegex(ConformanceError, "unresolved external"):
            validate_catalog(root)

    def test_catalog_rejects_fixture_baseline_rebinding(self) -> None:
        root = self.catalog_copy()
        vectors_path = root / "conformance" / "v1" / "vectors.json"
        vectors = json.loads(vectors_path.read_text(encoding="utf-8"))
        vector = next(
            item for item in vectors["vectors"] if item["vector_id"] == "ASP-V-SP-002"
        )
        vector["baseline_vector_id"] = "ASP-V-GI-001"
        vectors_path.write_text(json.dumps(vectors), encoding="utf-8")
        with self.assertRaises(ConformanceError):
            validate_catalog(root)
        for producer_role in ("application", "runtime"):
            polarities = {
                vector["polarity"]
                for vector in self.catalog.vectors.values()
                if vector["profile_id"] == RECEIPT_PROFILE
                and vector["producer_role"] == producer_role
            }
            self.assertEqual(polarities, {"positive", "negative"})

    def test_operational_feature_requires_semantic_fixture_state(self) -> None:
        root = self.catalog_copy()
        fixtures_path = root / "conformance" / "v1" / "fixtures.json"
        fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
        fixture = next(
            item
            for item in fixtures["fixtures"]
            if item["baseline_vector_id"] == "ASP-V-SP-005"
        )
        fixture["document"].pop("operational")
        fixtures_path.write_text(json.dumps(fixtures), encoding="utf-8")
        with self.assertRaisesRegex(ConformanceError, "feature selection.*differ"):
            validate_catalog(root)

        root = self.catalog_copy()
        fixtures_path = root / "conformance" / "v1" / "fixtures.json"
        fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
        fixtures_by_baseline = {
            item["baseline_vector_id"]: item for item in fixtures["fixtures"]
        }
        fixtures_by_baseline["ASP-V-SP-001"]["document"]["operational"] = copy.deepcopy(
            fixtures_by_baseline["ASP-V-SP-005"]["document"]["operational"]
        )
        fixtures_path.write_text(json.dumps(fixtures), encoding="utf-8")
        with self.assertRaisesRegex(ConformanceError, "feature selection.*differ"):
            validate_catalog(root)

    def test_strict_json_rejects_duplicate_keys_and_floats(self) -> None:
        with self.assertRaisesRegex(ConformanceError, "duplicate JSON"):
            loads_strict_json('{"a":1,"a":2}')
        with self.assertRaisesRegex(ConformanceError, "floating-point"):
            loads_strict_json('{"a":1.5}')

    def test_subject_rejects_unknown_feature(self) -> None:
        subject = self.subject(next(iter(PROFILE_ROLES)))
        subject["features"] = ["https://example.invalid/feature"]
        with self.assertRaises(ConformanceError):
            validate_subject(subject, self.catalog)

    def test_in_memory_api_rejects_floats_and_noncanonical_digests(self) -> None:
        subject = self.subject(next(iter(PROFILE_ROLES)))
        subject["schema_version"] = 1.0
        with self.assertRaisesRegex(ConformanceError, "floating-point"):
            validate_subject(subject, self.catalog)
        subject = self.subject(next(iter(PROFILE_ROLES)))
        subject["implementation"]["artifact_sha256"] = "sha-256:" + "B" * 43
        with self.assertRaisesRegex(ConformanceError, "non-canonical"):
            validate_subject(subject, self.catalog)

    def test_observed_feature_inventory_cannot_be_hidden(self) -> None:
        subject = self.subject(next(iter(PROFILE_ROLES)))
        subject["features"] = []
        with self.assertRaisesRegex(ConformanceError, "feature inventory differs"):
            self.run_subject(subject, probe_name="feature_probe.py")

    def test_receipt_subject_requires_exact_producer_role(self) -> None:
        with self.assertRaises(ConformanceError):
            validate_subject(self.subject(RECEIPT_PROFILE), self.catalog)
        valid = self.subject(RECEIPT_PROFILE, producer_role="application")
        validate_subject(valid, self.catalog)
        applicable, not_applicable, uncovered = applicable_vectors(self.catalog, valid)
        self.assertTrue(applicable)
        self.assertTrue(not_applicable)
        self.assertFalse(uncovered)
        self.assertTrue(
            all(
                self.catalog.vectors[vector_id].get("producer_role")
                == valid["producer_role"]
                for vector_id in applicable
            )
        )

    def test_suite_fixture_exercises_every_atomic_role_without_claiming_pass(self) -> None:
        subjects = [
            self.subject(profile_id)
            for profile_id in PROFILE_ROLES
            if profile_id != RECEIPT_PROFILE
        ] + [
            self.subject(RECEIPT_PROFILE, producer_role="application"),
            self.subject(RECEIPT_PROFILE, producer_role="runtime"),
        ]
        exercised_vector_ids: set[str] = set()
        for subject in subjects:
            with self.subTest(
                profile=subject["profile_id"], role=subject.get("producer_role")
            ):
                report = self.run_subject(subject)
                self.assertEqual(report["summary"]["suite_verdict"], "incomplete")
                self.assertEqual(
                    report["summary"]["incomplete_reasons"], ["suite_fixture"]
                )
                self.assertTrue(
                    all(result["status"] == "pass" for result in report["results"])
                )
                exercised_vector_ids.update(
                    result["vector_id"] for result in report["results"]
                )
                verify_report(report, root=ROOT)
        self.assertEqual(exercised_vector_ids, set(self.catalog.vectors))

    def test_repository_fixtures_cannot_claim_implementation_evidence(self) -> None:
        subject = self.subject(next(iter(PROFILE_ROLES)))
        subject["subject_kind"] = "implementation"
        with self.assertRaisesRegex(ConformanceError, "reference fixtures"):
            self.run_subject(subject)

    def test_assertion_mismatch_derives_fail(self) -> None:
        profile_id = next(
            item for item in PROFILE_ROLES if item != RECEIPT_PROFILE
        )
        report = self.run_subject(
            self.subject(profile_id), probe_name="failing_probe.py"
        )
        self.assertEqual(report["summary"]["suite_verdict"], "fail")
        self.assertGreater(report["summary"]["failed"], 0)
        verify_report(report, root=ROOT)

    def test_malformed_adapter_derives_incomplete(self) -> None:
        profile_id = next(
            item for item in PROFILE_ROLES if item != RECEIPT_PROFILE
        )
        report = self.run_subject(
            self.subject(profile_id), probe_name="malformed_probe.py"
        )
        self.assertEqual(report["summary"]["suite_verdict"], "incomplete")
        self.assertGreater(report["summary"]["errors"], 0)
        verify_report(report, root=ROOT)

    def test_oversized_probe_output_derives_incomplete(self) -> None:
        profile_id = next(
            item for item in PROFILE_ROLES if item != RECEIPT_PROFILE
        )
        report = self.run_subject(
            self.subject(profile_id), probe_name="oversized_probe.py"
        )
        self.assertEqual(report["summary"]["suite_verdict"], "incomplete")
        self.assertTrue(
            all(result["status"] == "error" for result in report["results"])
        )

    def test_timeout_is_not_a_passing_negative_vector(self) -> None:
        profile_id = next(
            item for item in PROFILE_ROLES if item != RECEIPT_PROFILE
        )
        report = self.run_subject(
            self.subject(profile_id), "timeout_adapter.py", timeout_seconds=1
        )
        self.assertEqual(report["summary"]["suite_verdict"], "incomplete")
        self.assertTrue(
            all(result["failure_token"] == "timeout" for result in report["results"])
        )

    def test_same_boundary_or_wrong_counterpart_cannot_satisfy_interop(self) -> None:
        profile_id = next(
            profile
            for profile in PROFILE_ROLES
            if any(
                vector["profile_id"] == profile
                and vector["execution_class"] == "interop"
                for vector in self.catalog.vectors.values()
            )
        )
        subject = self.subject(profile_id)
        for counterpart in subject["counterparts"]:
            counterpart["boundary_id"] = subject["boundary_id"]
        report = self.run_subject(subject)
        interop_errors = [
            result
            for result in report["results"]
            if self.catalog.vectors[result["vector_id"]]["execution_class"] == "interop"
        ]
        self.assertTrue(interop_errors)
        self.assertTrue(
            all(
                result["status"] == "error"
                and result["failure_token"] == "unavailable_probe"
                for result in interop_errors
            )
        )

    def test_report_rejects_missing_and_duplicate_results(self) -> None:
        profile_id = next(
            item for item in PROFILE_ROLES if item != RECEIPT_PROFILE
        )
        report = self.run_subject(self.subject(profile_id))
        missing = copy.deepcopy(report)
        missing["results"].pop()
        with self.assertRaisesRegex(ConformanceError, "exactly one ordered result"):
            verify_report(missing, root=ROOT)
        duplicate = copy.deepcopy(report)
        duplicate["results"].append(copy.deepcopy(duplicate["results"][0]))
        with self.assertRaisesRegex(ConformanceError, "exactly one ordered result"):
            verify_report(duplicate, root=ROOT)

    def test_report_rejects_stale_catalog_and_forged_summary(self) -> None:
        profile_id = next(
            item for item in PROFILE_ROLES if item != RECEIPT_PROFILE
        )
        report = self.run_subject(self.subject(profile_id))
        stale = copy.deepcopy(report)
        stale["suite"]["catalog_sha256"] = DIGEST_A
        with self.assertRaisesRegex(ConformanceError, "stale"):
            verify_report(stale, root=ROOT)
        forged = copy.deepcopy(report)
        forged["summary"]["suite_verdict"] = "fail"
        forged["summary"]["failed"] = 1
        with self.assertRaisesRegex(ConformanceError, "summary"):
            verify_report(forged, root=ROOT)

        float_summary = copy.deepcopy(report)
        float_summary["summary"]["passed"] = float(
            float_summary["summary"]["passed"]
        )
        with self.assertRaisesRegex(ConformanceError, "floating-point"):
            verify_report(float_summary, root=ROOT)

    def test_verify_report_cli_is_nonzero_for_valid_incomplete_report(self) -> None:
        profile_id = next(
            item for item in PROFILE_ROLES if item != RECEIPT_PROFILE
        )
        report = self.run_subject(self.subject(profile_id))
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual(main(["verify-report", str(report_path)]), 1)

    def test_extra_observation_token_cannot_preserve_pass(self) -> None:
        profile_id = next(
            item for item in PROFILE_ROLES if item != RECEIPT_PROFILE
        )
        report = self.run_subject(self.subject(profile_id))
        report["observations"][0]["tokens"].append("action_accepted")
        with self.assertRaisesRegex(ConformanceError, "status was not derived"):
            verify_report(report, root=ROOT)

    def test_one_role_report_cannot_be_relabelled_as_another(self) -> None:
        profiles = list(PROFILE_ROLES)
        report = self.run_subject(self.subject(profiles[0]))
        relabelled = copy.deepcopy(report)
        relabelled["subject"]["profile_id"] = profiles[1]
        with self.assertRaises(ConformanceError):
            verify_report(relabelled, root=ROOT)

    def test_observations_bind_the_exact_run_and_subject(self) -> None:
        profile_id = next(
            item for item in PROFILE_ROLES if item != RECEIPT_PROFILE
        )
        report = self.run_subject(self.subject(profile_id))

        relabelled_subject = copy.deepcopy(report)
        relabelled_subject["subject"]["implementation"]["artifact_sha256"] = DIGEST_C
        with self.assertRaises(ConformanceError):
            verify_report(relabelled_subject, root=ROOT)

        relabelled_run = copy.deepcopy(report)
        relabelled_run["run_id"] = "urn:uuid:00000000-0000-4000-8000-000000000000"
        with self.assertRaises(ConformanceError):
            verify_report(relabelled_run, root=ROOT)

        relabelled_harness = copy.deepcopy(report)
        relabelled_harness["runner"]["adapter_id"] = "relabelled-adapter"
        with self.assertRaisesRegex(ConformanceError, "binding"):
            verify_report(relabelled_harness, root=ROOT)

    def test_observation_timestamp_must_be_inside_run_interval(self) -> None:
        profile_id = next(
            item for item in PROFILE_ROLES if item != RECEIPT_PROFILE
        )
        report = self.run_subject(self.subject(profile_id))
        report["observations"][0]["captured_at"] = "2000-01-01T00:00:00Z"
        with self.assertRaisesRegex(ConformanceError, "outside the run interval"):
            verify_report(report, root=ROOT)

        invalid_rfc3339 = self.run_subject(self.subject(profile_id))
        invalid_rfc3339["started_at"] = invalid_rfc3339["started_at"].replace(
            "T", " "
        )
        with self.assertRaises(ConformanceError):
            verify_report(invalid_rfc3339, root=ROOT)


if __name__ == "__main__":
    unittest.main()
