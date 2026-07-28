## Grant Issuance Models

### Model A: App-Issued Grant

The application issues a grant after user consent.

```text
Runtime redirects user to app OAuth / consent
App issues agent grant
Runtime stores grant
Runtime calls app with grant credential
App verifies every call
```

This is the RECOMMENDED MVP model because it fits existing OAuth/resource-server
deployments.

Because this draft does not require browser-to-localhost communication, the
consent flow SHOULD support a completion mode that does not depend on a
loopback redirect — for example an OAuth device-authorization-style exchange
or an app-mediated pairing code that the runtime polls or receives over its
outbound channel.

Pros:

- Easy for applications to enforce.
- Works with existing consent and scope infrastructure.
- Does not require a new global trust authority.

Cons:

- The app learns runtime and agent metadata.
- Each app needs to implement agent grant issuance.

### Model B: Runtime-Held Grant Plus App Token

The app issues a scoped token to the runtime. The runtime locally binds that
token to an agent, passport, and policy. To satisfy the Action Executor
Profile, the application MUST also establish the runtime, agent,
and passport binding from app-verifiable state or a verified proof at action
time. A runtime-only assertion of that binding is insufficient.

Pros:

- Simpler for early app integrations.
- Can work with existing OAuth tokens.

Cons:

- The app can fail to know which agent actually acted.
- Weaker app-side audit unless receipts include runtime-attested metadata.

### Model C: Signed Delegation Object

The grant is a signed object with caveats. It MAY be signed by the app, user,
runtime, enterprise authority, or some combination.

Pros:

- Portable and cryptographically strong.
- Can support offline verification and third-party audit.

Cons:

- Requires a signed-grant profile, trust stores, signer-key lifecycle,
  revocation semantics, and stronger interop work beyond the receipt profile.
- Too large for the first MVP.

## OAuth Grant Lifecycle Profile

This profile maps an Agent Grant onto OAuth Rich Authorization Requests, Token
Exchange, Token Introspection, and Token Revocation. It applies when the Agent
Surface Manifest declares OAuth endpoints and the Agent Grant authorization
details type defined by this draft.

The authorization server and resource server MAY be operated by the same
application, but they retain their OAuth roles. The authorization server issues
and manages Grant Credentials. The credential-protected `agent_api` endpoints
form one logical resource server under `credential_audience`; the action
endpoint additionally enforces the semantic Agent Grant for every action, while
budget and session endpoints expose only their closed safety operations.

### Rich Authorization Request Profile

An Agent Grant authorization request MUST use the RFC 9396
`authorization_details` parameter encoded as a JSON array containing exactly
one object whose `type` is:

```text
https://github.com/0al-spec/agent-surface/authorization-details/agent-grant
```

The authorization server metadata MUST list this value in
`authorization_details_types_supported`. The Agent Surface Manifest `auth`
object MUST mirror that value and the standard `grant_types_supported` values
used by the deployment; conflicting metadata makes the OAuth profile invalid.

Example, shown decoded from its form-encoded authorization request parameter:

```json
[
  {
    "type": "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant",
    "locations": ["https://code.example.com/agent-actions"],
    "actions": ["pull_request.get", "comment.create"],
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
    "scopes": ["pull_request.read", "pull_request.comment"],
    "constraints": {
      "repositories": ["example-org/example-repo"],
      "pull_requests": [13],
      "expires_at": "2026-06-25T20:00:00Z",
      "purpose_binding": {
        "profile": "https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1",
        "purpose": {"id": "pur_01J2Q7M4K8X5", "revision": "rev_3"},
        "task": {"id": "tsk_01J2Q7N9C3V6", "revision": "rev_7"}
      },
      "write_approval": "required",
      "budgets": {
        "max_write_actions": 20
      }
    },
    "credential_profile": "proof_bound",
    "audit": {
      "local_receipt": "required",
      "app_receipt": "required"
    }
  }
]
```

The Agent Grant authorization details type has the following contract. Except
for the required RFC 9396 `type` discriminator, its field names and semantics
are the authoritative Grant Object wire shape defined above:

- `type`, `delegate`, `resource_server`, `scopes`, `constraints`,
  `credential_profile`, and `audit` are REQUIRED.
- `delegate` MUST contain `runtime`, `agent`, and the complete
  `identity_evidence` envelope; it MAY contain the request-only
  `runtime_identity_profile` selector. It MUST NOT contain the server-derived
  `runtime_identity` projection in a request. A legacy request MAY instead
  contain the complete Passport tuple only under the explicit migration rules;
  mixed or partial representations are invalid. When
  Runtime Attestation is selected, it MUST contain the request-only closed
  `runtime_attestation_requirement` object and a runtime-identity selector; it
  MUST NOT contain `runtime_attestation`, assurance output, appraisal state,
  hashes, raw Evidence, or raw Attestation Results.
- `resource_server` MUST contain `app_id`, `issuer`, `surface_version`, and the
  verified `surface_hash`. When the selected manifest is an Authorized Surface
  Projection, it MUST also contain that profile's exact request-visible
  `authorized_projection` binding; the authorization server verifies and
  preserves it in the authoritative Grant.
- `constraints` MUST contain `expires_at`; other fields use the semantics of the
  Agent Grant object. When Remote Processing Privacy is selected, it MUST also
  contain the closed request-only `remote_processing` object with exact
  `profile` and `path`, the request MUST select Runtime Identity, and the client
  MUST NOT supply `classification_ceiling`. When Agent Training Use Policy is
  selected, `constraints` MUST also contain its closed `training_use` object
  with the exact profile and canonical `permitted_classes` request set. When
  Purpose- and Task-Bound Agent Grant is selected, it MUST contain the exact
  closed `purpose_binding` object with the advertised profile, required purpose
  reference, and optional task reference; the client MUST NOT supply lifecycle
  state, a label, or another semantic projection.
- `credential_profile` MUST be `compatibility_bearer` or `proof_bound` and maps
  to the credential profiles defined in this draft.
- A request for action authority MUST contain non-empty RFC 9396 common
  `locations` and `actions` arrays of published action endpoints and Agent
  Surface action identifiers; omission requests no action authority. The
  granted values are authoritative allow-lists and every
  invoked action MUST be a member. The authorization applies to the product of
  the granted actions, locations, scopes, and resource filters; every allowed
  combination MUST be published by the surface and semantically compatible.
- `grant_id`, `grant_hash`, `subject`, `credential_binding`, `data_exposure`,
  `delegate.runtime_identity`, `delegate.runtime_attestation`, and
  `constraints.remote_processing.classification_ceiling` MUST NOT be supplied
  by the client in an authorization request; they are authorization-server
  output.
- A client selecting Approval Receipt MUST supply the exact closed
  `audit.approval_receipt` profile and requirement projection for its requested
  actions. The authorization server independently validates those roles and
  maximum ages against the pinned manifest and its own acceptance policy.
- A client MAY request an `audit.receipt_signing` profile and signer roles, but
  it MUST NOT supply authoritative `signer_keys`. Before issuance, the
  authorization server MUST reject a request containing those entries, derive
  them from issuer metadata and the authenticated runtime key registration,
  and include the resulting pins in `grant_hash`.
- The request MUST NOT supply `subject.user` or another asserted user identity;
  the authorization server derives the subject from its authenticated user
  session or, at the token endpoint, from the validated `subject_token`.

The authorization server MUST reject unknown fields, unknown action or scope
values, a mismatched `resource_server.app_id` or
`resource_server.surface_version`, a mismatched `resource_server.surface_hash`,
an identity-evidence envelope that is unadvertised, unsupported, stale, mixed
with legacy fields, or not independently verified, an unadvertised or unsatisfied runtime identity profile, a
client-supplied runtime identity projection, an unadvertised, unsupported, or
non-accepted Runtime Attestation requirement, client-supplied attestation
output, an unadvertised Remote Processing Privacy profile, a client-supplied
ceiling, a path inconsistent with the controlling Runtime Identity, an
effective exposure above the deterministic ceiling, an unadvertised or
malformed Agent Training Use Policy, an unknown, duplicate, non-canonical, or
unexposed requested training class, an unadvertised or malformed Approval
Receipt profile, an unadvertised or malformed Purpose Binding profile, an
unknown or inactive purpose or task, a wrong revision or parent relationship,
an incomplete or incompatible approval requirement projection,
an action set that is not closed over required companion dependencies, or
constraints that are invalid for the published surface. It MUST use the RFC 9396
`invalid_authorization_details` error for malformed or unsupported Agent Grant
authorization details.

Authorization Code use of this profile MUST use PKCE with the `S256` challenge
method. Deployments SHOULD use Pushed Authorization Requests when supported so
the rich grant request is integrity-protected and is not exposed in browser
URLs, history, or intermediary logs.

The OAuth `scope` request parameter MUST NOT be used in an authorization or
token-exchange request that carries this Agent Grant `authorization_details`
type. The authorization server MUST reject such a request with `invalid_request`.
Independent OAuth authorization therefore requires a separate request and
credential; this profile never silently drops or unions independent scopes.

In token and introspection responses, the standard OAuth `scope` member MAY be
an exact space-delimited projection of the granted Agent Grant `scopes` for
legacy resource-server integration. If present, it MUST contain exactly that
projection; the granted `authorization_details` remains authoritative. A
resource server MUST reject a credential when the two representations conflict.

