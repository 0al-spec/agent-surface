## Consent Preview Contract

Before initiating issuance of, storing, or using a new Agent Grant, a runtime
conforming to the Runtime Mediator Profile MUST present a local consent
preview and obtain an affirmative user confirmation. The preview is derived
from verified protocol state; it is not a client-authored authorization object
and MUST NOT be treated as evidence of consent by the grant issuer or resource
server. The grant issuer independently obtains the consent required by its
issuance model. A co-located runtime and grant issuer MAY use one physical
screen only when it satisfies both logical responsibilities and preserves the
exact verified sources defined below.

The runtime MUST derive the preview exclusively from:

- the verified manifest snapshot identified by issuer, `app_id`,
  `surface_version`, and `surface_hash`;
- the exact proposed semantic Agent Grant request; the OAuth profile represents
  this request as `authorization_details`, while another issuance model MUST
  preserve the same Grant Object field semantics;
- when Purpose- and Task-Bound Agent Grant is selected, the exact
  issuer-authenticated purpose and optional task references and every current
  lifecycle and relationship result available to the runtime;
- the verified runtime, agent, and complete identity-evidence envelope,
  including every selected format, digest, verification, key-binding,
  freshness, and status profile and the selected Runtime Identity Profile and
  locally authenticated projection when present, plus the exact Runtime Attestation
  requirement and any current locally authenticated appraisal state when that
  optional profile is selected; and
- the complete Data Exposure Contract projection recomputed for the requested
  actions and scopes.

A Capability Match Result MAY identify the locally selected candidate, but it
is not an additional authoritative preview source. Before deriving the preview,
the runtime MUST validate the result's profile, the selected candidate's
`grant_request_hash`, complete bindings, candidate status, and freshness, then
independently recompute the request semantics, effects, approvals, and exposure
projection from the primary verified sources above. Copied matching summaries
MUST NOT replace that work.

Application-authored labels, descriptions, redaction summaries, recovery
descriptions, and Risk Explanation UI Hints are untrusted display hints. A
runtime MAY display only a valid hint selected from the exact pinned action
using the language and cache-binding rules of that feature. It MUST label the
text as application-authored, preserve the corresponding machine identifier,
classification, risk, mode, approval, effect, and recovery value, and MUST NOT
let prose replace, contradict, visually suppress, or rank verified semantics.
A detached copy in the request, Capability Match Result, agent output, or local
cache with another surface tuple is not an authoritative preview source.

The preview MUST make the following material semantics visible before the user
confirms:

- application identity, issuer, surface mode, surface version, and an
  inspectable surface hash; a proposal-only mode MUST be identified as an ASP
  authority upper bound rather than a promise that the application has no
  human or non-ASP write path;
- runtime identity, agent identity, passport hash, and the kind of passport
  evidence verified; when the Minimal Agent Passport Grant-Issuance Profile is
  selected, it MUST also show the consuming, hash, and verification profiles,
  name, uid, version, issuer, expiry, status freshness, relevant capability
  names, and the verification boundary of any executable binding; when a Runtime
  Identity Profile is selected, the preview
  MUST show the requested profile and every locally authenticated identity
  facet; if the app-scoped binding id, claims revision, or complete server
  projection is not yet available, the preview MUST label it unresolved and
  state that a second local confirmation of the returned projection is required
  before storage or use;
- when Runtime Attestation is selected, its framework and concrete profile,
  verifier id, maximum age, proof-key thumbprint, claimed Target Environment
  coverage, and whether current appraisal is accepted and fresh; if the
  app-scoped attestation binding, accepted appraisal, or server-derived
  assurance is not yet available, the preview MUST label it unresolved and
  require a second local confirmation before storage or use; raw Evidence,
  measurements, reference values, and Verifier diagnostics MUST NOT be shown;
- exact action identifiers, scopes, locations, and resource filters;
- absolute expiration time, human-readable duration, budgets, and other
  constraints;
- when Purpose- and Task-Bound Agent Grant is selected, the exact purpose id
  and revision, optional task id and revision, purpose-only or task-bound mode,
  effective expiration, and any parent or child Grant relationship; an
  authenticated issuer label MAY accompany but MUST NOT replace those opaque
  references;
- each selected action's risk, static execution mode, approval requirement,
  and required companion stages; when a Risk Explanation UI Hint exists, its
  selected localization MAY accompany but MUST NOT replace those values;
- maximum effect envelopes, highlighting write, shared, external, and
  irreversible effects; actions with an external effect MUST also warn that
  their actual outcome can be partial or unknown;
- required dry-run or reservation stages and available compensation or revert
  actions with their limitations;
