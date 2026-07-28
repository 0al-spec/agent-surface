# Action Execution Model

The Action Execution Model separates an action's immutable, manifest-pinned
semantics from the context of one invocation. It standardizes preview, resource
coordination, commit, and recovery without letting a caller turn low-risk
authority into a state-changing operation.

## Static Execution Modes

Every action declaration MUST contain exactly one `execution.mode` selected
from this table:

| Mode | Meaning | `side_effect` |
| --- | --- | --- |
| `read` | Read application state without changing domain or coordination state. | `false` |
| `dry_run` | Validate a possible later commit and predict its preconditions and effects without performing it. | `false` |
| `propose` | Produce a non-committed proposal or draft. | `false` |
| `reserve` | Acquire, renew, or release time-bounded application coordination state. | `true` |
| `commit` | Apply declared effects to application or external state. | `true` |
| `compensate` | Apply a new counter-effect intended to offset an earlier commit. | `true` |
| `revert` | Attempt to restore a declared prior state controlled by the application. | `true` |

The mode is a property of the action identifier in the pinned manifest. It is
not a caller-selectable privilege. The `mode` repeated in an Action Request
MUST equal the declaration for its `action_id`; the application MUST reject a
mismatch as `execution_mode_invalid` before performing any effect.

Each action MUST also declare a non-empty `execution.operation_id` that groups
the separately authorized stages of one logical operation. Sharing an
`operation_id` does not share authority. Every companion action has its own
`action_id`, scope, risk, approval, schemas, idempotency key, and receipt
requirements, and every invoked action MUST independently be present in the
grant's authoritative `actions` allow-list. Scope alone never authorizes an
action or a stronger companion stage.

The legacy example values `direct`, `write`, and `proposal_only` are not
standard modes. A publisher MUST use `read` or `propose` according to the
operation's semantics, `commit`, and `propose`, respectively. An application
does not need to implement every standard mode.

Actions in mode `read`, `dry_run`, or `propose` MUST declare
`side_effect: false`. Actions in mode `reserve`, `commit`, `compensate`, or
`revert` MUST declare `side_effect: true`, `idempotency: "required"`,
an `idempotency_normalization` object using `asp-json-normalization-v1`,
`receipt: "required"`, a non-empty `effects` array,
`input_hash_profile: "asp-jcs-sha-256"`, and
`execution_hash_profile: "asp-jcs-sha-256"`. Persisted proposals remain
non-committed domain artifacts but MUST support idempotency as specified in
Proposal-Only Surface Mode.

Ephemeral preview handles, deduplication records, audit records, and stored
proposal drafts are protocol bookkeeping for this classification. A `dry_run`
MUST NOT reserve a resource, exclude another actor, or mutate the target domain;
an operation that affects availability or concurrency uses `reserve` and is
state-changing.

## Companion Actions and Transitions

Companion stages use separate action identifiers:

```text
dry_run ---------------------> commit
   |                             |
   +----------> reserve ---------+
                                 |
                                 +----> compensate
                                 +----> revert

propose ----------------------> commit
```

A commit action MAY declare `dry_run_action`, `proposal_action`,
`reservation_action`, and `recovery_actions`. It MAY declare
`dry_run_required: true` or `reservation_required: true`; when either flag is
true, the corresponding action reference and valid request evidence are
required. A dry-run, proposal, or reservation-acquire action that leads to a
commit MUST declare `commit_action`. A recovery action MUST declare a non-empty
`target_actions` array.

Every companion reference MUST resolve in the same manifest snapshot, MUST NOT
reference the declaring action itself, and MUST use the same `operation_id`.
The referenced mode MUST match the reference: `dry_run_action` identifies a
`dry_run` action, `proposal_action` a `propose` action,
`reservation_action` a `reserve` acquisition action, and each
`recovery_actions` entry identifies the declared `compensate` or `revert`
mode. Every recovery entry MUST also contain a non-empty, unique `effect_ids`
array naming effects from the commit declaration and a positive integer
`recovery_window_seconds`. A `revert` entry can name
only `reversible` effects whose boundary is `internal`; a `compensate` entry
can name only `compensatable` effects. Effects declared `irreversible` or
`not_applicable` MUST NOT be named by a recovery relationship.

A `revert` action MUST declare `revert_preconditions_schema`. Its schema
defines the application-controlled revision and prior-state evidence required
to restore the named reversible effects without overwriting intervening work.

For a `commit` action, every effect declared `reversible` MUST be covered by at
least one `revert` entry, and every effect declared `compensatable` MUST be
covered by at least one `compensate` entry. A publisher that cannot provide the
corresponding independently authorized action MUST declare the effect
`irreversible` rather than advertise unsupported recovery.

References MUST be reciprocal: a companion's `commit_action` or
`target_actions` MUST identify the originating commit action and the same
effect ids and recovery window. A recovery declaration represents each target
as an object with `action_id`, `effect_ids`, and `recovery_window_seconds`, not
as an unscoped action string.

A direct commit remains valid when neither dry run nor reservation is required.
Even when a companion stage succeeded, a commit MUST repeat complete current
grant, credential, tuple, scope, resource, policy, approval, and schema
verification. A companion result is never inherited authority.

An issued grant's `actions` allow-list MUST be closed over required companion
dependencies. Including a commit with `dry_run_required: true` requires its
`dry_run_action`; including a commit with `reservation_required: true` requires
its reservation-acquire action and that acquisition's mandatory release action.
Including an acquisition action requires its `commit_action` and
`release_action`. Closure is recursive when the required commit has other
required stages. Optional proposal, renewal, compensation, and revert actions
need not be granted. The authorization server MUST reject an unclosed subset;
it MUST NOT silently add authority to close it.

The following fragment declares a commit stage. Its referenced actions are
separate declarations in the same surface:

```json
{
  "id": "branch.create",
  "scope": "repository.branch.write",
  "risk": "write",
  "side_effect": true,
  "approval": "user_or_app",
  "idempotency": "required",
  "idempotency_normalization": {
    "profile": "asp-json-normalization-v1"
  },
  "input_hash_profile": "asp-jcs-sha-256",
  "execution_hash_profile": "asp-jcs-sha-256",
  "execution": {
    "mode": "commit",
    "operation_id": "repository.branch.create",
    "dry_run_action": "branch.create.preview",
    "dry_run_required": true,
    "reservation_action": "branch.create.reserve",
    "reservation_required": true,
    "recovery_actions": [
      {
        "mode": "revert",
        "action_id": "branch.delete",
        "effect_ids": ["branch-create"],
        "recovery_window_seconds": 86400
      }
    ]
  },
  "preconditions_schema": "https://example.com/schemas/branch-create.preconditions.schema.json",
  "expected_effects_schema": "https://example.com/schemas/branch-create.expected-effects.schema.json",
  "actual_effects_schema": "https://example.com/schemas/branch-create.actual-effects.schema.json",
  "effects": [
    {
      "effect_id": "branch-create",
      "operation": "create",
      "resource_type": "git.branch",
      "visibility": "shared",
      "boundary": "internal",
      "reversibility": "reversible",
      "domain": "workflow"
    }
  ],
  "input_schema": "https://example.com/schemas/branch-create.input.schema.json",
  "input_schema_hash": "sha-256:<input-schema-digest>",
  "output_schema": "https://example.com/schemas/branch-create.output.schema.json",
  "receipt": "required"
}
```

