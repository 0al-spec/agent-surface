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
    _mcp_contains_forbidden_credential,
    _resolved_fixture,
    _schema_registry,
    _validate_mcp_credential_free_uri,
    _validate_mcp_execution_token_pair,
    _validate_mcp_schema_instance,
    _validate_with_schema,
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
    validate_mcp_binding_projection,
    validate_mcp_wire_semantics,
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
        self.assertEqual(self.catalog.suite["suite_version"], "1.9.0")
        self.assertEqual(len(self.catalog.features), 14)
        self.assertEqual(len(self.catalog.requirements), 51)
        self.assertEqual(len(self.catalog.vectors), 163)
        self.assertEqual(len(self.catalog.bundles), 8)
        self.assertEqual(len(self.catalog.fixtures), 44)
        self.assertEqual(len(self.catalog.mutations), 117)
        self.assertEqual(len(self.catalog.schema_case_catalog["cases"]), 124)
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

    def test_asp_over_mcp_baselines_are_semantically_bound(self) -> None:
        mcp_vectors = {
            "ASP-V-SP-010",
            "ASP-V-SP-011",
            "ASP-V-SP-012",
            "ASP-V-SP-013",
            "ASP-V-AE-032",
            "ASP-V-AE-033",
            "ASP-V-AE-034",
            "ASP-V-AE-035",
            "ASP-V-AE-036",
            "ASP-V-AE-037",
            "ASP-V-RM-072",
            "ASP-V-RM-073",
            "ASP-V-RM-074",
            "ASP-V-RM-075",
            "ASP-V-RM-076",
            "ASP-V-RM-077",
            "ASP-V-RM-078",
            "ASP-V-RM-079",
            "ASP-V-RM-080",
            "ASP-V-AA-012",
            "ASP-V-AA-013",
            "ASP-V-AA-014",
            "ASP-V-AA-015",
            "ASP-V-GI-008",
            "ASP-V-GI-009",
            "ASP-V-GI-010",
        }
        self.assertEqual(
            {
                vector_id
                for vector_id, vector in self.catalog.vectors.items()
                if "asp_over_mcp_selected" in vector["setup"]
            },
            mcp_vectors,
        )

        # Discovery binds tools to the manifest inventory, never to a pre-existing Grant.
        root = self.catalog_copy()
        path = root / "conformance" / "v1" / "fixtures.json"
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        publisher = next(
            item
            for item in fixtures["fixtures"]
            if item["fixture_id"] == "ASP-F-SP-010"
        )
        publisher["document"]["grant"]["issued_actions"] = ["action.read"]
        path.write_text(json.dumps(fixtures), encoding="utf-8")
        validate_catalog(root)

        # Execution must independently prove that the exact mapped action is issued.
        root = self.catalog_copy()
        path = root / "conformance" / "v1" / "fixtures.json"
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        executor = next(
            item
            for item in fixtures["fixtures"]
            if item["fixture_id"] == "ASP-F-AE-032"
        )
        executor["document"]["grant"]["issued_actions"] = ["action.read"]
        path.write_text(json.dumps(fixtures), encoding="utf-8")
        with self.assertRaisesRegex(ConformanceError, "outside the issued ASP Grant"):
            validate_catalog(root)

        root = self.catalog_copy()
        path = root / "conformance" / "v1" / "fixtures.json"
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        runtime = next(
            item
            for item in fixtures["fixtures"]
            if item["fixture_id"] == "ASP-F-RM-072"
        )
        runtime["document"]["mcp"]["result_grant_hash"] = "grant_hash_b"
        path.write_text(json.dumps(fixtures), encoding="utf-8")
        with self.assertRaisesRegex(ConformanceError, "result tuple differs"):
            validate_catalog(root)

        root = self.catalog_copy()
        path = root / "conformance" / "v1" / "fixtures.json"
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        runtime = next(
            item
            for item in fixtures["fixtures"]
            if item["fixture_id"] == "ASP-F-RM-072"
        )
        runtime["document"]["mcp"]["resource_update_state"] = "updated"
        runtime["document"]["mcp"]["current_binding_view_id"] = "binding_view_b"
        path.write_text(json.dumps(fixtures), encoding="utf-8")
        with self.assertRaisesRegex(
            ConformanceError, "neither current nor an exact retained completed replay"
        ):
            validate_catalog(root)

        read_document = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-072"]["document"]
        )
        read_mcp = read_document["mcp"]
        read_mcp["tool_name"] = (
            "asp.action."
            "23366c437a0ce5ea66f4e84510f454c3ba3c7928d9ce9bfedcea86136355048b"
        )
        read_mcp["action_id"] = "action.read"
        read_mcp["mapped_action_id"] = "action.read"
        read_mcp["action_mode"] = "read"
        read_mcp["mapped_action_mode"] = "read"
        read_mcp["idempotency_key"] = "none"
        read_mcp["bound_idempotency_key"] = "none"
        read_mcp["idempotency_requirement"] = "optional"
        read_mcp["result_action_id"] = "action.read"
        read_mcp["result_idempotency_key"] = "none"
        read_mcp["receipt_channel"] = "not_applicable"
        read_mcp["receipt_requirement"] = "not_required"
        read_mcp["receipt_resource_authentication"] = "not_applicable"
        read_mcp["receipt_integrity"] = "not_applicable"
        read_mcp["receipt_persistence"] = "not_applicable"
        read_mcp["receipt_rematerialization"] = "not_applicable"
        read_document["mcp_authority"]["selected_action_id"] = "action.read"
        read_document["mcp_authority"]["selected_action_mode"] = "read"
        read_document["mcp_authority"]["idempotency_key"] = "none"
        validate_mcp_binding_projection(
            read_mcp,
            read_document,
            "mediate_mcp_action",
        )

    def test_asp_over_mcp_security_edges_are_executable(self) -> None:
        publisher = copy.deepcopy(
            self.catalog.fixtures["ASP-F-SP-010"]["document"]
        )
        for field, value in (
            ("surface_hash", "surface_hash_b"),
            ("surface_version", "surface_v2"),
        ):
            with self.subTest(publisher_binding=field):
                substituted_publisher = copy.deepcopy(publisher)
                substituted_publisher["mcp"][field] = value
                with self.assertRaisesRegex(
                    ConformanceError, "manifest authority|authoritative surface"
                ):
                    validate_mcp_binding_projection(
                        substituted_publisher["mcp"],
                        substituted_publisher,
                        "publish_mcp_surface",
                    )
        for surface_field, value in (
            ("status", "stale"),
            ("references", "incomplete"),
        ):
            with self.subTest(publisher_surface=surface_field):
                invalid_publisher = copy.deepcopy(publisher)
                invalid_publisher["surface"][surface_field] = value
                with self.assertRaisesRegex(
                    ConformanceError, "authoritative surface"
                ):
                    validate_mcp_binding_projection(
                        invalid_publisher["mcp"],
                        invalid_publisher,
                        "publish_mcp_surface",
                    )

        adapter = copy.deepcopy(
            self.catalog.fixtures["ASP-F-AA-012"]["document"]
        )
        for operation, source in (
            ("publish_mcp_surface", publisher),
            ("adapt_mcp_action", adapter),
        ):
            for label, mutate in (
                (
                    "action_set",
                    lambda document: document["mcp"]["manifest_action_ids"].append(
                        "evil.action"
                    ),
                ),
                (
                    "projection",
                    lambda document: document["mcp"].__setitem__(
                        "authorized_projection_state", "exact"
                    ),
                ),
                (
                    "grant_location",
                    lambda document: document["mcp_authority"].__setitem__(
                        "issued_locations", ["https://attacker.example/mcp"]
                    ),
                ),
            ):
                with self.subTest(operation=operation, authority_binding=label):
                    invalid = copy.deepcopy(source)
                    mutate(invalid)
                    with self.assertRaisesRegex(
                        ConformanceError,
                        "manifest authority|Grant locations",
                    ):
                        validate_mcp_binding_projection(
                            invalid["mcp"], invalid, operation
                        )

        grant_issuer = copy.deepcopy(
            self.catalog.fixtures["ASP-F-GI-008"]["document"]
        )
        grant_issuer["mcp_authority"]["manifest_credential_audience"] = "not-a-uri"
        with self.assertRaisesRegex(ConformanceError, "absolute HTTPS"):
            validate_mcp_binding_projection(
                grant_issuer["mcp"], grant_issuer, "issue_mcp_grant"
            )

        baseline = copy.deepcopy(
            self.catalog.fixtures["ASP-F-RM-072"]["document"]
        )
        first_page = {"jsonrpc": "2.0", "id": "", "method": "tools/list"}
        validate_mcp_wire_semantics(
            first_page,
            tools_list_first_page=True,
            prior_request_ids=["previous"],
        )
        with self.assertRaisesRegex(ConformanceError, "must omit params"):
            validate_mcp_wire_semantics(
                {**first_page, "params": {}},
                tools_list_first_page=True,
            )
        with self.assertRaisesRegex(ConformanceError, "already used"):
            validate_mcp_wire_semantics(
                first_page,
                tools_list_first_page=True,
                prior_request_ids=[""],
            )
        with self.assertRaisesRegex(ConformanceError, "already consumed"):
            validate_mcp_wire_semantics(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {"cursor": "cursor-1"},
                },
                expected_cursor="cursor-1",
                prior_cursors=["cursor-1"],
            )
        cursor_page = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"tools": [], "nextCursor": "cursor-1", "_meta": {}},
        }
        with self.assertRaisesRegex(ConformanceError, "repeats a cursor lineage"):
            validate_mcp_wire_semantics(cursor_page, prior_cursors=["cursor-1"])
        fresh_empty_page = copy.deepcopy(cursor_page)
        fresh_empty_page["result"]["nextCursor"] = "cursor-2"
        with self.assertRaisesRegex(ConformanceError, "empty page"):
            validate_mcp_wire_semantics(fresh_empty_page, prior_cursors=["cursor-1"])
        for lookup_outcome in (
            "unknown_404_no_mutation",
            "auth_mismatch_404_no_mutation",
        ):
            recovered = copy.deepcopy(baseline)
            recovered_mcp = recovered["mcp"]
            recovered_mcp["transport_lifecycle_event"] = "session_lookup_404_recovered"
            recovered_mcp["fresh_initialize_authority"] = "transport_only"
            recovered_mcp["session_lookup_outcome"] = lookup_outcome
            with self.assertRaisesRegex(ConformanceError, "transport lifecycle"):
                validate_mcp_binding_projection(
                    recovered_mcp, recovered, "mediate_mcp_action"
                )
            rediscovery = copy.deepcopy(publisher)
            rediscovery_mcp = rediscovery["mcp"]
            rediscovery_mcp["transport_lifecycle_event"] = (
                "session_lookup_404_recovered"
            )
            rediscovery_mcp["fresh_initialize_authority"] = "transport_only"
            rediscovery_mcp["session_lookup_outcome"] = lookup_outcome
            validate_mcp_binding_projection(
                rediscovery_mcp, rediscovery, "publish_mcp_surface"
            )

        for delimiter in ("?", "#"):
            with self.subTest(endpoint_delimiter=delimiter):
                invalid_endpoint = copy.deepcopy(baseline)
                endpoint = "https://app.example/mcp" + delimiter
                for owner, field in (
                    (invalid_endpoint["mcp"], "binding_endpoint"),
                    (invalid_endpoint["mcp"], "canonical_mcp_server_uri"),
                    (invalid_endpoint["mcp"], "credential_proof_target_uri"),
                    (invalid_endpoint["mcp_authority"], "manifest_binding_endpoint"),
                    (invalid_endpoint["mcp_authority"], "credential_proof_target_uri"),
                ):
                    owner[field] = endpoint
                invalid_endpoint["mcp_authority"]["requested_locations"] = [endpoint]
                invalid_endpoint["mcp_authority"]["issued_locations"] = [endpoint]
                with self.assertRaisesRegex(
                    ConformanceError, "fragmentless HTTPS"
                ):
                    validate_mcp_binding_projection(
                        invalid_endpoint["mcp"],
                        invalid_endpoint,
                        "mediate_mcp_action",
                    )

        invalid_audience = copy.deepcopy(baseline)
        invalid_audience["mcp_authority"]["manifest_credential_audience"] = "not-a-uri"
        invalid_audience["mcp"]["token_audience"] = "not-a-uri"
        invalid_audience["mcp"]["bound_token_audience"] = "not-a-uri"
        with self.assertRaisesRegex(ConformanceError, "absolute HTTPS"):
            validate_mcp_binding_projection(
                invalid_audience["mcp"], invalid_audience, "mediate_mcp_action"
            )

        replay = copy.deepcopy(baseline)
        replay_mcp = replay["mcp"]
        replay_mcp["binding_view_use"] = "current_completed_replay"
        replay_mcp["completed_record_state"] = "exact_authenticated"
        replay_mcp["replay_materialization"] = "exact_persisted_result_and_receipt"
        replay_mcp["retained_snapshot_state"] = "persisted_across_restart"
        replay_mcp["replay_disclosure_authorization"] = "allowed"
        validate_mcp_binding_projection(
            replay_mcp, replay, "mediate_mcp_action"
        )

        retained_replay = copy.deepcopy(replay)
        retained_mcp = retained_replay["mcp"]
        retained_mcp["binding_view_use"] = "retained_completed_replay"
        retained_mcp["resource_update_state"] = "updated"
        retained_mcp["current_binding_view_id"] = "binding_view_b"
        retained_mcp["tools_changed_state"] = "changed_after_snapshot"
        retained_mcp["schema_snapshot_state"] = "retained"
        retained_mcp["rotation_cause"] = "manifest"
        validate_mcp_binding_projection(
            retained_mcp, retained_replay, "mediate_mcp_action"
        )
        substituted_retained = copy.deepcopy(retained_replay)
        substituted_retained_mcp = substituted_retained["mcp"]
        substituted_retained_mcp["surface_version"] = "surface_v0"
        substituted_retained_mcp["result_surface_version"] = "surface_v0"
        for field in ("surface_hash", "bound_surface_hash", "result_surface_hash"):
            substituted_retained_mcp[field] = "surface_hash_b"
        with self.assertRaisesRegex(ConformanceError, "manifest authority"):
            validate_mcp_binding_projection(
                substituted_retained_mcp,
                substituted_retained,
                "mediate_mcp_action",
            )

        admission_mutations = (
            ("grant", "status", "revoked"),
            ("grant", "revocation_state", "revoked"),
            ("grant", "claimed_issuer", "issuer_b"),
            ("grant", "passport_status", "unavailable"),
            ("grant", "companion_closure", "unclosed"),
            ("execution", "input_hash", "input_hash_b"),
            ("execution", "input_schema_hash", "input_schema_hash_b"),
            ("execution", "normalization", "non_fixed_point"),
            ("execution", "execution_hash", "execution_hash_b"),
            ("execution", "approval_hash", "approval_hash_b"),
            ("execution", "policy", "deny"),
            ("execution", "runtime_identity", "runtime_identity_b"),
            ("execution", "sender_credential_audience", "credential_audience_b"),
            ("execution", "proof_session_binding", "session_binding_b"),
            ("execution", "attestation", "unavailable"),
        )
        for fixture_id, operation in (
            ("ASP-F-RM-072", "mediate_mcp_action"),
            ("ASP-F-AE-032", "execute_mcp_action"),
        ):
            for section, field, value in admission_mutations:
                with self.subTest(
                    fixture_id=fixture_id, admission_field=f"{section}.{field}"
                ):
                    invalid_admission = copy.deepcopy(
                        self.catalog.fixtures[fixture_id]["document"]
                    )
                    invalid_admission[section][field] = value
                    with self.assertRaisesRegex(
                        ConformanceError,
                        "ordinary ASP authority|authoritative ASP state",
                    ):
                        validate_mcp_binding_projection(
                            invalid_admission["mcp"],
                            invalid_admission,
                            operation,
                        )

        substituted = copy.deepcopy(baseline)
        substituted_mcp = substituted["mcp"]
        substituted_mcp["grant_id"] = "evil"
        substituted_mcp["bound_grant_id"] = "evil"
        substituted_mcp["result_grant_id"] = "evil"
        with self.assertRaisesRegex(ConformanceError, "independent authority"):
            validate_mcp_binding_projection(
                substituted_mcp, substituted, "mediate_mcp_action"
            )

        for field, invalid_value in (
            ("result_text_consistency", "divergent"),
            ("result_grant_hash", "grant_hash_b"),
            ("result_idempotency_key", "idempotency_key_b"),
            ("result_output_schema", "invalid"),
        ):
            with self.subTest(result_invariant=field):
                divergent = copy.deepcopy(baseline)
                divergent["mcp"][field] = invalid_value
                with self.assertRaises(ConformanceError):
                    validate_mcp_binding_projection(
                        divergent["mcp"], divergent, "mediate_mcp_action"
                    )

        valid_token = base64.urlsafe_b64encode(bytes(16)).rstrip(b"=").decode("ascii")
        token_hash = digest("\x00" * 16)
        # digest() hashes UTF-8 text; the token hash is over decoded token bytes.
        token_hash = "sha-256:" + base64.urlsafe_b64encode(
            hashlib.sha256(bytes(16)).digest()
        ).rstrip(b"=").decode("ascii")
        _validate_mcp_execution_token_pair(
            valid_token, token_hash, label="test.preview"
        )
        with self.assertRaisesRegex(ConformanceError, "canonical base64url"):
            _validate_mcp_execution_token_pair(
                valid_token[:-1] + "B", token_hash, label="test.preview"
            )
        short_token = base64.urlsafe_b64encode(b"x").rstrip(b"=").decode("ascii")
        short_token_hash = "sha-256:" + base64.urlsafe_b64encode(
            hashlib.sha256(b"x").digest()
        ).rstrip(b"=").decode("ascii")
        with self.assertRaisesRegex(ConformanceError, "fewer than 16 decoded octets"):
            _validate_mcp_execution_token_pair(
                short_token, short_token_hash, label="test.preview"
            )

        reserved_name_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {"$ref": {"type": "string"}},
            "required": ["$ref"],
            "additionalProperties": False,
        }
        _validate_mcp_schema_instance(
            {"$ref": "ordinary-domain-data"},
            reserved_name_schema,
            "reserved property",
            retrieval_uri="https://app.example/schemas/reserved.json",
        )
        nested_base_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": {
                "user": {
                    "$id": "defs/user",
                    "type": "object",
                    "properties": {"name": {"$ref": "inner"}},
                    "required": ["name"],
                },
                "inner": {"$id": "defs/inner", "type": "string"},
            },
            "$ref": "defs/user",
        }
        _validate_mcp_schema_instance(
            {"name": "Ada"},
            nested_base_schema,
            "nested retrieval base",
            retrieval_uri="https://app.example/schemas/root.json",
        )
        with self.assertRaisesRegex(ConformanceError, "self-contained"):
            _validate_mcp_schema_instance(
                {},
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$ref": "external.json",
                },
                "external retrieval",
                retrieval_uri="https://app.example/schemas/root.json",
            )

        self.assertFalse(
            _mcp_contains_forbidden_credential({"authorization": "none"})
        )
        secret = "synthetic-grant-credential-value"
        self.assertTrue(
            _mcp_contains_forbidden_credential(
                {"value": secret},
                forbidden_credential_values=frozenset({secret}),
            )
        )
        with self.assertRaisesRegex(ConformanceError, "credential material"):
            _validate_mcp_credential_free_uri(
                f"https://app.example/resource?x={secret}",
                label="neutral query",
                forbidden_credential_values=frozenset({secret}),
            )
        with self.assertRaisesRegex(ConformanceError, "credential material"):
            _validate_mcp_credential_free_uri(
                "asp://receipt/r#synthetic-grant-credential%252Dvalue",
                label="encoded fragment",
                forbidden_credential_values=frozenset({secret}),
            )

    def test_asp_over_mcp_dry_run_preview_is_bound_and_fresh(self) -> None:
        surface_hash = digest("surface")
        grant_hash = digest("grant")
        execution = {"mode": "dry_run", "execution_id": "exec-preview"}
        execution_hash = _canonical_object_hash(
            "https://github.com/0al-spec/agent-surface/hash/action-execution/v1",
            execution,
        )
        raw_token = bytes(range(16))
        execution_token = base64.urlsafe_b64encode(raw_token).rstrip(b"=").decode("ascii")
        execution_token_hash = "sha-256:" + base64.urlsafe_b64encode(
            hashlib.sha256(raw_token).digest()
        ).rstrip(b"=").decode("ascii")
        preview = {
            "preview_id": "preview-1",
            "commit_action_id": "mail.send",
            "execution_token": execution_token,
            "execution_token_hash": execution_token_hash,
            "expires_at": "2026-07-22T12:05:00Z",
        }
        preconditions = {"mailbox_revision": "r1"}
        expected_effects = [{"effect_id": "mail-send", "operation": "send"}]
        payload = {
            "session_id": "s1",
            "session_generation": 1,
            "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
            "span_id": "00f067aa0ba902b7",
            "grant_id": "g1",
            "grant_hash": grant_hash,
            "surface_hash": surface_hash,
            "action_id": "mail.preview",
            "execution": execution,
            "execution_hash": execution_hash,
            "result": "preview",
            "preview": preview,
            "preconditions": preconditions,
            "preconditions_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/action-preconditions/v1",
                preconditions,
            ),
            "expected_effects": expected_effects,
            "expected_effects_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/expected-effects/v1",
                expected_effects,
            ),
            "output": {"ready": True},
        }
        envelope = {
            "profile": "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1",
            "mcp_protocol_version": "2025-11-25",
            "binding_view_id": "view-1",
            "message": {"type": "action.result", "payload": payload},
        }
        message = {
            "jsonrpc": "2.0",
            "id": 9,
            "result": {
                "content": [{"type": "text", "text": json.dumps(envelope)}],
                "structuredContent": envelope,
                "isError": False,
            },
        }
        request_payload = {
            key: payload[key]
            for key in (
                "session_id", "session_generation", "trace_id", "grant_id",
                "grant_hash", "surface_hash", "action_id", "execution",
                "execution_hash",
            )
        }
        context = {
            "expected_surface_hash": surface_hash,
            "expected_request_payload": request_payload,
            "action_mode": "dry_run",
            "expected_result": "preview",
            "receipt_required": False,
            "expected_preview": preview,
            "expected_preview_preconditions": preconditions,
            "expected_preview_effects": expected_effects,
            "evaluation_time": "2026-07-22T12:00:00Z",
        }
        validate_mcp_wire_semantics(message, **context)
        expired = copy.deepcopy(message)
        expired_preview = expired["result"]["structuredContent"]["message"]["payload"]["preview"]
        expired_preview["expires_at"] = "2026-07-22T11:59:59Z"
        expired["result"]["content"][0]["text"] = json.dumps(
            expired["result"]["structuredContent"]
        )
        expired_context = dict(context)
        expired_context["expected_preview"] = expired_preview
        with self.assertRaisesRegex(ConformanceError, "expired"):
            validate_mcp_wire_semantics(expired, **expired_context)

    def test_asp_over_mcp_projection_and_receipt_resources_are_exact(self) -> None:
        projection = {
            "profile": "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1",
            "projection_id": "projection-1",
            "base_surface_version": "1",
            "base_surface_hash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "expires_at": "2026-07-22T13:00:00Z",
        }
        cases = {
            case["case_id"]: case
            for case in self.catalog.schema_case_catalog["cases"]
        }
        manifest_case = cases["ASP-SC-MB-007"]
        manifest_message = loads_human_json(
            manifest_case["instance_json"], source="MCP manifest resource"
        )
        manifest_context = copy.deepcopy(manifest_case["context"])
        validate_mcp_wire_semantics(manifest_message, **manifest_context)
        substituted_manifest = copy.deepcopy(manifest_message)
        substituted_body = loads_human_json(
            substituted_manifest["result"]["contents"][0]["text"],
            source="substituted MCP manifest",
        )
        substituted_body["surface_hash"] = digest("substituted-surface")
        substituted_manifest["result"]["contents"][0]["text"] = json.dumps(
            substituted_body
        )
        substituted_context = {
            **manifest_context,
            "expected_resource": substituted_body,
        }
        with self.assertRaisesRegex(ConformanceError, "surface_hash differs"):
            validate_mcp_wire_semantics(substituted_manifest, **substituted_context)

        http_case = cases["ASP-SC-MB-019"]
        http_message = loads_human_json(
            http_case["instance_json"], source="MCP HTTP evidence"
        )
        http_context = copy.deepcopy(http_case["context"])
        validate_mcp_wire_semantics(http_message, **http_context)
        mtls_message = copy.deepcopy(http_message)
        mtls_authorization = mtls_message["authorization"]
        mtls_authorization["asp_credential_profile"] = "mtls"
        mtls_authorization["authorization_scheme"] = "mTLS"
        for request_authorization in mtls_authorization["request_authorizations"]:
            request_authorization["binding_kind"] = "mtls_channel"
        validate_mcp_wire_semantics(mtls_message, **http_context)
        wrong_listener_method = copy.deepcopy(http_message)
        next(
            item
            for item in wrong_listener_method["authorization"]["request_authorizations"]
            if item["request_class"] == "listener"
        )["method"] = "POST"
        with self.assertRaisesRegex(ConformanceError, "every exact request target"):
            validate_mcp_wire_semantics(wrong_listener_method, **http_context)
        empty_query_endpoint = copy.deepcopy(http_message)
        empty_query_endpoint["endpoint"] += "?"
        for request_authorization in empty_query_endpoint["authorization"][
            "request_authorizations"
        ]:
            request_authorization["target_uri"] += "?"
        empty_query_context = {
            **http_context,
            "expected_endpoint": empty_query_endpoint["endpoint"],
            "expected_proof_target_uri": empty_query_endpoint["endpoint"],
        }
        with self.assertRaisesRegex(ConformanceError, "omit fragments"):
            validate_mcp_wire_semantics(empty_query_endpoint, **empty_query_context)
        empty_fragment_endpoint = copy.deepcopy(http_message)
        empty_fragment_endpoint["endpoint"] += "#"
        for request_authorization in empty_fragment_endpoint["authorization"][
            "request_authorizations"
        ]:
            request_authorization["target_uri"] += "#"
        empty_fragment_context = {
            **http_context,
            "expected_endpoint": empty_fragment_endpoint["endpoint"],
            "expected_proof_target_uri": empty_fragment_endpoint["endpoint"],
        }
        with self.assertRaisesRegex(ConformanceError, "omit fragments"):
            validate_mcp_wire_semantics(
                empty_fragment_endpoint, **empty_fragment_context
            )

        list_case = cases["ASP-SC-MB-009"]
        list_message = loads_human_json(
            list_case["instance_json"], source="projected tools/list"
        )
        list_context = copy.deepcopy(list_case["context"])
        page_binding = list_message["result"]["_meta"][
            "io.github.zeroal-spec/asp-over-mcp-v1"
        ]
        tool_binding = list_message["result"]["tools"][0]["_meta"][
            "io.github.zeroal-spec/asp-over-mcp-v1"
        ]
        page_binding["authorized_projection"] = projection
        tool_binding["authorized_projection"] = projection
        list_context["authorized_projection_expected"] = True
        list_context["expected_authorized_projection"] = projection
        list_context["expected_binding_record"]["authorized_projection"] = projection
        list_context["expected_tool_records"][0]["binding"][
            "authorized_projection"
        ] = projection
        validate_mcp_wire_semantics(list_message, **list_context)
        substituted_list = copy.deepcopy(list_message)
        substituted_list["result"]["tools"][0]["_meta"][
            "io.github.zeroal-spec/asp-over-mcp-v1"
        ]["authorized_projection"]["projection_id"] = "projection-2"
        with self.assertRaisesRegex(ConformanceError, "manifest-selected binding record"):
            validate_mcp_wire_semantics(substituted_list, **list_context)

        call_case = cases["ASP-SC-MB-010"]
        call_message = loads_human_json(
            call_case["instance_json"], source="projected tools/call"
        )
        call_context = copy.deepcopy(call_case["context"])
        call_binding = call_message["params"]["_meta"][
            "io.github.zeroal-spec/asp-over-mcp-v1"
        ]
        call_binding["authorized_projection"] = projection
        call_context["authorized_projection_expected"] = True
        call_context["expected_authorized_projection"] = projection
        call_context["expected_binding_record"]["authorized_projection"] = projection
        validate_mcp_wire_semantics(call_message, **call_context)
        missing_projection = copy.deepcopy(call_message)
        del missing_projection["params"]["_meta"][
            "io.github.zeroal-spec/asp-over-mcp-v1"
        ]["authorized_projection"]
        with self.assertRaisesRegex(ConformanceError, "presence differs"):
            validate_mcp_wire_semantics(missing_projection, **call_context)

        receipt_effects = [{"effect_id": "mail-send", "operation": "send"}]
        receipt_execution = {"mode": "commit", "execution_id": "exec-1"}
        receipt_policy = {
            "type": "policy.decision",
            "decision_id": "decision-1",
            "enforcer": {"type": "application", "id": "mail.example"},
            "outcome": "allow",
            "policy": {"id": "mail-action-policy", "version": "1"},
            "reason_code": "policy_allowed",
            "matched_rules": ["grant.active", "action.mail.send"],
            "safe_to_show": "The application accepted the authorized action.",
            "evaluated_at": "2026-07-22T12:00:00Z",
        }
        receipt_policy["policy_decision_hash"] = _canonical_object_hash(
            "https://github.com/0al-spec/agent-surface/hash/policy-decision/v1",
            receipt_policy,
        )
        receipt_body = {
            "receipt_id": "receipt-1",
            "receipt_type": "app",
            "grant_id": "g1",
            "grant_hash": digest("grant"),
            "session_id": "s1",
            "session_generation": 1,
            "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
            "span_id": "00f067aa0ba902b7",
            "action_id": "mail.send",
            "app_id": "mail.example",
            "surface_version": "1",
            "surface_hash": digest("surface"),
            "runtime": {"runtime_id": "runtime-1"},
            "actor_agent": {
                "agent_id": "agent-1",
                "identity_evidence_hash": digest("identity-evidence"),
            },
            "subject": {"user": "user-1"},
            "idempotency_key": "idem-1",
            "input_hash": digest("input"),
            "execution": receipt_execution,
            "execution_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/action-execution/v1",
                receipt_execution,
            ),
            "output_hash": digest("output"),
            "actual_effects": receipt_effects,
            "actual_effects_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/actual-effects/v1",
                receipt_effects,
            ),
            "effect_outcome": "applied",
            "policy_decision_hash": receipt_policy["policy_decision_hash"],
            "policy_decision": receipt_policy,
            "timestamp": "2026-07-22T12:00:00Z",
            "result": "success",
        }
        receipt_hash = _canonical_object_hash(
            "https://github.com/0al-spec/agent-surface/hash/receipt/v1",
            receipt_body,
        )
        receipt = {**receipt_body, "receipt_hash": receipt_hash}
        receipt_uri = "asp://receipt/receipt-1"

        def authenticated_receipt_record(
            value: dict, *, receipt_type: str = "app", approval_role: str | None = None
        ) -> dict:
            binding_members = (
                "session_id", "session_generation", "trace_id", "grant_id",
                "grant_hash", "app_id", "surface_hash", "surface_version",
                "action_id", "idempotency_key", "input_hash", "runtime",
                "actor_agent", "subject", "execution", "execution_hash",
            )
            return {
                "uri": receipt_uri,
                "receipt": value,
                "expected": {
                    "receipt_id": value["receipt_id"],
                    "receipt_hash": value["receipt_hash"],
                    "receipt_type": receipt_type,
                    "approval_role": approval_role,
                    "binding": {
                        member: value[member]
                        for member in binding_members
                        if member in value
                    },
                    "signature_required": False,
                },
            }

        def receipt_semantics(value: dict) -> dict:
            return {
                member: value.get(member)
                for member in (
                    "result", "error", "output_hash", "actual_effects",
                    "actual_effects_hash", "effect_outcome", "resource",
                )
            }
        receipt_message = {
            "jsonrpc": "2.0",
            "id": 11,
            "result": {
                "contents": [
                    {
                        "uri": receipt_uri,
                        "mimeType": "application/json",
                        "text": json.dumps(receipt),
                    }
                ]
            },
        }
        receipt_context = {
            "requested_resource_uri": receipt_uri,
            "resource_kind": "receipt",
            "expected_resource": receipt,
            "resource_hash_domain": "https://github.com/0al-spec/agent-surface/hash/receipt/v1",
            "expected_resource_hash": receipt_hash,
            "expected_receipt_type": "app",
            "expected_receipt_semantics": receipt_semantics(receipt),
            "expected_authenticated_receipt_resources": [
                authenticated_receipt_record(receipt)
            ],
        }
        validate_mcp_wire_semantics(receipt_message, **receipt_context)
        malformed_record_context = {
            **receipt_context,
            "expected_authenticated_receipt_resources": [None],
        }
        with self.assertRaisesRegex(
            ConformanceError, "exact authenticated resource record"
        ):
            validate_mcp_wire_semantics(
                receipt_message, **malformed_record_context
            )
        invalid_role = copy.deepcopy(receipt_message)
        invalid_receipt_body = {**receipt, "receipt_type": "runtime"}
        invalid_receipt_body.pop("receipt_hash")
        invalid_receipt = {
            **invalid_receipt_body,
            "receipt_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/receipt/v1",
                invalid_receipt_body,
            ),
        }
        invalid_role["result"]["contents"][0]["text"] = json.dumps(invalid_receipt)
        invalid_context = {
            **receipt_context,
            "expected_resource": invalid_receipt,
            "expected_resource_hash": invalid_receipt["receipt_hash"],
        }
        with self.assertRaisesRegex(ConformanceError, "receipt type and identity"):
            validate_mcp_wire_semantics(invalid_role, **invalid_context)
        tampered_hash = copy.deepcopy(receipt_message)
        tampered_receipt = {**receipt, "receipt_hash": digest("tampered-receipt")}
        tampered_hash["result"]["contents"][0]["text"] = json.dumps(tampered_receipt)
        tampered_context = {**receipt_context, "expected_resource": tampered_receipt}
        with self.assertRaisesRegex(ConformanceError, "receipt type and identity"):
            validate_mcp_wire_semantics(tampered_hash, **tampered_context)
        incomplete = copy.deepcopy(receipt_message)
        incomplete_receipt = copy.deepcopy(receipt)
        del incomplete_receipt["grant_id"]
        incomplete["result"]["contents"][0]["text"] = json.dumps(incomplete_receipt)
        incomplete_context = {**receipt_context, "expected_resource": incomplete_receipt}
        with self.assertRaisesRegex(ConformanceError, "receipt type and identity"):
            validate_mcp_wire_semantics(incomplete, **incomplete_context)

        partial_policy_body = copy.deepcopy(receipt_body)
        partial_policy_body["policy_decision"].pop("matched_rules")
        partial_policy_body["policy_decision"].pop("policy_decision_hash")
        partial_policy_body["policy_decision"]["policy_decision_hash"] = (
            _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/policy-decision/v1",
                partial_policy_body["policy_decision"],
            )
        )
        partial_policy_body["policy_decision_hash"] = partial_policy_body[
            "policy_decision"
        ]["policy_decision_hash"]
        partial_policy_receipt = {
            **partial_policy_body,
            "receipt_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/receipt/v1",
                partial_policy_body,
            ),
        }
        partial_policy_message = copy.deepcopy(receipt_message)
        partial_policy_message["result"]["contents"][0]["text"] = json.dumps(
            partial_policy_receipt
        )
        partial_policy_context = {
            **receipt_context,
            "expected_resource": partial_policy_receipt,
            "expected_resource_hash": partial_policy_receipt["receipt_hash"],
            "expected_receipt_semantics": receipt_semantics(
                partial_policy_receipt
            ),
            "expected_authenticated_receipt_resources": [
                authenticated_receipt_record(partial_policy_receipt)
            ],
        }
        with self.assertRaisesRegex(ConformanceError, "oracle rejected"):
            validate_mcp_wire_semantics(
                partial_policy_message, **partial_policy_context
            )

        invalid_outcome_body = copy.deepcopy(receipt_body)
        invalid_outcome_body["policy_decision"]["outcome"] = "explode"
        invalid_outcome_body["policy_decision"]["reason_code"] = (
            "https://example.invalid/policy-reason/explode"
        )
        invalid_outcome_body["policy_decision"].pop("policy_decision_hash")
        invalid_outcome_body["policy_decision"]["policy_decision_hash"] = (
            _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/policy-decision/v1",
                invalid_outcome_body["policy_decision"],
            )
        )
        invalid_outcome_body["policy_decision_hash"] = invalid_outcome_body[
            "policy_decision"
        ]["policy_decision_hash"]
        invalid_outcome_receipt = {
            **invalid_outcome_body,
            "receipt_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/receipt/v1",
                invalid_outcome_body,
            ),
        }
        invalid_outcome_message = copy.deepcopy(receipt_message)
        invalid_outcome_message["result"]["contents"][0]["text"] = json.dumps(
            invalid_outcome_receipt
        )
        invalid_outcome_context = {
            **receipt_context,
            "expected_resource": invalid_outcome_receipt,
            "expected_resource_hash": invalid_outcome_receipt["receipt_hash"],
            "expected_receipt_semantics": receipt_semantics(
                invalid_outcome_receipt
            ),
            "expected_authenticated_receipt_resources": [
                authenticated_receipt_record(invalid_outcome_receipt)
            ],
        }
        with self.assertRaisesRegex(ConformanceError, "oracle rejected"):
            validate_mcp_wire_semantics(
                invalid_outcome_message, **invalid_outcome_context
            )

        incomplete_success_body = copy.deepcopy(receipt_body)
        for member in (
            "output_hash", "actual_effects", "actual_effects_hash",
            "effect_outcome", "resource",
        ):
            incomplete_success_body.pop(member, None)
        incomplete_success_receipt = {
            **incomplete_success_body,
            "receipt_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/receipt/v1",
                incomplete_success_body,
            ),
        }
        incomplete_success_message = copy.deepcopy(receipt_message)
        incomplete_success_message["result"]["contents"][0]["text"] = (
            json.dumps(incomplete_success_receipt)
        )
        incomplete_success_context = {
            **receipt_context,
            "expected_resource": incomplete_success_receipt,
            "expected_resource_hash": incomplete_success_receipt["receipt_hash"],
            "expected_authenticated_receipt_resources": [
                authenticated_receipt_record(incomplete_success_receipt)
            ],
        }
        with self.assertRaisesRegex(ConformanceError, "authoritative semantics"):
            validate_mcp_wire_semantics(
                incomplete_success_message, **incomplete_success_context
            )

        no_effect_body = copy.deepcopy(receipt_body)
        no_effect_body["action_id"] = "mail.read"
        no_effect_body["result"] = "denied"
        for member in (
            "execution", "execution_hash", "output_hash", "actual_effects",
            "actual_effects_hash", "effect_outcome", "resource",
        ):
            no_effect_body.pop(member, None)
        denied_policy = {
            **receipt_policy,
            "decision_id": "decision-denied-1",
            "outcome": "deny",
            "reason_code": "app_policy_denied",
            "matched_rules": ["mail.read.denied"],
            "safe_to_show": "The application denied the read action.",
        }
        denied_policy.pop("policy_decision_hash")
        denied_policy["policy_decision_hash"] = _canonical_object_hash(
            "https://github.com/0al-spec/agent-surface/hash/policy-decision/v1",
            denied_policy,
        )
        no_effect_body["policy_decision"] = denied_policy
        no_effect_body["policy_decision_hash"] = denied_policy[
            "policy_decision_hash"
        ]
        no_effect_receipt = {
            **no_effect_body,
            "receipt_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/receipt/v1",
                no_effect_body,
            ),
        }
        no_effect_message = copy.deepcopy(receipt_message)
        no_effect_message["result"]["contents"][0]["text"] = json.dumps(
            no_effect_receipt
        )
        no_effect_context = {
            **receipt_context,
            "expected_resource": no_effect_receipt,
            "expected_resource_hash": no_effect_receipt["receipt_hash"],
            "expected_receipt_semantics": receipt_semantics(no_effect_receipt),
            "expected_authenticated_receipt_resources": [
                authenticated_receipt_record(no_effect_receipt)
            ],
        }
        validate_mcp_wire_semantics(no_effect_message, **no_effect_context)

        raw_token_body = copy.deepcopy(receipt_body)
        raw_token = base64.urlsafe_b64encode(bytes(range(16))).rstrip(b"=").decode("ascii")
        raw_token_body["execution"]["execution_token"] = raw_token
        raw_token_body["execution"]["execution_token_hash"] = (
            "sha-256:"
            + base64.urlsafe_b64encode(hashlib.sha256(bytes(range(16))).digest())
            .rstrip(b"=")
            .decode("ascii")
        )
        raw_token_receipt = {
            **raw_token_body,
            "receipt_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/receipt/v1",
                raw_token_body,
            ),
        }
        raw_token_message = copy.deepcopy(receipt_message)
        raw_token_message["result"]["contents"][0]["text"] = json.dumps(
            raw_token_receipt
        )
        raw_token_context = {
            **receipt_context,
            "expected_resource": raw_token_receipt,
            "expected_resource_hash": raw_token_receipt["receipt_hash"],
        }
        with self.assertRaisesRegex(ConformanceError, "leaks execution_token"):
            validate_mcp_wire_semantics(raw_token_message, **raw_token_context)

        approval_without_result_body = copy.deepcopy(receipt_body)
        approval_without_result_body["receipt_type"] = "approval"
        approval_without_result_body["approval"] = {
            "approval_id": "approval-1",
            "role": "runtime",
            "decided_by": "user",
            "valid_until": "2026-07-22T12:05:00Z",
        }
        approval_without_result_body.pop("result")
        for member in (
            "parent_receipt_hash", "output_hash", "actual_effects",
            "actual_effects_hash", "effect_outcome",
        ):
            approval_without_result_body.pop(member, None)
        approval_without_result = {
            **approval_without_result_body,
            "receipt_hash": _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/receipt/v1",
                approval_without_result_body,
            ),
        }
        approval_message = copy.deepcopy(receipt_message)
        approval_message["result"]["contents"][0]["text"] = json.dumps(
            approval_without_result
        )
        approval_context = {
            **receipt_context,
            "expected_resource": approval_without_result,
            "expected_resource_hash": approval_without_result["receipt_hash"],
            "expected_receipt_type": "approval",
        }
        with self.assertRaisesRegex(ConformanceError, "receipt type and identity"):
            validate_mcp_wire_semantics(approval_message, **approval_context)

    def test_asp_over_mcp_approval_receipt_maps_are_exact_and_resolvable(self) -> None:
        cases = {
            case["case_id"]: case
            for case in self.catalog.schema_case_catalog["cases"]
        }
        base_case = cases["ASP-SC-MB-011"]
        base_message = loads_human_json(
            base_case["instance_json"], source="MCP approval-map result"
        )
        base_context = copy.deepcopy(base_case["context"])
        base_app_receipt = base_context[
            "expected_authenticated_receipt_resources"
        ][0]["receipt"]
        receipt_domain = (
            "https://github.com/0al-spec/agent-surface/hash/receipt/v1"
        )

        def approval_receipt(role: str) -> tuple[str, dict]:
            enforcer = (
                {"type": "runtime", "id": "runtime-1"}
                if role == "runtime"
                else {"type": "application", "id": "mail.example"}
            )
            policy_decision = {
                "type": "policy.decision",
                "decision_id": f"decision-{role}-1",
                "enforcer": enforcer,
                "outcome": "allow",
                "policy": {"id": f"{role}-approval-policy", "version": "1"},
                "reason_code": "approval_satisfied",
                "matched_rules": ["writes.require_local_approval"],
                "safe_to_show": "The exact write request was approved.",
                "evaluated_at": "2026-07-22T12:00:00Z",
            }
            policy_decision["policy_decision_hash"] = _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/policy-decision/v1",
                policy_decision,
            )
            body = {
                "receipt_id": f"approval-{role}-1",
                "receipt_type": "approval",
                "grant_id": base_app_receipt["grant_id"],
                "grant_hash": base_app_receipt["grant_hash"],
                "session_id": base_app_receipt["session_id"],
                "session_generation": base_app_receipt["session_generation"],
                "trace_id": base_app_receipt["trace_id"],
                "span_id": "00f067aa0ba902b7",
                "action_id": base_app_receipt["action_id"],
                "app_id": base_app_receipt["app_id"],
                "surface_version": base_app_receipt["surface_version"],
                "surface_hash": base_app_receipt["surface_hash"],
                "runtime": base_app_receipt["runtime"],
                "actor_agent": base_app_receipt["actor_agent"],
                "subject": base_app_receipt["subject"],
                "idempotency_key": base_app_receipt["idempotency_key"],
                "input_hash": base_app_receipt["input_hash"],
                "execution": base_app_receipt["execution"],
                "execution_hash": base_app_receipt["execution_hash"],
                "approval": {
                    "approval_id": f"approval-{role}-1",
                    "role": role,
                    "decided_by": "user",
                    "valid_until": "2026-07-22T12:05:00Z",
                },
                "policy_decision_hash": policy_decision["policy_decision_hash"],
                "policy_decision": policy_decision,
                "timestamp": "2026-07-22T12:00:00Z",
                "result": "approved",
            }
            receipt_hash = _canonical_object_hash(receipt_domain, body)
            receipt = {
                **body,
                "receipt_hash": receipt_hash,
            }
            binding = {
                member: receipt[member]
                for member in (
                    "session_id", "session_generation", "trace_id", "grant_id",
                    "grant_hash", "app_id", "surface_hash", "surface_version",
                    "action_id", "idempotency_key", "input_hash", "runtime",
                    "actor_agent", "subject", "execution", "execution_hash",
                )
            }
            return f"asp://receipt/approval-{role}-1", {
                "uri": f"asp://receipt/approval-{role}-1",
                "receipt": receipt,
                "expected": {
                    "receipt_id": receipt["receipt_id"],
                    "receipt_hash": receipt_hash,
                    "receipt_type": "approval",
                    "approval_role": role,
                    "binding": binding,
                    "signature_required": False,
                },
            }

        runtime_uri, runtime_receipt = approval_receipt("runtime")
        application_uri, application_receipt = approval_receipt("application")
        records = {"runtime": runtime_receipt, "application": application_receipt}

        def approval_resource_read(record: dict) -> tuple[dict, dict]:
            receipt = record["receipt"]
            uri = record["uri"]
            message = {
                "jsonrpc": "2.0",
                "id": 12,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(receipt),
                        }
                    ]
                },
            }
            context = {
                "requested_resource_uri": uri,
                "resource_kind": "receipt",
                "expected_resource": receipt,
                "resource_hash_domain": receipt_domain,
                "expected_resource_hash": receipt["receipt_hash"],
                "expected_receipt_type": "approval",
                "expected_receipt_semantics": {
                    "result": receipt["result"],
                    "error": None,
                    "output_hash": None,
                    "actual_effects": None,
                    "actual_effects_hash": None,
                    "effect_outcome": None,
                    "resource": None,
                },
                "expected_authenticated_receipt_resources": [record],
            }
            return message, context

        approval_read, approval_read_context = approval_resource_read(
            runtime_receipt
        )
        validate_mcp_wire_semantics(approval_read, **approval_read_context)
        missing_valid_until_record = copy.deepcopy(runtime_receipt)
        missing_valid_until_record["receipt"]["approval"].pop("valid_until")
        missing_valid_until_record["receipt"].pop("receipt_hash")
        missing_valid_until_record["receipt"]["receipt_hash"] = (
            _canonical_object_hash(
                receipt_domain, missing_valid_until_record["receipt"]
            )
        )
        missing_valid_until_record["expected"]["receipt_hash"] = (
            missing_valid_until_record["receipt"]["receipt_hash"]
        )
        missing_valid_until, missing_valid_until_context = approval_resource_read(
            missing_valid_until_record
        )
        with self.assertRaisesRegex(ConformanceError, "oracle rejected"):
            validate_mcp_wire_semantics(
                missing_valid_until, **missing_valid_until_context
            )
        for label, invalid_value in (
            ("empty approval id", {"approval_id": ""}),
            ("numeric valid_until", {"valid_until": 42}),
        ):
            with self.subTest(invalid_approval_field=label):
                invalid_record = copy.deepcopy(runtime_receipt)
                invalid_record["receipt"]["approval"].update(invalid_value)
                invalid_record["receipt"].pop("receipt_hash")
                invalid_record["receipt"]["receipt_hash"] = (
                    _canonical_object_hash(
                        receipt_domain, invalid_record["receipt"]
                    )
                )
                invalid_record["expected"]["receipt_hash"] = invalid_record[
                    "receipt"
                ]["receipt_hash"]
                invalid_read, invalid_read_context = approval_resource_read(
                    invalid_record
                )
                with self.assertRaisesRegex(ConformanceError, "oracle rejected"):
                    validate_mcp_wire_semantics(
                        invalid_read, **invalid_read_context
                    )

        def sync_text(message: dict) -> None:
            message["result"]["content"][0]["text"] = json.dumps(
                message["result"]["structuredContent"],
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )

        deny_policy_message = copy.deepcopy(base_message)
        deny_policy_context = copy.deepcopy(base_context)
        deny_policy_record = deny_policy_context[
            "expected_authenticated_receipt_resources"
        ][0]
        deny_policy_receipt = deny_policy_record["receipt"]
        deny_policy_receipt["policy_decision"]["outcome"] = "deny"
        deny_policy_receipt["policy_decision"]["reason_code"] = (
            "app_policy_denied"
        )
        deny_policy_receipt["policy_decision"].pop("policy_decision_hash")
        deny_policy_receipt["policy_decision"]["policy_decision_hash"] = (
            _canonical_object_hash(
                "https://github.com/0al-spec/agent-surface/hash/policy-decision/v1",
                deny_policy_receipt["policy_decision"],
            )
        )
        deny_policy_receipt["policy_decision_hash"] = deny_policy_receipt[
            "policy_decision"
        ]["policy_decision_hash"]
        deny_policy_receipt.pop("receipt_hash")
        deny_policy_receipt["receipt_hash"] = _canonical_object_hash(
            receipt_domain, deny_policy_receipt
        )
        deny_policy_record["expected"]["receipt_hash"] = deny_policy_receipt[
            "receipt_hash"
        ]
        deny_policy_message["result"]["structuredContent"]["message"][
            "payload"
        ]["receipt_hash"] = deny_policy_receipt["receipt_hash"]
        sync_text(deny_policy_message)
        with self.assertRaisesRegex(ConformanceError, "Policy Decision"):
            validate_mcp_wire_semantics(
                deny_policy_message, **deny_policy_context
            )

        success_error_message = copy.deepcopy(base_message)
        success_error_context = copy.deepcopy(base_context)
        success_error_payload = success_error_message["result"][
            "structuredContent"
        ]["message"]["payload"]
        success_error_message["result"]["structuredContent"]["message"][
            "type"
        ] = "action.error"
        success_error_message["result"]["isError"] = True
        success_error_payload.pop("result")
        success_error_payload.pop("output")
        success_error_payload["error"] = {
            "code": "schema_invalid",
            "description": "The application result did not match its schema.",
            "retryable": False,
        }
        success_error_record = success_error_context[
            "expected_authenticated_receipt_resources"
        ][0]
        success_error_receipt = success_error_record["receipt"]
        success_error_receipt["error"] = copy.deepcopy(
            success_error_payload["error"]
        )
        success_error_receipt.pop("receipt_hash")
        success_error_receipt["receipt_hash"] = _canonical_object_hash(
            receipt_domain, success_error_receipt
        )
        success_error_record["expected"]["receipt_hash"] = (
            success_error_receipt["receipt_hash"]
        )
        success_error_payload["receipt_hash"] = success_error_receipt[
            "receipt_hash"
        ]
        sync_text(success_error_message)
        with self.assertRaisesRegex(
            ConformanceError, "claims success or output evidence"
        ):
            validate_mcp_wire_semantics(
                success_error_message, **success_error_context
            )

        def with_approval_roles(*roles: str) -> tuple[dict, dict]:
            message = copy.deepcopy(base_message)
            context = copy.deepcopy(base_context)
            structured = message["result"]["structuredContent"]
            payload = structured["message"]["payload"]
            approval_hashes = {
                role: records[role]["receipt"]["receipt_hash"] for role in roles
            }
            payload["approval_receipt_hashes"] = approval_hashes
            app_record = context["expected_authenticated_receipt_resources"][0]
            app_receipt = app_record["receipt"]
            app_receipt["approval_receipt_hashes"] = approval_hashes
            app_receipt.pop("receipt_hash")
            app_receipt["receipt_hash"] = _canonical_object_hash(
                receipt_domain, app_receipt
            )
            app_record["expected"]["receipt_hash"] = app_receipt["receipt_hash"]
            payload["receipt_hash"] = app_receipt["receipt_hash"]
            structured["receipt_resource_uris"].extend(
                records[role]["uri"] for role in roles
            )
            message["result"]["content"].extend(
                {
                    "type": "resource_link",
                    "name": "asp-receipt",
                    "uri": records[role]["uri"],
                }
                for role in roles
            )
            context["expected_request_payload"]["approval_receipt_hashes"] = {
                "runtime": runtime_receipt["receipt"]["receipt_hash"]
            }
            context["expected_authenticated_receipt_resources"] = [
                app_record,
                *(records[role] for role in roles),
            ]
            context["expected_receipt_resource_uris"] = list(
                structured["receipt_resource_uris"]
            )
            sync_text(message)
            return message, context

        runtime_message, runtime_context = with_approval_roles("runtime")
        _validate_with_schema(
            runtime_message,
            loads_strict_json(
                (ROOT / "conformance" / "v1" / "mcp-binding.schema.json").read_text(
                    encoding="utf-8"
                )
            ),
            "MCP approval-map positive",
            registry=_schema_registry(ROOT),
        )
        validate_mcp_wire_semantics(runtime_message, **runtime_context)

        changed_runtime = copy.deepcopy(runtime_message)
        changed_runtime["result"]["structuredContent"]["message"]["payload"][
            "approval_receipt_hashes"
        ]["runtime"] = digest("changed-runtime-approval")
        sync_text(changed_runtime)
        with self.assertRaisesRegex(ConformanceError, "does not preserve"):
            validate_mcp_wire_semantics(changed_runtime, **runtime_context)

        final_message, final_context = with_approval_roles(
            "runtime", "application"
        )
        with self.assertRaisesRegex(ConformanceError, "without final policy"):
            validate_mcp_wire_semantics(final_message, **final_context)
        final_context["expected_final_approval_receipt_hashes"] = {
            "runtime": runtime_receipt["receipt"]["receipt_hash"],
            "application": application_receipt["receipt"]["receipt_hash"],
        }
        _validate_with_schema(
            final_message,
            loads_strict_json(
                (ROOT / "conformance" / "v1" / "mcp-binding.schema.json").read_text(
                    encoding="utf-8"
                )
            ),
            "MCP final approval-map positive",
            registry=_schema_registry(ROOT),
        )
        validate_mcp_wire_semantics(final_message, **final_context)

        missing_approval_resource = copy.deepcopy(final_message)
        missing_approval_resource["result"]["content"] = [
            item
            for item in missing_approval_resource["result"]["content"]
            if item.get("uri") != application_uri
        ]
        missing_approval_resource["result"]["structuredContent"][
            "receipt_resource_uris"
        ].remove(application_uri)
        sync_text(missing_approval_resource)
        missing_context = {
            **final_context,
            "expected_receipt_resource_uris": missing_approval_resource["result"]
            ["structuredContent"]["receipt_resource_uris"],
        }
        with self.assertRaisesRegex(ConformanceError, "one-to-one"):
            validate_mcp_wire_semantics(
                missing_approval_resource, **missing_context
            )

        tampered_resource_context = copy.deepcopy(runtime_context)
        next(
            record
            for record in tampered_resource_context[
                "expected_authenticated_receipt_resources"
            ]
            if record["expected"]["approval_role"] == "runtime"
        )["receipt"]["result"] = "substituted"
        with self.assertRaisesRegex(ConformanceError, "oracle rejected"):
            validate_mcp_wire_semantics(
                runtime_message, **tampered_resource_context
            )

        ordinary_link_only = copy.deepcopy(runtime_message)
        ordinary_link_only["result"]["content"] = ordinary_link_only["result"][
            "content"
        ][:2]
        ordinary_link_only["result"]["structuredContent"][
            "receipt_resource_uris"
        ] = ["asp://receipt/receipt-1"]
        sync_text(ordinary_link_only)
        ordinary_only_context = {
            **runtime_context,
            "expected_receipt_resource_uris": ["asp://receipt/receipt-1"],
        }
        with self.assertRaisesRegex(ConformanceError, "one-to-one"):
            validate_mcp_wire_semantics(
                ordinary_link_only, **ordinary_only_context
            )

        capacity_case = cases["ASP-SC-MB-013"]
        capacity_message = loads_human_json(
            capacity_case["instance_json"], source="MCP capacity approval map"
        )
        capacity_context = copy.deepcopy(capacity_case["context"])
        capacity_structured = capacity_message["result"]["structuredContent"]
        capacity_structured["message"]["payload"]["approval_receipt_hashes"] = {
            "runtime": runtime_receipt["receipt"]["receipt_hash"]
        }
        capacity_structured["receipt_resource_uris"] = [runtime_uri]
        capacity_message["result"]["content"].append(
            {
                "type": "resource_link",
                "name": "asp-receipt",
                "uri": runtime_uri,
            }
        )
        capacity_context["expected_request_payload"]["approval_receipt_hashes"] = {
            "runtime": runtime_receipt["receipt"]["receipt_hash"]
        }
        capacity_context["expected_authenticated_receipt_resources"] = [
            records["runtime"]
        ]
        capacity_context["expected_receipt_resource_uris"] = [runtime_uri]
        capacity_context["action_mode"] = "commit"
        sync_text(capacity_message)
        with self.assertRaisesRegex(ConformanceError, "pre-admission capacity"):
            validate_mcp_wire_semantics(capacity_message, **capacity_context)

        for mode in ("read", "dry_run", "propose"):
            with self.subTest(disallowed_approval_mode=mode):
                invalid_mode, invalid_context = with_approval_roles("runtime")
                invalid_payload = invalid_mode["result"]["structuredContent"][
                    "message"
                ]["payload"]
                for member in (
                    "effect_outcome",
                    "actual_effects",
                    "actual_effects_hash",
                    "receipt_id",
                    "receipt_hash",
                ):
                    invalid_payload.pop(member, None)
                invalid_mode["result"]["content"] = [
                    item
                    for item in invalid_mode["result"]["content"]
                    if item.get("uri") != "asp://receipt/receipt-1"
                ]
                invalid_mode["result"]["structuredContent"][
                    "receipt_resource_uris"
                ] = [runtime_uri]
                execution = {"mode": mode, "execution_id": "e1"}
                execution_hash = _canonical_object_hash(
                    "https://github.com/0al-spec/agent-surface/hash/action-execution/v1",
                    execution,
                )
                invalid_payload["execution"] = execution
                invalid_payload["execution_hash"] = execution_hash
                invalid_context["expected_request_payload"]["execution"] = execution
                invalid_context["expected_request_payload"][
                    "execution_hash"
                ] = execution_hash
                invalid_context["action_mode"] = mode
                invalid_context["receipt_required"] = False
                invalid_context["expected_actual_effects"] = None
                invalid_context["expected_receipt_resource_uris"] = [runtime_uri]
                if mode == "propose":
                    invalid_payload["proposal_id"] = "proposal-1"
                    invalid_payload["proposal"] = {"draft": "mail"}
                if mode == "dry_run":
                    raw_token = bytes(range(16))
                    preview = {
                        "preview_id": "preview-1",
                        "commit_action_id": "mail.send",
                        "execution_token": base64.urlsafe_b64encode(raw_token)
                        .rstrip(b"=")
                        .decode("ascii"),
                        "execution_token_hash": "sha-256:"
                        + base64.urlsafe_b64encode(
                            hashlib.sha256(raw_token).digest()
                        )
                        .rstrip(b"=")
                        .decode("ascii"),
                        "expires_at": "2026-07-22T12:05:00Z",
                    }
                    preconditions = {"mailbox_revision": "r1"}
                    expected_effects = [
                        {"effect_id": "mail-send", "operation": "send"}
                    ]
                    invalid_payload["result"] = "preview"
                    invalid_payload["preview"] = preview
                    invalid_payload["preconditions"] = preconditions
                    invalid_payload["preconditions_hash"] = _canonical_object_hash(
                        "https://github.com/0al-spec/agent-surface/hash/action-preconditions/v1",
                        preconditions,
                    )
                    invalid_payload["expected_effects"] = expected_effects
                    invalid_payload["expected_effects_hash"] = _canonical_object_hash(
                        "https://github.com/0al-spec/agent-surface/hash/expected-effects/v1",
                        expected_effects,
                    )
                    invalid_context["expected_result"] = "preview"
                    invalid_context["expected_preview"] = preview
                    invalid_context["expected_preview_preconditions"] = preconditions
                    invalid_context["expected_preview_effects"] = expected_effects
                    invalid_context["evaluation_time"] = "2026-07-22T12:00:00Z"
                sync_text(invalid_mode)
                with self.assertRaisesRegex(
                    ConformanceError, "cannot claim approval receipts"
                ):
                    validate_mcp_wire_semantics(
                        invalid_mode, **invalid_context
                    )

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
