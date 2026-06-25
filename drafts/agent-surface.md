# Agent Surface Protocol Specification

Request for Comments

## Authors' Contact Information

- Egor Merkushev
- Organization: Individual
- Email: gorkaedeep@gmail.com
- Published: 25 June 2026

## Status of this Memo

This document is an **Experimental** Request for Comments. It represents a draft
proposal for an Agent Surface Protocol specification and is submitted to the
community for discussion, feedback, critique, and suggestions for improvement.
This document is a work in progress and is not yet a finalized standard.
Distribution of this memo is unlimited.

Submit comments as GitHub issues in the original repository hosting this RFC.

## Copyright Notice and Licensing

Copyright (c) 2026 0AL -- Zero-trust Agents Layer.

This document is released under the Creative Commons Attribution 4.0
International License (CC BY 4.0). You are free to copy, distribute, and modify
this specification, even for commercial purposes, provided that attribution is
given to the original author(s).

To contribute to this document, please submit an issue or pull request to the
original GitHub repository:

```text
https://github.com/0al-spec/agent-surface
```

This is not an IETF document and is not subject to BCP 78 or the IETF Trust.
However, it follows similar principles of openness and community participation.

## Abstract

This proposal defines **Agent Surface Protocol**, a user-mediated delegation
model for connecting user-owned agents to application contexts, including web
applications and SaaS products.

Agent Surface Protocol can be understood as the missing protocol substrate for
safe **Bring Your Own Agent (BYOA)**. BYOA describes the user expectation: a
person can bring a preferred local, enterprise, or hosted agent
into an application context. Agent Surface Protocol defines the security and
interoperability machinery that makes that expectation practical.

The central idea is not that an application "gets an agent". The user remains
the principal. The application publishes a typed **Agent Surface** describing
the resources, actions, events, scopes, risk labels, approval requirements,
schemas, idempotency rules, receipts, endpoints, and revocation semantics it
supports. The user chooses a local or remote agent they own. An application
runtime verifies the agent's Agent Passport, obtains a scoped **Agent Grant**,
enforces local policy, supervises the agent, and mediates all application
actions.

The goal is to replace brittle "computer use" automation patterns:

- screenshot interpretation
- mouse and keyboard control
- accessibility-tree scraping
- private API scraping
- raw user API tokens handed to agents

with a typed, scoped, auditable, revocable, app-verifiable delegation layer.

## Normative and Informative Sections

Unless otherwise stated, the following sections are **normative**:

- Terminology
- Design Principles
- Agent Surface Manifest
- Risk Taxonomy
- Approval Semantics
- Idempotency
- Agent Grant
- Sessions and Actions
- Receipts
- Revocation Semantics
- Error Model
- Versioning and Compatibility
- Security Considerations
- Privacy Considerations
- Conformance

The following sections are **informative**:

- Abstract
- Motivation
- Relationship to Existing Protocols
- Conceptual Architecture
- Protocol Layers
- Capability Matching
- Application MVP Mapping
- Example End-to-End Flow
- Open Questions
- References
- Appendices

## Motivation

Modern agents need to work inside applications. Today, they often do this in one
of two fragile ways:

1. They operate the user interface by observing screenshots, clicking controls,
   and reading accessibility trees.
2. They receive a user's broad API token and call ordinary application APIs
   directly, often without an agent-specific contract, local policy mediation,
   idempotency, or portable receipts.

Both approaches have structural problems.

Computer-use automation is brittle. It depends on pixels, layout, timing,
browser state, accessibility labels, and undocumented UI behavior. It is hard to
authorize precisely and hard to audit semantically. The user can see the result,
but the application rarely receives machine-verifiable evidence of which agent
acted, under which delegation, against which policy, and why a write was allowed.

Raw-token API automation is powerful but unsafe. A token is a transport
artifact, not a delegation model. If an agent receives a broad source-control,
issue-tracker, chat, docs, or CRM token, the application can be unable to
distinguish the user from the user's agent, the runtime can be unable to
constrain the agent's behavior after token release, and receipts become
difficult to produce without custom integration.

Agent Surface Protocol introduces a safer frame:

```text
BYOA is the model.
Agent Surface is the protocol.
Agent Grant is the authority.
Agent Passport is the evidence.

App exposes affordances.
User delegates an agent.
Runtime mediates and enforces.
App verifies authorization.
Agent acts only through typed, scoped actions.
```

The application becomes **agent-native**, but not **agent-owned**. It does not
need to build, host, pay for, or control the user's agent. It only needs to
publish a civilized surface and enforce grants on its side.

## Goals

- Define a protocol layer for safe Bring Your Own Agent (BYOA) in application
  contexts.
- Treat the user as the principal and the agent as a delegated worker.
- Make **Grant**, not token, the primary authorization object.
- Let applications publish typed resources, actions, events, schemas, scopes,
  risk labels, idempotency rules, approval hints, receipt requirements, and
  wire-level endpoints.
- Let runtimes verify Agent Passports before an agent can receive delegated work.
- Require both runtime-side and app-side enforcement.
- Avoid direct application credentials in agent processes where practical.
- Make proposal-first workflows the default safety posture:

  ```text
  read -> propose -> approve -> write -> receipt
  ```

- Fit alongside existing agent standards instead of replacing them:
  - MCP can remain a tool/resource transport.
  - ACP can remain an agent/client transport.
  - OAuth can remain a consent and authorization substrate.
  - Agent Passport can remain identity and capability evidence.

## Non-Goals

- Do not define another general-purpose agent framework.
- Do not replace MCP, ACP, OAuth, DID, Verifiable Credentials, JSON Schema, or
  existing application APIs.
- Do not require applications to trust local runtimes blindly.
- Do not require agents to receive raw user credentials.
- Do not require browser-to-localhost communication.
- Do not require every app action to be autonomous; proposal mode is valid and
  preferred for early adoption.
- Do not standardize every possible human approval UI.
- Do not specify a single cryptographic trust-store model in this draft.
- Do not require signed grants or signed receipts in the MVP profile.

## Conventions

The key words "MUST", "MUST NOT", "SHOULD", "SHOULD NOT", and "MAY" in this
document are to be interpreted in the RFC 2119 and RFC 8174 sense when, and only
when, they appear in all capitals.

This is not an IETF document. The keywords are used to make interoperability and
security expectations explicit for future implementers.

## Terminology

### User