- when the optional Impact Simulation feature is presented, its complete
  coverage and truncation metadata, exact `covered`, `not_covered`, or
  `indeterminate` outcome, and the distinction between request coverage and
  later execution admission;
- requested credential profile, credential-release policy, any parent or child
  grant fields actually present in the proposed request, and receipt
  requirements;
- when the Approval Receipt Profile is selected, its exact profile and each
  action's accepted producer roles and maximum approval age, including that a
  runtime receipt is a Grant-caveated runtime statement rather than independent
  proof of a human gesture; and
- effective data-exposure sources, class identifiers and classifications,
  redaction policy, and retention obligations; and
- when the Remote Processing Privacy Profile is selected, its exact path
  commitment, deterministic classification ceiling, every source that must fit
  that ceiling, and the distinction between application-authenticated Runtime
  Identity evidence and runtime-local downstream evidence; and
- when the Agent Training Use Policy Profile is selected, its exact permitted
  and prohibited classes by source, with training use and plaintext retention
  shown as independent dimensions.

The runtime SHOULD additionally identify its locally known operator and
processing environment. Such operator, model-provider, tool-recipient, and
concrete proof-method statements are runtime-local assertions unless backed by
separate verified evidence. They MUST be labeled with their verification status
and MUST NOT be presented as application-verified Grant Object fields. When the
Remote Processing Privacy Profile is selected, its path and ceiling are
semantic Grant fields, but provider names and recipient inventory remain local
evidence unless another profile verifies them. When Agent Training Use Policy
is selected, its effective class set is also a semantic Grant field, while a
provider's claimed enforcement remains local evidence. Without that profile,
training use is unspecified and MUST NOT be inferred from the selected path.

A runtime MAY group or summarize repeated entries, but every selected action,
companion stage, resource filter, material effect, and exposure source MUST
remain inspectable before confirmation. Progressive disclosure MUST NOT hide an
irreversible or external effect, an unknown value, an incomplete exposure
contract, credential release, or a material recovery limitation behind a
benign aggregate label. A scope-only summary is insufficient because action
and execution-stage allow-lists are independently authoritative.

The user MAY select a strict subset only when the resulting request remains
valid and closed over every required companion action. The runtime MUST derive
and present a new projection from that exact reduced request. It MUST NOT repair
an invalid selection by silently adding an action, scope, location, resource,
or data path. If local policy narrows the request, the narrowed exact request is
the one that MUST be shown and confirmed.

The local preview lifecycle is:

```text
derived -> presented -> confirmed | declined
   ^           |
   +--- stale -+
confirmed -> request sent -> granted | rejected
```

Any change to issuer, application, surface hash, runtime-agent-passport tuple,
Passport consuming, hash, or verification profile, Passport artifact or
lifecycle result, executable-integrity result, Runtime Identity Profile,
binding id, claims revision or projected identity facet, Runtime Attestation
requirement, concrete profile, verifier, maximum age, proof key, stable binding,
server-derived assurance, or current accepted appraisal state, actions, scopes,
locations, resource filters, constraints, budgets, expiration, credential
profile, receipt requirements, surface mode, execution or effect declarations,
or resolved exposure contracts makes the preview stale. A stale
preview MUST be regenerated and confirmed again before a request is sent or a
returned grant is stored or used. Decline terminates the local flow; the runtime
MUST NOT continue authorization in the background.
For a selected Purpose Binding, a changed purpose id, task id, revision,
purpose-to-task relationship, lifecycle result, or removal of either reference
also makes the complete preview stale.
Changing a Risk Explanation UI Hint necessarily changes the surface hash and
therefore stales the complete preview even though the prose is not authority.
The runtime does not patch the displayed hint while preserving the prior
confirmation.
Changing a runtime-local operator, provider, recipient inventory, or
enforcement-policy assertion within the same Grant-bound processing path, or a
concrete proof-method or proof-key assertion that was shown to the user, also
makes the local preview stale even when it does not alter the semantic Grant
request. That local assertion is not sent as authority to the grant issuer. A
change to the Remote Processing Privacy Profile or path value is a semantic
request change and requires a new Grant rather than this local-only refresh.

Presentation timestamps, UI session identifiers, authentication gestures, and
local confirmation timeouts are local policy and are not portable consent
evidence.

