"""Regression tests for vertical-slice evidence and binding validation."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


SLICE = Path(__file__).resolve().parents[1]
ROOT = SLICE.parents[1]
if str(SLICE) not in sys.path:
    sys.path.insert(0, str(SLICE))

from check import (  # noqa: E402
    SliceError,
    artifact_digest,
    validate_evidence_schema,
    validate_participant_bindings,
    validate_suite_binding,
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class BindingValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load(SLICE / "v1" / "manifest.json")
        cls.configs = {
            entry["participant_id"]: load(ROOT / entry["config_path"])
            for entry in cls.manifest["participants"]
        }

    def test_suite_binding_rejects_version_drift(self) -> None:
        suite = load(ROOT / "conformance" / "v1" / "suite.json")
        validate_suite_binding(self.manifest, suite)
        stale = copy.deepcopy(self.manifest)
        stale["suite_version"] = "0.0.0"
        with self.assertRaisesRegex(SliceError, "suite_version"):
            validate_suite_binding(stale, suite)

    def test_participant_entrypoint_drift_is_rejected(self) -> None:
        configs = copy.deepcopy(self.configs)
        configs["reference-app-control"]["entrypoint"]["path"] = (
            "reference/vertical-slice/app/src/bin/app_executor.rs"
        )
        with self.assertRaisesRegex(SliceError, "entrypoint"):
            validate_participant_bindings(self.manifest, configs)

    def test_participant_claim_and_lane_drift_are_rejected(self) -> None:
        for member, value in (
            ("claim_role", "additional_tested_participant"),
            ("lane_membership", ["remote"]),
        ):
            with self.subTest(member=member):
                configs = copy.deepcopy(self.configs)
                configs["reference-app-control"][member] = value
                with self.assertRaises(SliceError):
                    validate_participant_bindings(self.manifest, configs)

    def test_rust_participant_requires_locked_build_provenance(self) -> None:
        configs = copy.deepcopy(self.configs)
        configs["reference-app-control"]["implementation"]["artifact_paths"].remove(
            "Cargo.lock"
        )
        with self.assertRaisesRegex(SliceError, "artifact closure"):
            validate_participant_bindings(self.manifest, configs)

    def test_lockfile_changes_rust_artifact_digest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="asp-slice-digest-") as directory:
            root = Path(directory)
            (root / "Cargo.lock").write_text("version = 1\n", encoding="utf-8")
            (root / "source.rs").write_text("fn main() {}\n", encoding="utf-8")
            paths = ["Cargo.lock", "source.rs"]
            before = artifact_digest(root, paths)
            (root / "Cargo.lock").write_text("version = 2\n", encoding="utf-8")
            self.assertNotEqual(before, artifact_digest(root, paths))


class EvidenceSchemaTests(unittest.TestCase):
    @staticmethod
    def valid_evidence() -> dict:
        digest = "sha-256:" + "A" * 43
        participants = [
            ("reference-agent-a", "reference/agent/a", "reference/implementation/agent-a-python-v1"),
            ("reference-agent-b", "reference/agent/b", "reference/implementation/agent-b-python-v1"),
            (
                "reference-app-control",
                "reference/application/control",
                "reference/implementation/application-rust-v1",
            ),
            (
                "reference-app-executor",
                "reference/application/executor",
                "reference/implementation/application-rust-v1",
            ),
            (
                "reference-app-receipt",
                "reference/application/receipt",
                "reference/implementation/application-rust-v1",
            ),
            (
                "reference-runtime-local",
                "reference/runtime/local",
                "reference/implementation/runtime-local-python-v1",
            ),
            (
                "reference-runtime-remote",
                "reference/runtime/remote",
                "reference/implementation/runtime-remote-python-v1",
            ),
        ]
        report_specs = [
            ("surface-publisher", "reference-app-control", 1, 2, None),
            ("grant-issuer", "reference-app-control", 3, 3, None),
            ("action-executor", "reference-app-executor", 2, 9, None),
            ("receipt-producer", "reference-app-receipt", 1, 3, "application"),
            ("runtime-mediator", "reference-runtime-local", 1, 5, None),
            ("agent-adapter", "reference-agent-a", 1, 4, None),
        ]
        reports = []
        for profile, subject, positive, negative, producer_role in report_specs:
            report = {
                "profile_id": (
                    "https://github.com/0al-spec/agent-surface/conformance/"
                    f"{profile}/v1"
                ),
                "subject_id": subject,
                "run_id": f"https://example.test/runs/{profile}",
                "report_sha256": digest,
                "verdict": "pass",
                "positive_count": positive,
                "negative_count": negative,
            }
            if producer_role is not None:
                report["producer_role"] = producer_role
            reports.append(report)
        return {
            "$schema": "./evidence.schema.json",
            "schema_version": 1,
            "review_id": 74,
            "claim_effect": "descriptive_only",
            "max_maturity": "implementation_tested",
            "independence": "not_established",
            "bundle_id": (
                "https://github.com/0al-spec/agent-surface/conformance/"
                "bundles/application-audited-effects/v1"
            ),
            "participants": [
                {
                    "participant_id": participant_id,
                    "boundary_id": boundary_id,
                    "lineage_id": lineage_id,
                    "artifact_sha256": digest,
                    "configuration_sha256": digest,
                }
                for participant_id, boundary_id, lineage_id in participants
            ],
            "reports": reports,
            "scenario": {
                "schema_version": 1,
                "scenario_id": "card-74-task-comments",
                "verdict": "pass",
                "transport": "tcp-json-lines",
                "lanes": [
                    {
                        "lane_id": "local",
                        "runtime_participant_id": "reference-runtime-local",
                        "agent_participant_id": "reference-agent-a",
                        "positive": ["create"],
                        "negative": ["credential"],
                    },
                    {
                        "lane_id": "remote",
                        "runtime_participant_id": "reference-runtime-remote",
                        "agent_participant_id": "reference-agent-b",
                        "positive": ["create"],
                        "negative": ["revocation"],
                    },
                ],
                "effect_count": 2,
                "receipt_count": 2,
                "credentials_exposed": False,
                "transcript_sha256": digest,
            },
            "non_claims": [
                "certification",
                "independent_interoperability",
                "production_readiness",
                "security_certification",
                "stable_maturity",
            ],
        }

    def test_exact_evidence_topology_is_accepted(self) -> None:
        validate_evidence_schema(ROOT, self.valid_evidence())

    def test_duplicate_topology_and_incomplete_non_claims_are_rejected(self) -> None:
        mutations = {
            "participant": lambda value: value["participants"].__setitem__(
                1, copy.deepcopy(value["participants"][0])
            ),
            "report": lambda value: value["reports"].__setitem__(
                1, copy.deepcopy(value["reports"][0])
            ),
            "lane": lambda value: value["scenario"]["lanes"].__setitem__(
                1, copy.deepcopy(value["scenario"]["lanes"][0])
            ),
            "non_claims": lambda value: value["non_claims"].pop(),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                evidence = self.valid_evidence()
                mutate(evidence)
                with self.assertRaises(SliceError):
                    validate_evidence_schema(ROOT, evidence)


if __name__ == "__main__":
    unittest.main()