Its reciprocal revert declaration can be:

```json
{
  "id": "branch.delete",
  "scope": "repository.branch.delete",
  "risk": "destructive",
  "side_effect": true,
  "approval": "runtime_and_app",
  "idempotency": "required",
  "idempotency_normalization": {
    "profile": "asp-json-normalization-v1"
  },
  "input_hash_profile": "asp-jcs-sha-256",
  "execution_hash_profile": "asp-jcs-sha-256",
  "execution": {
    "mode": "revert",
    "operation_id": "repository.branch.create",
    "target_actions": [
      {
        "action_id": "branch.create",
        "effect_ids": ["branch-create"],
        "recovery_window_seconds": 86400
      }
    ]
  },
  "revert_preconditions_schema": "https://example.com/schemas/branch-delete.revert-preconditions.schema.json",
  "effects": [
    {
      "effect_id": "branch-delete",
      "operation": "delete",
      "resource_type": "git.branch",
      "visibility": "shared",
      "boundary": "internal",
      "reversibility": "irreversible",
      "domain": "workflow"
    }
  ],
  "input_schema": "https://example.com/schemas/branch-delete.input.schema.json",
  "input_schema_hash": "sha-256:<input-schema-digest>",
  "output_schema": "https://example.com/schemas/branch-delete.output.schema.json",
  "receipt": "required"
}
```

## Execution Context and Binding

Every Action Request MUST carry an `execution` object with `mode` and a
non-empty `execution_id`. The runtime chooses an `execution_id` that is unique
within the grant and session and reuses it for exact idempotent retries of that
invocation. The identifier is correlation, not authority.

For an idempotency-required invocation, the application MUST enforce that one
tuple of `grant_id`, `session_id`, `action_id`, and `execution_id` maps to
exactly one idempotency key, `input_hash`, and, when required,
`execution_hash`. Reusing an execution id with any different value in the same
grant and session is an `idempotency_conflict`. Read,
ordinary dry-run, and non-persisted proposal invocations can omit the key or
execution hash, but their execution ids still cannot be rebound to different
requests. Reusing the same preview or approval under a new execution id does
not bypass their own single-use and exact-binding rules.

The request execution context can additionally contain `preview_id`,
`execution_token`, `execution_token_hash`, `preconditions_hash`,
`expected_effects_hash`, `reservation_id`, and `target_receipt_hash`. Unknown
standard-looking bare names are invalid; extensions MUST use
collision-resistant URI member names.

For `reserve`, `commit`, `compensate`, and `revert`, the request MUST carry
`execution_hash` computed with the Canonical Object Hash Profile over the
`execution` object with `execution_token` omitted. The runtime receipt and app
receipt MUST contain the same sanitized `execution` object and matching
`execution_hash`. A verifier MUST recompute the hash and reject a request or
receipt mismatch as `integrity_mismatch`.

When a raw `execution_token` is present, `execution_token_hash` is REQUIRED and
MUST match it. The runtime MUST omit the raw token from receipts, logs, prompts,
events, and agent-visible context. The application MUST treat the token as
preview evidence only and MUST reject it when the current grant credential,
tuple, surface, action, input, resource state, or approval is invalid.

Example commit context:

```json
{
  "mode": "commit",
  "execution_id": "exec_01J2COMMIT",
  "preview_id": "preview_01J2ABCDEF",
  "execution_token": "FW_vZMMelqPUDUmFfxSr1A",
  "execution_token_hash": "sha-256:tONJJscZ4IsDBfafODsBja4waqe1AtkpH54rXv_tPrk",
  "preconditions_hash": "sha-256:<preconditions-digest>",
  "expected_effects_hash": "sha-256:<expected-effects-digest>",
  "reservation_id": "reservation_01J2ABCDEF"
}
```

`input_hash` continues to bind the exact validated action input.
`execution_hash` separately binds protocol control context. Reusing an
idempotency key with the same input but a different `execution_hash` is an
`idempotency_conflict`; an application MUST NOT select whichever context is
more permissive.

## Preconditions and Effect Preview

An Impact Simulation is not a dry run. It copies only the static maximum effect
envelope for a known action and MUST NOT call the application, carry action
input, create a preview token, or claim application-observed preconditions or
`expected_effects`.

A commit that declares `dry_run_action` MUST declare both
`preconditions_schema` and `expected_effects_schema`. Those two members MUST be
absent when no dry-run action is linked; a direct commit expresses ordinary
optimistic-concurrency fields through its `input_schema`. A state-changing
action MAY declare `actual_effects_schema` to further constrain the mandatory
core Effect Model. A linked dry-run action MUST set
`input_hash_profile: "asp-jcs-sha-256"`, use the same `input_schema` as its
target commit, repeat the same `input_schema_hash` and structurally identical
`idempotency_normalization` declaration, and identify that commit through
`execution.commit_action`. The runtime MUST apply that declaration before
requesting approval, hashing, or sending the dry run, and the application MUST
perform the same fixed-point check. The dry run MUST NOT change target-domain
or coordination state.

The dry-run request MUST carry `input_hash`, and the application MUST recompute
it from the exact validated wire input. A preview-bound commit MUST present the
same exact normalized input and matching `input_hash`. A mismatched
normalization declaration is an invalid companion relationship; schema
equivalence or post-preview application normalization does not make a different
wire input the previewed input.

A successful dry run returns application-produced preconditions and expected
effects, their canonical hashes, and time-bounded evidence:

