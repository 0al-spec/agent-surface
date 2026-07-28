# Revocation Semantics

The protocol MUST define what happens when authority changes.

Revocation MUST be possible from both sides. The application-managed and
runtime-managed user paths are defined below and converge on the same
authoritative grant transition.

## Active Grant Management

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
- when selected, the exact Purpose Binding profile, purpose id and revision,
  optional task id and revision, purpose-only or task-bound mode, current
  coarse active, suspended, terminal, or unavailable state, effective
  expiration, and an authenticated safe issuer label when available;
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

## User Revocation Intent and Confirmation

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

## Revocation Timing and Concurrency

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

## Semantic Grant Revocation Transition

Every issuance and transport binding uses one transport-neutral semantic
transition. For a located active grant, the application MUST atomically mark the
grant inactive, reject every credential derived from it, invalidate refresh
tokens and proof-bound sessions, invalidate outstanding execution tokens and
reservations, and cascade revocation to child, exchanged, renewed, or
superseding grants whose authority preserves its delegation lineage. The
transition establishes `effective_at` and the concurrency fence defined above.

When a Purpose Binding purpose becomes terminal, the Grant Issuer MUST invoke
this transition for every Grant bound to that exact purpose and every
descendant. When only a task becomes terminal, it invokes the transition for
the exact task-bound Grants and their descendants without revoking sibling
tasks or independently consented lineages. A purpose-only Grant can remain
active for other work that current purpose policy permits. Suspension or
temporary status unavailability fences sessions and actions as defined by the
profile but is not falsely recorded as terminal revocation.

The transition is idempotent. Reapplying it to an inactive grant MUST NOT emit
duplicate control events, repeat cleanup side effects, or change the original
effective instant. It does not erase receipts or undo committed effects.
Transport profiles define how a runtime or user authenticates a request and how
success is represented; they MUST NOT weaken this inactive state, cascade, or
timing boundary. A non-OAuth issuance model claiming Grant Issuer Profile
conformance MUST define an authenticated revocation binding that invokes this
same transition.

## OAuth Grant Revocation Profile

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
    "identity_evidence_hash": "sha-256:<base64url-digest>",
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
`grant_id`, `grant_hash`, `app_id`, `runtime_id`, `agent_id`, `identity_evidence_hash`,
`revoked_at`, `effective_at`, `reason`, and `cascade`; `parent_grant_id` is
REQUIRED for a child grant and otherwise MAY be null. `data.runtime_id` MUST
equal `aspaudience`. Defined reason values are `user_revoked`, `application_revoked`,
`runtime_revoked`, `credential_compromise`, `parent_revoked`, `policy_changed`,
`purpose_closed`, `task_closed`, and `superseded`. `purpose_closed` and
`task_closed` indicate the terminal Purpose Binding transitions defined by
that profile and reveal no record identifier beyond the Grant the runtime
already possesses. A runtime MUST still enforce revocation when it receives an
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

## Grant Revoked

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

## Runtime Disconnected

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

## Agent Identity Evidence Invalid or Unavailable

If the exact Grant-bound identity evidence becomes suspended, revoked,
expired, trust-invalid, key-invalid, or no longer bound to the selected agent:

- runtime MUST stop launching that agent for new sessions
- runtime and application MUST reject new actions before idempotency lookup,
  budget admission, receipt creation, or effect
- runtime and application MUST fence or cancel active sessions rather than let
  policy silently complete under invalid evidence
- application MUST apply the Semantic Grant Revocation Transition to every Grant
  and derived Grant bound to the exact identity-evidence envelope

When fresh authenticated status is `unknown`, `unavailable`, or stale but the
evidence is not known to be invalid, enforcing components MUST fail closed and
fence affected sessions while status is unresolved. A later fresh `active`
result for the same exact envelope MAY restore use without changing
`grant_hash`; an implementation MUST NOT substitute another format, artifact,
issuer, subject, key binding, status reference, or profile. Legacy Grants using
the Passport-specific tuple follow the equivalent rules in the Minimal Agent
Passport Grant-Issuance Profile.

## Surface Version Changed

If the Agent Surface changes incompatibly:

- app SHOULD publish a new `surface_version`
- runtime SHOULD re-fetch and re-validate schemas
- app MUST invalidate execution tokens and reservations bound to an
  incompatible old action declaration
- grants bound to incompatible actions SHOULD require renewal

## User Session Expired

If the user's ordinary app session expires, app policy decides whether existing
agent grants continue. High-risk grants SHOULD expire with or before the user
session unless explicitly configured otherwise. If policy ends the grant or
session, the app MUST cancel the affected ASP sessions and fence new actions.
If policy allows them to continue, the ordinary login expiry does not change the
ASP session generation. A later user login MAY observe or cancel those sessions
only after authenticating the same application subject; it is not session-resume
authority for a runtime with a different tuple.
