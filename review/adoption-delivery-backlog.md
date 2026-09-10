# Calcu adoption delivery backlog

Status: active, 2026-09-11. Owner: ASP/Calcu/SDK maintainers.

Current owner direction: [BYOA responsibility boundary and RFC compatibility audit](../reference/adoption/calcu/byoa-responsibility-decision.md).
The user accepts responsibility for the chosen agent implementation. The live
retention lane is stopped and the transient candidate withdrawn; this does not
waive current RFC requirements or complete ADP-03. The revised RFC explicitly
defines user-managed post-disclosure handling, retaining application-side
authority and stricter handling contracts. The gated
[Calcu contract design](../reference/adoption/calcu/user-managed-design.md) now
records the proposed source maximum, exact projection, consent binding and
implementation seams; it is not live migration or design approval.

The [RFC proposal](proposals/user-managed-retention.md) records the design and
acceptance inventory. The coordinated RFC revision now defines `user_managed`
and its schema/projection checks, not live Calcu support. ADP-03 still needs
review of the concrete application-side contract/consent design and route
applicability. Its prerequisite is design/feasibility approval, not a completed
ADP-08 implementation: actual-path enforcement tests are delivered with later
slices. ADP-02 retains the per-slice cost/acceptance gate below. Retention
investigation stays stopped.

