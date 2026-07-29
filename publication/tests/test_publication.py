from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

from publication.check import (
    PublicationError,
    _explicit_anchors,
    _historical_catalogs,
    _validate_normative_references,
    main,
    validate_catalog,
    validate_catalog_history,
    validate_history,
)
from publication import modular


ROOT = Path(__file__).resolve().parents[2]


class PublicationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = validate_catalog(ROOT)
        cls.pre_activation_catalog = json.loads(
            subprocess.check_output(
                ["git", "show", "origin/main:publication/document-set.json"],
                cwd=ROOT,
                text=True,
            )
        )

    def history(
        self, *snapshots: tuple[str, dict]
    ) -> list[tuple[str, dict]]:
        return [
            ("pre-activation", self.pre_activation_catalog),
            *snapshots,
        ]

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
        self.assertEqual(self.catalog["publication_mode"], "modular")
        self.assertEqual(len(self.catalog["documents"]), 7)
        self.assertEqual(len(self.catalog["reserved_documents"]), 0)
        self.assertEqual(len(self.catalog["anchor_relocations"]), 9)
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
                '"schema_version": 2,',
                '"schema_version": 2,\n  "schema_version": 2,',
                1,
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(PublicationError, "duplicate JSON object member"):
            validate_catalog(root)

    def test_floating_dependency_version_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["documents"][1]["normative_dependencies"][0][
            "version"
        ] = "latest"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "schema violation"):
            validate_catalog(root)

    def test_unknown_exact_dependency_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["documents"][1]["normative_dependencies"][0][
            "version"
        ] = "9.9.9"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "unknown or unpinned dependency"):
            validate_catalog(root)

    def test_cycle_and_forward_dependency_are_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        core = catalog["documents"][0]
        authorization = catalog["documents"][1]
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
        core = catalog["documents"][0]
        authorization = catalog["documents"][1]
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
        catalog["documents"][1]["normative_dependencies"] = []
        catalog["documents"][1]["normative_references"] = []
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "missing required.*core"):
            validate_catalog(root)

    def test_duplicate_active_export_owner_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        exported = {
            "kind": "identifier_namespace",
            "id": "https://github.com/0al-spec/agent-surface/identifiers/example",
        }
        catalog["documents"][0]["exports"].append(exported)
        catalog["documents"][1]["exports"].append(exported)
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "multiple owners"):
            validate_catalog(root)

    def test_registry_requires_exact_active_owner_export(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        owner = next(
            item
            for item in catalog["documents"]
            if item["role"] == "conformance"
        )
        owner["exports"] = [
            item
            for item in owner["exports"]
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

    def test_published_document_version_is_immutable(self) -> None:
        current = copy.deepcopy(self.catalog)
        current["document_set_version"] = "0.1.0-draft.2"
        current["documents"][0]["source_sha256"] = "0" * 64
        current["aggregate"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            PublicationError,
            "published document version.*bump document version",
        ):
            validate_catalog_history(
                current,
                self.history(("published-commit", self.catalog)),
            )

    def test_document_set_version_is_immutable(self) -> None:
        current = copy.deepcopy(self.catalog)
        current["documents"][0]["version"] = "0.1.0-draft.2"
        with self.assertRaisesRegex(
            PublicationError,
            "published document-set version.*bump document_set_version",
        ):
            validate_catalog_history(
                current,
                self.history(("published-commit", self.catalog)),
            )

    def test_published_registry_version_is_immutable(self) -> None:
        current = copy.deepcopy(self.catalog)
        current["document_set_version"] = "0.1.0-draft.2"
        current["registries"][0]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            PublicationError,
            "published registry version.*bump registry version",
        ):
            validate_catalog_history(
                current,
                self.history(("published-commit", self.catalog)),
            )

    def test_conflicting_historical_snapshot_is_rejected(self) -> None:
        conflicting = copy.deepcopy(self.catalog)
        conflicting["document_set_version"] = "0.1.0-draft.2"
        conflicting["documents"][0]["title"] = "Conflicting published title"
        with self.assertRaisesRegex(
            PublicationError,
            "published document version.*conflicts between",
        ):
            validate_catalog_history(
                copy.deepcopy(self.catalog),
                self.history(
                    ("first-published-commit", self.catalog),
                    ("later-published-commit", conflicting),
                ),
            )

    def test_new_document_and_set_versions_can_change(self) -> None:
        current = copy.deepcopy(self.catalog)
        current["document_set_version"] = "0.1.0-draft.2"
        current["documents"][0]["version"] = "0.1.0-draft.2"
        current["documents"][0]["source_sha256"] = "0" * 64
        current["aggregate"]["sha256"] = "0" * 64
        validate_catalog_history(
            current,
            self.history(("published-commit", self.catalog)),
        )

    def test_history_comparison_is_json_structural(self) -> None:
        reordered_keys = json.loads(
            json.dumps(self.catalog, ensure_ascii=False, sort_keys=True)
        )
        validate_catalog_history(
            reordered_keys,
            self.history(("published-commit", self.catalog)),
        )

        reordered_array = copy.deepcopy(self.catalog)
        reordered_array["documents"][0]["public_anchors"].reverse()
        with self.assertRaisesRegex(
            PublicationError,
            "published document version",
        ):
            validate_catalog_history(
                reordered_array,
                self.history(("published-commit", self.catalog)),
            )

    def test_shallow_git_history_is_rejected(self) -> None:
        result = mock.Mock(returncode=0, stdout="true\n", stderr="")
        with mock.patch("publication.check._run_git", return_value=result):
            with self.assertRaisesRegex(
                PublicationError,
                "requires a complete Git history",
            ):
                _historical_catalogs(ROOT, "origin/main")

    def test_git_history_rejects_changed_bytes_under_published_version(self) -> None:
        root, path = self.catalog_copy()
        for arguments in (
            ("init", "--quiet"),
            ("config", "user.name", "Publication Test"),
            ("config", "user.email", "publication-test@example.invalid"),
            ("add", "."),
            ("commit", "--quiet", "-m", "Published baseline"),
        ):
            subprocess.run(
                ["git", *arguments],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
        baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        source = root / self.catalog["documents"][0]["source_path"]
        source.write_text(
            source.read_text(encoding="utf-8") + "\n<!-- changed bytes -->\n",
            encoding="utf-8",
        )
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        catalog = copy.deepcopy(self.catalog)
        catalog["documents"][0]["source_sha256"] = digest
        self.write_catalog(path, catalog)

        with self.assertRaisesRegex(
            PublicationError,
            "published document version.*bump document version",
        ):
            validate_history(root, baseline)

    def test_explicit_anchor_inventory_is_bound_to_source(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["documents"][0]["public_anchors"][0][
            "heading"
        ] = "Different Heading"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "public anchor inventory"):
            validate_catalog(root)

    def test_alternate_valid_html_anchor_syntax_is_detected(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / "source.md"
        source.write_text(
            "  <A class='legacy' ID=example-anchor></A>  \n"
            "## Example Heading\n",
            encoding="utf-8",
        )
        self.assertEqual(
            _explicit_anchors(source),
            {"example-anchor": "Example Heading"},
        )

    def test_non_html_less_than_prose_is_not_an_anchor(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / "source.md"
        source.write_text(
            "The value is < a threshold, not an HTML anchor.\n",
            encoding="utf-8",
        )
        self.assertEqual(_explicit_anchors(source), {})

    def test_malformed_or_ambiguous_html_anchor_is_rejected(self) -> None:
        variants = (
            "prefix <a id='example-anchor'></a>",
            "<a id='example-anchor'></a junk>",
            "<a id='example-anchor'/>",
            "<a id='example-anchor'>text</a>",
            "<a id='example-anchor'><span></span></a>",
            "<a id='example-anchor' id='other-anchor'></a>",
            "<a class='missing-id'></a>",
            "<a\n id='example-anchor'></a>",
        )
        for line in variants:
            with self.subTest(line=line):
                temporary = tempfile.TemporaryDirectory()
                self.addCleanup(temporary.cleanup)
                source = Path(temporary.name) / "source.md"
                source.write_text(
                    f"{line}\n## Example Heading\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    PublicationError,
                    "malformed explicit anchor.*line 1",
                ):
                    _explicit_anchors(source)

    def test_alternate_html_anchor_duplicate_is_rejected(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / "source.md"
        source.write_text(
            "<a id='same-anchor'></a>\n"
            "# First\n"
            "  <A class=legacy ID=same-anchor></A>\n"
            "# Second\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(PublicationError, "duplicate explicit anchor"):
            _explicit_anchors(source)

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
        catalog["documents"][0]["source_path"] = "../outside.md"
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
                catalog["documents"][0]["source_path"] = value
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
        catalog["documents"][0]["source_path"] = "drafts/escape/core.md"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "escapes the repository"):
            validate_catalog(root)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_dangling_active_symlink_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        target = root / "drafts" / "dangling-core.md"
        target.symlink_to(root / "drafts" / "missing-core.md")
        catalog = copy.deepcopy(self.catalog)
        catalog["documents"][0]["source_path"] = "drafts/dangling-core.md"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "regular file"):
            validate_catalog(root)

    def test_partial_modular_activation_is_rejected(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["reserved_documents"] = [
            {
                "document_id": "https://github.com/0al-spec/agent-surface/documents/future",
                "version": "0.1.0-draft.1",
                "title": "Future Module",
                "kind": "extension",
                "role": "privacy",
                "status": "reserved",
                "publication_order": 0,
                "target_source_path": "drafts/modules/future.md",
                "normative_dependencies": [],
                "planned_exports": [],
                "activation_condition": "atomic_catalog_transition",
            }
        ]
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "schema violation"):
            validate_catalog(root)

    def test_modular_mode_requires_complete_assembly(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        del catalog["aggregate"]["assembly"]
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "schema violation"):
            validate_catalog(root)

    def test_modular_mode_rejects_non_authoritative_entrypoint(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["aggregate"]["assembly"][
            "entrypoint"
        ] = "publication/document-set.json"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "authoritative entrypoint"):
            validate_catalog(root)

    def test_relocation_target_must_resolve(self) -> None:
        root, path = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        catalog["anchor_relocations"][0]["replacement"][
            "anchor_id"
        ] = "missing-anchor"
        self.write_catalog(path, catalog)
        with self.assertRaisesRegex(PublicationError, "does not resolve"):
            validate_catalog(root)

    def test_authoritative_modular_build_is_current(self) -> None:
        modular.check(
            ROOT,
            ROOT / ".tools" / "hyperprompt" / "hyperprompt",
        )

    def test_modular_build_rejects_stale_sidecar(self) -> None:
        root, _ = self.catalog_copy()
        catalog = copy.deepcopy(self.catalog)
        aggregate = catalog["aggregate"]
        artifacts = (
            (root / aggregate["path"]).read_bytes(),
            (root / aggregate["assembly"]["manifest"]).read_bytes(),
            (root / aggregate["assembly"]["source_map"]).read_bytes(),
        )
        (root / aggregate["assembly"]["manifest"]).write_bytes(
            artifacts[1] + b"\n"
        )
        with (
            mock.patch.object(
                modular,
                "_verify_compiler",
                return_value=aggregate["assembly"]["compiler_revision"],
            ),
            mock.patch.object(modular, "_compile", return_value=artifacts),
            self.assertRaisesRegex(
                modular.ModularBuildError,
                "aggregate, manifest, or source map is stale",
            ),
        ):
            modular.check(root, root / "unused-compiler")

    def test_modular_build_rejects_source_map_gap(self) -> None:
        root, _ = self.catalog_copy()
        aggregate = self.catalog["aggregate"]
        output = (root / aggregate["path"]).read_bytes()
        manifest = (root / aggregate["assembly"]["manifest"]).read_bytes()
        source_map_path = root / aggregate["assembly"]["source_map"]
        source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
        source_map["mappings"][1]["generatedLine"] = 3
        encoded_source_map = (
            json.dumps(source_map, indent=2, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        source_map_path.write_bytes(encoded_source_map)
        artifacts = output, manifest, encoded_source_map
        with (
            mock.patch.object(
                modular,
                "_verify_compiler",
                return_value=aggregate["assembly"]["compiler_revision"],
            ),
            mock.patch.object(modular, "_compile", return_value=artifacts),
            self.assertRaisesRegex(
                modular.ModularBuildError,
                "coverage is not contiguous",
            ),
        ):
            modular.check(root, root / "unused-compiler")


if __name__ == "__main__":
    unittest.main()