After authorization, the runtime MUST compare the returned authoritative Grant
Object with the exact locally confirmed request and the same pinned manifest.
Immediately before storing or using the result, it MUST also re-evaluate every
semantic and runtime-local input that produced the preview. A changed issuer,
surface, request, tuple, or passport validity state invalidates the issuance
result and requires a new issuer consent flow. If only a labeled runtime-local
operator, provider or same-path recipient inventory, concrete proof-method, or
proof-key assertion changed, the runtime MUST regenerate the local preview for
the returned grant and obtain fresh local confirmation before storage or use;
it does not treat that assertion as new grant authority.
If the pre-request preview marked any Runtime Identity Profile output
unresolved, the runtime MUST likewise regenerate the preview with the complete
returned projection and obtain fresh local confirmation before storage or use.
If it marked Runtime Attestation output unresolved, the runtime MUST regenerate
the preview with the returned stable binding, server-derived assurance, and
current accepted appraisal state and obtain the same second confirmation. An
unattested or non-accepted result is not a silent attenuation of an attested
request; it is a failed issuance result.
The grant issuer still derives its own consent view from that exact projection;
neither local confirmation is issuer-side authorization evidence.

The returned object adds grant-issuer output such as `grant_id`,
subject, credential binding, effective exposure projection, and `grant_hash`.
It MAY be a semantically narrower valid subset under this comparison:

- issuer, `app_id`, surface version and hash, runtime id, agent id, Passport
  consuming profile, hash profile, artifact hash, verification profile, and
  requested credential profile MUST remain exactly equal; when the
  Runtime Identity Profile was selected, a returned projection that was already
  locally authenticated MUST remain exactly equal, an unresolved projection
  requires the second confirmation above, and its repeated credential-binding
  values MUST always match;
- when Runtime Attestation was selected, the returned object MUST remove the
  request-only requirement and contain the exact stable binding, concrete
  profile, verifier, maximum age, and proof key accepted by the server; its
  repeated credential-binding values and server-derived assurance MUST agree,
  its authoritative appraisal state MUST still be accepted and fresh, and an
  initially unresolved output requires the second confirmation above;
- when the Remote Processing Privacy Profile was selected, the returned
  constraint MUST preserve the exact requested profile and path and add only
  the deterministic output-only classification ceiling; a missing, changed, or
  client-supplied ceiling is invalid rather than an attenuation;
- when the Agent Training Use Policy Profile was selected, the returned profile
  MUST remain exact and `permitted_classes` MUST be a canonical set subset of
  both the requested set and the returned effective exposure-class union; an
  added class or omitted constraint is authority widening;
- when Purpose- and Task-Bound Agent Grant was selected, the returned profile,
  purpose id and revision, and optional task id and revision MUST remain exactly
  equal; the runtime MUST separately re-resolve authenticated current state and
  require the task still to belong to that exact purpose. Substituting a
  sibling, updating a revision, or dropping the task is not server attenuation,
  while `expires_at` can only move earlier;
- returned actions, scopes, and locations MUST be set subsets of the confirmed
  values and MUST remain closed over required companion actions;
- `expires_at` MAY be no later. A returned `budgets` object MUST retain every
  requested dimension with an equal or smaller limit; it MAY add a supported
  standard dimension as a further restriction. Cost currency MUST remain equal
  and each cost partition attenuates independently without borrowing. Returned
  `repositories` and `pull_requests` MUST remain present when requested and
  MUST be non-empty set subsets. Every other constraint MUST remain
  structurally equal unless its defining profile supplies an explicit
  attenuation order understood by the runtime; implementations MUST NOT guess
  that an unknown array, enum, or extension value is more restrictive;
- when the Approval Receipt Profile was selected, its profile MUST remain exact,
  requirements MUST project exactly to the returned approval-bearing actions,
  a `user_or_app` accepted-role set MAY be a non-empty subset, and
  `max_age_seconds` MAY be no greater; every other mode retains its fixed roles;
- requested audit profile and required signer roles MUST remain equal;
  issuer-derived signer keys can be added only when the selected issuance and
  receipt-signing profiles define that output;
- returned credential binding MUST repeat the confirmed tuple and satisfy the
  requested credential profile; a `proof_bound` request MUST NOT become a
  bearer credential. Its confirmation key, certificate thumbprint, or channel
  binding MUST match the evidence authenticated or registered for that runtime
  during issuance; merely recognizing the method or key format is insufficient.
  If the local preview displayed a concrete intended proof method or key, the
  returned binding MUST match it or the runtime MUST reject the result and
  obtain fresh confirmation; and
- effective `data_exposure` MUST be the exact deterministic projection
  recomputed for the returned action and scope subsets.

Manifest-declared action modes, effects, risks, and recovery semantics are not
grant fields that the issuer can rewrite; they remain fixed by the returned
grant's pinned surface hash. Subject, grant id, credential binding details,
effective projection, and hash are expected server output, not authority
widening. Any value that is wider, incomparable under these rules, or bound to
a different tuple or surface MUST be rejected without storing or using its
credential, and the user MUST be sent through a fresh consent flow.

