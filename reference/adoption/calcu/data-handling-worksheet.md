# ADP-03: Calcu data-handling evidence and decision worksheet

Current contract candidate and remaining design decisions:
[user-managed handling design](user-managed-design.md). RFC PR #89 resolved
the missing-mode gap, not Calcu's implementation or the other ADP-03 gates.
The baseline requirements and transient feasibility sections below are historical.

> Current direction (2026-09-08): see the
> [BYOA responsibility decision](byoa-responsibility-decision.md). Its owner
> decision supersedes this worksheet's transient candidate and proposed live
> retention work, not the RFC requirements recorded below. Agent-internal
> retention investigation is stopped; normative compatibility and remaining
> application-side design gates keep ADP-03 open.

Status: owner preferences recorded; **ASP handling contract not yet verified**
(2026-09-06).
Inspected Calcu SDK-consumer revision `5e5a23f04bad649a23eedaad4f83126b2ec3ff7e`.
The boundary findings below were rechecked against merged Calcu
`d483185825e637a7352dcbb2e3edabaac43807af`.
This is a deployment decision record, not an ASP consent receipt, provider
attestation or authorization to migrate live.

## Owner decision

The owner confirmed personal ChatGPT subscription login (not API-key access or
a managed workspace) and declined a synthetic-only restriction. The experiment
may accept arbitrary lawful tasks subject to provider rules. No additional
provider-retention requirement was requested. The subscription tier is not a
capability attestation and need not be recorded as an account identifier here.

This resolves those preference questions; do not ask the owner to approve a
synthetic-only scope again. It does not classify arbitrary tasks or numeric
results as public, authorize third-party data disclosure, establish provider
retention/training settings, or waive mandatory ASP requirements. Calcu still
exposes only four arithmetic operations; task content does not expand authority.

No new task classifier, history/export feature, provider switch or live workload
is introduced by this decision. Existing disclosure of provider submission and
server-only credential isolation remain part of the intended boundary.

## Observed paths

Paths below are relative to the Calcu repository. They identify implementation
evidence, not contractual promises by the CLI, provider or operating system.

| Data | Path / code evidence | Observed control | Remaining owner/evidence |
| --- | --- | --- | --- |
| User task | `src/features/agent-task/AgentTaskPanel.tsx`, `server/taskHost.ts` | React snapshot; same-origin task POST; bounded body; no application history/persistence API found | Deployment owner defines task retention separately from application-output exposure. Browser/OS capture is unverified. |
| Task sent to model | `server/codexAdapter.ts` thread/turn startup | Fresh CLI process, temporary working directory, `ephemeral: true`, allowlisted environment | CLI/account/provider retention and processing capabilities are unknown. Local CLI is not local inference. |
| Protocol stdout / stderr | `server/codexAdapter.ts`, `server/demo.ts` | Bounded in-memory protocol; normal stderr discarded; optional debug diagnostics go to process stderr | Deployment owns stderr sink, logging, crash dumps and proxy policy; debug output requires separate inventory. |
| Operands / application output | `server/localBackend.ts`, `server/executor.ts`, adapter tool response | Closed calculator input; independent engine execution; result returns through mediator to model | Classify output before delivery; establish enforceable runtime retention and redaction. Model/provider downstream storage is not established. |
| Result, task, trace and prose | `AgentTaskPanel.tsx`, `src/features/agent-task/protocol.ts` | Bounded stream; separate verified action/unverified prose; React state, no app persistence found | Browser extensions, devtools, session capture and future exports/history are outside this evidence. |
| Temporary directory | `server/codexAdapter.ts` cleanup | Process-group termination and recursive per-task directory removal | This does not establish erasure from filesystem journals, backups, CLI caches or files outside that directory. |
| Grant/session/credential | `server/demo.ts`, `server/executor.ts` | Per-task issuance/revocation; in-memory server ownership; not in browser/model payload | No durable deletion or audit claim; implementation remains a development demonstration. |

## Applicable distinctions

The Privacy module's authority-boundary clarification distinguishes current
caller input, application-held resources and derived output. Supplying a value
to an agent grants no resource access. Classification uses known provenance and
context, not a guess that arbitrary digits might encode a secret. Known
sensitivity and base handling remain applicable; Calcu needs no new semantic
classifier or opaque-reference interface to express that distinction.

[Data Exposure Contract](../../../drafts/modules/privacy.md) requires explicit
application source exposure and derived Grant projection. Action-output
retention does not define retention of the user's task or agent-supplied input.
Application redaction occurs before release, not after a provider receives data.
Base runtime/agent retention is not a whole-provider-path guarantee; that needs
the separately applicable Remote Processing Privacy obligations.

Consequently, no application persistence observed is **not** evidence of
provider-wide `transient` handling. Neither process exit nor `ephemeral` proves
deletion. No provider account/settings were inspected in this pass.