The human principal who owns or controls an account in an application and owns,
selects, or authorizes an agent.

### Application

The product or software system that exposes a bounded environment in which
agents can operate. An application can be a website, SaaS product, desktop app
backend, local bridge, control plane, browser extension, reference
implementation, or service that publishes an Agent Surface and enforces
app-side authorization.

This draft uses **Application** as the neutral term for concrete
implementations. Product-specific names belong in implementation documents, not
in the protocol role model.

### Agent Surface

The machine-readable map of application affordances available for agent
delegation. A surface includes resources, actions, events, schemas, scopes, risk
labels, approval hints, idempotency rules, audit semantics, versioning, endpoints,
and revocation semantics.

The surface is not merely an API endpoint list. It is an application contract for
safe delegated agent behavior.

### Agent Surface Manifest

A discoverable document, typically published at a well-known URL such as:

```text
/.well-known/agent-surface.json
```

The manifest describes the Agent Surface in a machine-readable format.

### User-Owned Agent

An agent selected by the user. It can run locally, in a company-controlled
environment, or in a remote service. The important property is that the
application does not own or silently choose it.

### Runtime

The local or user-controlled system that hosts, launches, supervises, or mediates
the user's agent. A runtime can be embedded in an application, delivered as a
companion bridge or daemon, provided by an operating system service, implemented
by a browser extension, or hosted in a user-controlled environment.

When the runtime is part of a concrete application implementation, this draft
refers to it as an **application runtime**.

This proposal separates two runtime responsibilities:

- **Agent Host**: starts or connects to agents, adapters, and tools.
- **Policy Enforcement Point**: stores grants, applies local policy, obtains
  approvals, mediates actions, writes audit logs, and blocks disallowed behavior.

One process can implement both roles, but the distinction matters for security
analysis.

### Agent Passport

Agent Passport is identity and capability evidence for an agent. It can describe
the agent, its declared capabilities, resource requirements, security policies,
integrity hashes, lifecycle, issuer, and signature.

An Agent Passport does **not** by itself grant authority inside an application.
It answers "what is this agent and what has been attested about it?" A grant
answers "what has this user allowed this runtime-agent-passport tuple to do in
this application context?"

Passport is evidence, not authority.

### Agent Grant

A user-approved, app-scoped, policy-bound delegation object.

The grant is the semantic authorization. Tokens, cookies, JWTs, capability URLs,
sender-constrained credentials, or signed objects are transport representations.
A grant SHOULD be temporary, constrained, auditable, revocable, and bound to the
user, application, runtime, agent, and passport evidence.

### Grant Credential

A concrete credential or proof used to represent or prove an Agent Grant on the
wire. Examples include opaque bearer tokens, sender-constrained tokens, DPoP
proofs, mTLS-bound tokens, JWTs, macaroon-like capabilities, signed delegation
objects, or app-side server sessions.

A `grant_id` is an identifier. It is not, by itself, authority.

### Capability Lease

An informal term for a time-limited, attenuated grant. A capability lease grants
only specific capabilities, under caveats such as duration, resource bounds,
approval requirements, max actions, or max spend.

### Action

A typed operation exposed by an Agent Surface. Examples:

- `comment.propose`
- `comment.create`
- `pull_request.review.submit`
- `task.assign`
- `invoice.refund.request`

### Resource

A typed object or collection exposed by an Agent Surface. Examples:

- `pull_request`
- `issue`
- `task`
- `document`
- `invoice`

### Event

A typed notification exposed by an Agent Surface or runtime. Examples:

- `review.requested`
- `ci.failed`
- `task.created`
- `grant.revoked`

### Receipt

Portable evidence that an action occurred, including the grant, session, agent,
passport hash, input hash, output hash, approval, timestamp, and result.

Receipts can be stored locally, in the application, in enterprise audit systems,
or in a provenance graph.

This proposal distinguishes:

- **Runtime Receipt**: evidence observed and produced by the runtime, such as
  agent intent, policy evaluation, and local user approval.
- **App Receipt**: evidence produced by the application that a mutation was
  actually performed or denied under a grant.

## Design Principles

### User Is the Principal

The user chooses whether to delegate work to an agent. The app MAY expose a
surface and request consent, but it MUST NOT silently select an agent or claim
that a user's agent acts on behalf of the app.

### App Exposes, Runtime Mediates, Agent Executes

The application exposes typed affordances. The runtime mediates access to those
affordances. The agent executes delegated work through the runtime.

```text
User
  -> authorizes grant
Runtime / Policy Enforcement Point
  -> verifies Agent Passport
  -> supervises User-Owned Agent
Agent
  -> requests typed actions
Runtime
  -> enforces local policy and grant caveats
Application
  -> enforces app-side grant scopes
```

### Grant Is More Important Than Token

A token is a bearer mechanism, proof key, or API credential. A grant is the
semantic delegation:

```text
This user allowed this runtime-agent-passport tuple to perform these typed
actions in this app context under these constraints until this expiration.
```

Implementations MAY represent a grant as an opaque token, OAuth access token,
sender-constrained token, signed object, macaroon-like capability, or server-side
grant identifier. The protocol model SHOULD still describe it as a grant.

### Grant Identifier Is Not Authority

Applications MUST NOT authorize an action based only on a client-supplied
`grant_id`.

A request that includes `grant_id` MUST also be authorized by an app-verifiable
grant credential, server-side grant state, signed delegation object,
introspection result, sender-constrained proof, or equivalent authorization
mechanism.

### App-Side Enforcement Is Mandatory

Runtime policy is necessary but not sufficient.

The runtime protects the user. The app protects its resources.

An application MUST verify grant authority for every action. It MUST NOT accept a
runtime's self-assertion that a grant exists without an app-verifiable token,
signed delegation object, introspection result, or equivalent authorization
mechanism.

### Agent Does Not Receive Raw Authority

Where practical, the agent SHOULD NOT receive the grant secret, OAuth access
token, cookie, session key, or broad application credential. The agent SHOULD
request typed actions from the runtime:

```text
Agent -> Runtime -> App Agent Surface
```

The runtime can then enforce local policy, approvals, idempotency, auditing, and
redaction before sending anything to the app.

### Proposal Mode Is the Default

The first safe interaction mode SHOULD be:

```text
read -> draft/propose -> human or app approval -> write -> receipt
```

Direct writes without approval can exist for mature grants and low-risk actions,
but the protocol SHOULD make proposal flows first-class.

