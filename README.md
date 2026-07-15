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
worked on. `machine_validated` maturity is accepted only when canonical local
schema and registry evidence resolves and the conformance catalog passes its
semantic validator. Higher maturity remains fail-closed until implementation
and independent interop evidence resolvers are added to the validation gate.
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

## Status

The specification is experimental and subject to change. The current draft is
intended to establish terminology, threat model, protocol layers, manifest
shape, grant lifecycle, receipt semantics, and MVP boundaries.

## License

- Specifications and documents in `drafts/`, `schema/`, `generated/`, `docs/`,
  and the declarative catalog under `conformance/v1/` are licensed under the
  Creative Commons Attribution 4.0 International License (CC BY 4.0).
- Source code and tooling, if added later, are licensed under the MIT License.

See [LICENSE](./LICENSE) and [LICENSE-CC-BY-4.0](./LICENSE-CC-BY-4.0).

[agent-passport]: https://github.com/0al-spec/agent-passport
