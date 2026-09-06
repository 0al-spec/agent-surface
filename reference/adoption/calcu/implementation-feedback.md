# Calcu implementation feedback: one safe action

- Date: 2026-09-06.
- Status: implementation-informed recommendations, not normative changes.
- Decision: improve the adopter path before expanding the SDK or protocol.

## Executive decision

Calcu supports keeping the central ASP boundary: an application independently
admits a narrow typed action while credentials stay outside agent input. It
does **not** establish that the complete protocol is cheap to adopt, that all
selected role requirements are implemented, or that every infrastructure line
was required by ASP.

Use three dispositions for each difficulty:

1. **Application correction** when a useful, explicit requirement was omitted.
2. **SDK/example improvement** when the requirement is useful but repetitive or
   easy to misunderstand.
3. **Profile review** when the benefit or applicability of a requirement for this
   deployment remains unclear. This is a question to investigate, not permission
   to omit it while claiming current conformance.

Do not start by copying Calcu's abbreviated records into the SDK, or by expanding
Calcu until it implements every optional profile. First write a complete selected
deployment checklist and identify which costs belong to ASP, its binding, the
provider adapter, or the application.

## Evidence boundary

Source inspection in this report uses:

- [Calcu at `5e5a23f`](https://github.com/SoundBlaster/Calcu/tree/5e5a23f): the
  hashing consumer snapshot, not an assertion that its PR is merged.
- [Calcu adoption report](https://github.com/SoundBlaster/Calcu/blob/5e5a23f/docs/ASP_ADOPTION_REPORT.md)
  and [boundary report](https://github.com/SoundBlaster/Calcu/blob/5e5a23f/server/CONFORMANCE.md):
  retained local tests and the reported 2026-09-05 manual Luna smoke. Their role
  labels describe local behavior; the gaps below prevent treating them as full
  normative role conformance.
- [SDK contract comparison at `6664456`](https://github.com/0al-spec/agent-surface-js/blob/6664456/docs/boundary-contract.md):
  detailed field inventory and BC-01 through BC-08 migration gaps. It is a design
  document, not an authoritative SDK schema or evidence that its planned tests pass.
- ASP consumer pin `951871c2d55db25d35512f29cc0970c69aa5cfd9`. Its normative
  modules and bundle registry are unchanged relative to this report's base,
  `4925528ee7e1ac35c91e6c3f5044f41dea43c2e9`; local section links below refer to
  those requirements. The separate adoption-outcome work in PR #78 is not a
  dependency of this report.

No live provider request, new human study, production security test, or independent
implementation was run for this report. Existing mock tests and the historical
manual smoke are different evidence classes. A correct admitted multiplication
does not prove that an agent cannot access any undeclared tool or alternative
channel inside its own environment; it tests the observed application path.

## Cost: count the right thing

The following physical line counts were measured from the Calcu snapshot above
with `wc -l`; they include comments/blanks, exclude tests and frontend code, and
are not implementation-time or complexity benchmarks.

| Category | Files under `server/` | Lines | Interpretation |
| --- | --- | ---: | --- |
| Candidate shared boundary behavior | `executor.ts`, `identity.ts`, `localBackend.ts`, `httpsActionServer.ts`, `transport.ts`, `hash.ts` | 1,209 | Mix of protocol obligations, development policy and implementation choices; not all directly reusable |
| Agent/provider and task hosting | `codexAdapter.ts`, `taskHost.ts` | 974 | CLI protocol, process cleanup, stream framing, cookie/origin checks; not all ASP obligations |
| Demo composition and TLS setup | `demo.ts`, `developmentTls.ts` | 141 | Local deployment mechanics; not universal SDK defaults |
| Calculator-facing adapter | `calcu.ts` | 48 | Closed operation input and call to the existing math engine |
| Total sampled server code | Eleven files above | 2,372 | Does not include the existing math engine, UI, tests, dependencies or declarations |

The earlier adoption report's 5,600+ line total includes tests, preflight and UI;
it should not be quoted as 5,600 mandatory ASP implementation lines. Conversely,
moving 1,209 lines to a package would not remove their maintenance or trust cost.
The first SDK extraction replaces canonical hashing only and retains the JCS
value serializer. It establishes a packaging seam, not a demonstrated large
reduction in integration cost. Active engineering hours, cold setup time and
second-developer reproduction remain unmeasured.

## Findings and dispositions

The IF identifiers below are report-local labels, not new canonical backlog IDs.

### IF-01 — Minimal example is not a declaration fragment

**Requirement and guarantee.** [Actions](../../../drafts/modules/core.md#actions),
[Proposal-Only Surface Mode](../../../drafts/modules/core.md#proposal-only-surface-mode)
and [Data Exposure Contract](../../../drafts/modules/privacy.md#data-exposure-contract)
make the interpreted action inventory, output handling and authority ceiling
explicit. A valid hash cannot supply missing semantics.

**Observation and cost.** `executor.ts` uses action-id strings plus a separate
single `action` object. It omits complete action schemas, `operation_id` and
exposure declarations. Constructing and hashing a convenient local snapshot
made the demo run but did not produce a complete published manifest. The burden
is selecting the applicable cross-section requirements, not just writing JSON.

**Disposition: application correction + example.** Keep the requirements. Add
one complete annotated example with its selected deployment checklist and a
clear list of intentionally unsupported features. Do not use a mock-bundle
manifest schema as an application-manifest validator. Exit criterion: the example
passes applicable static checks and every remaining behavioral obligation has
an owner; a green linter alone is not sufficient. Maps to BC-01/02/04.

### IF-02 — Successful action is not successful interpretation

**Requirement and guarantee.** [Static Execution Modes](../../../drafts/modules/safe-effects.md#static-execution-modes)
and [Grant Verification](../../../drafts/modules/authorization.md#grant-verification)
bind declared operations and authority. They do not provide a natural-language
semantic verifier.

**Observation and cost.** In the reported root task, the agent selected
`multiply(111,2)` and Calcu returned `222`. The initial success label was easy
to read as verification of the whole task. Current
[UI tests](https://github.com/SoundBlaster/Calcu/blob/5e5a23f/src/features/agent-task/AgentTaskPanel.test.tsx)
retain the immutable requested task, exact action, verification scope and separate
unverified prose. This required presentation changes, not a broader action surface.

**Disposition: RFC explanatory note/example.** Reuse that distinction in an
adopter example. Do not require task hashes, an NLP parser, or `sqrt` to fix this
communication issue. Exit criterion: a mismatched-intent example remains an
admitted-action success but makes no claim of intent correctness. User
comprehension beyond the author's observation remains unmeasured.

### IF-03 — Identity projection is application debt, not redundant authority

**Requirement and guarantee.** [Identity projection binding](../../../drafts/modules/authorization.md#grant-credential-consent-and-projection-binding)
requires equal full envelopes in delegate and credential binding. The invariant
prevents divergent representations from being interpreted as the same delegation.

**Observation and cost.** Calcu stores the envelope under `delegate` but only its
hash in `credential_binding`. Development artifact verification does not repair
the missing wire projection. There are repeated fields, but no measured evidence
that their byte cost is the dominant onboarding problem.

**Disposition: correct Calcu + SDK projection behavior.** Preserve the invariant;
construct both projections from one verified immutable value, validate their
equality, and hash the complete authoritative Grant. Keep identity evidence distinct
from proof of the running Codex binary. Exit criterion: changed/missing second
copy is rejected even when other ids and the first copy are valid. Maps to BC-03.

### IF-04 — Logical audience is not the loopback address

**Requirement and guarantee.** [Endpoint declarations](../../../drafts/modules/core.md#endpoints)
separate the logical protected-resource audience from action and control URLs;
transport still needs authenticated endpoint binding.

**Observation and cost.** `demo.ts` selects a random `127.0.0.1` HTTPS port while
`executor.ts` uses `https://calcu.local/agent-actions` as logical audience and
snapshot URL. TLS trust is provisioned locally. Readers cannot learn the intended
mapping merely from these values, and there is no discovery endpoint.

**Disposition: binding example first.** Show canonical discovery identity,
logical audience, actual endpoint, who provisions their trusted association,
and what rejects substitution. Separate protocol-required guarantees from the
chosen `openssl`/loopback deployment. Do not standardize Calcu's hard-coded URL
or pretend random endpoints match `locations` without an explicit binding.
Exit criterion: an endpoint/audience substitution test fails while valid
provisioning is reproducible. If the chosen binding cannot express this mapping,
record a binding design gap rather than bless an undocumented alias. Maps to BC-08.

### IF-05 — Session completion and Grant revocation were conflated

**Requirement and guarantee.** [Session Authority and Lifecycle](../../../drafts/modules/authorization.md#session-authority-and-lifecycle)
distinguishes orchestration state, generations and terminal outcomes from the
validity of reusable delegation. Cancellation fences work; it is not rollback.

**Observation and cost.** Calcu creates one Grant/session per task and revokes
the Grant in `finally`. Its states are `active/revoked/expired`; generation
rotation also revokes instead of resuming. This is a conservative local shutdown
policy, but not an implementation of the normative session lifecycle. Full resume
and multi-session machinery has no exercised user benefit in this one-shot demo.

**Disposition: correct naming/model + investigate a one-shot walkthrough.** Show
task completion, session completion and explicit teardown revocation as separate
events. Determine which session obligations remain applicable when no resume is
offered; do not infer that optional UI implies optional normative fencing.
A smaller normative profile is only a proposal if the existing rules cannot
express the use case without unnecessary obligations. Exit criterion: exact
start/terminal/fence behavior and late-message denial are mapped without implying
that a terminal session can be reused. Maps to BC-05/06.

### IF-06 — Privacy declarations are operational promises

**Requirement and guarantee.** [Data Exposure Contract](../../../drafts/modules/privacy.md#data-exposure-contract)
requires conservative class declarations and an exact Grant source projection.
`transient` limits durable retention; `delete_on_grant_end` is meaningful behavior,
not a decorative safe default.

**Observation and cost.** Calcu does not yet declare the contract. It sends task
text to a provider and retains the result in the UI after Grant revocation.
Task input, application-produced result, app-owned UI, runtime memory, logs and
provider copies need separate ownership analysis. CLI `ephemeral` and a process
exit do not independently prove deletion by every relevant recipient. Neither
an empty class set nor automatic `private` classification follows just from
the word calculator.

**Disposition: application policy + worked data-flow example.** Classify outputs
and errors, identify who retains each copy, and select only enforceable retention
claims. SDK can derive and compare projections; it cannot choose the business
classification or prove provider behavior. Exit criterion: each promised lifetime
has an enforcing owner/test or is explicitly unsupported. Keep optional remote
processing/training-use claims separate from base exposure. Maps to BC-04.

### IF-07 — Pure evaluation is an instructive mode-fit question

**Requirement and guarantee.** [Static Execution Modes](../../../drafts/modules/safe-effects.md#static-execution-modes)
describes `read` as reading application state and `propose` as producing a
non-committed proposal/draft. Proposal-only publication requires a proposal action.

**Observation and cost.** Calcu evaluates caller-supplied operands and returns a
number: no existing application object is read and no later commit stage is
needed. The implementation calls that result a non-persisted proposal. This may
be a reasonable artifact interpretation, but the intended fit is not obvious
from the short mode definitions alone.

**Disposition: profile/semantics review, not a new mode now.** Ask whether pure
evaluation is explicitly within an existing definition and whether Mediated
Proposal is the right example bundle. Compare with the existing
[private draft example](../contextbuilder/operation-selection.md), where proposal
semantics are clearer. Do not rename the action or fabricate a commit companion
to satisfy a test. Exit criterion: one documented interpretation with unchanged
authority bounds, or a separately reviewed normative change with concrete
counterexamples. Calcu alone does not justify a `compute` mode.

**Follow-up decision:** [Mode fit and one-action applicability](mode-and-applicability.md)
retains the non-persisted calculation-artifact interpretation of `propose` and
records the selected path's mandatory and conditional obligations. It does not
claim that the current Calcu meets them; in particular, session control and
durable runaway guards are not waived by the one-task development lifecycle.

## Minimal-path experiment to run next

The [adoption bundles](../../../drafts/modules/conformance.md#adoption-oriented-conformance-bundles)
are coverage targets, not permission to waive unconditional role requirements.
Role count is not process count. Keep app-side authorization, exact bindings,
credential containment, revocation and unsupported-feature rejection in every
candidate that claims those guarantees.

1. Produce a short applicability checklist for **one non-persisted operation**:
   required now, conditional/not selected, or unresolved. Resolve IF-07 first;
   do not call the deployment conforming while its mode fit remains uncertain.
2. Build the complete example and data-flow worksheet, without a new framework.
   Assign every guarantee an owner: application, shared SDK, trusted runtime,
   provider adapter or deployment configuration. Preserve the current Calcu
   snapshot for comparison; corrections change hashes and need fresh issuance.
3. Let the SDK eliminate repeated construction/validation, not policy decisions.
   Compare manual declarations/configuration and handwritten integration code
   before/after. Count tests, generated files and provider-specific code separately.
4. Reproduce with a second developer and record setup commands, intervention
   count, active time, wait time and one action-schema change. No such measurement
   is claimed by this report; historical LOC is not a substitute.

Continue if the complete selected path can be explained and reproduced without
unresolved security choices. Improve SDK/examples if assembly work dominates.
Consider a narrower profile only after identifying the exact obligation to
remove, its lost guarantee and its replacement or explicit non-claim. Stop or
change the example if no material application-authority benefit remains compared
with the app's ordinary authenticated typed API. That comparison has not yet
been measured and must not be rigged by weakening the non-ASP baseline.

## Proposed deliveries and explicit deferrals

| Priority | Delivery | Owner / boundary | Done when |
| --- | --- | --- | --- |
| First | Resolve pure-operation mode fit and selected obligation checklist | RFC explanation/profile review | No guessed classification of the action or omitted unconditional obligation |
| Next | One complete local example plus privacy/endpoint/lifecycle walkthrough | Calcu + non-normative RFC examples | Contract fields and operational promises have owners and negative cases |
| Then | Shared immutable projection and binding objects | SDK | Real consumer removes duplicate logic while preserving rejection behavior |
| Later | Second-developer reproduction and schema-change exercise | Adoption experiment | Measured results support continue/simplify/stop decision |

Do not add new canonical cards, change existing card coverage/maturity, expand
the publication pipeline, publish a new profile, or migrate runtime code as a
side effect of this report. Existing BC gaps remain valid for claiming the
current RFC contract; the applicability review precedes blindly implementing
all of the SDK comparison's proposed migration steps. This report refines the
next-work recommendation without retroactively changing either source snapshot.