### Every Write Is Idempotent

Any action with side effects MUST support idempotency. Retries, network
reconnects, agent loops, and duplicate messages MUST NOT create ten comments, ten
branches, ten refund requests, or ten approvals.

### Receipts Are First-Class

Audit logs are useful, but action receipts are portable. A receipt SHOULD be
created for every successful side-effecting action and for important denied or
failed actions.

## Relationship to Existing Protocols

### Model Context Protocol

The Model Context Protocol specification describes an open protocol for
connecting LLM applications to external data sources and tools:

<https://modelcontextprotocol.io/specification/2025-06-18>

MCP can be used under or alongside Agent Surface Protocol. For example, an
application might expose a resource/action surface that is implemented internally
using MCP servers. Agent Surface Protocol focuses on user-mediated delegation,
app-side grant enforcement, risk labels, approval semantics, and receipts.

### Agent Client Protocol

Agent Client Protocol focuses on communication between clients such as editors
and coding agents, including local and remote agent scenarios:

<https://agentclientprotocol.com/protocol/v1/overview>

ACP can be an Agent Adapter Protocol below an application runtime. Agent Surface
Protocol does not replace ACP; it defines how a user grants a user-owned agent
authority inside an application context.

### OAuth

OAuth 2.0 remains a practical substrate for consent, authorization codes, scopes,
refresh, revocation, token introspection, token exchange, and resource
indicators.

Relevant standards:

- OAuth 2.0: <https://www.rfc-editor.org/rfc/rfc6749>
- OAuth 2.0 Token Revocation: <https://www.rfc-editor.org/rfc/rfc7009>
- OAuth 2.0 Token Introspection: <https://www.rfc-editor.org/rfc/rfc7662>
- OAuth 2.0 Token Exchange: <https://www.rfc-editor.org/rfc/rfc8693>
- OAuth 2.0 Resource Indicators: <https://www.rfc-editor.org/rfc/rfc8707>

Agent Surface Protocol uses the term **grant** for the semantic object,
even when an OAuth access token is the transport representation.

If OAuth is used, `agent_delegation` MAY be represented as an OAuth extension
grant type. `agent_delegation` is not a standard OAuth grant type in this draft.

Implementations MAY also use existing OAuth flows, including:

- Authorization Code with PKCE and additional agent delegation parameters.
- OAuth Token Exchange to exchange a user-authorized credential for an
  agent-scoped grant credential.
- Resource Indicators to constrain the resource server or app surface.

### Agent Passport

Agent Passport provides agent identity, capability, policy, lifecycle, signature,
and integrity evidence.

Agent Surface Protocol consumes Agent Passport evidence during grant issuance and
runtime mediation:

- Is this agent known?
- Who issued or signed its passport?
- What capabilities does it declare?
- What runtime or resource constraints does it require?
- Has the passport expired or been revoked?
- Does the passport hash match the executable agent?

But the passport itself does not authorize application actions.

### DID and Verifiable Credentials

Decentralized Identifiers and Verifiable Credentials can be useful for future
signed grants, issuer trust, and portable delegation proofs:

- DID Core: <https://www.w3.org/TR/did-core/>
- Verifiable Credentials Data Model: <https://www.w3.org/TR/vc-data-model-2.0/>

This draft does not require DID or VC for the MVP.

## Conceptual Architecture

```text
Browser / App UI
        |
        | HTTPS / SSE / WebSocket
        v
Application Control Plane
  - publishes Agent Surface Manifest
  - issues or validates Agent Grants
  - enforces app-side scopes
  - emits app events
        ^
        | outbound WSS / HTTPS from runtime
        v
Application Runtime
  - pairs with app/account
  - verifies Agent Passport
  - stores grants
  - applies local policy
  - obtains local approvals
  - supervises agent adapters
  - writes audit log and receipts
        |
        | adapter boundary
        v
User-Owned Agent
  - local CLI agent
  - hosted coding agent
  - ACP agent
  - MCP-backed workflow
  - custom command
```

The browser can interact with the application control plane. It does not need to
connect directly to the local runtime.

## Protocol Layers

Agent Surface Protocol is specified as four separable layers.

### 1. Agent Surface Manifest

The application-published affordance contract:

- app identity
- surface version
- resources
- actions
- events
- scopes
- JSON Schemas
- risk labels
- approval hints
- idempotency requirements
- receipt requirements
- auth endpoints
- action endpoints
- event endpoints
- receipt endpoints
- revocation endpoints

### 2. Agent Grant Protocol

The user-mediated authorization lifecycle:

- grant request
- consent presentation
- runtime binding
- agent binding
- passport binding
- scope constraints
- expiration
- refresh
- revocation
- introspection
- receipt linkage

### 3. Runtime Bridge Protocol

The runtime-to-control-plane channel. A conforming application MAY expose this
kind of channel using typed session and approval messages such as:

- `runtime.hello`
- `runtime.accepted`
- `session.start`
- `session.event`
- `session.cancel`
- `approval.required`
- `approval.resolved`

This layer is transport and session orchestration. It is not intended to absorb
all Agent Surface semantics.

### 4. Agent Adapter Protocol

The runtime-to-agent integration layer:

- `custom-command`
- `codex-cli`
- `claude-code`
- `acp-stdio`
- `mcp-client`
- `mcp-server`

The adapter layer turns a concrete agent into a runtime-mediated worker.

## Agent Surface Manifest

### Discovery

Applications SHOULD publish a manifest at:

```text
https://example.com/.well-known/agent-surface.json
```

For multi-tenant SaaS systems, the public well-known manifest SHOULD describe
tenant-independent capabilities. Tenant-specific surfaces MAY be discovered
through authenticated application metadata or through tenant-specific origins,
such as:

```text
https://tenant.example.com/.well-known/agent-surface.json
```

If the manifest contains sensitive tenant-specific affordances, it MUST require
ordinary authenticated app access.

The manifest SHOULD be served with:

```http
Content-Type: application/json
Cache-Control: max-age=300
```

### Required Top-Level Fields

```json
{
  "protocol": "agent-surface/0.1",
  "app_id": "com.example.project-tool",
  "issuer": "https://example.com",
  "surface_version": "2026-06-25",
  "surface_url": "https://example.com/.well-known/agent-surface.json",
  "auth": {},
  "agent_api": {},
  "scopes": [],
  "resources": [],
  "actions": [],
  "events": [],
  "audit": {},
  "revocation": {}
}
```

