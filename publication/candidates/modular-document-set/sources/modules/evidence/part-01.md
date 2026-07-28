# Canonical Integrity and Provenance

## Canonical Object Hash Profile

The Document Set Catalog, canonical-source digests, aggregate digest,
Hyperprompt manifest, and source map identify specification publication
artifacts. They do not use or replace the ASP object-hash domains below.
Conversely, a valid `surface_hash`, `grant_hash`, receipt hash, or other ASP
object hash proves nothing about which specification document set was used by
an implementation.

ASP manifests, grants, events, action input schemas, action inputs and outputs,
action execution contexts, policy decisions, and receipts use the
`asp-jcs-sha-256` profile when a field in this draft is named `surface_hash`,
`grant_request_hash`, `grant_hash`, `aspeventhash`, `input_schema_hash`, `input_hash`,
`output_hash`, `execution_hash`, `preconditions_hash`,
`expected_effects_hash`, `actual_effects_hash`, `policy_decision_hash`,
`receipt_hash`, `parent_receipt_hash`, `record_hash`, `bundle_hash`, or
`report_hash`. The profile identifies exact JSON content; it does not by itself
authenticate the producer, exporter, or grant authority.

To compute an ASP object hash, an implementation MUST:

1. Construct the hashing view for the object type according to the table below.
2. Reject input that is not valid I-JSON, including duplicate object member
   names, non-Unicode strings, or numbers that cannot be represented as IEEE
   754 binary64 values. JSON negative zero also MUST be rejected rather than
   normalized to positive zero.
3. Construct an object with exactly two members: `domain`, containing the
   domain URI from the table, and `object`, containing the hashing view.
4. Serialize that wrapper with the JSON Canonicalization Scheme defined by RFC
   8785. Object members are sorted by JCS; array order is preserved and is
   therefore significant to the resulting hash. No additional Unicode, URI,
   timestamp, default-value, or array normalization is performed.
5. Compute SHA-256 over the canonical UTF-8 wrapper bytes.
6. Encode the digest with the RFC 4648 base64url alphabet without `=` padding
   and prepend the literal `sha-256:`.

| Object | Domain URI | Hashing view exclusions |
| --- | --- | --- |
| Agent Surface Manifest | `https://github.com/0al-spec/agent-surface/hash/manifest/v1` | top-level `surface_hash` |
| semantic Agent Grant request | `https://github.com/0al-spec/agent-surface/hash/grant-request/v1` | RFC 9396 `type` only; an authorization-server output member makes the request invalid and is not an exclusion |
| authoritative Agent Grant | `https://github.com/0al-spec/agent-surface/hash/grant/v1` | top-level `grant_hash`; the RFC 9396 `type` discriminator when starting from an OAuth authorization-details object |
| ASP CloudEvent occurrence | `https://github.com/0al-spec/agent-surface/hash/event/v1` | `aspeventhash`; delivery-only `aspsubid`, `aspdeliveryid`, `aspattempt`, `aspstream`, `aspsequence`, and `aspcursor`; diagnostic `traceparent` and `tracestate` |
| Action Input Schema | `https://github.com/0al-spec/agent-surface/hash/action-input-schema/v1` | none; the hashing view is the complete self-contained JSON Schema document |
| Action Request `input` | `https://github.com/0al-spec/agent-surface/hash/action-input/v1` | none; the hashing view is exactly the schema-valid `payload.input`; an idempotency-required input has already passed the action's fixed-point normalization check, and the hash performs no further transform |
| Action Response `output` | `https://github.com/0al-spec/agent-surface/hash/action-output/v1` | none; the hashing view is exactly the schema-valid `payload.output` and the hash performs no additional transform |
| Action Execution Context | `https://github.com/0al-spec/agent-surface/hash/action-execution/v1` | `execution_token`; the hashing view is `payload.execution` after structural validation with the confidential raw token omitted |
| Action Preconditions | `https://github.com/0al-spec/agent-surface/hash/action-preconditions/v1` | none; the hashing view is exactly the validated `preconditions` object |
| Expected Effects | `https://github.com/0al-spec/agent-surface/hash/expected-effects/v1` | none; the hashing view is exactly the validated `expected_effects` array |
| Actual Effects | `https://github.com/0al-spec/agent-surface/hash/actual-effects/v1` | none; the hashing view is exactly the validated `actual_effects` array |
| Human Elicitation context | `https://github.com/0al-spec/agent-surface/hash/human-elicitation-context/v1` | none; the hashing view is the complete closed `context` object |
| Human Elicitation request | `https://github.com/0al-spec/agent-surface/hash/human-elicitation-request/v1` | top-level `request_hash` |
| Human Elicitation response | `https://github.com/0al-spec/agent-surface/hash/human-elicitation-response/v1` | top-level `response_hash` |
| Policy Decision Object | `https://github.com/0al-spec/agent-surface/hash/policy-decision/v1` | top-level `policy_decision_hash` |
| receipt | `https://github.com/0al-spec/agent-surface/hash/receipt/v1` | top-level `receipt_hash` and `receipt_signatures` |
| Portable Replay Bundle record | `https://github.com/0al-spec/agent-surface/hash/replay-record/v1` | top-level `record_hash` |
| Portable Replay Bundle | `https://github.com/0al-spec/agent-surface/hash/replay-bundle/v1` | top-level `bundle_hash` |
| Replay Validation Report | `https://github.com/0al-spec/agent-surface/hash/replay-report/v1` | top-level `report_hash` |

