## Runtime Runaway Protection

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
`(guard_lineage_id, runtime_id, agent_id, identity_evidence_hash,
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