The authorization server's consent view MUST satisfy the Consent Preview
Contract's material-semantics and untrusted-label requirements using its own
verified copy of the request and pinned manifest. When a Runtime Identity
Profile is selected, that view MUST include the complete sanitized projection
the server derived from the authenticated runtime record; raw identity evidence
remains hidden. When the Minimal Agent Passport Grant-Issuance Profile is
selected, the view MUST include the server's independently verified Passport
identity, tuple, expiry, status freshness, relevant capability names, and
verification boundary without exposing the raw artifact. When Runtime
Attestation is selected, the view MUST additionally show its concrete profile,
opaque verifier id, maximum age, proof-key binding, claimed Target Environment
coverage, server-derived assurance, and current accepted state without exposing
Evidence, measurements, reference values, or Verifier diagnostics. When Remote
Processing Privacy is selected, the view MUST additionally show the exact path,
deterministic ceiling, and complete exposure closure while distinguishing the
runtime commitment from application-verified Runtime Identity evidence. When
Agent Training Use Policy is selected, the view MUST show the requested and
effective permitted classes by source, every prohibited class, and the durable-
influence warning independently of plaintext retention. When Purpose- and
Task-Bound Agent Grant is selected, the view MUST show the exact purpose and
optional task ids and revisions, their current relationship and state,
purpose-only or task-bound mode, and effective expiration without treating a
safe label as authority. The user MAY
approve a strict subset. The authorization server
MUST present each required companion closure as one approval group. It MUST
materialize the exact approved action stages in the returned `actions`
allow-list, reject a selection that breaks required closure, compare the
requested and approved objects according to Agent Grant semantics rather than
using raw JSON equality, and MUST NOT enrich the result with additional
authority.

The token response MUST return the granted `authorization_details` as required
by RFC 9396. For this type, the returned object MUST be enriched with the
authoritative `grant_id`, `subject`, delegate binding, effective constraints,
`credential_binding`, effective `data_exposure`, and `grant_hash` assigned by
the authorization server. The authorization server and resource server MUST
retain or receive the same
granted object for later action verification and introspection.
When the request selected a Runtime Identity Profile, the returned object MUST
remove the request-only selector and contain the exact server-derived
`delegate.runtime_identity` and repeated credential-binding values.
When the request selected Runtime Attestation, the returned object MUST remove
`runtime_attestation_requirement`, contain the exact stable
`delegate.runtime_attestation` object, and repeat its binding, profile,
verifier, and proof-key values in `credential_binding`. The current accepted
appraisal remains authoritative mutable state outside that returned object.
When the request selected Remote Processing Privacy, the returned constraints
MUST preserve its exact requested profile and path and add the deterministic
`classification_ceiling`; the authorization server MUST NOT change the path or
omit the complete constraint.
When the request selected Agent Training Use Policy, the returned constraints
MUST preserve its exact profile and a canonical `permitted_classes` subset of
the request and returned exposure union; the authorization server MUST NOT add
a class or omit an explicit empty result.
When the request selected Purpose- and Task-Bound Agent Grant, the returned
constraints MUST preserve the exact profile, purpose id and revision, and
optional task id and revision. The authorization server MUST NOT substitute a
sibling, update a revision, remove the task, or extend expiration beyond the
current record lifetime.
When the request selected the Pluggable Agent Identity Evidence Profile, the
returned delegate and credential binding MUST preserve the complete exact
envelope. A legacy Passport request follows only the explicit migration rules.

### OAuth Token Exchange Profile

A runtime MAY exchange a user-authorized subject token for an Agent Grant
Credential using RFC 8693. The request uses the standard token endpoint and
form-encoded parameters:

```http
POST /oauth/token HTTP/1.1
Host: code.example.com
Content-Type: application/x-www-form-urlencoded
DPoP: <proof-jwt>

grant_type=urn:ietf:params:oauth:grant-type:token-exchange
&resource=https%3A%2F%2Fcode.example.com%2Fagent-api
&requested_token_type=urn:ietf:params:oauth:token-type:access_token
&subject_token=<user-authorized-token>
&subject_token_type=urn:ietf:params:oauth:token-type:access_token
&authorization_details=<percent-encoded-agent-grant-details>
```

The Token Exchange request has these additional ASP requirements:

- The runtime MUST authenticate to the token endpoint. For a
  `proof_bound` request, it MUST authenticate using the key or channel binding
  that will identify the bound runtime.
- A DPoP-bound exchange MUST include a `DPoP` HTTP header containing a proof for
  the token request, as required by RFC 9449. The authorization server MUST
  validate that proof independently of OAuth client authentication and derive
  the issued token's `cnf.jkt` and Agent Grant `credential_binding.jkt` from the
  proof key. An mTLS-bound exchange instead derives `cnf["x5t#S256"]` and the
  corresponding credential binding from the client certificate presented on
  the token request; it does not use the example's DPoP header.
- `subject_token` MUST represent the authenticated user's authorization for the
  requested application and MUST be valid at the time of exchange.
- `resource` MUST contain exactly the pinned manifest
  `agent_api.credential_audience`. An `audience` value MAY additionally name
  that same logical protected resource but MUST NOT add another target. Action
  `locations` remain a separate RAR allow-list and MUST NOT replace or widen
  the credential audience.
- `requested_token_type` MUST be
  `urn:ietf:params:oauth:token-type:access_token` for the OAuth Grant Credential
  profile in this draft.
- `authorization_details` MUST contain exactly one Agent Grant object of the
  type defined above and MUST be semantically equal to or narrower than the
  authorization approved by the user.
- If OAuth client authentication does not establish the runtime identity, the
  request MUST include an `actor_token` representing the runtime and the
  corresponding `actor_token_type`. The authorization server MUST verify it and
  bind the output credential to that runtime. For a `proof_bound` request, the
  actor token MUST itself be sender-constrained or presented through the same
  bound channel authentication.

The authorization server MUST validate the subject token, runtime identity,
exact current accepted Runtime Attestation record when selected, agent and exact
current identity-evidence envelope, resource, requested action and location allow-lists,
scopes, constraints, and credential profile. Returned `actions` and `locations`
MUST be subsets of the source authorization. The exchange MUST NOT add a
stronger companion stage under a shared scope, increase authority, widen
resources, relax approval or receipt requirements, extend beyond the approved
expiration, or replace `proof_bound` with `compatibility_bearer` without fresh
user consent. Any attenuated action subset MUST remain closed over its required
companion dependencies; otherwise the exchange MUST reject it rather than add
missing stages.

When the source Grant selected Remote Processing Privacy, token exchange MUST
preserve its exact profile and path, recompute the same deterministic ceiling,
and verify the attenuated source closure against it. A different path is not an
OAuth attenuation and requires a new semantic Grant request and fresh consent.
The exchange MUST NOT omit the constraint or treat a lower apparent Runtime
Identity locality as proof that the downstream path changed safely.

When the source Grant selected Agent Training Use Policy, token exchange MUST
retain the profile and return a `permitted_classes` set no wider than the source
set intersected with the exchanged Grant's effective exposure classes. It MUST
retain an explicit empty result. When the source omitted the profile, exchange
MAY add the empty form as a new restriction only if the source selected Remote
Processing Privacy and the exchange retains its exact profile and path. In
every other case, adding this profile or a non-empty training permission
requires a fresh independent authorization and consent flow.

When the source Grant selected Purpose- and Task-Bound Agent Grant, token
exchange MUST preserve or narrow the binding only through that profile's
portable partial order. It MUST resolve current issuer-owned state and
relationship, retain exact revisions, and cap expiration by the source and
record lifetimes. Removing a binding, selecting a sibling, replacing a
revision, or widening from task-bound to purpose-only requires a fresh
independent authorization and consent flow. When the source omitted the
profile, adding one verified purpose or task binding is a restriction only if
all ordinary authority remains a subset and derivation linkage is retained.

When the source Grant selected Approval Receipt, token exchange MUST retain the
exact profile, project requirements to the exchanged action subset, preserve
fixed-role modes, and only narrow a `user_or_app` accepted-role set or lower a
maximum age. It MUST NOT reuse any source Approval Receipt: the exchanged
Grant's new `grant_hash`, and potentially its session and runtime tuple, require
fresh approval evidence.

RFC 8693 does not itself create lifecycle linkage between input and output
tokens. This ASP profile does: the authorization server MUST record the source
authorization or parent grant from which the Agent Grant was derived. Revoking
or invalidating that source authority MUST revoke or suspend every derived Agent
Grant unless an independently approved grant replaced it.

Issuance also MUST preserve cumulative caveats across that derivation graph.
Every application-authoritative charge or occupied session slot MUST apply to
the derived grant and every ancestor application ledger; every
runtime-authoritative charge MUST do the same in the controlling runtime's
lineage ledger. The authorization server MUST preserve the complete lineage and
MUST reject a cross-runtime child that cannot share or allocate the required
runtime accounting. Repeating an exchange therefore cannot multiply write,
tool, token, time, session, or partitioned cost budgets. The authorization
server MUST treat semantically equivalent exchanges with the
same source authorization, client and delegate tuple, target resource,
normalized Agent Grant details, and proof-binding key as idempotent: it MUST
reuse the same `grant_id`, `grant_hash`, and accounting state, although it MAY
rotate the access-token representation.

Example successful response:

