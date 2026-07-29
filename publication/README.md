# ASP Specification Publication Contract

`document-set.json` is the normative machine-readable catalog for the ASP
specification document set. Its closed schema and semantic validator select the
seven active canonical module sources and reject incomplete publication states.

Active source, aggregate, and registry entries bind their exact bytes with
SHA-256. Public anchors and local compatibility aliases are explicit,
source-checked, globally unique catalog entries. Internal normative references require a
declared exact dependency edge and a resolvable source-anchor/target-export
record.

The Git-aware history gate walks every commit on the first-parent history of
`PUBLICATION_BASE_REF` and in
`PUBLICATION_BASE_REF..PUBLICATION_CANDIDATE_REF`. At each commit it verifies the
catalog against the source, aggregate, and registry blobs in that exact Git tree,
then compares every unique catalog snapshot. Reusing an exact document, registry,
or document-set version with different structural content fails closed, as does
a stale source-only intermediate commit that a rebase merge could publish. The
check rejects shallow or non-ancestral history; CI fetches full history and
compares the exact pull-request head with its exact base.

The current publication mode is `modular`:

- Core, Authorization, Safe Effects, Evidence, Privacy, ASP-over-MCP, and
  Conformance are authoritative sources under `drafts/modules/`;
- `reserved_documents` is empty and the historical monolith is no longer an
  active document;
- `drafts/agent-surface.md` is a generated aggregate reading view with no
  independent normative authority;
- source-relative module links are provenance-rebased for the aggregate before
  its final digest is recorded, while external links, local fragments, inline
  code, and fenced examples remain unchanged;
- the exact Hyperprompt v0.2.0 release, aggregate digest, manifest, complete
  source map, active source digests, dependency graph, exports, registry owners,
  and anchor relocations are checked together;
- the active builder validates normalized repository-relative source and
  artifact paths, symlink containment, uniqueness, and input/output separation
  before reading module sources or invoking the compiler;
- conformance reports bind the exact active document-set id, version, and
  catalog digest in addition to the generated specification digest.

The `publication/assembly/` tree preserves the non-authoritative #78 rehearsal
pipeline. It pins
Hyperprompt release artifacts, validates closed candidate descriptors and
their declared inputs, and builds the ASP-over-MCP pilot twice in fail-closed
disposable staging. The generated aggregate must be byte-identical to the
canonical monolith. A separate Linux/macOS workflow compares revision-bound
machine-readable build reports; neither the candidate nor its reports becomes
authoritative. The active build is implemented by `publication/modular.py` and
`publication/modular/root.hc`.

Validate the contract with:

```sh
make publication-assembly-toolchain
make publication-modular-build
make publication-check
```

By default the immutable-history comparison uses `origin/main`. A different
review base can be selected explicitly:

```sh
make publication-check \
  PUBLICATION_BASE_REF=<base-commit-or-ref> \
  PUBLICATION_CANDIDATE_REF=<candidate-commit-or-ref>
```

Non-authoritative extraction fixtures remain under `publication/candidates/`
and the 79A–79C rehearsal artifacts remain under `publication/migration/`.
Neither tree is selected by the active catalog. Future publication changes edit
the canonical module sources, regenerate the aggregate with
`make publication-modular-build`, and validate the same state with
`make publication-check`.
