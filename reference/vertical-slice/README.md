# Independent Reference Vertical Slice

This directory is the executable delivery artifact for review card **#74**. It
implements the exact
[`Application-Audited Effects`](../../conformance/v1/bundles.json) bundle over
a small task-and-comment application surface:

- the application publishes `task.read` and `comment.create`;
- the application issues a narrowed Grant to each identified runtime;
- an agent submits a typed action through that runtime;
- the application independently verifies the Grant Credential and exact
  runtime-agent delegate binding before performing the effect;
- the application produces the authoritative receipt; and
- replay and negative paths prove that rejected requests do not create another
  effect.

The slice is real executable code, not a `suite_fixture`. Its evidence is still
descriptive: every participant is maintained in this repository, so the slice
does **not** establish independent interoperability, certification, production
readiness, security certification, or stable maturity.

## Versioned contract

[`v1/manifest.json`](v1/manifest.json) is the canonical topology and evidence
selection. [`v1/manifest.schema.json`](v1/manifest.schema.json) is a closed
JSON Schema Draft 2020-12 contract for the manifest and participant
configurations. All paths in the manifest and configurations are relative to
the repository root.

The manifest pins:

- review card `74`;
- protocol version `agent-surface/0.1`;
- conformance suite version `1.9.0`;
- the exact Application-Audited Effects bundle;
- six canonical role/profile claims with empty feature selections;
- all 9 positive and 26 negative bundle vectors;
- participant source artifacts, implementation lineages, deployment
  boundaries, and closed runtime configuration; and
- a maximum evidence maturity of `implementation_tested`.

The bundle registry remains `descriptive_only`. Passing reports demonstrate
the named implementation artifacts under the pinned suite; they are not a
portable `conformant: true` assertion.

## Participants

| Participant | Implementation | Boundary | Profiles | Bundle claim |
|---|---|---|---|---|
| `reference-app-control` | Rust | `reference/application/control` | Surface Publisher, Grant Issuer | canonical |
| `reference-app-executor` | Rust | `reference/application/executor` | Action Executor | canonical |
| `reference-app-receipt` | Rust | `reference/application/receipt` | Receipt Producer (`application`) | canonical |
| `reference-runtime-local` | Python | `reference/runtime/local` | Runtime Mediator | canonical |
| `reference-runtime-remote` | Python | `reference/runtime/remote` | Runtime Mediator | additional tested participant |
| `reference-agent-a` | Python | `reference/agent/a` | Agent Adapter | canonical |
| `reference-agent-b` | Python | `reference/agent/b` | Agent Adapter | additional tested participant |

The three application roles share one Rust application lineage, but use
separate conformance entry points and deployment boundary identifiers. The
local and remote runtimes, and agents A and B, have distinct source artifacts,
lineage identifiers, and boundaries.

The six conformance reports execute those role-specific subject entry points
against the exact bundle vectors. The TCP `app_server` is the separately
process-wired composition path used by the two-lane scenario; that scenario
tests a deliberately smaller end-to-end subset. A passing role report therefore
does not imply that every vector was replayed through the TCP server, and a
passing scenario does not replace the six atomic reports. Both paths remain in
the retained Rust artifact closure so changes to either invalidate evidence.

## Two end-to-end lanes

```text
local:  agent A -> local runtime  -> shared Rust application -> app receipt
remote: agent B -> remote runtime -> shared Rust application -> app receipt
```

Both lanes are bound to the exact scenario selection in the manifest. The
canonical six-report bundle claim uses the shared application roles, the local
Runtime Mediator, and agent A. The remote Runtime Mediator and agent B exercise
the second end-to-end lane without being counted as duplicate claims for the
same bundle.

The scenario uses loopback TCP with strict JSON Lines framing to create
separate process and connection boundaries while remaining deterministic in CI.
Reusable application credentials stay inside the runtimes. Each agent receives
only an unguessable runtime-scoped session proof plus the narrowed result and
application receipt. The runtime binds that proof to the exact agent identifier
in its private Grant configuration, rejects both proof impersonation and agent
substitution before dispatch, and never forwards the session proof to the
application. The application still repeats the independent runtime-agent-Grant
tuple check.

Grant issuance, revocation, state inspection, and shutdown require a separate
high-entropy control credential loaded from a private regular file. That
credential is never given to either runtime or agent and is checked separately
from the application-facing Grant Credential. The scenario proves that an
unauthenticated control request and an agent-substitution attempt fail before
an effect.

## Harness separation

[`harness/adapter.py`](harness/adapter.py) translates the suite's stimulus-only
case into the selected participant entry point.
[`harness/probe.py`](harness/probe.py) separately reads private execution
evidence and emits only the sanitized observation required by the conformance
runner. Neither component receives the runner's expected outcome.

The harness and generated reports are test evidence, not protocol authority.
The manifest records their exact source paths and closed protocol
configuration so their digests can be bound into each run.

## Run and verify

Use the repository virtual environment and the pinned Rust toolchain:

```sh
.venv/bin/python -B reference/vertical-slice/check.py validate-manifest
.venv/bin/python -B reference/vertical-slice/check.py validate-evidence
```

To retain the six machine-readable conformance reports, the two-lane scenario
report, and the aggregate evidence object:

```sh
output="$(mktemp -d)"
.venv/bin/python -B reference/vertical-slice/check.py run --output-dir "$output"
find "$output" -type f -print
```

`validate-evidence` rebuilds the Rust application, executes the exact bundle
claims, verifies every report against current source and configuration
digests, runs both end-to-end lanes, validates the aggregate evidence schema,
and discards the temporary output.

The build honors a shell-parsed `CARGO` override while forcing every run into a
fresh temporary target directory. It requires Cargo JSON `compiler-artifact`
records for all four allowlisted binaries, rejects artifacts outside that
directory, and passes the exact resolved paths to a byte-identical staged
adapter through a closed run configuration. The scenario receives the same
resolved server path directly. A no-op wrapper, ambient `CARGO_TARGET_DIR`,
Cargo `build.target-dir`, or target-triple subdirectory therefore cannot make
the evidence run fall back to stale executables.

The repository-wide quality gate also runs this self-check:

```sh
make review-check
```

## Evidence boundary

An `implementation_tested` result means only:

1. the exact versioned manifest is schema-valid;
2. every named artifact and configuration contributes to a digest;
3. the six canonical profile reports pass their exact bundle vector closure;
4. both local and remote lanes pass their positive and negative scenarios; and
5. generated evidence is closed and schema-valid.

The Rust artifact digests include the workspace manifest and `Cargo.lock`, so a
change to dependency resolution invalidates the bound reports even when source
files are unchanged.

Advancing card #74 to `interop_tested` requires evidence from independently
maintained implementation artifacts and deployment boundaries outside this
repository-owned reference lineage. A future verifier must bind those
counterparts to the observations rather than inferring independence from two
processes or two filenames.
