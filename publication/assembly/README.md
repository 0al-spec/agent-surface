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

## 78C cross-platform evidence

The `RFC assembly cross-platform` workflow executes the candidate from an exact
clean checkout on:

- `ubuntu-latest` as `linux-amd64`;
- ARM64 `macos-15` as `macos-arm64`.

Each runner emits a closed platform report bound to the checked-out Git
revision, candidate descriptor digest, canonical RFC, locked compiler release
and binary, and aggregate/manifest/source-map digests. A separate comparison
job accepts exactly one report from each required platform, rejects revision or
artifact drift, and emits a machine-readable cross-platform summary.

Reports are run-scoped CI provenance with 30-day retention. They are not
committed because a report for an earlier Git revision must never be mistaken
for evidence about the current checkout.

A platform report can also be produced from a clean local checkout:

```sh
revision="$(git rev-parse HEAD)"
.venv/bin/python -B publication/assembly/check.py build \
  --compiler .tools/hyperprompt/hyperprompt \
  --source-revision "${revision}" \
  --report "/tmp/rfc-assembly-${revision}.json"
```

The command fails if `HEAD` differs from `--source-revision`, the worktree is
dirty before or after compilation, the report path is inside the checkout, or
the destination already exists.

## Boundaries

78C completes the non-authoritative assembly rehearsal, but does not activate
modular publication or make the candidate source normative. Until the atomic
activation in `#79`, candidate sources, manifests, source maps, reports, and
aggregates are provenance or test artifacts only.

## 79B complete modular candidate

`publication/candidates/modular-document-set/` extends the rehearsal from the
single ASP-over-MCP extraction to the complete seven-document ownership map.
Its 25 committed Markdown fragments form seven module source closures while
remaining ordered for a byte-identical aggregate build. The migration
validator proves that every fragment is a maximal canonical ownership run and
that all reserved canonical module paths remain absent.

This candidate does not supersede the earlier ASP-over-MCP fixture: CI builds
both, so the focused extraction remains a regression test while the complete
candidate proves full RFC coverage.
