# ADP-03: Calcu source exposure and Grant projection design

Status: non-normative design fragment; not an advertised capability, deployment
approval or completed ADP-03 gate. Implementation baseline: Calcu `a059d77`.
Normative basis: [Data Exposure Contract](../../../drafts/modules/privacy.md#data-exposure-contract)
at ASP `c875ed0`. No RFC or live Calcu contract is changed here.

## One source, four operators

Calcu exposes one ASP action, `calculation.propose`, with execution mode
`propose`; `add`, `subtract`, `multiply`, and `divide` are input enum values,
not separately grantable actions. The adapter tool is `calculation_propose`.
Selecting that action contributes exactly one action source to the exposure
closure regardless of operator or how many times the caller invokes it.

| Path | Maximum application-originated fields | Design obligation |
| --- | --- | --- |
| add success | `operator`, `left`, `right`, numeric `result` | Include echoed operands and derived result; addition does not declassify either |
| subtract success | Same four fields | Same source contract |
| multiply success | Same four fields | Same source contract, including the `240 × 0.15 = 36` example |
| divide success | Same four fields | Same source contract; an undefined/non-finite outcome is not a successful numeric result |
| Action failure | Declared closed error code/envelope only; no raw input, task, stack or upstream diagnostic text | Include application-originated structured errors in the maximum exposure; errors must not echo rejected data |
| ASP response correlation | Current executor response includes binding and trace metadata before LocalBackend strips it | Inventory runtime-visible metadata too; stripping before model delivery does not erase exposure to the runtime |

`server/localBackend.ts` accepts a closed success envelope, verifies correlation
and operands, then returns only the four output fields. The adapter serializes
that result into a tool response. Its separately displayed trace repeats the
operands: a new presentation is not a new lower-sensitivity source.
User task text and agent-authored prose have separate ownership/policy; neither
belongs in an invented application output class merely to simplify this table.

Today HTTPS `action.error` carries a closed code to the transport. A backend
exception terminates the task/child; it is not returned as a structured model
tool error. The adapter's explicit rejected-call response is the fixed text
`Request rejected`. Browser `task.failed` uses a separate code allowlist.
The error row above is a maximum-envelope design obligation, not a claim that
all these error channels already share an implemented exposure contract.

## Classification decision still required

The existing offline `calculation.sample` class is explicitly a fixed synthetic
example. Its `private` classification is not evidence for arbitrary live
numbers. Live operands/results can represent sensitive financial or personal
information, and numbers can also encode credentials. Numeric schema validation
cannot establish their semantic classification.

Before issuance, the publisher must choose a defensible maximum for each live
class, including runtime-visible correlation metadata. If a class can contain
credential material, the normative most-protective rule applies; declaring
`credential` does not authorize release under `credential_release: deny`.
Do not silently choose `private`/`sensitive`, introduce a natural-language
classifier, or advertise unrestricted safe disclosure to evade that conflict.
Record the enforceable boundary or an explicit infeasibility finding. The owner
has not approved a synthetic-only product restriction.

`redaction.mode: none` is a possible design only when the declared classes cover
the full unredacted envelope. A future `policy` choice needs a named,
application-enforced pre-delivery policy and consent-safe summary. Removing
fields after the runtime receives them is not application-side redaction.

## Worked offline projection (not a live manifest)

Reuse the fixed synthetic scope of `contract_example.py`; this example does not
settle the live classification decision above. Given no resources/events and
the selected action `calculation.propose`, whose declaration is:

```json
{
  "classes": ["calculation.sample"],
  "redaction": {"mode": "none"},
  "retention": {"mode": "transient", "delete_on_grant_end": true}
}
```

the issuer-derived Grant member is exactly:

```json
[
  {
    "source": {"kind": "action", "id": "calculation.propose"},
    "classes": ["calculation.sample"],
    "redaction": {"mode": "none"},
    "retention": {"mode": "transient", "delete_on_grant_end": true}
  }
]
```

An exposure-only empty selection produces `[]` in this no-resource/no-event
example; that is not permission to issue an otherwise invalid empty Grant.
Do not extend this shortcut to a complete deployment: derive resources by exact
granted `read_scope`, actions by exact ID, non-control events by exact scope,
and every advertised core control event regardless of scopes. Include sources
with empty class arrays. Order by resource/action/event then Unicode source ID;
preserve the complete source contract and class ordering. Unknown control events
require the normative compatibility decision, not silent omission.

The client does not submit `data_exposure`. The issuer derives it from the
pinned manifest and approved authority; issuance and introspection agree.
The runtime independently recomputes it before storing/using the Grant and
requires exact structural equality, not merely equivalent class unions.

Hash the complete Grant hashing view (excluding its own `grant_hash`) using
RFC 8785 and the ASP `https://github.com/0al-spec/agent-surface/hash/grant/v1`
domain, as the existing offline example does. There is no new standalone
`exposure_hash`. A changed exposure changes the manifest hashing view and
requires a new surface version and fresh Grant binding, not mutation of an old
Grant. A correct hash alone proves neither source correctness nor enforceability.

## Negative cases to carry into ADP-05/08

| Mutation / condition | Required outcome |
| --- | --- |
| Selected action source missing, duplicated, unknown or extra | Reject projection as `integrity_mismatch` before use |
| Operator names substituted as source IDs | Reject; they are not manifest actions |
| Classes, ordering, redaction or retention differs from the pinned declaration | `integrity_mismatch`, even for a locally stricter replacement |
| Client supplies a derived projection | Reject invalid authorization request; never trust caller derivation |
| Old projection with changed manifest, or introspection disagrees | Reject stale/inconsistent binding; no automatic adoption |
| Payload exceeds declared envelope | Block/discard delivery with `data_exposure_violation`; no offending values in logs/errors |
| Selected runtime-agent retention cannot be enforced | Refuse use before disclosure, even with correct projection/hash |

These are design acceptance cases, not a new executable validator or passing
conformance report. Existing offline tests check fixed example construction and
hashing only; they do not implement these rejection paths. ADP-05 implements
issuer/runtime derivation and application enforcement; ADP-08 tests the real
HTTPS path, including rejected calls and data-minimized failures.

## Remaining gates

This slice fixes source identity and projection mechanics, not live policy.
Live source classification/redaction (including response metadata), retention
feasibility, selected-path evidence, task-input lifecycle, principal ownership
and UI disclosure/display lifecycle remain open in the
[worksheet](data-handling-worksheet.md). ADP-03 stays `in_progress`; ADP-05 also
requires the independent ADP-02 cost decision. No credentials, provider settings,
live CLI workload, additional operator or SDK implementation is part of this slice.