```json
{
  "access_token": "<opaque-grant-credential>",
  "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
  "token_type": "DPoP",
  "expires_in": 1800,
  "scope": "pull_request.read pull_request.comment",
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "authorization_details": [
    {
      "type": "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant",
      "locations": ["https://code.example.com/agent-actions"],
      "actions": ["pull_request.get", "comment.create"],
      "subject": {
        "user": "app-user-7f3a"
      },
      "delegate": {
        "runtime": "application_runtime_456",
        "agent": "local_agent_789",
        "identity_evidence": {
          "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1",
          "format_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
          "artifact_digest": {"profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1", "value": "sha-256:<base64url-digest>"},
          "issuer": "https://issuer.example/agents",
          "subject": "agent-subject-opaque-7f3a",
          "verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
          "key_binding": {"profile": "https://example.com/profiles/issuer-key-thumbprint/v1", "value": "sha-256:<base64url-digest>"},
          "lifecycle": {"freshness_profile": "https://example.com/profiles/status-max-age/2026-01", "status_profile": "https://example.com/profiles/agent-passport-status/2026-01", "status_ref": "app-status-subject-4c18"}
        }
      },
      "resource_server": {
        "app_id": "code.example.com",
        "issuer": "https://code.example.com",
        "surface_version": "2026-06-25",
        "surface_hash": "sha-256:<base64url-digest>"
      },
      "scopes": ["pull_request.read", "pull_request.comment"],
      "constraints": {
        "repositories": ["example-org/example-repo"],
        "pull_requests": [13],
        "expires_at": "2026-06-25T20:00:00Z",
        "purpose_binding": {
          "profile": "https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1",
          "purpose": {"id": "pur_01J2Q7M4K8X5", "revision": "rev_3"},
          "task": {"id": "tsk_01J2Q7N9C3V6", "revision": "rev_7"}
        },
        "write_approval": "required",
        "budgets": {
          "max_write_actions": 20
        }
      },
      "credential_profile": "proof_bound",
      "credential_binding": {
        "method": "dpop",
        "runtime_id": "application_runtime_456",
        "agent_id": "local_agent_789",
        "identity_evidence": {
          "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1",
          "format_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
          "artifact_digest": {"profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1", "value": "sha-256:<base64url-digest>"},
          "issuer": "https://issuer.example/agents",
          "subject": "agent-subject-opaque-7f3a",
          "verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
          "key_binding": {"profile": "https://example.com/profiles/issuer-key-thumbprint/v1", "value": "sha-256:<base64url-digest>"},
          "lifecycle": {"freshness_profile": "https://example.com/profiles/status-max-age/2026-01", "status_profile": "https://example.com/profiles/agent-passport-status/2026-01", "status_ref": "app-status-subject-4c18"}
        },
        "jkt": "<base64url-thumbprint>"
      },
      "audit": {
        "local_receipt": "required",
        "app_receipt": "required"
      },
      "grant_id": "grant_123",
      "grant_hash": "sha-256:<base64url-digest>"
    }
  ]
}
```

The response MUST include `access_token`, `issued_token_type`, `token_type`,
`expires_in`, `grant_id`, `grant_hash`, the exact `scope` projection defined
above, and the granted `authorization_details`. This also satisfies the RFC
8693 requirement to return `scope` when the issued scope differs from the
request. The `token_type` and method-specific credential confirmation data MUST
match the selected
credential profile and the binding established at the token endpoint. A
refresh token SHOULD NOT be issued by default; if one is issued, it MUST
preserve the tuple binding, attenuation, and revocation linkage of the Agent
Grant and follow RFC 9700 refresh-token replay protections.

Top-level `grant_id` and `grant_hash` MUST exactly match the same members in the
sole returned Agent Grant authorization-details object. The client MUST reject
the token response if either projection is absent or mismatched; it MUST NOT
select one representation and ignore the other.

Token responses containing a Grant Credential or its authorization details MUST
use `Cache-Control: no-store` and `Pragma: no-cache`.

### Grant Introspection Profile

The manifest `agent_api.grant_introspection_url` MAY identify the same RFC 7662
endpoint as `auth.introspection_url`. A protected resource or runtime
introspects a Grant Credential using an authenticated RFC 7662 request with the
required `token` parameter and optional `token_type_hint`. The endpoint MUST
authenticate and authorize the caller and disclose only grant data that caller
needs.

For an inactive, unknown, or undisclosable credential, the response MUST be:

```json
{
  "active": false
}
```

It MUST NOT reveal whether the credential was unknown, expired, revoked, or
outside the caller's authority.

A credential bound to a Runtime Identity Profile is inactive whenever the
authorization server cannot prove that the exact runtime binding and claims
revision remain active. Temporary evidence unavailability, suspension, and
revocation all use the same `{"active":false}` response and do not disclose
which identity check failed.

A credential bound to the Pluggable Agent Identity Evidence Profile is likewise
inactive whenever the exact artifact, issuer/subject projection, verification,
key or agent binding, expiry, lifecycle state, or status freshness cannot be
established. The inactive response MUST NOT reveal the concrete format or which
identity check failed. A legacy Passport Grant follows the equivalent pinned
legacy checks.

A credential bound to Runtime Attestation is inactive whenever the exact
attestation binding is not in current `accepted` state or its freshness,
Verifier, proof key, runtime-identity revision, appraisal policy, or reference
values cannot be established. The inactive response MUST NOT distinguish
rejection, indeterminate appraisal, staleness, revocation, or supersession.

A credential bound to Purpose- and Task-Bound Agent Grant is inactive whenever
the authorization server cannot establish the exact scoped purpose and optional
task revisions, their current active state, or their relationship. The
`{"active":false}` response MUST NOT distinguish an unknown record, wrong
subject, suspension, terminal closure, relationship change, or temporary state
unavailability. A resource server that cannot obtain current authoritative
state MUST fail closed rather than preserving a prior positive introspection
result.

For an active Grant Credential, the response MUST include the RFC 7662 fields
`active`, `client_id`, `scope`, `token_type`, `exp`, `iat`, `sub`, `aud`, and
`iss`, plus the ASP fields `grant_id`, `grant_hash`, `resource_server`, `delegate`,
`constraints`, `credential_binding`, and `authorization_details`. An active
proof-bound credential MUST additionally include the method-specific standard
`cnf` confirmation member. The `sub` value SHOULD be a stable app-scoped
pseudonymous user identifier. `client_id` identifies the OAuth client;
`delegate.runtime` is the authoritative ASP runtime binding and MAY differ from
`client_id`. `aud` MUST equal the `agent_api.credential_audience` in the
manifest snapshot selected by the returned Grant's `surface_hash`.

The `authorization_details` member MUST contain the granted Agent Grant object,
filtered only to data the authenticated caller may receive. Top-level `sub`,
`grant_id`, `grant_hash`, `resource_server`, `delegate`, `constraints`, and
`credential_binding` are projections of that object and MUST match it; `sub`
corresponds to `subject.user`. A resource server MUST treat a mismatch as an
invalid grant proof rather than selecting one representation. A filtered
response still MUST carry `grant_hash` as an opaque authoritative commitment,
but a caller MUST NOT claim to have recomputed it without the complete Grant
Object.

For DPoP, `cnf` MUST contain `jkt` as specified by RFC 9449; for mTLS, it MUST
contain `x5t#S256` as specified by RFC 8705. The confirmation value MUST match
the method-specific value in the Agent Grant `credential_binding`. The resource
server MUST reject a missing or mismatched confirmation member. A Compatibility
Bearer Credential MUST NOT fabricate a `cnf` member.

```json
{
  "active": true,
  "client_id": "application_runtime_456",
  "scope": "pull_request.read pull_request.comment",
  "token_type": "DPoP",
  "exp": 1782417600,
  "iat": 1782415800,
  "sub": "app-user-7f3a",
  "aud": "https://code.example.com/agent-api",
  "iss": "https://code.example.com",
  "cnf": {
    "jkt": "<base64url-thumbprint>"
  },
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "resource_server": {
    "app_id": "code.example.com",
    "issuer": "https://code.example.com",
    "surface_version": "2026-06-25",
    "surface_hash": "sha-256:<base64url-digest>"
  },
  "delegate": {
    "runtime": "application_runtime_456",
    "agent": "local_agent_789",
    "identity_evidence": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1",
      "format_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
      "artifact_digest": {"profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1", "value": "sha-256:<base64url-digest>"},
      "issuer": "https://issuer.example/agents",
      "subject": "agent-subject-opaque-7f3a",
      "verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
      "key_binding": {"profile": "https://example.com/profiles/issuer-key-thumbprint/v1", "value": "sha-256:<base64url-digest>"},
      "lifecycle": {"freshness_profile": "https://example.com/profiles/status-max-age/2026-01", "status_profile": "https://example.com/profiles/agent-passport-status/2026-01", "status_ref": "app-status-subject-4c18"}
    }
  },
  "constraints": {
    "repositories": ["example-org/example-repo"],
    "pull_requests": [13],
    "expires_at": "2026-06-25T20:00:00Z",
    "purpose_binding": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1",
      "purpose": {"id": "pur_01J2Q7M4K8X5", "revision": "rev_3"},
      "task": {"id": "tsk_01J2Q7N9C3V6", "revision": "rev_7"}
    },
    "write_approval": "required",
    "budgets": {
      "max_write_actions": 20
    }
  },
  "credential_binding": {
    "method": "dpop",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "identity_evidence": {
      "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1",
      "format_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
      "artifact_digest": {"profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1", "value": "sha-256:<base64url-digest>"},
      "issuer": "https://issuer.example/agents",
      "subject": "agent-subject-opaque-7f3a",
      "verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
      "key_binding": {"profile": "https://example.com/profiles/issuer-key-thumbprint/v1", "value": "sha-256:<base64url-digest>"},
      "lifecycle": {"freshness_profile": "https://example.com/profiles/status-max-age/2026-01", "status_profile": "https://example.com/profiles/agent-passport-status/2026-01", "status_ref": "app-status-subject-4c18"}
    },
    "jkt": "<base64url-thumbprint>"
  },
  "authorization_details": [
    {
      "type": "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant",
      "locations": ["https://code.example.com/agent-actions"],
      "actions": ["pull_request.get", "comment.create"],
      "subject": {
        "user": "app-user-7f3a"
      },
      "delegate": {
        "runtime": "application_runtime_456",
        "agent": "local_agent_789",
        "identity_evidence": {
          "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1",
          "format_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
          "artifact_digest": {"profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1", "value": "sha-256:<base64url-digest>"},
          "issuer": "https://issuer.example/agents",
          "subject": "agent-subject-opaque-7f3a",
          "verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
          "key_binding": {"profile": "https://example.com/profiles/issuer-key-thumbprint/v1", "value": "sha-256:<base64url-digest>"},
          "lifecycle": {"freshness_profile": "https://example.com/profiles/status-max-age/2026-01", "status_profile": "https://example.com/profiles/agent-passport-status/2026-01", "status_ref": "app-status-subject-4c18"}
        }
      },
      "resource_server": {
        "app_id": "code.example.com",
        "issuer": "https://code.example.com",
        "surface_version": "2026-06-25",
        "surface_hash": "sha-256:<base64url-digest>"
      },
      "scopes": ["pull_request.read", "pull_request.comment"],
      "constraints": {
        "repositories": ["example-org/example-repo"],
        "pull_requests": [13],
        "expires_at": "2026-06-25T20:00:00Z",
        "purpose_binding": {
          "profile": "https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1",
          "purpose": {"id": "pur_01J2Q7M4K8X5", "revision": "rev_3"},
          "task": {"id": "tsk_01J2Q7N9C3V6", "revision": "rev_7"}
        },
        "write_approval": "required",
        "budgets": {
          "max_write_actions": 20
        }
      },
      "credential_profile": "proof_bound",
      "credential_binding": {
        "method": "dpop",
        "runtime_id": "application_runtime_456",
        "agent_id": "local_agent_789",
        "identity_evidence": {
          "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1",
          "format_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
          "artifact_digest": {"profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1", "value": "sha-256:<base64url-digest>"},
          "issuer": "https://issuer.example/agents",
          "subject": "agent-subject-opaque-7f3a",
          "verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
          "key_binding": {"profile": "https://example.com/profiles/issuer-key-thumbprint/v1", "value": "sha-256:<base64url-digest>"},
          "lifecycle": {"freshness_profile": "https://example.com/profiles/status-max-age/2026-01", "status_profile": "https://example.com/profiles/agent-passport-status/2026-01", "status_ref": "app-status-subject-4c18"}
        },
        "jkt": "<base64url-thumbprint>"
      },
      "audit": {
        "local_receipt": "required",
        "app_receipt": "required"
      },
      "grant_id": "grant_123",
      "grant_hash": "sha-256:<base64url-digest>"
    }
  ]
}
```