## Remaining handling design before ADP-05

The [proposed handling policy](handling-policy.md) supplies a concrete class
maximum, redaction/retention fragment, copy lifecycle and disclosure draft for
review. These are design proposals, not deployed controls or closure evidence.
Its exit table tracks the remaining feasibility and policy-review work below.

The following require a proposed implementation contract and capability evidence,
not another general privacy-preference questionnaire or defaults invented by
the SDK:

1. Task, operand, output and trace classification; application redaction rules.
2. Confirm the selected path matches the owner-reported personal ChatGPT login;
   inventory extra provider/proxy hops only when they participate in that path.
3. Separate task-input and application-output retention periods, deletion owner
   and evidence; include diagnostic, proxy, history, backup and crash channels.
4. Whether whole-path remote-processing restrictions apply and can be enforced;
   reject unsupported restrictions before releasing application data.
5. Principal/tenant ownership, disclosure and consent wording; no multi-user
   deployment implied by the single-user demo.
6. UI display lifecycle and whether export/history is permitted (not added here).

ADP-03 owns this design and feasibility decision, not implementation of the
later tasks. Its closure permits ADP-05 planning only after the independent
ADP-02 gate; deployed enforcement and passing integration tests belong to
ADP-05/08 before conforming live use. No dependency on completing those tasks
is added as a prerequisite for closing ADP-03.
The existing demo is not reclassified as conforming and is not changed by this
worksheet. See the [delivery backlog](../../../review/adoption-delivery-backlog.md).

## Applicable obligations and bounded follow-up

These are obligations from the existing [Privacy module](../../../drafts/modules/privacy.md),
not new RFC requirements. The base contract covers application-originated
output, including echoed operands and structured errors. It does not itself
define application retention of the user task or agent-supplied input.

| Area | Applicability to this decision | Required implementation / evidence |
| --- | --- | --- |
| Source classification and redaction | Mandatory base contract, even for a non-persisted proposal | Explicit action `data_exposure`; conservative source classes for result/echoed operands/errors. `redaction.mode: none` is allowed if that unredacted envelope is declared. No natural-language classifier is required. |
| Runtime/agent retention | Mandatory base contract; independent of extra provider preferences | Choose and enforce `transient` or bounded positive lifetime with required `delete_on_grant_end`. Inventory runtime-controlled copies in context, caches, diagnostics and logs; an ephemeral flag is not enough evidence. |
| Grant exposure projection | Mandatory base contract | Issuer derives full source closure; runtime recomputes from the pinned manifest and rejects missing, extra or changed projection before use. Hash the complete projection. |
| UI and task-input ownership | Must be distinguished from action-output retention | Define which component owns displayed copies and their lifecycle. Task-text acceptance is not proof of permission to disclose another person's data; no new export/history behavior is approved here. |
| Remote Processing Privacy | Optional; not selected for this follow-up because no extra whole-path restriction is requested | No locality/ceiling guarantee is advertised. This omission does not waive base runtime-agent enforcement or prove downstream deletion. Revisit if a later selected bundle/profile requires it. |
| Agent Training Use Policy | Optional; no new secondary-use permission or prohibition specified here | Leave unspecified; do not infer no training or permission for training from the subscription, task scope or retention declaration. |

### Acceptance checks to carry into implementation

1. A selected action always contributes its declared exposure to the Grant;
   result and structured-error paths stay inside the same maximum envelope.
2. Missing/changed source projections fail with `integrity_mismatch` before
   dispatch; wider payload delivery fails with `data_exposure_violation` without
   echoing offending values into logs/errors.
3. The chosen runtime/agent retention contract has tests for its actual owned
   copies and deletion triggers. An unsupported path refuses the Grant before
   disclosure. Scope these tests to owned components; do not claim provider
   erasure or model unlearning from local deletion.
4. Prompt input and app-generated result are tracked separately; arithmetic
   shape does not silently relabel payloads as public. No task semantic verifier
   or extra arithmetic capability is introduced.
5. Existing browser/model credential-isolation tests continue passing. The UI
   disclosure continues to describe remote submission without a no-retention or
   no-training promise.

The next technical step is to map the selected Codex adapter's runtime/agent
boundary and owned plaintext copies to one concrete base retention contract.
Unknown third-party retention alone is not grounds to demand an unselected
whole-path profile; unknown ability to meet the selected base contract is a
real blocker. Keep those two findings separate. Full live migration also still
depends on the independent ADP-02 cost decision.

### Current implementation gap, not a new user preference

At the rechecked Calcu revision, `server/executor.ts` has an abbreviated
`SurfaceSnapshot` and Grant model with no `data_exposure`, retention declaration
or derived exposure projection. `server/localBackend.ts` checks result
correlation, not a manifest-derived exposure contract. Temporary-directory
cleanup and `Cache-Control: no-store` are useful controls, not that contract.

