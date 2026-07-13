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
the resources, actions, events, scopes, risk labels, execution modes, effect
dimensions, approval requirements, schemas, preconditions, reservations,
compensation links, idempotency rules, receipts, endpoints, and revocation
semantics it supports. The user chooses a local or remote agent they own. An application
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

- Conventions
- Terminology
- Design Principles
- Agent Surface Manifest
- Action Execution Model
- Risk Taxonomy
- Effect Model
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
- Goals
- Non-Goals
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
  risk labels, execution modes, effect dimensions, preconditions, reservation
  and compensation relationships, idempotency rules, approval hints, receipt
  requirements, and wire-level endpoints.
- Let runtimes verify Agent Passports before an agent can receive delegated work.
- Require both runtime-side and app-side enforcement.
- Avoid direct application credentials in agent processes where practical.
- Make proposal-first workflows the default safety posture:

  ```text
  read -> propose -> approve -> commit -> receipt
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

The key words "MUST", "MUST NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", and
"MAY" in this document are to be interpreted in the RFC 2119 and RFC 8174 sense
when, and only when, they appear in all capitals.

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

For agent-initiated access to an Agent Surface, the runtime is the reference
monitor. It is the only component allowed to mediate an agent's requested
application actions: it evaluates local policy, grant caveats, approvals, and
redaction before an action reaches the application. This does not make the
runtime the final authority; the application remains responsible for verifying
the grant on every action.

### Agent Passport

[Agent Passport](https://github.com/0al-spec/agent-passport) is identity and
capability evidence for an agent. It can describe the agent, its declared
capabilities, resource requirements, security policies, integrity hashes,
lifecycle, issuer, and signature.

An Agent Passport does **not** by itself grant authority inside an application.
It answers "what is this agent and what has been attested about it?" A grant
answers "what has this user allowed this runtime-agent-passport tuple to do in
this application context?"

Passport is evidence, not authority.

### Agent Grant

A user-approved, app-scoped, policy-bound delegation object.

The grant is the semantic authorization. Tokens, cookies, JWTs, capability URLs,
sender-constrained credentials, or signed objects are transport representations.
A grant SHOULD be temporary, constrained, auditable, and revocable. A
conforming grant MUST bind the user, application, runtime, agent, and passport
evidence that it authorizes. A credential presentation MUST let the application
verify that binding directly or retrieve it from authoritative grant state.

### Grant Credential

A concrete credential or proof used to represent or prove an Agent Grant on the
wire. Examples include opaque bearer tokens, sender-constrained tokens, DPoP
proofs, mTLS-bound tokens, JWTs, macaroon-like capabilities, signed delegation
objects, or app-side server sessions.

A `grant_id` is an identifier. It is not, by itself, authority.

Grant credentials are runtime-held by default. Releasing a raw credential into
an agent-visible process, tool, prompt, environment, or model context is a
privileged `credential.release` capability and is denied unless the grant
explicitly permits it. The Grant Credential that authorizes Agent Surface
actions is never releasable under this capability.

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

Every action has exactly one manifest-declared execution mode. Related actions
can represent preview, reservation, commit, compensation, or revert stages of
one logical operation, but each related action retains its own scope, risk,
approval, idempotency, and receipt requirements.

### Action Execution Context

The per-request object that identifies the manifest-declared mode and binds any
preview, precondition, expected-effect, reservation, or recovery evidence used
for one invocation. Its canonical `execution_hash` is distinct from the
business input's `input_hash`.

### Resource

A typed object or collection exposed by an Agent Surface. Examples:

- `pull_request`
- `issue`
- `task`
- `document`
- `invoice`

### Data Exposure Declaration

A manifest-pinned declaration of the maximum application-originated data that
can become visible to a runtime or agent through a resource, action, or event.
The contract names data classes and defines the redaction and retention
obligations that apply after disclosure. It describes and constrains exposure;
it does not grant authority to read a resource, invoke an action, receive an
event, or release a credential.

### Consent Preview Projection

A user-facing, runtime-derived projection of the exact proposed Agent Grant,
the verified runtime-agent-passport tuple, and the pinned manifest semantics
that materially affect authority, effects, and data exposure. The projection
helps a user decide whether to continue; it is not a credential, approval
object, or substitute for authorization-server consent.

### Execution Preview

An application-produced prediction of the preconditions and expected effects
for a possible later commit. A preview is time-bounded evidence about observed
state. It is not authority, approval, a reservation, or a promise that the
commit will still succeed.

### Resource Reservation

Time-bounded application coordination state that gives one grant-bound holder
priority to attempt a declared commit against named resources. A reservation is
not a grant, credential, approval, or guarantee that the commit will succeed.

### Compensation

A new action intended to offset some or all effects of an earlier committed
action. Compensation is independently authorized and can be partial or fail. A
revert is the narrower case in which the application can restore a declared
prior state.

### Event

A typed notification exposed by an Agent Surface or runtime. Examples:

- `review.requested`
- `ci.failed`
- `task.created`
- `grant.revoked`

### Receipt

Portable evidence that an action occurred, including the grant, session, agent,
passport hash, input and execution hashes, effects, approval, timestamp, and
result.

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

Every agent-initiated action against an Agent Surface MUST traverse the runtime.
An agent, adapter, tool, or subagent MUST NOT call an Agent Surface with an
independently obtained application credential or another authorization path that
bypasses runtime mediation. The runtime's reference-monitor role does not
replace application-side verification: the application MUST still enforce its
own grant authority and resource policy for every action.

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

An agent MUST NOT receive the grant secret, OAuth access token, cookie, session
key, or broad application credential by default. The agent MUST request typed
actions from the runtime:

```text
Agent -> Runtime -> App Agent Surface
```

The runtime can then enforce local policy, approvals, idempotency, auditing, and
redaction before sending anything to the app.

A runtime MAY release a raw credential only under an explicitly authorized
`credential.release` capability. The released credential MUST be newly issued,
target-bound, attenuated to a non-Agent-Surface audience, and unusable at every
Agent Surface endpoint. The application MUST reject that credential if it is
presented to an Agent Surface endpoint. A Grant Credential, app session, or
other credential that can authorize Agent Surface actions MUST NOT be released.

The grant MUST name the credential class, target agent identity and passport
hash, non-Agent-Surface resource-server audience, permitted scopes, expiration,
and required approval. The release MUST be shown during consent, require the
specified approval before delivery, and produce both a runtime receipt and an
app receipt where the application participates. Absence of this capability
means denial; a general action grant or an agent's request MUST NOT imply
credential release. A future direct-access profile would require a separate
authority model and is outside this draft.

### Proposal Mode Is the Default

The first safe interaction mode SHOULD be:

```text
read -> draft/propose -> human or app approval -> commit -> receipt
```

Direct writes without approval can exist for mature grants and low-risk actions,
but the protocol SHOULD make proposal flows first-class.

### Every Write Is Idempotent

Any action that changes domain or coordination state MUST support idempotency.
This includes `reserve`, `commit`, `compensate`, and `revert`. Retries, network
reconnects, agent loops, and duplicate messages MUST NOT create ten
reservations, comments, branches, refund requests, compensations, or approvals.

### Receipts Are First-Class

Audit logs are useful, but action receipts are portable. A receipt SHOULD be
created for every successful side-effecting action and for important denied or
failed actions.

## Relationship to Existing Protocols

### Model Context Protocol

The Model Context Protocol specification describes an open protocol for
connecting LLM applications to external data sources and tools:

<https://modelcontextprotocol.io/specification/2025-06-18>

MCP is primarily a context and tool integration protocol for agents and LLM
applications. It helps an agent reach external data sources and tools, including
data and operations that live inside applications, so the agent can enrich its
working context and call available tools.

That is different from admitting a user-owned agent into an application authority
model. MCP servers, direct CLI integrations, and direct API integrations can be
useful substrates below an agent or runtime, but they do not by themselves define
an app-native delegation contract, user-approved Agent Grants, app-side grant
enforcement, risk labels, approval semantics, revocation semantics, or portable
receipts.

More importantly, MCP makes agents more capable, but it does not by itself make
ordinary applications agentic. In an MCP-only integration, the application often
remains a data source or tool provider reached from the outside:

```text
MCP-only:
User <-> Application <- Agent <-> User
```

Agent Surface Protocol is the application augmentation layer. It gives an
ordinary application a typed way to accept a user-owned agent as a delegated
participant in application workflows:

```text
ASP:
User <-> Application <-> Agent <-> User
```

At the product level, this collapses into a simpler user experience:

```text
User <-> AI-App
```

In this framing, the agent is not merely extracting application data to enrich
its own context. The application itself becomes AI-augmented: it exposes typed
affordances, receives user-authorized agent participation, and can render,
approve, constrain, revoke, and receipt agent work as part of the application
experience.

### Agent Client Protocol

Agent Client Protocol focuses on communication between clients such as editors
and coding agents, including local and remote agent scenarios:

<https://agentclientprotocol.com/protocol/v1/overview>

ACP can be an Agent Adapter Protocol below an application runtime. Agent Surface
Protocol does not replace ACP; it defines how a user grants a user-owned agent
authority inside an application context.

Where ACP places environment management, user interaction, and resource access
under the Client role, ASP makes those responsibilities explicit as
Application-owned surfaces, grants, approvals, and receipts.

The practical composition is not "ASP or ACP". ACP can sit inside an
application, wrapped by ASP as the application-facing augmentation layer. In
Hypercode structural notation, with `.hcs` values and contracts omitted:

```hypercode
AIApplication
  UserInterface
  AgentSurfaceProtocolLayer
    ApplicationResources
    ApplicationActions
    AgentGrantRegistry
    ApprovalPolicy
    ActionReceiptLog
    ACPAgentAdapter
      ApplicationRuntimeClient
      UserOwnedAgent
      AgentSession
```

In that shape, ACP standardizes the operational conversation between the
application runtime and the agent. ASP defines the application shell around that
conversation: what the application exposes, what the user delegates, what the
agent can do inside the product, and how the product presents, approves,
constrains, revokes, and receipts agent participation.

```text
ACP:
ApplicationRuntime <-> Agent

ASP around ACP:
User <-> Application
          |
          +-- ASP layer
              |
              +-- ACP adapter <-> Agent

Product view:
User <-> AI-App
```

### OAuth

OAuth 2.0 remains a practical substrate for consent, authorization codes, scopes,
refresh, revocation, token introspection, token exchange, and resource
indicators.

Relevant standards:

- OAuth 2.0: <https://www.rfc-editor.org/rfc/rfc6749>
- OAuth 2.0 Proof Key for Code Exchange:
  <https://www.rfc-editor.org/rfc/rfc7636>
- OAuth 2.0 Token Revocation: <https://www.rfc-editor.org/rfc/rfc7009>
- OAuth 2.0 Token Introspection: <https://www.rfc-editor.org/rfc/rfc7662>
- OAuth 2.0 Token Exchange: <https://www.rfc-editor.org/rfc/rfc8693>
- OAuth 2.0 Resource Indicators: <https://www.rfc-editor.org/rfc/rfc8707>
- OAuth 2.0 Rich Authorization Requests:
  <https://www.rfc-editor.org/rfc/rfc9396>
- OAuth 2.0 Pushed Authorization Requests:
  <https://www.rfc-editor.org/rfc/rfc9126>
- Best Current Practice for OAuth 2.0 Security:
  <https://www.rfc-editor.org/rfc/rfc9700>

Agent Surface Protocol uses the term **grant** for the semantic object,
even when an OAuth access token is the transport representation.

The OAuth Grant Lifecycle Profile in this draft uses standard OAuth flows and
extension parameters; it does not define an `agent_delegation` OAuth grant type.
Implementations MAY use:

- Authorization Code with PKCE and an Agent Grant
  `authorization_details` object.
- OAuth Token Exchange to exchange a user-authorized credential for an
  agent-scoped grant credential.
- Resource Indicators to constrain the resource server or app surface.

The collision-resistant authorization-details type identifier defined by this
draft is:

```text
https://github.com/0al-spec/agent-surface/authorization-details/agent-grant
```

### Agent Passport

[Agent Passport](https://github.com/0al-spec/agent-passport) provides agent
identity, capability, policy, lifecycle, signature, and integrity evidence.

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
- execution modes and companion-action relationships
- effect dimensions
- precondition and expected-effect schemas
- reservation and compensation semantics
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
- `event.subscribe`
- `event.subscribed`
- `event.delivery`
- `event.ack`
- `event.replay`
- `event.flow`
- `event.gap`
- `session.start`
- `session.event`
- `session.cancel`
- `session.resume`
- `session.state`
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

## Canonical Integrity and Provenance

### Canonical Object Hash Profile

ASP manifests, grants, action inputs, action execution contexts, policy decisions, and receipts use the
`asp-jcs-sha-256` profile when a field in this draft is named `surface_hash`,
`grant_hash`, `input_hash`, `execution_hash`, `preconditions_hash`,
`expected_effects_hash`, `actual_effects_hash`, `policy_decision_hash`,
`receipt_hash`, or `parent_receipt_hash`. The profile identifies exact JSON
content; it does not by itself authenticate the producer or grant authority.

To compute an ASP object hash, an implementation MUST:

1. Construct the hashing view for the object type according to the table below.
2. Reject input that is not valid I-JSON, including duplicate object member
   names, non-Unicode strings, or numbers that cannot be represented as IEEE
   754 binary64 values. JSON negative zero also MUST be rejected rather than
   normalized to positive zero.
3. Construct an object with exactly two members: `domain`, containing the
   domain URI from the table, and `object`, containing the hashing view.
4. Serialize that wrapper with the JSON Canonicalization Scheme defined by RFC
   8785. Object members are sorted by JCS; array order is preserved and is
   therefore significant to the resulting hash. No additional Unicode, URI,
   timestamp, default-value, or array normalization is performed.
5. Compute SHA-256 over the canonical UTF-8 wrapper bytes.
6. Encode the digest with the RFC 4648 base64url alphabet without `=` padding
   and prepend the literal `sha-256:`.

| Object | Domain URI | Hashing view exclusions |
| --- | --- | --- |
| Agent Surface Manifest | `https://github.com/0al-spec/agent-surface/hash/manifest/v1` | top-level `surface_hash` |
| authoritative Agent Grant | `https://github.com/0al-spec/agent-surface/hash/grant/v1` | top-level `grant_hash`; the RFC 9396 `type` discriminator when starting from an OAuth authorization-details object |
| Action Request `input` | `https://github.com/0al-spec/agent-surface/hash/action-input/v1` | none; the hashing view is exactly `payload.input` after schema validation and before default insertion, coercion, or other semantic normalization |
| Action Execution Context | `https://github.com/0al-spec/agent-surface/hash/action-execution/v1` | `execution_token`; the hashing view is `payload.execution` after structural validation with the confidential raw token omitted |
| Action Preconditions | `https://github.com/0al-spec/agent-surface/hash/action-preconditions/v1` | none; the hashing view is exactly the validated `preconditions` object |
| Expected Effects | `https://github.com/0al-spec/agent-surface/hash/expected-effects/v1` | none; the hashing view is exactly the validated `expected_effects` array |
| Actual Effects | `https://github.com/0al-spec/agent-surface/hash/actual-effects/v1` | none; the hashing view is exactly the validated `actual_effects` array |
| Policy Decision Object | `https://github.com/0al-spec/agent-surface/hash/policy-decision/v1` | top-level `policy_decision_hash` |
| receipt | `https://github.com/0al-spec/agent-surface/hash/receipt/v1` | top-level `receipt_hash` and `receipt_signatures` |

All other members, including extension members, are part of the hashing view.
Omitting an unknown member before hashing is therefore an integrity failure,
not extension tolerance. A party that receives a redacted or filtered object
MAY carry its hash as an opaque reference but MUST NOT claim to have recomputed
it without the complete hashing view.

The Action Input hash commits to the exact validated wire input and prevents a
receipt from being attached to different input. It is distinct from the
action-specific semantic normalization used for idempotency; JCS does not
define default insertion, equivalence, or set ordering.

The Action Execution Context hash independently commits to the mode and any
preview, precondition, expected-effect, reservation, or target-receipt
references used for the request. The raw `execution_token` is omitted because
it is confidential runtime-held material; the context instead carries its
`execution_token_hash`. It prevents the non-secret controls from being changed
while reusing an `input_hash`. It does not make a preview, reservation, or
target receipt into authority; the application still verifies the current
grant, policy, approval, resource state, and mode-specific rules atomically.

`execution_token_hash` is not a JCS object hash. The producer MUST generate at
least 128 bits of entropy with a cryptographically secure random-number
generator and encode the resulting 16 or more octets with unpadded RFC 4648
base64url. Its hash is the SHA-256 digest of those decoded token octets, encoded
with the same unpadded `sha-256:` base64url representation. A receiver can
validate syntax and decoded length, not entropy quality; it MUST reject padding,
non-base64url characters, or fewer than 16 decoded octets.
The raw token MUST be sent only over the authenticated confidential action
channel, and MUST NOT appear in a receipt, log, prompt, event, or agent-visible
context.

For the example token `FW_vZMMelqPUDUmFfxSr1A`, the required token hash is
`sha-256:tONJJscZ4IsDBfafODsBja4waqe1AtkpH54rXv_tPrk`.

The following minimal vector fixes the domain separation, wrapper, JCS, and
encoding rules. For the Grant domain and hashing view
`{"grant_id":"grant_123","scopes":["read"]}`, the canonical wrapper is:

```json
{"domain":"https://github.com/0al-spec/agent-surface/hash/grant/v1","object":{"grant_id":"grant_123","scopes":["read"]}}
```

Its hash value is:

```text
sha-256:Xbq37_fP9PBiWI3Bv7Ch0t8TV5ikJGm55MxncSeA38Y
```

The following manifest vector demonstrates self-field exclusion and nested JCS
member ordering. Given this received object:

```json
{"z":1,"surface_hash":"sha-256:Mckhl9gi8ePkXnuOJtPFNE1pe9LhilOGu1OgzxsXb8A","a":"x"}
```

the hashing view omits `surface_hash`, and the canonical wrapper is:

```json
{"domain":"https://github.com/0al-spec/agent-surface/hash/manifest/v1","object":{"a":"x","z":1}}
```

The recomputed value is `sha-256:Mckhl9gi8ePkXnuOJtPFNE1pe9LhilOGu1OgzxsXb8A`.
Inputs containing duplicate members, JSON negative zero, a lone Unicode
surrogate, or numeric input that would overflow binary64 to a non-finite value
are negative vectors and MUST be rejected before hashing.

An implementation MUST treat a supplied hash that does not match a recomputed
hash as invalid. It MUST NOT fall back to `grant_id`, `surface_version`,
`receipt_id`, or another mutable identifier. Hash-profile agility requires a
future profile with a distinct identifier and domain URI; silently substituting
a different digest or canonicalization algorithm is forbidden.

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

The manifest MUST be served over HTTPS and SHOULD be served with:

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
  "surface_hash": "sha-256:<base64url-digest>",
  "surface_url": "https://example.com/.well-known/agent-surface.json",
  "auth": {},
  "agent_api": {},
  "scopes": [],
  "data_classes": [],
  "resources": [],
  "actions": [],
  "events": [],
  "audit": {},
  "revocation": {}
}
```

### Surface Hash

Every manifest MUST contain `surface_hash` computed with the Canonical Object
Hash Profile over the complete manifest hashing view. A runtime MUST recompute
and verify it before using the manifest for capability matching, consent, grant
issuance, or action validation. The authorization server MUST perform the same
check before embedding the value in a grant.

`surface_version` remains the application's opaque compatibility label;
`surface_hash` identifies the exact manifest object published under that label,
including schema URLs but not the transitive bytes served by those URLs. A
runtime MUST key cached surface state by issuer, app id, surface version, and
surface hash. A publisher MUST issue a new `surface_version` whenever the
manifest hashing view changes, including for a backward-compatible addition.
If the same issuer, app id, and `surface_version` appears with a different
`surface_hash`, the runtime MUST treat it as an integrity failure and MUST NOT
silently replace the pinned object.

The hash authenticates neither the issuer nor the transport. Runtimes MUST
still enforce HTTPS, issuer and app-id binding, and any local pinning policy.

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
    "event_delivery": {
      "profile": "at_least_once",
      "ack_deadline_seconds": 30,
      "max_in_flight": 32,
      "retention_seconds": 86400
    },
    "receipt_url": "https://example.com/agent-receipts"
  },
  "revocation": {
    "grant_management_url": "https://example.com/settings/agent-grants",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "event": "grant.revoked"
  }
}
```