```json
{
  "result": "preview",
  "execution": {
    "mode": "dry_run",
    "execution_id": "exec_01J2PREVIEW"
  },
  "preview": {
    "preview_id": "preview_01J2ABCDEF",
    "commit_action_id": "branch.create",
    "execution_token": "FW_vZMMelqPUDUmFfxSr1A",
    "execution_token_hash": "sha-256:tONJJscZ4IsDBfafODsBja4waqe1AtkpH54rXv_tPrk",
    "expires_at": "2026-07-12T12:05:00Z"
  },
  "preconditions": {
    "repository_revision": "rev_456",
    "branch_absent": "feature-x"
  },
  "preconditions_hash": "sha-256:<preconditions-digest>",
  "expected_effects": [
    {
      "effect_id": "branch-create",
      "operation": "create",
      "resource_type": "git.branch",
      "resource_key": "example/repo:feature-x",
      "visibility": "shared",
      "boundary": "internal",
      "reversibility": "reversible",
      "domain": "workflow"
    }
  ],
  "expected_effects_hash": "sha-256:<expected-effects-digest>"
}
```

`preconditions` and `expected_effects` MUST validate against the target
commit's declared schemas. Their hashes use the Canonical Object Hash Profile.
The application MUST keep the preview immutable until expiry and MUST bind the
execution token to at least the application and tenant, `grant_id`,
`grant_hash`, `session_id`, `surface_hash`, dry-run and commit action ids,
`input_hash`, `preview_id`, `preconditions_hash`, `expected_effects_hash`,
relevant resource identities and revisions, and expiry. The token can be an
opaque handle to server state, or its decoded random octets can select or carry
application-authenticated state, but its wire representation remains the single
unpadded base64url string defined by the Canonical Object Hash Profile.

`preview_id` MUST be unique within the application and tenant and MUST NOT be
rebound to different input, effects, authority, or state. `expires_at` MUST be
an RFC 3339 UTC timestamp with the `Z` suffix. After a commit applies any effect,
the application MUST mark the preview token consumed by that action's
execution id and idempotency key. An exact idempotent retry can retrieve the
original result; another key or execution id MUST NOT reuse the consumed token.

A commit that relies on the preview MUST repeat `preview_id`, the raw token and
its hash, `preconditions_hash`, and `expected_effects_hash` in its execution
context. The application MUST verify all bindings and re-evaluate the declared
preconditions immediately before applying any effect. For app-controlled state,
the final precondition and reservation check and the mutation MUST be atomic.

Expiry, a changed revision, mismatched input or resource, a different grant or
surface, or more severe expected effects MUST fail before mutation. The
application MUST return `execution_token_expired`, `precondition_failed`, or
`effect_mismatch` as appropriate. It MUST NOT silently generate a new preview
and continue the commit.

A preview is a prediction, not a reservation or commit guarantee. Approval for
a previewed commit MUST bind at least `action_id`, execution mode, `input_hash`,
`preview_id`, and `expected_effects_hash`. If any of those values or the
approval-relevant effect presentation changes, the runtime or application MUST
obtain new approval.

## Resource Reservations

A reservation coordinates competing attempts against typed resources. It does
not authorize the holder, override application concurrency control, or promise
that a later commit will pass its preconditions.

A `reserve` declaration MUST fix one `execution.reservation.operation` value:
`acquire`, `renew`, or `release`. The operation is not request-selectable.
An acquisition declaration MUST identify `commit_action`, `kind` (`exclusive`
or `shared`), a positive integer `max_ttl_seconds`, mandatory `release_action`,
and `disconnect_behavior` (`retain_until_expiry` or `release`). It MAY identify
a `renew_action`; when present, a positive integer `max_renewals` is REQUIRED.
Renew and release declarations MUST reciprocally identify the
acquisition through `execution.reservation.acquisition_action` and use the same
operation id. The declared effect operation MUST be `reserve`, `renew`, or
`release` for acquisition, renewal, or release, respectively.

```json
{
  "id": "branch.create.reserve",
  "scope": "repository.branch.reserve",
  "risk": "write",
  "side_effect": true,
  "approval": "none",
  "idempotency": "required",
  "idempotency_normalization": {
    "profile": "asp-json-normalization-v1"
  },
  "input_hash_profile": "asp-jcs-sha-256",
  "execution_hash_profile": "asp-jcs-sha-256",
  "execution": {
    "mode": "reserve",
    "operation_id": "repository.branch.create",
    "commit_action": "branch.create",
    "reservation": {
      "operation": "acquire",
      "kind": "exclusive",
      "max_ttl_seconds": 600,
      "disconnect_behavior": "release",
      "renew_action": "branch.create.reservation.renew",
      "max_renewals": 2,
      "release_action": "branch.create.reservation.release"
    }
  },
  "effects": [
    {
      "effect_id": "branch-name-reservation",
      "operation": "reserve",
      "resource_type": "git.branch_name",
      "visibility": "private",
      "boundary": "internal",
      "reversibility": "reversible",
      "domain": "workflow"
    }
  ],
  "input_schema": "https://example.com/schemas/branch-reservation.input.schema.json",
  "input_schema_hash": "sha-256:<input-schema-digest>",
  "output_schema": "https://example.com/schemas/branch-reservation.output.schema.json",
  "receipt": "required"
}
```

The acquisition input schema MUST identify the complete target set and a positive integer
requested TTL no greater than `max_ttl_seconds`. Each target consists of
`resource_type` and an application-canonical `resource_key` that is stable
within issuer and tenant. The application MUST resolve aliases, case rules, and
equivalent locators to that canonical tuple before conflict checking; two
targets are equal when their canonical issuer, tenant, type, and key are equal.

An acquire operation over multiple targets MUST be atomic: either every target
is reserved or none is. Two `shared` reservations on the same target are
compatible. Any overlap where the existing or requested kind is `exclusive`
is a conflict and MUST fail the complete acquisition with
`reservation_conflict`. The response MUST NOT reveal another holder's identity
or grant details.

A successful acquisition returns and records in the app receipt a
`reservation_result` object containing `reservation_id`, `state: "active"`,
kind, targets, `commit_action_id`, `created_at`, and `expires_at`. This outcome
object is not added to the parent runtime receipt's request execution context.
The application MUST bind its authoritative reservation state to
the application and tenant, grant, runtime-agent-passport tuple, surface,
session, acquisition and commit action ids, `input_hash`, exact targets, kind,
and expiry. `reservation_id` alone is never sufficient to use, renew, release,
or consume the reservation.

A successful renewal also reports `reservation_result.state: "active"` with
the new expiry and an actual effect operation of `renew`. A successful explicit
release reports state `released` and an actual effect operation of `release`.
The app receipt MUST NOT report a state or effect operation inconsistent with
the declaration's fixed reservation operation.