The response MUST describe current authoritative state and MUST use
`Cache-Control: no-store`. A resource-server enforcement point that does not
share the authorization server's authoritative grant state MUST introspect on
every action and MUST NOT positively cache `active: true`. This prohibition is
required by this profile's immediate revocation semantics; deployments that
need positive caching must define and advertise a different bounded stale-use
profile rather than claiming conformance to this one.

## Grant Credentials and Proof

An Agent Grant MAY be represented or proven by one of several mechanisms:

- bearer grant token
- sender-constrained token
- DPoP-bound token
- mTLS-bound token
- app-side server session binding
- token introspection result
- signed delegation object
- macaroon-like caveated capability

This draft defines two credential profiles:

- **Compatibility Bearer Credential Profile**: an explicitly labeled
  development or compatibility profile in which the runtime holds a bearer
  credential outside every agent-visible context. It is not proof-bound and
  MUST NOT be advertised as the Proof-Bound Credential Profile.
- **Proof-Bound Credential Profile**: every Agent Surface action uses a
  sender-constrained credential or an app-authenticated runtime session that
  requires possession of a bound key or channel credential on every request. A
  reusable session identifier, cookie, or bearer token by itself does not
  satisfy this profile.

A future draft is expected to define additional interoperable proof profiles.

Regardless of representation, a Grant Credential MUST let the application
establish or obtain from authoritative grant state all of the following:

- the active `grant_id`;
- the intended application or resource-server audience;
- the bound runtime identity;
- when Runtime Attestation is selected, the exact stable attestation binding,
  concrete profile, verifier id, proof-key thumbprint, and access to current
  authoritative appraisal state;
- the bound agent identity and complete identity-evidence envelope required by
  its selected profiles; and
- the credential-binding method and any proof-of-possession key or session
  binding that it requires.

The application MUST reject a presentation whose binding does not match the
grant's `delegate` or `credential_binding` values. An introspection or
server-side session profile MAY supply these values indirectly, but the runtime
MUST NOT substitute its own unverified assertion for application-verifiable
binding evidence.

Proof-Bound Credential Profile methods include DPoP, mTLS, and equivalent
proof-of-possession mechanisms. A DPoP method MUST follow RFC 9449, bind the
proof to the request, and accept proofs only within a limited freshness window.
It SHOULD track `jti` values during that window and reject duplicates where the
deployment can maintain the required shared state. Reuse of a server-provided
DPoP nonce MUST NOT by itself be treated as replay. An mTLS method MUST follow
RFC 8705, require the protected-resource request to use the certificate bound
to the token, and reject a certificate mismatch or an invalidated binding.
Reuse of that bound certificate across valid requests MUST NOT by itself be
treated as replay. A proof-bound server session MUST be active, bound to the
grant and runtime, and authenticated with its bound key or channel credential
on every request.

A bare bearer credential MAY be used only in the Compatibility Bearer
Credential Profile. It remains outside every agent-visible context and is
subject to short expiration, audience restriction, revocation, and
application-side grant verification.

## Subdelegation

A runtime MAY use a subagent, remote model, MCP server, tool, adapter, or an
ungranted secondary runtime to help execute delegated work. Receiving task
context does not make that component a grant delegate and does not transfer
Agent Grant authority.

The runtime MUST treat every downstream component, including an ungranted
secondary runtime, as untrusted with respect to application authority. It MUST
NOT forward a Grant Credential, raw application credential, approval artifact,
or an authorization path that can invoke an Agent Surface outside runtime
mediation. A downstream component that needs an application action MUST request
a typed action through the controlling runtime; the runtime MUST evaluate the
original grant, policy, approval, and redaction rules again for that request.

The application MAY instead issue a child grant that makes a secondary runtime
a separate delegate. Once that grant is issued, the child runtime is the
controlling runtime for actions under the child grant and sends them directly to
the application with its own bound credential; those actions do not route
through the parent runtime. The parent runtime MUST NOT present the child
credential or mediate an action as if it originated from the child.

The child grant MUST record `parent_grant_id` and `parent_runtime_id`, and MUST
have equal or narrower actions, locations, scopes, resources, caveats,
credential-release permissions, and lifetime. When the parent has an `actions`
allow-list, the child's list MUST be a subset; when the parent has no action
authority, the child MUST NOT add it. A child MUST NOT add a stronger companion
stage, effect envelope, or weaker approval semantics under a reused scope. The
child action subset MUST remain closed over required companion dependencies;
the application MUST reject an unclosed subset instead of adding stages. The
child `resource_server.app_id`, issuer, surface version, and `surface_hash` MUST
exactly equal the parent's values. Derivation onto another surface snapshot
requires a future explicit compatibility profile or fresh independent user
consent. The application MUST revoke or suspend the child
grant when the parent grant expires, is revoked, or loses the authority from
which the child grant was derived. A parent grant or credential MUST NOT be
forwarded as implicit subdelegation.

When the parent selected a Runtime Identity Profile, a child bound to the same
runtime MUST retain the exact active runtime identity projection or obtain a
new Grant after a material identity change. A child bound to another runtime
MUST use that runtime's independently authenticated projection and binding; it
MUST NOT inherit the parent's authentication method, management posture,
locality, assurance, binding id, or claims revision.

When the parent selected the Remote Processing Privacy Profile, every ungranted
downstream component remains part of the parent's complete processing path.
A child Grant selecting the profile MUST resolve its own path and receive its
own deterministic ceiling; it MUST NOT inherit the parent's path commitment as
evidence. This profile does not project a parent source into the child's
effective `data_exposure`, so a parent MUST NOT forward application-originated
payloads or equivalent representations to a separately granted child. The
child obtains such data from its own independently authorized application
source. Path enum values have no attenuation order, so an issuer MUST NOT
rewrite one value into another while deriving a child.

When the parent selected the Agent Training Use Policy Profile, a child MUST
retain the exact profile and a canonical `permitted_classes` set no wider than
the parent set intersected with the child's complete effective exposure-class
union. An empty intersection remains an explicit empty array; the child MUST
NOT omit the constraint or add a class. When the parent omitted the profile, a
derived child MAY add the empty-array form only if the parent selected Remote
Processing Privacy and the child retains its exact profile and path value while
deriving its own binding and ceiling. Otherwise the child needs a fresh
independent root Grant and consent. When the parent omitted this profile, a
non-empty training permission requires that fresh flow and is not child
attenuation.

When the parent selected Runtime Attestation, every child MUST obtain a new
challenge and accepted appraisal bound to the child's exact
`grant_request_hash`, producing a child-specific stable binding and mutable
record. A same-runtime child MAY retain the exact Runtime Identity projection,
concrete profile, verifier, maximum age, proof key, and sanitized assurance when
they remain current, but it MUST NOT reuse the parent's binding, Evidence, or
Result. A child bound to another runtime MUST instead use that runtime's
independently authenticated identity, proof key, Evidence, and assurance.
Parent Grant revocation still cascades through the ordinary Semantic Grant
Revocation Transition. Revocation or invalidation of a shared runtime identity,
Attester, proof key, Verifier, policy, endorsement, or reference value makes
every dependent child-specific appraisal inactive.

When the parent selected the Purpose- and Task-Bound Agent Grant Profile, child
derivation MUST follow that profile's portable partial order. A purpose-bound
parent can retain that exact purpose or add one issuer-verified task under it; a
task-bound parent can retain only that exact purpose and task tuple. Removing
or replacing a binding, selecting a sibling task, or changing either revision
is not child attenuation. A parent that omitted the profile can add a verified
purpose or task binding as a restriction, but the child MUST still be linked to
the parent and cannot use that binding to add any ordinary authority.