When `event_subscription_url` is present, `agent_api.event_delivery` is
REQUIRED. This draft defines only the `at_least_once` profile. Its
`ack_deadline_seconds`, `max_in_flight`, and `retention_seconds` members MUST be
positive integers. `ack_deadline_seconds` is the retry deadline,
`max_in_flight` is the largest negotiable application-event window, and
`retention_seconds` is the conditional replay commitment defined below. A
runtime MAY request a smaller in-flight window. An `event.subscribed` response
MUST repeat the advertised acknowledgement deadline and retention window and
MUST NOT return a larger in-flight window. Changing any of these values changes
the manifest hashing view and requires a new `surface_version` and
`surface_hash`.

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
  "surface_hash": "sha-256:<base64url-digest>",
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
    "grant_types_supported": [
      "authorization_code",
      "urn:ietf:params:oauth:grant-type:token-exchange"
    ],
    "authorization_details_types_supported": [
      "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant"
    ],
    "token_binding": ["runtime", "agent_passport_hash"],
    "pkce_required": true
  },
  "agent_api": {
    "grant_request_url": "https://example.com/agent-grants/request",
    "grant_introspection_url": "https://example.com/agent-grants/introspect",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "action_url": "https://example.com/agent-actions",
    "event_subscription_url": "https://example.com/agent-events",
    "event_delivery": {
      "profile": "at_least_once",
      "ack_deadline_seconds": 30,
      "max_in_flight": 32,
      "retention_seconds": 86400
    },
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
  "data_classes": [
    {
      "id": "grant.metadata",
      "classification": "sensitive",
      "label": "Grant metadata",
      "description": "Identifiers and lifecycle state for an Agent Grant."
    },
    {
      "id": "repository.content",
      "classification": "private",
      "label": "Repository content",
      "description": "Content visible to the connected repository user."
    },
    {
      "id": "user.identifier",
      "classification": "sensitive",
      "label": "User identifiers",
      "description": "Stable account identifiers associated with repository content."
    }
  ],
  "resources": [
    {
      "id": "task",
      "read_scope": "tasks.read",
      "schema": "https://example.com/schemas/task.schema.json",
      "data_exposure": {
        "classes": ["repository.content", "user.identifier"],
        "redaction": {
          "mode": "policy",
          "policy_id": "repository-visible-fields-only",
          "summary": "Only fields visible to the connected repository user are returned."
        },
        "retention": {
          "mode": "bounded",
          "max_seconds": 7200,
          "delete_on_grant_end": true
        }
      }
    }
  ],
  "actions": [
    {
      "id": "comment.propose",
      "scope": "comments.propose",
      "risk": "propose",
      "side_effect": false,
      "approval": "none",
      "idempotency": "required",
      "execution": {
        "mode": "propose",
        "operation_id": "comment.publish",
        "persisted": true,
        "commit_action": "comment.create"
      },
      "input_schema": "https://example.com/schemas/comment-propose.input.schema.json",
      "output_schema": "https://example.com/schemas/comment-propose.output.schema.json",
      "data_exposure": {
        "classes": ["repository.content"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    },
    {
      "id": "comment.create",
      "scope": "comments.write",
      "risk": "write",
      "side_effect": true,
      "effects": [
        {
          "effect_id": "comment-publish",
          "operation": "publish",
          "resource_type": "comment",
          "visibility": "shared",
          "boundary": "internal",
          "reversibility": "irreversible",
          "domain": "communication"
        }
      ],
      "approval": "user_or_app",
      "idempotency": "required",
      "input_hash_profile": "asp-jcs-sha-256",
      "execution_hash_profile": "asp-jcs-sha-256",
      "execution": {
        "mode": "commit",
        "operation_id": "comment.publish",
        "proposal_action": "comment.propose"
      },
      "input_schema": "https://example.com/schemas/comment-create.input.schema.json",
      "output_schema": "https://example.com/schemas/comment-create.output.schema.json",
      "data_exposure": {
        "classes": ["repository.content"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      },
      "receipt": "required"
    }
  ],
  "events": [
    {
      "id": "task.created",
      "scope": "tasks.read",
      "schema": "https://example.com/schemas/task-created.event.schema.json",
      "data_exposure": {
        "classes": ["repository.content", "user.identifier"],
        "redaction": {
          "mode": "policy",
          "policy_id": "repository-visible-fields-only",
          "summary": "Only fields visible to the connected repository user are returned."
        },
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    },
    {
      "id": "review.requested",
      "scope": "tasks.read",
      "schema": "https://example.com/schemas/review-requested.event.schema.json",
      "data_exposure": {
        "classes": ["repository.content", "user.identifier"],
        "redaction": {
          "mode": "policy",
          "policy_id": "repository-visible-fields-only",
          "summary": "Only fields visible to the connected repository user are returned."
        },
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    },
    {
      "id": "grant.revoked",
      "control": true,
      "schema": "https://example.com/schemas/grant-revoked.event.schema.json",
      "data_exposure": {
        "classes": ["grant.metadata"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    }
  ],
  "audit": {
    "hash_profile": "asp-jcs-sha-256",
    "receipt_schema": "https://example.com/schemas/action-receipt.schema.json",
    "receipt_signing": {
      "profiles_supported": ["asp-jws-detached"],
      "algorithms_supported": ["ES256"],
      "jwks_uri": "https://example.com/.well-known/agent-surface-receipt-jwks.json"
    },
    "required_fields": [
      "receipt_id",
      "receipt_type",
      "receipt_hash",
      "grant_id",
      "grant_hash",
      "session_id",
      "session_generation",
      "trace_id",
      "span_id",
      "action_id",
      "app_id",
      "surface_version",
      "surface_hash",
      "runtime",
      "actor_agent",
      "subject",
      "idempotency_key",
      "input_hash",
      "execution",
      "execution_hash",
      "policy_decision",
      "policy_decision_hash",
      "timestamp",
      "result"
    ]
  },
  "revocation": {
    "grant_management_url": "https://example.com/settings/agent-grants",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "event": "grant.revoked"
  }
}
```

`audit.required_fields` advertises the non-conditional minimum for application
receipts and MUST NOT weaken the Receipt Requirements profile. Conditional
fields such as `parent_receipt_hash`, `output_hash`, approval evidence, error
classification, and required signatures remain mandatory when their receipt
semantics require them even if they are not repeated in this list.

### Resources

Resources describe data the agent MAY read, reference, or attach to an action.

Each resource MUST include:

- `id`
- `read_scope`
- `schema`
- optional `query_actions`
- `data_exposure`

Example:

```json
{
  "id": "pull_request",
  "read_scope": "pull_request.read",
  "schema": "https://github.example/schemas/pull-request.schema.json",
  "query_actions": ["pull_request.get", "pull_request.list_files"],
  "data_exposure": {
    "classes": ["repository.content", "user.identifier"],
    "redaction": {
      "mode": "policy",
      "policy_id": "repository-visible-fields-only",
      "summary": "Only fields visible to the connected repository user are returned."
    },
    "retention": {
      "mode": "bounded",
      "max_seconds": 7200,
      "delete_on_grant_end": true
    }
  }
}
```

### Actions

Actions are typed operations the app allows agents to request through a runtime.

Each action SHOULD include the following fields as applicable.
`data_exposure` is REQUIRED for every action:

- `id`
- `scope`
- `risk`
- `approval`
- `input_schema`
- `output_schema`
- `side_effect`
- `effects` for actions that change domain or coordination state
- `execution`
- optional `capability_hint`
- `idempotency` for side-effecting actions
- `receipt` for side-effecting actions
- `input_hash_profile` for actions requiring receipt-linked input evidence
- `execution_hash_profile` for `reserve`, `commit`, `compensate`, and `revert`
- `data_exposure`

An action whose receipt chain binds the exact request input MUST set
`input_hash_profile` to `asp-jcs-sha-256`. Other profile identifiers are not
defined by this draft.

Every action MUST declare exactly one standard `execution.mode` and a stable
`execution.operation_id`. The mode, companion-action references, effect model,
and mode-specific schemas are defined by the Action Execution Model. An action
in mode `reserve`, `commit`, `compensate`, or `revert` MUST set
`execution_hash_profile` to `asp-jcs-sha-256`; other profile identifiers are not
defined by this draft.

Example:

```json
{
  "id": "pull_request.review.submit",
  "scope": "pull_request.review.write",
  "risk": "write",
  "side_effect": true,
  "effects": [
    {
      "effect_id": "review-publish",
      "operation": "publish",
      "resource_type": "pull_request.review",
      "visibility": "shared",
      "boundary": "internal",
      "reversibility": "irreversible",
      "domain": "communication"
    }
  ],
  "approval": "user_or_app",
  "idempotency": "required",
  "input_hash_profile": "asp-jcs-sha-256",
  "execution_hash_profile": "asp-jcs-sha-256",
  "execution": {
    "mode": "commit",
    "operation_id": "pull_request.review.publish",
    "proposal_action": "pull_request.review.propose"
  },
  "input_schema": "https://example.com/schemas/pr-review-submit.input.schema.json",
  "output_schema": "https://example.com/schemas/pr-review-submit.output.schema.json",
  "data_exposure": {
    "classes": ["repository.content"],
    "redaction": {"mode": "none"},
    "retention": {"mode": "transient", "delete_on_grant_end": true}
  },
  "receipt": "required"
}
```

### Proposal-Only Support

Applications that are not ready to allow direct agent writes SHOULD expose
proposal-only actions.

A proposal-only action is a typed action whose output is a draft, suggestion,
patch, review body, or other non-committed artifact.

A proposal-only action declares `side_effect: false` because it does not
commit domain-visible changes. However, when the application persists
proposals as drafts — as the proposal flow in this draft assumes — repeated
proposal requests can still accumulate duplicate drafts under retries and
agent loops. An action that persists proposals MUST declare
`execution.persisted: true` and `idempotency: "required"`, accept idempotency
keys, and deduplicate stored drafts accordingly. A non-persisted proposal MUST
omit `execution.persisted` or set it to `false`.

Example:

```json
{
  "id": "pull_request.review.propose",
  "scope": "pull_request.review.propose",
  "risk": "propose",
  "side_effect": false,
  "approval": "none",
  "idempotency": "required",
  "execution": {
    "mode": "propose",
    "operation_id": "pull_request.review.publish",
    "persisted": true,
    "commit_action": "pull_request.review.submit"
  },
  "input_schema": "https://example.com/schemas/pr-review-propose.input.schema.json",
  "output_schema": "https://example.com/schemas/pr-review-propose.output.schema.json",
  "data_exposure": {
    "classes": ["repository.content"],
    "redaction": {"mode": "none"},
    "retention": {"mode": "transient", "delete_on_grant_end": true}
  }
}
```

If a commit action depends on a proposal, it SHOULD reference the proposal action:

```json
{
  "id": "pull_request.review.submit",
  "execution": {
    "mode": "commit",
    "operation_id": "pull_request.review.publish",
    "proposal_action": "pull_request.review.propose"
  }
}
```

This allows early adopters to become agent-native without allowing direct writes.

### Events

Events let applications notify runtimes and agents about app context changes.

Every non-control event MUST declare a non-empty `scope`. A grant that permits
`pull_request.read` MAY receive `pull_request.updated`, but MUST NOT receive an
unrelated financial, HR, or admin event or an event whose scope is absent. An
unscoped non-control event declaration is an invalid surface, not an event
implicitly available to every grant.

Example:

```json
{
  "id": "ci.failed",
  "scope": "pull_request.read",
  "schema": "https://example.com/schemas/ci-failed.event.schema.json",
  "data_exposure": {
    "classes": ["repository.content"],
    "redaction": {"mode": "none"},
    "retention": {"mode": "transient", "delete_on_grant_end": true}
  }
}
```

Grant constraints filter events the same way they filter actions: a grant
constrained to one repository SHOULD NOT receive events about other
repositories, even when the event scope matches.

An event declaration MAY set `control: true` only for an application control
event whose delivery authority and closure are defined by this specification or
another profile understood by the runtime. A control event omits `scope`; it is
not authorized by the affected grant. This draft defines `grant.revoked` as the
only core control event. A manifest that advertises `grant.revoked` MUST list it
in `events` with `control: true` and a `data_exposure` contract.

`grant.revoked` is an application control event rather than an event authorized
by the revoked grant. Its payload, authentication, and processing requirements
are defined in the OAuth Grant Revocation Profile.

### Event Subscription Authority

An event subscription is an application-authoritative delivery record bound to
one authenticated runtime and one exact grant tuple. It does not widen the
grant and is not a session. A non-control subscription MUST bind:

- `subscription_id`, application issuer, and pinned `surface_hash`
- grant subject, `grant_id`, and `grant_hash`
- runtime id, agent id, and passport hash
- the accepted event type allow-list and resource-filter projection
- negotiated delivery profile, acknowledgement deadline, in-flight window, and
  retention window

The runtime requests a subscription through the manifest
`event_subscription_url` or an equivalent authenticated bridge operation:

```json
{
  "type": "event.subscribe",
  "payload": {
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_hash": "sha256:...",
    "requested_events": ["ci.failed", "pull_request.updated"],
    "max_in_flight": 16
  }
}
```

The application MUST select the subject and resource filters from the
authoritative grant; caller-supplied identifiers or filters cannot replace
that state. It MUST reject an event type absent from the pinned manifest, a
type outside the grant's scope or constraints, a mismatched tuple or hash, and
an in-flight request above the advertised maximum. It MAY accept a strict
subset but MUST NOT add an event type. An unsuccessful request creates no
subscription.

The application returns the accepted immutable binding and an initial opaque
cursor representing the position before any delivery:

```json
{
  "type": "event.subscribed",
  "payload": {
    "subscription_id": "sub_01J2EVENTS",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_hash": "sha256:...",
    "accepted_events": ["ci.failed", "pull_request.updated"],
    "profile": "at_least_once",
    "ack_deadline_seconds": 30,
    "max_in_flight": 16,
    "retention_seconds": 86400,
    "cursor": "opaque:initial-position"
  }
}
```

Before both enqueue and delivery, the application MUST recheck current grant
state, event scope, resource constraints, surface binding, and the effective
Data Exposure Contract. A queued event that no longer passes MUST NOT cross the
application boundary. Changing the accepted event set, tuple, grant hash,
surface hash, or resource-filter projection requires a new subscription; an
implementation MUST NOT reinterpret an old cursor under wider authority.

Control events use a logically separate application-to-runtime control
subscription bound to the application issuer and authenticated runtime, not to
the affected grant. It MAY share one physical connection with non-control
events, but its authority, flow-control capacity, and closure rules remain
separate. A guessed `subscription_id` or cursor is never authority, and an
unauthorized query MUST NOT reveal whether either exists.

### Event Delivery Semantics

The `at_least_once` profile separates an occurrence from its delivery. The
application creates one stable event object for the authorized, redacted
occurrence and one stable `delivery_id` for that event in each subscription.
Every transmission of the same delivery increments `attempt` but preserves the
subscription id, delivery id, event object, stream, sequence, and cursor:

```json
{
  "type": "event.delivery",
  "payload": {
    "subscription_id": "sub_01J2EVENTS",
    "delivery_id": "delivery_01J2FAILED",
    "attempt": 1,
    "stream": "repository:example-org/example-repo",
    "sequence": 42,
    "cursor": "opaque:position-after-42",
    "event": {
      "id": "evt_01J2FAILED",
      "source": "https://code.example.com",
      "type": "ci.failed",
      "time": "2026-06-25T16:20:00Z",
      "subject": "example-org/example-repo/pull/13",
      "scope": "pull_request.read",
      "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
      "data": {
        "repository": "example-org/example-repo",
        "pull_request": 13,
        "check": "tests"
      }
    }
  }
}
```

While the subscription is active and the delivery remains inside its effective
retention window, the application MUST retransmit an unacknowledged delivery
after the acknowledgement deadline. Retries SHOULD use bounded backoff and
MUST NOT change the event projection to include newly available data. If
current authorization or redaction policy can no longer permit the immutable
projection, the application expires that delivery rather than sending a
different object under the same `delivery_id`.

The runtime MUST deduplicate on `(subscription_id, delivery_id)` and retain
enough identity state to distinguish a retry from a conflicting reuse. Seeing
the same delivery id with a different event identity, content, stream,
sequence, or cursor is `event_delivery_conflict`; the runtime MUST NOT process
either version as a new occurrence and MUST resynchronize. Duplicate delivery
can still happen after a crash or loss of local deduplication state, so this
profile does not provide exactly-once processing. Any Action Request triggered
by an event remains subject to the action's independent authorization,
idempotency, session, and effect rules.

Delivery authentication establishes the application and bound subscription;
fields inside `event` do not. The runtime MUST match the event type to the
pinned manifest and effective grant projection before exposing its data to an
agent. Event content is untrusted application data, not an instruction that can
bypass runtime policy or the Data Exposure Contract.

### Ordering and Acknowledgement

Ordering is defined only inside a `stream` of one subscription. The application
starts at sequence `1`, increments by exactly one for each event eligible for
that stream, and MUST keep an event in the same stream across every retry and
replay. It MUST NOT first-deliver sequence `N + 1` until sequence `N` has a
terminal acknowledgement. Different streams have no defined total order and
MAY progress concurrently up to the negotiated in-flight window. A runtime
MUST NOT infer cross-stream causality from arrival time.

Sequence numbers describe only events authorized for that subscription. Gaps
in an application's source log, filtered events, or events for another subject
MUST NOT be exposed through the subscription sequence. A replay preserves the
original stream and sequence; it does not allocate a new position.

The runtime acknowledges each delivery explicitly:

```json
{
  "type": "event.ack",
  "payload": {
    "subscription_id": "sub_01J2EVENTS",
    "delivery_id": "delivery_01J2FAILED",
    "cursor": "opaque:position-after-42",
    "outcome": "processed",
    "reason": "durably_recorded"
  }
}
```

Defined outcomes are:

- `processed`: the runtime durably recorded its deduplication decision and any
  required local state before acknowledging
- `discarded`: local policy or unsupported event semantics made deliberate
  non-processing terminal; a stable reason is REQUIRED
- `retry`: processing is temporarily unavailable; the delivery remains
  unacknowledged and an optional bounded retry delay is only a hint

`processed` means accepted by the runtime, not that an agent completed a task
or an application action succeeded. `discarded` MUST NOT be used for
`grant.revoked` until the runtime has fail-closed the matching grant and begun
authoritative resynchronization; a valid control event is normally acknowledged
as `processed` only after its required state transition.

A terminal acknowledgement is valid only on the authenticated subscription
and when its delivery id and cursor exactly match the delivery record. It is
idempotent for the same outcome and reason. Conflicting terminal outcomes,
unknown response state, connection loss, or a timeout leave the delivery
unacknowledged. The application MUST NOT advance ordering or discard retained
delivery state merely because it sent a message.

### Replay Cursors and Gaps

A cursor is an opaque, integrity-protected application value bound to the
issuer, applicable subject and delegate tuple, subscription, accepted event and
filter projection, surface hash, and delivery position. It is neither an event
identifier nor a credential. The runtime MUST store and return it unchanged and
MUST NOT infer ordering by comparing cursor bytes.

The runtime requests replay after a previously issued cursor:

```json
{
  "type": "event.replay",
  "payload": {
    "subscription_id": "sub_01J2EVENTS",
    "after_cursor": "opaque:last-durable-position",
    "limit": 100
  }
}
```

The application MUST authenticate the subscription before resolving the
cursor. Replayed records retain their original event and delivery identities,
stream, sequence, and cursor; `attempt` increments for another transmission.
The runtime applies ordinary deduplication and acknowledgement rules. Replay
does not reactivate an interrupted or terminal ASP session, and receiving an
event does not authorize a session transition.

A malformed, tampered, wrong-subscription, wrong-tuple, or wrong-surface cursor
fails as `event_cursor_invalid`. A position no longer available under the
effective retention window fails as `event_cursor_expired`. The application
MUST NOT silently substitute the latest or earliest position. It returns an
authenticated `event.gap` containing the subscription id, last accepted
cursor, earliest currently available cursor when disclosure is permitted, and
reason `retention_expired` or `authorization_changed`. The gap MUST NOT reveal
filtered event identities or counts.

After a gap, the runtime MUST pause automation that depends on complete event
history and reconcile authoritative application state through granted resource
reads or an application-defined snapshot operation. Continuing from the
earliest cursor requires an explicit local policy decision; it cannot be
represented as complete replay. A new or widened grant always requires a new
subscription and initial cursor.

### Retention and Backpressure

For an otherwise active and authorized subscription, the application MUST keep
the delivery record, immutable redacted event projection, and replay position
available for `retention_seconds` after the event first becomes eligible for
that subscription. Earlier deletion is permitted only when required by grant
expiry or revocation, a stricter Data Exposure Contract, subject deletion, or
security response. Such deletion creates an explicit gap; it never permits
silent cursor advancement.

The effective replay window is the shortest applicable delivery-retention,
grant-lifetime, and data-exposure limit. `delete_on_grant_end` applies to queued
and replayable projections when the grant ends. A runtime SHOULD keep compact
deduplication metadata for at least the same effective window but MUST apply
its own retention policy to payloads; acknowledgement does not authorize
indefinite local storage.

`max_in_flight` counts distinct, non-terminally acknowledged deliveries. A
retry of the same `delivery_id` consumes the same slot. The application MUST
NOT exceed the negotiated window. The runtime MAY use authenticated
`event.flow` to lower the window, pause new non-control deliveries with a value
of zero, or restore a value no greater than the negotiated maximum. Pausing
does not terminally acknowledge existing deliveries, extend retention, or
permit the application to ignore their outcomes.

The runtime changes the application-event window with this wire request:

```json
{
  "type": "event.flow",
  "payload": {
    "kind": "request",
    "flow_id": "flow_01J2PAUSE",
    "subscription_id": "sub_01J2EVENTS",
    "max_in_flight": 0
  }
}
```

The request MUST arrive on a channel authenticated as the runtime bound to the
subscription. `flow_id` is unique within that subscription, and
`max_in_flight` MUST be an integer from `0` through the negotiated maximum.
Zero pauses new application-event deliveries. A positive value replaces the
current window; it does not add to it. A request targeting an unknown, closed,
wrong-runtime, or control subscription fails uniformly as
`event_subscription_invalid`. Invalid kinds or values fail as `schema_invalid`.

The application atomically installs the new window before returning its state:

```json
{
  "type": "event.flow",
  "payload": {
    "kind": "state",
    "flow_id": "flow_01J2PAUSE",
    "subscription_id": "sub_01J2EVENTS",
    "effective_max_in_flight": 0,
    "result": "applied"
  }
}
```

Lowering the window below the current in-flight count does not cancel or
terminally acknowledge those deliveries; the application sends no new one
until the count falls below the effective window. An exact duplicate request
with the same `flow_id`, subscription, and value is idempotent and returns the
same state. Conflicting reuse of `flow_id` fails as `schema_invalid` without
changing the window. If the response is lost or ambiguous, the runtime MUST
NOT assume the remote window changed; it MAY repeat the exact request or stop
local consumption and close the channel while it reconciles state.

When the window is full, the application queues eligible events within the
effective retention window rather than exceeding the limit. If an event expires
before first delivery, the next delivery or replay response MUST carry an
`event.gap`; silent loss is forbidden. Implementations SHOULD expose bounded
metrics for queued, in-flight, retried, expired, and gap states without
including event payloads.

Application-event backpressure MUST NOT starve the runtime control
subscription. The application MUST reserve independent capacity for
`grant.revoked` or deliver it on a separate authenticated channel. If the
control path is unavailable, application-side revocation remains immediately
authoritative; the runtime MUST stop new use when it cannot re-establish or
introspect authoritative grant state rather than assuming that the absence of a
control event means the grant is active.

### Data Exposure Contract

The manifest `data_classes` array defines the application-local data classes
used by exposure declarations. Every entry MUST contain a unique, stable `id`,
a `classification`, a non-empty `label`, and a non-empty `description`.
Defined classification values are:

- `public`: information intentionally available without user-specific access
- `private`: non-public application or user content
- `sensitive`: information whose disclosure can create material privacy,
  safety, financial, or organizational harm
- `credential`: secrets or authentication material

The protection order is `public` < `private` < `sensitive` < `credential`.

Class identifiers name semantic kinds of data, such as
`repository.content` or `user.identifier`; classifications describe their
minimum handling sensitivity. A publisher MUST assign the most protective
applicable classification when a class can contain data of different
sensitivities. Labels and descriptions are application-authored display hints,
not authority or evidence that a class is harmless. A runtime MUST preserve the
class identifier and classification when it renders an application label.
The `data_classes` array and every exposure `classes` array MUST be ordered by
ascending Unicode code point of the class identifier; duplicates are invalid.

Every resource, action, and event declaration MUST contain a `data_exposure`
object. The object describes the maximum application-originated data that can
reach the runtime or agent through that declaration after application-side
redaction. It has this shape:

```json
{
  "classes": ["repository.content", "user.identifier"],
  "redaction": {
    "mode": "policy",
    "policy_id": "repository-visible-fields-only",
    "summary": "Only fields visible to the connected repository user are returned."
  },
  "retention": {
    "mode": "bounded",
    "max_seconds": 7200,
    "delete_on_grant_end": true
  }
}
```

Examples in later sections that isolate execution, receipt, or error semantics
are declaration fragments and can omit unrelated required manifest members for
readability. A complete manifest cannot omit `data_exposure`.

`classes` MUST be an array of unique identifiers declared in `data_classes`.
It is a conservative maximum: every class that can occur on a success, partial
result, preview, structured error, pagination path, nested representation, or
event payload MUST be listed. An explicit empty array means that the declaration
delivers no application-originated data. Omission never means "no exposure".
A JSON Schema reference does not replace this declaration.

`redaction.mode` is `none` or `policy`. `none` means that the class set already
describes the unredacted representation and the object MUST omit `policy_id`
and `summary`. `policy` means the application applies a named policy before the
payload crosses the application boundary; it MUST include a stable non-empty
`policy_id` and a consent-safe non-empty `summary`. The application MUST apply
redaction before delivery. A runtime or agent MUST NOT be made responsible for
removing fields whose receipt would already violate the contract.

`retention.mode` is `transient` or `bounded`. `transient` prohibits durable
persistence of the disclosed payload by the runtime or agent. `bounded` MUST
include a positive integer `max_seconds`, measured from receipt, after which
runtime-controlled plaintext copies MUST be deleted. `transient` MUST omit
`max_seconds`. `delete_on_grant_end` is REQUIRED; when true, expiry or
revocation shortens the retention period and requires prompt deletion of
runtime-controlled plaintext copies. When false, the declared time bound still
applies. Hashes and data-minimized audit metadata MAY outlive the plaintext
only when another grant or policy requirement explicitly permits their
retention.

The resource contract applies to every representation and query result of that
resource. The action contract applies to all application-originated
agent-visible output from that action, including dry-run or proposal output,
success responses, partial results, and structured error details. It does not
describe application retention of agent-supplied action input. The event
contract applies to its payload. Control events such as `grant.revoked` MUST
also appear in the manifest `events` array with `control: true` and an exposure
contract; they cannot bypass these rules merely because their delivery
authority is independent of the affected grant.

The application is responsible for classifying source fields and enforcing the
declared post-redaction envelope before delivery. This draft does not define a
field-level classifier and does not require a runtime to infer semantic data
classes from arbitrary payload bytes. A schema MAY carry implementation-specific
classification annotations, but those annotations do not replace the contract.

The authorization server MUST derive the issued grant's effective
`data_exposure` array from the exact pinned manifest and approved Grant Object
using this conservative source closure:

1. include every resource whose `read_scope` is an exact member of the granted
   `scopes`, even when a resource filter narrows the instances;
2. include every action whose `id` is an exact member of the granted `actions`;
3. include every non-control event whose `scope` is an exact member of the
   granted `scopes`; and
4. include the core `grant.revoked` event when the manifest advertises it with
   `control: true`, regardless of the revoked grant's scopes.

The conservative resource and event rules may display a class that a narrower
resource filter never returns, but they MUST NOT omit a class that remains
reachable. Future control events require their own explicit closure rule; an
unknown `control: true` event makes the surface incompatible with this profile.
Every selected source is included, including one with an empty `classes` array.
Duplicate source pairs are invalid. Projection entries MUST be ordered first by
source kind in the order `resource`, `action`, `event`, then by ascending Unicode
code point of `source.id`. Each entry copies that source's complete
post-redaction contract:

```json
[
  {
    "source": {"kind": "resource", "id": "task"},
    "classes": ["repository.content", "user.identifier"],
    "redaction": {
      "mode": "policy",
      "policy_id": "repository-visible-fields-only",
      "summary": "Only fields visible to the connected repository user are returned."
    },
    "retention": {
      "mode": "bounded",
      "max_seconds": 7200,
      "delete_on_grant_end": true
    }
  }
]
```

Defined source kinds are `resource`, `action`, and `event`. The client MUST NOT
supply `data_exposure` in an Agent Grant authorization request. The
authorization server derives it after applying the approved subset and MUST
NOT omit a selected source. Its `classes`, `redaction`, and `retention` members
MUST be structurally identical to the pinned source declaration; a narrower
runtime policy is a local overlay and does not rewrite this projection.
The returned Grant Object and introspection response MUST contain the same
projection. The complete projection is part of the Grant Object hashing view
and therefore changes `grant_hash`.

Before storing or using a grant, the runtime MUST recompute this projection
from the exact pinned manifest and granted authority. It MUST require exact
structural equality, including source and class array ordering, and reject a
missing, extra, unknown, stale, or inconsistent projection as
`integrity_mismatch`. A
runtime MAY apply additional redaction or a shorter retention period as local
policy, but it MUST NOT widen the class set or retain plaintext longer. If it
cannot enforce the effective contract for the selected runtime-agent path, it
MUST refuse to use the grant for that path.

An exposure declaration never grants access and never weakens scope, resource,
action, subdelegation, or credential-release checks. In particular, declaring a
class with classification `credential` does not authorize its disclosure. An
Agent Surface Grant Credential remains non-releasable, and other credential
material can cross into agent-visible context only through the separately
authorized `credential.release` capability and its constraints.

If the application detects that a payload would exceed the effective contract,
it MUST block delivery and return `data_exposure_violation`. If the runtime
detects such a violation before agent delivery, it MUST discard the payload and
fail the operation with the same error. Either component records only
data-minimized evidence: the offending value MUST NOT be copied into the error,
receipt, trace, prompt, or audit log. Changing a data class or exposure contract
changes the manifest hashing view and requires a new `surface_version`; an
existing grant MUST NOT silently adopt the replacement contract.

## Action Execution Model

The Action Execution Model separates an action's immutable, manifest-pinned
semantics from the context of one invocation. It standardizes preview, resource
coordination, commit, and recovery without letting a caller turn low-risk
authority into a state-changing operation.

### Static Execution Modes

Every action declaration MUST contain exactly one `execution.mode` selected
from this table:

| Mode | Meaning | `side_effect` |
| --- | --- | --- |
| `read` | Read application state without changing domain or coordination state. | `false` |
| `dry_run` | Validate a possible later commit and predict its preconditions and effects without performing it. | `false` |
| `propose` | Produce a non-committed proposal or draft. | `false` |
| `reserve` | Acquire, renew, or release time-bounded application coordination state. | `true` |
| `commit` | Apply declared effects to application or external state. | `true` |
| `compensate` | Apply a new counter-effect intended to offset an earlier commit. | `true` |
| `revert` | Attempt to restore a declared prior state controlled by the application. | `true` |

The mode is a property of the action identifier in the pinned manifest. It is
not a caller-selectable privilege. The `mode` repeated in an Action Request
MUST equal the declaration for its `action_id`; the application MUST reject a
mismatch as `execution_mode_invalid` before performing any effect.

Each action MUST also declare a non-empty `execution.operation_id` that groups
the separately authorized stages of one logical operation. Sharing an
`operation_id` does not share authority. Every companion action has its own
`action_id`, scope, risk, approval, schemas, idempotency key, and receipt
requirements, and every invoked action MUST independently be present in the
grant's authoritative `actions` allow-list. Scope alone never authorizes an
action or a stronger companion stage.

The legacy example values `direct`, `write`, and `proposal_only` are not
standard modes. A publisher MUST use `read` or `propose` according to the
operation's semantics, `commit`, and `propose`, respectively. An application
does not need to implement every standard mode.

Actions in mode `read`, `dry_run`, or `propose` MUST declare
`side_effect: false`. Actions in mode `reserve`, `commit`, `compensate`, or
`revert` MUST declare `side_effect: true`, `idempotency: "required"`,
`receipt: "required"`, a non-empty `effects` array,
`input_hash_profile: "asp-jcs-sha-256"`, and
`execution_hash_profile: "asp-jcs-sha-256"`. Persisted proposals remain
non-committed domain artifacts but MUST support idempotency as specified in
Proposal-Only Support.

Ephemeral preview handles, deduplication records, audit records, and stored
proposal drafts are protocol bookkeeping for this classification. A `dry_run`
MUST NOT reserve a resource, exclude another actor, or mutate the target domain;
an operation that affects availability or concurrency uses `reserve` and is
state-changing.

### Companion Actions and Transitions

Companion stages use separate action identifiers:

```text
dry_run ---------------------> commit
   |                             |
   +----------> reserve ---------+
                                 |
                                 +----> compensate
                                 +----> revert

propose ----------------------> commit
```

A commit action MAY declare `dry_run_action`, `proposal_action`,
`reservation_action`, and `recovery_actions`. It MAY declare
`dry_run_required: true` or `reservation_required: true`; when either flag is
true, the corresponding action reference and valid request evidence are
required. A dry-run, proposal, or reservation-acquire action that leads to a
commit MUST declare `commit_action`. A recovery action MUST declare a non-empty
`target_actions` array.

Every companion reference MUST resolve in the same manifest snapshot, MUST NOT
reference the declaring action itself, and MUST use the same `operation_id`.
The referenced mode MUST match the reference: `dry_run_action` identifies a
`dry_run` action, `proposal_action` a `propose` action,
`reservation_action` a `reserve` acquisition action, and each
`recovery_actions` entry identifies the declared `compensate` or `revert`
mode. Every recovery entry MUST also contain a non-empty, unique `effect_ids`
array naming effects from the commit declaration and a positive integer
`recovery_window_seconds`. A `revert` entry can name
only `reversible` effects whose boundary is `internal`; a `compensate` entry
can name only `compensatable` effects. Effects declared `irreversible` or
`not_applicable` MUST NOT be named by a recovery relationship.

A `revert` action MUST declare `revert_preconditions_schema`. Its schema
defines the application-controlled revision and prior-state evidence required
to restore the named reversible effects without overwriting intervening work.

For a `commit` action, every effect declared `reversible` MUST be covered by at
least one `revert` entry, and every effect declared `compensatable` MUST be
covered by at least one `compensate` entry. A publisher that cannot provide the
corresponding independently authorized action MUST declare the effect
`irreversible` rather than advertise unsupported recovery.

References MUST be reciprocal: a companion's `commit_action` or
`target_actions` MUST identify the originating commit action and the same
effect ids and recovery window. A recovery declaration represents each target
as an object with `action_id`, `effect_ids`, and `recovery_window_seconds`, not
as an unscoped action string.

A direct commit remains valid when neither dry run nor reservation is required.
Even when a companion stage succeeded, a commit MUST repeat complete current
grant, credential, tuple, scope, resource, policy, approval, and schema
verification. A companion result is never inherited authority.

An issued grant's `actions` allow-list MUST be closed over required companion
dependencies. Including a commit with `dry_run_required: true` requires its
`dry_run_action`; including a commit with `reservation_required: true` requires
its reservation-acquire action and that acquisition's mandatory release action.
Including an acquisition action requires its `commit_action` and
`release_action`. Closure is recursive when the required commit has other
required stages. Optional proposal, renewal, compensation, and revert actions
need not be granted. The authorization server MUST reject an unclosed subset;
it MUST NOT silently add authority to close it.

The following fragment declares a commit stage. Its referenced actions are
separate declarations in the same surface:

```json
{
  "id": "branch.create",
  "scope": "repository.branch.write",
  "risk": "write",
  "side_effect": true,
  "approval": "user_or_app",
  "idempotency": "required",
  "input_hash_profile": "asp-jcs-sha-256",
  "execution_hash_profile": "asp-jcs-sha-256",
  "execution": {
    "mode": "commit",
    "operation_id": "repository.branch.create",
    "dry_run_action": "branch.create.preview",
    "dry_run_required": true,
    "reservation_action": "branch.create.reserve",
    "reservation_required": true,
    "recovery_actions": [
      {
        "mode": "revert",
        "action_id": "branch.delete",
        "effect_ids": ["branch-create"],
        "recovery_window_seconds": 86400
      }
    ]
  },
  "preconditions_schema": "https://example.com/schemas/branch-create.preconditions.schema.json",
  "expected_effects_schema": "https://example.com/schemas/branch-create.expected-effects.schema.json",
  "actual_effects_schema": "https://example.com/schemas/branch-create.actual-effects.schema.json",
  "effects": [
    {
      "effect_id": "branch-create",
      "operation": "create",
      "resource_type": "git.branch",
      "visibility": "shared",
      "boundary": "internal",
      "reversibility": "reversible",
      "domain": "workflow"
    }
  ],
  "input_schema": "https://example.com/schemas/branch-create.input.schema.json",
  "output_schema": "https://example.com/schemas/branch-create.output.schema.json",
  "receipt": "required"
}
```

Its reciprocal revert declaration can be:

```json
{
  "id": "branch.delete",
  "scope": "repository.branch.delete",
  "risk": "destructive",
  "side_effect": true,
  "approval": "runtime_and_app",
  "idempotency": "required",
  "input_hash_profile": "asp-jcs-sha-256",
  "execution_hash_profile": "asp-jcs-sha-256",
  "execution": {
    "mode": "revert",
    "operation_id": "repository.branch.create",
    "target_actions": [
      {
        "action_id": "branch.create",
        "effect_ids": ["branch-create"],
        "recovery_window_seconds": 86400
      }
    ]
  },
  "revert_preconditions_schema": "https://example.com/schemas/branch-delete.revert-preconditions.schema.json",
  "effects": [
    {
      "effect_id": "branch-delete",
      "operation": "delete",
      "resource_type": "git.branch",
      "visibility": "shared",
      "boundary": "internal",
      "reversibility": "irreversible",
      "domain": "workflow"
    }
  ],
  "input_schema": "https://example.com/schemas/branch-delete.input.schema.json",
  "output_schema": "https://example.com/schemas/branch-delete.output.schema.json",
  "receipt": "required"
}
```

### Execution Context and Binding

Every Action Request MUST carry an `execution` object with `mode` and a
non-empty `execution_id`. The runtime chooses an `execution_id` that is unique
within the grant and session and reuses it for exact idempotent retries of that
invocation. The identifier is correlation, not authority.

For an idempotency-required invocation, the application MUST enforce that one
tuple of `grant_id`, `session_id`, `action_id`, and `execution_id` maps to
exactly one idempotency key, `input_hash`, and, when required,
`execution_hash`. Reusing an execution id with any different value in the same
grant and session is an `idempotency_conflict`. Read,
ordinary dry-run, and non-persisted proposal invocations can omit the key or
execution hash, but their execution ids still cannot be rebound to different
requests. Reusing the same preview or approval under a new execution id does
not bypass their own single-use and exact-binding rules.

The request execution context can additionally contain `preview_id`,
`execution_token`, `execution_token_hash`, `preconditions_hash`,
`expected_effects_hash`, `reservation_id`, and `target_receipt_hash`. Unknown
standard-looking bare names are invalid; extensions MUST use
collision-resistant URI member names.

For `reserve`, `commit`, `compensate`, and `revert`, the request MUST carry
`execution_hash` computed with the Canonical Object Hash Profile over the
`execution` object with `execution_token` omitted. The runtime receipt and app
receipt MUST contain the same sanitized `execution` object and matching
`execution_hash`. A verifier MUST recompute the hash and reject a request or
receipt mismatch as `integrity_mismatch`.

When a raw `execution_token` is present, `execution_token_hash` is REQUIRED and
MUST match it. The runtime MUST omit the raw token from receipts, logs, prompts,
events, and agent-visible context. The application MUST treat the token as
preview evidence only and MUST reject it when the current grant credential,
tuple, surface, action, input, resource state, or approval is invalid.

Example commit context:

```json
{
  "mode": "commit",
  "execution_id": "exec_01J2COMMIT",
  "preview_id": "preview_01J2ABCDEF",
  "execution_token": "FW_vZMMelqPUDUmFfxSr1A",
  "execution_token_hash": "sha-256:tONJJscZ4IsDBfafODsBja4waqe1AtkpH54rXv_tPrk",
  "preconditions_hash": "sha-256:<preconditions-digest>",
  "expected_effects_hash": "sha-256:<expected-effects-digest>",
  "reservation_id": "reservation_01J2ABCDEF"
}
```

`input_hash` continues to bind the exact validated action input.
`execution_hash` separately binds protocol control context. Reusing an
idempotency key with the same input but a different `execution_hash` is an
`idempotency_conflict`; an application MUST NOT select whichever context is
more permissive.

### Preconditions and Effect Preview

A commit that declares `dry_run_action` MUST declare both
`preconditions_schema` and `expected_effects_schema`. Those two members MUST be
absent when no dry-run action is linked; a direct commit expresses ordinary
optimistic-concurrency fields through its `input_schema`. A state-changing
action MAY declare `actual_effects_schema` to further constrain the mandatory
core Effect Model. A linked dry-run action MUST set
`input_hash_profile: "asp-jcs-sha-256"`, use the same `input_schema` as its
target commit, and identify that commit through `execution.commit_action`. It
MUST NOT change target-domain or coordination state.

The dry-run request MUST carry `input_hash`, and the application MUST recompute
it from the exact validated wire input. A preview-bound commit MUST present the
same exact input and matching `input_hash`; schema equivalence or application
normalization does not make a different wire input the previewed input.

A successful dry run returns application-produced preconditions and expected
effects, their canonical hashes, and time-bounded evidence:

```json
{
  "result": "preview",
  "execution": {
    "mode": "dry_run",
    "execution_id": "exec_01J2PREVIEW"
  },
  "preview": {
    "preview_id": "preview_01J2ABCDEF",
    "commit_action_id": "branch.create",
    "execution_token": "FW_vZMMelqPUDUmFfxSr1A",
    "execution_token_hash": "sha-256:tONJJscZ4IsDBfafODsBja4waqe1AtkpH54rXv_tPrk",
    "expires_at": "2026-07-12T12:05:00Z"
  },
  "preconditions": {
    "repository_revision": "rev_456",
    "branch_absent": "feature-x"
  },
  "preconditions_hash": "sha-256:<preconditions-digest>",
  "expected_effects": [
    {
      "effect_id": "branch-create",
      "operation": "create",
      "resource_type": "git.branch",
      "resource_key": "example/repo:feature-x",
      "visibility": "shared",
      "boundary": "internal",
      "reversibility": "reversible",
      "domain": "workflow"
    }
  ],
  "expected_effects_hash": "sha-256:<expected-effects-digest>"
}
```

`preconditions` and `expected_effects` MUST validate against the target
commit's declared schemas. Their hashes use the Canonical Object Hash Profile.
The application MUST keep the preview immutable until expiry and MUST bind the
execution token to at least the application and tenant, `grant_id`,
`grant_hash`, `session_id`, `surface_hash`, dry-run and commit action ids,
`input_hash`, `preview_id`, `preconditions_hash`, `expected_effects_hash`,
relevant resource identities and revisions, and expiry. The token can be an
opaque handle to server state, or its decoded random octets can select or carry
application-authenticated state, but its wire representation remains the single
unpadded base64url string defined by the Canonical Object Hash Profile.

`preview_id` MUST be unique within the application and tenant and MUST NOT be
rebound to different input, effects, authority, or state. `expires_at` MUST be
an RFC 3339 UTC timestamp with the `Z` suffix. After a commit applies any effect,
the application MUST mark the preview token consumed by that action's
execution id and idempotency key. An exact idempotent retry can retrieve the
original result; another key or execution id MUST NOT reuse the consumed token.

A commit that relies on the preview MUST repeat `preview_id`, the raw token and
its hash, `preconditions_hash`, and `expected_effects_hash` in its execution
context. The application MUST verify all bindings and re-evaluate the declared
preconditions immediately before applying any effect. For app-controlled state,
the final precondition and reservation check and the mutation MUST be atomic.

Expiry, a changed revision, mismatched input or resource, a different grant or
surface, or more severe expected effects MUST fail before mutation. The
application MUST return `execution_token_expired`, `precondition_failed`, or
`effect_mismatch` as appropriate. It MUST NOT silently generate a new preview
and continue the commit.

A preview is a prediction, not a reservation or commit guarantee. Approval for
a previewed commit MUST bind at least `action_id`, execution mode, `input_hash`,
`preview_id`, and `expected_effects_hash`. If any of those values or the
approval-relevant effect presentation changes, the runtime or application MUST
obtain new approval.

### Resource Reservations

A reservation coordinates competing attempts against typed resources. It does
not authorize the holder, override application concurrency control, or promise
that a later commit will pass its preconditions.

A `reserve` declaration MUST fix one `execution.reservation.operation` value:
`acquire`, `renew`, or `release`. The operation is not request-selectable.
An acquisition declaration MUST identify `commit_action`, `kind` (`exclusive`
or `shared`), a positive integer `max_ttl_seconds`, mandatory `release_action`,
and `disconnect_behavior` (`retain_until_expiry` or `release`). It MAY identify
a `renew_action`; when present, a positive integer `max_renewals` is REQUIRED.
Renew and release declarations MUST reciprocally identify the
acquisition through `execution.reservation.acquisition_action` and use the same
operation id. The declared effect operation MUST be `reserve`, `renew`, or
`release` for acquisition, renewal, or release, respectively.

```json
{
  "id": "branch.create.reserve",
  "scope": "repository.branch.reserve",
  "risk": "write",
  "side_effect": true,
  "approval": "none",
  "idempotency": "required",
  "input_hash_profile": "asp-jcs-sha-256",
  "execution_hash_profile": "asp-jcs-sha-256",
  "execution": {
    "mode": "reserve",
    "operation_id": "repository.branch.create",
    "commit_action": "branch.create",
    "reservation": {
      "operation": "acquire",
      "kind": "exclusive",
      "max_ttl_seconds": 600,
      "disconnect_behavior": "release",
      "renew_action": "branch.create.reservation.renew",
      "max_renewals": 2,
      "release_action": "branch.create.reservation.release"
    }
  },
  "effects": [
    {
      "effect_id": "branch-name-reservation",
      "operation": "reserve",
      "resource_type": "git.branch_name",
      "visibility": "private",
      "boundary": "internal",
      "reversibility": "reversible",
      "domain": "workflow"
    }
  ],
  "input_schema": "https://example.com/schemas/branch-reservation.input.schema.json",
  "output_schema": "https://example.com/schemas/branch-reservation.output.schema.json",
  "receipt": "required"
}
```

The acquisition input schema MUST identify the complete target set and a positive integer
requested TTL no greater than `max_ttl_seconds`. Each target consists of
`resource_type` and an application-canonical `resource_key` that is stable
within issuer and tenant. The application MUST resolve aliases, case rules, and
equivalent locators to that canonical tuple before conflict checking; two
targets are equal when their canonical issuer, tenant, type, and key are equal.

An acquire operation over multiple targets MUST be atomic: either every target
is reserved or none is. Two `shared` reservations on the same target are
compatible. Any overlap where the existing or requested kind is `exclusive`
is a conflict and MUST fail the complete acquisition with
`reservation_conflict`. The response MUST NOT reveal another holder's identity
or grant details.

A successful acquisition returns and records in the app receipt a
`reservation_result` object containing `reservation_id`, `state: "active"`,
kind, targets, `commit_action_id`, `created_at`, and `expires_at`. This outcome
object is not added to the parent runtime receipt's request execution context.
The application MUST bind its authoritative reservation state to
the application and tenant, grant, runtime-agent-passport tuple, surface,
session, acquisition and commit action ids, `input_hash`, exact targets, kind,
and expiry. `reservation_id` alone is never sufficient to use, renew, release,
or consume the reservation.

A successful renewal also reports `reservation_result.state: "active"` with
the new expiry and an actual effect operation of `renew`. A successful explicit
release reports state `released` and an actual effect operation of `release`.
The app receipt MUST NOT report a state or effect operation inconsistent with
the declaration's fixed reservation operation.

An acquire request MUST omit `execution.reservation_id`. A renew or release
request MUST carry the active `reservation_id`, and a commit whose declaration
sets `reservation_required: true` MUST carry it. The application MUST reject a
missing value or wrong binding before mutation. A reservation id MUST be unique
within issuer and tenant and MUST NOT be rebound after consumption, release,
expiry, or invalidation. `created_at` and `expires_at` MUST be RFC 3339 UTC
timestamps with the `Z` suffix.

Reservation state transitions are:

```text
active -> consumed
active -> released
active -> expired
active -> invalidated
```

The effective expiry MUST NOT exceed the acquisition declaration's maximum or
the grant expiry. On renewal, the application computes the new expiry from the
time of successful renewal, not by adding duration to the old expiry, and again
caps it by `max_ttl_seconds` and grant expiry. A renewal input schema MUST carry
a positive requested TTL subject to the same cap. The application MUST reject a
renewal beyond declared `max_renewals`. Applications SHOULD impose additional
per-grant and per-resource limits on active reservations to prevent starvation. An
exact idempotent retry returns the original reservation and receipt.

Renew and release are independently granted, state-changing `reserve` actions
with their own idempotency keys and receipts. Grant revocation, grant expiry,
tuple invalidation, or an incompatible surface change MUST immediately
invalidate affected active reservations. A successful commit MUST atomically
validate and mark its required reservation `consumed`. A commit that performs
no effect MUST leave the reservation active for a retry, explicit release, or
expiry unless the response explicitly reports that it was invalidated.

### Compensation and Revert

`compensate` and `revert` are recovery actions, not rollback flags on the
original request. A commit lists them in `execution.recovery_actions`; each
recovery declaration reciprocally lists objects containing the supported
original `action_id` and exact `effect_ids` in `execution.target_actions`.
The reciprocal entry also repeats the positive `recovery_window_seconds`.

A compensation applies a new semantic counter-effect, such as issuing a refund
after a charge. It can be partial and does not claim that the original state or
external world was restored. A revert is appropriate only when the application
can define and conditionally restore a prior app-controlled state, such as a
document revision. Neither mode erases the original effect or receipt, and
neither is a universal transactional rollback guarantee.

For every effect advertised as `reversible`, the original commit's app receipt
MUST include a `revert_evidence` entry containing `effect_id`, an opaque
`prior_state_ref`, and `committed_state_revision`. The prior-state reference is
receipt-bound evidence and a lookup handle, not authority. The application MUST
retain the referenced state for the declared recovery window; otherwise the
effect cannot be advertised as reversible.

A revert request MUST carry `revert_preconditions` in its business input. The
object MUST validate against `revert_preconditions_schema` and bind the target
effect id, prior-state reference, and expected current revision from the
verified target receipt. Immediately before restoring state, the application
MUST atomically verify that the current revision is the target receipt's
`committed_state_revision`. A mismatch returns `revert_conflict` without
mutation; a prior-state reference MUST NOT be accepted as a credential or used
with another target receipt.

A recovery request MUST carry the hash of the original application receipt:

```json
{
  "mode": "compensate",
  "execution_id": "exec_01J2REFUND",
  "target_receipt_hash": "sha-256:<original-app-receipt-digest>"
}
```

`target_receipt_hash` is a causal cross-action link. It MUST NOT be placed in
`parent_receipt_hash`, because the parent link joins the runtime and app
receipts for the same action, input, grant, and idempotency key. Recovery starts
a new runtime-to-application receipt chain and repeats `target_receipt_hash` in
both receipts.

The application MUST retrieve and verify the complete target app receipt,
recompute its `receipt_hash`, and load the exact manifest snapshot named by its
`surface_hash`. That target commit declaration MUST have authorized the same
recovery action, mode, operation id, and target effect ids. The current recovery
declaration MUST contain the reciprocal mapping. When the target and current
surface hashes differ, the complete original-action and recovery-action
declaration objects in both snapshots MUST be byte-identical after JCS
serialization. This exact pair is the recovery compatibility projection for
the current profile; looser mappings require a future profile. A mismatch MUST
be rejected as `recovery_not_supported` rather than reinterpret old effects
under a new surface. The application MUST also validate tenant and resource
relationships.
The target receipt timestamp MUST fall within the declared recovery window.
An application advertising recovery MUST retain the relevant manifest snapshots
and target receipts for its declared recovery window; unavailable evidence
means recovery is unsupported, never that the current surface can be
substituted.

The target receipt MUST record `effect_outcome` as
`applied` or as a reconciled `partially_applied` outcome with the exact
recoverable `actual_effects`. A denied or `not_applied` action has nothing to
recover. An `unknown` outcome is ineligible for compensation or revert in this
profile because the immutable target receipt does not prove the recoverable
effect. It MUST return `recovery_not_supported`. A future
reconciliation-evidence profile can define a separate app-authoritative
cross-linked object; until then, any corrective action is an independently
authorized operation rather than recovery under this target receipt.

The target receipt and its original grant are evidence, not authority. Recovery
MUST use a currently valid Grant Credential that independently permits the
recovery action, scope, resources, risk, and approval; it MAY use a different
grant from the original action.

Every recovery input schema MUST identify a non-empty subset of the effect ids
authorized by the reciprocal manifest relationship and, for
quantified effects such as a charge or transfer, the amount or quantity to
recover. The application MUST maintain authoritative remaining-effect state
keyed by target receipt and target effect. It MUST aggregate every compensation
or revert action, grant, execution id, and idempotency key against that single
state and prevent cumulative recovery from exceeding the confirmed unrecovered
effect. Per-action attempt records MAY be stored separately but MUST NOT create
independent remaining balances. A non-quantified effect can be recovered
at most once unless its action-specific schema defines a safe repeatable
recovery unit. An exact retry under the original idempotency key returns its
original result. A new request whose target is already exhausted or whose
amount exceeds the remaining effect MUST return `recovery_already_applied` and
MUST NOT emit another counter-effect.

Every recovery action MUST also be idempotent per request and MUST record
whether its outcome is `applied`, `partially_applied`, `not_applied`, or
`unknown`. A revert MUST
recheck its declared prior-state preconditions and return `revert_conflict`
without mutation when they no longer hold. An external effect whose outcome is
uncertain MUST return and receipt `unknown`; a runtime MUST NOT blindly retry it
under a new idempotency key.

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

Risk labels are ordered by increasing severity from `read` to `privileged`.
The labels are not mutually exclusive properties of an action: a single action
can plausibly be described by several of them. When more than one label
applies, the action MUST carry the most severe applicable label. For example,
`invoice.refund.request` is both a mutation and a financial operation; it MUST
be labeled `financial_side_effect`, not `write`.

The `risk` label and the `side_effect` flag MUST be consistent: an action
labeled `write` or a more severe label MUST declare `side_effect: true`, and
an action labeled `read` MUST declare `side_effect: false`.

Applications MAY define extension risk labels, but they SHOULD map them to the
standard labels for runtime interoperability.

## Effect Model

Risk is a policy-oriented severity label. Effects are independent,
machine-readable descriptions of what an action can change. A state-changing
action MUST declare a non-empty `effects` array whose entries contain exactly
the standard members below unless collision-resistant extension members are
used:

- `effect_id`: non-empty identifier unique within the action
- `operation`: `create`, `update`, `delete`, `publish`, `send`, `execute`,
  `transfer`, `grant`, `revoke`, `deploy`, `reserve`, `renew`, or `release`
- `resource_type`: non-empty application resource type
- `visibility`: `private`, `shared`, or `public`
- `boundary`: `internal` or `external`
- `reversibility`: `reversible`, `compensatable`, `irreversible`, or
  `not_applicable`
- `domain`: `data`, `communication`, `workflow`, `financial`, `security`,
  `identity`, `authorization`, `deployment`, or `configuration`

An extension value for any enumerated member MUST be a collision-resistant URI.
Its specification MUST define a conservative mapping to a standard visibility,
boundary, reversibility, and risk floor and MUST define comparison with its
expected and actual values. A verifier that does not support that mapping MUST
reject the surface or action as `surface_incompatible`; it MUST NOT assume an
unknown extension is less severe. Bare unrecognized values are invalid. Effect
identifiers are stable within one surface version and allow a runtime to match
declared, expected, and actual effects without relying on array position.

The manifest declaration is the maximum effect envelope for the action. A
publisher that permits materially different alternatives MUST declare each
alternative effect rather than using a less severe generic value. Within the
standard values, `public` is more exposed than `shared`, which is more exposed
than `private`; `external` crosses a stronger boundary than `internal`; and
`irreversible` is less recoverable than `compensatable`, which is less
recoverable than `reversible`. `not_applicable` is valid only for an operation
that does not claim recovery semantics.

An expected or actual effect exceeds the declaration when it:

- uses an undeclared `effect_id`, operation, resource type, or domain
- has greater visibility or crosses a stronger boundary
- is less recoverable than declared
- identifies a resource not authorized by the grant and the action's declared
  target, container, or produced-output semantics
- otherwise violates the action's expected- or actual-effects schema

Actions in mode `read`, `dry_run`, and `propose` MUST omit `effects` because
they do not commit the predicted target-domain effects. A `reserve` action MUST
declare its coordination effect. Actions in mode `commit`, `compensate`, and
`revert` MUST declare every maximum domain or external effect they can
intentionally produce.

The action declaration, `risk`, and effects MUST be consistent. At minimum:

- a public effect requires `public_side_effect` or a more severe risk
- an external effect requires `external_side_effect` or a more severe risk
- a `financial` effect requires `financial_side_effect` or a more severe risk
- a state-changing `security`, `identity`, or `authorization` effect requires
  `privileged`
- a delete or revoke that is irreversible requires `destructive` or
  `privileged`

When several rules apply, the action MUST use the most severe applicable risk.
Effect dimensions do not reduce scope, approval, or grant checks and MUST NOT be
used to downgrade a more severe risk label.

`expected_effects` is an application-produced prediction for one validated
input and state snapshot. `actual_effects` is the application's record of what
the invocation applied or may have applied. Both are arrays of effect entries
under the mandatory core Effect Model; each declared `effect_id` MUST appear at
most once in either array. Standard instance members `resource_key`,
`resource_keys`, and `safe_summary` MAY appear without an application-specific
schema. An `expected_effects_schema` or `actual_effects_schema` can further
constrain entries and define additional instance members. Multiple instances of
one declared effect are represented through `resource_keys` or another
schema-defined value, not duplicate `effect_id` entries. Their canonical hashes
bind the exact arrays, including extension members and array order.

Before a commit, the application MUST reject an expected effect that exceeds
the manifest envelope. If the expected effects differ from the approved
`expected_effects_hash`, the application MUST fail with `effect_mismatch` and
require a new preview and approval. It MUST NOT silently approve the changed
impact on the user's behalf.

When an effect was or may have been attempted, the response and app receipt MUST
include `actual_effects`, `actual_effects_hash`, and `effect_outcome`. The
outcome is `applied`, `partially_applied`, `not_applied`, or `unknown`. A
successful internal atomic mutation normally reports `applied`. A denial or
validation failure before any attempt MAY omit those fields; if it reports
`not_applied`, it uses an empty `actual_effects` array and its canonical hash.

An application MUST NOT report plain success when an actual effect exceeded the
declared or approved envelope, only part of an external operation completed, or
the external outcome is unknown. A pre-effect mismatch returns
`effect_mismatch` with no mutation. Once an effect may have occurred, the app
records the safest accurate `partially_applied` or `unknown` outcome and
requires explicit reconciliation before a new attempt; it MUST NOT describe
that condition as a retryable preview mismatch.

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

The `runtime` and `user_or_app` modes allow a runtime-side approval to satisfy
the requirement. In those modes the application is accepting the runtime's
assertion that a local user approval occurred. To keep this compatible with
the rule that an application MUST NOT accept a runtime's self-assertion of
authority, that acceptance MUST be an explicit grant caveat presented to the
user at consent time, not a silent default. Action requests that rely on a
runtime-side approval SHOULD carry an approval reference (for example an
`approval_ref` identifier, or in future profiles a signed approval object) so
the approval can be linked into receipts and audited. Applications that do not
want to accept runtime approval assertions MUST declare `app` or
`runtime_and_app` for the affected actions.

Approval for a state-changing invocation MUST bind the exact action id,
manifest-declared execution mode, `idempotency_key`, `input_hash`, and
`execution_hash`. When a
preview is used, it MUST additionally bind `preview_id` and
`expected_effects_hash`; when a reservation or recovery target materially
affects the decision, it MUST bind `reservation_id` or `target_receipt_hash`.
An approval for `dry_run`, `propose`, or `reserve` MUST NOT be reused as
approval for `commit`, `compensate`, or `revert`. Expired evidence, changed
preconditions, changed expected effects, a different companion action, or a
different execution hash requires a new policy decision and any required user
approval.

### Policy Decision Object

A runtime or application that records why an action was allowed, denied, or
paused for approval MUST use a `policy.decision` object. The object explains one
component's final policy evaluation; it is evidence for audit and user
explanation, not authority that another component must accept.

```json
{
  "type": "policy.decision",
  "decision_id": "pdec_runtime_01J2ABCDEF",
  "enforcer": {
    "type": "runtime",
    "id": "application_runtime_456"
  },
  "outcome": "allow",
  "policy": {
    "id": "local-agent-action-policy",
    "version": "2026-06-25"
  },
  "reason_code": "approval_satisfied",
  "matched_rules": ["writes.require_local_approval"],
  "safe_to_show": "The requested write is within the grant and was approved.",
  "evaluated_at": "2026-06-25T16:29:59Z",
  "policy_decision_hash": "sha-256:<base64url-digest>"
}
```

`type`, `decision_id`, `enforcer`, `outcome`, `policy`, `reason_code`,
`matched_rules`, `safe_to_show`, `evaluated_at`, and `policy_decision_hash` are
REQUIRED. `outcome` MUST be `allow`, `deny`, or `require_approval`.
`enforcer.type` MUST be `runtime`, `application`, or `enterprise`; `enforcer.id`
identifies the component whose policy was evaluated. `policy.id` and
`policy.version` identify the applied policy snapshot. Identifiers and
`safe_to_show` are non-empty strings. `matched_rules` is an array of unique
strings. `evaluated_at` is an RFC 3339 UTC timestamp with the `Z` suffix.

`reason_code` is the primary stable machine-readable explanation. This draft
defines `policy_allowed`, `approval_required`, `approval_satisfied`,
`scope_denied`, `resource_denied`, `binding_invalid`, `limit_exceeded`,
`local_policy_denied`, and `app_policy_denied`. Extensions MUST use a
collision-resistant URI. `matched_rules` contains stable, non-secret rule
identifiers and MAY be empty when disclosure would reveal policy internals.
`safe_to_show` MUST be suitable for display to the affected user and MUST NOT
contain secrets, credentials, hidden rule content, or sensitive resource data.

The standard reason codes are valid only with these outcomes:

| Outcome | Allowed standard reason codes |
| --- | --- |
| `allow` | `policy_allowed`, `approval_satisfied` |
| `require_approval` | `approval_required` |
| `deny` | `scope_denied`, `resource_denied`, `binding_invalid`, `limit_exceeded`, `local_policy_denied`, `app_policy_denied` |

An extension reason-code specification MUST declare its allowed outcome. A
producer and verifier MUST reject a standard or extension reason code used with
an incompatible outcome.

The producer MUST compute `policy_decision_hash` with the Canonical Object Hash
Profile. A receipt MUST include the complete decision that directly determined
its producer's outcome and repeat the matching hash at receipt top level. A
runtime and application normally produce different decisions and hashes; an
application MUST NOT treat a runtime decision as authority to widen the Agent
Grant or bypass its own checks.

## Idempotency

Every action in mode `reserve`, `commit`, `compensate`, or `revert` MUST support
idempotency. A persisted proposal MUST support it as defined in
Proposal-Only Support.

Requests in mode `reserve`, `commit`, `compensate`, or `revert`, and requests
for a persisted proposal, MUST include `idempotency_key` in the body. In the
HTTP binding they MUST also send the same value in `Idempotency-Key`. The
application MUST reject a missing required key as `schema_invalid` before any
effect. Other requests MAY include a key for retry correlation.

Example:

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

Idempotency keys are scoped to the grant and action: the application MUST
treat a request as a duplicate only when the same key is presented under the
same `grant_id` and `action_id`. On a duplicate request, the application
SHOULD return the original result and receipt reference rather than an error,
so a retrying runtime can converge on the outcome of the first attempt.
Applications SHOULD retain idempotency state at least for the remaining
lifetime of the grant and SHOULD document their retention window.

Because one action id has exactly one static execution mode, the action id also
binds the mode for idempotency. The application's stored idempotency record for
a state-changing action MUST additionally bind `input_hash` and
`execution_hash`. Reuse of the same key with a different execution id, preview,
precondition hash, expected-effects hash, reservation, or recovery target
therefore returns `idempotency_conflict` even when the business input is
unchanged. A runtime MUST use distinct idempotency keys for different companion
action ids.

The application MUST also maintain the execution-id mapping defined by the
Action Execution Model. A new key with an old execution id, preview token, or
approval is a conflict, not a new invocation. Successful commit consumes its
preview evidence for that execution id and key; only an exact retry can obtain
the original immutable result.

After authenticating the caller and tuple, the application SHOULD check for an
exact completed idempotency record before rejecting mutable execution evidence
that expired only after the original effect. An exact retry of a completed
commit returns the original result and receipt even when its preview token has
since expired or its reservation is now `consumed`; it MUST NOT repeat the
effect or require a new reservation. This rule does not reactivate a revoked
grant or require disclosure of an old result when current authorization policy
forbids it.

An exact retry under the Receipt Hash Chain profile MUST reuse the original
finalized runtime receipt and the same `parent_receipt_hash`; it MUST NOT create
a second policy receipt for the already-authorized side effect. The application
returns the original immutable app receipt. If the same grant, action,
idempotency key, and normalized input arrives with a different parent hash, the
application MUST NOT repeat the side effect and MUST report
`integrity_mismatch` rather than attaching the original result to a competing
provenance chain.

Applications SHOULD define the semantic input-normalization procedure per
action. After that procedure, they MAY use the Canonical Object Hash Profile's
JCS rules to obtain stable JSON bytes. JCS does not define action-specific
normalization, default insertion, set ordering, or schema equivalence, so its
availability does not remove that requirement.

## Agent Grant

### Grant Object

An Agent Grant binds a user, runtime, agent, passport evidence, application,
surface, scopes, and caveats.

```json
{
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
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
    "surface_version": "2026-06-25",
    "surface_hash": "sha-256:<base64url-digest>"
  },
  "locations": ["https://code.example.com/agent-actions"],
  "actions": ["pull_request.get", "comment.create"],
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
    "max_cost_usd": 5,
    "credential_release": {
      "mode": "deny"
    }
  },
  "data_exposure": [
    {
      "source": {"kind": "action", "id": "comment.create"},
      "classes": ["repository.content"],
      "redaction": {"mode": "none"},
      "retention": {"mode": "transient", "delete_on_grant_end": true}
    },
    {
      "source": {"kind": "action", "id": "pull_request.get"},
      "classes": ["repository.content", "user.identifier"],
      "redaction": {
        "mode": "policy",
        "policy_id": "repository-visible-fields-only",
        "summary": "Only fields visible to the connected repository user are returned."
      },
      "retention": {
        "mode": "bounded",
        "max_seconds": 7200,
        "delete_on_grant_end": true
      }
    }
  ],
  "credential_profile": "proof_bound",
  "credential_binding": {
    "method": "dpop",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_hash": "sha256:...",
    "jkt": "<base64url-thumbprint>"
  },
  "audit": {
    "local_receipt": "required",
    "app_receipt": "required"
  }
}
```

This object is the authoritative Agent Grant wire shape. A grant that authorizes
any Agent Surface action MUST contain non-empty `locations` and `actions`
arrays. `locations` is the allow-list of action endpoints and `actions` is the
authoritative allow-list of action identifiers. A resource-only grant can omit
them but cannot authorize an Action Request. Scope alone is never sufficient to
select an action. The authorization server derives the issued arrays from the
exact user-approved endpoints and stages and MUST NOT add companion actions
implicitly.

The authoritative action allow-list MUST satisfy the required companion closure
defined by the Action Execution Model. A list that contains a commit or
reservation acquisition without its required stages is an invalid Grant Object,
not a partially usable delegation.

This draft defines `constraints.repositories` and
`constraints.pull_requests` as resource allow-lists. `repositories`, when
present, MUST be a non-empty array of unique non-empty application repository
identifiers. `pull_requests`, when present, MUST be a non-empty array of unique
positive integer identifiers. Each list restricts the corresponding resource
dimension; absence means that this core profile adds no restriction for that
dimension. A grant issuer MAY return a non-empty set subset of a requested list
but MUST NOT add an entry or drop the member entirely, because omission would
widen the request. Other application resource-filter members are extension
constraints and require their defining profile to specify any attenuation
order.

OAuth `authorization_details` uses this same shape with the additional RFC 9396
`type` discriminator; it does not define aliases for Grant Object fields.
`credential_binding` is authorization-server output and MUST repeat the bound
runtime, agent, and passport tuple. A DPoP binding MUST additionally contain
`jkt`; an mTLS binding MUST instead contain `x5t#S256`. Those values use the
same encoding and semantics as the corresponding standard `cnf` members.
`data_exposure` is also authorization-server output. It is the complete
effective projection derived under the Data Exposure Contract and does not
grant authority independent of the action, scope, location, and resource
members from which it was derived.

### Grant Hash

The authorization server MUST add `grant_hash` after constructing the complete
authoritative Agent Grant, including `grant_id`, subject, delegate,
`resource_server.surface_hash`, effective constraints, credential profile, and
credential binding, and the effective `data_exposure` projection. It computes
the value with the Canonical Object Hash
Profile and persists the exact hashing view for the lifetime of the grant and
its audit-retention period.

The client MUST NOT supply `grant_hash` in an authorization request. Token and
introspection responses MUST return it with the authoritative grant. An action
request and every receipt under that grant MUST carry the same value. The
application MUST compare it with current authoritative grant state and reject a
mismatch as `integrity_mismatch`; selecting state by `grant_id` and ignoring a
hash mismatch is forbidden.

Attenuating, renewing, or otherwise changing any hashed member creates a new
`grant_hash`, even when a deployment retains a related identifier for lifecycle
tracking. Token rotation alone does not change `grant_hash` when the underlying
Agent Grant object is unchanged. Parent and child grants have independent
hashes and retain their explicit derivation linkage.

`grant_hash` does not prove that a grant is active, unrevoked, or within its
remaining stateful budget. Those mutable checks still use authoritative grant
state on every action.

Numeric caveats need defined accounting. In this draft, `max_actions` counts
requests in mode `reserve`, `commit`, `compensate`, or `revert` accepted by the
application under the grant. Reservation acquisition and renewal count when
they are separate accepted actions. An explicit release is idempotent cleanup:
it does not consume `max_actions` and remains allowed while the grant is active
even when that budget is exhausted; revocation or expiry invalidates the
reservation without a release action. Reads, dry runs, proposals, and denied
requests do not consume this budget, and neither do idempotent replays:
a retry deduplicated under a previously accepted idempotency key
MUST NOT consume the budget again, or lost responses and transport retries
could exhaust a grant without producing new side effects. `max_cost_usd` is
advisory in the MVP profile: the runtime SHOULD meter agent-side cost against
it, and applications MAY additionally meter app-side cost where actions carry
a price. When a budget caveat is exhausted, further matching requests MUST be
rejected with `limit_exceeded`.

### Grant Lifecycle

```text
discover surface
  -> verify manifest
  -> choose agent
  -> verify Agent Passport
  -> derive and confirm local consent preview
  -> request grant through the selected issuance model
  -> grant-issuer consent
  -> issue or exchange Grant Credential
  -> store grant in runtime
  -> start session
  -> introspect / verify and mediate actions
  -> issue receipts
  -> expire / revoke / notify / renew
```

### Consent Preview Contract

Before initiating issuance of, storing, or using a new Agent Grant, a runtime
conforming to the Application Runtime Profile MUST present a local consent
preview and obtain an affirmative user confirmation. The preview is derived
from verified protocol state; it is not a client-authored authorization object
and MUST NOT be treated as evidence of consent by the grant issuer or resource
server. The grant issuer independently obtains the consent required by its
issuance model. A co-located runtime and grant issuer MAY use one physical
screen only when it satisfies both logical responsibilities and preserves the
exact verified sources defined below.

The runtime MUST derive the preview exclusively from:

- the verified manifest snapshot identified by issuer, `app_id`,
  `surface_version`, and `surface_hash`;
- the exact proposed semantic Agent Grant request; the OAuth profile represents
  this request as `authorization_details`, while another issuance model MUST
  preserve the same Grant Object field semantics;
- the verified runtime, agent, and passport tuple; and
- the complete Data Exposure Contract projection recomputed for the requested
  actions and scopes.

Application-authored labels, descriptions, risk summaries, redaction summaries,
and recovery descriptions are untrusted display hints. A runtime MAY display
them, but MUST preserve the corresponding machine identifier, classification,
mode, or effect value and MUST NOT let prose replace or contradict verified
semantics.

The preview MUST make the following material semantics visible before the user
confirms:

- application identity, issuer, surface version, and an inspectable surface
  hash;
- runtime identity, agent identity, passport hash, and the kind of passport
  evidence verified;
- exact action identifiers, scopes, locations, and resource filters;
- absolute expiration time, human-readable duration, budgets, and other
  constraints;
- each selected action's risk, static execution mode, approval requirement,
  and required companion stages;
- maximum effect envelopes, highlighting write, shared, external, and
  irreversible effects; actions with an external effect MUST also warn that
  their actual outcome can be partial or unknown;
- required dry-run or reservation stages and available compensation or revert
  actions with their limitations;
- requested credential profile, credential-release policy, any parent or child
  grant fields actually present in the proposed request, and receipt
  requirements; and
- effective data-exposure sources, class identifiers and classifications,
  redaction policy, and retention obligations.

The runtime SHOULD additionally identify its locally known operator and
processing environment. Such operator, model-provider, tool-recipient, and
concrete proof-method statements are runtime-local assertions unless backed by
separate verified evidence. They MUST be labeled with their verification status
and MUST NOT be presented as application-verified Grant Object fields. This
profile does not claim complete downstream-recipient coverage; remote-agent and
training-use policies remain separate profiles.

A runtime MAY group or summarize repeated entries, but every selected action,
companion stage, resource filter, material effect, and exposure source MUST
remain inspectable before confirmation. Progressive disclosure MUST NOT hide an
irreversible or external effect, an unknown value, an incomplete exposure
contract, credential release, or a material recovery limitation behind a
benign aggregate label. A scope-only summary is insufficient because action
and execution-stage allow-lists are independently authoritative.

The user MAY select a strict subset only when the resulting request remains
valid and closed over every required companion action. The runtime MUST derive
and present a new projection from that exact reduced request. It MUST NOT repair
an invalid selection by silently adding an action, scope, location, resource,
or data path. If local policy narrows the request, the narrowed exact request is
the one that MUST be shown and confirmed.

The local preview lifecycle is:

```text
derived -> presented -> confirmed | declined
   ^           |
   +--- stale -+
confirmed -> request sent -> granted | rejected
```

Any change to issuer, application, surface hash, runtime-agent-passport tuple,
actions, scopes, locations, resource filters, constraints, budgets, expiration,
credential profile, receipt requirements, execution or effect declarations,
or resolved exposure contracts makes the preview stale. A stale preview MUST
be regenerated and confirmed again before a request is sent or a returned grant
is stored or used. Decline terminates the local flow; the runtime MUST NOT
continue authorization in the background.
Changing a runtime-local operator, processing-path, concrete proof-method, or
proof-key assertion that was shown to the user also makes the local preview
stale, even when it does not alter the semantic Grant request. That local
assertion is not sent as authority to the grant issuer.

Presentation timestamps, UI session identifiers, authentication gestures, and
local confirmation timeouts are local policy and are not portable consent
evidence.

After authorization, the runtime MUST compare the returned authoritative Grant
Object with the exact locally confirmed request and the same pinned manifest.
Immediately before storing or using the result, it MUST also re-evaluate every
semantic and runtime-local input that produced the preview. A changed issuer,
surface, request, tuple, or passport validity state invalidates the issuance
result and requires a new issuer consent flow. If only a labeled runtime-local
operator, processing-path, concrete proof-method, or proof-key assertion
changed, the runtime MUST regenerate the local preview for the returned grant
and obtain fresh local confirmation before storage or use; it does not treat
that assertion as new grant authority.

The returned object adds grant-issuer output such as `grant_id`,
subject, credential binding, effective exposure projection, and `grant_hash`.
It MAY be a semantically narrower valid subset under this comparison:

- issuer, `app_id`, surface version and hash, runtime id, agent id, passport
  hash, and requested credential profile MUST remain exactly equal;
- returned actions, scopes, and locations MUST be set subsets of the confirmed
  values and MUST remain closed over required companion actions;
- `expires_at` MAY be no later, and `max_actions` and `max_cost_usd` MAY be no
  greater. Returned `repositories` and `pull_requests` MUST remain present when
  requested and MUST be non-empty set subsets. Every other constraint MUST
  remain structurally equal unless its defining profile supplies an explicit
  attenuation order understood by the runtime; implementations MUST NOT guess
  that an unknown array, enum, or extension value is more restrictive;
- requested audit profile and required signer roles MUST remain equal;
  issuer-derived signer keys can be added only when the selected issuance and
  receipt-signing profiles define that output;
- returned credential binding MUST repeat the confirmed tuple and satisfy the
  requested credential profile; a `proof_bound` request MUST NOT become a
  bearer credential. Its confirmation key, certificate thumbprint, or channel
  binding MUST match the evidence authenticated or registered for that runtime
  during issuance; merely recognizing the method or key format is insufficient.
  If the local preview displayed a concrete intended proof method or key, the
  returned binding MUST match it or the runtime MUST reject the result and
  obtain fresh confirmation; and
- effective `data_exposure` MUST be the exact deterministic projection
  recomputed for the returned action and scope subsets.

Manifest-declared action modes, effects, risks, and recovery semantics are not
grant fields that the issuer can rewrite; they remain fixed by the returned
grant's pinned surface hash. Subject, grant id, credential binding details,
effective projection, and hash are expected server output, not authority
widening. Any value that is wider, incomparable under these rules, or bound to
a different tuple or surface MUST be rejected without storing or using its
credential, and the user MUST be sent through a fresh consent flow.

The grant issuer's consent view MUST present the common material semantics it
can independently derive from the verified request, manifest, tuple, and
exposure projection. It is not required to repeat runtime-local operator or
processing-path assertions. It MUST NOT trust client-supplied human-readable
prose as the authoritative description. Its final approved subset remains
authoritative for issuance. The local runtime preview reduces surprise and
app-controlled UI risk, but it does not replace issuer authentication, consent,
or the application's obligation to enforce the issued grant.

Expected effects and previews MUST be identified as maximum or predicted
semantics rather than a guarantee that a commit will occur. Compensation MUST
NOT be described as exact rollback; only a declared `revert` action with
enforceable prior-state preconditions can make that narrower claim. Missing or
unknown actions, exposure classes, source contracts, risk values, or effect
values fail closed as `surface_incompatible`; omission MUST NOT be rendered as
"no access", "no risk", or "no exposure".

This contract standardizes the semantic inputs and staleness rules for a
preview, not layout, localization, icons, ordering, accessibility mechanisms,
biometric confirmation, or example simulations. It deliberately defines no
`preview_id`, consent hash, signed approval object, or portable human-readable
wire payload. Such evidence requires a separate approval profile.

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

Because this draft does not require browser-to-localhost communication, the
consent flow SHOULD support a completion mode that does not depend on a
loopback redirect — for example an OAuth device-authorization-style exchange
or an app-mediated pairing code that the runtime polls or receives over its
outbound channel.

Pros:

- Easy for applications to enforce.
- Works with existing consent and scope infrastructure.
- Does not require a new global trust authority.

Cons:

- The app learns runtime and agent metadata.
- Each app needs to implement agent grant issuance.

#### Model B: Runtime-Held Grant Plus App Token

The app issues a scoped token to the runtime. The runtime locally binds that
token to an agent, passport, and policy. To satisfy the Grant-Enforcing
Application profile, the application MUST also establish the runtime, agent,
and passport binding from app-verifiable state or a verified proof at action
time. A runtime-only assertion of that binding is insufficient.

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

- Requires a signed-grant profile, trust stores, signer-key lifecycle,
  revocation semantics, and stronger interop work beyond the receipt profile.
- Too large for the first MVP.

### OAuth Grant Lifecycle Profile

This profile maps an Agent Grant onto OAuth Rich Authorization Requests, Token
Exchange, Token Introspection, and Token Revocation. It applies when the Agent
Surface Manifest declares OAuth endpoints and the Agent Grant authorization
details type defined by this draft.

The authorization server and resource server MAY be operated by the same
application, but they retain their OAuth roles. The authorization server issues
and manages Grant Credentials. The application action endpoint is the resource
server and continues to enforce the semantic Agent Grant for every action.

#### Rich Authorization Request Profile

An Agent Grant authorization request MUST use the RFC 9396
`authorization_details` parameter encoded as a JSON array containing exactly
one object whose `type` is:

```text
https://github.com/0al-spec/agent-surface/authorization-details/agent-grant
```

The authorization server metadata MUST list this value in
`authorization_details_types_supported`. The Agent Surface Manifest `auth`
object MUST mirror that value and the standard `grant_types_supported` values
used by the deployment; conflicting metadata makes the OAuth profile invalid.

Example, shown decoded from its form-encoded authorization request parameter:

```json
[
  {
    "type": "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant",
    "locations": ["https://code.example.com/agent-actions"],
    "actions": ["pull_request.get", "comment.create"],
    "delegate": {
      "runtime": "application_runtime_456",
      "agent": "local_agent_789",
      "passport_ref": "agent-passport://local-agent",
      "passport_hash": "sha256:..."
    },
    "resource_server": {
      "app_id": "code.example.com",
      "issuer": "https://code.example.com",
      "surface_version": "2026-06-25",
      "surface_hash": "sha-256:<base64url-digest>"
    },
    "scopes": ["pull_request.read", "pull_request.comment"],
    "constraints": {
      "repositories": ["example-org/example-repo"],
      "pull_requests": [13],
      "expires_at": "2026-06-25T20:00:00Z",
      "write_approval": "required",
      "max_actions": 20
    },
    "credential_profile": "proof_bound",
    "audit": {
      "local_receipt": "required",
      "app_receipt": "required"
    }
  }
]
```

The Agent Grant authorization details type has the following contract. Except
for the required RFC 9396 `type` discriminator, its field names and semantics
are the authoritative Grant Object wire shape defined above:

- `type`, `delegate`, `resource_server`, `scopes`, `constraints`,
  `credential_profile`, and `audit` are REQUIRED.
- `delegate` MUST contain `runtime`, `agent`, and `passport_hash`; it MAY contain
  `passport_ref`.
- `resource_server` MUST contain `app_id`, `issuer`, `surface_version`, and the
  verified `surface_hash`.
- `constraints` MUST contain `expires_at`; other fields use the semantics of the
  Agent Grant object.
- `credential_profile` MUST be `compatibility_bearer` or `proof_bound` and maps
  to the credential profiles defined in this draft.
- A request for action authority MUST contain non-empty RFC 9396 common
  `locations` and `actions` arrays of published action endpoints and Agent
  Surface action identifiers; omission requests no action authority. The
  granted values are authoritative allow-lists and every
  invoked action MUST be a member. The authorization applies to the product of
  the granted actions, locations, scopes, and resource filters; every allowed
  combination MUST be published by the surface and semantically compatible.
- `grant_id`, `grant_hash`, `subject`, `credential_binding`, and
  `data_exposure` MUST NOT be supplied by the client in an authorization
  request; they are
  authorization-server output.
- A client MAY request an `audit.receipt_signing` profile and signer roles, but
  it MUST NOT supply authoritative `signer_keys`. Before issuance, the
  authorization server MUST reject a request containing those entries, derive
  them from issuer metadata and the authenticated runtime key registration,
  and include the resulting pins in `grant_hash`.
- The request MUST NOT supply `subject.user` or another asserted user identity;
  the authorization server derives the subject from its authenticated user
  session or, at the token endpoint, from the validated `subject_token`.

The authorization server MUST reject unknown fields, unknown action or scope
values, a mismatched `resource_server.app_id` or
`resource_server.surface_version`, a mismatched `resource_server.surface_hash`,
an unverified passport hash, an action set that is not closed over required
companion dependencies, or constraints that are invalid for the published
surface. It MUST use the RFC 9396
`invalid_authorization_details` error for malformed or unsupported Agent Grant
authorization details.

Authorization Code use of this profile MUST use PKCE with the `S256` challenge
method. Deployments SHOULD use Pushed Authorization Requests when supported so
the rich grant request is integrity-protected and is not exposed in browser
URLs, history, or intermediary logs.

The OAuth `scope` request parameter MUST NOT be used in an authorization or
token-exchange request that carries this Agent Grant `authorization_details`
type. The authorization server MUST reject such a request with `invalid_request`.
Independent OAuth authorization therefore requires a separate request and
credential; this profile never silently drops or unions independent scopes.

In token and introspection responses, the standard OAuth `scope` member MAY be
an exact space-delimited projection of the granted Agent Grant `scopes` for
legacy resource-server integration. If present, it MUST contain exactly that
projection; the granted `authorization_details` remains authoritative. A
resource server MUST reject a credential when the two representations conflict.

The authorization server's consent view MUST satisfy the Consent Preview
Contract's material-semantics and untrusted-label requirements using its own
verified copy of the request and pinned manifest. The user MAY approve a strict
subset. The authorization server
MUST present each required companion closure as one approval group. It MUST
materialize the exact approved action stages in the returned `actions`
allow-list, reject a selection that breaks required closure, compare the
requested and approved objects according to Agent Grant semantics rather than
using raw JSON equality, and MUST NOT enrich the result with additional
authority.

The token response MUST return the granted `authorization_details` as required
by RFC 9396. For this type, the returned object MUST be enriched with the
authoritative `grant_id`, `subject`, delegate binding, effective constraints,
`credential_binding`, effective `data_exposure`, and `grant_hash` assigned by
the authorization server. The
authorization server and resource server MUST retain or receive the same
granted object for later action verification and introspection.

#### OAuth Token Exchange Profile

A runtime MAY exchange a user-authorized subject token for an Agent Grant
Credential using RFC 8693. The request uses the standard token endpoint and
form-encoded parameters:

```http
POST /oauth/token HTTP/1.1
Host: code.example.com
Content-Type: application/x-www-form-urlencoded
DPoP: <proof-jwt>

grant_type=urn:ietf:params:oauth:grant-type:token-exchange
&resource=https%3A%2F%2Fcode.example.com%2Fagent-actions
&requested_token_type=urn:ietf:params:oauth:token-type:access_token
&subject_token=<user-authorized-token>
&subject_token_type=urn:ietf:params:oauth:token-type:access_token
&authorization_details=<percent-encoded-agent-grant-details>
```

The Token Exchange request has these additional ASP requirements:

- The runtime MUST authenticate to the token endpoint. For a
  `proof_bound` request, it MUST authenticate using the key or channel binding
  that will identify the bound runtime.
- A DPoP-bound exchange MUST include a `DPoP` HTTP header containing a proof for
  the token request, as required by RFC 9449. The authorization server MUST
  validate that proof independently of OAuth client authentication and derive
  the issued token's `cnf.jkt` and Agent Grant `credential_binding.jkt` from the
  proof key. An mTLS-bound exchange instead derives `cnf["x5t#S256"]` and the
  corresponding credential binding from the client certificate presented on
  the token request; it does not use the example's DPoP header.
- `subject_token` MUST represent the authenticated user's authorization for the
  requested application and MUST be valid at the time of exchange.
- `resource` MUST contain exactly the published Agent Surface action resource
  URI. An `audience` value MAY additionally name the same logical resource
  server but MUST NOT add another target.
- `requested_token_type` MUST be
  `urn:ietf:params:oauth:token-type:access_token` for the OAuth Grant Credential
  profile in this draft.
- `authorization_details` MUST contain exactly one Agent Grant object of the
  type defined above and MUST be semantically equal to or narrower than the
  authorization approved by the user.
- If OAuth client authentication does not establish the runtime identity, the
  request MUST include an `actor_token` representing the runtime and the
  corresponding `actor_token_type`. The authorization server MUST verify it and
  bind the output credential to that runtime. For a `proof_bound` request, the
  actor token MUST itself be sender-constrained or presented through the same
  bound channel authentication.

The authorization server MUST validate the subject token, runtime identity,
agent and passport binding, resource, requested action and location allow-lists,
scopes, constraints, and credential profile. Returned `actions` and `locations`
MUST be subsets of the source authorization. The exchange MUST NOT add a
stronger companion stage under a shared scope, increase authority, widen
resources, relax approval or receipt requirements, extend beyond the approved
expiration, or replace `proof_bound` with `compatibility_bearer` without fresh
user consent. Any attenuated action subset MUST remain closed over its required
companion dependencies; otherwise the exchange MUST reject it rather than add
missing stages.

RFC 8693 does not itself create lifecycle linkage between input and output
tokens. This ASP profile does: the authorization server MUST record the source
authorization or parent grant from which the Agent Grant was derived. Revoking
or invalidating that source authority MUST revoke or suspend every derived Agent
Grant unless an independently approved grant replaced it.

Issuance also MUST preserve cumulative caveats across that derivation graph.
Every accepted action or cost charge MUST atomically consume both the derived
grant's local budget and the authoritative remaining budget of every ancestor
authorization from which it derives. Repeating an exchange therefore cannot
multiply `max_actions`, `max_cost_usd`, or another stateful budget. The
authorization server MUST treat semantically equivalent exchanges with the
same source authorization, client and delegate tuple, target resource,
normalized Agent Grant details, and proof-binding key as idempotent: it MUST
reuse the same `grant_id`, `grant_hash`, and accounting state, although it MAY
rotate the access-token representation.

Example successful response:

```json
{
  "access_token": "<opaque-grant-credential>",
  "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
  "token_type": "DPoP",
  "expires_in": 1800,
  "scope": "pull_request.read pull_request.comment",
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "authorization_details": [
    {
      "type": "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant",
      "locations": ["https://code.example.com/agent-actions"],
      "actions": ["pull_request.get", "comment.create"],
      "subject": {
        "user": "app-user-7f3a"
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
        "surface_version": "2026-06-25",
        "surface_hash": "sha-256:<base64url-digest>"
      },
      "scopes": ["pull_request.read", "pull_request.comment"],
      "constraints": {
        "repositories": ["example-org/example-repo"],
        "pull_requests": [13],
        "expires_at": "2026-06-25T20:00:00Z",
        "write_approval": "required",
        "max_actions": 20
      },
      "credential_profile": "proof_bound",
      "credential_binding": {
        "method": "dpop",
        "runtime_id": "application_runtime_456",
        "agent_id": "local_agent_789",
        "passport_hash": "sha256:...",
        "jkt": "<base64url-thumbprint>"
      },
      "audit": {
        "local_receipt": "required",
        "app_receipt": "required"
      },
      "grant_id": "grant_123",
      "grant_hash": "sha-256:<base64url-digest>"
    }
  ]
}
```

The response MUST include `access_token`, `issued_token_type`, `token_type`,
`expires_in`, `grant_id`, `grant_hash`, the exact `scope` projection defined
above, and the granted `authorization_details`. This also satisfies the RFC
8693 requirement to return `scope` when the issued scope differs from the
request. The `token_type` and method-specific credential confirmation data MUST
match the selected
credential profile and the binding established at the token endpoint. A
refresh token SHOULD NOT be issued by default; if one is issued, it MUST
preserve the tuple binding, attenuation, and revocation linkage of the Agent
Grant and follow RFC 9700 refresh-token replay protections.

Top-level `grant_id` and `grant_hash` MUST exactly match the same members in the
sole returned Agent Grant authorization-details object. The client MUST reject
the token response if either projection is absent or mismatched; it MUST NOT
select one representation and ignore the other.

Token responses containing a Grant Credential or its authorization details MUST
use `Cache-Control: no-store` and `Pragma: no-cache`.

#### Grant Introspection Profile

The manifest `agent_api.grant_introspection_url` MAY identify the same RFC 7662
endpoint as `auth.introspection_url`. A protected resource or runtime
introspects a Grant Credential using an authenticated RFC 7662 request with the
required `token` parameter and optional `token_type_hint`. The endpoint MUST
authenticate and authorize the caller and disclose only grant data that caller
needs.

For an inactive, unknown, or undisclosable credential, the response MUST be:

```json
{
  "active": false
}
```

It MUST NOT reveal whether the credential was unknown, expired, revoked, or
outside the caller's authority.

For an active Grant Credential, the response MUST include the RFC 7662 fields
`active`, `client_id`, `scope`, `token_type`, `exp`, `iat`, `sub`, `aud`, and
`iss`, plus the ASP fields `grant_id`, `grant_hash`, `resource_server`, `delegate`,
`constraints`, `credential_binding`, and `authorization_details`. An active
proof-bound credential MUST additionally include the method-specific standard
`cnf` confirmation member. The `sub` value SHOULD be a stable app-scoped
pseudonymous user identifier. `client_id` identifies the OAuth client;
`delegate.runtime` is the authoritative ASP runtime binding and MAY differ from
`client_id`.

The `authorization_details` member MUST contain the granted Agent Grant object,
filtered only to data the authenticated caller may receive. Top-level `sub`,
`grant_id`, `grant_hash`, `resource_server`, `delegate`, `constraints`, and
`credential_binding` are projections of that object and MUST match it; `sub`
corresponds to `subject.user`. A resource server MUST treat a mismatch as an
invalid grant proof rather than selecting one representation. A filtered
response still MUST carry `grant_hash` as an opaque authoritative commitment,
but a caller MUST NOT claim to have recomputed it without the complete Grant
Object.

For DPoP, `cnf` MUST contain `jkt` as specified by RFC 9449; for mTLS, it MUST
contain `x5t#S256` as specified by RFC 8705. The confirmation value MUST match
the method-specific value in the Agent Grant `credential_binding`. The resource
server MUST reject a missing or mismatched confirmation member. A Compatibility
Bearer Credential MUST NOT fabricate a `cnf` member.

```json
{
  "active": true,
  "client_id": "application_runtime_456",
  "scope": "pull_request.read pull_request.comment",
  "token_type": "DPoP",
  "exp": 1782417600,
  "iat": 1782415800,
  "sub": "app-user-7f3a",
  "aud": "https://code.example.com/agent-actions",
  "iss": "https://code.example.com",
  "cnf": {
    "jkt": "<base64url-thumbprint>"
  },
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "resource_server": {
    "app_id": "code.example.com",
    "issuer": "https://code.example.com",
    "surface_version": "2026-06-25",
    "surface_hash": "sha-256:<base64url-digest>"
  },
  "delegate": {
    "runtime": "application_runtime_456",
    "agent": "local_agent_789",
    "passport_ref": "agent-passport://local-agent",
    "passport_hash": "sha256:..."
  },
  "constraints": {
    "repositories": ["example-org/example-repo"],
    "pull_requests": [13],
    "expires_at": "2026-06-25T20:00:00Z",
    "write_approval": "required",
    "max_actions": 20
  },
  "credential_binding": {
    "method": "dpop",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_hash": "sha256:...",
    "jkt": "<base64url-thumbprint>"
  },
  "authorization_details": [
    {
      "type": "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant",
      "locations": ["https://code.example.com/agent-actions"],
      "actions": ["pull_request.get", "comment.create"],
      "subject": {
        "user": "app-user-7f3a"
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
        "surface_version": "2026-06-25",
        "surface_hash": "sha-256:<base64url-digest>"
      },
      "scopes": ["pull_request.read", "pull_request.comment"],
      "constraints": {
        "repositories": ["example-org/example-repo"],
        "pull_requests": [13],
        "expires_at": "2026-06-25T20:00:00Z",
        "write_approval": "required",
        "max_actions": 20
      },
      "credential_profile": "proof_bound",
      "credential_binding": {
        "method": "dpop",
        "runtime_id": "application_runtime_456",
        "agent_id": "local_agent_789",
        "passport_hash": "sha256:...",
        "jkt": "<base64url-thumbprint>"
      },
      "audit": {
        "local_receipt": "required",
        "app_receipt": "required"
      },
      "grant_id": "grant_123",
      "grant_hash": "sha-256:<base64url-digest>"
    }
  ]
}
```

The response MUST describe current authoritative state and MUST use
`Cache-Control: no-store`. A resource-server enforcement point that does not
share the authorization server's authoritative grant state MUST introspect on
every action and MUST NOT positively cache `active: true`. This prohibition is
required by this profile's immediate revocation semantics; deployments that
need positive caching must define and advertise a different bounded stale-use
profile rather than claiming conformance to this one.

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

This draft defines two credential profiles:

- **Compatibility Bearer Credential Profile**: an explicitly labeled
  development or compatibility profile in which the runtime holds a bearer
  credential outside every agent-visible context. It is not proof-bound and
  MUST NOT be advertised as the Proof-Bound Credential Profile.
- **Proof-Bound Credential Profile**: every Agent Surface action uses a
  sender-constrained credential or an app-authenticated runtime session that
  requires possession of a bound key or channel credential on every request. A
  reusable session identifier, cookie, or bearer token by itself does not
  satisfy this profile.

A future draft is expected to define additional interoperable proof profiles.

Regardless of representation, a Grant Credential MUST let the application
establish or obtain from authoritative grant state all of the following:

- the active `grant_id`;
- the intended application or resource-server audience;
- the bound runtime identity;
- the bound agent identity and passport hash; and
- the credential-binding method and any proof-of-possession key or session
  binding that it requires.

The application MUST reject a presentation whose binding does not match the
grant's `delegate` or `credential_binding` values. An introspection or
server-side session profile MAY supply these values indirectly, but the runtime
MUST NOT substitute its own unverified assertion for application-verifiable
binding evidence.

Proof-Bound Credential Profile methods include DPoP, mTLS, and equivalent
proof-of-possession mechanisms. A DPoP method MUST follow RFC 9449, bind the
proof to the request, and accept proofs only within a limited freshness window.
It SHOULD track `jti` values during that window and reject duplicates where the
deployment can maintain the required shared state. Reuse of a server-provided
DPoP nonce MUST NOT by itself be treated as replay. An mTLS method MUST follow
RFC 8705, require the protected-resource request to use the certificate bound
to the token, and reject a certificate mismatch or an invalidated binding.
Reuse of that bound certificate across valid requests MUST NOT by itself be
treated as replay. A proof-bound server session MUST be active, bound to the
grant and runtime, and authenticated with its bound key or channel credential
on every request.

A bare bearer credential MAY be used only in the Compatibility Bearer
Credential Profile. It remains outside every agent-visible context and is
subject to short expiration, audience restriction, revocation, and
application-side grant verification.

### Subdelegation

A runtime MAY use a subagent, remote model, MCP server, tool, adapter, or an
ungranted secondary runtime to help execute delegated work. Receiving task
context does not make that component a grant delegate and does not transfer
Agent Grant authority.

The runtime MUST treat every downstream component, including an ungranted
secondary runtime, as untrusted with respect to application authority. It MUST
NOT forward a Grant Credential, raw application credential, approval artifact,
or an authorization path that can invoke an Agent Surface outside runtime
mediation. A downstream component that needs an application action MUST request
a typed action through the controlling runtime; the runtime MUST evaluate the
original grant, policy, approval, and redaction rules again for that request.

The application MAY instead issue a child grant that makes a secondary runtime
a separate delegate. Once that grant is issued, the child runtime is the
controlling runtime for actions under the child grant and sends them directly to
the application with its own bound credential; those actions do not route
through the parent runtime. The parent runtime MUST NOT present the child
credential or mediate an action as if it originated from the child.

The child grant MUST record `parent_grant_id` and `parent_runtime_id`, and MUST
have equal or narrower actions, locations, scopes, resources, caveats,
credential-release permissions, and lifetime. When the parent has an `actions`
allow-list, the child's list MUST be a subset; when the parent has no action
authority, the child MUST NOT add it. A child MUST NOT add a stronger companion
stage, effect envelope, or weaker approval semantics under a reused scope. The
child action subset MUST remain closed over required companion dependencies;
the application MUST reject an unclosed subset instead of adding stages. The
child `resource_server.app_id`, issuer, surface version, and `surface_hash` MUST
exactly equal the parent's values. Derivation onto another surface snapshot
requires a future explicit compatibility profile or fresh independent user
consent. The application MUST revoke or suspend the child
grant when the parent grant expires, is revoked, or loses the authority from
which the child grant was derived. A parent grant or credential MUST NOT be
forwarded as implicit subdelegation.

### Grant Verification

Applications MUST verify every action against grant state:

- grant exists and is active
- recomputed `grant_hash` matches both the presented action context and current
  authoritative Grant Object
- `resource_server.surface_hash` matches the retained, verified manifest
  snapshot used to interpret the action and its schemas
- grant credential or proof is valid
- grant is bound to the user
- grant is bound to the runtime
- grant is bound to the agent/passport hash
- credential-binding method and proof-of-possession requirements are satisfied
- for DPoP, the proof is request-bound and within the limited acceptance window;
  when `jti` replay tracking is enabled, its `jti` has not already been accepted;
  reuse of a valid server nonce is not rejected by itself
- for mTLS, the presented certificate matches the certificate bound to the token
  and the binding has not been invalidated; reuse of the matching certificate is
  not rejected by itself
- for a proof-bound server session, the session is active, bound to the grant
  and runtime, and authenticated with the bound key or channel credential
- the grant contains a non-empty `actions` allow-list, the requested action
  identifier is a member, is served at a granted `location`, and remains
  compatible with the granted scopes and resource constraints
- the grant action allow-list is closed over every required companion
  dependency in its pinned manifest snapshot
- request `execution.mode` exactly matches the action declaration in the
  manifest snapshot selected by `surface_hash`
- whenever the action declares `input_hash_profile`, recomputed `input_hash`
  matches the request and any verified runtime receipt
- for a state-changing action, recomputed `execution_hash` matches the request
  and verified runtime receipt
- referenced companion actions resolve in the same manifest snapshot and the
  invoked companion action is independently granted
- any preview token is unexpired and bound to this app, grant, session,
  surface, action, input, preconditions, and expected effects
- declared preconditions still hold immediately before a state change
- any required reservation is active, holder-bound, resource-compatible, and
  atomically consumable by this commit
- expected effects remain within the manifest declaration and applicable
  schemas before mutation
- a compensation or revert has independent current authority and a verified
  eligible target application receipt with unrecovered confirmed effects
- a revert has receipt-bound prior-state evidence and its declared current-state
  preconditions hold atomically with restoration
- scope permits the action
- resource constraints permit the target object
- expiration has not passed
- action count and cost bounds have not been exceeded
- approval caveats are satisfied
- idempotency key is valid

After an effect was or may have been attempted, the application MUST validate
and record actual effects against the core Effect Model and any declared
`actual_effects_schema`. Post-effect uncertainty does not retroactively satisfy
a failed precondition or authorize an undeclared effect.

Runtimes SHOULD verify:

- grant is active
- `grant_hash` matches the complete grant returned at issuance or introspection
- `surface_hash` matches the verified manifest snapshot pinned for that grant
- local user has not revoked the app, runtime, or agent
- Agent Passport is valid
- requested action is compatible with the Agent Passport capability set
- local policy allows the action
- local approval is present when required
- action input matches the declared schema
- execution mode, context, and hashes match the pinned action declaration
- preview evidence is current and any required reservation belongs to the
  bound tuple
- expected effects and recovery limitations are presented before approval
- secrets and credentials are not exposed to the agent
- any subagent, tool, adapter, remote model, or secondary runtime remains
  subject to the same runtime mediation and does not receive implicit authority

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
- execution modes and required companion stages
- declared effect envelopes and effect schemas
- declared data classes, redaction, and retention obligations
- reservation requirements and available recovery actions
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
- supported execution stages and any missing preview or reservation support
- maximum effects and recovery limitations
- effective data exposure and any unsupported retention obligations
- expected sandbox constraints

The matching result is advisory input to the local Consent Preview Contract. It
MUST be reconciled with the exact request and pinned manifest; a stale matching
summary cannot substitute for the required preview.

## Observability Context

ASP uses W3C Trace Context for cross-component diagnostic correlation. An ASP
session, action, event, and receipt MAY participate in a distributed trace, but
trace context is never authorization, identity, idempotency, or proof that two
objects belong to the same grant.

JSON envelopes that carry observability context use `trace_id` and `span_id`.
`trace_id` MUST be 32 lowercase hexadecimal characters representing 16 bytes
and MUST NOT be all zero. `span_id` MUST be 16 lowercase hexadecimal characters
representing 8 bytes and MUST NOT be all zero. These are projections of the W3C
`trace-id` and `parent-id` formats. `session_id` and `session_generation` remain
the ASP lifecycle and accounting context and MUST continue to be validated
independently.

When an implementation claims the Application Runtime or Receipt-Producing
profile, its `session.start`, `action.request`, `action.result`, and receipt
envelopes MUST carry `session_id`, `session_generation`, `trace_id`, and the
producer's `span_id` as shown below. Each runtime and application MUST record
the identifiers from the envelope or receipt it produces in the corresponding
local log entry so those logs can be joined without parsing human-readable
messages. Trace and session ids can match across components while each producer
records its own span id. This draft defines correlation fields, not a telemetry
export protocol or vendor backend.

For an HTTP binding, a component carrying valid ASP observability context MUST
send `traceparent`. A component participating in an incoming W3C trace MUST
propagate `traceparent` and `tracestate` according to W3C Trace Context, subject
to its defined trust-boundary privacy policy. It preserves a valid incoming
`trace_id`, creates a fresh `span_id` for its own operation, and propagates that
child context downstream. A receipt records the span of the component that
produced it. Runtime and application receipts for one action therefore normally
share `trace_id`, `session_id`, and `session_generation` but have different
`span_id` values.

An intermediary is allowed to create another span, so a receiver MUST NOT
require the JSON `span_id` to equal the `parent-id` in the HTTP header after
intermediation. For local processing, a valid `traceparent` takes precedence
over the JSON projection. If no valid header exists and a verified parent
receipt is available, the receiver continues the parent receipt's `trace_id`
with a new span. Otherwise it uses a valid JSON `trace_id` or starts a new
trace, in that order.

If the selected processing trace differs from a verified parent receipt's
trace because an intermediary or trust boundary restarted it, the child receipt
MUST include `linked_trace_id` equal to the parent `trace_id`. Without such a
documented restart, parent and child receipts MUST use the same `trace_id`.
`linked_trace_id` uses the same format as `trace_id` and is included in the
receipt hash. Invalid or conflicting trace context MUST NOT cause an otherwise
unauthorized action to be accepted, and it MUST NOT bypass grant, session, or
receipt-link verification.

Trace identifiers MUST be generated without embedding user, agent, resource,
tenant, or policy semantics. Producers MUST apply the same disclosure and
retention controls to `tracestate` and correlated telemetry as to other audit
metadata. An Agent Adapter preserves `session_id` and a valid `trace_id` across
its boundary and creates a new `span_id` for each adapter operation.

## Sessions and Actions

### Session Authority and Lifecycle

An ASP session is a bounded orchestration record for work performed under one
Agent Grant. A session does not mint authority, widen a grant, keep an expired
grant alive, or make an agent a protocol principal. Every session is bound to
exactly one authoritative tuple consisting of:

- the grant `subject.user`, `grant_id`, and `grant_hash`
- the grant-bound `runtime`, `agent`, and `passport_hash`
- the application `app_id`, `surface_version`, and `surface_hash`

The application is authoritative for the application-side session record and
state. The runtime is authoritative for whether the corresponding local worker
is still running, but a local process state MUST NOT cause the application to
accept an action for a session that is absent, interrupted, or terminal in the
application record. The application MUST either assign `session_id` or validate
a caller-proposed value for uniqueness before creating the record. A
`session_id` is a correlation identifier, not a credential, and MUST NOT be
accepted as evidence of the bound user or delegate tuple.

The application record MUST contain the bound tuple, `session_id`, a positive
integer `session_generation`, the initiating role, the current state, and the
latest transition reason. The initial generation is `1`. Every accepted resume
increments the generation by exactly one. All session-scoped bridge messages,
Action Requests, Action Responses, and receipts MUST carry the current
`session_generation`. The application and runtime MUST reject a message from an
older or future generation rather than copying its generation into local state.

ASP assigns the following authority to session participants:

| Participant | Session authority |
| --- | --- |
| User | MAY request start, observe state, cancel, or approve resume through an authenticated application or runtime UI. A user-facing gesture is not itself a bridge credential. |
| Application | Creates or accepts the authoritative record, verifies every transition and action against the current grant and tuple, exposes an authorized user view, and MAY cancel or interrupt a session to enforce application policy. |
| Runtime | MAY request start for its authenticated grant-bound tuple, observe that tuple's sessions, stop local work, request cancellation, and request resume after interruption. It MUST enforce application state in addition to local policy. |
| Agent | MAY express task intent only through its runtime. It has no direct authority to start, enumerate, observe, cancel, or resume application sessions, and MUST receive session data only through runtime-mediated, exposure-authorized paths. |

An application-started session MUST arise from an authenticated user action or
an application policy that the user authorized independently of the agent. The
application MUST deliver any proposed task through an authorized event path;
it MUST NOT use `session.start` to bypass the Data Exposure Contract. A runtime
MUST identify itself as the initiator for a runtime-originated request and MUST
NOT assert `initiated_by: "user"` merely because it observed a local gesture.
The receiving application derives the authoritative initiating role from its
authenticated context and verified policy evidence.

The normative application-side states and transitions are:

| Current state | Trigger | Next state | Requirements |
| --- | --- | --- | --- |
| absent | accepted start | `active` | Current grant, tuple, surface, and authenticated channel all verify; generation becomes `1`. |
| `active` | channel loss, runtime pause, or application safety fence | `interrupted` | New actions are rejected until an explicit resume succeeds. |
| `interrupted` | accepted resume | `active` | Same tuple, current grant and surface, fresh channel authentication, and exact prior generation; generation increments by one. |
| `active` or `interrupted` | accepted cancel | `cancelled` | Application fences new actions before acknowledging the transition and the runtime stops local work. |
| `active` | successful task completion | `completed` | Runtime reports completion and the application reconciles any outstanding action outcomes. |
| `active` | unrecoverable task failure | `failed` | Runtime or application records a stable reason without treating unknown action outcomes as rolled back. |

`cancelled`, `completed`, and `failed` are terminal. A terminal `session_id`
MUST NOT be resumed or reused for new work. A duplicate request for an already
accepted transition is idempotent only when its session id, prior generation,
target state, and bound hashes are identical. A conflicting reuse MUST fail as
`session_transition_invalid` and MUST NOT move the session.

`session.cancel` and `session.resume` requests MUST contain `session_id`, the
caller's current `session_generation`, `grant_id`, `grant_hash`, and
`surface_hash`. The channel authenticates the runtime or application actor; an
agent-supplied field inside the payload does not. A `session.state` response
MUST repeat those binding fields, report the authoritative state and generation,
and include a stable transition reason. Receipt or event transport can record
the transition, but neither is authority to create it.

Cancellation fences future work; it is not a transactional rollback. Before
acknowledging `cancelled`, the application MUST reject new Action Requests for
the session and invalidate unconsumed execution tokens and reservations bound
to it. An already-started irreversible effect retains its Action Response and
receipt outcome, including `unknown` or `partially_applied`; cancellation MUST
NOT rewrite that outcome as if no effect occurred. Cancelling a session does
not by itself revoke its Agent Grant or cancel another session under that grant.

Observation is also scoped authority. The application MAY show a user sessions
for that user's authenticated account. A runtime MAY observe only sessions for
its verified grant-bound tuple. Responses to an unauthorized or mismatched
observer MUST NOT reveal whether a guessed `session_id` exists. An agent can
receive only the current task, authorized event or action data, and state needed
for its local execution; ASP does not grant it a session-list operation.

### Session Start

Once a grant exists, an application or runtime MAY start a session.

```json
{
  "type": "session.start",
  "payload": {
    "session_id": "sess_456",
    "session_generation": 1,
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "a3ce929d0e0e4736",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_hash": "sha256:...",
    "initiated_by": "runtime",
    "surface": {
      "app_id": "code.example.com",
      "surface_version": "2026-06-25",
      "surface_hash": "sha-256:<base64url-digest>"
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

The sender treats this message as a request until the application returns an
authenticated `session.state` with state `active`, the accepted binding, and
generation `1`. A timeout or ambiguous response does not authorize the runtime
to assume that the session exists; it MAY query authoritative state using the
same tuple and proposed identifier. Retrying an identical start MUST return the
existing record, while reuse of the identifier with different bindings or task
content MUST fail as `session_transition_invalid`.

```json
{
  "type": "session.state",
  "payload": {
    "session_id": "sess_456",
    "session_generation": 1,
    "state": "active",
    "transition_reason": "start_accepted",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_hash": "sha256:...",
    "surface_hash": "sha-256:<base64url-digest>"
  }
}
```

`session.start.task` is user- or runtime-authored orchestration, not an
application data-delivery mechanism. The application MUST NOT place
application-originated content in `goal`, `inputs`, or another task member.
Opaque identifiers and filters already present in the grant constraints MAY be
copied into `inputs`; their presence identifies the task but does not disclose
the referenced application representation. Application content needed by the
agent MUST first cross an independently authorized resource, action-result, or
event path and remains subject to that source's exposure contract. Merely
listing a source in the grant's `data_exposure` projection never authorizes the
application to push its data during session start. An application that wants to
suggest a task MUST use an authorized event; the runtime decides whether to
construct a local task after applying user and local policy.

### Action Request

The agent requests an action through the runtime. The runtime sends the action to
the app only if grant and policy allow it.

The action request MUST be authorized by the HTTP authorization layer or an
equivalent proof. The `grant_id` inside the body is a correlation identifier, not
a credential.

The application MUST also verify that the supplied `session_id` and
`session_generation` identify an `active` session bound to the complete subject,
runtime, agent, passport, grant, application, and surface tuple selected by the
presented credential. Otherwise a valid grant credential could be replayed
against sessions created under other grants or against a stale generation,
corrupting session accounting and receipt linkage. Unknown, non-active,
mismatched, and stale sessions fail uniformly as `session_invalid` so the
action endpoint does not become a session-enumeration oracle.

The application MUST also verify that body `grant_hash` matches the complete
authoritative grant selected by the credential and that `surface_hash` matches
the manifest snapshot pinned by that grant. These hashes are correlation and
integrity commitments, not substitutes for the HTTP authorization proof.

If both the `Idempotency-Key` header and the body `idempotency_key` field are
present, they MUST match, and the application MUST reject a mismatch as
`schema_invalid`. Accepting a mismatched request and picking either value
would let app-side deduplication and runtime receipts refer to different
idempotency identifiers.

Example:

```http
POST /agent-actions HTTP/1.1
Host: example.com
Authorization: DPoP <grant-credential>
DPoP: <signed-proof>
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-b7ad6b7169203331-01
Idempotency-Key: idem_01HX7DS8AC6G9
Content-Type: application/json
```

```json
{
  "type": "action.request",
  "payload": {
    "session_id": "sess_456",
    "session_generation": 1,
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "b7ad6b7169203331",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "action_id": "comment.create",
    "idempotency_key": "idem_01HX7DS8AC6G9",
    "parent_receipt_hash": "sha-256:<runtime-receipt-digest>",
    "input_hash": "sha-256:<action-input-digest>",
    "execution": {
      "mode": "commit",
      "execution_id": "exec_01J2COMMENT"
    },
    "execution_hash": "sha-256:<action-execution-digest>",
    "input": {
      "repository": "example-org/example-repo",
      "pull_request": 13,
      "body": "The proposed review comment text."
    }
  }
}
```

The request's proof material MUST use the authorization mechanism selected by
the credential-binding profile. For example, a DPoP-bound credential carries a
DPoP proof in the `DPoP` header as defined by RFC 9449.

Before forwarding a state-changing action, the runtime MUST finalize its
runtime receipt and place that receipt's `receipt_hash` in
`parent_receipt_hash`. When the application requires the runtime receipt
content, the runtime MUST either submit the complete receipt through the
manifest `agent_api.receipt_url` before the action or carry it inline through a
declared action-request extension. The application MUST recompute the supplied
receipt and policy-decision hashes before treating the receipt as verified. A
bare parent hash is correlation evidence only and is insufficient when app
policy requires verification of the runtime decision.

For an action requiring runtime receipt evidence, the action declaration MUST
set `input_hash_profile` to `asp-jcs-sha-256`. The runtime and application MUST
compute the Action Input hash over the exact validated wire `input` and require
equality with both the action request and verified parent runtime receipt. A
receipt for one input MUST NOT be attached to a different input even when the
grant, action id, and idempotency key match. The semantic normalization used
for idempotency remains a separate action contract.

For `reserve`, `commit`, `compensate`, or `revert`, the runtime and application
MUST also compute `execution_hash` over the structurally validated execution
context, require it to match the request, and require the sanitized context and
hash to match the verified parent runtime receipt. The runtime MUST remove a
raw `execution_token` before producing its receipt. The application verifies
the raw request token against `execution_token_hash` and authoritative preview
state, but MUST NOT copy the token into its receipt.

### Action Response

```json
{
  "type": "action.result",
  "payload": {
    "session_id": "sess_456",
    "session_generation": 1,
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "00f067aa0ba902b7",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "action_id": "comment.create",
    "idempotency_key": "idem_01HX7DS8AC6G9",
    "execution": {
      "mode": "commit",
      "execution_id": "exec_01J2COMMENT"
    },
    "execution_hash": "sha-256:<action-execution-digest>",
    "result": "success",
    "effect_outcome": "applied",
    "actual_effects": [
      {
        "effect_id": "comment-publish",
        "operation": "publish",
        "resource_type": "comment",
        "resource_key": "comment_789",
        "visibility": "shared",
        "boundary": "internal",
        "reversibility": "irreversible",
        "domain": "communication"
      }
    ],
    "actual_effects_hash": "sha-256:<actual-effects-digest>",
    "resource": {
      "type": "comment",
      "id": "comment_789",
      "url": "https://code.example.com/example-org/example-repo/pull/13#discussion_r..."
    },
    "receipt_id": "receipt_app_abc",
    "receipt_hash": "sha-256:<app-receipt-digest>"
  }
}
```

An Action Response MUST repeat `session_id`, `session_generation`, grant and
surface hashes, `action_id`, and the idempotency key from the request. For a
state-changing action it MUST repeat the sanitized execution context and
`execution_hash`.
When an effect was or may have been attempted, it MUST return
`effect_outcome`, `actual_effects`, and `actual_effects_hash` as defined by the
Effect Model. A response MUST distinguish `partially_applied` and `unknown`
from success so a runtime does not create a new idempotency key and duplicate an
external effect.

Dry-run and reservation responses use the mode-specific objects defined in the
Action Execution Model. A failed request that performed no effect MAY omit
`actual_effects`; its structured error and any failure receipt MUST agree about
retryability and whether the outcome is known. An exact idempotent retry MUST
return the original immutable result and receipt reference.

### Proposal Flow

Proposal mode separates drafting from committing.

```text
Agent -> comment.propose
Runtime -> local policy check
App -> stores draft/proposal
Runtime/App -> optional dry_run and reservation
User/App -> approves exact input and expected effects
App -> comment.create commit
Runtime/App -> receipt
```

This is the RECOMMENDED default for early integrations.

## Receipts

### Receipt Requirements

Receipts produced under the Receipt-Producing Application profile MUST include:

- receipt id
- receipt type
- receipt hash
- grant id
- grant hash
- session id
- session generation
- trace id
- producer span id
- linked parent trace id when a trust boundary restarted tracing
- action id
- app id
- user id or stable pseudonymous user reference
- runtime id
- agent id
- Agent Passport hash
- surface version
- surface hash
- policy decision and policy decision hash
- input hash
- sanitized execution context and execution hash for state-changing actions
- preconditions and expected-effects hashes when preview evidence is used
- reservation id when it was part of the request execution context, and an
  app-produced `reservation_result` with id and state when the operation
  created or changed reservation state
- target receipt hash for compensation or revert
- revert evidence for every effect advertised as reversible
- output hash
- actual effects, actual-effects hash, and effect outcome when an effect was or
  may have been attempted
- approval reference
- idempotency key
- timestamp
- result
- error classification when failed

Fields that do not apply to the recorded outcome, such as `output_hash` for a
denial before execution, MAY be omitted. The identity, authority, trace,
decision, and result fields that do apply MUST be present and internally
consistent.

A receipt MUST NOT contain the raw `execution_token`. It carries the sanitized
execution context with `execution_token_hash`, allowing a verifier to recompute
`execution_hash` without receiving reusable preview evidence.

### Receipt Hash Chain

Every runtime and application receipt MUST contain `receipt_hash` computed with
the Canonical Object Hash Profile. A root receipt omits
`parent_receipt_hash`; it MUST NOT encode the missing parent as `null`. A
non-root receipt contains exactly one `parent_receipt_hash`, which is included
in its own hashing view.

For a runtime-mediated state-changing action whose grant requires a runtime
receipt, the application receipt MUST use the verified runtime
`receipt_hash` from the action request as its `parent_receipt_hash`. A later
runtime receipt MAY use the returned application `receipt_hash` as its parent.
This single-parent model permits branches but does not represent multi-parent
causal joins; a future profile may define a DAG representation.

A parent and child receipt for one action MUST carry identical `grant_hash`,
`surface_hash`, `session_id`, `session_generation`, `action_id`,
`idempotency_key`, `input_hash`, sanitized `execution`, and `execution_hash`.
Conditional `preview_id`,
`execution_token_hash`, `preconditions_hash`, `expected_effects_hash`,
`reservation_id`, and `target_receipt_hash` values inside that request context
MUST therefore also match. An app-only `reservation_result`,
`actual_effects`, `actual_effects_hash`, and `effect_outcome` describe the
outcome and are not required in the parent runtime receipt.
They also carry the same `trace_id` unless the child records a trust-boundary
restart with `linked_trace_id` equal to the parent's `trace_id`.
Their `span_id` and `policy_decision_hash` normally differ because each producer
records its own operation and decision. A consumer MUST recompute every
available object hash, verify these invariants, reject a cycle, and stop at any
missing or mismatched parent. Reusing one `receipt_id` for different
`receipt_hash` values is an invalid receipt conflict.

For `compensate` or `revert`, `target_receipt_hash` links to a separately
verified original application receipt but does not create another parent edge.
A verifier MUST validate that target receipt and the manifest's reciprocal
recovery relationship independently. It MUST NOT apply the same-action parent
invariants across this causal link, and MUST NOT treat the target as authority
for the recovery action.

The runtime makes its parent receipt available to the application through the
`agent_api.receipt_url` or an explicitly declared inline action-request
extension, as defined in Action Request. The application MUST NOT claim a
verified parent link when it received only an unverified hash and its policy
requires the parent content.

A hash chain is tamper-evident only relative to a trusted stored chain head or
authenticated signature. A party that can replace an entire unsigned chain can
recompute every hash. Receipt hashes and links therefore do not authenticate a
producer and do not authorize an action.

### Runtime Receipt

A runtime receipt records what the runtime observed and enforced, such as agent
intent, local policy decisions, local approvals, denials, and runtime-side
redactions.

```json
{
  "receipt_id": "receipt_runtime_abc",
  "receipt_type": "runtime",
  "receipt_hash": "sha-256:<runtime-receipt-digest>",
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "session_id": "sess_456",
  "session_generation": 1,
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "b7ad6b7169203331",
  "action_id": "comment.create",
  "app_id": "code.example.com",
  "surface_version": "2026-06-25",
  "surface_hash": "sha-256:<base64url-digest>",
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
  "input_hash": "sha-256:<action-input-digest>",
  "execution": {
    "mode": "commit",
    "execution_id": "exec_01J2COMMENT"
  },
  "execution_hash": "sha-256:<action-execution-digest>",
  "policy_decision_hash": "sha-256:<runtime-policy-decision-digest>",
  "policy_decision": {
    "type": "policy.decision",
    "decision_id": "pdec_runtime_01J2ABCDEF",
    "enforcer": {
      "type": "runtime",
      "id": "application_runtime_456"
    },
    "outcome": "allow",
    "policy": {
      "id": "local-agent-action-policy",
      "version": "2026-06-25"
    },
    "reason_code": "approval_satisfied",
    "matched_rules": ["writes.require_local_approval"],
    "safe_to_show": "The requested write is within the grant and was approved.",
    "evaluated_at": "2026-06-25T16:29:59Z",
    "policy_decision_hash": "sha-256:<runtime-policy-decision-digest>"
  },
  "approved_by": {
    "type": "runtime_user_approval",
    "approval_id": "appr_123"
  },
  "timestamp": "2026-06-25T16:30:00Z",
  "result": "authorized_for_forwarding"
}
```

### App Receipt

An app receipt records what the application actually committed, denied, or
deduplicated under a grant.

```json
{
  "receipt_id": "receipt_app_abc",
  "receipt_type": "app",
  "receipt_hash": "sha-256:<app-receipt-digest>",
  "parent_receipt_hash": "sha-256:<runtime-receipt-digest>",
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "session_id": "sess_456",
  "session_generation": 1,
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "action_id": "comment.create",
  "app_id": "code.example.com",
  "surface_version": "2026-06-25",
  "surface_hash": "sha-256:<base64url-digest>",
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
  "input_hash": "sha-256:<action-input-digest>",
  "execution": {
    "mode": "commit",
    "execution_id": "exec_01J2COMMENT"
  },
  "execution_hash": "sha-256:<action-execution-digest>",
  "output_hash": "sha256:...",
  "actual_effects": [
    {
      "effect_id": "comment-publish",
      "operation": "publish",
      "resource_type": "comment",
      "resource_key": "comment_789",
      "visibility": "shared",
      "boundary": "internal",
      "reversibility": "irreversible",
      "domain": "communication"
    }
  ],
  "actual_effects_hash": "sha-256:<actual-effects-digest>",
  "effect_outcome": "applied",
  "policy_decision_hash": "sha-256:<app-policy-decision-digest>",
  "policy_decision": {
    "type": "policy.decision",
    "decision_id": "pdec_app_01J2ABCDEG",
    "enforcer": {
      "type": "application",
      "id": "code.example.com"
    },
    "outcome": "allow",
    "policy": {
      "id": "agent-action-policy",
      "version": "2026-06-25"
    },
    "reason_code": "policy_allowed",
    "matched_rules": ["grant.active", "action.comment.create"],
    "safe_to_show": "The application accepted the authorized comment action.",
    "evaluated_at": "2026-06-25T16:30:00Z",
    "policy_decision_hash": "sha-256:<app-policy-decision-digest>"
  },
  "approved_by": {
    "type": "runtime_user_approval",
    "approval_id": "appr_123"
  },
  "resource": {
    "type": "comment",
    "id": "comment_789"
  },
  "timestamp": "2026-06-25T16:30:00Z",
  "result": "success"
}
```

### Receipt Signing Profile

The optional `asp-jws-detached` profile lets an application, runtime, or both
authenticate a receipt without changing `receipt_hash`. The base MVP permits
unsigned receipts. Unsigned means that `receipt_signatures` is absent; it MUST
NOT be represented by a JWS using `alg: none`.

A grant that requires both runtime and application signatures carries:

```json
{
  "audit": {
    "local_receipt": "required",
    "app_receipt": "required",
    "receipt_signing": {
      "profile": "asp-jws-detached",
      "required_signers": ["runtime", "application"],
      "signer_keys": [
        {
          "role": "runtime",
          "kid": "runtime-receipt-key-2026-01",
          "jwk_thumbprint": "<base64url-rfc7638-sha256-thumbprint>"
        },
        {
          "role": "application",
          "kid": "app-receipt-key-2026-01",
          "jwk_thumbprint": "<base64url-rfc7638-sha256-thumbprint>"
        }
      ]
    }
  }
}
```

For this profile, the signing view is the complete receipt with
`receipt_signatures` omitted and with `receipt_hash` retained. The signer wraps
that view as an object with `domain` equal to
`https://github.com/0al-spec/agent-surface/signature/receipt/v1` and `receipt`
equal to the signing view, then serializes the wrapper with RFC 8785 JCS. Those
UTF-8 bytes are the JWS payload.

The receipt carries a detached General JWS JSON Serialization as follows. The
`payload` member is omitted according to RFC 7515 Appendix F; the verifier
reconstructs it from the canonical signing view. Ordinary JWS base64url payload
encoding is used, so the RFC 7797 `b64` extension MUST NOT be present.

The decoded protected header for a runtime receipt has this form:

```json
{
  "alg": "ES256",
  "kid": "runtime-receipt-key-2026-01",
  "typ": "asp-receipt+jws"
}
```

The following envelope is schematic; angle-bracket strings mark values that a
producer replaces with valid base64url JWS values.

```json
{
  "receipt_signatures": {
    "signatures": [
      {
        "protected": "<base64url-protected-header>",
        "signature": "<base64url-es256-signature>"
      }
    ]
  }
}
```

The `receipt_signatures` object MUST contain exactly the non-empty `signatures`
array; `payload` and every other member are forbidden in the transported
envelope. Each signature object MUST contain exactly `protected` and
`signature`; a JWS `header` member is forbidden. The
decoded protected header MUST contain exactly three unique members: `alg`,
`kid`, and `typ`. `typ` MUST be `asp-receipt+jws`; this is an ASP-private type
string pending any media-type registration and MUST be compared exactly.
Duplicate header members, `alg: none`, inline `jwk`, and any `jku`, `x5u`, or
`x5c` key location MUST be rejected.

Implementations of this profile MUST support `ES256` and MUST enforce an
explicit algorithm allow-list. An ES256 JWK MUST use `kty: "EC"` and
`crv: "P-256"`; when present, `alg` MUST be `ES256`, `use` MUST be `sig`, and
`key_ops` MUST permit `verify`. The JWS signature decodes to the 64-octet `R ||
S` form defined by RFC 7518, not an ASN.1 DER signature. ES256 signers SHOULD
derive the nonce deterministically according to RFC 6979. A future profile MAY
add a fully specified algorithm such as `Ed25519`; the polymorphic `EdDSA`
identifier MUST NOT be substituted.

`kid` is only a lookup hint. Application keys MUST be resolved through
issuer-bound authenticated metadata such as the manifest
`audit.receipt_signing.jwks_uri`; runtime keys MUST be resolved through the
runtime identity or key registration bound to the grant. A verifier MUST ensure
that the resolved key is authorized for the claimed signer and receipt role.
For a required signer, the JWS `kid` MUST select an entry in the hashed grant's
`audit.receipt_signing.signer_keys` whose `role` matches the receipt producer,
and the resolved public JWK's RFC 7638 SHA-256 thumbprint MUST match
`jwk_thumbprint`. A `kid` match without the role and pinned thumbprint is
insufficient.

An application advertising this profile MUST include `asp-jws-detached` in
`audit.receipt_signing.profiles_supported`, `ES256` in
`algorithms_supported`, and an issuer-bound HTTPS `jwks_uri`. A runtime signing
receipt evidence MUST register or attest its verification key through the
authenticated runtime relationship before a grant can require the `runtime`
signer role. A receipt-supplied URL or inline key is never sufficient trust.
Signers MUST retain or make their historical public keys available for at least
the applicable receipt-retention period. Key rotation does not rewrite an old
grant's pinned thumbprints; requiring a new key for future receipts requires a
new grant hash or explicit grant renewal. Within one issuer and signer role, a
`kid` MUST NOT be rebound to different key material. A compromise or revocation can make
historical evidence indeterminate according to verifier policy because this
profile does not provide an independent trusted timestamp.

The manifest advertises supported algorithms and key metadata. A grant MAY
make signatures mandatory through an `audit.receipt_signing` object containing
`profile: "asp-jws-detached"` and `required_signers`, whose values are
`runtime` and/or `application`. A listed role MUST sign the receipts it
produces; listing both roles requires a signed runtime receipt and a signed
application receipt, not two signatures on every receipt. Additional
co-signatures over the same detached payload remain possible through General
JWS. The requirement MUST include at least one pinned `signer_keys` entry for
each required role. Because the requirement and key pins are inside the hashed
grant rather than the removable signature envelope, they cannot be stripped
without changing `grant_hash`. If the grant has no such requirement, an
unsigned receipt remains conforming hash-linked audit material but MUST NOT be
represented as authenticated portable evidence.

A verifier MUST validate receipt structure and linked hashes first, reconstruct
the canonical detached payload, enforce protected-header and key policy, verify
the signature required for that receipt's producer role, and then validate the
parent chain to a trusted anchor. A present but invalid, unknown, or
unverifiable signature MUST NOT be downgraded to an unsigned receipt. Missing
or invalid required signatures make the receipt invalid as evidence; they do
not retroactively authorize or undo the underlying application action.

## Revocation Semantics

The protocol MUST define what happens when authority changes.

Revocation MUST be possible from both sides. The application-managed and
runtime-managed user paths are defined below and converge on the same
authoritative grant transition.

### Active Grant Management

A Grant-Enforcing Application MUST publish an HTTPS
`revocation.grant_management_url` in its manifest. The URL identifies the
application's human-facing active-grant management page, not the RFC 7009
runtime revocation endpoint and not an authority-bearing capability URL. Its
origin MUST match the manifest issuer origin. The published URL MUST be a
generic issuer-wide entry point shared by all users and grants. It MUST NOT
encode a grant id, token, user id, or other user- or grant-specific sensitive
value in its path, query, fragment, user information, host, or any other URL
component. Selection of a user or grant happens only after authentication from
server-side state, not through the manifest URL.

The application management page is the authoritative user view of current
grant state. It MUST authenticate the resource owner through the application's
ordinary user-authentication mechanism, derive the subject from that session,
and list only grants belonging to that subject. It MUST NOT accept a caller-
supplied subject selector, treat an Agent Grant Credential as user
authentication, or let a runtime or agent enumerate another user's grants.
Responses containing grant details MUST use `Cache-Control: no-store` and
`Referrer-Policy: no-referrer`.

For each active grant, the page MUST make these semantics visible and
inspectable:

- application and issuer, grant id and hash, pinned surface version and hash,
  and authoritative active or expiry state;
- runtime id, agent id, passport hash, and available verified identity labels;
- exact actions, scopes, locations, resource filters, expiration, budgets, and
  approval caveats;
- maximum effects, execution stages, and recovery limitations;
- effective data-exposure classes, redaction, and retention obligations;
- credential profile and receipt requirements; and
- whether revocation cascades to derived grants and the known number of
  affected descendants.

The summary MUST be derived from the stored authoritative Grant Object and the
exact pinned manifest snapshot that the grant references. It MUST NOT silently
reinterpret an old grant using the current manifest. If the pinned snapshot or
some historical display metadata is unavailable, the page MUST mark those
details unavailable, preserve the stored machine identifiers and hashes, and
still allow immediate revocation. Missing display metadata never makes a grant
look less privileged.

The page MUST NOT expose Grant Credentials, refresh tokens, cookies, raw
credential-binding material, receipt-signing private material, application
resource content, or passport data beyond what the user needs to identify the
delegate. Every active entry MUST provide a direct inspect-and-revoke path; a
user MUST NOT need the runtime, agent, or an active Grant Credential to use it.

An Application Runtime MUST also provide a local view of the grants and
credentials it stores, including their last known state and the trusted
`grant_management_url`. The application remains authoritative. If the local
view and an authenticated application view or introspection result disagree,
the runtime MUST stop new use, mark its state uncertain or inactive, and
resynchronize rather than treating cached `active` state as authority.

### User Revocation Intent and Confirmation

Before accepting a user-facing revocation, the application MUST show the
current grant using the common grant- and manifest-derived semantics listed in
Active Grant Management. It does not need runtime-local assertions from the
Consent Preview Contract and MUST NOT represent the old preview as portable
consent evidence. The application MUST additionally explain:

- that new actions will stop under this grant and its derived grants;
- which known child grants, sessions, execution tokens, and reservations are
  affected by the cascade;
- that queued or in-flight actions which have not passed the final atomic
  grant-state check will be rejected, while effects irreversibly committed
  before revocation remain authoritative and receiptable;
- that already committed effects are not undone and require separately
  authorized compensation or revert when available; and
- which `delete_on_grant_end` exposure obligations become effective, without
  claiming deletion of application source data or model unlearning.

The confirmation MUST be bound server-side to the exact `grant_id` and
`grant_hash` displayed to the user. That binding prevents target substitution;
it is not a fail-open precondition when authority changes concurrently. On
confirmation, the application MUST atomically freeze new use of the displayed
grant and every derived, renewed, exchanged, or superseding grant that preserves
its delegation lineage, then apply the Semantic Grant Revocation Transition.
New lineage members discovered during that transition are included in the
cascade. The application MUST show updated impact after authority has stopped,
but MUST NOT keep the lineage active while waiting for another confirmation.
An unrelated grant with a different lineage is never silently included and
requires its own user action. The user cannot disable the required cascade or
select only one credential of the semantic grant.

The management action uses the ordinary authenticated user session, not an
Agent Grant Credential. Implementations MUST apply their normal protections
against CSRF, clickjacking, session fixation, and confused-account actions, and
SHOULD require recent or step-up user authentication when local risk policy
warrants it. A missing grant and a grant belonging to another subject MUST
produce the same non-enumerating user-visible result.

User-facing revocation invokes the transport-neutral Semantic Grant Revocation
Transition; it is not a second authority mechanism.
Repeating an already confirmed request for the same grant state is idempotent
and MUST NOT repeat cascade side effects or emit duplicate control events.

### Revocation Timing and Concurrency

Revocation is logically immediate: before the application presents success to
the user, authoritative grant state MUST already be inactive and every
application enforcement point MUST reject a newly linearized action under the
grant. The application records an `effective_at` instant for that transition
and a `confirmed_at` instant for the user-visible success;
`confirmed_at` MUST NOT precede `effective_at`.

For a state-changing action, the effect linearization point is the final
authoritative grant-state check performed atomically with the first irreversible
application mutation or external-effect dispatch. Queued or in-flight work that
has not crossed that point before `effective_at` MUST be cancelled or fail as
`grant_revoked`. Work that crossed it before `effective_at` MAY finish only the
consequences already irreversibly committed at that point and MUST receipt its
actual outcome; it MUST NOT initiate another effect afterward without a new
current grant check. An implementation that cannot fence its effect dispatch
against revocation MUST NOT confirm success until the fence is established.
Cached introspection, an in-flight session, or an outstanding execution token
or reservation cannot move this boundary.

After success, the authenticated management page MUST provide read-your-writes
behavior: the grant MUST no longer appear active, and its detail view MUST show
the authoritative revoked state and `effective_at`. Event delivery, runtime
notification, session cleanup, credential deletion, and exposure-retention
cleanup MAY finish asynchronously, but none is the enforcement transition or a
precondition for success confirmation.

If the application cannot confirm the authoritative transition, it MUST show
revocation as unconfirmed and MUST NOT claim success. A runtime that initiates
revocation locally MUST stop new actions as soon as the user confirms intent;
on timeout or a binding-specific unavailable response it keeps the credential
frozen, labels confirmation as unknown, and retries or resynchronizes according
to the selected authenticated revocation binding. For OAuth, HTTP 503 and
`Retry-After` provide that signal. `pending` or `confirmation_unknown` are local
presentation states, not active-grant authority states.

This specification intentionally defines no universal wall-clock UI deadline.
Deployment latency is an operational SLO; the interoperable security invariant
is that application-side invalidation precedes success confirmation and later
authorization decisions observe it. Delivery of `grant.revoked` is notification,
not user confirmation, and loss of the event never reactivates a grant.

### Semantic Grant Revocation Transition

Every issuance and transport binding uses one transport-neutral semantic
transition. For a located active grant, the application MUST atomically mark the
grant inactive, reject every credential derived from it, invalidate refresh
tokens and proof-bound sessions, invalidate outstanding execution tokens and
reservations, and cascade revocation to child, exchanged, renewed, or
superseding grants whose authority preserves its delegation lineage. The
transition establishes `effective_at` and the concurrency fence defined above.

The transition is idempotent. Reapplying it to an inactive grant MUST NOT emit
duplicate control events, repeat cleanup side effects, or change the original
effective instant. It does not erase receipts or undo committed effects.
Transport profiles define how a runtime or user authenticates a request and how
success is represented; they MUST NOT weaken this inactive state, cascade, or
timing boundary. A non-OAuth issuance model claiming Grant-Enforcing
conformance MUST define an authenticated revocation binding that invokes this
same transition.

### OAuth Grant Revocation Profile

The manifest `agent_api.grant_revocation_url` MAY identify the same endpoint as
`auth.revocation_url`. When it does, a runtime requests revocation using RFC
7009: an authenticated form-encoded `POST` containing the Grant Credential in
the required `token` parameter and, optionally, an `access_token`
`token_type_hint`.

The endpoint MUST authenticate the runtime client and, for a credential it can
locate, verify that the credential was issued to that client. A successful
request and a request containing an unknown or already invalid credential both
return HTTP 200 with no response body, as required by RFC 7009. The runtime MUST
stop using the credential after that response. An HTTP 503 response means
revocation is not confirmed; the runtime MUST continue treating the credential
as sensitive, MUST NOT initiate new actions with it, and SHOULD retry according
to `Retry-After`.

For the Agent Grant profile, a successful request for a located credential MUST
invoke the Semantic Grant Revocation Transition for the semantic Agent Grant,
not only that token. A user-facing request invokes the same transition through
Active Grant Management and its confirmation and timing requirements.

When an active grant changes to revoked and the manifest declares an event
subscription endpoint, the application MUST emit a `grant.revoked` control event
with this minimum envelope:

```json
{
  "id": "event_01J2ABCDEF",
  "type": "grant.revoked",
  "occurred_at": "2026-06-25T18:30:00Z",
  "issuer": "https://code.example.com",
  "audience": "application_runtime_456",
  "payload": {
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "app_id": "code.example.com",
    "surface_hash": "sha-256:<base64url-digest>",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_hash": "sha256:...",
    "revoked_at": "2026-06-25T18:30:00Z",
    "effective_at": "2026-06-25T18:30:00Z",
    "reason": "user_revoked",
    "parent_grant_id": null,
    "cascade": true
  }
}
```

Required event fields are `id`, `type`, `occurred_at`, `issuer`, `audience`, and
`payload`. The payload MUST contain `grant_id`, `grant_hash`, `app_id`,
`surface_hash`, `runtime_id`, `agent_id`, `passport_hash`, `revoked_at`,
`effective_at`, `reason`, and
`cascade`; `parent_grant_id` is REQUIRED for a child grant and otherwise MAY be
null. Defined reason values are `user_revoked`, `application_revoked`,
`runtime_revoked`, `credential_compromise`, `parent_revoked`, `policy_changed`,
and `superseded`. A runtime MUST still enforce revocation when it receives an
unknown future reason value and MAY preserve that value as opaque audit data.

The event MUST be delivered over an application-authenticated event channel
bound to the manifest issuer and target runtime. The runtime MUST verify
`issuer`, `audience`, tuple binding, and channel authenticity before acting on
it. Delivery of this control event MUST use event-channel authority independent
of the revoked grant and MUST disclose no more grant data than the target
runtime already possessed. Under the Event Delivery Semantics profile it is
carried in `event.delivery` on the logically separate control subscription and
retains the same event and delivery identity across retries. A future signing
profile MAY additionally define an application signature for portable event
verification.

The runtime MUST compare event `grant_hash` and `surface_hash` with its retained
grant and manifest snapshot. If an authenticated event matches the stored
`grant_id` and delegate tuple but either hash differs, the runtime MUST fail
closed: mark the stored grant inactive, record `integrity_mismatch`, and
resynchronize authoritative state. It MUST NOT replace its stored hash
projections from the event, but it also MUST NOT ignore the revocation and keep
using the grant.

After accepting the event, the runtime MUST atomically mark the grant inactive,
discard cached active introspection state, stop new actions and credential use,
discard cached execution tokens and reservation state, cancel or downgrade
affected sessions according to app policy, cascade the state to locally tracked
child grants, and record a runtime receipt. Event processing is idempotent by
`issuer` and `id`, while transport retry is deduplicated by subscription and
delivery id. A duplicate event MUST NOT create duplicate receipts or repeat
external side effects. The runtime terminally acknowledges the control delivery
only after this fail-closed transition or authoritative resynchronization has
begun.

The event is notification, not the enforcement mechanism. The application MUST
reject the revoked grant immediately even if delivery is delayed or lost. A
runtime that misses the event learns the inactive state from introspection or a
rejected action. General event ordering, acknowledgement, replay cursor,
retention, and backpressure follow Event Delivery Semantics. Loss or expiry of
the control delivery never reactivates the grant.

### Grant Revoked

If a grant is revoked:

- runtime MUST stop initiating new actions under that grant
- app MUST reject new actions under that grant
- app MUST invalidate outstanding execution tokens and active reservations
  bound to that grant
- active sessions SHOULD be cancelled or downgraded to read-only according to
  app policy
- receipt generation SHOULD record the revocation event
- when the manifest declares an event subscription endpoint, the app MUST emit
  `grant.revoked` on the runtime control subscription according to the OAuth
  Grant Revocation Profile; closing the affected grant's non-control
  subscription MUST NOT close or suppress that control path

### Runtime Disconnected

If the runtime disconnects:

- when the app detects loss of the authenticated runtime channel, it MUST mark
  sessions bound to that channel as `interrupted` before accepting an action on
  a replacement channel
- app MUST NOT treat pending runtime approvals as approved
- app MUST apply each acquisition declaration's `disconnect_behavior`; a
  retained reservation remains bounded by its existing expiry and MUST NOT be
  consumed until the same tuple reconnects with a current Grant Credential and
  required proof
- app MAY accept `session.resume` only for an `interrupted` session when the
  same tuple reconnects with a current Grant Credential, matching surface, exact
  prior generation, and required proof; acceptance increments the generation
- a reconnect or local worker restart by itself MUST NOT reactivate a session
- unacknowledged event deliveries remain pending subject to retention and are
  retried with their original identities after the runtime restores the same
  subscription or requests replay from its last durable cursor

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
- app MUST invalidate execution tokens and reservations bound to an
  incompatible old action declaration
- grants bound to incompatible actions SHOULD require renewal

### User Session Expired

If the user's ordinary app session expires, app policy decides whether existing
agent grants continue. High-risk grants SHOULD expire with or before the user
session unless explicitly configured otherwise. If policy ends the grant or
session, the app MUST cancel the affected ASP sessions and fence new actions.
If policy allows them to continue, the ordinary login expiry does not change the
ASP session generation. A later user login MAY observe or cancel those sessions
only after authenticating the same application subject; it is not session-resume
authority for a runtime with a different tuple.

## Error Model

Agent Surface Protocol SHOULD define structured errors:

| Error | Meaning |
| --- | --- |
| `grant_missing` | No grant was supplied or found. |
| `grant_expired` | Grant has expired. |
| `grant_revoked` | Grant was revoked. |
| `grant_proof_invalid` | Grant credential or proof is missing, invalid, or not bound correctly. |
| `integrity_mismatch` | A supplied surface, grant, input, execution, precondition, effect, policy-decision, receipt, or parent hash does not match its complete hashing view or authoritative projection. |
| `scope_denied` | Grant scope does not permit the action. |
| `resource_denied` | Grant constraints do not permit the target resource. |
| `approval_required` | Required approval is absent. |
| `schema_invalid` | Input, output, preconditions, expected effects, actual effects, or mode-specific context does not match its declared or core schema. |
| `idempotency_conflict` | Idempotency key was reused with different input or execution context. |
| `execution_mode_invalid` | Request mode does not match the manifest-declared mode for the action. |
| `execution_transition_invalid` | Required companion stage or reciprocal action relationship is absent or invalid. |
| `execution_token_invalid` | Preview evidence is malformed or bound to different authority, input, state, or effects. |
| `execution_token_expired` | Preview evidence has expired and a new dry run is required. |
| `precondition_failed` | Declared state preconditions no longer hold. |
| `effect_mismatch` | Before mutation, expected effects exceed or differ from the declared or approved envelope. |
| `reservation_conflict` | An atomic reservation cannot be acquired because a target conflicts. |
| `reservation_expired` | The referenced reservation has expired. |
| `reservation_invalid` | Reservation is unknown, inactive, wrong-holder, wrong-surface, or incompatible with the commit. |
| `recovery_not_supported` | Target action or receipt does not support the requested compensation or revert. |
| `recovery_already_applied` | Confirmed target effects have already been fully recovered or the requested amount exceeds the unrecovered remainder. |
| `revert_conflict` | Prior state required for an exact revert is no longer available. |
| `outcome_unknown` | An external or partial effect may have occurred and blind retry is unsafe. |
| `risk_denied` | Local or app policy denied the risk class. |
| `data_exposure_violation` | An application-originated payload contains an undeclared data class or violates its redaction or retention contract. |
| `passport_invalid` | Agent Passport is missing, expired, revoked, or invalid. |
| `runtime_untrusted` | Runtime binding or attestation is not accepted. |
| `surface_incompatible` | Runtime does not support the surface version. |
| `proposal_required` | The app only supports proposal mode for this action or grant. |
| `session_invalid` | Session is unknown, non-active, stale-generation, or not bound to the complete tuple selected by the presented credential. |
| `session_transition_invalid` | Requested session transition, prior generation, target state, or idempotent replay binding is invalid. |
| `event_subscription_invalid` | Event subscription is unknown, inactive, or not bound to the authenticated tuple and current authority. |
| `event_delivery_conflict` | A delivery id was reused with different event content, stream, sequence, or cursor. |
| `event_cursor_invalid` | Replay cursor is malformed, tampered, or bound to another subscription, tuple, projection, or surface. |
| `event_cursor_expired` | Replay position is no longer available under the effective retention window and requires explicit gap recovery. |
| `action_unknown` | Action id is not part of the surface version the grant was issued against. |
| `limit_exceeded` | A grant budget caveat such as `max_actions` or `max_cost_usd` is exhausted. |
| `rate_limited` | The request was throttled independently of grant caveats. |

Errors SHOULD be returned in a structured envelope containing at least the
error code, a human-readable description, and a retryability indication.
Mapping error codes to HTTP status codes is left to a future draft.

Errors SHOULD be safe to show to users and precise enough for runtime policy
debugging.

`execution_mode_invalid`, `execution_transition_invalid`,
`execution_token_invalid`, `reservation_invalid`, `recovery_not_supported`,
`recovery_already_applied`, `session_transition_invalid`,
`event_delivery_conflict`, and `event_cursor_invalid` are not blindly retryable.
`event_cursor_expired` requires explicit gap recovery rather than substitution
of another cursor. An expired token or failed precondition requires a new read
or dry run and any required approval. A
reservation conflict MAY be retried after a safe `retry_after` interval without
disclosing the holder; an expired reservation requires a new acquisition.
After an effect was attempted, drift or uncertainty is represented by
`effect_outcome: "partially_applied"` or `"unknown"`, not a retryable
`effect_mismatch`. `outcome_unknown` MUST NOT be retried under a new
idempotency key until the application reconciles the authoritative outcome.

## Versioning and Compatibility

Surface manifests MUST include:

```json
{
  "protocol": "agent-surface/0.1",
  "surface_version": "2026-06-25",
  "surface_hash": "sha-256:<base64url-digest>",
  "compatibility": {
    "min_runtime": "application-runtime/0.1",
    "schema_dialect": "https://json-schema.org/draft/2020-12/schema"
  }
}
```

The `surface_version` value is an opaque identifier. Runtimes MUST compare
surface versions for exact equality; this draft defines no ordering between
surface versions.

Any change to the manifest hashing view MUST produce both a new `surface_hash`
and a new `surface_version`. Compatibility classification determines whether
an existing grant requires renewal; it does not permit two different manifest
objects to reuse one version. Applications SHOULD retain the exact old manifest
snapshot identified by every active grant. If that snapshot is unavailable,
the application MUST NOT interpret the action against the latest manifest and
MUST reject the action as `surface_incompatible`.

Compatibility rules:

- Removing an action is a breaking change for grants whose scopes cover that
  action.
- Tightening a schema can be a breaking change.
- Adding optional fields is non-breaking.
- Adding a new action is non-breaking.
- Changing risk labels to a higher risk class can require grant renewal.
- Changing an action's execution mode, operation id, required companion stage,
  effect envelope, precondition or effect schema, reservation policy, or
  recovery relationship is breaking for grants that authorize that action.
- Adding an optional companion action is non-breaking only when existing action
  semantics, approval, and effect envelopes remain unchanged.
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
application. Grants MUST bind user, app, runtime, agent, and passport hash.

### Raw Token Leakage

If an agent process receives raw app tokens, the runtime loses mediation control.
The preferred architecture is:

```text
Agent -> Runtime -> App
```

The runtime holds or obtains credentials and exposes only typed action results to
the agent. A raw credential release requires the explicit `credential.release`
capability and its corresponding approval and receipts; it is never implied by
a normal action grant. A released credential is restricted to a
non-Agent-Surface audience and MUST be rejected at Agent Surface endpoints.

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

### App-Embedded Runtime

The Terminology section allows a runtime to be embedded in an application.
That deployment collapses the two trust domains this protocol otherwise
separates: the component that is supposed to protect the user is operated by
the party the user is being protected from. An app-embedded runtime can
satisfy the wire protocol while voiding the "runtime protects the user"
guarantee — its policy checks, approvals, and runtime receipts are all
app-controlled.

When the runtime is app-operated, the user's protection reduces to app-side
consent and app receipts. Runtimes SHOULD disclose their operator during
consent, and enterprise policy MAY require user-controlled or third-party
runtimes for high-risk scopes.

### Malicious or Compromised Agent

Agents can hallucinate, loop, ignore instructions, leak data, or attempt
unauthorized actions.

Mitigations:

- no direct credentials in agent process
- no implicit credential or grant transfer to subagents, tools, or remote models
- schema validation
- risk-based approval
- static execution modes and preview-bound approval
- atomic precondition and reservation checks
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

- runtime derives grant and exposure details from the verified manifest rather
  than trusting application-authored labels alone
- runtime derives and confirms the complete local consent preview before
  sending the exact authorization request
- runtime presents grant details clearly
- local policy can deny high-risk surfaces
- user can inspect and revoke authoritative app grants without the runtime, and
  can freeze locally held credentials from the runtime view
- app manifest can be pinned or allowlisted
- enterprise policy can restrict issuers

### Stolen Grant Credential

A grant credential can be stolen from runtime storage, logs, memory, or network
traffic.

Mitigations:

- short-lived grants
- sender-constrained tokens
- DPoP or mTLS binding where practical
- credential-release default denial and explicit release receipts
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

Session task descriptions, resource payloads, and event payloads are
app-authored input to the agent and can carry injected instructions. The
runtime SHOULD present the session task to the user at session start or
consent time, and MUST NOT allow app-delivered content to widen grant scope,
weaken approval requirements, or alter local policy.

### Replay and Duplicate Actions

Idempotency keys, timestamps, nonce binding, and grant expiration reduce replay
risk. Side-effecting actions MUST be idempotent.

### Execution Mode Confusion, TOCTOU, and Reservation Abuse

A malicious agent can request a benign preview and then attempt to relabel it as
a commit. ASP prevents that escalation by assigning one static mode to each
action id and authorizing every companion action independently. Applications
MUST compare request mode with the pinned manifest and MUST NOT accept a client
request to select a stronger mode under the same action authority.

State can change between dry run, approval, reservation, and commit. An
execution token, preview id, precondition hash, or reservation id is evidence
about that flow, not authority and not a lock on all relevant state. The
application MUST revalidate current grant authority and check preconditions and
required reservations atomically with every app-controlled mutation. A stale
preview MUST fail closed instead of being silently refreshed after approval.

Effect under-classification can mislead both policy and the user. Applications
MUST publish the maximum effect envelope, reject a more severe predicted effect
before commit, and receipt partial or unknown external outcomes accurately.
Runtimes SHOULD compare expected effects with the declaration and SHOULD show
visibility, boundary, domain, and recovery limitations during approval.

Reservations can be used for starvation or as an oracle about other users.
Applications SHOULD use short TTLs, bounded renewals, per-grant and per-resource
quotas, atomic all-or-none acquisition, and non-identifying conflict responses.
Reservation identifiers MUST NOT confer authority, and revocation or tuple
invalidation MUST release their coordination effect.

Compensation and revert are new effects with their own failure modes. They MUST
use current independent authority and a new idempotent receipt chain. A target
receipt proves what was recorded; it does not authorize recovery. Neither mode
erases the original audit record, and compensation MUST NOT be described as
transactional rollback. Applications MUST track recovery against the target
receipt and effect rather than relying only on request idempotency; changing an
idempotency key MUST NOT produce a second refund, revert, or counter-effect for
an already recovered target.

### Surface Downgrade

A malicious network or compromised app path can present an older, less safe
surface version. Runtimes SHOULD pin issuer, app id, minimum accepted protocol
versions, and the verified version/hash tuple. Reusing one `surface_version`
with a different hash is an integrity failure. A self-declared `surface_hash`
does not authenticate the publisher because an attacker able to replace the
manifest can also recompute it; HTTPS, issuer binding, and local trust policy
remain mandatory.

`surface_hash` commits to schema URLs and other manifest values, not to the
transitive content later served by those URLs. A deployment that needs that
property must separately pin schema content hashes or use a future canonical
surface-bundle profile.

### Receipt Forgery

Receipts are hash-linked with the Canonical Object Hash Profile. This detects a
changed receipt or broken parent link relative to a retained chain head, but an
attacker that controls the whole unsigned history can replace and rehash the
chain. The optional Receipt Signing Profile authenticates a receipt only after
the verifier resolves an authorized signer key and validates the detached JWS;
`kid`, hash fields, and link fields are not trust anchors by themselves.

A verifier MUST reject duplicate JSON members, hash mismatches, parent cycles,
untrusted signature keys, disallowed algorithms, and a present invalid
signature. It MUST NOT treat an unsigned optional receipt as signed evidence or
downgrade an invalid signature to the unsigned MVP.

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

Data Exposure Contracts make application-to-agent disclosure inspectable but
do not prove that a publisher classified its data correctly. A runtime MUST
treat application-authored labels and descriptions as untrusted hints, preserve
the manifest identifier and classification in consent and policy decisions,
and MAY apply a stricter local classification. Unknown classes, missing
contracts, and inconsistent grant projections fail closed; they MUST NOT be
rendered as no exposure.

Redaction and retention obligations apply to prompts, model context, tool
arguments, caches, diagnostic captures, and agent-visible logs under runtime
control, not only to the primary response object. A runtime MUST NOT select an
agent or remote processing path that cannot enforce the effective contract.
Deletion of runtime-controlled plaintext does not prove model unlearning or
deletion by an undeclared external processor. Training use and remote-agent
defaults require separate policy profiles and are not implied by a retention
declaration in this draft.

Consent previews contain sensitive relationship metadata even when they omit
application payloads. Implementations SHOULD avoid placing rendered previews in
telemetry, browser history, or general-purpose logs. A local preview is not
portable consent evidence and SHOULD be retained only as long as local policy
needs it to complete and audit the authorization flow.

Active-grant management views contain the same relationship metadata plus
lifecycle state and usage-sensitive constraints. Applications and runtimes MUST
authenticate those views, avoid cross-subject enumeration, exclude credentials
and application payloads, and prevent caching or referrer leakage as defined by
Active Grant Management. Historical summaries SHOULD retain only the metadata
needed for user understanding, security audit, and applicable legal obligations.

Cross-system trace correlation can reveal relationships between otherwise
separate user actions, tenants, and services. `trace_id`, `span_id`, and
`tracestate` MUST NOT encode semantic identifiers or secrets. Components SHOULD
apply bounded retention, access control, and sampling independently of whether
the incoming trace flags request recording.

Preconditions, expected effects, resource keys, reservation conflicts, and
recovery targets can reveal sensitive application state. Schemas and approval
views SHOULD expose only what the user and runtime need to understand and
authorize the effect. Conflict responses MUST NOT identify another reservation
holder. Raw execution tokens are confidential runtime-held material and MUST
NOT enter receipts, logs, prompts, traces, or agent-visible context.

## Conformance

This draft defines conformance profiles instead of a single all-or-nothing
profile.

### Surface-Only Application

An application conforms to the Surface-Only profile when it:

- publishes an Agent Surface Manifest
- computes and publishes a valid `surface_hash` and changes
  `surface_version` whenever the manifest hashing view changes
- declares actions, resources, events, scopes, and schemas
- declares every referenced data class and complete exposure contracts for
  resources, actions, and events
- declares risk labels for actions
- declares one static execution mode and operation id per action
- declares maximum effects for state-changing actions and internally consistent
  companion-action, precondition, reservation, and recovery metadata
- declares endpoints or explicitly marks the surface as proposal/documentation
  only
- declares the `at_least_once` delivery contract whenever it publishes an event
  subscription endpoint
- provides `propose` actions or read-only resources

### Grant-Enforcing Application

An application conforms to the Grant-Enforcing profile when it:

- satisfies the Surface-Only profile
- issues, validates, or introspects Agent Grants
- validates grant state for every action
- validates credential binding to runtime, agent, and passport evidence
- creates or accepts an authoritative session record and validates its active
  state, complete tuple binding, and current generation for every action
- creates event subscriptions only as an attenuation of the current grant,
  rechecks authorization and exposure before delivery, and implements
  at-least-once retry, per-stream ordering, acknowledgement, replay, retention,
  explicit gaps, and bounded in-flight delivery
- validates `grant_hash` and binds the grant to the exact verified
  `surface_hash` snapshot
- validates static execution mode, companion authority, execution context and
  hash, preconditions, effect envelope, and any required reservation or
  recovery target before a state change
- issues and accepts only action allow-lists closed over required companion
  dependencies
- derives the complete effective data-exposure projection from the pinned
  manifest, returns it with the grant, and includes it in `grant_hash`
- applies declared redaction before application-originated data crosses the
  application boundary
- enforces cumulative per-target recovery limits independently of request
  idempotency keys
- treats `grant_id` as an identifier, not authority
- supports idempotency for `reserve`, `commit`, `compensate`, and `revert`
- invalidates preview evidence and reservations when their grant or surface
  binding becomes invalid
- does not accept `reserve`, `commit`, `compensate`, or `revert` unless it also
  satisfies the Receipt-Producing Application profile for that action
- supports grant revocation
- publishes the issuer-bound active-grant management page, authenticates the
  resource owner independently of Agent Grant Credentials, and confirms
  revocation only after authoritative invalidation

### OAuth Grant Lifecycle Application

An application conforms to the OAuth Grant Lifecycle Application profile when
it:

- satisfies the Grant-Enforcing Application profile
- advertises the Agent Grant authorization-details type and supported standard
  OAuth grant types
- validates and returns Agent Grant `authorization_details` according to the
  Rich Authorization Request Profile
- implements the OAuth Token Exchange Profile without privilege amplification
- returns the active and inactive Grant Introspection Profile contracts
- returns matching top-level and authorization-details hash projections
- binds RFC 7009 token revocation to the Semantic Grant Revocation Transition
  and emits the authenticated `grant.revoked` control event when an event
  endpoint is declared
- routes user-facing grant management through the same semantic revocation
  transition and preserves its immediate confirmation boundary
- presents authorization-server consent from the exact verified request,
  manifest semantics, and effective exposure projection

### Receipt-Producing Application

An application conforms to the Receipt-Producing profile when it:

- satisfies the Grant-Enforcing profile
- emits app receipts for required state-changing actions
- emits recomputable `receipt_hash`, `grant_hash`, `surface_hash`,
  `execution_hash`, effect hashes, and `policy_decision_hash` values
- includes the complete typed Policy Decision Object and requires its embedded
  hash to match the receipt's `policy_decision_hash`
- links an app receipt to the verified runtime receipt through
  `parent_receipt_hash` when runtime receipt evidence is required
- preserves trace id, session id and generation, action id, agent id, runtime
  id, and idempotency key while using a producer-specific span id
- preserves sanitized execution context across the runtime/app receipt edge,
  omits raw execution tokens, and uses `target_receipt_hash` rather than a
  parent edge for recovery causality
- records actual effects and distinguishes applied, partial, absent, and unknown
  outcomes
- records and retains receipt-bound revert evidence for effects advertised as
  reversible
- records session id and generation, trace id, and producer span id in the
  corresponding local action and receipt log entry
- records denied or failed high-risk actions

An application or runtime claims the `asp-jws-detached` Receipt Signing Profile
only when it supports the canonical detached payload, ES256 verification,
authenticated key resolution, grant-pinned signer roles and thumbprints,
historical public-key retention, and the no-downgrade behavior defined above.
It MUST emit every signature required for its producer role and reject required
or present signatures that do not verify.

### Proof-Bound Grant-Enforcing Application

An application conforms to the Proof-Bound Grant-Enforcing Application profile
when it:

- satisfies the Grant-Enforcing Application profile
- accepts Agent Surface actions only under the Proof-Bound Credential Profile
- verifies the per-request proof-of-possession or bound-channel authentication
- applies the method-specific DPoP, mTLS, or proof-bound session checks defined
  in Grant Verification
- rejects a bearer token, cookie, or reusable session identifier as sufficient
  authority by itself

### Application Runtime Profile

An application runtime conforms to this profile when it:

- discovers and validates Agent Surface Manifests
- recomputes `surface_hash` and pins the exact manifest snapshot
- verifies Agent Passport evidence before delegation
- obtains explicit user consent before storing a grant
- derives and confirms the local Consent Preview Contract projection before
  sending a grant issuance request, regenerates it after any material change,
  and rejects a returned grant that is not equal to or narrower than the exact
  confirmed request
- recomputes the grant's effective data-exposure projection, refuses missing or
  inconsistent contracts, and selects only runtime-agent paths that can enforce
  redaction and retention obligations
- mediates agent actions instead of exposing raw authority
- enforces the Session Authority and Lifecycle state machine, including
  complete tuple binding, generation changes on resume, and terminal-state
  rejection
- denies credential release unless an explicit `credential.release` capability
  and its constraints are satisfied
- preserves parent-runtime mediation for subagents, tools, adapters, remote
  models, and ungranted secondary runtimes
- treats a separately granted child runtime as its own controlling runtime and
  preserves parent linkage, attenuation, and cascade revocation
- implements RAR, Token Exchange, introspection, and revocation processing when
  using the OAuth Grant Lifecycle Application profile
- implements the Proof-Bound Credential Profile when the application requires
  the Proof-Bound Grant-Enforcing Application profile
- enforces local policy and approval rules
- validates action input against schemas before sending to the app
- validates request mode against the pinned declaration and computes input and
  execution hashes
- presents expected effects and recovery limitations, and binds approval to the
  exact input and preview evidence
- protects raw execution tokens, tracks reservations, and does not treat either
  as authority
- handles stale previews, reservation conflicts, and partial or unknown recovery
  outcomes without blind retry
- records local audit events and runtime receipts
- durably deduplicates event deliveries, acknowledges only after its processing
  decision is stable, preserves opaque cursors, applies explicit gap recovery,
  and enforces negotiated event backpressure
- computes and validates grant, execution, effect, policy-decision, and receipt
  hashes; propagates session id and generation and W3C-compatible trace context
- records session id and generation, trace id, and producer span id in local
  action and receipt logs
- stops actions when grants are revoked or expired
- provides a local grant view with the trusted application management link,
  freezes local use while revocation confirmation is unknown, and treats
  application state or introspection as authoritative over cached active state

### Agent Adapter

An adapter conforms to this draft when it:

- runs under runtime supervision
- does not require raw app credentials
- does not receive a Grant Credential or transfer one to downstream components
- requests app actions through runtime APIs
- emits typed events
- handles denials and approval waits
- preserves the manifest-declared action id and mode and handles preview,
  reservation, precondition, and recovery errors without selecting stronger
  authority
- preserves session and grant identifiers in audit context
- preserves valid trace ids and creates a new span id for each adapter operation

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
7. Assign one static execution mode to every action and split
   `comment.propose` from the `comment.create` commit action.
8. Declare effect envelopes and add preview/precondition schemas for selected
   commit actions.
9. Require idempotency keys and execution hashes for state-changing actions.
10. Add bounded reservation and recovery actions only where the application can
    enforce their lifecycle and semantics.
11. Produce local runtime receipts and app-visible receipts with execution and
    actual-effect evidence.
12. Integrate Agent Passport verification as an admission precondition.

## Example End-to-End Flow

```text
1. App publishes /.well-known/agent-surface.json with `surface_hash`.
2. Application runtime recomputes the hash and pins the exact surface.
3. User chooses "Connect my local agent".
4. Runtime verifies the selected agent's Agent Passport.
5. Runtime derives and the user confirms a local preview from the exact request,
   verified tuple, pinned manifest, effects, exposure contracts, and labeled
   local operator/processing-path assertions.
6. Runtime sends that exact Agent Grant `authorization_details` request.
7. The app authorization server independently shows consent:
   - app: code.example.com
   - runtime: application-runtime-456
   - agent: local-agent
   - passport: sha256:...
   - scopes: pull_request.read, pull_request.comment
   - actions: pull_request.get, comment.create
   - repository: example-org/example-repo
   - duration: 2 hours
   - commit effects: shared, internal communication
   - commit: requires approval
   - data classes: repository.content, user.identifier
   - retention: 2 hours, delete on grant end
8. User approves a subset or the complete request.
9. App issues or token-exchanges grant_123, its canonical `grant_hash`, and its
   bound Grant Credential.
10. Runtime verifies that the result is equal to or narrower than the confirmed
    request, recomputes its exposure projection, and stores the authoritative
    details and credential.
11. App starts a pull-request review session.
12. Agent reads typed PR context through runtime-mediated resources.
13. Agent proposes a review comment.
14. When declared, runtime requests a dry run and the app returns immutable
    preconditions, expected effects, and time-bounded preview evidence.
15. User or app approves the exact commit input and expected effects.
16. Runtime records its policy decision and receipt, then sends comment.create
    with trace context, parent receipt hash, idempotency key, execution context
    and hash, and Grant Credential.
17. App verifies current grant, surface, decision, input, execution, preview,
    and receipt hashes, rechecks preconditions, and commits the comment.
18. App returns actual effects and an app receipt. Runtime and app receipts form
    a verified parent-hash chain and MAY carry
    detached JWS signatures when required by the grant.
19. User opens the issuer-bound grant management page, inspects the exact
    grant_123 summary, and confirms revocation; the app marks the grant inactive
    before confirming success and invalidates outstanding preview evidence and
    reservations.
20. App emits authenticated `grant.revoked`; runtime stops affected work.
```

## Open Questions

- Does the first MVP use app-issued grants only, or also support
  runtime-held grants for compatibility with existing OAuth APIs?
- What is the minimal Agent Passport verification profile required before a
  runtime can request an Agent Grant?
- Does grant binding require runtime attestation, or is a registered runtime id
  enough for early implementations?
- Is `/.well-known/agent-surface.json` public, authenticated, or both
  depending on app tenancy?
- What is the minimal sender-constrained grant credential profile?
- How do users compare two agents with overlapping Agent Passport
  capabilities during grant consent?
- What happens to active sessions when an app changes surface versions?
- How is `max_cost_usd` metered when runtime-side inference cost and app-side
  action cost diverge, and which side is authoritative?
- How are runtime-side approvals proven to the application beyond an
  `approval_ref` identifier — signed approval objects, step-up verification,
  or app-rendered approval UI?

## References

- Model Context Protocol Specification:
  <https://modelcontextprotocol.io/specification/2025-06-18>
- Agent Client Protocol Overview:
  <https://agentclientprotocol.com/protocol/v1/overview>
- OAuth 2.0:
  <https://www.rfc-editor.org/rfc/rfc6749>
- OAuth 2.0 Proof Key for Code Exchange:
  <https://www.rfc-editor.org/rfc/rfc7636>
- OAuth 2.0 Token Revocation:
  <https://www.rfc-editor.org/rfc/rfc7009>
- OAuth 2.0 Token Introspection:
  <https://www.rfc-editor.org/rfc/rfc7662>
- OAuth 2.0 Token Exchange:
  <https://www.rfc-editor.org/rfc/rfc8693>
- OAuth 2.0 Resource Indicators:
  <https://www.rfc-editor.org/rfc/rfc8707>
- OAuth 2.0 Rich Authorization Requests:
  <https://www.rfc-editor.org/rfc/rfc9396>
- OAuth 2.0 Pushed Authorization Requests:
  <https://www.rfc-editor.org/rfc/rfc9126>
- Best Current Practice for OAuth 2.0 Security:
  <https://www.rfc-editor.org/rfc/rfc9700>
- OAuth 2.0 Mutual-TLS Client Authentication and Certificate-Bound Access
  Tokens:
  <https://www.rfc-editor.org/rfc/rfc8705>
- OAuth 2.0 Demonstrating Proof-of-Possession at the Application Layer (DPoP):
  <https://www.rfc-editor.org/rfc/rfc9449>
- The I-JSON Message Format:
  <https://www.rfc-editor.org/rfc/rfc7493>
- Base-N Encodings:
  <https://www.rfc-editor.org/rfc/rfc4648>
- Date and Time on the Internet: Timestamps:
  <https://www.rfc-editor.org/rfc/rfc3339>
- JSON Web Signature (JWS):
  <https://www.rfc-editor.org/rfc/rfc7515>
- JSON Web Key (JWK):
  <https://www.rfc-editor.org/rfc/rfc7517>
- JSON Web Algorithms (JWA):
  <https://www.rfc-editor.org/rfc/rfc7518>
- JSON Web Key (JWK) Thumbprint:
  <https://www.rfc-editor.org/rfc/rfc7638>
- Deterministic Usage of DSA and ECDSA:
  <https://www.rfc-editor.org/rfc/rfc6979>
- JSON Web Signature Unencoded Payload Option:
  <https://www.rfc-editor.org/rfc/rfc7797>
- JSON Canonicalization Scheme (JCS):
  <https://www.rfc-editor.org/rfc/rfc8785>
- Verified erratum 7920 for JSON Canonicalization Scheme:
  <https://www.rfc-editor.org/errata/eid7920>
- JSON Web Token Best Current Practices:
  <https://www.rfc-editor.org/rfc/rfc8725>
- Fully Specified Algorithms for JOSE:
  <https://www.rfc-editor.org/rfc/rfc9864>
- Secure Hash Standard (SHS), FIPS 180-4:
  <https://csrc.nist.gov/pubs/fips/180-4/upd1/final>
- W3C Trace Context:
  <https://www.w3.org/TR/trace-context/>
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
