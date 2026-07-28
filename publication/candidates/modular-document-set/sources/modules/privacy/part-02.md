# Remote Processing Privacy Profile

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

## Processing Path Commitment and Baselines

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

## Issuance and Data-Path Enforcement

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

## Lifecycle, Delegation, and Evidence Boundary

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

## Remote Processing Consent and Privacy

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

# Agent Training Use Policy Profile

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

## Training Class Constraint and Attenuation

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

## Issuance, Enforcement, and Lifecycle

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

## Delegation, Consent, and Evidence Boundary

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
