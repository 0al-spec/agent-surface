<a id="asp-privacy"></a>
# ASP Privacy

> [!NOTE]
> This is an authoritative module selected by the ASP Document Set Catalog.
> `drafts/agent-surface.md` is a generated aggregate reading view.

- Document ID: `https://github.com/0al-spec/agent-surface/documents/privacy`
- Exact version: `0.1.0-draft.1`
- Canonical path: `drafts/modules/privacy.md`

## Exact Normative Dependencies

- `https://github.com/0al-spec/agent-surface/documents/core` at `0.1.0-draft.1` (canonical `drafts/modules/core.md`)
- `https://github.com/0al-spec/agent-surface/documents/authorization` at `0.1.0-draft.1` (canonical `drafts/modules/authorization.md`)
- `https://github.com/0al-spec/agent-surface/documents/evidence` at `0.1.0-draft.1` (canonical `drafts/modules/evidence.md`)


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

## Remote Processing Privacy Profile

The Data Exposure Contract describes which application-originated data can
cross the application boundary, while the Runtime Identity Profile describes
the controlling runtime. Neither one, by itself, constrains every agent, model,
tool, adapter, subagent, or secondary runtime that can receive that data after
the boundary. An application and runtime that need an interoperable whole-path
restriction use the optional profile defined here. Its identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1
```

This profile requires the Data Exposure Contract, the Runtime Identity Profile,
and the Consent Preview Contract. It binds a runtime commitment and an
application-enforced disclosure ceiling into the semantic Grant. It does not
turn a client declaration, issuer echo, Grant hash, management posture, or
Runtime Identity locality into independent evidence that a downstream
processor followed the commitment.

### Processing Path Commitment and Baselines

The **processing path** is the complete set of components that can receive
application-originated plaintext or a semantically equivalent representation
while carrying out the Grant. It includes the controlling runtime, selected
agent, model providers, tools, MCP servers, adapters, subagents, ungranted
secondary runtimes, diagnostic processors, and any other recipient under
runtime control. A local bridge that sends prompts to a remote model has a
remote processing path even when the bridge itself executes on the user's
device.

A client selects the profile with this request-only closed object:

```json
{
  "constraints": {
    "remote_processing": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1",
      "path": "enterprise_managed"
    }
  }
}
```

`profile` and `path` are REQUIRED and unknown members are forbidden. `path` is
exactly one of `local_user_device`, `enterprise_managed`, or
`remote_user_selected`. The request MUST NOT contain `classification_ceiling`.
The path predicates are mutually exclusive over one resolved path:

- `local_user_device` means every data-bearing component executes on the same
  user device as the controlling runtime and no application-originated data or
  equivalent representation crosses from that device to a processor. The
  server-derived Runtime Identity projection MUST have
  `execution.locality` equal to `user_device` and `execution.verification`
  equal to `registered` or `attested`; that necessary condition does not prove
  the absence of downstream egress.
- `enterprise_managed` means at least one data-bearing component can execute
  remotely, the controlling runtime has `management.posture` equal to
  `enterprise_managed`, and the runtime or its authenticated enterprise policy
  has mapped every remote recipient to the same exact Runtime Identity
  `authority_id`. A domain name, network location, provider label, employee
  login, or self-asserted management claim is insufficient.
- `remote_user_selected` means at least one data-bearing remote recipient is
  outside the verified enterprise boundary and every such recipient and its
  operator is known to the runtime and affirmatively selected or accepted in
  the local consent flow. A path containing both local and such remote
  components uses this value.

A path with an unknown recipient, incomplete processor inventory, unresolved
operator, or processor whose policy cannot be evaluated cannot be selected or
used under this profile. Matching remains `indeterminate` until the missing
input is resolved. The path MUST NOT be represented as `local_user_device`, silently
folded into `enterprise_managed`, or treated as no remote processing. An
`application_embedded` controlling runtime cannot use the local or enterprise
value merely because it is co-located with application code. It can use
`remote_user_selected` only when every recipient is resolved and the consent
view conspicuously identifies the app-operated trust boundary; otherwise the
profile fails closed.

After validating the request, the authorization server returns the same exact
`profile` and `path` plus the deterministic output-only
`classification_ceiling`:

| `path` | `classification_ceiling` |
| --- | --- |
| `local_user_device` | `sensitive` |
| `enterprise_managed` | `private` |
| `remote_user_selected` | `public` |

For example:

```json
{
  "constraints": {
    "remote_processing": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1",
      "path": "enterprise_managed",
      "classification_ceiling": "private"
    }
  }
}
```

The returned object is closed and contains exactly `profile`, `path`, and
`classification_ceiling`. The ceiling uses the Data Exposure Contract
protection order and is this versioned profile's conservative baseline, not a
universal trust ranking. The authorization server MUST NOT rewrite `path`, and
there is no inferred attenuation order among path values. Local, enterprise,
or application policy MAY reject a path or impose a stricter local ceiling,
but a different wire mapping requires a new collision-resistant profile
identifier.

No path in this profile admits the `credential` classification. The ceiling
does not authorize credential disclosure, does not weaken the separate
`credential.release` capability and constraints, and never makes an Agent
Surface Grant Credential releasable. A profile that deliberately carries
credential-class application data requires a separate specification.

### Issuance and Data-Path Enforcement

The manifest MUST advertise this profile in
`compatibility.remote_processing_profiles`. A semantic Grant request selecting
it MUST also select the Runtime Identity Profile and MUST include the
request-only `constraints.remote_processing` object above. The complete request
object, including exact `profile` and `path` but excluding the server-only
ceiling, is part of the Semantic Grant Request Hash.

Before issuer consent and issuance, the authorization server MUST:

1. authenticate the runtime and derive its exact active Runtime Identity
   projection;
2. validate that the requested profile is advertised and that the controlling
   runtime satisfies the necessary Runtime Identity predicate for the selected
   path;
3. independently derive the complete effective `data_exposure` source closure
   from the pinned manifest and approved actions and scopes;
4. resolve every class identifier in that closure to its pinned manifest
   classification; and
5. reject issuance if any classification is above the deterministic ceiling.

The server MUST reject an unknown class, missing projection, client-supplied
ceiling, mismatched path output, or unsupported profile with
`invalid_authorization_details` under the OAuth profile. It MUST NOT make an
incompatible request appear valid by deleting one class from an exposure
entry, inventing a narrower redaction policy, omitting a source, or assuming
that a resource filter removes the protected data. The user can instead
approve a whole action or scope subset whose recomputed source closure fits the
same exact path.

The returned `constraints.remote_processing` object, effective
`data_exposure`, and complete Runtime Identity projection are included in the
authoritative Grant Object, `grant_hash`, token response, introspection response,
and server-side Grant state. Before every protected disclosure, the application
MUST validate the exact object, deterministic ceiling, active Runtime Identity
binding, and full exposure closure. These checks prove what the application
will disclose under the Grant; they do not prove what a conforming or malicious
runtime does after receipt.

Before every application-originated payload crosses to the selected agent or
another downstream component, the controlling runtime MUST independently:

- recompute the applicable source entry and pinned class classifications;
- verify that the actual complete path still satisfies the Grant-bound path
  predicate;
- apply any stricter local classification or policy; and
- verify that every recipient can enforce the redaction, retention, and
  processing-path restrictions.

If any check is false or unknown, the runtime MUST block and discard the
pending disclosure before downstream dispatch and fail it as
`remote_processing_violation`. The offending value, recipient details, and
policy evidence MUST NOT be copied into the error, receipt, trace, prompt, or
ordinary log. A malformed or mismatched authoritative Grant remains
`integrity_mismatch`, an inactive or mismatched Runtime Identity remains
`runtime_untrusted`, and a payload outside its declared class, redaction, or
retention envelope remains `data_exposure_violation`. The new error is only for
a valid Grant whose current processing path or recipient enforcement state no
longer satisfies its bound constraint.

The path and ceiling apply Grant-wide. A workflow that needs sensitive local
processing and only public data in a remote tool requires separate Grants and
separate source closures under this version. Implementations MUST NOT combine
the two flows and claim that a field-level split occurred when the manifest
defines only source-level classes.

### Lifecycle, Delegation, and Evidence Boundary

A change to `profile` or `path` changes the semantic Grant request, Capability
Match Result, Consent Preview, and Grant hash. It requires a fresh issuance and
issuer consent flow; an implementation MUST NOT migrate an active Grant or
session in place. A recipient, operator, provider policy, processor inventory,
or enforcement-capability change within the same path value makes the local
match and consent preview stale and requires fresh local confirmation before
further disclosure. If application policy binds that changed fact, a new Grant
is also required.

An ungranted subagent, remote model, tool, adapter, or secondary runtime remains
inside the controlling runtime's path. Creating a child Grant does not erase
that fact for data the parent transmits. Every child Grant that selects this
profile has its own independently resolved path commitment and ceiling. A child
bound to another runtime MUST NOT copy the parent's path claim or Runtime
Identity evidence. This version defines no exposure projection for forwarding
application-originated data previously received by a parent into a separately
granted child. The parent MUST NOT perform that transfer; the child must obtain
the data through its own independently authorized application resource, action,
or event source and effective `data_exposure` projection. A future transfer
profile would need to preserve the original source, classes, and both Grant
bindings. In particular, a parent `local_user_device` commitment cannot be used
to route application data to a remote child.

Expiry, suspension, or revocation stops new disclosures immediately. Existing
retention and `delete_on_grant_end` obligations continue to apply to plaintext
already delivered. A runtime that learns that an earlier disclosure violated
the path MUST stop further use, isolate the affected work, retain only
data-minimized incident evidence, and initiate the applicable Grant suspension
or revocation path; ASP does not claim that this reverses an external
disclosure.

The `grant_hash` in a receipt binds that receipt to the selected restriction.
It is not a processing receipt, provider attestation, proof of recipient
topology, or proof of deletion. A runtime MAY retain a local, data-minimized
path revision or policy-decision hash for audit, but portable receipts and
public errors MUST NOT enumerate provider accounts, endpoints, tenant ids, or
processor topology unless a separate evidence profile defines that disclosure.

This profile does not specify training or model-improvement use. Locality,
enterprise management, a restrictive classification ceiling, and transient
plaintext retention MUST NOT be presented as a no-training promise.

### Remote Processing Consent and Privacy

The local Consent Preview MUST show the exact profile, path value, deterministic
ceiling, every effective source and class, and whether the full path predicate
is currently satisfied. It MUST separately label the app-authenticated
controlling Runtime Identity facets and the runtime-local downstream
commitment. Known operator and recipient labels MAY be shown, but their
verification boundary MUST be explicit and they MUST NOT be represented as
application-verified Grant fields.

The authorization server's consent view MUST show the same requested path,
effective ceiling, and source closure derived from its pinned manifest and
approved request. It MUST state that the ceiling is application-enforced while
the downstream path is an authenticated runtime commitment unless a separately
negotiated evidence profile proves more. Issuer consent to this object does not
certify a provider or waive the runtime's local confirmation responsibility.

Active-grant management views MUST show the exact hash-bound path and ceiling
without exposing application payloads or a recipient inventory. Applications
and runtimes SHOULD minimize retained path metadata and use opaque local
references for diagnostic correlation. A provider name, authority id, endpoint,
or recipient graph can reveal organizational relationships and user choices;
none is included in this profile's Grant object.

## Agent Training Use Policy Profile

The Data Exposure Contract controls disclosure, redaction, and plaintext
retention. The Remote Processing Privacy Profile controls the whole processing
path and its classification ceiling. Neither contract states whether a runtime,
agent, or provider can reuse disclosed data to improve a model or reusable
processing artifact. An application and runtime that need an explicit,
interoperable answer use the optional profile defined here:

```text
https://github.com/0al-spec/agent-surface/profiles/agent-training-use/v1
```

This profile requires the Data Exposure Contract, Remote Processing Privacy,
and the Consent Preview Contract. Its constraint is an authorized secondary-use
policy, not evidence that a provider complied with the policy and not a legal,
deletion, or model-unlearning claim.

For this profile, **training use** means using application-originated plaintext
or a semantically derived representation to create, update, select for future
reuse, evaluate for model improvement, or improve a reusable model, adapter,
reward or ranking function, persistent embedding or retrieval index, training
or evaluation dataset, annotation set, or corpus. The definition applies
whether that use occurs during or after execution of the exact current
Grant-authorized task. Fine-tuning, distillation, model-improvement evaluation,
retaining examples for a later training run, and an online update that can
leave durable influence are training use. Ephemeral inference context strictly
necessary to execute the current task is not training use only when it creates,
updates, selects, evaluates, or retains no reusable artifact covered by this
definition; it remains subject to the Data Exposure redaction and retention
contract. Operational security or abuse processing is not training use unless
its data or results are repurposed for such a reusable artifact.

### Training Class Constraint and Attenuation

The semantic Grant request carries this closed constraint:

```json
{
  "constraints": {
    "training_use": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-training-use/v1",
      "permitted_classes": []
    }
  }
}
```

`profile` and `permitted_classes` are REQUIRED and unknown members are
forbidden. `permitted_classes` is an array of unique manifest `data_classes`
identifiers ordered by ascending Unicode code point. Every requested identifier
MUST appear in the union of class ids in the deterministic exposure projection
for the exact requested actions and scopes.

An empty array is an explicit prohibition on training use of every
application-originated class disclosed under the Grant. A non-empty array names
the post-redaction classes that can participate in training, but it permits a
given source payload only when that source satisfies the complete whole-source
predicate below. Omission of `training_use` means unspecified; it MUST NOT be
rendered, matched, or enforced as either an empty array or a permission. A
runtime or application policy that requires no training MUST require this exact
profile with an empty array.

This profile defines no field-level selection rule. A complete source payload
is eligible for training use only when:

```text
source.data_exposure.classes is a subset of training_use.permitted_classes
```

If a source contains both `repository.content` and `user.identifier`, a Grant
that permits only `repository.content` does not permit training on any part of
that source payload. The application can publish a separate source with an
independently enforced redaction contract; the runtime MUST NOT infer which
bytes belong to the permitted class. Derived data retains every source class
for this decision unless a separately negotiated irreversible-transformation
profile defines and proves a different classification. Hashing, embedding,
pseudonymizing, summarizing, or aggregating data alone does not escape the
constraint.

After issuer-side approval, the authorization server returns the same closed
object with an effective set satisfying:

```text
returned permitted_classes
  is a subset of requested permitted_classes
  intersected with the returned effective data-exposure class union
