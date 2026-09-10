# Calcu: mode fit and one-action applicability

Date: 2026-09-06. Status: non-normative implementation decision and planning
checklist, not a new profile, conformance report, or exemption from the RFC.
This follows [implementation feedback](implementation-feedback.md), especially
IF-05 and IF-07, using the same pinned Calcu and RFC sources. No runtime changes
or new test results are implied.

## Decision: keep a non-persisted calculation proposal

Keep `calculation.propose` in `propose` mode. Interpret its output as a
non-committed calculation artifact: `{operator, left, right, result}`. The
[current application adapter](https://github.com/SoundBlaster/Calcu/blob/5e5a23f/server/calcu.ts)
evaluates the supplied operands and returns this object; it does not apply it
to the calculator's reducer, display, saved history, or another domain object.
This fits the "other non-committed artifact" language in
[Proposal-Only Surface Mode](../../../drafts/modules/core.md#proposal-only-surface-mode).
It is an explicit interpretation for this action, not a claim that every pure
function is a proposal or that a returned number requires a future commit.

| Existing mode | Fit for this action |
| --- | --- |
| `propose` | Selected: produce a non-persisted calculation artifact without applying it to application state. |
| `read` | Describes reading application state. This action accepts caller-supplied operands; do not invent a stored object merely to fit that description. A future action reading calculator history would be a different case. |
| `dry_run` | Not selected: it validates a possible later commit. Calcu has no such stage, and proposal-only explicitly excludes this mode. |

The [static mode rules](../../../drafts/modules/safe-effects.md#static-execution-modes)
remain unchanged. Keep four operators (`add`, `subtract`, `multiply`, `divide`),
`side_effect: false`, no `effects`, no state-changing companions, and
`execution.persisted: false` or omitted. The complete example must declare a
stable `execution.operation_id`; the operation family is not authority.
Both the semantic Grant request and authoritative Grant must contain exactly
`constraints.credential_release: {"mode":"deny"}`.

The task `sqrt(111) * 2` can still produce an admitted `multiply(111, 2)` action
and `222`. The artifact proves neither that the root was computed nor that the
natural-language task was understood. Keep the requested text, verified
application action, and unverified agent explanation visibly separate. No new
`compute` mode, `sqrt`, intent verifier, task hash, or fake commit companion is
needed for this decision.

## Selected deployment and limits of the checklist

Target the existing
[Mediated Proposal bundle](../../../drafts/modules/conformance.md#adoption-oriented-conformance-bundles):
Surface Publisher, Grant Issuer, Action Executor, Runtime Mediator, Agent Adapter.
These are five responsibilities, not five services. The
[bundle registry](../../../conformance/v1/bundles.json) supplies executable
coverage targets; its selected requirements/vectors are not an exhaustive list
of every normative obligation of the roles.

Keep Compatibility Bearer over authenticated loopback HTTPS as a development
deployment, not Proof-Bound or production certification. Ephemeral development
identity describes the adapter under its configured trust policy; it does not
attest the Codex binary. The following is a planning checklist grouped by
obligation, not a declaration that the current Calcu fulfills these roles.
Items marked partial or missing remain blockers to that claim.

## Required now

| Obligation and owner | Current Calcu evidence / next acceptance condition |
| --- | --- |
| **Full manifest and discovery — publisher + mediator.** Pin the complete manifest, schemas, version/hash, action mode, operation family, risk, exposure and authenticated endpoints; verify the proposal-only invariant independently. | Partial: the abbreviated private snapshot is not the full wire manifest. Replace it with a complete example; unknown action, changed mode or changed snapshot must fail before application execution. See IF-01. |
| **Exact consent and Grant — issuer + mediator.** Authenticate the principal, confirm the exact request, retain the authoritative Grant, and compare returned authority with the confirmed projection. | Missing complete flow: trusted demo provisioning is not evidence of issuer-side consent or the Consent Preview Contract. A task Submit button alone is insufficient. |
| **Verified identity and its complete projection — issuer + mediator + executor.** Verify selected evidence profiles/status and preserve the required exact copies in the Grant/credential contract. | Partial: a verified development fixture is useful evidence, but a digest-only credential projection is not the full required projection. Reject substitutions and unsupported/unavailable verification rather than accepting an agent identifier. See IF-03. |
| **Independent admission — executor.** Verify current credential, Grant, surface, complete subject/delegate/audience/session tuple, generation, action/mode and closed input schema before the engine runs. | Existing bounded negative tests support parts of this boundary, not full RFC conformance. Repeat them against the complete contract after migration; malformed or unauthorized requests must not reach the engine. |
| **Endpoint trust — publisher + mediator + deployment.** Establish the trusted mapping from the pinned logical audience and manifest to the actual HTTPS endpoint; authenticate TLS and contain credentials. | Partial: loopback TLS tests do not explain the logical `calcu.local` audience versus a random-port endpoint. Document and test the explicit trusted mapping; an arbitrary localhost URL is not discovery. See IF-04. |
| **Session lifecycle and control — application + mediator.** Preserve authoritative state/generation and implement the authenticated session-control contract, including runaway fencing and exact recovery transitions. | Missing full contract: completion-time revoke and rotate-then-revoke do not implement pause/resume. `session_control_url` is required because Calcu accepts a Runtime participant, regardless of whether its UI offers Resume. See the [endpoint trigger](../../../drafts/modules/core.md#endpoints) and [lifecycle](../../../drafts/modules/authorization.md#session-authority-and-lifecycle). |
| **Durable runaway guards — mediator.** Initialize guards before scheduling; retain finite counts and fences across the required epoch/lineage transitions; fail closed on unavailable state. | Missing: one successful tool call, a timeout and process-per-task isolation are useful local limits, not evidence of durable guards. Test restart, new session/renewal and unresolved-fence behavior against [Runtime Runaway Protection](../../../drafts/modules/safe-effects.md#runtime-runaway-protection). |
| **Revocation and management — issuer + application + mediator.** Expose authenticated active-Grant management/revocation and a trusted management link; stop use on expiry, revocation or uncertain confirmation. | Partial: local revoke exists, but does not establish the complete [Active Grant Management](../../../drafts/modules/authorization.md#active-grant-management) boundary or user-visible runtime Grant view. |
| **Base data exposure — publisher + issuer + mediator.** Classify sources, derive the exact Grant projection and enforce redaction/retention for every selected path. | Missing complete policy: classify application output/errors separately from user task input; assign enforcement for runtime, UI, logs and provider copies. `ephemeral` does not prove provider deletion. See IF-06 and [Data Exposure Contract](../../../drafts/modules/privacy.md#data-exposure-contract). |
| **Mediation, validation and local audit — mediator + adapter.** Keep raw authority out of model/browser context, validate the pinned wire input/output and correlation, record required session/generation/trace audit context, and reject unsupported behavior. | Partial: current adapter and transport tests are useful but narrower than the [Runtime Mediator role](../../../drafts/modules/conformance.md#runtime-mediator-profile). Hashing support alone does not implement input projections or audit. Agent prose remains presentation, never an authorization or intent-correctness decision. |

This table exposes a real adoption-cost question: the current selected role
requires durable runtime safety even for one non-persisted action. Neither a
small surface nor a fresh Grant per task creates an exception. If that cost is
unacceptable, propose a separate profile change naming the removed guarantee;
do not quietly relabel the demo conforming.

## Conditional mechanisms and deliberately unselected features

| Mechanism | Applicability for this candidate |
| --- | --- |
| Grant budgets and capacity accounting | Do not select `constraints.budgets` in the candidate until its accounting owners are implemented. Under [Budget Caveats and Accounting](../../../drafts/modules/authorization.md#budget-caveats-and-accounting), an absent dimension is uncapped by that profile, not zero. Adding any dimension requires its authoritative durable accounting and associated control behavior. This does **not** remove independent runaway guards or local cost limits; Calcu's private quota is not a normative budget claim. |
| Persisted-proposal idempotency | Not triggered by the chosen non-persisted artifact. [Idempotency](../../../drafts/modules/safe-effects.md#idempotency) becomes mandatory for persisted proposals or state-changing actions; selecting `idempotency: required` brings the pinned normalization requirements. No exact-once or "timeout means not executed" claim follows from omission. |
| State-changing lifecycle | No reserve/commit/compensate/revert, target mutation, external operation or transferable authority. Their preview/effect/recovery obligations are not implemented by calling an arithmetic result a proposal. Adding such behavior needs a different action contract and reassessment of the surface. |
| Per-action human approval and Approval Receipts | Do not select approval-receipt production or a per-action approval requirement for this candidate unless app/user policy requires it. Issuance consent and local policy still apply; removing an approval dialog does not remove those duties. |
| App/runtime Receipt Producer roles | Not selected. The state-changing-action receipt trigger is absent, and no additional receipt requirement is selected. If action, Grant or audit policy requires receipts, implement the corresponding producer obligations before claiming support. Local audit remains required; returned arithmetic is not a signed receipt. |
| Domain events and automation | No domain event surface or subscriptions in this example. Reassess delivery/replay/CloudEvents requirements before selecting them. [Budget Control Events](../../../drafts/modules/core.md#budget-control-events) have their own endpoint/budget triggers; omitting domain events does not waive required session control or durable scheduling guards. |
| OAuth, Proof-Bound, remote-processing/training-use and other optional bindings/profiles | Not selected by this development path. Reject requirements the deployment cannot satisfy rather than silently falling back. Optional profile omission does not waive base identity, exposure, credential containment or secure transport, and makes no claim about provider training or retention. |

These decisions scope the proposed example; they do not retrospectively change
Calcu's current manifests, grants or policies. If a complete example selects a
conditional feature, update this checklist and its acceptance tests together.
Any apparent conflict between this summary and normative role prose must be
resolved against the RFC, not treated as an exemption supplied by this document.

## Next bounded delivery

The [offline contract walkthrough](contract-walkthrough.md) materializes the
selected objects and records endpoint, consent, data-flow and safety-cost
decisions. Its synthetic identity and unresolved retention leave live use
explicitly blocked; it does not complete the following implementation work.

Prepare one complete manifest/Grant/session example and a small data-flow
worksheet before extracting additional SDK types. Resolve three explicit
choices: trusted endpoint provisioning, enforceable exposure/retention, and the
implementation plan/cost for mandatory session control and durable guards.
Show the exact confirmed consent and identity projections, not placeholder
promises. A changed manifest requires a new surface hash and fresh issuance.

The example is ready for implementation planning when every required row has
an owner, concrete acceptance cases and an estimated cost. It is not ready for
a conformance claim until those cases and the selected role requirements have
been implemented and checked. If safety-state cost dominates the calculator,
bring back a narrow continue/simplify/change-example decision rather than
automatically expanding Calcu or weakening the RFC.