### Endpoints

The manifest MUST declare enough endpoint information for a runtime to obtain or
validate a grant and invoke typed actions.

This draft separates OAuth-style authorization endpoints from application action
endpoints.

Example:

```json
{
  "auth": {
    "type": "oauth2",
    "authorization_url": "https://example.com/oauth/authorize",
    "token_url": "https://example.com/oauth/token",
    "introspection_url": "https://example.com/oauth/introspect",
    "revocation_url": "https://example.com/oauth/revoke"
  },
  "agent_api": {
    "grant_request_url": "https://example.com/agent-grants/request",
    "grant_introspection_url": "https://example.com/agent-grants/introspect",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "action_url": "https://example.com/agent-actions",
    "event_subscription_url": "https://example.com/agent-events",
    "receipt_url": "https://example.com/agent-receipts"
  }
}
```

Implementations MAY collapse these endpoints when the application already has
equivalent OAuth or API infrastructure, but the manifest MUST make the wire-level
surface discoverable.

### Example Manifest

```json
{
  "protocol": "agent-surface/0.1",
  "app_id": "com.example.project-tool",
  "issuer": "https://example.com",
  "surface_version": "2026-06-25",
  "surface_url": "https://example.com/.well-known/agent-surface.json",
  "compatibility": {
    "min_runtime": "application-runtime/0.1",
    "schema_dialect": "https://json-schema.org/draft/2020-12/schema"
  },
  "auth": {
    "type": "oauth2",
    "authorization_url": "https://example.com/oauth/authorize",
    "token_url": "https://example.com/oauth/token",
    "introspection_url": "https://example.com/oauth/introspect",
    "revocation_url": "https://example.com/oauth/revoke",
    "grant_types": ["agent_delegation"],
    "token_binding": ["runtime", "agent_passport_hash"],
    "pkce_required": true
  },
  "agent_api": {
    "grant_request_url": "https://example.com/agent-grants/request",
    "grant_introspection_url": "https://example.com/agent-grants/introspect",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "action_url": "https://example.com/agent-actions",
    "event_subscription_url": "https://example.com/agent-events",
    "receipt_url": "https://example.com/agent-receipts"
  },
  "scopes": [
    {
      "id": "tasks.read",
      "description": "Read tasks visible to the user."
    },
    {
      "id": "comments.propose",
      "description": "Prepare comments without committing them."
    },
    {
      "id": "comments.write",
      "description": "Create comments in the application."
    }
  ],
  "resources": [
    {
      "id": "task",
      "read_scope": "tasks.read",
      "schema": "https://example.com/schemas/task.schema.json"
    }
  ],
  "actions": [
    {
      "id": "comment.propose",
      "scope": "comments.propose",
      "risk": "propose",
      "side_effect": false,
      "approval": "none",
      "execution": {
        "mode": "direct"
      },
      "input_schema": "https://example.com/schemas/comment-propose.input.schema.json",
      "output_schema": "https://example.com/schemas/comment-propose.output.schema.json"
    },
    {
      "id": "comment.create",
      "scope": "comments.write",
      "risk": "write",
      "side_effect": true,
      "approval": "user_or_app",
      "idempotency": "required",
      "execution": {
        "mode": "write",
        "proposal_action": "comment.propose"
      },
      "input_schema": "https://example.com/schemas/comment-create.input.schema.json",
      "output_schema": "https://example.com/schemas/comment-create.output.schema.json",
      "receipt": "required"
    }
  ],
  "events": [
    {
      "id": "task.created",
      "scope": "tasks.read",
      "schema": "https://example.com/schemas/task-created.event.schema.json"
    },
    {
      "id": "review.requested",
      "scope": "tasks.read",
      "schema": "https://example.com/schemas/review-requested.event.schema.json"
    }
  ],
  "audit": {
    "receipt_schema": "https://example.com/schemas/action-receipt.schema.json",
    "required_fields": [
      "grant_id",
      "session_id",
      "action_id",
      "actor_agent",
      "user",
      "timestamp",
      "result"
    ]
  },
  "revocation": {
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "event": "grant.revoked"
  }
}
```

### Resources

Resources describe data the agent MAY read, reference, or attach to an action.

Each resource SHOULD include:

- `id`
- `read_scope`
- `schema`
- optional `query_actions`
- optional `redaction_policy`
- optional `retention_policy`

Example:

```json
{
  "id": "pull_request",
  "read_scope": "pull_request.read",
  "schema": "https://github.example/schemas/pull-request.schema.json",
  "query_actions": ["pull_request.get", "pull_request.list_files"],
  "redaction_policy": "repository-visible-fields-only"
}
```

### Actions

Actions are typed operations the app allows agents to request through a runtime.

Each action SHOULD include:

- `id`
- `scope`
- `risk`
- `approval`
- `input_schema`
- `output_schema`
- `side_effect`
- `execution`
- `idempotency` for side-effecting actions
- `receipt` for side-effecting actions

Example:

```json
{
  "id": "pull_request.review.submit",
  "scope": "pull_request.review.write",
  "risk": "write",
  "side_effect": true,
  "approval": "user_or_app",
  "idempotency": "required",
  "execution": {
    "mode": "write",
    "proposal_action": "pull_request.review.propose"
  },
  "input_schema": "https://example.com/schemas/pr-review-submit.input.schema.json",
  "output_schema": "https://example.com/schemas/pr-review-submit.output.schema.json",
  "receipt": "required"
}
```

### Proposal-Only Support

Applications that are not ready to allow direct agent writes SHOULD expose
proposal-only actions.

A proposal-only action is a typed action whose output is a draft, suggestion,
patch, review body, or other non-committed artifact.

Example:

```json
{
  "id": "pull_request.review.propose",
  "scope": "pull_request.review.propose",
  "risk": "propose",
  "side_effect": false,
  "approval": "none",
  "execution": {
    "mode": "proposal_only"
  },
  "input_schema": "https://example.com/schemas/pr-review-propose.input.schema.json",
  "output_schema": "https://example.com/schemas/pr-review-propose.output.schema.json"
}
```

If a write action depends on a proposal, it SHOULD reference the proposal action:

```json
{
  "id": "pull_request.review.submit",
  "execution": {
    "mode": "write",
    "proposal_action": "pull_request.review.propose"
  }
}
```

This allows early adopters to become agent-native without allowing direct writes.