The grant issuer's consent view MUST present the common material semantics it
can independently derive from the verified request, manifest, tuple, and
exposure projection. When Remote Processing Privacy is selected, this includes
the exact requested path commitment and server-enforced ceiling, labeled so the
commitment is not mistaken for independently verified downstream topology. It
MUST also show the effective Agent Training Use class set when that profile is
selected and warn that allowed training influence is not reversed by plaintext
deletion or revocation. When Approval Receipt is selected, it MUST show every
effective action role and maximum age and explicitly distinguish accepting a
runtime statement from application-side approval. It is not required to repeat
runtime-local operator, recipient, or processing-path assertions. It MUST NOT
trust client-supplied human-readable prose as the authoritative description.
When Purpose- and Task-Bound Agent Grant is selected, it MUST show the exact
issuer-owned purpose and optional task references, their current relationship
and lifecycle state, purpose-only or task-bound mode, and effective expiration;
any safe label remains informational.
Its final approved subset remains authoritative for issuance. The local runtime
preview reduces surprise and app-controlled UI risk, but it does not replace
issuer authentication, consent, or the application's obligation to enforce the
issued grant.

Expected effects and previews MUST be identified as maximum or predicted
semantics rather than a guarantee that a commit will occur. Compensation MUST
NOT be described as exact rollback; only a declared `revert` action with
enforceable prior-state preconditions can make that narrower claim. Missing or
unknown actions, exposure classes, source contracts, risk values, or effect
values fail closed as `surface_incompatible`; omission MUST NOT be rendered as
"no access", "no risk", or "no exposure".

This contract standardizes the semantic inputs and staleness rules for a
preview, not layout, icons, ordering, accessibility mechanisms, or biometric
confirmation. The optional Impact Simulation feature below defines a bounded
local machine projection for example actions; it does not change the required
canonical preview or turn an example into consent or authority. Localization
remains runtime-local except for selection and fallback of the optional
publisher-authored Risk Explanation UI Hint. The contract deliberately defines
no `preview_id`, consent hash, signed approval object, or portable
human-readable wire payload. Such evidence requires a separate approval
profile.

## Impact Simulation

This draft assigns the following optional core feature identifier:

```text
agent-surface/feature/impact-simulation
```

The feature is a bounded, Runtime Mediator-local supplement to one Consent
Preview. It gives deterministic examples of known manifest actions that are
covered, not covered, or not currently decidable under the exact proposed
semantic Grant request and current runtime evaluation inputs. It is not a
negotiated profile, manifest member, Grant constraint, capability, policy
decision, execution preview, approval, receipt, credential, consent record, or
prediction that an action will succeed. An implementation declares the feature
only in its conformance feature inventory; it MUST NOT add the identifier or an
Impact Simulation Result to the semantic Grant request.

An Impact Simulation Result is a closed I-JSON object. Its top level contains
exactly `feature`, `evaluated_at`, `valid_until`, `bindings`, `coverage`, and
`examples`. The `bindings`, `surface`, `delegate`, `capability_match`,
`coverage`, requested-coverage, unrequested-coverage,
example, and action objects are also closed. Embedded Effect Model and Data
Exposure Contract objects retain the closed shapes and extension rules of
their defining sections. `feature` MUST exactly equal the identifier above.
This feature defines no `profile`, `schema_version`, `simulation_id`,
simulation hash, consent hash, signature, or portable confirmation field.

Example:

```json
{
  "feature": "agent-surface/feature/impact-simulation",
  "evaluated_at": "2026-07-19T10:00:00Z",
  "valid_until": "2026-07-19T10:05:00Z",
  "bindings": {
    "surface": {
      "issuer": "https://code.example.com",
      "app_id": "code.example.com",
      "surface_version": "2026-07-19",
      "surface_hash": "sha-256:<base64url-digest>"
    },
    "grant_request_hash": "sha-256:<base64url-digest>",
    "delegate": {
      "runtime_id": "application_runtime_456",
      "agent_id": "local_agent_789",
      "identity_evidence_hash": "sha-256:<base64url-digest>"
    },
    "capability_match": {
      "match_id": "match_01J2E7M2V6Z91Y2R3B4C5D6E7F",
      "evaluated_at": "2026-07-19T10:00:00Z",
      "valid_until": "2026-07-19T10:05:00Z"
    },
    "agent_inventory_revision": "agents-42",
    "adapter_inventory_revision": "adapters-9",
    "local_policy_revision": "local-policy-18",
    "enterprise_policy_revision": "enterprise-policy-7",
    "user_preferences_revision": "preferences-4"
  },
  "coverage": {
    "requested": {
      "total": 2,
      "included": 2,
      "complete": true
    },
    "unrequested": {
      "total": 1,
      "included": 1,
      "truncated": false
    },
    "selection_algorithm": "highest-risk-then-action-id-v1"
  },
  "examples": [
    {
      "request_relation": "requested",
      "outcome": "covered",
      "reasons": [],
      "action": {
        "action_id": "comment.create",
        "scope": "comments.write",
        "mode": "commit",
        "risk": "public_side_effect",
        "approval": "user_or_app",
        "required_companion_action_ids": [],
        "maximum_effects": [
          {
            "effect_id": "comment-publish",
            "operation": "publish",
            "resource_type": "comment",
            "visibility": "shared",
            "boundary": "internal",
            "reversibility": "irreversible",
            "domain": "communication"
          }
        ],
        "data_exposure": {
          "classes": ["repository.content"],
          "redaction": {"mode": "none"},
          "retention": {"mode": "transient", "delete_on_grant_end": true}
        },
        "recovery": {
          "available_action_ids": [],
          "limitations": ["irreversible", "no_recovery_action"]
        }
      }
    },
    {
      "request_relation": "unrequested",
      "outcome": "not_covered",
      "reasons": ["action_not_requested"],
      "action": {
        "action_id": "comment.propose",
        "scope": "comments.propose",
        "mode": "propose",
        "risk": "propose",
        "approval": "none",
        "required_companion_action_ids": [],
        "maximum_effects": [],
        "data_exposure": {
          "classes": ["repository.content"],
          "redaction": {"mode": "none"},
          "retention": {"mode": "transient", "delete_on_grant_end": true}
        },
        "recovery": {
          "available_action_ids": [],
          "limitations": []
        }
      }
    }
  ]
}
```

`evaluated_at` and `valid_until` are RFC 3339 UTC timestamps with the `Z`
suffix and MUST satisfy `evaluated_at < valid_until`. `valid_until` MUST be no
later than the earliest contributing identity-evidence status, capability-match,
inventory, policy, preference, runtime-identity, attestation, or local maximum
simulation freshness deadline. Passing that time invalidates the complete
result.

`bindings.surface` contains exactly `issuer`, `app_id`, `surface_version`, and
`surface_hash` from the verified manifest snapshot. `grant_request_hash` is
the Canonical Object Hash of the exact candidate-specific semantic Grant
request defined by Capability Matching. The runtime MUST recompute it from the
primary request and MUST NOT copy it without verification from a Capability
Match Result or caller.

`bindings.delegate` contains exactly `runtime_id`, `agent_id`, and
`identity_evidence_hash`. They are the compact selected base delegate binding
projected from `delegate.runtime`, `delegate.agent`, and the complete envelope
in the exact request. The runtime recomputes the hash under the Agent Identity
Evidence hash domain; an artifact digest is not a substitute. Selected runtime-identity, Runtime
Attestation, privacy, training-use, approval-receipt, and other optional
request semantics remain bound through `grant_request_hash`; their current
runtime-local inputs remain subject to the complete Consent Preview staleness
rules.

`bindings.capability_match` is REQUIRED and is either `null` or contains
exactly `match_id`, `evaluated_at`, and `valid_until` from the fresh Capability
Match Result used to identify the selected candidate. A runtime is not required
to create a Capability Match Result before this feature and uses `null` when it
did not use one; it MUST NOT omit the member. When it uses a result the binding
MUST be exact and the timestamps MUST satisfy
`capability_match.evaluated_at <= evaluated_at < valid_until <=
capability_match.valid_until`. The runtime MUST locate the exact candidate
whose agent id, identity-evidence hash, and `grant_request_hash` match the selected
delegate and request, then verify the complete Capability Match Result
bindings, candidate status, and reasons against the same current primary
inputs. It MUST also independently recompute the equivalent candidate decision
and every action projection from those primary inputs. A stale result, missing
exact candidate, binding mismatch, invalid causal ordering, or difference
between the retained and recomputed status or reasons invalidates the complete
simulation. A copied candidate summary is not an authoritative simulation
source.

When `capability_match` is `null`, the runtime MUST independently evaluate the
selected candidate with the same inputs, status rules, blocking-reason
vocabulary, and classification rules as the Capability Match Result Profile.
This local equivalent decision need not be serialized as a Capability Match
Result, but it MUST produce the same candidate status and blocking reasons that
a fresh exact result would have produced. Thus `null` means that no result was
used; it does not permit a weaker, action-local, optimistic, or
implementation-defined decision.

