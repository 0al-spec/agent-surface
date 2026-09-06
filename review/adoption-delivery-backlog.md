# Calcu adoption delivery backlog

Status: active, 2026-09-06. Owner: ASP/Calcu maintainers.

This is the canonical task tracker for this bounded implementation lane, not
another RFC requirement backlog. `ADP-*` identifiers are delivery tasks, not RFC
card or GitHub issue numbers. [RFC cards](review-data.json) remain authoritative
for coverage and maturity; none are changed by this plan. The SDK's
[BC-01…08 inventory](https://github.com/0al-spec/agent-surface-js/blob/66644562e6f529f29c4d02a780fc69726314ecf0/docs/boundary-contract.md)
records extraction gaps, not a competing task lifecycle.

Baseline: ASP `1783f50508b5498c8a24f60a758c4ce11868b294`; Calcu SDK-consumer
PR #3 remains a separate prerequisite. The implementation evidence and cost
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
| ADP-01 | Correct identity evidence hash domain / Calcu | in_review | [Calcu PR #4](https://github.com/SoundBlaster/Calcu/pull/4), stacked on #3. RFC-domain independent vector, old-domain invocation rejected before engine, fresh executor/session isolation; restart and reissue guidance. |
| ADP-02 | Bounded durable safety-state spike / ASP examples | in_review | [ASP PR #81](https://github.com/0al-spec/agent-surface/pull/81): separate Grant/session state, atomic admission/revocation race, stale/future generation rejection, connection-reopen/new-session lineage counter, unavailable-store rejection. Obligation matrix provided; owner cost/limitations decision remains open. |
| ADP-03 | Data handling and provider applicability decision / Calcu + deployment owner | in_progress | Code-path inventory first; owner-approved task/output classifications, retention, provider/CLI/log evidence and enforcement plan before live migration. Unknown capabilities remain unknown. |
| ADP-04 | Offline example maintenance / ASP examples | in_review | ASP PR #81: correct additive estimate, reject non-JSON tuple inputs, derive and test the stated 60-second lifetime. No live authority. |
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

- ADP-03: [data-handling worksheet](../reference/adoption/calcu/data-handling-worksheet.md).
- ADP-02: [safety-state experiment](../reference/adoption/calcu/safety_spike/README.md).
- ADP-01: Calcu `dd8d7d1`; `npm run check` (170 Vitest, 6 preflight,
  10 bundle checks), build, coverage and diff check passed. Independent review
  found no blockers. No live CLI smoke test was run.
- ADP-02/04: 11 SQLite prototype tests and 13 offline example tests passed;
  independent review findings corrected and rechecked. Full process-crash
  recovery remains ADP-07, not evidence claimed by the prototype.
- ADP-03 evidence worksheet is included in ASP PR #81; policy approval is not.
- Calcu PR #4 CI was green at 2026-09-06 10:26 UTC. ASP full CI is pending;
  no task has been marked done or merged by this delivery.
