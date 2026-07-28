from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from publication.assembly.check import (
    AssemblyError,
    LOCK_PATH,
    _artifact_for_platform,
    _expected_candidate_evidence_set,
    _sha256_file,
    compare_platform_reports,
    require_clean_checkout,
    validate_cross_platform_report_data,
    validate_lock,
    validate_platform_report_data,
)


ROOT = Path(__file__).resolve().parents[3]
SOURCE_REVISION = "a" * 40
PLATFORMS = ("linux-amd64", "macos-arm64")


class CrossPlatformEvidenceTests(unittest.TestCase):
    @staticmethod
    def write_json(path: Path, value: dict) -> None:
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def platform_report(platform: str) -> dict:
        lock = validate_lock(ROOT)
        artifact = _artifact_for_platform(lock, platform)
        return {
            "$schema": (
                "https://github.com/0al-spec/agent-surface/publication/"
                "schemas/assembly-platform-report/v1"
            ),
            "schema_version": 1,
            "report_kind": "asp_rfc_assembly_platform",
            "authority": "provenance_only",
            "source_revision": SOURCE_REVISION,
            "checkout": "clean_before_and_after",
            "platform": platform,
            "toolchain": {
                "version": lock["release"]["version"],
                "release_commit": lock["release"]["commit"],
                "lock_sha256": _sha256_file(ROOT / LOCK_PATH),
                "binary_sha256": artifact["binary_sha256"],
            },
            "candidates": _expected_candidate_evidence_set(ROOT),
            "repetitions": 2,
            "result": "reproducible",
        }

    def test_platform_reports_bind_exact_repository_and_toolchain(self) -> None:
        for platform in PLATFORMS:
            with self.subTest(platform=platform):
                report = self.platform_report(platform)
                self.assertIs(
                    validate_platform_report_data(
                        ROOT,
                        report,
                        expected_source_revision=SOURCE_REVISION,
                    ),
                    report,
                )

    def test_cross_platform_comparison_emits_valid_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            paths: list[Path] = []
            for platform in PLATFORMS:
                path = directory / f"{platform}.json"
                self.write_json(path, self.platform_report(platform))
                paths.append(path)
            output = directory / "cross-platform.json"
            report = compare_platform_reports(
                ROOT,
                paths,
                source_revision=SOURCE_REVISION,
                output_path=output,
            )
            self.assertEqual(report["result"], "cross_platform_reproducible")
            self.assertEqual(report["platforms"], list(PLATFORMS))
            self.assertEqual(
                report["platform_report_sha256"],
                {
                    platform: hashlib.sha256(path.read_bytes()).hexdigest()
                    for platform, path in zip(PLATFORMS, paths, strict=True)
                },
            )
            validate_cross_platform_report_data(
                ROOT,
                json.loads(output.read_text(encoding="utf-8")),
                expected_source_revision=SOURCE_REVISION,
            )

    def test_cross_platform_comparison_rejects_tampering_and_incomplete_matrix(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            linux_path = directory / "linux.json"
            macos_path = directory / "macos.json"
            self.write_json(linux_path, self.platform_report("linux-amd64"))
            tampered = copy.deepcopy(self.platform_report("macos-arm64"))
            tampered["candidates"][0]["manifest_sha256"] = "0" * 64
            self.write_json(macos_path, tampered)

            with self.assertRaisesRegex(AssemblyError, "do not match the repository"):
                compare_platform_reports(
                    ROOT,
                    [linux_path, macos_path],
                    source_revision=SOURCE_REVISION,
                    output_path=directory / "tampered-output.json",
                )
            with self.assertRaisesRegex(AssemblyError, "exactly two reports"):
                compare_platform_reports(
                    ROOT,
                    [linux_path],
                    source_revision=SOURCE_REVISION,
                    output_path=directory / "incomplete-output.json",
                )

    def test_clean_checkout_binding_rejects_revision_and_worktree_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Fixture"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "config",
                    "user.email",
                    "fixture@example.invalid",
                ],
                check=True,
            )
            fixture = root / "fixture.txt"
            fixture.write_text("clean\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "fixture.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "Create fixture"],
                check=True,
            )
            revision = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            require_clean_checkout(root, revision)

            with self.assertRaisesRegex(AssemblyError, "revision mismatch"):
                require_clean_checkout(root, "0" * 40)
            fixture.write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(AssemblyError, "clean Git worktree"):
                require_clean_checkout(root, revision)
