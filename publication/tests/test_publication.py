from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from publication.check import (
    PublicationError,
    _validate_normative_references,
    main,
    validate_catalog,
)


ROOT = Path(__file__).resolve().parents[2]


class PublicationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = validate_catalog(ROOT)

    def catalog_copy(self) -> tuple[Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / "publication", root / "publication")
        shutil.copytree(ROOT / "drafts", root / "drafts")
        (root / "conformance" / "v1").mkdir(parents=True)
        for name in ("suite.json", "bundles.json"):
            shutil.copy2(
                ROOT / "conformance" / "v1" / name,
                root / "conformance" / "v1" / name,
            )
        return root, root / "publication" / "document-set.json"

    def write_catalog(self, path: Path, catalog: dict) -> None:
        path.write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def test_canonical_catalog_and_schema_are_valid(self) -> None:
        schema = json.loads(
            (ROOT / "publication" / "document-set.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        self.assertEqual(self.catalog["publication_mode"], "transitional_monolith")
        self.assertEqual(len(self.catalog["documents"]), 1)
        self.assertEqual(len(self.catalog["reserved_documents"]), 7)
        self.assertEqual(len(self.catalog["registries"]), 2)
        self.assertEqual(main(["validate", "--root", str(ROOT)]), 0)

    def test_unknown_member_is_rejected_by_closed_schema(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["unexpected"] = True
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "schema violation"):
            validate_catalog(root)

    def test_duplicate_json_member_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace(
                '"schema_version": 1,',
                '"schema_version": 1,\n  "schema_version": 1,',
                1,
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(PublicationError, "duplicate JSON object member"):
            validate_catalog(root)

    def test_floating_dependency_version_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["reserved_documents"][1]["normative_dependencies"][0][
            "version"
        ] = "latest"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "schema violation"):
            validate_catalog(root)

    def test_unknown_exact_dependency_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["reserved_documents"][1]["normative_dependencies"][0][
            "version"
        ] = "9.9.9"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "unknown or unpinned dependency"):
            validate_catalog(root)

    def test_cycle_and_forward_dependency_are_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        core = catalog["reserved_documents"][0]
        authorization = catalog["reserved_documents"][1]
        core["normative_dependencies"] = [
            {
                "document_id": authorization["document_id"],
                "version": authorization["version"],
            }
        ]
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(
            PublicationError, "cannot depend normatively|must precede"
        ):
            validate_catalog(root)

    def test_core_cannot_depend_on_an_extension(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        core = catalog["reserved_documents"][0]
        authorization = catalog["reserved_documents"][1]
        core["normative_dependencies"] = [
            {
                "document_id": authorization["document_id"],
                "version": authorization["version"],
            }
        ]
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "core.*authorization"):
            validate_catalog(root)

    def test_required_role_dependency_is_enforced(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["reserved_documents"][1]["normative_dependencies"] = []
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "missing required.*core"):
            validate_catalog(root)

    def test_duplicate_planned_export_owner_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        exported = {
            "kind": "identifier_namespace",
            "id": "https://github.com/0al-spec/agent-surface/identifiers/example",
        }
        catalog["reserved_documents"][0]["planned_exports"] = [exported]
        catalog["reserved_documents"][1]["planned_exports"] = [exported]
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "multiple owners"):
            validate_catalog(root)

    def test_registry_requires_exact_active_owner_export(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["documents"][0]["exports"] = [
            item
            for item in catalog["documents"][0]["exports"]
            if item["id"] != catalog["registries"][0]["registry_id"]
        ]
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "not declared by its owner"):
            validate_catalog(root)

    def test_active_source_requires_artifact_ownership(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["documents"][0]["exports"] = [
            item
            for item in catalog["documents"][0]["exports"]
            if not (
                item["kind"] == "artifact"
                and item["id"] == catalog["documents"][0]["source_path"]
            )
        ]
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "canonical source artifact"):
            validate_catalog(root)

    def test_registry_source_identity_and_version_are_bound(self) -> None:
        for member, value, message in (
            ("id_member", "missing_id", "does not match the catalog"),
            ("version_member", "missing_version", "does not match catalog version"),
        ):
            with self.subTest(member=member):
                root, path = self.catalog_copy()
                catalog = copy.deepcopy(self.catalog)
                catalog["registries"][0][member] = value
                self.write_catalog(path, catalog)
                with self.assertRaisesRegex(PublicationError, message):
                    validate_catalog(root)

    def test_source_and_aggregate_digests_are_bound(self) -> None:
        for location in ("document", "aggregate"):
            with self.subTest(location=location):
                root, path = self.catalog_copy()
                catalog = copy.deepcopy(self.catalog)
                if location == "document":
                    catalog["documents"][0]["source_sha256"] = "0" * 64
                    message = "source digest does not match"
                else:
                    catalog["aggregate"]["sha256"] = "0" * 64
                    message = "aggregate digest does not match"
                self.write_catalog(path, catalog)
                with self.assertRaisesRegex(PublicationError, message):
                    validate_catalog(root)

    def test_explicit_anchor_inventory_is_bound_to_source(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["documents"][0]["public_anchors"][0][
            "heading"
        ] = "Different Heading"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "public anchor inventory"):
            validate_catalog(root)

    def test_cross_document_anchor_move_is_fail_closed_in_schema_v1(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["anchor_policy"]["move_policy"] = "retain_immutable_alias"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "schema violation"):
            validate_catalog(root)

    def test_internal_dependency_requires_resolved_reference_record(self) -> None:
        target = copy.deepcopy(self.catalog["documents"][0])
        target["document_id"] = (
            "https://github.com/0al-spec/agent-surface/documents/core"
        )
        target["version"] = "1.0.0"
        source = copy.deepcopy(self.catalog["documents"][0])
        source["document_id"] = (
            "https://github.com/0al-spec/agent-surface/documents/authorization"
        )
        source["version"] = "1.0.0"
        source["normative_dependencies"] = [
            {
                "document_id": target["document_id"],
                "version": target["version"],
            }
        ]
        source["normative_references"] = []
        by_ref = {
            (target["document_id"], target["version"]): target,
            (source["document_id"], source["version"]): source,
        }
        with self.assertRaisesRegex(PublicationError, "lack normative reference"):
            _validate_normative_references([target, source], by_ref)

        source["normative_references"] = [
            {
                "source_anchor_id": "modular-rfc-publication-architecture",
                "target_document": {
                    "document_id": target["document_id"],
                    "version": target["version"],
                },
                "target_kind": "anchor",
                "target_id": "document-classes",
            }
        ]
        _validate_normative_references([target, source], by_ref)

    def test_orphan_registry_export_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["documents"][0]["exports"].append(
            {
                "kind": "registry",
                "id": "https://github.com/0al-spec/agent-surface/conformance/orphan/v1",
            }
        )
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "orphan exports"):
            validate_catalog(root)

    def test_repository_escape_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["reserved_documents"][0]["target_source_path"] = "../outside.md"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(
            PublicationError, "schema violation|repository-relative"
        ):
            validate_catalog(root)

    def test_noncanonical_repository_path_is_rejected(self) -> None:
        for value in (
            "./drafts/modules/core.md",
            "drafts//modules/core.md",
            "drafts/modules/./core.md",
        ):
            with self.subTest(value=value):
                root, path = self.catalog_copy()
                catalog = copy.deepcopy(self.catalog)
                catalog["reserved_documents"][0]["target_source_path"] = value
                self.write_catalog(path, catalog)
                with self.assertRaisesRegex(
                    PublicationError, "canonical repository-relative syntax"
                ):
                    validate_catalog(root)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_symlink_escape_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        (root / "drafts" / "escape").symlink_to(outside, target_is_directory=True)
        catalog = copy.deepcopy(self.catalog)
        catalog["reserved_documents"][0][
            "target_source_path"
        ] = "drafts/escape/core.md"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "escapes the repository"):
            validate_catalog(root)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_dangling_reserved_symlink_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        target = root / "drafts" / "dangling-core.md"
        target.symlink_to(root / "drafts" / "missing-core.md")
        catalog = copy.deepcopy(self.catalog)
        catalog["reserved_documents"][0][
            "target_source_path"
        ] = "drafts/dangling-core.md"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "reserved but already exists"):
            validate_catalog(root)

    def test_materialized_reserved_source_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        target = root / self.catalog["reserved_documents"][0]["target_source_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Premature Core\n", encoding="utf-8")
        with self.assertRaisesRegex(PublicationError, "reserved but already exists"):
            validate_catalog(root)

    def test_modular_mode_requires_complete_assembly(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["publication_mode"] = "modular"
        catalog["aggregate"]["generated"] = True
        del catalog["aggregate"]["source_document"]
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "schema violation"):
            validate_catalog(root)

    def test_complete_modular_shape_is_fail_closed_until_resolver_exists(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["publication_mode"] = "modular"
        catalog["reserved_documents"] = []
        catalog["aggregate"]["generated"] = True
        del catalog["aggregate"]["source_document"]
        catalog["aggregate"]["assembly"] = {
            "compiler": "https://github.com/0al-spec/Hyperprompt",
            "compiler_revision": "0" * 40,
            "entrypoint": "publication/document-set.json",
            "manifest": "publication/document-set.json",
            "source_map": "publication/document-set.json",
        }
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "modular publication mode is unsupported"):
            validate_catalog(root)


if __name__ == "__main__":
    unittest.main()
