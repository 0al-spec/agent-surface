#!/usr/bin/env python3
"""Deterministic local test agent. Receives no Grant or app credentials."""
import base64
from pathlib import Path
import subprocess
import sys
import tempfile

from runtime import canonical, loads


def main():
    value = loads(sys.stdin.buffer.read(65537))
    if set(value) != {"challenge", "read_output", "text", "request_id"}:
        raise ValueError("Unexpected agent input")
    read = value["read_output"]
    proposal = {"workspace_id": read["workspace_id"], "snapshot_hash": read["snapshot_hash"],
                "request_id": value["request_id"], "idea_text": value["text"]}
    with tempfile.TemporaryDirectory(prefix="asp-agent-proof-") as directory:
        challenge, sig = Path(directory) / "challenge", Path(directory) / "signature"
        challenge.write_bytes(canonical({"challenge": value["challenge"], "input": proposal}))
        subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", sys.argv[1],
                        "-in", str(challenge), "-out", str(sig)], check=True, capture_output=True, timeout=5)
        sys.stdout.buffer.write(canonical({"input": proposal, "signature": base64.b64encode(sig.read_bytes()).decode()}))


if __name__ == "__main__":
    main()
