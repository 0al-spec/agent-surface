# ADP-03: Calcu user-managed handling design

Status: current design candidate, not deployed or approved as live conformance.
Normative baseline: ASP `b2d7e3627a08ec40ed7c0fd2f76370acc1c7e691`
(Privacy `0.1.0-draft.4`). Implementation inspected: Calcu
`a059d777405579f64a24af96aa1119e1950beee8`.

This replaces the withdrawn transient design, not an existing issued Grant.
Agent cache/rollout/provider retention investigation stays stopped. The
[backlog](../../../review/adoption-delivery-backlog.md) remains authoritative:
ADP-03 is design/feasibility work; live ADP-05 integration needs approved design
inputs and scoped ADP-02 investment approval. The owner has selected SDK-first
security engineering, not all implementation work. This document defines no
new protocol fields or public SDK API; reusable behavior is delivered with
Calcu through the backlog's coordinated vertical slices.

## Application boundary and selected contract

One source/action: `calculation.propose`, mode `propose`, no persisted business
artifact. The four operators remain input enum values. There are no granted
history, file, account or database resources. Receiving numeric operands does
not authorize access to any other application data.

The publisher selects this exact source fragment:

```json
{
  "classes": ["calculation.content", "calculation.runtime_context", "calculation.status"],
  "redaction": {"mode": "none"},
  "retention": {"mode": "user_managed"}
}
```

The existing candidate class maximum is retained for design review:

| Class | Classification | Covered fields / boundary |
| --- | --- | --- |
| `calculation.content` | `sensitive` | Operator, echoed operands, derived numeric result, including repeated result/trace presentations |
| `calculation.runtime_context` | `sensitive` | Runtime-visible binding/correlation metadata before LocalBackend strips it: session/generation, Grant ID/hash, surface hash, subject/delegate/audience, identity-evidence hash, trace/span |
| `calculation.status` | `private` | Closed success/error discriminants, action/mode identifiers and allowlisted error codes; never raw diagnostics or task text |

These are proposed application-local IDs, not new ASP classes. `none` requires
the complete delivered envelope to fit this maximum; model-side stripping is
not application-side redaction. No semantic PIN detector or synthetic-only
product restriction is proposed. Known provenance must not be discarded:
application-held credentials and trusted stricter source obligations remain
non-releasable/restrictive even when represented as numbers. Unknown numerical
meaning alone does not establish credential provenance. A future protected
source needs a separately authorized read and inherited handling obligations.

No `delete_on_grant_end`, `max_seconds`, implicit mode or caller-selected
override is allowed for this source's `user_managed` shape. It makes no
source-level deletion promise for runtime/agent copies. It does not authorize
training, remove stricter policy or alter application-owned storage policy.

## Exact projection and consent design

The issuer derives `Grant.data_exposure` from the exact manifest and approved
actions/scopes. It is a top-level projection, **not** an invented retention
member in `Grant.constraints`, and not client-submitted authority. In this
no-resource/no-event example it contains exactly one action source with the
complete fragment above. Runtime independently recomputes the same projection;
introspection must agree. General control-event closure must not be omitted if
the future manifest advertises such events.

The complete manifest and Grant views use the existing ASP JCS hash domains.
Changed handling requires a new surface version/hash and fresh consent/Grant;
never mutate active records or reuse old preview/Grant hashes. A stricter local
overlay is enforced separately without rewriting the signed/pinned projection.
No additional exposure hash, acknowledgement token or receipt format is needed.

The future UI must show the approved principal, runtime/agent, action, full
source classes, selected mode and lifetime against an immutable server preview.
Suggested source-specific notice:

> Your task and the calculator operands/result are sent to your selected agent
> and its configured model provider. This source uses user-managed retention:
> ASP sets no storage deadline or automatic deletion when the Grant ends.
> Revocation stops future application access, not recall of disclosed copies.
> Stricter applicable policies still apply. Calcu makes no provider deletion or
> training guarantee. ASP credentials remain inside the local server boundary.

