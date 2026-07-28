## Session Start

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

## Session Pause

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
