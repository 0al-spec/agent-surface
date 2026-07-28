# Error Model

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

### HTTP Capacity Error Binding

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

# Versioning and Compatibility

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

# Security Considerations

## Threat Model Summary

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

## Confused Deputy

The runtime can accidentally use a grant for the wrong agent, user, workspace, or
application. Grants MUST bind user, app, runtime, agent, and the complete exact
identity-evidence envelope selected by the Grant.
When Purpose- and Task-Bound Agent Grant is selected, the complete purpose and
optional task references are part of the same boundary. A matching action,
repository, issue number, goal, description, or external task id does not allow
the runtime to substitute another issuer-owned purpose or task.

## Raw Token Leakage

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

## Malicious or Compromised Runtime

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

## Misleading Impact Simulation

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

## App-Embedded Runtime

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

## Malicious or Compromised Agent

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

## Malicious or Compromised Application

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

## Stolen Grant Credential

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

## Prompt Injection

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

## Replay and Duplicate Actions

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

## Execution Mode Confusion, TOCTOU, and Reservation Abuse

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

## Surface Downgrade

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

## Receipt Forgery

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