All other members, including extension members, are part of the hashing view.
Omitting an unknown member before hashing is therefore an integrity failure,
not extension tolerance. A party that receives a redacted or filtered object
MAY carry its hash as an opaque reference but MUST NOT claim to have recomputed
it without the complete hashing view.

The Action Input hash commits to the exact validated wire input and prevents a
receipt from being attached to different input. For an idempotency-required
action, the runtime first applies the manifest-pinned Idempotency Input
Normalization profile and sends that fixed-point value as the wire input. The
hash function itself still performs no default insertion, equivalence, or set
ordering: it commits to the already-normalized wire value so approval,
idempotency, execution evidence, and receipts cannot select different views.

The Action Output hash commits an application receipt to the exact
schema-valid `payload.output` carried by the corresponding Action Response.
The producer computes it only after output-schema validation, and a consumer
that has the complete response MUST recompute it before accepting the receipt
as bound result evidence. The hash performs no default insertion, redaction,
equivalence, or ordering beyond RFC 8785 canonicalization of that exact wire
value.

For an idempotency-required action, `input_schema_hash` commits to the complete
I-JSON document retrieved from `input_schema` using the Action Input Schema
domain above. That schema MUST be self-contained: every `$ref` or `$dynamicRef`
MUST be a same-document fragment reference, and retrieval redirects MUST NOT
change the final authenticated origin. The runtime and application MUST verify
the declared hash before using the schema for normalization, approval, hashing,
or execution. A missing or mismatching document is `integrity_mismatch` and
MUST NOT fall back to a cached or newly fetched interpretation. Changing the
schema JSON data model changes `input_schema_hash`, the manifest hashing view,
`surface_version`, and `surface_hash`. A future surface-bundle profile can
define transitive external schema references; this profile does not.

The Action Execution Context hash independently commits to the mode and any
preview, precondition, expected-effect, reservation, or target-receipt
references used for the request. The raw `execution_token` is omitted because
it is confidential runtime-held material; the context instead carries its
`execution_token_hash`. It prevents the non-secret controls from being changed
while reusing an `input_hash`. It does not make a preview, reservation, or
target receipt into authority; the application still verifies the current
grant, policy, approval, resource state, and mode-specific rules atomically.

`execution_token_hash` is not a JCS object hash. The producer MUST generate at
least 128 bits of entropy with a cryptographically secure random-number
generator and encode the resulting 16 or more octets with unpadded RFC 4648
base64url. Its hash is the SHA-256 digest of those decoded token octets, encoded
with the same unpadded `sha-256:` base64url representation. A receiver can
validate syntax and decoded length, not entropy quality; it MUST reject padding,
non-base64url characters, or fewer than 16 decoded octets.
The raw token MUST be sent only over the authenticated confidential action
channel, and MUST NOT appear in a receipt, log, prompt, event, or agent-visible
context.

For the example token `FW_vZMMelqPUDUmFfxSr1A`, the required token hash is
`sha-256:tONJJscZ4IsDBfafODsBja4waqe1AtkpH54rXv_tPrk`.

The following minimal vector fixes the domain separation, wrapper, JCS, and
encoding rules. For the Grant domain and hashing view
`{"grant_id":"grant_123","scopes":["read"]}`, the canonical wrapper is:

```json
{"domain":"https://github.com/0al-spec/agent-surface/hash/grant/v1","object":{"grant_id":"grant_123","scopes":["read"]}}
```

Its hash value is:

```text
sha-256:Xbq37_fP9PBiWI3Bv7Ch0t8TV5ikJGm55MxncSeA38Y
```

The following manifest vector demonstrates self-field exclusion and nested JCS
member ordering. Given this received object:

```json
{"z":1,"surface_hash":"sha-256:Mckhl9gi8ePkXnuOJtPFNE1pe9LhilOGu1OgzxsXb8A","a":"x"}
```

the hashing view omits `surface_hash`, and the canonical wrapper is:

```json
{"domain":"https://github.com/0al-spec/agent-surface/hash/manifest/v1","object":{"a":"x","z":1}}
```

The recomputed value is `sha-256:Mckhl9gi8ePkXnuOJtPFNE1pe9LhilOGu1OgzxsXb8A`.
Inputs containing duplicate members, JSON negative zero, a lone Unicode
surrogate, or numeric input that would overflow binary64 to a non-finite value
are negative vectors and MUST be rejected before hashing.

An implementation MUST treat a supplied hash that does not match a recomputed
hash as invalid. It MUST NOT fall back to `grant_id`, `surface_version`,
`receipt_id`, or another mutable identifier. Hash-profile agility requires a
future profile with a distinct identifier and domain URI; silently substituting
a different digest or canonicalization algorithm is forbidden.
