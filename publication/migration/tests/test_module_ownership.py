from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from publication.migration.check import (
    OwnershipError,
    SCHEMA_PATH,
    validate_ownership_map,
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


if __name__ == "__main__":
    unittest.main()