The five revision members are REQUIRED. `agent_inventory_revision`,
`adapter_inventory_revision`, and `local_policy_revision` are non-empty opaque
strings. `enterprise_policy_revision` and `user_preferences_revision` are
either non-empty opaque strings or `null` when that input does not exist. They
have the same exact-equality semantics as the Capability Match Result bindings.
A runtime that cannot name a current required input MUST NOT substitute an
empty string, old revision, or invented revision merely to produce a result.

`coverage` contains exactly `requested`, `unrequested`, and
`selection_algorithm`. Each count is a non-negative I-JSON safe integer.
`selection_algorithm` MUST equal `highest-risk-then-action-id-v1`.
`requested` contains exactly `total`, `included`, and `complete`. A valid
result exists only when the exact semantic request contains from one through
64 action identifiers: each requested action MUST appear exactly once,
`requested.included` MUST equal `requested.total`, and `complete` MUST be the
literal `true`. If the request contains zero or more than 64 actions, the
runtime MUST atomically omit the complete optional action simulation and retain
the canonical Consent Preview; it MUST NOT fabricate or sample requested
actions or claim partial coverage.

`unrequested.total` is the number of actions in the pinned manifest that are
not in the exact request. `unrequested.included` is the lesser of that value
and eight. `truncated` is `true` exactly when `total` is greater than
`included`. The runtime selects those examples by descending minimum standard
risk severity, using the Risk Taxonomy order, then by ascending unsigned
lexicographic order of UTF-8 `action_id` bytes. A supported extension risk uses
its required conservative standard mapping. An unsupported or invalid mapping
makes the action or surface `surface_incompatible`; it is not assigned a low
risk or skipped. This selection is deterministic and prevents a presenter from
choosing only benign omitted actions.

The `examples` array contains all requested examples first in ascending
unsigned lexicographic order of UTF-8 `action_id` bytes, followed by the
selected unrequested examples in their risk-descending selection order. It
contains at most 72 entries. The tuple (`request_relation`,
`action.action_id`) is unique. Every identifier MUST resolve exactly once in
the pinned manifest; a runtime MUST NOT fabricate an action, copy an action
from another snapshot, or silently substitute a similarly named companion.

Each example contains exactly `request_relation`, `outcome`, `reasons`, and
`action`. `request_relation` is `requested` or `unrequested`. `outcome` is
`covered`, `not_covered`, or `indeterminate`:

- for every requested example, selected-candidate status `compatible` maps to
  `covered` with an empty `reasons` array;
- for every requested example, selected-candidate status `incompatible` maps
  to `not_covered` with exactly the sorted unique codes from that candidate's
  definitive blocking reasons;
- for every requested example, selected-candidate status `indeterminate` maps
  to `indeterminate` with exactly the sorted unique codes from that candidate's
  indeterminate blocking reasons; and
- every unrequested example remains `not_covered` and its `reasons` array is
  exactly `["action_not_requested"]`.

The mapping is candidate-wide: every requested example in one result has the
same outcome and `reasons` array. It deliberately projects only the decisive
blocking codes after the complete candidate status has been determined.
Advisory reasons MUST NOT be serialized. For an incompatible candidate,
indeterminate blocking reasons that were overridden by a definitive blocking
reason MUST NOT be serialized; for an indeterminate candidate, no definitive
blocking reason can exist. Sorting uses ascending unsigned lexicographic order
of UTF-8 code bytes, and duplicate codes caused by different reason subjects
collapse to one string. The reason subject and repeated occurrences are
deliberately lost only after the candidate-wide decision; their omission MUST
NOT be used to calculate that decision action by action.

`covered` does not mean that a Grant will be issued or that a later invocation
will pass approval, active-Grant, session, input, precondition, reservation,
budget, capacity, current policy, or final application checks.
`indeterminate` MUST NOT be presented optimistically as covered or definitively
denied.

`reasons` is a sorted array of unique machine reason-code strings. Except for
`action_not_requested`, its complete core vocabulary and classifications are
exactly those defined by **Candidate Status and Reasons** for a Capability Match
Result:

| Classification | Allowed core reason codes |
| --- | --- |
| Indeterminate | `identity_evidence_profile_unsupported`, `identity_evidence_status_unavailable`, `runtime_identity_unavailable`, `runtime_attestation_unavailable`, `input_unknown` |
| Definitive | `identity_evidence_missing`, `identity_evidence_invalid`, `capability_missing`, `adapter_unavailable`, `schema_unsupported`, `execution_stage_unsupported`, `scope_unavailable`, `approval_unsupported`, `risk_denied`, `effect_unsupported`, `recovery_unsupported`, `data_exposure_unsupported`, `retention_unsupported`, `remote_processing_unsupported`, `training_use_unsupported`, `sandbox_unsatisfied`, `runtime_identity_invalid`, `runtime_attestation_unsupported`, `policy_denied` |
| Impact Simulation-specific definitive | `action_not_requested` |

