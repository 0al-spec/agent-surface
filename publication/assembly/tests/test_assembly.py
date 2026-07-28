from __future__ import annotations

import hashlib
import io
import json
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path

from publication.assembly.check import (
    AssemblyError,
    disposable_staging,
    materialize_candidate,
    require_empty_staging,
    validate_candidate,
    validate_lock,
    validate_repository,
    verify_archive,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LOCK_FILES = (
    "hyperprompt.lock.json",
    "hyperprompt.lock.schema.json",
    "candidate.schema.json",
)


class AssemblyFoundationTests(unittest.TestCase):
    def fixture_root(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(FIXTURES / "abstract", root, dirs_exist_ok=True)
        assembly = root / "publication" / "assembly"
        assembly.mkdir(parents=True)
        for name in LOCK_FILES:
            shutil.copy2(ROOT / "publication" / "assembly" / name, assembly / name)
        return root

    @staticmethod
    def candidate_path(root: Path) -> Path:
        return root / "publication" / "candidates" / "abstract-pilot" / "candidate.json"

    @staticmethod
    def read_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path: Path, value: dict) -> None:
        path.write_text(
            json.dumps(value, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )

    def test_repository_foundation_and_exact_release_lock_are_valid(self) -> None:
        self.assertIsInstance(validate_repository(ROOT), list)
        lock = validate_lock(ROOT)
        self.assertEqual(lock["release"]["version"], "0.2.0")
        self.assertEqual(lock["release"]["tag"], "v0.2.0")
        self.assertEqual(
            lock["release"]["commit"],
            "d76e0a057c44fd249cf4f62fe856bf6054b1c264",
        )
        self.assertEqual(
            {artifact["platform"] for artifact in lock["artifacts"]},
            {"linux-amd64", "macos-arm64"},
        )

    def test_abstract_positive_candidate_is_valid_and_materializes(self) -> None:
        root = self.fixture_root()
        candidate_path = self.candidate_path(root)
        candidate = validate_candidate(root, candidate_path)
        self.assertEqual(candidate["authority"], "non_authoritative")

        stage_path: Path | None = None
        with disposable_staging() as staging:
            stage_path = staging
            materialize_candidate(root, candidate_path, staging)
            actual = sorted(
                path.relative_to(staging).as_posix()
                for path in staging.rglob("*")
                if path.is_file()
            )
            self.assertEqual(actual, ["root.hc", "sections/module.md"])
            self.assertEqual(
                (staging / "sections" / "module.md").read_text(encoding="utf-8"),
                "## Fixture Module\n\nThe fixture remains non-authoritative.\n",
            )
        self.assertIsNotNone(stage_path)
        self.assertFalse(stage_path.exists())

    def test_canonical_byte_range_source_is_validated_and_materialized(self) -> None:
        root = self.fixture_root()
        candidate_path = self.candidate_path(root)
        candidate = self.read_json(candidate_path)
        canonical = (root / "drafts" / "agent-surface.md").read_bytes()
        end = canonical.index(b"\n") + 1
        fragment = canonical[:end]
        candidate["sources"]["declared"].append(
            {
                "path": "fragments/title.md",
                "media_type": "markdown",
                "origin": "derived_canonical",
                "sha256": hashlib.sha256(fragment).hexdigest(),
                "extraction": {
                    "method": "byte_range",
                    "source_path": "drafts/agent-surface.md",
                    "start_byte": 0,
                    "end_byte": end,
                },
            }
        )
        self.write_json(candidate_path, candidate)

        with disposable_staging() as staging:
            materialize_candidate(root, candidate_path, staging)
            self.assertEqual(
                (staging / "fragments" / "title.md").read_bytes(), fragment
            )

    def test_data_driven_negative_candidates_fail_closed(self) -> None:
        cases = self.read_json(FIXTURES / "negative-cases.json")["cases"]
        for case in cases:
            with self.subTest(case=case["name"]):
                root = self.fixture_root()
                path = self.candidate_path(root)
                candidate = self.read_json(path)
                operation = case["operation"]

                if operation == "replace_lock_digest":
                    candidate["compiler"]["lock_sha256"] = "0" * 64
                    self.write_json(path, candidate)
                elif operation == "add_undeclared_source":
                    (path.parent / "sources" / "unexpected.md").write_text(
                        "undeclared\n",
                        encoding="utf-8",
                    )
                elif operation == "add_file_outside_source_root":
                    (path.parent / "stale-output.md").write_text(
                        "stale candidate output\n",
                        encoding="utf-8",
                    )
                elif operation == "replace_staged_path_with_traversal":
                    candidate["sources"]["declared"][0]["path"] = "../root.hc"
                    self.write_json(path, candidate)
                elif operation == "modify_canonical_source":
                    (root / "drafts" / "agent-surface.md").write_text(
                        "# Drifted protocol\n",
                        encoding="utf-8",
                    )
                elif operation == "collide_output_with_entrypoint":
                    candidate["assembly"]["output"] = "root.hc"
                    self.write_json(path, candidate)
                else:
                    self.fail(f"unknown negative fixture operation: {operation}")

                with self.assertRaisesRegex(AssemblyError, case["expected_error"]):
                    validate_candidate(root, path)

    def test_duplicate_candidate_member_is_rejected(self) -> None:
        root = self.fixture_root()
        path = self.candidate_path(root)
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace(
                '"schema_version": 1,',
                '"schema_version": 1,\n  "schema_version": 1,',
                1,
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(AssemblyError, "duplicate JSON object member"):
            validate_candidate(root, path)

    def test_dirty_staging_is_rejected_and_disposable_staging_always_cleans_up(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            dirty = Path(temporary) / "dirty"
            dirty.mkdir()
            (dirty / "partial.manifest.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(AssemblyError, "not empty"):
                require_empty_staging(dirty)

            stage_path: Path | None = None
            with self.assertRaisesRegex(RuntimeError, "simulated compiler failure"):
                with disposable_staging(Path(temporary)) as staging:
                    stage_path = staging
                    (staging / "partial.map.json").write_text("{}\n", encoding="utf-8")
                    raise RuntimeError("simulated compiler failure")
            self.assertIsNotNone(stage_path)
            self.assertFalse(stage_path.exists())

    def test_locked_archive_and_embedded_provenance_are_verified(self) -> None:
        root = self.fixture_root()
        lock_path = root / "publication" / "assembly" / "hyperprompt.lock.json"
        lock = self.read_json(lock_path)
        artifact = next(
            item for item in lock["artifacts"] if item["platform"] == "macos-arm64"
        )
        metadata = {
            "artifact_kind": "hyperprompt_release_binary",
            "schema_version": 1,
            "binary": "hyperprompt",
            "compiler_version": lock["release"]["version"],
            "os": artifact["os"],
            "arch": artifact["arch"],
            "linkage": artifact["linkage"],
            "source_repository": "0al-spec/Hyperprompt",
            "source_commit": lock["release"]["commit"],
            "source_tag": lock["release"]["tag"],
            "workflow_run_id": "123456",
        }

        archive_path = root / artifact["asset"]
        members = {
            "hyperprompt": (b"fixture binary\n", 0o755),
            "README.md": (b"fixture readme\n", 0o644),
            "LICENSE": (b"MIT fixture\n", 0o644),
            "hyperprompt-artifact.json": (
                (json.dumps(metadata, sort_keys=True) + "\n").encode("utf-8"),
                0o644,
            ),
        }
        with tarfile.open(archive_path, mode="w:gz") as archive:
            root_info = tarfile.TarInfo(artifact["archive_root"])
            root_info.type = tarfile.DIRTYPE
            root_info.mode = 0o755
            archive.addfile(root_info)
            for name, (content, mode) in members.items():
                info = tarfile.TarInfo(f"{artifact['archive_root']}/{name}")
                info.size = len(content)
                info.mode = mode
                archive.addfile(info, io.BytesIO(content))

        artifact["sha256"] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        self.write_json(lock_path, lock)
        verify_archive(archive_path, "macos-arm64", root=root)

        archive_path.write_bytes(archive_path.read_bytes() + b"corruption")
        with self.assertRaisesRegex(AssemblyError, "archive digest mismatch"):
            verify_archive(archive_path, "macos-arm64", root=root)


if __name__ == "__main__":
    unittest.main()
