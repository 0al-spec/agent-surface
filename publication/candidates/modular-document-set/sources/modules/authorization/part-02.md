# Runtime Attestation Optional Profile

Runtime attestation is an optional extension to the Runtime Identity Profile.
The base ASP profile accepts an application-registered runtime id without
attestation; no implementation is required to support this section for MVP
conformance. An application that requires runtime integrity evidence uses the
framework defined here and one concrete attestation profile.

The framework identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/runtime-attestation/v1
```

This framework follows the RATS roles from RFC 9334:

- the Runtime, or a protected environment that measures it, is the **Attester**;
- a **Verifier** appraises Evidence against endorsements, reference values, and
  its Appraisal Policy for Evidence and produces authenticated Attestation
  Results; and
- the application authorization server is the **Relying Party** that applies
  its own Appraisal Policy for Attestation Results.

One component MAY perform multiple roles, but implementations MUST preserve the
logical trust and policy boundaries. Evidence is not an Attestation Result, a
Verifier decision is not the Relying Party's authorization decision, and none
of those artifacts is an Agent Grant.

## Attestation Discovery and Concrete Profiles

An application advertises support with the optional closed
`auth.runtime_attestation` object shown in the manifest example. It contains
exactly:

- `framework`, equal to the framework identifier above;
- `attestation_url`, an absolute HTTPS URL;
- `profiles_supported`, a non-empty array of unique collision-resistant
  concrete profile identifiers; and
- `verifiers`, a non-empty array of closed objects containing unique
  `verifier_id` values and non-empty unique `profiles` arrays. Every listed
  profile MUST also appear in `profiles_supported`.

Absence means the application does not support attestation under this draft. It
does not make the base runtime anonymous or non-conforming. A runtime MUST NOT
infer support from a TPM, TEE, Secure Enclave, SPIFFE credential, MDM record,
EAT media type, or hardware-backed key.

Every concrete profile identifier MUST define all of the following without
leaving security-critical choices to deployment guesswork:

- Attester, Target Environment, and layered or composite coverage;
- Evidence and Attestation Result formats, media types, required claims, and
  validation schemas;
- authenticated challenge request, Evidence submission, Result delivery or
  polling, correlation, timeout, and retry transport mappings;
- security envelopes, allowed algorithms, key types, authenticated key
  resolution, trust anchors, and algorithm-downgrade behavior;
- verifier identity, result authentication, status and key lifecycle;
- nonce, timestamp or epoch freshness, replay state, maximum ages, and clock
  skew;
- endorsement and reference-value resolution, appraisal-policy identity and
  versioning, and failure behavior when any input is unavailable;
- proof-key binding and its thumbprint algorithm;
- privacy minimization and which sanitized result claims the Relying Party may
  retain; and
- revocation, remediation, and transition semantics.

RFC 9711 EAT is a claims framework, not a complete runtime-attestation profile.
An implementation MUST NOT accept a generic EAT, arbitrary JWT or CWT, or a
media type alone. An EAT-based concrete profile MUST identify an exact
`eat_profile`, required claims and processing, security envelope, and
verification rules. RFC 9782 media types aid format negotiation but do not
validate the advertised content.

## Attestation Requirement and Stable Grant Binding

Attestation requires the Runtime Identity Profile. A semantic Grant request
selects it with the request-only closed object:

```json
{
  "runtime_attestation_requirement": {
    "profile": "https://verifier.example/profiles/eat-tpm-runtime/v1",
    "verifier_id": "verifier_7f3a",
    "max_age_seconds": 300,
    "proof_key_thumbprint": "sha-256:<profile-defined-thumbprint>"
  }
}
```

This object is a member of `delegate` and contains exactly the four fields
shown. `profile` and `verifier_id` MUST be an advertised pair.
`max_age_seconds` is a positive integer no greater than `9007199254740991`.
The concrete profile defines the public-key representation and exact thumbprint
calculation; the value MUST use the unpadded `sha-256:` syntax unless that
profile defines another collision-resistant hash identifier.

The client MUST NOT supply an attestation binding, assurance result, appraisal
state, result hash, policy hash, reference-value hash, raw Evidence, or raw
Attestation Result in the Grant request. The authorization server authenticates
the runtime, validates the exact requirement, obtains an accepted appraisal,
removes `runtime_attestation_requirement`, and returns this closed output-only
`delegate.runtime_attestation` object:

```json
{
  "binding_id": "atbind_01J2F7M2V6Z91Y2R3B4C5D6E7F",
  "profile": "https://verifier.example/profiles/eat-tpm-runtime/v1",
  "verifier_id": "verifier_7f3a",
  "max_age_seconds": 300,
  "proof_key_thumbprint": "sha-256:<profile-defined-thumbprint>"
}
```

`binding_id` is an opaque, collision-resistant, application-and-tenant scoped
identifier bound to the exact runtime identity revision, requirement, and
`grant_request_hash`; it MUST NOT be reassigned or reused for another request.
An idempotent replay of the same exact request MAY reuse it. The returned
`max_age_seconds` MUST be positive and no greater than the requested value; a
smaller value is an explicit attenuation. The complete stable object is included
in `grant_hash`. `credential_binding` MUST repeat `binding_id`, `profile`,
`verifier_id`, and `proof_key_thumbprint` as
`runtime_attestation_binding_id`, `runtime_attestation_profile`,
`runtime_attestation_verifier_id`, and
`runtime_attestation_proof_key_thumbprint`.

The selected proof key and Grant Credential proof key are distinct bindings.
They MAY use one key only when both concrete profiles allow it. Otherwise the
attestation profile MUST authenticate a cross-binding, and the application MUST
verify that binding on every action. Possession of either key alone MUST NOT be
silently substituted for the other.

When the accepted concrete profile covers a hardware-rooted measurement chain
through the exact Runtime Target Environment, the server-derived
`runtime_identity.assurance` contains exactly one corresponding entry:

```json
{
  "type": "hardware_attested",
  "profile": "https://verifier.example/profiles/eat-tpm-runtime/v1",
  "verifier_id": "verifier_7f3a"
}
```

The entry describes the stable required assurance profile, not current mutable
appraisal state. `runtime_identity.execution.verification` is `attested` only
when the same profile explicitly covers execution locality. Attestation of a
hardware root, boot layer, container host, or key without the Runtime Target
Environment MUST NOT be represented as runtime integrity or attested locality.

The complete attestation binding, Runtime Identity projection, assurance entry,
and repeated credential-binding fields MUST agree. A profile, verifier,
maximum age, proof-key, coverage, assurance, or stable binding change is
material: it changes the Runtime Identity claims revision, requires a new Grant
and Consent Preview, and MUST NOT be applied as an in-place appraisal refresh.
Every child Grant has its own semantic `grant_request_hash` and therefore needs
a child-specific challenge, accepted appraisal record, and stable attestation
binding, even when it retains the parent's Runtime Identity projection. A child
for a different runtime additionally needs that runtime's independent identity,
proof key, and Evidence; no child copies the parent's binding or Result.

## Challenge, Evidence, and Appraisal

Before Evidence is generated, `auth.runtime_attestation.attestation_url` returns
an authenticated, closed challenge object:

```json
{
  "framework": "https://github.com/0al-spec/agent-surface/profiles/runtime-attestation/v1",
  "challenge_id": "atch_01J2F8M2V6Z91Y2R3B4C5D6E7F",
  "nonce": "<unpadded-base64url-16-to-64-octets>",
  "issuer": "https://code.example.com",
  "app_id": "code.example.com",
  "audience": "https://example.com/runtime-attestation",
  "runtime_id": "application_runtime_456",
  "runtime_identity_binding_id": "rbind_01J2D7M2V6Z91Y2R3B4C5D6E7F",
  "runtime_identity_claims_revision": 3,
  "profile": "https://verifier.example/profiles/eat-tpm-runtime/v1",
  "verifier_id": "verifier_7f3a",
  "max_age_seconds": 300,
  "proof_key_thumbprint": "sha-256:<profile-defined-thumbprint>",
  "grant_request_hash": "sha-256:<base64url-digest>",
  "issued_at": "2026-07-14T10:00:00Z",
  "expires_at": "2026-07-14T10:02:00Z"
}
```

The endpoint MUST authenticate the requesting runtime binding before issuing a
challenge. `challenge_id` is collision-resistant and single-use. `nonce`
decodes to 16 through 64 unpredictable octets generated by a cryptographically
secure random-number generator. `audience` exactly equals the advertised
`attestation_url`; the other application and runtime fields come from the
pinned manifest, authenticated runtime record, and exact semantic Grant
request. `max_age_seconds` is the server-selected effective value and MUST be no
greater than the request. `issued_at` and `expires_at` are RFC 3339 timestamps,
and expiry MUST be short enough to satisfy the concrete profile and local
policy.

The concrete profile defines how Evidence authenticates the nonce and every
challenge binding. The Verifier MUST reject missing, altered, expired, or
replayed challenges, unexpected profile or media type, wrong audience, wrong
runtime or proof key, and untrusted or stale endorsements, reference values,
keys, or appraisal policy. A request change produces a different
`grant_request_hash` and requires a new challenge. A challenge and appraisal do
not claim an action idempotency key, consume a Grant budget, create an action
receipt, or authorize an effect.

The Verifier appraises Evidence and returns an authenticated Attestation Result
under the concrete profile. The application verifies the result's issuer,
signature or authenticated channel, profile, challenge, Attester and Target
Environment coverage, proof key, freshness, appraisal policy, and status before
applying its own Relying Party policy. It MUST NOT accept an Attester's
self-declared compliance bit as an Attestation Result.

Raw Evidence flows only to the Verifier. When the Verifier is separate, the
application receives only the profile-defined, privacy-minimized Attestation
Result. When roles are co-located, raw Evidence remains inside the logical
Verifier boundary and MUST NOT be copied into the Grant or application business
data. The runtime receives only the challenge and a sanitized state needed to
continue or diagnose the flow.

## Mutable Appraisal State

The application keeps mutable state outside the Grant Object:

```json
{
  "attestation_binding_id": "atbind_01J2F7M2V6Z91Y2R3B4C5D6E7F",
  "revision": 8,
  "runtime_id": "application_runtime_456",
  "runtime_identity_binding_id": "rbind_01J2D7M2V6Z91Y2R3B4C5D6E7F",
  "runtime_identity_claims_revision": 3,
  "profile": "https://verifier.example/profiles/eat-tpm-runtime/v1",
  "verifier_id": "verifier_7f3a",
  "proof_key_thumbprint": "sha-256:<profile-defined-thumbprint>",
  "grant_request_hash": "sha-256:<base64url-digest>",
  "result_hash": "sha-256:<profile-defined-result-digest>",
  "verifier_policy_hash": "sha-256:<profile-defined-policy-digest>",
  "reference_value_hashes": ["sha-256:<profile-defined-reference-digest>"],
  "state": "accepted",
  "verified_at": "2026-07-14T10:00:20Z",
  "fresh_until": "2026-07-14T10:05:20Z",
  "state_changed_at": "2026-07-14T10:00:20Z"
}
```

This record is authoritative application state, not a wire Attestation Result.
`revision` is a positive safe integer that strictly increments on every record
mutation, including a state transition or an accepted appraisal refresh.
The selected concrete profile defines the three hash algorithms and hashing
views. `reference_value_hashes` is sorted and unique. `fresh_until` MUST be no
later than the Evidence or Result expiry, requirement `max_age_seconds`,
Verifier key and status validity, appraisal-policy validity, or reference-value
freshness.

The state machine is:

```text
absent -> challenged
challenged -> appraising | indeterminate | revoked | superseded
appraising -> accepted | rejected | indeterminate | revoked | superseded
accepted -> stale | revoked | superseded
rejected | indeterminate | stale -> challenged | revoked | superseded
```

Only current `accepted` state satisfies the Grant requirement. Challenge expiry,
transport failure, unverifiable input, unavailable reference values, or an
unknown result produces `indeterminate`, never optimistic acceptance.
`rejected` means a current authenticated appraisal failed policy. `stale` means
freshness elapsed; the record is logically `stale` at `fresh_until` even if a
persisted transition has not yet run. `revoked` permanently invalidates the
stable binding.
`superseded` means a material stable binding or coverage change requires a new
Grant.

The application MUST check the exact record, revision, and current accepted
state before issuing a Grant, on introspection, before every action, and before
resuming a session. A non-accepted state makes introspection inactive, rejects
new actions as `runtime_untrusted`, and fences affected sessions before another
effect. It MUST NOT fall back to an unattested runtime, another verifier,
another profile, an older accepted result, or a different proof key.

Refreshing Evidence under the same exact stable binding and Runtime Identity
projection MAY update mutable hashes, revision, and freshness without changing
`grant_hash`. `rejected`, `indeterminate`, or `stale` state MAY return to a new
challenge and later `accepted` state if the same profile permits remediation.
`revoked` triggers the Semantic Grant Revocation Transition for every bound
Grant and derived Grant. `superseded` remains inactive until fresh consent and a
new Grant bind the replacement.

## Attestation Authority, Security, and Privacy

Attestation is evidence for a Relying Party policy. It MAY deny a Grant, require
narrower scopes, force stronger approval, or reject an action, but it MUST NOT
add actions, scopes, resources, credential release, or approval bypasses. An
accepted Result is not a credential and does not prove that the runtime remains
unchanged after measurement; freshness narrows but cannot eliminate that race.

The application MUST treat Verifier compromise, stale reference values,
ambiguous Target Environment coverage, replayed Evidence, proof-key substitution,
and appraisal-policy downgrade as security failures. A different policy or
reference-value set MUST NOT be called equivalent merely because both return
`accepted`. Runtime authentication, Agent Passport verification, Grant
proof-of-possession, and runtime attestation remain independent checks.

The Grant, introspection response, Consent Preview record, receipts, events,
traces, and ordinary logs MUST NOT contain raw Evidence or Results, measurements,
endorsements, reference values, hardware serials, device identifiers, Attester
keys, firmware inventory, debug state, or Verifier diagnostics. The Grant
contains only the stable binding, concrete profile, opaque verifier id,
proof-key thumbprint, and sanitized assurance reference. An authenticated and
authorized introspection or management view MAY additionally disclose only the
coarse current `accepted` or inactive state needed by that caller; mutable state
is never added to the Grant hashing view. Public errors MUST NOT reveal which
measurement, reference value, or appraisal rule failed.

Reference-value distribution, transparency services, and supply-chain statement
registration are outside this profile. Such systems can authenticate provenance
and history, but their presence alone does not prove current runtime state or
freshness.

# Agent Grant

## Grant Object

An Agent Grant binds a user, runtime, agent, versioned identity evidence,
application, surface, scopes, and caveats.

```json
{
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "subject": {
    "user": "user_abc"
  },
  "delegate": {
    "runtime": "application_runtime_456",
    "agent": "local_agent_789",
    "identity_evidence": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1",
      "format_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
      "artifact_ref": "agent-passport://local-agent",
      "artifact_digest": {
        "profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
        "value": "sha-256:<base64url-digest>"
      },
      "issuer": "https://issuer.example/agents",
      "subject": "agent-subject-opaque-7f3a",
      "verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
      "key_binding": {
        "profile": "https://example.com/profiles/issuer-key-thumbprint/v1",
        "value": "sha-256:<base64url-digest>"
      },
      "lifecycle": {
        "freshness_profile": "https://example.com/profiles/status-max-age/2026-01",
        "status_profile": "https://example.com/profiles/agent-passport-status/2026-01",
        "status_ref": "app-status-subject-4c18"
      }
    }
  },
  "resource_server": {
    "app_id": "code.example.com",
    "issuer": "https://code.example.com",
    "surface_version": "2026-06-25",
    "surface_hash": "sha-256:<base64url-digest>"
  },
  "locations": ["https://code.example.com/agent-actions"],
  "actions": ["pull_request.get", "comment.create"],
  "scopes": [
    "pull_request.read",
    "pull_request.comment"
  ],
  "constraints": {
    "repositories": ["example-org/example-repo"],
    "pull_requests": [13],
    "expires_at": "2026-06-25T20:00:00Z",
    "purpose_binding": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1",
      "purpose": {
        "id": "pur_01J2Q7M4K8X5",
        "revision": "rev_3"
      },
      "task": {
        "id": "tsk_01J2Q7N9C3V6",
        "revision": "rev_7"
      }
    },
    "write_approval": "required",
    "budgets": {
      "max_write_actions": 20,
      "max_tool_calls": 100,
      "max_model_tokens": 50000,
      "max_runtime_seconds": 1800,
      "max_parallel_sessions": 2,
      "cost": {
        "currency": "USD",
        "max_runtime_microunits": 4000000,
        "max_application_microunits": 1000000
      }
    },
    "credential_release": {
      "mode": "deny"
    }
  },
  "data_exposure": [
    {
      "source": {"kind": "action", "id": "comment.create"},
      "classes": ["repository.content"],
      "redaction": {"mode": "none"},
      "retention": {"mode": "transient", "delete_on_grant_end": true}
    },
    {
      "source": {"kind": "action", "id": "pull_request.get"},
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
  ],
  "credential_profile": "proof_bound",
  "credential_binding": {
    "method": "dpop",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "identity_evidence": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1",
      "format_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
      "artifact_ref": "agent-passport://local-agent",
      "artifact_digest": {
        "profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
        "value": "sha-256:<base64url-digest>"
      },
      "issuer": "https://issuer.example/agents",
      "subject": "agent-subject-opaque-7f3a",
      "verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
      "key_binding": {
        "profile": "https://example.com/profiles/issuer-key-thumbprint/v1",
        "value": "sha-256:<base64url-digest>"
      },
      "lifecycle": {
        "freshness_profile": "https://example.com/profiles/status-max-age/2026-01",
        "status_profile": "https://example.com/profiles/agent-passport-status/2026-01",
        "status_ref": "app-status-subject-4c18"
      }
    },
    "jkt": "<base64url-thumbprint>"
  },
  "audit": {
    "local_receipt": "required",
    "app_receipt": "required",
    "approval_receipt": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1",
      "requirements": [
        {
          "action_id": "comment.create",
          "accepted_roles": ["runtime"],
          "max_age_seconds": 300
        }
      ]
    }
  }
}
```

This object is the authoritative Agent Grant wire shape. A grant that authorizes
any Agent Surface action MUST contain non-empty `locations` and `actions`
arrays. `locations` is the allow-list of action endpoints and `actions` is the
authoritative allow-list of action identifiers. A resource-only grant can omit
them but cannot authorize an Action Request. Scope alone is never sufficient to
select an action. The authorization server derives the issued arrays from the
exact user-approved endpoints and stages and MUST NOT add companion actions
implicitly.

`resource_server` binds the Grant to the exact manifest used for interpretation.
When that manifest is an Authorized Surface Projection, `resource_server` MUST
also contain the exact `authorized_projection` Grant binding defined by that
profile. The binding is included in `grant_hash`; omitting it, copying it from
another projection lifecycle key, or matching only the projected
`surface_hash` makes the Grant invalid.

`locations` restricts only Action Requests; it is not an OAuth credential
audience and does not list `budget_state_url` or `session_control_url`. Those
endpoints accept only their closed safety operations, authenticate the same
exact Grant and delegate tuple under `agent_api.credential_audience`, and MUST
NOT infer action authority merely because the credential is valid there.

The authoritative action allow-list MUST satisfy the required companion closure
defined by the Action Execution Model. A list that contains a commit or
reservation acquisition without its required stages is an invalid Grant Object,
not a partially usable delegation.

This draft defines `constraints.repositories` and
`constraints.pull_requests` as resource allow-lists. `repositories`, when
present, MUST be a non-empty array of unique non-empty application repository
identifiers. `pull_requests`, when present, MUST be a non-empty array of unique
positive integer identifiers. Each list restricts the corresponding resource
dimension; absence means that this core profile adds no restriction for that
dimension. A grant issuer MAY return a non-empty set subset of a requested list
but MUST NOT add an entry or drop the member entirely, because omission would
widen the request. Other application resource-filter members are extension
constraints and require their defining profile to specify any attenuation
order.

OAuth `authorization_details` uses this same shape with the additional RFC 9396
`type` discriminator; it does not define aliases for Grant Object fields.
`credential_binding` is authorization-server output and MUST repeat the bound
runtime, agent, and complete identity-evidence envelope. A DPoP binding MUST additionally contain
`jkt`; an mTLS binding MUST instead contain `x5t#S256`. Those values use the
same encoding and semantics as the corresponding standard `cnf` members.
When the Runtime Identity Profile is selected, `delegate.runtime_identity` is
also authorization-server output and `credential_binding` MUST repeat its
binding id and claims revision as defined by that profile. The request-only
`delegate.runtime_identity_profile` selector is the request/Grant shape
exception within `delegate`; it MUST NOT remain in the authoritative Grant.
When the Pluggable Agent Identity Evidence Profile is selected, `delegate` and
`credential_binding` MUST each contain the same complete `identity_evidence`
envelope. Unlike runtime identity output, the client supplies the requested
projection from its local verification and the authorization server derives
and verifies every member independently. Passport-specific top-level delegate
fields are accepted only under the explicit legacy migration rules.
When Runtime Attestation is selected,
`delegate.runtime_attestation_requirement` is request-only and MUST be replaced
by the server-derived stable `delegate.runtime_attestation` binding. The
credential binding repeats its stable identifiers and proof key, while mutable
appraisal state remains outside the Grant Object.

