from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from publication.migration.check import (
    MATERIALIZATION_PATH,
    OwnershipError,
    SCHEMA_PATH,
    STANDALONE_PATH,
    validate_materialization,
    validate_ownership_map,
    validate_standalone,
)


ROOT = Path(__file__).resolve().parents[3]


class ModuleOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ownership_map = validate_ownership_map(ROOT)

    def fixture(self) -> tuple[Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / "publication", root / "publication")
        shutil.copytree(ROOT / "drafts", root / "drafts")
        return root, root / "publication/migration/module-ownership.json"

    @staticmethod
    def write(path: Path, value: dict) -> None:
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def test_canonical_map_and_schema_are_valid(self) -> None:
        schema = json.loads((ROOT / SCHEMA_PATH).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.assertEqual(len(self.ownership_map["modules"]), 7)
        self.assertEqual(
            self.ownership_map["authority"],
            "non_authoritative_migration_plan",
        )

    def test_missing_top_level_assignment_is_rejected(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.ownership_map)
        value["section_assignments"] = [
            item
            for item in value["section_assignments"]
            if item["heading"] != "Security Considerations"
        ]
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "no explicit owner"):
            validate_ownership_map(root)

    def test_duplicate_section_owner_is_rejected(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.ownership_map)
        value["section_assignments"].append(
            copy.deepcopy(value["section_assignments"][0])
        )
        self.write(path, value)
        with self.assertRaisesRegex(
            OwnershipError,
            "sorted by source_line|multiple explicit owners",
        ):
            validate_ownership_map(root)

    def test_non_reserved_owner_is_rejected(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.ownership_map)
        value["section_assignments"][0]["owner_document_id"] = (
            "https://github.com/0al-spec/agent-surface/documents/not-reserved"
        )
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "non-reserved owner"):
            validate_ownership_map(root)

    def test_stale_heading_location_is_rejected(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.ownership_map)
        value["section_assignments"][0]["source_line"] = 2
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "does not identify a heading"):
            validate_ownership_map(root)

    def test_stale_source_digest_is_rejected(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.ownership_map)
        value["canonical_source"]["sha256"] = "0" * 64
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "digest is stale"):
            validate_ownership_map(root)

    def test_missing_export_owner_is_rejected(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.ownership_map)
        value["export_assignments"].pop()
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "export ownership is not closed"):
            validate_ownership_map(root)

    def test_public_anchor_owner_must_match_section_owner(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.ownership_map)
        value["public_anchor_assignments"][0]["owner_document_id"] = (
            "https://github.com/0al-spec/agent-surface/documents/conformance"
        )
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "conflicts with its section"):
            validate_ownership_map(root)


class ModuleMaterializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ownership_map = validate_ownership_map(ROOT)
        cls.materialization = validate_materialization(ROOT, cls.ownership_map)

    def fixture(self) -> tuple[Path, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / "publication", root / "publication")
        shutil.copytree(ROOT / "drafts", root / "drafts")
        return (
            root,
            root / MATERIALIZATION_PATH,
            root / "publication/candidates/modular-document-set/candidate.json",
        )

    @staticmethod
    def write(path: Path, value: dict) -> None:
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def test_complete_candidate_materializes_all_reserved_modules(self) -> None:
        self.assertEqual(len(self.materialization["modules"]), 7)
        self.assertEqual(
            sum(
                len(module["fragments"])
                for module in self.materialization["modules"]
            ),
            25,
        )

    def test_stale_ownership_map_digest_is_rejected(self) -> None:
        root, path, _ = self.fixture()
        value = copy.deepcopy(self.materialization)
        value["ownership_map"]["sha256"] = "0" * 64
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "ownership-map digest is stale"):
            validate_materialization(root)

    def test_fragment_reassignment_is_rejected(self) -> None:
        root, path, _ = self.fixture()
        value = copy.deepcopy(self.materialization)
        moved = value["modules"][0]["fragments"].pop()
        value["modules"][1]["fragments"].append(moved)
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "fragment ownership is stale"):
            validate_materialization(root)

    def test_candidate_fragment_order_is_closed(self) -> None:
        root, _, candidate_path = self.fixture()
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["sources"]["declared"][1], candidate["sources"]["declared"][2] = (
            candidate["sources"]["declared"][2],
            candidate["sources"]["declared"][1],
        )
        self.write(candidate_path, candidate)
        with self.assertRaisesRegex(OwnershipError, "fragment order"):
            validate_materialization(root)

    def test_stale_fragment_derivation_is_rejected(self) -> None:
        root, _, candidate_path = self.fixture()
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["sources"]["declared"][1]["canonical_derivation"][
            "end_byte"
        ] -= 1
        self.write(candidate_path, candidate)
        with self.assertRaisesRegex(
            OwnershipError,
            "modular candidate is invalid|derivation is stale",
        ):
            validate_materialization(root)

    def test_reserved_canonical_target_must_remain_absent(self) -> None:
        root, _, _ = self.fixture()
        target = root / self.materialization["modules"][0]["target_source_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Premature canonical module\n", encoding="utf-8")
        with self.assertRaisesRegex(OwnershipError, "must remain absent"):
            validate_materialization(root)


class StandaloneModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ownership_map = validate_ownership_map(ROOT)
        cls.materialization = validate_materialization(ROOT, cls.ownership_map)
        cls.standalone = validate_standalone(
            ROOT,
            cls.ownership_map,
            cls.materialization,
        )

    def fixture(self) -> tuple[Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / "publication", root / "publication")
        shutil.copytree(ROOT / "drafts", root / "drafts")
        return root, root / STANDALONE_PATH

    @staticmethod
    def write(path: Path, value: dict) -> None:
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def test_complete_standalone_set_has_closed_reference_and_anchor_maps(
        self,
    ) -> None:
        self.assertEqual(len(self.standalone["documents"]), 7)
        self.assertEqual(len(self.standalone["navigation_references"]), 48)
        self.assertEqual(len(self.standalone["public_anchor_relocations"]), 9)

    def test_stale_materialization_digest_is_rejected(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.standalone)
        value["materialization"]["sha256"] = "0" * 64
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "input digest is stale"):
            validate_standalone(root)

    def test_missing_normative_reference_is_rejected(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.standalone)
        value["documents"][1]["normative_references"] = []
        self.write(path, value)
        with self.assertRaisesRegex(
            OwnershipError,
            "standalone document metadata is stale",
        ):
            validate_standalone(root)

    def test_navigation_cannot_target_the_wrong_document(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.standalone)
        value["navigation_references"][0]["target_document_id"] = (
            value["documents"][1]["document_id"]
        )
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "navigation reference is stale"):
            validate_standalone(root)

    def test_public_relocation_requires_both_compatibility_aliases(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.standalone)
        value["public_anchor_relocations"][0]["compatibility_aliases"].pop()
        self.write(path, value)
        with self.assertRaisesRegex(
            OwnershipError,
            "schema violation|relocation is stale",
        ):
            validate_standalone(root)

    def test_stale_candidate_document_digest_is_rejected(self) -> None:
        root, _ = self.fixture()
        document = self.standalone["documents"][0]
        candidate = root / document["candidate_path"]
        candidate.write_text(
            candidate.read_text(encoding="utf-8") + "\nStale prose.\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(OwnershipError, "candidate digest is stale"):
            validate_standalone(root)

    def test_standalone_document_must_have_one_reserved_h1(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.standalone)
        document = value["documents"][1]
        candidate = root / document["candidate_path"]
        content = candidate.read_text(encoding="utf-8") + "\n# Extra root\n"
        candidate.write_text(content, encoding="utf-8")
        document["sha256"] = hashlib.sha256(candidate.read_bytes()).hexdigest()
        self.write(path, value)
        with self.assertRaisesRegex(OwnershipError, "exactly one reserved H1"):
            validate_standalone(root)

    def test_replacement_public_anchor_must_exist(self) -> None:
        root, path = self.fixture()
        value = copy.deepcopy(self.standalone)
        document = value["documents"][0]
        candidate = root / document["candidate_path"]
        content = candidate.read_text(encoding="utf-8").replace(
            '<a id="modular-rfc-publication-architecture"></a>\n',
            "",
            1,
        )
        candidate.write_text(content, encoding="utf-8")
        document["sha256"] = hashlib.sha256(candidate.read_bytes()).hexdigest()
        self.write(path, value)
        with self.assertRaisesRegex(
            OwnershipError,
            "replacement public anchor is missing",
        ):
            validate_standalone(root)


if __name__ == "__main__":
    unittest.main()
