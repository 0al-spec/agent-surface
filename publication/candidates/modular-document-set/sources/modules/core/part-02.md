## Agent Client Protocol

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

## OAuth

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

## Agent Passport

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

## DID and Verifiable Credentials

Decentralized Identifiers and Verifiable Credentials can be useful for future
signed grants, issuer trust, and portable delegation proofs:

- DID Core: <https://www.w3.org/TR/did-core/>
- Verifiable Credentials Data Model: <https://www.w3.org/TR/vc-data-model-2.0/>

This draft does not require DID or VC for the MVP.

# Conceptual Architecture

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

# Protocol Layers

Agent Surface Protocol is specified as four separable layers.

These protocol layers describe semantic responsibility boundaries. They do not
define publication files, document ownership, or normative-reference
direction. One publication document can temporarily contain several protocol
layers, and one protocol layer can later be specified by several
exact-versioned documents, subject to the Modular RFC Publication Architecture.

## 1. Agent Surface Manifest

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

## 2. Agent Grant Protocol

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

## 3. Runtime Bridge Protocol

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

## Human Elicitation Events Profile

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

### Authority Boundary and Participants

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

### Common Request Object

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

### Elicitation Kinds

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

### Resolution Object

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

### Lifecycle, Replay, and Rebinding

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

### Privacy and Failure Rules

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

## ASP-over-AHP Binding Profile

The ASP-over-AHP Binding Profile identifier is
`https://github.com/0al-spec/agent-surface/profiles/asp-over-ahp/v1`. It defines
how a deployment can carry ASP participation through an AHP session while
keeping ASP authority and evidence semantics
unchanged. This draft does not define the base AHP protocol, media type, or
representation syntax. A deployment claiming this profile MUST identify the
base AHP version and serialization independently and MUST implement the closed
binding contract below without inferring omitted AHP semantics.

### Scope and Authority Boundary

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

### Binding Negotiation and Record

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

### Binding State Machine

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

### Replay, Failure, and Security Rules

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

## 4. Agent Adapter Protocol

The runtime-to-agent integration layer:

- `custom-command`
- `codex-cli`
- `claude-code`
- `acp-stdio`
- `mcp-client`
- `mcp-server`

The adapter layer turns a concrete agent into a runtime-mediated worker.

<a id="modular-rfc-publication-architecture"></a>
# Modular RFC Publication Architecture

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
## Publication Authority and Transitional State

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
## Document Classes

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
## Exact Normative References

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
## Namespace and Registry Ownership

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
## Stable Anchors and Compatibility Aliases

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
## Version Namespaces and Independent Lifecycles

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
## Aggregate Assembly and Build Provenance

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
## Atomic Modular Activation

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
