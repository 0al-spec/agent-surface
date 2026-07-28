# Receipts

## Receipt Requirements

Runtime and application action receipts produced under the corresponding
`producer_role` of the Receipt Producer Profile MUST include:

- receipt id
- receipt type
- receipt hash
- grant id
- grant hash
- session id
- session generation
- trace id
- producer span id
- linked parent trace id when a trust boundary restarted tracing
- action id
- app id
- user id or stable pseudonymous user reference
- runtime id
- agent id
- Agent Passport hash
- surface version
- surface hash
- policy decision and policy decision hash
- input hash
- sanitized execution context and execution hash for state-changing actions
- preconditions and expected-effects hashes when preview evidence is used
- reservation id when it was part of the request execution context, and an
  app-produced `reservation_result` with id and state when the operation
  created or changed reservation state
- target receipt hash for compensation or revert
- revert evidence for every effect advertised as reversible
- output hash
- actual effects, actual-effects hash, and effect outcome when an effect was or
  may have been attempted
- an opaque approval reference under the base profile, or the applicable
  role-indexed `approval_receipt_hashes` under the Approval Receipt Profile
- idempotency key
- producer-authoritative `budget_charges` with budget id, non-negative amount,
  and resulting receipt-grant-local ledger revision when the recorded operation
  consumed budget
- timestamp
- result
- error classification when failed

For action receipts, `receipt_type` is exactly `runtime` or `app` according to
the producer. The Approval Receipt Profile additionally defines
`receipt_type: "approval"` for its prerequisite decision object; it is not an
action receipt and follows the separate closed shape below.

Fields that do not apply to the recorded outcome, such as `output_hash` for a
denial before execution, MAY be omitted. The identity, authority, trace,
decision, and result fields that do apply MUST be present and internally
consistent.

A producer MUST report only charges from ledgers for which it is the accounting
authority. A pre-admission denial carries no application write or cost charge.
An exact idempotent replay returns the original immutable charge evidence and
MUST NOT create a second charge or revision. Budget evidence is audit data, not
authority to increase a limit or overwrite current ledger state.

A runaway guard record and its `session.pause` transition are control-plane
safety metadata, not an application action receipt. A fence reached before an
Action Request is dispatched MUST NOT fabricate an app receipt, actual effects,
or an application error response. An already dispatched action retains its
ordinary immutable response, budget evidence, effect outcome, and runtime or
application receipts; the guard MUST NOT rewrite them. A runtime MAY reference
`guard_id` in its local audit record, subject to the minimized retention rules
above.

For a child-grant operation, `ledger_revision` is the resulting revision of the
named counter in the receipt's own `grant_id` ledger. The same atomic charge can
also advance ancestor ledgers, but this field does not claim their revisions;
their current state remains available only from each ancestor's accounting
authority.

A receipt MUST NOT contain the raw `execution_token`. It carries the sanitized
execution context with `execution_token_hash`, allowing a verifier to recompute
`execution_hash` without receiving reusable preview evidence.

## Approval Receipt Profile

