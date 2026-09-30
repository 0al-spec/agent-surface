# Application exposure: Calcu and Memos

Status: non-normative application design decision, recorded 2026-09-30 UTC.
The owner selected refinement of Calcu's disclosure description while keeping
ASP generic. This does not close ADP-03 or authorize live migration; the
[delivery backlog](../../review/adoption-delivery-backlog.md) controls task status.

## Two user stories

A user asks Calcu to multiply 240 by 0.15. The model receives the operator,
both operands and result, 36. The local mediator first receives a larger
response with session/request bindings, execution information and a receipt.
The disclosure description must cover that larger response too: removing
fields before forwarding to the model does not undo disclosure to the mediator.

A user asks the Memos prototype to create a private note. The agent supplies
the note text, which the user reviews before creation. The runtime receives
an application result and receipt; the tool message forwarded to the model
confirms creation and names the note identifier. It does not return the body.
A future read-note feature would expose a separate source and require its own
access and disclosure contract.

Both use the existing ASP source-closure, exact-copy, consent and hashing rules.
Business operations, field classifications and class identifiers are chosen by
each application.

## Calcu: observed output and selected design

Inspected code: Calcu `3b226b0` (`origin/main`), paths `server/manifest.ts`,
`server/executor.ts`, `server/localBackend.ts`, `server/codexAdapter.ts` and
`server/taskHost.ts`. This is static code evidence, not a live-path test.

| Situation | Actual boundary output | Current declaration | Selected design / follow-up |
| --- | --- | --- | --- |
| Calculate 240 × 0.15 | Model receives `operator`, `left`, `right`, `result`; UI trace repeats operands | One `application.result` class classified `private` | Calcu-local `calculation.content`, conservatively `sensitive`, covers operands, result and repeated representations |
| Receive a successful response | Mediator receives binding/correlation fields, execution information and a receipt before shortening the model response | No separate class identifies this envelope | Calcu-local `calculation.runtime_context` covers the complete runtime-visible envelope; review receipt fields as well as session/Grant/hash/trace fields |
| Reject a request or report failure | HTTPS has a closed action error; UI has allowlisted task codes; rejected tool calls can return fixed `Request rejected` text | Errors/status are not explicitly identified by the class description | Calcu-local `calculation.status` covers permitted discriminants, action identifiers and codes; keep raw diagnostics, secret values and input echoes out of error paths |
| Submit user task text | Adapter sends user input to the selected agent/provider | UI discloses remote submission | Record input ownership separately; action-output exposure does not define application retention of this input |
| Cancel or end a task | Authority settlement and app-owned copy/display cleanup follow separate lifecycles | Action selects `user_managed` | Explain that revocation stops future access, not recall of disclosed copies; review app-owned lifecycle separately |

The three classes are a selected Calcu design for implementation review, not
standard ASP vocabulary. An application may use one class or many. The complete
success/error/receipt envelope must fit the declared maximum when redaction is
`none`. Protected data added later needs separately authorized access and
preservation of its known source obligations before delivery.

`retention: {"mode":"user_managed"}` makes no ASP deletion promise for
runtime/agent copies. The user chooses the agent implementation; application
access checks, credential containment and stricter applicable policies still
apply.

Calcu's existing issuer derives exposure from the prepared semantic request,
includes it in the complete Grant hash and validates the selected Grant against
the manifest. That checks representation under the current declaration; it
does not establish complete field coverage, consent or host qualification.

The selected SDK manifest includes the proposal action and `grant.revoked`.
The control event needs an explicit projection entry even with empty classes;
its own handling declaration is preserved rather than replaced by the action's
`user_managed` mode.

## Applying the same rules to Memos

Inspected local `server/aspdemo` prototype: `service.go` and `codex_runtime.go`,
in a checkout based on upstream `2b2192d4e153bd04f1d325b60fd880cf00d68b01`.
These prototype files are local additions; the upstream commit does not pin
or establish their behavior. Observations are static code evidence.

| Situation | Application-originated output to describe | Access implication |
| --- | --- | --- |
| Current `memo.create_private` prototype | Created-note identifier, `PRIVATE` visibility, creator identifier (`created_by`), complete returned receipt and runtime-visible response fields; model gets a shorter confirmation | Creation does not grant reading existing notes, listing history or deletion |
| Hypothetical read-selected-note feature | Authorized note content and metadata, including errors and partial results | Select permitted note resources independently of create authority |
| Failure or uncertain creation | Fixed error/outcome information and any returned receipt | Failure cannot expose other notes or widen authority |

Memos `PRIVATE` visibility is an application access setting, not evidence of
an ASP classification or retention promise. Memos must select defensible output
classes from known provenance independently of Calcu names. This comparison
does not select a Memos handling mode or qualify prototype exposure behavior.

The current JS SDK supports a narrow non-persisted proposal manifest. Memos
creation is a state-changing commit with additional execution, approval,
receipt and recovery requirements. Rejection by that SDK subset is a support
limit. The generic exposure rule applies to both action types; this comparison
does not demonstrate full Memos support or interoperability.

## Ownership and next delivery

| Owner | Responsibility |
| --- | --- |
| ASP | Existing source kinds, closure/ordering, exact-copy checks, consent/hash binding and disclosure obligations |
| SDK | Validate supported declarations, derive source entries and independently verify returned entries without business-name heuristics |
| Application | Curate actions/resources, classify complete output, enforce pre-delivery policy and bind ordinary-user consent through its trusted host |
| Agent owner | Choose and operate the agent under the accepted handling contract and applicable policies |

Next Calcu slice: map the selected maximum to every actual success/error/receipt
field, update declaration and safe consent view together, and reject stale
surface/Grant/consent bindings. Check extra output fields and changed exposure
entries with focused negative cases. Record SDK and application work separately.
Principal/preview binding, app-owned lifecycle, route applicability and ADP-02
remain open gates. No new wire fields or mandatory business-class taxonomy is
needed for this decision.

References: [Data Exposure Contract](../../drafts/modules/privacy.md#data-exposure-contract),
[Calcu handling design](calcu/user-managed-design.md) and
[source exposure history](calcu/exposure-design.md).
