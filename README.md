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
make review-build
make review-check
```

When the RFC changes, update the relevant cards in
[`review/review-data.json`](review/review-data.json), rebuild the dashboard,
and commit the RFC, review data, and generated HTML together. `review-check`
validates card fields and priorities, verifies every linked heading still
exists in the RFC, checks that the generated artifact is current, and parses
the dashboard's inline JavaScript.

## Status

The specification is experimental and subject to change. The current draft is
intended to establish terminology, threat model, protocol layers, manifest
shape, grant lifecycle, receipt semantics, and MVP boundaries.

## License

- Specifications and documents in `drafts/`, `schema/`, `generated/`, and
  `docs/` are licensed under the Creative Commons Attribution 4.0 International
  License (CC BY 4.0).
- Source code and tooling, if added later, are licensed under the MIT License.

See [LICENSE](./LICENSE) and [LICENSE-CC-BY-4.0](./LICENSE-CC-BY-4.0).

[agent-passport]: https://github.com/0al-spec/agent-passport