The runtime MUST implement the complete vocabulary above and MUST NOT create a
local alias for a Capability Match Result reason. `action_not_requested` is
valid only for an unrequested `not_covered` example, and it is the sole reason
for such an example; candidate blocking or advisory codes MUST NOT be copied to
an unrequested action because the candidate decision covers the exact requested
set. A missing requested scope, unclosed required companion set, malformed
request, or stale primary input invalidates or stales the complete simulation
under the primary request and freshness rules; it MUST NOT be represented by a
per-example reason.

An extension reason code MUST be a collision-resistant URI and retains the
definitive or indeterminate classification assigned by its supported Capability
Match Result profile. An unknown blocking extension code defaults to
indeterminate, as it does in a Capability Match Result. A supported definitive
extension blocking code is included for an incompatible candidate; a supported
or unknown indeterminate extension blocking code is included for an
indeterminate candidate. Advisory extension codes are omitted. A `covered`
requested example has no reason. A requested `not_covered` example has at least
one definitive reason. An `indeterminate` example has at least one
indeterminate reason and no definitive reason. Human-readable explanations are
runtime-local presentation, not members of this object.

The `action` object contains exactly `action_id`, `scope`, `mode`, `risk`,
`approval`, `required_companion_action_ids`, `maximum_effects`,
`data_exposure`, and `recovery`. The runtime MUST independently copy or derive
these fields from the exact pinned action and request:

- `scope`, `mode`, `risk`, and `approval` repeat the manifest values without
  relabeling or attenuation;
- `required_companion_action_ids` is the sorted unique recursive closure of
  required companion actions for that action, excluding the action itself;
- `maximum_effects` is the complete manifest effect envelope in declaration
  order, or an empty array when the action correctly omits `effects`;
- `data_exposure` is the complete manifest-pinned action exposure contract;
  for a requested action it MUST equal the corresponding source contract in
  the recomputed proposed Data Exposure projection, while for an unrequested
  action it describes only hypothetical potential disclosure and MUST NOT be
  presented as effective Grant exposure; and
- `recovery` contains exactly `available_action_ids` and `limitations`.
  `available_action_ids` is the exact sorted unique set of recovery actions
  declared for the action in the same retained surface that are also present
  in the proposed request and its required companion closure. It is sorted by
  ascending unsigned lexicographic order of UTF-8 action-id bytes and contains
  each action exactly once even when several relationships name it. The actions
  are only potentially available: inclusion is not issuance, approval, current
  authority, satisfied recovery preconditions, or a promise of success.
  `limitations` is derived exactly from the retained declaration:

  - `irreversible` is present if and only if at least one
    `maximum_effects` entry has the effective standard reversibility
    `irreversible`;
  - `external_outcome_may_be_unknown` is present if and only if at least one
    `maximum_effects` entry has the effective standard boundary `external`;
  - `recovery_window_limited` is present if and only if the action declares at
    least one outbound `execution.recovery_actions` relationship with a finite
    positive `recovery_window_seconds`; and
  - `no_recovery_action` is present if and only if the action has mode
    `commit`, has a non-empty `maximum_effects` array, and declares no outbound
    `execution.recovery_actions` relationship.

  For a standard effect value, its effective standard value is the literal
  value. For a supported extension value, the runtime MUST use the defining
  specification's required conservative mapping to the standard
  `reversibility` or `boundary` value before applying these conditions. A
  missing, invalid, or unsupported conservative mapping makes the action or
  surface `surface_incompatible`; the runtime MUST NOT omit a limitation or
  derive a reassuring lower-severity value.

  These four core codes appear if and only if their conditions apply; absence
  of a recovery action from the proposed request does not create
  `no_recovery_action` when a valid relationship exists in the retained
  manifest. A supported collision-resistant URI limitation code is included if
  and only if its defining profile says its condition applies to the retained
  declaration. Unsupported extension limitation semantics make the action or
  surface `surface_incompatible`; they are not silently omitted. The complete
  `limitations` array is sorted by ascending unsigned lexicographic order of
  UTF-8 code bytes and contains each applicable code exactly once.

  The `irreversible` and `external_outcome_may_be_unknown` tests apply to the
  maximum effects of every state-changing mode. `no_recovery_action` does not
  apply to a `reserve` action, including reservation acquire, renew, or release:
  its cleanup contract is represented by the required companion closure and
  the reservation release, consumption, invalidation, and expiry semantics.
  Nor does it apply to `compensate` or `revert`; those actions are already
  independently authorized recovery stages, and this projection MUST NOT infer
  recursive recovery for them.

  Actions in mode `read`, `dry_run`, or `propose` have no committed
  `maximum_effects` and cannot declare a recovery relationship; therefore both
  `available_action_ids` and `limitations` are empty. Both arrays remain
  present for every mode. They are a canonical declaration projection, not a
  recovery promise; the canonical Consent Preview continues to show the exact
  effect ids, recovery modes, windows, and preconditions. An unavailable
  recovery action or irreversible effect MUST NOT be described as rollback.

