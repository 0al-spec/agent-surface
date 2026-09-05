#!/usr/bin/env python3
"""Probe an existing draft save, not an ASP adapter. Trusted clean checkout only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from baseline import REVISION, git, require, snapshot


def run(checkout: Path) -> dict:
    require(git(checkout, "rev-parse", "HEAD") == REVISION, "Wrong experiment pin")
    require(not git(checkout, "status", "--porcelain", "--untracked-files=all"),
            "Use a clean isolated checkout")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(checkout))
    from viewer import real_idea_entry_requests as entry
    from viewer import real_idea_intake_execution as intake

    for module in (entry, intake):
        require(Path(module.__file__).resolve().is_relative_to(checkout),
                "Imported module outside checkout")

    with tempfile.TemporaryDirectory(prefix="asp-draft-selection-") as temporary:
        root = Path(temporary).resolve()
        server = SimpleNamespace(repo_root=root, specspace_state_dir=root)
        payload = {"workspace_id": "adoption-synthetic", "request_id": "draft-1",
                   "status": "draft", "idea_text": "Synthetic team decision log."}

        def save(body):
            return entry.save_request(server, body, workspace_id="adoption-synthetic")

        with patch.object(entry, "now_iso", return_value="2026-09-05T00:00:00Z"):
            status, first = save(payload)
        require(status == 200, "Draft save failed")
        require(len(first["requests"]) == 1, "Unexpected request count")
        require(first["requests"][0]["status"] == "draft", "Draft became submitted")
        require(first["summary"]["active_submitted_count"] == 0,
                "Draft counts as submitted")
        before = snapshot(root)
        require(list(before) == [entry.ENTRY_REQUEST_FILENAME], "Unexpected file effects")

        # Exercise only the existing read-only admission helper, never execute intake.
        error = intake._entry_request_error(
            server, selected_workspace_id="adoption-synthetic", entry_request_id="draft-1"
        )
        require(error is not None, "Draft passed submitted-entry admission")
        require(snapshot(root) == before, "Admission helper changed state")

        with patch.object(entry, "now_iso", return_value="2026-09-05T00:00:01Z"):
            status, repeat = save(payload)
        require(status == 200 and len(repeat["requests"]) == 1, "Unexpected repeat result")
        require(repeat["requests"][0]["request_id"] == "draft-1", "Identity changed")
        require(repeat["requests"][0]["created_at"] != first["requests"][0]["created_at"],
                "Expected existing timestamp rewrite behavior")
        require(snapshot(root) != before, "Expected non-exact retry")
        after_repeat = snapshot(root)

        status, _ = save({**payload, "workspace_id": "another-workspace"})
        require(status == 409 and snapshot(root) == after_repeat,
                "Workspace mismatch was not rejected without mutation")
        status, _ = save({**payload, "may_execute_specgraph": True})
        require(status == 400 and snapshot(root) == after_repeat,
                "Authority expansion was not rejected without mutation")

        # One-record upsert is not create-only or replay conflict protection.
        status, changed = save({**payload, "idea_text": "A different synthetic idea."})
        require(status == 200 and len(changed["requests"]) == 1,
                "Expected existing same-ID update semantics")
        require(changed["requests"][0]["idea_text"] != payload["idea_text"],
                "Expected changed input to replace draft")

        return {
            "experiment": "contextbuilder-draft-selection",
            "revision": REVISION,
            "scope": "synthetic direct operation; file backend; no HTTP or execution",
            "files_after_save": sorted(before),
            "draft_rejected_by_submitted_entry_gate": True,
            "same_id_keeps_one_row": True,
            "same_id_repeat_rewrites_timestamp_and_bytes": True,
            "same_id_different_input_updates_existing_draft": True,
            "workspace_mismatch_rejected_without_mutation": True,
            "authority_expansion_rejected_without_mutation": True,
            "asp_conformance": "not_evaluated",
            "human_approval": "not_evaluated",
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.checkout.resolve()), indent=2))
