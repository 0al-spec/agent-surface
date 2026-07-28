# RFC Assembly Foundation

This directory contains the non-authoritative foundation for review backlog
item `#78`. It does not change the publication authority of
`drafts/agent-surface.md`.

## 78A contract

- `hyperprompt.lock.json` pins Hyperprompt `v0.2.0` by annotated tag object,
  source commit, release URLs, platform metadata, and archive SHA-256.
- `candidate.schema.json` defines a closed descriptor for candidate inputs,
  canonical byte-range derivations, output identities, and byte-identical
  expectations.
- `check.py` validates the lock, declared candidate input inventory, repository
  confinement, input digests, current `transitional_monolith` mode, and
  disposable staging behavior.
- `verify-archive` verifies a downloaded release archive and its embedded
  `hyperprompt-artifact.json` without extracting it.

Run the foundation gate with:

```sh
make publication-assembly-check
```

To verify a separately downloaded compiler artifact:

```sh
.venv/bin/python -B publication/assembly/check.py verify-archive \
  --platform macos-arm64 \
  --archive /path/to/hyperprompt-0.2.0-macos-arm64.tar.gz
```

The normal gate does not access the network. Candidate builds must create a new
staging directory, verify that it is empty, discard it after any failure, and
only treat compiler exit status `0` plus validated artifacts as readiness.

## Boundaries

78A does not extract ASP-over-MCP prose, execute a candidate RFC build, or
activate modular publication. Those steps remain in 78B and 78C. Until the
atomic activation in `#79`, candidate sources, manifests, source maps, and
aggregates are provenance or test artifacts only.