### Events

Events let applications notify runtimes and agents about app context changes.

Events SHOULD be scoped. A grant that permits `pull_request.read` MAY receive
`pull_request.updated`, but SHOULD NOT receive unrelated financial, HR, or admin
events.

Example:

```json
{
  "id": "ci.failed",
  "scope": "pull_request.read",
  "schema": "https://example.com/schemas/ci-failed.event.schema.json"
}
```

## Risk Taxonomy

Every action SHOULD have a standard risk label. Runtimes can map risk labels to
local policy defaults.

| Risk | Meaning | Suggested Default |
| --- | --- | --- |
| `read` | Reads data visible under the grant. | Allow if scope permits. |
| `propose` | Produces a draft, suggestion, or patch without committing it. | Allow and audit. |
| `write` | Mutates app state. | Ask or require app approval. |
| `public_side_effect` | Publishes, sends, or exposes user-visible or public content. | Ask; often require app-side confirmation. |
| `external_side_effect` | Sends data or causes effects outside the app boundary. | Ask; often deny by default. |
| `financial_side_effect` | Charges, refunds, purchases, invoices, payroll. | Always require explicit approval. |
| `destructive` | Deletes, closes, revokes, disables, or irreversibly changes state. | Deny by default or require step-up approval. |
| `privileged` | Changes permissions, secrets, tokens, admin settings, or access policy. | Deny by default. |

Applications MAY define extension risk labels, but they SHOULD map them to the
standard labels for runtime interoperability.

## Approval Semantics

Actions SHOULD declare an approval mode:

| Approval | Meaning |
| --- | --- |
| `none` | Runtime MAY execute if grant and policy allow. |
| `runtime` | Runtime MUST obtain local user approval before sending the action. |
| `app` | App MUST obtain or verify app-side approval before committing. |
| `user_or_app` | Either a runtime approval or app-side approval MAY satisfy the requirement, depending on grant caveats. |
| `runtime_and_app` | Both runtime-side and app-side approval are required. |

Approval records SHOULD be linked into receipts.

## Idempotency

Every side-effecting action MUST support idempotency.

Action requests SHOULD include:

```json
{
  "idempotency_key": "idem_01HX...",
  "action_id": "comment.create"
}
```

The application MUST ensure repeated requests with the same idempotency key and
same normalized input do not repeat the side effect.

If the same key is reused with different normalized input, the application SHOULD
return an idempotency conflict error.

Applications SHOULD define the input normalization procedure per action, or use
the declared input schema with a canonical JSON profile. A future draft is
expected to define canonicalization requirements for signed receipts and signed
grants.

## Agent Grant

### Grant Object

An Agent Grant binds a user, runtime, agent, passport evidence, application,
surface, scopes, and caveats.

```json
{
  "grant_id": "grant_123",
  "subject": {
    "user": "user_abc"
  },
  "delegate": {
    "runtime": "application_runtime_456",
    "agent": "local_agent_789",
    "passport_ref": "agent-passport://local-agent",
    "passport_hash": "sha256:..."
  },
  "resource_server": {
    "app_id": "code.example.com",
    "issuer": "https://code.example.com",
    "surface_version": "code-review-agent-surface/0.1"
  },
  "scopes": [
    "pull_request.read",
    "pull_request.comment"
  ],
  "constraints": {
    "repositories": ["example-org/example-repo"],
    "pull_requests": [13],
    "expires_at": "2026-06-25T20:00:00Z",
    "write_approval": "required",
    "max_actions": 20,
    "max_cost_usd": 5
  },
  "audit": {
    "local_receipt": "required",
    "app_receipt": "required"
  }
}
```

### Grant Lifecycle

```text
discover surface
  -> verify manifest
  -> choose agent
  -> verify Agent Passport
  -> request grant
  -> user consent
  -> issue grant
  -> store grant in runtime
  -> start session
  -> mediate actions
  -> issue receipts
  -> expire / revoke / renew
```

### Grant Issuance Models

#### Model A: App-Issued Grant

The application issues a grant after user consent.

```text
Runtime redirects user to app OAuth / consent
App issues agent grant
Runtime stores grant
Runtime calls app with grant credential
App verifies every call
```

This is the RECOMMENDED MVP model because it fits existing OAuth/resource-server
deployments.

Pros:

- Easy for applications to enforce.
- Works with existing consent and scope infrastructure.
- Does not require a new global trust authority.

Cons:

- The app learns runtime and agent metadata.
- Each app needs to implement agent grant issuance.

#### Model B: Runtime-Held Grant Plus App Token

The app issues a scoped token to the runtime. The runtime locally binds that
token to an agent, passport, and policy.

Pros:

- Simpler for early app integrations.
- Can work with existing OAuth tokens.

Cons:

- The app can fail to know which agent actually acted.
- Weaker app-side audit unless receipts include runtime-attested metadata.

#### Model C: Signed Delegation Object

The grant is a signed object with caveats. It MAY be signed by the app, user,
runtime, enterprise authority, or some combination.

Pros:

- Portable and cryptographically strong.
- Can support offline verification and third-party audit.

Cons:

- Requires canonicalization, trust stores, signing profiles, revocation
  semantics, and stronger interop work.
- Too large for the first MVP.

### Grant Credentials and Proof

An Agent Grant MAY be represented or proven by one of several mechanisms:

- bearer grant token
- sender-constrained token
- DPoP-bound token
- mTLS-bound token
- app-side server session binding
- token introspection result
- signed delegation object
- macaroon-like caveated capability

A future draft is expected to define required proof profiles. The MVP profile
MAY use app-issued bearer grant credentials, but production deployments SHOULD
prefer sender-constrained credentials where practical.

### Grant Verification

Applications SHOULD verify every action against grant state:

- grant exists and is active
- grant credential or proof is valid
- grant is bound to the user
- grant is bound to the runtime when binding is required
- grant is bound to the agent/passport hash when binding is required
- scope permits the action
- resource constraints permit the target object
- expiration has not passed
- action count and cost bounds have not been exceeded
- approval caveats are satisfied
- idempotency key is valid

Runtimes SHOULD verify:

- grant is active
- local user has not revoked the app, runtime, or agent
- Agent Passport is valid
- requested action is compatible with the Agent Passport capability set
- local policy allows the action
- local approval is present when required
- action input matches the declared schema
- secrets and credentials are not exposed to the agent

## Capability Matching