When the Remote Processing Privacy Profile is selected, the request contains
`constraints.remote_processing` with only `profile` and `path`. The
authorization server MUST preserve both exactly and add the profile's
deterministic output-only `classification_ceiling` to the authoritative Grant.
That complete constraint is included in `grant_hash`, token and introspection
responses, management views, and protected-resource validation. It restricts
disclosure and does not prove downstream compliance.

When the Agent Training Use Policy Profile is selected, both request and Grant
contain `constraints.training_use`. The authorization server MAY return only a
canonical set subset of requested `permitted_classes` and MUST NOT add a class
or omit the constraint. The exact effective object is included in `grant_hash`,
token and introspection responses, management views, and runtime enforcement.
It authorizes only the defined secondary use and does not prove provider
behavior or model unlearning.

When the Purpose- and Task-Bound Agent Grant Profile is selected, request and
Grant both contain the exact closed `constraints.purpose_binding` object. The
authorization server MUST resolve the referenced issuer-owned records for the
authenticated subject and application, preserve the exact identifiers and
revisions it approved, and cap `constraints.expires_at` by their current
lifetime. The complete object is included in `grant_hash`, token and
introspection responses, session binding, consent and management views, and
protected-resource enforcement. It narrows the ordinary action, location,
scope, and resource intersection; it never grants authority by itself.

