# Agent Surface

This repository hosts the draft specification for **Agent Surface Protocol**:
a user-mediated delegation protocol for safely connecting user-owned agents to
application contexts, including web applications and SaaS products.

The protocol is built around a simple authority model:

```text
App exposes affordances.
User delegates an agent.
Runtime mediates and enforces.
App verifies authorization.
Agent acts only through typed, scoped actions.
```

Agent Surface Protocol is intended to replace brittle automation patterns such
as screenshots, mouse clicks, accessibility scraping, private API scraping, and
raw user tokens handed to agents with typed resources, typed actions, scoped
grants, local policy, app-side authorization, idempotency, revocation, and
portable receipts.

## Drafts

- [Agent Surface Protocol RFC](drafts/agent-surface.md)

## Core Concepts

- **Agent Surface**: the application-published map of resources, actions,
  events, schemas, scopes, risk labels, approval requirements, endpoints,
  idempotency rules, receipt requirements, and revocation semantics.
- **Agent Grant**: the user-approved, app-scoped, policy-bound delegation object.
  A token or signed object may represent a grant on the wire, but the grant is
  the semantic authorization.
- **Grant Credential**: the concrete credential or proof used to prove a grant,
  such as an opaque token, sender-constrained token, DPoP proof, mTLS-bound
  token, signed delegation object, or app-side server session.
- **Runtime**: the policy enforcement point that hosts or supervises the user's
  agent, verifies Agent Passport evidence, stores grants, mediates actions,
  obtains approvals, and emits receipts.
- **Agent Passport**: [identity and capability evidence][agent-passport] for an
  agent. Passport is evidence, not authority; application authority comes from a
  grant.

## Relationship to Other Protocols

Agent Surface Protocol is designed to compose with, not replace, existing
protocols:

```text
MCP exposes tools.
ACP connects clients to agents.
OAuth delegates access.
Agent Passport proves agent identity and capabilities.
Agent Surface + Agent Grant bind those pieces into safe app-specific delegation.
```

## Repository Structure

```text
agent-surface/
  .github/
    PULL_REQUEST_TEMPLATE.md
    workflows/docs.yml       Markdown, RFC, and dashboard checks.
  conformance/             Versioned executable matrix, vectors, schemas, and runner.
  mocks/                   Synthetic Mock App and Mock Runtime suite fixtures.
  tools/                   Rust API importer, manifest linter, and passive replay verifier.
  drafts/                  Source RFCs written in Markdown.
  review/                  Source data, template, and generated RFC review dashboard.
  LICENSE                  MIT license for repository source code.
  LICENSE-CC-BY-4.0        CC BY 4.0 summary for specifications and documents.
  CONTRIBUTING.md          Contribution guidelines.
```

## Interactive RFC Review Dashboard

The standalone [RFC review dashboard](review/agent-surface-rfc-review.html) is
generated from the RFC, card data, and UI template. Do not edit the generated
HTML directly.

```sh
python3 -m pip install -r review/requirements.txt
make review-data-check
make review-build
make review-check
```

When the RFC changes, update the relevant cards in
[`review/review-data.json`](review/review-data.json), rebuild the dashboard,
and commit the RFC, review data, and generated HTML together. `review-check`
validates card fields and priorities, verifies every linked heading still
exists in the RFC, checks that the generated artifact is current, and parses
the dashboard's inline JavaScript.

Each card keeps RFC coverage (`status`) separate from delivery maturity
(`maturity`). `profile`, `depends_on`, `target_release`, and `evidence` are
canonical planning metadata. Reverse `blocks` links and `readiness` are derived
during the build and MUST NOT be stored in `review-data.json`. A card is ready
when every direct dependency has `present` coverage and at least `specified`
maturity; the card's own coverage does not affect whether it is ready to be
worked on. `machine_validated` maturity is accepted only through a card-specific
binding whose canonical local schema, registry, and any declared implementation
artifacts resolve through their authoritative validator. The conformance suite
and reference mock bundle have separate bindings; mock implementation paths
identify suite-fixture tooling and do not grant ASP implementation credit.
Higher maturity remains fail-closed until implementation and independent
interop evidence resolvers are added to the validation gate.
The canonical file keeps `planning_metadata_mode` set to `required`;
`transitional` exists only so schema v2 can validate the stacked migration
without silently changing the v2 contract.

The generated dashboard can filter by profile, priority, coverage, maturity,
target release, and readiness. Its counters and Next/Previous navigation use
the filtered card set. Dependency chips select the referenced card and relax
only filters that would otherwise hide it.

## Executable Conformance Suite

The versioned suite in [`conformance/v1`](conformance/v1) maps stable
requirements for the six role profiles to positive and negative vectors. Its
runner executes one atomic role boundary through a separate adapter and emits a
closed machine-readable report:

```sh
make conformance-check
python3 conformance/check.py run \
  --subject subject.json \
  --adapter /absolute/path/to/test-adapter \
  --adapter-id example-adapter \
  --adapter-version 1.0.0 \
  --adapter-configuration-sha256 "$ADAPTER_CONFIG_SHA256" \
  --probe /absolute/path/to/authoritative-probe \
  --probe-id example-probe \
  --probe-version 1.0.0 \
  --probe-configuration-sha256 "$PROBE_CONFIG_SHA256" \
  --output report.json
python3 conformance/check.py verify-report report.json \
  --adapter /absolute/path/to/test-adapter \
  --probe /absolute/path/to/authoritative-probe
```

