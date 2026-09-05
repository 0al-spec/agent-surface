# SpecSpace: first adoption operation selection

Date: 2026-09-05. Decision: keep SpecSpace as the target application; select
**saving one private raw-idea draft** as the first integration slice. Defer the
export transaction spike. This document selects work; it does not report an
ASP implementation, human approval test or conformance result.

Implementation follow-up: [the isolated HTTPS draft scenario](https-draft.md)
now records the selected concrete boundaries and synthetic execution results.
The baseline observations below remain unchanged.

Execution scope clarification: the user subsequently selected a deterministic
mock user for the functional E2E run. The human-confirmed criteria below remain
the historical adoption/UX objective, not a claim that automated approval meets
it. See [mock-user boundaries](https-draft.md#mock-user-and-human-pass).

"Private" describes the application's intended non-public draft storage, not
verified confidentiality or authentication. The probe bypasses HTTP and does
not establish an authenticated user/agent boundary.

## Evidence and comparison

Inspected the same clean SpecSpace pin as the export baseline:
`567d5e39aecb83b9879a07cfab2c6f7062a98a20`. The current dirty application
checkout was not used for tests or changed. Links below are commit-pinned.

| Candidate | Existing operation and prerequisites | Main remaining cost | Decision |
| --- | --- | --- | --- |
| Raw-idea draft | [`save_request`](https://github.com/0al-spec/SpecSpace/blob/567d5e39aecb83b9879a07cfab2c6f7062a98a20/viewer/real_idea_entry_requests.py#L207), `status: draft`, explicit request ID; bounded text and one private state collection; no producer artifacts | Existing save is an upsert, not exact retry or create-only admission | First slice |
| Intake clarification answer | [`save_intake_answer`](https://github.com/0al-spec/SpecSpace/blob/567d5e39aecb83b9879a07cfab2c6f7062a98a20/viewer/idea_to_spec_intake_clarification_answers.py#L245); published questions, answer template and allowed actions | Bind changing question/template context as well as the answer; exact retry still absent | Second, richer test |
| Project-local ontology decision | [`save_decision`](https://github.com/0al-spec/SpecSpace/blob/567d5e39aecb83b9879a07cfab2c6f7062a98a20/viewer/project_local_ontology_review_decisions.py#L204); review lane, term identity and supported action | Lane freshness and domain-specific interpretation; exact retry still absent | Alternative after first slice |

Repair drafts additionally depend on repair-session readiness. Promotion
confirmation has useful reuse tests, but leads toward a higher-authority,
multi-step execution lifecycle. Neither is a better starting point than a
private idea draft. The export remains a later recovery/stress test.

The selected `draft` state already exists in both the backend and the
[frontend input type](https://github.com/0al-spec/SpecSpace/blob/567d5e39aecb83b9879a07cfab2c6f7062a98a20/graphspace/src/pages/viewer/model/use-real-idea-entry-requests.ts#L43).
We are selecting an existing API subcase, not claiming the current UI has a
separate tested Save Draft button. The
[POST handler](https://github.com/0al-spec/SpecSpace/blob/567d5e39aecb83b9879a07cfab2c6f7062a98a20/viewer/specspace_v1_api.py#L1793)
delegates to that business function. A separate
[intake admission check](https://github.com/0al-spec/SpecSpace/blob/567d5e39aecb83b9879a07cfab2c6f7062a98a20/viewer/real_idea_intake_execution.py#L456)
requires a submitted entry; saving a draft does not call intake execution.

## What the baseline actually proves

The [draft probe](draft_probe.py) calls the existing business function with
synthetic input, a temporary file backend and a controlled clock:

- Saving creates `real_idea_entry_requests.json`, containing a draft, with no
  active submitted request. The intake helper rejects that draft.
- Reusing an explicit request ID leaves one row, but changes timestamps and
  file bytes. It is not exact retry.
- Different text under the same ID replaces that draft instead of returning
  an idempotency conflict. The existing API intentionally permits updates.
- Workspace mismatch and an execution-authority claim are rejected without
  changing the stored file.

This is a smaller application boundary, **not a ready-made ASP endpoint**.
No model, browser, external service, human approval or canonical specification
mutation is exercised by the probe. Rejected client flags are not proof of
authenticated agent identity.

## Revise the experiment honestly

The first slice becomes **read → inspect proposed text → human confirmation →
persist draft → exact retry**. Persistence here is not ASP `commit`.

Under [Proposal-Only Surface Mode](../../../drafts/modules/core.md#proposal-only-surface-mode),
the intended mapping is `read` plus persisted `propose`, with
`execution.persisted: true` and required idempotency. Do not label a preview
screen as normative `dry_run`, add a `commit` action just to match the old
experiment diagram, or claim Application-Audited Effects on that basis.
Confirmation of draft text does not authorize submission or later execution.

This deliberately narrows the original export experiment. It can measure
discovery, scoped delegation, draft isolation, approval comprehension and
deduplication cost. It cannot validate safe domain commits, compensation,
multi-file recovery or the full original effects scenario. Preserve those as
unmeasured, not as passed or silently removed acceptance criteria.

## Smallest implementation boundary

Expose only creation of a new draft in one granted workspace, plus a scoped
read. Preview must show the exact text, workspace and the fact that nothing
will be submitted, generated or published. Reuse existing validation/storage;
do not expose a generic state-store PUT or all fields of `save_request`.

The adapter must fix `status: draft`, derive actor identity from verified
authority, and reject attempts to supply execution flags, another workspace
or an existing request ID as an update. Creation admission and deduplication
must share the application mutation boundary; an adapter-only precheck cannot
prevent a competing native update. Keep the result/execution identity for
response-loss retry without silently overwriting a later user edit. An
immutable execution result is distinct from the mutable current draft.

Select the transport and identity profile and map the applicable normative
requirements before implementation. Proposal-only reduces effects scope; it
does not remove Grant verification, privacy, revocation, admission limits or
persisted-proposal idempotency requirements. Do not increase card maturity.

### Storage facts, not assumed guarantees

- The [file backend](https://github.com/0al-spec/SpecSpace/blob/567d5e39aecb83b9879a07cfab2c6f7062a98a20/viewer/specspace_state_backend.py#L109)
  writes a temporary file, flushes/fsyncs it and replaces the JSON file. The
  handler uses a process-local lock. This is not a cross-process CAS or a
  demonstrated crash-durable transaction over draft and execution records.
- The [external backend](https://github.com/0al-spec/SpecSpace/blob/567d5e39aecb83b9879a07cfab2c6f7062a98a20/viewer/specspace_state_backend.py#L750)
  sends expected revision and a digest-derived key. They protect a state
  record, not an entire business operation or its authorization inputs.
- Platform's existing
  [SQLite store](https://github.com/0al-spec/Platform/blob/f900513681fbb2c9ae41ad60047291301b496858/scripts/specspace_state_store.py#L350)
  and service offer a reusable transaction/history path. Its retry lookup
  accepts a result only while that revision is current; this is not a complete
  ASP exact-retry implementation after subsequent edits. SQLite store tests
  below are sequential, not multi-process concurrency evidence.
- SpecSpace's external-state test double returns `adapter: postgresql` without
  running PostgreSQL. Do not use those tests as PostgreSQL evidence.

Choose file or external deployment explicitly at the next implementation gate.
Reuse a proven transaction boundary where suitable; do not launch a general
storage rewrite for this experiment. If the remaining guarantees do not fit a
bounded change, report that result and stop before expanding the application.

## Reproduction and checks performed

The draft imports require SpecSpace's Python dependencies, including
`PyYAML==6.0.3`. ASP's existing environment alone lacked PyYAML; that attempted
run failed before mutation. No dependency was installed: successful runs used
the existing SpecSpace virtual environment. This setup difference is part of
the adoption cost. Trust the entire checkout/dependency environment and do not
modify it concurrently, as in the [baseline prerequisites](README.md#reproduction).

From a clean pinned SpecSpace checkout, use its prepared environment:

```sh
/path/to/specspace/.venv/bin/python -B \
  /path/to/agent-surface/reference/adoption/contextbuilder/draft_probe.py \
  --checkout /path/to/clean-specspace

/path/to/specspace/.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_specspace_api_v1.py -k real_idea_entry_requests_v1

/path/to/specspace/.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_project_local_ontology_review_decisions.py
```

Observed: draft probe passed; five selected API tests and eight ontology
decision tests passed. Tests exercise synthetic handlers, not production HTTP
authentication. The draft probe also passed under `-O -B`.

Separately, at Platform commit
`f900513681fbb2c9ae41ad60047291301b496858`, four existing SQLite store tests passed:

```sh
.venv/bin/python -B -m unittest \
  tests.test_specspace_state_store.SpecSpaceStateStoreTests -v
```

The inspected Platform store/service/test files match that commit; unrelated
dirty Platform work was preserved. No PostgreSQL integration, crash recovery
or full ASP CI suite was run for this selection.

## Next step and stopping rule

Implement a bounded proposal-only adapter for this one draft operation after
pinning its deployment/profile choices. Measure business changes separately
from ASP code, setup and declaration burden. Retain the original 16-active-hour
experiment ceiling and the uncertainty in earlier uninstrumented work; do not
reset it because the operation changed. The two-hour export spike is deferred,
not a second allocation. This selection does not establish remaining hours or
promise that the integration fits the ceiling.

Success for this first slice means an actual human-confirmed, authorized draft
and negative cases run without changing canonical specifications or executing
intake. Wrong workspace, changed approved text, revoked/expired Grant, replay,
conflicting input and response loss remain required integration cases. Only
then decide whether an intake answer or a genuine effects operation is worth
the next increment. No new RFC features are justified by selection alone.