A malformed action, unresolved companion, unclosed requested subset, unknown
scope, unsupported risk or effect mapping, missing exposure contract, or
inconsistent recovery relationship is a failure of the primary surface or
request, not an `indeterminate` simulation example. The runtime follows the
ordinary fail-closed `surface_incompatible` or request-invalid path and MUST
NOT use an Impact Simulation Result to make the primary input appear usable.

This v1 feature produces action examples only. It does not define a mapping
from a Grant resource constraint to a particular action-input field. A runtime
MUST NOT invent or probe an out-of-filter resource, contact the application to
discover one, infer a constraint-to-input binding from field names or prose, or
claim that a concrete resource would be allowed or denied. Exact resource
filters remain visible in the canonical Consent Preview. A future profile can
define concrete resource examples only with a machine-readable binding and
non-enumerating privacy rules.

The runtime derives the result without invoking an application action, sending
an Action Request, running a `dry_run`, validating an application state
precondition, acquiring a reservation, consuming budget or capacity, creating
a session, requesting approval, or contacting an action endpoint. In
particular, `maximum_effects` is a static manifest envelope, not the
application-produced `expected_effects` for one input and state snapshot.

The complete result remains inside the user-controlled Runtime Mediator
boundary. The runtime MUST NOT send it to the application or authorization
server as request input, expose it to an agent or Agent Adapter, copy it into a
Grant, credential, Policy Decision, approval or action receipt, Human
Elicitation request or response, Action Request or Response, prompt, tool
instruction, or privileged instruction channel. A component that nevertheless
receives a detached out-of-band result MUST discard it and MUST NOT treat it as
authority, consent, approval, policy evidence, or a reason to skip an ordinary
check. If a sender embeds the feature identifier or result in a closed ASP
request, Grant, receipt, approval, policy, action, or elicitation object that
does not define that member, the receiver MUST reject the complete enclosing
object under its ordinary structural validation; it MUST NOT remove only the
unexpected member and continue.

Risk Explanation UI Hint prose is not part of the result and MUST NOT affect
outcome, reasons, inclusion, ordering, or truncation. A presenter MAY attach
one valid selected hint only after validating the complete machine result and
retrieving the hint independently from the same pinned action. It MUST label
the text as publisher-authored and keep it distinct from the runtime-derived
example. A malformed or stale hint is suppressed under its own rules without
changing the simulation.

The examples supplement rather than replace the canonical Consent Preview.
Every requested action, companion stage, scope, location, resource filter,
constraint, material effect, approval, recovery limitation, and exposure
source remains inspectable before confirmation. The presenter MUST describe
`covered` as no stronger than "would be covered by this proposed Grant" and
MUST NOT label it "safe", "approved", "will succeed", or equivalent. If no
unrequested action exists, the result honestly contains no unrequested example;
the runtime MUST NOT invent a denial or present that absence as unlimited
authority.

The result has no independent confirmation or authority lifecycle. It is
derived and presented as part of one local Consent Preview. Any condition that
makes that preview stale also makes the complete simulation stale. In
addition, expiry or any change to its surface, request hash, delegate tuple,
Capability Match Result binding, agent or adapter inventory, local or
enterprise policy, user preferences, selected action, outcome, or projected
machine semantics invalidates the complete result. The runtime MUST regenerate
it from all current sources; it MUST NOT patch one example, carry forward the
unrequested sample, or preserve confirmation of the old preview.

A structurally invalid, detached, expired, stale, partially inconsistent,
incorrectly ordered, incorrectly counted, or incorrectly truncated result MUST
be atomically suppressed. The runtime falls back to the complete canonical
Consent Preview and MUST NOT render only the fields or examples it recognizes.
Suppression of this optional supplement does not repair an invalid primary
manifest, request, tuple, policy, or exposure projection.

After local confirmation and dispatch of the issuance request, the simulation
is only transient local presentation state. It MUST NOT be used as the active
Grant view. A returned Grant that is a valid narrower subset does not inherit
examples for omitted authority; the runtime derives active management and use
from the authoritative returned Grant and retained manifest. Rejection,
expiry, revocation, renewal, exchange, child derivation, or a later surface
version MUST NOT reactivate, mutate, or reinterpret the pre-issuance result.
Deriving post-issuance or historical examples is outside this feature.