An acquire request MUST omit `execution.reservation_id`. A renew or release
request MUST carry the active `reservation_id`, and a commit whose declaration
sets `reservation_required: true` MUST carry it. The application MUST reject a
missing value or wrong binding before mutation. A reservation id MUST be unique
within issuer and tenant and MUST NOT be rebound after consumption, release,
expiry, or invalidation. `created_at` and `expires_at` MUST be RFC 3339 UTC
timestamps with the `Z` suffix.

Reservation state transitions are:

```text
active -> consumed
active -> released
active -> expired
active -> invalidated
```

The effective expiry MUST NOT exceed the acquisition declaration's maximum or
the grant expiry. On renewal, the application computes the new expiry from the
time of successful renewal, not by adding duration to the old expiry, and again
caps it by `max_ttl_seconds` and grant expiry. A renewal input schema MUST carry
a positive requested TTL subject to the same cap. The application MUST reject a
renewal beyond declared `max_renewals`. Applications SHOULD impose additional
per-grant and per-resource limits on active reservations to prevent starvation. An
exact idempotent retry returns the original reservation and receipt.

Renew and release are independently granted, state-changing `reserve` actions
with their own idempotency keys and receipts. Grant revocation, grant expiry,
tuple invalidation, or an incompatible surface change MUST immediately
invalidate affected active reservations. A successful commit MUST atomically
validate and mark its required reservation `consumed`. A commit that performs
no effect MUST leave the reservation active for a retry, explicit release, or
expiry unless the response explicitly reports that it was invalidated.

## Compensation and Revert

`compensate` and `revert` are recovery actions, not rollback flags on the
original request. A commit lists them in `execution.recovery_actions`; each
recovery declaration reciprocally lists objects containing the supported
original `action_id` and exact `effect_ids` in `execution.target_actions`.
The reciprocal entry also repeats the positive `recovery_window_seconds`.

A compensation applies a new semantic counter-effect, such as issuing a refund
after a charge. It can be partial and does not claim that the original state or
external world was restored. A revert is appropriate only when the application
can define and conditionally restore a prior app-controlled state, such as a
document revision. Neither mode erases the original effect or receipt, and
neither is a universal transactional rollback guarantee.

For every effect advertised as `reversible`, the original commit's app receipt
MUST include a `revert_evidence` entry containing `effect_id`, an opaque
`prior_state_ref`, and `committed_state_revision`. The prior-state reference is
receipt-bound evidence and a lookup handle, not authority. The application MUST
retain the referenced state for the declared recovery window; otherwise the
effect cannot be advertised as reversible.

A revert request MUST carry `revert_preconditions` in its business input. The
object MUST validate against `revert_preconditions_schema` and bind the target
effect id, prior-state reference, and expected current revision from the
verified target receipt. Immediately before restoring state, the application
MUST atomically verify that the current revision is the target receipt's
`committed_state_revision`. A mismatch returns `revert_conflict` without
mutation; a prior-state reference MUST NOT be accepted as a credential or used
with another target receipt.

A recovery request MUST carry the hash of the original application receipt:

```json
{
  "mode": "compensate",
  "execution_id": "exec_01J2REFUND",
  "target_receipt_hash": "sha-256:<original-app-receipt-digest>"
}
```

`target_receipt_hash` is a causal cross-action link. It MUST NOT be placed in
`parent_receipt_hash`, because the parent link joins the runtime and app
receipts for the same action, input, grant, and idempotency key. Recovery starts
a new runtime-to-application receipt chain and repeats `target_receipt_hash` in
both receipts.

The application MUST retrieve and verify the complete target app receipt,
recompute its `receipt_hash`, and load the exact manifest snapshot named by its
`surface_hash`. That target commit declaration MUST have authorized the same
recovery action, mode, operation id, and target effect ids. The current recovery
declaration MUST contain the reciprocal mapping. When the target and current
surface hashes differ, the complete original-action and recovery-action
declaration objects in both snapshots MUST be byte-identical after JCS
serialization. This exact pair is the recovery compatibility projection for
the current profile; looser mappings require a future profile. A mismatch MUST
be rejected as `recovery_not_supported` rather than reinterpret old effects
under a new surface. The application MUST also validate tenant and resource
relationships.
The target receipt timestamp MUST fall within the declared recovery window.
An application advertising recovery MUST retain the relevant manifest snapshots
and target receipts for its declared recovery window; unavailable evidence
means recovery is unsupported, never that the current surface can be
substituted.

The target receipt MUST record `effect_outcome` as
`applied` or as a reconciled `partially_applied` outcome with the exact
recoverable `actual_effects`. A denied or `not_applied` action has nothing to
recover. An `unknown` outcome is ineligible for compensation or revert in this
profile because the immutable target receipt does not prove the recoverable
effect. It MUST return `recovery_not_supported`. A future
reconciliation-evidence profile can define a separate app-authoritative
cross-linked object; until then, any corrective action is an independently
authorized operation rather than recovery under this target receipt.

The target receipt and its original grant are evidence, not authority. Recovery
MUST use a currently valid Grant Credential that independently permits the
recovery action, scope, resources, risk, and approval; it MAY use a different
grant from the original action.

Every recovery input schema MUST identify a non-empty subset of the effect ids
authorized by the reciprocal manifest relationship and, for
quantified effects such as a charge or transfer, the amount or quantity to
recover. The application MUST maintain authoritative remaining-effect state
keyed by target receipt and target effect. It MUST aggregate every compensation
or revert action, grant, execution id, and idempotency key against that single
state and prevent cumulative recovery from exceeding the confirmed unrecovered
effect. Per-action attempt records MAY be stored separately but MUST NOT create
independent remaining balances. A non-quantified effect can be recovered
at most once unless its action-specific schema defines a safe repeatable
recovery unit. An exact retry under the original idempotency key returns its
original result. A new request whose target is already exhausted or whose
amount exceeds the remaining effect MUST return `recovery_already_applied` and
MUST NOT emit another counter-effect.

Every recovery action MUST also be idempotent per request and MUST record
whether its outcome is `applied`, `partially_applied`, `not_applied`, or
`unknown`. A revert MUST
recheck its declared prior-state preconditions and return `revert_conflict`
without mutation when they no longer hold. An external effect whose outcome is
uncertain MUST return and receipt `unknown`; a runtime MUST NOT blindly retry it
under a new idempotency key.

# Risk Taxonomy

Every action SHOULD have a standard risk label. Runtimes can map risk labels to
local policy defaults.

