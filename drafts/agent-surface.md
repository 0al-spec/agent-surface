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

<!-- BEGIN GENERATED RFC TOC -->
<details>
<summary>Table of Contents</summary>

- [Authors' Contact Information](#authors-contact-information)
- [Status of this Memo](#status-of-this-memo)
- [Copyright Notice and Licensing](#copyright-notice-and-licensing)
- [Abstract](#abstract)
- [Normative and Informative Sections](#normative-and-informative-sections)
- [Motivation](#motivation)
- [Goals](#goals)
- [Non-Goals](#non-goals)
- [Conventions](#conventions)
- [Terminology](#terminology)
- [Design Principles](#design-principles)
- [Relationship to Existing Protocols](#relationship-to-existing-protocols)
- [Conceptual Architecture](#conceptual-architecture)
- [Protocol Layers](#protocol-layers)
- [Canonical Integrity and Provenance](#canonical-integrity-and-provenance)
- [Agent Surface Manifest](#agent-surface-manifest-1)
- [Action Execution Model](#action-execution-model)
- [Risk Taxonomy](#risk-taxonomy)
- [Effect Model](#effect-model)
- [Approval Semantics](#approval-semantics)
- [Idempotency](#idempotency)
- [Minimal Agent Passport Grant-Issuance Profile](#minimal-agent-passport-grant-issuance-profile)
- [Runtime Identity Profile](#runtime-identity-profile)
- [Remote Processing Privacy Profile](#remote-processing-privacy-profile)
- [Agent Training Use Policy Profile](#agent-training-use-policy-profile)
- [Runtime Attestation Optional Profile](#runtime-attestation-optional-profile)
- [Agent Grant](#agent-grant-1)
- [Capability Matching](#capability-matching)
- [Observability Context](#observability-context)
- [Sessions and Actions](#sessions-and-actions)
- [Receipts](#receipts)
- [Portable Replay Bundle Profile](#portable-replay-bundle-profile)
- [Revocation Semantics](#revocation-semantics)
- [Error Model](#error-model)
- [Versioning and Compatibility](#versioning-and-compatibility)
- [Security Considerations](#security-considerations)
- [Privacy Considerations](#privacy-considerations)
- [Conformance](#conformance)
- [Application MVP Mapping](#application-mvp-mapping)
- [Example End-to-End Flow](#example-end-to-end-flow)
- [Open Questions](#open-questions)
- [References](#references)
- [Appendix A: Why This Is Not Just an API Token](#appendix-a-why-this-is-not-just-an-api-token)
- [Appendix B: Why This Is Not Just Computer Use](#appendix-b-why-this-is-not-just-computer-use)
- [Appendix C: Product Positioning](#appendix-c-product-positioning)

</details>
<!-- END GENERATED RFC TOC -->

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
- Approval Receipt Profile
- Idempotency
- Minimal Agent Passport Grant-Issuance Profile
- Runtime Identity Profile
- Remote Processing Privacy Profile
- Agent Training Use Policy Profile
- Runtime Attestation Optional Profile
- Agent Grant
- Sessions and Actions
- Receipts
- Portable Replay Bundle Profile
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
- Do not require an application to expose, enumerate, or mirror every public,
  private, or internal API operation, UI command, RPC method, or integration
  endpoint through an Agent Surface.
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

The surface is a deliberately curated affordance layer, not merely an API
endpoint list and not a mirror or completeness claim for the application's
public, private, or internal APIs. It is an application contract for safe
delegated agent behavior. Its inventory is authoritative only for the exact ASP
surface snapshot: omission means that an operation has no ASP discovery, Grant,
or action authority under that snapshot, not that the underlying application
operation does not exist.

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

The system that hosts, launches, supervises, or mediates the user's selected
agent. A runtime can be local, user-controlled, enterprise-managed,
application-operated, or supplied by a remote service. A runtime can be embedded
in an application, delivered as a companion bridge or daemon, provided by an
operating system service, implemented by a browser extension, or hosted in a
separate execution environment. Deployment location, operator, authentication
method, management posture, and assurance are distinct properties; none is
implied merely by calling a component a Runtime.

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

The presence or syntactic validity of those fields is not cryptographic
verification. A consuming profile must separately define exact signed bytes,
algorithm policy, authenticated key resolution, issuer trust, lifecycle status,
and any executable-integrity binding it claims.

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
approval requirements, write actions, tool calls, model tokens, runtime time,
parallel sessions, or partitioned application and runtime spend.

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

### Impact Simulation Result

A bounded, runtime-local, machine-readable supplement to one Consent Preview
that gives one example for every requested action plus a deterministic bounded
set of unrequested actions, classified as covered, not covered, or not
currently decidable under the exact proposed semantic Grant request and current
runtime evaluation inputs. It is not an execution preview, policy decision,
Grant, credential, consent record, approval, receipt, or prediction that an
action will succeed.

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
- `budget.warning`
- `budget.exceeded`
- `session.paused_budget`
- `grant.revoked`

ASP application events use the CloudEvents 1.0.2 information model and JSON
structured format with ASP extension attributes for scope, control, integrity,
and delivery context. The event envelope itself carries no authority.

### Receipt

Portable evidence that an action or approval decision occurred, including the
grant, session, agent, passport hash, input and execution hashes, producer
decision, timestamp, and applicable action effects or result.

Receipts can be stored locally, in the application, in enterprise audit systems,
or in a provenance graph.

This proposal distinguishes:

- **Runtime Receipt**: evidence observed and produced by the runtime, such as
  agent intent, policy evaluation, and local user approval.
- **App Receipt**: evidence produced by the application that a mutation was
  actually performed or denied under a grant.
- **Approval Receipt**: immutable evidence that a runtime-side or
  application-side approval interaction approved or denied one exact action
  invocation. It is a causal prerequisite record, not action authority or proof
  that an effect occurred.

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

This recommendation does not itself prohibit a state-changing action. An
application that claims a surface-wide prohibition MUST declare
`surface_mode: "proposal_only"` and satisfy the fail-closed Proposal-Only
Surface Mode contract. A runtime MUST NOT infer that contract merely because a
surface currently happens to expose only proposal actions.

### Every Write Is Idempotent

Any action that changes domain or coordination state MUST support idempotency.
This includes `reserve`, `commit`, `compensate`, and `revert`. Retries, network
reconnects, agent loops, and duplicate messages MUST NOT create ten
reservations, comments, branches, refund requests, compensations, or approvals.
The pinned action declaration defines one normalized wire input for approval,
hashing, duplicate lookup, and receipts; components MUST NOT deduplicate against
an application-local representation that those other checks did not bind.

Idempotency prevents one logical request from repeating an application effect;
it is not a behavioral loop detector. A runtime MUST still count exact cached
replays, transport retries, and semantically repeated actions using new keys in
the independent runaway guards defined below. Those guard fingerprints are
safety signals only and MUST NOT cause an application to merge distinct
idempotency records or accept an otherwise unauthorized request.

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

Likewise, discovering a tool or resource through MCP does not add it to an
Agent Surface. The application must deliberately publish the corresponding ASP
resource, action, or event with complete ASP semantics before it can participate
in capability matching, consent, Grant issuance, or ASP invocation.

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
- Does the exact Passport artifact hash match the verified artifact?
- Has an independent integrity profile bound that artifact to the executable
  agent, or is the evidence document-only?

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
- surface mode
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
- budget state endpoints
- session control endpoints
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
- `budget.query`
- `budget.state`
- `session.start`
- `session.event`
- `session.pause`
- `session.cancel`
- `session.resume`
- `session.state`
- `approval.required`
- `approval.resolved`
- `elicitation.required`
- `elicitation.resolved`

This layer is transport and session orchestration. It is not intended to absorb
all Agent Surface semantics.

### Human Elicitation Events Profile

The optional Human Elicitation Events Profile identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/human-elicitation/v1
```

It defines a transport-neutral interaction contract for asking an authenticated
user to clarify a value, choose from a closed option set, edit a candidate,
review a redline, or complete step-up authentication. A conforming deployment
MAY carry the two typed messages below over the Runtime Bridge Protocol, an
authenticated AHP channel that independently selects this profile, or another
authenticated channel, but the carrier does not change their semantics. The
ASP-over-AHP Binding Profile does not implicitly select this profile.

The application advertises support in
`compatibility.human_elicitation_profiles` and publishes
`compatibility.human_elicitation_replay_retention_seconds`. Before either
message is accepted, the authenticated application and runtime channel MUST
select the exact profile identifier or select no Human Elicitation profile.
The selection is bound to the authenticated application and runtime
identifiers, `surface_hash`, and channel or session context. A participant MUST
NOT infer selection from a rendered prompt, AHP negotiation, schema
availability, prior session, or peer implementation claim. The `profile` in
both messages MUST equal the selected identifier. A surface change invalidates
the selection and every pending interaction; selection on a non-Runtime-Bridge
carrier MUST provide the same authenticated binding and fail-closed behavior.

#### Authority Boundary and Participants

An elicitation records bounded human input. It is not an Agent Grant, consent,
approval, Policy Decision, Approval Receipt, Action Request, execution token,
reservation, effect, action receipt, or proof that an effect occurred. A
successful answer can become input to a later policy or action decision only
after the component responsible for that decision independently validates its
current authority and bindings.

The `requester` is the application or runtime asking for input. The `presenter`
is the application or runtime that owns the authenticated user interaction.
The receiver derives both protocol roles and their identifiers from the
authenticated channel and local configuration. A role field inside a message
cannot authenticate its sender, presenter, or user.

An agent MAY propose a question or candidate through its typed adapter API. It
MUST NOT originate `elicitation.resolved`, claim that a person answered, handle
an authentication secret, select its own answer as a user answer, or turn an
elicitation result into authority. The Runtime Mediator exposes to the agent
only the minimized, type-specific answer that is needed for the current task.

The application remains authoritative for its ASP session record, Grant,
surface, app-side policy, action admission, and effects. The runtime remains
authoritative for its local user interaction, local policy, and agent-facing
projection. An AHP representation or another UI carrier can present the
interaction, but a rendered control, page revision, navigation state, or
connection identity cannot substitute for any elicitation or ASP binding.

#### Common Request Object

An elicitation starts with `elicitation.required`. Its normalized JSON shape is
closed:

```json
{
  "type": "elicitation.required",
  "profile": "https://github.com/0al-spec/agent-surface/profiles/human-elicitation/v1",
  "elicitation_id": "elicit_01J2ABCDEF",
  "revision": 1,
  "requester": {
    "type": "application",
    "id": "code.example.com"
  },
  "presenter": {
    "type": "runtime",
    "id": "application-runtime-456"
  },
  "kind": "choose",
  "session_id": "sess_456",
  "session_generation": 1,
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<grant-digest>",
  "surface_hash": "sha-256:<surface-digest>",
  "context": {
    "action_id": "comment.propose",
    "mode": "propose",
    "input_hash": "sha-256:<input-digest>",
    "proposal_id": "proposal_42"
  },
  "context_hash": "sha-256:<context-digest>",
  "prompt": {
    "title": "Choose a review outcome",
    "detail": "Select the outcome to place in the draft."
  },
  "request": {
    "question_id": "review-outcome",
    "options": [
      {
        "option_id": "comment",
        "label": "Comment",
        "detail": "Submit non-blocking feedback."
      },
      {
        "option_id": "request_changes",
        "label": "Request changes",
        "detail": "Mark the draft as blocking."
      }
    ],
    "min_selected": 1,
    "max_selected": 1
  },
  "expires_at": "2026-06-25T16:35:00Z",
  "request_hash": "sha-256:<request-digest>"
}
```

`type`, `profile`, `elicitation_id`, `revision`, `requester`, `presenter`,
`kind`, the complete session and Grant binding, `surface_hash`, `context`,
`context_hash`, `prompt`, `request`, `expires_at`, and `request_hash` are
REQUIRED. Unknown members are forbidden at every profile-defined level.

`elicitation_id` is a collision-resistant identifier that the requester MUST
NOT reuse within the authenticated requester and presenter pair. `revision` is
a positive integer. The requester increments it by exactly one when replacing
an unanswered request. `requester.type` and
`presenter.type` are `application` or `runtime`, MUST differ, and each `id` is a
non-empty authenticated component identifier. `session_generation` is the
current positive generation of the named active ASP session. The Grant,
surface, and session tuple MUST equal the presenter's current verified state.

`context` is a closed binding object containing the fields that apply to the
interaction. It MUST contain `action_id`, `mode`, and `input_hash` when an
answer can affect an action input. It additionally contains every available
`proposal_id`, `preview_id`, `expected_effects_hash`, `reservation_id`,
`execution_hash`, `policy_decision_hash`, and `approval_id` that the
presentation depends on. Omission means that value is not part of the
interaction; it never means that a receiver can infer or add it. `context_hash`
uses the Canonical Object Hash Profile over the complete `context` object.

`prompt` contains exactly `title` and `detail`, both non-empty user-displayable
strings. They MUST be safe for the presenter to disclose under the effective
Data Exposure Contract and MUST NOT contain a credential, authentication
secret, hidden policy rule, raw execution token, or data not needed for the
decision. `expires_at` is an RFC 3339 UTC timestamp with the `Z` suffix.
`request_hash` uses the Canonical Object Hash Profile over the complete request
object excluding `request_hash`.

When a requester copies Risk Explanation UI Hint text into `prompt`, that copy
remains requester-authored prompt text. The presenter MUST NOT relabel the copy
as manifest-derived publisher text. It MAY independently resolve and present a
valid localization from the exact current manifest snapshot identified by the
bound `action_id` in `context` and the retained `surface_hash`; that presentation
uses the feature's ordinary publisher label and keeps canonical risk and effect
semantics visible independently. The prompt copy is not a risk mapping,
approval, or instruction. A changed hint changes the surface hash and
invalidates the pending elicitation rather than updating its prompt in place.

#### Elicitation Kinds

`kind` is exactly one of `clarify`, `choose`, `edit`, `redline`, or `step_up`.
The request and answered response use the same kind:

| Kind | Closed request semantics | Answer semantics |
| --- | --- | --- |
| `clarify` | `question_id`, a self-contained `response_schema`, its `response_schema_hash`, and `max_bytes` | One JSON value that validates against the exact schema and byte ceiling. |
| `choose` | `question_id`, ordered `options`, `min_selected`, and `max_selected` | An ordered array of unique `option_id` values from that exact revision. Labels and list positions are not identifiers. |
| `edit` | `base`, `base_hash`, `input_schema_hash`, and ordered unique `editable_paths` using RFC 6901 JSON Pointers | A complete candidate value; the receiver validates allowed paths, schema, normalization, and the recomputed candidate hash. |
| `redline` | `base_hash`, `media_type`, `patch_schema`, `patch_schema_hash`, and optional ordered unique `editable_paths` | A patch in the declared media type plus the repeated base hash and recomputed candidate hash. The receiver applies it to the exact base before validation. |
| `step_up` | `transaction_text`, ordered unique `required_assurance` URI values, and `max_age_seconds` | An opaque verifier result reference, achieved assurance set, authentication time, expiry, and verifier identity; never an authentication factor or secret. |

For `clarify`, `max_bytes` is the length in octets of the RFC 8785
serialization of the `answer` value encoded as UTF-8. It does not count a
transport envelope, whitespace from a non-canonical serialization, or the
surrounding Human Elicitation response.

Each option contains exactly `option_id`, `label`, and `detail`. Option ids are
unique non-empty strings. `min_selected` and `max_selected` are safe
non-negative integers satisfying
`min_selected <= max_selected <= number of options`. An unanswered request
does not imply a default choice.

For `edit`, the presenter treats the request's `base` as display data, not as
current application state. The receiver rechecks `base_hash` and every editable
path against its authoritative candidate. For `redline`, v1 does not assign
semantics to a visual diff. The declared media type and patch schema define the
machine input; any rendered redline is explanatory only. A base mismatch is
not resolved by applying the patch to a newer document. The v1 redline media
type is `application/json-patch+json`; the receiver applies its ordered
`add`, `remove`, and `replace` operations to the exact base according to
RFC 6902. Other JSON Patch operations are unsupported in v1 and fail as
`elicitation_invalid`. An array token is either `0` or a non-zero ASCII decimal
integer without a leading zero. `remove` and `replace` require an existing
index strictly below the current array length. `add` permits an index no
greater than the current length or the special final token `-`; a signed,
negative, leading-zero, non-decimal, or out-of-range index is invalid. Each
operation is evaluated against the candidate produced by the preceding
operation.

`response_schema` and `patch_schema` use the manifest-selected Draft 2020-12
dialect, MUST be self-contained, and are hashed exactly as carried before they
are evaluated. Neither schema may contain a `$ref` or `$dynamicRef` whose
URI-reference is anything other than a fragment-only reference into that exact
schema object. A relative path, absolute URI, network location, or another
schema resource is non-local and MUST be rejected without dereferencing it.

For `step_up`, the presenter invokes an independently authenticated verifier.
Passwords, one-time codes, passkeys, private keys, biometric samples, recovery
codes, and equivalent factors MUST NOT appear in either profile message or in
agent-visible data. The verifier result MUST bind the application or runtime
audience, authenticated subject, `elicitation_id`, revision, `context_hash`,
achieved assurance, authentication time, and expiry. A result is usable only
when the receiving component independently obtains that exact verifier record,
its audience equals the authenticated requester, every other binding equals the
current interaction, the result status is verified,
the current policy-evaluation time is no later than its expiry, and the elapsed
time since `authenticated_at` is no greater than `max_age_seconds`. Resolution
time does not substitute for current evaluation time. Step-up proves an
authentication event to that verifier; it does not by itself approve an action
or widen a Grant.

#### Resolution Object

The presenter returns `elicitation.resolved` on the authenticated channel. Its
normalized JSON shape is also closed:

```json
{
  "type": "elicitation.resolved",
  "profile": "https://github.com/0al-spec/agent-surface/profiles/human-elicitation/v1",
  "elicitation_id": "elicit_01J2ABCDEF",
  "revision": 1,
  "kind": "choose",
  "disposition": "answered",
  "responder": {
    "type": "runtime",
    "id": "application-runtime-456"
  },
  "session_id": "sess_456",
  "session_generation": 1,
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<grant-digest>",
  "surface_hash": "sha-256:<surface-digest>",
  "context_hash": "sha-256:<context-digest>",
  "request_hash": "sha-256:<request-digest>",
  "response": {
    "option_ids": ["comment"]
  },
  "resolved_at": "2026-06-25T16:31:00Z",
  "response_hash": "sha-256:<response-digest>"
}
```

`type`, `profile`, `elicitation_id`, `revision`, `kind`, `disposition`,
`responder`, the complete session and Grant binding, `surface_hash`,
`context_hash`, `request_hash`, `resolved_at`, and `response_hash` are REQUIRED.
`request_hash` MUST equal the accepted request revision's hash.
`disposition` is `answered`, `declined`, `cancelled`, or `expired`. `response`
is REQUIRED exactly for `answered` and forbidden otherwise. `responder` MUST
equal the authenticated presenter from the request.

An answered response contains exactly:

- `answer` for `clarify`;
- `option_ids` for `choose`;
- `candidate` and `candidate_hash` for `edit`;
- `base_hash`, `patch`, and `candidate_hash` for `redline`;
- `result_ref`, `verifier`, `achieved_assurance`, `authenticated_at`, and
  `expires_at` for `step_up`.

`resolved_at`, `authenticated_at`, and the step-up `expires_at` are RFC 3339
UTC timestamps with the `Z` suffix. Before accepting a fresh response, the
receiver compares `resolved_at` with its own authoritative policy-evaluation
time: `resolved_at` MUST be no later than both that evaluation time and the
accepted request's `expires_at`. A future resolution is invalid even when its
timestamp precedes request expiry. The evaluation time is local authoritative
state and is never taken from either profile message. Exact retained terminal
replay returns the previously accepted immutable result; it does not create a
new resolution time. `response_hash` uses the Canonical Object Hash Profile
over the complete response object excluding `response_hash`.

#### Lifecycle, Replay, and Rebinding

The requester and presenter retain the following state per authenticated
participant pair and `elicitation_id`:

| Current state | Input | Next state | Required behavior |
| --- | --- | --- | --- |
| absent | valid revision `1` request | `pending` | Verify the complete tuple, context hash, kind contract, exposure, and expiry before presentation. |
| `pending` | exact request replay | `pending` | Return or retain the same presentation state without another user prompt or side effect. |
| `pending` | valid next revision | `pending` | Mark the prior revision `superseded`, replace the presentation, and accept no response to the prior revision. |
| `pending` | valid matching `answered` response | `resolved` | Persist the immutable response before acknowledging it; perform the kind-specific validation below. |
| `pending` | matching `declined`, `cancelled`, or `expired` response | same named terminal state | Persist the terminal disposition; create no candidate authority or action effect. |
| any non-terminal state | Grant, surface, session, context, authentication, or policy binding becomes invalid | `invalidated` | Suppress the prompt or response and require a new elicitation after authoritative state is re-established. |

`resolved`, `declined`, `cancelled`, `expired`, `superseded`, and `invalidated`
are terminal for that revision. An exact replay of a terminal response returns
the original immutable result while its terminal replay record is retained.
Both participants retain the request hash, response hash, terminal disposition,
and result reference for at least
`compatibility.human_elicitation_replay_retention_seconds` after terminal
acceptance. Terminal acceptance is the instant at which that participant
durably persists the validated terminal response; it is not the response's
self-asserted `resolved_at` or its transport delivery time. They MAY delete
response payload fields earlier when a stricter
privacy rule requires it, but MUST retain a non-sensitive tombstone sufficient
to reject reuse and MUST NOT report the original result after deleting the
fields needed to reproduce it. After the retention interval, a replay or
unknown reused id fails closed as stale `elicitation_invalid`; it never creates
a new prompt or result. Conflicting reuse of an accepted request or response
revision, a skipped revision, response-kind mismatch, stale or future session
generation, expired request, unlisted option, invalid schema answer, changed
redline base, unverified step-up result, or tuple mismatch fails as
`elicitation_invalid`. It MUST NOT advance session state, satisfy approval,
dispatch an action, release a credential, or create effect or receipt evidence.
Waiting for an answer pauses only the bound operation. It does not transition
the authoritative ASP session from `active` to `interrupted`; ordinary session
fencing and cancellation continue to use the Session Authority and Lifecycle
state machine.

Clarify and choose answers are typed data only. Edit and redline answers are
candidates only. Before any candidate can replace action input, the responsible
runtime and application independently validate the schema and editable paths,
apply the manifest-pinned normalization, recompute `input_hash` and
`execution_hash`, and re-evaluate policy. If the normalized input or another
bound context member changes, all prior preview evidence, reservations,
expected-effects evidence, policy decisions, and approvals that bind the old
value become unusable. A new preview, reservation, policy decision, or approval
is obtained when the ordinary action contract requires it.

A verified step-up result is an authentication input to the receiving
component's current policy evaluation. It cannot satisfy an approval mode
unless the component subsequently obtains the separately defined exact
approval. No Human Elicitation response is included in
`approval_receipt_hashes`; an Approval Receipt can refer only to the later
approval interaction it actually records.

#### Privacy and Failure Rules

The requester minimizes the prompt, base candidate, options, schema, and
context to the data needed for this interaction. The presenter applies the
effective redaction, recipient, processing-path, retention, and training-use
constraints before showing or storing that data. A response inherits the
strictest applicable retention bound from its request, Grant, and local policy.
Authentication factors and verifier-private evidence are never retained as
elicitation data.

Transport loss, UI dismissal, ordinary application-login expiry, or an AHP
navigation change does not imply `answered`, `declined`, `cancelled`, or
`expired`. After an ambiguous delivery the participants reconcile by
`elicitation_id`, revision, and complete hashes. They MUST NOT create a new
answer, approval, action idempotency key, or effect merely to discover whether
the prior resolution was accepted.

### ASP-over-AHP Binding Profile

The ASP-over-AHP Binding Profile identifier is
`https://github.com/0al-spec/agent-surface/profiles/asp-over-ahp/v1`. It defines
how a deployment can carry ASP participation through an AHP session while
keeping ASP authority and evidence semantics
unchanged. This draft does not define the base AHP protocol, media type, or
representation syntax. A deployment claiming this profile MUST identify the
base AHP version and serialization independently and MUST implement the closed
binding contract below without inferring omitted AHP semantics.

#### Scope and Authority Boundary

AHP owns its representation navigation, presentation revision, control
discovery, and user-interface state. Those values can tell a runtime what a
user can see or which transition can be requested next. They are not an Agent
Grant, Grant Credential, ASP session record, approval, Action Request, action
result, effect, receipt, revocation state, or proof that any of those objects
exists or remains current.

ASP continues to own:

- manifest and `surface_hash` semantics;
- Grant, credential, delegate, and lifecycle authority;
- the authoritative application session record and `session_generation`;
- action identifiers, modes, input and execution hashes, idempotency, approval,
  admission, effects, and recovery;
- receipt production, role attribution, integrity, and hash-chain semantics;
- event subscription, delivery, acknowledgement, replay, and exposure rules.

An `ahp_session_id`, representation URI, revision, control id, link relation,
form value, rendered approval state, or connection identity is correlation and
presentation state only. None can substitute for an ASP tuple member. The AHP
session id and ASP `session_id` remain separate namespaces and MUST be mapped
explicitly rather than copied or compared as interchangeable credentials.

The binding MUST NOT carry a Grant Credential, proof key, raw execution token,
private receipt material, or application credential in an AHP representation or
agent-visible control. A runtime can retain those values inside its ordinary ASP
security boundary and use them only when constructing the corresponding ASP
request on the authenticated ASP path.

#### Binding Negotiation and Record

Before interpreting an AHP representation as ASP-related, both peers MUST
explicitly select the exact profile identifier above on an authenticated AHP
channel. Profile selection is scoped to that authenticated channel and base AHP
session. Missing, unknown, downgraded, or conflicting selection is unbound AHP
content and MUST NOT be interpreted as ASP state. Reconnect performs a new
selection and revalidates current ASP state; it does not restore authority from
the earlier connection.

Each ASP-related representation or control carries one binding record. The base
AHP serialization MAY embed this JSON object or provide an exactly equivalent
typed projection, but the normalized members and meanings are closed:

```json
{
  "profile": "https://github.com/0al-spec/agent-surface/profiles/asp-over-ahp/v1",
  "ahp_session_id": "ahp_session_7",
  "representation_id": "review/42",
  "representation_revision": 7,
  "control_id": "submit-comment",
  "control_kind": "invoke",
  "asp": {
    "message_type": "action.request",
    "session_id": "sess_456",
    "session_generation": 1,
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<grant-digest>",
    "surface_hash": "sha-256:<surface-digest>",
    "action_id": "comment.create"
  }
}
```

`representation_revision` is a positive, monotonically increasing AHP
presentation revision within one `ahp_session_id` and `representation_id`.
`control_id` is stable only within that representation lineage. `control_kind`
is `present` when the binding projects ASP state for display and `invoke` when a
control proposes an ordinary ASP operation. The nested `asp` object MUST be the
complete type-specific ASP message or an exact typed reference to one available
through the authenticated ASP path. Extracted tuple members shown above are not
a second authority record: a receiver MUST require them to equal the validated
ASP object and current local binding.

An AHP control can propose only the exact ASP message type, action id, mode,
input, hashes, and session generation named by its validated binding. Activating
the control causes the Runtime Mediator to construct or retrieve the ordinary
ASP request, revalidate current Grant, surface, session, approval, policy,
budget, and idempotency state, and submit it through the normal ASP endpoint.
Changing an AHP form value requires the same ASP schema validation,
normalization, hashing, preview, and approval processing as any other input
change. The control itself never authorizes dispatch.

#### Binding State Machine

For each authenticated AHP session and representation lineage, a conforming
Runtime Mediator implements these states:

| State | Input | Next state | Required behavior |
| --- | --- | --- | --- |
| `unbound` | exact profile selection on an authenticated channel | `bound` | Record the selected profile and base AHP session; disclose no ASP state yet. |
| `bound` | fresh representation with a valid ASP tuple | `presented` | Revalidate exposure and current ASP state, retain the exact revision binding, then present only the authorized projection. |
| `presented` | exact control activation | `pending` | Revalidate the current ASP object and authority, then send at most one ordinary ASP request under its own idempotency rules. |
| `pending` | authenticated, validated ASP response | `presented` or `terminal` | Update AHP presentation only from the accepted ASP result; verify any receipt independently. |
| `pending` | timeout, disconnect, or ambiguous outcome | `reconciling` | Preserve the ASP idempotency identity and authority tuple; do not infer failure or retry from AHP navigation. |
| any non-terminal state | profile loss, authentication loss, tuple mismatch, stale/conflicting revision, revocation, or invalid ASP state | `fenced` | Suppress presentation updates and new dispatch until a fresh binding and authoritative ASP reconciliation succeed. |

The AHP presentation lifecycle does not change the ASP Session Authority and
Lifecycle state machine. An AHP `terminal` page does not complete or cancel an
ASP session, and an AHP reconnect does not resume one. Only a validated ASP
transition can do so.

#### Replay, Failure, and Security Rules

A receiver retains the highest accepted representation revision and a digest of
the complete normalized binding for each representation lineage. A lower
revision is stale. Reuse of the current revision is an exact replay only when
the complete binding is identical; conflicting reuse is rejected and MUST NOT
update UI state, release credentials, advance an ASP session, dispatch an
action, or create receipt evidence. A higher revision can replace presentation
state, but every embedded ASP tuple and object is revalidated independently.

An AHP representation claiming `active`, `approved`, `success`, `cancelled`,
`revoked`, or another ASP-significant label is descriptive UI content until the
corresponding authenticated ASP object verifies. A receipt summary, receipt
link, hash-shaped string, or rendered signature badge is not a receipt. A
runtime or adapter MUST retrieve or receive the complete receipt through the
ordinary authenticated receipt path and apply all role, integrity, tuple, and
hash-chain checks before using it as evidence.

Invalid binding data produces a deterministic local `binding_invalid` policy
decision. It is not converted into an ASP denial allegedly issued by the
application. The runtime retains current ASP authority, session, idempotency,
and outcome-reconciliation state, suppresses the AHP UI update or dispatch, and
MAY show a non-authoritative local error. Unknown AHP extensions remain
presentation metadata and MUST NOT add ASP meaning.

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

ASP manifests, grants, events, action input schemas, action inputs, action
execution contexts, policy decisions, and receipts use the
`asp-jcs-sha-256` profile when a field in this draft is named `surface_hash`,
`grant_request_hash`, `grant_hash`, `aspeventhash`, `input_schema_hash`, `input_hash`,
`execution_hash`, `preconditions_hash`,
`expected_effects_hash`, `actual_effects_hash`, `policy_decision_hash`,
`receipt_hash`, `parent_receipt_hash`, `record_hash`, `bundle_hash`, or
`report_hash`. The profile identifies exact JSON content; it does not by itself
authenticate the producer, exporter, or grant authority.

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
| semantic Agent Grant request | `https://github.com/0al-spec/agent-surface/hash/grant-request/v1` | RFC 9396 `type` only; an authorization-server output member makes the request invalid and is not an exclusion |
| authoritative Agent Grant | `https://github.com/0al-spec/agent-surface/hash/grant/v1` | top-level `grant_hash`; the RFC 9396 `type` discriminator when starting from an OAuth authorization-details object |
| ASP CloudEvent occurrence | `https://github.com/0al-spec/agent-surface/hash/event/v1` | `aspeventhash`; delivery-only `aspsubid`, `aspdeliveryid`, `aspattempt`, `aspstream`, `aspsequence`, and `aspcursor`; diagnostic `traceparent` and `tracestate` |
| Action Input Schema | `https://github.com/0al-spec/agent-surface/hash/action-input-schema/v1` | none; the hashing view is the complete self-contained JSON Schema document |
| Action Request `input` | `https://github.com/0al-spec/agent-surface/hash/action-input/v1` | none; the hashing view is exactly the schema-valid `payload.input`; an idempotency-required input has already passed the action's fixed-point normalization check, and the hash performs no further transform |
| Action Execution Context | `https://github.com/0al-spec/agent-surface/hash/action-execution/v1` | `execution_token`; the hashing view is `payload.execution` after structural validation with the confidential raw token omitted |
| Action Preconditions | `https://github.com/0al-spec/agent-surface/hash/action-preconditions/v1` | none; the hashing view is exactly the validated `preconditions` object |
| Expected Effects | `https://github.com/0al-spec/agent-surface/hash/expected-effects/v1` | none; the hashing view is exactly the validated `expected_effects` array |
| Actual Effects | `https://github.com/0al-spec/agent-surface/hash/actual-effects/v1` | none; the hashing view is exactly the validated `actual_effects` array |
| Human Elicitation context | `https://github.com/0al-spec/agent-surface/hash/human-elicitation-context/v1` | none; the hashing view is the complete closed `context` object |
| Human Elicitation request | `https://github.com/0al-spec/agent-surface/hash/human-elicitation-request/v1` | top-level `request_hash` |
| Human Elicitation response | `https://github.com/0al-spec/agent-surface/hash/human-elicitation-response/v1` | top-level `response_hash` |
| Policy Decision Object | `https://github.com/0al-spec/agent-surface/hash/policy-decision/v1` | top-level `policy_decision_hash` |
| receipt | `https://github.com/0al-spec/agent-surface/hash/receipt/v1` | top-level `receipt_hash` and `receipt_signatures` |
| Portable Replay Bundle record | `https://github.com/0al-spec/agent-surface/hash/replay-record/v1` | top-level `record_hash` |
| Portable Replay Bundle | `https://github.com/0al-spec/agent-surface/hash/replay-bundle/v1` | top-level `bundle_hash` |
| Replay Validation Report | `https://github.com/0al-spec/agent-surface/hash/replay-report/v1` | top-level `report_hash` |

All other members, including extension members, are part of the hashing view.
Omitting an unknown member before hashing is therefore an integrity failure,
not extension tolerance. A party that receives a redacted or filtered object
MAY carry its hash as an opaque reference but MUST NOT claim to have recomputed
it without the complete hashing view.

The Action Input hash commits to the exact validated wire input and prevents a
receipt from being attached to different input. For an idempotency-required
action, the runtime first applies the manifest-pinned Idempotency Input
Normalization profile and sends that fixed-point value as the wire input. The
hash function itself still performs no default insertion, equivalence, or set
ordering: it commits to the already-normalized wire value so approval,
idempotency, execution evidence, and receipts cannot select different views.

For an idempotency-required action, `input_schema_hash` commits to the complete
I-JSON document retrieved from `input_schema` using the Action Input Schema
domain above. That schema MUST be self-contained: every `$ref` or `$dynamicRef`
MUST be a same-document fragment reference, and retrieval redirects MUST NOT
change the final authenticated origin. The runtime and application MUST verify
the declared hash before using the schema for normalization, approval, hashing,
or execution. A missing or mismatching document is `integrity_mismatch` and
MUST NOT fall back to a cached or newly fetched interpretation. Changing the
schema JSON data model changes `input_schema_hash`, the manifest hashing view,
`surface_version`, and `surface_hash`. A future surface-bundle profile can
define transitive external schema references; this profile does not.

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

For surface lifecycle decisions, the application MUST define a surface
lifecycle key as (server-authenticated tenant context or a public-context
marker, `issuer`, `app_id`, canonical `surface_url`) and maintain exactly one
issuer-authoritative current discovery snapshot for that key. Tenant context
is server state, never a caller-supplied selector. The authenticated object
served at the canonical URL MUST be the designated snapshot. This designation
is application state shared with the authorization server; it is not inferred
by ordering opaque `surface_version` values. Changing the canonical URL for the
same tenant, issuer, and app id MUST atomically migrate the lifecycle state and
supersede the prior location; it MUST NOT create an independent issuance
history. A cached or retained object can remain valid for an already-issued
Grant without remaining eligible for new issuance.

### Curated Surface Boundary

An Agent Surface is an explicit, application-selected allow-list of affordances
for agent delegation. It is not a requirement to publish the application's full
API, route table, RPC service, MCP tool inventory, UI command set, or
administrative interface. A publisher MAY expose a very small surface, such as
one read resource and one proposal action, while leaving billing, account
administration, bulk export, destructive maintenance, and other application
operations outside ASP.

The curated inventory defines which affordances are eligible for ASP discovery
and delegation; it is not authority by itself. A valid Agent Grant and every
ordinary runtime-side and application-side check remain required.

For every included resource, action, or event, the publisher MUST provide the
complete ASP declaration required by this specification. That completeness
requirement applies to the selected surface inventory and its references; it
does not require completeness relative to any underlying application API. An
underlying operation's existence, visibility, or authentication policy is not
by itself an ASP declaration.

A publisher MUST NOT treat membership in an OpenAPI document, AsyncAPI
document, route table, RPC schema, MCP server, SDK, or UI registry as sufficient
for inclusion in the Agent Surface. It MUST NOT mechanically mirror an
underlying interface merely because those operations exist; every resulting ASP
member MUST independently declare every field and semantic required for its
member type, including the applicable scope, risk, approval, exposure,
execution, idempotency, effect, receipt, endpoint, and lifecycle semantics. A
publisher MAY deliberately map every operation from an underlying interface
only when it explicitly selects each operation and every resulting ASP
declaration independently satisfies this specification. One ASP action MAY
compose multiple application operations, and multiple ASP actions MAY map to
different safety stages of one application operation.

Only declarations in the exact verified manifest snapshot define its ASP
inventory. A runtime, Grant Issuer, Action Executor, or Agent Adapter MUST NOT
synthesize additional ASP resources, actions, events, scopes, or authority from
endpoint naming, ordinary API documentation, SDK metadata, MCP discovery, UI
availability, or a credential's broader capabilities. A request for an action
absent from the Grant's pinned surface remains `action_unknown`; the component
MUST NOT search another API description, call an ordinary application endpoint,
or substitute a similarly named operation.

Publishing a previously omitted affordance is a manifest change and therefore
requires a new `surface_version` and `surface_hash`. It does not add authority
to a Grant pinned to the prior snapshot. The ordinary compatibility,
fresh-consent, renewal, and attenuation rules determine whether a new Grant can
include it. Conversely, adding or removing an underlying application operation
that was never part of the Agent Surface does not by itself change the manifest,
unless that change alters the implementation or semantics of a published
affordance.

Applications and non-agent integrations MAY continue to use ordinary
application APIs under their own authority models. Such access is outside ASP
and MUST NOT be represented as an ASP Grant, ASP action, ASP receipt, or ASP
conformance evidence. The separate runtime-mediation rule still prohibits an
agent, adapter, or subagent from using that alternative path to bypass the
Agent Surface authority boundary.

The boundary has these required fail-closed outcomes:

| Condition | Required outcome |
| --- | --- |
| An API route, RPC method, MCP tool, SDK method, or UI command exists but is absent from the exact manifest snapshot | It remains outside ASP; do not infer or synthesize a resource, action, event, scope, or authority. |
| A semantic Grant request names an action absent from the current verified manifest | Reject issuance; the OAuth profile uses `invalid_authorization_details`. |
| An Action Request names an action absent from the Grant's retained pinned manifest | Return `action_unknown` before idempotency lookup, budget admission, receipt creation, workload dispatch, or effect; do not search another interface or snapshot. |
| A selected affordance lacks required ASP semantics or the publisher cannot enforce its declaration | Reject the manifest as `surface_incompatible`; do not expose the member as partially usable. |
| The application adds a backend operation without publishing a new manifest snapshot | Do not change ASP discovery or any active Grant. |

### OpenAPI and AsyncAPI Import Profile

The optional OpenAPI and AsyncAPI Import Profile lets a publisher generate one
ordinary Agent Surface Manifest from deliberately placed `x-agent-surface`
specification extensions. Its profile identifier is
`https://github.com/0al-spec/agent-surface/profiles/api-import/v1`.
The profile is a publishing-time authoring transform, not an ASP runtime
discovery, authorization, or invocation wire protocol, conformance handshake,
or certification mechanism. An API description, an annotation, importer output
that has not passed complete manifest validation, or an importer report is
never Agent Grant or action authority.

Version 1 consumes the parsed I-JSON data model of exactly one of:

- an OpenAPI Description whose `openapi` value is `3.1.<patch>` or
  `3.2.<patch>`; or
- an AsyncAPI document whose `asyncapi` value is `3.0.<patch>` or
  `3.1.<patch>`.

`<patch>` is one or more ASCII decimal digits. A document containing both
version fields, neither field, another major or minor version, a pre-release
label, or a non-string version is unsupported and MUST fail without output.
The importer does not establish that the remaining source document conforms to
OpenAPI or AsyncAPI; the publisher remains responsible for validating it under
the selected source specification.

The input can originate from JSON or a YAML 1.2 representation only when the
frontend produces the same unambiguous I-JSON data model. A frontend MUST
reject duplicate mapping keys, non-string mapping keys, non-JSON tags,
every number that is not a finite IEEE 754 binary64 value, JSON negative zero,
every mathematically integral number outside
`[-9007199254740991, 9007199254740991]`, every alias, every merge key, and
any string or member name containing an unpaired surrogate or Unicode
Noncharacter forbidden by I-JSON. These restrictions apply even to unannotated
source metadata. Numeric source spellings otherwise identify their parsed
binary64 value; v1 does not retain decimal lexemes. Version 1 does not define
alias expansion or merge precedence, even when a frontend could produce one
deterministic expansion. A frontend MUST NOT resolve ambiguity by last-key-wins
parsing. The reference importer below intentionally accepts strict JSON only.

#### Annotation Objects and Locations

The source root MUST contain exactly one `x-agent-surface` root annotation.
That annotation is a closed object containing exactly:

- `profile`, REQUIRED and equal to the profile identifier above;
- `manifest_base`, REQUIRED and containing the complete ordinary manifest
  top-level members other than the four importer-owned output members
  `surface_hash`, `resources`, `actions`, and `events`; and
- `members`, OPTIONAL, a non-empty array of member mappings.

`manifest_base` MUST contain `protocol`, `app_id`, `issuer`, `surface_mode`,
`surface_version`, `surface_url`, `auth`, `agent_api`, `scopes`,
`data_classes`, `audit`, and `revocation` with their ordinary meanings. It MUST
NOT contain any importer-owned output member, even with an empty, null,
placeholder, or allegedly precomputed value. In particular, the importer
always computes `surface_hash`; accepting a caller-supplied value would permit
a stale or unrelated integrity claim.

Every operation annotation is a closed object containing exactly one
non-empty `members` array. Each entry in a root or operation array is a closed
object containing exactly:

- `kind`: `resource`, `action`, or `event`; and
- `declaration`: the complete ASP declaration for that kind, including a
  non-empty `id`.

The root `members` array MAY contain any of the three kinds. It is the explicit
escape hatch for resources, composed actions, events derived from more than one
source operation, and other mappings that are not one-to-one. An absent root
array is equivalent to no root members, but the complete document MUST select
at least one member.

Operation annotations are accepted only at these direct, inline locations:

| Source | Eligible location | Permitted member kind |
| --- | --- | --- |
| OpenAPI | an inline HTTP Operation Object at `/paths/{path-template}/{method}`, where `{method}` is exactly `get`, `put`, `post`, `delete`, `options`, `head`, `patch`, or `trace` | `action` |
| AsyncAPI | an inline Operation Object at `/operations/{operation-id}` whose exact `action` is `send` | `event` |

An annotated Reference Object, OpenAPI callback, webhook, 3.2 `query` or
`additionalOperations` entry, AsyncAPI `receive` operation or trait, reusable
component, or any other location is unsupported in v1. The importer MUST reject
the complete input when the exact `x-agent-surface` name occurs anywhere other
than the root or an eligible inline operation. It MUST NOT ignore a misplaced
annotation, merge siblings into a referenced object, or infer that an
annotation elsewhere was only documentation.

The importer scans only the supplied root document. It MUST NOT fetch a URI,
follow a `$ref`, load another file, expand a callback, apply a trait, contact an
API endpoint, or inspect implementation code to discover more annotations.
An unannotated operation, including one reached through a reference, remains
unselected.

#### Projection Algorithm

A v1 publishing pipeline using this profile MUST perform these steps in order:

1. Parse the complete source into one duplicate-free I-JSON object and validate
   the supported source version, exact root profile, annotation shapes, and
   annotation locations.
2. Validate every member as a complete declaration of its stated ASP kind.
   The annotation location supplies build provenance only; it supplies no
   declaration default.
3. Collect root members and eligible operation members. Reject a repeated
   `(kind, declaration.id)` pair even when the declarations are byte-identical.
4. Sort each resulting `resources`, `actions`, and `events` array by ascending
   unsigned lexicographic order of the UTF-8 bytes of `declaration.id`. Array
   order is hash-significant, so a source map's serialization order MUST NOT
   select the output hash.
5. Deep-copy `manifest_base`, insert the three complete arrays, validate the
   resulting object under every ordinary Agent Surface Manifest requirement,
   and verify that all scopes, data classes, schemas, companions, endpoints,
   modes, effects, exposure contracts, and other references resolve.
6. Compute `surface_hash` with the Agent Surface Manifest hashing view in the
   Canonical Object Hash Profile, insert it, and revalidate the complete
   publishable manifest.
7. Emit that one manifest only after every prior step succeeds.

Any parse, profile, version, location, shape, reference, duplicate,
completeness, lint, validation, or hashing failure aborts the complete
projection. The importer MUST NOT emit a partial manifest, retain an earlier
array, skip only the invalid member, or label an unvalidated candidate as
publishable. Import failure is a local publishing-tool error, not an ASP error
response. If an invalid generated object is nevertheless served, ordinary
consumers reject it as `surface_incompatible`.

The importer MUST NOT derive an ASP identifier, scope, resource, schema, risk,
approval mode, execution mode, idempotency rule, effect, exposure class,
retention rule, event direction, endpoint, authentication policy, or authority
from an OpenAPI HTTP method, `operationId`, server, security requirement,
parameter, request or response schema, tag, callback, or from an AsyncAPI
channel, message, payload, `schemaFormat`, binding, or trait. Such source
metadata can help an author prepare an explicit declaration, but it has no
standardized ASP meaning.

The emitted manifest is the only runtime object produced by this profile.
It contains neither `x-agent-surface` annotations nor an implicit source
binding. A publisher MAY add a separately defined collision-resistant
provenance extension to `manifest_base`; if it does, that extension is part of
the manifest hashing view and does not become authority merely because it is
hash-bound.

Changing a projected declaration or any other emitted member changes the
manifest hashing view and requires a new `surface_version` and
`surface_hash`. Reordering source maps or changing an unannotated source
operation does not by itself change the output. The publisher still MUST update
the manifest when an underlying change alters the implementation or semantics
of a published affordance. A previously unannotated operation becomes eligible
for ASP only after an explicit annotation or root mapping produces a new valid
snapshot and the ordinary consent and Grant lifecycle completes.

At issuance and execution time, import provenance has no fallback semantics. A
source operation that is absent from the Grant's pinned generated manifest
remains outside ASP and follows the Curated Surface Boundary:
`invalid_authorization_details` during OAuth issuance and `action_unknown`
before idempotency lookup, dispatch, receipt creation, or effect during action
execution.

### Required Top-Level Fields

```json
{
  "protocol": "agent-surface/0.1",
  "app_id": "com.example.project-tool",
  "issuer": "https://example.com",
  "surface_mode": "standard",
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

`surface_mode` is REQUIRED and MUST be either `standard` or `proposal_only`.
`standard` means that the independently declared action modes and issued Grant
remain the authority boundary; it does not itself authorize a write or require
that the surface expose one. `proposal_only` adds the surface-wide upper bound
defined in Proposal-Only Surface Mode. An implementation that does not
understand the value MUST reject the manifest as `surface_incompatible` rather
than ignore it.

This version defines the exact protocol identifier `agent-surface/0.1`.
Publishers, consumers, conformance claims, and conformance reports MUST compare
that value case-sensitively and MUST NOT substitute an alias or a compatible-
looking version label.

The optional top-level `operational_limits` member declares only the
hash-bound load-planning ceilings defined in Rate Limits and Quotas. Its
absence means that the surface publishes no standardized operational capacity
contract; it MUST NOT be interpreted as unlimited capacity or as permission to
ignore a `rate_limited` response.

### Surface Hash

Every manifest MUST contain `surface_hash` computed with the Canonical Object
Hash Profile over the complete manifest hashing view. A runtime MUST recompute
and verify it before using the manifest for capability matching, consent, grant
issuance, or action validation. The authorization server MUST perform the same
check before embedding the value in a grant.

`surface_version` remains the application's opaque compatibility label;
`surface_hash` identifies the exact manifest object published under that label,
including schema URLs and any explicit schema hashes. It does not commit
transitive schema content for which the manifest declares no content hash. A
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
    "credential_audience": "https://example.com/agent-api",
    "grant_request_url": "https://example.com/agent-grants/request",
    "grant_introspection_url": "https://example.com/agent-grants/introspect",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "action_url": "https://example.com/agent-actions",
    "budget_state_url": "https://example.com/agent-budgets/state",
    "budget_query_retention_seconds": 300,
    "session_control_url": "https://example.com/agent-sessions/control",
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

`agent_api.credential_audience` is REQUIRED and MUST be an absolute HTTPS URI
identifying the application's logical ASP protected resource. The authorization
server issues every Agent Grant Credential with exactly this audience, and each
credential-protected endpoint in `agent_api` MUST reject a credential for
another audience. The URI need not be an invocation endpoint: DPoP still binds
each proof to the actual request method and target URI. One audience lets the
same exact grant tuple authenticate Action Requests and the closed budget and
session safety operations without treating those control operations as granted
actions. Changing it changes the manifest hashing view and requires a new
`surface_version` and `surface_hash`.

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

`agent_api.budget_state_url` and `agent_api.budget_query_retention_seconds` are
REQUIRED when the application can accept `max_write_actions`,
`max_parallel_sessions`, or the application-cost partition in an Agent Grant.
The URL MUST be absolute HTTPS. The retention value MUST be a positive integer
and fixes how long an accepted `budget.query` idempotency record remains
replayable. Together they expose the authenticated `budget.query` /
`budget.state` contract defined below. An already negotiated Runtime Bridge MAY
carry the identical typed messages, but support remains discoverable through
the manifest and cannot be inferred from an action or event endpoint. Changing
either value changes the manifest hashing view and requires a new
`surface_version` and `surface_hash`.

`agent_api.session_control_url` is REQUIRED when the application accepts a
Runtime participant in an ASP session or a Grant containing `max_tool_calls`,
`max_model_tokens`, `max_runtime_seconds`, or the runtime-cost partition. It
MUST be an absolute HTTPS URL, accept the `runaway_guard` reason and, when the
application supports a runtime-authoritative budget dimension, the
`budget_exceeded` reason, and return `session.state` as defined below. An already
negotiated Runtime Bridge MAY carry the identical messages, but it does not
replace this discoverable HTTP binding. The endpoint uses the Grant Credential
and its required credential-binding proof; fields inside a message are not
authentication. Changing the URL changes the manifest hashing view and requires
a new `surface_version` and `surface_hash`.

Implementations MAY collapse these endpoints when the application already has
equivalent OAuth or API infrastructure, but the manifest MUST make the wire-level
surface discoverable.

### Example Manifest

```json
{
  "protocol": "agent-surface/0.1",
  "app_id": "com.example.project-tool",
  "issuer": "https://example.com",
  "surface_mode": "standard",
  "surface_version": "2026-06-25",
  "surface_hash": "sha-256:<base64url-digest>",
  "surface_url": "https://example.com/.well-known/agent-surface.json",
  "compatibility": {
    "min_runtime": "application-runtime/0.1",
    "schema_dialect": "https://json-schema.org/draft/2020-12/schema",
    "runtime_identity_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1"
    ],
    "remote_processing_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1"
    ],
    "training_use_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/agent-training-use/v1"
    ],
    "approval_receipt_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1"
    ],
    "human_elicitation_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/human-elicitation/v1"
    ],
    "human_elicitation_replay_retention_seconds": 86400,
    "agent_passport_profiles": [
      {
        "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
        "hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
        "verification_profiles": [
          "https://example.com/profiles/agent-passport-verification/2026-01"
        ],
        "max_artifact_bytes": 262144
      }
    ]
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
    "pkce_required": true,
    "runtime_attestation": {
      "framework": "https://github.com/0al-spec/agent-surface/profiles/runtime-attestation/v1",
      "attestation_url": "https://example.com/runtime-attestation",
      "profiles_supported": [
        "https://verifier.example/profiles/eat-tpm-runtime/v1"
      ],
      "verifiers": [
        {
          "verifier_id": "verifier_7f3a",
          "profiles": [
            "https://verifier.example/profiles/eat-tpm-runtime/v1"
          ]
        }
      ]
    }
  },
  "agent_api": {
    "credential_audience": "https://example.com/agent-api",
    "grant_request_url": "https://example.com/agent-grants/request",
    "grant_introspection_url": "https://example.com/agent-grants/introspect",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "action_url": "https://example.com/agent-actions",
    "budget_state_url": "https://example.com/agent-budgets/state",
    "budget_query_retention_seconds": 300,
    "session_control_url": "https://example.com/agent-sessions/control",
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
      "id": "session.metadata",
      "classification": "sensitive",
      "label": "Session metadata",
      "description": "Identifiers and lifecycle state for an ASP session."
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
      "idempotency_normalization": {
        "profile": "asp-json-normalization-v1"
      },
      "input_hash_profile": "asp-jcs-sha-256",
      "execution": {
        "mode": "propose",
        "operation_id": "comment.publish",
        "persisted": true,
        "commit_action": "comment.create"
      },
      "input_schema": "https://example.com/schemas/comment-propose.input.schema.json",
      "input_schema_hash": "sha-256:<input-schema-digest>",
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
      "risk": "public_side_effect",
      "risk_explanation": {
        "default_language": "en",
        "localizations": [
          {
            "language": "en",
            "summary": "Publishes a comment for other repository users.",
            "effect_summaries": [
              {
                "effect_id": "comment-publish",
                "summary": "Creates an irreversible shared communication record."
              }
            ]
          }
        ]
      },
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
      "idempotency_normalization": {
        "profile": "asp-json-normalization-v1"
      },
      "input_hash_profile": "asp-jcs-sha-256",
      "execution_hash_profile": "asp-jcs-sha-256",
      "execution": {
        "mode": "commit",
        "operation_id": "comment.publish",
        "proposal_action": "comment.propose"
      },
      "input_schema": "https://example.com/schemas/comment-create.input.schema.json",
      "input_schema_hash": "sha-256:<input-schema-digest>",
      "output_schema": "https://example.com/schemas/comment-create.output.schema.json",
      "data_exposure": {
        "classes": ["repository.content"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      },
      "receipt": "required"
    }
  ],
  "operational_limits": {
    "profile": "https://github.com/0al-spec/agent-surface/profiles/operational-limits/v1",
    "actions": [
      {
        "action_id": "comment.create",
        "partition": "grant",
        "windows": [
          {
            "limit_id": "comment-create-per-minute",
            "max_admissions": 20,
            "window_seconds": 60
          },
          {
            "limit_id": "comment-create-per-day",
            "max_admissions": 1000,
            "window_seconds": 86400
          }
        ],
        "in_flight": {
          "limit_id": "comment-create-in-flight",
          "max": 4
        }
      }
    ],
    "events": [
      {
        "event_id": "task.created",
        "partition": "subscription",
        "windows": [
          {
            "limit_id": "task-created-per-minute",
            "max_first_deliveries": 120,
            "window_seconds": 60
          }
        ]
      }
    ]
  },
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
      "id": "budget.warning",
      "control": true,
      "schema": "https://example.com/schemas/budget-warning.event.schema.json",
      "data_exposure": {
        "classes": ["grant.metadata"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    },
    {
      "id": "budget.exceeded",
      "control": true,
      "schema": "https://example.com/schemas/budget-exceeded.event.schema.json",
      "data_exposure": {
        "classes": ["grant.metadata"],
        "redaction": {"mode": "none"},
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
    },
    {
      "id": "session.paused_budget",
      "control": true,
      "schema": "https://example.com/schemas/session-paused-budget.event.schema.json",
      "data_exposure": {
        "classes": ["grant.metadata", "session.metadata"],
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

`compatibility.runtime_identity_profiles`, when present, MUST be a non-empty
array of unique collision-resistant profile identifiers. It advertises the
runtime identity profiles the authorization server can authenticate, project
into an Agent Grant, and revalidate at protected-resource time. A runtime MUST
NOT infer support from an OAuth client registration, a credential format, or a
human-readable deployment label. Absence means that this manifest requires only
the base app-scoped `delegate.runtime` binding; it does not mean that the
runtime is anonymous or attested.

`compatibility.remote_processing_profiles`, when present, MUST be a non-empty
array of unique collision-resistant profile identifiers. It advertises only
profiles whose request commitment, issuer-derived disclosure ceiling, Grant
binding, and protected-resource checks the application implements completely.
A runtime MUST NOT infer support from a Runtime Identity locality, management
posture, network location, provider label, or an application privacy notice.
Absence means that the application makes no Remote Processing Privacy Profile
claim; it MUST NOT be interpreted as either allowing or prohibiting remote
processing.

`compatibility.training_use_profiles`, when present, MUST be a non-empty array
of unique collision-resistant profile identifiers. It advertises only profiles
whose class-set validation, issuer-side attenuation, Grant binding, downstream
enforcement, and consent semantics the application implements completely. A
runtime MUST NOT infer support or policy from a retention mode, privacy notice,
provider label, model setting, or Remote Processing path. Absence means training
use is unspecified, not prohibited and not permitted.

`compatibility.approval_receipt_profiles`, when present, MUST be a non-empty
array of unique collision-resistant profile identifiers. It advertises only
profiles for which the application can validate per-action Grant requirements,
authenticate complete runtime Approval Receipts, produce application Approval
Receipts, bind their hashes into action evidence, and enforce replay and expiry
rules completely. Advertising a receipt schema or signing algorithm alone is
not support. Absence means the application implements only the base opaque
approval-reference behavior and MUST reject a Grant selecting this profile.

`compatibility.human_elicitation_profiles`, when present, MUST be a non-empty
array of unique collision-resistant profile identifiers and MUST be accompanied
by `compatibility.human_elicitation_replay_retention_seconds`, a positive safe
integer. The two members advertise only profiles the application can negotiate
on an authenticated participant channel, validate under the current surface
and Grant tuple, and retain with the terminal replay guarantees defined by the
Human Elicitation Events Profile. The retention value starts at terminal
acceptance and changes the manifest hashing view. Absence of either member
means that the application does not support Human Elicitation; a runtime MUST
NOT infer support from UI capabilities, an AHP carrier, or receipt behavior.

`compatibility.agent_passport_profiles`, when present, MUST be a non-empty array
of closed objects. Each object MUST contain `profile`, `hash_profile`,
`verification_profiles`, and `max_artifact_bytes`. The first two values are
collision-resistant identifiers; `verification_profiles` is a non-empty array
of unique collision-resistant identifiers; and `max_artifact_bytes` is a
positive integer no greater than `9007199254740991`. The object advertises only
combinations the application can retrieve, independently verify, status-check,
and bind into a Grant. A runtime MUST NOT infer production verification support
from the source `apiVersion`, signature algorithm label, file extension, or
presence of a validator.

`audit.required_fields` advertises the non-conditional minimum for application
receipts and MUST NOT weaken the Receipt Requirements profile. Conditional
fields such as `parent_receipt_hash`, `output_hash`, approval evidence, error
classification, producer-authoritative budget charges, and required signatures
remain mandatory when their receipt semantics require them even if they are not
repeated in this list.

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
- optional `risk_explanation`
- `approval`
- `input_schema`
- `input_schema_hash` for every idempotency-required action and linked dry run
- `output_schema`
- `side_effect`
- `effects` for actions that change domain or coordination state
- `execution`
- optional `capability_hint`
- `idempotency` for side-effecting actions
- `idempotency_normalization` whenever `idempotency` is `required`
- `receipt` for side-effecting actions
- `input_hash_profile` for every idempotency-required action and every action
  requiring receipt- or preview-linked input evidence
- `execution_hash_profile` for `reserve`, `commit`, `compensate`, and `revert`
- `data_exposure`

An action whose receipt chain binds the exact request input MUST set
`input_hash_profile` to `asp-jcs-sha-256`. Other profile identifiers are not
defined by this draft.

An action with `idempotency: "required"` MUST declare an
`idempotency_normalization` object whose `profile` is
`asp-json-normalization-v1` and MUST set `input_hash_profile` to
`asp-jcs-sha-256`, including when the action is a persisted proposal that does
not require a receipt. It MUST also publish `input_schema_hash` for the
self-contained schema document. The optional `defaults` and
`unordered_arrays` members and their fail-closed processing rules are defined
in Idempotency Input Normalization. Other profile identifiers are not defined
by this draft; a runtime that does not understand the declared profile MUST
treat the surface as incompatible for that action rather than guess
equivalence.

Every action MUST declare exactly one standard `execution.mode` and a stable
`execution.operation_id`. The mode, companion-action references, effect model,
and mode-specific schemas are defined by the Action Execution Model. An action
in mode `reserve`, `commit`, `compensate`, or `revert` MUST set
`execution_hash_profile` to `asp-jcs-sha-256`; other profile identifiers are not
defined by this draft.

A publisher MAY declare per-action operational admission windows and
concurrency through the top-level `operational_limits` profile. Such a
declaration is a load-planning ceiling, not action authority, approval, a Grant
budget, an idempotency rule, or a capacity reservation.

Example:

```json
{
  "id": "pull_request.review.submit",
  "scope": "pull_request.review.write",
  "risk": "public_side_effect",
  "risk_explanation": {
    "default_language": "en",
    "localizations": [
      {
        "language": "en",
        "summary": "Publishes a review for other repository users.",
        "effect_summaries": [
          {
            "effect_id": "review-publish",
            "summary": "Creates an irreversible shared communication record."
          }
        ]
      }
    ]
  },
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
  "idempotency_normalization": {
    "profile": "asp-json-normalization-v1"
  },
  "input_hash_profile": "asp-jcs-sha-256",
  "execution_hash_profile": "asp-jcs-sha-256",
  "execution": {
    "mode": "commit",
    "operation_id": "pull_request.review.publish",
    "proposal_action": "pull_request.review.propose"
  },
  "input_schema": "https://example.com/schemas/pr-review-submit.input.schema.json",
  "input_schema_hash": "sha-256:<input-schema-digest>",
  "output_schema": "https://example.com/schemas/pr-review-submit.output.schema.json",
  "data_exposure": {
    "classes": ["repository.content"],
    "redaction": {"mode": "none"},
    "retention": {"mode": "transient", "delete_on_grant_end": true}
  },
  "receipt": "required"
}
```

### Proposal-Only Surface Mode

Applications that are not ready to allow direct agent writes SHOULD expose a
surface with `surface_mode: "proposal_only"`. This value is a hash-bound,
surface-wide upper bound on ASP authority, not an action mode, risk label,
approval shortcut, or grant. `surface_mode: "standard"` leaves the upper bound
to each independently declared action and issued Grant; it does not itself
authorize a write.

A proposal-only manifest MUST contain at least one action whose
`execution.mode` is `propose`. Every action in the manifest MUST use mode
`read` or `propose`, MUST declare `side_effect: false`, and MUST omit `effects`.
Mode `dry_run` is excluded because this draft defines it as validation of a
possible later commit; `reserve`, `commit`, `compensate`, and `revert` are
excluded because they change domain or coordination state. No action in a
proposal-only manifest may declare a companion-action relationship to a
state-changing stage, including `commit_action`, `dry_run_action`,
`proposal_action`, `reservation_action`, `recovery_actions`, `target_actions`,
or a reservation acquisition, renewal, or release action.

A proposal-only action is a typed action whose output is a draft, suggestion,
patch, review body, or other non-committed artifact. The proposal artifact,
its identifier or hash, approval of it, and any receipt are evidence only.
None of them is transferable ASP authority. Another API MAY accept the
artifact only after applying its own independent authentication and
authorization; for example, the application MAY let a human apply it through
an ordinary UI under that human's app-native authority.

Persisting a proposal as a draft is protocol bookkeeping, not a
domain-visible commit. Repeated proposal requests can nevertheless accumulate
duplicate drafts under retries and agent loops. An action that persists
proposals MUST declare `execution.persisted: true` and
`idempotency: "required"`, accept idempotency keys, declare
`idempotency_normalization` using `asp-json-normalization-v1`, set
`input_hash_profile` to `asp-jcs-sha-256`, and deduplicate stored drafts by the
resulting hash. A non-persisted proposal MUST omit `execution.persisted` or set
it to `false`.

A proposal action, including any proposal persistence, MUST NOT mutate the
proposed target object, reserve or exclude a resource, publish or send domain
content, trigger an external operation, or return bearer authority. An
operation with any such effect is state-changing and cannot be declared as
`propose`. The action's Data Exposure Contract governs proposal content
returned to the runtime or agent; it does not govern application-side storage
of agent-supplied draft input. Idempotency, audit, and the application's own
storage and retention obligations still apply to a persisted draft.

The proposal-only bound also excludes direct credential authority. A runtime
MUST NOT request, and an authorization server MUST NOT issue, the separately
authorized `credential.release` capability for a Grant pinned to such a
surface. The semantic Grant request and authoritative Grant MUST contain
`constraints.credential_release` as exactly `{"mode":"deny"}` with no other
member. A contradictory or extension member is invalid rather than an
attenuation. A released credential for a non-Agent-Surface audience would
bypass the claimed bound even though Agent Surface endpoints correctly reject
it.

A runtime MUST validate the complete proposal-only invariant before capability
matching or consent preview. An authorization server MUST validate it before
issuing, renewing, exchanging, or attenuating a Grant, and the application MUST
validate it from the exact retained manifest snapshot before accepting every
Action Request. An inconsistent manifest fails as `surface_incompatible`
before idempotency lookup, budget admission, receipt creation, or any effect.
Because a valid proposal-only inventory contains no state-changing action, a
request for such an action id is `action_unknown`; a request that relabels a
known proposal action is `execution_mode_invalid`. `proposal_required` is
reserved for the separately defined case where a `standard` surface contains a
state-changing action but the effective Grant authorizes only its proposal
companion. No component may silently change a requested mode or substitute a
similarly named proposal action.

Required fail-closed cases are:

| Condition | Required outcome |
| --- | --- |
| Unknown `surface_mode`, missing proposal action, forbidden mode, effect, or companion relationship | Reject the manifest as `surface_incompatible`. |
| Proposal-only semantic Grant request or returned Grant does not contain exactly `constraints.credential_release: {"mode":"deny"}` | Reject issuance; the OAuth profile uses `invalid_authorization_details`. |
| State-changing action id is absent from the pinned proposal-only manifest | Return `action_unknown`; do not search another snapshot. |
| Request repeats `commit` for a manifest-declared `propose` action | Return `execution_mode_invalid`; do not reinterpret the input. |
| Pinned standard manifest contains a commit, but the Grant authorizes only its reciprocal proposal companion | Return `proposal_required`; do not invoke the proposal implicitly. |
| Proposal id, artifact, approval, or receipt is presented as commit authority | Reject before effect under the ordinary Grant, action, approval, and integrity checks. |
| Superseded standard snapshot is used for new issuance after a proposal-only snapshot becomes current | Reject through the authoritative surface lifecycle gate. |

The Grant does not repeat `surface_mode`; its exact
`resource_server.surface_hash` selects the retained manifest and therefore
binds the mode. A scope, action name, proposal result, old Grant, refresh token,
or token exchange MUST NOT override that binding.

An Impact Simulation for a proposal-only surface can project only the exact
known `read` and `propose` action inventory and the proposal-only upper bound.
It MUST NOT fabricate a state-changing companion as a denied example or claim
that the application has no human-operated or non-ASP write path.

The bound forbids application-domain or external write authority through an
ASP action and forbids raw credential release. Closed Grant lifecycle,
revocation, budget-query, session start/pause/resume/cancel, event
subscribe/ack/replay, receipt retrieval, audit, deduplication, and stored-draft
operations remain available under their own authenticated
contracts. They are protocol control or bookkeeping operations, not granted
application actions, and MUST NOT widen a Grant, mutate the proposed target, or
provide a domain-write path. A purported control operation that does so is a
state-changing application action and is invalid on a proposal-only surface.

Example proposal-only fragment:

```json
{
  "surface_mode": "proposal_only",
  "actions": [
    {
      "id": "pull_request.review.propose",
      "scope": "pull_request.review.propose",
      "risk": "propose",
      "side_effect": false,
      "approval": "none",
      "idempotency": "required",
      "idempotency_normalization": {
        "profile": "asp-json-normalization-v1"
      },
      "input_hash_profile": "asp-jcs-sha-256",
      "execution": {
        "mode": "propose",
        "operation_id": "pull_request.review.publish",
        "persisted": true
      },
      "input_schema": "https://example.com/schemas/pr-review-propose.input.schema.json",
      "input_schema_hash": "sha-256:<input-schema-digest>",
      "output_schema": "https://example.com/schemas/pr-review-propose.output.schema.json",
      "data_exposure": {
        "classes": ["repository.content"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    }
  ]
}
```

On a `standard` surface, a proposal action that leads to an ASP commit MUST
declare `commit_action`, and the commit MUST reciprocally identify the
proposal action:

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

The proposal declaration independently contains:

```json
{
  "id": "pull_request.review.propose",
  "execution": {
    "mode": "propose",
    "operation_id": "pull_request.review.publish",
    "commit_action": "pull_request.review.submit"
  }
}
```

Those companion references are invalid on a proposal-only surface. This
distinction lets early adopters expose useful proposal flows without creating
latent ASP write authority.

### Events

Events let applications notify runtimes and agents about app context changes.

Every event declaration MUST contain a non-empty `id` and an absolute `schema`
URI. The CloudEvents binding uses them without aliasing as `type` and
`dataschema`.

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
not authorized by the affected grant. This draft defines `budget.warning`,
`budget.exceeded`, `session.paused_budget`, and `grant.revoked` as core control
events. A manifest that advertises one of them MUST list it in `events` with
`control: true` and a `data_exposure` contract.

`grant.revoked` is an application control event rather than an event authorized
by the revoked grant. Its payload, authentication, and processing requirements
are defined in the OAuth Grant Revocation Profile.

The three budget-related control events are application events. Their producer
MUST be the application bound by the manifest `issuer`; a runtime MUST NOT
fabricate them from its local counters because the CloudEvents `source` binding
would falsely attribute that state to the application. Their payload and
session-fencing requirements are defined in Budget Control Events.

A publisher MAY declare a first-delivery throughput ceiling for a non-control
event through `operational_limits`. Event retry, replay, retention, negotiated
`max_in_flight`, and runtime-directed `event.flow` remain governed by Event
Delivery Semantics and are not replaced by that planning declaration. Core
control events MUST NOT be subject to an operational-limit entry.

### Rate Limits and Quotas

The optional Operational Limits Profile publishes deterministic upper ceilings
that a runtime can use to plan Action Requests and application-event intake.
Its identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/operational-limits/v1
```

`operational_limits` is a closed object containing exactly `profile`, `actions`,
and `events`. `profile` MUST equal the identifier above. `actions` and `events`
are arrays, at least one of which is non-empty. An action or event id appears at
most once in its respective array, resolves exactly in the same manifest, and
every `limit_id` is a non-empty string unique across the complete object.
Unknown members, duplicate ids, unresolved references, an unsupported profile,
or an invalid target make the surface `surface_incompatible`.

An action limit entry has this closed shape:

```json
{
  "action_id": "comment.create",
  "partition": "grant",
  "windows": [
    {
      "limit_id": "comment-create-per-minute",
      "max_admissions": 20,
      "window_seconds": 60
    }
  ],
  "in_flight": {
    "limit_id": "comment-create-in-flight",
    "max": 4
  }
}
```

`partition` MUST be the literal `grant`. `windows`, when present, is a
non-empty array of closed objects containing `limit_id`, `max_admissions`, and
`window_seconds`. `in_flight`, when present, is a closed object containing
`limit_id` and `max`. At least one of `windows` or `in_flight` is REQUIRED.
Every numeric value is a positive I-JSON safe integer. Every referenced action
MUST declare `idempotency: "required"`, so one durable logical record identifies
the window admission and any slot across retry and reconciliation. A short
window describes a rate ceiling; longer conjunctive windows express operational
quotas without calendar, timezone, or reset-boundary ambiguity.

For one authoritative request time `t`, a window counts distinct new logical
admissions in the half-open monotonic interval `(t - window_seconds, t]`. The
application MUST NOT admit the request when doing so would make the count exceed
`max_admissions`. Every applicable window is conjunctive. The partition key is
the server-selected tuple `(issuer, app_id, surface_hash, grant_hash, action_id)`;
no caller-supplied subject, tenant, Grant id, or resource key can select another
partition. `in_flight.max` counts distinct admitted idempotency records without
an authoritative terminal outcome. Connection loss, timeout, an unknown
effect, or a caller assertion does not release a slot; reconciliation or an
authoritative terminal result does. The application uses one logically
consistent monotonic duration source for each partition and MUST fail closed as
`capacity_state_unavailable` without resetting or guessing when authoritative
limiter state is unavailable.

Each successful admission durably records its `limit_id` and elapsed-time
evidence with, or atomically linked to, the idempotency record until every
applicable window has expired; slot state remains until the authoritative
terminal outcome. A distributed deployment MUST serialize competing admissions
through one authoritative state machine. After restart, failover, clock
rollback, or uncertain elapsed time, it retains possibly live admissions
conservatively until it can prove expiry. It MUST NOT reset a window or slot
because process-local monotonic state was lost.

An event limit entry has this closed shape:

```json
{
  "event_id": "task.created",
  "partition": "subscription",
  "windows": [
    {
      "limit_id": "task-created-per-minute",
      "max_first_deliveries": 120,
      "window_seconds": 60
    }
  ]
}
```

`partition` MUST be the literal `subscription`. `windows` is REQUIRED and is a
non-empty array of closed objects containing `limit_id`,
`max_first_deliveries`, and `window_seconds`, all with the same string and
positive-safe-integer requirements above. The partition key is
`(issuer, app_id, surface_hash, subscription_id, event_id)`. A window counts
only the first transmission of a new stable `delivery_id`; retransmission and
replay of that delivery consume no new first-delivery unit. The negotiated
event in-flight window remains the only core event-concurrency limit.

Before first transmission, the application atomically persists the delivery
record, its first-delivery admission marker and elapsed-time evidence, and every
window update. A crash after that transaction is treated as an admitted first
delivery even when the application cannot prove that bytes reached the runtime;
the next transmission is a retry of the same `delivery_id`. A crash before the
transaction sends nothing. Uncertain or unavailable window state queues the
delivery fail closed and never creates an uncharged alternate identity.

The application is the enforcement authority. It MUST atomically evaluate all
applicable windows and any action in-flight slot with creation of the new
logical admission; partial acquisition is forbidden. A runtime SHOULD use each
declared action window as a conservative local scheduling ceiling across every
worker that can dispatch under the same Grant. Such a scheduler uses its own
monotonic sliding history and tentatively counts each fresh logical dispatch
until a definite pre-admission rejection proves that no admission occurred; an
ambiguous outcome remains counted until reconciliation or local window expiry.
For `in_flight.max`, the runtime MUST maintain one local outstanding set keyed
by complete idempotency binding across every such worker. It acquires one
tentative slot before first dispatch, reuses that slot for exact retries, and
releases it only after a definite pre-admission rejection or authoritative
terminal reconciliation. Timeout, connection loss, or an ambiguous outcome
retains the slot; uncertain local slot state MUST NOT be treated as available.
These planning counters and slots neither duplicate application authority nor
prove that capacity is available. A declaration is not a Grant, an SLA, a
promise that the next request will succeed, or permission to exceed local
policy.
Application-authoritative adaptive, anti-abuse, or emergency controls MAY be
stricter without a surface-version change. They MUST NOT be represented as a
wider declared ceiling or used to expose another Grant, subscription, tenant,
or caller's occupancy. The standardized partition is a planning boundary, not
a promise that Grant rotation bypasses independent subject- or tenant-level
defenses.

A new Grant hash or event subscription intentionally starts a new standardized
partition. Neither the profile nor a capacity response authorizes creation,
renewal, exchange, or churn of those objects. An application that must preserve
anti-abuse or commercial quota across such lifecycle changes enforces a
separate server-selected lineage, subject, or tenant policy and reports no
cross-partition counts through ASP.

For an Action Request, the application validates current authority, session,
surface, schema, normalized input, and the complete idempotency binding before
a new operational admission. An exact completed replay returns the original
immutable result and receipt reference without consuming another window unit
or slot. An exact in-progress replay refers to the same record and slot; it does
not start a second effect. Conflicting reuse remains `idempotency_conflict` and
MUST NOT be hidden by `rate_limited`.

A fresh operational rejection occurs before a new idempotency record, budget
reservation or charge, app receipt, action effect, or application workload is
created. A runtime receipt already finalized before dispatch remains truthful
runtime evidence, but the application MUST NOT fabricate an app action receipt
for a request it never semantically admitted. Perimeter throttles for malformed,
unauthenticated, or abusive traffic are independent security controls and MUST
NOT use caller-provided identifiers to debit another authenticated partition.

When an event first delivery cannot be admitted, the application queues the
eligible immutable projection within the effective retention window. It does
not allocate a different delivery identity, advance the cursor silently, or
consume control-event capacity. Expiry before first delivery produces the
ordinary authenticated `event.gap`; an operational limit never converts
at-least-once delivery into silent loss.

Changing `operational_limits` changes the manifest hashing view and requires a
new `surface_version` and `surface_hash`. A Grant remains pinned to its retained
surface snapshot. A stricter current defensive throttle can deny work under an
older snapshot, but it does not rewrite the old Grant, become a Grant caveat, or
authorize use under a newer surface.

### CloudEvents 1.0.2 Event Binding

The ASP core event format is the CloudEvents 1.0.2 information model serialized
with the CloudEvents JSON Event Format 1.0.2. Every non-control and control event
delivered by this profile MUST be a valid CloudEvent with `specversion` equal to
the literal `1.0`. CloudEvents defines the interoperable occurrence envelope;
ASP continues to define grant authority, exposure, subscription, delivery,
acknowledgement, replay, and control-event semantics.

The core mapping is:

| ASP meaning | CloudEvents member | ASP requirement |
| --- | --- | --- |
| event identity | `id` | REQUIRED non-empty string; stable across retries and replay |
| application event source | `source` | REQUIRED absolute URI equal to the pinned manifest `issuer` in this core profile |
| manifest event id | `type` | REQUIRED exact match to one declared `events[].id` |
| CloudEvents version | `specversion` | REQUIRED literal `1.0` |
| occurrence time | `time` | REQUIRED RFC 3339 timestamp for the occurrence, not a retry or delivery time |
| declared event schema | `dataschema` | REQUIRED absolute URI exactly equal to the matched declaration's `schema` |
| payload media type | `datacontenttype` | REQUIRED literal `application/json` |
| authorized, redacted payload | `data` | REQUIRED JSON value conforming to `dataschema` |
| application resource key | `subject` | OPTIONAL non-empty string scoped by `source` and covered by exposure rules |

The core profile does not permit `data_base64`, CloudEvents batch mode, or a
non-JSON data content type. A future profile can add those representations only
with explicit schema, exposure, hashing, acknowledgement, and replay rules.
Omitting `datacontenttype` is valid in generic CloudEvents JSON, but is invalid
in ASP because an explicit media type prevents translation ambiguity.

The pair `(source, id)` identifies one immutable ASP event occurrence. The same
pair MUST carry the same `aspeventhash` wherever it is delivered. If
authorization, resource filtering, redaction, or another material member causes
two subscribers to receive different projections of one underlying application
occurrence, the application MUST assign distinct event ids. It MAY reuse one id
across subscriptions only when the complete occurrence hashing view is equal.

CloudEvents `id`, `source`, `type`, `subject`, and extension attributes are
descriptive context, not authority. A runtime still authenticates the channel,
subscription, grant or control binding, and current manifest before acting on
the event.

### ASP CloudEvents Extension Attributes

ASP defines the following CloudEvents 1.0 extension attributes. Their names use
the CloudEvents lower-case attribute namespace and their values use the
CloudEvents type system.

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `aspscope` | String | REQUIRED for non-control; absent for control | Exact scope from the matched manifest event declaration. |
| `aspcontrol` | Boolean | REQUIRED | `false` for grant-authorized application events; `true` only for a defined control event. |
| `aspsurfacehash` | String | REQUIRED | Exact pinned manifest hash used to interpret `type`, schema, scope, and exposure. |
| `aspeventhash` | String | REQUIRED | `asp-jcs-sha-256` hash of the immutable occurrence view. |
| `aspsubid` | String | REQUIRED on delivery | Bound Event Delivery subscription id. |
| `aspdeliveryid` | String | REQUIRED on delivery | Stable per-subscription delivery id. |
| `aspattempt` | Integer | REQUIRED on delivery | Positive transmission attempt, starting at `1` and increasing by one. |
| `aspstream` | String | REQUIRED on delivery | Ordering stream assigned by the application. |
| `aspsequence` | Integer | REQUIRED on delivery | Positive per-stream sequence from Event Delivery Semantics. |
| `aspcursor` | String | REQUIRED on delivery | Opaque replay position accompanying this delivery. |
| `aspaudience` | String | REQUIRED for control; absent for non-control | Authenticated runtime id targeted by the control event. |
| `aspsessionid` | String | conditional | Session correlation when the occurrence belongs to a specific ASP session. |
| `aspsessiongen` | Integer | conditional | Positive generation paired with `aspsessionid`. |

`aspsessionid` and `aspsessiongen` MUST appear together or both be absent. They
are correlation context and MUST match the authoritative session record when a
current session is required; they never resume or create a session. A control
event has `aspcontrol: true`, omits `aspscope`, and carries `aspaudience`. A
non-control event has `aspcontrol: false`, carries `aspscope`, and omits
`aspaudience`. Null does not satisfy any ASP-required attribute.

Every ASP Integer extension MUST be in the CloudEvents signed 32-bit range and,
where defined as positive, between `1` and `2147483647` inclusive. Before an
attempt, stream sequence, or session generation would overflow, the authority
MUST end the affected delivery, subscription, or session and allocate a new
identifier. It MUST NOT wrap or reset the value under the same identifier.

When observability context is present, the event uses the standard CloudEvents
Distributed Tracing `traceparent` and optional `tracestate` extension
attributes. It MUST NOT define duplicate `asptraceid` or `aspspanid`
projections. Trace attributes remain diagnostic and never participate in grant,
session, subscription, or delivery authority.

To compute `aspeventhash`, the producer applies the Canonical Object Hash
Profile to the complete CloudEvent while omitting `aspeventhash`, the
delivery-only attributes `aspsubid`, `aspdeliveryid`, `aspattempt`, `aspstream`,
`aspsequence`, and `aspcursor`, and the diagnostic `traceparent` and
`tracestate` attributes. All other core and extension attributes and the
complete `data` value are included. The consumer MUST recompute the hash before
acknowledging the event as processed.

Only the authenticated application delivery authority may set or change the
excluded delivery attributes, and the receiver still validates them against
subscription state. An intermediary may handle the excluded diagnostic
attributes only as permitted by the CloudEvents Distributed Tracing extension.
Adding, removing, or changing any other member requires a new `id` and
recomputed `aspeventhash`; otherwise the result is an integrity failure.
Unknown extension attributes are never interpreted as ASP authority and MUST
NOT substitute for a required ASP attribute.

### Serialization and Transport Mapping

An HTTP event endpoint conforming to this profile MUST support CloudEvents JSON
structured content mode. Its request or delivery body is the complete
CloudEvent JSON object and its media type is `application/cloudevents+json`.
Transport authentication, Grant Credentials, proof-of-possession, and
acknowledgement responses remain outside the CloudEvent body.

The Runtime Bridge JSON binding carries the same object as the complete
`payload` of the `event.delivery` frame:

```json
{
  "type": "event.delivery",
  "payload": {
    "specversion": "1.0",
    "id": "evt_01J2FAILED",
    "source": "https://code.example.com",
    "type": "ci.failed",
    "time": "2026-06-25T16:20:00Z",
    "subject": "example-org/example-repo/pull/13",
    "datacontenttype": "application/json",
    "dataschema": "https://code.example.com/schemas/ci-failed.event.schema.json",
    "aspscope": "pull_request.read",
    "aspcontrol": false,
    "aspsurfacehash": "sha-256:<base64url-digest>",
    "aspeventhash": "sha-256:<event-digest>",
    "aspsubid": "sub_01J2EVENTS",
    "aspdeliveryid": "delivery_01J2FAILED",
    "aspattempt": 1,
    "aspstream": "repository:example-org/example-repo",
    "aspsequence": 42,
    "aspcursor": "opaque:position-after-42",
    "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    "data": {
      "repository": "example-org/example-repo",
      "pull_request": 13,
      "check": "tests"
    }
  }
}
```

The frame type is Runtime Bridge routing metadata; `payload` itself is the
CloudEvent. A direct HTTP structured delivery sends that payload without the
outer frame. Both forms have identical ASP event and delivery semantics, and an
acknowledgement repeats the values of `aspsubid`, `aspdeliveryid`, and
`aspcursor` as `subscription_id`, `delivery_id`, and `cursor`.

CloudEvents HTTP binary content mode and JSON batch mode are outside the core
ASP binding. An implementation MUST NOT silently translate a structured ASP
event into either form unless a future negotiated profile defines lossless
placement of all required attributes and per-delivery acknowledgement state.

### Binding Validation and Security

Before accepting or acknowledging an ASP CloudEvent, a runtime MUST:

1. reject duplicate JSON members and validate the CloudEvents 1.0 required
   attributes, JSON types, and structured-format rules;
2. require the ASP core members and extension-presence combinations above;
3. require `source` to equal the authenticated pinned manifest issuer and
   `type`, `dataschema`, `aspscope`, and `aspcontrol` to match exactly one event
   declaration;
4. for a non-control event, require `aspsurfacehash` and all delivery attributes
   to match the authenticated grant-bound subscription; for a control event,
   require the delivery attributes to match the issuer/runtime-bound control
   record, then validate `aspsurfacehash` independently against the retained
   affected Grant and manifest snapshot under that event's rules;
5. validate `data` against the exact declared schema, apply the complete
   current grant and resource-filter projection for non-control events, and
   enforce the Data Exposure Contract over `data` and every context attribute
   that contains application, user, tenant, or resource semantics;
6. recompute `aspeventhash`, enforce one hash per `(source, id)`, and apply
   delivery deduplication before exposing the event to an agent.

A malformed CloudEvent or ASP extension combination fails as `schema_invalid`.
A supplied event hash, surface hash, issuer, or immutable binding mismatch fails
as `integrity_mismatch`. Reuse of `(source, id)` with a different valid event
hash, or reuse of `aspdeliveryid` with different source, id, event hash, stream,
sequence, or cursor, fails as `event_delivery_conflict`. None of these failures
MAY fall back to trusting the event payload, a cursor, or a transport header as
authority.

For a direct single-hop HTTP delivery, CloudEvents `traceparent` and
`tracestate`, when present, MUST carry the same trace information as their HTTP
header counterparts. A mismatch makes the tracing binding `schema_invalid`; it
does not select alternate authorization state. On a multi-hop path the
CloudEvents attributes preserve the starting event trace while protocol headers
describe the current hop, as defined by the CloudEvents Distributed Tracing
extension.

Context attributes can disclose data even when `data` is minimal. The
application MUST apply declared redaction before placing semantic values in
`subject`, application-defined extensions, tracing attributes, or other
occurrence metadata, and MUST declare every disclosed data class. Required ASP
delivery metadata MUST be opaque or minimally identifying and remains subject
to the same access-control and retention boundary even when it adds no event
data class. CloudEvents compatibility never permits an intermediary to route an
event to a runtime, agent, subject, or grant that ASP would not authorize.

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
- the pinned Operational Limits Profile entries for every accepted event type,
  when the manifest declares them

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
    "passport_hash": "sha-256:<base64url-digest>",
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
    "passport_hash": "sha-256:<base64url-digest>",
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
Every transmission of the same delivery increments the CloudEvents
`aspattempt` value by one but preserves `aspsubid`, `aspdeliveryid`, the
occurrence view and `aspeventhash`, `aspstream`, `aspsequence`, and `aspcursor`.
The canonical Runtime Bridge representation is shown in Serialization and
Transport Mapping.

While the subscription is active and the delivery remains inside its effective
retention window, the application MUST retransmit an unacknowledged delivery
after the acknowledgement deadline. Retries SHOULD use bounded backoff and
MUST NOT change the event projection to include newly available data. If
current authorization or redaction policy can no longer permit the immutable
projection, the application expires that delivery rather than sending a
different object under the same `delivery_id`.

An operational first-delivery window is checked before the first transmission
of a new `delivery_id`. Once admitted, every retry and replay keeps that same
logical admission and consumes no additional first-delivery unit. It still
occupies the same negotiated in-flight slot until terminal acknowledgement.
Thus loss of an acknowledgement cannot multiply either operational admissions
or slots, and a runtime cannot obtain more event authority by reconnecting.

The runtime MUST deduplicate on `(aspsubid, aspdeliveryid)` and retain
enough identity state to distinguish a retry from a conflicting reuse. Seeing
the same delivery id with a different `(source, id)`, `aspeventhash`, stream,
sequence, or cursor is `event_delivery_conflict`; the runtime MUST NOT process
either version as a new occurrence and MUST resynchronize. Duplicate delivery
can still happen after a crash or loss of local deduplication state, so this
profile does not provide exactly-once processing. Any Action Request triggered
by an event remains subject to the action's independent authorization,
idempotency, session, and effect rules.

The runtime MUST complete that validation and durable delivery-deduplication
decision before it allocates an automation root, advances a runaway-guard
counter, or schedules an agent, model, tool, or action. A valid new application
non-control event root is identified by
`(aspsubid, source, id, aspeventhash)`. A core control event never becomes an
automation root. A transport retry or replay of a non-control occurrence reuses
the same root and MUST NOT create another causal branch merely because
`aspattempt`, arrival time, or transport connection changed.

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
or an application action succeeded. `discarded` MUST NOT be used for a valid
core control event before the runtime durably applies its required fail-closed,
scheduling, or reconciliation state. Such an event is normally acknowledged as
`processed` only after that state and its deduplication decision are durable.

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
stream, sequence, and cursor; `aspattempt` increments for another transmission.
The runtime applies ordinary deduplication and acknowledgement rules. Replay
does not reactivate an interrupted or terminal ASP session, and receiving an
event does not authorize a session transition.

Replay also MUST NOT reset a runtime runaway-guard epoch, causal-depth counter,
cycle history, or action-repetition state. The validated root-event reference
above is causal identity for this purpose; `trace_id`, arrival order, a new
connection, or a receipt parent link MUST NOT be substituted for it.

The online `event.replay` operation is distinct from the Portable Replay
Bundle Profile. An online replay remains an authenticated subscription
operation governed by the cursor, retention, deduplication, acknowledgement,
and flow-control rules in this section. A portable bundle is passive historical
evidence and MUST NOT be submitted as an `event.replay` request, used as a
cursor, or interpreted as authority to acknowledge or redeliver an event.

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

When the negotiated in-flight window is full, or an applicable operational
first-delivery window has no capacity, the application queues eligible events
within the effective retention window rather than exceeding either limit. If
an event expires before first delivery, the next delivery or replay response
MUST carry an `event.gap`; silent loss is forbidden. Implementations SHOULD
expose bounded metrics for queued, in-flight, operationally delayed, retried,
expired, and gap states without including event payloads.

Application-event backpressure MUST NOT starve the runtime control
subscription. The application MUST reserve independent capacity for
core control events or deliver them on a separate authenticated channel. If the
control path is unavailable, application-side revocation, budget state, and
session fences remain immediately authoritative; the runtime MUST stop affected
new use when it cannot re-establish or introspect authoritative state rather
than assuming that the absence of a control event means capacity or authority
still exists.

### Budget Control Events

`budget.warning`, `budget.exceeded`, and `session.paused_budget` are
application-authored control notifications. They use the logically separate
control subscription, carry `aspcontrol: true` and `aspaudience`, omit
`aspscope`, and satisfy every CloudEvents binding, integrity, exposure,
delivery, replay, and acknowledgement rule above. The affected grant does not
authorize their delivery, but their payload MUST identify only a grant and
delegate tuple already known to the target runtime.

When an application publishes `event_subscription_url` and accepts an
application-authoritative budget, its manifest MUST declare
`budget.exceeded`; it MUST also declare `budget.warning` when it configures a
warning threshold. Independently, an application with
`event_subscription_url` MUST declare `session.paused_budget` when application
policy can interrupt a session for a budget condition or the application
accepts `session.pause` with reason `budget_exceeded`. Accepting only the
`runaway_guard` variant does not require or permit that budget event. Absence or
failure of the control channel never delays the underlying counter or session
transition; delivery is notification, not authority.

An application MUST emit `budget.warning` and `budget.exceeded` only for
application-authoritative `write_actions`, `parallel_sessions`, and
`application_cost` counters. It MUST NOT copy or estimate runtime-authoritative
tool, token, time, or runtime-cost state into an application CloudEvent. A
runtime observes those counters locally and uses the authenticated
`session.pause` operation below when its own budget state requires an
application session fence.

The event-producing state machines are:

```text
consumptive: absent -> available <-> warning <-> exhausted
                            \-----------------> exhausted
occupancy:   absent -> available <-> saturated
session:                active  -> interrupted
```

Every authoritative counter transition occurs whether or not event delivery is
configured. After a local or ancestor transition, the application recomputes
effective lineage state and retryability separately for each affected grant.
When the corresponding event is declared, `budget.warning` is produced exactly
when that effective consumptive state enters `warning`, and `budget.exceeded`
is produced exactly when effective state enters `exhausted` or `saturated`.
`budget.exceeded` is also produced when effective retryability changes while
state remains exhausted or saturated. A counter transition that an already
stricter ledger masks produces no occurrence and no effective state revision
for that affected grant.

Creation directly in a non-available effective state counts as entry from
`absent`, and a transition MAY skip `warning`. The name `budget.exceeded`
reports that no further matching admission currently fits; it does not mean the
hard limit was overdrawn. Because `remaining` includes durable reservations,
releasing unused capacity can move a consumptive counter back to `warning` or
`available`; settled `used` never decreases. Repeated denied attempts without
an effective change MUST NOT create more events.

For each event-producing transition and affected delegate, the application
creates exactly one immutable occurrence with a distinct CloudEvents `id`.
Delivery retry and replay preserve its `(source, id)`, `aspeventhash`, and
stable data; they MUST NOT produce another counter transition, session
transition, charge, or receipt. `effective_at` is the authoritative counter
transition time, `observed_at` is when the immutable event projection was
recorded, and CloudEvents `time` MUST equal `observed_at`.

The application MUST commit the authoritative transition record and a durable
outbox record containing the stable occurrence key and immutable redacted
projection atomically, or with an equivalent recoverable transaction, before it
acknowledges the transition-causing operation or session fence. A crash after
the transition but before network delivery resumes the same occurrence from
that outbox; it MUST NOT omit the event, reconstruct it from later mutable
state, or allocate a second event id. Network delivery remains the independent
at-least-once process defined above.

For each `(affected_grant_hash, budget_id)`, the application maintains a
positive safe-integer `effective_state_revision`, starting at `1` and
increasing by exactly one whenever effective state or effective retryability
changes. It is scoped to the target grant and reveals no ancestor ledger
revision. Every `budget.warning` and `budget.exceeded` occurrence and every
`budget.state` response carries it so a delayed event cannot overwrite a newer
query result. Overflow fails closed as `budget_state_unavailable`; the revision
MUST NOT wrap or reset under the same affected grant and budget id.

The runtime durably retains the highest effective revision seen across budget
events and query responses. A lower revision is historical and cannot change
current scheduling. An equal revision with different effective state or
retryability is `integrity_mismatch` and fails closed; projection detail MAY
differ because an event can contain a complete local counter while
`budget.state` is always lineage-minimized.

This is a minimum `budget.exceeded` delivery:

```json
{
  "specversion": "1.0",
  "id": "event_01J2BUDGET",
  "source": "https://code.example.com",
  "type": "budget.exceeded",
  "time": "2026-06-25T18:20:00Z",
  "datacontenttype": "application/json",
  "dataschema": "https://code.example.com/schemas/budget-exceeded.event.schema.json",
  "aspcontrol": true,
  "aspaudience": "application_runtime_456",
  "aspsurfacehash": "sha-256:<base64url-digest>",
  "aspeventhash": "sha-256:<event-digest>",
  "aspsubid": "control_application_runtime_456",
  "aspdeliveryid": "delivery_01J2BUDGET",
  "aspattempt": 1,
  "aspstream": "grant:grant_123",
  "aspsequence": 7,
  "aspcursor": "opaque:control-position-after-7",
  "data": {
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "app_id": "code.example.com",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_hash": "sha-256:<base64url-digest>",
    "previous_state": "warning",
    "effective_state_revision": 3,
    "budget": {
      "budget_id": "write_actions",
      "authority": "application",
      "scope": "grant",
      "mode": "consumptive",
      "unit": "actions",
      "limit": 20,
      "used": 19,
      "reserved": 1,
      "remaining": 0,
      "state": "exhausted",
      "warning_at_remaining": 2,
      "revision": 42
    },
    "effective_at": "2026-06-25T18:19:59Z",
    "observed_at": "2026-06-25T18:20:00Z",
    "retryable": true
  }
}
```

Both budget event payloads MUST contain `grant_id`, `grant_hash`, `app_id`,
`runtime_id`, `agent_id`, `passport_hash`, `previous_state`, `budget`,
`effective_state_revision`, `effective_at`, and `observed_at`. The grant and
complete tuple identify the affected grant bound to the target delegate; they
are not part of the grant-agnostic control-subscription authority. The delivery
channel, `source`, `aspaudience`, and `aspsubid` MUST match the control
subscription's application issuer and authenticated target runtime, and
`data.runtime_id` MUST equal `aspaudience`. Independently, the runtime MUST
match the complete payload tuple and `aspsurfacehash` against its retained
authoritative Grant and pinned manifest snapshot. `budget_id` MUST name an
application-authoritative dimension retained in that grant.

When the transitioned counter belongs to the affected grant and its complete
local state and retryability equal the effective lineage result, `budget` MAY be
the complete canonical Budget Counter State with `scope: "grant"`, as shown
above. Otherwise, including when an ancestor or stricter local/ancestor counter
determines the effective result, the event MUST use this minimized projection:

```json
{
  "budget_id": "write_actions",
  "authority": "application",
  "scope": "effective_lineage",
  "mode": "consumptive",
  "unit": "actions",
  "state": "exhausted"
}
```

The minimized projection MUST omit ancestor grant identifiers and hashes,
`limit`, `used`, `reserved`, `remaining`, warning threshold, and ledger
revision. The authenticated application source is authoritative for the
effective application-owned state; the projection is not a reusable ledger
credential. When one ancestor transition affects grants bound to multiple
runtimes, the application emits a separately identified occurrence for each
affected grant and `aspaudience` and MUST NOT disclose ancestor or sibling
delegate identities or aggregate consumption.

The application computes both `previous_state` and the new state over the
complete lineage: consumptive `exhausted` dominates `warning`, which dominates
`available`, and occupancy `saturated` dominates `available`.
If multiple ledgers block admission, non-retryable settled-hard exhaustion
dominates a retryable reservation or occupancy blocker. An ancestor warning
MUST NOT make an already exhausted descendant appear to recover, and releasing
one blocker MUST NOT emit availability while another blocker remains.

For `budget.warning`, state MUST be consumptive `warning`, and a complete local
projection MUST carry `warning_at_remaining`; `previous_state` is `absent`,
`available`, or `exhausted`. For `budget.exceeded`, state MUST be consumptive
`exhausted` or occupancy `saturated`. Its `retryable` is REQUIRED. For a
complete consumptive projection it is `true` exactly when `reserved` is
positive and `used` is smaller than `limit`, and `false` for settled hard
exhaustion where `used` equals `limit` and `reserved` is zero. For a minimized
projection the application derives the same value without disclosing its
inputs. For occupancy saturation it is `true` only when every blocking
occupancy ledger has a positive limit and currently occupied or reserved
capacity that can be authoritatively released; a zero-slot limit is
non-retryable. A true value only says capacity can return after authoritative
reservation or slot release; the runtime still requires a fresher authenticated
`budget.state` before retry. The field never authorizes automatic retry or
reserves future capacity.

The runtime obtains that fresher state without exposing ancestor totals through
an authenticated control-plane query. It sends the complete typed envelope as
an `application/json` POST to the manifest `budget_state_url`, using the grant's
required credential-binding proof, or carries the identical message on an
already authenticated Runtime Bridge:

```json
{
  "type": "budget.query",
  "payload": {
    "query_id": "budget_query_01J2AVAILABLE",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "budget_id": "write_actions"
  }
}
```

Before consulting an idempotency record or returning state, the application
MUST authenticate the runtime and presented credential, resolve an active,
unexpired current grant, and match its subject, runtime, agent, passport,
credential binding, `grant_id`, `grant_hash`, and `surface_hash`. It MUST then
require `budget_id` to name an application-authoritative dimension retained by
that grant. Revocation, expiry, a superseded surface, or any mismatched or
unknown authority dominates an earlier cached response. Every failure of these
checks, including an unknown or runtime-authoritative `budget_id`, returns the
same terminal, non-enumerating `budget_query_invalid` error and no
`budget.state`; the response MUST NOT disclose which check failed. Only after
all checks pass does the application evaluate the local and every ancestor
ledger and return the effective admission state for that target grant:

```json
{
  "type": "budget.state",
  "payload": {
    "query_id": "budget_query_01J2AVAILABLE",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "budget": {
      "budget_id": "write_actions",
      "authority": "application",
      "scope": "effective_lineage",
      "mode": "consumptive",
      "unit": "actions",
      "state": "available"
    },
    "effective_state_revision": 4,
    "observed_at": "2026-06-25T18:21:00Z",
    "query_expires_at": "2026-06-25T18:26:00Z"
  }
}
```

For consumptive state, `exhausted` dominates `warning`, which dominates
`available`; for occupancy, `saturated` dominates `available`. When the
effective state is `exhausted` or `saturated`, the `budget` projection MUST also
carry `retryable`. It is `false` if any currently blocking consumptive ledger
is settled-hard and is `true` only when every blocker can recover through an
authoritative reservation or occupancy release. It is absent for `available`
or `warning`. The response MUST omit every ancestor identifier, hash, limit,
counter value, threshold, and revision. A runtime MUST allocate a `query_id`
unique for the lifetime of the target grant and MUST NOT deliberately reuse an
expired id. On first acceptance, the application binds the complete request to
its response through `query_expires_at`, computed from the manifest
`budget_query_retention_seconds`, and retains that full idempotency record until
the timestamp. After the current-authority checks above, it consults this record
before evaluating live ledger state. An exact duplicate received before expiry
therefore returns the immutable cached response and effective revision even if
the live ledger later becomes unavailable; the response remains only the
point-in-time observation it claims. A caller needing fresher state uses a new
id, whose evaluation fails as `budget_state_unavailable` when current ledger
state is missing or uncertain, never as synthetic availability.

At `query_expires_at`, the application MUST delete the cached state payload and
compact the record to `(query_id, request_hash, query_expires_at)` for one
additional `budget_query_retention_seconds` interval. Any exact or conflicting
reuse during that tombstone interval fails as the same terminal,
non-enumerating `budget_query_invalid` error with no state. After the tombstone
deadline the application MUST evict it; a later occurrence is processed as a
new query, but a conforming runtime never relies on that fallback. A conflicting
reuse before either deadline also fails as `budget_query_invalid`.
`request_hash` is the Canonical Object Hash Profile digest of the complete typed
`budget.query` envelope; it is local bookkeeping and is not inserted into that
envelope. The application MUST enforce finite per-grant
cardinality and authenticated-caller rate limits over live records and
tombstones; rejection at either bound returns `rate_limited` without allocating
a record. Because tombstones have a mandatory eviction deadline, reaching the
bound cannot permanently consume the grant's query namespace.

`budget.state` is point-in-time application authority, not a reservation. A
runtime MAY reconsider an unchanged operation after a response of `available`
or `warning`, subject to local policy and ordinary atomic admission at the
application. It MUST use bounded backoff for another query after a retryable
exhaustion or saturation, MUST stop same-grant recovery queries after a
non-retryable result, and MUST NOT query or retry from an agent-controlled loop.
`budget.query` and `budget.state` use the safety control plane, consume no grant
budget, require no active session, and MUST NOT be exposed to an agent.

Budget exhaustion does not itself interrupt a session. If application policy
chooses to fence an active session because of settled exhaustion of an
application-owned consumptive `write_actions` or `application_cost` counter,
the application MUST first atomically transition that session from `active` to
`interrupted`, without changing its generation, and, when the event is declared,
then emit exactly one `session.paused_budget` occurrence for that transition.
`parallel_sessions` saturation MUST NOT pause or cancel a session that already
owns a slot. A runtime-owned budget can cause an application transition only
through an accepted `session.pause` request. A duplicate pause request or event
delivery does not create a second transition or occurrence.

A `session.paused_budget` event MUST carry matching `aspsessionid` and
`aspsessiongen` attributes. This is the minimum data for the
controlling-runtime variant:

```json
{
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "budget_grant_id": "grant_123",
  "budget_grant_hash": "sha-256:<base64url-digest>",
  "app_id": "code.example.com",
  "runtime_id": "application_runtime_456",
  "agent_id": "local_agent_789",
  "passport_hash": "sha-256:<base64url-digest>",
  "pause_id": "pause_01J2BUDGET",
  "session_id": "sess_456",
  "session_generation": 1,
  "previous_state": "active",
  "state": "interrupted",
  "transition_reason": "budget_exceeded",
  "budget_id": "runtime_seconds",
  "budget_authority": "controlling_runtime",
  "budget_scope": "grant",
  "reported_budget_revision": 31,
  "effective_at": "2026-06-25T18:20:00Z",
  "observed_at": "2026-06-25T18:20:01Z",
  "automatic_resume": false
}
```

Every variant contains `grant_id`, `grant_hash`, `app_id`, `runtime_id`,
`agent_id`, `passport_hash`, `pause_id`, `session_id`, `session_generation`,
`previous_state`, `state`, `transition_reason`, `budget_id`,
`budget_authority`, `budget_scope`, `effective_at`, `observed_at`, and
`automatic_resume`. The event's session attributes, data, tuple, and hashes
MUST match the authoritative interrupted record. `budget_authority` is
`application` or `controlling_runtime`; `budget_scope` is `grant` or
`ancestor`. For a local application-owned counter, `budget_scope` is `grant`,
`budget_revision` is REQUIRED, and all `budget_grant_*` and
`reported_budget_revision` members are absent. For an ancestor application-owned
counter, `budget_scope` is `ancestor` and every causal ancestor identifier,
hash, counter value, and revision MUST be omitted. The application remains
authoritative for the effective fence without exposing aggregate lineage state.

For a runtime-owned counter, `budget_grant_id` and `budget_grant_hash` MUST
identify the session grant or an ancestor containing `budget_id`,
`budget_scope` reflects which, and `reported_budget_revision` MUST repeat the
causal grant and revision from the accepted pause request. `budget_revision`
is absent, and the application MUST NOT represent that runtime report as its
own counter state. `automatic_resume` is the literal `false`: only an explicit,
independently authorized resume after the budget condition is resolved can
return the session to `active`.
`effective_at` records the authoritative fence, `observed_at` and CloudEvents
`time` record the immutable event projection, and an application-initiated
fence MUST allocate a `pause_id` unique in that session generation.

The runtime MUST validate and durably deduplicate a budget control occurrence
before changing local scheduling. Channel authentication proves only the
application issuer and target runtime. If no locally retained authoritative
Grant matches the event's complete affected tuple, the runtime MUST apply one
non-enumerating unknown-authority disposition, accept no payload state, and
MUST NOT disclose whether the tuple was unknown, ended, or outside local
authority. If `grant_id` resolves locally but any delegate member,
`grant_hash`, or `aspsurfacehash` differs, the runtime MUST stop scheduling on
the affected local grant, record `integrity_mismatch`, and begin authoritative
grant and manifest resynchronization without replacing retained authority from
the event. The control-delivery acknowledgement MUST NOT echo the mismatched
value or distinguish which binding failed.

After those checks, the runtime MUST NOT deliver any core control event to an
agent as a task, treat it as authority for an Action Request, automatically
retry denied work, or infer that pausing rolled back an in-flight effect. A
`budget.warning` or `budget.exceeded` occurrence MUST NOT replace a newer
effective state revision with an older event or query result. A valid duplicate
or older effective revision receives a terminal `processed` acknowledgement
without repeating local side effects. For `session.paused_budget`, the runtime
stops matching local scheduling and reconciles in-flight outcomes before
terminal acknowledgement. A historical pause replay for an older session
generation MUST NOT interrupt or downgrade a later generation; the runtime
validates it against retained transition history and acknowledges it without
changing current session state.

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

For a core control event, `transient` applies to the raw CloudEvent and its
application-originated payload; it does not prohibit the receiver from durably
projecting the minimum safety state that this protocol requires before terminal
acknowledgement. That projection MUST be data-minimized and limited to delivery
deduplication keys or hashes, the affected-grant hash, effective state revision,
state and retryability, and the session id, generation, and fence state when
applicable. It MUST NOT retain raw event data, ancestor identifiers, counter
values, thresholds, or unrelated session metadata. The receiver MUST retain
deduplication state through the effective replay window and safety state while
the affected grant or session can still admit or resume work. Once both the
effective replay window is closed and the affected authority can no longer
admit or resume work, the receiver MUST delete that projection; only a
non-reversible tombstone permitted by an independently declared bounded audit
policy MAY remain.

The resource contract applies to every representation and query result of that
resource. The action contract applies to all application-originated
agent-visible output from that action, including dry-run or proposal output,
success responses, partial results, and structured error details. It does not
describe application retention of agent-supplied action input. The event
contract applies to its payload. Core control events MUST also appear in the
manifest `events` array with `control: true` and an exposure contract; they
cannot bypass these rules merely because their delivery authority is
independent of the affected grant.

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
4. include every core control event advertised with `control: true`, regardless
   of the affected grant's scopes.

The conservative resource and event rules may display a class that a narrower
resource filter never returns, but they MUST NOT omit a class that remains
reachable. An unknown `control: true` event makes the surface incompatible with
this profile unless another negotiated profile defines its closure rule.
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

When the Remote Processing Privacy Profile is selected, the complete projection
is also the input to its Grant-wide classification-ceiling check. Every class
is evaluated at its pinned manifest classification; a processor path MUST NOT
drop a source or class, reinterpret a mixed-class payload, or rely on a
runtime-only redaction to fit the ceiling. A whole action or scope subset can be
approved only after the authorization server recomputes this source closure.

When the Agent Training Use Policy Profile is selected, the union of class
identifiers in this same complete projection bounds its `permitted_classes`.
The profile does not add a field-level classifier: a complete payload from one
source is eligible for training use only when every class in that source entry
is permitted. A runtime MUST NOT extract an allegedly lower-class field from a
mixed-class payload by inference; the application must publish a separately
redacted source contract when that distinction is required.

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
an `idempotency_normalization` object using `asp-json-normalization-v1`,
`receipt: "required"`, a non-empty `effects` array,
`input_hash_profile: "asp-jcs-sha-256"`, and
`execution_hash_profile: "asp-jcs-sha-256"`. Persisted proposals remain
non-committed domain artifacts but MUST support idempotency as specified in
Proposal-Only Surface Mode.

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
  "idempotency_normalization": {
    "profile": "asp-json-normalization-v1"
  },
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
  "input_schema_hash": "sha-256:<input-schema-digest>",
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
  "idempotency_normalization": {
    "profile": "asp-json-normalization-v1"
  },
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
  "input_schema_hash": "sha-256:<input-schema-digest>",
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

An Impact Simulation is not a dry run. It copies only the static maximum effect
envelope for a known action and MUST NOT call the application, carry action
input, create a preview token, or claim application-observed preconditions or
`expected_effects`.

A commit that declares `dry_run_action` MUST declare both
`preconditions_schema` and `expected_effects_schema`. Those two members MUST be
absent when no dry-run action is linked; a direct commit expresses ordinary
optimistic-concurrency fields through its `input_schema`. A state-changing
action MAY declare `actual_effects_schema` to further constrain the mandatory
core Effect Model. A linked dry-run action MUST set
`input_hash_profile: "asp-jcs-sha-256"`, use the same `input_schema` as its
target commit, repeat the same `input_schema_hash` and structurally identical
`idempotency_normalization` declaration, and identify that commit through
`execution.commit_action`. The runtime MUST apply that declaration before
requesting approval, hashing, or sending the dry run, and the application MUST
perform the same fixed-point check. The dry run MUST NOT change target-domain
or coordination state.

The dry-run request MUST carry `input_hash`, and the application MUST recompute
it from the exact validated wire input. A preview-bound commit MUST present the
same exact normalized input and matching `input_hash`. A mismatched
normalization declaration is an invalid companion relationship; schema
equivalence or post-preview application normalization does not make a different
wire input the previewed input.

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
  "idempotency_normalization": {
    "profile": "asp-json-normalization-v1"
  },
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
  "input_schema_hash": "sha-256:<input-schema-digest>",
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

Applications MAY define extension risk labels, but each extension label MUST be
a collision-resistant URI whose specification defines a conservative mapping
to one standard risk label as its minimum severity. A runtime that does not
support that exact mapping MUST reject the surface or action as
`surface_incompatible`; it MUST NOT infer severity from a human-readable
description, identifier spelling, icon, or local similarity rule. A bare
unrecognized label is invalid.

Impact Simulation uses this same conservative mapping only to select the
bounded set of unrequested examples. It MUST NOT change an action's risk,
downgrade an extension, or use the selection order as a safety or authority
ranking.

### Risk Explanation UI Hints

This draft assigns the following core feature identifier:

```text
agent-surface/feature/risk-explanation-ui-hints
```

The identifier names the optional manifest and conformance feature defined in
this section. It is not a negotiated profile, Grant constraint, consent
artifact, approval mode, or authority-bearing capability. Presence is declared
only by a valid `risk_explanation` member on an action; absence means that the
publisher supplies no standardized prose for that action and MUST NOT be
rendered as no risk.

An action MAY contain one `risk_explanation` object:

```json
{
  "default_language": "en",
  "localizations": [
    {
      "language": "en",
      "summary": "Publishes a review for other repository users.",
      "effect_summaries": [
        {
          "effect_id": "review-publish",
          "summary": "Creates an irreversible shared communication record."
        }
      ]
    }
  ]
}
```

The `risk_explanation` object, every localization, and every effect summary are
closed objects. `default_language` and `localizations` are REQUIRED and no
other member is allowed. A localization contains exactly `language`, `summary`,
and `effect_summaries`; an effect summary contains exactly `effect_id` and
`summary`. A Surface Publisher MUST NOT publish a present object that violates
this section. A consumer that nevertheless receives one MUST atomically
suppress the complete hint and use its machine-derived risk and effect
presentation; it MUST NOT display or otherwise interpret only the fields it
recognizes. Suppression does not turn malformed prose into authority and MUST
NOT be rendered as no risk.

`localizations` contains between one and sixteen entries. `default_language`
and every `language` are canonical lowercase ASCII language tags no longer than
63 characters and MUST match this complete regular expression:

```text
^[a-z]{2,8}(?:-[a-z]{4})?(?:-(?:[a-z]{2}|[0-9]{3}))?(?:-(?:[a-z0-9]{5,8}|[0-9][a-z0-9]{3}))*$
```

This is the ASP-canonical lowercase wire form for a deliberately restricted,
structurally well-formed subset of RFC 5646: a language subtag, optional
script, optional region, and zero or more variants. It intentionally excludes
extlang, extension, private-use, and grandfathered forms and does not claim
registry-based canonicalization. Variant subtags within one value MUST be
unique. Localization entries are unique by `language` and sorted by unsigned
lexicographic order of their ASCII bytes. Exactly one entry MUST have a
`language` equal to `default_language`.

Every `summary` is plain text containing between one and 512 Unicode code
points. It MUST NOT contain a C0 or C1 control character or any Unicode
`Bidi_Control` character: U+061C, U+200E, U+200F, U+202A through U+202E, or
U+2066 through U+2069. A presenter MUST treat it as inert text, escape it for
the output context, and place each string inside a presentation-controlled
bidirectional-isolation boundary. It MUST NOT interpret the string as HTML,
Markdown, a URI, a template, executable content, a policy rule, or an
instruction. The strings MUST be safe for every user allowed to discover that
manifest and MUST NOT contain credentials, secrets, hidden policy content, or
instance-specific resource data.

For each localization, `effect_summaries` contains exactly one entry for every
member of the parent action's `effects` array, with the same `effect_id` values
in the same declaration order. An action that omits `effects` has an empty
`effect_summaries` array in every localization. An unknown, missing, duplicate,
reordered, or extra effect id is invalid. Complete per-language coverage
prevents a publisher from omitting a less favorable effect only in one
localization; the prose still does not replace the Effect Model declaration.

A Runtime Mediator that claims this feature chooses one complete localization
using RFC 4647 Lookup against zero to sixteen ordered local language
preferences. Each preference uses the same ASP-canonical language form;
duplicates have no additional effect. When the list is empty or Lookup finds no
available tag, the runtime uses the exact `default_language` entry. It MUST NOT
combine a summary from one localization with effect summaries from another. A
locally generated translation is runtime-authored content and MUST be labeled
separately; it MUST NOT be represented as publisher text.

Risk explanation text is an untrusted publisher hint. The publisher MUST NOT
describe a lower risk, narrower effect, stronger recovery guarantee, weaker
approval requirement, or more certain outcome than the machine-readable action
contract. Regardless of prose, a user-facing runtime MUST keep the canonical
action id, standard risk label or supported extension mapping, execution mode,
approval mode, and every material effect and recovery limitation visible and
distinguishable as machine-derived semantics. It MUST NOT use the prose to
change capability-match status or ranking, local or enterprise policy,
approval, admission, scope, effect validation, or receipt production. It MUST
NOT place publisher prose in an agent system prompt, tool instruction, or other
privileged instruction channel.

The complete object is part of the manifest hashing view and needs no separate
hint hash. A runtime retrieves it only from the exact verified manifest
snapshot and keys any extracted display cache by (`issuer`, `app_id`,
`surface_version`, `surface_hash`, action id, selected language). It MUST NOT
accept a detached caller- or agent-supplied copy as publisher text. Any change
to a hint changes `surface_hash` and `surface_version` and makes an in-progress
Consent Preview or Human Elicitation bound to the former snapshot stale.
Existing Grants remain bound to their exact retained snapshot; a new hint MUST
NOT be overlaid on an old Grant or used to reinterpret its action.

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

The `maximum_effects` member of an Impact Simulation example is instead an
exact copy of this manifest envelope. It contains no resource keys or
input-specific prediction and MUST NOT be presented as an `expected_effects`
array, dry-run result, or guarantee of the actual outcome.

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

An action's Risk Explanation UI Hint can accompany an approval presentation
only as labeled application-authored prose from the exact pinned manifest. It
MUST NOT satisfy an approval mode, alter the required producer roles, replace
the canonical risk or effect presentation, or become part of the approval
decision binding except through the already required `surface_hash`. A stale or
detached hint is discarded. Approval evidence for an old Grant remains
interpreted under that Grant's retained snapshot; a new snapshot follows the
ordinary fresh preview, policy, and approval rules and does not rewrite the old
evidence.

An Impact Simulation outcome is likewise not invocation approval. A
`covered` example MUST NOT satisfy an approval mode, create approval evidence,
or be included in an approval binding. Consent confirmation authorizes only the
subsequent Grant request; every invocation continues to require its exact
policy decision and approval evidence.

Approval records SHOULD be linked into action receipts. The base profile permits
an opaque approval reference. A Grant selecting the Approval Receipt Profile
instead uses the complete hash-bound, role-indexed evidence defined below.

The `runtime` and `user_or_app` modes allow a runtime-side approval to satisfy
the requirement. In those modes the application is accepting the runtime's
assertion that a local user approval occurred. To keep this compatible with
the rule that an application MUST NOT accept a runtime's self-assertion of
authority, that acceptance MUST be an explicit grant caveat presented to the
user at consent time, not a silent default. Action requests that rely on a
runtime-side approval SHOULD carry an approval reference so the decision can be
linked into receipts and audited. Under the Approval Receipt Profile, the
Grant's per-action rule MUST explicitly accept the `runtime` producer role and
the request MUST carry the verified runtime Approval Receipt hash. Applications
that do not want to accept runtime approval assertions MUST declare `app` or
`runtime_and_app` for the affected actions or issue a `user_or_app` Grant rule
that accepts only `application`.

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
`approval_denied`, `scope_denied`, `resource_denied`, `binding_invalid`,
`limit_exceeded`, `local_policy_denied`, and `app_policy_denied`. Extensions
MUST use a collision-resistant URI. `matched_rules` contains stable, non-secret
rule identifiers and MAY be empty when disclosure would reveal policy
internals.
`safe_to_show` MUST be suitable for display to the affected user and MUST NOT
contain secrets, credentials, hidden rule content, or sensitive resource data.

The standard reason codes are valid only with these outcomes:

| Outcome | Allowed standard reason codes |
| --- | --- |
| `allow` | `policy_allowed`, `approval_satisfied` |
| `require_approval` | `approval_required` |
| `deny` | `approval_denied`, `scope_denied`, `resource_denied`, `binding_invalid`, `limit_exceeded`, `local_policy_denied`, `app_policy_denied` |

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
Proposal-Only Surface Mode.

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

### Idempotency Input Normalization

Every action with `idempotency: "required"` MUST publish a manifest-pinned
normalization declaration. This draft defines one profile:

```json
{
  "profile": "asp-json-normalization-v1",
  "defaults": {
    "/notify_subscribers": false
  },
  "unordered_arrays": ["/labels"]
}
```

`defaults` is an optional object whose member names are RFC 6901 JSON Pointers
and whose values are literal I-JSON defaults. `unordered_arrays` is an optional
array of unique RFC 6901 JSON Pointers. An omitted member has the same meaning
as an empty object or array. The v1 declaration contains exactly `profile` and
those two optional members; an unknown member invalidates the action rather
than being ignored as a transform. The declaration is part of the manifest
hashing view; changing a rule requires a new `surface_version` and
`surface_hash`.

The `asp-json-normalization-v1` algorithm is:

1. Parse the action input as I-JSON and validate it against the exact pinned
   `input_schema` without coercion, default insertion, or member removal.
2. Deep-copy that JSON value. Process default pointers by increasing pointer
   depth and then unsigned lexicographic order of their UTF-8 pointer bytes. A
   pointer MUST traverse object members only and name an object member. When
   its parent exists and the member is absent, insert the declared literal
   value. An explicit `null` is present and MUST NOT be replaced. An absent
   parent is unchanged. A present non-object ancestor contradicts the
   declaration and makes the action surface incompatible.
3. Process `unordered_arrays` pointers in unsigned lexicographic order of their
   UTF-8 bytes. A present target MUST be an array. Serialize each element
   independently with RFC 8785 JCS and sort the elements by unsigned
   lexicographic order of those canonical UTF-8 bytes. Preserve duplicate
   elements; an action requiring uniqueness MUST express it in `input_schema`.
   A present non-array target contradicts the declaration and makes the action
   surface incompatible.
4. Validate the resulting value against the same `input_schema` again.
5. Compare the result with the received JSON data model, ignoring only object
   member serialization order. The application MUST reject a non-fixed-point
   value as `input_not_normalized` before idempotency lookup, budget admission,
   policy approval, receipt creation, or any effect. It MUST NOT silently
   replace the received input.

A surface is invalid when a pointer is malformed, traverses an array, a default
pointer is an ancestor of another default pointer, a default pointer descends
through an unordered array, or applying its declarations can produce a value
that violates the pinned input schema. The schema MUST guarantee that every
present ancestor traversed by a default pointer is an object and every present
`unordered_arrays` target is an array; admitting `null`, a scalar, or another
type at those positions is an invalid action declaration. An
unordered-array rule is valid only when element order cannot change validation,
authorization, approval, target selection, or effects. A default is valid only
when application behavior for omission is exactly the behavior of the declared
literal. A contradiction discovered while loading or processing the pinned
surface fails as `surface_incompatible` before lookup, budget admission, or
effect; an implementation MUST NOT ignore the offending rule. Publishers MUST
NOT use these rules to hide a material choice from consent or approval.

The profile performs no trimming, case folding, Unicode normalization, URI or
timestamp normalization, numeric-string coercion, member removal, array
deduplication, or implicit use of JSON Schema `default` annotations. Absent and
explicit `null` remain distinct. Future profiles that add transforms MUST use a
collision-resistant URI identifier and define deterministic validation,
ordering, and fixed-point rules. A runtime MUST reject an unsupported profile
as `surface_incompatible` rather than approximate it.

The runtime MUST normalize before deriving approval input, computing
`input_hash`, producing its receipt, or transmitting the Action Request. Every
idempotency-required Action Request MUST carry that `input_hash`, including a
persisted proposal request. The
application independently recomputes the fixed point before trusting the hash
or consulting an idempotency record. For example, declarations for a default
`/notify_subscribers: false` and unordered `/labels` make these caller inputs
equivalent:

```json
{"body":"x","labels":["urgent","bug"]}
```

```json
{"body":"x","labels":["bug","urgent"],"notify_subscribers":false}
```

Both are sent on the wire in the second fixed-point form. The existing
`input_hash` therefore commits to the normalized value; no second semantic hash
is introduced. A request that omits the default or sends the array out of order
is retryable after local normalization because rejection does not claim its
idempotency key.

The application MUST ensure repeated requests with the same idempotency key and
same normalized-wire `input_hash` do not repeat the side effect. If the same key
is reused with a different normalized-wire `input_hash`, the application MUST
return `idempotency_conflict` without performing an effect.

Idempotency keys are scoped to the grant and action: the application MUST
treat a request as a duplicate only when the same key is presented under the
same `grant_id` and `action_id`. On a duplicate request, the application
SHOULD return the original result and receipt reference rather than an error,
so a retrying runtime can converge on the outcome of the first attempt.
Applications SHOULD retain idempotency state at least for the remaining
lifetime of the grant and SHOULD document their retention window.

The application checks an exact completed record before reserving an
application-authoritative write or cost budget. The runtime likewise reuses its
existing logical tool/model dispatch record instead of charging a transport
retry. A conflict or pre-admission denial consumes no application write or
application-cost budget, although a runtime tool dispatch that already reached
the application remains one runtime-authoritative tool call. Unknown outcomes
retain their original reservations until authoritative reconciliation.

Because one action id has exactly one static execution mode, the action id also
binds the mode for idempotency. The application's stored idempotency record for
a state-changing action MUST additionally bind `input_hash` and
`execution_hash`. Reuse of the same key with a different execution id, preview,
precondition hash, expected-effects hash, reservation, or recovery target
therefore returns `idempotency_conflict` even when the business input is
unchanged. A runtime MUST use distinct idempotency keys for different companion
action ids.

When Approval Receipt is selected, the application MUST also bind the final
role-indexed Approval Receipt hash set into that same idempotency record before
effect admission. A duplicate with the same runtime-side request evidence
returns the original result and final application role map. The same key with a
different runtime Approval Receipt or any attempt to substitute the stored
application receipt is `idempotency_conflict` and MUST NOT reopen approval or
admit another effect.

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
idempotency key, and normalized input arrives with a different parent hash
because that runtime receipt carries a different Approval Receipt evidence set,
the `idempotency_conflict` rule above takes precedence. After the admitted
approval set is equal, a different parent hash is `integrity_mismatch`; the
application MUST NOT repeat the side effect or attach the original result to a
competing provenance chain.

## Minimal Agent Passport Grant-Issuance Profile

This profile defines the minimum Agent Passport evidence that an ASP runtime
and authorization server can consume during Grant issuance. It does not modify
the Agent Passport source specification and does not make every syntactically
valid v1alpha1 document suitable for production authorization.

The consuming profile identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1
```

The exact-artifact hash profile identifier is:

```text
https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1
```

An implementation claims this profile only when it supports both identifiers
and at least one separately named Passport verification profile advertised in
the manifest. The source document's `signature` fields, generic v1alpha1
verification prose, or a schema-validation success are not a concrete
cryptographic verification profile.

### Minimal Source Document

The input MUST be exactly one UTF-8 YAML 1.2 document with one top-level
`passport` mapping and no other top-level member. Before interpreting fields, a
consumer MUST reject duplicate mapping keys, merge keys, aliases, non-core
tags, non-string mapping keys, cyclic data, multiple YAML documents, and values
that cannot be represented in the I-JSON data model. Parsing MUST use a safe,
non-object-constructing YAML implementation.

The source document MUST contain all of these paths:

```text
passport.apiVersion
passport.kind
passport.metadata.name
passport.metadata.uid
passport.metadata.version
passport.metadata.issueDate
passport.metadata.expiryDate
passport.metadata.issuer
passport.spec.entity.type
passport.spec.capabilities
passport.spec.capabilities[].name
passport.spec.capabilities[].signature
passport.signature.algorithm
passport.signature.value
passport.signature.publicKeyRef
```

`passport.apiVersion` MUST be `agent-passport.io/v1alpha1` and
`passport.kind` MUST be `AgentPassport`. Every listed scalar MUST be a non-empty
string. `issueDate` and `expiryDate` MUST be RFC 3339 timestamps; `issueDate`
MUST precede `expiryDate`, and issuance requires
`issueDate <= now < expiryDate` under the verification profile's clock-skew
rules. This profile promotes `expiryDate` from optional in the source draft to
required for ASP Grant issuance.

`spec.capabilities` MUST be an array. Capability names MUST be unique by exact
string equality, and every entry MUST satisfy the source schema for its callable
`signature` object. That object describes parameters and returns; it is not the
Passport's cryptographic signature. An empty capability array can identify an
agent but cannot make an ASP action compatible.

All optional source sections, including resources, security policies,
`agentIntegrity`, signature metadata, and extension fields, remain part of the
retrieved artifact and its cryptographic verification. A consumer MUST NOT drop
unknown fields before signature verification or artifact hashing. An unknown
field has no ASP authority or enforcement semantics unless the selected
verification or integrity profile explicitly defines it.

`metadata.uid` identifies the agent described by the Passport. It is not a
runtime id, OAuth client id, user id, executable hash, or proof that the
currently connected process is that agent.

### Exact Artifact Hash

For a local file, `artifact_octets` is the exact file byte sequence. For a
retrieved representation, it is the exact representation data after transport
framing and content-encoding have been removed and before character decoding,
YAML parsing, newline conversion, or other normalization. The consumer MUST
enforce the advertised `max_artifact_bytes` before buffering or parsing it.

The hash profile computes:

```text
digest = SHA-256(
  UTF8("ASP agent-passport artifact v1") || 0x00 || artifact_octets
)

passport_hash = "sha-256:" || BASE64URL-NOPAD(digest)
```

`BASE64URL-NOPAD` uses the RFC 4648 URL-safe alphabet without `=` padding. The
digest portion is exactly 43 characters decoding to 32 octets; padding,
whitespace, another alphabet, or a different decoded length is invalid.

For the 13 artifact octets consisting of the UTF-8 text `passport: {}` followed
by one LF byte, the result is:

```text
sha-256:218YMarWJ5KKssblgnAdgryNm_8JGmVt4sAkYPeq9Mk
```

This vector exercises only the hash layer; the empty Passport later fails the
minimal source-document checks. Omitting the final LF instead produces
`sha-256:YOwAV1bQimyIkP1UI06EYZRXqi4Eua5DF8yPN-5-EOA`, demonstrating that line
ending normalization is forbidden.

The hash therefore covers the complete artifact, including its top-level
`signature` object, comments, whitespace, YAML presentation choices, and
unknown extensions. It does not parse and reserialize the document. Any byte
change, including re-signing or semantically equivalent YAML reformatting,
produces a different `passport_hash`.

`passport_hash` is an integrity commitment to bytes only. It does not prove a
valid signature, a trusted issuer, current lifecycle status, truthful
capabilities, enforceable policy, or a match to executable code.
`passport_ref` is an optional locator only; recognizing its scheme or fetching
bytes from it is not verification. Redirects, content negotiation, caches, and
local aliases MUST NOT cause a consumer to accept bytes whose exact hash differs
from the Grant-bound value.
An application MUST NOT dereference an arbitrary client-supplied URI. It accepts
only a pre-registered artifact or a locator scheme, origin, redirect policy,
media type, and authentication method explicitly allowed by the selected
verification profile and local SSRF policy.

### Passport Verification Profile

`passport_verification_profile` MUST be a collision-resistant identifier
selected from the applicable manifest entry. Its defining specification MUST
completely define:

- allowed signature algorithms and parameters, with algorithm-confusion and
  downgrade behavior;
- the exact signed byte sequence, including how the top-level `signature`
  object and YAML presentation are handled;
- authenticated `publicKeyRef` resolution, key type checks, issuer-to-key
  binding, trust anchors, key rotation, and historical verification;
- exact issuer identity semantics and any federation or delegation rules;
- signature decoding and verification;
- clock source, accepted skew, issue and expiry validation;
- an authenticated Passport status mechanism, stable status key, response
  binding, freshness, replay handling, and revoked, unknown, and unavailable
  states; and
- fail-closed behavior when keys, trust state, or fresh status cannot be
  obtained.

A profile that leaves any of those items implementation-defined is not usable
for production Grant issuance. In particular, the current Agent Passport
v1alpha1 draft does not itself specify canonical signing bytes, a common trust
store, or an interoperable status protocol. A validator that checks required
fields and base64 syntax but does not cryptographically verify the signature is
schema validation, not Passport verification.

The runtime and authorization server MUST independently support the exact
verification-profile identifier. Neither may substitute a profile with the
same algorithm name, key, issuer, or source `apiVersion`. Status freshness is
mutable verifier state and is not copied into `grant_hash`; every enforcing
component retains the selected profile and checks current status before use.

### Verification and Admission

Verification follows this order:

1. Retrieve no more than `max_artifact_bytes` through an authenticated or
   locally trusted resolution path.
2. Compute the exact-artifact `passport_hash` before parsing and compare it with
   any expected value using a constant-time digest comparison.
3. Perform the safe YAML and minimal source-document checks above.
4. Select the exact consuming, hash, and verification profiles without
   fallback.
5. Resolve an authenticated key, verify the exact signed bytes and issuer trust,
   and reject any algorithm or key mismatch.
6. Validate issue and expiry time and obtain fresh authenticated lifecycle
   status.
7. Treat optional resource, policy, integrity, and extension declarations only
   according to explicitly supported profiles; unsupported declarations do not
   become authority.
8. Extract the unique capability-name set for advisory capability matching.
9. Bind the Passport uid and hash to the runtime-local agent identifier and,
   when claimed, independently verify executable integrity.
10. Derive the Consent Preview and only then request or accept a Grant.

Failure at any step invalidates the admission result. A component MUST NOT keep
a later step's successful result after an earlier binding, trust, time, or
status input changes.

A verifier SHOULD retain a local admission projection such as:

```json
{
  "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
  "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
  "passport_hash": "sha-256:<base64url-digest>",
  "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
  "api_version": "agent-passport.io/v1alpha1",
  "uid": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "version": "1.0.0",
  "issuer": "TrustedAgentIssuers Inc.",
  "public_key_ref": "https://issuer.example/keys/passport-key.jwk",
  "issued_at": "2026-07-01T00:00:00Z",
  "expires_at": "2026-08-01T00:00:00Z",
  "status_checked_at": "2026-07-14T10:00:00Z",
  "status_valid_until": "2026-07-14T10:05:00Z",
  "capability_names": ["comment.create", "pull_request.get"],
  "agent_binding": "document_only"
}
```

This is verifier-local state, not a portable Grant member or attestation. Raw
artifacts, external issuer subjects, key-resolution credentials, and status
responses MUST NOT be copied into an Agent Grant, receipt, event, trace, or
agent-visible context.
`status_valid_until` MUST be no later than Passport expiry, key-validity expiry,
or the selected status profile's maximum freshness deadline.

`agent_binding` is `document_only` unless a separately named integrity profile
has verified a complete, unambiguous mapping from the Passport to the executable
artifacts actually launched under the local agent identifier. A present
`agentIntegrity.codeHashes` array or one matching file is insufficient by
itself: the integrity profile must define path roots, algorithm and encoding,
required artifact inventory, symlink and file-replacement behavior, measurement
time, and failure semantics. When all of those checks succeed, the local value
MAY be `code_hash_verified` and MUST also retain the integrity-profile
identifier. The authorization server MUST NOT present a runtime-local
`code_hash_verified` value as application-verified evidence unless it has a
separate attestation profile that proves that claim.

### Passport Grant Binding

When this profile is selected, a semantic Grant request's `delegate` contains:

```json
{
  "runtime": "application_runtime_456",
  "agent": "local_agent_789",
  "passport_ref": "agent-passport://local-agent",
  "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
  "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
  "passport_hash": "sha-256:<base64url-digest>",
  "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01"
}
```

`passport_profile`, `passport_hash_profile`, `passport_hash`, and
`passport_verification_profile` are REQUIRED and form one exact tuple.
`passport_ref` remains optional. The runtime supplies only values from its
successful local verification. The authorization server independently obtains
the exact artifact, recomputes the hash, verifies the selected profile and fresh
status, and binds its app-scoped `delegate.agent` record to the verified
Passport uid. It MUST NOT accept the runtime's admission projection as a
substitute for those checks.
When `passport_ref` is absent, the authorization server MUST already possess an
authenticated registration for the exact artifact hash and profile tuple; the
authorization request does not carry raw Passport bytes.

`credential_binding` MUST repeat all four required Passport tuple values. The
complete delegate and credential-binding copies are included in `grant_hash`
and MUST remain exact in Rich Authorization Request results, token exchange,
introspection, sessions, child Grants for the same agent, and action
verification. Any missing or mismatched copy is `integrity_mismatch`.

The local and grant-issuer consent views MUST display the profile identifiers,
artifact hash, Passport name, uid, version, issuer, expiration, status freshness,
capability names relevant to the requested actions, and whether executable
binding is `document_only`, locally `code_hash_verified`, or unavailable. Local
integrity and operator claims MUST be labeled as local evidence. A changed
artifact byte, profile identifier, issuer trust result, lifecycle state,
capability set, agent binding, or executable-integrity result makes the Consent
Preview stale.

Passport capabilities, callable signatures, `accessControl`, resources,
security policies, and extensions are signed declarations and policy evidence.
They can make an action incompatible or add a local restriction, but they MUST
NOT add an action, location, scope, resource, approval bypass, or credential
release to an Agent Grant. A valid Passport signature proves only that the
selected key signed the profile-defined bytes; it does not prove the truth of a
claim or that the runtime is executing the described code.

### Passport Lifecycle and Privacy

The exact Passport tuple and fresh status MUST be checked at issuance, before
storing a returned Grant, during introspection, and before every action. A
status refresh for the same artifact and profile does not change `grant_hash`.
Expiry, revocation, unknown status beyond the profile's freshness window, or a
trust/key invalidation makes the Passport unusable and triggers the failure and
session behavior defined by Agent Passport Revoked or Expired.

Renewal, re-signing, reserialization, an extension change, or any other byte
change creates a new `passport_hash`, invalidates pending previews, and requires
new Grant issuance. An implementation MUST NOT silently replace a Grant-bound
artifact with a semantically similar or newer Passport. An updated
`passport_ref` is also a Grant change when that locator is present in the
authoritative delegate.

Consent and management interfaces SHOULD minimize retention of Passport names,
uids, issuers, capability inventories, and local integrity results. The Grant
and its protocol projections contain only the opaque agent id, optional locator,
and four Passport tuple values. Raw artifacts, signatures, external issuer
subjects, status responses, executable paths, and code hashes remain inside the
applicable verifier or runtime boundary.

## Runtime Identity Profile

The base protocol identifies a runtime with the application-scoped
`delegate.runtime` value. Applications that need interoperable information
about how that runtime was authenticated, managed, or deployed MAY additionally
use the Runtime Identity Profile defined here. Its collision-resistant profile
identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1
```

The profile separates five properties that implementations MUST NOT flatten
into one ranked "identity class":

1. the stable application binding for the runtime;
2. the authentication method used for that binding;
3. the runtime's verified management posture;
4. the declared or verified execution locality; and
5. optional assurance results such as hardware-backed attestation.

Authentication, management, locality, and assurance are evidence inputs to
authorization policy. They do not grant actions, locations, scopes, resources,
or approval bypasses. A policy MAY require an exact combination, but this
profile defines no ordering such as SPIFFE being stronger than device
registration or enterprise management implying hardware assurance.

### Runtime Identity Projection

When this profile is selected, the authorization server MUST derive the
following output-only `delegate.runtime_identity` object from its authenticated
runtime record:

```json
{
  "profile": "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1",
  "binding_id": "rbind_01J2D7M2V6Z91Y2R3B4C5D6E7F",
  "claims_revision": 3,
  "authentication": {
    "method": "spiffe",
    "format": "x509_svid"
  },
  "management": {
    "posture": "enterprise_managed",
    "authority_id": "org_7f3a"
  },
  "execution": {
    "locality": "shared_remote",
    "verification": "registered"
  },
  "assurance": []
}
```

`binding_id` MUST be a collision-resistant, opaque, application-and-tenant
scoped identifier. It is immutable and MUST NOT be reassigned to another
runtime identity. `claims_revision` MUST be a positive integer no greater than
`9007199254740991`. It changes only when a material projected claim changes;
ordinary rotation of a short-lived credential with the same verified subject
and projection does not change it.

The authorization server MUST maintain an authoritative record that maps the
pair (`delegate.runtime`, `binding_id`) to the exact external issuer and
subject, current authentication credentials, complete projected object,
revision, and active, suspended, or revoked state. External subjects and raw
credentials are not Grant Object fields. The same `binding_id` MUST NOT be
accepted under another runtime, tenant, or application.

The profile object is closed. `profile`, `binding_id`, `claims_revision`,
`authentication`, `management`, `execution`, and `assurance` are REQUIRED, and
unknown members are forbidden. An extension that adds members or enum values
MUST use a different collision-resistant profile identifier and define its
complete validation and comparison rules.

### Authentication Methods

`authentication.method` is exactly one of `registered_device`, `spiffe`, or
`oidc_workload`. A new method requires a new collision-resistant Runtime
Identity Profile identifier with complete validation rules. One Grant selects
exactly one active authentication binding. A runtime or application MUST NOT
fall back to a different method or subject while retaining the Grant; it
requires renewal and fresh consent.

For `registered_device`, `authentication.format` MUST be `public_key`. The
`authentication` object MUST contain exactly `method` and `format`. The
enrollment procedure MUST bind `delegate.runtime` and `binding_id` to a public
key after proof of possession and explicit confirmation by the authenticated
application account or user. A display name, model, serial number, cookie, or
OAuth Device Authorization Grant alone is not proof of device identity or key
possession. RFC 8628 MAY supply the user interaction for enrollment, but the
application still performs the binding and proof checks. Key rotation preserves
the binding only through an authenticated continuity or recovery procedure;
otherwise the application creates a new `binding_id`.

For `spiffe`, `authentication.format` MUST be `x509_svid` or `jwt_svid`, the
`authentication` object MUST contain exactly `method` and `format`, and the
stable external subject in the authoritative record is the exact SPIFFE ID. An
X.509-SVID validator MUST validate the certificate chain against the applicable
trust-domain bundle, the leaf constraints, and the requirement for exactly one
URI SAN containing the SPIFFE ID. It MUST also authenticate proof of possession
of the corresponding private key through successful mutual TLS at the intended
authorization-server endpoint or through another negotiated profile that binds
a fresh challenge, endpoint context, and selected SPIFFE ID. Merely receiving a
copy of a valid certificate does not authenticate a runtime. A JWT-SVID
validator MUST validate the signature, exact `sub`, narrowly scoped exact
`aud`, and expiration under the applicable trust domain. A JWT-SVID is a bearer
credential and MUST NOT be represented as sender-constrained merely because it
is an SVID. The SPIFFE path is opaque to ASP: an implementation MUST NOT infer
tenant, operator, management posture, locality, or hardware assurance from path
segments or arbitrary claims.

For `oidc_workload`, `authentication.assertion_profile` is REQUIRED and MUST be
a collision-resistant identifier for a concrete workload or client-assertion
profile. The `authentication` object MUST contain exactly `method` and
`assertion_profile` and MUST omit `format`. A generic OpenID Connect ID Token is
defined for End-User authentication and MUST NOT by itself be accepted as
workload identity. The
named assertion profile MUST define trusted issuer or federation-anchor
resolution, allowed signature algorithms, exact `iss`, stable exact `sub`,
narrow exact `aud`, time validation, and replay handling. Email addresses,
display names, and other mutable claims MUST NOT be stable runtime subjects. An
RFC 7523 client assertion or another explicitly profiled workload assertion can
satisfy this method; an arbitrary signed JWT cannot.

The selected runtime authentication key and the Grant Credential
proof-of-possession key are logically separate. They MAY be the same key only
when both profiles permit that use, but implementations MUST NOT assume or infer
that equality.

### Management, Locality, and Assurance

`management.posture` is exactly one of `unmanaged`, `user_managed`,
`enterprise_managed`, `application_managed`, or `third_party_managed`.
`enterprise_managed`, `application_managed`, and `third_party_managed` require
an opaque, application-scoped `authority_id` derived from verified management
evidence. The `management` object MUST contain exactly `posture` and, for those
three values, `authority_id`. `unmanaged` and `user_managed` MUST omit
`authority_id`; self-asserted management labels MUST NOT produce a managed
posture.

`execution.locality` is exactly one of `user_device`, `dedicated_remote`,
`shared_remote`, or `application_embedded`. `execution.verification` is exactly
one of `declared`, `registered`, or `attested`. `declared` cannot satisfy a
policy that requires verified locality. `registered` means only that the
application has recorded and authenticated the locality claim; it is not
continuous attestation. `attested` requires at least one current `assurance`
entry whose named profile explicitly covers execution locality.
The `execution` object MUST contain exactly `locality` and `verification`.

`assurance` is a unique array of objects ordered lexicographically by the UTF-8
values of `type`, then `profile`, then `verifier_id`. An assurance object MUST
contain exactly those three non-empty strings and no raw evidence. The reserved
`hardware_attested` type can appear only when the application has evaluated a
separately negotiated Runtime Attestation Profile that defines the verifier,
evidence format, freshness, reference values, and revocation behavior. SPIFFE,
device registration, an MDM record, a TPM-backed key, or a managed posture alone
MUST NOT produce `hardware_attested`.

### Issuance and Grant Binding

A client selects this profile in a semantic Grant request with the request-only
member:

```json
{
  "delegate": {
    "runtime": "application_runtime_456",
    "runtime_identity_profile": "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1",
    "agent": "local_agent_789",
    "passport_hash": "sha-256:<base64url-digest>"
  }
}
```

The client MUST NOT supply `delegate.runtime_identity`, `binding_id`,
`claims_revision`, a management posture, locality verification, or assurance.
The authorization server authenticates the runtime, verifies that the requested
profile was advertised, derives the exact projection, removes the request-only
`runtime_identity_profile` selector, and returns `delegate.runtime_identity` in
the authoritative Grant Object. It MUST reject a selector it cannot satisfy;
it MUST NOT silently issue an unprofiled or differently profiled Grant.

When `delegate.runtime_identity` is present, `credential_binding` MUST repeat
its `binding_id` as `runtime_identity_binding_id` and its `claims_revision` as
`runtime_identity_claims_revision`. The server MUST include the complete
projection and both repeated values in `grant_hash`. Returned Rich Authorization
Request details, token-exchange responses, introspection responses, and
server-side session state MUST preserve the exact projection. A mismatch among
those copies is `integrity_mismatch`.

Before issuance, the authorization server MUST verify that the exact
(`delegate.runtime`, `binding_id`) record is active, belongs to the authenticated
client and tenant context, and has the projected revision and claims. It MUST
perform the same current-state check before every protected action. Identity
evidence can deny or constrain a Grant, but the issuer MUST NOT add scopes,
actions, resources, or approval exceptions because a method, posture, locality,
or assurance appears stronger.

A child Grant for the same runtime MAY retain the exact projection subject to
ordinary attenuation. A child Grant that names a different runtime MUST have
that runtime's independently authenticated `runtime_identity`; it MUST NOT copy
the parent runtime's binding, claims, management posture, or assurance.

### Rotation, Suspension, and Revocation

Refreshing a credential, SVID, or assertion for the same verified external
subject and exact projected claims retains `binding_id` and `claims_revision`.
A change of authentication method or external subject creates a new binding. A
change of management posture or authority, locality, verification level, or
assurance creates a new revision at minimum. A material downgrade MUST suspend
affected Grants and sessions until the user completes renewal and fresh
consent; it MUST NOT be treated as a transparent refresh.

Expired or temporarily unavailable identity evidence makes the binding
inactive and causes protected actions and introspection to fail closed. A later
successful refresh for the same subject and projection MAY restore the same
binding and Grant without changing `grant_hash`. Permanent revocation of the
runtime binding MUST reject new actions, fence or cancel affected sessions,
apply the Semantic Grant Revocation Transition to every bound Grant and derived
Grant, and make introspection return `{"active":false}`. Revocation of one
binding MUST NOT affect an unrelated runtime merely because both use the same
authentication method or management authority.

### Runtime Identity Privacy

The Grant, introspection response, receipts, events, traces, consent records,
and ordinary logs MUST NOT contain the external workload subject, raw SVID,
certificate, JWT, MDM record, attestation evidence, device serial, hardware key
handle, or reusable enrollment or recovery material. The application MAY expose
only the app-scoped runtime identifier, opaque binding identifier, sanitized
facets, claims revision, and a user-meaningful operator label derived from its
authenticated local state. A display label is not authority and MUST NOT replace
`authority_id` or another verified machine value.

## Remote Processing Privacy Profile

The Data Exposure Contract describes which application-originated data can
cross the application boundary, while the Runtime Identity Profile describes
the controlling runtime. Neither one, by itself, constrains every agent, model,
tool, adapter, subagent, or secondary runtime that can receive that data after
the boundary. An application and runtime that need an interoperable whole-path
restriction use the optional profile defined here. Its identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1
```

This profile requires the Data Exposure Contract, the Runtime Identity Profile,
and the Consent Preview Contract. It binds a runtime commitment and an
application-enforced disclosure ceiling into the semantic Grant. It does not
turn a client declaration, issuer echo, Grant hash, management posture, or
Runtime Identity locality into independent evidence that a downstream
processor followed the commitment.

### Processing Path Commitment and Baselines

The **processing path** is the complete set of components that can receive
application-originated plaintext or a semantically equivalent representation
while carrying out the Grant. It includes the controlling runtime, selected
agent, model providers, tools, MCP servers, adapters, subagents, ungranted
secondary runtimes, diagnostic processors, and any other recipient under
runtime control. A local bridge that sends prompts to a remote model has a
remote processing path even when the bridge itself executes on the user's
device.

A client selects the profile with this request-only closed object:

```json
{
  "constraints": {
    "remote_processing": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1",
      "path": "enterprise_managed"
    }
  }
}
```

`profile` and `path` are REQUIRED and unknown members are forbidden. `path` is
exactly one of `local_user_device`, `enterprise_managed`, or
`remote_user_selected`. The request MUST NOT contain `classification_ceiling`.
The path predicates are mutually exclusive over one resolved path:

- `local_user_device` means every data-bearing component executes on the same
  user device as the controlling runtime and no application-originated data or
  equivalent representation crosses from that device to a processor. The
  server-derived Runtime Identity projection MUST have
  `execution.locality` equal to `user_device` and `execution.verification`
  equal to `registered` or `attested`; that necessary condition does not prove
  the absence of downstream egress.
- `enterprise_managed` means at least one data-bearing component can execute
  remotely, the controlling runtime has `management.posture` equal to
  `enterprise_managed`, and the runtime or its authenticated enterprise policy
  has mapped every remote recipient to the same exact Runtime Identity
  `authority_id`. A domain name, network location, provider label, employee
  login, or self-asserted management claim is insufficient.
- `remote_user_selected` means at least one data-bearing remote recipient is
  outside the verified enterprise boundary and every such recipient and its
  operator is known to the runtime and affirmatively selected or accepted in
  the local consent flow. A path containing both local and such remote
  components uses this value.

A path with an unknown recipient, incomplete processor inventory, unresolved
operator, or processor whose policy cannot be evaluated cannot be selected or
used under this profile. Matching remains `indeterminate` until the missing
input is resolved. The path MUST NOT be represented as `local_user_device`, silently
folded into `enterprise_managed`, or treated as no remote processing. An
`application_embedded` controlling runtime cannot use the local or enterprise
value merely because it is co-located with application code. It can use
`remote_user_selected` only when every recipient is resolved and the consent
view conspicuously identifies the app-operated trust boundary; otherwise the
profile fails closed.

After validating the request, the authorization server returns the same exact
`profile` and `path` plus the deterministic output-only
`classification_ceiling`:

| `path` | `classification_ceiling` |
| --- | --- |
| `local_user_device` | `sensitive` |
| `enterprise_managed` | `private` |
| `remote_user_selected` | `public` |

For example:

```json
{
  "constraints": {
    "remote_processing": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1",
      "path": "enterprise_managed",
      "classification_ceiling": "private"
    }
  }
}
```

The returned object is closed and contains exactly `profile`, `path`, and
`classification_ceiling`. The ceiling uses the Data Exposure Contract
protection order and is this versioned profile's conservative baseline, not a
universal trust ranking. The authorization server MUST NOT rewrite `path`, and
there is no inferred attenuation order among path values. Local, enterprise,
or application policy MAY reject a path or impose a stricter local ceiling,
but a different wire mapping requires a new collision-resistant profile
identifier.

No path in this profile admits the `credential` classification. The ceiling
does not authorize credential disclosure, does not weaken the separate
`credential.release` capability and constraints, and never makes an Agent
Surface Grant Credential releasable. A profile that deliberately carries
credential-class application data requires a separate specification.

### Issuance and Data-Path Enforcement

The manifest MUST advertise this profile in
`compatibility.remote_processing_profiles`. A semantic Grant request selecting
it MUST also select the Runtime Identity Profile and MUST include the
request-only `constraints.remote_processing` object above. The complete request
object, including exact `profile` and `path` but excluding the server-only
ceiling, is part of the Semantic Grant Request Hash.

Before issuer consent and issuance, the authorization server MUST:

1. authenticate the runtime and derive its exact active Runtime Identity
   projection;
2. validate that the requested profile is advertised and that the controlling
   runtime satisfies the necessary Runtime Identity predicate for the selected
   path;
3. independently derive the complete effective `data_exposure` source closure
   from the pinned manifest and approved actions and scopes;
4. resolve every class identifier in that closure to its pinned manifest
   classification; and
5. reject issuance if any classification is above the deterministic ceiling.

The server MUST reject an unknown class, missing projection, client-supplied
ceiling, mismatched path output, or unsupported profile with
`invalid_authorization_details` under the OAuth profile. It MUST NOT make an
incompatible request appear valid by deleting one class from an exposure
entry, inventing a narrower redaction policy, omitting a source, or assuming
that a resource filter removes the protected data. The user can instead
approve a whole action or scope subset whose recomputed source closure fits the
same exact path.

The returned `constraints.remote_processing` object, effective
`data_exposure`, and complete Runtime Identity projection are included in the
authoritative Grant Object, `grant_hash`, token response, introspection response,
and server-side Grant state. Before every protected disclosure, the application
MUST validate the exact object, deterministic ceiling, active Runtime Identity
binding, and full exposure closure. These checks prove what the application
will disclose under the Grant; they do not prove what a conforming or malicious
runtime does after receipt.

Before every application-originated payload crosses to the selected agent or
another downstream component, the controlling runtime MUST independently:

- recompute the applicable source entry and pinned class classifications;
- verify that the actual complete path still satisfies the Grant-bound path
  predicate;
- apply any stricter local classification or policy; and
- verify that every recipient can enforce the redaction, retention, and
  processing-path restrictions.

If any check is false or unknown, the runtime MUST block and discard the
pending disclosure before downstream dispatch and fail it as
`remote_processing_violation`. The offending value, recipient details, and
policy evidence MUST NOT be copied into the error, receipt, trace, prompt, or
ordinary log. A malformed or mismatched authoritative Grant remains
`integrity_mismatch`, an inactive or mismatched Runtime Identity remains
`runtime_untrusted`, and a payload outside its declared class, redaction, or
retention envelope remains `data_exposure_violation`. The new error is only for
a valid Grant whose current processing path or recipient enforcement state no
longer satisfies its bound constraint.

The path and ceiling apply Grant-wide. A workflow that needs sensitive local
processing and only public data in a remote tool requires separate Grants and
separate source closures under this version. Implementations MUST NOT combine
the two flows and claim that a field-level split occurred when the manifest
defines only source-level classes.

### Lifecycle, Delegation, and Evidence Boundary

A change to `profile` or `path` changes the semantic Grant request, Capability
Match Result, Consent Preview, and Grant hash. It requires a fresh issuance and
issuer consent flow; an implementation MUST NOT migrate an active Grant or
session in place. A recipient, operator, provider policy, processor inventory,
or enforcement-capability change within the same path value makes the local
match and consent preview stale and requires fresh local confirmation before
further disclosure. If application policy binds that changed fact, a new Grant
is also required.

An ungranted subagent, remote model, tool, adapter, or secondary runtime remains
inside the controlling runtime's path. Creating a child Grant does not erase
that fact for data the parent transmits. Every child Grant that selects this
profile has its own independently resolved path commitment and ceiling. A child
bound to another runtime MUST NOT copy the parent's path claim or Runtime
Identity evidence. This version defines no exposure projection for forwarding
application-originated data previously received by a parent into a separately
granted child. The parent MUST NOT perform that transfer; the child must obtain
the data through its own independently authorized application resource, action,
or event source and effective `data_exposure` projection. A future transfer
profile would need to preserve the original source, classes, and both Grant
bindings. In particular, a parent `local_user_device` commitment cannot be used
to route application data to a remote child.

Expiry, suspension, or revocation stops new disclosures immediately. Existing
retention and `delete_on_grant_end` obligations continue to apply to plaintext
already delivered. A runtime that learns that an earlier disclosure violated
the path MUST stop further use, isolate the affected work, retain only
data-minimized incident evidence, and initiate the applicable Grant suspension
or revocation path; ASP does not claim that this reverses an external
disclosure.

The `grant_hash` in a receipt binds that receipt to the selected restriction.
It is not a processing receipt, provider attestation, proof of recipient
topology, or proof of deletion. A runtime MAY retain a local, data-minimized
path revision or policy-decision hash for audit, but portable receipts and
public errors MUST NOT enumerate provider accounts, endpoints, tenant ids, or
processor topology unless a separate evidence profile defines that disclosure.

This profile does not specify training or model-improvement use. Locality,
enterprise management, a restrictive classification ceiling, and transient
plaintext retention MUST NOT be presented as a no-training promise.

### Remote Processing Consent and Privacy

The local Consent Preview MUST show the exact profile, path value, deterministic
ceiling, every effective source and class, and whether the full path predicate
is currently satisfied. It MUST separately label the app-authenticated
controlling Runtime Identity facets and the runtime-local downstream
commitment. Known operator and recipient labels MAY be shown, but their
verification boundary MUST be explicit and they MUST NOT be represented as
application-verified Grant fields.

The authorization server's consent view MUST show the same requested path,
effective ceiling, and source closure derived from its pinned manifest and
approved request. It MUST state that the ceiling is application-enforced while
the downstream path is an authenticated runtime commitment unless a separately
negotiated evidence profile proves more. Issuer consent to this object does not
certify a provider or waive the runtime's local confirmation responsibility.

Active-grant management views MUST show the exact hash-bound path and ceiling
without exposing application payloads or a recipient inventory. Applications
and runtimes SHOULD minimize retained path metadata and use opaque local
references for diagnostic correlation. A provider name, authority id, endpoint,
or recipient graph can reveal organizational relationships and user choices;
none is included in this profile's Grant object.

## Agent Training Use Policy Profile

The Data Exposure Contract controls disclosure, redaction, and plaintext
retention. The Remote Processing Privacy Profile controls the whole processing
path and its classification ceiling. Neither contract states whether a runtime,
agent, or provider can reuse disclosed data to improve a model or reusable
processing artifact. An application and runtime that need an explicit,
interoperable answer use the optional profile defined here:

```text
https://github.com/0al-spec/agent-surface/profiles/agent-training-use/v1
```

This profile requires the Data Exposure Contract, Remote Processing Privacy,
and the Consent Preview Contract. Its constraint is an authorized secondary-use
policy, not evidence that a provider complied with the policy and not a legal,
deletion, or model-unlearning claim.

For this profile, **training use** means using application-originated plaintext
or a semantically derived representation to create, update, select for future
reuse, evaluate for model improvement, or improve a reusable model, adapter,
reward or ranking function, persistent embedding or retrieval index, training
or evaluation dataset, annotation set, or corpus. The definition applies
whether that use occurs during or after execution of the exact current
Grant-authorized task. Fine-tuning, distillation, model-improvement evaluation,
retaining examples for a later training run, and an online update that can
leave durable influence are training use. Ephemeral inference context strictly
necessary to execute the current task is not training use only when it creates,
updates, selects, evaluates, or retains no reusable artifact covered by this
definition; it remains subject to the Data Exposure redaction and retention
contract. Operational security or abuse processing is not training use unless
its data or results are repurposed for such a reusable artifact.

### Training Class Constraint and Attenuation

The semantic Grant request carries this closed constraint:

```json
{
  "constraints": {
    "training_use": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-training-use/v1",
      "permitted_classes": []
    }
  }
}
```

`profile` and `permitted_classes` are REQUIRED and unknown members are
forbidden. `permitted_classes` is an array of unique manifest `data_classes`
identifiers ordered by ascending Unicode code point. Every requested identifier
MUST appear in the union of class ids in the deterministic exposure projection
for the exact requested actions and scopes.

An empty array is an explicit prohibition on training use of every
application-originated class disclosed under the Grant. A non-empty array names
the post-redaction classes that can participate in training, but it permits a
given source payload only when that source satisfies the complete whole-source
predicate below. Omission of `training_use` means unspecified; it MUST NOT be
rendered, matched, or enforced as either an empty array or a permission. A
runtime or application policy that requires no training MUST require this exact
profile with an empty array.

This profile defines no field-level selection rule. A complete source payload
is eligible for training use only when:

```text
source.data_exposure.classes is a subset of training_use.permitted_classes
```

If a source contains both `repository.content` and `user.identifier`, a Grant
that permits only `repository.content` does not permit training on any part of
that source payload. The application can publish a separate source with an
independently enforced redaction contract; the runtime MUST NOT infer which
bytes belong to the permitted class. Derived data retains every source class
for this decision unless a separately negotiated irreversible-transformation
profile defines and proves a different classification. Hashing, embedding,
pseudonymizing, summarizing, or aggregating data alone does not escape the
constraint.

After issuer-side approval, the authorization server returns the same closed
object with an effective set satisfying:

```text
returned permitted_classes
  is a subset of requested permitted_classes
  intersected with the returned effective data-exposure class union
```

The server MAY remove a requested class because of application policy or user
choice and MUST remove a class that is no longer exposed after an approved
action or scope subset. It MUST NOT add a class. The exact returned array MUST
remain present even when empty, and its order is canonical. The sequence
`["repository.content", "user.identifier"]` to
`["repository.content"]` to `[]` is attenuation; the reverse direction is
authority widening and requires a new request and fresh consent.

Training permission never widens actions, scopes, sources, processors,
redaction, classification ceilings, or plaintext retention. The Remote
Processing Privacy check still evaluates the full exposure closure, including
classes that are prohibited for training. A lower training-use set cannot make
sensitive data eligible for a `public` processing ceiling.

`retention.mode` continues to govern runtime-controlled plaintext, examples,
and corpora. A training permission does not authorize storage beyond that
contract. Conversely, `transient` plaintext retention does not mean no
training: an allowed online update can leave durable influence after plaintext
deletion. A consent or management view MUST show those two dimensions
separately and MUST NOT label an empty training set as “transient only.”

### Issuance, Enforcement, and Lifecycle

The manifest MUST advertise this profile in
`compatibility.training_use_profiles`. A request selecting it MUST also select
the Remote Processing Privacy Profile. The complete request constraint is part
of the Semantic Grant Request Hash. The effective returned constraint is part
of the authoritative Grant Object, `grant_hash`, token response, introspection
response, management view, and server-side Grant state.

Before consent and issuance, the authorization server MUST independently derive
the exact effective exposure closure, validate every requested class and the
source-level rule above, apply application policy, and obtain issuer-side user
approval for the effective set. A non-empty client request is not training
authority by itself. Under the OAuth profile, an absent required member, unknown
or duplicate class, non-canonical order, unadvertised profile, or class outside
the requested exposure union is `invalid_authorization_details`.

Before storing or using the returned Grant, the runtime MUST recompute the
returned exposure closure and reject a missing constraint, added class,
non-subset result, unknown class, stale source, or mismatch among Grant, token,
and introspection representations as `integrity_mismatch`. A valid strict
subset is privacy attenuation and does not require a second expanding consent.

Before any training use, the controlling runtime MUST first apply the ordinary
Grant, Data Exposure, and Remote Processing validations. An inactive Grant
fails with its existing Grant lifecycle error, an invalid source or retention
contract fails as `data_exposure_violation`, and a failed path commitment fails
as `remote_processing_violation`. Under an otherwise valid Grant, exposure
projection, and path, the runtime MUST verify that the source payload's complete
class set is a subset of the effective `permitted_classes` and that every
downstream recipient enforces an equal or stricter training policy. Failure of
either training-specific check is `training_use_denied`, and the payload MUST be
blocked before training dispatch. If a required provider capability or policy
input is unknown or stale, matching is `indeterminate` and disclosure remains
blocked; it is not optimistic consent.

A provider, operator, model, processing configuration, policy, or enforcement
capability change makes the local Capability Match Result and Consent Preview
stale even when the Remote Processing path value remains the same. A change to
the requested `permitted_classes` set for the same root authorization changes
the semantic request and requires a new issuer consent flow. The server-side
subset during that issuance and a derived child or token exchange that satisfies
the explicit attenuation rules below MAY narrow the set without expanding
consent; the derived Grant receives its own authoritative hash and lineage. An
existing Grant MUST NOT be mutated in place.

Expiry, suspension, or revocation prohibits every new training use and new
disclosure under the Grant and activates its existing plaintext cleanup
obligations. It does not reverse training use that was permitted and completed,
prove that a model forgot data, or authorize continued use of retained material.
Data obtained under a Grant for a class absent from `permitted_classes` remains
prohibited from later training use after Grant termination; expiration does not
convert a prohibition into permission.

### Delegation, Consent, and Evidence Boundary

An ungranted subagent, model, tool, adapter, or secondary runtime remains under
the controlling runtime's effective training constraint. The runtime MUST NOT
send a source payload to a component whose training policy is wider or unknown.

For a derived child Grant, when the parent selected this profile, the child
MUST retain the constraint and satisfy:

```text
child permitted_classes
  is a subset of parent permitted_classes
  intersected with child effective data-exposure classes
```

The child retains an explicit empty array when the intersection is empty. A
child MUST NOT omit the constraint, add a class, or reuse the parent's provider
commitment as evidence for another runtime. When the parent omitted this
profile, a derived child MAY add the empty-array form as a further restriction
only when the parent already selected Remote Processing Privacy and the child
retains its exact profile and path value while resolving its own runtime-bound
path commitment and ceiling. Otherwise adding this profile, or adding a
non-empty permission, requires a fresh independent root Grant and consent. As
defined by Remote Processing Privacy, the parent does not forward previously
received application payloads into a separately granted child; the child
obtains data through its own authorized application sources.

The local Consent Preview and issuer consent view MUST show the exact requested
or effective permitted set, every prohibited effective class, and every source
in which each class occurs, alongside the separate path, ceiling, redaction,
and plaintext-retention semantics. A non-empty set MUST carry a conspicuous
warning that permitted training can leave durable influence in a model,
adapter, or index after plaintext deletion and Grant revocation. An omitted
profile MUST be labeled unspecified, never “no training.” Provider statements
MUST be labeled as runtime-local commitments unless a separate evidence profile
verifies them.

Active-grant management views MUST show the exact hash-bound permitted set and
the same no-unlearning boundary. The `grant_hash` in a receipt binds the receipt
to that policy but proves neither provider compliance nor training or
unlearning. A runtime MAY retain a data-minimized local decision record keyed by
`grant_hash`, source ids, policy revision, decision, and timestamp. This profile
defines no portable provider receipt, compliance attestation, legal-purpose
taxonomy, or verifiable unlearning mechanism.

## Runtime Attestation Optional Profile

Runtime attestation is an optional extension to the Runtime Identity Profile.
The base ASP profile accepts an application-registered runtime id without
attestation; no implementation is required to support this section for MVP
conformance. An application that requires runtime integrity evidence uses the
framework defined here and one concrete attestation profile.

The framework identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/runtime-attestation/v1
```

This framework follows the RATS roles from RFC 9334:

- the Runtime, or a protected environment that measures it, is the **Attester**;
- a **Verifier** appraises Evidence against endorsements, reference values, and
  its Appraisal Policy for Evidence and produces authenticated Attestation
  Results; and
- the application authorization server is the **Relying Party** that applies
  its own Appraisal Policy for Attestation Results.

One component MAY perform multiple roles, but implementations MUST preserve the
logical trust and policy boundaries. Evidence is not an Attestation Result, a
Verifier decision is not the Relying Party's authorization decision, and none
of those artifacts is an Agent Grant.

### Attestation Discovery and Concrete Profiles

An application advertises support with the optional closed
`auth.runtime_attestation` object shown in the manifest example. It contains
exactly:

- `framework`, equal to the framework identifier above;
- `attestation_url`, an absolute HTTPS URL;
- `profiles_supported`, a non-empty array of unique collision-resistant
  concrete profile identifiers; and
- `verifiers`, a non-empty array of closed objects containing unique
  `verifier_id` values and non-empty unique `profiles` arrays. Every listed
  profile MUST also appear in `profiles_supported`.

Absence means the application does not support attestation under this draft. It
does not make the base runtime anonymous or non-conforming. A runtime MUST NOT
infer support from a TPM, TEE, Secure Enclave, SPIFFE credential, MDM record,
EAT media type, or hardware-backed key.

Every concrete profile identifier MUST define all of the following without
leaving security-critical choices to deployment guesswork:

- Attester, Target Environment, and layered or composite coverage;
- Evidence and Attestation Result formats, media types, required claims, and
  validation schemas;
- authenticated challenge request, Evidence submission, Result delivery or
  polling, correlation, timeout, and retry transport mappings;
- security envelopes, allowed algorithms, key types, authenticated key
  resolution, trust anchors, and algorithm-downgrade behavior;
- verifier identity, result authentication, status and key lifecycle;
- nonce, timestamp or epoch freshness, replay state, maximum ages, and clock
  skew;
- endorsement and reference-value resolution, appraisal-policy identity and
  versioning, and failure behavior when any input is unavailable;
- proof-key binding and its thumbprint algorithm;
- privacy minimization and which sanitized result claims the Relying Party may
  retain; and
- revocation, remediation, and transition semantics.

RFC 9711 EAT is a claims framework, not a complete runtime-attestation profile.
An implementation MUST NOT accept a generic EAT, arbitrary JWT or CWT, or a
media type alone. An EAT-based concrete profile MUST identify an exact
`eat_profile`, required claims and processing, security envelope, and
verification rules. RFC 9782 media types aid format negotiation but do not
validate the advertised content.

### Attestation Requirement and Stable Grant Binding

Attestation requires the Runtime Identity Profile. A semantic Grant request
selects it with the request-only closed object:

```json
{
  "runtime_attestation_requirement": {
    "profile": "https://verifier.example/profiles/eat-tpm-runtime/v1",
    "verifier_id": "verifier_7f3a",
    "max_age_seconds": 300,
    "proof_key_thumbprint": "sha-256:<profile-defined-thumbprint>"
  }
}
```

This object is a member of `delegate` and contains exactly the four fields
shown. `profile` and `verifier_id` MUST be an advertised pair.
`max_age_seconds` is a positive integer no greater than `9007199254740991`.
The concrete profile defines the public-key representation and exact thumbprint
calculation; the value MUST use the unpadded `sha-256:` syntax unless that
profile defines another collision-resistant hash identifier.

The client MUST NOT supply an attestation binding, assurance result, appraisal
state, result hash, policy hash, reference-value hash, raw Evidence, or raw
Attestation Result in the Grant request. The authorization server authenticates
the runtime, validates the exact requirement, obtains an accepted appraisal,
removes `runtime_attestation_requirement`, and returns this closed output-only
`delegate.runtime_attestation` object:

```json
{
  "binding_id": "atbind_01J2F7M2V6Z91Y2R3B4C5D6E7F",
  "profile": "https://verifier.example/profiles/eat-tpm-runtime/v1",
  "verifier_id": "verifier_7f3a",
  "max_age_seconds": 300,
  "proof_key_thumbprint": "sha-256:<profile-defined-thumbprint>"
}
```

`binding_id` is an opaque, collision-resistant, application-and-tenant scoped
identifier bound to the exact runtime identity revision, requirement, and
`grant_request_hash`; it MUST NOT be reassigned or reused for another request.
An idempotent replay of the same exact request MAY reuse it. The returned
`max_age_seconds` MUST be positive and no greater than the requested value; a
smaller value is an explicit attenuation. The complete stable object is included
in `grant_hash`. `credential_binding` MUST repeat `binding_id`, `profile`,
`verifier_id`, and `proof_key_thumbprint` as
`runtime_attestation_binding_id`, `runtime_attestation_profile`,
`runtime_attestation_verifier_id`, and
`runtime_attestation_proof_key_thumbprint`.

The selected proof key and Grant Credential proof key are distinct bindings.
They MAY use one key only when both concrete profiles allow it. Otherwise the
attestation profile MUST authenticate a cross-binding, and the application MUST
verify that binding on every action. Possession of either key alone MUST NOT be
silently substituted for the other.

When the accepted concrete profile covers a hardware-rooted measurement chain
through the exact Runtime Target Environment, the server-derived
`runtime_identity.assurance` contains exactly one corresponding entry:

```json
{
  "type": "hardware_attested",
  "profile": "https://verifier.example/profiles/eat-tpm-runtime/v1",
  "verifier_id": "verifier_7f3a"
}
```

The entry describes the stable required assurance profile, not current mutable
appraisal state. `runtime_identity.execution.verification` is `attested` only
when the same profile explicitly covers execution locality. Attestation of a
hardware root, boot layer, container host, or key without the Runtime Target
Environment MUST NOT be represented as runtime integrity or attested locality.

The complete attestation binding, Runtime Identity projection, assurance entry,
and repeated credential-binding fields MUST agree. A profile, verifier,
maximum age, proof-key, coverage, assurance, or stable binding change is
material: it changes the Runtime Identity claims revision, requires a new Grant
and Consent Preview, and MUST NOT be applied as an in-place appraisal refresh.
Every child Grant has its own semantic `grant_request_hash` and therefore needs
a child-specific challenge, accepted appraisal record, and stable attestation
binding, even when it retains the parent's Runtime Identity projection. A child
for a different runtime additionally needs that runtime's independent identity,
proof key, and Evidence; no child copies the parent's binding or Result.

### Challenge, Evidence, and Appraisal

Before Evidence is generated, `auth.runtime_attestation.attestation_url` returns
an authenticated, closed challenge object:

```json
{
  "framework": "https://github.com/0al-spec/agent-surface/profiles/runtime-attestation/v1",
  "challenge_id": "atch_01J2F8M2V6Z91Y2R3B4C5D6E7F",
  "nonce": "<unpadded-base64url-16-to-64-octets>",
  "issuer": "https://code.example.com",
  "app_id": "code.example.com",
  "audience": "https://example.com/runtime-attestation",
  "runtime_id": "application_runtime_456",
  "runtime_identity_binding_id": "rbind_01J2D7M2V6Z91Y2R3B4C5D6E7F",
  "runtime_identity_claims_revision": 3,
  "profile": "https://verifier.example/profiles/eat-tpm-runtime/v1",
  "verifier_id": "verifier_7f3a",
  "max_age_seconds": 300,
  "proof_key_thumbprint": "sha-256:<profile-defined-thumbprint>",
  "grant_request_hash": "sha-256:<base64url-digest>",
  "issued_at": "2026-07-14T10:00:00Z",
  "expires_at": "2026-07-14T10:02:00Z"
}
```

The endpoint MUST authenticate the requesting runtime binding before issuing a
challenge. `challenge_id` is collision-resistant and single-use. `nonce`
decodes to 16 through 64 unpredictable octets generated by a cryptographically
secure random-number generator. `audience` exactly equals the advertised
`attestation_url`; the other application and runtime fields come from the
pinned manifest, authenticated runtime record, and exact semantic Grant
request. `max_age_seconds` is the server-selected effective value and MUST be no
greater than the request. `issued_at` and `expires_at` are RFC 3339 timestamps,
and expiry MUST be short enough to satisfy the concrete profile and local
policy.

The concrete profile defines how Evidence authenticates the nonce and every
challenge binding. The Verifier MUST reject missing, altered, expired, or
replayed challenges, unexpected profile or media type, wrong audience, wrong
runtime or proof key, and untrusted or stale endorsements, reference values,
keys, or appraisal policy. A request change produces a different
`grant_request_hash` and requires a new challenge. A challenge and appraisal do
not claim an action idempotency key, consume a Grant budget, create an action
receipt, or authorize an effect.

The Verifier appraises Evidence and returns an authenticated Attestation Result
under the concrete profile. The application verifies the result's issuer,
signature or authenticated channel, profile, challenge, Attester and Target
Environment coverage, proof key, freshness, appraisal policy, and status before
applying its own Relying Party policy. It MUST NOT accept an Attester's
self-declared compliance bit as an Attestation Result.

Raw Evidence flows only to the Verifier. When the Verifier is separate, the
application receives only the profile-defined, privacy-minimized Attestation
Result. When roles are co-located, raw Evidence remains inside the logical
Verifier boundary and MUST NOT be copied into the Grant or application business
data. The runtime receives only the challenge and a sanitized state needed to
continue or diagnose the flow.

### Mutable Appraisal State

The application keeps mutable state outside the Grant Object:

```json
{
  "attestation_binding_id": "atbind_01J2F7M2V6Z91Y2R3B4C5D6E7F",
  "revision": 8,
  "runtime_id": "application_runtime_456",
  "runtime_identity_binding_id": "rbind_01J2D7M2V6Z91Y2R3B4C5D6E7F",
  "runtime_identity_claims_revision": 3,
  "profile": "https://verifier.example/profiles/eat-tpm-runtime/v1",
  "verifier_id": "verifier_7f3a",
  "proof_key_thumbprint": "sha-256:<profile-defined-thumbprint>",
  "grant_request_hash": "sha-256:<base64url-digest>",
  "result_hash": "sha-256:<profile-defined-result-digest>",
  "verifier_policy_hash": "sha-256:<profile-defined-policy-digest>",
  "reference_value_hashes": ["sha-256:<profile-defined-reference-digest>"],
  "state": "accepted",
  "verified_at": "2026-07-14T10:00:20Z",
  "fresh_until": "2026-07-14T10:05:20Z",
  "state_changed_at": "2026-07-14T10:00:20Z"
}
```

This record is authoritative application state, not a wire Attestation Result.
`revision` is a positive safe integer that strictly increments on every record
mutation, including a state transition or an accepted appraisal refresh.
The selected concrete profile defines the three hash algorithms and hashing
views. `reference_value_hashes` is sorted and unique. `fresh_until` MUST be no
later than the Evidence or Result expiry, requirement `max_age_seconds`,
Verifier key and status validity, appraisal-policy validity, or reference-value
freshness.

The state machine is:

```text
absent -> challenged
challenged -> appraising | indeterminate | revoked | superseded
appraising -> accepted | rejected | indeterminate | revoked | superseded
accepted -> stale | revoked | superseded
rejected | indeterminate | stale -> challenged | revoked | superseded
```

Only current `accepted` state satisfies the Grant requirement. Challenge expiry,
transport failure, unverifiable input, unavailable reference values, or an
unknown result produces `indeterminate`, never optimistic acceptance.
`rejected` means a current authenticated appraisal failed policy. `stale` means
freshness elapsed; the record is logically `stale` at `fresh_until` even if a
persisted transition has not yet run. `revoked` permanently invalidates the
stable binding.
`superseded` means a material stable binding or coverage change requires a new
Grant.

The application MUST check the exact record, revision, and current accepted
state before issuing a Grant, on introspection, before every action, and before
resuming a session. A non-accepted state makes introspection inactive, rejects
new actions as `runtime_untrusted`, and fences affected sessions before another
effect. It MUST NOT fall back to an unattested runtime, another verifier,
another profile, an older accepted result, or a different proof key.

Refreshing Evidence under the same exact stable binding and Runtime Identity
projection MAY update mutable hashes, revision, and freshness without changing
`grant_hash`. `rejected`, `indeterminate`, or `stale` state MAY return to a new
challenge and later `accepted` state if the same profile permits remediation.
`revoked` triggers the Semantic Grant Revocation Transition for every bound
Grant and derived Grant. `superseded` remains inactive until fresh consent and a
new Grant bind the replacement.

### Attestation Authority, Security, and Privacy

Attestation is evidence for a Relying Party policy. It MAY deny a Grant, require
narrower scopes, force stronger approval, or reject an action, but it MUST NOT
add actions, scopes, resources, credential release, or approval bypasses. An
accepted Result is not a credential and does not prove that the runtime remains
unchanged after measurement; freshness narrows but cannot eliminate that race.

The application MUST treat Verifier compromise, stale reference values,
ambiguous Target Environment coverage, replayed Evidence, proof-key substitution,
and appraisal-policy downgrade as security failures. A different policy or
reference-value set MUST NOT be called equivalent merely because both return
`accepted`. Runtime authentication, Agent Passport verification, Grant
proof-of-possession, and runtime attestation remain independent checks.

The Grant, introspection response, Consent Preview record, receipts, events,
traces, and ordinary logs MUST NOT contain raw Evidence or Results, measurements,
endorsements, reference values, hardware serials, device identifiers, Attester
keys, firmware inventory, debug state, or Verifier diagnostics. The Grant
contains only the stable binding, concrete profile, opaque verifier id,
proof-key thumbprint, and sanitized assurance reference. An authenticated and
authorized introspection or management view MAY additionally disclose only the
coarse current `accepted` or inactive state needed by that caller; mutable state
is never added to the Grant hashing view. Public errors MUST NOT reveal which
measurement, reference value, or appraisal rule failed.

Reference-value distribution, transparency services, and supply-chain statement
registration are outside this profile. Such systems can authenticate provenance
and history, but their presence alone does not prove current runtime state or
freshness.

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
    "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
    "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
    "passport_hash": "sha-256:<base64url-digest>",
    "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01"
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
    "budgets": {
      "max_write_actions": 20,
      "max_tool_calls": 100,
      "max_model_tokens": 50000,
      "max_runtime_seconds": 1800,
      "max_parallel_sessions": 2,
      "cost": {
        "currency": "USD",
        "max_runtime_microunits": 4000000,
        "max_application_microunits": 1000000
      }
    },
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
    "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
    "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
    "passport_hash": "sha-256:<base64url-digest>",
    "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
    "jkt": "<base64url-thumbprint>"
  },
  "audit": {
    "local_receipt": "required",
    "app_receipt": "required",
    "approval_receipt": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1",
      "requirements": [
        {
          "action_id": "comment.create",
          "accepted_roles": ["runtime"],
          "max_age_seconds": 300
        }
      ]
    }
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

`locations` restricts only Action Requests; it is not an OAuth credential
audience and does not list `budget_state_url` or `session_control_url`. Those
endpoints accept only their closed safety operations, authenticate the same
exact Grant and delegate tuple under `agent_api.credential_audience`, and MUST
NOT infer action authority merely because the credential is valid there.

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
When the Runtime Identity Profile is selected, `delegate.runtime_identity` is
also authorization-server output and `credential_binding` MUST repeat its
binding id and claims revision as defined by that profile. The request-only
`delegate.runtime_identity_profile` selector is the request/Grant shape
exception within `delegate`; it MUST NOT remain in the authoritative Grant.
When the Minimal Agent Passport Grant-Issuance Profile is selected, `delegate`
and `credential_binding` MUST each contain the same `passport_profile`,
`passport_hash_profile`, `passport_hash`, and
`passport_verification_profile` tuple. Unlike runtime identity output, the
client supplies this tuple from its local verification and the authorization
server independently verifies it.
When Runtime Attestation is selected,
`delegate.runtime_attestation_requirement` is request-only and MUST be replaced
by the server-derived stable `delegate.runtime_attestation` binding. The
credential binding repeats its stable identifiers and proof key, while mutable
appraisal state remains outside the Grant Object.

When the Remote Processing Privacy Profile is selected, the request contains
`constraints.remote_processing` with only `profile` and `path`. The
authorization server MUST preserve both exactly and add the profile's
deterministic output-only `classification_ceiling` to the authoritative Grant.
That complete constraint is included in `grant_hash`, token and introspection
responses, management views, and protected-resource validation. It restricts
disclosure and does not prove downstream compliance.

When the Agent Training Use Policy Profile is selected, both request and Grant
contain `constraints.training_use`. The authorization server MAY return only a
canonical set subset of requested `permitted_classes` and MUST NOT add a class
or omit the constraint. The exact effective object is included in `grant_hash`,
token and introspection responses, management views, and runtime enforcement.
It authorizes only the defined secondary use and does not prove provider
behavior or model unlearning.

When the Approval Receipt Profile is selected, request and Grant both contain
the complete `audit.approval_receipt` object. The authorization server projects
its requirements to the returned action subset and MAY only narrow a
`user_or_app` role set or lower a maximum age as defined by that profile. The
effective object is included in `grant_hash`, token and introspection responses,
consent and management views, and protected-resource verification. It records
which producer roles the application can accept; it is not approval itself.
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

### Budget Caveats and Accounting

`constraints.budgets` is the authoritative immutable limit declaration for the
Operations Safety profile. When present, it MUST contain at least one limit
from this object:

```json
{
  "max_write_actions": 20,
  "max_tool_calls": 100,
  "max_model_tokens": 50000,
  "max_runtime_seconds": 1800,
  "max_parallel_sessions": 2,
  "cost": {
    "currency": "USD",
    "max_runtime_microunits": 4000000,
    "max_application_microunits": 1000000
  }
}
```

Every count, duration, and microunit limit MUST be an integer from `0` through
`9007199254740991`. Absence means this ASP profile imposes no cap for that
dimension; `0` prohibits new consumption. `cost`, when present, MUST contain
`currency` and at least one of `max_runtime_microunits` or
`max_application_microunits`, and MUST NOT contain other members. An omitted
partition is uncapped by this ASP profile. `currency` is an uppercase
three-letter ISO 4217 code, and one microunit is one millionth of that currency
unit. Implementations MUST use integer arithmetic, MUST NOT perform currency
conversion, and MUST NOT borrow unused runtime allowance for application cost
or vice versa. When both partitions are present, their sum is a displayable
maximum, not a shared counter.

The legacy flat members `constraints.max_actions` and
`constraints.max_cost_usd` are not aliases and are invalid in this profile.
Separating the two cost partitions is required because no single component
authoritatively observes both runtime inference/tool spend and application-side
charges. A deployment needing a shared distributed spend ledger requires a
future authenticated accounting profile.

The issuer chooses and hashes the limits, but mutable accounting belongs to the
component that authoritatively observes each dimension:

| Budget id | Authority | Unit and charge boundary |
| --- | --- | --- |
| `write_actions` | application | One accepted logical invocation in mode `reserve`, `commit`, `compensate`, or `revert`; reservation acquisition and renewal count, explicit release does not. |
| `tool_calls` | controlling runtime | One distinct dispatch to a runtime-mediated tool or ASP action endpoint; transport attempts for the same dispatch do not add charges. |
| `model_tokens` | controlling runtime | Provider-reported input plus output tokens for one model invocation, without double-counting cached or reasoning subsets. |
| `runtime_seconds` | controlling runtime | Aggregate monotonic active-work seconds across sessions under the grant. |
| `parallel_sessions` | application | Current number of authoritative sessions in `active`; this is occupancy, not cumulative consumption. |
| `runtime_cost` | controlling runtime | Provider or tool cost charged to the runtime partition, in declared microunits. |
| `application_cost` | application | Application-side price charged to the application partition, in declared microunits. |

Agent-supplied counters, token estimates, timestamps, prices, and remaining
values are never authoritative. A component MUST reject a grant when it cannot
durably meter a dimension assigned to that component in the table above. It
MUST preserve, display, and pass through limits assigned to the other authority
without inventing mutable state for them. The application MUST NOT claim runtime
token, tool, time, or runtime-cost enforcement merely because it can see Action
Requests. The runtime MUST NOT claim application write, application-cost, or
session-occupancy enforcement from local process state.

`max_write_actions` is charged exactly once when the application atomically
admits a new logical invocation after authorization, tuple, normalization,
idempotency, approval, and precondition checks. A denial before admission is
free. Once admitted, a later success, failure, partial effect, or unknown effect
does not refund the charge. An explicit reservation-release action is
idempotent safety cleanup and remains permitted while the grant is active even
when the write budget is exhausted; revocation or expiry invalidates the
reservation independently.

`max_tool_calls` counts when the runtime commits to one distinct agent-work
dispatch after local policy admits it, immediately before finalizing any parent
runtime receipt and sending the first transport attempt. This includes a read,
dry run, proposal, state-changing ASP request, or non-ASP tool call. The closed
list of mandatory safety and cleanup operations below uses a separate
control-plane dispatch path and is not `tool_calls`; those operations still
require their ordinary authorization, binding, and idempotency checks and MUST
NOT carry an unrelated agent-work effect. A local denial before the charge
boundary is free; a crash, downstream denial, or failure afterward still
counts. A transport retransmission preserving the same logical dispatch and
idempotency context is not another tool call.

For `max_model_tokens`, the runtime MUST reserve known input tokens plus the
configured maximum output before starting a model call and settle against the
provider's authoritative final usage. Cached-input, reasoning, or other detail
is a subset unless the provider explicitly reports it outside input and output
totals. When final usage is absent or uncertain, the runtime retains its
conservative reservation or stops new work; it MUST NOT assume zero.

For either cost partition, the accounting authority MUST reserve a conservative
upper-bound charge before its admission or dispatch boundary and settle the
integer microunit amount from authoritative billing or declared application
pricing. If no safe upper bound exists, the operation is rejected before that
boundary. Missing or disputed final billing retains the reservation; it is not
rounded down or transferred to the other partition.

`max_runtime_seconds` uses a monotonic clock. Within one session generation the
runtime unions overlapping intervals in which the agent, model, or tool is
actively working, including an outstanding dispatched operation, then sums
those per-session intervals across concurrent sessions. Explicit user or policy
waits and application-authoritative `interrupted` or terminal session time do
not accrue. Each session contribution is the ceiling of its cumulative unioned
duration in seconds, so splitting one interval cannot reduce usage and parallel
sessions remain additive. Clock rollback, restart, or missing duration state
fails closed and does not reset usage.

An `active` application session occupies one `max_parallel_sessions` slot.
Start and resume atomically acquire a slot across the grant and every ancestor;
an exact replay does not acquire another. Transition to `interrupted` releases
the slot only after the application fences new actions, and terminal states
release it permanently. Saturation rejects a new start or resume as
`limit_exceeded` without identifying the occupying sessions; it MUST NOT pause
or cancel a session that already owns a slot.

An accounting authority represents one counter with this canonical Budget
Counter State projection:

```json
{
  "budget_id": "write_actions",
  "authority": "application",
  "scope": "grant",
  "mode": "consumptive",
  "unit": "actions",
  "limit": 20,
  "used": 7,
  "reserved": 1,
  "remaining": 12,
  "state": "available",
  "revision": 18
}
```

`scope` is `grant` in this profile. `mode` is `consumptive` except for
`parallel_sessions`, which is `occupancy`. `unit` is respectively `actions`,
`calls`, `tokens`, `seconds`, `sessions`, or `currency_microunits`; a cost state
also carries the declared `currency`. `used`, `reserved`, `remaining`, and
`revision` are safe non-negative integers, `revision` strictly increases on
every authoritative state change, and `remaining` MUST equal
`max(0, limit - used - reserved)`. For a consumptive counter, `used` is settled
monotonic consumption. For occupancy, `used` is the current active-slot count
and decreases only after the authoritative session fence releases a slot.
`reserved` is a durable in-flight admission amount; successful settlement moves
the applicable amount to `used`, and an authoritative rejection releases it.
A consumptive counter MAY include `warning_at_remaining`, a positive safe
integer smaller than `limit` that the authority fixes for the counter's ledger
lifetime. When it is absent, consumptive state MUST be `available` exactly when
`remaining` is positive. When present, state MUST be `available` when
`remaining` is greater than the threshold and `warning` when it is positive and
no greater than the threshold. Consumptive state MUST be `exhausted` exactly
when `remaining` is zero. An occupancy counter does not carry a warning
threshold and MUST be `available` exactly when `remaining` is positive and
`saturated` exactly when it is zero. The warning threshold and mutable state are
not part of `grant_hash` and MUST NOT be copied from an untrusted caller.

Before new consumption, the authority MUST calculate a conservative maximum
increment and atomically verify and reserve it against the local grant and
every ancestor ledger. It then dispatches or linearizes the operation, settles
authoritative actual usage no greater than that reservation, and releases only
unused reservation. Exactly one of two races for the last unit can succeed.
A proven insufficient remainder returns `limit_exceeded` without changing the
counter. Arithmetic overflow, missing ledger state, or inability to calculate a
bounded reservation returns `budget_state_unavailable` without advancing
`used` or `revision`. If an external authoritative meter later reports usage
greater than the reserved upper bound, the component MUST retain the
reservation, stop matching new work, and report `budget_state_unavailable`; the
already authoritative operation outcome is not rewritten, but usage beyond the
hard limit is never treated as permitted budget consumption.

The ledger is keyed by the grant and lineage, persists for their audit lifetime,
and survives credential rotation, process restart, session interruption,
resume, and generation change. Attenuation, renewal, token exchange,
supersession that preserves authority, and child derivation remain in the same
cumulative lineage: their used, reserved, and occupied state is retained and
cannot be reset by changing a grant or credential identifier. Only a fresh
independent root grant following distinct authorization and consent can begin a
new ledger. An exact completed idempotent retry returns the original result and
receipts without a new reservation or charge, even after a budget is exhausted,
subject to current authorization and disclosure policy. An unknown outcome
retains its original charge or reservation until reconciled. Changing the
idempotency key MUST NOT create a refund or escape accounting.

The absence of another budget charge does not exempt that attempt from runtime
transport, repetition, causal-depth, or cycle guards. Conversely, a runaway
guard transition and its `session.pause` safety request do not consume or mutate
a Budget Counter State; guard and budget records remain separate authorities.

Every child charge is applied to the child and all ancestors. A child grant
bound to the same controlling runtime shares its ancestors' runtime ledgers. A
child bound to another runtime MUST NOT be issued while any runtime-authoritative
budget is present unless a future authenticated shared-accounting or explicit
allocation profile is selected; otherwise subdelegation would multiply tool,
token, time, and runtime-cost allowances. Ungranted models, tools, adapters, and
secondary runtimes remain mediated and charged by the controlling runtime.
Every `cost.currency` present in one budget lineage MUST exactly equal the
currency of every ancestor cost budget. Mixed-currency derivation MUST be
rejected rather than converted or treated as an independent allowance.

Exhaustion MUST NOT block grant revocation, `session.pause`, session
cancellation, authenticated `budget.query`, introspection, receipt retrieval,
explicit reservation release, authoritative reconciliation, or an exact
idempotent replay. Settled hard
consumptive exhaustion, where `used` equals `limit` and `reserved` is zero, is
not retryable under the same grant. Temporary admission exhaustion MAY recover
only after an authoritative reservation release. Occupancy saturation MAY
recover after an authoritative slot or occupancy reservation release only when
its limit is positive; a zero-slot limit is non-retryable under that grant. A
retry hint is advisory and never reserves that future capacity. These
operations are the closed set of mandatory safety and cleanup operations in
this profile. They do not consume a grant budget; an implementation bears their
control-plane cost separately and MUST NOT route them through an exhausted
agent-work counter.

### Grant Lifecycle

```text
discover surface
  -> verify manifest
  -> choose agent
  -> verify Agent Passport
  -> derive local consent preview and optional impact simulation
  -> confirm the canonical local consent preview
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
conforming to the Runtime Mediator Profile MUST present a local consent
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
- the verified runtime, agent, and Passport tuple, including every selected
  Passport profile and the selected Runtime Identity Profile and locally
  authenticated projection when present, plus the exact Runtime Attestation
  requirement and any current locally authenticated appraisal state when that
  optional profile is selected; and
- the complete Data Exposure Contract projection recomputed for the requested
  actions and scopes.

A Capability Match Result MAY identify the locally selected candidate, but it
is not an additional authoritative preview source. Before deriving the preview,
the runtime MUST validate the result's profile, the selected candidate's
`grant_request_hash`, complete bindings, candidate status, and freshness, then
independently recompute the request semantics, effects, approvals, and exposure
projection from the primary verified sources above. Copied matching summaries
MUST NOT replace that work.

Application-authored labels, descriptions, redaction summaries, recovery
descriptions, and Risk Explanation UI Hints are untrusted display hints. A
runtime MAY display only a valid hint selected from the exact pinned action
using the language and cache-binding rules of that feature. It MUST label the
text as application-authored, preserve the corresponding machine identifier,
classification, risk, mode, approval, effect, and recovery value, and MUST NOT
let prose replace, contradict, visually suppress, or rank verified semantics.
A detached copy in the request, Capability Match Result, agent output, or local
cache with another surface tuple is not an authoritative preview source.

The preview MUST make the following material semantics visible before the user
confirms:

- application identity, issuer, surface mode, surface version, and an
  inspectable surface hash; a proposal-only mode MUST be identified as an ASP
  authority upper bound rather than a promise that the application has no
  human or non-ASP write path;
- runtime identity, agent identity, passport hash, and the kind of passport
  evidence verified; when the Minimal Agent Passport Grant-Issuance Profile is
  selected, it MUST also show the consuming, hash, and verification profiles,
  name, uid, version, issuer, expiry, status freshness, relevant capability
  names, and the verification boundary of any executable binding; when a Runtime
  Identity Profile is selected, the preview
  MUST show the requested profile and every locally authenticated identity
  facet; if the app-scoped binding id, claims revision, or complete server
  projection is not yet available, the preview MUST label it unresolved and
  state that a second local confirmation of the returned projection is required
  before storage or use;
- when Runtime Attestation is selected, its framework and concrete profile,
  verifier id, maximum age, proof-key thumbprint, claimed Target Environment
  coverage, and whether current appraisal is accepted and fresh; if the
  app-scoped attestation binding, accepted appraisal, or server-derived
  assurance is not yet available, the preview MUST label it unresolved and
  require a second local confirmation before storage or use; raw Evidence,
  measurements, reference values, and Verifier diagnostics MUST NOT be shown;
- exact action identifiers, scopes, locations, and resource filters;
- absolute expiration time, human-readable duration, budgets, and other
  constraints;
- each selected action's risk, static execution mode, approval requirement,
  and required companion stages; when a Risk Explanation UI Hint exists, its
  selected localization MAY accompany but MUST NOT replace those values;
- maximum effect envelopes, highlighting write, shared, external, and
  irreversible effects; actions with an external effect MUST also warn that
  their actual outcome can be partial or unknown;
- required dry-run or reservation stages and available compensation or revert
  actions with their limitations;
- when the optional Impact Simulation feature is presented, its complete
  coverage and truncation metadata, exact `covered`, `not_covered`, or
  `indeterminate` outcome, and the distinction between request coverage and
  later execution admission;
- requested credential profile, credential-release policy, any parent or child
  grant fields actually present in the proposed request, and receipt
  requirements;
- when the Approval Receipt Profile is selected, its exact profile and each
  action's accepted producer roles and maximum approval age, including that a
  runtime receipt is a Grant-caveated runtime statement rather than independent
  proof of a human gesture; and
- effective data-exposure sources, class identifiers and classifications,
  redaction policy, and retention obligations; and
- when the Remote Processing Privacy Profile is selected, its exact path
  commitment, deterministic classification ceiling, every source that must fit
  that ceiling, and the distinction between application-authenticated Runtime
  Identity evidence and runtime-local downstream evidence; and
- when the Agent Training Use Policy Profile is selected, its exact permitted
  and prohibited classes by source, with training use and plaintext retention
  shown as independent dimensions.

The runtime SHOULD additionally identify its locally known operator and
processing environment. Such operator, model-provider, tool-recipient, and
concrete proof-method statements are runtime-local assertions unless backed by
separate verified evidence. They MUST be labeled with their verification status
and MUST NOT be presented as application-verified Grant Object fields. When the
Remote Processing Privacy Profile is selected, its path and ceiling are
semantic Grant fields, but provider names and recipient inventory remain local
evidence unless another profile verifies them. When Agent Training Use Policy
is selected, its effective class set is also a semantic Grant field, while a
provider's claimed enforcement remains local evidence. Without that profile,
training use is unspecified and MUST NOT be inferred from the selected path.

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
Passport consuming, hash, or verification profile, Passport artifact or
lifecycle result, executable-integrity result, Runtime Identity Profile,
binding id, claims revision or projected identity facet, Runtime Attestation
requirement, concrete profile, verifier, maximum age, proof key, stable binding,
server-derived assurance, or current accepted appraisal state, actions, scopes,
locations, resource filters, constraints, budgets, expiration, credential
profile, receipt requirements, surface mode, execution or effect declarations,
or resolved exposure contracts makes the preview stale. A stale
preview MUST be regenerated and confirmed again before a request is sent or a
returned grant is stored or used. Decline terminates the local flow; the runtime
MUST NOT continue authorization in the background.
Changing a Risk Explanation UI Hint necessarily changes the surface hash and
therefore stales the complete preview even though the prose is not authority.
The runtime does not patch the displayed hint while preserving the prior
confirmation.
Changing a runtime-local operator, provider, recipient inventory, or
enforcement-policy assertion within the same Grant-bound processing path, or a
concrete proof-method or proof-key assertion that was shown to the user, also
makes the local preview stale even when it does not alter the semantic Grant
request. That local assertion is not sent as authority to the grant issuer. A
change to the Remote Processing Privacy Profile or path value is a semantic
request change and requires a new Grant rather than this local-only refresh.

Presentation timestamps, UI session identifiers, authentication gestures, and
local confirmation timeouts are local policy and are not portable consent
evidence.

After authorization, the runtime MUST compare the returned authoritative Grant
Object with the exact locally confirmed request and the same pinned manifest.
Immediately before storing or using the result, it MUST also re-evaluate every
semantic and runtime-local input that produced the preview. A changed issuer,
surface, request, tuple, or passport validity state invalidates the issuance
result and requires a new issuer consent flow. If only a labeled runtime-local
operator, provider or same-path recipient inventory, concrete proof-method, or
proof-key assertion changed, the runtime MUST regenerate the local preview for
the returned grant and obtain fresh local confirmation before storage or use;
it does not treat that assertion as new grant authority.
If the pre-request preview marked any Runtime Identity Profile output
unresolved, the runtime MUST likewise regenerate the preview with the complete
returned projection and obtain fresh local confirmation before storage or use.
If it marked Runtime Attestation output unresolved, the runtime MUST regenerate
the preview with the returned stable binding, server-derived assurance, and
current accepted appraisal state and obtain the same second confirmation. An
unattested or non-accepted result is not a silent attenuation of an attested
request; it is a failed issuance result.
The grant issuer still derives its own consent view from that exact projection;
neither local confirmation is issuer-side authorization evidence.

The returned object adds grant-issuer output such as `grant_id`,
subject, credential binding, effective exposure projection, and `grant_hash`.
It MAY be a semantically narrower valid subset under this comparison:

- issuer, `app_id`, surface version and hash, runtime id, agent id, Passport
  consuming profile, hash profile, artifact hash, verification profile, and
  requested credential profile MUST remain exactly equal; when the
  Runtime Identity Profile was selected, a returned projection that was already
  locally authenticated MUST remain exactly equal, an unresolved projection
  requires the second confirmation above, and its repeated credential-binding
  values MUST always match;
- when Runtime Attestation was selected, the returned object MUST remove the
  request-only requirement and contain the exact stable binding, concrete
  profile, verifier, maximum age, and proof key accepted by the server; its
  repeated credential-binding values and server-derived assurance MUST agree,
  its authoritative appraisal state MUST still be accepted and fresh, and an
  initially unresolved output requires the second confirmation above;
- when the Remote Processing Privacy Profile was selected, the returned
  constraint MUST preserve the exact requested profile and path and add only
  the deterministic output-only classification ceiling; a missing, changed, or
  client-supplied ceiling is invalid rather than an attenuation;
- when the Agent Training Use Policy Profile was selected, the returned profile
  MUST remain exact and `permitted_classes` MUST be a canonical set subset of
  both the requested set and the returned effective exposure-class union; an
  added class or omitted constraint is authority widening;
- returned actions, scopes, and locations MUST be set subsets of the confirmed
  values and MUST remain closed over required companion actions;
- `expires_at` MAY be no later. A returned `budgets` object MUST retain every
  requested dimension with an equal or smaller limit; it MAY add a supported
  standard dimension as a further restriction. Cost currency MUST remain equal
  and each cost partition attenuates independently without borrowing. Returned
  `repositories` and `pull_requests` MUST remain present when requested and
  MUST be non-empty set subsets. Every other constraint MUST remain
  structurally equal unless its defining profile supplies an explicit
  attenuation order understood by the runtime; implementations MUST NOT guess
  that an unknown array, enum, or extension value is more restrictive;
- when the Approval Receipt Profile was selected, its profile MUST remain exact,
  requirements MUST project exactly to the returned approval-bearing actions,
  a `user_or_app` accepted-role set MAY be a non-empty subset, and
  `max_age_seconds` MAY be no greater; every other mode retains its fixed roles;
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
exposure projection. When Remote Processing Privacy is selected, this includes
the exact requested path commitment and server-enforced ceiling, labeled so the
commitment is not mistaken for independently verified downstream topology. It
MUST also show the effective Agent Training Use class set when that profile is
selected and warn that allowed training influence is not reversed by plaintext
deletion or revocation. When Approval Receipt is selected, it MUST show every
effective action role and maximum age and explicitly distinguish accepting a
runtime statement from application-side approval. It is not required to repeat
runtime-local operator, recipient, or processing-path assertions. It MUST NOT
trust client-supplied human-readable prose as the authoritative description.
Its final approved subset remains authoritative for issuance. The local runtime
preview reduces surprise and app-controlled UI risk, but it does not replace
issuer authentication, consent, or the application's obligation to enforce the
issued grant.

Expected effects and previews MUST be identified as maximum or predicted
semantics rather than a guarantee that a commit will occur. Compensation MUST
NOT be described as exact rollback; only a declared `revert` action with
enforceable prior-state preconditions can make that narrower claim. Missing or
unknown actions, exposure classes, source contracts, risk values, or effect
values fail closed as `surface_incompatible`; omission MUST NOT be rendered as
"no access", "no risk", or "no exposure".

This contract standardizes the semantic inputs and staleness rules for a
preview, not layout, icons, ordering, accessibility mechanisms, or biometric
confirmation. The optional Impact Simulation feature below defines a bounded
local machine projection for example actions; it does not change the required
canonical preview or turn an example into consent or authority. Localization
remains runtime-local except for selection and fallback of the optional
publisher-authored Risk Explanation UI Hint. The contract deliberately defines
no `preview_id`, consent hash, signed approval object, or portable
human-readable wire payload. Such evidence requires a separate approval
profile.

### Impact Simulation

This draft assigns the following optional core feature identifier:

```text
agent-surface/feature/impact-simulation
```

The feature is a bounded, Runtime Mediator-local supplement to one Consent
Preview. It gives deterministic examples of known manifest actions that are
covered, not covered, or not currently decidable under the exact proposed
semantic Grant request and current runtime evaluation inputs. It is not a
negotiated profile, manifest member, Grant constraint, capability, policy
decision, execution preview, approval, receipt, credential, consent record, or
prediction that an action will succeed. An implementation declares the feature
only in its conformance feature inventory; it MUST NOT add the identifier or an
Impact Simulation Result to the semantic Grant request.

An Impact Simulation Result is a closed I-JSON object. Its top level contains
exactly `feature`, `evaluated_at`, `valid_until`, `bindings`, `coverage`, and
`examples`. The `bindings`, `surface`, `delegate`, `capability_match`,
`coverage`, requested-coverage, unrequested-coverage,
example, and action objects are also closed. Embedded Effect Model and Data
Exposure Contract objects retain the closed shapes and extension rules of
their defining sections. `feature` MUST exactly equal the identifier above.
This feature defines no `profile`, `schema_version`, `simulation_id`,
simulation hash, consent hash, signature, or portable confirmation field.

Example:

```json
{
  "feature": "agent-surface/feature/impact-simulation",
  "evaluated_at": "2026-07-19T10:00:00Z",
  "valid_until": "2026-07-19T10:05:00Z",
  "bindings": {
    "surface": {
      "issuer": "https://code.example.com",
      "app_id": "code.example.com",
      "surface_version": "2026-07-19",
      "surface_hash": "sha-256:<base64url-digest>"
    },
    "grant_request_hash": "sha-256:<base64url-digest>",
    "delegate": {
      "runtime_id": "application_runtime_456",
      "agent_id": "local_agent_789",
      "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
      "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
      "passport_hash": "sha-256:<base64url-digest>",
      "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01"
    },
    "capability_match": {
      "match_id": "match_01J2E7M2V6Z91Y2R3B4C5D6E7F",
      "evaluated_at": "2026-07-19T10:00:00Z",
      "valid_until": "2026-07-19T10:05:00Z"
    },
    "agent_inventory_revision": "agents-42",
    "adapter_inventory_revision": "adapters-9",
    "local_policy_revision": "local-policy-18",
    "enterprise_policy_revision": "enterprise-policy-7",
    "user_preferences_revision": "preferences-4"
  },
  "coverage": {
    "requested": {
      "total": 2,
      "included": 2,
      "complete": true
    },
    "unrequested": {
      "total": 1,
      "included": 1,
      "truncated": false
    },
    "selection_algorithm": "highest-risk-then-action-id-v1"
  },
  "examples": [
    {
      "request_relation": "requested",
      "outcome": "covered",
      "reasons": [],
      "action": {
        "action_id": "comment.create",
        "scope": "comments.write",
        "mode": "commit",
        "risk": "public_side_effect",
        "approval": "user_or_app",
        "required_companion_action_ids": [],
        "maximum_effects": [
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
        "data_exposure": {
          "classes": ["repository.content"],
          "redaction": {"mode": "none"},
          "retention": {"mode": "transient", "delete_on_grant_end": true}
        },
        "recovery": {
          "available_action_ids": [],
          "limitations": ["irreversible", "no_recovery_action"]
        }
      }
    },
    {
      "request_relation": "unrequested",
      "outcome": "not_covered",
      "reasons": ["action_not_requested"],
      "action": {
        "action_id": "comment.propose",
        "scope": "comments.propose",
        "mode": "propose",
        "risk": "propose",
        "approval": "none",
        "required_companion_action_ids": [],
        "maximum_effects": [],
        "data_exposure": {
          "classes": ["repository.content"],
          "redaction": {"mode": "none"},
          "retention": {"mode": "transient", "delete_on_grant_end": true}
        },
        "recovery": {
          "available_action_ids": [],
          "limitations": []
        }
      }
    }
  ]
}
```

`evaluated_at` and `valid_until` are RFC 3339 UTC timestamps with the `Z`
suffix and MUST satisfy `evaluated_at < valid_until`. `valid_until` MUST be no
later than the earliest contributing Passport-status, capability-match,
inventory, policy, preference, runtime-identity, attestation, or local maximum
simulation freshness deadline. Passing that time invalidates the complete
result.

`bindings.surface` contains exactly `issuer`, `app_id`, `surface_version`, and
`surface_hash` from the verified manifest snapshot. `grant_request_hash` is
the Canonical Object Hash of the exact candidate-specific semantic Grant
request defined by Capability Matching. The runtime MUST recompute it from the
primary request and MUST NOT copy it without verification from a Capability
Match Result or caller.

`bindings.delegate` contains exactly `runtime_id`, `agent_id`,
`passport_profile`, `passport_hash_profile`, `passport_hash`, and
`passport_verification_profile`. They are the complete selected base delegate
tuple projected from `delegate.runtime`, `delegate.agent`, and the four-value
Passport tuple in the exact request. Selected runtime-identity, Runtime
Attestation, privacy, training-use, approval-receipt, and other optional
request semantics remain bound through `grant_request_hash`; their current
runtime-local inputs remain subject to the complete Consent Preview staleness
rules.

`bindings.capability_match` is REQUIRED and is either `null` or contains
exactly `match_id`, `evaluated_at`, and `valid_until` from the fresh Capability
Match Result used to identify the selected candidate. A runtime is not required
to create a Capability Match Result before this feature and uses `null` when it
did not use one; it MUST NOT omit the member. When it uses a result the binding
MUST be exact and the timestamps MUST satisfy
`capability_match.evaluated_at <= evaluated_at < valid_until <=
capability_match.valid_until`. The runtime MUST locate the exact candidate
whose agent id, Passport tuple, and `grant_request_hash` match the selected
delegate and request, then verify the complete Capability Match Result
bindings, candidate status, and reasons against the same current primary
inputs. It MUST also independently recompute the equivalent candidate decision
and every action projection from those primary inputs. A stale result, missing
exact candidate, binding mismatch, invalid causal ordering, or difference
between the retained and recomputed status or reasons invalidates the complete
simulation. A copied candidate summary is not an authoritative simulation
source.

When `capability_match` is `null`, the runtime MUST independently evaluate the
selected candidate with the same inputs, status rules, blocking-reason
vocabulary, and classification rules as the Capability Match Result Profile.
This local equivalent decision need not be serialized as a Capability Match
Result, but it MUST produce the same candidate status and blocking reasons that
a fresh exact result would have produced. Thus `null` means that no result was
used; it does not permit a weaker, action-local, optimistic, or
implementation-defined decision.

The five revision members are REQUIRED. `agent_inventory_revision`,
`adapter_inventory_revision`, and `local_policy_revision` are non-empty opaque
strings. `enterprise_policy_revision` and `user_preferences_revision` are
either non-empty opaque strings or `null` when that input does not exist. They
have the same exact-equality semantics as the Capability Match Result bindings.
A runtime that cannot name a current required input MUST NOT substitute an
empty string, old revision, or invented revision merely to produce a result.

`coverage` contains exactly `requested`, `unrequested`, and
`selection_algorithm`. Each count is a non-negative I-JSON safe integer.
`selection_algorithm` MUST equal `highest-risk-then-action-id-v1`.
`requested` contains exactly `total`, `included`, and `complete`. A valid
result exists only when the exact semantic request contains from one through
64 action identifiers: each requested action MUST appear exactly once,
`requested.included` MUST equal `requested.total`, and `complete` MUST be the
literal `true`. If the request contains zero or more than 64 actions, the
runtime MUST atomically omit the complete optional action simulation and retain
the canonical Consent Preview; it MUST NOT fabricate or sample requested
actions or claim partial coverage.

`unrequested.total` is the number of actions in the pinned manifest that are
not in the exact request. `unrequested.included` is the lesser of that value
and eight. `truncated` is `true` exactly when `total` is greater than
`included`. The runtime selects those examples by descending minimum standard
risk severity, using the Risk Taxonomy order, then by ascending unsigned
lexicographic order of UTF-8 `action_id` bytes. A supported extension risk uses
its required conservative standard mapping. An unsupported or invalid mapping
makes the action or surface `surface_incompatible`; it is not assigned a low
risk or skipped. This selection is deterministic and prevents a presenter from
choosing only benign omitted actions.

The `examples` array contains all requested examples first in ascending
unsigned lexicographic order of UTF-8 `action_id` bytes, followed by the
selected unrequested examples in their risk-descending selection order. It
contains at most 72 entries. The tuple (`request_relation`,
`action.action_id`) is unique. Every identifier MUST resolve exactly once in
the pinned manifest; a runtime MUST NOT fabricate an action, copy an action
from another snapshot, or silently substitute a similarly named companion.

Each example contains exactly `request_relation`, `outcome`, `reasons`, and
`action`. `request_relation` is `requested` or `unrequested`. `outcome` is
`covered`, `not_covered`, or `indeterminate`:

- for every requested example, selected-candidate status `compatible` maps to
  `covered` with an empty `reasons` array;
- for every requested example, selected-candidate status `incompatible` maps
  to `not_covered` with exactly the sorted unique codes from that candidate's
  definitive blocking reasons;
- for every requested example, selected-candidate status `indeterminate` maps
  to `indeterminate` with exactly the sorted unique codes from that candidate's
  indeterminate blocking reasons; and
- every unrequested example remains `not_covered` and its `reasons` array is
  exactly `["action_not_requested"]`.

The mapping is candidate-wide: every requested example in one result has the
same outcome and `reasons` array. It deliberately projects only the decisive
blocking codes after the complete candidate status has been determined.
Advisory reasons MUST NOT be serialized. For an incompatible candidate,
indeterminate blocking reasons that were overridden by a definitive blocking
reason MUST NOT be serialized; for an indeterminate candidate, no definitive
blocking reason can exist. Sorting uses ascending unsigned lexicographic order
of UTF-8 code bytes, and duplicate codes caused by different reason subjects
collapse to one string. The reason subject and repeated occurrences are
deliberately lost only after the candidate-wide decision; their omission MUST
NOT be used to calculate that decision action by action.

`covered` does not mean that a Grant will be issued or that a later invocation
will pass approval, active-Grant, session, input, precondition, reservation,
budget, capacity, current policy, or final application checks.
`indeterminate` MUST NOT be presented optimistically as covered or definitively
denied.

`reasons` is a sorted array of unique machine reason-code strings. Except for
`action_not_requested`, its complete core vocabulary and classifications are
exactly those defined by **Candidate Status and Reasons** for a Capability Match
Result:

| Classification | Allowed core reason codes |
| --- | --- |
| Indeterminate | `passport_profile_unsupported`, `passport_status_unavailable`, `runtime_identity_unavailable`, `runtime_attestation_unavailable`, `input_unknown` |
| Definitive | `passport_missing`, `passport_invalid`, `capability_missing`, `adapter_unavailable`, `schema_unsupported`, `execution_stage_unsupported`, `scope_unavailable`, `approval_unsupported`, `risk_denied`, `effect_unsupported`, `recovery_unsupported`, `data_exposure_unsupported`, `retention_unsupported`, `remote_processing_unsupported`, `training_use_unsupported`, `sandbox_unsatisfied`, `runtime_identity_invalid`, `runtime_attestation_unsupported`, `policy_denied` |
| Impact Simulation-specific definitive | `action_not_requested` |

The runtime MUST implement the complete vocabulary above and MUST NOT create a
local alias for a Capability Match Result reason. `action_not_requested` is
valid only for an unrequested `not_covered` example, and it is the sole reason
for such an example; candidate blocking or advisory codes MUST NOT be copied to
an unrequested action because the candidate decision covers the exact requested
set. A missing requested scope, unclosed required companion set, malformed
request, or stale primary input invalidates or stales the complete simulation
under the primary request and freshness rules; it MUST NOT be represented by a
per-example reason.

An extension reason code MUST be a collision-resistant URI and retains the
definitive or indeterminate classification assigned by its supported Capability
Match Result profile. An unknown blocking extension code defaults to
indeterminate, as it does in a Capability Match Result. A supported definitive
extension blocking code is included for an incompatible candidate; a supported
or unknown indeterminate extension blocking code is included for an
indeterminate candidate. Advisory extension codes are omitted. A `covered`
requested example has no reason. A requested `not_covered` example has at least
one definitive reason. An `indeterminate` example has at least one
indeterminate reason and no definitive reason. Human-readable explanations are
runtime-local presentation, not members of this object.

The `action` object contains exactly `action_id`, `scope`, `mode`, `risk`,
`approval`, `required_companion_action_ids`, `maximum_effects`,
`data_exposure`, and `recovery`. The runtime MUST independently copy or derive
these fields from the exact pinned action and request:

- `scope`, `mode`, `risk`, and `approval` repeat the manifest values without
  relabeling or attenuation;
- `required_companion_action_ids` is the sorted unique recursive closure of
  required companion actions for that action, excluding the action itself;
- `maximum_effects` is the complete manifest effect envelope in declaration
  order, or an empty array when the action correctly omits `effects`;
- `data_exposure` is the complete manifest-pinned action exposure contract;
  for a requested action it MUST equal the corresponding source contract in
  the recomputed proposed Data Exposure projection, while for an unrequested
  action it describes only hypothetical potential disclosure and MUST NOT be
  presented as effective Grant exposure; and
- `recovery` contains exactly `available_action_ids` and `limitations`.
  `available_action_ids` is the exact sorted unique set of recovery actions
  declared for the action in the same retained surface that are also present
  in the proposed request and its required companion closure. It is sorted by
  ascending unsigned lexicographic order of UTF-8 action-id bytes and contains
  each action exactly once even when several relationships name it. The actions
  are only potentially available: inclusion is not issuance, approval, current
  authority, satisfied recovery preconditions, or a promise of success.
  `limitations` is derived exactly from the retained declaration:

  - `irreversible` is present if and only if at least one
    `maximum_effects` entry has the effective standard reversibility
    `irreversible`;
  - `external_outcome_may_be_unknown` is present if and only if at least one
    `maximum_effects` entry has the effective standard boundary `external`;
  - `recovery_window_limited` is present if and only if the action declares at
    least one outbound `execution.recovery_actions` relationship with a finite
    positive `recovery_window_seconds`; and
  - `no_recovery_action` is present if and only if the action has mode
    `commit`, has a non-empty `maximum_effects` array, and declares no outbound
    `execution.recovery_actions` relationship.

  For a standard effect value, its effective standard value is the literal
  value. For a supported extension value, the runtime MUST use the defining
  specification's required conservative mapping to the standard
  `reversibility` or `boundary` value before applying these conditions. A
  missing, invalid, or unsupported conservative mapping makes the action or
  surface `surface_incompatible`; the runtime MUST NOT omit a limitation or
  derive a reassuring lower-severity value.

  These four core codes appear if and only if their conditions apply; absence
  of a recovery action from the proposed request does not create
  `no_recovery_action` when a valid relationship exists in the retained
  manifest. A supported collision-resistant URI limitation code is included if
  and only if its defining profile says its condition applies to the retained
  declaration. Unsupported extension limitation semantics make the action or
  surface `surface_incompatible`; they are not silently omitted. The complete
  `limitations` array is sorted by ascending unsigned lexicographic order of
  UTF-8 code bytes and contains each applicable code exactly once.

  The `irreversible` and `external_outcome_may_be_unknown` tests apply to the
  maximum effects of every state-changing mode. `no_recovery_action` does not
  apply to a `reserve` action, including reservation acquire, renew, or release:
  its cleanup contract is represented by the required companion closure and
  the reservation release, consumption, invalidation, and expiry semantics.
  Nor does it apply to `compensate` or `revert`; those actions are already
  independently authorized recovery stages, and this projection MUST NOT infer
  recursive recovery for them.

  Actions in mode `read`, `dry_run`, or `propose` have no committed
  `maximum_effects` and cannot declare a recovery relationship; therefore both
  `available_action_ids` and `limitations` are empty. Both arrays remain
  present for every mode. They are a canonical declaration projection, not a
  recovery promise; the canonical Consent Preview continues to show the exact
  effect ids, recovery modes, windows, and preconditions. An unavailable
  recovery action or irreversible effect MUST NOT be described as rollback.

A malformed action, unresolved companion, unclosed requested subset, unknown
scope, unsupported risk or effect mapping, missing exposure contract, or
inconsistent recovery relationship is a failure of the primary surface or
request, not an `indeterminate` simulation example. The runtime follows the
ordinary fail-closed `surface_incompatible` or request-invalid path and MUST
NOT use an Impact Simulation Result to make the primary input appear usable.

This v1 feature produces action examples only. It does not define a mapping
from a Grant resource constraint to a particular action-input field. A runtime
MUST NOT invent or probe an out-of-filter resource, contact the application to
discover one, infer a constraint-to-input binding from field names or prose, or
claim that a concrete resource would be allowed or denied. Exact resource
filters remain visible in the canonical Consent Preview. A future profile can
define concrete resource examples only with a machine-readable binding and
non-enumerating privacy rules.

The runtime derives the result without invoking an application action, sending
an Action Request, running a `dry_run`, validating an application state
precondition, acquiring a reservation, consuming budget or capacity, creating
a session, requesting approval, or contacting an action endpoint. In
particular, `maximum_effects` is a static manifest envelope, not the
application-produced `expected_effects` for one input and state snapshot.

The complete result remains inside the user-controlled Runtime Mediator
boundary. The runtime MUST NOT send it to the application or authorization
server as request input, expose it to an agent or Agent Adapter, copy it into a
Grant, credential, Policy Decision, approval or action receipt, Human
Elicitation request or response, Action Request or Response, prompt, tool
instruction, or privileged instruction channel. A component that nevertheless
receives a detached out-of-band result MUST discard it and MUST NOT treat it as
authority, consent, approval, policy evidence, or a reason to skip an ordinary
check. If a sender embeds the feature identifier or result in a closed ASP
request, Grant, receipt, approval, policy, action, or elicitation object that
does not define that member, the receiver MUST reject the complete enclosing
object under its ordinary structural validation; it MUST NOT remove only the
unexpected member and continue.

Risk Explanation UI Hint prose is not part of the result and MUST NOT affect
outcome, reasons, inclusion, ordering, or truncation. A presenter MAY attach
one valid selected hint only after validating the complete machine result and
retrieving the hint independently from the same pinned action. It MUST label
the text as publisher-authored and keep it distinct from the runtime-derived
example. A malformed or stale hint is suppressed under its own rules without
changing the simulation.

The examples supplement rather than replace the canonical Consent Preview.
Every requested action, companion stage, scope, location, resource filter,
constraint, material effect, approval, recovery limitation, and exposure
source remains inspectable before confirmation. The presenter MUST describe
`covered` as no stronger than "would be covered by this proposed Grant" and
MUST NOT label it "safe", "approved", "will succeed", or equivalent. If no
unrequested action exists, the result honestly contains no unrequested example;
the runtime MUST NOT invent a denial or present that absence as unlimited
authority.

The result has no independent confirmation or authority lifecycle. It is
derived and presented as part of one local Consent Preview. Any condition that
makes that preview stale also makes the complete simulation stale. In
addition, expiry or any change to its surface, request hash, delegate tuple,
Capability Match Result binding, agent or adapter inventory, local or
enterprise policy, user preferences, selected action, outcome, or projected
machine semantics invalidates the complete result. The runtime MUST regenerate
it from all current sources; it MUST NOT patch one example, carry forward the
unrequested sample, or preserve confirmation of the old preview.

A structurally invalid, detached, expired, stale, partially inconsistent,
incorrectly ordered, incorrectly counted, or incorrectly truncated result MUST
be atomically suppressed. The runtime falls back to the complete canonical
Consent Preview and MUST NOT render only the fields or examples it recognizes.
Suppression of this optional supplement does not repair an invalid primary
manifest, request, tuple, policy, or exposure projection.

After local confirmation and dispatch of the issuance request, the simulation
is only transient local presentation state. It MUST NOT be used as the active
Grant view. A returned Grant that is a valid narrower subset does not inherit
examples for omitted authority; the runtime derives active management and use
from the authoritative returned Grant and retained manifest. Rejection,
expiry, revocation, renewal, exchange, child derivation, or a later surface
version MUST NOT reactivate, mutate, or reinterpret the pre-issuance result.
Deriving post-issuance or historical examples is outside this feature.

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
token to an agent, passport, and policy. To satisfy the Action Executor
Profile, the application MUST also establish the runtime, agent,
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
and manages Grant Credentials. The credential-protected `agent_api` endpoints
form one logical resource server under `credential_audience`; the action
endpoint additionally enforces the semantic Agent Grant for every action, while
budget and session endpoints expose only their closed safety operations.

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
      "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
      "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
      "passport_hash": "sha-256:<base64url-digest>",
      "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01"
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
      "budgets": {
        "max_write_actions": 20
      }
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
  `passport_ref` and the request-only `runtime_identity_profile` selector. It
  MUST NOT contain the server-derived `runtime_identity` projection in a
  request. When the Minimal Agent Passport Grant-Issuance Profile is selected,
  it MUST also contain the exact `passport_profile`, `passport_hash_profile`,
  and `passport_verification_profile` values required by that profile. When
  Runtime Attestation is selected, it MUST contain the request-only closed
  `runtime_attestation_requirement` object and a runtime-identity selector; it
  MUST NOT contain `runtime_attestation`, assurance output, appraisal state,
  hashes, raw Evidence, or raw Attestation Results.
- `resource_server` MUST contain `app_id`, `issuer`, `surface_version`, and the
  verified `surface_hash`.
- `constraints` MUST contain `expires_at`; other fields use the semantics of the
  Agent Grant object. When Remote Processing Privacy is selected, it MUST also
  contain the closed request-only `remote_processing` object with exact
  `profile` and `path`, the request MUST select Runtime Identity, and the client
  MUST NOT supply `classification_ceiling`. When Agent Training Use Policy is
  selected, `constraints` MUST also contain its closed `training_use` object
  with the exact profile and canonical `permitted_classes` request set.
- `credential_profile` MUST be `compatibility_bearer` or `proof_bound` and maps
  to the credential profiles defined in this draft.
- A request for action authority MUST contain non-empty RFC 9396 common
  `locations` and `actions` arrays of published action endpoints and Agent
  Surface action identifiers; omission requests no action authority. The
  granted values are authoritative allow-lists and every
  invoked action MUST be a member. The authorization applies to the product of
  the granted actions, locations, scopes, and resource filters; every allowed
  combination MUST be published by the surface and semantically compatible.
- `grant_id`, `grant_hash`, `subject`, `credential_binding`, `data_exposure`,
  `delegate.runtime_identity`, `delegate.runtime_attestation`, and
  `constraints.remote_processing.classification_ceiling` MUST NOT be supplied
  by the client in an authorization request; they are authorization-server
  output.
- A client selecting Approval Receipt MUST supply the exact closed
  `audit.approval_receipt` profile and requirement projection for its requested
  actions. The authorization server independently validates those roles and
  maximum ages against the pinned manifest and its own acceptance policy.
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
a Passport tuple that is unadvertised, unsupported, stale, or not independently
verified, an unadvertised or unsatisfied runtime identity profile, a
client-supplied runtime identity projection, an unadvertised, unsupported, or
non-accepted Runtime Attestation requirement, client-supplied attestation
output, an unadvertised Remote Processing Privacy profile, a client-supplied
ceiling, a path inconsistent with the controlling Runtime Identity, an
effective exposure above the deterministic ceiling, an unadvertised or
malformed Agent Training Use Policy, an unknown, duplicate, non-canonical, or
unexposed requested training class, an unadvertised or malformed Approval
Receipt profile, an incomplete or incompatible approval requirement projection,
an action set that is not closed over required companion dependencies, or
constraints that are invalid for the published surface. It MUST use the RFC 9396
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
verified copy of the request and pinned manifest. When a Runtime Identity
Profile is selected, that view MUST include the complete sanitized projection
the server derived from the authenticated runtime record; raw identity evidence
remains hidden. When the Minimal Agent Passport Grant-Issuance Profile is
selected, the view MUST include the server's independently verified Passport
identity, tuple, expiry, status freshness, relevant capability names, and
verification boundary without exposing the raw artifact. When Runtime
Attestation is selected, the view MUST additionally show its concrete profile,
opaque verifier id, maximum age, proof-key binding, claimed Target Environment
coverage, server-derived assurance, and current accepted state without exposing
Evidence, measurements, reference values, or Verifier diagnostics. When Remote
Processing Privacy is selected, the view MUST additionally show the exact path,
deterministic ceiling, and complete exposure closure while distinguishing the
runtime commitment from application-verified Runtime Identity evidence. When
Agent Training Use Policy is selected, the view MUST show the requested and
effective permitted classes by source, every prohibited class, and the durable-
influence warning independently of plaintext retention. The user MAY
approve a strict subset. The authorization server
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
the authorization server. The authorization server and resource server MUST
retain or receive the same
granted object for later action verification and introspection.
When the request selected a Runtime Identity Profile, the returned object MUST
remove the request-only selector and contain the exact server-derived
`delegate.runtime_identity` and repeated credential-binding values.
When the request selected Runtime Attestation, the returned object MUST remove
`runtime_attestation_requirement`, contain the exact stable
`delegate.runtime_attestation` object, and repeat its binding, profile,
verifier, and proof-key values in `credential_binding`. The current accepted
appraisal remains authoritative mutable state outside that returned object.
When the request selected Remote Processing Privacy, the returned constraints
MUST preserve its exact requested profile and path and add the deterministic
`classification_ceiling`; the authorization server MUST NOT change the path or
omit the complete constraint.
When the request selected Agent Training Use Policy, the returned constraints
MUST preserve its exact profile and a canonical `permitted_classes` subset of
the request and returned exposure union; the authorization server MUST NOT add
a class or omit an explicit empty result.
When the request selected the Minimal Agent Passport Grant-Issuance Profile,
the returned delegate and credential binding MUST preserve its exact four-value
Passport tuple.

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
&resource=https%3A%2F%2Fcode.example.com%2Fagent-api
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
- `resource` MUST contain exactly the pinned manifest
  `agent_api.credential_audience`. An `audience` value MAY additionally name
  that same logical protected resource but MUST NOT add another target. Action
  `locations` remain a separate RAR allow-list and MUST NOT replace or widen
  the credential audience.
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
exact current accepted Runtime Attestation record when selected, agent and exact
current Passport tuple, resource, requested action and location allow-lists,
scopes, constraints, and credential profile. Returned `actions` and `locations`
MUST be subsets of the source authorization. The exchange MUST NOT add a
stronger companion stage under a shared scope, increase authority, widen
resources, relax approval or receipt requirements, extend beyond the approved
expiration, or replace `proof_bound` with `compatibility_bearer` without fresh
user consent. Any attenuated action subset MUST remain closed over its required
companion dependencies; otherwise the exchange MUST reject it rather than add
missing stages.

When the source Grant selected Remote Processing Privacy, token exchange MUST
preserve its exact profile and path, recompute the same deterministic ceiling,
and verify the attenuated source closure against it. A different path is not an
OAuth attenuation and requires a new semantic Grant request and fresh consent.
The exchange MUST NOT omit the constraint or treat a lower apparent Runtime
Identity locality as proof that the downstream path changed safely.

When the source Grant selected Agent Training Use Policy, token exchange MUST
retain the profile and return a `permitted_classes` set no wider than the source
set intersected with the exchanged Grant's effective exposure classes. It MUST
retain an explicit empty result. When the source omitted the profile, exchange
MAY add the empty form as a new restriction only if the source selected Remote
Processing Privacy and the exchange retains its exact profile and path. In
every other case, adding this profile or a non-empty training permission
requires a fresh independent authorization and consent flow.

When the source Grant selected Approval Receipt, token exchange MUST retain the
exact profile, project requirements to the exchanged action subset, preserve
fixed-role modes, and only narrow a `user_or_app` accepted-role set or lower a
maximum age. It MUST NOT reuse any source Approval Receipt: the exchanged
Grant's new `grant_hash`, and potentially its session and runtime tuple, require
fresh approval evidence.

RFC 8693 does not itself create lifecycle linkage between input and output
tokens. This ASP profile does: the authorization server MUST record the source
authorization or parent grant from which the Agent Grant was derived. Revoking
or invalidating that source authority MUST revoke or suspend every derived Agent
Grant unless an independently approved grant replaced it.

Issuance also MUST preserve cumulative caveats across that derivation graph.
Every application-authoritative charge or occupied session slot MUST apply to
the derived grant and every ancestor application ledger; every
runtime-authoritative charge MUST do the same in the controlling runtime's
lineage ledger. The authorization server MUST preserve the complete lineage and
MUST reject a cross-runtime child that cannot share or allocate the required
runtime accounting. Repeating an exchange therefore cannot multiply write,
tool, token, time, session, or partitioned cost budgets. The authorization
server MUST treat semantically equivalent exchanges with the
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
        "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
        "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
        "passport_hash": "sha-256:<base64url-digest>",
        "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01"
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
        "budgets": {
          "max_write_actions": 20
        }
      },
      "credential_profile": "proof_bound",
      "credential_binding": {
        "method": "dpop",
        "runtime_id": "application_runtime_456",
        "agent_id": "local_agent_789",
        "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
        "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
        "passport_hash": "sha-256:<base64url-digest>",
        "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
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

A credential bound to a Runtime Identity Profile is inactive whenever the
authorization server cannot prove that the exact runtime binding and claims
revision remain active. Temporary evidence unavailability, suspension, and
revocation all use the same `{"active":false}` response and do not disclose
which identity check failed.

A credential bound to the Minimal Agent Passport Grant-Issuance Profile is
likewise inactive whenever the exact artifact, verification profile, issuer
trust, expiry, revocation state, or status freshness cannot be established.
The inactive response MUST NOT reveal which Passport check failed.

A credential bound to Runtime Attestation is inactive whenever the exact
attestation binding is not in current `accepted` state or its freshness,
Verifier, proof key, runtime-identity revision, appraisal policy, or reference
values cannot be established. The inactive response MUST NOT distinguish
rejection, indeterminate appraisal, staleness, revocation, or supersession.

For an active Grant Credential, the response MUST include the RFC 7662 fields
`active`, `client_id`, `scope`, `token_type`, `exp`, `iat`, `sub`, `aud`, and
`iss`, plus the ASP fields `grant_id`, `grant_hash`, `resource_server`, `delegate`,
`constraints`, `credential_binding`, and `authorization_details`. An active
proof-bound credential MUST additionally include the method-specific standard
`cnf` confirmation member. The `sub` value SHOULD be a stable app-scoped
pseudonymous user identifier. `client_id` identifies the OAuth client;
`delegate.runtime` is the authoritative ASP runtime binding and MAY differ from
`client_id`. `aud` MUST equal the `agent_api.credential_audience` in the
manifest snapshot selected by the returned Grant's `surface_hash`.

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
  "aud": "https://code.example.com/agent-api",
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
    "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
    "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
    "passport_hash": "sha-256:<base64url-digest>",
    "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01"
  },
  "constraints": {
    "repositories": ["example-org/example-repo"],
    "pull_requests": [13],
    "expires_at": "2026-06-25T20:00:00Z",
    "write_approval": "required",
    "budgets": {
      "max_write_actions": 20
    }
  },
  "credential_binding": {
    "method": "dpop",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
    "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
    "passport_hash": "sha-256:<base64url-digest>",
    "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
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
        "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
        "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
        "passport_hash": "sha-256:<base64url-digest>",
        "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01"
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
        "budgets": {
          "max_write_actions": 20
        }
      },
      "credential_profile": "proof_bound",
      "credential_binding": {
        "method": "dpop",
        "runtime_id": "application_runtime_456",
        "agent_id": "local_agent_789",
        "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
        "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
        "passport_hash": "sha-256:<base64url-digest>",
        "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
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
- when Runtime Attestation is selected, the exact stable attestation binding,
  concrete profile, verifier id, proof-key thumbprint, and access to current
  authoritative appraisal state;
- the bound agent identity and exact Passport tuple required by its selected
  profile; and
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

When the parent selected a Runtime Identity Profile, a child bound to the same
runtime MUST retain the exact active runtime identity projection or obtain a
new Grant after a material identity change. A child bound to another runtime
MUST use that runtime's independently authenticated projection and binding; it
MUST NOT inherit the parent's authentication method, management posture,
locality, assurance, binding id, or claims revision.

When the parent selected the Remote Processing Privacy Profile, every ungranted
downstream component remains part of the parent's complete processing path.
A child Grant selecting the profile MUST resolve its own path and receive its
own deterministic ceiling; it MUST NOT inherit the parent's path commitment as
evidence. This profile does not project a parent source into the child's
effective `data_exposure`, so a parent MUST NOT forward application-originated
payloads or equivalent representations to a separately granted child. The
child obtains such data from its own independently authorized application
source. Path enum values have no attenuation order, so an issuer MUST NOT
rewrite one value into another while deriving a child.

When the parent selected the Agent Training Use Policy Profile, a child MUST
retain the exact profile and a canonical `permitted_classes` set no wider than
the parent set intersected with the child's complete effective exposure-class
union. An empty intersection remains an explicit empty array; the child MUST
NOT omit the constraint or add a class. When the parent omitted the profile, a
derived child MAY add the empty-array form only if the parent selected Remote
Processing Privacy and the child retains its exact profile and path value while
deriving its own binding and ceiling. Otherwise the child needs a fresh
independent root Grant and consent. When the parent omitted this profile, a
non-empty training permission requires that fresh flow and is not child
attenuation.

When the parent selected Runtime Attestation, every child MUST obtain a new
challenge and accepted appraisal bound to the child's exact
`grant_request_hash`, producing a child-specific stable binding and mutable
record. A same-runtime child MAY retain the exact Runtime Identity projection,
concrete profile, verifier, maximum age, proof key, and sanitized assurance when
they remain current, but it MUST NOT reuse the parent's binding, Evidence, or
Result. A child bound to another runtime MUST instead use that runtime's
independently authenticated identity, proof key, Evidence, and assurance.
Parent Grant revocation still cascades through the ordinary Semantic Grant
Revocation Transition. Revocation or invalidation of a shared runtime identity,
Attester, proof key, Verifier, policy, endorsement, or reference value makes
every dependent child-specific appraisal inactive.

Child budget limits MUST retain every inherited member with an equal or smaller
limit, and every charge or occupied slot consumes the child and ancestor
ledgers. A child MAY add a supported standard dimension as a further
restriction. Every child `cost.currency` MUST exactly equal every ancestor
`cost.currency`; mixed-currency derivation is invalid. A child bound to the same
runtime shares that runtime's lineage ledger. When the child would bind a
different runtime and any `max_tool_calls`, `max_model_tokens`,
`max_runtime_seconds`, or runtime-cost partition is present in its ancestry,
the application MUST reject issuance because this draft defines no
cross-runtime shared-accounting or allocation profile.

### Grant Verification

Applications MUST verify every action against grant state:

- grant exists and is active
- the credential audience exactly matches `agent_api.credential_audience` in
  the verified manifest snapshot selected by the grant
- recomputed `grant_hash` matches both the presented action context and current
  authoritative Grant Object
- `resource_server.surface_hash` matches the retained, verified manifest
  snapshot used to interpret the action and its schemas
- the retained manifest declares a supported `surface_mode`; when it is
  `proposal_only`, the complete action catalog satisfies that mode, the Grant
  explicitly denies credential release, the requested action's manifest-
  declared `execution.mode` is `read` or `propose`, and the request repeats
  that exact mode
- grant credential or proof is valid
- grant is bound to the user
- grant is bound to the runtime
- when `delegate.runtime_identity` is present, its complete projection and
  repeated credential-binding values match the authoritative active runtime
  record at the exact claims revision
- when `delegate.runtime_attestation` is present, its complete stable object
  and repeated credential-binding values match the exact authoritative binding,
  the proof-key cross-binding is valid, and the mutable appraisal record is
  current `accepted` at the required freshness, policy, and reference values
- when `constraints.remote_processing` is present, its profile and path are
  supported, its output-only ceiling is the exact deterministic value, the
  controlling Runtime Identity satisfies the necessary predicate, and every
  class in the complete effective exposure closure is at or below that ceiling
- when `constraints.training_use` is present, its profile is supported, its
  `permitted_classes` value is a canonical set no wider than the approved
  request and complete effective exposure-class union, and every authoritative
  Grant, token, introspection, and stored-state copy matches the hashed value
- grant is bound to the agent and exact Passport tuple, and the independently
  verified artifact remains unexpired, unrevoked, and fresh under its selected
  verification profile
- credential-binding method and proof-of-possession requirements are satisfied
- for DPoP, the proof is request-bound and within the limited acceptance window;
  when `jti` replay tracking is enabled, its `jti` has not already been accepted;
  reuse of a valid server nonce is not rejected by itself
- for mTLS, the presented certificate matches the certificate bound to the token
  and the binding has not been invalidated; reuse of the matching certificate is
  not rejected by itself
- for a proof-bound server session, the session is active, bound to the grant
  and runtime, and authenticated with the bound key or channel credential
- the requested action identifier resolves exactly once in the retained pinned
  manifest, the grant contains a non-empty `actions` allow-list containing that
  identifier, and the action is served at a granted `location` and remains
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
- every application-authoritative write, session-occupancy, and
  application-cost reservation fits the grant and all ancestor ledgers
- when `audit.approval_receipt` is present, its exact profile and per-action
  requirement are supported and every required approved receipt is complete,
  authenticated, unexpired for first admission, bound to the exact invocation,
  and represented by the role map required for the manifest approval mode
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
- `surface_mode` is supported and the selected action and credential-release
  policy satisfy its surface-wide bound
- local user has not revoked the app, runtime, or agent
- the exact Grant-bound Agent Passport tuple remains valid under the locally
  supported consuming, hash, verification, status, and integrity profiles
- when Runtime Attestation was selected, the returned stable binding, profile,
  verifier, proof key, assurance, and current privacy-filtered accepted state
  match the locally confirmed requirement without fallback
- requested action is compatible with the verified Agent Passport capability
  set without treating a declaration as Grant authority
- local policy allows the action
- local approval is present when required
- every runtime-authoritative tool, model-token, runtime-time, and runtime-cost
  reservation fits the grant and all ancestor ledgers
- durable lineage-delegate and session runaway-guard state for the exact Grant,
  delegate, session, and generation is available and the next scheduling or
  transport step fits every applicable finite guard
- action input matches the declared schema
- execution mode, context, and hashes match the pinned action declaration
- preview evidence is current and any required reservation belongs to the
  bound tuple
- expected effects and recovery limitations are presented before approval
- secrets and credentials are not exposed to the agent
- any subagent, tool, adapter, remote model, or secondary runtime remains
  subject to the same runtime mediation and does not receive implicit authority
- when the Remote Processing Privacy Profile is selected, the actual complete
  data-bearing path still satisfies the exact Grant commitment immediately
  before every disclosure, every class fits the effective ceiling, and an
  unknown recipient or enforcement state fails closed
- when the Agent Training Use Policy Profile is selected, a source is withheld
  from training unless its complete class set is a subset of the effective
  `permitted_classes`, the Remote Processing path remains valid, and every
  downstream recipient enforces an equal or stricter training policy

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

- the manifest's `surface_mode` upper bound
- action `capability_hint`
- action schemas
- required scopes
- risk labels
- approval modes and the selected Approval Receipt role and maximum-age rules
- execution modes and required companion stages
- declared effect envelopes and effect schemas
- declared data classes, redaction, and retention obligations
- the complete selected processing path, its Remote Processing Privacy
  classification ceiling, and current recipient-policy enforcement capability
- the requested Agent Training Use class set, complete class set of every
  source, and current downstream training-policy enforcement capability
- reservation requirements and available recovery actions
- Agent Passport capabilities
- Agent Passport security policy
- selected Runtime Attestation concrete profile and the runtime's current
  ability to generate profile-conforming Evidence with the selected proof key
- local runtime adapter availability
- user preferences
- enterprise policy

Risk Explanation UI Hint prose is not a matching input. A matcher MUST NOT use
its presence, wording, language coverage, or apparent sentiment to change
candidate status, reasons, ranking, required approval, or the canonical risk
summary. A local user interface can attach the selected publisher hint only
after matching, from the still-current pinned manifest snapshot.

Impact Simulation is a downstream local presentation feature, not a matching
input, candidate-ranking signal, or Capability Match Result member. When a
runtime binds a result to a selected Capability Match Result, it can use the
fresh candidate status and machine reasons only after exact verification and
independent recomputation of the same candidate decision. Every requested
example projects that one decision; the runtime MUST NOT rerun matching per
action or serialize advisory or overridden reasons. It also independently
recomputes every example's request relation, action semantics, effect envelope,
exposure, companion closure, and exact recovery projection. Adding, removing,
or reordering an example MUST NOT change candidate status or
`grant_request_hash`.

This draft standardizes those outputs with the local-only Capability Match
Result Profile:

```text
https://github.com/0al-spec/agent-surface/profiles/capability-match-result/v1
```

It also defines this Canonical Object Hash domain for the exact semantic Grant
request evaluated by the matcher:

```text
https://github.com/0al-spec/agent-surface/hash/grant-request/v1
```

### Semantic Grant Request Hash

The hashing view is one complete candidate-specific semantic Agent Grant request
before any authorization-server output is added. For RFC 9396, the runtime
starts with the sole Agent Grant authorization-details object and removes only
its `type` member. `locations`, `actions`, `delegate`, `resource_server`,
`scopes`, `constraints`, `credential_profile`, and `audit`, including the exact
candidate agent and Passport tuple, every selected profile, and the complete
request-only Runtime Attestation requirement, remain in the hashing view. A
selected Remote Processing Privacy constraint contributes its exact request
`profile` and `path`; the server-only `classification_ceiling` is absent.
Selected Agent Training Use Policy contributes its exact request `profile` and
canonical `permitted_classes` set; the set remains present when empty.
A selected Approval Receipt Profile contributes its exact profile and complete
per-action role and maximum-age requirement projection.
Another issuance model MUST construct the same semantic object.

A multi-candidate match MUST construct and hash one complete request for each
candidate. All non-candidate request semantics and the controlling runtime
binding MUST be identical across those requests; `delegate.agent` and the
Passport tuple MUST equal that candidate. The matcher MUST NOT hash a
candidate-independent template or one candidate's delegate and represent the
result as binding the other candidates.

`grant_id`, `grant_hash`, `subject`, `credential_binding`, `data_exposure`, and
server-derived `delegate.runtime_identity`, `delegate.runtime_attestation`, and
`constraints.remote_processing.classification_ceiling` are invalid in a
request and MUST NOT be silently removed from malformed input merely to compute
a hash. OAuth parameters, redirect URIs, PKCE values, client
authentication, user-interface labels, raw Passport artifacts, and local policy
state are not semantic Grant Object members and are not included.

The runtime computes each candidate's `grant_request_hash` with the Canonical
Object Hash Profile and the domain above. The value identifies the exact
authority request for that candidate; it does not authorize that request or
prove consent. A change to common request semantics requires every candidate
hash and the complete match result to be recomputed. A candidate tuple change
requires a new candidate entry and hash.

For the hash-layer test view `{"delegate":{"runtime":"r"}}`, the canonical
wrapper is:

```json
{"domain":"https://github.com/0al-spec/agent-surface/hash/grant-request/v1","object":{"delegate":{"runtime":"r"}}}
```

Its hash is
`sha-256:NIahpleJauoH9OEqZhL1Spqj6oP1r78nA1A7GCwJnYA`. The view is intentionally
not a complete valid Grant request; the vector fixes only domain separation and
hash encoding.

### Capability Match Result Object

A Capability Match Result is a closed I-JSON object with this wire shape:

```json
{
  "profile": "https://github.com/0al-spec/agent-surface/profiles/capability-match-result/v1",
  "match_id": "match_01J2E7M2V6Z91Y2R3B4C5D6E7F",
  "evaluated_at": "2026-07-14T10:00:00Z",
  "valid_until": "2026-07-14T10:05:00Z",
  "bindings": {
    "surface": {
      "issuer": "https://code.example.com",
      "app_id": "code.example.com",
      "surface_version": "2026-06-25",
      "surface_hash": "sha-256:<base64url-digest>"
    },
    "runtime": {
      "runtime_id": "application_runtime_456",
      "runtime_identity_profile": "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1",
      "binding_id": "rbind_01J2D7M2V6Z91Y2R3B4C5D6E7F",
      "claims_revision": 3
    },
    "agent_inventory_revision": "agents-42",
    "adapter_inventory_revision": "adapters-9",
    "local_policy_revision": "local-policy-18",
    "enterprise_policy_revision": "enterprise-policy-7",
    "user_preferences_revision": "preferences-4"
  },
  "candidates": [
    {
      "agent_id": "local_agent_789",
      "passport": {
        "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
        "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
        "passport_hash": "sha-256:<base64url-digest>",
        "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
        "status_valid_until": "2026-07-14T10:05:00Z",
        "agent_binding": "document_only",
        "integrity_profile": null,
        "capability_names": ["comment.create", "pull_request.get"]
      },
      "grant_request_hash": "sha-256:<base64url-digest>",
      "status": "compatible",
      "reasons": [],
      "missing_capabilities": [],
      "required_scopes": ["pull_request.comment", "pull_request.read"],
      "required_approvals": [
        {"action_id": "comment.create", "mode": "user_or_app"}
      ],
      "risk_summary": {
        "highest": "public_side_effect",
        "actions": [
          {"action_id": "comment.create", "risk": "public_side_effect"},
          {"action_id": "pull_request.get", "risk": "read"}
        ]
      },
      "execution": {
        "supported_stages": ["comment.create", "comment.propose"],
        "missing_stages": [],
        "maximum_effects": [
          {
            "action_id": "comment.create",
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
            ]
          }
        ],
        "recovery_limitations": [
          {"action_id": "comment.create", "code": "irreversible"}
        ]
      },
      "data_exposure": [
        {
          "source": {"kind": "action", "id": "comment.create"},
          "classes": ["repository.content"],
          "redaction": {"mode": "none"},
          "retention": {"mode": "transient", "delete_on_grant_end": true}
        }
      ],
      "sandbox_constraints": [
        {"id": "network.egress", "status": "satisfied", "source": "passport"}
      ]
    }
  ]
}
```

`profile`, `match_id`, `evaluated_at`, `valid_until`, `bindings`, and
`candidates` are REQUIRED. Unknown members are forbidden in the top-level,
bindings, surface, runtime, candidate, Passport, approval, risk-summary,
execution-wrapper, recovery-limitation, sandbox, reason, and reason-subject
objects. Embedded Effect Model and Data Exposure Contract objects retain the
closed shapes and extension rules of their defining sections.
`evaluated_at` and `valid_until` are RFC 3339 timestamps and MUST satisfy
`evaluated_at < valid_until`. `match_id` is an opaque, collision-resistant
local correlation identifier. It is not a credential, approval, idempotency
key, or stable user or agent identifier. `profile` MUST exactly equal the
Capability Match Result Profile identifier, and `match_id` MUST be unique among
results retained by that runtime.

`bindings` contains exactly `surface`, `runtime`,
`agent_inventory_revision`, `adapter_inventory_revision`,
`local_policy_revision`, `enterprise_policy_revision`, and
`user_preferences_revision`; every member is REQUIRED. `bindings.surface`
contains exactly `issuer`, `app_id`, `surface_version`, and `surface_hash` from
the verified manifest. The five revision members are opaque
non-empty strings compared only for exact equality; `enterprise_policy_revision`
and `user_preferences_revision` MAY be `null` when that input does not exist.
The runtime object always contains `runtime_id`. Its other three members are
all `null` when no Runtime Identity Profile is selected. When a profile is
selected but its server projection remains unresolved,
`runtime_identity_profile` contains the requested identifier while `binding_id`
and `claims_revision` are `null`. When the app-scoped projection is locally
known, all three contain its exact values. A policy decision that requires an
unresolved runtime-identity value makes affected candidates at most
`indeterminate`.

`candidates` contains at most one entry for each (`agent_id`, `passport_hash`)
pair and at most one null-Passport entry for an agent. `passport` is either
`null`, producing a blocking `passport_missing` reason, or a closed object
containing the exact four-value Passport tuple,
`status_valid_until`, `agent_binding`, `integrity_profile`, and sorted unique
`capability_names`. `status_valid_until` MAY be `null` only when status is
unavailable and the candidate is not `compatible`. `agent_binding` is
`document_only`, `code_hash_verified`, or `unavailable`; `integrity_profile` is
non-null only for `code_hash_verified` and MUST otherwise be `null`.
`capability_names` is the exact sorted unique set extracted under the selected
Passport profile; it is declaration evidence, not authority.

Every candidate also contains `grant_request_hash`. It is the hash of that
candidate's complete request and MUST be non-null whenever `passport` is
non-null. For a null-Passport candidate it MUST be `null`, the candidate MUST be
`incompatible` with `passport_missing`, and it cannot be selected for a Consent
Preview or Grant request.

Every candidate contains all fields shown above. `missing_capabilities`,
`required_scopes`, `execution.supported_stages`, and
`execution.missing_stages` are sorted arrays of unique identifiers.
`required_approvals` entries contain exactly `action_id` and `mode`, are sorted
by `action_id`, and repeat the exact effective approval mode.
`risk_summary` contains exactly `highest` and `actions`; each action entry
contains exactly `action_id` and `risk`, is sorted by action id, and `highest`
is the maximum under the Risk Taxonomy. For a request with no actions, `highest`
is `null` and `actions` is empty. It contains no Risk Explanation UI Hint text;
adding publisher prose would make the closed result invalid. Each
`maximum_effects` entry contains
exactly `action_id` and `effects` and preserves the manifest's complete effect
declarations for every requested state-changing action. A
`recovery_limitations` entry contains exactly `action_id` and `code`; its code
is a value defined by the Action Execution Model or a collision-resistant
extension URI.
`data_exposure` is the deterministic effective projection for the candidate and
request. A sandbox constraint contains exactly `id`, `status`, and `source`;
status is `satisfied`, `unsatisfied`, or `unknown`, and source is `passport`,
`runtime`, `local_policy`, or `enterprise_policy`.

Candidate order is lexicographic by `agent_id` and then `passport_hash`, using
UTF-8 byte order; a null Passport sorts before non-null hashes for the same
agent. This profile defines no trust score or preferred-agent
ranking. A user interface MAY apply a local ranking but MUST label it as local
policy and MUST NOT serialize it as protocol authority.

### Candidate Status and Reasons

`status` is exactly `compatible`, `incompatible`, or `indeterminate`:

- `compatible` means every required input is known and current, the Passport
  and local agent binding are valid, every capability and execution stage is
  supported, all effective policies permit the path, and every required
  exposure, retention, remote-processing, training-use, approval, effect,
  recovery, adapter, and sandbox obligation can be enforced. It has no blocking
  reason and no missing entry.
- `incompatible` means at least one current, authoritative input proves a
  requirement cannot be satisfied. A definitive blocking reason takes
  precedence over additional unknowns.
- `indeterminate` means there is no definitive incompatibility, but at least one
  required input is missing, stale, temporarily unavailable, unsupported, or
  not verifiable. It MUST NOT be treated optimistically as compatible.

A reason object contains exactly `code`, `severity`, and `subject`. `severity`
is `blocking` or `advisory`. `subject` contains exactly `kind` and `id`; kind is
`candidate`, `runtime`, `passport`, `capability`, `adapter`, `action`, `scope`,
`approval`, `effect`, `recovery`, `exposure`, `sandbox`, or `policy`. Core reason
codes are:

| Code | Meaning |
| --- | --- |
| `passport_missing` | No exact Passport tuple is available for the candidate. |
| `passport_invalid` | Current verification proves the Passport or agent binding invalid. |
| `passport_profile_unsupported` | A required Passport profile is not implemented completely. |
| `passport_status_unavailable` | Fresh authenticated Passport status is unavailable. |
| `capability_missing` | A required semantic capability is not declared or mapped. |
| `adapter_unavailable` | No current local adapter can mediate the candidate. |
| `schema_unsupported` | The runtime cannot validate a required schema or dialect. |
| `execution_stage_unsupported` | A required companion, preview, reservation, or recovery stage cannot be mediated. |
| `scope_unavailable` | The exact requested scope cannot be requested under the selected path. |
| `approval_unsupported` | A required approval mode cannot be enforced. |
| `risk_denied` | Effective policy denies a manifest risk class. |
| `effect_unsupported` | A declared maximum effect exceeds the path's enforceable envelope. |
| `recovery_unsupported` | A required recovery property or limitation cannot be honored. |
| `data_exposure_unsupported` | A required exposure or redaction contract cannot be enforced. |
| `retention_unsupported` | A retention or deletion obligation cannot be enforced. |
| `remote_processing_unsupported` | Current authoritative path state proves the ceiling is exceeded or a recipient cannot enforce the exact profile. |
| `training_use_unsupported` | Current authoritative policy proves the requested training class constraint cannot be enforced for a source or recipient. |
| `sandbox_unsatisfied` | A required sandbox constraint is unsatisfied. |
| `runtime_identity_invalid` | Current verification proves required runtime identity evidence mismatched or invalid. |
| `runtime_identity_unavailable` | Required runtime identity evidence has no current authoritative value. |
| `runtime_attestation_unsupported` | The runtime cannot implement the exact requested concrete attestation profile and proof-key binding. |
| `runtime_attestation_unavailable` | Evidence-generation input required by the concrete profile is temporarily unavailable or not currently verifiable. |
| `policy_denied` | Local or enterprise policy denies the exact path. |
| `input_unknown` | A required input has no authoritative value. |

Blocking `passport_profile_unsupported`, `passport_status_unavailable`,
`runtime_identity_unavailable`, `runtime_attestation_unavailable`, and
`input_unknown` reasons produce
`indeterminate` when no definitive blocking reason exists. Every other core
blocking reason produces `incompatible`. An extension reason code MUST be a
collision-resistant URI and its defining profile MUST classify it as definitive
or indeterminate. Only `code` is extensible in this profile: an extension reason
MUST use one of the closed core `subject.kind` values above. Extending the
subject taxonomy requires a different Capability Match Result profile identifier
and complete processing rules. Unknown extension codes with a recognized
subject kind MUST be preserved; an unknown blocking reason defaults to
indeterminate and prevents `compatible`. It MUST NOT be ignored or rewritten as
advisory. Reasons are sorted by blocking before advisory, then code, subject
kind, and subject id.

An unresolved recipient, processor inventory, operator, or enforcement-policy
input uses blocking `input_unknown` with subject kind `policy` and therefore
produces `indeterminate` unless another definitive reason exists. Once current
state proves a path or recipient cannot satisfy the selected profile, the
runtime uses definitive `remote_processing_unsupported` instead. An unknown or
stale training-policy capability also uses `input_unknown`; once current state
proves the source-level constraint or a recipient policy cannot be enforced,
the runtime uses definitive `training_use_unsupported`.

### Freshness, Privacy, and Consent Boundary

`valid_until` MUST be no later than the earliest Passport status deadline,
policy or inventory freshness deadline, runtime-identity freshness deadline,
locally evaluated Runtime Attestation input deadline, or local maximum matching
TTL used by any candidate decision. The complete result becomes stale when that
time passes or when the manifest tuple, common Grant request semantics or any
candidate hash, runtime identity tuple, selected attestation profile or
proof-key capability, candidate Passport tuple or status, agent or adapter
inventory, processing-path, recipient-policy, or training-policy inventory,
local or enterprise policy, or user preferences no longer exactly match the
recorded binding.

A stale result MUST NOT be used to select a candidate, populate a new Consent
Preview, or justify a Grant request. The runtime recomputes the complete result;
it does not patch one status or revision in place. A result that becomes stale
during selection makes the selection stale as well. An Impact Simulation bound
to that result becomes stale at the same transition and MUST be regenerated in
full rather than retaining its prior examples.

In a deployment with separate runtime and application trust domains, the object
remains inside the user-controlled runtime boundary. The runtime MUST NOT send
the application its candidate list, local inventory revisions, other Passport
tuples, sandbox inventory, policy revisions, or user preferences.
It sends only the exact selected semantic Grant request and evidence required by
that request's negotiated profiles. Logs and telemetry SHOULD retain only the
`match_id`, profile, surface tuple, selected candidate request hash and
reference, status, and reason codes unless local policy explicitly requires
more. Before a candidate is selected, telemetry SHOULD omit candidate request
hashes rather than record the complete set.

An application-operated or app-embedded runtime has no confidentiality boundary
from that application. It MUST disclose that fact before enumerating local
agents, and local or enterprise policy MAY prohibit matching in that deployment.

The result is advisory input to the local Consent Preview Contract. A
`compatible` status is not consent, approval, a Grant, a credential, Passport
verification by the application, or permission to add scopes. After selection,
for a Runtime Attestation requirement it means only that the runtime can attempt
the exact concrete profile; it is not an accepted Verifier or Relying Party
appraisal, which remains unresolved until the application completes the flow.
The runtime MUST then recompute the exact semantic request and its hash,
independently recompute the data-exposure projection, verify that the hash
equals the selected candidate's `grant_request_hash` and that all bindings still
match, and, when Remote Processing Privacy is selected, re-resolve the complete
path and verify every class against the expected ceiling before deriving a
fresh Consent Preview. When Agent Training Use Policy is selected, it MUST also
verify the canonical requested set, the complete class set of every source, and
the enforcement policy of every downstream recipient. Adding a suggested scope
or action changes every candidate hash; adding or changing a candidate requires
a new result entry. Either change requires a fresh match result. The
authorization server independently verifies the selected tuple and obtains
issuer-side consent.

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

The CloudEvents event binding is the exception to those JSON projection names:
an event uses the standard CloudEvents `traceparent` and optional `tracestate`
extensions and MUST NOT also carry `trace_id` or `span_id`. A runtime derives
the starting trace and producer span from valid `traceparent` when it records
the event locally.

When an implementation claims the Runtime Mediator or Receipt Producer
Profile, its `session.start`, `action.request`, `action.result`, and receipt
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
intermediation. For non-CloudEvent ASP JSON, a valid `traceparent` takes
precedence over the JSON projection. If no valid header exists and a verified
parent receipt is available, the receiver continues the parent receipt's
`trace_id` with a new span. Otherwise it uses a valid JSON `trace_id` or starts
a new trace, in that order. Direct CloudEvents delivery instead follows the
single-hop and multi-hop consistency rules in Binding Validation and Security.

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

The Portable Replay Bundle Profile can carry exact historical
`session.transition` records for one generation. Such a record remains passive
evidence: loading, validating, or displaying it MUST NOT create, interrupt,
cancel, complete, fail, or resume an application session, and MUST NOT replace
a current authenticated state query.

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
| Runtime | MAY request start for its authenticated grant-bound tuple, observe that tuple's sessions, stop local work, request an application fence for an authoritative local budget or a durable runaway guard, request cancellation, and request resume after interruption. It MUST enforce application state in addition to local policy. |
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
| absent | accepted start | `active` | Current grant, tuple, surface, authenticated channel, and an available parallel-session slot across the grant lineage all verify; generation becomes `1`. |
| `active` | channel loss, runtime pause, or application safety fence | `interrupted` | New agent work is rejected until an explicit resume succeeds; the closed safety and cleanup path remains available, and the slot is released only after the fence. |
| `interrupted` | accepted resume | `active` | Same tuple, current grant and surface, fresh channel authentication, exact prior generation, and a newly acquired lineage slot; generation increments by one. |
| `active` or `interrupted` | accepted cancel | `cancelled` | Application fences new actions before acknowledging the transition and the runtime stops local work. |
| `active` | successful task completion | `completed` | Runtime reports completion and the application reconciles any outstanding action outcomes. |
| `active` | unrecoverable task failure | `failed` | Runtime or application records a stable reason without treating unknown action outcomes as rolled back. |

`cancelled`, `completed`, and `failed` are terminal. A terminal `session_id`
MUST NOT be resumed or reused for new work. A duplicate request for an already
accepted transition is idempotent only when its session id, prior generation,
target state, bound hashes, and any reason-specific `guard_id` and
`guard_resolution_id` are identical. A conflicting reuse MUST fail as
`session_transition_invalid` and MUST NOT move the session.

When `max_parallel_sessions` is present, the application MUST acquire or
release its occupancy atomically with the authoritative transition. A full
limit leaves a proposed start absent and a proposed resume `interrupted`; it
does not increment generation, expose the occupying sessions, or disturb work
already active under the grant. Credential rotation, reconnect, or a duplicate
transition request MUST NOT allocate another slot or reset lineage occupancy.

An accepted resume does not by itself clear runtime budget or runaway state.
The runtime MUST resolve its own authoritative blocker first. A resumed
generation after channel loss, a budget pause, or another non-runaway
interruption continues the same runaway-guard epoch and counts. A new epoch can
start only after the explicit runaway resolution rules below; historical guard
and event-deduplication records are not rewritten as if the earlier generation
never ran.

`session.pause`, `session.cancel`, and `session.resume` requests MUST contain
`session_id`, the caller's current `session_generation`, `grant_id`,
`grant_hash`, and `surface_hash`. The channel authenticates the runtime or
application actor; an agent-supplied field inside the payload does not. A
`session.state` response MUST repeat those binding fields, report the
authoritative state and generation, and include a stable transition reason.
Receipt or event transport can record the transition, but neither is authority
to create it.

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
Before a runtime sends or accepts a start, it MUST admit session creation
through the lineage-delegate guard defined in Runtime Runaway Protection. A
fenced or unavailable parent guard blocks the new session even when the Grant
is otherwise active. If the application has already created a proposed record,
the runtime MUST NOT schedule it or assume an authoritative application state.
Every newly observed `active` session in that fenced lineage MUST receive the
same exact `runaway_guard` pause flow with the causal parent `guard_id` and MUST
join the parent resolution snapshot. The only alternative is an authenticated
terminal cancellation after an independently authenticated actor abandons the
complete lineage recovery. A merely proposed record MUST be cancelled or
allowed to remain absent according to application policy; local interruption
alone cannot release an application slot or satisfy parent resolution.

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
    "passport_hash": "sha-256:<base64url-digest>",
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
    "passport_hash": "sha-256:<base64url-digest>",
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

### Session Pause

`session.pause` lets a bound controlling runtime request an application fence
after it has already stopped matching new local work. This draft defines two
runtime-authoritative reasons: `budget_exceeded` and `runaway_guard`. Neither
payload is authority to change an application budget or bypass application
session policy.

For an exhausted runtime budget, the cause applies to every active session
controlled by that same runtime whose Grant lineage contains the causal
`budget_grant_id`, including sessions on same-runtime descendant Grants. It does
not affect a sibling whose lineage excludes that causal Grant or a session
controlled by another runtime. The controlling runtime sends a distinct pause
request for each affected active session and MUST NOT leave another matching
worker eligible for scheduling. A runaway guard is scoped to its exact session
and generation, but its trip also fences the local cumulative
Grant-lineage/delegate scope defined below. The runtime stops every active local
session in that scope and sends a distinct pause request for each; it does not
affect a different delegate or an independently consented root Grant lineage.

The runtime sends the complete typed envelope as an `application/json` POST to
the manifest `session_control_url`, using the Grant Credential and its required
credential-binding proof, or carries the identical message on an already
authenticated Runtime Bridge. This example is the budget variant:

```json
{
  "type": "session.pause",
  "payload": {
    "pause_id": "pause_01J2BUDGET",
    "session_id": "sess_456",
    "session_generation": 1,
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "budget_grant_id": "grant_123",
    "budget_grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "reason": "budget_exceeded",
    "budget_id": "runtime_seconds",
    "budget_revision": 31
  }
}
```

`pause_id` is a non-empty identifier unique within the session generation and
`reason` is `budget_exceeded` or `runaway_guard`. For `budget_exceeded`,
`budget_grant_id` and `budget_grant_hash` MUST identify the session grant or one
of its authoritative ancestors, `budget_id` MUST name one runtime-authoritative
counter in that causal ledger, and `budget_revision` MUST be the safe
non-negative revision of the runtime's durably recorded `exhausted` state.
`guard_id` MUST be absent. For `runaway_guard`, a stable non-empty `guard_id`
from the runtime's durable guard record is REQUIRED and every `budget_grant_*`,
`budget_id`, and `budget_revision` member MUST be absent. These values are an
authenticated report by the bound runtime; they do not make the application
authoritative for the runtime counter or guard and do not permit the runtime to
change application budget state.

`guard_id` MUST be collision-resistant and unique across the runtime's retained
guard records; a later epoch or unrelated guard MUST NOT reuse it. One causal
parent guard MAY be referenced by the distinct pause records in its fan-out.

The runaway variant is therefore:

```json
{
  "type": "session.pause",
  "payload": {
    "pause_id": "pause_01J2RUNAWAY",
    "session_id": "sess_456",
    "session_generation": 1,
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "reason": "runaway_guard",
    "guard_id": "guard_01J2CYCLE"
  }
}
```

Before either idempotency lookup or a state response, the application MUST
authenticate the channel as the runtime bound to the complete session tuple,
verify an active, unexpired current grant and the current surface hashes, require
the exact current generation, and validate the reason-specific members. For
`budget_exceeded` it also verifies the causal grant hash and ancestor relation.
For `runaway_guard` it verifies only that `guard_id` is syntactically valid and
bound to this authenticated request; it MUST NOT claim to have verified the
runtime's private detector state. Revocation, expiry, or a changed authority
dominates a cached pause response. After those checks, an exact `pause_id` match
to an accepted record returns that record as described below even though the
session is already `interrupted`. A new pause is accepted only for an `active`
session. The application atomically fences new Action Requests, changes the
authoritative state to `interrupted` with the requested reason, records
`pause_id`, the reason-specific causal fields and effective time, and releases
the parallel-session slot. The generation does not change. Only after that
transition does it return the authoritative state. This is the budget response:

```json
{
  "type": "session.state",
  "payload": {
    "pause_id": "pause_01J2BUDGET",
    "session_id": "sess_456",
    "session_generation": 1,
    "state": "interrupted",
    "transition_reason": "budget_exceeded",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "budget_grant_id": "grant_123",
    "budget_grant_hash": "sha-256:<base64url-digest>",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "budget_id": "runtime_seconds",
    "reported_budget_revision": 31
  }
}
```

For `runaway_guard`, `session.state` repeats `pause_id`, `guard_id`, the exact
session and Grant tuple, `state: "interrupted"`, and
`transition_reason: "runaway_guard"`; it omits all budget-specific members.

An exact duplicate request under still-current authority returns the same state
without another transition, slot release, or control event. Reuse of `pause_id`
with different content, a different pause for an already interrupted session, a
terminal session, a stale generation, or a tuple/hash mismatch fails uniformly as
`session_transition_invalid` and reveals no other session. A timeout leaves the
runtime locally paused; it MAY repeat the exact request or query authoritative
session state, but MUST NOT resume or create a new generation by itself.

An interrupted safety-paused session retains a closed safety and cleanup path
for grant revocation, session cancellation, `budget.query`, introspection,
receipt retrieval, authoritative outcome reconciliation, explicit reservation
release, and an exact completed idempotent replay. These operations require the
current grant, exact interrupted session tuple and generation, ordinary actor
authentication, and their operation-specific authorization. They do not make
the session active, allocate a parallel-session slot, or admit unrelated agent
work.

When exact replay or reservation release uses the Action Request envelope, the
application evaluates this closed exception before rejecting the session as
non-active, but after tuple, generation, grant, surface, schema, normalization,
and idempotency validation. An exact replay MUST match a completed record from
that session and return only its stored response and receipts without a new
policy decision, effect, charge, or revision. A release MUST name the
manifest-declared reservation action whose static operation is `release`, match
an existing reservation bound to that session and grant, and perform only its
idempotent release effect. The first release attempt uses one new
release-specific idempotency key bound to that reservation and normalized input;
every retry reuses that same key and record. No other action id, mode, changed
input, unknown-outcome retry, or new idempotency key qualifies. Reconciliation
that could create a new effect requires resume and ordinary active-session
admission.

When the manifest declares `session.paused_budget`, the application emits the
control event defined above after an accepted `budget_exceeded` transition. The
event records the fence but does not create it. The application MUST NOT emit
`session.paused_budget` for `runaway_guard`; this draft defines no application
event for runtime guard state.

Explicit `session.resume` remains the only way back to `active`. Before
requesting resume, the runtime MUST independently verify that its authoritative
budget or guard condition is resolved. When a runaway fence applies to the
session, the request MUST carry the stored `guard_id` and a non-empty opaque
`guard_resolution_id` from the explicit local resolution record. This includes
a session that was already authoritatively `interrupted` for another reason
when its parent guard tripped, even though no second pause transition was
permitted. The application binds those values to the transition for audit but
does not treat them as proof of detector state; its ordinary authenticated
runtime and local policy checks remain authoritative.
The resulting `session.state` MUST repeat both identifiers so an ambiguous
response can be retried without selecting another resolution record.
The application increments generation only after the current grant, surface,
application-owned budget availability, parallel-session occupancy, and its
local policy verify; it does not invent runtime counter or guard state. Pause
neither cancels the grant nor rewrites an in-flight action or receipt outcome.

### Runtime Runaway Protection

Application idempotency and Grant budgets bound effects and aggregate
consumption, but they do not by themselves stop an agent that repeatedly reads,
retries cached operations, changes idempotency keys, or turns application events
into an automation cycle. A conforming runtime MUST enforce an independent,
durable runaway-guard epoch before it permits any agent, model, tool, or Action
Request scheduling. Autonomous scheduling is multi-step work for which each next
operation does not receive a new, contemporaneous user approval, but a per-step
approval neither exempts an operation from counting nor resets the epoch.

The runtime allocates a collision-resistant local `guard_epoch_id` before it
schedules the first step for a session. One guard registry epoch is keyed by
`(grant_hash, session_id, guard_epoch_id)`, maps every current
`session_generation` that continues it, and contains a record for each
applicable guard type and counting key. Channel-loss, budget, and other
non-runaway resumes MUST bind the incremented generation to the same epoch and
carry every count forward. Every record uses this state machine:

```text
armed -> warning -> fenced
   +----------------> fenced
```

`warning` MAY be skipped. Each record has a stable collision-resistant
`guard_id`, unique across retained runtime guard records; any record entering
`fenced` fences the complete epoch, which is terminal. The runtime MUST
durably retain each record's state, guard type, positive finite safe-integer hard limit,
optional lower warning threshold, current safe-integer count, opaque local or
keyed-hash root and parent references, transition times, and any resolution
reference. Agent output, an event payload, or a caller-supplied counter MUST NOT
select a limit or move state backward. Restart, reconnect, credential rotation,
session interruption, delivery retry, and replay MUST NOT reset the epoch.

Missing, corrupt, or overflowing state in either registry fails closed. The
runtime MUST first attempt to durably create a minimal fenced fault record with
a new stable `guard_id`, type `guard_state_unavailable`, the exact retained
session or lineage-delegate binding, any affected current session tuple, and no
invented count. It uses the retained epoch id when that binding is intact;
otherwise it allocates a recovery-only epoch id that MUST never enter `armed`.
If that record commits, it is the causal fenced record and can support the exact
pause and resolution flow below for every affected active session. If even the
minimal record cannot be persisted, the runtime MUST remain locally fenced,
MUST NOT send a `runaway_guard` pause that falsely claims a stable `guard_id`,
and MUST require authenticated operator reconciliation or session cancellation.
When no application session exists, it simply blocks session creation. Loss of
local state never authorizes a clean epoch or resumed scheduling.

The runtime MUST also maintain a parent lineage-delegate guard registry. It
allocates a local `guard_lineage_id` for one cumulative Grant derivation lineage
and carries that id across attenuation, renewal, token exchange, credential
rotation, and supersession that preserves authority. Only a fresh independent
root Grant following distinct authorization and consent can allocate a new
lineage id. Before the first session admission, the runtime allocates a
collision-resistant `lineage_guard_epoch_id`. The parent epoch is keyed by
`(guard_lineage_id, runtime_id, agent_id, passport_hash,
lineage_guard_epoch_id)`, its records use the same state machine, and it has
positive finite safe-integer limits for session creation, automation roots, total scheduling
steps, and cycle signatures across every child session epoch in that scope.

Every session start, root allocation, and scheduling admission MUST atomically
check and advance both the applicable parent and session records. A new
`session_id`, generation, child Grant, credential, root id, or event delivery
MUST NOT reset or partition parent counts. If either layer trips, the runtime
durably fences the parent epoch with the causal `guard_id`, stops admission in
every local session in that lineage-delegate scope, and applies the pause fan-out
above. A terminal child session does not clear the parent fence or its unresolved
tombstone. No new session or existing session may continue the causal task,
root, action fingerprint, or cycle signature until independent resolution.

Before work begins, local policy MUST configure positive finite safe-integer hard
limits for at least:

- transport attempts for one logical agent-work dispatch
- attempts of one repeated logical ASP action across idempotency keys
- automation roots and total scheduling steps in one epoch
- logical actions scheduled from one validated automation root
- runtime-assigned causal depth from that root
- repetitions of one cycle signature

The runtime MUST also enforce every applicable Grant budget from Budget Caveats
and Accounting. A budget ledger is not a runaway counter and a guard record is
not Budget Counter State; satisfying one never disables the other. A warning
threshold, when configured, MUST be smaller than its hard limit. Crossing it
MAY notify a local user or policy engine but creates no ASP event and grants no
additional authority. When the next count would exceed a hard limit, the
runtime MUST enter `fenced` before that attempt or scheduling step occurs and
return `safety_guard_triggered` to the local caller.

The applicable parent-and-session checks, count increments, and scheduling
admission MUST be one atomic or recoverable durable decision. Exactly the
configured number of concurrent admissions can succeed. The first guard record
that fences the scope selects the causal `guard_id`; racing steps observe that
fence, fail without scheduling, and MUST NOT allocate another pause transition.

The runtime allocates a stable logical-dispatch id before a first agent-work
transport attempt and durably increments its attempt counter before every send.
A crash between increment and send can conservatively overcount; it MUST NOT
permit an uncounted retry. Retransmission with the same idempotency key is the
same logical dispatch but another transport attempt. Creating a new key or
obtaining an exact cached result can avoid a second application effect or budget
charge, but it still advances the applicable repetition guard. Closed safety
and cleanup operations use a separate control-plane path with finite retry and
backoff policy; a fenced agent-work epoch MUST NOT block that path or let an
agent use it for unrelated work.

For an action with `asp-json-normalization-v1`, the runtime derives the local
repetition fingerprint from the pinned `surface_hash`, `action_id`, and verified
normalized-wire `input_hash`. It MUST exclude the idempotency key, trace ids,
event delivery ids, transport attempt, timestamps, and transient execution or
preview evidence. For an action without that normalization profile, the runtime
MUST at least apply a conservative finite counter keyed by `surface_hash` and
`action_id`; it MUST NOT invent semantic normalization and claim that two raw
inputs are the same application request. A fingerprint is a local safety signal,
not authority, an idempotency key, or evidence an application may use to merge
requests.

A validated non-control application event uses
`(aspsubid, source, id, aspeventhash)` as its automation-root reference after
the delivery decision is durably deduplicated; a core control event cannot be a
root. A user- or runtime-originated task uses a collision-resistant local root id
bound to the authenticated initiating record, Grant, session, and generation.
The runtime assigns every scheduled step a parent guard node and increments
depth itself; an agent-supplied parent, `traceparent`, receipt link, arrival
order, or connection identity is not causal authority.

A cycle signature is a collision-resistant local digest over a bounded ordered
window of runtime-assigned node kinds, action fingerprints, event types, and
data-minimized stable resource references. Per-occurrence event ids, root ids,
delivery ids, attempts, traces, and timestamps MUST NOT make an otherwise
repeated cycle distinct. The signature also MUST exclude raw prompts, event
payloads, action inputs, model output, and tool arguments. The runtime can use
stricter local signals, but it MUST NOT omit the finite roots-per-epoch,
steps-per-epoch, actions-per-root, and causal-depth guards merely because a
changing input evades an exact cycle signature.

On any trip, the runtime MUST atomically or recoverably persist the `fenced`
transition before it stops admission. It then rejects new agent, model, tool,
event-root, and Action Request scheduling for the epoch. Already dispatched
effects remain subject to their ordinary Action Responses, receipts, and
authoritative outcome reconciliation; the runtime MUST NOT report them as
rolled back, failed, or absent merely because the guard tripped. Only the closed
safety and cleanup path defined in Session Pause remains available, and it MUST
run outside agent-controlled scheduling.

For each affected application session that is `active`, the runtime sends
exactly one logical, exactly replayed `session.pause` request using a stable
per-session `pause_id`, reason `runaway_guard`, and the causal `guard_id`. A
timeout leaves the runtime locally fenced and retries that same request with
bounded backoff; it never allocates another pause id for the session. Exhausting
the control-plane retry policy leaves the local fence in place and requires
operator or authenticated state reconciliation; it does not reopen agent
scheduling. If authoritative session state is unknown, the runtime remains
fenced while it queries or reconciles that state. The fence does not create a
`session.paused_budget` event, change a budget ledger, fabricate an application
event, or produce an application action receipt. The fan-out set remains open
while the parent is fenced: a session first observed as `active` after the
initial scan receives the same treatment and prevents a resumable lineage
resolution from committing until its authoritative state is reconciled.

Leaving `fenced` requires an explicit resolution by an independently
authenticated user or local policy actor. Agent output, elapsed time, process
restart, reconnection, or another delivery MUST NOT resolve it. Because every
child trip also fences its parent, the authoritative local resolution is one
durably committed lineage resolution record. It contains a collision-resistant
`guard_resolution_id` unique across retained resolution records; the causal
`guard_id`, `guard_lineage_id`, and old `lineage_guard_epoch_id`; the reviewed
trigger, known in-flight outcomes, and limits that will apply next; and a
complete `affected_sessions` snapshot. A `causal_session` containing the
complete bound Session Authority tuple and local `guard_epoch_id` is REQUIRED
for a child trip and absent for a parent-only trip before any session exists.

The snapshot covers every locally known nonterminal session in the fenced
lineage-delegate scope and the causal session even if it becomes terminal while
resolution is prepared. Each entry binds its complete Session Authority tuple
and local `guard_epoch_id` and has one of these statuses: `resume_pending` after
the application has authoritatively accepted its exact pause or confirms it was
already `interrupted`, `terminal` after authoritative terminal state is
confirmed, or `abandoned` after the independently authenticated actor chooses
to retire the complete lineage rather than recover it. An already interrupted
entry is locally bound to the parent `guard_id` and uses the guard-aware resume
above; the runtime MUST NOT fabricate a second application transition. The
runtime MUST NOT commit a resumable resolution while an affected or newly
observed active session still has an unknown or pending pause outcome. An empty
array is valid for a reviewed parent-only trip, but the explicit record and
reviewed cause are still required; emptiness by itself is never reset authority.

For a resumable resolution, every entry MUST be `resume_pending` or `terminal`.
Only after that global record commits may the runtime allocate a new armed
parent epoch. It supplies the same `guard_resolution_id` and causal `guard_id`
on the exact `session.resume` for every `resume_pending` entry; a terminal entry
is not resumed. After the application accepts a resume and increments that
session generation, the runtime MAY allocate a new child `guard_epoch_id` under
the new parent. It MUST NOT mutate either old epoch into `armed`. A non-runaway
resume has no such authority and continues the existing parent and session
epochs.

If any entry is `abandoned`, the resolution outcome retires that complete local
Grant lineage. The runtime MUST request authenticated terminal cancellation for
every nonterminal application session when the control plane is available,
MUST NOT allocate another parent epoch for that `guard_lineage_id`, and MUST
reject later descendant, renewal, exchange, credential, or session work that
would preserve its authority. New work then requires a fresh independent root
Grant following distinct authorization and consent.

The minimized record for an unresolved fenced session epoch, including
`guard_id`, trigger, limits, counts, and any resolution identity, MUST remain
available until the application accepts resume, that session becomes terminal,
or an independently authenticated user explicitly abandons its recovery. The
corresponding parent fence or unresolved tombstone MUST remain until explicit
lineage-delegate resolution commits or terminal expiry or revocation closes the
complete cumulative Grant lineage. Terminal state of one or even every session
is never parent reset authority. An abandoned-lineage resolution preserves a
local no-resume parent tombstone until that complete authority becomes terminal;
application cancellation updates its affected-session status but does not
delete the tombstone or permit a replacement parent epoch. Missing state cannot
silently satisfy either boundary. After the authority lifecycle closes,
guard records and deduplication state MUST still remain available through the
longest applicable event-replay, agent-work transport-retry, and in-flight
outcome-reconciliation window, including after a new generation starts, and
only then enter a bounded local security-audit retention period.
The guard registry MUST NOT extend the retention of an underlying application
payload or other semantic record beyond its effective Data Exposure Contract.
It may retain only opaque local references, counters, or keyed
collision-resistant hashes; a compact hash or tombstone may outlive plaintext
only under an independently declared bounded security-audit policy that permits
it. A runtime MUST delete any guard-specific transient copy of raw input
immediately after deriving the required fingerprint. This does not delete the
canonical input held by the ordinary approval, transmission, idempotency, or
receipt lifecycle under its own retention rules. No guard log may become a
retained copy of a prompt, application event, action input, model output, or
tool argument.

### Action Request

The agent requests an action through the runtime. The runtime sends the action to
the app only if grant and policy allow it.

The action request MUST be authorized by the HTTP authorization layer or an
equivalent proof. The `grant_id` inside the body is a correlation identifier, not
a credential.

The application MUST also verify that the supplied `session_id` and
`session_generation` identify an `active` session bound to the complete subject,
runtime, agent, passport, grant, application, and surface tuple selected by the
presented credential, unless an interrupted session request satisfies the exact
closed safety and cleanup exception in Session Pause. Before returning a
non-active failure, the application MAY perform only the validation and record
lookup required to decide that exception; it MUST NOT admit an effect
speculatively. Otherwise a valid grant credential could be replayed against
sessions created under other grants or against a stale generation, corrupting
session accounting and receipt linkage. Unknown, non-qualifying non-active,
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

For an idempotency-required action, the runtime MUST apply the pinned
`idempotency_normalization` declaration before approval, hashing, receipt
creation, and transmission, and MUST carry the resulting `input_hash` even when
the action does not require a receipt. The application MUST verify the pinned
`input_schema_hash`, validate the received input, independently reapply the same
declaration, require a fixed point, and recompute the `input_hash` before
consulting the idempotency record or admitting any work. A non-fixed-point
request fails as `input_not_normalized`; the application does not reserve the
key, charge a budget, or create policy or action receipts for that rejected
attempt.

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
    "approval_receipt_hashes": {
      "runtime": "sha-256:<runtime-approval-receipt-digest>"
    },
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

When the Grant selects Approval Receipt, the request's optional
`approval_receipt_hashes` object is closed and the runtime can supply only its
`runtime` member. It MUST match the same object in the verified parent runtime
action receipt. The application MUST retrieve or receive the complete Approval
Receipt through `agent_api.receipt_url` or the same declared inline receipt
extension, recompute its hashes, authenticate the producer, and validate the
exact Grant requirement and invocation bindings before accepting it. A
runtime-side denial stops before Action Request dispatch. A missing required
runtime role is `approval_required`; an expired receipt is `approval_expired`;
a mismatched, malformed, denied, or unauthenticated receipt never satisfies
approval and uses the error precedence defined below. App-side approval occurs
inside the application boundary and is added only to the final application
action receipt and Action Response.

For an action requiring runtime receipt evidence, the action declaration MUST
set `input_hash_profile` to `asp-jcs-sha-256`. The runtime and application MUST
compute the Action Input hash over the exact validated wire `input` and require
equality with both the action request and verified parent runtime receipt. For
an idempotency-required action that wire value is already the fixed point of
the manifest-pinned normalization declaration. A receipt for one normalized
input MUST NOT be attached to a different input even when the grant, action id,
and idempotency key match.

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
    "approval_receipt_hashes": {
      "runtime": "sha-256:<runtime-approval-receipt-digest>"
    },
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
When Approval Receipt is selected, it MUST also return the exact final
`approval_receipt_hashes` map from the application action receipt. An
application-side denial response instead returns `approval_denied`, includes
`approval_receipt_id` and `approval_receipt_hash` for the immutable denial
Approval Receipt, and makes the complete object available through the
authenticated receipt channel. Those fields are correlation evidence, not
authority; the response MUST NOT claim satisfied approval or an action effect.
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

This is the RECOMMENDED default for early integrations on a `standard`
surface. The proposal and commit are separate actions and authorities even
when they share one `operation_id`.

For a proposal-only surface, the ASP flow terminates with the non-authoritative
artifact:

```text
Agent -> typed propose action
Runtime/App -> policy, validation, optional draft persistence
App -> proposal result and optional receipt
User -> reviews or applies through independently authenticated app-native UI
```

If the publisher later wants the agent to commit through ASP, it MUST publish a
new `standard` surface version and hash containing a separate commit action.
The runtime MUST perform a new capability match and Consent Preview, and the
authorization server MUST obtain fresh consent and issue a new independent
Grant that explicitly contains the commit action. Renewal, token exchange,
subdelegation, an old proposal approval, or reuse of the proposal's id,
operation id, receipt, or input hash MUST NOT widen the proposal-only Grant.

## Receipts

### Receipt Requirements

Runtime and application action receipts produced under the corresponding
`producer_role` of the Receipt Producer Profile MUST include:

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
- an opaque approval reference under the base profile, or the applicable
  role-indexed `approval_receipt_hashes` under the Approval Receipt Profile
- idempotency key
- producer-authoritative `budget_charges` with budget id, non-negative amount,
  and resulting receipt-grant-local ledger revision when the recorded operation
  consumed budget
- timestamp
- result
- error classification when failed

For action receipts, `receipt_type` is exactly `runtime` or `app` according to
the producer. The Approval Receipt Profile additionally defines
`receipt_type: "approval"` for its prerequisite decision object; it is not an
action receipt and follows the separate closed shape below.

Fields that do not apply to the recorded outcome, such as `output_hash` for a
denial before execution, MAY be omitted. The identity, authority, trace,
decision, and result fields that do apply MUST be present and internally
consistent.

A producer MUST report only charges from ledgers for which it is the accounting
authority. A pre-admission denial carries no application write or cost charge.
An exact idempotent replay returns the original immutable charge evidence and
MUST NOT create a second charge or revision. Budget evidence is audit data, not
authority to increase a limit or overwrite current ledger state.

A runaway guard record and its `session.pause` transition are control-plane
safety metadata, not an application action receipt. A fence reached before an
Action Request is dispatched MUST NOT fabricate an app receipt, actual effects,
or an application error response. An already dispatched action retains its
ordinary immutable response, budget evidence, effect outcome, and runtime or
application receipts; the guard MUST NOT rewrite them. A runtime MAY reference
`guard_id` in its local audit record, subject to the minimized retention rules
above.

For a child-grant operation, `ledger_revision` is the resulting revision of the
named counter in the receipt's own `grant_id` ledger. The same atomic charge can
also advance ancestor ledgers, but this field does not claim their revisions;
their current state remains available only from each ancestor's accounting
authority.

A receipt MUST NOT contain the raw `execution_token`. It carries the sanitized
execution context with `execution_token_hash`, allowing a verifier to recompute
`execution_hash` without receiving reusable preview evidence.

### Approval Receipt Profile

The optional Approval Receipt Profile replaces an opaque approval reference
with immutable, typed evidence for one exact approval interaction. Its profile
identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1
```

An Approval Receipt records a decision; it is not a Grant Credential,
standalone action authority, proof that an effect occurred, or an instruction
to execute. Every component still verifies current Grant, session, surface,
policy, preview, reservation, precondition, effect-envelope, idempotency, and
budget state at its ordinary enforcement boundary.

#### Grant Requirement

A semantic Grant request selects this profile with the following `audit`
fragment containing a closed `approval_receipt` object:

```json
{
  "audit": {
    "approval_receipt": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1",
      "requirements": [
        {
          "action_id": "comment.create",
          "accepted_roles": ["application", "runtime"],
          "max_age_seconds": 300
        }
      ]
    }
  }
}
```

`profile` and `requirements` are REQUIRED and unknown members are forbidden.
`requirements` is ordered by ascending Unicode code point of `action_id` and
contains exactly one entry for every requested action whose manifest approval
mode is not `none`; duplicate or extra actions are invalid. Each entry is
closed and contains exactly `action_id`, `accepted_roles`, and
`max_age_seconds`. `accepted_roles` is a non-empty array containing unique
values in ascending Unicode code point order from `application` and `runtime`.
`max_age_seconds` is a positive safe integer.

This v1 profile covers only approval-bearing actions in mode `reserve`,
`commit`, `compensate`, or `revert`. Every covered declaration therefore has
`idempotency: "required"`, the `asp-json-normalization-v1` declaration,
`input_hash_profile: "asp-jcs-sha-256"`, and
`execution_hash_profile: "asp-jcs-sha-256"`, and every invocation carries the
complete receipt tuple below. A semantic request selecting this profile while
including an approval-bearing `read`, `dry_run`, or `propose` action is invalid,
even when the proposal is persisted. Such actions require a separate Grant
using the base opaque approval reference, or a future profile with mode-specific
receipt bindings. The authorization server rejects an invalid OAuth request as
`invalid_authorization_details`.

The accepted roles MUST agree with the pinned action declaration:

| Manifest approval mode | Valid Grant requirement |
| --- | --- |
| `none` | No requirement entry. |
| `runtime` | Exactly `runtime`. |
| `app` | Exactly `application`. |
| `user_or_app` | Any non-empty subset of `application` and `runtime`. |
| `runtime_and_app` | Both `application` and `runtime`. |

This per-action rule is the explicit Grant caveat under which an application
can accept a runtime approval assertion. A generic `write_approval` constraint,
receipt schema, signature capability, or manifest approval mode does not add an
accepted role. In particular, a runtime MUST NOT choose `runtime` for a
`user_or_app` action unless the authoritative Grant requirement includes it.

The profile MUST be advertised in
`compatibility.approval_receipt_profiles`. A request accepting a runtime role
MUST also require `audit.local_receipt: "required"`; every request selecting the
profile MUST require `audit.app_receipt: "required"`. The authorization server
MUST reject an unadvertised profile, malformed or unclosed requirement set,
unsupported role, missing required action, extra action, incompatible mode, or
invalid maximum age. Under the OAuth profile these failures are
`invalid_authorization_details`.

The authorization server returns the same profile and a requirement projection
for the returned action subset. It MAY remove a role from a `user_or_app`
requirement and MAY lower `max_age_seconds`; it MUST NOT add a role or increase
the age. Requirements for removed actions are removed, and requirements for
retained approval-bearing actions remain present. The fixed-role `runtime`,
`app`, and `runtime_and_app` modes cannot change roles. Token exchange and child
Grant derivation apply the same attenuation and MUST NOT reuse an Approval
Receipt from the source or parent because its `grant_hash` and invocation tuple
differ. The complete effective object is part of the semantic Grant request
hash, authoritative Grant, `grant_hash`, consent views, token and introspection
responses, and server-side Grant state. It is never mutable in place.

#### Approval Receipt Object

An Approval Receipt has `receipt_type: "approval"` and this wire shape:

```json
{
  "receipt_id": "receipt_approval_01J2APPROVE",
  "receipt_type": "approval",
  "receipt_hash": "sha-256:<approval-receipt-digest>",
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
  "runtime": {
    "runtime_id": "application_runtime_456"
  },
  "actor_agent": {
    "agent_id": "local_agent_789",
    "passport_hash": "sha-256:<base64url-digest>"
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
  "policy_decision_hash": "sha-256:<approval-policy-decision-digest>",
  "policy_decision": {
    "type": "policy.decision",
    "decision_id": "pdec_approval_01J2ABCDEF",
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
    "safe_to_show": "The exact write request was approved.",
    "evaluated_at": "2026-06-25T16:29:59Z",
    "policy_decision_hash": "sha-256:<approval-policy-decision-digest>"
  },
  "approval": {
    "approval_id": "approval_01J2ABCDEF",
    "role": "runtime",
    "decided_by": "user",
    "valid_until": "2026-06-25T16:34:59Z"
  },
  "timestamp": "2026-06-25T16:29:59Z",
  "result": "approved"
}
```

The top-level object is closed except for `receipt_signatures` when the Receipt
Signing Profile is used. Every member shown is REQUIRED for an approved
receipt. `approval` is closed and contains exactly `approval_id`, `role`,
`decided_by`, and `valid_until`. `approval_id` is a collision-resistant
identifier unique within its producer. `role` is `runtime` or `application` and
MUST be accepted by the exact Grant requirement. `decided_by` is `user` or
`policy`; a runtime approval MUST use `user`. For role `runtime`, the Policy
Decision enforcer MUST be the exact bound runtime. For role `application`, it
MUST be the manifest application. `timestamp` and `valid_until` are
RFC 3339 UTC timestamps with the `Z` suffix and MUST satisfy
`timestamp < valid_until`. `valid_until` MUST be no later than `timestamp` plus
the Grant's `max_age_seconds`, Grant expiry, and any preview, reservation, or
other approval-bound evidence expiry.

On first authenticated ingestion of a receipt hash, a consumer MUST durably
record a local `first_authenticated_at` time and MUST NOT move it forward on
replay. It MUST reject as `integrity_mismatch` a receipt whose `timestamp` is
later than that time plus a finite locally configured clock-skew allowance. For
first effect admission, the effective expiry is the earliest of
`approval.valid_until`,
`first_authenticated_at + max_age_seconds`, Grant expiry, and every applicable
approval-bound evidence expiry. This receiver-side cap prevents a future-dated
producer timestamp from extending the Grant caveat. `first_authenticated_at`
is verification state, not a wire member or portable trusted timestamp.

For a denied receipt, `result` is `denied`, `approval.valid_until` is absent,
and the closed `approval` object contains the other three members. The valid
decision combinations are:

| Role | Result | `decided_by` | Policy Decision outcome and reason |
| --- | --- | --- | --- |
| `runtime` | `approved` | `user` | `allow`, `approval_satisfied` |
| `runtime` | `denied` | `user` | `deny`, `approval_denied` |
| `runtime` | `denied` | `policy` | `deny`, `local_policy_denied` |
| `application` | `approved` | `user` or `policy` | `allow`, `approval_satisfied` |
| `application` | `denied` | `user` | `deny`, `approval_denied` |
| `application` | `denied` | `policy` | `deny`, `app_policy_denied` |

Every other combination is invalid. The top-level and embedded
policy-decision hashes MUST match. `policy_decision.evaluated_at` MUST equal
`timestamp`.

The receipt binds the complete subject, runtime, agent, Passport, application,
Grant, session generation, surface, action, idempotency key, normalized
`input_hash`, sanitized execution context, and `execution_hash`. Conditional
preview, precondition, expected-effect, reservation, execution-token-hash, and
recovery-target bindings are already inside that execution context. Changing
any bound value requires a new approval interaction and receipt. Approval for a
proposal, dry run, reservation, or different companion action cannot satisfy a
commit, compensation, or revert.

An Approval Receipt MUST omit `parent_receipt_hash`, `approval_receipt_hashes`,
raw action input, raw execution tokens, output and resource fields,
`actual_effects`, effect hashes and outcome, revert evidence, and budget
charges. It records no action attempt or accounting admission. The producer
computes `receipt_hash` with the ordinary Receipt hash domain. The optional
Receipt Signing Profile applies without changing that hash.

#### Producer Authentication and Role Mapping

A bare `receipt_hash` is correlation only. Across a trust boundary, the
consumer MUST obtain the complete receipt, recompute its receipt and Policy
Decision hashes, authenticate the producer through the Grant-bound channel or
store, and verify every binding above. When the Grant's
`audit.receipt_signing.required_signers` contains the Approval Receipt's
producer role, the consumer MUST also require and verify the signature and its
pinned role-specific key. Every present signature MUST be verified even when
that role is not required, and an invalid required or present signature MUST
NOT be downgraded to unsigned evidence. A valid runtime signature authenticates
the runtime's statement; it does not independently prove a human gesture,
understanding, or identity.

Action evidence links approvals with a closed `approval_receipt_hashes` object
whose only possible members are `runtime` and `application`. Each present value
is the hash of one verified approved Approval Receipt for that role; members are
never `null`. The object is a causal side link, not `parent_receipt_hash`, and
MUST NOT appear inside `execution`, because the Approval Receipt already binds
`execution_hash` and that placement would create a hash cycle.

The role mapping in the final application action receipt is:

| Manifest approval mode | Required approved receipt hashes |
| --- | --- |
| `none` | Object absent. |
| `runtime` | Exactly `runtime`. |
| `app` | Exactly `application`. |
| `user_or_app` | Exactly one role accepted by the Grant rule. |
| `runtime_and_app` | Both `application` and `runtime`. |

The Action Request and its runtime action receipt carry the exact same absent
object or `runtime` member; a runtime MUST NOT supply an `application` member.
The map is absent for `none` and `app`, contains exactly `runtime` for `runtime`
and `runtime_and_app`, and for `user_or_app` contains `runtime` only when that
role is accepted and selected, otherwise it is absent only when `application`
is accepted. The application receipt MUST preserve a verified runtime member
and add its own `application` member when app-side approval is required. For
`user_or_app`, a present valid runtime member fixes the selected role and the
application MUST NOT add another member; when it is absent, the application
MUST obtain and add an application approval before effect admission. A known
denial in any required role blocks the effect and MUST NOT appear as satisfied
approval evidence in an action receipt. `runtime_and_app` proves two producer
decisions, not two distinct humans, quorum, separation of duties, or absence of
collusion.

#### Lifecycle, Replay, and Effect Boundary

The producer MUST atomically persist the first terminal `approved` or `denied`
decision for its producer-local `approval_id`. A verifier keys this identity by
producer role, authenticated producer identity, and `approval_id`; equal local
identifiers from the runtime and application are not a collision. An exact
replay returns the same immutable receipt; a conflicting second decision under
that complete producer key is an integrity failure and MUST NOT rewrite the
first. A runtime denial ends before Action Request dispatch. An application
denial occurs after request dispatch but before budget or effect admission; it
MUST NOT dispatch an external effect. Neither denial revokes the Grant.
Reversal requires a new decision attempt, new `approval_id`, and new receipt
while retaining the denial record according to policy.

Before first effect admission, the application MUST verify the complete
required approval set, current Grant and session, exact surface and invocation
tuple, current application policy, receiver-capped approval expiry, preview and
reservation, preconditions, and effect envelope. It MUST atomically bind the
accepted approval hashes into the action's idempotency record with budget and
effect admission. Reusing the same idempotency key with a different approval
set is `idempotency_conflict`; reusing a receipt with any other bound tuple is
`integrity_mismatch`. A receipt that has reached its effective expiry cannot
admit a first effect and fails as `approval_expired`.

An exact replay after an effect was already admitted returns the original
immutable action result and approval and action receipt references even if the
approval later expires; it MUST NOT admit another effect or request another
approval. If no effect was admitted, expiry requires a fresh approval. Grant
revocation, session invalidation, a changed surface or execution, stale preview
or reservation, changed preconditions or expected effects, and current policy
denial always take precedence over an unused approval. Expiry after an external
effect dispatch begins does not rewrite its actual outcome.

This profile does not itself standardize approval UI, step-up authentication,
clarification, redlines, option selection, legal consent, electronic
signatures, non-repudiation, trusted timestamps, cancellation, rollback,
compensation, or proof that a person saw or understood a presentation. The
separate Human Elicitation Events Profile can carry typed clarification,
selection, edit, redline, and step-up results, but none is Approval Receipt
evidence or proof that a person understood an approval presentation.

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

Approval Receipts are root evidence objects and always omit
`parent_receipt_hash`; their hashes are prerequisite side links and do not add a
parent edge. Under the Approval Receipt Profile, a runtime action receipt MUST
carry exactly the absent object or `runtime` member sent in the Action Request.
The application action receipt MUST preserve that runtime member and MAY add
only its newly produced `application` member. Its final map MUST exactly satisfy
the effective manifest mode and Grant requirement. An application receipt that
claims an applied or attempted effect while omitting a required role, linking a
denial, or substituting another Approval Receipt is invalid evidence.

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

Copying a receipt into a Portable Replay Bundle does not strengthen its
authentication, completeness, effect, or authority claim. A replay validator
applies the same receipt structure, hash, parent-link, signature, and producer
rules to the exact carried object and MUST NOT treat the bundle or its exporter
as the receipt producer.

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
    "passport_hash": "sha-256:<base64url-digest>"
  },
  "runtime": {
    "runtime_id": "application_runtime_456"
  },
  "subject": {
    "user": "user_abc"
  },
  "idempotency_key": "idem_01HX7DS8AC6G9",
  "approval_receipt_hashes": {
    "runtime": "sha-256:<runtime-approval-receipt-digest>"
  },
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
  "budget_charges": [
    {
      "budget_id": "tool_calls",
      "amount": 1,
      "ledger_revision": 12
    }
  ],
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
    "passport_hash": "sha-256:<base64url-digest>"
  },
  "subject": {
    "user": "user_abc"
  },
  "idempotency_key": "idem_01HX7DS8AC6G9",
  "approval_receipt_hashes": {
    "runtime": "sha-256:<runtime-approval-receipt-digest>"
  },
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
  "resource": {
    "type": "comment",
    "id": "comment_789"
  },
  "budget_charges": [
    {
      "budget_id": "write_actions",
      "amount": 1,
      "ledger_revision": 18
    }
  ],
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
JWS. Under the Approval Receipt Profile, a listed role MUST also sign every
Approval Receipt it produces; `approval.role` selects the same role-specific
key policy. That signature authenticates the producer record, not a human
approver or trusted timestamp. The requirement MUST include at least one pinned
`signer_keys` entry for each required role. Because the requirement and key
pins are inside the hashed grant rather than the removable signature envelope,
they cannot be stripped without changing `grant_hash`. If the grant has no such
requirement, an unsigned receipt remains conforming hash-linked audit material
but MUST NOT be represented as authenticated portable evidence.

A verifier MUST validate receipt structure and linked hashes first, reconstruct
the canonical detached payload, enforce protected-header and key policy, verify
the signature required for that receipt's producer role, and then validate the
parent chain to a trusted anchor. A present but invalid, unknown, or
unverifiable signature MUST NOT be downgraded to an unsigned receipt. Missing
or invalid required signatures make the receipt invalid as evidence; they do
not retroactively authorize or undo the underlying application action.

## Portable Replay Bundle Profile

The Portable Replay Bundle Profile defines one bounded, deterministic,
offline representation of historical ASP evidence for debugging and audit. Its
profile identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/replay-bundle/v1
```

A v1 bundle covers exactly one `session_id` and one positive
`session_generation` under one complete subject, application, Surface, Grant,
runtime, agent, and Passport-hash tuple. It carries an exact historical Agent
Surface Manifest, an exact historical semantic Agent Grant, and an ordered
hash chain containing only session transitions, application-event deliveries,
event acknowledgements, event gaps, receipts, and explicit capture gaps.

The profile is passive and descriptive. A bundle is not a Grant, Grant
Credential, current session record, event cursor, acknowledgement, approval,
receipt signature, trusted timestamp, effect proof, execution request, or
instruction. Its `claim_effect` is the literal `descriptive_only`. Loading,
hashing, validating, or rendering a bundle MUST NOT cause network access,
online event replay or acknowledgement, session lifecycle mutation, action
dispatch, agent or model execution, approval, compensation, revert, or another
application effect.

### Bundle Scope and Historical Context

The bundle is a closed I-JSON object containing exactly the required members in
this table:

| Member | Requirement |
| --- | --- |
| `$schema` | Literal `./bundle.schema.json`. It selects the repository schema for this wire object and is not a network retrieval instruction. |
| `schema_version` | Integer `1`. |
| `profile` | Exact Portable Replay Bundle Profile identifier above. |
| `protocol_version` | Literal `agent-surface/0.1`. |
| `claim_effect` | Literal `descriptive_only`. |
| `bundle_id` | Non-empty bounded identifier unique in the exporter's retained bundle namespace. It is correlation, not authority. |
| `created_at` | RFC 3339 UTC timestamp with the `Z` suffix describing export construction time, not trusted occurrence time. |
| `scope` | Closed one-session-generation tuple defined below. |
| `context` | Closed object containing exactly `surface` and `grant`. |
| `capture` | Closed capture-boundary object defined below. |
| `records` | Non-empty ordered array of at most 4096 Replay Records. |
| `bundle_hash` | Canonical Object Hash Profile result for the complete bundle with only `bundle_hash` omitted. |

`scope` contains exactly:

- `subject_user`
- `issuer`
- `app_id`
- `surface_version`
- `surface_hash`
- `grant_id`
- `grant_hash`
- `runtime_id`
- `agent_id`
- `passport_hash`
- `session_id`
- `session_generation`

The string identifiers are non-empty and bounded, each hash uses the
`sha-256:` representation from the Canonical Object Hash Profile,
`session_generation` is a positive CloudEvents-compatible 32-bit integer, and
`issuer` is an absolute URI. The tuple is descriptive replay scope; none of its
identifiers is a credential.

Every timestamp whose syntax is evaluated by this v1 profile uses a four-digit
year, the UTC `Z` suffix, seconds from `00` through `59`, and at most nine
fractional-second digits. Leap-second timestamps and other UTC offsets are not
supported by v1 and make the bundle invalid. This restriction also applies to
the carried event, acknowledgement, gap, receipt, Policy Decision, and approval
timestamps inspected by replay checks; it does not reinterpret an unchecked
timestamp elsewhere in an embedded native object.

`context.surface` is the complete exact historical Agent Surface Manifest,
including its `surface_hash`. `context.grant` is the complete exact historical
semantic Agent Grant, including its `grant_hash`; it MUST NOT contain or embed
a Grant Credential. A validator MUST recompute both hashes and require:

- the manifest `issuer`, `app_id`, `surface_version`, and `surface_hash` to
  match `scope`;
- the Grant id, subject user, Grant hash, resource-server issuer, app, Surface
  version and hash, runtime id, agent id, and Passport hash to match `scope`;
- every carried event and receipt binding that applies to the same tuple to
  match `scope` and those exact historical objects.

The historical context permits deterministic interpretation of the carried
records. It does not establish that the manifest is still current, the Grant
is active, the Passport is valid, the session exists, or any credential would
be accepted now. A verifier MUST NOT contact an issuer, schema host, status
service, JWKS endpoint, or another URI to upgrade those historical objects.

`capture` contains exactly `started_at`, `ended_at`, and `completeness`.
The timestamps use RFC 3339 UTC with the `Z` suffix and `started_at` MUST NOT be
later than `ended_at`. `completeness` is `complete` or `partial`. It is an
exporter assertion about the bounded record source, not independently
authenticated proof that no event or receipt ever existed. The value is
`partial` if and only if at least one `capture.gap` records exporter loss,
redaction, or unavailable source material; with no such gap it is `complete`.
An `event.gap` instead describes the application event history and independently
makes replay completeness incomplete without changing capture completeness.

### Replay Record Object

Every element of `records` is a closed object containing:

| Member | Requirement |
| --- | --- |
| `ordinal` | Zero-based array position. Ordinals are contiguous and equal their array indexes. |
| `record_id` | Non-empty identifier unique within the bundle. |
| `recorded_at` | RFC 3339 UTC timestamp with the `Z` suffix. It is diagnostic capture time, not causal or trusted time. |
| `kind` | One exact kind from the table below. |
| `name` | The one exact name paired with `kind`. |
| `representation` | Literal `exact`. |
| `elisions` | Required empty array. |
| `body` | Exact closed or existing ASP object selected by `kind` and `name`. |
| `previous_record_hash` | Required from ordinal `1`; absent at ordinal `0`; equal to the immediately preceding `record_hash`. |
| `record_hash` | Canonical Object Hash Profile result for the complete Replay Record with only `record_hash` omitted. |

The allowed record pairs and bodies are:

| `kind` | `name` | Exact `body` |
| --- | --- | --- |
| `session_transition` | `session.transition` | Closed object containing exactly `session_generation`, `prior_state`, `next_state`, and non-empty `reason`. |
| `event_delivery` | `event.delivery` | Complete ASP CloudEvent structured event object, without an additional Runtime Bridge envelope. |
| `event_ack` | `event.ack` | Complete `event.ack` Runtime Bridge message defined by Ordering and Acknowledgement. |
| `event_gap` | `event.gap` | Complete authenticated gap message defined by Replay Cursors and Gaps. |
| `receipt` | `receipt.runtime` | Complete Runtime Receipt whose `receipt_type` is `runtime`. |
| `receipt` | `receipt.app` | Complete App Receipt whose `receipt_type` is `app`. |
| `receipt` | `receipt.approval` | Complete Approval Receipt whose `receipt_type` is `approval`. |
| `capture_gap` | `capture.gap` | Closed object containing exactly `reason`, `started_at`, and `ended_at`; `reason` is `not_captured`, `redacted`, or `source_unavailable`. |

Unknown Replay Bundle or Replay Record members, another kind/name combination,
another representation, a non-empty `elisions` array, or an unknown member in
the closed `session.transition` or `capture.gap` body makes the bundle invalid.
Carried CloudEvents and receipts retain their own extension rules, and every
such extension remains inside the applicable native and replay hashing views.
An exporter that cannot retain or disclose an exact object MUST add
`capture.gap` and set capture completeness to `partial`; it MUST NOT remove
fields, substitute hashes for required bodies, fabricate neutral payloads, or
label a transformed object `exact`.
For every `capture.gap`, `started_at` and `ended_at` use RFC 3339 UTC with the
`Z` suffix and `started_at` MUST NOT be later than `ended_at`.

A bundle never carries a prompt, Action Request, Action Response, raw action
input, standalone execution context, agent message, tool call, executable
content, transport headers, Grant Credential, access or refresh token, cookie,
proof-of-possession material, private key, or raw `execution_token`. A complete
receipt continues to carry the sanitized execution and hash members required
by the Receipts section, but the bundle adds no execution payload and the raw
token remains forbidden.

### Deterministic Replay and Ordering

Replay is a pure reduction over `records` in ascending ordinal order. The
validator first validates strict I-JSON and closed schemas, recomputes the
historical Surface and Grant hashes, recomputes every record hash and prior
link, and recomputes `bundle_hash`. Only after those integrity checks succeed
does it reduce session, event, gap, and receipt state. A validation failure
MUST NOT be repaired by reordering records, resolving a URI, retrieving a
missing parent, accepting a mutable identifier, or inserting inferred state.

A component claiming complete Portable Replay Bundle Profile validation MUST
evaluate every normative requirement in this section. This includes the
complete native Agent Surface Manifest, semantic Agent Grant, CloudEvent,
acknowledgement, gap, and receipt structure, hashing, binding, state-machine,
required-signature, and verification rules selected by each carried object. It
MAY compose authoritative native-profile validators, but an unavailable
required validator, unevaluated required rule, or unavailable required
signature verification is an evaluation error. The component MUST NOT issue a
`valid` or `incomplete` complete-profile result from a strict subset of those
requirements. A bounded tool or check registry does not relax these
requirements.

For `scope.session_generation` equal to `1`, the first
`session.transition` is `absent` to `active` with `session_generation: 1`.
For a later generation `N`, the first transition is `interrupted` to `active`
with `session_generation: N`; this represents the already-authoritative resume
boundary from generation `N - 1` into the scoped generation. Every later
transition remains in generation `N` and follows the Session Authority and
Lifecycle state machine. In particular, a later `interrupted` to `active`
transition in the same bundle is invalid because an accepted resume creates
generation `N + 1` and therefore requires another bundle. A record does not
cause any represented transition; it only describes the historical transition.

For events, the validator MUST:

- apply the complete ASP CloudEvents structure, historical Surface declaration,
  Grant scope, exposure, control/non-control, and `aspeventhash` checks;
- preserve one hash for each `(source, id)` occurrence;
- preserve source, id, event hash, subscription, delivery id, stream, sequence,
  and cursor across delivery attempts;
- require the first completely captured attempt to be `1` and each exact retry
  to increment `aspattempt` by one;
- within one `(subscription, stream)`, require the first delivery of sequence
  `N + 1` to follow an earlier terminal acknowledgement of sequence `N`;
  retries retain the original stream, sequence, and cursor and never allocate
  another position;
- bind every acknowledgement to an earlier delivery's subscription, delivery
  id, and cursor and enforce terminal-outcome consistency; and
- treat every `event.gap` as incomplete event history rather than inventing
  deliveries or authoritative application state.

A covering `event.gap` makes the affected ordering conclusion incomplete. The
validator MUST NOT guess an acknowledgement, infer a missing sequence from
cursor bytes, or treat a later delivery as proof that the predecessor reached a
terminal outcome. An `event.gap` can cover unavailable application-event
positions, but it does not cover the absent terminal acknowledgement of a
delivery that is already present in the bundle. A validated `capture.gap`
between that delivery and later stream progress can instead make the
acknowledgement conclusion incomplete because the exporter may have failed to
capture it.

Record array order supplies deterministic validator input, but it does not
create cross-stream event order or cross-component causality. `recorded_at`,
CloudEvents `time`, trace context, arrival order, cursors, receipt parent links,
and identifier lexical order MUST NOT be substituted for the ordering and
causal rules defined by their source profiles.

For every receipt, the validator applies the existing receipt shape, role,
Canonical Object Hash, embedded Policy Decision, execution, actual-effect,
parent-chain, Approval Receipt side-link, recovery-target, and scope-binding
rules. A referenced parent or side-link receipt appears earlier in a complete
bundle. A missing predecessor in a partial capture makes the corresponding
replay conclusion incomplete; it MUST NOT be fetched or treated as verified.
A missing predecessor in a bundle that claims complete capture is invalid.
Receipt content can describe a producer's historical effect observation, but
the replay result does not independently prove that effect, authenticate the
producer, or authorize recovery.

### Integrity, Completeness, and Validation Report

Integrity and completeness are distinct conclusions once structural and
semantic integrity evaluation succeeds:

- integrity answers whether the present exact objects, hashes, bindings,
  ordering, and state reductions are internally valid;
- completeness answers whether the bounded replay can account for all required
  predecessors and whether the capture contains no declared protocol or export
  gap.

When integrity evaluation fails, the validator cannot safely draw the
completeness conclusion and reports replay completeness as `not_evaluated`.
`capture.completeness: "partial"`, any `event.gap`, any `capture.gap`, or an
unavailable predecessor permitted only by a partial capture makes replay
completeness `incomplete` without weakening hash validation. A validator MUST
NOT upgrade it because later state appears consistent. A bundle claiming
`complete` that omits a required earlier delivery, receipt parent, approval
side link, recovery target, or initial session transition is invalid rather
than incomplete. The absence of an explicit gap does not authenticate an
exporter's completeness claim.

A failure to obtain one strict I-JSON value is outside the Replay Validation
Report state machine. The same is true of a local read or resource-limit
failure, report-serialization failure, or tool self-integrity failure. Such a
failure MUST NOT be mapped to `preflight_failed`, `semantic_invalid`,
`incomplete`, or `valid`, and MUST NOT produce a Replay Validation Report.

Once strict parsing succeeds, the deterministic Replay Validation Report is a
closed object conforming to `./report.schema.json`. It binds its schema and
report versions, literal `claim_effect: "descriptive_only"`, exact tool and
check-registry identity, raw input-byte hash, ordered check results,
data-minimized diagnostics, an evaluated or explicitly neutral replay summary,
a conservative assurance boundary, and `report_hash`. The input `bundle_id`
and `bundle_hash` are non-null in every state except `preflight_failed`. In that
state either value is `null` only when no canonical value can be recovered from
the parsed input; neither value may be inferred or repaired.

The report state is an exact derived truth table:

| `evaluation_state` | Required check outcome | `integrity_verdict` | `replay_completeness` | `verdict` | `replay.status` |
| --- | --- | --- | --- | --- | --- |
| `preflight_failed` | At least one structure, context, secret, record-envelope, hash, ordinal, or prior-link preflight check fails; dependent semantic checks are `not_evaluated`. | `invalid` | `not_evaluated` | `invalid` | `not_evaluated` |
| `semantic_invalid` | Every preflight check passes and at least one lifecycle, event, acknowledgement, gap, or receipt semantic check fails. | `invalid` | `not_evaluated` | `invalid` | `not_evaluated` |
| `incomplete` | No check fails or is unevaluated, and at least one evaluated check reports an explicit permitted evidence gap as `incomplete`. | `valid` | `incomplete` | `incomplete` | `evaluated` |
| `valid` | Every required check is evaluated and passes, and no permitted evidence gap exists. | `valid` | `complete` | `valid` | `evaluated` |

Both invalid states carry a neutral replay summary: `final_session_state` is
`unknown`, `session_generation` and every count are zero, and
`assurance.verified` is empty. Neutralization prevents a partially reduced
state from being represented as replayed history. It does not erase the
ordered diagnostic and check results that distinguish preflight failure from
semantic invalidity.

A check status is local to the exact `tool.check_profile`. `pass` means that
the named check was evaluated in that bounded scope and produced no finding;
it is not a complete-profile assurance claim. `incomplete` means the check was
evaluated without a contradiction but lacked evidence required for a complete
conclusion. `not_evaluated` MUST NOT be interpreted as `pass`.

`assurance.verified` is derived conservatively from passed prerequisite checks,
not merely from the absence of an error diagnostic. A `valid` report includes
all assurance values supported by its exact check profile. An `incomplete`
report includes `recorded_lifecycle` or `recorded_linkage` only when every
check supporting that assurance passes rather than being incomplete; those
assurances cover only the present records and explicit gap boundaries, not
uncaptured history. A `not_verified` assurance value is an explicit negative
boundary, not a waiver of a normative validation requirement. In particular, a
bounded report that leaves complete native object semantics or signature
validity unverified cannot be represented as complete Portable Replay Bundle
Profile validation.

`report_hash` uses the Replay Validation Report domain from the Canonical
Object Hash Profile over the complete report with only `report_hash` omitted.
The report hash and source-byte hash identify bytes; they do not authenticate
the tool, exporter, or source.

Diagnostics contain stable check identifiers, severity, JSON Pointer, and
bounded inert messages. They MUST NOT copy event data, user content, receipt
payloads, identifiers not needed for the pointer, secret values, or retrieved
remote content. Invalid receipt signatures MUST NOT be downgraded to unsigned
evidence. A bounded checker that does not perform required signature
verification MUST expose that limitation in its assurance boundary and MUST
NOT issue a complete-profile validation claim. Offline validation never
upgrades a key by resolving a remote URI. Unless a complete validator has
separately satisfied a normative requirement, the report assurance boundary
leaves producer authentication, current authority, trusted time, external
effect occurrence, and remote schemas unverified.

### Failure, Privacy, and Non-Authority Rules

A parser or validator MUST reject duplicate JSON members, invalid Unicode,
negative zero, non-I-JSON numbers, unknown closed members, unsupported profile
or protocol versions, more than 4096 records, duplicate record ids, broken
ordinals, a wrong prior link, a mismatched native or replay hash, an illegal
session transition, conflicting event delivery identity, a conflicting
terminal acknowledgement, a conflicting receipt identity, or known raw secret
material. It MUST fail closed without emitting a partially trusted replay or
performing recovery. A strict parse rejection occurs before a report state
exists. An unavailable file, exhausted local evaluation limit, report
serialization failure, or tool self-integrity failure is an evaluation error,
not an ASP rejection and not evidence that the bundle is valid.

The exact historical Surface, Grant, event data, and receipts can contain user,
tenant, resource, policy, and audit data. Export, storage, access, rendering,
retention, and deletion remain subject to the strictest applicable Data
Exposure Contract, Grant lifecycle, receipt policy, and local audit policy.
Creating a bundle MUST NOT extend source retention. If exact content can no
longer be retained, the exporter uses a capture gap or declines export; a
digest is not permission to retain plaintext or reconstruct deleted content.

A bundle hash is tamper-evident only relative to an independently trusted
value. An actor able to replace a complete unsigned bundle can recompute its
record and bundle hashes. A validator MUST NOT represent internal consistency
as exporter authentication, non-repudiation, completeness outside the declared
capture, or current protocol authority. Replaying the evidence means reducing
and displaying it inertly; it never means re-executing the recorded system.

## Revocation Semantics

The protocol MUST define what happens when authority changes.

Revocation MUST be possible from both sides. The application-managed and
runtime-managed user paths are defined below and converge on the same
authoritative grant transition.

### Active Grant Management

A Surface Publisher used by a Grant Issuer MUST publish an HTTPS
`revocation.grant_management_url` in the manifest used for issuance. The URL
identifies the application's human-facing active-grant management page, not
the RFC 7009 runtime revocation endpoint and not an authority-bearing
capability URL. Its
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

- application and issuer, grant id and hash, pinned surface mode, version and
  hash, and authoritative active or expiry state;
- runtime id, agent id, passport hash, and available verified identity labels;
- when Runtime Attestation is selected, its concrete profile, opaque verifier
  id, proof-key binding, sanitized assurance, freshness deadline, and coarse
  current accepted or inactive state without raw Evidence or diagnostics;
- exact actions, scopes, locations, resource filters, expiration, immutable
  budget limits, application-authoritative current budget states, and approval
  caveats;
- maximum effects, execution stages, and recovery limitations;
- effective data-exposure classes, redaction, and retention obligations;
- when selected, the exact Remote Processing Privacy profile, path commitment,
  and deterministic classification ceiling without implying verified provider
  behavior;
- when selected, the exact Agent Training Use Policy profile and permitted and
  prohibited effective classes, shown separately from plaintext retention and
  with no claim that revocation or deletion causes model unlearning;
- credential profile and receipt requirements;
- when Approval Receipt is selected, each action's accepted producer roles and
  maximum approval age without exposing individual approval decisions;
- whether revocation cascades to derived grants and the known number of
  affected descendants.

The summary MUST be derived from the stored authoritative Grant Object and the
exact pinned manifest snapshot that the grant references. It MUST NOT silently
reinterpret an old grant using the current manifest. If the pinned snapshot or
some historical display metadata is unavailable, the page MUST mark those
details unavailable, preserve the stored machine identifiers and hashes, and
still allow immediate revocation. Missing display metadata never makes a grant
look less privileged.

Current runtime-authoritative tool, token, time, and runtime-cost states MAY be
shown only when obtained from a mutually authenticated accounting profile. In
its absence the application page MUST label those current states unavailable;
it MUST NOT derive or estimate them from observed Action Requests. Conversely,
the runtime local view is authoritative only for its runtime-owned dimensions
and MAY show current application-owned states only from authenticated
application accounting or introspection. Both views MUST still show every
immutable limit from the Grant Object.

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

When Agent Training Use Policy is selected, the confirmation MUST also state
that revocation stops every new training use under the Grant but does not undo
a permitted training use already completed or prove deletion from a reusable
model, adapter, index, dataset, or other derived artifact.

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
timing boundary. A non-OAuth issuance model claiming Grant Issuer Profile
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
  "specversion": "1.0",
  "id": "event_01J2ABCDEF",
  "source": "https://code.example.com",
  "type": "grant.revoked",
  "time": "2026-06-25T18:30:00Z",
  "datacontenttype": "application/json",
  "dataschema": "https://code.example.com/schemas/grant-revoked.event.schema.json",
  "aspcontrol": true,
  "aspaudience": "application_runtime_456",
  "aspsurfacehash": "sha-256:<base64url-digest>",
  "aspeventhash": "sha-256:<event-digest>",
  "aspsubid": "control_application_runtime_456",
  "aspdeliveryid": "delivery_01J2REVOKED",
  "aspattempt": 1,
  "aspstream": "runtime:application_runtime_456",
  "aspsequence": 7,
  "aspcursor": "opaque:control-position-after-7",
  "data": {
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "app_id": "code.example.com",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "passport_hash": "sha-256:<base64url-digest>",
    "revoked_at": "2026-06-25T18:30:00Z",
    "effective_at": "2026-06-25T18:30:00Z",
    "reason": "user_revoked",
    "parent_grant_id": null,
    "cascade": true
  }
}
```

The event MUST satisfy the CloudEvents 1.0.2 Event Binding and control-event
extension rules. `source` is the manifest issuer, `time` is the revocation
occurrence time, `aspaudience` identifies the target runtime, and
`aspsurfacehash` identifies the retained manifest snapshot. `data` MUST contain
`grant_id`, `grant_hash`, `app_id`, `runtime_id`, `agent_id`, `passport_hash`,
`revoked_at`, `effective_at`, `reason`, and `cascade`; `parent_grant_id` is
REQUIRED for a child grant and otherwise MAY be null. `data.runtime_id` MUST
equal `aspaudience`. Defined reason values are `user_revoked`, `application_revoked`,
`runtime_revoked`, `credential_compromise`, `parent_revoked`, `policy_changed`,
and `superseded`. A runtime MUST still enforce revocation when it receives an
unknown future reason value and MAY preserve that value as opaque audit data.

The event MUST be delivered over an application-authenticated event channel
bound to the manifest issuer and target runtime. The runtime MUST verify
`source`, `aspaudience`, tuple binding, and channel authenticity before acting on
it. Delivery of this control event MUST use event-channel authority independent
of the revoked grant and MUST disclose no more grant data than the target
runtime already possessed. Under the Event Delivery Semantics profile it is
carried in `event.delivery` on the logically separate control subscription and
retains the same event and delivery identity across retries. A future signing
profile MAY additionally define an application signature for portable event
verification.

The runtime MUST compare `data.grant_hash` and `aspsurfacehash` with its retained
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
`source` and `id`, while transport retry is deduplicated by `aspsubid` and
`aspdeliveryid`. A duplicate event MUST NOT create duplicate receipts or repeat
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
- runtime and application MUST reject new actions before idempotency lookup,
  budget admission, receipt creation, or effect
- runtime and application MUST fence or cancel active sessions rather than let
  policy silently complete under invalid evidence
- application MUST apply the Semantic Grant Revocation Transition to every Grant
  and derived Grant bound to the exact Passport tuple

When fresh authenticated status is temporarily unavailable but the Passport is
not known to be expired or revoked, enforcing components MUST fail closed and
fence affected sessions while status is unresolved. A later fresh status result
for the same exact tuple MAY restore use without changing `grant_hash`; an
implementation MUST NOT substitute another artifact or verification profile.

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
| `integrity_mismatch` | A supplied surface, grant, event, input, execution, precondition, effect, policy-decision, receipt, or parent hash does not match its complete hashing view or authoritative projection. |
| `scope_denied` | Grant scope does not permit the action. |
| `resource_denied` | Grant constraints do not permit the target resource. |
| `approval_required` | Required approval is absent. |
| `approval_denied` | A required runtime-side or application-side approval path reached a terminal denial for this exact invocation. |
| `approval_expired` | Required approval evidence expired before first effect admission. |
| `elicitation_invalid` | A Human Elicitation request or response is malformed, stale, expired, conflicting, mismatched to its authenticated tuple or kind contract, or otherwise cannot be accepted safely. |
| `schema_invalid` | Input, output, preconditions, expected effects, actual effects, or mode-specific context does not match its declared or core schema. |
| `input_not_normalized` | Input is schema-valid but is not the fixed point required by the action's manifest-pinned idempotency normalization profile. |
| `idempotency_conflict` | Idempotency key was reused with different input, execution context, or admitted approval-evidence set. |
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
| `remote_processing_violation` | Under an otherwise valid Grant and exposure projection, the runtime's current complete path or recipient enforcement state no longer satisfies the bound Remote Processing Privacy constraint. |
| `training_use_denied` | Under an otherwise valid Grant and source projection, current authoritative state proves that a payload's complete class set is not permitted for training or a recipient's training policy is wider. |
| `passport_invalid` | The exact Agent Passport artifact is missing, malformed, expired, revoked, untrusted, incorrectly signed, or not bound to the selected agent. |
| `passport_profile_unsupported` | A required Passport consuming, artifact-hash, verification, status, or integrity profile is unsupported or incomplete. |
| `passport_status_unavailable` | Fresh authenticated status for the exact Passport tuple cannot currently be established. |
| `runtime_untrusted` | Runtime authentication cannot be mapped to the exact active runtime identity projection, or a required posture, locality, or assurance is absent, stale, suspended, revoked, or mismatched. |
| `surface_incompatible` | A required surface version, profile, or action declaration is unsupported or internally inconsistent and cannot be interpreted safely. |
| `proposal_required` | On a standard surface, the requested state-changing action exists but the Grant authorizes only its reciprocal proposal companion for the same operation. |
| `session_invalid` | Session is unknown, non-active, stale-generation, or not bound to the complete tuple selected by the presented credential. |
| `session_transition_invalid` | Requested session transition, prior generation, target state, or idempotent replay binding is invalid. |
| `event_subscription_invalid` | Event subscription is unknown, inactive, or not bound to the authenticated tuple and current authority. |
| `event_delivery_conflict` | A delivery id was reused with different event content, stream, sequence, or cursor. |
| `event_cursor_invalid` | Replay cursor is malformed, tampered, or bound to another subscription, tuple, projection, or surface. |
| `event_cursor_expired` | Replay position is no longer available under the effective retention window and requires explicit gap recovery. |
| `action_unknown` | Action id is not part of the surface version the grant was issued against. |
| `limit_exceeded` | A named consumptive grant budget is exhausted or the parallel-session occupancy limit is saturated. |
| `safety_guard_triggered` | A runtime runaway guard fenced the current session or lineage-delegate scope before another session creation, scheduling, or transport step. |
| `budget_query_invalid` | A budget query id or its active, current grant, delegate, credential, surface, or application-authoritative budget binding cannot be validated; the response intentionally does not distinguish which check failed. |
| `budget_state_unavailable` | The accounting authority cannot prove the durable grant-lineage ledger or a required reservation and therefore fails closed. |
| `rate_limited` | An authenticated caller-bound partition was throttled independently of Grant caveats and budgets. |
| `capacity_state_unavailable` | The application cannot prove the durable operational-limit state required for safe admission and therefore fails closed without claiming exhaustion. |
| `service_unavailable` | Shared service capacity is unavailable independently of a caller-bound partition; no manifest-declared limit is claimed. |

Errors SHOULD be returned in a structured envelope containing at least the
error code, a human-readable description, and a retryability indication.
Mapping error codes to HTTP status codes is left to a future draft except for
the operational-capacity mappings defined below.

Errors SHOULD be safe to show to users and precise enough for runtime policy
debugging.

`rate_limited` means that an authenticated operational partition exceeded an
admission window, its per-Grant outstanding-action slot count, or a stricter
defensive throttle independently of Grant authority and budgets. ASP treats
too many outstanding requests in that caller-bound partition as caller rate
limiting; shared service overload is not this error. Its transport-neutral
envelope is:

```json
{
  "code": "rate_limited",
  "description": "Application capacity did not admit this request.",
  "retryable": true,
  "limit": {
    "limit_ids": ["comment-create-per-minute"],
    "retry_after_seconds": 12
  }
}
```

The envelope MUST contain `code` with the exact value `rate_limited`, a
non-empty human-readable `description`, and a boolean `retryable`. `retryable`
is true only when the producer has a safe basis that the unchanged logical
request might be admitted later; it is not an instruction to retry.
`limit`, when present, is a closed object. `limit_ids`, when present, is a
non-empty array of unique manifest-declared ids that are safe to disclose for
the authenticated partition. `retry_after_seconds`, when present, is a positive
I-JSON safe integer giving the minimum delay before all disclosed window
blockers can admit the same logical request, rounded up to whole seconds and
never down. When both are present, the array
contains every safely disclosed blocker used to compute that delay; hidden
stricter controls can still prevent admission. Either member can be omitted
when the throttle is private, shared, concurrency-based, or cannot provide a
safe non-identifying estimate. The response MUST NOT expose remaining counts,
raw partition keys, other callers, tenants, Grants, subscriptions, or system
load. Presence of `retry_after_seconds` requires `retryable: true`.

#### HTTP Capacity Error Binding

An HTTP status or response field is transport evidence, not an ASP error
authority by itself. A runtime recognizes an HTTP capacity error only on the
authenticated ASP response path and only when the response carries a valid
common error envelope whose code, status, cache directives, and retry metadata
are mutually consistent. A proxy-generated or unauthenticated `429` or `503`
does not create `rate_limited`, `capacity_state_unavailable`, or
`service_unavailable` semantics.

Every authenticated ASP HTTP endpoint returns `429 Too Many Requests` for this
error and MUST NOT permit the response to be stored; it sends
`Cache-Control: no-store` in addition to the RFC 6585 status semantics. When it
sends `Retry-After`, it MUST use the `delay-seconds` form from RFC 9110 and MUST
include the equal integer as `retry_after_seconds`. A general service overload
not attributed to the authenticated partition uses `503 Service Unavailable`
under RFC 9110 with ASP code `service_unavailable`; it MUST NOT carry
`code: "rate_limited"` or a fabricated manifest limit id. Non-HTTP bindings
carry the same ASP envelope without deriving authority from an HTTP status or
header. HTTP `RateLimit` and vendor `X-RateLimit-*` fields are outside this core
profile. After normalizing the HTTP field values, `Cache-Control` MUST contain
the `no-store` response directive; `no-cache` alone does not satisfy this
requirement.

A retry hint is neither capacity reservation nor proof that no effect occurred.
When `retryable` is false, the runtime stops unchanged automatic retry. When it
is true, the runtime applies its stricter local ceiling and bounded exponential
backoff with jitter; if `retry_after_seconds` is present, it waits at least that
delay before adding jitter. An Action Request reuses the same idempotency key,
normalized input hash, execution context, and still-valid approval evidence. A
throttled `budget.query` reuses the same `query_id` and complete request binding
because no query record was allocated; it MUST NOT allocate new ids to evade
the cardinality throttle. Any other binding follows its defined exact retry
identity. After an ambiguous or possibly admitted action outcome the runtime
first reconciles the authoritative idempotency record; it MUST NOT create a new
key merely because `Retry-After` elapsed. Semantic retry identity remains
stable, while transport authentication follows its binding-specific per-attempt
rules. A DPoP retry creates a fresh proof JWT with a new `jti` and current `iat`,
binds it to the unchanged semantic request, and includes the currently required
server-provided nonce value, if any; the runtime does not invent a new nonce. An
mTLS retry presents the same token-bound certificate over a valid or
re-established authenticated TLS channel, and certificate reuse is not replay.
Other proof-bound and compatibility bindings follow their selected profile.
Every retry revalidates current Grant, session, surface, and approval state,
remains subject to the Runtime Runaway Protection counters, and does not reset
an event root, session epoch, or lineage guard.

`capacity_state_unavailable` is distinct from proven exhaustion. It is
returned in the common envelope with `code`, `description`, and `retryable`, and
MUST omit `limit`. The producer MAY set `retryable` to true only when it expects
authoritative limiter-state recovery to make the unchanged logical request safe
to reconsider; otherwise it sets false. On HTTP it maps to `503 Service
Unavailable`, sends `Cache-Control: no-store`, and MAY carry a `Retry-After`
delay only when `retryable` is true and the producer has a safe recovery
estimate. It creates no new idempotency record, budget delta, app receipt,
workload, or effect. Recovery MUST restore or conservatively retain durable
window and slot state; it never initializes empty counters for an existing
partition.

`service_unavailable` follows the same common envelope and omits `limit`. It is
valid only for a definite pre-admission shared-capacity rejection. If semantic
admission or an effect might already have occurred, the application instead
returns `outcome_unknown` when it can do so or requires authoritative
reconciliation; it MUST NOT disguise that ambiguity as overload. The producer
sets `retryable` true only when the unchanged logical request can safely be
reconsidered after shared-capacity recovery. An HTTP response uses `503 Service
Unavailable`, `Cache-Control: no-store`, and an optional RFC 9110 `Retry-After`
delay consistent with that retryability. It discloses no manifest limit,
partition, caller occupancy, or remaining shared capacity.

For either `503` mapping, `Retry-After` is permitted only when `retryable` is
true and the producer has a safe recovery estimate. It can use either RFC 9110
form. The field is only a minimum transport delay: for
`capacity_state_unavailable` it does not replace authoritative limiter-state
recovery, and for `service_unavailable` it does not replace a new shared
capacity decision. A runtime that observes a status, authenticated response
path, `no-store` directive, envelope code, or `Retry-After` relationship that
does not satisfy this binding MUST reject the HTTP capacity response before
releasing local admission state or scheduling a retry. It retains tentative
accounting and semantic retry identity until the ordinary authoritative
recovery or reconciliation rule resolves them.

`limit_exceeded` remains Grant-budget exhaustion or occupancy saturation;
`safety_guard_triggered` remains a runtime fence; event `max_in_flight`,
`event.flow`, retention, and `event.gap` remain delivery backpressure. An
implementation MUST NOT substitute `rate_limited` for any of them or use a
capacity hint to widen their authority.

An application MUST return `proposal_required` only when the requested action
is a state-changing action in the pinned `standard` manifest, the Grant omits
that action, and the Grant contains its reciprocal `propose` companion with the
same operation id. A missing action in a proposal-only manifest remains
`action_unknown`, and a mode mismatch remains `execution_mode_invalid`.
`proposal_required` is terminal for the unchanged Grant and surface. Changing
only the request mode, action id, execution id, or idempotency key cannot repair
it. The runtime MUST NOT retry by silently selecting a proposal action; it MAY
offer that explicit granted proposal operation or begin a new consent flow for
the existing standard surface.

`runtime_untrusted` intentionally does not reveal which issuer, subject,
credential, posture, locality, assurance, Verifier, measurement, reference
value, or appraisal rule failed. It covers every non-accepted required Runtime
Attestation state and is not retryable with an unchanged request.
Re-authentication, a new challenge and Evidence refresh, enrollment, or Grant
renewal can establish new state. The application MUST return it before
idempotency lookup, budget admission, receipt creation, or any effect. A Grant
Credential or proof failure remains `grant_proof_invalid`; a mismatch between a
stored runtime or stable attestation projection and the hashed Grant remains
`integrity_mismatch`; and an unsupported framework or concrete profile remains
`surface_incompatible`.

`passport_invalid` is not retryable with the same unchanged artifact and trust
state. `passport_profile_unsupported` requires support for the exact named
profile or a new consent and issuance flow; an implementation MUST NOT fall
back to schema-only validation or another verification profile.
`passport_status_unavailable` MAY be retried after authenticated status service
recovery or the profile-defined `retry_after`, but the unresolved attempt MUST
NOT claim an idempotency key, admit budget, create a receipt, or permit an
effect.

`remote_processing_violation` is terminal for the same unchanged path and
Grant. The detecting component MUST block application-originated data before
downstream dispatch and MUST NOT claim that retry, a lower-privilege recipient
label, or a local runtime location repairs the violation. Resolution requires a
known enforceable path under the same exact commitment or a newly matched,
previewed, and consented Grant. Public errors expose neither the recipient nor
the class or policy rule that failed. This code MUST NOT replace
`integrity_mismatch` for a Grant or hash divergence, `runtime_untrusted` for an
invalid Runtime Identity binding, or `data_exposure_violation` for an invalid
source envelope.

`training_use_denied` is terminal for the same unchanged training operation,
source, recipient policy, and Grant. The detecting component MUST block the
payload before training dispatch. Retrying ordinary current-task inference or
obtaining a newly matched, previewed, and consented training set can establish
a different operation; changing only a request id or deleting retained
plaintext cannot. Public errors expose neither the source class set, provider,
nor failed policy rule. This code MUST NOT replace `integrity_mismatch` for a
constraint or hash divergence, `data_exposure_violation` for an invalid source
envelope, or `remote_processing_violation` for a failed path commitment.
An unknown or stale provider capability, policy, or inventory does not establish
this terminal error: it produces blocking `input_unknown` and an
`indeterminate` Capability Match Result. Disclosure remains blocked, but the
runtime MAY retry matching after it refreshes the authoritative provider-policy
state; it MUST NOT retry training dispatch against the unchanged unknown state.

Approval errors apply only after higher-authority Grant, credential, runtime,
session, surface, schema, and execution checks have succeeded. A missing
required role is `approval_required`; an authenticated terminal denial is
`approval_denied`; and an otherwise valid approved receipt past its effective
expiry defined by the Approval Receipt Profile is `approval_expired`. A
malformed, mismatched, hash-invalid receipt, or a denial presented as approval
is `integrity_mismatch`. Reusing an admitted
idempotency key with a different approval hash set is `idempotency_conflict`.
That code takes precedence over a changed `parent_receipt_hash` when the parent
changed because it embeds the different approval set; a competing parent with
the admitted set unchanged is `integrity_mismatch`. These errors occur before
budget or effect admission and expose neither the approver identity nor hidden
policy detail. An authenticated application-side denial error carries only its
opaque `approval_receipt_id` and `approval_receipt_hash`; the caller obtains the
complete receipt through the authenticated receipt channel. A user denial
requires a new explicit interaction rather than blind retry. A policy denial
remains terminal until the relevant policy, Grant, or current state materially
changes and a new decision attempt is authorized; it MUST NOT trigger a repeated
user prompt by itself. `approval_expired` requires fresh approval for the same
still-current invocation. None of these cases invalidates an already completed
exact idempotent replay, which returns its original result.

`input_not_normalized` is retryable only after the runtime applies the pinned
normalization rules; the rejected attempt does not claim the idempotency key or
admit an effect. `execution_mode_invalid`, `execution_transition_invalid`,
`execution_token_invalid`, `reservation_invalid`, `recovery_not_supported`,
`recovery_already_applied`, `session_transition_invalid`,
`event_delivery_conflict`, `event_cursor_invalid`,
`remote_processing_violation`, `training_use_denied`, and `approval_denied` are
not blindly retryable. `approval_expired` is retryable only after fresh
approval.
`safety_guard_triggered` is not retryable within the fenced guard epoch; it
requires explicit local resolution and, for an application session, an accepted
authoritative resume into a new generation.
`budget_query_invalid` is terminal for that query id; a caller MUST NOT assume
that changing only the id repairs invalid authority.
`capacity_state_unavailable` requires authoritative limiter-state recovery and
MUST NOT reset windows or slots.
`service_unavailable` requires a new capacity decision and is automatically
retryable only when its envelope says so; it never proves non-admission after an
ambiguous outcome.
`event_cursor_expired` requires explicit gap recovery rather than substitution
of another cursor. An expired token or failed precondition requires a new read
or dry run and any required approval. A
reservation conflict MAY be retried after a safe `retry_after` interval without
disclosing the holder; an expired reservation requires a new acquisition.
`limit_exceeded` for settled consumptive exhaustion is not retryable under the
same grant. Temporary reservation exhaustion and parallel-session saturation
MAY be retried only after authoritative capacity release when a non-identifying
`retry_after` is available. `budget_state_unavailable` requires authoritative
resynchronization and MUST NOT reset counters.
After an effect was attempted, drift or uncertainty is represented by
`effect_outcome: "partially_applied"` or `"unknown"`, not a retryable
`effect_mismatch`. `outcome_unknown` MUST NOT be retried under a new
idempotency key until the application reconciles the authoritative outcome.

## Versioning and Compatibility

Surface manifests MUST include:

```json
{
  "protocol": "agent-surface/0.1",
  "surface_mode": "standard",
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

- Changing `surface_mode` is a security-relevant incompatible migration. It
  never rebinds or rewrites an existing Grant: that Grant retains the semantics
  of its exact pinned snapshot until expiry or revocation.
  `proposal_only` to `standard` relaxes the surface-wide invariant but does not
  itself authorize an action.
- Removing an action is a breaking change for grants whose scopes cover that
  action.
- Tightening a schema can be a breaking change.
- Adding optional fields is non-breaking.
- Adding, changing, or removing only a valid `risk_explanation` is
  non-breaking for action authority, but still requires a new
  `surface_version` and `surface_hash` and invalidates every pending Consent
  Preview or Human Elicitation bound to the prior snapshot. An active Grant
  continues to use its retained old snapshot and hint. This rule does not make
  a simultaneous change to risk, effects, approval, execution, or recovery
  semantics non-breaking.
- Impact Simulation is runtime-local and adds no manifest member. Enabling or
  disabling the feature does not itself change a surface version. Any manifest
  change still changes `surface_hash`, invalidates a pending simulation with
  its parent Consent Preview, and requires the runtime to regenerate examples
  from the new snapshot. A simulation for a new snapshot MUST NOT reinterpret
  an active Grant pinned to an older retained snapshot.
- Adding a new action is non-breaking only when the resulting manifest remains
  valid under its `surface_mode` and existing action semantics do not change. A
  state-changing action on a proposal-only surface is invalid, not an addition
  that compatibility rules can repair.
- Publishing an application operation that was previously outside ASP is an
  ordinary resource, action, or event addition: it requires a new surface
  version and hash and does not widen a Grant pinned to the prior curated
  snapshot. An underlying API-only change need not change the manifest when it
  does not alter any published affordance or its implementation semantics.
- Changing risk labels to a higher risk class can require grant renewal.
- Changing an action's execution mode, operation id, required companion stage,
  effect envelope, precondition or effect schema, reservation policy, or
  recovery relationship is breaking for grants that authorize that action.
- Adding an optional companion action is non-breaking only when existing action
  semantics, approval, and effect envelopes remain unchanged.
- Changing receipt requirements can require grant renewal.
- Changing endpoint semantics can require grant renewal.

A publisher that changes from `proposal_only` to `standard` MUST use a new
surface version and hash. A runtime MUST require a new semantic Grant request,
fresh Consent Preview, and fresh issuer consent before any state-changing
action can be granted; renewal, refresh, token exchange, or child derivation of
the proposal-only Grant MUST NOT add such authority.

Before, or atomically with, designating a proposal-only snapshot as current and
serving it from the canonical `surface_url`, the application and authorization
server MUST mark every superseded `standard` snapshot for that surface
lifecycle key ineligible for issuance, renewal, token exchange, and child
derivation. This transition MUST fail closed if the shared lifecycle state
cannot be committed.
Retained snapshots remain usable only to interpret, enforce, audit, expire, or
revoke already-issued Grants.

Publishing a proposal-only snapshot does not retroactively narrow an active
Grant pinned to an older `standard` snapshot. If the application intends an
application-wide stop on agent writes, it MUST complete the Semantic Grant
Revocation Transition for those wider Grants, make introspection report them
inactive, and fence their sessions and every action that has not passed final
effect admission before making that claim. Otherwise those Grants retain their
pinned semantics only until their existing expiry or revocation, and the
proposal-only claim applies only to the exact new issuer, app id, surface
version, and surface hash tuple.

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
application. Grants MUST bind user, app, runtime, agent, and the complete exact
Passport tuple selected by the Grant.

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

A Runtime Identity Profile projection is an application-derived description of
an authenticated binding, not a runtime self-assertion. The application MUST
revalidate its current authoritative record for the exact binding id and claims
revision on every action. It MUST NOT infer enterprise management or hardware
assurance from a SPIFFE ID, OIDC claim, device name, key storage mechanism, or
network location, and MUST NOT accept a fallback identity when the Grant-bound
method becomes unavailable.

Runtime Attestation does not change that authority boundary. The application
MUST authenticate the concrete-profile Attestation Result, apply its own
Relying Party policy, verify the exact runtime, Grant request, Target
Environment, proof key, and freshness bindings, and recheck current accepted
state before every effect. It MUST NOT accept the runtime's self-asserted
posture, raw Evidence as a Verifier decision, an accepted result for a different
layer, or an unattested fallback when appraisal becomes stale or unavailable.
Compromise of a co-located Verifier remains a trust-anchor compromise; combining
roles does not turn runtime-controlled policy into independent evidence.

Remote Processing Privacy preserves the same distinction. The application can
authenticate the controlling runtime, bind its requested path, and refuse data
above the server-derived ceiling, but it does not observe every downstream
dispatch. A malicious runtime can falsely claim a local or managed path. The
issuer MUST NOT describe its echo, Grant hash, or runtime locality as proof of
recipient topology. Deployments that require such proof need a separately
negotiated egress or processor-evidence profile; absent one, the path remains an
accountable runtime commitment and the application still minimizes disclosure.

Agent Training Use Policy binds the requested and effective class sets but does
not let the application observe provider-side reuse or prove deletion from a
model or reusable artifact. A malicious runtime can report an equal-or-stricter
recipient policy and then violate it. The issuer MUST NOT describe consent, a
Grant hash, retention cleanup, or a runtime receipt as compliance or unlearning
evidence. Deployments that require such evidence need a separately negotiated
provider-attestation, audit, or verifiable-unlearning profile and still enforce
the class constraint before disclosure.

A runtime budget report can safely request a fence for its own bound session,
but it MUST NOT change application counters, grant authority, or another
session. The application authenticates the complete tuple and performs the
fence itself. Conversely, a runtime accepts application budget state only from
the authenticated control subscription and MUST NOT let an agent fabricate a
control event or pause request.

Mitigations:

- app-issued grants
- token introspection
- runtime binding
- exact Passport profile, artifact-hash, verification, and agent binding
- concrete Runtime Attestation profiles with challenge replay protection,
  authenticated Results, proof-key binding, freshness, and Relying Party policy
- sender-constrained grant credentials
- action-scoped grants
- app-side receipts
- anomaly detection

### Misleading Impact Simulation

A compromised runtime can omit severe examples, label request coverage as
execution permission, reuse a stale result, or invent reassuring denied cases.
The deterministic coverage counts and selection order make those deviations
machine-detectable, while the mandatory canonical Consent Preview keeps every
requested action and material semantic inspectable. An application or
authorization server that receives a result embedded in a closed protocol
object MUST reject that complete object; if it receives a detached out-of-band
supplement, it MUST discard it as evidence. In both cases it performs ordinary
request, consent, Grant, and action verification. The result cannot weaken
app-side enforcement even when the runtime lies to its user.

A malicious application outside the Runtime Mediator trust boundary can
publish misleading labels or Risk Explanation UI Hints and can attempt to send
a fabricated supplement, but it does not supply the machine result or select
its outcome. The user-controlled runtime rejects or discards that input and
derives its result from the verified manifest, exact request, and current local
matching inputs. It retains the canonical risk and effect projection and keeps
any publisher prose outside the closed object. It MUST NOT contact the
application for a concrete negative example because doing so could create a
resource-enumeration oracle or disclose the user's intended delegation before
issuance.

An app-operated, app-embedded, or otherwise compromised runtime collapses that
provenance boundary: the application can then fabricate both the canonical
presentation and the local machine result. In that deployment the Impact
Simulation Result is not independently trustworthy evidence for the user or
any other party. The ordinary application-side and authorization-server-side
verification requirements still apply, and no downstream component can recover
the lost user-controlled presentation guarantee by validating this local
result.

A malformed or stale result is suppressed as one object. Partial rendering is
unsafe because accepting only known examples, omitting coverage metadata, or
retaining an old high-risk ordering can make a broader request appear narrower.
Suppression falls back to the canonical Consent Preview; it never converts
unknown impact into no impact.

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

A signed Passport is declarative evidence, not behavioral containment. Its
artifact hash does not verify the signature, and a valid signature does not
prove capability truth or executable identity. Runtimes and applications MUST
apply the selected verification and status profile independently; runtimes need
a separate integrity profile before claiming a local code binding.

Mitigations:

- no direct credentials in agent process
- no implicit credential or grant transfer to subagents, tools, or remote models
- schema validation
- risk-based approval
- static execution modes and preview-bound approval
- atomic precondition and reservation checks
- durable grant-lineage budgets for writes, tools, tokens, runtime time,
  parallel sessions, and partitioned cost
- durable finite transport, repetition, root-action, causal-depth, and cycle
  guards that fence locally before another scheduling step
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
- runtime presents canonical risk, effect, approval, and recovery semantics
  independently of a labeled application-authored Risk Explanation UI Hint
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
- application-authoritative write and session limits
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

Risk Explanation UI Hint text is also app-authored input. A runtime MUST render
it as inert user-facing text and MUST NOT copy it into an agent system prompt,
tool description, policy expression, approval rule, or privileged instruction
channel. It cannot convert the prose into agent instructions or protocol
authority.

### Replay and Duplicate Actions

Idempotency keys, timestamps, nonce binding, and grant expiration reduce replay
risk. Side-effecting actions MUST be idempotent.

Normalization is part of the pinned action contract, not an application-local
heuristic. A runtime and application MUST use the same supported profile and
MUST NOT infer equivalence from mutable schema defaults or business logic. An
attacker can otherwise reuse a key with two representations that policy,
approval, hashing, and execution interpret differently. Fixed-point wire input
ensures those components bind one value; a changed normalized value or
execution context remains `idempotency_conflict`, and a competing verified
parent receipt remains `integrity_mismatch`.

Application idempotency and runtime runaway detection are separate decisions.
The application uses the idempotency key plus normalized input and execution
binding to decide whether an effect is an exact replay. The runtime uses the
data-minimized action fingerprint only to count repetition, including attempts
with different keys; it MUST NOT send that fingerprint as authority or infer
that two application records can be merged. Transport retry, reconnect, event
replay, and trace restart do not reset the applicable runtime guards.

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

`surface_mode` is part of the manifest hashing view. A runtime that has matched
or obtained consent for `proposal_only` MUST NOT silently accept `standard` as
a compatible refresh, even if every currently selected action has the same
name or schema. That transition requires the fresh surface and Grant flow
defined in Versioning and Compatibility. Conversely, designating a
proposal-only snapshot as current does not erase an old standard Grant. The
application MUST revoke it or continue to enforce that exact older authority
until its existing expiry, while the atomic lifecycle gate MUST reject issuance,
renewal, exchange, and derivation against every superseded standard snapshot.

`surface_hash` commits to schema URLs, explicit schema hashes, and other
manifest values. The required `input_schema_hash` pins the self-contained input
schema for idempotency-required and linked dry-run actions. Other schema URLs
remain references rather than commitments to their transitive content. A
deployment that needs that property must separately pin those schema hashes or
use a future canonical surface-bundle profile.

A cached Risk Explanation UI Hint is subject to the same downgrade boundary.
The runtime MUST bind it to the complete surface tuple, action id, and selected
language and MUST NOT overlay a newer, older, or caller-supplied explanation on
an action interpreted under another snapshot.

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

Approval Receipt side links require the same complete-object verification and
do not become trusted merely because an action receipt names their hashes. An
application MUST reject role substitution, an unaccepted runtime role, an
expired approval at first admission, a denial presented as approval, a
different invocation tuple, and a conflicting decision for one complete
`(producer role, authenticated producer identity, approval_id)` key. Neither a
valid receipt hash nor a producer signature replaces current action authority
or proves a human gesture. `runtime_and_app` authenticates two producer records
only; it is not a quorum or separation-of-duties guarantee.

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

Approval and denial receipts reveal user decisions, timing, application and
runtime relationships, action frequency, and policy outcomes. They MUST contain
only an app-scoped user reference and hashes of the exact invocation, never raw
input, previews, credentials, execution tokens, hidden rules, authentication
artifacts, or globally correlatable approver identities. Runtime-local denials
SHOULD remain local when no Action Request was dispatched. Applications and
runtimes SHOULD retain complete Approval Receipts only for the bounded
idempotency, reconciliation, audit, and applicable legal period and MUST NOT
expose full denial evidence to the agent process merely for error handling.

Runtime identity metadata requires the same minimization. Grants and their
derived protocol artifacts use only the app-scoped runtime id, opaque binding
id, sanitized profile facets, claims revision, and policy-relevant assurance
references. External subjects, raw certificates, SVIDs, JWTs, management
records, attestation evidence, device serials, hardware handles, and recovery
material MUST remain in the authoritative verifier boundary and MUST NOT enter
receipts, events, traces, ordinary logs, prompts, or agent-visible context.

Runtime Attestation can expose uniquely identifying measurements, hardware and
firmware inventory, debug state, location-correlatable device identifiers, and
long-lived Attester keys. The runtime sends raw Evidence only to the selected
Verifier, and the application retains only the concrete profile's minimized
Attestation Result and authoritative appraisal record. Grants contain only the
stable opaque binding and policy-relevant assurance; authorized status views
expose at most the coarse current state. Consent, public errors, receipts,
events, traces, prompts, and ordinary logs MUST NOT disclose raw Evidence or the
specific failing measurement, reference value, or appraisal rule.

Passport artifacts and admission projections can expose stable agent uids,
issuers, capability inventories, security policies, executable paths, and code
measurements. Protocol-visible Grant state is limited to the app-scoped agent
id, optional locator, and exact consuming, hash, artifact, and verification
profile tuple. Raw Passport bytes, signatures, external issuer subjects, status
responses, executable paths, and code hashes MUST remain inside the applicable
verifier boundary.

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
defaults are not implied by a retention declaration. The Remote Processing
Privacy Profile, when selected, applies a conservative Grant-wide ceiling and
requires the runtime to resolve the complete path before disclosure; it still
does not prove provider behavior. When Agent Training Use Policy is selected,
its explicit class set independently controls secondary use: an empty set means
no training use, a non-empty set permits only whole sources whose complete
class set is covered, and omission remains unspecified. A training permission
does not widen path, redaction, or retention constraints, and plaintext cleanup
or revocation does not prove that an allowed durable model influence was
removed.

Processing-path metadata can expose provider relationships, enterprise
boundaries, user choices, and regional deployment details. The Grant therefore
contains only the coarse path value and ceiling. Recipient inventory, endpoints,
account ids, enterprise mapping evidence, and provider-policy records remain in
the runtime or enterprise-policy boundary and SHOULD be retained only as long
as enforcement and data-minimized audit require.

Training-policy metadata reveals user choices, source classifications, and
provider capabilities. Protocol artifacts therefore carry only the profile and
canonical class set. Provider policy documents, account identifiers, model
names, enforcement inventories, local decision records, and audit evidence
remain within their applicable trust boundary and SHOULD be retained only as
long as enforcement, user management, and data-minimized audit require.

Consent previews contain sensitive relationship metadata even when they omit
application payloads. Implementations SHOULD avoid placing rendered previews in
telemetry, browser history, or general-purpose logs. A local preview is not
portable consent evidence and SHOULD be retained only as long as local policy
needs it to complete and audit the authorization flow.

Impact Simulation Results contain the same surface, delegate, Passport,
inventory, policy, preference, and requested-action relationship metadata.
They MUST remain within the user-controlled runtime boundary, MUST NOT contain
action input, concrete resource keys, hidden policy text, publisher prose, or
application payloads, and SHOULD be retained no longer than their parent local
preview. Telemetry SHOULD retain at most the feature identifier, request and
surface hashes, coverage counts, outcome counts, and machine reason codes under
a bounded local policy; it SHOULD omit action identifiers when aggregate
diagnostics suffice.

Active-grant management views contain the same relationship metadata plus
lifecycle state and usage-sensitive constraints. Applications and runtimes MUST
authenticate those views, avoid cross-subject enumeration, exclude credentials
and application payloads, and prevent caching or referrer leakage as defined by
Active Grant Management. Historical summaries SHOULD retain only the metadata
needed for user understanding, security audit, and applicable legal obligations.

Budget states and charges reveal workload volume, model usage, session
concurrency, and spend. Components MUST expose them only to the bound subject,
accounting authority, and authorized audit consumers, and SHOULD retain
fine-grained revisions no longer than reconciliation and audit require. Errors
and events MUST identify the budget dimension without disclosing another
session, tenant, model prompt, tool argument, or provider billing record.
For a descendant delegate, control events and `budget.state` MUST use the
effective lineage projection and per-target revision defined above; ancestor
identifiers, limits, counters, revisions, and sibling consumption are not part
of that delegate's disclosure.

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

This draft defines six independent role profiles instead of one
all-or-nothing application profile:

| Role profile | Profile identifier | Responsibility boundary |
| --- | --- | --- |
| Surface Publisher | `https://github.com/0al-spec/agent-surface/conformance/surface-publisher/v1` | Manifest discovery, integrity, lifecycle, schemas, and advertised surface semantics. |
| Grant Issuer | `https://github.com/0al-spec/agent-surface/conformance/grant-issuer/v1` | Consent, authoritative Grant construction, credential binding, attenuation, lifecycle, and revocation. |
| Action Executor | `https://github.com/0al-spec/agent-surface/conformance/action-executor/v1` | Protected-resource verification, session and event enforcement, and final effect admission. |
| Receipt Producer | `https://github.com/0al-spec/agent-surface/conformance/receipt-producer/v1` | Immutable role-scoped receipt evidence for authoritative observations made by that producer. |
| Runtime Mediator | `https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1` | Local consent, credential custody, agent mediation, policy, runtime safety, and revocation handling. |
| Agent Adapter | `https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1` | Typed translation between an agent and a Runtime Mediator without receiving or creating authority. |

The identifiers above name the exact role-profile versions defined by this
draft. A similar name, an older version, an implementation-specific label, or
an unknown profile identifier MUST NOT be substituted. This draft does not
define a manifest `conformance` member, a signed conformance certificate, or a
certification authority. It defines the descriptive machine-readable test
report below, but that report is not protocol authority. If a future profile
adds claim metadata to a manifest, that metadata MUST use a closed versioned
shape and be included in the manifest hashing view.

### Conformance Claim and Composition Rules

A conformance claim is descriptive. It is not a Grant, credential, approval,
attestation result, certification, trust anchor, or evidence that another role
performed its checks. A participant MUST NOT skip manifest, Grant, credential,
session, selected-profile, receipt, lifecycle, or current-state verification
because another participant claims a conformance role.

Conformance is atomic for one role-profile version and one named implementation
or deployment boundary. A claim MUST identify that boundary, the exact profile
identifier, the supported ASP protocol version, and every optional profile or
feature included in its scope. A Receipt Producer claim MUST additionally name
exactly one `producer_role`, `application` or `runtime`. This documentation is
not a protocol authority object and MUST NOT be copied into a Grant or receipt
as proof of conformance.

An implementation that omits an unconditional requirement, or a conditional
requirement for a feature it advertises, selects, accepts, invokes, or produces,
MUST NOT claim that role profile for the affected boundary. It MAY instead
claim a smaller deployment boundary that does not expose the feature. A claim
MUST NOT use terms such as "partial", "mostly", or "compatible" as if they
were the role profile identifier.

Each claim names exactly one role. A process, product, or deployment MAY claim
multiple roles only by satisfying and documenting each role independently.
Conformance to one role does not imply conformance to another role, even when
one binary or operator implements both. In particular:

- a Surface Publisher claim does not prove Grant Issuer or Action Executor
  behavior;
- a Grant Issuer claim does not let an Action Executor trust a credential or
  cached Grant state without its own checks;
- an Action Executor claim does not make that component a Grant Issuer or
  Receipt Producer;
- a signature service does not become a Receipt Producer merely by signing
  bytes; and
- a Runtime Mediator or Agent Adapter does not become an application-side
  authority by observing a request or response.

A conforming deployment can compose independently operated roles. The consumer
of another role's output MUST validate that output under the ordinary protocol
rules; the producer's self-claim is not sufficient. Delegating an internal
task, endpoint, signing operation, schema host, database, or policy engine does
not dilute the externally observable requirements of the claiming role. If a
required delegate or authoritative state is unavailable, the composed service
MUST fail closed before Grant issuance, application-originated disclosure,
effect admission, or an authoritative receipt claim.

Active Grants remain bound to their exact manifest and Grant semantics when a
deployment changes its claimed roles or implementation topology. A role change
MUST NOT reinterpret an old Grant, weaken a selected optional profile, or make
an unsupported profile look conforming. The ordinary versioning, renewal,
revocation, and fresh-consent rules continue to apply.

The role boundaries have these required fail-closed cases:

| Role | Invalid claim or operation |
| --- | --- |
| Surface Publisher | Reusing a surface version with another hash, publishing incomplete references, or advertising semantics that the exposed surface cannot provide. |
| Grant Issuer | Issuing against a stale or superseded surface, widening a request, returning an unclosed action set, or treating unknown Passport or selected-profile state as accepted. |
| Action Executor | Trusting the issuer claim instead of independently validating audience, active Grant state, exact surface and delegate tuple, session generation, policy, budget, approval, idempotency, and effect preconditions. |
| Receipt Producer | Claiming another producer role's observation, producing a receipt outside the authoritative decision record, downgrading an invalid signature, or treating a receipt as action authority. |
| Runtime Mediator | Using a stale match or Consent Preview, storing a wider Grant, releasing a Grant Credential, or continuing while revocation state is unknown. |
| Agent Adapter | Receiving credentials, selecting stronger authority, fabricating approval/effect/receipt evidence, or blindly retrying a partial or unknown outcome. |

### Interoperability Test Suite

The versioned suite identifier
`https://github.com/0al-spec/agent-surface/conformance/suite/v1` targets the
exact protocol identifier `agent-surface/0.1` and the six role-profile
identifiers above. Its canonical matrix, vectors, semantic fixtures, schemas,
and runner contract are published under `conformance/v1/` in this specification
repository. Stable requirement, vector, fixture, and mutation identifiers MUST
NOT be reused with different semantics.

The v1 matrix is an executable high-risk coverage subset. It covers manifest
integrity and proposal-only bounds, exact Grant attenuation and revocation,
Grant verification, idempotent replay and conflicts, denied actions, receipt
role integrity, runtime mediation, adapter authority boundaries, and the
Operational Limits declaration, action-admission, logical event-delivery, and
retry contracts. It also covers the core Risk Explanation UI Hints manifest
shape and the boundary between inert publisher prose and runtime-derived
machine semantics, plus the bounded local Impact Simulation projection and its
separation from execution, consent, and authority. It does not enumerate every
normative requirement in every role profile. Consequently,
a `pass` suite verdict means only that every applicable vector in the exact
catalog revision passed. It MUST NOT be represented as complete role-profile
conformance, certification, interoperability with arbitrary implementations,
or current operational security.

One test run and one report evaluate exactly one profile identifier for one
named deployment boundary and one implementation artifact and configuration.
The subject binds their digests, the exact protocol identifier, and the complete
set of optional features in scope. A Receipt Producer subject additionally
binds exactly one `producer_role`, `application` or `runtime`; that field is
invalid for every other role. Co-located roles require separate reports. A
counterpart participating in an `interop` vector MUST match every exact profile
and Receipt Producer role required by that vector, use another deployment
boundary and implementation artifact, and be bound into the observation. An
unrelated, same-boundary, suite-fixture, or self-asserted counterpart does not
satisfy the vector and gives no conformance credit to any role.

Each matrix requirement has closed applicability: unconditional, selected
optional feature, or Receipt Producer role. Before deriving applicability, the
runner obtains a feature inventory from the separately configured probe and
requires it to equal the subject's complete declared feature scope. An operator
or subject MUST NOT hide a supported, advertised, selected, accepted, invoked,
or produced feature or mark an applicable case as not applicable. A selected
feature with no matrix row for the target role is reported as uncovered and
makes the suite verdict `incomplete`. Unknown profiles, features, producer
roles, requirement ids, vector ids, results, members, or applicability states
invalidate the run rather than weakening its closure.

Vectors use only the suite's closed declarative operation, fixture, mutation,
assertion, observation, and state-delta vocabulary. Each case resolves to one
digest-bound semantic baseline and an exact closed `replace` patch. Vectors
MUST NOT contain executable code, shell commands, or target URLs.

The versioned `schema-cases.json` corpus executes positive and negative cases
for the Operational Limits declaration, operational-capacity error envelope,
Risk Explanation UI Hint object, and Impact Simulation Result.
Each candidate is carried as an inert JSON string so malformed I-JSON,
duplicate-member, unsafe-integer, schema-invalid, and semantic binding failures
can be represented without making the corpus itself invalid. The validator
parses each candidate with the suite's strict I-JSON rules, validates it against
its versioned JSON Schema, and, for a declaration, checks action and event
resolution, idempotency eligibility, globally unique `limit_id` values, and the
core control event plus manifest-declared control-event exclusion against the
case's closed manifest context. For a risk explanation it additionally checks
canonical sorted languages, exact default-language presence, bounded inert
text, and complete declaration-order effect coverage against the case's closed
parent-action context. For an impact simulation it additionally checks exact
surface, request, delegate, match and revision bindings, complete requested
coverage, bounded deterministic unrequested selection, outcome/reason
consistency with the exact selected-candidate decision, omission of advisory
reasons, canonical action projections, exact derived recovery limitations, and
absence of resource instances or publisher prose. For a capacity envelope it
additionally
requires every disclosed `limit_id` to be both manifest-declared and safe for
the authenticated active partition. The common capacity envelope remains open
to extension members as required by the Error Model, while its `limit` member
remains closed.
A positive case that fails or a negative case that passes invalidates the
catalog.

The separately configured stimulus adapter receives the resolved fixture,
setup, operation, subject, and required counterpart topology, but it MUST NOT
receive expected errors, policy or match reasons, observation tokens, or state
values. A separate authoritative probe discovers feature inventory and returns
sanitized observations after execution. The runner alone compares those
observations with its oracle and decides the result.

The runner invokes fresh adapter and probe processes with a fresh working
directory, constrained environment, process-group timeout, file-size,
file-descriptor, and CPU limits, and bounded captured output for every vector.
Both executables are trusted test components; these limits do not sandbox them
or block filesystem and network
access. Operators MUST isolate the harness and non-production subject
environment for their risk model. Concurrency tests use deterministic barriers
around the specified linearization point rather than timing sleeps.

A negative vector passes only when the observed ASP decision and namespaced ASP
error, Policy Decision reason, or Capability Match reason, where the RFC defines
one, match the expected values and every declared
postcondition holds. Error status alone is insufficient. The vector can require
zero new effects, budget revisions, idempotency records, credentials, receipts,
Grant records, or control events, or the exact receipt and lifecycle deltas
required by that denial phase. A crash, timeout, malformed response,
unavailable authoritative probe, or unknown state is an execution error, never
a successful rejection. An HTTP status is an assertion only when a vector
explicitly selects a binding for which this draft defines a normative mapping.
The HTTP Capacity Error Binding vectors use a closed normalized fixture
projection of the authenticated response path, status, parsed cache directive
result, and parsed `Retry-After` form. That projection is test-harness input,
not an ASP wire object. The transport-neutral Operational Limits vectors
continue to validate the common capacity envelope without inferring an HTTP
status from an ASP error code alone.

The ASP-over-AHP vectors likewise use a closed normalized projection of profile
selection, authenticated carrier state, AHP representation identity and
revision, and the embedded ASP tuple. The projection exercises the binding
contract without defining the base AHP wire format. Positive cases prove that
presentation and exact action translation preserve ASP authority; negative
cases cover profile downgrade, unauthenticated transport, session-generation
substitution, conflicting representation replay, action substitution, and an
AHP receipt summary presented as authority.

The Human Elicitation vectors use the standalone closed profile schema and a
closed normalized projection of authenticated requester and presenter state,
the current session, Grant, surface, context, immutable replay record, and any
candidate validation state. Positive cases cover clarification, closed choice,
step-up verification, normalized edit, base-bound redline results, and exact
retained terminal replay. Negative cases cover stale session generations,
conflicting terminal replay, agent-asserted or secret-bearing step-up results,
stale edit bindings, and redline result substitution. Agent Adapter cases
separately prove minimized, purpose-bound answer projection and rejection of
agent-originated resolutions or secret-bearing envelopes. No passing Human
Elicitation vector establishes approval, consent, Grant, dispatch, effect,
receipt, or authentication-factor authority.

The Risk Explanation UI Hints cases use a closed parent-action context and
publisher object plus a normalized Runtime Mediator presentation observation.
Positive cases cover a sorted multilingual object, RFC 4647 Lookup and default
fallback, exact effect-summary order, literal isolated presentation, and
display alongside canonical risk and effects. Negative cases cover a missing
default, duplicate or non-canonical languages, control characters, unknown,
missing, duplicate, or reordered effect ids, a stale surface or action cache
binding, an incomplete retained manifest projection, missing output-context
escaping or presenter-controlled bidirectional isolation, use of prose in
matching or approval, and projection into an agent instruction. A passing case
establishes only structural and boundary behavior; it cannot prove that
human-authored prose is truthful or complete beyond its machine-checkable
effect-id coverage.

The Impact Simulation cases use a closed normalized verified-manifest semantic
projection produced from an exact manifest, semantic Grant request, selected
delegate, normalized matching check facts, complete authoritative binding and
freshness facts, plus a normalized Runtime Mediator presentation observation.
Positive schema and direct semantic cases cover complete
requested action projection, deterministic highest-risk unrequested selection,
covered, not-covered, and indeterminate outcomes, empty and truncated
unrequested sets, exact companion, effect, exposure, and recovery data, and
atomic fallback to the canonical Consent Preview. Negative catalog cases cover
an omitted requested action, more than 64 requested actions represented as a
partial result, incorrect high-risk selection or coverage counts, stale
surface, request, match or revision bindings, outcome/reason conflicts, closed
Grant and Action carrier embedding, and post-issuance reuse. Direct semantic
and state-isolation checks additionally prove that accepted and suppressed
paths do not contact the application, run an application dry run, or project
the result into approval, receipt, Policy Decision, or agent state. Detached
publisher prose and fabricated concrete resource examples remain prohibited
normative inputs but are outside the executable input subset of this v1
harness. Closed-carrier vectors and direct semantic cases duplicate the
complete Result into Grant and Action objects, reuse an active post-issuance
Grant, and exercise exact-action replay. Each Grant Issuer, Runtime Mediator,
Action Executor, and Agent Adapter case rejects the duplicate before changing
state whenever that operation actually consumes the affected closed object. A
passing case establishes local projection behavior only; it does not establish
consent, issuance, current authority, approval, or successful execution.

The report binds the exact suite and specification sources, ordered applicable
requirements and vectors, each vector digest, subject and counterpart artifacts,
runner, adapter and probe entry-point digests, configuration digests and
versions, execution environment, run identifier, and run interval. Each
observation binds that run identifier, the complete subject, harness, and exact
participating counterparts.
The report contains one result for every applicable vector. The validator
recomputes all applicability, digests, vector closure, result counts, and the
suite verdict:

- any assertion failure produces `fail`;
- otherwise any missing result, execution error, unavailable probe, uncovered
  selected feature, suite-fixture subject, or stale binding produces
  `incomplete`;
- only a complete applicable set of passing results produces `pass`.

The catalog digest is SHA-256 over the ASCII domain
`ASP-CONFORMANCE-CATALOG-V1` followed by a zero octet, then each canonical
catalog path in lexicographic order as UTF-8, a zero octet, its raw file bytes,
and a final zero octet. The canonical set is exactly
`capacity-error.schema.json`, `fixtures.json`, `fixtures.schema.json`,
`human-elicitation.schema.json`, `impact-simulation.schema.json`,
`observation.schema.json`,
`operational-limits.schema.json`,
`report.schema.json`, `risk-explanation.schema.json`, `schema-cases.json`,
`schema-cases.schema.json`,
`subject.schema.json`, `suite.json`, `suite.schema.json`, `vectors.json`, and
`vectors.schema.json`, each under `conformance/v1/`. The specification
digest uses the ASCII domain
`ASP-SPECIFICATION-SOURCE-V1`, a zero octet, and the raw bytes of
`drafts/agent-surface.md`. A vector digest uses the ASCII domain
`ASP-CONFORMANCE-VECTOR-V1`, a zero octet, and the RFC 8785 serialization of
the vector object. The subject digest uses the ASCII domain
`ASP-CONFORMANCE-SUBJECT-V1`, a zero octet, and the RFC 8785 serialization of
the complete subject object, including counterpart bindings. A counterpart
entry and the complete runner object use the same form with domains
`ASP-CONFORMANCE-COUNTERPART-V1` and `ASP-CONFORMANCE-HARNESS-V1`.
The canonical runner entry point and configured adapter and probe entry points
use raw bytes under `ASP-CONFORMANCE-RUNNER-V1`,
`ASP-CONFORMANCE-ADAPTER-V1`, and `ASP-CONFORMANCE-PROBE-V1`. Each digest is
encoded as `sha-256:` followed by canonical unpadded base64url. These digests
bind bytes and catalog selection; they do not authenticate an implementation,
runner, operator, or report.

Reports and observations MUST NOT contain Grant Credentials, execution tokens,
private keys, raw Attestation Evidence, hidden policy text, or real sensitive
application payloads. A report is descriptive test evidence only. It is not a
Grant, credential, receipt, approval, attestation result, trust anchor, action
authority, or permission to skip ordinary current-state verification. A
repository self-test subject MUST declare `subject_kind: suite_fixture`; its
verdict remains `incomplete` even when every assertion matches. A suite
self-check can establish machine validation of its catalog; `interop_tested`
maturity requires successful use with independently implemented participant
boundaries and cannot be derived from the repository's own fixtures.

### Reference Mock Participants

This repository publishes a reference Mock App and Mock Runtime under `mocks/`
so an operator can exercise the conformance harness without a real agent or a
production application. The closed participant manifest
`mocks/v1/manifest.json` binds the exact mock protocol version, participant
identifiers, boundary identifiers, role assignments, feature inventory,
entry points, and artifact digests. The adjacent JSON Schema and the repository
mock validator define the machine-checked bundle shape.
Its `claim_effect` value MUST be exactly `suite_fixture_only` and MUST NOT be
overridden by an operator, adapter, probe, subject document, or report.

The reference participants are conformance-suite fixtures, not ASP
implementations. Every subject or counterpart backed by this bundle MUST use
`subject_kind: suite_fixture`. A report that uses either participant therefore
remains `incomplete` with the `suite_fixture` reason even when every applicable
assertion passes. Such a report gives no implementation-conformance,
interoperability, certification, deployment-readiness, or production-security
credit. In particular, the two participants are maintained together and MUST
NOT be represented as independently implemented boundaries.

The versioned mock participant protocol is an internal harness control
protocol. It carries deterministic setup, stimulus, and sanitized observation
messages between the runner and the mock entry points. It is not an ASP wire
protocol, transport binding, discovery mechanism, Grant, credential, receipt,
or authority channel, and implementations MUST NOT expose it as any of those.
Changing the mock protocol does not change ASP wire semantics or establish a
new ASP compatibility claim.

The Mock App and Mock Runtime MUST keep disjoint authority stores. The Mock App
owns only synthetic application-side manifest, Grant, action-admission, effect,
and App Receipt state. The Mock Runtime owns only synthetic runtime-side local
policy, credential-custody, mediation, safety, and Runtime Receipt state.
Each participant MUST NOT read or mutate the other's authority store to satisfy
an assertion. Cross-participant behavior uses only the typed mock exchange
declared by the manifest, while the probe returns privacy-minimized observations
derived from the owning participant's resulting state.

For HTTP capacity tests, the Mock App derives the `429` or `503`, `no-store`,
and optional `Retry-After` observations from the transport-neutral envelope.
The Mock Runtime validates the normalized authenticated HTTP projection before
it invokes the ordinary capacity recovery state machine. A failed binding
preserves local admission and semantic retry state and produces a deterministic
negative observation; it is not converted into an adapter execution error.

For ASP-over-AHP tests, the Mock Runtime validates negotiated profile,
authenticated carrier, representation replay state, and the complete ASP tuple
before changing presentation state. The Mock Agent Adapter forwards only an
exact action binding. Profile downgrade, unauthenticated carrier state, tuple or
action substitution, conflicting replay, and receipt-authority claims preserve
the prior ASP and AHP state and produce deterministic negative observations.

For Human Elicitation tests, the Mock Runtime mediates the authenticated
presenter boundary and immutable request/response replay record. The Mock App
owns application-requested edit and redline candidate validation. Both
participants preserve the prior proposal, approval, dispatch, effect,
credential, and receipt state when a binding, hash, option, assurance, base, or
result check fails. The Mock Agent Adapter projects only the minimized,
purpose-bound synthetic answer and rejects agent-originated resolutions,
unbound envelopes, and secret-bearing data. Synthetic step-up fixtures contain
only opaque verifier results and MUST NOT carry authentication factors.

For Risk Explanation UI Hint tests, the Mock App publishes only deterministic
synthetic closed hint objects bound to its exact manifest actions. The Mock
Runtime validates the complete object, resolves one language or the default,
renders an inert normalized observation beside independently derived risk and
effect values, and preserves its matching, approval, admission, and agent
projection state when a hint is malformed, stale, detached, or hostile. The
Mock Agent Adapter MUST NOT receive the hint as an instruction or authority.

For Impact Simulation tests, the Mock Runtime derives a deterministic closed
result only from a synthetic normalized verified-manifest semantic projection,
request, delegate, runner-owned Capability Match check facts, complete current
binding facts, and per-source freshness deadlines. It derives candidate-wide
status and decisive blocking reason codes from those check facts, maps them to
every requested example, omits advisory and overridden indeterminate reasons,
and derives the exact recovery limitation set from the retained effects and
recovery relationships. It includes every requested
action or atomically suppresses the feature above the bound, selects only the
required highest-risk unrequested actions, and keeps all examples local. The
Mock App MUST NOT provide an example or be contacted for a dry run or resource
probe, and the Mock Agent Adapter MUST NOT receive a result. Malformed, stale,
detached, incomplete, or authority-bearing candidates preserve all Grant,
approval, dispatch, effect, receipt, policy-decision, and agent-projection
state while the Mock Runtime returns the canonical Consent Preview fallback
observation. Before dispatch, every mock consumer checks each closed Grant or
Action object it actually consumes and rejects an embedded Result; the direct
semantic matrix includes Grant issue and revocation, Grant and action
mediation, action invocation and replay, and native and AHP action translation.

All mock inputs, identifiers, payloads, keys, credentials, evidence, and state
are deterministic synthetic test values. The bundle MUST NOT accept or retain
production secrets, user content, tenant data, private keys, live Grant
Credentials, execution tokens, cookies, or raw Runtime Attestation Evidence.
The synthetic agent-side input is a fixed typed fixture and is not evidence of
agent identity, capability, intent, approval, or successful agent execution.

### Reference API Importer

This repository publishes the `asp-api-import` reference CLI under
`tools/asp-api-importer/` for the deterministic projection defined by the
OpenAPI and AsyncAPI Import Profile. The tool accepts strict JSON, operates
offline, recognizes only the source versions and annotation locations defined
by the profile, sorts emitted members deterministically, computes the manifest
hash with the Canonical Object Hash Profile, and rejects the complete
projection when any annotation or generated declaration fails its implemented
checks.

The adjacent annotation JSON Schema defines the closed root, operation, and
member objects. The versioned case registry and its schema bind positive
OpenAPI and AsyncAPI inputs, exact generated outputs, and negative parse,
version, location, reference, duplicate, reserved-member, and incomplete-
declaration cases. In particular, the positive OpenAPI case contains an
ordinary unannotated destructive operation and requires it to be absent from
all generated ASP inventories.

`generate` returns status `0` and writes one hash-bound JSON candidate only after
the transform, the case-registry-pinned reference-linter ruleset,
deterministic ordering, and hashing succeed. A ruleset identifier or version
mismatch fails closed rather than silently changing importer acceptance. The
command returns status `2` and writes no candidate when it cannot evaluate the
input safely. `self-check` requires the compiled schemas and case registry to
equal the selected repository artifacts, validates the registry, ruleset
binding, and schemas, executes every bound case, and compares positive output
byte-for-byte with its golden manifest.

The reference importer deliberately does not parse YAML, validate the complete
OpenAPI or AsyncAPI specification, fetch or resolve a reference, validate
remote ASP schema bytes, or replace a complete Agent Surface Manifest
validator. Its successful output is machine evidence for this bounded
authoring transform, not permission to serve the candidate automatically. The
publisher MUST complete every ordinary manifest, implementation-semantic,
version, and deployment check from the profile before designating and serving
the output as its issuer-authoritative current surface.

The tool never consumes credentials, Grants, user data, live endpoints,
implementation code, private keys, or network resources. A generated hash
commits to candidate bytes under the manifest hash profile; it does not
authenticate the publisher, prove that an annotation is truthful, establish
source-spec conformance, or authorize an omitted or included operation.

### Reference Manifest Linter

This repository publishes the `asp-lint` reference CLI under
`tools/asp-manifest-linter/` for deterministic static checking of an Agent
Surface Manifest. The versioned rule registry and its JSON Schema define stable
rule identifiers, severity, RFC anchors, and operator help. The adjacent
diagnostics JSON Schema defines the machine-readable report contract. A rule
identifier MUST NOT be reused with different semantics within the same
ruleset version.

The v1 ruleset contains exactly these checks:

| Rule | Static requirement |
| --- | --- |
| `ASP-LINT-SCHEMA-001` | Every resource and event declares a non-empty `schema`; every action declares non-empty `input_schema` and `output_schema`. |
| `ASP-LINT-RISK-001` | Every action declares one standard `risk` label or an extension identifier in the reference linter's conservative RFC 3986 URI subset; runtime support for the URI's defining conservative mapping remains a separate compatibility check. |
| `ASP-LINT-RISK-EXPLANATION-001` | Every present `risk_explanation` uses the closed bounded shape, canonical language order and default, inert text, and exact declaration-order coverage of the parent action effects. |
| `ASP-LINT-IDEMPOTENCY-001` | A side-effecting, state-changing-mode, or persisted proposal action declares required idempotency, fixed-point normalization, the required input hash profile, and `input_schema_hash`. |
| `ASP-LINT-SCOPE-001` | Scope identifiers are unique; resource, action, and non-control event references resolve exactly; control events omit `scope`. |

The CLI MUST parse the complete input before applying rules and MUST fail
closed on duplicate object members, floating-point values, integers outside
the I-JSON safe range, malformed Unicode, trailing JSON, a non-object root, or
non-array `scopes`, `resources`, `actions`, or `events`. It returns status `0`
only when no finding exists, status `1` when one or more lint findings exist,
and status `2` when input or tool integrity prevents a safe result. A JSON
report binds the exact tool and ruleset versions, input source label, counts,
stable rule identifiers, severity, JSON Pointer, message, and operator help.

Reference linting is offline. It MUST NOT execute manifest content, contact a
schema host, follow a network reference, inspect production credentials or
state, or infer a missing declaration. `self-check` validates the rule registry
against its schema, requires the registry to match the implemented rule set,
validates a generated report against the diagnostics schema, and requires the
compiled schema and registry bytes to equal the selected repository artifacts.

A clean lint report is static evidence about those exact v1 declarations only.
It does not validate remote schema bytes, `surface_hash`, issuer identity,
current Grant state, authorization, approval, effects, receipts, runtime
behavior, interoperability, conformance, certification, or deployment
security. Consumers MUST continue every ordinary protocol and current-state
check defined by this specification.

### Reference Replay Tool

This repository publishes the `asp-replay` reference CLI under
`tools/asp-replay/` for the Portable Replay Bundle Profile. The tool accepts
strict I-JSON and performs deterministic offline validation of one passive
session-generation bundle. It verifies the embedded historical Surface and
semantic Grant hashes, the ordered replay-record hash chain, exact session
transitions, event delivery and acknowledgement identity, event gaps,
receipt hashes and links, capture gaps, and the enclosing bundle hash.

For every input that can be parsed as strict I-JSON and safely evaluated,
`verify` emits the bounded Replay Validation Report identified by the exact
`tool.check_profile`. A strict-parse or local evaluation failure returns status
`2` and emits no report. An `incomplete` or `invalid` report returns status `1`;
only `valid` returns status `0`. `self-check` requires the compiled schemas,
case registry, and implementation behavior to match the selected repository
artifacts.

The reference CLI implements only the checks enumerated by that exact check
profile. It is not the complete native-object validator required for a complete
Portable Replay Bundle Profile validation claim. Even a `valid` CLI verdict
MUST NOT be represented as complete profile conformance or substituted for the
authoritative Surface, Grant, CloudEvent, acknowledgement, gap, receipt, and
required-signature validators. A composed complete-profile validator MUST
combine those gates fail closed.

A successful bounded result therefore describes only the internal integrity
and declared completeness checked for the exact bundle bytes. It is not a
conformance claim for any of the six ASP roles, exporter authentication,
producer authentication, current-state proof, trusted time, proof of an
external effect, or permission to perform an operation.

The reference tool is inert and offline. It MUST NOT follow a URI, resolve a
remote schema or key, open a network connection, send `event.replay`,
`event.ack`, or `event.flow`, mutate or resume a session, dispatch an action,
invoke an agent, model, tool, approval, compensation, or revert path, or copy
application payloads into diagnostics. It accepts no Grant Credential, bearer
token, cookie, proof-of-possession material, private key, raw execution token,
prompt, Action Request, Action Response, or executable content. An invalid or
incomplete bundle MUST NOT cause partial execution or best-effort recovery.

### Surface Publisher Profile

A component conforms to the Surface Publisher Profile when it:

- publishes an Agent Surface Manifest
- publishes an explicitly curated ASP inventory and does not infer exposure
  merely from an underlying API, route, RPC, MCP, SDK, or UI inventory; every
  selected affordance has complete ASP semantics and every omitted operation
  remains outside that surface snapshot
- when using the OpenAPI and AsyncAPI Import Profile, accepts only its exact
  source versions and annotation locations, projects complete declarations
  atomically without inference, validates the complete generated manifest, and
  treats the served manifest rather than source annotations as the authority
- computes and publishes a valid `surface_hash` and changes
  `surface_version` whenever the manifest hashing view changes
- does not publish an Impact Simulation Result or feature identifier as a
  manifest semantic; the result is derived only inside a claiming Runtime
  Mediator
- declares a supported `surface_mode` and, for `proposal_only`, exposes only a
  closed `read`/`propose` action inventory with at least one proposal action,
  no effects, and no state-changing companion relationship
- declares actions, resources, events, scopes, and schemas
- declares every referenced data class and complete exposure contracts for
  resources, actions, and events
- declares risk labels for actions
- when publishing a Risk Explanation UI Hint, emits the exact closed,
  size-bounded, sorted localization shape, covers every declared effect in
  every language, changes the surface version and hash with the prose, and does
  not represent that prose as narrower machine semantics
- declares one static execution mode and operation id per action
- declares valid fixed-point input-normalization rules for every
  idempotency-required action and publishes a valid hash of its self-contained
  input schema
- declares maximum effects for state-changing actions and internally consistent
  companion-action, precondition, reservation, and recovery metadata
- declares the required endpoints for every invocable action, including a
  proposal-only action
- when publishing operational limits, uses the exact supported profile,
  resolves every referenced action and non-control event exactly once, declares
  only positive safe-integer windows and slots, and changes the surface version
  and hash whenever that contract changes
- declares the `at_least_once` delivery contract whenever it publishes an event
  subscription endpoint
- declares every event type and schema so it can be mapped without ambiguity to
  the CloudEvents 1.0.2 ASP binding
- provides `propose` actions or read-only resources

### Grant Issuer Profile

A component conforms to the Grant Issuer Profile when it:

- consumes the exact verified, issuer-authoritative current manifest snapshot
  for the applicable surface lifecycle key and rejects stale, superseded,
  hash-invalid, or unsupported surface semantics
- authenticates the resource owner and obtains issuer-side consent from the
  exact semantic Grant request, manifest semantics, delegate tuple, effects,
  constraints, and effective data-exposure projection
- rejects the complete closed protocol object when a client embeds an Impact
  Simulation Result or feature identifier in an undefined member, discards a
  detached out-of-band supplement as consent, authority, request semantics, or
  evidence, and independently derives its own consent presentation from the
  verified primary sources
- validates requested actions, locations, scopes, resources, surface mode,
  required companion closure, expiration, budgets, credential-release policy,
  audit requirements, and every selected optional profile before issuance
- constructs the authoritative Agent Grant Object without adding authority,
  derives only permitted output fields and attenuations, computes `grant_hash`,
  and persists the complete hashing view for the Grant lifetime and audit period
- binds the Grant and Grant Credential to the user, application, exact surface,
  runtime, agent, Passport evidence, credential audience, and selected
  credential-binding method
- provides the Action Executor an app-verifiable way to obtain current
  authoritative Grant state; co-location, signed delegation, and authenticated
  introspection are deployment choices, not permission to trust a caller's
  assertion
- when it selects the Minimal Agent Passport Grant-Issuance Profile,
  independently retrieves, hashes, parses, verifies, status-checks, and binds
  the exact Passport tuple without treating declarations as authority or an
  artifact hash as signature or executable proof
- when it selects the Runtime Identity Profile, derives only server-side
  projections, binds the exact active revision into the Grant and credential,
  and maintains the authoritative identity lifecycle
- when it selects the Remote Processing Privacy Profile, validates the exact
  requested path, derives and hash-binds only its deterministic ceiling, and
  makes no application-verified downstream-compliance claim
- when it selects the Agent Training Use Policy Profile, validates the
  canonical requested set against the complete exposure union, obtains consent
  for the returned subset, preserves every authoritative copy, and makes no
  provider-compliance or unlearning claim
- when it selects the Approval Receipt Profile, validates and hash-binds the
  exact per-action producer roles and maximum ages without treating an approval
  receipt as issuance authority
- when it selects Runtime Attestation, performs the issuance-time duties of the
  Grant Issuer in Runtime Attestation Role Requirements below
- preserves required constraints, optional-profile bindings, companion closure,
  member-wise budget attenuation, cumulative lineage accounting, and
  cross-runtime restrictions through renewal, exchange, supersession, and
  child derivation
- denies credential-release authority unless the explicit capability and its
  complete constraints are valid, and always denies it for a proposal-only
  surface
- maintains authoritative active, expired, and revoked Grant state; makes
  revocation converge on the Semantic Grant Revocation Transition; and defines
  an authenticated revocation binding when it does not select the OAuth Grant
  Issuer Profile
- operates the authenticated user-facing active-grant management boundary and
  issues only against a verified manifest that advertises its generic
  issuer-bound management URL
- fails closed before issuance, renewal, exchange, derivation, introspection,
  or revocation confirmation when required manifest, identity, Passport,
  appraisal, consent, lineage, or Grant state is unavailable or inconsistent

A Grant Issuer claim does not claim that the component publishes the manifest,
executes actions, delivers events, or produces receipts. Those are independent
role claims even when the same application deployment performs them.

### Action Executor Profile

A protected-resource component conforms to the Action Executor Profile when it:

- consumes the exact verified manifest snapshot and current app-verifiable
  Grant state selected by the request, without trusting a Surface Publisher,
  Grant Issuer, runtime, or caller conformance claim as verification evidence
- enforces the pinned surface mode during every Action Request and rejects an
  inconsistent proposal-only inventory before idempotency lookup or any effect
- validates the manifest-pinned `credential_audience` at every
  credential-protected `agent_api` endpoint
- validates active Grant state, `grant_hash`, the exact retained
  `surface_hash`, credential proof, user-runtime-agent-Passport binding, action
  allow-list, scopes, resource constraints, expiration, and current lifecycle
  state for every action
- rejects an Impact Simulation Result presented as Action Request input,
  approval, policy evidence, receipt evidence, or authority
- when the Grant selects the Minimal Agent Passport Grant-Issuance Profile,
  independently revalidates the exact Passport tuple and current authenticated
  lifecycle state before every action without treating declarations or
  artifact hashes as signature or executable proof
- when the Grant selects the Runtime Identity Profile, revalidates the exact
  current server-side projection and active claims revision before every action
- when the Grant selects the Remote Processing Privacy Profile, rejects every
  effective application-originated exposure above the exact hash-bound ceiling
  and does not represent the runtime path commitment as verified downstream
  topology
- when the Grant selects the Agent Training Use Policy Profile, enforces the
  complete effective class set at disclosure time and makes no provider-
  compliance or unlearning claim
- when the Grant selects the Approval Receipt Profile, authenticates and
  verifies the complete required role map and maximum age before first effect
  admission; producing an application Approval Receipt additionally requires an
  application-role Receipt Producer claim
- when selecting the Human Elicitation Events Profile, authenticates the
  requester and presenter, retains the exact request and terminal-response
  revision state, validates every session, Grant, surface, context, kind, and
  response binding, and treats any clarification, choice, edit, redline, or
  step-up result only as input to a fresh application policy and action
  decision
- when the Grant selects Runtime Attestation, performs the action-time duties
  of the Action Executor in Runtime Attestation Role Requirements below rather
  than inferring accepted state from hardware, EAT parsing, or a co-located
  Verifier
- creates or accepts an authoritative session record and validates its active
  state, complete tuple binding, and current generation for every action
- creates non-control event subscriptions only as an attenuation of the current
  grant, and binds the logically separate control subscription to the manifest
  issuer and authenticated runtime rather than to an affected grant
- rechecks applicable authority and exposure before delivery and implements
  at-least-once retry, per-stream ordering, acknowledgement, replay, retention,
  explicit gaps, and bounded in-flight delivery
- emits valid CloudEvents 1.0.2 JSON event objects, recomputable
  `aspeventhash` values, and extension attributes consistent with the pinned
  manifest and authoritative subscription or control record
- validates `grant_hash` and binds the grant to the exact verified
  `surface_hash` snapshot
- validates static execution mode, companion authority, execution context and
  hash, preconditions, effect envelope, and any required reservation or
  recovery target before a state change
- rejects any action allow-list that is not closed over required companion
  dependencies in the pinned manifest
- recomputes the complete effective data-exposure projection from the pinned
  manifest and rejects a Grant, request, or disclosure that does not match it
- applies declared redaction before application-originated data crosses the
  application boundary
- enforces cumulative per-target recovery limits independently of request
  idempotency keys
- treats `grant_id` as an identifier, not authority
- supports idempotency for `reserve`, `commit`, `compensate`, and `revert`,
  verifies the pinned input schema, independently checks normalized-wire fixed
  points before lookup or effect, and binds each record to the normalized
  `input_hash` and execution context
- validates and atomically enforces every pinned per-Grant operational action
  window and in-flight slot; resolves exact and conflicting idempotency records
  before new admission; and makes a `rate_limited`,
  `capacity_state_unavailable`, or `service_unavailable` rejection create no new
  idempotency record, budget delta, app receipt, workload, or effect
- enforces pinned per-subscription first-delivery windows without charging a
  retry or replay twice, exceeding the negotiated in-flight window, silently
  dropping an expired queued event, or consuming capacity reserved for control
  events
- durably enforces write, parallel-session, and application-cost budgets across
  the grant lineage and fails closed when ledger state is uncertain
- declares and emits application-authoritative budget control events when an
  event endpoint is present, without fabricating runtime-owned counter state
- when it accepts an application-authoritative budget dimension, advertises
  `budget_state_url` and `budget_query_retention_seconds` and returns
  authenticated, privacy-minimized effective lineage state for `budget.query`
  without exposing ancestor or sibling accounting totals
- when it accepts a Runtime participant in an ASP session, advertises
  `session_control_url`, accepts authenticated `session.pause` with
  `runaway_guard` for the exact active tuple, and also accepts
  `budget_exceeded` when it supports a runtime-authoritative budget dimension
- fences new actions before returning `interrupted`, preserves generation,
  and exactly replays a matching pause; when the manifest declares
  `session.paused_budget`, emits exactly one occurrence for each qualifying
  budget transition, emits none when undeclared, and never emits it for a
  runaway-guard transition
- accepts a guard-aware exact `session.resume` after authenticated lineage
  resolution whether its interrupted state came from the guard pause or
  predated the parent trip, and binds the supplied guard and resolution ids to
  the accepted transition without treating them as detector proof
- invalidates preview evidence and reservations when their grant or surface
  binding becomes invalid
- does not accept `reserve`, `commit`, `compensate`, or `revert` unless the
  deployment composes an application-role Receipt Producer for that action
- rejects expired or authoritatively inactive Grants, fences their sessions and
  outstanding pre-effect work, and fails closed when current Grant or lineage
  state is unavailable

An Action Executor claim does not claim issuance, consent, attenuation,
credential minting, authoritative Grant lifecycle, or receipt production. A
co-located component that performs those functions claims their roles
independently.

### OAuth Grant Issuer Profile

A Grant Issuer additionally conforms to the OAuth Grant Issuer Profile when
it independently satisfies the Grant Issuer Profile and:
- advertises the Agent Grant authorization-details type and supported standard
  OAuth grant types
- uses `agent_api.credential_audience` as the sole OAuth resource indicator and
  issued Grant Credential audience while keeping action `locations` separate
- validates and returns Agent Grant `authorization_details` according to the
  Rich Authorization Request Profile
- preserves the complete selected Passport tuple through authorization, token
  exchange, introspection, credential binding, and Grant hashing
- treats `runtime_identity_profile` only as a request selector and returns the
  exact server-derived runtime identity projection without identity-method
  fallback
- treats `runtime_attestation_requirement` only as a request selector, returns
  the exact stable server-derived attestation binding, preserves its repeated
  credential fields, and keeps mutable appraisal state outside the Grant
- validates the request-only Remote Processing Privacy profile and path, adds
  only the deterministic output ceiling, and preserves the complete effective
  constraint through token responses, introspection, Grant hashing, and consent
- validates the Agent Training Use request profile and canonical class set,
  preserves only a permitted subset through authorization, token exchange,
  introspection, Grant hashing, and consent, and retains an explicit empty set
- validates and preserves Approval Receipt requirements through authorization,
  token response, introspection, Grant hashing, and token exchange without
  adding a role, increasing maximum age, or reusing source approval evidence
- implements the OAuth Token Exchange Profile without privilege amplification
- preserves member-wise budget attenuation, lineage accounting, and the
  cross-runtime issuance restriction through authorization and token exchange
- returns the active and inactive Grant Introspection Profile contracts
- returns matching top-level and authorization-details hash projections
- binds RFC 7009 token revocation to the Semantic Grant Revocation Transition
  and emits the authenticated `grant.revoked` control event when an event
  endpoint is declared
- routes user-facing grant management through the same semantic revocation
  transition and preserves its immediate confirmation boundary
- presents authorization-server consent from the exact verified request,
  manifest semantics, and effective exposure projection

### Receipt Producer Profile

A component conforms to the Receipt Producer Profile only for the exact
`producer_role` named by its claim, `application` or `runtime`. It MUST produce
only receipt types assigned to that role and MUST derive every claim from the
role's authoritative decision or observation record. A signing service that
receives already-constructed bytes is not the producer merely because it holds
the signing key.

Every Receipt Producer:

- emits the role-appropriate receipts required by the selected action, Grant,
  approval, and receipt profiles
- emits recomputable `receipt_hash`, `grant_hash`, `surface_hash`,
  `execution_hash`, effect hashes, and `policy_decision_hash` values
- includes the complete typed Policy Decision Object and requires its embedded
  hash to match the receipt's `policy_decision_hash`
- preserves trace id, session id and generation, action id, agent id, runtime
  id, and idempotency key while using a producer-specific span id
- preserves sanitized execution context across the runtime/app receipt edge,
  omits raw execution tokens, and uses `target_receipt_hash` rather than a
  parent edge for recovery causality
- records session id and generation, trace id, and producer span id in the
  corresponding local action and receipt log entry
- binds receipt creation to the immutable idempotency, decision, approval,
  outcome, and accounting records available to its producer role rather than
  constructing authoritative evidence later from mutable logs
- never treats a receipt, signature, proposal, target link, or approval side
  link as authority for an action, retry, commit, or recovery operation

An application-role Receipt Producer additionally:

- emits app receipts for required state-changing actions and denied or failed
  high-risk actions, except for the definite pre-admission `rate_limited`,
  `capacity_state_unavailable`, and `service_unavailable` rejections that the
  Error Model requires to create no application action receipt
- when Approval Receipt is selected, emits immutable application-role approved
  or denied Approval Receipts, binds accepted hashes into the idempotency record
  and app action receipt, and never uses `parent_receipt_hash` for those
  prerequisite side links
- links an app receipt to the verified runtime receipt through
  `parent_receipt_hash` when runtime receipt evidence is required
- records actual effects and distinguishes applied, partial, absent, and
  unknown outcomes without trusting the runtime as effect authority
- records and retains receipt-bound revert evidence for effects advertised as
  reversible
- records application-authoritative budget charges and resulting ledger
  revisions without treating receipt evidence as mutable ledger state

A runtime-role Receipt Producer additionally:

- emits runtime receipts only for runtime-observed agent intent, local policy,
  runtime approval, request construction, and runtime-authoritative budget
  state
- never emits an app receipt or claims that an application effect occurred,
  succeeded, failed, or was reversed merely because it sent a request or
  observed a response
- when Approval Receipt is selected, emits immutable runtime-role approved or
  denied Approval Receipts and preserves their prerequisite side-link semantics
- protects raw execution tokens and credentials and records only their required
  hashes or sanitized projections

Receipt Producer conformance is independent of Grant Issuer, Action Executor,
and Runtime Mediator conformance. The producer MUST nevertheless validate the
authoritative input required for its role and fail closed when that input is
missing, conflicting, or outside the claim boundary.

An application or runtime claims the `asp-jws-detached` Receipt Signing Profile
only when it supports the canonical detached payload, ES256 verification,
authenticated key resolution, grant-pinned signer roles and thumbprints,
historical public-key retention, and the no-downgrade behavior defined above.
It MUST emit every signature required for its producer role and reject required
or present signatures that do not verify.

### Proof-Bound Action Executor Profile

An Action Executor conforms to the Proof-Bound Action Executor Profile when it
independently satisfies the Action Executor Profile and:

- accepts Agent Surface actions only under the Proof-Bound Credential Profile
- verifies the per-request proof-of-possession or bound-channel authentication
- applies the method-specific DPoP, mTLS, or proof-bound session checks defined
  in Grant Verification
- rejects a bearer token, cookie, or reusable session identifier as sufficient
  authority by itself

### Runtime Attestation Role Requirements

Selecting Runtime Attestation does not create a combined conformance role. The
following requirements apply independently to every claimed role:

- the Surface Publisher advertises the framework, endpoint, concrete profiles,
  and exact Verifier-to-profile relationships in the pinned manifest
- the Grant Issuer implements the authenticated single-use challenge, requires
  every concrete profile to bind its nonce, application audience, runtime
  identity binding and revision, proof key, and exact `grant_request_hash`, and
  derives stable Grant and credential bindings only from a current accepted
  appraisal with verified proof-key cross-binding
- the Action Executor checks the current authoritative `accepted` state on
  every action and session resume, independently of any issuer or conformance
  claim, and rejects a stale, inactive, mismatched, or unavailable appraisal
- the Runtime Mediator supports the exact selected concrete profile, protects
  its proof key and raw Evidence, authenticates every challenge and binding,
  and rejects a non-accepted, mismatched, downgraded, or fallback result before
  storing or using a Grant

The Grant Issuer authenticates Attestation Results, verifies complete Target
Environment coverage, applies its own Relying Party policy, and never treats raw
Evidence or an Attester self-assertion as an accepted Result. It maintains the
authoritative mutable appraisal state machine outside the Grant, applies the
strictest freshness input, makes every state other than `accepted` inactive,
and fences affected sessions before another effect. No role falls back to
another profile, Verifier, proof key, older Result, or unattested runtime.

An in-place appraisal refresh is distinct from a material identity, profile,
Verifier, proof-key, or coverage change that requires a new Grant and Consent
Preview. A revoked binding triggers semantic revocation. Every role exposes
outside the Verifier boundary only the privacy-minimized stable binding,
assurance, and coarse authorized state, never raw Evidence, measurements,
reference values, hardware identifiers, or diagnostics.

### Runtime Mediator Profile

An application runtime conforms to the Runtime Mediator Profile when it:

- discovers and validates Agent Surface Manifests
- recomputes `surface_hash` and pins the exact manifest snapshot
- independently verifies the exact Agent Passport artifact, signature, issuer
  trust, lifecycle status, and local agent binding under the selected profiles
  before delegation
- distinguishes `document_only` Passport admission from a separately profiled
  and locally verified executable-integrity binding
- when selecting the Runtime Identity Profile, shows every locally authenticated
  facet, re-previews and confirms any initially unresolved server projection,
  rejects a returned projection or credential binding that conflicts with known
  state, and treats every material identity change as stale
- when selecting the Remote Processing Privacy Profile, resolves the complete
  data-bearing path rather than only the controlling runtime, verifies every
  effective class against the expected and returned ceiling, labels downstream
  commitments accurately, and fails closed before disclosure on any unknown or
  changed recipient or enforcement state
- when selecting the Agent Training Use Policy Profile, resolves every source's
  complete class set, presents the permitted and prohibited sets separately
  from retention, enforces the whole-source and downstream-recipient rules,
  treats omission as unspecified, and makes no model-unlearning claim
- when selecting Runtime Attestation, supports the exact concrete profile,
  protects its proof key and raw Evidence, authenticates every challenge and its
  runtime, request, audience, and freshness bindings, confirms any initially
  unresolved stable binding and assurance, and rejects a non-accepted,
  mismatched, downgraded, or fallback result before storing or using a Grant
- when claiming the Capability Match Result Profile, emits its closed local
  object with the exact manifest, semantic request, identity, Passport,
  inventory, policy, and preference bindings; treats unknowns as indeterminate;
  and discards stale results before selection or consent
- when claiming the Impact Simulation feature, emits only the exact closed,
  bounded, deterministic local result; includes every requested action or
  suppresses the complete optional result; selects unrequested actions by the
  fixed conservative risk order; projects the exact candidate-wide status and
  decisive blocking reason codes to every requested example; treats unknown
  blocking extensions as indeterminate; derives the exact recovery limitation
  set; keeps hints and concrete resources outside the object; and never uses an
  example as execution, consent, approval, policy, receipt, Grant, or agent
  authority
- obtains explicit user consent before storing a grant
- derives and confirms the local Consent Preview Contract projection before
  sending a grant issuance request, regenerates it after any material change,
  and rejects a returned grant that is not equal to or narrower than the exact
  confirmed request
- when claiming the Risk Explanation UI Hints feature, validates the complete
  closed object, selects one localization with the required fallback, retrieves
  it only from the exact pinned action, renders it as inert labeled publisher
  text alongside canonical machine semantics, and excludes it from matching,
  policy, approval, admission, and agent instructions
- recomputes the grant's effective data-exposure projection, refuses missing or
  inconsistent contracts, and selects only runtime-agent paths that can enforce
  redaction and retention obligations
- mediates agent actions instead of exposing raw authority
- enforces the Session Authority and Lifecycle state machine, including
  complete tuple binding, generation changes on resume, and terminal-state
  rejection
- when selecting the ASP-over-AHP Binding Profile, explicitly negotiates the
  exact profile on an authenticated AHP channel, keeps AHP and ASP session
  namespaces separate, validates monotonic representation bindings and every
  embedded ASP tuple before presentation or dispatch, and fences conflicting
  replay or ambiguous outcomes without deriving authority from UI state
- when selecting the Human Elicitation Events Profile, presents only a
  minimized request on an authenticated user channel, persists exact request
  and terminal-response revision state, validates every session, Grant,
  surface, context, kind, expiry, and verifier binding, withholds
  authentication factors from profile and agent-visible data, and never treats
  a clarification, choice, edit, redline, or step-up result as approval or
  action authority
- denies credential release unless an explicit `credential.release` capability
  and its constraints are satisfied
- preserves parent-runtime mediation for subagents, tools, adapters, remote
  models, and ungranted secondary runtimes
- treats a separately granted child runtime as its own controlling runtime and
  preserves parent linkage, attenuation, and cascade revocation
- implements RAR, Token Exchange, introspection, and revocation processing when
  interacting with the OAuth Grant Issuer Profile
- requests and validates the manifest-pinned `credential_audience` without
  treating it as action or control-operation authority
- implements the Proof-Bound Credential Profile when the application requires
  the Proof-Bound Action Executor Profile
- enforces local policy and approval rules
- when selecting the Approval Receipt Profile, constructs the exact Grant
  requirement projection, obtains and records fresh runtime approvals, stops on
  runtime denial, transmits only the verified runtime side link, and verifies
  the final application receipt role map without treating any receipt as action
  authority
- durably enforces `tool_calls`, `model_tokens`, `runtime_seconds`, and
  `runtime_cost` across the grant lineage, retaining conservative reservations
  when usage is uncertain
- stops matching local work before reporting runtime budget exhaustion through
  an exact, idempotent `session.pause` request and requires authoritative
  application state before any resume
- initializes a durable runaway-guard epoch before agent work, enforces
  positive finite transport, action-repetition, epoch-root, epoch-step,
  root-action, causal-depth, and cycle limits independently of Grant budgets,
  and fails closed when guard state is unavailable
- treats declared operational limits as scheduling ceilings rather than
  authority or availability promises, conservatively accounts fresh dispatches
  and outstanding idempotency tuples across workers, applies the stricter local
  policy, preserves exact idempotency and event-delivery identity while
  refreshing binding-specific per-attempt authentication, and uses bounded
  backoff with jitter without resetting runaway guards
- carries finite lineage-delegate session, root, step, and cycle admission
  guards across new session ids, child Grants, renewal, reconnect, and ordinary
  resume, and does not clear an unresolved parent fence when one session ends
- persists `fenced` before another disallowed scheduling step, preserves
  in-flight outcome reconciliation, requests an exact `runaway_guard` fence for
  every affected or newly observed active session, commits one lineage
  resolution covering every affected session, and requires that resolution
  plus authoritative exact resume before a new generation can start a new
  child epoch
- validates action input against schemas, applies the pinned idempotency
  normalization before approval and hashing, verifies the self-contained input
  schema against `input_schema_hash`, and sends only the fixed-point wire value
  to the app
- validates request mode against the pinned declaration and computes input and
  execution hashes
- presents expected effects and recovery limitations, and binds approval to the
  exact input and preview evidence
- protects raw execution tokens, tracks reservations, and does not treat either
  as authority
- handles stale previews, reservation conflicts, and partial or unknown recovery
  outcomes without blind retry
- records local audit events and emits runtime receipts only when it separately
  claims the runtime-role Receipt Producer Profile
- durably deduplicates event deliveries, acknowledges only after its processing
  decision is stable, preserves opaque cursors, applies explicit gap recovery,
  enforces negotiated event backpressure, and deduplicates before allocating an
  automation root or advancing its runaway guards
- validates the CloudEvents 1.0.2 JSON binding, ASP extension combinations,
  event hash, manifest mapping, schema, authority, and exposure before exposing
  event data to an agent
- durably orders and deduplicates budget control revisions, never exposes a
  core control event as an agent task, and never treats delivery or replay as
  authority for an action, automatic retry, or automatic resume
- uses authenticated `budget.query` with bounded backoff for retryable
  application-owned capacity recovery and rejects any event or query result
  older than its highest retained effective state revision
- computes and validates grant, execution, effect, policy-decision, and receipt
  hashes; propagates session id and generation and W3C-compatible trace context
- records session id and generation, trace id, and producer span id in local
  action and receipt logs
- stops actions when grants are revoked or expired
- provides a local grant view with the trusted application management link,
  freezes local use while revocation confirmation is unknown, and treats
  application state or introspection as authoritative over cached active state

### Agent Adapter Profile

An adapter conforms to the Agent Adapter Profile when it:

- runs under runtime supervision
- does not require raw app credentials
- does not receive a Grant Credential or transfer one to downstream components
- requests app actions through runtime APIs
- does not receive, request, interpret, or forward an Impact Simulation Result
  as agent-visible state or an instruction
- emits typed events
- handles denials and approval waits
- preserves the manifest-declared action id and mode and handles preview,
  reservation, precondition, and recovery errors without selecting stronger
  authority
- preserves session and grant identifiers in audit context
- preserves valid trace ids and creates a new span id for each adapter operation
- when selecting the ASP-over-AHP Binding Profile, translates only the exact
  validated embedded ASP message and control binding, rejects action or tuple
  substitution, and never treats AHP state or a receipt summary as authority
- never originates or resolves a Human Elicitation interaction, claims that a
  person answered, or forwards an authentication factor; after the Runtime
  Mediator accepts an exact response, exposes only the minimized,
  type-specific answer required by an independently verified task-purpose and
  Data Exposure Contract, never the profile envelope, verifier-private data,
  or unrelated candidate fields
- never fabricates consent, approval, grant, policy decision, app effect, or
  receipt evidence and never treats a conformance claim as authority
- fails closed instead of blindly retrying when authority, session generation,
  idempotency state, effect outcome, or recovery state is stale or unknown

## Application MVP Mapping

An application implementation can start with a small runtime bridge:

- outbound WebSocket from runtime to control plane
- `runtime.hello`
- typed `session.start`
- normalized `session.event`
- local policy evaluation
- local approvals
- agent adapter boundary

The MVP surface SHOULD begin with a deliberately selected subset of application
affordances rather than an import of the complete route or API inventory. For
example, an application can initially publish `task.read` and
`comment.propose` while keeping account deletion, billing changes, workspace
export, and other operations outside ASP. Each later addition follows the
ordinary manifest version, hash, consent, and Grant rules.

An application that already maintains an OpenAPI or AsyncAPI description MAY
use the import profile to keep those selected declarations near their source
operations. The initial annotation set should remain equally small: leaving an
operation unannotated is the explicit safe default, and the generated diff
should be reviewed as a security-sensitive manifest change before publication.

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
9. Require manifest-pinned input normalization, idempotency keys, and execution
   hashes for state-changing actions.
10. Add durable grant-lineage accounting for writes, tools, tokens, runtime
    time, parallel sessions, and partitioned cost.
11. Add authenticated budget control events and idempotent `session.pause`
    fencing without exposing control events to agents.
12. Add durable finite retry, repetition, causal-depth, and event-loop guards
    with explicit resolution before resume.
13. Add bounded reservation and recovery actions only where the application can
    enforce their lifecycle and semantics.
14. Produce local runtime receipts and app-visible receipts with execution and
    actual-effect evidence.
15. Integrate Agent Passport verification as an admission precondition.
16. Export and verify passive Portable Replay Bundles for bounded debugging and
    audit without connecting replay validation to live event, session, action,
    approval, or effect paths.

## Example End-to-End Flow

```text
1. App publishes /.well-known/agent-surface.json with `surface_hash`.
2. Application runtime recomputes the hash and pins the exact surface.
3. User chooses "Connect my local agent".
4. Runtime verifies the selected agent's Agent Passport.
5. Runtime derives and the user confirms a local preview from the exact request,
   verified tuple, pinned manifest, effects, exposure contracts, and labeled
   local operator/processing-path assertions. When it claims Impact Simulation,
   the runtime also shows the complete bounded local action examples and labels
   `covered` as proposed-request coverage rather than execution permission.
6. Runtime sends that exact Agent Grant `authorization_details` request.
7. The app authorization server independently shows consent:
   - app: code.example.com
   - runtime: application-runtime-456
   - agent: local-agent
   - passport: sha-256:<base64url-digest>
   - scopes: pull_request.read, pull_request.comment
   - actions: pull_request.get, comment.create
   - repository: example-org/example-repo
   - duration: 2 hours
   - budgets: 20 writes, 100 tool calls, 50,000 model tokens, 30 active
     runtime minutes, 2 parallel sessions, and separate runtime/application
     cost partitions
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
15. User or app approves the exact commit input and expected effects; when the
    Approval Receipt Profile is selected, each required producer emits its own
    hash-bound approved receipt.
16. Runtime records its policy decision and action receipt, links any runtime
    Approval Receipt, then sends comment.create with trace context, parent
    receipt hash, idempotency key, execution context and hash, and Grant
    Credential.
17. App verifies current grant, surface, decision, input, execution, preview,
    and complete receipt evidence, produces any required application Approval
    Receipt, atomically binds the accepted set to idempotency admission, rechecks
    preconditions, and commits the comment.
18. App returns actual effects and an app receipt with the final role-indexed
    approval links. Runtime and app action receipts form a verified parent-hash
    chain and MAY carry
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
- OpenAPI Specification 3.2.0:
  <https://spec.openapis.org/oas/v3.2.0.html>
- OpenAPI Specification 3.1.2:
  <https://spec.openapis.org/oas/v3.1.2.html>
- AsyncAPI Specification 3.1.0:
  <https://www.asyncapi.com/docs/reference/specification/v3.1.0>
- AsyncAPI Specification 3.0.0:
  <https://www.asyncapi.com/docs/reference/specification/v3.0.0>
- CloudEvents 1.0.2:
  <https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md>
- CloudEvents JSON Event Format 1.0.2:
  <https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/formats/json-format.md>
- CloudEvents HTTP Protocol Binding 1.0.2:
  <https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/bindings/http-protocol-binding.md>
- CloudEvents Distributed Tracing extension 1.0.2:
  <https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/extensions/distributed-tracing.md>
- HTTP Semantics:
  <https://www.rfc-editor.org/rfc/rfc9110>
- Additional HTTP Status Codes:
  <https://www.rfc-editor.org/rfc/rfc6585>
- OAuth 2.0:
  <https://www.rfc-editor.org/rfc/rfc6749>
- OAuth 2.0 Proof Key for Code Exchange:
  <https://www.rfc-editor.org/rfc/rfc7636>
- OAuth 2.0 Device Authorization Grant:
  <https://www.rfc-editor.org/rfc/rfc8628>
- JSON Web Token (JWT) Profile for OAuth 2.0 Client Authentication and
  Authorization Grants:
  <https://www.rfc-editor.org/rfc/rfc7523>
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
- OpenID Connect Core 1.0:
  <https://openid.net/specs/openid-connect-core-1_0-final.html>
- Remote ATtestation procedureS (RATS) Architecture:
  <https://www.rfc-editor.org/rfc/rfc9334>
- The Entity Attestation Token (EAT):
  <https://www.rfc-editor.org/rfc/rfc9711>
- Entity Attestation Token (EAT) Media Types:
  <https://www.rfc-editor.org/rfc/rfc9782>
- An Architecture for Trustworthy and Transparent Digital Supply Chains:
  <https://www.rfc-editor.org/rfc/rfc9943>
- SPIFFE Identity and Verifiable Identity Document specifications:
  <https://spiffe.io/docs/latest/spiffe-specs/spiffe-id/>
- SPIFFE X.509-SVID specification:
  <https://spiffe.io/docs/latest/spiffe-specs/x509-svid/>
- SPIFFE JWT-SVID specification:
  <https://spiffe.io/docs/latest/spiffe-specs/jwt-svid/>
- The I-JSON Message Format:
  <https://www.rfc-editor.org/rfc/rfc7493>
- Uniform Resource Identifier (URI): Generic Syntax:
  <https://www.rfc-editor.org/rfc/rfc3986>
- Tags for Identifying Languages:
  <https://www.rfc-editor.org/rfc/rfc5646>
- Matching of Language Tags:
  <https://www.rfc-editor.org/rfc/rfc4647>
- Base-N Encodings:
  <https://www.rfc-editor.org/rfc/rfc4648>
- Date and Time on the Internet: Timestamps:
  <https://www.rfc-editor.org/rfc/rfc3339>
- ISO 4217:2015 — Codes for the representation of currencies:
  <https://www.iso.org/standard/64758.html>
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
- JavaScript Object Notation (JSON) Pointer:
  <https://www.rfc-editor.org/rfc/rfc6901>
- JavaScript Object Notation (JSON) Patch:
  <https://www.rfc-editor.org/rfc/rfc6902>
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