Child budget limits MUST retain every inherited member with an equal or smaller
limit, and every charge or occupied slot consumes the child and ancestor
ledgers. A child MAY add a supported standard dimension as a further
restriction. Every child `cost.currency` MUST exactly equal every ancestor
`cost.currency`; mixed-currency derivation is invalid. A child bound to the same
runtime shares that runtime's lineage ledger. When the child would bind a
different runtime and any `max_tool_calls`, `max_model_tokens`,
`max_runtime_seconds`, or runtime-cost partition is present in its ancestry,
the application MUST reject issuance because this draft defines no
cross-runtime shared-accounting or allocation profile.

## Grant Verification

Applications MUST verify every action against grant state:

- grant exists and is active
- the credential audience exactly matches `agent_api.credential_audience` in
  the verified manifest snapshot selected by the grant
- recomputed `grant_hash` matches both the presented action context and current
  authoritative Grant Object
- `resource_server.surface_hash` matches the retained, verified manifest
  snapshot used to interpret the action and its schemas
- the retained manifest declares a supported `surface_mode`; when it is
  `proposal_only`, the complete action catalog satisfies that mode, the Grant
  explicitly denies credential release, the requested action's manifest-
  declared `execution.mode` is `read` or `propose`, and the request repeats
  that exact mode
- grant credential or proof is valid
- grant is bound to the user
- grant is bound to the runtime
- when `delegate.runtime_identity` is present, its complete projection and
  repeated credential-binding values match the authoritative active runtime
  record at the exact claims revision
- when `delegate.runtime_attestation` is present, its complete stable object
  and repeated credential-binding values match the exact authoritative binding,
  the proof-key cross-binding is valid, and the mutable appraisal record is
  current `accepted` at the required freshness, policy, and reference values
- when `constraints.remote_processing` is present, its profile and path are
  supported, its output-only ceiling is the exact deterministic value, the
  controlling Runtime Identity satisfies the necessary predicate, and every
  class in the complete effective exposure closure is at or below that ceiling
- when `constraints.training_use` is present, its profile is supported, its
  `permitted_classes` value is a canonical set no wider than the approved
  request and complete effective exposure-class union, and every authoritative
  Grant, token, introspection, and stored-state copy matches the hashed value
- when `constraints.purpose_binding` is present, its exact profile is supported,
  the scoped purpose and optional task records are at the Grant-bound revisions
  and in active state, the task still belongs to that purpose, the authoritative
  session repeats the exact binding, and the action, resources, normalized
  input, mode, and effects satisfy the current issuer-owned policy
- grant is bound to the agent and complete identity-evidence envelope, both
  authoritative copies are exact, and the independently verified artifact,
  key binding, agent binding, lifecycle state, and freshness remain usable
  under every selected profile
- credential-binding method and proof-of-possession requirements are satisfied
- for DPoP, the proof is request-bound and within the limited acceptance window;
  when `jti` replay tracking is enabled, its `jti` has not already been accepted;
  reuse of a valid server nonce is not rejected by itself
- for mTLS, the presented certificate matches the certificate bound to the token
  and the binding has not been invalidated; reuse of the matching certificate is
  not rejected by itself
- for a proof-bound server session, the session is active, bound to the grant
  and runtime, and authenticated with the bound key or channel credential
- the requested action identifier resolves exactly once in the retained pinned
  manifest, the grant contains a non-empty `actions` allow-list containing that
  identifier, and the action is served at a granted `location` and remains
  compatible with the granted scopes and resource constraints
- the grant action allow-list is closed over every required companion
  dependency in its pinned manifest snapshot
- request `execution.mode` exactly matches the action declaration in the
  manifest snapshot selected by `surface_hash`
- whenever the action declares `input_hash_profile`, recomputed `input_hash`
  matches the request and any verified runtime receipt
- for a state-changing action, recomputed `execution_hash` matches the request
  and verified runtime receipt
- referenced companion actions resolve in the same manifest snapshot and the
  invoked companion action is independently granted
- any preview token is unexpired and bound to this app, grant, session,
  surface, action, input, preconditions, and expected effects
- declared preconditions still hold immediately before a state change
- any required reservation is active, holder-bound, resource-compatible, and
  atomically consumable by this commit
- expected effects remain within the manifest declaration and applicable
  schemas before mutation
- a compensation or revert has independent current authority and a verified
  eligible target application receipt with unrecovered confirmed effects
- a revert has receipt-bound prior-state evidence and its declared current-state
  preconditions hold atomically with restoration
- scope permits the action
- resource constraints permit the target object
- expiration has not passed
- every application-authoritative write, session-occupancy, and
  application-cost reservation fits the grant and all ancestor ledgers
- when `audit.approval_receipt` is present, its exact profile and per-action
  requirement are supported and every required approved receipt is complete,
  authenticated, unexpired for first admission, bound to the exact invocation,
  and represented by the role map required for the manifest approval mode
- approval caveats are satisfied
- idempotency key is valid

After an effect was or may have been attempted, the application MUST validate
and record actual effects against the core Effect Model and any declared
`actual_effects_schema`. Post-effect uncertainty does not retroactively satisfy
a failed precondition or authorize an undeclared effect.

Runtimes SHOULD verify:

- grant is active
- `grant_hash` matches the complete grant returned at issuance or introspection
- `surface_hash` matches the verified manifest snapshot pinned for that grant
- `surface_mode` is supported and the selected action and credential-release
  policy satisfy its surface-wide bound
- local user has not revoked the app, runtime, or agent
- the exact Grant-bound identity-evidence envelope remains valid under the
  locally supported format, digest, verification, key-binding, freshness,
  status, and any selected integrity profiles
- when Runtime Attestation was selected, the returned stable binding, profile,
  verifier, proof key, assurance, and current privacy-filtered accepted state
  match the locally confirmed requirement without fallback
- requested action is compatible with the verified Agent Passport capability
  set without treating a declaration as Grant authority
- local policy allows the action
- local approval is present when required
- every runtime-authoritative tool, model-token, runtime-time, and runtime-cost
  reservation fits the grant and all ancestor ledgers
- durable lineage-delegate and session runaway-guard state for the exact Grant,
  delegate, session, and generation is available and the next scheduling or
  transport step fits every applicable finite guard
- action input matches the declared schema
- execution mode, context, and hashes match the pinned action declaration
- preview evidence is current and any required reservation belongs to the
  bound tuple
- expected effects and recovery limitations are presented before approval
- secrets and credentials are not exposed to the agent
- any subagent, tool, adapter, remote model, or secondary runtime remains
  subject to the same runtime mediation and does not receive implicit authority
- when the Remote Processing Privacy Profile is selected, the actual complete
  data-bearing path still satisfies the exact Grant commitment immediately
  before every disclosure, every class fits the effective ceiling, and an
  unknown recipient or enforcement state fails closed
- when the Agent Training Use Policy Profile is selected, a source is withheld
  from training unless its complete class set is a subset of the effective
  `permitted_classes`, the Remote Processing path remains valid, and every
  downstream recipient enforces an equal or stricter training policy
- when the Purpose- and Task-Bound Agent Grant Profile is selected, the exact
  issuer-authenticated purpose and optional task revisions, relationship, and
  current active state match the Grant and session, and local policy does not
  treat task prose or an external task identifier as authority

# Purpose- and Task-Bound Agent Grant Profile