```

The server MAY remove a requested class because of application policy or user
choice and MUST remove a class that is no longer exposed after an approved
action or scope subset. It MUST NOT add a class. The exact returned array MUST
remain present even when empty, and its order is canonical. The sequence
`["repository.content", "user.identifier"]` to
`["repository.content"]` to `[]` is attenuation; the reverse direction is
authority widening and requires a new request and fresh consent.

Training permission never widens actions, scopes, sources, processors,
redaction, classification ceilings, or plaintext retention. The Remote
Processing Privacy check still evaluates the full exposure closure, including
classes that are prohibited for training. A lower training-use set cannot make
sensitive data eligible for a `public` processing ceiling.

`retention.mode` continues to govern runtime-controlled plaintext, examples,
and corpora. A training permission does not authorize storage beyond that
contract. Conversely, `transient` plaintext retention does not mean no
training: an allowed online update can leave durable influence after plaintext
deletion. A consent or management view MUST show those two dimensions
separately and MUST NOT label an empty training set as “transient only.”

### Issuance, Enforcement, and Lifecycle

The manifest MUST advertise this profile in
`compatibility.training_use_profiles`. A request selecting it MUST also select
the Remote Processing Privacy Profile. The complete request constraint is part
of the Semantic Grant Request Hash. The effective returned constraint is part
of the authoritative Grant Object, `grant_hash`, token response, introspection
response, management view, and server-side Grant state.

Before consent and issuance, the authorization server MUST independently derive
the exact effective exposure closure, validate every requested class and the
source-level rule above, apply application policy, and obtain issuer-side user
approval for the effective set. A non-empty client request is not training
authority by itself. Under the OAuth profile, an absent required member, unknown
or duplicate class, non-canonical order, unadvertised profile, or class outside
the requested exposure union is `invalid_authorization_details`.

Before storing or using the returned Grant, the runtime MUST recompute the
returned exposure closure and reject a missing constraint, added class,
non-subset result, unknown class, stale source, or mismatch among Grant, token,
and introspection representations as `integrity_mismatch`. A valid strict
subset is privacy attenuation and does not require a second expanding consent.

Before any training use, the controlling runtime MUST first apply the ordinary
Grant, Data Exposure, and Remote Processing validations. An inactive Grant
fails with its existing Grant lifecycle error, an invalid source or retention
contract fails as `data_exposure_violation`, and a failed path commitment fails
as `remote_processing_violation`. Under an otherwise valid Grant, exposure
projection, and path, the runtime MUST verify that the source payload's complete
class set is a subset of the effective `permitted_classes` and that every
downstream recipient enforces an equal or stricter training policy. Failure of
either training-specific check is `training_use_denied`, and the payload MUST be
blocked before training dispatch. If a required provider capability or policy
input is unknown or stale, matching is `indeterminate` and disclosure remains
blocked; it is not optimistic consent.

A provider, operator, model, processing configuration, policy, or enforcement
capability change makes the local Capability Match Result and Consent Preview
stale even when the Remote Processing path value remains the same. A change to
the requested `permitted_classes` set for the same root authorization changes
the semantic request and requires a new issuer consent flow. The server-side
subset during that issuance and a derived child or token exchange that satisfies
the explicit attenuation rules below MAY narrow the set without expanding
consent; the derived Grant receives its own authoritative hash and lineage. An
existing Grant MUST NOT be mutated in place.

Expiry, suspension, or revocation prohibits every new training use and new
disclosure under the Grant and activates its existing plaintext cleanup
obligations. It does not reverse training use that was permitted and completed,
prove that a model forgot data, or authorize continued use of retained material.
Data obtained under a Grant for a class absent from `permitted_classes` remains
prohibited from later training use after Grant termination; expiration does not
convert a prohibition into permission.

### Delegation, Consent, and Evidence Boundary

An ungranted subagent, model, tool, adapter, or secondary runtime remains under
the controlling runtime's effective training constraint. The runtime MUST NOT
send a source payload to a component whose training policy is wider or unknown.

For a derived child Grant, when the parent selected this profile, the child
MUST retain the constraint and satisfy:

```text
child permitted_classes
  is a subset of parent permitted_classes
  intersected with child effective data-exposure classes
