#!/usr/bin/env python3
"""Measure the pinned existing export operation with disposable synthetic data.

This is an adoption probe, not an ASP implementation or conformance runner.
The supplied checkout is trusted executable code; only use the reviewed pin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

REVISION = "567d5e39aecb83b9879a07cfab2c6f7062a98a20"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, timeout=10
    ).strip()


def snapshot(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def run(checkout: Path) -> dict:
    if git(checkout, "rev-parse", "HEAD") != REVISION:
        raise ValueError("ContextBuilder revision does not match experiment pin")
    if git(checkout, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Use a clean isolated ContextBuilder checkout")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(checkout))
    from viewer import export, graph, workspace_io

    for module in (export, graph, workspace_io):
        if not Path(module.__file__).resolve().is_relative_to(checkout):
            raise ValueError("Imported module is outside pinned checkout")

    with tempfile.TemporaryDirectory(prefix="asp-adoption-") as temporary:
        root = Path(temporary).resolve()
        source = root / "synthetic.json"
        fixture = {
            "conversation_id": "adoption-synthetic",
            "title": "Synthetic adoption experiment",
            "messages": [{"message_id": "message-1", "role": "user",
                          "content": "Export this synthetic note."}],
            "lineage": {"parents": []},
        }
        source.write_text(json.dumps(fixture), encoding="utf-8")

        def listing(directory):
            return workspace_io.build_workspace_listing(
                directory, load_json_file=workspace_io.load_json_file
            )

        def invoke():
            return export.export_graph_nodes(
                root, "adoption-synthetic",
                collect_workspace_listing=listing,
                build_graph_indexes=graph.build_graph_indexes,
                build_compile_target=graph.build_compile_target,
                export_sentinel=".ctxb_export",
            )

        started = time.perf_counter()
        nodes = listing(root)["graph"]["nodes"]
        read_seconds = time.perf_counter() - started
        require(len(nodes) == 1, "Expected one synthetic graph node")
        started = time.perf_counter()
        status, response = invoke()
        export_seconds = time.perf_counter() - started
        require(status == 200, f"Initial export failed: {response}")
        destination = Path(response["export_dir"])
        require(destination.resolve().is_relative_to(root), "Export escaped temporary root")
        before = snapshot(destination)
        require(response["node_count"] == 1, "Unexpected exported node count")
        require(len(before) > 1, "Expected multi-file export")

        # Replay produces equal bytes but still deletes and rewrites output.
        with patch.object(export.shutil, "rmtree", wraps=export.shutil.rmtree) as remove:
            require(invoke()[0] == 200, "Repeat export failed")
            rewrite_calls = remove.call_count
        same_bytes = before == snapshot(destination)
        require(same_bytes and rewrite_calls == 1, "Repeat behavior changed")

        # Existing ownership safeguard, preserved in the comparison.
        sentinel = destination / ".ctxb_export"
        sentinel.unlink()
        unowned_before = snapshot(destination)
        denied_status, _ = invoke()
        require(denied_status == 500, "Expected missing-sentinel rejection")
        require(snapshot(destination) == unowned_before, "Unowned output was changed")
        sentinel.write_text("Synthetic owned directory\n", encoding="utf-8")

        # A stale source changes exported bytes; no preview token is accepted.
        fixture["messages"][0]["content"] = "Changed after hypothetical preview."
        source.write_text(json.dumps(fixture), encoding="utf-8")
        require(invoke()[0] == 200, "Changed-source export failed")
        changed_source_changes_output = snapshot(destination) != before
        require(changed_source_changes_output, "Expected changed-source output")
        complete = snapshot(destination)

        # Deterministic I/O failure after deletion demonstrates partial effects.
        original_write = Path.write_text

        def fail_node_write(path, *args, **kwargs):
            if path.suffix == ".md" and "nodes" in path.parts:
                raise OSError("synthetic node write failure")
            return original_write(path, *args, **kwargs)

        with patch.object(Path, "write_text", fail_node_write):
            try:
                invoke()
            except OSError:
                pass
            else:
                raise AssertionError("Injected export failure did not occur")
        after_failure = snapshot(destination)
        require(after_failure != complete, "Expected incomplete export after injected failure")
        require(not any(name.endswith(".md") for name in after_failure),
                "Unexpected Markdown after injected failure")

        return {
            "experiment": "contextbuilder-adoption-baseline",
            "revision": REVISION,
            "scope": "direct application operation; HTTP and ASP not tested",
            "synthetic_only": True,
            "read_node_count": len(nodes),
            "export_file_count": len(before),
            "exported_files": sorted(before),
            "read_seconds": read_seconds,
            "export_seconds": export_seconds,
            "repeat_equal_bytes": same_bytes,
            "repeat_directory_deletions": rewrite_calls,
            "missing_sentinel_rejected_without_mutation": True,
            "changed_source_changes_export": changed_source_changes_output,
            "injected_failure_loses_previous_complete_export": True,
            "files_after_injected_failure": sorted(after_failure),
            "asp_conformance": "not_evaluated",
            "human_approval": "not_evaluated",
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.checkout.resolve()), indent=2))
