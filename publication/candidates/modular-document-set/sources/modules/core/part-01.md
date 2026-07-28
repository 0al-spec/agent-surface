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
- [Modular RFC Publication Architecture](#modular-rfc-publication-architecture)
- [Canonical Integrity and Provenance](#canonical-integrity-and-provenance)
- [Agent Surface Manifest](#agent-surface-manifest-1)
- [Action Execution Model](#action-execution-model)
- [Risk Taxonomy](#risk-taxonomy)
- [Effect Model](#effect-model)
- [Approval Semantics](#approval-semantics)
- [Idempotency](#idempotency)
- [Pluggable Agent Identity Evidence Profile](#pluggable-agent-identity-evidence-profile)
- [Minimal Agent Passport Grant-Issuance Profile](#minimal-agent-passport-grant-issuance-profile)
- [Runtime Identity Profile](#runtime-identity-profile)
- [Remote Processing Privacy Profile](#remote-processing-privacy-profile)
- [Agent Training Use Policy Profile](#agent-training-use-policy-profile)
- [Runtime Attestation Optional Profile](#runtime-attestation-optional-profile)
- [Agent Grant](#agent-grant-1)
- [Purpose- and Task-Bound Agent Grant Profile](#purpose-and-task-bound-agent-grant-profile)
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
- Modular RFC Publication Architecture
- ASP-over-MCP Binding Profile
- Agent Surface Manifest
- Action Execution Model
- Risk Taxonomy
- Effect Model
- Approval Semantics
- Approval Receipt Profile
- Idempotency
- Pluggable Agent Identity Evidence Profile
- Minimal Agent Passport Grant-Issuance Profile
- Runtime Identity Profile
- Remote Processing Privacy Profile
- Agent Training Use Policy Profile
- Runtime Attestation Optional Profile
- Agent Grant
- Purpose- and Task-Bound Agent Grant Profile
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
- Relationship to Existing Protocols, except the ASP-over-MCP Binding Profile
- Conceptual Architecture
- Protocol Layers
- Capability Matching
- Application MVP Mapping
- Example End-to-End Flow
- Open Questions
- References
- Appendices

The ASP-over-MCP Binding Profile subsection is normative notwithstanding its
placement under the otherwise informative Relationship to Existing Protocols
section.

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

### Authorized Surface Projection

A complete Agent Surface Manifest derived for one server-authenticated
authorization context by removing affordances from one issuer-authoritative
base snapshot. A projection is discovery metadata, not authority. It cannot add
or rewrite an affordance, and it does not replace an Agent Grant or any
application-side authorization check.

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

<https://modelcontextprotocol.io/specification/2025-11-25>

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
