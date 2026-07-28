## Action Request

The agent requests an action through the runtime. The runtime sends the action to
the app only if grant and policy allow it.

The action request MUST be authorized by the HTTP authorization layer or an
equivalent proof. The `grant_id` inside the body is a correlation identifier, not
a credential.

The application MUST also verify that the supplied `session_id` and
`session_generation` identify an `active` session bound to the complete subject,
runtime, agent, passport, grant, application, and surface tuple selected by the
presented credential, unless an interrupted session request satisfies the exact
closed safety and cleanup exception in Session Pause. Before returning a
non-active failure, the application MAY perform only the validation and record
lookup required to decide that exception; it MUST NOT admit an effect
speculatively. Otherwise a valid grant credential could be replayed against
sessions created under other grants or against a stale generation, corrupting
session accounting and receipt linkage. Unknown, non-qualifying non-active,
mismatched, and stale sessions fail uniformly as `session_invalid` so the
action endpoint does not become a session-enumeration oracle.

The application MUST also verify that body `grant_hash` matches the complete
authoritative grant selected by the credential and that `surface_hash` matches
the manifest snapshot pinned by that grant. These hashes are correlation and
integrity commitments, not substitutes for the HTTP authorization proof.

When the Grant contains `constraints.purpose_binding`, the application MUST
resolve its exact issuer-owned purpose and optional task records for the
Grant-bound subject and app, verify exact revisions, active state and
relationship, require the authoritative session's exact equal binding, and
apply the current purpose and task policy to the action, target resources,
normalized input, execution mode, and maximum effects. It performs these checks
before idempotency lookup or allocation, budget or capacity admission, policy
receipt creation, workload dispatch, reservation, or effect. The Action Request
does not repeat the object: adding a client-authored copy cannot repair the
Grant or session and would be invalid unless a future extension defines it.

If both the `Idempotency-Key` header and the body `idempotency_key` field are
present, they MUST match, and the application MUST reject a mismatch as
`schema_invalid`. Accepting a mismatched request and picking either value
would let app-side deduplication and runtime receipts refer to different
idempotency identifiers.

For an idempotency-required action, the runtime MUST apply the pinned
`idempotency_normalization` declaration before approval, hashing, receipt
creation, and transmission, and MUST carry the resulting `input_hash` even when
the action does not require a receipt. The application MUST verify the pinned
`input_schema_hash`, validate the received input, independently reapply the same
declaration, require a fixed point, and recompute the `input_hash` before
consulting the idempotency record or admitting any work. A non-fixed-point
request fails as `input_not_normalized`; the application does not reserve the
key, charge a budget, or create policy or action receipts for that rejected
attempt.

Example:

```http
POST /agent-actions HTTP/1.1
Host: example.com
Authorization: DPoP <grant-credential>
DPoP: <signed-proof>
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-b7ad6b7169203331-01
Idempotency-Key: idem_01HX7DS8AC6G9
Content-Type: application/json
```

```json
{
  "type": "action.request",
  "payload": {
    "session_id": "sess_456",
    "session_generation": 1,
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "b7ad6b7169203331",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "action_id": "comment.create",
    "idempotency_key": "idem_01HX7DS8AC6G9",
    "parent_receipt_hash": "sha-256:<runtime-receipt-digest>",
    "approval_receipt_hashes": {
      "runtime": "sha-256:<runtime-approval-receipt-digest>"
    },
    "input_hash": "sha-256:<action-input-digest>",
    "execution": {
      "mode": "commit",
      "execution_id": "exec_01J2COMMENT"
    },
    "execution_hash": "sha-256:<action-execution-digest>",
    "input": {
      "repository": "example-org/example-repo",
      "pull_request": 13,
      "body": "The proposed review comment text."
    }
  }
}
```

The request's proof material MUST use the authorization mechanism selected by
the credential-binding profile. For example, a DPoP-bound credential carries a
DPoP proof in the `DPoP` header as defined by RFC 9449.

