from __future__ import annotations

import copy
import base64
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from conformance.check import (
    ConformanceError,
    PROFILE_ROLES,
    RECEIPT_PROFILE,
    _canonical_object_hash,
    _derive_impact_actions,
    _hash_without_member,
    _impact_candidate_projection,
    _resolved_fixture,
    _schema_registry,
    applicable_vectors,
    catalog_digest,
    loads_human_json,
    loads_strict_json,
    main,
    run_suite,
    select_risk_explanation_localization,
    validate_agent_human_elicitation_projection,
    validate_catalog,
    validate_human_elicitation,
    validate_human_elicitation_projection,
    validate_impact_simulation,
    validate_impact_simulation_projection,
    validate_risk_explanation,
    validate_risk_explanation_publisher_projection,
    validate_risk_explanation_projection,
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
HUMAN_CONTEXT_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/human-elicitation-context/v1"
)
HUMAN_REQUEST_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/human-elicitation-request/v1"
)
HUMAN_RESPONSE_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/human-elicitation-response/v1"
)
ACTION_INPUT_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/action-input/v1"
)
ACTION_INPUT_SCHEMA_DOMAIN = (
    "https://github.com/0al-spec/agent-surface/hash/action-input-schema/v1"
)


def refresh_human_hashes(elicitation: dict) -> None:
    request = elicitation["request"]
    response = elicitation["response"]
    request["context_hash"] = _canonical_object_hash(
        HUMAN_CONTEXT_DOMAIN, request["context"]
    )
    request["request_hash"] = _hash_without_member(
        HUMAN_REQUEST_DOMAIN, request, "request_hash"
    )
    response["context_hash"] = request["context_hash"]
    response["request_hash"] = request["request_hash"]
    response["response_hash"] = _hash_without_member(
        HUMAN_RESPONSE_DOMAIN, response, "response_hash"
    )


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
        self.assertEqual(self.catalog.suite["suite_version"], "1.8.0")
        self.assertEqual(len(self.catalog.features), 13)
        self.assertEqual(len(self.catalog.requirements), 46)
        self.assertEqual(len(self.catalog.vectors), 137)
        self.assertEqual(len(self.catalog.bundles), 8)
        self.assertEqual(len(self.catalog.fixtures), 39)
        self.assertEqual(len(self.catalog.mutations), 96)
        self.assertEqual(len(self.catalog.schema_case_catalog["cases"]), 65)
        self.assertRegex(catalog_digest(ROOT), r"^sha-256:[A-Za-z0-9_-]{43}$")

    def test_adoption_bundles_are_non_linear_closed_vector_plans(self) -> None:
        self.assertEqual(
            {bundle["kind"] for bundle in self.catalog.bundles.values()},
            {"foundation", "feature_overlay"},
        )
        self.assertIn(
            "https://github.com/0al-spec/agent-surface/conformance/bundles/mediated-proposal/v1",
            self.catalog.bundles,
        )
        serialized = json.dumps(self.catalog.bundle_registry, sort_keys=True)
        for forbidden in ("level", "rank", "assurance_score", "supersedes"):
            self.assertNotIn(f'"{forbidden}"', serialized)
        for bundle in self.catalog.bundles.values():
            for claim in bundle["claims"]:
                polarities = {
                    self.catalog.vectors[vector_id]["polarity"]
                    for vector_id in claim["vector_ids"]
                }
                self.assertEqual(polarities, {"positive", "negative"})

    def test_bundle_registry_rejects_omitted_requirement_and_vector(self) -> None:
        for member, message in (
            ("requirement_ids", "omits or reorders applicable requirements"),
            ("vector_ids", "omits or reorders executable vectors"),
        ):
            with self.subTest(member=member):
                root = self.catalog_copy()
                path = root / "conformance" / "v1" / "bundles.json"
                registry = json.loads(path.read_text(encoding="utf-8"))
                registry["bundles"][0]["claims"][1][member].pop()
                path.write_text(json.dumps(registry), encoding="utf-8")
                with self.assertRaisesRegex(ConformanceError, message):
                    validate_catalog(root)

    def test_bundle_registry_rejects_uncovered_role_feature_pair(self) -> None:
        root = self.catalog_copy()
        path = root / "conformance" / "v1" / "bundles.json"
        registry = json.loads(path.read_text(encoding="utf-8"))
        grant_claim = registry["bundles"][0]["claims"][1]
        grant_claim["feature_ids"] = ["agent-surface/feature/impact-simulation"]
        path.write_text(json.dumps(registry), encoding="utf-8")
        with self.assertRaisesRegex(
            ConformanceError, "selects features without matrix coverage"
        ):
            validate_catalog(root)

    def test_feature_vocabularies_match_the_catalog(self) -> None:
        expected = set(self.catalog.features)
        for schema_name in ("report", "subject", "suite", "vectors"):
            with self.subTest(schema_name=schema_name):
                schema = json.loads(
                    (
                        ROOT
                        / "conformance"
                        / "v1"
                        / f"{schema_name}.schema.json"
                    ).read_text(encoding="utf-8")
                )
                self.assertEqual(
                    set(schema["$defs"]["featureId"]["enum"]),
                    expected,
                )

    def test_vector_and_observation_vocabularies_match(self) -> None:
        schemas = {}
        for schema_name in ("vectors", "observation"):
            schemas[schema_name] = json.loads(
                (
                    ROOT
                    / "conformance"
                    / "v1"
                    / f"{schema_name}.schema.json"
                ).read_text(encoding="utf-8")
            )

        for definition in ("observationToken", "stateName"):
            with self.subTest(definition=definition):
                self.assertEqual(
                    schemas["vectors"]["$defs"][definition]["enum"],
                    schemas["observation"]["$defs"][definition]["enum"],
                )

        catalog_tokens = {
            token
            for vector in self.catalog.vectors.values()
            for field in ("required_observations", "forbidden_observations")
            for token in vector[field]
        }
        catalog_states = {
            delta["state"]
            for vector in self.catalog.vectors.values()
            for delta in vector["state_deltas"]
        }
        self.assertLessEqual(
            catalog_tokens,
            set(schemas["observation"]["$defs"]["observationToken"]["enum"]),
        )
        self.assertLessEqual(
            catalog_states,
            set(schemas["observation"]["$defs"]["stateName"]["enum"]),
        )

    def test_schema_case_polarities_are_executable_and_fail_closed(self) -> None:
        cases = self.catalog.schema_case_catalog["cases"]
        for schema_id in {
            "https://github.com/0al-spec/agent-surface/conformance/schemas/operational-limits/v1",
            "https://github.com/0al-spec/agent-surface/conformance/schemas/capacity-error/v1",
            "https://github.com/0al-spec/agent-surface/conformance/schemas/human-elicitation/v1",
            "https://github.com/0al-spec/agent-surface/conformance/schemas/impact-simulation/v1",
            "https://github.com/0al-spec/agent-surface/conformance/schemas/risk-explanation/v1",
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

    def test_risk_explanation_schema_rejects_terminal_lf_without_semantics(
        self,
    ) -> None:
        schema = json.loads(
            (
                ROOT
                / "conformance"
                / "v1"
                / "risk-explanation.schema.json"
            ).read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(schema)
        cases = {
            case["case_id"]: case
            for case in self.catalog.schema_case_catalog["cases"]
        }
        case_ids = {
            "ASP-SC-RE-105",
            "ASP-SC-RE-106",
            "ASP-SC-RE-107",
            "ASP-SC-RE-108",
        }
        self.assertLessEqual(case_ids, set(cases))
        for case_id in sorted(case_ids):
            with self.subTest(case_id=case_id):
                instance = loads_strict_json(
                    cases[case_id]["instance_json"],
                    source=case_id,
                )
                self.assertFalse(validator.is_valid(instance))

    def test_impact_simulation_schema_rejects_terminal_lf_and_non_ascii_uri(
        self,
    ) -> None:
        schema = json.loads(
            (
                ROOT
                / "conformance"
                / "v1"
                / "impact-simulation.schema.json"
            ).read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(
            schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        cases = {
            case["case_id"]: case
            for case in self.catalog.schema_case_catalog["cases"]
        }
        for case_id in ("ASP-SC-IS-101", "ASP-SC-IS-102"):
            with self.subTest(case_id=case_id):
                instance = loads_strict_json(
                    cases[case_id]["instance_json"],
                    source=case_id,
                )
                self.assertFalse(validator.is_valid(instance))

        positive = cases["ASP-SC-IS-001"]
        instance = loads_strict_json(positive["instance_json"])
        context = copy.deepcopy(positive["context"])
        invalid_uri = "https://example.com/réason"
        instance["examples"][0]["outcome"] = "indeterminate"
        instance["examples"][0]["reasons"] = [invalid_uri]
        context["candidate_check_facts"].append(
            {
                "check_id": invalid_uri,
                "state": "blocking",
                "subject": {"kind": "policy", "id": "current-inputs"},
            }
        )
        self.assertFalse(validator.is_valid(instance))
        with self.assertRaises(ConformanceError):
            validate_impact_simulation(instance, context)

    def test_impact_simulation_schema_bounds_coverage_and_effect_extensions(
        self,
    ) -> None:
        schema = json.loads(
            (
                ROOT
                / "conformance"
                / "v1"
                / "impact-simulation.schema.json"
            ).read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(
            schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        cases = {
            case["case_id"]: case
            for case in self.catalog.schema_case_catalog["cases"]
        }
        for case_id in (
            "ASP-SC-IS-109",
            "ASP-SC-IS-110",
            "ASP-SC-IS-111",
            "ASP-SC-IS-112",
        ):
            with self.subTest(case_id=case_id):
                instance = loads_strict_json(
                    cases[case_id]["instance_json"],
                    source=case_id,
                )
                self.assertFalse(validator.is_valid(instance))

        positive = loads_strict_json(cases["ASP-SC-IS-001"]["instance_json"])
        positive["examples"][0]["action"]["maximum_effects"] = [
            {
                "effect_id": "effect.read",
                "operation": "create",
                "resource_type": "item",
                "visibility": "private",
                "boundary": "internal",
                "reversibility": "reversible",
                "domain": "data",
                "https://example.com/effect/member": {"value": True},
            }
        ]
        self.assertTrue(validator.is_valid(positive))

    def test_impact_derivation_uses_verified_manifest_semantics(self) -> None:
        fixture = self.catalog.fixtures["ASP-F-RM-051"]["document"]
        source = fixture["impact_simulation"]["source"]
        registry = _schema_registry(ROOT)
        derived = _derive_impact_actions(
            copy.deepcopy(source["actions"]),
            source["requested_action_ids"],
            root=ROOT,
            registry=registry,
        )
        self.assertEqual(
            derived["action.write"]["required_companion_action_ids"],
            ["action.read"],
        )
        self.assertEqual(
            derived["action.write"]["recovery"],
            {
                "available_action_ids": ["action.revert"],
                "limitations": ["recovery_window_limited"],
            },
        )
        self.assertEqual(
            _impact_candidate_projection(
                source["candidate_check_facts"],
                None,
                source["bindings"],
            ),
            ("covered", []),
        )
        indeterminate = copy.deepcopy(source["candidate_check_facts"])
        next(
            fact
            for fact in indeterminate
            if fact["check_id"] == "required_input"
        )["state"] = "blocking"
        next(
            fact for fact in indeterminate if fact["check_id"] == "risk"
        )["state"] = "advisory"
        self.assertEqual(
            _impact_candidate_projection(
                indeterminate, None, source["bindings"]
            ),
            ("indeterminate", ["input_unknown"]),
        )
        incompatible = copy.deepcopy(indeterminate)
        next(
            fact for fact in incompatible if fact["check_id"] == "policy"
        )["state"] = "blocking"
        self.assertEqual(
            _impact_candidate_projection(
                incompatible, None, source["bindings"]
            ),
            ("not_covered", ["policy_denied"]),
        )
        extension_facts = copy.deepcopy(source["candidate_check_facts"])
        extension_facts.append(
            {
                "check_id": "https://example.com/check/custom",
                "state": "blocking",
                "subject": {"kind": "policy", "id": "extension-input"},
            }
        )
        extension_facts.sort(key=lambda fact: fact["check_id"].encode("utf-8"))
        self.assertEqual(
            _impact_candidate_projection(
                extension_facts, None, source["bindings"]
            ),
            ("indeterminate", ["https://example.com/check/custom"]),
        )
        incomplete_facts = copy.deepcopy(source["candidate_check_facts"])[1:]
        incomplete_facts.append(
            {
                "check_id": "https://example.com/check/replacement",
                "state": "satisfied",
                "subject": {"kind": "policy", "id": "replacement"},
            }
        )
        incomplete_facts.sort(key=lambda fact: fact["check_id"].encode("utf-8"))
        with self.assertRaisesRegex(ConformanceError, "complete for the core"):
            _impact_candidate_projection(
                incomplete_facts, None, source["bindings"]
            )

        reciprocal_cycle = copy.deepcopy(source["actions"])
        next(
            action
            for action in reciprocal_cycle
            if action["action_id"] == "action.read"
        )["required_companion_action_ids"] = ["action.write"]
        cyclic_derived = _derive_impact_actions(
            reciprocal_cycle,
            source["requested_action_ids"],
            root=ROOT,
            registry=registry,
        )
        self.assertEqual(
            cyclic_derived["action.read"]["required_companion_action_ids"],
            ["action.write"],
        )
        self.assertEqual(
            cyclic_derived["action.write"]["required_companion_action_ids"],
            ["action.read"],
        )

        low_risk = copy.deepcopy(source["actions"])
        next(
            action for action in low_risk if action["action_id"] == "action.publish"
        )["risk"] = "write"
        with self.assertRaisesRegex(ConformanceError, "effect floor"):
            _derive_impact_actions(
                low_risk,
                source["requested_action_ids"],
                root=ROOT,
                registry=registry,
            )

        empty_commit = copy.deepcopy(source["actions"])
        next(
            action for action in empty_commit if action["action_id"] == "action.delete"
        )["effects"] = []
        with self.assertRaisesRegex(ConformanceError, "mode and effect"):
            _derive_impact_actions(
                empty_commit,
                source["requested_action_ids"],
                root=ROOT,
                registry=registry,
            )

        projection = copy.deepcopy(fixture["impact_simulation"])
        match_binding = {
            "match_id": "match_current",
            "evaluated_at": "2026-07-19T09:59:00Z",
            "valid_until": "2026-07-19T10:05:00Z",
        }
        projection["source"]["bindings"]["capability_match"] = match_binding
        projection["result"]["bindings"]["capability_match"] = copy.deepcopy(
            match_binding
        )
        projection["source"]["freshness_deadlines"][
            "capability_match"
        ] = match_binding["valid_until"]
        projection["current_binding_facts"] = copy.deepcopy(
            projection["source"]["bindings"]
        )
        projection["source"]["matched_candidate"] = {
            "bindings": copy.deepcopy(projection["source"]["bindings"]),
            "agent_id": "wrong-agent",
            "identity_evidence_hash": projection["source"]["bindings"][
                "delegate"
            ]["identity_evidence_hash"],
            "grant_request_hash": projection["source"]["bindings"][
                "grant_request_hash"
            ],
            "status": "compatible",
            "reasons": [],
        }
        with self.assertRaisesRegex(ConformanceError, "exact delegate"):
            validate_impact_simulation_projection(
                projection,
                fixture["surface"],
                fixture["grant"],
                fixture["execution"],
                root=ROOT,
            )

        absent_runtime_identity = copy.deepcopy(fixture["impact_simulation"])
        identity_fact = next(
            fact
            for fact in absent_runtime_identity["source"][
                "candidate_check_facts"
            ]
            if fact["check_id"] == "runtime_identity_availability"
        )
        identity_fact["state"] = "blocking"
        absent_runtime_identity["source"]["freshness_deadlines"][
            "runtime_identity"
        ] = None
        for example in absent_runtime_identity["result"]["examples"][:3]:
            example["outcome"] = "indeterminate"
            example["reasons"] = ["runtime_identity_unavailable"]
        validate_impact_simulation_projection(
            absent_runtime_identity,
            fixture["surface"],
            fixture["grant"],
            fixture["execution"],
            root=ROOT,
        )
        inconsistent_deadline = copy.deepcopy(fixture["impact_simulation"])
        inconsistent_deadline["source"]["freshness_deadlines"][
            "runtime_identity"
        ] = None
        with self.assertRaisesRegex(
            ConformanceError, "deadline presence differs"
        ):
            validate_impact_simulation_projection(
                inconsistent_deadline,
                fixture["surface"],
                fixture["grant"],
                fixture["execution"],
                root=ROOT,
            )

        schema = json.loads(
            (
                ROOT
                / "conformance"
                / "v1"
                / "impact-simulation.schema.json"
            ).read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(
            schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        result = copy.deepcopy(fixture["impact_simulation"]["result"])
        result["examples"][0]["action"]["risk"] = "bare-extension"
        self.assertFalse(validator.is_valid(result))
        result["examples"][0]["action"]["risk"] = (
            "https://example.com/risk/custom"
        )
        self.assertTrue(validator.is_valid(result))
        for field in (
            "operation",
            "visibility",
            "boundary",
            "reversibility",
            "domain",
        ):
            with self.subTest(extension_field=field):
                bare = copy.deepcopy(fixture["impact_simulation"]["result"])
                bare["examples"][1]["action"]["maximum_effects"][0][field] = (
                    "bare-extension"
                )
                self.assertFalse(validator.is_valid(bare))
                uri = copy.deepcopy(fixture["impact_simulation"]["result"])
                uri["examples"][1]["action"]["maximum_effects"][0][field] = (
                    f"https://example.com/effect/{field}"
                )
                self.assertTrue(validator.is_valid(uri))

        unsupported_mapping = copy.deepcopy(source["actions"])
        next(
            action
            for action in unsupported_mapping
            if action["action_id"] == "action.revert"
        )["effects"][0]["boundary"] = "https://example.com/boundary/remote"
        with self.assertRaisesRegex(ConformanceError, "unsupported effect mapping"):
            _derive_impact_actions(
                unsupported_mapping,
                source["requested_action_ids"],
                root=ROOT,
                registry=registry,
            )

    def test_impact_negative_vectors_reach_semantic_failures(self) -> None:
        for vector_id in (
            "ASP-V-RM-052",
            "ASP-V-RM-053",
            "ASP-V-RM-054",
            "ASP-V-RM-055",
            "ASP-V-RM-056",
            "ASP-V-RM-057",
            "ASP-V-RM-058",
            "ASP-V-RM-060",
            "ASP-V-RM-061",
            "ASP-V-RM-062",
            "ASP-V-RM-064",
            "ASP-V-RM-065",
            "ASP-V-RM-066",
            "ASP-V-RM-067",
            "ASP-V-RM-068",
        ):
            with self.subTest(vector_id=vector_id):
                document = _resolved_fixture(
                    self.catalog, self.catalog.vectors[vector_id]
                )["document"]
                with self.assertRaises(ConformanceError):
                    validate_impact_simulation_projection(
                        document["impact_simulation"],
                        document["surface"],
                        document["grant"],
                        document["execution"],
                        root=ROOT,
                    )

        for vector_id, carrier, operation in (
            ("ASP-V-RM-059", "grant", "mediate_grant"),
            ("ASP-V-RM-063", "execution", "mediate_action"),
            ("ASP-V-RM-069", "grant", "simulate_impact"),
            ("ASP-V-RM-070", "execution", "simulate_impact"),
            ("ASP-V-RM-071", "grant", "mediate_action"),
        ):
            with self.subTest(vector_id=vector_id):
                vector = self.catalog.vectors[vector_id]
                self.assertEqual(vector["stimulus"]["operation"], operation)
                document = _resolved_fixture(self.catalog, vector)["document"]
                self.assertEqual(
                    document[carrier]["impact_simulation"],
                    document["impact_simulation"]["result"],
                )
                with self.assertRaisesRegex(
                    ConformanceError,
                    "absent from closed Grant and Action",
                ):
                    validate_impact_simulation_projection(
                        document["impact_simulation"],
                        document["surface"],
                        document["grant"],
                        document["execution"],
                        root=ROOT,
                    )

    def test_risk_explanation_lookup_binding_and_machine_fallback_inputs(self) -> None:
        fixture = self.catalog.fixtures["ASP-F-RM-043"]
        projection = copy.deepcopy(fixture["document"]["risk_explanation"])
        hint = projection["hint"]

        selected = select_risk_explanation_localization(
            hint,
            ["fr-ca", "fr-ca", "en"],
        )
        self.assertEqual(selected["language"], "fr")
        defaulted = select_risk_explanation_localization(hint, [])
        self.assertEqual(defaulted["language"], "en")
        with self.assertRaises(ConformanceError):
            select_risk_explanation_localization(hint, ["en"] * 17)

        validate_risk_explanation(
            hint,
            {"effect_ids": ["comment-publish"]},
            root=ROOT,
        )
        validate_risk_explanation_projection(
            projection,
            fixture["document"]["surface"],
            root=ROOT,
        )

        incomplete_surface = copy.deepcopy(fixture["document"]["surface"])
        incomplete_surface["references"] = "incomplete"
        with self.assertRaisesRegex(ConformanceError, "complete verified retained"):
            validate_risk_explanation_projection(
                projection,
                incomplete_surface,
                root=ROOT,
            )

        for presentation_field in ("escaped", "bidi_isolated"):
            with self.subTest(presentation_field=presentation_field, state="missing"):
                missing = copy.deepcopy(projection)
                del missing[presentation_field]
                with self.assertRaisesRegex(ConformanceError, "closed presentation"):
                    validate_risk_explanation_projection(
                        missing,
                        fixture["document"]["surface"],
                        root=ROOT,
                    )
            with self.subTest(presentation_field=presentation_field, state="false"):
                disabled = copy.deepcopy(projection)
                disabled[presentation_field] = False
                with self.assertRaisesRegex(ConformanceError, "bidi-isolated"):
                    validate_risk_explanation_projection(
                        disabled,
                        fixture["document"]["surface"],
                        root=ROOT,
                    )

        publisher_owned_only = copy.deepcopy(projection)
        publisher_owned_only["language_preferences"] = ["not-a-language-tag!"]
        publisher_owned_only["selected_language"] = "de"
        publisher_owned_only["rendered_summary"] = "Runtime-owned stale state"
        publisher_owned_only["rendered_effect_summaries"] = []
        publisher_owned_only["rendering"] = "not-a-rendering-mode"
        publisher_owned_only["authority_use"] = "attempted"
        publisher_owned_only["agent_projection"] = "present"
        validate_risk_explanation_publisher_projection(
            publisher_owned_only,
            fixture["document"]["surface"],
            root=ROOT,
        )

        next_surface = copy.deepcopy(fixture["document"]["surface"])
        next_surface["candidate_hash"] = "surface_hash_b"
        next_publisher = copy.deepcopy(projection)
        next_publisher["hint_surface_hash"] = "surface_hash_b"
        validate_risk_explanation_publisher_projection(
            next_publisher,
            next_surface,
            root=ROOT,
        )
        validate_risk_explanation_projection(
            projection,
            next_surface,
            root=ROOT,
        )

        substituted = copy.deepcopy(projection)
        substituted["hint_action_id"] = "comment.delete"
        with self.assertRaisesRegex(ConformanceError, "authoritative action"):
            validate_risk_explanation_projection(
                substituted,
                fixture["document"]["surface"],
                root=ROOT,
            )

        controlled = copy.deepcopy(hint)
        controlled["localizations"][0]["summary"] = "unsafe\u0000summary"
        with self.assertRaises(ConformanceError):
            validate_risk_explanation(
                controlled,
                {"effect_ids": ["comment-publish"]},
                root=ROOT,
            )
        for language in ("en-a", "en-12"):
            with self.subTest(language=language):
                invalid_language = copy.deepcopy(hint)
                invalid_language["default_language"] = language
                invalid_language["localizations"][0]["language"] = language
                with self.assertRaises(ConformanceError):
                    validate_risk_explanation(
                        invalid_language,
                        {"effect_ids": ["comment-publish"]},
                        root=ROOT,
                    )

        repeated_variant = copy.deepcopy(hint)
        repeated_variant["default_language"] = "de-1901-1901"
        repeated_variant["localizations"][0]["language"] = "de-1901-1901"
        with self.assertRaisesRegex(ConformanceError, "repeats a variant"):
            validate_risk_explanation(
                repeated_variant,
                {"effect_ids": ["comment-publish"]},
                root=ROOT,
            )

        bidi = copy.deepcopy(hint)
        bidi["localizations"][0]["summary"] = "unsafe\u202esummary"
        with self.assertRaises(ConformanceError):
            validate_risk_explanation(
                bidi,
                {"effect_ids": ["comment-publish"]},
                root=ROOT,
            )

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

    def test_human_elicitation_baselines_are_semantically_bound(self) -> None:
        elicitation_vectors = {
            "ASP-V-RM-033",
            "ASP-V-RM-034",
            "ASP-V-RM-035",
            "ASP-V-RM-036",
            "ASP-V-RM-037",
            "ASP-V-RM-038",
            "ASP-V-RM-039",
            "ASP-V-RM-040",
            "ASP-V-RM-041",
            "ASP-V-RM-042",
            "ASP-V-AE-027",
            "ASP-V-AE-028",
            "ASP-V-AE-029",
            "ASP-V-AE-030",
            "ASP-V-AE-031",
            "ASP-V-AA-009",
            "ASP-V-AA-010",
            "ASP-V-AA-011",
        }
        self.assertEqual(
            {
                vector_id
                for vector_id, vector in self.catalog.vectors.items()
                if "human_elicitation_selected" in vector["setup"]
            },
            elicitation_vectors,
        )

        root = self.catalog_copy()
        path = root / "conformance" / "v1" / "fixtures.json"
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        baseline = next(
            item
            for item in fixtures["fixtures"]
            if item["fixture_id"] == "ASP-F-RM-034"
        )
        baseline["document"]["elicitation"]["response"]["session_generation"] = 2
        path.write_text(json.dumps(fixtures), encoding="utf-8")
        with self.assertRaisesRegex(
            ConformanceError,
            "response_hash is invalid",
        ):
            validate_catalog(root)

    def test_human_hashing_uses_rfc8785_numbers_and_utf16_order(self) -> None:
        domain = "urn:example:human-jcs"
        value = {"\ue000": 2, "\U00010000": 1.5}
        canonical = (
            '{"domain":"urn:example:human-jcs",'
            '"object":{"\U00010000":1.5,"\ue000":2}}'
        ).encode("utf-8")
        expected = "sha-256:" + base64.urlsafe_b64encode(
            hashlib.sha256(canonical).digest()
        ).rstrip(b"=").decode("ascii")
        self.assertEqual(_canonical_object_hash(domain, value), expected)
        self.assertEqual(loads_human_json('{"value":1.5}')["value"], 1.5)
        for document in ('{"value":-0}', '{"value":-0.0}'):
            with self.subTest(document=document):
                with self.assertRaisesRegex(ConformanceError, "negative zero"):
                    loads_human_json(document)
        with self.assertRaisesRegex(ConformanceError, "negative zero"):
            _canonical_object_hash(domain, {"value": -0.0})

    def test_human_schema_case_parser_accepts_binary64_edit_base(self) -> None:
        positive = next(
            item
            for item in self.catalog.schema_case_catalog["cases"]
            if item["case_id"] == "ASP-SC-HE-002"
        )
        request = loads_human_json(positive["instance_json"])
        base = request["request"]["base"]
        self.assertEqual(base["\U00010000"], 1.5)
        self.assertEqual(
            request["request"]["base_hash"],
            _canonical_object_hash(ACTION_INPUT_DOMAIN, base),
        )
        self.assertEqual(
            request["request_hash"],
            _hash_without_member(HUMAN_REQUEST_DOMAIN, request, "request_hash"),
        )
        negative = next(
            item
            for item in self.catalog.schema_case_catalog["cases"]
            if item["case_id"] == "ASP-SC-HE-102"
        )
        with self.assertRaisesRegex(ConformanceError, "negative zero"):
            loads_human_json(negative["instance_json"])

    def test_human_participant_types_must_differ(self) -> None:
        case = next(
            item
            for item in self.catalog.schema_case_catalog["cases"]
            if item["case_id"] == "ASP-SC-HE-001"
        )
        request = loads_human_json(case["instance_json"])
        request["presenter"] = {"type": "application", "id": "app_b"}
        request["request_hash"] = _hash_without_member(
            HUMAN_REQUEST_DOMAIN, request, "request_hash"
        )
        with self.assertRaisesRegex(
            ConformanceError, "requester.type and presenter.type must differ"
        ):
            validate_human_elicitation(request, {})

    def test_clarification_max_bytes_uses_rfc8785_utf8(self) -> None:
        clarify = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-033"]["document"]["elicitation"]
        )
        response_schema = {"type": "number"}
        clarify["request"]["request"]["response_schema"] = response_schema
        clarify["request"]["request"]["response_schema_hash"] = (
            _canonical_object_hash(ACTION_INPUT_SCHEMA_DOMAIN, response_schema)
        )
        clarify["request"]["request"]["max_bytes"] = 4
        clarify["response"]["response"]["answer"] = 1e-7
        refresh_human_hashes(clarify)
        validate_human_elicitation_projection(clarify)

        clarify["request"]["request"]["max_bytes"] = 3
        refresh_human_hashes(clarify)
        with self.assertRaisesRegex(ConformanceError, "exceeds max_bytes"):
            validate_human_elicitation_projection(clarify)

    def test_human_embedded_schemas_reject_external_dynamic_refs(self) -> None:
        clarify = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-033"]["document"]["elicitation"]
        )
        response_schema = {
            "$dynamicRef": "https://example.invalid/external-schema"
        }
        clarify["request"]["request"]["response_schema"] = response_schema
        clarify["request"]["request"]["response_schema_hash"] = (
            _canonical_object_hash(ACTION_INPUT_SCHEMA_DOMAIN, response_schema)
        )
        refresh_human_hashes(clarify)
        with self.assertRaisesRegex(ConformanceError, "must be self-contained"):
            validate_human_elicitation_projection(clarify)

    def test_redline_rejects_invalid_json_patch_array_indexes(self) -> None:
        operations = (
            {"op": "add", "path": "/items/-1", "value": "new"},
            {"op": "add", "path": "/items/999", "value": "new"},
            {"op": "replace", "path": "/items/-1", "value": "new"},
            {"op": "replace", "path": "/items/01", "value": "new"},
            {"op": "remove", "path": "/items/-1"},
        )
        for operation in operations:
            with self.subTest(operation=operation):
                redline = copy.deepcopy(
                    self.catalog.fixtures["ASP-F-AE-028"]["document"][
                        "elicitation"
                    ]
                )
                base = {"items": ["first", "second"]}
                base_hash = _canonical_object_hash(ACTION_INPUT_DOMAIN, base)
                redline["authoritative_base"] = base
                redline["request"]["context"]["input_hash"] = base_hash
                redline["request"]["request"]["base_hash"] = base_hash
                redline["response"]["response"]["base_hash"] = base_hash
                redline["response"]["response"]["patch"] = [operation]
                refresh_human_hashes(redline)
                with self.assertRaisesRegex(
                    ConformanceError, "JSON Patch array index is invalid"
                ):
                    validate_human_elicitation_projection(redline)

    def test_human_resolution_cannot_follow_evaluation_time(self) -> None:
        clarify = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-033"]["document"]["elicitation"]
        )
        clarify["response"]["resolved_at"] = "2026-07-18T13:07:00Z"
        refresh_human_hashes(clarify)
        with self.assertRaisesRegex(ConformanceError, "after evaluation_time"):
            validate_human_elicitation_projection(clarify)

    def test_human_kind_specific_constraints_fail_after_valid_hashes(self) -> None:
        clarify = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-033"]["document"]["elicitation"]
        )
        clarify["response"]["response"]["answer"] = 7
        refresh_human_hashes(clarify)
        with self.assertRaisesRegex(ConformanceError, "clarification answer"):
            validate_human_elicitation_projection(clarify)

        step_up = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-035"]["document"]["elicitation"]
        )
        step_up["authenticated_verifier"] = {
            "type": "external",
            "id": "verifier_b",
        }
        with self.assertRaisesRegex(ConformanceError, "verifier binding"):
            validate_human_elicitation_projection(step_up)
        step_up = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-035"]["document"]["elicitation"]
        )
        step_up["response"]["response"]["authenticated_at"] = (
            "2026-07-18T12:55:00Z"
        )
        step_up["authoritative_step_up_result"]["authenticated_at"] = (
            "2026-07-18T12:55:00Z"
        )
        refresh_human_hashes(step_up)
        with self.assertRaisesRegex(ConformanceError, "max_age_seconds"):
            validate_human_elicitation_projection(step_up)

        authoritative_fields = {
            "status": "unverified",
            "result_ref": "auth_result_other",
            "verifier": {"type": "external", "id": "verifier_b"},
            "audience": {"type": "runtime", "id": "runtime_a"},
            "subject": "user_other",
            "elicitation_id": "elicit_other",
            "revision": 2,
            "context_hash": digest("other-context"),
            "achieved_assurance": ["https://example.com/assurance/a3"],
            "authenticated_at": "2026-07-18T13:03:00Z",
            "expires_at": "2026-07-18T13:08:00Z",
        }
        for field, value in authoritative_fields.items():
            with self.subTest(authoritative_field=field):
                step_up = copy.deepcopy(
                    self.catalog.fixtures["ASP-F-RM-035"]["document"][
                        "elicitation"
                    ]
                )
                step_up["authoritative_step_up_result"][field] = value
                with self.assertRaisesRegex(ConformanceError, "verifier binding"):
                    validate_human_elicitation_projection(step_up)

        edit = _resolved_fixture(
            self.catalog,
            self.catalog.vectors["ASP-V-AE-029"],
        )["document"]["elicitation"]
        with self.assertRaisesRegex(ConformanceError, "forbidden path"):
            validate_human_elicitation_projection(edit)

        redline = copy.deepcopy(
            self.catalog.fixtures["ASP-F-AE-028"]["document"]["elicitation"]
        )
        redline["response"]["response"]["patch"][0]["path"] = "/metadata"
        redline["response"]["response"]["patch"][0]["value"] = "unsafe"
        redline["response"]["response"]["candidate_hash"] = _canonical_object_hash(
            ACTION_INPUT_DOMAIN,
            {"message": "Old text", "metadata": "unsafe"},
        )
        refresh_human_hashes(redline)
        with self.assertRaisesRegex(ConformanceError, "forbidden path"):
            validate_human_elicitation_projection(redline)

        redline = copy.deepcopy(
            self.catalog.fixtures["ASP-F-AE-028"]["document"]["elicitation"]
        )
        redline["response"]["response"]["patch"][0]["value"] = 7
        redline["response"]["response"]["candidate_hash"] = _canonical_object_hash(
            ACTION_INPUT_DOMAIN,
            {"message": 7, "metadata": "safe"},
        )
        refresh_human_hashes(redline)
        with self.assertRaisesRegex(ConformanceError, "redline patch"):
            validate_human_elicitation_projection(redline)

    def test_human_negative_vectors_reach_bound_semantic_failures(self) -> None:
        expected = {
            "ASP-V-RM-036": "exact request binding",
            "ASP-V-RM-038": "verifier binding",
            "ASP-V-RM-040": "verifier binding",
            "ASP-V-RM-041": "self-contained",
            "ASP-V-RM-042": "after evaluation_time",
            "ASP-V-AE-029": "forbidden path",
            "ASP-V-AE-030": "base or result binding",
            "ASP-V-AE-031": "array index",
        }
        for vector_id, message in expected.items():
            with self.subTest(vector_id=vector_id):
                elicitation = _resolved_fixture(
                    self.catalog,
                    self.catalog.vectors[vector_id],
                )["document"]["elicitation"]
                with self.assertRaisesRegex(ConformanceError, message):
                    validate_human_elicitation_projection(elicitation)

    def test_human_terminal_replay_requires_current_retained_record(self) -> None:
        replay = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-039"]["document"]["elicitation"]
        )
        validate_human_elicitation_projection(replay)
        replay["replay_record_state"] = "evicted"
        with self.assertRaisesRegex(ConformanceError, "unavailable or expired"):
            validate_human_elicitation_projection(replay)
        replay = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-039"]["document"]["elicitation"]
        )
        replay["evaluation_time"] = "2026-07-18T14:06:00Z"
        with self.assertRaisesRegex(ConformanceError, "unavailable or expired"):
            validate_human_elicitation_projection(replay)
        replay = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-039"]["document"]["elicitation"]
        )
        replay["terminal_accepted_at"] = "absent"
        with self.assertRaisesRegex(ConformanceError, "lacks terminal_accepted_at"):
            validate_human_elicitation_projection(replay)
        replay = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-039"]["document"]["elicitation"]
        )
        replay["terminal_accepted_at"] = "2026-07-18T13:04:59Z"
        with self.assertRaisesRegex(ConformanceError, "not current"):
            validate_human_elicitation_projection(replay)

    def test_agent_adapter_human_projection_is_minimized_and_bound(self) -> None:
        positive = copy.deepcopy(
            self.catalog.fixtures["ASP-F-AA-009"]["document"]["elicitation"]
        )
        validate_agent_human_elicitation_projection(positive)
        for vector_id in ("ASP-V-AA-010", "ASP-V-AA-011"):
            with self.subTest(vector_id=vector_id):
                elicitation = _resolved_fixture(
                    self.catalog,
                    self.catalog.vectors[vector_id],
                )["document"]["elicitation"]
                with self.assertRaisesRegex(
                    ConformanceError,
                    "originated, unbound, overbroad, or secret-bearing",
                ):
                    validate_agent_human_elicitation_projection(elicitation)

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
