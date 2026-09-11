# ASP adoption retrospective and experiment decision

- Date: 2026-09-05
- Audited baseline: `521eac88e75c728e6907981392917279133f0ae5`
- Status: initial audit and experiment plan; the bounded draft integration is now merged
- Authority: planning decision; does not change normative requirements or card maturity

## Decision

Historical post-experiment decision: [the outcome retrospective](adoption-outcome-2026-09.md)
records the merged draft experiment, its cost and limits, and the then-selected
independent reproduction step. The [current SDK-first delivery plan](adoption-delivery-backlog.md#sdk-first-delivery-decision-2026-09-11)
supersedes that sequencing and the pause below; it does not establish the
experiment's unmeasured outcomes. The original plan remains historical evidence:
neither its export criteria nor its time budget are declared met.

Pause expansion of bindings and publication infrastructure for one bounded
adoption experiment. Defer the proposed #80 WebMCP executable follow-up (not
yet a canonical card). Keep the existing backlog. The next delivery is evidence
about integrating ASP into an existing application, followed by a decision to
continue, simplify, or stop the selected adoption path.

The strongest current hypothesis is that ASP earns its integration cost when
an application needs to independently enforce a user's bounded delegation to
an agent, bind approval to exact inputs, and reconcile an ambiguous write.
The repository does not yet establish that ordinary application developers
can adopt that combination cheaply or that users prefer it.

## What the repository demonstrates