When the Approval Receipt Profile is selected, request and Grant both contain
the complete `audit.approval_receipt` object. The authorization server projects
its requirements to the returned action subset and MAY only narrow a
`user_or_app` role set or lower a maximum age as defined by that profile. The
effective object is included in `grant_hash`, token and introspection responses,
consent and management views, and protected-resource verification. It records
which producer roles the application can accept; it is not approval itself.
`data_exposure` is also authorization-server output. It is the complete
effective projection derived under the Data Exposure Contract and does not
grant authority independent of the action, scope, location, and resource
members from which it was derived.

## Grant Hash

The authorization server MUST add `grant_hash` after constructing the complete
authoritative Agent Grant, including `grant_id`, subject, delegate,
`resource_server.surface_hash`, effective constraints, credential profile, and
credential binding, and the effective `data_exposure` projection. It computes
the value with the Canonical Object Hash
Profile and persists the exact hashing view for the lifetime of the grant and
its audit-retention period.

Because `constraints.purpose_binding` is an effective constraint, its complete
profile, purpose reference, and optional task reference are covered by this
same hashing view. This profile defines no separate purpose, task, or binding
hash. A human-readable purpose description, task goal, or digest outside the
Grant cannot replace the hashed closed object or prove its current semantics.

The client MUST NOT supply `grant_hash` in an authorization request. Token and
introspection responses MUST return it with the authoritative grant. An action
request and every receipt under that grant MUST carry the same value. The
application MUST compare it with current authoritative grant state and reject a
mismatch as `integrity_mismatch`; selecting state by `grant_id` and ignoring a
hash mismatch is forbidden.

