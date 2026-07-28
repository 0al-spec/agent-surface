## Session Authority and Lifecycle

An ASP session is a bounded orchestration record for work performed under one
Agent Grant. A session does not mint authority, widen a grant, keep an expired
grant alive, or make an agent a protocol principal. Every session is bound to
exactly one authoritative tuple consisting of:

- the grant `subject.user`, `grant_id`, and `grant_hash`
- the grant-bound `runtime`, `agent`, and `identity_evidence_hash`
- the application `app_id`, `surface_version`, and `surface_hash`
- when selected, the complete exact `constraints.purpose_binding`

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

When a Purpose Binding record is suspended or current authenticated state is
unavailable, the application MUST fence the affected session before accepting
another action and the runtime MUST stop local work. Resume requires the exact
same purpose and optional task ids and revisions, the same relationship, and a
current active result; it cannot change the binding or revive a terminal
record. Terminal closure follows Semantic Grant Revocation rather than session
resume.

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