The optional Approval Receipt Profile replaces an opaque approval reference
with immutable, typed evidence for one exact approval interaction. Its profile
identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1
```

An Approval Receipt records a decision; it is not a Grant Credential,
standalone action authority, proof that an effect occurred, or an instruction
to execute. Every component still verifies current Grant, session, surface,
policy, preview, reservation, precondition, effect-envelope, idempotency, and
budget state at its ordinary enforcement boundary.

### Grant Requirement

A semantic Grant request selects this profile with the following `audit`
fragment containing a closed `approval_receipt` object:

```json
{
  "audit": {
    "approval_receipt": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1",
      "requirements": [
        {
          "action_id": "comment.create",
          "accepted_roles": ["application", "runtime"],
          "max_age_seconds": 300
        }
      ]
    }
  }
}
```

`profile` and `requirements` are REQUIRED and unknown members are forbidden.
`requirements` is ordered by ascending Unicode code point of `action_id` and
contains exactly one entry for every requested action whose manifest approval
mode is not `none`; duplicate or extra actions are invalid. Each entry is
closed and contains exactly `action_id`, `accepted_roles`, and
`max_age_seconds`. `accepted_roles` is a non-empty array containing unique
values in ascending Unicode code point order from `application` and `runtime`.
`max_age_seconds` is a positive safe integer.

This v1 profile covers only approval-bearing actions in mode `reserve`,
`commit`, `compensate`, or `revert`. Every covered declaration therefore has
`idempotency: "required"`, the `asp-json-normalization-v1` declaration,
`input_hash_profile: "asp-jcs-sha-256"`, and
`execution_hash_profile: "asp-jcs-sha-256"`, and every invocation carries the
complete receipt tuple below. A semantic request selecting this profile while
including an approval-bearing `read`, `dry_run`, or `propose` action is invalid,
even when the proposal is persisted. Such actions require a separate Grant
using the base opaque approval reference, or a future profile with mode-specific
receipt bindings. The authorization server rejects an invalid OAuth request as
`invalid_authorization_details`.

The accepted roles MUST agree with the pinned action declaration:

| Manifest approval mode | Valid Grant requirement |
| --- | --- |
| `none` | No requirement entry. |
| `runtime` | Exactly `runtime`. |
| `app` | Exactly `application`. |
| `user_or_app` | Any non-empty subset of `application` and `runtime`. |
| `runtime_and_app` | Both `application` and `runtime`. |

This per-action rule is the explicit Grant caveat under which an application
can accept a runtime approval assertion. A generic `write_approval` constraint,
receipt schema, signature capability, or manifest approval mode does not add an
accepted role. In particular, a runtime MUST NOT choose `runtime` for a
`user_or_app` action unless the authoritative Grant requirement includes it.

The profile MUST be advertised in
`compatibility.approval_receipt_profiles`. A request accepting a runtime role
MUST also require `audit.local_receipt: "required"`; every request selecting the
profile MUST require `audit.app_receipt: "required"`. The authorization server
MUST reject an unadvertised profile, malformed or unclosed requirement set,
unsupported role, missing required action, extra action, incompatible mode, or
invalid maximum age. Under the OAuth profile these failures are
`invalid_authorization_details`.

The authorization server returns the same profile and a requirement projection
for the returned action subset. It MAY remove a role from a `user_or_app`
requirement and MAY lower `max_age_seconds`; it MUST NOT add a role or increase
the age. Requirements for removed actions are removed, and requirements for
retained approval-bearing actions remain present. The fixed-role `runtime`,
`app`, and `runtime_and_app` modes cannot change roles. Token exchange and child
Grant derivation apply the same attenuation and MUST NOT reuse an Approval
Receipt from the source or parent because its `grant_hash` and invocation tuple
differ. The complete effective object is part of the semantic Grant request
hash, authoritative Grant, `grant_hash`, consent views, token and introspection
responses, and server-side Grant state. It is never mutable in place.

### Approval Receipt Object

An Approval Receipt has `receipt_type: "approval"` and this wire shape:

```json
{
  "receipt_id": "receipt_approval_01J2APPROVE",
  "receipt_type": "approval",
  "receipt_hash": "sha-256:<approval-receipt-digest>",
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "session_id": "sess_456",
  "session_generation": 1,
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "b7ad6b7169203331",
  "action_id": "comment.create",
  "app_id": "code.example.com",
  "surface_version": "2026-06-25",
  "surface_hash": "sha-256:<base64url-digest>",
  "runtime": {
    "runtime_id": "application_runtime_456"
  },
  "actor_agent": {
    "agent_id": "local_agent_789",
    "identity_evidence_hash": "sha-256:<base64url-digest>"
  },
  "subject": {
    "user": "user_abc"
  },
  "idempotency_key": "idem_01HX7DS8AC6G9",
  "input_hash": "sha-256:<action-input-digest>",
  "execution": {
    "mode": "commit",
    "execution_id": "exec_01J2COMMENT"
  },
  "execution_hash": "sha-256:<action-execution-digest>",
  "policy_decision_hash": "sha-256:<approval-policy-decision-digest>",
  "policy_decision": {
    "type": "policy.decision",
    "decision_id": "pdec_approval_01J2ABCDEF",
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
    "safe_to_show": "The exact write request was approved.",
    "evaluated_at": "2026-06-25T16:29:59Z",
    "policy_decision_hash": "sha-256:<approval-policy-decision-digest>"
  },
  "approval": {
    "approval_id": "approval_01J2ABCDEF",
    "role": "runtime",
    "decided_by": "user",
    "valid_until": "2026-06-25T16:34:59Z"
  },
  "timestamp": "2026-06-25T16:29:59Z",
  "result": "approved"
}
```

The top-level object is closed except for `receipt_signatures` when the Receipt
Signing Profile is used. Every member shown is REQUIRED for an approved
receipt. `approval` is closed and contains exactly `approval_id`, `role`,
`decided_by`, and `valid_until`. `approval_id` is a collision-resistant
identifier unique within its producer. `role` is `runtime` or `application` and
MUST be accepted by the exact Grant requirement. `decided_by` is `user` or
`policy`; a runtime approval MUST use `user`. For role `runtime`, the Policy
Decision enforcer MUST be the exact bound runtime. For role `application`, it
MUST be the manifest application. `timestamp` and `valid_until` are
RFC 3339 UTC timestamps with the `Z` suffix and MUST satisfy
`timestamp < valid_until`. `valid_until` MUST be no later than `timestamp` plus
the Grant's `max_age_seconds`, Grant expiry, and any preview, reservation, or
other approval-bound evidence expiry.

On first authenticated ingestion of a receipt hash, a consumer MUST durably
record a local `first_authenticated_at` time and MUST NOT move it forward on
replay. It MUST reject as `integrity_mismatch` a receipt whose `timestamp` is
later than that time plus a finite locally configured clock-skew allowance. For
first effect admission, the effective expiry is the earliest of
`approval.valid_until`,
`first_authenticated_at + max_age_seconds`, Grant expiry, and every applicable
approval-bound evidence expiry. This receiver-side cap prevents a future-dated
producer timestamp from extending the Grant caveat. `first_authenticated_at`
is verification state, not a wire member or portable trusted timestamp.

For a denied receipt, `result` is `denied`, `approval.valid_until` is absent,
and the closed `approval` object contains the other three members. The valid
decision combinations are:

| Role | Result | `decided_by` | Policy Decision outcome and reason |
| --- | --- | --- | --- |
| `runtime` | `approved` | `user` | `allow`, `approval_satisfied` |
| `runtime` | `denied` | `user` | `deny`, `approval_denied` |
| `runtime` | `denied` | `policy` | `deny`, `local_policy_denied` |
| `application` | `approved` | `user` or `policy` | `allow`, `approval_satisfied` |
| `application` | `denied` | `user` | `deny`, `approval_denied` |
| `application` | `denied` | `policy` | `deny`, `app_policy_denied` |

Every other combination is invalid. The top-level and embedded
policy-decision hashes MUST match. `policy_decision.evaluated_at` MUST equal
`timestamp`.

The receipt binds the complete subject, runtime, agent, Passport, application,
Grant, session generation, surface, action, idempotency key, normalized
`input_hash`, sanitized execution context, and `execution_hash`. Conditional
preview, precondition, expected-effect, reservation, execution-token-hash, and
recovery-target bindings are already inside that execution context. Changing
any bound value requires a new approval interaction and receipt. Approval for a
proposal, dry run, reservation, or different companion action cannot satisfy a
commit, compensation, or revert.

An Approval Receipt MUST omit `parent_receipt_hash`, `approval_receipt_hashes`,
raw action input, raw execution tokens, output and resource fields,
`actual_effects`, effect hashes and outcome, revert evidence, and budget
charges. It records no action attempt or accounting admission. The producer
computes `receipt_hash` with the ordinary Receipt hash domain. The optional
Receipt Signing Profile applies without changing that hash.

### Producer Authentication and Role Mapping

A bare `receipt_hash` is correlation only. Across a trust boundary, the
consumer MUST obtain the complete receipt, recompute its receipt and Policy
Decision hashes, authenticate the producer through the Grant-bound channel or
store, and verify every binding above. When the Grant's
`audit.receipt_signing.required_signers` contains the Approval Receipt's
producer role, the consumer MUST also require and verify the signature and its
pinned role-specific key. Every present signature MUST be verified even when
that role is not required, and an invalid required or present signature MUST
NOT be downgraded to unsigned evidence. A valid runtime signature authenticates
the runtime's statement; it does not independently prove a human gesture,
understanding, or identity.

Action evidence links approvals with a closed `approval_receipt_hashes` object
whose only possible members are `runtime` and `application`. Each present value
is the hash of one verified approved Approval Receipt for that role; members are
never `null`. The object is a causal side link, not `parent_receipt_hash`, and
MUST NOT appear inside `execution`, because the Approval Receipt already binds
`execution_hash` and that placement would create a hash cycle.

The role mapping in the final application action receipt is:

| Manifest approval mode | Required approved receipt hashes |
| --- | --- |
| `none` | Object absent. |
| `runtime` | Exactly `runtime`. |
| `app` | Exactly `application`. |
| `user_or_app` | Exactly one role accepted by the Grant rule. |
| `runtime_and_app` | Both `application` and `runtime`. |

The Action Request and its runtime action receipt carry the exact same absent
object or `runtime` member; a runtime MUST NOT supply an `application` member.
The map is absent for `none` and `app`, contains exactly `runtime` for `runtime`
and `runtime_and_app`, and for `user_or_app` contains `runtime` only when that
role is accepted and selected, otherwise it is absent only when `application`
is accepted. The application receipt MUST preserve a verified runtime member
and add its own `application` member when app-side approval is required. For
`user_or_app`, a present valid runtime member fixes the selected role and the
application MUST NOT add another member; when it is absent, the application
MUST obtain and add an application approval before effect admission. A known
denial in any required role blocks the effect and MUST NOT appear as satisfied
approval evidence in an action receipt. `runtime_and_app` proves two producer
decisions, not two distinct humans, quorum, separation of duties, or absence of
collusion.

### Lifecycle, Replay, and Effect Boundary

The producer MUST atomically persist the first terminal `approved` or `denied`
decision for its producer-local `approval_id`. A verifier keys this identity by
producer role, authenticated producer identity, and `approval_id`; equal local
identifiers from the runtime and application are not a collision. An exact
replay returns the same immutable receipt; a conflicting second decision under
that complete producer key is an integrity failure and MUST NOT rewrite the
first. A runtime denial ends before Action Request dispatch. An application
denial occurs after request dispatch but before budget or effect admission; it
MUST NOT dispatch an external effect. Neither denial revokes the Grant.
Reversal requires a new decision attempt, new `approval_id`, and new receipt
while retaining the denial record according to policy.

Before first effect admission, the application MUST verify the complete
required approval set, current Grant and session, exact surface and invocation
tuple, current application policy, receiver-capped approval expiry, preview and
reservation, preconditions, and effect envelope. It MUST atomically bind the
accepted approval hashes into the action's idempotency record with budget and
effect admission. Reusing the same idempotency key with a different approval
set is `idempotency_conflict`; reusing a receipt with any other bound tuple is
`integrity_mismatch`. A receipt that has reached its effective expiry cannot
admit a first effect and fails as `approval_expired`.

An exact replay after an effect was already admitted returns the original
immutable action result and approval and action receipt references even if the
approval later expires; it MUST NOT admit another effect or request another
approval. If no effect was admitted, expiry requires a fresh approval. Grant
revocation, session invalidation, a changed surface or execution, stale preview
or reservation, changed preconditions or expected effects, and current policy
denial always take precedence over an unused approval. Expiry after an external
effect dispatch begins does not rewrite its actual outcome.

This profile does not itself standardize approval UI, step-up authentication,
clarification, redlines, option selection, legal consent, electronic
signatures, non-repudiation, trusted timestamps, cancellation, rollback,
compensation, or proof that a person saw or understood a presentation. The
separate Human Elicitation Events Profile can carry typed clarification,
selection, edit, redline, and step-up results, but none is Approval Receipt
evidence or proof that a person understood an approval presentation.

## Receipt Hash Chain

Every runtime and application receipt MUST contain `receipt_hash` computed with
the Canonical Object Hash Profile. A root receipt omits
`parent_receipt_hash`; it MUST NOT encode the missing parent as `null`. A
non-root receipt contains exactly one `parent_receipt_hash`, which is included
in its own hashing view.

For a runtime-mediated state-changing action whose grant requires a runtime
receipt, the application receipt MUST use the verified runtime
`receipt_hash` from the action request as its `parent_receipt_hash`. A later
runtime receipt MAY use the returned application `receipt_hash` as its parent.
This single-parent model permits branches but does not represent multi-parent
causal joins; a future profile may define a DAG representation.

A parent and child receipt for one action MUST carry identical `grant_hash`,
`surface_hash`, `session_id`, `session_generation`, `action_id`,
`idempotency_key`, `input_hash`, sanitized `execution`, and `execution_hash`.
Conditional `preview_id`,
`execution_token_hash`, `preconditions_hash`, `expected_effects_hash`,
`reservation_id`, and `target_receipt_hash` values inside that request context
MUST therefore also match. An app-only `reservation_result`,
`actual_effects`, `actual_effects_hash`, and `effect_outcome` describe the
outcome and are not required in the parent runtime receipt.
They also carry the same `trace_id` unless the child records a trust-boundary
restart with `linked_trace_id` equal to the parent's `trace_id`.
Their `span_id` and `policy_decision_hash` normally differ because each producer
records its own operation and decision. A consumer MUST recompute every
available object hash, verify these invariants, reject a cycle, and stop at any
missing or mismatched parent. Reusing one `receipt_id` for different
`receipt_hash` values is an invalid receipt conflict.

Approval Receipts are root evidence objects and always omit
`parent_receipt_hash`; their hashes are prerequisite side links and do not add a
parent edge. Under the Approval Receipt Profile, a runtime action receipt MUST
carry exactly the absent object or `runtime` member sent in the Action Request.
The application action receipt MUST preserve that runtime member and MAY add
only its newly produced `application` member. Its final map MUST exactly satisfy
the effective manifest mode and Grant requirement. An application receipt that
claims an applied or attempted effect while omitting a required role, linking a
denial, or substituting another Approval Receipt is invalid evidence.

For `compensate` or `revert`, `target_receipt_hash` links to a separately
verified original application receipt but does not create another parent edge.
A verifier MUST validate that target receipt and the manifest's reciprocal
recovery relationship independently. It MUST NOT apply the same-action parent
invariants across this causal link, and MUST NOT treat the target as authority
for the recovery action.

The runtime makes its parent receipt available to the application through the
`agent_api.receipt_url` or an explicitly declared inline action-request
extension, as defined in Action Request. The application MUST NOT claim a
verified parent link when it received only an unverified hash and its policy
requires the parent content.

A hash chain is tamper-evident only relative to a trusted stored chain head or
authenticated signature. A party that can replace an entire unsigned chain can
recompute every hash. Receipt hashes and links therefore do not authenticate a
producer and do not authorize an action.

Copying a receipt into a Portable Replay Bundle does not strengthen its
authentication, completeness, effect, or authority claim. A replay validator
applies the same receipt structure, hash, parent-link, signature, and producer
rules to the exact carried object and MUST NOT treat the bundle or its exporter
as the receipt producer.

## Runtime Receipt

A runtime receipt records what the runtime observed and enforced, such as agent
intent, local policy decisions, local approvals, denials, and runtime-side
redactions.

```json
{
  "receipt_id": "receipt_runtime_abc",
  "receipt_type": "runtime",
  "receipt_hash": "sha-256:<runtime-receipt-digest>",
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "session_id": "sess_456",
  "session_generation": 1,
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "b7ad6b7169203331",
  "action_id": "comment.create",
  "app_id": "code.example.com",
  "surface_version": "2026-06-25",
  "surface_hash": "sha-256:<base64url-digest>",
  "actor_agent": {
    "agent_id": "local_agent_789",
    "identity_evidence_hash": "sha-256:<base64url-digest>"
  },
  "runtime": {
    "runtime_id": "application_runtime_456"
  },
  "subject": {
    "user": "user_abc"
  },
  "idempotency_key": "idem_01HX7DS8AC6G9",
  "approval_receipt_hashes": {
    "runtime": "sha-256:<runtime-approval-receipt-digest>"
  },
  "input_hash": "sha-256:<action-input-digest>",
  "execution": {
    "mode": "commit",
    "execution_id": "exec_01J2COMMENT"
  },
  "execution_hash": "sha-256:<action-execution-digest>",
  "policy_decision_hash": "sha-256:<runtime-policy-decision-digest>",
  "policy_decision": {
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
    "policy_decision_hash": "sha-256:<runtime-policy-decision-digest>"
  },
  "budget_charges": [
    {
      "budget_id": "tool_calls",
      "amount": 1,
      "ledger_revision": 12
    }
  ],
  "timestamp": "2026-06-25T16:30:00Z",
  "result": "authorized_for_forwarding"
}
```

## App Receipt

An app receipt records what the application actually committed, denied, or
deduplicated under a grant.

```json
{
  "receipt_id": "receipt_app_abc",
  "receipt_type": "app",
  "receipt_hash": "sha-256:<app-receipt-digest>",
  "parent_receipt_hash": "sha-256:<runtime-receipt-digest>",
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "session_id": "sess_456",
  "session_generation": 1,
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "action_id": "comment.create",
  "app_id": "code.example.com",
  "surface_version": "2026-06-25",
  "surface_hash": "sha-256:<base64url-digest>",
  "runtime": {
    "runtime_id": "application_runtime_456"
  },
  "actor_agent": {
    "agent_id": "local_agent_789",
    "identity_evidence_hash": "sha-256:<base64url-digest>"
  },
  "subject": {
    "user": "user_abc"
  },
  "idempotency_key": "idem_01HX7DS8AC6G9",
  "approval_receipt_hashes": {
    "runtime": "sha-256:<runtime-approval-receipt-digest>"
  },
  "input_hash": "sha-256:<action-input-digest>",
  "execution": {
    "mode": "commit",
    "execution_id": "exec_01J2COMMENT"
  },
  "execution_hash": "sha-256:<action-execution-digest>",
  "output_hash": "sha256:...",
  "actual_effects": [
    {
      "effect_id": "comment-publish",
      "operation": "publish",
      "resource_type": "comment",
      "resource_key": "comment_789",
      "visibility": "shared",
      "boundary": "internal",
      "reversibility": "irreversible",
      "domain": "communication"
    }
  ],
  "actual_effects_hash": "sha-256:<actual-effects-digest>",
  "effect_outcome": "applied",
  "policy_decision_hash": "sha-256:<app-policy-decision-digest>",
  "policy_decision": {
    "type": "policy.decision",
    "decision_id": "pdec_app_01J2ABCDEG",
    "enforcer": {
      "type": "application",
      "id": "code.example.com"
    },
    "outcome": "allow",
    "policy": {
      "id": "agent-action-policy",
      "version": "2026-06-25"
    },
    "reason_code": "policy_allowed",
    "matched_rules": ["grant.active", "action.comment.create"],
    "safe_to_show": "The application accepted the authorized comment action.",
    "evaluated_at": "2026-06-25T16:30:00Z",
    "policy_decision_hash": "sha-256:<app-policy-decision-digest>"
  },
  "resource": {
    "type": "comment",
    "id": "comment_789"
  },
  "budget_charges": [
    {
      "budget_id": "write_actions",
      "amount": 1,
      "ledger_revision": 18
    }
  ],
  "timestamp": "2026-06-25T16:30:00Z",
  "result": "success"
}
```

## Receipt Signing Profile

The optional `asp-jws-detached` profile lets an application, runtime, or both
authenticate a receipt without changing `receipt_hash`. The base MVP permits
unsigned receipts. Unsigned means that `receipt_signatures` is absent; it MUST
NOT be represented by a JWS using `alg: none`.

A grant that requires both runtime and application signatures carries:

```json
{
  "audit": {
    "local_receipt": "required",
    "app_receipt": "required",
    "receipt_signing": {
      "profile": "asp-jws-detached",
      "required_signers": ["runtime", "application"],
      "signer_keys": [
        {
          "role": "runtime",
          "kid": "runtime-receipt-key-2026-01",
          "jwk_thumbprint": "<base64url-rfc7638-sha256-thumbprint>"
        },
        {
          "role": "application",
          "kid": "app-receipt-key-2026-01",
          "jwk_thumbprint": "<base64url-rfc7638-sha256-thumbprint>"
        }
      ]
    }
  }
}
```

For this profile, the signing view is the complete receipt with
`receipt_signatures` omitted and with `receipt_hash` retained. The signer wraps
that view as an object with `domain` equal to
`https://github.com/0al-spec/agent-surface/signature/receipt/v1` and `receipt`
equal to the signing view, then serializes the wrapper with RFC 8785 JCS. Those
UTF-8 bytes are the JWS payload.