Attenuating, renewing, or otherwise changing any hashed member creates a new
`grant_hash`, even when a deployment retains a related identifier for lifecycle
tracking. Token rotation alone does not change `grant_hash` when the underlying
Agent Grant object is unchanged. Parent and child grants have independent
hashes and retain their explicit derivation linkage.

`grant_hash` does not prove that a grant is active, unrevoked, or within its
remaining stateful budget. Those mutable checks still use authoritative grant
state on every action.

## Budget Caveats and Accounting

`constraints.budgets` is the authoritative immutable limit declaration for the
Operations Safety profile. When present, it MUST contain at least one limit
from this object:

```json
{
  "max_write_actions": 20,
  "max_tool_calls": 100,
  "max_model_tokens": 50000,
  "max_runtime_seconds": 1800,
  "max_parallel_sessions": 2,
  "cost": {
    "currency": "USD",
    "max_runtime_microunits": 4000000,
    "max_application_microunits": 1000000
  }
}
```

Every count, duration, and microunit limit MUST be an integer from `0` through
`9007199254740991`. Absence means this ASP profile imposes no cap for that
dimension; `0` prohibits new consumption. `cost`, when present, MUST contain
`currency` and at least one of `max_runtime_microunits` or
`max_application_microunits`, and MUST NOT contain other members. An omitted
partition is uncapped by this ASP profile. `currency` is an uppercase
three-letter ISO 4217 code, and one microunit is one millionth of that currency
unit. Implementations MUST use integer arithmetic, MUST NOT perform currency
conversion, and MUST NOT borrow unused runtime allowance for application cost
or vice versa. When both partitions are present, their sum is a displayable
maximum, not a shared counter.

