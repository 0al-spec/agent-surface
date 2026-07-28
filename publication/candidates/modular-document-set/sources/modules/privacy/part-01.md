## Data Exposure Contract

The manifest `data_classes` array defines the application-local data classes
used by exposure declarations. Every entry MUST contain a unique, stable `id`,
a `classification`, a non-empty `label`, and a non-empty `description`.
Defined classification values are:

- `public`: information intentionally available without user-specific access
- `private`: non-public application or user content
- `sensitive`: information whose disclosure can create material privacy,
  safety, financial, or organizational harm
- `credential`: secrets or authentication material

The protection order is `public` < `private` < `sensitive` < `credential`.

Class identifiers name semantic kinds of data, such as
`repository.content` or `user.identifier`; classifications describe their
minimum handling sensitivity. A publisher MUST assign the most protective
applicable classification when a class can contain data of different
sensitivities. Labels and descriptions are application-authored display hints,
not authority or evidence that a class is harmless. A runtime MUST preserve the
class identifier and classification when it renders an application label.
The `data_classes` array and every exposure `classes` array MUST be ordered by
ascending Unicode code point of the class identifier; duplicates are invalid.

Every resource, action, and event declaration MUST contain a `data_exposure`
object. The object describes the maximum application-originated data that can
reach the runtime or agent through that declaration after application-side
redaction. It has this shape:

```json
{
  "classes": ["repository.content", "user.identifier"],
  "redaction": {
    "mode": "policy",
    "policy_id": "repository-visible-fields-only",
    "summary": "Only fields visible to the connected repository user are returned."
  },
  "retention": {
    "mode": "bounded",
    "max_seconds": 7200,
    "delete_on_grant_end": true
  }
}
```

Examples in later sections that isolate execution, receipt, or error semantics
are declaration fragments and can omit unrelated required manifest members for
readability. A complete manifest cannot omit `data_exposure`.

`classes` MUST be an array of unique identifiers declared in `data_classes`.
It is a conservative maximum: every class that can occur on a success, partial
result, preview, structured error, pagination path, nested representation, or
event payload MUST be listed. An explicit empty array means that the declaration
delivers no application-originated data. Omission never means "no exposure".
A JSON Schema reference does not replace this declaration.

`redaction.mode` is `none` or `policy`. `none` means that the class set already
describes the unredacted representation and the object MUST omit `policy_id`
and `summary`. `policy` means the application applies a named policy before the
payload crosses the application boundary; it MUST include a stable non-empty
`policy_id` and a consent-safe non-empty `summary`. The application MUST apply
redaction before delivery. A runtime or agent MUST NOT be made responsible for
removing fields whose receipt would already violate the contract.

`retention.mode` is `transient` or `bounded`. `transient` prohibits durable
persistence of the disclosed payload by the runtime or agent. `bounded` MUST
include a positive integer `max_seconds`, measured from receipt, after which
runtime-controlled plaintext copies MUST be deleted. `transient` MUST omit
`max_seconds`. `delete_on_grant_end` is REQUIRED; when true, expiry or
revocation shortens the retention period and requires prompt deletion of
runtime-controlled plaintext copies. When false, the declared time bound still
applies. Hashes and data-minimized audit metadata MAY outlive the plaintext
only when another grant or policy requirement explicitly permits their
retention.

For a core control event, `transient` applies to the raw CloudEvent and its
application-originated payload; it does not prohibit the receiver from durably
projecting the minimum safety state that this protocol requires before terminal
acknowledgement. That projection MUST be data-minimized and limited to delivery
deduplication keys or hashes, the affected-grant hash, effective state revision,
state and retryability, and the session id, generation, and fence state when
applicable. It MUST NOT retain raw event data, ancestor identifiers, counter
values, thresholds, or unrelated session metadata. The receiver MUST retain
deduplication state through the effective replay window and safety state while
the affected grant or session can still admit or resume work. Once both the
effective replay window is closed and the affected authority can no longer
admit or resume work, the receiver MUST delete that projection; only a
non-reversible tombstone permitted by an independently declared bounded audit
policy MAY remain.

The resource contract applies to every representation and query result of that
resource. The action contract applies to all application-originated
agent-visible output from that action, including dry-run or proposal output,
success responses, partial results, and structured error details. It does not
describe application retention of agent-supplied action input. The event
contract applies to its payload. Core control events MUST also appear in the
manifest `events` array with `control: true` and an exposure contract; they
cannot bypass these rules merely because their delivery authority is
independent of the affected grant.