| Risk | Meaning | Suggested Default |
| --- | --- | --- |
| `read` | Reads data visible under the grant. | Allow if scope permits. |
| `propose` | Produces a draft, suggestion, or patch without committing it. | Allow and audit. |
| `write` | Mutates app state. | Ask or require app approval. |
| `public_side_effect` | Publishes, sends, or exposes user-visible or public content. | Ask; often require app-side confirmation. |
| `external_side_effect` | Sends data or causes effects outside the app boundary. | Ask; often deny by default. |
| `financial_side_effect` | Charges, refunds, purchases, invoices, payroll. | Always require explicit approval. |
| `destructive` | Deletes, closes, revokes, disables, or irreversibly changes state. | Deny by default or require step-up approval. |
| `privileged` | Changes permissions, secrets, tokens, admin settings, or access policy. | Deny by default. |

Risk labels are ordered by increasing severity from `read` to `privileged`.
The labels are not mutually exclusive properties of an action: a single action
can plausibly be described by several of them. When more than one label
applies, the action MUST carry the most severe applicable label. For example,
`invoice.refund.request` is both a mutation and a financial operation; it MUST
be labeled `financial_side_effect`, not `write`.

The `risk` label and the `side_effect` flag MUST be consistent: an action
labeled `write` or a more severe label MUST declare `side_effect: true`, and
an action labeled `read` MUST declare `side_effect: false`.

Applications MAY define extension risk labels, but each extension label MUST be
a collision-resistant URI whose specification defines a conservative mapping
to one standard risk label as its minimum severity. A runtime that does not
support that exact mapping MUST reject the surface or action as
`surface_incompatible`; it MUST NOT infer severity from a human-readable
description, identifier spelling, icon, or local similarity rule. A bare
unrecognized label is invalid.

Impact Simulation uses this same conservative mapping only to select the
bounded set of unrequested examples. It MUST NOT change an action's risk,
downgrade an extension, or use the selection order as a safety or authority
ranking.

## Risk Explanation UI Hints

This draft assigns the following core feature identifier:

```text
agent-surface/feature/risk-explanation-ui-hints
```

The identifier names the optional manifest and conformance feature defined in
this section. It is not a negotiated profile, Grant constraint, consent
artifact, approval mode, or authority-bearing capability. Presence is declared
only by a valid `risk_explanation` member on an action; absence means that the
publisher supplies no standardized prose for that action and MUST NOT be
rendered as no risk.

An action MAY contain one `risk_explanation` object:

```json
{
  "default_language": "en",
  "localizations": [
    {
      "language": "en",
      "summary": "Publishes a review for other repository users.",
      "effect_summaries": [
        {
          "effect_id": "review-publish",
          "summary": "Creates an irreversible shared communication record."
        }
      ]
    }
  ]
}
```

The `risk_explanation` object, every localization, and every effect summary are
closed objects. `default_language` and `localizations` are REQUIRED and no
other member is allowed. A localization contains exactly `language`, `summary`,
and `effect_summaries`; an effect summary contains exactly `effect_id` and
`summary`. A Surface Publisher MUST NOT publish a present object that violates
this section. A consumer that nevertheless receives one MUST atomically
suppress the complete hint and use its machine-derived risk and effect
presentation; it MUST NOT display or otherwise interpret only the fields it
recognizes. Suppression does not turn malformed prose into authority and MUST
NOT be rendered as no risk.

`localizations` contains between one and sixteen entries. `default_language`
and every `language` are canonical lowercase ASCII language tags no longer than
63 characters and MUST match this complete regular expression:

```text
^[a-z]{2,8}(?:-[a-z]{4})?(?:-(?:[a-z]{2}|[0-9]{3}))?(?:-(?:[a-z0-9]{5,8}|[0-9][a-z0-9]{3}))*$
```

This is the ASP-canonical lowercase wire form for a deliberately restricted,
structurally well-formed subset of RFC 5646: a language subtag, optional
script, optional region, and zero or more variants. It intentionally excludes
extlang, extension, private-use, and grandfathered forms and does not claim
registry-based canonicalization. Variant subtags within one value MUST be
unique. Localization entries are unique by `language` and sorted by unsigned
lexicographic order of their ASCII bytes. Exactly one entry MUST have a
`language` equal to `default_language`.

Every `summary` is plain text containing between one and 512 Unicode code
points. It MUST NOT contain a C0 or C1 control character or any Unicode
`Bidi_Control` character: U+061C, U+200E, U+200F, U+202A through U+202E, or
U+2066 through U+2069. A presenter MUST treat it as inert text, escape it for
the output context, and place each string inside a presentation-controlled
bidirectional-isolation boundary. It MUST NOT interpret the string as HTML,
Markdown, a URI, a template, executable content, a policy rule, or an
instruction. The strings MUST be safe for every user allowed to discover that
manifest and MUST NOT contain credentials, secrets, hidden policy content, or
instance-specific resource data.

For each localization, `effect_summaries` contains exactly one entry for every
member of the parent action's `effects` array, with the same `effect_id` values
in the same declaration order. An action that omits `effects` has an empty
`effect_summaries` array in every localization. An unknown, missing, duplicate,
reordered, or extra effect id is invalid. Complete per-language coverage
prevents a publisher from omitting a less favorable effect only in one
localization; the prose still does not replace the Effect Model declaration.

A Runtime Mediator that claims this feature chooses one complete localization
using RFC 4647 Lookup against zero to sixteen ordered local language
preferences. Each preference uses the same ASP-canonical language form;
duplicates have no additional effect. When the list is empty or Lookup finds no
available tag, the runtime uses the exact `default_language` entry. It MUST NOT
combine a summary from one localization with effect summaries from another. A
locally generated translation is runtime-authored content and MUST be labeled
separately; it MUST NOT be represented as publisher text.

Risk explanation text is an untrusted publisher hint. The publisher MUST NOT
describe a lower risk, narrower effect, stronger recovery guarantee, weaker
approval requirement, or more certain outcome than the machine-readable action
contract. Regardless of prose, a user-facing runtime MUST keep the canonical
action id, standard risk label or supported extension mapping, execution mode,
approval mode, and every material effect and recovery limitation visible and
distinguishable as machine-derived semantics. It MUST NOT use the prose to
change capability-match status or ranking, local or enterprise policy,
approval, admission, scope, effect validation, or receipt production. It MUST
NOT place publisher prose in an agent system prompt, tool instruction, or other
privileged instruction channel.

The complete object is part of the manifest hashing view and needs no separate
hint hash. A runtime retrieves it only from the exact verified manifest
snapshot and keys any extracted display cache by (`issuer`, `app_id`,
`surface_version`, `surface_hash`, action id, selected language). It MUST NOT
accept a detached caller- or agent-supplied copy as publisher text. Any change
to a hint changes `surface_hash` and `surface_version` and makes an in-progress
Consent Preview or Human Elicitation bound to the former snapshot stale.
Existing Grants remain bound to their exact retained snapshot; a new hint MUST
NOT be overlaid on an old Grant or used to reinterpret its action.

