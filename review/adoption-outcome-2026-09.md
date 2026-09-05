# ASP adoption experiment: outcome and next decision

- Date: 2026-09-05
- ASP evidence snapshot: `4925528ee7e1ac35c91e6c3f5044f41dea43c2e9` (merged PRs #75–#77)
- SpecSpace implementation pin: `181926375d27b18b95d8e596e569540477e427b2`, merged through [PR #430](https://github.com/0al-spec/SpecSpace/pull/430) as `d4e850a1`
- Authority: planning/evidence assessment only; no RFC, card, release or maturity changes

## Decision

**Continue validation of this one slice; review packaging cost before expanding it.**
The private draft flow works in the tested configuration. Cheap adoption, human
comprehension and independent interoperability are not established. Do not start
a second operation, a general SDK or another binding to compensate for those gaps.

The next selected step is a clean-checkout reproduction by a developer who did
not build this adapter. Fix demonstrated setup/documentation friction first.
A shared helper is only a candidate after that exercise identifies repeated
mechanical work; changing normative guarantees is not justified by this result.

This closes the bounded mock-user functional experiment, not the full adoption
hypothesis or the original export experiment in the
[initial plan](adoption-retrospective-2026-09.md). The 16-hour active-work budget
was not continuously recorded, so compliance with it cannot be claimed.

## What was actually integrated

The [reproducible scenario](../reference/adoption/contextbuilder/https-draft.md)
uses a real SpecSpace server, verified loopback HTTPS, a separate runtime worker,
a deterministic agent and private SQLite state. Credentials are development-only
Compatibility Bearer. The application issues and checks its own Grant; a local
pinned Ed25519 identity profile supplies evidence, not executable attestation.

The sequence is scoped read → exact draft approval → persisted `propose` →
response-loss retry. MockUser makes distinct Grant and draft decisions. There is
no ASP `commit`, production migration, signed receipt or natural-language agent
evaluation. The later native edit is scripted too.

| Existing application contribution | Added boundary and observed benefit |
| --- | --- |
| Native raw-idea validation/save and `draft` state; operator authentication already existed | Reused save without rewriting its business rules. ASP adds bounded runtime/agent authority; it does not invent all application access control. |
| Native save is intentionally an upsert | ASP create-only admission plus immutable execution/result records prevents an exact retry from overwriting a later native edit. |
| Existing storage abstractions and process-local lock | New synthetic SQLite backend and shared transaction join native mutation with authority/result state. Tests cover rollback/concurrency; this is not evidence for migration of existing file/external deployments. |
| Native operator access is not exact agent-action consent | Grant and approval bindings reject wrong workspace, changed input and revoked authority. Mock tests verify refusal mechanics, not human understanding. |

## Integration size: count both sides

Physical added lines include comments and blanks. These are implementation
inventory counts, not engineering hours, normative requirement counts or a
minimum that every adopter must implement.

| Category | Added lines | Files / boundary |
| --- | ---: | --- |
| Native business-function transaction hook | 15 | SpecSpace `viewer/real_idea_entry_requests.py`; no deletions |
| Existing server integration hooks | 18 | `viewer/server.py`, `viewer/server_runtime.py`; 2 deletions |
| New app-side protocol/storage code | 802 | `viewer/asp_draft{,_http,_identity,_store,_wire}.py`: 369 + 147 + 68 + 110 + 108 |
| Independent runtime and deterministic agent | 312 | ASP `runtime.py` 284 + `draft_agent.py` 28 |
| Mock-user policy and E2E orchestration | 351 | `mock_user.py` 71 + `https_scenario.py` 280 |
| Focused test files | 1,057 | SpecSpace `test_asp_draft_*.py` 743; ASP `test_runtime.py` 152 + `test_mock_user.py` 162 |
| App docs/planning and draft walkthrough | 351 | SpecSpace 196; ASP `https-draft.md` 155 at the snapshot |
| New CI workflow | 52 | ASP `.github/workflows/asp-draft-adoption.yml` |

The application alone adds **835 integration lines** (833 net). Including the
runtime/agent gives **1,147**, already above the initial plan's advisory 1,000-line
threshold. Including mock-user/driver scaffolding gives **1,498**. Counting only
the 15-line business hook would hide most of the cost. Conversely, charging all
test scaffolding to every future application would overstate required adoption work.

Declarations/schemas are embedded in the implementation and are not separately
counted. No generated publication artifacts or canonical RFC files changed for
this integration. The table excludes earlier export/draft preflight scripts and
their historical planning material; it is not the full retrospective project's
size. Reproduce the app counts with `git diff --no-renames --numstat 567d5e39
18192637` in SpecSpace; obtain each listed ASP file with `git show 4925528:<path>`
and count its lines. The ASP file prefix is `reference/adoption/contextbuilder/`.

## Evidence and unresolved cost

- Recorded local checks: 18 ASP tests; 31 app-side tests; 402 existing scoped app
  tests plus 25 subtests. The real HTTPS scenario passed against the exact app pin.
  These are recorded implementation results, not a new full conformance run.
- [Mock-user CI](https://github.com/0al-spec/agent-surface/actions/runs/33963939600/job/101300564395)
  passed in 11 seconds. Real response loss and app process restart are tested;
  the whole Mediated Proposal bundle and independent implementations are not.
- Four review findings required fixes: response idempotency binding, bypassing
  pause through a new session, workspace normalization mismatch and malformed
  approval IDs reaching SQLite. Final review also prompted request-key preflight.
  These exposed cross-boundary integration mistakes, not demonstrated RFC defects.
- OpenSSL 3.x, a prepared Python environment, exact checkout selection, local
  issuer/subject keys, TLS and separate operator/runtime credentials are real setup
  dependencies. The driver automates disposable material; this does not establish
  deployable production trust or credential lifecycle management.
- A manual attempt expired at the 120-second approval window before ASP saving.
  It demonstrates fail-closed expiry and friction in the chat-mediated CLI test,
  not a validated product UI problem or permission to weaken expiry.
- [PR #76 quality gate](https://github.com/0al-spec/agent-surface/actions/runs/33963920053/job/101300511307)
  took 13m03s; [PR #77 quality gate](https://github.com/0al-spec/agent-surface/actions/runs/33963939587/job/101300564269)
  took 17m52s in the recorded runs. These are individual samples, not medians or
  adopter setup time. Preserve the focused smoke; consider broader CI scope only
  as a separate measured maintenance proposal, not part of this document change.

Unknown: total active implementation hours, time spent consulting the RFC,
all author interventions, schema-change maintenance cost, independent setup time,
human comprehension and whether a product owner values the extra guarantees.
The advisory code-size threshold therefore triggers review, not an automatic
rejection of ASP or an assertion that the two-day budget was exceeded.

## Next gate: independent reproduction, not a second feature

1. The project owner nominates a developer who did not implement this slice.
   Another run by the author or a same-context agent is not independent evidence.
2. That developer uses the linked walkthrough and exact pins in fresh trusted
   checkouts, with synthetic data only. Record environment preparation separately
   from time to the first successful mock-user report. Do not reuse private tokens.
3. Retain a short report: ASP/app SHAs, OS/Python/OpenSSL versions, commands,
   setup/run minutes, failure messages with secrets removed, author interventions,
   final `approval: mock_user` result, and the most confusing setup/contract step.
4. Success means the documented flow works without undisclosed prerequisites or
   code edits. Help is allowed but must be counted; it identifies documentation
   debt rather than becoming an invisible pass. Reproduction of the same code
   does not qualify as two independent interoperable implementations.
5. Review the result before choosing further work: fix docs/setup if those block;
   consider one bounded helper only for observed repetition; stop expanding this
   path if the application owner does not value its authority/retry guarantees.

An intake clarification answer is a possible later operation, not an approved
next implementation. Human UX and a small schema-change maintenance exercise
remain separate follow-ups. This recommendation creates no new card and does
not reset the historical effort budget or claim the remaining work fits it.