The legacy flat members `constraints.max_actions` and
`constraints.max_cost_usd` are not aliases and are invalid in this profile.
Separating the two cost partitions is required because no single component
authoritatively observes both runtime inference/tool spend and application-side
charges. A deployment needing a shared distributed spend ledger requires a
future authenticated accounting profile.

The issuer chooses and hashes the limits, but mutable accounting belongs to the
component that authoritatively observes each dimension:

| Budget id | Authority | Unit and charge boundary |
| --- | --- | --- |
| `write_actions` | application | One accepted logical invocation in mode `reserve`, `commit`, `compensate`, or `revert`; reservation acquisition and renewal count, explicit release does not. |
| `tool_calls` | controlling runtime | One distinct dispatch to a runtime-mediated tool or ASP action endpoint; transport attempts for the same dispatch do not add charges. |
| `model_tokens` | controlling runtime | Provider-reported input plus output tokens for one model invocation, without double-counting cached or reasoning subsets. |
| `runtime_seconds` | controlling runtime | Aggregate monotonic active-work seconds across sessions under the grant. |
| `parallel_sessions` | application | Current number of authoritative sessions in `active`; this is occupancy, not cumulative consumption. |
| `runtime_cost` | controlling runtime | Provider or tool cost charged to the runtime partition, in declared microunits. |
| `application_cost` | application | Application-side price charged to the application partition, in declared microunits. |