Approval must bind that exact preview and authenticated local principal; a
generic checkbox or task POST alone is not that binding. Missing/stale preview,
changed policy/identity/source, or a different principal requires rejection or
fresh consent before issuance. Browser receives only a safe preview/projection,
never a credential or identity artifact. This is Grant consent, not an action
Approval Receipt. Multi-user/tenant operation remains out of scope.

## SDK + Calcu implementation seams (not implemented here)

| Calcu seam | Required migration work / acceptance evidence |
| --- | --- |
| SDK contracts/issuer/executor + `server/executor.ts` | Implement reusable validated construction and admission in SDK, consumed by Calcu under ADP-05. App publisher owns declaration, issuer policy/authority owns projection/issuance; exact hash/session/identity checks remain |
| SDK mediator + `server/localBackend.ts` | Independently verify effective projection before Grant use; no caller override; retain typed app facade, correlation checks and HTTPS-only executor path |
| SDK preview/binding behavior + `server/demo.ts`, `server/taskHost.ts` | Calcu owns authenticated principal, policy and credential custody. Bind exact approved preview to issuance; reject invalid consent before executor invocation; revoke on settlement |
| UI integration + `AgentTaskPanel.tsx` | Display source-specific notice and immutable consent snapshot; fresh consent on changes; retain task/action provenance. Future hooks cannot issue authority or import privileged server modules |
| Executor response boundary | Enforce closed success/error/correlation maximum before HTTPS disclosure, not after receipt; no credential/raw error echo |
| App UI/task lifecycle | On cancel/error/unmount invalidate generation, abort work, release abandoned projections; editable task may remain for retry; no durable history feature |
| SDK state engine/transactional adapter + app authority store | Reuse verified transition/fencing mechanics while the host owns durable state and policy. Keep revocation/recovery state; minimization is separate from agent-output deletion; generic get/set is insufficient |

The current demo lacks complete projection, principal/consent and support
knowledge. A future adapter must declare current revision-bound grammar support;
known unsupported yields `schema_unsupported`, unknown/stale support yields
`input_unknown`. No agent-deletion evidence is needed for this mode alone.
Stricter unenforceable retention still yields `retention_unsupported`; applicable
policy denial is separate. These reason codes describe normative compatibility,
not newly implemented Calcu API errors.

## Evidence and remaining decisions

`contract_example.py` now constructs the explicit mode using fixed synthetic
`calculation.sample` data, fresh example surface version, exact Grant/consent
projection and existing hashes. It deliberately does **not** substitute that
sample classification for the proposed live classes above. Its synthetic,
expired identity and `publishable: false` status remain unchanged.

Tests check deterministic construction, closed retention grammar, changed
surface/Grant hashes, unchanged four-operator schema and matching unconfirmed
consent projection. They do not prove a real issuer rejects stale consent or
that a runtime independently validates projection. Existing RFC conformance
tests cover other schema/projection cases; neither suite proves Calcu support.

Before closing the ADP-03 design/feasibility gate, review the candidate class maximum and credible known-
provenance controls, issuer/runtime integration feasibility, principal/preview
binding, app-owned lifecycle and selected-route applicability. Other principals'
and applicable application/enterprise policies still matter. No account-secret
inspection, provider certification or retention probe is needed for this design.

ADP-05/06/08 slices must exercise actual rejection of omitted/duplicate/extra
sources, changed class order/retention, caller projection, stale consent/hash,
unsupported mode, stricter policy and out-of-envelope output; rejection must
precede disclosure (and admission rejection precede engine execution). Include
revocation/session tests and zero credential leakage. These implementation tests
are accumulated during the slices, not required as completed ADP-08 evidence
before starting them. Record reusable SDK engineering separately from app
integration cost. ADP-02 still needs scoped budget/stop/exit approval despite the
selected SDK-first strategy. ADP-09 later stabilizes proven interfaces and tests
a second consumer; neither this design nor a fixture closes implementation gates.