| Observation | Evidence | What it establishes / remaining uncertainty |
| --- | --- | --- |
| 79 cards: 72 present, 1 partial, 6 missing | [Canonical backlog](review-data.json) | Broad prose coverage, not adoption. |
| 53 specified, 17 machine_validated, 8 proposal, 1 implementation_tested; zero interop_tested/stable | [Canonical backlog](review-data.json) | Most contracts still lack implementation evidence; no independent interoperability claim. No release targets are assigned. |
| Seven canonical modules contain 17,385 lines, including examples and metadata | [Document catalog](../publication/document-set.json) | Large reading surface. Line count is not a count of normative obligations or a required reading assignment. |
| Core alone is 6,120 lines; authorization is 4,035 | [Core](../drafts/modules/core.md), [Authorization](../drafts/modules/authorization.md) | Physical modularization has not itself produced a short adopter path. |
| Surface Catalog: 1 role, 1 requirement entry, 3 vector entries; Application-Audited Effects: 6 roles, 21 requirement entries, 35 vector entries | [Bundle registry](../conformance/v1/bundles.json) | Discovery has a small entry point. Execution still needs a multi-role closure; roles do not necessarily mean six services. Counts are summed claim entries, not all RFC MUST clauses. |
| Real process-separated task/comment slice, local and remote runtimes, two scripted agents | [Slice description](../reference/vertical-slice/README.md), [Agent A](../reference/vertical-slice/agent_a.py), [Runtime](../reference/vertical-slice/runtime_local.py) | Useful implementation evidence, with separately tested role and composition paths. It is purpose-built and repository-maintained; it does not measure adaptation of an existing product, natural-language usability, or independent implementation. |
| WebMCP execution requires privileged browser-only invocation proof beyond the pinned callback API | [WebMCP profile](../drafts/modules/bindings/asp-over-mcp.md#asp-over-webmcp-binding-profile) | A security requirement is specified. Availability of a deployable browser bridge is not demonstrated by these artifacts. Treat WebMCP execution as a research dependency until that bridge is demonstrated. |

## Maintenance cost and concrete friction

The #70 commit `eb037aa` changed 27 files. Its primary addition was roughly
360 lines in the binding module; other changes included the aggregate,
dashboard, source map, document/dependency versions, conformance registry
versions, schema constants, evidence references, and reference-suite pin.
This is an observed example of publication coupling, not an estimate of every
future edit. Generated files are cheap when generated reliably; manually
coordinated version changes and repeated validation are the concern.

The [PR #74 quality job](https://github.com/0al-spec/agent-surface/actions/runs/30537728466/job/90854946358)
took 17m56s (11:13:47–11:31:43 UTC on July 30). This is one historical run,
not a benchmark or a current median. The [workflow](../.github/workflows/docs.yml)
runs publication, conformance, mocks, reference implementation, Rust tooling,
review data/tests and dashboard checks on every PR. Its 50-minute timeout is a
limit, not measured execution time.

Three specific documentation problems surfaced:

- The planning snapshot still counted 71 present / 7 missing after #70 and
  recommended already-completed publication work. This PR updates that view.
- [Application MVP Mapping](../drafts/modules/conformance.md#application-mvp-mapping)
  lists 16 steps without a compact selected deployment checklist, including
  accounting, loop guards and replay. Determine applicability before asking an
  adopter to implement them all.
- README/MVP text still foregrounds Passport verification while #76 defines
  selectable identity evidence. A walkthrough must explicitly select an
  identity profile. A later focused editorial fix should align entry docs with
  that contract; this audit does not silently alter normative text.

Keep reproducible assembly, stable links, independent app enforcement and
honest maturity gates. Freeze additional publication guarantees. During the
experiment, record every manually edited derivative and every wait for a gate.
Propose pipeline simplification only against measured friction and identified
consumers of each guarantee.

## Selected adoption experiment

Selection update: [the executed export preflight](../reference/adoption/contextbuilder/README.md)
disproved the single-file assumption below. After comparing smaller operations,
[the current decision](../reference/adoption/contextbuilder/operation-selection.md)
selects saving one private raw-idea draft, using proposal-only semantics, and
defers export transaction work. The original scenario below is retained for
traceability; its effects/recovery acceptance criteria remain unmeasured and
must not be reported as passed by the narrower draft experiment.

### Original export scenario (historical, deferred)

The following scenario and stage selection are retained as the original plan,
not instructions for the next implementation. Use the selection update above.

Use the existing local ContextBuilder application as the first candidate. Its
README describes graph selection and export, and `viewer/server.py` delegates
to existing `viewer/export.py` and `viewer/hyperprompt_compile.py` operations.
This is a preliminary source assessment, not a verified integration. It shares
the author's ecosystem, so success would establish product adaptation, not
independent interoperability. Pin its commit at experiment start.

Scenario: read a synthetic conversation graph, select a small set of nodes,
preview the exact export destination/content, obtain user approval, and write
one Markdown context artifact through the existing application operation.
Use synthetic conversations and a disposable output directory. Start with
export, avoiding an extra compiler dependency in the action under study.

Compare two implementations against the same application operation and data:

1. Existing application/API flow: measure setup, authorized export and failure
   recovery using its current controls. Do not weaken it to manufacture an ASP
   advantage.
2. ASP integration: one application process containing the necessary
   application roles, one local Runtime Mediator, and one agent adapter. Reuse
   business logic. Select Application-Audited Effects plus every applicable
   approval requirement; map the complete requirement closure before coding.

Proposed agent-facing stages are read, dry-run/preview and commit with distinct
action IDs. They are experiment candidates, not new standardized action names.
If the selected contract requires more stages or infrastructure, record it as
an integration cost rather than bypassing the requirement. Use one existing
ASP transport supported by the application/runtime; pin that choice in the
experiment plan before implementation. Browser WebMCP is not a prerequisite.

Start with a deterministic client to measure integration. Then run a small
human-guided agent session through the same adapter to assess tool selection
and approval comprehension. If no suitable agent is available, retain the
engineering results and mark the usability result unmeasured.

## Budget, measurements and acceptance

The budget remains shared across the experiment. The table's export/write and
recovery criteria describe the original full-effects goal; draft-only results
must be reported separately and cannot satisfy those criteria.

Timebox: two engineer-days of active work (16 hours), recording waiting time
separately. This is a decision threshold, not a delivery estimate. At the limit,
publish the incomplete result and blockers; do not grow the RFC to finish it.

| Measurement | Required retained evidence / decision threshold |
| --- | --- |
| Time to first read and approved write | Timestamped work log; target read within 4 active hours and full scenario within 16. |
| Integration size | Diff split into business-logic changes, ASP adapter/runtime code, declarations, tests and generated files. Report all categories; an advisory 1,000 handwritten integration-line budget triggers simplification review, not a safety exemption. |
| Setup burden | Exact clean-checkout commands, processes, dependencies and secrets/configuration categories; record each manual step. |
| Specification burden | Sections actually consulted, obligatory artifacts, unresolved questions and author interventions. Every guess gets an entry, even if later resolved. |
| Correctness | Positive export; denial; changed input after approval; revoked Grant; stale preview; repeated request; response loss after write. Show authoritative output state and receipt/correlation evidence, including no duplicate output. |
| Incremental value | Explain which failures each flow prevents, detects or reconciles, and the added user/developer cost. Do not compare conformance badge counts. |
| Maintenance | Make one small action-schema change and record files edited manually/generated, commands and elapsed gate time. |
| Transferability | Another developer follows the walkthrough from a clean checkout; count interventions. If unavailable, this criterion stays unmeasured. |

The experiment succeeds when the approved write and negative cases run within
the budget, the requirement closure is explicit, and the resulting walkthrough
is repeatable. Adoption remains unproven until another developer reproduces it.
No card maturity is raised automatically by this experiment.

## Decision after the experiment

- Continue the selected ASP path if it delivers a concrete delegation or
  recovery benefit with acceptable setup and a reproducible walkthrough.
- Simplify packaging if semantics work but assembly/version/configuration
  chores dominate. Prioritize the smallest helper supported by the experiment
  before undertaking the full #75 SDK.
- Propose a smaller normative profile only if the obligation map demonstrates
  unnecessary mandatory coupling. Review any removed guarantee explicitly.
- Stop or change the target scenario if existing controls solve the need with
  materially less work and ASP adds no benefit the application owner values.
- Keep #67/#68/#71/#72/#73 and #77 deferred until there is a concrete adopter
  for the corresponding mapping. Reconsider WebMCP follow-up after evidence of
  a viable privileged browser bridge.

The proposal-only deployment/profile map and runnable draft adapter are merged.
The [outcome retrospective](adoption-outcome-2026-09.md) supplies the bounded
engineering result and continue/simplify/stop decision. Human UX, independent
reproduction, the maintenance-change exercise and the original export scenario
remain unmeasured. Mock-user consent is not a successful human experiment.