Agent-supplied counters, token estimates, timestamps, prices, and remaining
values are never authoritative. A component MUST reject a grant when it cannot
durably meter a dimension assigned to that component in the table above. It
MUST preserve, display, and pass through limits assigned to the other authority
without inventing mutable state for them. The application MUST NOT claim runtime
token, tool, time, or runtime-cost enforcement merely because it can see Action
Requests. The runtime MUST NOT claim application write, application-cost, or
session-occupancy enforcement from local process state.

`max_write_actions` is charged exactly once when the application atomically
admits a new logical invocation after authorization, tuple, normalization,
idempotency, approval, and precondition checks. A denial before admission is
free. Once admitted, a later success, failure, partial effect, or unknown effect
does not refund the charge. An explicit reservation-release action is
idempotent safety cleanup and remains permitted while the grant is active even
when the write budget is exhausted; revocation or expiry invalidates the
reservation independently.

`max_tool_calls` counts when the runtime commits to one distinct agent-work
dispatch after local policy admits it, immediately before finalizing any parent
runtime receipt and sending the first transport attempt. This includes a read,
dry run, proposal, state-changing ASP request, or non-ASP tool call. The closed
list of mandatory safety and cleanup operations below uses a separate
control-plane dispatch path and is not `tool_calls`; those operations still
require their ordinary authorization, binding, and idempotency checks and MUST
NOT carry an unrelated agent-work effect. A local denial before the charge
boundary is free; a crash, downstream denial, or failure afterward still
counts. A transport retransmission preserving the same logical dispatch and
idempotency context is not another tool call.