# Effect Model

Risk is a policy-oriented severity label. Effects are independent,
machine-readable descriptions of what an action can change. A state-changing
action MUST declare a non-empty `effects` array whose entries contain exactly
the standard members below unless collision-resistant extension members are
used:

- `effect_id`: non-empty identifier unique within the action
- `operation`: `create`, `update`, `delete`, `publish`, `send`, `execute`,
  `transfer`, `grant`, `revoke`, `deploy`, `reserve`, `renew`, or `release`
- `resource_type`: non-empty application resource type
- `visibility`: `private`, `shared`, or `public`
- `boundary`: `internal` or `external`
- `reversibility`: `reversible`, `compensatable`, `irreversible`, or
  `not_applicable`
- `domain`: `data`, `communication`, `workflow`, `financial`, `security`,
  `identity`, `authorization`, `deployment`, or `configuration`

An extension value for any enumerated member MUST be a collision-resistant URI.
Its specification MUST define a conservative mapping to a standard visibility,
boundary, reversibility, and risk floor and MUST define comparison with its
expected and actual values. A verifier that does not support that mapping MUST
reject the surface or action as `surface_incompatible`; it MUST NOT assume an
unknown extension is less severe. Bare unrecognized values are invalid. Effect
identifiers are stable within one surface version and allow a runtime to match
declared, expected, and actual effects without relying on array position.

The manifest declaration is the maximum effect envelope for the action. A
publisher that permits materially different alternatives MUST declare each
alternative effect rather than using a less severe generic value. Within the
standard values, `public` is more exposed than `shared`, which is more exposed
than `private`; `external` crosses a stronger boundary than `internal`; and
`irreversible` is less recoverable than `compensatable`, which is less
recoverable than `reversible`. `not_applicable` is valid only for an operation
that does not claim recovery semantics.

An expected or actual effect exceeds the declaration when it:

- uses an undeclared `effect_id`, operation, resource type, or domain
- has greater visibility or crosses a stronger boundary
- is less recoverable than declared
- identifies a resource not authorized by the grant and the action's declared
  target, container, or produced-output semantics
- otherwise violates the action's expected- or actual-effects schema

Actions in mode `read`, `dry_run`, and `propose` MUST omit `effects` because
they do not commit the predicted target-domain effects. A `reserve` action MUST
declare its coordination effect. Actions in mode `commit`, `compensate`, and
`revert` MUST declare every maximum domain or external effect they can
intentionally produce.

The action declaration, `risk`, and effects MUST be consistent. At minimum:

- a public effect requires `public_side_effect` or a more severe risk
- an external effect requires `external_side_effect` or a more severe risk
- a `financial` effect requires `financial_side_effect` or a more severe risk
- a state-changing `security`, `identity`, or `authorization` effect requires
  `privileged`
- a delete or revoke that is irreversible requires `destructive` or
  `privileged`

When several rules apply, the action MUST use the most severe applicable risk.
Effect dimensions do not reduce scope, approval, or grant checks and MUST NOT be
used to downgrade a more severe risk label.

`expected_effects` is an application-produced prediction for one validated
input and state snapshot. `actual_effects` is the application's record of what
the invocation applied or may have applied. Both are arrays of effect entries
under the mandatory core Effect Model; each declared `effect_id` MUST appear at
most once in either array. Standard instance members `resource_key`,
`resource_keys`, and `safe_summary` MAY appear without an application-specific
schema. An `expected_effects_schema` or `actual_effects_schema` can further
constrain entries and define additional instance members. Multiple instances of
one declared effect are represented through `resource_keys` or another
schema-defined value, not duplicate `effect_id` entries. Their canonical hashes
bind the exact arrays, including extension members and array order.

The `maximum_effects` member of an Impact Simulation example is instead an
exact copy of this manifest envelope. It contains no resource keys or
input-specific prediction and MUST NOT be presented as an `expected_effects`
array, dry-run result, or guarantee of the actual outcome.

Before a commit, the application MUST reject an expected effect that exceeds
the manifest envelope. If the expected effects differ from the approved
`expected_effects_hash`, the application MUST fail with `effect_mismatch` and
require a new preview and approval. It MUST NOT silently approve the changed
impact on the user's behalf.

When an effect was or may have been attempted, the response and app receipt MUST
include `actual_effects`, `actual_effects_hash`, and `effect_outcome`. The
outcome is `applied`, `partially_applied`, `not_applied`, or `unknown`. A
successful internal atomic mutation normally reports `applied`. A denial or
validation failure before any attempt MAY omit those fields; if it reports
`not_applied`, it uses an empty `actual_effects` array and its canonical hash.

An application MUST NOT report plain success when an actual effect exceeded the
declared or approved envelope, only part of an external operation completed, or
the external outcome is unknown. A pre-effect mismatch returns
`effect_mismatch` with no mutation. Once an effect may have occurred, the app
records the safest accurate `partially_applied` or `unknown` outcome and
requires explicit reconciliation before a new attempt; it MUST NOT describe
that condition as a retryable preview mismatch.

# Approval Semantics

Actions SHOULD declare an approval mode:

| Approval | Meaning |
| --- | --- |
| `none` | Runtime MAY execute if grant and policy allow. |
| `runtime` | Runtime MUST obtain local user approval before sending the action. |
| `app` | App MUST obtain or verify app-side approval before committing. |
| `user_or_app` | Either a runtime approval or app-side approval MAY satisfy the requirement, depending on grant caveats. |
| `runtime_and_app` | Both runtime-side and app-side approval are required. |

An action's Risk Explanation UI Hint can accompany an approval presentation
only as labeled application-authored prose from the exact pinned manifest. It
MUST NOT satisfy an approval mode, alter the required producer roles, replace
the canonical risk or effect presentation, or become part of the approval
decision binding except through the already required `surface_hash`. A stale or
detached hint is discarded. Approval evidence for an old Grant remains
interpreted under that Grant's retained snapshot; a new snapshot follows the
ordinary fresh preview, policy, and approval rules and does not rewrite the old
evidence.

An Impact Simulation outcome is likewise not invocation approval. A
`covered` example MUST NOT satisfy an approval mode, create approval evidence,
or be included in an approval binding. Consent confirmation authorizes only the
subsequent Grant request; every invocation continues to require its exact
policy decision and approval evidence.

Approval records SHOULD be linked into action receipts. The base profile permits
an opaque approval reference. A Grant selecting the Approval Receipt Profile
instead uses the complete hash-bound, role-indexed evidence defined below.