The receipt carries a detached General JWS JSON Serialization as follows. The
`payload` member is omitted according to RFC 7515 Appendix F; the verifier
reconstructs it from the canonical signing view. Ordinary JWS base64url payload
encoding is used, so the RFC 7797 `b64` extension MUST NOT be present.

The decoded protected header for a runtime receipt has this form:

```json
{
  "alg": "ES256",
  "kid": "runtime-receipt-key-2026-01",
  "typ": "asp-receipt+jws"
}
```

The following envelope is schematic; angle-bracket strings mark values that a
producer replaces with valid base64url JWS values.

```json
{
  "receipt_signatures": {
    "signatures": [
      {
        "protected": "<base64url-protected-header>",
        "signature": "<base64url-es256-signature>"
      }
    ]
  }
}
```

The `receipt_signatures` object MUST contain exactly the non-empty `signatures`
array; `payload` and every other member are forbidden in the transported
envelope. Each signature object MUST contain exactly `protected` and
`signature`; a JWS `header` member is forbidden. The
decoded protected header MUST contain exactly three unique members: `alg`,
`kid`, and `typ`. `typ` MUST be `asp-receipt+jws`; this is an ASP-private type
string pending any media-type registration and MUST be compared exactly.
Duplicate header members, `alg: none`, inline `jwk`, and any `jku`, `x5u`, or
`x5c` key location MUST be rejected.

