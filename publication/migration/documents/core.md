# ASP Core

> [!IMPORTANT]
> Non-authoritative modular publication candidate. The canonical source
> remains `drafts/agent-surface.md` until atomic activation.

- Document ID: `https://github.com/0al-spec/agent-surface/documents/core`
- Exact version: `0.1.0-draft.1`
- Planned canonical path: `drafts/modules/core.md`

## Exact Normative Dependencies

- None.

## Document Set Contents

- [Authors' Contact Information](core.md#authors-contact-information)
- [Status of this Memo](core.md#status-of-this-memo)
- [Copyright Notice and Licensing](core.md#copyright-notice-and-licensing)
- [Abstract](core.md#abstract)
- [Normative and Informative Sections](core.md#normative-and-informative-sections)
- [Motivation](core.md#motivation)
- [Goals](core.md#goals)
- [Non-Goals](core.md#non-goals)
- [Conventions](core.md#conventions)
- [Terminology](core.md#terminology)
- [Design Principles](core.md#design-principles)
- [Relationship to Existing Protocols](core.md#relationship-to-existing-protocols)
- [Conceptual Architecture](core.md#conceptual-architecture)
- [Protocol Layers](core.md#protocol-layers)
- [Modular RFC Publication Architecture](core.md#modular-rfc-publication-architecture)
- [Canonical Integrity and Provenance](evidence.md#canonical-integrity-and-provenance)
- [Agent Surface Manifest](core.md#agent-surface-manifest-1)
- [Action Execution Model](safe-effects.md#action-execution-model)
- [Risk Taxonomy](safe-effects.md#risk-taxonomy)
- [Effect Model](safe-effects.md#effect-model)
- [Approval Semantics](safe-effects.md#approval-semantics)
- [Idempotency](safe-effects.md#idempotency)
- [Pluggable Agent Identity Evidence Profile](authorization.md#pluggable-agent-identity-evidence-profile)
- [Minimal Agent Passport Grant-Issuance Profile](authorization.md#minimal-agent-passport-grant-issuance-profile)
- [Runtime Identity Profile](authorization.md#runtime-identity-profile)
- [Remote Processing Privacy Profile](privacy.md#remote-processing-privacy-profile)
- [Agent Training Use Policy Profile](privacy.md#agent-training-use-policy-profile)
- [Runtime Attestation Optional Profile](authorization.md#runtime-attestation-optional-profile)
- [Agent Grant](authorization.md#agent-grant)
- [Purpose- and Task-Bound Agent Grant Profile](authorization.md#purpose-and-task-bound-agent-grant-profile)
- [Capability Matching](authorization.md#capability-matching)
- [Observability Context](evidence.md#observability-context)
- [Sessions and Actions](core.md#sessions-and-actions)
- [Receipts](evidence.md#receipts)
- [Portable Replay Bundle Profile](evidence.md#portable-replay-bundle-profile)
- [Revocation Semantics](authorization.md#revocation-semantics)
- [Error Model](core.md#error-model)
- [Versioning and Compatibility](core.md#versioning-and-compatibility)
- [Security Considerations](core.md#security-considerations)
- [Privacy Considerations](privacy.md#privacy-considerations)
- [Conformance](conformance.md#conformance)
- [Application MVP Mapping](conformance.md#application-mvp-mapping)
- [Example End-to-End Flow](conformance.md#example-end-to-end-flow)
- [Open Questions](core.md#open-questions)
- [References](core.md#references)
- [Appendix A: Why This Is Not Just an API Token](core.md#appendix-a-why-this-is-not-just-an-api-token)
- [Appendix B: Why This Is Not Just Computer Use](core.md#appendix-b-why-this-is-not-just-computer-use)
- [Appendix C: Product Positioning](core.md#appendix-c-product-positioning)

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

Agent Surface Protocol can consume Agent Passport as one concrete Agent
Identity Evidence format during grant issuance and runtime mediation:

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

These protocol layers describe semantic responsibility boundaries. They do not
define publication files, document ownership, or normative-reference
direction. One publication document can temporarily contain several protocol
layers, and one protocol layer can later be specified by several
exact-versioned documents, subject to the Modular RFC Publication Architecture.

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

<a id="modular-rfc-publication-architecture"></a>
## Modular RFC Publication Architecture

This section defines how ASP specification prose, registries, bindings, and
generated publication views are divided and versioned without changing their
authority by accident. It is a publication contract, not an ASP wire object,
runtime negotiation mechanism, or permission to interpret an incomplete module
set.

The canonical machine-readable Document Set Catalog is:

```text
publication/document-set.json
```

Its closed schema is:

```text
publication/document-set.schema.json
```

The catalog and its active canonical source documents jointly define one ASP
specification publication. The catalog defines document selection, exact
versions, normative dependency edges, publication order, export ownership,
aggregate role, and transition state. It MUST NOT add, weaken, or repair wire
semantics that are absent from or conflict between active canonical sources.
Such a conflict makes the publication invalid.

<a id="publication-authority-and-transitional-state"></a>
### Publication Authority and Transitional State

Only entries in the catalog's `documents` collection with `status` equal to
`canonical` are normative sources for that document set. An entry in
`reserved_documents` reserves a future document identity, target path, role,
and planned dependency graph. It has no normative authority, does not satisfy a
normative dependency, and MUST NOT be cited as if it had been published.

The current catalog uses `transitional_monolith`. In that mode:

- `drafts/agent-surface.md` is the only active canonical source;
- the aggregate path is that same source and is not represented as generated;
- all future Core, extension, binding, and conformance documents remain
  reserved and non-authoritative;
- the monolith owns the legacy aggregate anchor and identifier namespaces and
  every registry assigned to it by the catalog; and
- creating a reserved target file without atomically activating the complete
  modular document set is an invalid publication state.

`transitional_monolith` does not claim that the specification has already been
split. It allows tooling and review work to agree on the target boundaries
before source authority moves.

<a id="document-classes"></a>
### Document Classes

A modular ASP publication uses the following document roles:

| Role | Responsibility | Normative dependency direction |
| --- | --- | --- |
| Core | Common terminology, base objects, canonical JSON hashing and digest rules, discovery, invocation, errors, and compatibility rules needed by every ASP use | MUST NOT depend on an extension, binding, or conformance document |
| Authorization | Delegated user authority, Grant construction, identity bindings, constraints, lifecycle, and revocation | Exact Core version |
| Safe Effects | Proposal, preview, approval, Approval Receipts, reservation, commit, compensation, idempotency, effect admission, and the base mandatory Runtime/App Receipt wire shapes and action/effect bindings required by that lifecycle | Exact Core and required Authorization versions |
| Evidence | Signed or enriched receipt profiles, replay, signatures, provenance composition, and verification semantics layered over the base receipts | Exact Core and only the Authorization or Safe Effects versions whose objects it covers |
| Privacy | Data exposure, processing path, retention, training-use, and consent semantics | Exact Core and only required lower-layer extension versions |
| Binding | Mapping of ASP semantics onto one external transport or platform | Exact Core and only the extensions used by that binding |
| Conformance | Claims, requirements, vectors, reports, and registry rules for exact documents under test | Every exact document version whose requirements it tests |

A document's `kind` and `role` MUST agree. Core has no downstream normative
dependency. A binding MUST NOT depend normatively on another binding merely to
inherit transport behavior. A conformance document can test a binding, but a
normative protocol document MUST NOT depend on a conformance document for its
wire semantics.

The initial reserved modular graph contains Core, Authorization, Safe Effects,
Evidence, Privacy, the ASP-over-MCP binding, and Conformance. These reservations
record migration intent only and are valid only while the catalog is in its
transitional mode. A modular v1 catalog contains no reservations. A future
catalog version can define post-activation reservation and multi-version
selection rules; this one does not. Later document sets MAY add or omit
extensions and bindings when their exact dependency closure remains valid.

<a id="exact-normative-references"></a>
### Exact Normative References

Every normative dependency between ASP documents is an exact pair:

```text
(document_id, version)
```

Versions such as `latest`, branches, mutable URLs, compatible ranges, and
implicit repository state are forbidden for an internal ASP document
dependency. Every selected internal dependency MUST be an active document in
the same document set. The internal normative dependency graph MUST be closed,
acyclic, and in canonical dependency-before-dependent publication order.

An externally governed standard is not made an ASP document by being cited.
An ASP document MAY depend normatively on such a standard only through its
stable published identifier and an exact edition, revision, or dated version
when the external publisher defines one. A mutable `latest`, default branch, or
unversioned draft URL is not an exact external normative reference. External
references do not own ASP identifiers and do not participate in the internal
document DAG.

A Markdown link does not create normative authority. A normative reference
between active ASP documents MUST have all of:

1. a declared exact dependency edge from the referring document; and
2. a machine-readable reference record in the referring document's catalog
   entry; and
3. a target tuple containing the target `document_id`, exact `version`, and
   exported `anchor_id`, identifier namespace, registry id, or artifact id.

The record also names an exported source anchor in the referring document.
The publication validator resolves the source anchor, target document,
dependency edge, and target export as one closed reference. An ordinary
informative link MAY point outside the graph but MUST NOT be used to supply a
missing requirement, default, algorithm, validation rule, or security
decision. A reference cycle cannot be made informative in name while supplying
normative semantics in practice.

<a id="namespace-and-registry-ownership"></a>
### Namespace and Registry Ownership

Each exported anchor namespace, protocol or profile identifier namespace,
registry, and machine-readable normative artifact has exactly one owning active
document in one document set. A non-owner MAY reference an export through an
allowed exact dependency. It MUST NOT redefine, shadow, extend, or assign
fallback meaning to that export.

Registry identity and registry contents are separate versioned concerns. A
registry entry in the Document Set Catalog names its registry id, exact
registry version, repository source, and exact owning document. The owner MUST
declare that registry as an export. Moving ownership requires a new document
set version and one atomic catalog transition; two documents MUST NOT claim the
same registry concurrently.

The catalog itself owns publication selection only. It is not the owner of all
ASP identifiers merely because it lists their document owners.

<a id="stable-anchors-and-compatibility-aliases"></a>
### Stable Anchors and Compatibility Aliases

New public normative anchors MUST be explicit. Their ids use lowercase ASCII
letters and digits separated by single hyphens:

```text
[a-z0-9]+(?:-[a-z0-9]+)*
```

An explicit Markdown publication anchor appears immediately before its
heading. Its public reference identity is the exact tuple:

```text
(document_id, version, anchor_id)
```

An `anchor_id` MUST be globally unique among active documents in one document
set. Heading text, file order, renderer-specific slug generation, and duplicate
heading ordinals are not public identifier algorithms.

An alias in `public_anchors` is local to the same `(document_id, version)` as its
canonical anchor. It can preserve a renamed local fragment or a legacy fragment
in the generated aggregate, but it cannot redirect a former document tuple to a
different document. An alias MUST NOT be reassigned to unrelated semantics.
Moving a public section across documents requires a first-class relocation
record that names both exact old and new `(document_id, version, anchor_id)`
tuples and a resolver that verifies the historical source tuple as well as the
selected target. Schema version 1 does not define that record. Consequently,
cross-document relocation of any still-public anchor is fail-closed until the
publication pipeline and atomic-activation profiles add and validate it.

The transitional monolith predates this rule and contains derived aggregate
fragments. Its existing tooling has two duplicate-heading suffix conventions:
the GitHub and generated-TOC convention starts duplicate suffixes at `-1`,
while existing dashboard and review evidence starts them at `-2`. Neither
ordinal convention is a valid source of new public ids. A modular activation
MUST preserve every still-referenced legacy form as an explicit compatibility
alias or update all consumers in the same atomic transition. Until that
activation, a legacy fragment remains an aggregate compatibility reference,
not a document-scoped exported anchor.

Every active document declares each public anchor, its exact heading text, and
its local immutable aliases in `public_anchors`. The validator requires every
declared id and alias to appear as an explicit source anchor immediately before
that heading, rejects undeclared explicit source anchors, and enforces global
uniqueness. A cross-document normative reference targets this inventory rather
than recomputing a renderer slug; it is a reference to the selected target, not
a relocation redirect from an older tuple.

<a id="version-namespaces-and-independent-lifecycles"></a>
### Version Namespaces and Independent Lifecycles

The following values are distinct and MUST NOT be substituted for one another:

- `protocol_version`, which selects an ASP wire-semantics family;
- document `version`, which selects immutable prose and exports for one
  `document_id`;
- `document_set_version`, which selects an exact ordered document closure;
- registry version, which selects exact registry contents;
- runtime `surface_version`, which selects one application-published Agent
  Surface Manifest snapshot; and
- compiler revision and build-artifact digests, which identify publication
  tooling and output provenance.

Changing only a binding does not require a new Core version when Core semantics
and exports are unchanged. It does require a new binding version and a new
document-set version that selects it. Because this catalog selects at most one
version of each `document_id` and every internal dependency is an exact pin,
changing any selected document version requires republishing every selected
transitive dependent with a pin to the new version, even when its prose is
otherwise byte-identical. In the initial planned graph, changing ASP-over-MCP
therefore also republishes Conformance with the new exact binding pin. A binding
is independently versioned from Core, but it is a leaf only in a document set
where no selected document depends on it. This is an explicit lockstep cost for
upstream changes, not an inference of compatibility. A future versioned
export-interface mechanism can relax the lockstep rule; v1 does not.

Every active source and registry is bound to an exact SHA-256 digest in the
catalog, encoded as 64 lowercase hexadecimal digits. The aggregate has its own
exact digest. Every published document version, including a `-draft.N`
prerelease snapshot, is immutable together with its selected digest and
dependency edges. Any later source change requires a new document version, a
new document-set version, and updated digests before publication or use as
conformance evidence. A prerelease label communicates stability, not mutable
identity.

No publication version changes an active Agent Grant, retained manifest,
`surface_version`, or `surface_hash` by itself. Implementations select protocol
and surface semantics through their ordinary ASP bindings; they do not fetch a
new document set and silently reinterpret existing authority.

<a id="aggregate-assembly-and-build-provenance"></a>
### Aggregate Assembly and Build Provenance

In modular mode, the repository publishes a generated aggregate reading view in
addition to canonical module sources. The aggregate represents the exact
selected document set but has no independent namespace ownership or lifecycle.
Requirements remain owned by their canonical documents. A conflict between an
aggregate and its selected sources invalidates the aggregate; the aggregate
cannot override the sources.

The modular aggregate is assembled with Hyperprompt from an entrypoint and
compiler revision pinned by immutable release or commit identity. The build
manifest records source and include provenance. The source map records output
mapping and the aggregate output digest. Those artifacts are build provenance
only: they are not ASP Grants, signatures, conformance claims, protocol
registries, or normative owners.

Every content-changing transform, including generated table-of-contents or
anchor injection, MUST execute before the final provenance-bound assembly.
Mutating the aggregate after its final source map is produced makes the
publication stale unless the aggregate and all affected provenance artifacts
are regenerated and revalidated.

A modular publication build MUST:

1. use the exact compiler revision and catalog-selected sources;
2. run in a clean staging location and publish no partial output;
3. fail if an include is missing, undeclared, cyclic, or outside the allowed
   repository source set;
4. verify that the source-map output digest equals the final aggregate bytes;
5. preserve source mapping for the complete output;
6. produce byte-identical normative output and provenance for identical
   versioned inputs and the same declared reproducibility environment; and
7. pass publication, RFC, review, link, and conformance quality gates before
   publication.

A successful compiler exit alone proves neither normative readiness nor
atomic publication.

The v1 validator shipped with the transitional catalog deliberately rejects
`modular` mode. It does not claim to validate Hyperprompt provenance, source-map
coverage, output digests, cross-document relocation records, or transactional
readiness yet. The modular mode becomes selectable only with the separately
reviewed publication-pipeline resolver and its positive and negative tests.

<a id="atomic-modular-activation"></a>
### Atomic Modular Activation

Changing from `transitional_monolith` to `modular` is one atomic document-set
transition. It is valid only when:

- every selected canonical module source exists;
- the exact dependency graph is closed, acyclic, and role-valid;
- every export and registry has one active owner;
- the generated aggregate, build manifest, source map, and output digest agree;
- all legacy public references required by current consumers still resolve
  through a same-document alias or a validated first-class relocation record;
- the monolith is no longer selected as an active canonical document; and
- every publication and repository validator passes against the same source
  state.

Partial activation is forbidden. On any missing source, unresolved reference,
duplicate owner, stale sidecar, source-map gap, non-reproducible output, or
validation failure, publishers and tooling MUST retain the last complete
document set and MUST NOT present the candidate aggregate or reserved modules
as a current ASP specification.

Before activation, non-authoritative candidate sources MAY be prepared under a
catalog-excluded `publication/candidates/` tree. They MUST NOT occupy a reserved
canonical target path, satisfy a normative dependency, own an export, or be
presented as a current specification. The first candidate extraction SHOULD be
a semantic no-op and reproduce the previous aggregate bytes and compatibility
references. ASP-over-MCP is the pilot candidate. Changes to its protocol
semantics, requirements, or conformance vectors SHOULD be reviewed separately
so publication regressions are distinguishable from normative changes.

Activation occurs only after every Core, extension, binding, and conformance
candidate selected for the first modular set is complete. The atomic transition
moves all selected candidates to their canonical target paths, removes every
reservation, selects them as active documents, builds and validates the
aggregate and provenance, and removes the monolith from active selection in the
same source state. No incremental module extraction can claim active modular
authority before that point.

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
is server state, never a caller-supplied selector. Except for the Authorized
Discovery Bootstrap Descriptor defined below, an Agent Surface Manifest served
at the canonical URL MUST be the designated snapshot. This designation
is application state shared with the authorization server; it is not inferred
by ordering opaque `surface_version` values. Changing the canonical URL for the
same tenant, issuer, and app id MUST atomically migrate the lifecycle state and
supersede the prior location; it MUST NOT create an independent issuance
history. A cached or retained object can remain valid for an already-issued
Grant without remaining eligible for new issuance.

The snapshot above is the **base snapshot** for its lifecycle key. The
application MAY serve that complete base directly when its inventory is safe
for the authenticated or public context at the canonical URL. When disclosing
the complete base would reveal affordances that are not appropriate for a
particular user, runtime, or agent context, the application MUST either deny
that discovery request or use the Authorized Surface Projection Profile below.
When it uses the profile while withholding the base, it serves the profile's
non-inventory bootstrap descriptor at the canonical URL. It MUST NOT improvise
an unmarked partial manifest.

#### Authorized Surface Projection Profile

The optional Authorized Surface Projection Profile defines a minimized
manifest for one server-authenticated authorization context. Its identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1
```

The profile preserves exactly one issuer-authoritative base snapshot for each
ordinary surface lifecycle key. A projection never becomes another base and
never creates an independent issuance history.

A base manifest advertises support only by including the exact identifier above
in `compatibility.authorized_discovery_profiles` and by publishing an absolute
HTTPS `agent_api.authorized_surface_url`. Absence of either member in the base
means that the profile is unsupported. A client learns those values either from
a complete base it is permitted to receive or from the bootstrap descriptor
below. It MUST NOT infer support from an authentication challenge, a
tenant-specific origin, a filtered response, an OAuth scope, or ordinary
application behavior.

When the complete base is not disclosed, an authenticated or public `GET` of
its canonical `surface_url` returns this closed **Authorized Discovery
Bootstrap Descriptor** instead:

```json
{
  "document_type": "agent-surface-authorized-discovery-bootstrap/1",
  "profile": "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1",
  "surface_url": "https://example.com/.well-known/agent-surface.json",
  "authorized_surface_url": "https://example.com/agent-surfaces/authorized",
  "base": {
    "issuer": "https://example.com",
    "app_id": "com.example.project-tool",
    "surface_version": "2026-06-25",
    "surface_hash": "sha-256:<base64url-digest>"
  }
}
```

`document_type` and `profile` MUST equal the literals above. Descriptor
retrieval in version 1 MUST NOT redirect, and `surface_url` MUST equal the exact
canonical HTTPS URL requested by the client.
`authorized_surface_url` MUST be the absolute HTTPS endpoint declared as
`agent_api.authorized_surface_url` in the exact base. `base` MUST identify the
issuer-authoritative current base selected from the server-authenticated
lifecycle key and MUST be structurally identical to the corresponding base
manifest fields. A mismatch between the descriptor and base is
`surface_incompatible` and makes the descriptor unusable for issuance.

The descriptor contains no resources, actions, events, scopes, data classes,
schemas, operational limits, compatibility inventory, policy names, subject or
tenant identifiers, runtime or agent identifiers, entitlement facts, alternate
URLs, or counts. Unknown or additional members are invalid. It is discovery
metadata only: HTTPS and issuer binding remain required, and the descriptor,
its base hash, and possession of its endpoint grant no ASP authority and do not
prove that a later projection is an attenuation.

The descriptor response MUST send `Content-Type: application/json`,
`Cache-Control: private, no-store`, and `Referrer-Policy: no-referrer`. A public
descriptor still uses `private, no-store` so one URL cannot become a shared
cache path when the deployment later requires an authenticated tenant context.
The application selects its lifecycle key only from authenticated server state
or the public marker; a query parameter, path template supplied by the caller,
request header, or untrusted cookie MUST NOT select another tenant, subject, or
base. If no descriptor is available for the applicable context, the endpoint
returns `404 Not Found` without stating whether another base or context exists.

The client copies `profile`, `authorized_surface_url`, and the complete `base`
object verbatim into the projection request below. A descriptor becomes stale
as soon as its base is no longer current. The application MUST compare the
request with current server state and MUST NOT redirect, upgrade, or substitute
the request to another base. A client MAY repeat canonical discovery after a
generic stale failure, but it MUST NOT enumerate candidate base versions or
projection endpoints.

The projection endpoint accepts an authenticated `POST` with
`Content-Type: application/json`. The request is the following closed object:

```json
{
  "profile": "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1",
  "base": {
    "issuer": "https://example.com",
    "app_id": "com.example.project-tool",
    "surface_version": "2026-06-25",
    "surface_hash": "sha-256:<base64url-digest>"
  }
}
```

`profile` MUST equal the identifier above. `base` MUST identify the exact
current base snapshot for the server-derived surface lifecycle key. The request
MUST NOT contain a tenant id, user id, runtime id, agent id, role, group,
affordance name, desired projection id, or another authorization selector. The
application derives the applicable tenant and application subject from its
authenticated session and derives runtime and agent bindings only from the
independently authenticated or verified state used by its Grant flow. A
caller-supplied header, query value, cookie value not issued by the
application, request-body extension, display label, or previous projection is
not such state.

Version 1 does not define a new discovery credential. The deployment uses its
ordinary authenticated application-subject session and independently
authenticated runtime or verified agent state when available. Those mechanisms
identify the projection context but do not themselves grant an ASP action. If
the application cannot authenticate a dimension required by its projection
policy, it fails or uses the explicit `unbound` behavior below; it MUST NOT
trust the requested base tuple as identity evidence.

For this profile, the application defines the **projection lifecycle key** as:

```text
(
  base surface lifecycle key,
  server-side application-subject key,
  authenticated runtime-binding key,
  verified agent-evidence key,
  authorized-discovery profile identifier
)
```

The keys are application state and MUST NOT be serialized into the manifest.
The application maintains at most one current projection snapshot for that
complete key. It MUST use a distinct key when any element differs or is
unknown; it MUST NOT substitute a public marker, another subject, another
runtime, or another agent merely to obtain a cache hit. If the deployment does
not distinguish one of the runtime or agent dimensions before Grant issuance,
it uses an explicit server-side `unbound` marker for that dimension and MUST
re-evaluate the projection when the dimension becomes bound.

A successful response is a complete Agent Surface Manifest with this REQUIRED
top-level member:

```json
{
  "authorized_projection": {
    "profile": "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1",
    "projection_id": "prj_V7pQ2uQ0gVM7mVnR3Dck2w",
    "base_surface_version": "2026-06-25",
    "base_surface_hash": "sha-256:<base64url-digest>",
    "expires_at": "2026-07-21T21:00:00Z"
  }
}
```

`authorized_projection` is a closed object and part of the projected manifest
hashing view. `profile` MUST equal the identifier above. `projection_id` is an
opaque, non-empty, issuer-generated identifier for exactly one materialized
projection snapshot. It MUST contain at least 128 bits of unpredictable output
from a cryptographically secure generator, MUST NOT encode a tenant, subject,
runtime, agent, role, entitlement, or affordance, and MUST NOT be treated as a
credential. `base_surface_version` and `base_surface_hash` MUST equal the exact
base snapshot used to derive the projection. `expires_at` is a required RFC
3339 UTC timestamp with no fractional seconds and MUST be later than issuance.

The projected manifest has its own opaque `surface_version` and computed
`surface_hash`. The publisher MUST allocate a new projection id, surface
version, and surface hash whenever the projection hashing view, base snapshot,
projection lifecycle key, or authorization result changes. It MUST NOT reuse a
base or another projection's surface version for different bytes. The
projection retains the base manifest's `protocol`, `issuer`, `app_id`,
`surface_url`, and `surface_mode` exactly.

Version 1 permits attenuation only by omission:

1. `resources`, `actions`, and non-control `events` MAY contain only complete
   entries structurally identical to entries in the exact base snapshot;
2. every base control event remains present and structurally identical;
3. `scopes` and `data_classes` MAY remove only entries no retained declaration
   references;
4. when base `operational_limits` is present, its `actions` and `events` arrays
   remove every entry for an omitted affordance and retain every other entry
   structurally unchanged; if both projected arrays are empty, the projection
   omits the complete `operational_limits` object;
5. every retained reference, companion-action relationship, schema,
   operational-limit relationship, endpoint requirement, receipt requirement,
   and selected-profile dependency MUST remain closed and valid; and
6. every other base member remains structurally identical except the projected
   manifest's `surface_version`, `surface_hash`, and the added
   `authorized_projection` member.

A projection MUST NOT add an affordance absent from the base; change an id,
schema, scope, risk, approval, execution, effect, exposure, retention,
redaction, endpoint, audit, revocation, or compatibility semantic; weaken
`surface_mode`; or retain a declaration whose references are no longer closed.
Data exposure is narrowed only by omitting whole sources and their now-unused
classes. Version 1 does not permit rewriting a retained source to claim a
smaller class set, stronger redaction, or shorter retention; the publisher must
define a distinct base affordance when those semantics differ.

The Grant Issuer MUST possess and verify the complete exact base before it
accepts a projection for issuance. It recomputes both hashes, applies the
omission rules, verifies that the base and projection are current for their
respective lifecycle keys, and verifies that the authenticated context still
maps to `projection_id`. A runtime that also possesses the base SHOULD perform
the same verification. A runtime that possesses only the projection can verify
its manifest hash and authenticated issuer binding, but MUST NOT represent
`base_surface_hash` alone as a cryptographic proof that attenuation was
correct.

When this profile is selected, the Agent Grant `resource_server` object MUST
contain the following closed object copied exactly from the retained projected
manifest:

```json
{
  "authorized_projection": {
    "profile": "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1",
    "projection_id": "prj_V7pQ2uQ0gVM7mVnR3Dck2w",
    "base_surface_version": "2026-06-25",
    "base_surface_hash": "sha-256:<base64url-digest>"
  }
}
```

The Grant copy omits `expires_at`; projection freshness is checked at issuance,
renewal, exchange, and derivation rather than converted into Grant expiry. The
complete copy is part of the Grant hashing view. The runtime, Grant Issuer, and
Action Executor MUST require exact equality of every copied field with the
retained projected manifest and MUST reject a missing, extra, mismatched,
expired-at-issuance, or unknown projection as `surface_incompatible`. A child Grant can retain the
exact projection only for the same complete projection lifecycle key and can
only attenuate its Grant authority. A different subject, runtime, agent, or
base requires a newly derived projection and a new Grant; copying the prior
projection object never authorizes that transition.

An authorized response MUST send:

```http
Content-Type: application/json
Cache-Control: private, no-store
Referrer-Policy: no-referrer
```

An intermediary, browser HTTP cache, service worker, runtime discovery cache,
or application cache MUST NOT key an authorized response only by URL, bearer
token, projection id, issuer, app id, or base hash. A runtime that retains the
verified object as Grant authority state uses the complete projection cache
key: its local authenticated tenant, subject, runtime, and agent keys plus
`issuer`, `app_id`, canonical `surface_url`, profile, `projection_id`, projected
surface version and hash, and base surface version and hash. Those local
identity keys MUST remain outside agent-visible context, URLs, logs, receipts,
and the manifest. A missing or unresolved key disables reuse. HTTP `no-store`
does not prohibit retaining the exact verified manifest as bounded Grant state;
it prohibits using a general HTTP response cache as that authority store.

If the base is superseded, the projection expires, authenticated context
changes, entitlement state becomes unavailable, or the projection is no longer
current, the application MUST reject new issuance, renewal, exchange, and
derivation through that projection. It MUST NOT fall back to a cached base,
public surface, wider projection, or another context. Existing Grants retain
their exact projected manifest semantics until their own expiry or revocation;
an application policy that intends the authorization change to end existing
authority MUST perform the Semantic Grant Revocation Transition.

Failure responses use `surface_projection_unavailable` and MUST NOT distinguish
an unknown base, hidden affordance, unknown subject, wrong tenant, unauthorized
agent, stale projection, expired projection, or unavailable entitlement state.
They MUST contain no inventory counts, candidate ids, base diff, policy name,
membership fact, or alternate URL and MUST send `Cache-Control: no-store` and
`Referrer-Policy: no-referrer`. Implementations SHOULD make status, response
shape, and observable timing as uniform as operationally practical. A semantic
Grant request for an absent or hidden member continues to use
`invalid_authorization_details`; an Action Request is interpreted only against
its Grant's retained projection and returns `action_unknown` for an absent
action without searching the base or another projection.

After successful transport authentication and syntactic validation, every
profile failure above uses HTTP `404 Not Found` with the common ASP error
envelope and `code: "surface_projection_unavailable"`. Missing or invalid
transport authentication uses the deployment's ordinary `401` or `403`
challenge without projection detail. Malformed JSON, duplicate members, an
unknown member, or a value of the wrong type uses `400 Bad Request` with the
same ASP code and no projection detail. These transport distinctions describe
caller-correctable authentication or syntax state and MUST NOT vary according
to whether a hidden affordance or entitlement exists.

The required fail-closed outcomes are:

| Condition | Required outcome |
| --- | --- |
| Sensitive base is withheld but no valid bootstrap descriptor is available | Return generic `404 Not Found`; do not disclose or partially filter the base. |
| Bootstrap descriptor redirects, contains inventory, has an unknown member, or disagrees with the exact base | Reject it; do not send a projection request or infer another endpoint. |
| Caller supplies a tenant, subject, runtime, agent, role, or affordance selector | Reject the closed request as `surface_projection_unavailable`; do not use the selector. |
| Base hash is unknown, stale, superseded, or mismatched | Return `surface_projection_unavailable`; do not derive from another base. |
| Projection adds or rewrites a base declaration or has incomplete reference closure | Reject it as `surface_incompatible`; do not expose a partial result. |
| Cached projection key lacks or mismatches any authenticated context component | Treat it as a cache miss and perform fresh authenticated discovery. |
| Projection is expired or no longer current at issuance | Reject issuance without revealing which context or entitlement changed. |
| Hidden or nonexistent member is requested for a Grant | Return the same `invalid_authorization_details` outcome and disclosure shape. |
| Existing Grant is presented after the discovery context changes | Enforce the exact retained projection and current Grant state; revoke explicitly when policy requires existing authority to end. |

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

The top-level `authorized_projection` member is REQUIRED only for a manifest
produced under the Authorized Surface Projection Profile and is otherwise
forbidden. Its presence selects that exact profile and all of its base binding,
attenuation, lifecycle, caching, anti-enumeration, and Grant-copy rules; a
consumer MUST NOT ignore the member and process the object as an ordinary base
manifest.

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

For an Authorized Surface Projection, that ordinary key is necessary but not
sufficient: the runtime MUST also apply the complete authenticated-context and
base-snapshot cache partition defined by the selected profile. The projected
`surface_hash` commits to `authorized_projection`, while
`base_surface_hash` identifies the derivation source. Neither digest proves
that the projection is an attenuation unless the verifier possesses and checks
the exact base snapshot.

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
    "bindings": [
      {
        "profile": "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1",
        "transport": "streamable-http",
        "mcp_protocol_version": "2025-11-25",
        "authorization_composition": "asp-native",
        "endpoint": "https://example.com/mcp"
      }
    ],
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

`agent_api.bindings`, when present, is a non-empty array of closed
profile-specific application-facing carrier descriptors. A manifest selecting
the ASP-over-MCP Binding Profile contains exactly one entry for that profile
with `transport: "streamable-http"`, `mcp_protocol_version: "2025-11-25"`,
`authorization_composition` equal to `asp-native` or
`mcp-oauth-dual-use`, and an absolute HTTPS `endpoint` without a fragment.
The endpoint MUST NOT contain a query component or URI userinfo. These
restrictions make that exact URI string both the canonical MCP server URI and,
when DPoP is selected, the RFC 9449 `htu` request target for this profile;
implementations MUST NOT drop a query or otherwise normalize it into a
different comparison or credential audience value. A DPoP-bound
Grant requires `asp-native`; `mcp-oauth-dual-use` is valid only under the
Bearer and audience-equality rules in the binding profile. The runtime discovers and verifies
the manifest through ordinary ASP HTTPS discovery before opening MCP; MCP
resource discovery is a verification of that pinned snapshot, not a bootstrap
mechanism. A runtime using an Authorized Surface Projection obtains and
verifies it through the ordinary authenticated projection flow before opening
the projected MCP channel.

The authorization request names the selected MCP endpoint in `locations`, and
the issued Grant MUST retain that exact location. Consequently the endpoint,
profile descriptor, and surface are included in the Grant hashing view through
`locations` and `resource_server.surface_hash`. The Runtime Mediator
authenticates the endpoint's TLS identity and rejects every endpoint-changing
redirect, including a same-origin path change. It never forwards a credential
or proof to a target absent from the Grant's exact `locations`,
and requires initialize metadata, the manifest resource, every mapped call,
and every receipt read to use that exact selected MCP endpoint and the current
active binding session. Stable receipt identity and retention survive the
transport-session replacement defined by the profile. A server-provided URI or successful MCP authorization cannot replace
the manifest-pinned endpoint. For MCP-OAuth dual use, the existing additional
rule requires `credential_audience` to equal this canonical server URI.
Both initialize peers and every transport attempt MUST repeat or implement the
manifest-selected composition exactly; omission, substitution, or fallback is
a binding downgrade and fails before ASP reconstruction.

`agent_api.authorized_surface_url` is REQUIRED exactly when
`compatibility.authorized_discovery_profiles` is present. It MUST be an
absolute HTTPS URL and MUST implement only the authenticated projection
contract defined by the selected profile. It is not an action endpoint, does
not accept a Grant Credential as authority to widen discovery, and MUST NOT be
included in a Grant's `locations` allow-list. Changing the URL changes the base
manifest hashing view, invalidates every derived projection for new issuance,
and requires a new base `surface_version` and `surface_hash`.

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
    "purpose_binding_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1"
    ],
    "approval_receipt_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1"
    ],
    "human_elicitation_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/human-elicitation/v1"
    ],
    "authorized_discovery_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1"
    ],
    "human_elicitation_replay_retention_seconds": 86400,
    "agent_identity_evidence_profiles": [
      {
        "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1",
        "format_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
        "artifact_digest_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
        "verification_profiles": [
          "https://example.com/profiles/agent-passport-verification/2026-01"
        ],
        "key_binding_profiles": [
          "https://example.com/profiles/issuer-key-thumbprint/v1"
        ],
        "freshness_profiles": [
          "https://example.com/profiles/status-max-age/2026-01"
        ],
        "status_profiles": [
          "https://example.com/profiles/agent-passport-status/2026-01"
        ],
        "migration_profiles": [
          "https://github.com/0al-spec/agent-surface/migration/agent-passport-fields-to-identity-evidence/v1"
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
    "token_binding": ["runtime", "agent_identity_evidence"],
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
    "authorized_surface_url": "https://example.com/agent-surfaces/authorized",
    "bindings": [
      {
        "profile": "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1",
        "transport": "streamable-http",
        "mcp_protocol_version": "2025-11-25",
        "authorization_composition": "asp-native",
        "endpoint": "https://example.com/mcp"
      }
    ],
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

`compatibility.purpose_binding_profiles`, when present, MUST be a non-empty
array of unique collision-resistant profile identifiers. This draft defines
`https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1`.
The member advertises only profiles for which the Grant Issuer and every
protected-resource enforcement point can resolve the exact issuer-owned purpose
and optional task records, enforce their revisions, lifecycle, relationship,
attenuation order, and action policy, and fail closed when current state is
unavailable. Absence means that the application does not support purpose-bound
issuance. A runtime MUST NOT infer support or authority from
`session.start.payload.task`, an A2A task identifier, an application workflow,
human-readable goal text, a label, or a digest.

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

`compatibility.authorized_discovery_profiles`, when present, MUST be a
non-empty array of unique collision-resistant profile identifiers. This draft
defines only the exact Authorized Surface Projection Profile identifier. The
member MUST be accompanied by an absolute HTTPS
`agent_api.authorized_surface_url`, and that endpoint MUST implement the
profile's closed request, attenuation, lifecycle, anti-enumeration, and cache
rules. Advertising a filtered UI, OAuth scope, tenant endpoint, or generic
authorization service is not support. Absence means that callers can consume
only the ordinary manifest response permitted for their discovery context.

`compatibility.agent_identity_evidence_profiles`, when present, MUST satisfy
the closed discovery contract in the Pluggable Agent Identity Evidence Profile.
The member advertises only atomic combinations the application can retrieve,
independently verify, status-check, project, migrate when named, and bind into a
Grant. A runtime MUST NOT infer production verification support from a source
format version, signature algorithm label, file extension, public key, Agent
Card, DID, validator, or legacy Passport advertisement.

`compatibility.agent_passport_profiles` is the legacy advertisement for the
Passport-specific Grant wire shape. It retains the previous closed-object
contract (`profile`, `hash_profile`, `verification_profiles`, and
`max_artifact_bytes`) only for unexpired legacy Grants and explicit migration.
It MUST NOT be interpreted as support for a new generic envelope. An
application that issues a new `identity_evidence` envelope MUST advertise the
generic member, and one that supports migration MUST name the exact migration
profile in that generic entry. New deployments SHOULD omit the legacy member.

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
- runtime id, agent id, and identity-evidence hash
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
    "identity_evidence_hash": "sha-256:<base64url-digest>",
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
    "identity_evidence_hash": "sha-256:<base64url-digest>",
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
    "identity_evidence_hash": "sha-256:<base64url-digest>",
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
`runtime_id`, `agent_id`, `identity_evidence_hash`, `previous_state`, `budget`,
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
  "identity_evidence_hash": "sha-256:<base64url-digest>",
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
`agent_id`, `identity_evidence_hash`, `pause_id`, `session_id`, `session_generation`,
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

## Sessions and Actions

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
    "identity_evidence_hash": "sha-256:<base64url-digest>",
    "initiated_by": "runtime",
    "surface": {
      "app_id": "code.example.com",
      "surface_version": "2026-06-25",
      "surface_hash": "sha-256:<base64url-digest>"
    },
    "task": {
      "purpose_binding": {
        "profile": "https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1",
        "purpose": {"id": "pur_01J2Q7M4K8X5", "revision": "rev_3"},
        "task": {"id": "tsk_01J2Q7N9C3V6", "revision": "rev_7"}
      },
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
    "identity_evidence_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "purpose_binding": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1",
      "purpose": {"id": "pur_01J2Q7M4K8X5", "revision": "rev_3"},
      "task": {"id": "tsk_01J2Q7N9C3V6", "revision": "rev_7"}
    }
  }
}
```

When the Grant contains `constraints.purpose_binding`,
`session.start.payload.task.purpose_binding` is REQUIRED and MUST be deeply
equal to it after structural validation. The application stores that exact
object in the authoritative session and `session.state` repeats it as shown.
When the Grant omits the profile, both session members MUST be absent. An
omitted, additional, or changed binding fails as `session_invalid`; the
application does not repair it from `kind`, `goal`, or `inputs`.

`session.start.payload.task` is user- or runtime-authored orchestration, not an
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
    "identity_evidence_hash": "sha-256:<base64url-digest>",
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

When the Grant contains `constraints.purpose_binding`, the application MUST
resolve its exact issuer-owned purpose and optional task records for the
Grant-bound subject and app, verify exact revisions, active state and
relationship, require the authoritative session's exact equal binding, and
apply the current purpose and task policy to the action, target resources,
normalized input, execution mode, and maximum effects. It performs these checks
before idempotency lookup or allocation, budget or capacity admission, policy
receipt creation, workload dispatch, reservation, or effect. The Action Request
does not repeat the object: adding a client-authored copy cannot repair the
Grant or session and would be invalid unless a future extension defines it.

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
    "output": {
      "resource": {
        "type": "comment",
        "id": "comment_789",
        "url": "https://code.example.com/example-org/example-repo/pull/13#discussion_r..."
      }
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
| `identity_evidence_invalid` | The exact identity artifact, signature, issuer/subject projection, key binding, agent binding, lifecycle state, or trust result is definitively invalid. |
| `identity_evidence_profile_unsupported` | A required envelope, format, digest, verification, key-binding, freshness, status, integrity, or migration profile is unsupported or incomplete. |
| `identity_evidence_status_unavailable` | Fresh authenticated status for the exact identity-evidence envelope cannot currently be established. |
| `identity_evidence_migration_required` | A legacy identity tuple cannot be projected uniquely and safely into the selected envelope without a new verified migration and consent flow. |
| `passport_invalid` | The exact Agent Passport artifact is missing, malformed, expired, revoked, untrusted, incorrectly signed, or not bound to the selected agent. |
| `passport_profile_unsupported` | A required Passport consuming, artifact-hash, verification, status, or integrity profile is unsupported or incomplete. |
| `passport_status_unavailable` | Fresh authenticated status for the exact Passport tuple cannot currently be established. |
| `runtime_untrusted` | Runtime authentication cannot be mapped to the exact active runtime identity projection, or a required posture, locality, or assurance is absent, stale, suspended, revoked, or mismatched. |
| `purpose_binding_denied` | A known current purpose or optional task binding does not authorize new work under its current state or policy. |
| `purpose_binding_status_unavailable` | Current authenticated lifecycle or relationship state for the exact purpose and optional task binding cannot be established. |
| `surface_incompatible` | A required surface version, profile, or action declaration is unsupported or internally inconsistent and cannot be interpreted safely. |
| `surface_projection_unavailable` | An authorized discovery projection cannot be returned without revealing whether its base, authenticated context, entitlement state, or requested member exists. |
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

Every direct authenticated ASP HTTP endpoint returns `429 Too Many Requests`
for this error and MUST NOT permit the response to be stored; it sends
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

An HTTP-based encapsulating binding whose protocol requires a successful HTTP
exchange for its own result framing is not a direct ASP HTTP endpoint for the
previous paragraph. In the ASP-over-MCP Binding Profile, once a valid
`tools/call` has been reconstructed and processed, `rate_limited`,
`capacity_state_unavailable`, and `service_unavailable` travel as the exact
closed `action.error` projection in a `CallToolResult` with `isError: true`; the enclosing
MCP HTTP response remains a successful MCP result response and carries
`Cache-Control: no-store`. Its ASP `retry_after_seconds`, if present, remains
inside the structured envelope and MUST NOT be promoted to an HTTP
`Retry-After` header on that successful MCP response. Conversely, an MCP
endpoint, authorization layer, or intermediary can return transport-level
`429` or `503` before an Action Request reaches the Action Executor, but that
response is only MCP transport evidence and MUST NOT be synthesized into an
ASP capacity error, no-effect claim, or semantic retry decision.

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

`identity_evidence_invalid` is not retryable with the same unchanged envelope
and trust state. `identity_evidence_profile_unsupported` requires support for
the exact named profile combination or a new consent and issuance flow; an
implementation MUST NOT fall back to schema-only validation or another
profile. `identity_evidence_status_unavailable` MAY be retried after
authenticated status-service recovery or the profile-defined retry delay, but
the unresolved attempt MUST NOT claim an idempotency key, admit budget, create
a receipt, workload, or effect. `identity_evidence_migration_required` is
terminal for the unchanged legacy tuple and operation; it requires the explicit
fresh migration flow defined by the selected migration profile.

`passport_invalid`, `passport_profile_unsupported`, and
`passport_status_unavailable` are legacy error codes only for a Grant using the
legacy Passport wire shape. They have the equivalent invalid, unsupported, and
temporarily unavailable semantics above. A component MUST NOT return a legacy
Passport code for a generic envelope merely because its concrete
`format_profile` is Agent Passport, and MUST NOT expose the concrete format in
a public generic error.

`purpose_binding_status_unavailable` is a fail-closed indeterminate result, not
proof that a record was revoked or that a task does not exist. It MAY be
retried only after authenticated issuer-state recovery, while the affected
session remains fenced. The rejected attempt MUST NOT claim an idempotency key,
admit budget or capacity, create a policy or action receipt, dispatch workload,
or attempt an effect. A malformed or hash-mismatched binding remains
`integrity_mismatch`; a Grant/session mismatch remains `session_invalid`; Grant
expiry remains `grant_expired`; and a terminal purpose or task follows semantic
revocation and returns `grant_revoked`.

`purpose_binding_denied` covers both a known suspended record and a definitive
current purpose/task policy denial. Its public envelope MUST set
`retryable: false` for the unchanged binding and authenticated state, MUST NOT
reveal which record, relationship, action, resource, input predicate, or rule
failed, and MUST occur before idempotency, budget, capacity, receipt, workload,
or effect admission. An application Policy Decision can use
`app_policy_denied`, and a runtime-local decision can use
`local_policy_denied`, but those reason codes do not replace this action-error
mapping. A later authenticated activation or material policy change can permit
a new ordinary attempt; a suspended session additionally requires explicit
resume under the exact same binding and generation rules.

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
`purpose_binding_status_unavailable` requires authenticated recovery of the
exact same issuer-owned revisions and relationship; retry never substitutes a
new purpose, task, revision, session, or idempotency key.
After an effect was attempted, drift or uncertainty is represented by
`effect_outcome: "partially_applied"` or `"unknown"`, not a retryable
`effect_mismatch`. `outcome_unknown` MUST NOT be retried under a new
idempotency key until the application reconciles the authoritative outcome.

## Versioning and Compatibility

This section defines runtime `surface_version` compatibility. It is separate
from the publication `document_set_version`, individual specification document
versions, registry versions, and compiler revisions defined by the Modular RFC
Publication Architecture. None of those publication values can be substituted
for a manifest version or hash.

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
- Changing a base snapshot invalidates every Authorized Surface Projection
  derived from the prior base for issuance, renewal, exchange, and derivation.
  The publisher derives a new projection with a new `projection_id`, projected
  surface version, and projected surface hash. It MUST NOT rebase the old
  projection in place or preserve its id while changing `base_surface_hash`.
- Changing the server-side subject, runtime, agent, or entitlement input to an
  Authorized Surface Projection produces a new projection lifecycle key or a
  new current projection snapshot for that key. It does not silently rewrite
  an existing Grant. Ending authority already issued under the old projection
  requires the ordinary Semantic Grant Revocation Transition.
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
its own resources, but not for the user's local machine. Identity evidence,
including an Agent Passport, is evidence, not authority. Grant is authority only
within caveats.

### Confused Deputy

The runtime can accidentally use a grant for the wrong agent, user, workspace, or
application. Grants MUST bind user, app, runtime, agent, and the complete exact
identity-evidence envelope selected by the Grant.
When Purpose- and Task-Bound Agent Grant is selected, the complete purpose and
optional task references are part of the same boundary. A matching action,
repository, issue number, goal, description, or external task id does not allow
the runtime to substitute another issuer-owned purpose or task.

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

Purpose Binding preserves the same independent-enforcement boundary. A
malicious runtime can claim that an agent remains on-task, change
`session.start.payload.task.goal`, copy an A2A task id, or present a local policy
decision. None of those values proves the current issuer-owned record or its
action relation. The application MUST resolve the exact hashed references and
current state itself and MUST fail closed when that state is unavailable.

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

- Model Context Protocol Specification 2025-11-25:
  <https://modelcontextprotocol.io/specification/2025-11-25>
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
which versioned identity evidence, to perform which typed app actions, against which
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