Capability matching is an advisory process used by the runtime to help the user
choose a compatible agent. It does not invert authority.

Incorrect framing:

```text
The app needs an agent with capability X, so the runtime picks one.
```

Correct framing:

```text
The app exposes actions X/Y/Z.
The user wants to delegate work in that app.
The runtime compares app requirements with passports of user-owned agents.
The user authorizes a specific runtime-agent-passport tuple through a grant.
```

Matching inputs:

- action `capability_hint`
- action schemas
- required scopes
- risk labels
- Agent Passport capabilities
- Agent Passport security policy
- local runtime adapter availability
- user preferences
- enterprise policy

Matching outputs:

- compatible agents
- missing capabilities
- required scopes
- required approvals
- risk summary
- expected sandbox constraints

The matching result is shown to the user before grant issuance.

## Sessions and Actions

### Session Start

Once a grant exists, an application or runtime MAY start a session.

```json
{
  "type": "session.start",
  "payload": {
    "session_id": "sess_456",
    "grant_id": "grant_123",
    "agent_id": "local_agent_789",
    "surface": {
      "app_id": "code.example.com",
      "surface_version": "code-review-agent-surface/0.1"
    },
    "task": {
      "kind": "pull_request.review",
      "goal": "Review PR #13 and propose a concise review comment.",
      "inputs": {
        "repository": "example-org/example-repo",
        "pull_request": 13
      }
    }
  }
}
```

### Action Request

The agent requests an action through the runtime. The runtime sends the action to
the app only if grant and policy allow it.

The action request MUST be authorized by the HTTP authorization layer or an
equivalent proof. The `grant_id` inside the body is a correlation identifier, not
a credential.

Example:

```http
POST /agent-actions HTTP/1.1
Host: example.com
Authorization: Bearer <grant-credential>
Idempotency-Key: idem_01HX7DS8AC6G9
Content-Type: application/json
```

```json
{
  "type": "action.request",
  "payload": {
    "session_id": "sess_456",
    "grant_id": "grant_123",
    "action_id": "comment.create",
    "idempotency_key": "idem_01HX7DS8AC6G9",
    "input": {
      "repository": "example-org/example-repo",
      "pull_request": 13,
      "body": "The proposed review comment text."
    }
  }
}
```

If the runtime uses a signed proof instead of a bearer grant credential, the
request SHOULD carry proof material in a standard authorization header or an
explicit `proof` field.

Example proof shape:

```json
{
  "proof": {
    "type": "dpop+jwt",
    "jti": "proof_123",
    "iat": 1782400000,
    "signature": "..."
  }
}
```

### Action Response

```json
{
  "type": "action.result",
  "payload": {
    "session_id": "sess_456",
    "grant_id": "grant_123",
    "action_id": "comment.create",
    "idempotency_key": "idem_01HX7DS8AC6G9",
    "result": "success",
    "resource": {
      "type": "comment",
      "id": "comment_789",
      "url": "https://code.example.com/example-org/example-repo/pull/13#discussion_r..."
    },
    "receipt_id": "receipt_abc"
  }
}
```

### Proposal Flow

Proposal mode separates drafting from committing.

```text
Agent -> comment.propose
Runtime -> local policy check
App -> stores draft/proposal
User/App -> approves
App -> comment.create
Runtime/App -> receipt
```

This is the RECOMMENDED default for early integrations.

## Receipts

### Receipt Requirements

Receipts SHOULD include:

- receipt id
- receipt type
- grant id
- session id
- action id
- app id
- user id or stable pseudonymous user reference
- runtime id
- agent id
- Agent Passport hash
- surface version
- input hash
- output hash
- approval reference
- idempotency key
- timestamp
- result
- error classification when failed

### Runtime Receipt

A runtime receipt records what the runtime observed and enforced, such as agent
intent, local policy decisions, local approvals, denials, and runtime-side
redactions.

```json
{
  "receipt_id": "receipt_runtime_abc",
  "receipt_type": "runtime",
  "grant_id": "grant_123",
  "session_id": "sess_456",
  "action_id": "comment.create",
  "actor_agent": {
    "agent_id": "local_agent_789",
    "passport_hash": "sha256:..."
  },
  "runtime": {
    "runtime_id": "application_runtime_456"
  },
  "subject": {
    "user": "user_abc"
  },
  "idempotency_key": "idem_01HX7DS8AC6G9",
  "input_hash": "sha256:...",
  "approved_by": {
    "type": "runtime_user_approval",
    "approval_id": "appr_123"
  },
  "timestamp": "2026-06-25T16:30:00Z",
  "result": "forwarded_to_app"
}
```

### App Receipt

An app receipt records what the application actually committed, denied, or
deduplicated under a grant.

```json
{
  "receipt_id": "receipt_app_abc",
  "receipt_type": "app",
  "grant_id": "grant_123",
  "session_id": "sess_456",
  "action_id": "comment.create",
  "app_id": "code.example.com",
  "surface_version": "code-review-agent-surface/0.1",
  "runtime": {
    "runtime_id": "application_runtime_456"
  },
  "actor_agent": {
    "agent_id": "local_agent_789",
    "passport_hash": "sha256:..."
  },
  "subject": {
    "user": "user_abc"
  },
  "idempotency_key": "idem_01HX7DS8AC6G9",
  "input_hash": "sha256:...",
  "output_hash": "sha256:...",
  "approved_by": {
    "type": "runtime_user_approval",
    "approval_id": "appr_123"
  },
  "resource": {
    "type": "comment",
    "id": "comment_789"
  },
  "timestamp": "2026-06-25T16:30:00Z",
  "result": "success",
  "links": {
    "runtime_receipt_hash": "sha256:..."
  }
}
```

Receipts MAY be signed by the app, runtime, or both. A future draft is expected
to define canonicalization and signature profiles.

## Revocation Semantics

The protocol MUST define what happens when authority changes.

### Grant Revoked

If a grant is revoked:

- runtime MUST stop initiating new actions under that grant
- app MUST reject new actions under that grant
- active sessions SHOULD be cancelled or downgraded to read-only according to
  app policy
- receipt generation SHOULD record the revocation event

### Runtime Disconnected

If the runtime disconnects:

- app SHOULD mark active runtime-mediated sessions as interrupted
- app MUST NOT treat pending runtime approvals as approved
- app MAY allow resumable sessions when the same runtime reconnects

### Agent Passport Revoked or Expired