Implementations of this profile MUST support `ES256` and MUST enforce an
explicit algorithm allow-list. An ES256 JWK MUST use `kty: "EC"` and
`crv: "P-256"`; when present, `alg` MUST be `ES256`, `use` MUST be `sig`, and
`key_ops` MUST permit `verify`. The JWS signature decodes to the 64-octet `R ||
S` form defined by RFC 7518, not an ASN.1 DER signature. ES256 signers SHOULD
derive the nonce deterministically according to RFC 6979. A future profile MAY
add a fully specified algorithm such as `Ed25519`; the polymorphic `EdDSA`
identifier MUST NOT be substituted.

`kid` is only a lookup hint. Application keys MUST be resolved through
issuer-bound authenticated metadata such as the manifest
`audit.receipt_signing.jwks_uri`; runtime keys MUST be resolved through the
runtime identity or key registration bound to the grant. A verifier MUST ensure
that the resolved key is authorized for the claimed signer and receipt role.
For a required signer, the JWS `kid` MUST select an entry in the hashed grant's
`audit.receipt_signing.signer_keys` whose `role` matches the receipt producer,
and the resolved public JWK's RFC 7638 SHA-256 thumbprint MUST match
`jwk_thumbprint`. A `kid` match without the role and pinned thumbprint is
insufficient.