The application is responsible for classifying source fields and enforcing the
declared post-redaction envelope before delivery. This draft does not define a
field-level classifier and does not require a runtime to infer semantic data
classes from arbitrary payload bytes. A schema MAY carry implementation-specific
classification annotations, but those annotations do not replace the contract.

The authorization server MUST derive the issued grant's effective
`data_exposure` array from the exact pinned manifest and approved Grant Object
using this conservative source closure:

1. include every resource whose `read_scope` is an exact member of the granted
   `scopes`, even when a resource filter narrows the instances;
2. include every action whose `id` is an exact member of the granted `actions`;
3. include every non-control event whose `scope` is an exact member of the
   granted `scopes`; and
4. include every core control event advertised with `control: true`, regardless
   of the affected grant's scopes.

The conservative resource and event rules may display a class that a narrower
resource filter never returns, but they MUST NOT omit a class that remains
reachable. An unknown `control: true` event makes the surface incompatible with
this profile unless another negotiated profile defines its closure rule.
Every selected source is included, including one with an empty `classes` array.
Duplicate source pairs are invalid. Projection entries MUST be ordered first by
source kind in the order `resource`, `action`, `event`, then by ascending Unicode
code point of `source.id`. Each entry copies that source's complete
post-redaction contract:

```json
[
  {
    "source": {"kind": "resource", "id": "task"},
    "classes": ["repository.content", "user.identifier"],
    "redaction": {
      "mode": "policy",
      "policy_id": "repository-visible-fields-only",
      "summary": "Only fields visible to the connected repository user are returned."
    },
    "retention": {
      "mode": "bounded",
      "max_seconds": 7200,
      "delete_on_grant_end": true
    }
  }
]
```

Defined source kinds are `resource`, `action`, and `event`. The client MUST NOT
supply `data_exposure` in an Agent Grant authorization request. The
authorization server derives it after applying the approved subset and MUST
NOT omit a selected source. Its `classes`, `redaction`, and `retention` members
MUST be structurally identical to the pinned source declaration; a narrower
runtime policy is a local overlay and does not rewrite this projection.
The returned Grant Object and introspection response MUST contain the same
projection. The complete projection is part of the Grant Object hashing view
and therefore changes `grant_hash`.

Before storing or using a grant, the runtime MUST recompute this projection
from the exact pinned manifest and granted authority. It MUST require exact
structural equality, including source and class array ordering, and reject a
missing, extra, unknown, stale, or inconsistent projection as
`integrity_mismatch`. A
runtime MAY apply additional redaction or a shorter retention period as local
policy, but it MUST NOT widen the class set or retain plaintext longer. If it
cannot enforce the effective contract for the selected runtime-agent path, it
MUST refuse to use the grant for that path.

When the Remote Processing Privacy Profile is selected, the complete projection
is also the input to its Grant-wide classification-ceiling check. Every class
is evaluated at its pinned manifest classification; a processor path MUST NOT
drop a source or class, reinterpret a mixed-class payload, or rely on a
runtime-only redaction to fit the ceiling. A whole action or scope subset can be
approved only after the authorization server recomputes this source closure.

When the Agent Training Use Policy Profile is selected, the union of class
identifiers in this same complete projection bounds its `permitted_classes`.
The profile does not add a field-level classifier: a complete payload from one
source is eligible for training use only when every class in that source entry
is permitted. A runtime MUST NOT extract an allegedly lower-class field from a
mixed-class payload by inference; the application must publish a separately
redacted source contract when that distinction is required.

An exposure declaration never grants access and never weakens scope, resource,
action, subdelegation, or credential-release checks. In particular, declaring a
class with classification `credential` does not authorize its disclosure. An
Agent Surface Grant Credential remains non-releasable, and other credential
material can cross into agent-visible context only through the separately
authorized `credential.release` capability and its constraints.

If the application detects that a payload would exceed the effective contract,
it MUST block delivery and return `data_exposure_violation`. If the runtime
detects such a violation before agent delivery, it MUST discard the payload and
fail the operation with the same error. Either component records only
data-minimized evidence: the offending value MUST NOT be copied into the error,
receipt, trace, prompt, or audit log. Changing a data class or exposure contract
changes the manifest hashing view and requires a new `surface_version`; an
existing grant MUST NOT silently adopt the replacement contract.