Before forwarding a state-changing action, the runtime MUST finalize its
runtime receipt and place that receipt's `receipt_hash` in
`parent_receipt_hash`. When the application requires the runtime receipt
content, the runtime MUST either submit the complete receipt through the
manifest `agent_api.receipt_url` before the action or carry it inline through a
declared action-request extension. The application MUST recompute the supplied
receipt and policy-decision hashes before treating the receipt as verified. A
bare parent hash is correlation evidence only and is insufficient when app
policy requires verification of the runtime decision.

When the Grant selects Approval Receipt, the request's optional
`approval_receipt_hashes` object is closed and the runtime can supply only its
`runtime` member. It MUST match the same object in the verified parent runtime
action receipt. The application MUST retrieve or receive the complete Approval
Receipt through `agent_api.receipt_url` or the same declared inline receipt
extension, recompute its hashes, authenticate the producer, and validate the
exact Grant requirement and invocation bindings before accepting it. A
runtime-side denial stops before Action Request dispatch. A missing required
runtime role is `approval_required`; an expired receipt is `approval_expired`;
a mismatched, malformed, denied, or unauthenticated receipt never satisfies
approval and uses the error precedence defined below. App-side approval occurs
inside the application boundary and is added only to the final application
action receipt and Action Response.

For an action requiring runtime receipt evidence, the action declaration MUST
set `input_hash_profile` to `asp-jcs-sha-256`. The runtime and application MUST
compute the Action Input hash over the exact validated wire `input` and require
equality with both the action request and verified parent runtime receipt. For
an idempotency-required action that wire value is already the fixed point of
the manifest-pinned normalization declaration. A receipt for one normalized
input MUST NOT be attached to a different input even when the grant, action id,
and idempotency key match.

For `reserve`, `commit`, `compensate`, or `revert`, the runtime and application
MUST also compute `execution_hash` over the structurally validated execution
context, require it to match the request, and require the sanitized context and
hash to match the verified parent runtime receipt. The runtime MUST remove a
raw `execution_token` before producing its receipt. The application verifies
the raw request token against `execution_token_hash` and authoritative preview
state, but MUST NOT copy the token into its receipt.

## Action Response

```json
{
  "type": "action.result",
  "payload": {
    "session_id": "sess_456",
    "session_generation": 1,
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "00f067aa0ba902b7",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "action_id": "comment.create",
    "idempotency_key": "idem_01HX7DS8AC6G9",
    "execution": {
      "mode": "commit",
      "execution_id": "exec_01J2COMMENT"
    },
    "execution_hash": "sha-256:<action-execution-digest>",
    "approval_receipt_hashes": {
      "runtime": "sha-256:<runtime-approval-receipt-digest>"
    },
    "result": "success",
    "effect_outcome": "applied",
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
    "output": {
      "resource": {
        "type": "comment",
        "id": "comment_789",
        "url": "https://code.example.com/example-org/example-repo/pull/13#discussion_r..."
      }
    },
    "receipt_id": "receipt_app_abc",
    "receipt_hash": "sha-256:<app-receipt-digest>"
  }
}
```

An Action Response MUST repeat `session_id`, `session_generation`, grant and
surface hashes, `action_id`, and the idempotency key from the request. For a
state-changing action it MUST repeat the sanitized execution context and
`execution_hash`.
When Approval Receipt is selected, it MUST also return the exact final
`approval_receipt_hashes` map from the application action receipt. An
application-side denial response instead returns `approval_denied`, includes
`approval_receipt_id` and `approval_receipt_hash` for the immutable denial
Approval Receipt, and makes the complete object available through the
authenticated receipt channel. Those fields are correlation evidence, not
authority; the response MUST NOT claim satisfied approval or an action effect.
When an effect was or may have been attempted, it MUST return
`effect_outcome`, `actual_effects`, and `actual_effects_hash` as defined by the
Effect Model. A response MUST distinguish `partially_applied` and `unknown`
from success so a runtime does not create a new idempotency key and duplicate an
external effect.

Dry-run and reservation responses use the mode-specific objects defined in the
Action Execution Model. A failed request that performed no effect MAY omit
`actual_effects`; its structured error and any failure receipt MUST agree about
retryability and whether the outcome is known. An exact idempotent retry MUST
return the original immutable result and receipt reference.