This optional profile binds an Agent Grant to an issuer-owned purpose record
and, when required, one exact task record within that purpose. It prevents a
long-lived or otherwise broad Grant from being reused merely because an action
is in its ordinary action, scope, location, and resource allow-lists. The
profile identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1
```

The profile adds a restriction, not a new source of authority. Effective action
authority remains the intersection of the current credential, Grant actions,
locations, scopes, resource constraints, active session, application policy,
and every other selected profile. A purpose or task match can only narrow that
intersection. It cannot add an action, resource, scope, location, execution
stage, effect, approval, lifetime, budget, or disclosure permission.

## Purpose Binding Object and Authority Boundary

The profile uses this closed `constraints.purpose_binding` object:

```json
{
  "profile": "https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1",
  "purpose": {
    "id": "pur_01J2Q7M4K8X5",
    "revision": "rev_3"
  },
  "task": {
    "id": "tsk_01J2Q7N9C3V6",
    "revision": "rev_7"
  }
}
```

`profile` and `purpose` are REQUIRED. `task` is OPTIONAL. The top-level object
and each nested reference object are closed. A reference contains exactly `id`
and `revision`, each a non-empty opaque I-JSON string. This profile assigns no
lexical ordering, hierarchy, URL dereference, prefix, path, UUID, timestamp, or
digest semantics to either value. An implementation MUST compare both strings
for exact equality after ordinary JSON parsing and MUST NOT normalize case,
whitespace, Unicode, separators, or number-like content.

The purpose and task namespace is scoped to the exact
`(resource_server.issuer, resource_server.app_id, subject.user)` tuple. The
Grant Issuer owns the records, their revisions, their lifecycle, and the
purpose-to-task relationship. A runtime can request exact references already
made available through an authenticated user or application workflow, but it
cannot mint a record, define its semantics, move a task between purposes, or
prove current state by asserting an identifier. A copied A2A task id, workflow
run id, issue id, agent-generated goal, label, description, prompt, digest, or
receipt is not an issuer record unless the Grant Issuer has independently
resolved it as the exact scoped record.

For each purpose record, the Grant Issuer MUST retain an authoritative revision,
current lifecycle state, and policy capable of deciding whether a proposed
Grant and later action remain within that purpose. For a task record, it MUST
also retain the exact parent purpose, task revision, current lifecycle state,
and task policy. A semantic change to a record's allowed action family,
resource set, normalized input predicate, effect boundary, or parent
relationship MUST create a new revision. A deployment MUST NOT change those
semantics under an existing revision. A lifecycle transition can occur without
changing the revision because current lifecycle state is independently checked
on every admission.

The current evaluation state is one of:

- **active**: the exact revision and, for a task, its exact parent relationship
  are current and can constrain new work;
- **suspended**: the exact record is known but temporarily cannot authorize new
  work;
- **terminal**: the record is completed, cancelled, revoked, expired,
  superseded, or otherwise permanently closed for new work; or
- **unavailable**: the enforcement point cannot establish authenticated current
  state for the exact scoped record.

These states are authoritative server state and are not added to the Grant
hashing view. A status response, label, or client cache cannot override them.
An implementation MAY use richer internal states but MUST map them
conservatively to this behavior.

This profile reuses the single `constraints.expires_at` member. During issuance,
the Grant Issuer MUST set it no later than every known purpose or task lifetime
boundary. The profile defines no second `valid_until` member. Later closure,
suspension, or policy change takes effect immediately even if the hashed Grant
expiration is later.

## Issuance, Consent, and Returned Grant

A request selecting this profile MUST contain the exact
`constraints.purpose_binding` object and the manifest MUST advertise its exact
profile identifier. The Grant Issuer MUST:

1. derive `subject.user` from authenticated authority rather than the request;
2. resolve the exact purpose and optional task references in that subject and
   application namespace;
3. verify exact revisions, active lifecycle state, and the task-to-purpose
   relationship;
4. verify that the requested actions, locations, scopes, resources, constraints,
   effects, and expiry satisfy both the purpose and optional task policy;
5. obtain the issuance-model consent required for that exact binding; and
6. return the exact approved binding in the authoritative Grant.

An unknown identifier, wrong revision, wrong subject, wrong application,
missing task relationship, inactive record, or action outside the effective
policy MUST fail closed. The issuer MUST NOT search other users or applications
for a similarly named record, silently substitute a sibling task, remove the
task to make the request purpose-only, or replace a revision with a newer one.

The local Consent Preview and Grant Issuer consent view MUST show the exact
purpose id and revision, the exact task id and revision when present, whether
the request is purpose-only or task-bound, the effective Grant expiry, and any
parent or child Grant relationship. They MAY show an authenticated,
issuer-supplied safe label as non-authoritative help. The label and
`session.start.payload.task.goal` MUST be visually distinguished from the opaque
authority references and MUST NOT replace them.

Changing, adding, removing, or substituting a purpose id, task id, revision,
relationship, lifecycle result, or expiration makes a pending preview stale.
The runtime MUST regenerate and reconfirm the preview before dispatch. After
issuance, it MUST require the returned binding to be exactly equal to the
confirmed request. A different binding is not a valid server attenuation,
including when the returned task appears more specific or has a
human-readable description that looks equivalent.

The complete binding participates in the ordinary `grant_hash`. No purpose- or
task-specific digest, signed description, intent hash, or natural-language
similarity result can replace exact object comparison and current issuer
resolution.

## Session and Action Enforcement

A session under a bound Grant MUST copy the complete
`constraints.purpose_binding` object into
`session.start.payload.task.purpose_binding`. The two objects MUST be deeply
equal after structural validation. The application stores that exact binding
in the authoritative session record, and a `session.state` response for this
profile repeats it. When the Grant is unbound, the session member MUST be
absent. A runtime or application MUST reject an invented, omitted, changed, or
additional session binding as `session_invalid`.

`session.start.payload.task.kind`, `goal`, and `inputs` remain informational
orchestration data. They do not establish purpose, task identity, resource
authority, or policy satisfaction, even when their text or identifiers happen
to match an issuer record. Multiple sessions MAY use one active bound Grant;
this profile is not a single-use or single-session profile.

Before admitting each new action, the application MUST:

1. verify the complete ordinary Grant, credential, hash, surface, delegate, and
   active session tuple;
2. resolve the exact current purpose and optional task records under the
   Grant-bound user and application;
3. require the exact revisions, active state, and task-to-purpose relationship;
4. require exact equality between the Grant and authoritative session binding;
   and
5. apply the issuer-owned purpose and task policy to the requested action,
   target resources, normalized input, execution mode, and maximum effects.

These checks occur before idempotency admission, budget charge, capacity
admission, policy receipt creation, workload dispatch, reservation, or effect.
The runtime SHOULD perform the equivalent local check from its authenticated
current view, but a runtime decision or receipt never replaces independent
application enforcement.
An unavailable authenticated record result uses
`purpose_binding_status_unavailable`. A known suspended record or definitive
purpose/task policy denial uses `purpose_binding_denied`. Neither code reveals
the record or rule that failed.

The Action Request and receipts continue to carry the existing `grant_hash`,
session tuple, action, input, execution, policy, and effect bindings. They MUST
NOT add a raw purpose label, goal, task input, or parallel purpose hash under
this profile. Avoiding a duplicate projection prevents two synchronization
sources and limits disclosure. A Policy Decision uses its existing wire shape;
the exact purpose binding and current issuer record are mandatory evaluation
inputs, while `matched_rules` and `safe_to_show` contain only identifiers and
text safe for the affected user.

## Attenuation, Subdelegation, Exchange, and Renewal

Purpose binding has this portable partial order, subject to every ordinary
Grant attenuation rule:

```text
unbound
  -> exact purpose
       -> exact task under that purpose
