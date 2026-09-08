# ADP-03: proposed Calcu handling policy

> Superseded direction (2026-09-08): the owner withdrew the transient-retention
> candidate and stopped the live probe lane. See the
> [BYOA responsibility decision](byoa-responsibility-decision.md) for the current
> application/agent boundary and unresolved RFC compatibility. The proposal
> below is historical design evidence, not the selected deployment policy.

Status: concrete design for review, **not deployed or capability-verified**.
Baselines: ASP `11f68c1` (Privacy `0.1.0-draft.3`), Calcu `a059d77`.
This does not close ADP-03, approve live migration or replace the independent
ADP-02 cost decision. No new RFC fields or Calcu features are introduced.

## Scope and classification

One action, `calculation.propose`, accepts current-request numeric operands
with one of four operators. It performs no protected application-resource read.
The caller's task does not authorize history, account, file or database access.
The following maximum is deliberately conservative without a semantic detector:

| Proposed class | Classification | Covered representation |
| --- | --- | --- |
| `calculation.content` | `sensitive` | Operator, echoed left/right operands and derived numeric result; includes repeated operands in application projections |
| `calculation.runtime_context` | `sensitive` | Runtime-visible session/generation, Grant ID/hash, surface hash, subject/delegate/audience, identity-evidence hash and trace/span correlation; hashes are not public declassification |
| `calculation.status` | `private` | Fixed envelope discriminants, action/mode identifiers, success marker and closed error codes; no task text, raw arguments, stack or upstream diagnostics |

These are application-local class identifiers, not new protocol classes.
The publisher would provide non-empty labels/descriptions matching this table.
Each mixed payload retains the complete declared source envelope; the agent
must not infer a less protective subset from the status field alone.

Proposed action `data_exposure` fragment:

```json
{
  "classes": [
    "calculation.content",
    "calculation.runtime_context",
    "calculation.status"
  ],
  "redaction": {"mode": "none"},
  "retention": {"mode": "transient", "delete_on_grant_end": true}
}
```

`none` means this maximum covers the complete unredacted allowed response; it
does not disable closed schemas or permit arbitrary diagnostics. All response
paths must be checked before the application boundary. LocalBackend stripping
metadata after HTTPS receipt is not pre-delivery redaction. Credential material
and identity artifacts themselves are not part of this allowed envelope.

Ordinary unannotated numbers do not require a PIN detector. Known credential
provenance, including a non-releasable ASP Grant Credential, is outside this
maximum and must be rejected before echo or result delivery, with no offending
value in diagnostics. Trusted sensitivity must not be discarded. The current
demo has no verified trusted-classification enforcement mechanism; the proposal
does not claim otherwise. If a future source enriches results with protected
data, it needs authorized access and a reassessed exposure contract.

The issuer derives the complete projection, and the runtime independently checks
it, as described in [exposure design](exposure-design.md). No caller-provided
projection is trusted. A matching hash does not prove retention feasibility.

## Ownership and proposed lifecycle

The proposal separates app-owned display from runtime/agent copies. These are
desired controls, not statements that every cleanup path is already implemented.

| Copy / owner | Proposed end of useful lifetime | Current evidence / gap |
| --- | --- | --- |
| Editable task / application UI | User replaces it or closes/unmounts the panel; Cancel may preserve it for editing/retry | React state observed; no new history, export or durable storage feature; no forensic browser-erasure promise |
| Submitted task snapshot, result, trace, agent prose / application UI | Successful result may remain until next submission or panel close; cancellation/error clears task-result projection and invalidates late events | Current Cancel hides but retains references; explicit clearing and unmount cancellation need implementation/tests |
| Task/API request locals / application host | Request/task termination; release outstanding references | No new raw-payload logging or persistence; asynchronous references need lifecycle evidence |
| Protocol buffers, queues, tool output and agent context / runtime-agent path | Transient only; Grant expiry/revocation shortens lifetime, including cancellation/task settlement | Fake cleanup and sanitized diagnostics are partial evidence; exact CLI local context/cache/log behavior remains unverified |
| Per-task temporary directory / adapter | After process termination on success, failure, timeout or cancel | Four fake-process cleanup cases pass; not proof of no writes elsewhere |
| Grant/identity records / application authority store | Separate data-minimized safety/audit policy | Do not delete live safety state to satisfy output retention; Map minimization remains ADP-07/08 debt |
| Remote provider copies | Governed by the selected route and applicable provider handling, not local UI cleanup | No downstream deletion/training claim; no additional whole-path profile selected; base runtime-agent feasibility still required |