For `max_model_tokens`, the runtime MUST reserve known input tokens plus the
configured maximum output before starting a model call and settle against the
provider's authoritative final usage. Cached-input, reasoning, or other detail
is a subset unless the provider explicitly reports it outside input and output
totals. When final usage is absent or uncertain, the runtime retains its
conservative reservation or stops new work; it MUST NOT assume zero.

For either cost partition, the accounting authority MUST reserve a conservative
upper-bound charge before its admission or dispatch boundary and settle the
integer microunit amount from authoritative billing or declared application
pricing. If no safe upper bound exists, the operation is rejected before that
boundary. Missing or disputed final billing retains the reservation; it is not
rounded down or transferred to the other partition.

`max_runtime_seconds` uses a monotonic clock. Within one session generation the
runtime unions overlapping intervals in which the agent, model, or tool is
actively working, including an outstanding dispatched operation, then sums
those per-session intervals across concurrent sessions. Explicit user or policy
waits and application-authoritative `interrupted` or terminal session time do
not accrue. Each session contribution is the ceiling of its cumulative unioned
duration in seconds, so splitting one interval cannot reduce usage and parallel
sessions remain additive. Clock rollback, restart, or missing duration state
fails closed and does not reset usage.

An `active` application session occupies one `max_parallel_sessions` slot.
Start and resume atomically acquire a slot across the grant and every ancestor;
an exact replay does not acquire another. Transition to `interrupted` releases
the slot only after the application fences new actions, and terminal states
release it permanently. Saturation rejects a new start or resume as
`limit_exceeded` without identifying the occupying sessions; it MUST NOT pause
or cancel a session that already owns a slot.

An accounting authority represents one counter with this canonical Budget
Counter State projection:

```json
{
  "budget_id": "write_actions",
  "authority": "application",
  "scope": "grant",
  "mode": "consumptive",
  "unit": "actions",
  "limit": 20,
  "used": 7,
  "reserved": 1,
  "remaining": 12,
  "state": "available",
  "revision": 18
}
```