If an Agent Passport is revoked or expired:

- runtime MUST stop launching that agent for new sessions
- runtime SHOULD cancel or pause active sessions unless policy explicitly allows
  completion
- grants bound to the passport SHOULD be suspended or require re-consent

### Surface Version Changed

If the Agent Surface changes incompatibly:

- app SHOULD publish a new `surface_version`
- runtime SHOULD re-fetch and re-validate schemas
- grants bound to incompatible actions SHOULD require renewal

### User Session Expired

If the user's ordinary app session expires, app policy decides whether existing
agent grants continue. High-risk grants SHOULD expire with or before the user
session unless explicitly configured otherwise.

## Error Model

Agent Surface Protocol SHOULD define structured errors:

| Error | Meaning |
| --- | --- |
| `grant_missing` | No grant was supplied or found. |
| `grant_expired` | Grant has expired. |
| `grant_revoked` | Grant was revoked. |
| `grant_proof_invalid` | Grant credential or proof is missing, invalid, or not bound correctly. |
| `scope_denied` | Grant scope does not permit the action. |
| `resource_denied` | Grant constraints do not permit the target resource. |
| `approval_required` | Required approval is absent. |
| `schema_invalid` | Input or output does not match the declared schema. |
| `idempotency_conflict` | Idempotency key was reused with different input. |
| `risk_denied` | Local or app policy denied the risk class. |
| `passport_invalid` | Agent Passport is missing, expired, revoked, or invalid. |
| `runtime_untrusted` | Runtime binding or attestation is not accepted. |
| `surface_incompatible` | Runtime does not support the surface version. |
| `proposal_required` | The app only supports proposal mode for this action or grant. |

Errors SHOULD be safe to show to users and precise enough for runtime policy
debugging.

## Versioning and Compatibility

Surface manifests SHOULD include:

```json
{
  "protocol": "agent-surface/0.1",
  "surface_version": "2026-06-25",
  "compatibility": {
    "min_runtime": "application-runtime/0.1",
    "schema_dialect": "https://json-schema.org/draft/2020-12/schema"
  }
}
```

Compatibility rules:

- Removing an action is a breaking change for grants that include that action.
- Tightening a schema can be a breaking change.
- Adding optional fields is non-breaking.
- Adding a new action is non-breaking.
- Changing risk labels to a higher risk class can require grant renewal.
- Changing receipt requirements can require grant renewal.
- Changing endpoint semantics can require grant renewal.

Applications SHOULD keep old surface versions available long enough for active
grants to expire naturally.

## Security Considerations

### Threat Model Summary

This draft assumes several possible adversarial or failure modes:

- malicious or compromised agent
- malicious or compromised runtime
- malicious or compromised application
- compromised app user session
- prompt-injected app content
- stolen grant credential
- replaying network attacker
- confused-deputy runtime
- stale or downgraded surface manifest
- forged or misleading receipts

Agent is untrusted by default. Runtime is trusted by the user only within local
policy bounds, but the app MUST verify app-side authorization. App is trusted for
its own resources, but not for the user's local machine. Passport is evidence,
not authority. Grant is authority only within caveats.

### Confused Deputy

The runtime can accidentally use a grant for the wrong agent, user, workspace, or
application. Grants SHOULD bind user, app, runtime, agent, and passport hash.

### Raw Token Leakage

If an agent process receives raw app tokens, the runtime loses mediation control.
The preferred architecture is:

```text
Agent -> Runtime -> App
```

The runtime holds or obtains credentials and exposes only typed action results to
the agent.

### Malicious or Compromised Runtime

Applications MUST NOT trust runtime claims blindly. Every app action MUST be
authorized by app-verifiable grant state.

Mitigations:

- app-issued grants
- token introspection
- runtime binding
- passport hash binding
- sender-constrained grant credentials
- action-scoped grants
- app-side receipts
- anomaly detection

### Malicious or Compromised Agent

Agents can hallucinate, loop, ignore instructions, leak data, or attempt
unauthorized actions.

Mitigations:

- no direct credentials in agent process
- schema validation
- risk-based approval
- action count limits
- cost limits
- sandboxing
- local audit log
- Agent Passport verification
- proposal mode

### Malicious or Compromised Application

An application can request excessive scopes, misleading consent, or dangerous
actions.

Mitigations:

- runtime presents grant details clearly
- local policy can deny high-risk surfaces
- user can revoke app grants locally
- app manifest can be pinned or allowlisted
- enterprise policy can restrict issuers

### Stolen Grant Credential

A grant credential can be stolen from runtime storage, logs, memory, or network
traffic.

Mitigations:

- short-lived grants
- sender-constrained tokens
- DPoP or mTLS binding where practical
- token introspection
- revocation
- action count limits
- resource constraints
- anomaly detection
- no tokens in URLs

### Prompt Injection

App data and repository content are untrusted input. Agents SHOULD NOT interpret
application content as authority to escalate scopes, reveal secrets, or bypass
policy.

Runtime and app policies SHOULD treat model output as untrusted until validated.

### Replay and Duplicate Actions

Idempotency keys, timestamps, nonce binding, and grant expiration reduce replay
risk. Side-effecting actions MUST be idempotent.

### Surface Downgrade

A malicious network or compromised app path can present an older, less safe
surface version. Runtimes SHOULD pin issuer, app id, and minimum accepted
protocol versions where possible.

### Receipt Forgery

Receipts SHOULD be hash-linked to normalized inputs and outputs. Future drafts
are expected to define signing and canonicalization profiles.

## Privacy Considerations

Agent Surface Protocol can reveal sensitive metadata:

- which agents the user owns
- which runtime the user runs
- which app resources the user delegates
- which tasks the user asks agents to perform
- which approvals were accepted or denied

Applications SHOULD request only the metadata needed for authorization and audit.
Runtimes SHOULD minimize agent and passport disclosure when possible. Receipts
SHOULD support pseudonymous user references where legal and operationally
appropriate.

## Conformance

This draft defines conformance profiles instead of a single all-or-nothing
profile.

### Surface-Only Application

An application conforms to the Surface-Only profile when it:

- publishes an Agent Surface Manifest
- declares actions, resources, events, scopes, and schemas
- declares risk labels for actions
- declares endpoints or explicitly marks the surface as proposal/documentation
  only
- provides proposal-mode actions or read-only resources

### Grant-Enforcing Application

An application conforms to the Grant-Enforcing profile when it:

- satisfies the Surface-Only profile
- issues, validates, or introspects Agent Grants
- validates grant state for every action
- treats `grant_id` as an identifier, not authority
- supports idempotency for side-effecting actions
- supports grant revocation

### Receipt-Producing Application

An application conforms to the Receipt-Producing profile when it:

- satisfies the Grant-Enforcing profile
- emits app receipts for required side-effecting actions
- links receipts to grant id, session id, action id, agent id, runtime id, and
  idempotency key
- records denied or failed high-risk actions

### Application Runtime Profile

An application runtime conforms to this profile when it:

- discovers and validates Agent Surface Manifests
- verifies Agent Passport evidence before delegation
- obtains explicit user consent before storing a grant
- mediates agent actions instead of exposing raw authority
- enforces local policy and approval rules
- validates action input against schemas before sending to the app
- records local audit events and runtime receipts
- stops actions when grants are revoked or expired

### Agent Adapter

An adapter conforms to this draft when it:

- runs under runtime supervision
- does not require raw app credentials
- requests app actions through runtime APIs
- emits typed events
- handles denials and approval waits
- preserves session and grant identifiers in audit context

## Application MVP Mapping

An application implementation can start with a small runtime bridge:

- outbound WebSocket from runtime to control plane
- `runtime.hello`
- typed `session.start`
- normalized `session.event`
- local policy evaluation
- local approvals
- agent adapter boundary

To support Agent Surface Protocol, the next slices are:

1. Add `AgentSurfaceManifest` TypeScript types and JSON examples.
2. Add `AgentGrant` TypeScript types and validation helpers.
3. Add surface discovery to the demo control plane.
4. Add a grant consent screen in the demo browser UI.
5. Bind session start to a grant id.
6. Add `action.request` and `action.result` events.
7. Split `comment.propose` from `comment.create` in the demo.
8. Require idempotency keys for write actions.
9. Produce local runtime receipts and app-visible receipts.
10. Integrate Agent Passport verification as an admission precondition.

## Example End-to-End Flow

```text
1. App publishes /.well-known/agent-surface.json.
2. Application runtime discovers and validates the surface.
3. User chooses "Connect my local agent".
4. Runtime verifies the selected agent's Agent Passport.
5. Runtime shows consent:
   - app: code.example.com
   - agent: local-agent
   - scopes: pull_request.read, pull_request.comment
   - repository: example-org/example-repo
   - duration: 2 hours
   - writes: require approval
6. User approves.
7. App issues grant_123 and a grant credential.
8. Runtime stores grant_123 and the grant credential.
9. App starts a pull-request review session.
10. Agent reads typed PR context through runtime-mediated resources.
11. Agent proposes a review comment.
12. User or app approves the write.
13. Runtime sends comment.create with an idempotency key and grant credential.
14. App verifies grant and writes the comment.
15. Runtime and app issue linked receipts.
16. User revokes grant or grant expires.
```

## Open Questions

- Does the first MVP use app-issued grants only, or also support
  runtime-held grants for compatibility with existing OAuth APIs?
- What is the minimal Agent Passport verification profile required before a
  runtime can request an Agent Grant?
- Does grant binding require runtime attestation, or is a registered runtime id
  enough for early implementations?
- Are receipts signed in the first version, or only hash-linked and
  locally stored?
- Which JSON canonicalization profile is used for signed grants and
  receipts?
- Is `/.well-known/agent-surface.json` public, authenticated, or both
  depending on app tenancy?
- What is the minimal sender-constrained grant credential profile?
- How do users compare two agents with overlapping Agent Passport
  capabilities during grant consent?
- What happens to active sessions when an app changes surface versions?

## References

- Model Context Protocol Specification:
  <https://modelcontextprotocol.io/specification/2025-06-18>
- Agent Client Protocol Overview:
  <https://agentclientprotocol.com/protocol/v1/overview>
- OAuth 2.0:
  <https://www.rfc-editor.org/rfc/rfc6749>
- OAuth 2.0 Token Revocation:
  <https://www.rfc-editor.org/rfc/rfc7009>
- OAuth 2.0 Token Introspection:
  <https://www.rfc-editor.org/rfc/rfc7662>
- OAuth 2.0 Token Exchange:
  <https://www.rfc-editor.org/rfc/rfc8693>
- OAuth 2.0 Resource Indicators:
  <https://www.rfc-editor.org/rfc/rfc8707>
- Key words for use in RFCs to Indicate Requirement Levels:
  <https://www.rfc-editor.org/rfc/rfc2119>
- Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words:
  <https://www.rfc-editor.org/rfc/rfc8174>
- JSON Schema Draft 2020-12:
  <https://json-schema.org/draft/2020-12>
- YAML 1.2.2:
  <https://github.com/yaml/yaml-spec/blob/main/spec/1.2.2/spec.md>
- DID Core:
  <https://www.w3.org/TR/did-core/>
- Verifiable Credentials Data Model 2.0:
  <https://www.w3.org/TR/vc-data-model-2.0/>
- Agent Passport draft repository:
  <https://github.com/0al-spec/agent-passport>

## Appendix A: Why This Is Not Just an API Token

An API token answers:

```text
Can this bearer call this endpoint?
```

An Agent Grant answers:

```text
Which user delegated which agent, running through which runtime, verified by
which passport evidence, to perform which typed app actions, against which
resources, under which caveats, until when, with which approval and receipt
requirements?
```

The second question is the actual security and product problem.

## Appendix B: Why This Is Not Just Computer Use

Computer use automates a UI from the outside. It is useful when no better
surface exists.

Agent Surface Protocol asks applications to expose an agent-native surface:

- typed reads
- typed proposals
- typed writes
- typed events
- scopes
- schemas
- approvals
- idempotency
- receipts
- revocation

The app remains in control of its resource model, and the user remains in control
of agent delegation.

## Appendix C: Product Positioning

Short form:

```text
Agent Surface Protocol lets users safely bring their own agents to apps.
```

Long form:

```text
Agent Surface Protocol is a user-mediated delegation protocol for connecting
user-owned agents to application-defined, app-enforced, typed action surfaces
through a policy-enforcing runtime.
```

Comparison:

```text
MCP exposes tools.
ACP connects clients to agents.
OAuth delegates access.
Agent Passport proves agent identity and capabilities.
Agent Surface + Agent Grant bind those pieces into safe app-specific delegation.
```