Releasing references is not deterministic memory zeroization. Application UI
ownership cannot be used to relabel a runtime cache. Clearing the UI does not
prove provider deletion. Cancellation must invalidate the current generation,
abort active work, settle/revoke task authority and clear the abandoned result
projection; the editable task may remain app-owned. No extra confirmation or
opaque-reference calculator UX is proposed.

## User-facing disclosure draft

“Your task and the calculator operation's operands and result are sent through
the configured agent to its model provider. The application keeps the displayed
task/result in this panel until replacement or close; it does not add a saved
history. ASP credentials stay in the local server boundary. This demo does not
promise provider deletion or no training.”

This is proposed wording to validate against the eventual implementation, not
a deployed notice or consent receipt. Personal ChatGPT login and lawful,
non-synthetic-only task scope are owner-reported choices, not proof of another
person's consent or effective account settings. The demo remains single-user;
an authenticated principal/tenant mapping is still a separate design gate.

## Exit evidence and next bounded work

**Historical gate inventory, superseded.** The table below records the withdrawn
proposal's gates, not current closure requirements. The current BYOA decision
replaces agent-retention verification with the normative compatibility question;
it does not remove the remaining application-side design gates.

| ADP-03 area | Progress from this proposal | Still needed before closure |
| --- | --- | --- |
| Classification/redaction | Concrete class maximum and `none` candidate | Review live envelope coverage and credible known-provenance enforcement design |
| Grant projection | Exact derivation mechanics already documented | Feasible issuer/runtime integration design; executable migration belongs to ADP-05/08 |
| Task/UI ownership | Explicit copy owners, event-bound display and cancellation policy | Review policy and lifecycle feasibility; distinguish observed behavior from missing cleanup |
| Runtime-agent retention | Concrete transient contract unchanged | Verify selected CLI local persistence and outstanding references using a separately approved isolated test strategy |
| Selected route / optional restrictions | Owner preferences remain recorded; no new provider profile | Actual-path evidence, applicable settings and base-contract capability evidence; no credential inspection implied |
| Principal/disclosure | Single-user limit and notice draft | Exact principal binding and disclosure review, not an inferred multi-user authorization |

Historical next step, superseded by the BYOA decision: specify an isolated real-CLI retention probe
and its evidence criteria without running it or copying an auth store. Report
which behavior is observable and which remains unknown. The former plan required
credential-strategy approval; no such approval is requested now. Do not treat a clean filesystem
snapshot as proof of complete context deletion or provider handling.

The [prepared probe kit](retention_probe/README.md) now supplies the bounded
runbook and offline report interpreter. It has not collected live evidence;
authentication and collection were never performed. Neither is now a pending
prerequisite: the probe lane is stopped.

The subsequent [pinned CLI source audit](retention_probe/source-audit.md) finds
a separate payload-bearing SQLite diagnostic path outside ephemeral thread
persistence. This is a source-level feasibility objection, not live evidence;
the transient capability remains unestablished. The proposed targeted probe was
superseded; no collector or live approval is currently requested.

ADP-03 stays `in_progress`. Deployment enforcement, API/UI changes and integrated
negative tests remain ADP-05/08 after their gates; this proposal does not make
those later tasks prerequisites for recording the design feasibility decision.