`scope` is `grant` in this profile. `mode` is `consumptive` except for
`parallel_sessions`, which is `occupancy`. `unit` is respectively `actions`,
`calls`, `tokens`, `seconds`, `sessions`, or `currency_microunits`; a cost state
also carries the declared `currency`. `used`, `reserved`, `remaining`, and
`revision` are safe non-negative integers, `revision` strictly increases on
every authoritative state change, and `remaining` MUST equal
`max(0, limit - used - reserved)`. For a consumptive counter, `used` is settled
monotonic consumption. For occupancy, `used` is the current active-slot count
and decreases only after the authoritative session fence releases a slot.
`reserved` is a durable in-flight admission amount; successful settlement moves
the applicable amount to `used`, and an authoritative rejection releases it.
A consumptive counter MAY include `warning_at_remaining`, a positive safe
integer smaller than `limit` that the authority fixes for the counter's ledger
lifetime. When it is absent, consumptive state MUST be `available` exactly when
`remaining` is positive. When present, state MUST be `available` when
`remaining` is greater than the threshold and `warning` when it is positive and
no greater than the threshold. Consumptive state MUST be `exhausted` exactly
when `remaining` is zero. An occupancy counter does not carry a warning
threshold and MUST be `available` exactly when `remaining` is positive and
`saturated` exactly when it is zero. The warning threshold and mutable state are
not part of `grant_hash` and MUST NOT be copied from an untrusted caller.

Before new consumption, the authority MUST calculate a conservative maximum
increment and atomically verify and reserve it against the local grant and
every ancestor ledger. It then dispatches or linearizes the operation, settles
authoritative actual usage no greater than that reservation, and releases only
unused reservation. Exactly one of two races for the last unit can succeed.
A proven insufficient remainder returns `limit_exceeded` without changing the
counter. Arithmetic overflow, missing ledger state, or inability to calculate a
bounded reservation returns `budget_state_unavailable` without advancing
`used` or `revision`. If an external authoritative meter later reports usage
greater than the reserved upper bound, the component MUST retain the
reservation, stop matching new work, and report `budget_state_unavailable`; the
already authoritative operation outcome is not rewritten, but usage beyond the
hard limit is never treated as permitted budget consumption.

The ledger is keyed by the grant and lineage, persists for their audit lifetime,
and survives credential rotation, process restart, session interruption,
resume, and generation change. Attenuation, renewal, token exchange,
supersession that preserves authority, and child derivation remain in the same
cumulative lineage: their used, reserved, and occupied state is retained and
cannot be reset by changing a grant or credential identifier. Only a fresh
independent root grant following distinct authorization and consent can begin a
new ledger. An exact completed idempotent retry returns the original result and
receipts without a new reservation or charge, even after a budget is exhausted,
subject to current authorization and disclosure policy. An unknown outcome
retains its original charge or reservation until reconciled. Changing the
idempotency key MUST NOT create a refund or escape accounting.

The absence of another budget charge does not exempt that attempt from runtime
transport, repetition, causal-depth, or cycle guards. Conversely, a runaway
guard transition and its `session.pause` safety request do not consume or mutate
a Budget Counter State; guard and budget records remain separate authorities.

Every child charge is applied to the child and all ancestors. A child grant
bound to the same controlling runtime shares its ancestors' runtime ledgers. A
child bound to another runtime MUST NOT be issued while any runtime-authoritative
budget is present unless a future authenticated shared-accounting or explicit
allocation profile is selected; otherwise subdelegation would multiply tool,
token, time, and runtime-cost allowances. Ungranted models, tools, adapters, and
secondary runtimes remain mediated and charged by the controlling runtime.
Every `cost.currency` present in one budget lineage MUST exactly equal the
currency of every ancestor cost budget. Mixed-currency derivation MUST be
rejected rather than converted or treated as an independent allowance.

Exhaustion MUST NOT block grant revocation, `session.pause`, session
cancellation, authenticated `budget.query`, introspection, receipt retrieval,
explicit reservation release, authoritative reconciliation, or an exact
idempotent replay. Settled hard
consumptive exhaustion, where `used` equals `limit` and `reserved` is zero, is
not retryable under the same grant. Temporary admission exhaustion MAY recover
only after an authoritative reservation release. Occupancy saturation MAY
recover after an authoritative slot or occupancy reservation release only when
its limit is positive; a zero-slot limit is non-retryable under that grant. A
retry hint is advisory and never reserves that future capacity. These
operations are the closed set of mandatory safety and cleanup operations in
this profile. They do not consume a grant budget; an implementation bears their
control-plane cost separately and MUST NOT route them through an exhausted
agent-work counter.

## Grant Lifecycle

```text
discover surface
  -> verify manifest
  -> choose agent
  -> verify Agent Passport
  -> derive local consent preview and optional impact simulation
  -> confirm the canonical local consent preview
  -> request grant through the selected issuance model
  -> grant-issuer consent
  -> issue or exchange Grant Credential
  -> store grant in runtime
  -> start session
  -> introspect / verify and mediate actions
  -> issue receipts
  -> expire / revoke / notify / renew
```
