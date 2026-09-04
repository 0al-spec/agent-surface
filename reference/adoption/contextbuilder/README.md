# ContextBuilder adoption experiment: preflight

Date: 2026-09-05. Status: existing-operation baseline executed; ASP integration
and human approval experiment remain unimplemented. No conformance or maturity
claim follows from this probe.

## Reproduction

Use a clean detached ContextBuilder worktree at
`567d5e39aecb83b9879a07cfab2c6f7062a98a20`. The original local checkout contains
uncommitted product changes and must not be used or cleaned by this experiment.
The probe checks the revision and clean worktree before importing trusted code.
The entire checkout and Python dependency environment must be trusted and not
modified concurrently. The revision check is a reproducibility guard, not
signature verification or an execution sandbox; checking selected import paths
does not authenticate transitive dependencies.

From the ASP repository, using its existing Python environment:

```sh
.venv/bin/python -B reference/adoption/contextbuilder/baseline.py \
  --checkout /absolute/path/to/clean-contextbuilder-worktree
```

The probe creates and removes its own temporary synthetic conversation. It
imports the existing `viewer.export.export_graph_nodes`, `viewer.graph` and
`viewer.workspace_io` implementation. No production conversation, running server,
browser session or application credential is used. This measures a direct
business operation; the HTTP authentication path is not exercised.

## Observed baseline

One synthetic conversation with one message produced HTTP-style result 200 and
five files: `.ctxb_export`, `nodes/adoption-synthetic/0000_message-1.md`,
`provenance.json`, `provenance.md`, and `root.hc`. Export does not produce a
single compiled Markdown artifact; that requires the separate compiler flow.
The initial retrospective's single-artifact assumption was incorrect.

On the first local run, read took approximately 0.31 ms and export 1.34 ms.
These are one warm-process sample, excluding environment setup/imports, and
are not adoption-time measurements or benchmarks.

| Probe | Observed outcome |
| --- | --- |
| Read synthetic graph | One node found. |
| Export | Five files produced by existing business logic. |
| Repeat identical request | Equal output bytes, but one directory deletion followed by rewriting. |
| Remove ownership sentinel and retry | Rejected with 500; existing files preserved. |
| Change source after a hypothetical preview | New source exported; the operation has no preview-binding argument. |
| Inject failure at the node Markdown write during re-export | Exception propagates; previous complete export is gone, only sentinel remains. |

These are characteristics of the selected local export function, not claims
that ContextBuilder advertised ASP guarantees and violated them. Its sentinel
is a coarse ownership marker and is preserved in the comparison; its existence
does not authenticate ownership, and a filesystem writer can create it. The probe
does not evaluate concurrent writers, process crashes, HTTP authentication,
user approval, model behavior or ASP receipts.

## Integration decision and next boundary

The existing export cannot simply be wrapped and advertised as the planned
preview/approval/idempotent commit. Source inspection and fault injection show
that replacement semantics require an application-owned transaction/recovery
boundary first. Ordinary equal-byte re-export is not exact ASP replay.

Preserve the existing directory replacement behavior for a fair baseline.
Before implementing authority objects, design a staged export with a durable
operation journal, application-owned source/destination revision checks,
coordination with every writer, and explicit recovery from failure during
publication. Reuse the current rendering functions. Do not call the existing
destructive export against the live destination during preview.

An alternative immutable-output operation would be a different product action
and must be measured separately; it must not silently replace the baseline.
The original 16-hour active-work ceiling remains in force. This preflight does
not establish that the transaction prerequisite or full integration fits it.

## Obligation map for the next implementation

The foundation bundle selects six role claims and 21 requirement entries in
[the canonical bundle registry](../../../conformance/v1/bundles.json).
That matrix is an entry point, not a complete list of normative MUST clauses.

| Area | Contract | Existing operation / required work |
| --- | --- | --- |
| Discovery and curated actions | [Surface Publisher](../../../drafts/modules/conformance.md#surface-publisher-profile) | Graph listing exists; define manifest and distinct read/preview/commit actions and their exact schemas. |
| Delegation | [Grant verification](../../../drafts/modules/authorization.md#grant-verification) | Application-local operator access is not an agent Grant; implement app-side verification of exact user/runtime/agent/Grant and surface bindings. |
| Preview and state drift | [Preconditions and Effect Preview](../../../drafts/modules/safe-effects.md#preconditions-and-effect-preview) | Preview must pin source and destination revisions, exact input and effects; final check and mutation of app-controlled state must be atomic. Current export rereads then removes output. |
| Approval | [Approval Semantics](../../../drafts/modules/safe-effects.md#approval-semantics) | Add actual user approval for exact action/input/preview/effects; a scripted boolean is not the human experiment. |
| Replay | [Idempotency](../../../drafts/modules/safe-effects.md#idempotency) | Persist execution/result identity and return it on exact retry; current rewrite does real work again. |
| Receipt and ambiguous outcome | [App Receipt](../../../drafts/modules/evidence.md#app-receipt) | Existing provenance describes content, not ASP execution evidence. Journal outcome and receipt linkage and reconcile after response loss. |
| Runtime and agent boundary | [Runtime Mediator](../../../drafts/modules/conformance.md#runtime-mediator-profile) | Keep credentials outside agent input, enforce admission limits and approval; select a transport and identity profile before claiming a complete implementation. |

No transport or identity profile has yet been selected. A source function call
in this baseline must not be presented as a conforming ASP transport. Completing
the obligation closure, including applicable approval features and runtime
limits, is a prerequisite to the authority-bearing implementation.

## Work log and remaining measurements

- Isolated the committed application source instead of touching its dirty
  product worktree; two Luna medium readers mapped export and ASP obligations.
- Added a disposable fault-injection probe and executed it successfully.
- Retained only synthetic outcomes; setup and investigation time were not
  continuously instrumented, so no reliable active-hour total is claimed.
- Not measured: ASP integration size/time, all seven planned ASP negative cases,
  user comprehension, second-developer reproduction, schema-change cost.

The [transaction/recovery design](transaction-boundary.md) records the next
implementation slice and its stop conditions. The
full adoption experiment has not passed or failed; the thin-wrapper approach
has failed this preflight.