An application advertising this profile MUST include `asp-jws-detached` in
`audit.receipt_signing.profiles_supported`, `ES256` in
`algorithms_supported`, and an issuer-bound HTTPS `jwks_uri`. A runtime signing
receipt evidence MUST register or attest its verification key through the
authenticated runtime relationship before a grant can require the `runtime`
signer role. A receipt-supplied URL or inline key is never sufficient trust.
Signers MUST retain or make their historical public keys available for at least
the applicable receipt-retention period. Key rotation does not rewrite an old
grant's pinned thumbprints; requiring a new key for future receipts requires a
new grant hash or explicit grant renewal. Within one issuer and signer role, a
`kid` MUST NOT be rebound to different key material. A compromise or revocation can make
historical evidence indeterminate according to verifier policy because this
profile does not provide an independent trusted timestamp.

The manifest advertises supported algorithms and key metadata. A grant MAY
make signatures mandatory through an `audit.receipt_signing` object containing
`profile: "asp-jws-detached"` and `required_signers`, whose values are
`runtime` and/or `application`. A listed role MUST sign the receipts it
produces; listing both roles requires a signed runtime receipt and a signed
application receipt, not two signatures on every receipt. Additional
co-signatures over the same detached payload remain possible through General
JWS. Under the Approval Receipt Profile, a listed role MUST also sign every
Approval Receipt it produces; `approval.role` selects the same role-specific
key policy. That signature authenticates the producer record, not a human
approver or trusted timestamp. The requirement MUST include at least one pinned
`signer_keys` entry for each required role. Because the requirement and key
pins are inside the hashed grant rather than the removable signature envelope,
they cannot be stripped without changing `grant_hash`. If the grant has no such
requirement, an unsigned receipt remains conforming hash-linked audit material
but MUST NOT be represented as authenticated portable evidence.

A verifier MUST validate receipt structure and linked hashes first, reconstruct
the canonical detached payload, enforce protected-header and key policy, verify
the signature required for that receipt's producer role, and then validate the
parent chain to a trusted anchor. A present but invalid, unknown, or
unverifiable signature MUST NOT be downgraded to an unsigned receipt. Missing
or invalid required signatures make the receipt invalid as evidence; they do
not retroactively authorize or undo the underlying application action.

# Portable Replay Bundle Profile