This is the canonical task tracker for this bounded implementation lane, not
another RFC requirement backlog. `ADP-*` identifiers are delivery tasks, not RFC
card or GitHub issue numbers. [RFC cards](review-data.json) remain authoritative
for coverage and maturity; none are changed by this plan. The SDK's
[BC-01…08 inventory](https://github.com/0al-spec/agent-surface-js/blob/66644562e6f529f29c4d02a780fc69726314ecf0/docs/boundary-contract.md)
records the original extraction gaps, not a competing task lifecycle. The
[SDK architecture](https://github.com/0al-spec/agent-surface-js/blob/aab2c9ea1e586c5039bfafe5bd0ad26786ebdf35/docs/architecture.md)
owns component boundaries; the
[boundary contract](https://github.com/0al-spec/agent-surface-js/blob/aab2c9ea1e586c5039bfafe5bd0ad26786ebdf35/docs/boundary-contract.md)
owns implementation acceptance cases. Their SDK-first update is reviewed in
[SDK PR #3](https://github.com/0al-spec/agent-surface-js/pull/3); this backlog
alone owns ADP status and cross-repository sequencing.

Historical starting baseline: ASP `1783f50508b5498c8a24f60a758c4ce11868b294`.
Calcu SDK-consumer PR #3 was a separate prerequisite, now satisfied by its
merge; current merge evidence appears below. The implementation evidence and cost
assumptions are in the [contract walkthrough](../reference/adoption/calcu/contract-walkthrough.md).

## SDK-first delivery decision (2026-09-11)

Owner direction: preserve ASP's security guarantees and reduce repeated
application integration work through a modular, idiomatic SDK. The initial
security implementation can be substantial; every consumer should not have to
reimplement it. Calcu is the first integration/test consumer, not a prerequisite
complete handwritten implementation to extract only at the end.

This selects the delivery strategy, not every implementation, package, language
binding or production deployment. It does not close ADP-03, approve a new
conformance claim or change normative requirements. SDK-first cannot turn
incomplete Calcu records into accepted ASP contracts. Missing dependencies for
a selected security guarantee must fail closed, never become optional checks.

Measure two costs separately at each slice:

- **Reusable SDK engineering:** contract/state behavior, adapters, shared vectors
  and verification. The historical 13–25 developer-day estimate did not separate
  this investment from integration and remains low-confidence, not a new budget.
- **Consumer integration:** app-specific declaration/policy/handler code, setup
  steps, manual security decisions, integration tests and migration changes.
  Report actual effort separately from agent wall time and CI/review waits.

ADP-02's original **maximum two developer-day spike** is historical scope; its
transaction prototype is delivered, not a full crash/recovery implementation.
Before each live slice, record its bounded scope, prerequisites, budget/stop
conditions and exit evidence. The remaining decision is the scoped investment,
not whether the owner accepts security as ASP's priority. Use measured cost to
decide the next slice; do not require the whole migration's cost to be measured
before the first integration or approve all work from this documentation change.
A reduced RFC profile still needs a separate normative proposal naming the
lost guarantee.

| ID | Task / repository | Status | Dependency / exit evidence |
| --- | --- | --- | --- |
| ADP-01 | Correct identity evidence hash domain / Calcu | done | [Calcu PR #4](https://github.com/SoundBlaster/Calcu/pull/4) merged after #3 with green CI. RFC-domain independent vector, old-domain invocation rejected before engine, fresh executor/session isolation; restart and reissue guidance. |
| ADP-02 | Safety-state evidence and per-slice investment gate / ASP + SDK + Calcu | blocked | [ASP PR #81](https://github.com/0al-spec/agent-surface/pull/81) delivered the prototype and obligation matrix. SDK-first/security-first strategy is selected; bounded implementation scope, budget and stop/exit criteria still need approval. Separate SDK cost from app integration; no full-migration authorization. |
| ADP-03 | Data handling and provider applicability decision / Calcu + deployment owner | in_progress | User-selected agent implementation is the owner's responsibility; transient candidate withdrawn and live retention work stopped. Revised RFC defines explicit user_managed retention; actual Calcu support is not implemented. Classification/redaction, Grant projection, principal/disclosure, app-owned lifecycle and route applicability design remain open; no conformance claim or migration authorization. |
| ADP-04 | Offline example maintenance / ASP examples | done | ASP PR #81 merged: correct additive estimate, reject non-JSON tuple inputs, derive and test the stated 60-second lifetime. No live authority. |
| ADP-05 | Manifest/Grant behavior and consumer migration / JS SDK + Calcu | blocked | For live integration: ADP-01, ADP-03 design/feasibility approval and scoped ADP-02 approval. Implement validated contracts and issuer/runtime projection in SDK, then consume them in Calcu; no second handwritten complete implementation. Covers applicable BC-01…04/08; fresh consent and negative vectors required. |
| ADP-06 | Principal, consent and Grant management integration / SDK adapters + Calcu | blocked | Builds on ADP-05 contract sub-slices and ADP-03 policy; review together to avoid a completion cycle. Authenticated principal and consent policy stay app-owned; reusable preview/binding/revocation mechanics belong in SDK/adapters. No live switch before both tasks' applicable exit evidence. Browser never receives authority. |
| ADP-07 | Session/security state engine and transactional adapters / JS SDK + Calcu | blocked | Scoped ADP-02 approval and ADP-05/06 contract alignment. Reusable lifecycle/epoch/lineage transitions in SDK, first concrete transactional store plus Calcu integration; crash recovery/fencing and BC-05/06/07 checks. In-memory fixtures cannot satisfy durable obligations. |
| ADP-08 | Per-slice and composed boundary validation / SDK + Calcu | blocked | Add negative/integration tests within every ADP-05…07 slice, not only afterward. Final composed evidence needs ADP-03 design plus ADP-05/06/07: actual HTTPS, loss/retry/cancellation/restart/races, zero handler calls on admission rejection, no credential disclosure and split cost report. |
| ADP-09 | Stabilize modular SDK API and verify reuse / JS SDK + second consumer | blocked | SDK implementation starts inside ADP-05…07, not after this task. Stabilize demonstrated interfaces after ADP-08 evidence and check a second consumer before generality claims. Resolve BC gaps while preserving app policy/storage ownership/engine boundary. Linked to #75; no automatic maturity increase. |

### First vertical slice and later expansion

1. Explicitly review the SDK spec-lock/source coverage update against the selected
   RFC revision, then implement manifest/Grant/exposure values and negative
   vectors. Existing content hashing does not become complete manifest support.
2. Add issuer-derived `Grant.data_exposure` and independent runtime validation in
   SDK behavior. App policy and identity verification stay explicit trusted
   dependencies; never infer authority from a schema-valid value.
3. Integrate Calcu's action declaration and policy with those implementations;
   add exact principal/consent-preview binding and stale/changed-input rejection
   in the coordinated ADP-05/06 slice. Preserve the HTTPS admission path.
4. Collect per-slice ADP-08 evidence and split cost measurements. Unimplemented
   mandatory session/durability guarantees still block full conformance claims
   and live activation of the selected full contract.
5. Scope the next ADP-07 transactional state engine/storage slice from this
   evidence. Packaging stabilization, second consumer, broader frameworks and
   other languages follow demonstrated reuse, not speculative API commitments.

Pure value/fixture development is not live migration and need not wait for a
complete Calcu implementation; it still needs an explicitly scoped implementation
task and compatible source lock. No ADP task is marked done by this plan.

## Tracking rules

- `planned` means selected but not started; `in_progress` means bounded work is
  underway; `in_review` requires a PR and local evidence; `blocked` names a
  dependency or decision; `done` requires merged delivery and exit evidence.
- Prototype completion does not complete ADP-07, prove conformance, or resolve
  ADP-03. Provider policy cannot be inferred from `ephemeral` or process exit.
- Keep the historical spike bounded; SDK work belongs in the explicit vertical
  slices above, not expansion of that prototype into a generic framework.
  Track SDK effort and consumer effort separately; avoid new crypto/protocols.
- No `sqrt`, natural-language semantic verifier, receipts, production identity,
  Proof-Bound or new RFC features are authorized by these tasks.
- CI is reported after push; no merge or prolonged monitoring is implicit.

## Evidence ledger

- 2026-09-11: owner selected security-first, modular SDK-assisted adoption.
  Delivery order changes to SDK behavior + Calcu consumer + negative evidence
  per slice; public stabilization stays later. This is a planning decision,
  not implementation evidence, completed ADP gates or new conformance maturity.

- 2026-09-08: [owner decision and RFC audit](../reference/adoption/calcu/byoa-responsibility-decision.md)
  supersede the historical transient candidate and probe next steps below.
  No live run or authentication occurred. ASP PR #86 merged as `73c78fc`;
  PR #87 records static CLI evidence and the subsequent responsibility decision.
  No normative requirement is changed by this delivery.

- ASP PR #85 merged as `b6f750f`. ADP-03
  [retention probe preparation](../reference/adoption/calcu/retention_probe/README.md)
  supplies an isolated-run plan and tested offline observation interpreter.
  No live launcher/collector, authentication or runtime evidence is delivered;
  no-residue results cannot establish conformance. Other ADP-03 gates remain open.

- ASP PR #84 merged as `11f68c1` with green CI and no review threads. Its
  authority-boundary clarification is now normative; it does not close ADP-03.
- ADP-03 [handling policy proposal](../reference/adoption/calcu/handling-policy.md)
  records sensitive calculation/context classes, private status, a complete
  exposure fragment and event-bound app lifecycle. Policy review, known-source
  enforcement design, actual-path/CLI retention, principal and other feasibility
  gates remain open. No live migration, Calcu changes or provider claims.

- Calcu applicability finding: Privacy now distinguishes caller-supplied,
  application-held and derived data without new wire fields. Voluntary data
  disclosure does not grant resource authority; unknown hypothetical meaning
  does not mandate credential classification. Known sensitivity and handling
  obligations remain. This clarification does not close ADP-03 or authorize
  migration, and requires no extra Calcu privacy layer.

- ASP PR #83 merged as `c875ed0`; Calcu PR #5 merged as `a059d77`.
- ADP-03 [source exposure design](../reference/adoption/calcu/exposure-design.md)
  records one action/four operators, offline projection mechanics and negative
  acceptance cases. Live classification (including runtime-visible metadata)
  and all other handling gates remain open; this is not executable conformance.

- ADP-03: [data-handling worksheet](../reference/adoption/calcu/data-handling-worksheet.md).
- ADP-02: [safety-state experiment](../reference/adoption/calcu/safety_spike/README.md).
- ADP-01: Calcu `dd8d7d1`; `npm run check` (170 Vitest, 6 preflight,
  10 bundle checks), build, coverage and diff check passed. Independent review
  found no blockers. No live CLI smoke test was run.
- ADP-02/04: 14 SQLite prototype tests and 13 offline example tests passed;
  independent review findings corrected and rechecked. Full process-crash
  recovery remains ADP-07, not evidence claimed by the prototype.
- ADP-03 evidence worksheet is included in ASP PR #81; policy approval is not.
- Merge verified 2026-09-06: ASP #81 `9d559066ef744cee95194c63182f2235e7fc34ca`;
  Calcu #3 `71d994f` then rebased #4 `d483185825e637a7352dcbb2e3edabaac43807af`.
  CI green and unresolved review threads zero before each merge.
- ADP-03 now includes an authentication-route decision table based on official
  product documentation and the owner-reported personal ChatGPT route/task scope.
  Actual provider settings remain unverified; no live workload or credential
  inspection was performed. This decision is not a conformance claim.
- ASP PR #82 merged as `c99e35d`; owner preferences are recorded in `main`.
- ADP-03 selected a concrete candidate: `transient` with
  `delete_on_grant_end: true` for runtime/agent action-output copies, distinct
  from application UI display. Calcu fake-process cleanup/diagnostic tests
  provide partial evidence; actual CLI retention and outstanding references
  remain a feasibility gate, not a new privacy preference. See the worksheet's
  concrete-retention section and companion
  [Calcu PR #5](https://github.com/SoundBlaster/Calcu/pull/5), commit `3bb1d5c`.
- ADP-07/08 follow-up inventory: executor Grant/identity Map minimization and
  UI unmount cancellation need scoped design/tests; neither is silently fixed
  or covered by the current fake-process retention experiment.