```

The child retains an explicit empty array when the intersection is empty. A
child MUST NOT omit the constraint, add a class, or reuse the parent's provider
commitment as evidence for another runtime. When the parent omitted this
profile, a derived child MAY add the empty-array form as a further restriction
only when the parent already selected Remote Processing Privacy and the child
retains its exact profile and path value while resolving its own runtime-bound
path commitment and ceiling. Otherwise adding this profile, or adding a
non-empty permission, requires a fresh independent root Grant and consent. As
defined by Remote Processing Privacy, the parent does not forward previously
received application payloads into a separately granted child; the child
obtains data through its own authorized application sources.

The local Consent Preview and issuer consent view MUST show the exact requested
or effective permitted set, every prohibited effective class, and every source
in which each class occurs, alongside the separate path, ceiling, redaction,
and plaintext-retention semantics. A non-empty set MUST carry a conspicuous
warning that permitted training can leave durable influence in a model,
adapter, or index after plaintext deletion and Grant revocation. An omitted
profile MUST be labeled unspecified, never “no training.” Provider statements
MUST be labeled as runtime-local commitments unless a separate evidence profile
verifies them.

Active-grant management views MUST show the exact hash-bound permitted set and
the same no-unlearning boundary. The `grant_hash` in a receipt binds the receipt
to that policy but proves neither provider compliance nor training or
unlearning. A runtime MAY retain a data-minimized local decision record keyed by
`grant_hash`, source ids, policy revision, decision, and timestamp. This profile
defines no portable provider receipt, compliance attestation, legal-purpose
taxonomy, or verifiable unlearning mechanism.

## Privacy Considerations

Agent Surface Protocol can reveal sensitive metadata:

- which agents the user owns
- which runtime the user runs
- which app resources the user delegates
- which tasks the user asks agents to perform
- which approvals were accepted or denied

Applications SHOULD request only the metadata needed for authorization and audit.
Runtimes SHOULD minimize agent and passport disclosure when possible. Receipts
SHOULD support pseudonymous user references where legal and operationally
appropriate.

Purpose and task bindings reveal user intent, workflow structure, and
potentially sensitive relationships even when no application payload is
present. Their ids SHOULD be opaque and scoped to issuer, app, and app-scoped
subject; they MUST NOT embed repository, customer, prompt, goal, or task prose.
Safe labels, raw task inputs, relationship records, and purpose-policy internals
remain in authenticated issuer or user interfaces and MUST NOT enter Grants,
credentials, ordinary receipts, public errors, traces, prompts, or
agent-visible logs. Lookup failures MUST be uniform across unknown,
wrong-subject, wrong-app, wrong-revision, and unauthorized records. This
technical purpose restriction is not by itself evidence of GDPR or other legal
compliance.

Authorized Surface discovery can reveal account roles, tenant membership,
agent eligibility, and the existence of privileged or experimental
affordances. The projection endpoint therefore accepts no caller-selected
identity or affordance filter, returns one generic failure class, and prohibits
shared caching. `projection_id` and projected surface versions MUST be opaque
and non-semantic. Raw projection lifecycle keys, base-versus-projection diffs,
hidden member ids, policy names, entitlement records, and alternate-context
suggestions MUST NOT enter the manifest, Grant, receipt, event, trace, prompt,
agent-visible log, URL, referrer, or public error. An implementation SHOULD
retain the server-side projection mapping only while it is needed for active
issuance, Grant enforcement, bounded audit, or applicable legal obligations.

Approval and denial receipts reveal user decisions, timing, application and
runtime relationships, action frequency, and policy outcomes. They MUST contain
only an app-scoped user reference and hashes of the exact invocation, never raw
input, previews, credentials, execution tokens, hidden rules, authentication
artifacts, or globally correlatable approver identities. Runtime-local denials
SHOULD remain local when no Action Request was dispatched. Applications and
runtimes SHOULD retain complete Approval Receipts only for the bounded
idempotency, reconciliation, audit, and applicable legal period and MUST NOT
expose full denial evidence to the agent process merely for error handling.

Runtime identity metadata requires the same minimization. Grants and their
derived protocol artifacts use only the app-scoped runtime id, opaque binding
id, sanitized profile facets, claims revision, and policy-relevant assurance
references. External subjects, raw certificates, SVIDs, JWTs, management
records, attestation evidence, device serials, hardware handles, and recovery
material MUST remain in the authoritative verifier boundary and MUST NOT enter
receipts, events, traces, ordinary logs, prompts, or agent-visible context.

Runtime Attestation can expose uniquely identifying measurements, hardware and
firmware inventory, debug state, location-correlatable device identifiers, and
long-lived Attester keys. The runtime sends raw Evidence only to the selected
Verifier, and the application retains only the concrete profile's minimized
Attestation Result and authoritative appraisal record. Grants contain only the
stable opaque binding and policy-relevant assurance; authorized status views
expose at most the coarse current state. Consent, public errors, receipts,
events, traces, prompts, and ordinary logs MUST NOT disclose raw Evidence or the
specific failing measurement, reference value, or appraisal rule.

Passport artifacts and admission projections can expose stable agent uids,
issuers, capability inventories, security policies, executable paths, and code
measurements. Protocol-visible Grant state is limited to the app-scoped agent
id, optional locator, and exact consuming, hash, artifact, and verification
profile tuple. Raw Passport bytes, signatures, external issuer subjects, status
responses, executable paths, and code hashes MUST remain inside the applicable
verifier boundary.

Data Exposure Contracts make application-to-agent disclosure inspectable but
do not prove that a publisher classified its data correctly. A runtime MUST
treat application-authored labels and descriptions as untrusted hints, preserve
the manifest identifier and classification in consent and policy decisions,
and MAY apply a stricter local classification. Unknown classes, missing
contracts, and inconsistent grant projections fail closed; they MUST NOT be
rendered as no exposure.

Redaction and retention obligations apply to prompts, model context, tool
arguments, caches, diagnostic captures, and agent-visible logs under runtime
control, not only to the primary response object. A runtime MUST NOT select an
agent or remote processing path that cannot enforce the effective contract.
Deletion of runtime-controlled plaintext does not prove model unlearning or
deletion by an undeclared external processor. Training use and remote-agent
defaults are not implied by a retention declaration. The Remote Processing
Privacy Profile, when selected, applies a conservative Grant-wide ceiling and
requires the runtime to resolve the complete path before disclosure; it still
does not prove provider behavior. When Agent Training Use Policy is selected,
its explicit class set independently controls secondary use: an empty set means
no training use, a non-empty set permits only whole sources whose complete
class set is covered, and omission remains unspecified. A training permission
does not widen path, redaction, or retention constraints, and plaintext cleanup
or revocation does not prove that an allowed durable model influence was
removed.

Processing-path metadata can expose provider relationships, enterprise
boundaries, user choices, and regional deployment details. The Grant therefore
contains only the coarse path value and ceiling. Recipient inventory, endpoints,
account ids, enterprise mapping evidence, and provider-policy records remain in
the runtime or enterprise-policy boundary and SHOULD be retained only as long
as enforcement and data-minimized audit require.

Training-policy metadata reveals user choices, source classifications, and
provider capabilities. Protocol artifacts therefore carry only the profile and
canonical class set. Provider policy documents, account identifiers, model
names, enforcement inventories, local decision records, and audit evidence
remain within their applicable trust boundary and SHOULD be retained only as
long as enforcement, user management, and data-minimized audit require.

Consent previews contain sensitive relationship metadata even when they omit
application payloads. Implementations SHOULD avoid placing rendered previews in
telemetry, browser history, or general-purpose logs. A local preview is not
portable consent evidence and SHOULD be retained only as long as local policy
needs it to complete and audit the authorization flow.

Impact Simulation Results contain the same surface, delegate, Passport,
inventory, policy, preference, and requested-action relationship metadata.
They MUST remain within the user-controlled runtime boundary, MUST NOT contain
action input, concrete resource keys, hidden policy text, publisher prose, or
application payloads, and SHOULD be retained no longer than their parent local
preview. Telemetry SHOULD retain at most the feature identifier, request and
surface hashes, coverage counts, outcome counts, and machine reason codes under
a bounded local policy; it SHOULD omit action identifiers when aggregate
diagnostics suffice.

Active-grant management views contain the same relationship metadata plus
lifecycle state and usage-sensitive constraints. Applications and runtimes MUST
authenticate those views, avoid cross-subject enumeration, exclude credentials
and application payloads, and prevent caching or referrer leakage as defined by
Active Grant Management. Historical summaries SHOULD retain only the metadata
needed for user understanding, security audit, and applicable legal obligations.

Budget states and charges reveal workload volume, model usage, session
concurrency, and spend. Components MUST expose them only to the bound subject,
accounting authority, and authorized audit consumers, and SHOULD retain
fine-grained revisions no longer than reconciliation and audit require. Errors
and events MUST identify the budget dimension without disclosing another
session, tenant, model prompt, tool argument, or provider billing record.
For a descendant delegate, control events and `budget.state` MUST use the
effective lineage projection and per-target revision defined above; ancestor
identifiers, limits, counters, revisions, and sibling consumption are not part
of that delegate's disclosure.

Cross-system trace correlation can reveal relationships between otherwise
separate user actions, tenants, and services. `trace_id`, `span_id`, and
`tracestate` MUST NOT encode semantic identifiers or secrets. Components SHOULD
apply bounded retention, access control, and sampling independently of whether
the incoming trace flags request recording.

Preconditions, expected effects, resource keys, reservation conflicts, and
recovery targets can reveal sensitive application state. Schemas and approval
views SHOULD expose only what the user and runtime need to understand and
authorize the effect. Conflict responses MUST NOT identify another reservation
holder. Raw execution tokens are confidential runtime-held material and MUST
NOT enter receipts, logs, prompts, traces, or agent-visible context.
