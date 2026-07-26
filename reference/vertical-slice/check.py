#!/usr/bin/env python3
"""Build, run, and verify the independent ASP reference vertical slice."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from build_support import application_target_dir


HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[1]
MANIFEST_RELATIVE = Path("reference/vertical-slice/v1/manifest.json")
SCHEMA_RELATIVE = Path("reference/vertical-slice/v1/manifest.schema.json")
EVIDENCE_SCHEMA_RELATIVE = Path(
    "reference/vertical-slice/v1/evidence.schema.json"
)
BUNDLE_ID = (
    "https://github.com/0al-spec/agent-surface/conformance/"
    "bundles/application-audited-effects/v1"
)
ADAPTER_RELATIVE = Path("reference/vertical-slice/harness/adapter.py")
PROBE_RELATIVE = Path("reference/vertical-slice/harness/probe.py")
BUILD_SUPPORT_RELATIVE = Path("reference/vertical-slice/build_support.py")
APP_PACKAGE = "asp-reference-vertical-app"
DIGEST_PATTERN_PREFIX = "sha-256:"
EXPECTED_HARNESS_ARTIFACTS = sorted(
    path.as_posix()
    for path in (ADAPTER_RELATIVE, BUILD_SUPPORT_RELATIVE, PROBE_RELATIVE)
)
EXPECTED_PARTICIPANT_BINDINGS = {
    "reference-app-control": {
        "participant_kind": "application",
        "claim_role": "canonical_claim_subject",
        "entrypoint": {
            "kind": "cargo_binary",
            "name": "asp-reference-app-control",
            "path": "reference/vertical-slice/app/src/bin/app_control.rs",
        },
        "profiles": [
            {
                "profile_id": "https://github.com/0al-spec/agent-surface/conformance/surface-publisher/v1"
            },
            {
                "profile_id": "https://github.com/0al-spec/agent-surface/conformance/grant-issuer/v1"
            },
        ],
    },
    "reference-app-executor": {
        "participant_kind": "application",
        "claim_role": "canonical_claim_subject",
        "entrypoint": {
            "kind": "cargo_binary",
            "name": "asp-reference-app-executor",
            "path": "reference/vertical-slice/app/src/bin/app_executor.rs",
        },
        "profiles": [
            {
                "profile_id": "https://github.com/0al-spec/agent-surface/conformance/action-executor/v1"
            }
        ],
    },
    "reference-app-receipt": {
        "participant_kind": "application",
        "claim_role": "canonical_claim_subject",
        "entrypoint": {
            "kind": "cargo_binary",
            "name": "asp-reference-app-receipt",
            "path": "reference/vertical-slice/app/src/bin/app_receipt.rs",
        },
        "profiles": [
            {
                "profile_id": "https://github.com/0al-spec/agent-surface/conformance/receipt-producer/v1",
                "producer_role": "application",
            }
        ],
    },
    "reference-runtime-local": {
        "participant_kind": "runtime",
        "claim_role": "canonical_claim_subject",
        "entrypoint": {
            "kind": "python_script",
            "name": "reference-runtime-local",
            "path": "reference/vertical-slice/runtime_local.py",
        },
        "profiles": [
            {
                "profile_id": "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1"
            }
        ],
    },
    "reference-runtime-remote": {
        "participant_kind": "runtime",
        "claim_role": "additional_tested_participant",
        "entrypoint": {
            "kind": "python_script",
            "name": "reference-runtime-remote",
            "path": "reference/vertical-slice/runtime_remote.py",
        },
        "profiles": [
            {
                "profile_id": "https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1"
            }
        ],
    },
    "reference-agent-a": {
        "participant_kind": "agent",
        "claim_role": "canonical_claim_subject",
        "entrypoint": {
            "kind": "python_script",
            "name": "reference-agent-a",
            "path": "reference/vertical-slice/agent_a.py",
        },
        "profiles": [
            {
                "profile_id": "https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1"
            }
        ],
    },
    "reference-agent-b": {
        "participant_kind": "agent",
        "claim_role": "additional_tested_participant",
        "entrypoint": {
            "kind": "python_script",
            "name": "reference-agent-b",
            "path": "reference/vertical-slice/agent_b.py",
        },
        "profiles": [
            {
                "profile_id": "https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1"
            }
        ],
    },
}


class SliceError(ValueError):
    """Raised when retained or generated slice evidence is invalid."""


def strict_object(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise SliceError(f"{path}: duplicate JSON member {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                SliceError(f"{path}: non-I-JSON number {token}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SliceError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise SliceError(f"{path}: top-level value must be an object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def domain_digest(domain: str, content: bytes) -> str:
    digest = hashlib.sha256(domain.encode("ascii") + b"\0" + content).digest()
    return DIGEST_PATTERN_PREFIX + base64.urlsafe_b64encode(digest).rstrip(b"=").decode(
        "ascii"
    )


def repository_file(root: Path, relative: str | Path) -> Path:
    root = root.resolve()
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SliceError(f"repository path escapes the root: {relative}")
    try:
        resolved = (root / candidate).resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise SliceError(f"repository file is unavailable: {relative}") from error
    if not resolved.is_file() or resolved.is_symlink():
        raise SliceError(f"repository evidence must be a regular non-symlink file: {relative}")
    return resolved


def artifact_digest(root: Path, paths: list[str]) -> str:
    if not paths or paths != sorted(set(paths)):
        raise SliceError("artifact_paths must be non-empty, unique, and sorted")
    payload = bytearray()
    for relative in paths:
        if relative.startswith(("mocks/", "conformance/tests/", "target/")):
            raise SliceError(f"fixtures and build outputs cannot be implementation artifacts: {relative}")
        path = repository_file(root, relative)
        encoded = Path(relative).as_posix().encode("utf-8")
        payload.extend(encoded)
        payload.extend(b"\0")
        payload.extend(path.read_bytes())
        payload.extend(b"\0")
    return domain_digest("ASP-REFERENCE-ARTIFACT-V1", bytes(payload))


def configuration_digest(config: dict[str, Any]) -> str:
    return domain_digest("ASP-REFERENCE-CONFIGURATION-V1", canonical_bytes(config))


def validate_suite_binding(
    manifest: dict[str, Any], suite: dict[str, Any]
) -> None:
    for member in ("suite_id", "suite_version", "protocol_version"):
        if manifest[member] != suite.get(member):
            raise SliceError(
                f"vertical-slice manifest {member} does not match the canonical suite"
            )


def validate_participant_bindings(
    manifest: dict[str, Any],
    participant_configs: dict[str, dict[str, Any]],
) -> None:
    if set(participant_configs) != set(EXPECTED_PARTICIPANT_BINDINGS):
        raise SliceError("participant inventory is not the exact card #74 topology")

    claims_by_participant: dict[str, list[dict[str, str]]] = {
        participant_id: [] for participant_id in participant_configs
    }
    for claim in manifest["claim_selection"]:
        binding = {"profile_id": claim["profile_id"]}
        if "producer_role" in claim:
            binding["producer_role"] = claim["producer_role"]
        claims_by_participant[claim["participant_id"]].append(binding)

    lanes_by_participant: dict[str, list[str]] = {
        participant_id: [] for participant_id in participant_configs
    }
    for lane in manifest["lanes"]:
        members = [
            lane["runtime_participant_id"],
            lane["agent_participant_id"],
            *lane["application_participant_ids"],
        ]
        if len(members) != len(set(members)):
            raise SliceError(f"lane {lane['lane_id']} contains a duplicate participant")
        for participant_id in members:
            lanes_by_participant[participant_id].append(lane["lane_id"])

    for participant_id, config in participant_configs.items():
        expected = EXPECTED_PARTICIPANT_BINDINGS[participant_id]
        for member in ("participant_kind", "claim_role", "entrypoint", "profiles"):
            if config[member] != expected[member]:
                raise SliceError(
                    f"participant {participant_id} {member} differs from its executable binding"
                )
        artifact_paths = config["implementation"]["artifact_paths"]
        if config["entrypoint"]["path"] not in artifact_paths:
            raise SliceError(
                f"participant {participant_id} entrypoint is absent from its artifact closure"
            )
        if config["entrypoint"]["kind"] == "cargo_binary":
            required_rust_artifacts = {
                "Cargo.lock",
                "Cargo.toml",
                "reference/vertical-slice/app/Cargo.toml",
                "reference/vertical-slice/app/src/lib.rs",
                "reference/vertical-slice/app/src/bin/app_server.rs",
                config["entrypoint"]["path"],
            }
            if not required_rust_artifacts.issubset(artifact_paths):
                raise SliceError(
                    f"participant {participant_id} Rust artifact closure is incomplete"
                )
        elif artifact_paths != [config["entrypoint"]["path"]]:
            raise SliceError(
                f"participant {participant_id} Python artifact closure is not exact"
            )
        if config["lane_membership"] != lanes_by_participant[participant_id]:
            raise SliceError(
                f"participant {participant_id} lane membership differs from the manifest"
            )
        claims = claims_by_participant[participant_id]
        if config["claim_role"] == "canonical_claim_subject":
            if claims != config["profiles"]:
                raise SliceError(
                    f"participant {participant_id} claims differ from advertised profiles"
                )
        elif claims:
            raise SliceError(
                f"additional participant {participant_id} cannot satisfy a canonical claim"
            )


def validate_manifest(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest_path = repository_file(root, MANIFEST_RELATIVE)
    schema_path = repository_file(root, SCHEMA_RELATIVE)
    manifest = strict_object(manifest_path)
    schema = strict_object(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    if errors:
        rendered = "; ".join(
            "$"
            + "".join(
                f"[{part}]" if isinstance(part, int) else f".{part}"
                for part in error.absolute_path
            )
            + f": {error.message}"
            for error in errors
        )
        raise SliceError(f"vertical-slice manifest is invalid: {rendered}")
    if manifest["review_id"] != 74 or manifest["bundle_id"] != BUNDLE_ID:
        raise SliceError("vertical-slice manifest is not bound to card #74 and its exact bundle")
    if manifest["independence"] != "not_established":
        raise SliceError("this repository-owned slice must not self-assert independent interop")
    suite = strict_object(repository_file(root, "conformance/v1/suite.json"))
    validate_suite_binding(manifest, suite)
    if manifest["harness"]["artifact_paths"] != EXPECTED_HARNESS_ARTIFACTS:
        raise SliceError("vertical-slice harness artifact closure is not exact")
    artifact_digest(root, manifest["harness"]["artifact_paths"])

    participant_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": schema["$defs"],
        "$ref": "#/$defs/participantConfig",
    }
    participant_validator = Draft202012Validator(participant_schema)
    participant_configs: dict[str, dict[str, Any]] = {}
    for entry in manifest["participants"]:
        config_path = repository_file(root, entry["config_path"])
        config = strict_object(config_path)
        participant_id = entry["participant_id"]
        config_errors = sorted(
            participant_validator.iter_errors(config),
            key=lambda error: tuple(str(item) for item in error.absolute_path),
        )
        if config_errors:
            raise SliceError(
                f"participant config is invalid for {participant_id}: "
                f"{config_errors[0].message}"
            )
        if config.get("participant_id") != participant_id:
            raise SliceError(f"participant config binding differs for {participant_id}")
        if participant_id in participant_configs:
            raise SliceError(f"duplicate participant: {participant_id}")
        participant_configs[participant_id] = config
        artifact_digest(root, config["implementation"]["artifact_paths"])
        configuration_digest(config["config"])

    validate_participant_bindings(manifest, participant_configs)
    local = next(item for item in manifest["lanes"] if item["lane_id"] == "local")
    remote = next(item for item in manifest["lanes"] if item["lane_id"] == "remote")
    if (
        local["runtime_participant_id"] == remote["runtime_participant_id"]
        or local["agent_participant_id"] == remote["agent_participant_id"]
    ):
        raise SliceError("local and remote lanes must use distinct runtime and agent artifacts")
    for left, right in (
        ("reference-runtime-local", "reference-runtime-remote"),
        ("reference-agent-a", "reference-agent-b"),
    ):
        left_config = participant_configs[left]
        right_config = participant_configs[right]
        if (
            artifact_digest(root, left_config["implementation"]["artifact_paths"])
            == artifact_digest(root, right_config["implementation"]["artifact_paths"])
            or left_config["deployment"]["boundary_id"]
            == right_config["deployment"]["boundary_id"]
        ):
            raise SliceError(f"{left} and {right} are not distinct artifacts and boundaries")
    return manifest, participant_configs


def _cargo_command() -> list[str]:
    override = os.environ.get("CARGO")
    if override is not None:
        command = shlex.split(override)
        if not command:
            raise SliceError("CARGO override is empty")
        return command
    cargo = shutil.which("cargo")
    if cargo is None:
        raise SliceError("cargo is unavailable")
    return [cargo]


def build_application(root: Path) -> None:
    environment = dict(os.environ)
    environment["CARGO_TERM_COLOR"] = "never"
    process = subprocess.run(
        [
            *_cargo_command(),
            "build",
            "--quiet",
            "--locked",
            "-p",
            APP_PACKAGE,
            "--target-dir",
            str(application_target_dir(root)),
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise SliceError(f"cannot build reference application: {process.stderr.strip()}")


def _claim_key(claim: dict[str, Any]) -> tuple[str, str | None]:
    return claim["profile_id"], claim.get("producer_role")


def _catalog_modules(root: Path):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from conformance.check import run_suite, validate_catalog, verify_report

    return validate_catalog, run_suite, verify_report


def _subject_for_claim(
    *,
    root: Path,
    claim: dict[str, Any],
    participant_configs: dict[str, dict[str, Any]],
    all_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    participant = participant_configs[claim["participant_id"]]
    implementation = participant["implementation"]
    subject_artifact = artifact_digest(root, implementation["artifact_paths"])
    subject = {
        "schema_version": 1,
        "subject_kind": "implementation",
        "subject_id": claim["participant_id"],
        "boundary_id": participant["deployment"]["boundary_id"],
        "implementation": {
            "name": implementation["name"],
            "version": implementation["version"],
            "artifact_sha256": subject_artifact,
            "configuration_sha256": configuration_digest(participant["config"]),
        },
        "profile_id": claim["profile_id"],
        "protocol_version": "agent-surface/0.1",
        "features": claim["feature_ids"],
        "counterparts": [],
    }
    if "producer_role" in claim:
        subject["producer_role"] = claim["producer_role"]
    for counterpart_claim in all_claims:
        if counterpart_claim is claim:
            continue
        counterpart_participant = participant_configs[counterpart_claim["participant_id"]]
        counterpart_implementation = counterpart_participant["implementation"]
        counterpart = {
            "kind": "implementation",
            "boundary_id": counterpart_participant["deployment"]["boundary_id"],
            "profile_id": counterpart_claim["profile_id"],
            "artifact_sha256": artifact_digest(
                root, counterpart_implementation["artifact_paths"]
            ),
            "configuration_sha256": configuration_digest(
                counterpart_participant["config"]
            ),
        }
        if "producer_role" in counterpart_claim:
            counterpart["producer_role"] = counterpart_claim["producer_role"]
        subject["counterparts"].append(counterpart)
    return subject


def run_conformance(
    root: Path,
    manifest: dict[str, Any],
    participant_configs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    validate_catalog, run_suite, verify_report = _catalog_modules(root)
    catalog = validate_catalog(root)
    validate_suite_binding(manifest, catalog.suite)
    bundle = next(
        (
            item
            for item in catalog.bundles.values()
            if item["bundle_id"] == manifest["bundle_id"]
        ),
        None,
    )
    if bundle is None:
        raise SliceError("selected bundle is absent from the canonical catalog")
    claims = manifest["claim_selection"]
    canonical_by_key = {_claim_key(item): item for item in bundle["claims"]}
    selected_by_key = {_claim_key(item): item for item in claims}
    if set(canonical_by_key) != set(selected_by_key):
        raise SliceError("claim selection is not the exact bundle claim set")
    for key, canonical in canonical_by_key.items():
        selected = selected_by_key[key]
        for member in ("feature_ids", "requirement_ids", "vector_ids"):
            if selected[member] != canonical[member]:
                raise SliceError(f"claim {key} differs from canonical {member}")

    adapter = repository_file(root, ADAPTER_RELATIVE)
    probe = repository_file(root, PROBE_RELATIVE)
    harness_config = manifest["harness"]["config"]
    harness_config_digest = configuration_digest(
        {
            "config": harness_config,
            "artifact_sha256": artifact_digest(
                root, manifest["harness"]["artifact_paths"]
            ),
        }
    )
    reports = []
    for claim in claims:
        subject = _subject_for_claim(
            root=root,
            claim=claim,
            participant_configs=participant_configs,
            all_claims=claims,
        )
        report = run_suite(
            subject=subject,
            adapter=adapter,
            probe=probe,
            adapter_id="asp-reference-vertical-slice-adapter",
            adapter_version="1.0.0",
            adapter_configuration_sha256=harness_config_digest,
            probe_id="asp-reference-vertical-slice-probe",
            probe_version="1.0.0",
            probe_configuration_sha256=harness_config_digest,
            timeout_seconds=10,
            root=root,
        )
        verify_report(report, root=root, catalog=catalog, adapter=adapter, probe=probe)
        if report["summary"]["suite_verdict"] != "pass":
            raise SliceError(
                f"conformance report did not pass for {_claim_key(claim)}"
            )
        if report["applicability"]["applicable_vector_ids"] != claim["vector_ids"]:
            raise SliceError(f"report vector closure differs for {_claim_key(claim)}")
        reports.append(report)
    return reports


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def report_digest(report: dict[str, Any]) -> str:
    return domain_digest("ASP-REFERENCE-REPORT-V1", canonical_bytes(report))


def generate_evidence(
    root: Path,
    output_dir: Path,
    *,
    keep_reports: bool,
) -> dict[str, Any]:
    manifest, participant_configs = validate_manifest(root)
    build_application(root)
    reports = run_conformance(root, manifest, participant_configs)
    from scenario import run_scenario

    scenario_report = run_scenario(root)
    evidence = {
        "$schema": "./evidence.schema.json",
        "schema_version": 1,
        "review_id": 74,
        "claim_effect": "descriptive_only",
        "max_maturity": "implementation_tested",
        "independence": "not_established",
        "bundle_id": BUNDLE_ID,
        "participants": [
            {
                "participant_id": participant_id,
                "boundary_id": config["deployment"]["boundary_id"],
                "lineage_id": config["implementation"]["lineage_id"],
                "artifact_sha256": artifact_digest(
                    root, config["implementation"]["artifact_paths"]
                ),
                "configuration_sha256": configuration_digest(config["config"]),
            }
            for participant_id, config in sorted(participant_configs.items())
        ],
        "reports": [
            {
                "profile_id": report["subject"]["profile_id"],
                **(
                    {"producer_role": report["subject"]["producer_role"]}
                    if "producer_role" in report["subject"]
                    else {}
                ),
                "subject_id": report["subject"]["subject_id"],
                "run_id": report["run_id"],
                "report_sha256": report_digest(report),
                "verdict": report["summary"]["suite_verdict"],
                "positive_count": sum(
                    1
                    for result in report["results"]
                    if result["status"] == "pass"
                    and catalog_vector_polarity(root, result["vector_id"]) == "positive"
                ),
                "negative_count": sum(
                    1
                    for result in report["results"]
                    if result["status"] == "pass"
                    and catalog_vector_polarity(root, result["vector_id"]) == "negative"
                ),
            }
            for report in reports
        ],
        "scenario": scenario_report,
        "non_claims": manifest["non_claims"],
    }
    validate_evidence_schema(root, evidence)
    if keep_reports:
        for report in reports:
            role = report["subject"]["profile_id"].rsplit("/", 2)[-2]
            if "producer_role" in report["subject"]:
                role += f"-{report['subject']['producer_role']}"
            write_json(output_dir / "conformance" / f"{role}.json", report)
        write_json(output_dir / "scenario-report.json", scenario_report)
        write_json(output_dir / "evidence.json", evidence)
    return evidence


def catalog_vector_polarity(root: Path, vector_id: str) -> str:
    vectors = strict_object(root / "conformance" / "v1" / "vectors.json")["vectors"]
    return next(item["polarity"] for item in vectors if item["vector_id"] == vector_id)


def validate_evidence_schema(root: Path, evidence: dict[str, Any]) -> None:
    schema = strict_object(repository_file(root, EVIDENCE_SCHEMA_RELATIVE))
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(evidence))
    if errors:
        raise SliceError(f"generated evidence is invalid: {errors[0].message}")


def validate_evidence(root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="asp-reference-slice-") as directory:
        return generate_evidence(root, Path(directory), keep_reports=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("validate-manifest", "validate-evidence", "run"),
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.expanduser().resolve()
    try:
        if args.command == "validate-manifest":
            validate_manifest(root)
        elif args.command == "validate-evidence":
            validate_evidence(root)
        else:
            if args.output_dir is None:
                raise SliceError("run requires --output-dir")
            output = args.output_dir.expanduser().resolve()
            if output.exists() and any(output.iterdir()):
                raise SliceError("output directory must be absent or empty")
            output.mkdir(parents=True, exist_ok=True)
            generate_evidence(root, output, keep_reports=True)
    except (ValueError, subprocess.SubprocessError) as error:
        print(f"vertical slice: {error}", file=sys.stderr)
        return 2
    print("vertical slice: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