The existing `AgentTaskPanel.tsx` disclosure and server credential isolation
should be preserved, not replaced with promises about provider deletion.
Free-form task input already has no synthetic-only filter; there is no reason
to add one. The agent report's absence of observed app persistence is only
code-mapping evidence, not a passing retention conformance result.

Carry the contract/projection implementation into ADP-05 (BC-02/04) after its
gates, with base-path enforcement evidence and integrated tests in ADP-08.
ADP-03 remains in progress until that concrete handling design and its
enforcement feasibility are recorded. The preference part is resolved; neither
this record nor the owner's tolerance removes the implementation gap.

## Authentication-dependent policy evidence (2026-09-06)

The official [Codex authentication documentation](https://developers.openai.com/codex/auth/)
distinguishes ChatGPT subscription login from API-key access: the applicable
workspace controls or API organization data settings depend on that choice.
It also allows custom providers/proxies. These are product capabilities, not
evidence of this deployment's effective settings. Current documentation is not
proof that every control is supported by the demo's pinned CLI version.

| Selected route | Evidence needed from the owner | Do not infer |
| --- | --- | --- |
| Personal ChatGPT login | Account category, applicable data controls and documented handling of task/tool output | Enterprise retention, API retention or no training from the word Codex |
| Managed ChatGPT workspace | Workspace category and administrator-confirmed applicable retention/processing controls | That an available enterprise control is enabled for this workspace |
| API key | Effective organization/project data-sharing and retention controls, actual endpoint/provider path | Zero retention from API authentication or ephemeral thread creation |
| Custom provider or proxy | Each additional processor/logging hop and its applicable policy | That OpenAI account settings govern an independent proxy or provider |

No authentication file, account identifier, API key, token or workspace secret
is needed in this public record. The owner can report just the route and policy
categories; sensitive deployment evidence should stay outside the repository.

### Decision boundary

The login route and lack of a synthetic-only restriction are now owner-reported
decisions, not unanswered questions. Do not reinterpret "no additional provider
restriction" as `retention: unlimited`, a provider deletion guarantee or an ASP
wire value. Required handling constraints still need an enforceable contract.
If that contract cannot be met, report the exact failing obligation instead of
silently changing the Grant, replacing the provider or adding a new RFC profile.

## Concrete retention candidate and measured limit

The subsequent [source exposure design](exposure-design.md) maps the single
`calculation.propose` action (four operators), runtime-visible output and offline
Grant projection. It does not settle live classification or the remaining gates.

The next bounded experiment selected the candidate action-output retention
`{"mode":"transient","delete_on_grant_end":true}`. It is not yet advertised
by the Calcu manifest/Grant. Application-owned display state is separate from
runtime/agent plaintext: grant revocation must not be confused with deleting
the user's calculator result. Task input has its own application policy.

The companion [Calcu PR #5](https://github.com/SoundBlaster/Calcu/pull/5)
records the copy owners in `server/RETENTION.md` and seven new
fake-process tests. Four check adapter temporary-directory cleanup after
success/failure/timeout/cancel; three exposed actual diagnostic leakage through
CLI-controlled IDs/methods/error text/status. The fix restricts diagnostics to
fixed stages/status and classified error codes. These are observed local
controls, not proof of a real CLI or provider's retention behavior.

One remaining retention feasibility question is whether the pinned
CLI agent's local context/rollout/cache/diagnostic behavior and the adapter's
outstanding-reference lifecycle can satisfy the chosen base contract. The fake
process cannot answer this. Do not replace that question with an enterprise
subscription requirement, provider-wide deletion guarantee or synthetic-only
product scope. No live CLI request or credential-store inspection was made.

Passing that check alone does not close ADP-03 or unblock ADP-05. All items in
[Remaining handling design before ADP-05](#remaining-handling-design-before-adp-05)
remain open: source classification/redaction, selected-path evidence and
applicable restrictions, separate task-input/output retention and deletion
ownership, principal/tenant ownership and disclosure, and UI display/export/
history lifecycle. The mandatory manifest-derived Grant exposure projection
design and its feasibility also remain unresolved, as recorded in the
[delivery backlog](../../../review/adoption-delivery-backlog.md). The candidate
and fake-process tests do not resolve these design gates. ADP-03 closure requires
the complete handling design and feasibility evidence; deployed implementation
and integration remain ADP-05/08, and the independent ADP-02 decision still gates
ADP-05.

Executor Grant/identity-record cleanup and UI unmount cancellation were noted
as separate lifecycle debt. They are not evidence that calculator outputs are
durably stored, and must not be solved by deleting authority records blindly.