The Portable Replay Bundle Profile defines one bounded, deterministic,
offline representation of historical ASP evidence for debugging and audit. Its
profile identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/replay-bundle/v1
```

A v1 bundle covers exactly one `session_id` and one positive
`session_generation` under one complete subject, application, Surface, Grant,
runtime, agent, and Passport-hash tuple. It carries an exact historical Agent
Surface Manifest, an exact historical semantic Agent Grant, and an ordered
hash chain containing only session transitions, application-event deliveries,
event acknowledgements, event gaps, receipts, and explicit capture gaps.

The profile is passive and descriptive. A bundle is not a Grant, Grant
Credential, current session record, event cursor, acknowledgement, approval,
receipt signature, trusted timestamp, effect proof, execution request, or
instruction. Its `claim_effect` is the literal `descriptive_only`. Loading,
hashing, validating, or rendering a bundle MUST NOT cause network access,
online event replay or acknowledgement, session lifecycle mutation, action
dispatch, agent or model execution, approval, compensation, revert, or another
application effect.

## Bundle Scope and Historical Context

The bundle is a closed I-JSON object containing exactly the required members in
this table:

| Member | Requirement |
| --- | --- |
| `$schema` | Literal `./bundle.schema.json`. It selects the repository schema for this wire object and is not a network retrieval instruction. |
| `schema_version` | Integer `1`. |
| `profile` | Exact Portable Replay Bundle Profile identifier above. |
| `protocol_version` | Literal `agent-surface/0.1`. |
| `claim_effect` | Literal `descriptive_only`. |
| `bundle_id` | Non-empty bounded identifier unique in the exporter's retained bundle namespace. It is correlation, not authority. |
| `created_at` | RFC 3339 UTC timestamp with the `Z` suffix describing export construction time, not trusted occurrence time. |
| `scope` | Closed one-session-generation tuple defined below. |
| `context` | Closed object containing exactly `surface` and `grant`. |
| `capture` | Closed capture-boundary object defined below. |
| `records` | Non-empty ordered array of at most 4096 Replay Records. |
| `bundle_hash` | Canonical Object Hash Profile result for the complete bundle with only `bundle_hash` omitted. |

`scope` contains exactly:

- `subject_user`
- `issuer`
- `app_id`
- `surface_version`
- `surface_hash`
- `grant_id`
- `grant_hash`
- `runtime_id`
- `agent_id`
- `identity_evidence_hash`
- `session_id`
- `session_generation`

The string identifiers are non-empty and bounded, each hash uses the
`sha-256:` representation from the Canonical Object Hash Profile,
`session_generation` is a positive CloudEvents-compatible 32-bit integer, and
`issuer` is an absolute URI. The tuple is descriptive replay scope; none of its
identifiers is a credential.

Every timestamp whose syntax is evaluated by this v1 profile uses a four-digit
year, the UTC `Z` suffix, seconds from `00` through `59`, and at most nine
fractional-second digits. Leap-second timestamps and other UTC offsets are not
supported by v1 and make the bundle invalid. This restriction also applies to
the carried event, acknowledgement, gap, receipt, Policy Decision, and approval
timestamps inspected by replay checks; it does not reinterpret an unchecked
timestamp elsewhere in an embedded native object.

`context.surface` is the complete exact historical Agent Surface Manifest,
including its `surface_hash`. `context.grant` is the complete exact historical
semantic Agent Grant, including its `grant_hash`; it MUST NOT contain or embed
a Grant Credential. A validator MUST recompute both hashes and require:

- the manifest `issuer`, `app_id`, `surface_version`, and `surface_hash` to
  match `scope`;
- the Grant id, subject user, Grant hash, resource-server issuer, app, Surface
  version and hash, runtime id, agent id, and identity-evidence hash to match
  `scope`;
- every carried event and receipt binding that applies to the same tuple to
  match `scope` and those exact historical objects.

The historical context permits deterministic interpretation of the carried
records. It does not establish that the manifest is still current, the Grant
is active, the Passport is valid, the session exists, or any credential would
be accepted now. A verifier MUST NOT contact an issuer, schema host, status
service, JWKS endpoint, or another URI to upgrade those historical objects.

`capture` contains exactly `started_at`, `ended_at`, and `completeness`.
The timestamps use RFC 3339 UTC with the `Z` suffix and `started_at` MUST NOT be
later than `ended_at`. `completeness` is `complete` or `partial`. It is an
exporter assertion about the bounded record source, not independently
authenticated proof that no event or receipt ever existed. The value is
`partial` if and only if at least one `capture.gap` records exporter loss,
redaction, or unavailable source material; with no such gap it is `complete`.
An `event.gap` instead describes the application event history and independently
makes replay completeness incomplete without changing capture completeness.

## Replay Record Object

Every element of `records` is a closed object containing:

| Member | Requirement |
| --- | --- |
| `ordinal` | Zero-based array position. Ordinals are contiguous and equal their array indexes. |
| `record_id` | Non-empty identifier unique within the bundle. |
| `recorded_at` | RFC 3339 UTC timestamp with the `Z` suffix. It is diagnostic capture time, not causal or trusted time. |
| `kind` | One exact kind from the table below. |
| `name` | The one exact name paired with `kind`. |
| `representation` | Literal `exact`. |
| `elisions` | Required empty array. |
| `body` | Exact closed or existing ASP object selected by `kind` and `name`. |
| `previous_record_hash` | Required from ordinal `1`; absent at ordinal `0`; equal to the immediately preceding `record_hash`. |
| `record_hash` | Canonical Object Hash Profile result for the complete Replay Record with only `record_hash` omitted. |

The allowed record pairs and bodies are:

| `kind` | `name` | Exact `body` |
| --- | --- | --- |
| `session_transition` | `session.transition` | Closed object containing exactly `session_generation`, `prior_state`, `next_state`, and non-empty `reason`. |
| `event_delivery` | `event.delivery` | Complete ASP CloudEvent structured event object, without an additional Runtime Bridge envelope. |
| `event_ack` | `event.ack` | Complete `event.ack` Runtime Bridge message defined by Ordering and Acknowledgement. |
| `event_gap` | `event.gap` | Complete authenticated gap message defined by Replay Cursors and Gaps. |
| `receipt` | `receipt.runtime` | Complete Runtime Receipt whose `receipt_type` is `runtime`. |
| `receipt` | `receipt.app` | Complete App Receipt whose `receipt_type` is `app`. |
| `receipt` | `receipt.approval` | Complete Approval Receipt whose `receipt_type` is `approval`. |
| `capture_gap` | `capture.gap` | Closed object containing exactly `reason`, `started_at`, and `ended_at`; `reason` is `not_captured`, `redacted`, or `source_unavailable`. |

Unknown Replay Bundle or Replay Record members, another kind/name combination,
another representation, a non-empty `elisions` array, or an unknown member in
the closed `session.transition` or `capture.gap` body makes the bundle invalid.
Carried CloudEvents and receipts retain their own extension rules, and every
such extension remains inside the applicable native and replay hashing views.
An exporter that cannot retain or disclose an exact object MUST add
`capture.gap` and set capture completeness to `partial`; it MUST NOT remove
fields, substitute hashes for required bodies, fabricate neutral payloads, or
label a transformed object `exact`.
For every `capture.gap`, `started_at` and `ended_at` use RFC 3339 UTC with the
`Z` suffix and `started_at` MUST NOT be later than `ended_at`.

A bundle never carries a prompt, Action Request, Action Response, raw action
input, standalone execution context, agent message, tool call, executable
content, transport headers, Grant Credential, access or refresh token, cookie,
proof-of-possession material, private key, or raw `execution_token`. A complete
receipt continues to carry the sanitized execution and hash members required
by the Receipts section, but the bundle adds no execution payload and the raw
token remains forbidden.

## Deterministic Replay and Ordering

Replay is a pure reduction over `records` in ascending ordinal order. The
validator first validates strict I-JSON and closed schemas, recomputes the
historical Surface and Grant hashes, recomputes every record hash and prior
link, and recomputes `bundle_hash`. Only after those integrity checks succeed
does it reduce session, event, gap, and receipt state. A validation failure
MUST NOT be repaired by reordering records, resolving a URI, retrieving a
missing parent, accepting a mutable identifier, or inserting inferred state.

A component claiming complete Portable Replay Bundle Profile validation MUST
evaluate every normative requirement in this section. This includes the
complete native Agent Surface Manifest, semantic Agent Grant, CloudEvent,
acknowledgement, gap, and receipt structure, hashing, binding, state-machine,
required-signature, and verification rules selected by each carried object. It
MAY compose authoritative native-profile validators, but an unavailable
required validator, unevaluated required rule, or unavailable required
signature verification is an evaluation error. The component MUST NOT issue a
`valid` or `incomplete` complete-profile result from a strict subset of those
requirements. A bounded tool or check registry does not relax these
requirements.

For `scope.session_generation` equal to `1`, the first
`session.transition` is `absent` to `active` with `session_generation: 1`.
For a later generation `N`, the first transition is `interrupted` to `active`
with `session_generation: N`; this represents the already-authoritative resume
boundary from generation `N - 1` into the scoped generation. Every later
transition remains in generation `N` and follows the Session Authority and
Lifecycle state machine. In particular, a later `interrupted` to `active`
transition in the same bundle is invalid because an accepted resume creates
generation `N + 1` and therefore requires another bundle. A record does not
cause any represented transition; it only describes the historical transition.

For events, the validator MUST:

- apply the complete ASP CloudEvents structure, historical Surface declaration,
  Grant scope, exposure, control/non-control, and `aspeventhash` checks;
- preserve one hash for each `(source, id)` occurrence;
- preserve source, id, event hash, subscription, delivery id, stream, sequence,
  and cursor across delivery attempts;
- require the first completely captured attempt to be `1` and each exact retry
  to increment `aspattempt` by one;
- within one `(subscription, stream)`, require the first delivery of sequence
  `N + 1` to follow an earlier terminal acknowledgement of sequence `N`;
  retries retain the original stream, sequence, and cursor and never allocate
  another position;
- bind every acknowledgement to an earlier delivery's subscription, delivery
  id, and cursor and enforce terminal-outcome consistency; and
- treat every `event.gap` as incomplete event history rather than inventing
  deliveries or authoritative application state.

A covering `event.gap` makes the affected ordering conclusion incomplete. The
validator MUST NOT guess an acknowledgement, infer a missing sequence from
cursor bytes, or treat a later delivery as proof that the predecessor reached a
terminal outcome. An `event.gap` can cover unavailable application-event
positions, but it does not cover the absent terminal acknowledgement of a
delivery that is already present in the bundle. A validated `capture.gap`
between that delivery and later stream progress can instead make the
acknowledgement conclusion incomplete because the exporter may have failed to
capture it.

Record array order supplies deterministic validator input, but it does not
create cross-stream event order or cross-component causality. `recorded_at`,
CloudEvents `time`, trace context, arrival order, cursors, receipt parent links,
and identifier lexical order MUST NOT be substituted for the ordering and
causal rules defined by their source profiles.

For every receipt, the validator applies the existing receipt shape, role,
Canonical Object Hash, embedded Policy Decision, execution, actual-effect,
parent-chain, Approval Receipt side-link, recovery-target, and scope-binding
rules. A referenced parent or side-link receipt appears earlier in a complete
bundle. A missing predecessor in a partial capture makes the corresponding
replay conclusion incomplete; it MUST NOT be fetched or treated as verified.
A missing predecessor in a bundle that claims complete capture is invalid.
Receipt content can describe a producer's historical effect observation, but
the replay result does not independently prove that effect, authenticate the
producer, or authorize recovery.

## Integrity, Completeness, and Validation Report

Integrity and completeness are distinct conclusions once structural and
semantic integrity evaluation succeeds:

- integrity answers whether the present exact objects, hashes, bindings,
  ordering, and state reductions are internally valid;
- completeness answers whether the bounded replay can account for all required
  predecessors and whether the capture contains no declared protocol or export
  gap.

When integrity evaluation fails, the validator cannot safely draw the
completeness conclusion and reports replay completeness as `not_evaluated`.
`capture.completeness: "partial"`, any `event.gap`, any `capture.gap`, or an
unavailable predecessor permitted only by a partial capture makes replay
completeness `incomplete` without weakening hash validation. A validator MUST
NOT upgrade it because later state appears consistent. A bundle claiming
`complete` that omits a required earlier delivery, receipt parent, approval
side link, recovery target, or initial session transition is invalid rather
than incomplete. The absence of an explicit gap does not authenticate an
exporter's completeness claim.

A failure to obtain one strict I-JSON value is outside the Replay Validation
Report state machine. The same is true of a local read or resource-limit
failure, report-serialization failure, or tool self-integrity failure. Such a
failure MUST NOT be mapped to `preflight_failed`, `semantic_invalid`,
`incomplete`, or `valid`, and MUST NOT produce a Replay Validation Report.

Once strict parsing succeeds, the deterministic Replay Validation Report is a
closed object conforming to `./report.schema.json`. It binds its schema and
report versions, literal `claim_effect: "descriptive_only"`, exact tool and
check-registry identity, raw input-byte hash, ordered check results,
data-minimized diagnostics, an evaluated or explicitly neutral replay summary,
a conservative assurance boundary, and `report_hash`. The input `bundle_id`
and `bundle_hash` are non-null in every state except `preflight_failed`. In that
state either value is `null` only when no canonical value can be recovered from
the parsed input; neither value may be inferred or repaired.

The report state is an exact derived truth table:

| `evaluation_state` | Required check outcome | `integrity_verdict` | `replay_completeness` | `verdict` | `replay.status` |
| --- | --- | --- | --- | --- | --- |
| `preflight_failed` | At least one structure, context, secret, record-envelope, hash, ordinal, or prior-link preflight check fails; dependent semantic checks are `not_evaluated`. | `invalid` | `not_evaluated` | `invalid` | `not_evaluated` |
| `semantic_invalid` | Every preflight check passes and at least one lifecycle, event, acknowledgement, gap, or receipt semantic check fails. | `invalid` | `not_evaluated` | `invalid` | `not_evaluated` |
| `incomplete` | No check fails or is unevaluated, and at least one evaluated check reports an explicit permitted evidence gap as `incomplete`. | `valid` | `incomplete` | `incomplete` | `evaluated` |
| `valid` | Every required check is evaluated and passes, and no permitted evidence gap exists. | `valid` | `complete` | `valid` | `evaluated` |

Both invalid states carry a neutral replay summary: `final_session_state` is
`unknown`, `session_generation` and every count are zero, and
`assurance.verified` is empty. Neutralization prevents a partially reduced
state from being represented as replayed history. It does not erase the
ordered diagnostic and check results that distinguish preflight failure from
semantic invalidity.

A check status is local to the exact `tool.check_profile`. `pass` means that
the named check was evaluated in that bounded scope and produced no finding;
it is not a complete-profile assurance claim. `incomplete` means the check was
evaluated without a contradiction but lacked evidence required for a complete
conclusion. `not_evaluated` MUST NOT be interpreted as `pass`.

`assurance.verified` is derived conservatively from passed prerequisite checks,
not merely from the absence of an error diagnostic. A `valid` report includes
all assurance values supported by its exact check profile. An `incomplete`
report includes `recorded_lifecycle` or `recorded_linkage` only when every
check supporting that assurance passes rather than being incomplete; those
assurances cover only the present records and explicit gap boundaries, not
uncaptured history. A `not_verified` assurance value is an explicit negative
boundary, not a waiver of a normative validation requirement. In particular, a
bounded report that leaves complete native object semantics or signature
validity unverified cannot be represented as complete Portable Replay Bundle
Profile validation.

`report_hash` uses the Replay Validation Report domain from the Canonical
Object Hash Profile over the complete report with only `report_hash` omitted.
The report hash and source-byte hash identify bytes; they do not authenticate
the tool, exporter, or source.

Diagnostics contain stable check identifiers, severity, JSON Pointer, and
bounded inert messages. They MUST NOT copy event data, user content, receipt
payloads, identifiers not needed for the pointer, secret values, or retrieved
remote content. Invalid receipt signatures MUST NOT be downgraded to unsigned
evidence. A bounded checker that does not perform required signature
verification MUST expose that limitation in its assurance boundary and MUST
NOT issue a complete-profile validation claim. Offline validation never
upgrades a key by resolving a remote URI. Unless a complete validator has
separately satisfied a normative requirement, the report assurance boundary
leaves producer authentication, current authority, trusted time, external
effect occurrence, and remote schemas unverified.

## Failure, Privacy, and Non-Authority Rules

A parser or validator MUST reject duplicate JSON members, invalid Unicode,
negative zero, non-I-JSON numbers, unknown closed members, unsupported profile
or protocol versions, more than 4096 records, duplicate record ids, broken
ordinals, a wrong prior link, a mismatched native or replay hash, an illegal
session transition, conflicting event delivery identity, a conflicting
terminal acknowledgement, a conflicting receipt identity, or known raw secret
material. It MUST fail closed without emitting a partially trusted replay or
performing recovery. A strict parse rejection occurs before a report state
exists. An unavailable file, exhausted local evaluation limit, report
serialization failure, or tool self-integrity failure is an evaluation error,
not an ASP rejection and not evidence that the bundle is valid.

The exact historical Surface, Grant, event data, and receipts can contain user,
tenant, resource, policy, and audit data. Export, storage, access, rendering,
retention, and deletion remain subject to the strictest applicable Data
Exposure Contract, Grant lifecycle, receipt policy, and local audit policy.
Creating a bundle MUST NOT extend source retention. If exact content can no
longer be retained, the exporter uses a capture gap or declines export; a
digest is not permission to retain plaintext or reconstruct deleted content.

A bundle hash is tamper-evident only relative to an independently trusted
value. An actor able to replace a complete unsigned bundle can recompute its
record and bundle hashes. A validator MUST NOT represent internal consistency
as exporter authentication, non-repudiation, completeness outside the declared
capture, or current protocol authority. Replaying the evidence means reducing
and displaying it inertly; it never means re-executing the recorded system.