The `runtime` and `user_or_app` modes allow a runtime-side approval to satisfy
the requirement. In those modes the application is accepting the runtime's
assertion that a local user approval occurred. To keep this compatible with
the rule that an application MUST NOT accept a runtime's self-assertion of
authority, that acceptance MUST be an explicit grant caveat presented to the
user at consent time, not a silent default. Action requests that rely on a
runtime-side approval SHOULD carry an approval reference so the decision can be
linked into receipts and audited. Under the Approval Receipt Profile, the
Grant's per-action rule MUST explicitly accept the `runtime` producer role and
the request MUST carry the verified runtime Approval Receipt hash. Applications
that do not want to accept runtime approval assertions MUST declare `app` or
`runtime_and_app` for the affected actions or issue a `user_or_app` Grant rule
that accepts only `application`.

Approval for a state-changing invocation MUST bind the exact action id,
manifest-declared execution mode, `idempotency_key`, `input_hash`, and
`execution_hash`. When a
preview is used, it MUST additionally bind `preview_id` and
`expected_effects_hash`; when a reservation or recovery target materially
affects the decision, it MUST bind `reservation_id` or `target_receipt_hash`.
An approval for `dry_run`, `propose`, or `reserve` MUST NOT be reused as
approval for `commit`, `compensate`, or `revert`. Expired evidence, changed
preconditions, changed expected effects, a different companion action, or a
different execution hash requires a new policy decision and any required user
approval.

## Policy Decision Object

A runtime or application that records why an action was allowed, denied, or
paused for approval MUST use a `policy.decision` object. The object explains one
component's final policy evaluation; it is evidence for audit and user
explanation, not authority that another component must accept.

```json
{
  "type": "policy.decision",
  "decision_id": "pdec_runtime_01J2ABCDEF",
  "enforcer": {
    "type": "runtime",
    "id": "application_runtime_456"
  },
  "outcome": "allow",
  "policy": {
    "id": "local-agent-action-policy",
    "version": "2026-06-25"
  },
  "reason_code": "approval_satisfied",
  "matched_rules": ["writes.require_local_approval"],
  "safe_to_show": "The requested write is within the grant and was approved.",
  "evaluated_at": "2026-06-25T16:29:59Z",
  "policy_decision_hash": "sha-256:<base64url-digest>"
}
```

`type`, `decision_id`, `enforcer`, `outcome`, `policy`, `reason_code`,
`matched_rules`, `safe_to_show`, `evaluated_at`, and `policy_decision_hash` are
REQUIRED. `outcome` MUST be `allow`, `deny`, or `require_approval`.
`enforcer.type` MUST be `runtime`, `application`, or `enterprise`; `enforcer.id`
identifies the component whose policy was evaluated. `policy.id` and
`policy.version` identify the applied policy snapshot. Identifiers and
`safe_to_show` are non-empty strings. `matched_rules` is an array of unique
strings. `evaluated_at` is an RFC 3339 UTC timestamp with the `Z` suffix.

`reason_code` is the primary stable machine-readable explanation. This draft
defines `policy_allowed`, `approval_required`, `approval_satisfied`,
`approval_denied`, `scope_denied`, `resource_denied`, `binding_invalid`,
`limit_exceeded`, `local_policy_denied`, and `app_policy_denied`. Extensions
MUST use a collision-resistant URI. `matched_rules` contains stable, non-secret
rule identifiers and MAY be empty when disclosure would reveal policy
internals.
`safe_to_show` MUST be suitable for display to the affected user and MUST NOT
contain secrets, credentials, hidden rule content, or sensitive resource data.

The standard reason codes are valid only with these outcomes:

| Outcome | Allowed standard reason codes |
| --- | --- |
| `allow` | `policy_allowed`, `approval_satisfied` |
| `require_approval` | `approval_required` |
| `deny` | `approval_denied`, `scope_denied`, `resource_denied`, `binding_invalid`, `limit_exceeded`, `local_policy_denied`, `app_policy_denied` |

An extension reason-code specification MUST declare its allowed outcome. A
producer and verifier MUST reject a standard or extension reason code used with
an incompatible outcome.

When the Purpose- and Task-Bound Agent Grant Profile is selected, the complete
exact binding, current issuer-owned record states and relationship, action,
target resources, normalized input, mode, and effects are mandatory policy
inputs. The Policy Decision wire shape does not repeat the binding. Its
enclosing action and receipt context carries the `grant_hash` that commits to
the Grant, and a detached Policy Decision is never binding proof of a purpose
or task. `matched_rules` and `safe_to_show` MUST NOT reveal hidden purpose
policy, raw task inputs, another user's record, or an issuer-only label. An
application MUST evaluate its own current records and MUST NOT accept a runtime
`allow` decision as proof that the binding is active or that the action fits
its purpose.

The producer MUST compute `policy_decision_hash` with the Canonical Object Hash
Profile. A receipt MUST include the complete decision that directly determined
its producer's outcome and repeat the matching hash at receipt top level. A
runtime and application normally produce different decisions and hashes; an
application MUST NOT treat a runtime decision as authority to widen the Agent
Grant or bypass its own checks.

# Idempotency

Every action in mode `reserve`, `commit`, `compensate`, or `revert` MUST support
idempotency. A persisted proposal MUST support it as defined in
Proposal-Only Surface Mode.

Requests in mode `reserve`, `commit`, `compensate`, or `revert`, and requests
for a persisted proposal, MUST include `idempotency_key` in the body. In the
direct ASP HTTP binding they MUST also send the same value in
`Idempotency-Key`. An encapsulating HTTP-based binding defines its own carrier;
the ASP-over-MCP Binding Profile intentionally omits that outer header and
carries the semantic key only in its reconstructed Action Request. The
application MUST reject a missing required key as `schema_invalid` before any
effect. Other requests MAY include a key for retry correlation.

Example:

```json
{
  "idempotency_key": "idem_01HX...",
  "action_id": "comment.create"
}
```

## Idempotency Input Normalization

Every action with `idempotency: "required"` MUST publish a manifest-pinned
normalization declaration. This draft defines one profile:

```json
{
  "profile": "asp-json-normalization-v1",
  "defaults": {
    "/notify_subscribers": false
  },
  "unordered_arrays": ["/labels"]
}
```

`defaults` is an optional object whose member names are RFC 6901 JSON Pointers
and whose values are literal I-JSON defaults. `unordered_arrays` is an optional
array of unique RFC 6901 JSON Pointers. An omitted member has the same meaning
as an empty object or array. The v1 declaration contains exactly `profile` and
those two optional members; an unknown member invalidates the action rather
than being ignored as a transform. The declaration is part of the manifest
hashing view; changing a rule requires a new `surface_version` and
`surface_hash`.

