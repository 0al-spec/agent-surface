# RFC Assembly Candidate Pipeline

This directory contains the non-authoritative foundation for review backlog
item `#78`. It does not change the publication authority of
`drafts/agent-surface.md`.

## 78A foundation

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

## 78B executable candidate

`publication/candidates/asp-over-mcp/` contains the first executable,
non-authoritative module candidate:

- `sections/asp-over-mcp.md` is committed, but its exact derivation from the
  canonical monolith is verified;
- prefix and suffix inputs are derived from closed canonical byte ranges;
- the locked compiler must reproduce `drafts/agent-surface.md` byte-for-byte;
- the manifest must describe the complete source/dependency closure;
- the source map must cover every generated line and only the declared
  generated separator;
- two clean builds must produce identical aggregate, manifest, and source-map
  bytes.

Install the exact platform artifact, then run the complete gate:

```sh
make publication-assembly-toolchain
make publication-assembly-check
```

To verify a separately downloaded compiler artifact:

```sh
.venv/bin/python -B publication/assembly/check.py verify-archive \
  --platform macos-arm64 \
  --archive /path/to/hyperprompt-0.2.0-macos-arm64.tar.gz
```

Only `publication-assembly-toolchain` accesses the network. The normal
validation and build gates use the already installed, digest-verified compiler.
Candidate builds create a new staging directory, verify that it is empty,
discard it after any failure, and only treat compiler exit status `0` plus
validated artifacts as readiness.

## Boundaries

78B does not activate modular publication or make the candidate source
normative. Cross-platform reproduction and the final assembly contract remain
in 78C. Until the atomic activation in `#79`, candidate sources, manifests,
source maps, and aggregates are provenance or test artifacts only.
