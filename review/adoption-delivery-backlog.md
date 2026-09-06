# Calcu adoption delivery backlog

Status: active, 2026-09-06. Owner: ASP/Calcu maintainers.

This is the canonical task tracker for this bounded implementation lane, not
another RFC requirement backlog. `ADP-*` identifiers are delivery tasks, not RFC
card or GitHub issue numbers. [RFC cards](review-data.json) remain authoritative
for coverage and maturity; none are changed by this plan. The SDK's
[BC-01…08 inventory](https://github.com/0al-spec/agent-surface-js/blob/66644562e6f529f29c4d02a780fc69726314ecf0/docs/boundary-contract.md)
records extraction gaps, not a competing task lifecycle.

Historical starting baseline: ASP `1783f50508b5498c8a24f60a758c4ce11868b294`.
Calcu SDK-consumer PR #3 was a separate prerequisite, now satisfied by its
merge; current merge evidence appears below. The implementation evidence and cost
assumptions are in the [contract walkthrough](../reference/adoption/calcu/contract-walkthrough.md).

## First delivery and decision gate

Start ADP-01…04 in bounded scopes. ADP-02 has a **maximum two developer-day
timebox**, not a commitment to implement the complete safety model. Review its
measured work, missing obligations and integration cost before authorizing
ADP-05…09. A passing prototype is not that authorization.

Choose explicitly: continue the full contract, simplify the example without
weakening mandatory guarantees, or change the adoption example. A reduced RFC
profile would require a separate approved normative task.

| ID | Task / repository | Status | Dependency / exit evidence |
| --- | --- | --- | --- |
| ADP-01 | Correct identity evidence hash domain / Calcu | done | [Calcu PR #4](https://github.com/SoundBlaster/Calcu/pull/4) merged after #3 with green CI. RFC-domain independent vector, old-domain invocation rejected before engine, fresh executor/session isolation; restart and reissue guidance. |
| ADP-02 | Bounded durable safety-state spike / ASP examples | blocked | [ASP PR #81](https://github.com/0al-spec/agent-surface/pull/81) merged with green CI: prototype and obligation matrix delivered, including persisted Grant/lineage binding. Owner cost/limitations decision remains open; full migration is not authorized by merge. |
| ADP-03 | Data handling and provider applicability decision / Calcu + deployment owner | in_progress | Owner selected personal ChatGPT login, declined synthetic-only scope and requested no extra provider-retention constraint. Remaining work is mandatory source classification, runtime/agent retention, Grant projection and applicable-path evidence, not another generic privacy preference. Unknown capabilities remain unknown. |
| ADP-04 | Offline example maintenance / ASP examples | done | ASP PR #81 merged: correct additive estimate, reject non-JSON tuple inputs, derive and test the stated 60-second lifetime. No live authority. |
| ADP-05 | Complete Manifest/Grant migration / Calcu | blocked | ADP-01, resolved ADP-03 and explicit ADP-02 continue decision. Closed manifest/discovery/schema and identity/Grant projections; fresh consent on changed snapshot; negative vectors. Covers applicable BC-01…04/08 gaps, not all RFC profiles. |
| ADP-06 | Principal, consent and Grant management / Calcu | blocked | ADP-05 and ADP-03 policy. Authenticated principal, exact preview/issued projection comparison, stale preview rejection and authoritative revocation confirmation. Browser never receives authority. |
| ADP-07 | Session control and durable runtime guards / Calcu | blocked | ADP-02 decision and ADP-05; share exact authorization contract with ADP-06. Implement complete applicable lifecycle/epoch/lineage obligations, crash recovery and fencing, not just the spike subset. Resolve BC-05/06/07 lifecycle, raw JSON/structural comparison and error mapping gaps. |
| ADP-08 | Integrated boundary validation / Calcu | blocked | ADP-03/05/06/07. Actual HTTPS path, loss/retry/cancellation/restart/race cases, zero engine execution for rejected calls, no credential disclosure. Produce obligation-to-test report and measured adoption cost. |
| ADP-09 | Extract stabilized boundary contracts / JS SDK | blocked | ADP-08 evidence and stable interfaces from ADP-05…07. Resolve BC inventory item by item, preserve app-owned policy/storage/engine boundary; second consumer evidence before claiming generality. Linked to RFC card #75, no automatic maturity increase. |

## Tracking rules

- `planned` means selected but not started; `in_progress` means bounded work is
  underway; `in_review` requires a PR and local evidence; `blocked` names a
  dependency or decision; `done` requires merged delivery and exit evidence.
- Prototype completion does not complete ADP-07, prove conformance, or resolve
  ADP-03. Provider policy cannot be inferred from `ephemeral` or process exit.
- Track actual elapsed work separately from estimates. Do not build an SDK,
  new workflow framework, crypto infrastructure or new protocol in the spike.
- No `sqrt`, natural-language semantic verifier, receipts, production identity,
  Proof-Bound or new RFC features are authorized by these tasks.
- CI is reported after push; no merge or prolonged monitoring is implicit.

## Evidence ledger

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