The `asp-json-normalization-v1` algorithm is:

1. Parse the action input as I-JSON and validate it against the exact pinned
   `input_schema` without coercion, default insertion, or member removal.
2. Deep-copy that JSON value. Process default pointers by increasing pointer
   depth and then unsigned lexicographic order of their UTF-8 pointer bytes. A
   pointer MUST traverse object members only and name an object member. When
   its parent exists and the member is absent, insert the declared literal
   value. An explicit `null` is present and MUST NOT be replaced. An absent
   parent is unchanged. A present non-object ancestor contradicts the
   declaration and makes the action surface incompatible.
3. Process `unordered_arrays` pointers in unsigned lexicographic order of their
   UTF-8 bytes. A present target MUST be an array. Serialize each element
   independently with RFC 8785 JCS and sort the elements by unsigned
   lexicographic order of those canonical UTF-8 bytes. Preserve duplicate
   elements; an action requiring uniqueness MUST express it in `input_schema`.
   A present non-array target contradicts the declaration and makes the action
   surface incompatible.
4. Validate the resulting value against the same `input_schema` again.
5. Compare the result with the received JSON data model, ignoring only object
   member serialization order. The application MUST reject a non-fixed-point
   value as `input_not_normalized` before idempotency lookup, budget admission,
   policy approval, receipt creation, or any effect. It MUST NOT silently
   replace the received input.

A surface is invalid when a pointer is malformed, traverses an array, a default
pointer is an ancestor of another default pointer, a default pointer descends
through an unordered array, or applying its declarations can produce a value
that violates the pinned input schema. The schema MUST guarantee that every
present ancestor traversed by a default pointer is an object and every present
`unordered_arrays` target is an array; admitting `null`, a scalar, or another
type at those positions is an invalid action declaration. An
unordered-array rule is valid only when element order cannot change validation,
authorization, approval, target selection, or effects. A default is valid only
when application behavior for omission is exactly the behavior of the declared
literal. A contradiction discovered while loading or processing the pinned
surface fails as `surface_incompatible` before lookup, budget admission, or
effect; an implementation MUST NOT ignore the offending rule. Publishers MUST
NOT use these rules to hide a material choice from consent or approval.

The profile performs no trimming, case folding, Unicode normalization, URI or
timestamp normalization, numeric-string coercion, member removal, array
deduplication, or implicit use of JSON Schema `default` annotations. Absent and
explicit `null` remain distinct. Future profiles that add transforms MUST use a
collision-resistant URI identifier and define deterministic validation,
ordering, and fixed-point rules. A runtime MUST reject an unsupported profile
as `surface_incompatible` rather than approximate it.

The runtime MUST normalize before deriving approval input, computing
`input_hash`, producing its receipt, or transmitting the Action Request. Every
idempotency-required Action Request MUST carry that `input_hash`, including a
persisted proposal request. The
application independently recomputes the fixed point before trusting the hash
or consulting an idempotency record. For example, declarations for a default
`/notify_subscribers: false` and unordered `/labels` make these caller inputs
equivalent:

```json
{"body":"x","labels":["urgent","bug"]}
```

```json
{"body":"x","labels":["bug","urgent"],"notify_subscribers":false}
```

Both are sent on the wire in the second fixed-point form. The existing
`input_hash` therefore commits to the normalized value; no second semantic hash
is introduced. A request that omits the default or sends the array out of order
is retryable after local normalization because rejection does not claim its
idempotency key.

The application MUST ensure repeated requests with the same idempotency key and
same normalized-wire `input_hash` do not repeat the side effect. If the same key
is reused with a different normalized-wire `input_hash`, the application MUST
return `idempotency_conflict` without performing an effect.

Idempotency keys are scoped to the grant and action: the application MUST
treat a request as a duplicate only when the same key is presented under the
same `grant_id` and `action_id`. On a duplicate request, the application
SHOULD return the original result and receipt reference rather than an error,
so a retrying runtime can converge on the outcome of the first attempt.
Applications SHOULD retain idempotency state at least for the remaining
lifetime of the grant and SHOULD document their retention window.

The application checks an exact completed record before reserving an
application-authoritative write or cost budget. The runtime likewise reuses its
existing logical tool/model dispatch record instead of charging a transport
retry. A conflict or pre-admission denial consumes no application write or
application-cost budget, although a runtime tool dispatch that already reached
the application remains one runtime-authoritative tool call. Unknown outcomes
retain their original reservations until authoritative reconciliation.

Because one action id has exactly one static execution mode, the action id also
binds the mode for idempotency. The application's stored idempotency record for
a state-changing action MUST additionally bind `input_hash` and
`execution_hash`. Reuse of the same key with a different execution id, preview,
precondition hash, expected-effects hash, reservation, or recovery target
therefore returns `idempotency_conflict` even when the business input is
unchanged. A runtime MUST use distinct idempotency keys for different companion
action ids.

When Approval Receipt is selected, the application MUST also bind the final
role-indexed Approval Receipt hash set into that same idempotency record before
effect admission. A duplicate with the same runtime-side request evidence
returns the original result and final application role map. The same key with a
different runtime Approval Receipt or any attempt to substitute the stored
application receipt is `idempotency_conflict` and MUST NOT reopen approval or
admit another effect.

The application MUST also maintain the execution-id mapping defined by the
Action Execution Model. A new key with an old execution id, preview token, or
approval is a conflict, not a new invocation. Successful commit consumes its
preview evidence for that execution id and key; only an exact retry can obtain
the original immutable result.

After authenticating the caller and tuple, the application SHOULD check for an
exact completed idempotency record before rejecting mutable execution evidence
that expired only after the original effect. An exact retry of a completed
commit returns the original result and receipt even when its preview token has
since expired or its reservation is now `consumed`; it MUST NOT repeat the
effect or require a new reservation. This rule does not reactivate a revoked
grant or require disclosure of an old result when current authorization policy
forbids it.

An exact retry under the Receipt Hash Chain profile MUST reuse the original
finalized runtime receipt and the same `parent_receipt_hash`; it MUST NOT create
a second policy receipt for the already-authorized side effect. The application
returns the original immutable app receipt. If the same grant, action,
idempotency key, and normalized input arrives with a different parent hash
because that runtime receipt carries a different Approval Receipt evidence set,
the `idempotency_conflict` rule above takes precedence. After the admitted
approval set is equal, a different parent hash is `integrity_mismatch`; the
application MUST NOT repeat the side effect or attach the original result to a
competing provenance chain.