Catalog vectors contain no commands, code, or target URLs. Digest-bound
fixtures provide exact baseline documents and closed mutations. The runner
invokes a stimulus adapter and separate authoritative probe without a shell,
with a fresh working directory, minimal environment, process-group timeout, and
captured-output limit for each vector. The adapter never receives the expected
oracle. Both executables remain trusted test code and must be isolated by the
operator. A report verdict is descriptive evidence for that exact catalog,
subject artifact, configuration, harness, and run. It is not certification,
protocol authority, or proof of complete role conformance.

## Reference Mock Participants

The synthetic Mock App and Mock Runtime exercise the runner without a real
agent or production service:

```sh
make mock-check
```

Their closed manifest, schema, validator, and tests live under [`mocks/`](mocks).
The two participants use separate application-side and runtime-side authority
stores and exchange only versioned mock control messages. That control protocol
is a harness interface, not an ASP wire protocol. Every mock-backed conformance
subject is a `suite_fixture`, so even a fully matching run remains `incomplete`
and supplies neither implementation nor interoperability credit. The bundle
uses deterministic synthetic data only and must never receive production
credentials, secrets, user content, or attestation evidence.

## OpenAPI and AsyncAPI Importer

The Rust `asp-api-import` CLI projects explicit `x-agent-surface` annotations
from a strict-JSON OpenAPI or AsyncAPI document into a deterministic Agent
Surface Manifest candidate:

```sh
make api-import-check
cargo run --locked -p asp-api-importer -- generate openapi.json
cargo run --locked -p asp-api-importer -- self-check --root .
```

The versioned annotation schema, case registry, positive and negative fixtures,
golden manifests, and implementation live in
[`tools/asp-api-importer/`](tools/asp-api-importer). The importer is offline,
does not resolve references, and never infers ASP scopes, risk, approval,
effects, or authority from API metadata. Unannotated operations are omitted.
A generated candidate still requires complete publisher-side manifest and
implementation validation before it can be served as an authoritative Surface.

## ASP Manifest Linter

The Rust `asp-lint` CLI performs deterministic offline checks for missing
schema declarations, risk labels, malformed optional Risk Explanation UI
Hints, idempotency closure, and inconsistent scope references:

```sh
make manifest-lint-check
cargo run --locked -p asp-manifest-linter -- check manifest.json
cargo run --locked -p asp-manifest-linter -- check manifest.json --format json
```

The canonical rules, diagnostic schemas, fixtures, and implementation live in
[`tools/asp-manifest-linter/`](tools/asp-manifest-linter). The parser rejects
ambiguous JSON before linting. A clean result is static declaration evidence
only; it does not verify remote schema bytes, authority, runtime behavior,
interoperability, or deployment security.

## Portable Replay Bundle Verifier

The Rust `asp-replay` CLI validates one portable, passive ASP
session-generation evidence bundle:

```sh
make replay-check
cargo run --locked -p asp-replay-tool -- verify bundle.json
cargo run --locked -p asp-replay-tool -- self-check --root .
```

The bundle contains an exact historical Surface, semantic Grant, and a bounded
ordered record chain containing only session transitions, event deliveries,
event acknowledgements, event gaps, receipts, and explicit capture gaps. It
never contains a Grant Credential, raw token, prompt, Action Request, Action
Response, or executable content.

Verification is deterministic and offline. The tool never follows a URI, opens
a network connection, requests online event replay, acknowledges an event,
changes or resumes a session, dispatches an action, invokes an agent, or
performs an effect.

For safely parsed input, the report has exactly one evaluation state:
`preflight_failed`, `semantic_invalid`, `incomplete`, or `valid`. Strict parse,
local resource, serialization, and tool-integrity failures occur outside that
report state machine. They return status `2` and emit no report. Invalid and
incomplete reports return status `1`; only a valid report returns status `0`.

`valid` means only that every check in the report's exact
`tool.check_profile` ran and passed and that the bounded checker found no replay
gap. It is not, by itself, complete Portable Replay Bundle Profile validation
or native-object conformance. A complete profile validator must also apply the
authoritative Surface, Grant, CloudEvent, acknowledgement, gap, receipt, and
required-signature rules. It must combine those gates fail closed.

The report does not authenticate the exporter or receipt producer, establish
current authority or state, verify remote schemas or keys, or prove that an
external effect occurred. Its assurance values cover only claims supported by
passed prerequisite checks; an unevaluated or incomplete check is never
silently promoted to verified assurance.

## Status

The specification is experimental and subject to change. The current draft is
intended to establish terminology, threat model, protocol layers, manifest
shape, grant lifecycle, receipt semantics, and MVP boundaries.

## License

- Specifications and documents in `drafts/`, `schema/`, `generated/`, `docs/`,
  and the declarative catalog under `conformance/v1/` are licensed under the
  Creative Commons Attribution 4.0 International License (CC BY 4.0).
- Source code and tooling are licensed under the MIT License.

See [LICENSE](./LICENSE) and [LICENSE-CC-BY-4.0](./LICENSE-CC-BY-4.0).

[agent-passport]: https://github.com/0al-spec/agent-passport