```

More precisely:

- an unbound parent can derive a child bound to one verified purpose or one
  verified task under that purpose;
- a purpose-bound parent can derive a child with the exact same purpose
  reference, or add one exact task whose current authoritative parent is that
  purpose;
- a task-bound parent can derive only a child with the exact same purpose and
  task ids and revisions; and
- every child still has a subset of ordinary actions, locations, scopes, and
  resources, equal or stricter caveats, a no-later expiry, the same pinned
  surface, and explicit lineage.

The following changes are not attenuation and require a fresh independently
consented semantic Grant: removing the binding; changing a purpose; replacing a
task with its purpose-only parent; replacing a task with a sibling; changing
either revision; increasing expiry; or treating a string prefix, URI path,
digest, description, or external task id as proof of narrowing. Every accepted
binding change produces a new Grant Object and `grant_hash`. A verified
purpose- or task-narrowing child can use the existing child-derivation consent
rules because it cannot widen the parent; an incomparable or wider result
requires the complete local preview and Grant Issuer consent flow.

Token exchange MUST apply the same order and preserve source lifecycle linkage.
RFC 8693 token exchange does not establish that linkage by itself. Renewal or
refresh can preserve the exact binding only while its records remain active,
the relationship is unchanged, and the new expiry does not exceed either
record's current lifetime. A revision replacement, even for the same id,
requires fresh consent rather than an automatic refresh.

## Lifecycle, Revocation, Recovery, and Replay

A terminal purpose record invokes the Semantic Grant Revocation Transition for
every Grant bound to that purpose and every descendant. A terminal task record
does the same for Grants bound to that exact task and their descendants, but
does not revoke a sibling task or an independently consented Grant. A
purpose-only Grant can remain active for other permitted tasks after one child
task closes; the application still denies every action whose current purpose
policy requires that closed task.

When a selected record is suspended or its current state is unavailable, the
application and runtime MUST stop new sessions and actions and fence affected
active sessions without claiming that a terminal revocation occurred. If the
exact same revision and relationship later return to active state, the runtime
can explicitly resume the interrupted session under the ordinary generation
rules or start a new session; the Grant hash does not change. An implementation
MUST NOT continue optimistically from a cached active result.

Terminal closure does not erase receipts, rewrite an already authoritative
effect, or turn an unknown outcome into no effect. A completed idempotency
record and its original response and receipts remain immutable, but a revoked
Grant Credential cannot invoke the Action Request replay path. Historical
results can be retrieved only through an existing independently authenticated
and authorized receipt or reconciliation path whose disclosure checks remain
current; retrieval creates no admission or effect. A new idempotency key after
closure is new work and MUST be rejected. Replay validation can prove
historical Grant-byte integrity, but it does not prove that the purpose
semantics were correct or that the issuer record is currently active.

## Security and Privacy Requirements

Purpose and task identifiers SHOULD be random or opaque application-scoped
references and MUST NOT embed repository names, customer identities, task prose,
prompt content, or another user's stable identifier. The Grant Issuer MUST make
unknown, wrong-subject, wrong-application, wrong-revision, and unauthorized
lookups externally indistinguishable. Neither the runtime nor the application
may use this profile as an enumeration interface.

Human-readable purpose or task labels, workflow descriptions, task inputs,
provider records, and policy internals remain in their authoritative UI or
policy boundary. They MUST NOT be copied into the Grant, credential, ordinary
receipts, public errors, traces, prompts, or agent-visible logs. Retention of the
opaque binding and lifecycle record MUST be bounded by active enforcement,
receipt reconciliation, security audit, and applicable legal obligations.

This profile makes reuse outside an issuer-defined purpose or task detectable
and enforceable. It does not prove that a human-authored label is truthful,
that an agent's reasoning remained on-topic, that downstream processing
complied with a purpose limitation, or that a deployment satisfies GDPR or
another legal regime. Such claims require separate policy, evidence, audit,
and legal analysis.

# Capability Matching

Capability matching is an advisory process used by the runtime to help the user
choose a compatible agent. It does not invert authority.

Incorrect framing:

```text
The app needs an agent with capability X, so the runtime picks one.
```

Correct framing:

```text
The app exposes actions X/Y/Z.
The user wants to delegate work in that app.
The runtime compares app requirements with passports of user-owned agents.
The user authorizes a specific runtime-agent-passport tuple through a grant.
```

Matching inputs:

- the manifest's `surface_mode` upper bound
- action `capability_hint`
- action schemas
- required scopes
- risk labels
- approval modes and the selected Approval Receipt role and maximum-age rules
- execution modes and required companion stages
- declared effect envelopes and effect schemas
- declared data classes, redaction, and retention obligations
- the complete selected processing path, its Remote Processing Privacy
  classification ceiling, and current recipient-policy enforcement capability
- the requested Agent Training Use class set, complete class set of every
  source, and current downstream training-policy enforcement capability
- the exact requested Purpose Binding profile, purpose and optional task
  references, and whether current authenticated issuer state and relationship
  are available; goal text and external task ids are not matching authority
- reservation requirements and available recovery actions
- Agent Passport capabilities
- Agent Passport security policy
- selected Runtime Attestation concrete profile and the runtime's current
  ability to generate profile-conforming Evidence with the selected proof key
- local runtime adapter availability
- user preferences
- enterprise policy

Risk Explanation UI Hint prose is not a matching input. A matcher MUST NOT use
its presence, wording, language coverage, or apparent sentiment to change
candidate status, reasons, ranking, required approval, or the canonical risk
summary. A local user interface can attach the selected publisher hint only
after matching, from the still-current pinned manifest snapshot.

Impact Simulation is a downstream local presentation feature, not a matching
input, candidate-ranking signal, or Capability Match Result member. When a
runtime binds a result to a selected Capability Match Result, it can use the
fresh candidate status and machine reasons only after exact verification and
independent recomputation of the same candidate decision. Every requested
example projects that one decision; the runtime MUST NOT rerun matching per
action or serialize advisory or overridden reasons. It also independently
recomputes every example's request relation, action semantics, effect envelope,
exposure, companion closure, and exact recovery projection. Adding, removing,
or reordering an example MUST NOT change candidate status or
`grant_request_hash`.

This draft standardizes those outputs with the local-only Capability Match
Result Profile:

```text
https://github.com/0al-spec/agent-surface/profiles/capability-match-result/v1
```

It also defines this Canonical Object Hash domain for the exact semantic Grant
request evaluated by the matcher:

```text
https://github.com/0al-spec/agent-surface/hash/grant-request/v1
```

## Semantic Grant Request Hash

The hashing view is one complete candidate-specific semantic Agent Grant request
before any authorization-server output is added. For RFC 9396, the runtime
starts with the sole Agent Grant authorization-details object and removes only
its `type` member. `locations`, `actions`, `delegate`, `resource_server`,
`scopes`, `constraints`, `credential_profile`, and `audit`, including the exact
candidate agent and complete identity-evidence envelope, every selected
profile, and the complete
request-only Runtime Attestation requirement, remain in the hashing view. A
selected Remote Processing Privacy constraint contributes its exact request
`profile` and `path`; the server-only `classification_ceiling` is absent.
Selected Agent Training Use Policy contributes its exact request `profile` and
canonical `permitted_classes` set; the set remains present when empty.
A selected Approval Receipt Profile contributes its exact profile and complete
per-action role and maximum-age requirement projection.
Another issuance model MUST construct the same semantic object.

A multi-candidate match MUST construct and hash one complete request for each
candidate. All non-candidate request semantics and the controlling runtime
binding MUST be identical across those requests; `delegate.agent` and the
complete identity-evidence envelope MUST equal that candidate. The matcher MUST NOT hash a
candidate-independent template or one candidate's delegate and represent the
result as binding the other candidates.

`grant_id`, `grant_hash`, `subject`, `credential_binding`, `data_exposure`, and
server-derived `delegate.runtime_identity`, `delegate.runtime_attestation`, and
`constraints.remote_processing.classification_ceiling` are invalid in a
request and MUST NOT be silently removed from malformed input merely to compute
a hash. OAuth parameters, redirect URIs, PKCE values, client
authentication, user-interface labels, raw identity artifacts, and local policy
state are not semantic Grant Object members and are not included.

The runtime computes each candidate's `grant_request_hash` with the Canonical
Object Hash Profile and the domain above. The value identifies the exact
authority request for that candidate; it does not authorize that request or
prove consent. A change to common request semantics requires every candidate
hash and the complete match result to be recomputed. A candidate tuple change
requires a new candidate entry and hash.

For the hash-layer test view `{"delegate":{"runtime":"r"}}`, the canonical
wrapper is:

```json
{"domain":"https://github.com/0al-spec/agent-surface/hash/grant-request/v1","object":{"delegate":{"runtime":"r"}}}
```

Its hash is
`sha-256:NIahpleJauoH9OEqZhL1Spqj6oP1r78nA1A7GCwJnYA`. The view is intentionally
not a complete valid Grant request; the vector fixes only domain separation and
hash encoding.

## Capability Match Result Object

A Capability Match Result is a closed I-JSON object with this wire shape:

```json
{
  "profile": "https://github.com/0al-spec/agent-surface/profiles/capability-match-result/v1",
  "match_id": "match_01J2E7M2V6Z91Y2R3B4C5D6E7F",
  "evaluated_at": "2026-07-14T10:00:00Z",
  "valid_until": "2026-07-14T10:05:00Z",
  "bindings": {
    "surface": {
      "issuer": "https://code.example.com",
      "app_id": "code.example.com",
      "surface_version": "2026-06-25",
      "surface_hash": "sha-256:<base64url-digest>"
    },
    "runtime": {
      "runtime_id": "application_runtime_456",
      "runtime_identity_profile": "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1",
      "binding_id": "rbind_01J2D7M2V6Z91Y2R3B4C5D6E7F",
      "claims_revision": 3
    },
    "agent_inventory_revision": "agents-42",
    "adapter_inventory_revision": "adapters-9",
    "local_policy_revision": "local-policy-18",
    "enterprise_policy_revision": "enterprise-policy-7",
    "user_preferences_revision": "preferences-4"
  },
  "candidates": [
    {
      "agent_id": "local_agent_789",
      "identity_evidence": {
        "identity_evidence_hash": "sha-256:<base64url-digest>",
        "status_valid_until": "2026-07-14T10:05:00Z",
        "agent_binding": "document_only",
        "integrity_profile": null,
        "capability_names": ["comment.create", "pull_request.get"]
      },
      "grant_request_hash": "sha-256:<base64url-digest>",
      "status": "compatible",
      "reasons": [],
      "missing_capabilities": [],
      "required_scopes": ["pull_request.comment", "pull_request.read"],
      "required_approvals": [
        {"action_id": "comment.create", "mode": "user_or_app"}
      ],
      "risk_summary": {
        "highest": "public_side_effect",
        "actions": [
          {"action_id": "comment.create", "risk": "public_side_effect"},
          {"action_id": "pull_request.get", "risk": "read"}
        ]
      },
      "execution": {
        "supported_stages": ["comment.create", "comment.propose"],
        "missing_stages": [],
        "maximum_effects": [
          {
            "action_id": "comment.create",
            "effects": [
              {
                "effect_id": "comment-publish",
                "operation": "publish",
                "resource_type": "comment",
                "visibility": "shared",
                "boundary": "internal",
                "reversibility": "irreversible",
                "domain": "communication"
              }
            ]
          }
        ],
        "recovery_limitations": [
          {"action_id": "comment.create", "code": "irreversible"}
        ]
      },
      "data_exposure": [
        {
          "source": {"kind": "action", "id": "comment.create"},
          "classes": ["repository.content"],
          "redaction": {"mode": "none"},
          "retention": {"mode": "transient", "delete_on_grant_end": true}
        }
      ],
      "sandbox_constraints": [
        {"id": "network.egress", "status": "satisfied", "source": "passport"}
      ]
    }
  ]
}
```

`profile`, `match_id`, `evaluated_at`, `valid_until`, `bindings`, and
`candidates` are REQUIRED. Unknown members are forbidden in the top-level,
bindings, surface, runtime, candidate, identity-evidence, approval, risk-summary,
execution-wrapper, recovery-limitation, sandbox, reason, and reason-subject
objects. Embedded Effect Model and Data Exposure Contract objects retain the
closed shapes and extension rules of their defining sections.
`evaluated_at` and `valid_until` are RFC 3339 timestamps and MUST satisfy
`evaluated_at < valid_until`. `match_id` is an opaque, collision-resistant
local correlation identifier. It is not a credential, approval, idempotency
key, or stable user or agent identifier. `profile` MUST exactly equal the
Capability Match Result Profile identifier, and `match_id` MUST be unique among
results retained by that runtime.

`bindings` contains exactly `surface`, `runtime`,
`agent_inventory_revision`, `adapter_inventory_revision`,
`local_policy_revision`, `enterprise_policy_revision`, and
`user_preferences_revision`; every member is REQUIRED. `bindings.surface`
contains exactly `issuer`, `app_id`, `surface_version`, and `surface_hash` from
the verified manifest. The five revision members are opaque
non-empty strings compared only for exact equality; `enterprise_policy_revision`
and `user_preferences_revision` MAY be `null` when that input does not exist.
The runtime object always contains `runtime_id`. Its other three members are
all `null` when no Runtime Identity Profile is selected. When a profile is
selected but its server projection remains unresolved,
`runtime_identity_profile` contains the requested identifier while `binding_id`
and `claims_revision` are `null`. When the app-scoped projection is locally
known, all three contain its exact values. A policy decision that requires an
unresolved runtime-identity value makes affected candidates at most
`indeterminate`.

`candidates` contains at most one entry for each (`agent_id`,
`identity_evidence_hash`) pair and at most one null-evidence entry for an agent.
`identity_evidence` is either `null`, producing a blocking
`identity_evidence_missing` reason, or a closed object containing the compact
hash of the complete selected envelope,
`status_valid_until`, `agent_binding`, `integrity_profile`, and sorted unique
`capability_names`. `status_valid_until` MAY be `null` only when status is
unavailable and the candidate is not `compatible`. `agent_binding` is
`document_only`, `code_hash_verified`, or `unavailable`; `integrity_profile` is
non-null only for `code_hash_verified` and MUST otherwise be `null`.
`capability_names` is the exact sorted unique set extracted under the selected
format and verification profiles; it is declaration evidence, not authority.

Every candidate also contains `grant_request_hash`. It is the hash of that
candidate's complete request and MUST be non-null whenever `identity_evidence`
is non-null. For a null-evidence candidate it MUST be `null`, the candidate MUST be
`incompatible` with `identity_evidence_missing`, and it cannot be selected for a Consent
Preview or Grant request.

Every candidate contains all fields shown above. `missing_capabilities`,
`required_scopes`, `execution.supported_stages`, and
`execution.missing_stages` are sorted arrays of unique identifiers.
`required_approvals` entries contain exactly `action_id` and `mode`, are sorted
by `action_id`, and repeat the exact effective approval mode.
`risk_summary` contains exactly `highest` and `actions`; each action entry
contains exactly `action_id` and `risk`, is sorted by action id, and `highest`
is the maximum under the Risk Taxonomy. For a request with no actions, `highest`
is `null` and `actions` is empty. It contains no Risk Explanation UI Hint text;
adding publisher prose would make the closed result invalid. Each
`maximum_effects` entry contains
exactly `action_id` and `effects` and preserves the manifest's complete effect
declarations for every requested state-changing action. A
`recovery_limitations` entry contains exactly `action_id` and `code`; its code
is a value defined by the Action Execution Model or a collision-resistant
extension URI.
`data_exposure` is the deterministic effective projection for the candidate and
request. A sandbox constraint contains exactly `id`, `status`, and `source`;
status is `satisfied`, `unsatisfied`, or `unknown`, and source is
`identity_evidence`, `runtime`, `local_policy`, or `enterprise_policy`.

Candidate order is lexicographic by `agent_id` and then
`identity_evidence_hash`, using UTF-8 byte order; null evidence sorts before non-null hashes for the same
agent. This profile defines no trust score or preferred-agent
ranking. A user interface MAY apply a local ranking but MUST label it as local
policy and MUST NOT serialize it as protocol authority.

## Candidate Status and Reasons

`status` is exactly `compatible`, `incompatible`, or `indeterminate`:

- `compatible` means every required input is known and current, the identity evidence
  and local agent binding are valid, every capability and execution stage is
  supported, all effective policies permit the path, and every required
  exposure, retention, remote-processing, training-use, approval, effect,
  recovery, adapter, and sandbox obligation can be enforced. It has no blocking
  reason and no missing entry.
- `incompatible` means at least one current, authoritative input proves a
  requirement cannot be satisfied. A definitive blocking reason takes
  precedence over additional unknowns.
- `indeterminate` means there is no definitive incompatibility, but at least one
  required input is missing, stale, temporarily unavailable, unsupported, or
  not verifiable. It MUST NOT be treated optimistically as compatible.

A reason object contains exactly `code`, `severity`, and `subject`. `severity`
is `blocking` or `advisory`. `subject` contains exactly `kind` and `id`; kind is
`candidate`, `runtime`, `identity_evidence`, `capability`, `adapter`, `action`, `scope`,
`approval`, `effect`, `recovery`, `exposure`, `sandbox`, or `policy`. Core reason
codes are:

| Code | Meaning |
| --- | --- |
| `identity_evidence_missing` | No complete identity-evidence envelope is available for the candidate. |
| `identity_evidence_invalid` | Current verification proves the evidence or agent binding invalid. |
| `identity_evidence_profile_unsupported` | A required envelope, format, digest, verification, key-binding, freshness, or status profile is not implemented completely. |
| `identity_evidence_status_unavailable` | Fresh authenticated evidence status is unavailable. |
| `capability_missing` | A required semantic capability is not declared or mapped. |
| `adapter_unavailable` | No current local adapter can mediate the candidate. |
| `schema_unsupported` | The runtime cannot validate a required schema or dialect. |
| `execution_stage_unsupported` | A required companion, preview, reservation, or recovery stage cannot be mediated. |
| `scope_unavailable` | The exact requested scope cannot be requested under the selected path. |
| `approval_unsupported` | A required approval mode cannot be enforced. |
| `risk_denied` | Effective policy denies a manifest risk class. |
| `effect_unsupported` | A declared maximum effect exceeds the path's enforceable envelope. |
| `recovery_unsupported` | A required recovery property or limitation cannot be honored. |
| `data_exposure_unsupported` | A required exposure or redaction contract cannot be enforced. |
| `retention_unsupported` | A retention or deletion obligation cannot be enforced. |
| `remote_processing_unsupported` | Current authoritative path state proves the ceiling is exceeded or a recipient cannot enforce the exact profile. |
| `training_use_unsupported` | Current authoritative policy proves the requested training class constraint cannot be enforced for a source or recipient. |
| `sandbox_unsatisfied` | A required sandbox constraint is unsatisfied. |
| `runtime_identity_invalid` | Current verification proves required runtime identity evidence mismatched or invalid. |
| `runtime_identity_unavailable` | Required runtime identity evidence has no current authoritative value. |
| `runtime_attestation_unsupported` | The runtime cannot implement the exact requested concrete attestation profile and proof-key binding. |
| `runtime_attestation_unavailable` | Evidence-generation input required by the concrete profile is temporarily unavailable or not currently verifiable. |
| `policy_denied` | Local or enterprise policy denies the exact path. |
| `input_unknown` | A required input has no authoritative value. |

Blocking `identity_evidence_profile_unsupported`, `identity_evidence_status_unavailable`,
`runtime_identity_unavailable`, `runtime_attestation_unavailable`, and
`input_unknown` reasons produce
`indeterminate` when no definitive blocking reason exists. Every other core
blocking reason produces `incompatible`. An extension reason code MUST be a
collision-resistant URI and its defining profile MUST classify it as definitive
or indeterminate. Only `code` is extensible in this profile: an extension reason
MUST use one of the closed core `subject.kind` values above. Extending the
subject taxonomy requires a different Capability Match Result profile identifier
and complete processing rules. Unknown extension codes with a recognized
subject kind MUST be preserved; an unknown blocking reason defaults to
indeterminate and prevents `compatible`. It MUST NOT be ignored or rewritten as
advisory. Reasons are sorted by blocking before advisory, then code, subject
kind, and subject id.

An unresolved recipient, processor inventory, operator, or enforcement-policy
input uses blocking `input_unknown` with subject kind `policy` and therefore
produces `indeterminate` unless another definitive reason exists. Once current
state proves a path or recipient cannot satisfy the selected profile, the
runtime uses definitive `remote_processing_unsupported` instead. An unknown or
stale training-policy capability also uses `input_unknown`; once current state
proves the source-level constraint or a recipient policy cannot be enforced,
the runtime uses definitive `training_use_unsupported`.

## Freshness, Privacy, and Consent Boundary

`valid_until` MUST be no later than the earliest Passport status deadline,
policy or inventory freshness deadline, runtime-identity freshness deadline,
locally evaluated Runtime Attestation input deadline, or local maximum matching
TTL used by any candidate decision. The complete result becomes stale when that
time passes or when the manifest tuple, common Grant request semantics or any
candidate hash, runtime identity tuple, selected attestation profile or
proof-key capability, candidate identity-evidence envelope or status, agent or adapter
inventory, processing-path, recipient-policy, or training-policy inventory,
local or enterprise policy, or user preferences no longer exactly match the
recorded binding.

A stale result MUST NOT be used to select a candidate, populate a new Consent
Preview, or justify a Grant request. The runtime recomputes the complete result;
it does not patch one status or revision in place. A result that becomes stale
during selection makes the selection stale as well. An Impact Simulation bound
to that result becomes stale at the same transition and MUST be regenerated in
full rather than retaining its prior examples.

In a deployment with separate runtime and application trust domains, the object
remains inside the user-controlled runtime boundary. The runtime MUST NOT send
the application its candidate list, local inventory revisions, other Passport
tuples, sandbox inventory, policy revisions, or user preferences.
It sends only the exact selected semantic Grant request and evidence required by
that request's negotiated profiles. Logs and telemetry SHOULD retain only the
`match_id`, profile, surface tuple, selected candidate request hash and
reference, status, and reason codes unless local policy explicitly requires
more. Before a candidate is selected, telemetry SHOULD omit candidate request
hashes rather than record the complete set.

An application-operated or app-embedded runtime has no confidentiality boundary
from that application. It MUST disclose that fact before enumerating local
agents, and local or enterprise policy MAY prohibit matching in that deployment.

The result is advisory input to the local Consent Preview Contract. A
`compatible` status is not consent, approval, a Grant, a credential, Passport
verification by the application, or permission to add scopes. After selection,
for a Runtime Attestation requirement it means only that the runtime can attempt
the exact concrete profile; it is not an accepted Verifier or Relying Party
appraisal, which remains unresolved until the application completes the flow.
The runtime MUST then recompute the exact semantic request and its hash,
independently recompute the data-exposure projection, verify that the hash
equals the selected candidate's `grant_request_hash` and that all bindings still
match, and, when Remote Processing Privacy is selected, re-resolve the complete
path and verify every class against the expected ceiling before deriving a
fresh Consent Preview. When Agent Training Use Policy is selected, it MUST also
verify the canonical requested set, the complete class set of every source, and
the enforcement policy of every downstream recipient. Adding a suggested scope
or action changes every candidate hash; adding or changing a candidate requires
a new result entry. Either change requires a fresh match result. The
authorization server independently verifies the selected tuple and obtains
issuer-side consent.
