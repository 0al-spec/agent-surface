<a id="asp-delegated-authorization"></a>
# ASP Delegated Authorization

> [!NOTE]
> This is an authoritative module selected by the ASP Document Set Catalog.
> `drafts/agent-surface.md` is a generated aggregate reading view.

- Document ID: `https://github.com/0al-spec/agent-surface/documents/authorization`
- Exact version: `0.1.0-draft.1`
- Canonical path: `drafts/modules/authorization.md`

## Exact Normative Dependencies

- `https://github.com/0al-spec/agent-surface/documents/core` at `0.1.0-draft.1` (canonical `drafts/modules/core.md`)


## Pluggable Agent Identity Evidence Profile

ASP identifies the selected agent inside an application with the opaque,
application-scoped `delegate.agent` value. Deployments that use portable
identity material MUST carry the stable result of verifying that material in a
versioned Agent Identity Evidence Envelope rather than make the source document
format part of the Agent Grant wire shape. The envelope profile identifier
defined by this draft is:

```text
https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1
```

Identity evidence is evidence about a delegate. It is never authority to call
an action, add a scope, bypass approval, release a credential, or claim an
effect. Authority continues to come only from the current app-verifiable Agent
Grant and the application policy decision for the exact action.

### Discovery and Exact Profile Selection

An application that accepts this envelope advertises
`compatibility.agent_identity_evidence_profiles` as a non-empty array of closed
objects. Each object contains exactly these members:

- `profile`, equal to the envelope profile identifier above;
- `format_profile`, a collision-resistant identifier for the source evidence
  syntax and semantic extraction contract;
- `artifact_digest_profile`, a collision-resistant identifier for hashing the
  complete source artifact;
- `verification_profiles`, a non-empty array of unique collision-resistant
  identifiers;
- `key_binding_profiles`, a non-empty array of unique collision-resistant
  identifiers;
- `freshness_profiles`, a non-empty array of unique collision-resistant
  identifiers;
- `status_profiles`, a non-empty array of unique collision-resistant
  identifiers;
- `migration_profiles`, an array of unique collision-resistant identifiers,
  which MAY be empty; and
- `max_artifact_bytes`, a positive I-JSON safe integer.

Example:

```json
{
  "profile": "https://github.com/0al-spec/agent-surface/profiles/agent-identity-evidence/v1",
  "format_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
  "artifact_digest_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
  "verification_profiles": [
    "https://example.com/profiles/agent-passport-verification/2026-01"
  ],
  "key_binding_profiles": [
    "https://example.com/profiles/issuer-key-thumbprint/v1"
  ],
  "freshness_profiles": [
    "https://example.com/profiles/status-max-age/2026-01"
  ],
  "status_profiles": [
    "https://example.com/profiles/agent-passport-status/2026-01"
  ],
  "migration_profiles": [
    "https://github.com/0al-spec/agent-surface/migration/agent-passport-fields-to-identity-evidence/v1"
  ],
  "max_artifact_bytes": 262144
}
```

Every advertised combination is atomic. A runtime, authorization server, or
application MUST select one exact entry and one identifier from each required
profile array. It MUST NOT combine a format from one entry with verification,
key-binding, freshness, status, size, or migration rules from another entry.
An unknown identifier, an unavailable required implementation, or an
incomplete profile definition fails closed as
`identity_evidence_profile_unsupported`; there is no fallback to another
format, an algorithm with the same name, schema validation, or unsigned claims.

Each concrete format profile MUST completely define safe parsing, required
claims, duplicate and extension handling, and how an issuer and subject are
derived. Each digest profile MUST define the exact artifact octets and digest
encoding. Each verification profile MUST define signed bytes, algorithms,
trust anchors, issuer-to-key binding, key rotation, and failure behavior. Each
key-binding profile MUST produce one stable, privacy-safe value that identifies
the verified subject key or key set without embedding raw key material. Each
freshness profile MUST define clock, skew, maximum age, expiry interaction, and
unavailable-state behavior. Each status profile MUST define an authenticated
resolver, an opaque stable status reference, response binding, revision and
replay behavior, and at least the states `active`, `suspended`, `revoked`,
`expired`, `unknown`, and `unavailable`. It MUST define which terminal or
temporary state maps to each of those core states; an implementation MUST NOT
map an unknown source state to `active`.

The profile definitions and their trust configuration are deployment inputs,
not claims supplied by the agent. Merely advertising a profile identifier does
not make an implementation conformant; every selected step and negative case
must be implemented completely.

### Agent Identity Evidence Envelope

The `delegate.identity_evidence` member is a closed object containing exactly
the following members, except that `artifact_ref` is OPTIONAL:

```json
{
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
```

All string members are non-empty. Every `profile` member and
`verification_profile` is a collision-resistant identifier. `issuer` and
`subject` have only the exact semantics assigned by the selected format and
verification profiles; they are not required to be URLs or globally reusable
identifiers. The consuming application SHOULD issue an app-scoped pairwise
`subject` or another non-correlating verified projection when the concrete
profile permits it. It MUST NOT invent or rewrite an issuer or subject after
verification merely to make two artifacts appear equivalent.

`artifact_digest.profile` and `artifact_digest.value` commit to the complete
artifact under the selected digest profile. A digest proves byte identity only;
it does not prove signature validity, issuer trust, lifecycle status, truthful
claims, executable identity, or authority. `artifact_ref` is an optional
locator governed by the selected format and verification profiles. It is not
an identifier, authentication result, or permission, and an application MUST
NOT dereference an arbitrary client-supplied URI outside its allow-listed
resolution and SSRF policy.

`key_binding.profile` defines how `value` is derived from the exact verified
subject key or key set. The value MUST be stable for the Grant lifetime,
collision-resistant within that profile, and safe to place in the app-visible
Grant. A raw public key, certificate chain, DID document, key-resolution
credential, hardware quote, or verifier-private handle MUST NOT be placed in
the envelope. A key rotation that changes this value changes the envelope even
when issuer, subject, or artifact claims remain the same.

`lifecycle.freshness_profile` fixes how current evidence is timed and when it
becomes unusable. `lifecycle.status_profile` fixes the resolver and state
semantics. `lifecycle.status_ref` is an opaque stable application/verifier
reference for the exact issuer, subject, artifact and key binding; it MUST NOT
be a bearer credential or expose a reusable external account identifier. The
reference is included in `grant_hash`, but the current status response,
`checked_at`, `valid_until`, source revision, retry hint, and resolver
credentials are mutable verifier state and MUST NOT be copied into the Grant.

Two envelopes are equal only when their complete closed I-JSON objects are
equal under the Canonical Object Hash Profile. Matching issuer and subject,
matching keys, matching digest bytes under different profile identifiers, or a
resolver claim that two records are aliases does not make them equal. Unknown
members are prohibited; an extension requires a different envelope profile.

Where a compact protocol projection needs to bind this envelope without
repeating it, it uses `identity_evidence_hash` computed by the Canonical Object
Hash Profile with this domain:

```text
https://github.com/0al-spec/agent-surface/hash/agent-identity-evidence/v1
```

The hashing `object` is the complete `identity_evidence` envelope, including
`artifact_ref` exactly when it is present. The result uses the ordinary
`sha-256:<base64url-digest>` encoding. A compact projection MUST carry both the
application-scoped `agent_id` and this hash; it MUST NOT use artifact digest,
issuer, subject, key binding, or status reference alone as a substitute. The
authoritative Grant and credential binding still carry the complete envelope.

### Verification and Mutable Lifecycle State

Before issuance and every enforcement decision, the verifier performs these
steps in order:

1. Select one exact advertised profile combination without fallback.
2. Retrieve no more than `max_artifact_bytes` through the selected authenticated
   or locally trusted resolution path.
3. Compute the selected complete-artifact digest before parsing and compare it
   in constant time with the envelope value.
4. Safely parse and validate the exact concrete format profile.
5. Resolve authenticated trust material and verify the exact signed bytes under
   the selected verification profile.
6. Derive and exact-match the envelope issuer, subject, verification profile,
   and key binding.
7. Resolve the exact `status_ref` under the selected status profile and map its
   authenticated response to one core lifecycle state.
8. Apply the selected freshness profile and derive a local verification record.
9. Bind that verified identity projection to the application-scoped
   `delegate.agent` and, if required, separately verify executable integrity.
10. Only then evaluate consent, issue or introspect a Grant, or admit an action.

The verifier-local record contains at least the complete envelope,
`checked_at`, `valid_until`, the mapped core lifecycle state, authenticated
status revision, local agent-binding result, and any concrete-format claims
needed for policy or capability matching. `valid_until` MUST be no later than
the earliest artifact expiry, key-validity expiry, status maximum age, or local
trust-policy deadline. The record is not a portable attestation. Raw evidence,
external issuer subjects, status responses, resolver credentials, trust paths,
keys, executable paths, and code hashes remain inside the verifier boundary.

Only `active` with an unexpired record is usable. `suspended`, `revoked`, and
`expired` are definitive invalid states. `unknown` and `unavailable` are
indeterminate but fail closed. A stale record is equivalent to unavailable
current status. A component MUST NOT retain a later successful step after any
earlier artifact, profile, trust, key, agent-binding, time, or status input
changes. A fresh response for the same exact envelope can update mutable local
state without changing `grant_hash`.

Verification by the runtime does not replace independent verification by the
authorization server or application. Each enforcing component MUST possess the
selected profiles and either perform the checks itself or rely on an
authenticated verifier relationship explicitly defined by those profiles. A
runtime assertion, copied verification result, Agent Card, self-declared key,
schema-validation success, or source-format signature label is insufficient.

### Grant, Credential, Consent, and Projection Binding

When this profile is selected, a semantic Grant request and authoritative Grant
contain `delegate.runtime`, `delegate.agent`, and the complete
`delegate.identity_evidence` envelope. The requester supplies only an envelope
derived from successful local verification. The authorization server derives
the same projection independently and exact-matches every member before
issuance. When `artifact_ref` is absent, the authorization server MUST already
have an authenticated registration for the exact digest and selected profiles;
the request never carries raw artifact bytes.

`credential_binding.identity_evidence` MUST be an exact copy of
`delegate.identity_evidence`. Both copies are included in `grant_hash` and MUST
remain exact in authorization results, credential issuance and exchange,
introspection, sessions, child Grants for the same agent, consent records,
capability matches, simulations, action verification, management views, and
receipts that project the delegate identity. A missing, mixed, widened,
normalized, or mismatched copy is `integrity_mismatch`.

Consent and management views MUST display the concrete format and verification
profiles, privacy-safe issuer and subject labels, artifact digest, key-binding
profile and value, freshness and status profiles, current state and freshness,
and the local/application agent-binding result. Concrete profiles MAY require
additional human-readable claims. The UI MUST distinguish verified identity
facts, source declarations, verifier-local claims, and application authority.
Any envelope member, trust result, lifecycle state, relevant capability set,
or agent/executable-binding result change makes a pending Consent Preview
stale.

Source claims can make an action incompatible or add a local restriction, but
they MUST NOT add any Grant authority. `issuer`, `subject`, key binding, or
active status proves neither control of the currently connected process nor
that the evidence describes the executable unless a separately named
integrity/attestation profile proves that exact relationship.

### Migration and Legacy Passport Wire Shape

The migration profile defined by this draft is:

```text
https://github.com/0al-spec/agent-surface/migration/agent-passport-fields-to-identity-evidence/v1
```

It migrates the legacy `passport_ref`, `passport_profile`,
`passport_hash_profile`, `passport_hash`, and
`passport_verification_profile` delegate fields into the generic envelope. A
new request or Grant MUST contain either the complete generic envelope or the
complete legacy Passport tuple, never both. Mixed, partial, or conflicting
forms are `integrity_mismatch`; a parser MUST NOT choose one representation.

For an active legacy Grant, the issuer MAY migrate only when it retains or can
freshly reconstruct the exact successful Passport verification record that
created the legacy tuple. The deterministic projection is:

- `profile` is the Agent Identity Evidence Envelope profile above;
- `format_profile` is the legacy `passport_profile`;
- optional `artifact_ref` is the exact legacy `passport_ref`;
- `artifact_digest.profile` and `artifact_digest.value` are the exact legacy
  `passport_hash_profile` and `passport_hash`;
- `verification_profile` is the exact legacy
  `passport_verification_profile`; and
- `issuer`, `subject`, `key_binding`, and `lifecycle` are derived from fresh,
  authenticated verification under the selected concrete profiles, never from
  unverified display metadata or guessed defaults.

Because the legacy tuple does not contain enough information to derive the
last group safely, field renaming alone is not migration. If the issuer cannot
produce one unique current envelope, migration fails closed as
`identity_evidence_migration_required`. It MUST NOT use empty values, local
aliases, first-key selection, last-known status beyond freshness, or a newly
chosen profile to fill the gaps.

Migration always creates a new authoritative Grant Object and `grant_hash`; it
does not mutate a Grant in place. The issuer obtains a fresh Consent Preview
that shows the complete new envelope before issuance. A token exchange, Grant
renewal, child derivation, session resume, credential rotation, or idempotent
retry MUST NOT silently trigger representation migration. Existing unexpired
legacy Grants MAY continue under their pinned legacy Passport semantics, but
new Grants using this envelope MUST NOT emit legacy fields. A child of a legacy
Grant remains legacy unless it completes this migration as a distinct issuance
flow. Revocation, expiry, or suspension of the legacy Passport remains binding
during migration and cannot be repaired by representation change.

No migration profile can establish equivalence between different artifacts,
issuers, subjects, keys, or status records merely because their display names
or claimed capabilities match. A profile change, re-signing, reserialization,
key-binding change, artifact byte change, status-reference change, or issuer /
subject change creates a different envelope and requires new issuance and
consent.

### Revocation, Failure, and Privacy

If current lifecycle state is `suspended`, `revoked`, or `expired`, the runtime
MUST stop new launches, every enforcing component MUST reject new work before
idempotency lookup, budget admission, receipt creation, workload creation, or
effect, affected sessions MUST be fenced, and the application MUST apply the
Semantic Grant Revocation Transition to every Grant and descendant bound to the
exact envelope. A different artifact, profile, subject, key, or status reference
does not repair those Grants.

When status is `unknown`, `unavailable`, or stale, enforcement fails closed and
affected sessions remain fenced while resolution is unavailable. A later fresh
`active` result for the same exact envelope MAY restore use without changing
`grant_hash`; no other envelope may be substituted. The public error response
MUST NOT reveal issuer, subject, key, resolver, status reference, trust path, or
which internal verification step failed.

Applications and runtimes SHOULD minimize retention of issuer and subject
labels, artifact locators and digests, key-binding values, capability
inventories, and agent-binding results. Only the stable privacy-safe envelope
is portable. Raw artifacts and signatures, external correlation identifiers,
status responses, resolver credentials, trust paths, executable measurements,
and verifier-local lifecycle records MUST NOT enter agent-visible context,
receipts, traces, events, or logs beyond an explicitly defined privacy-safe
projection. Identity evidence is not a license to correlate the same agent
across applications, users, runtimes, or tenants.

## Minimal Agent Passport Grant-Issuance Profile

Agent Passport is the first concrete format profile for the Pluggable Agent
Identity Evidence Profile. It is not a mandatory ASP identity format. New
Grants using the generic profile carry an `identity_evidence` envelope; the
Passport-specific delegate fields described in this section are the legacy
wire shape retained only for the migration contract above.

This profile defines the minimum Agent Passport evidence that an ASP runtime
and authorization server can consume during Grant issuance. It does not modify
the Agent Passport source specification and does not make every syntactically
valid v1alpha1 document suitable for production authorization.

The consuming profile identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1
```

The exact-artifact hash profile identifier is:

```text
https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1
```

An implementation claims this profile only when it supports both identifiers
and at least one separately named Passport verification profile advertised in
the manifest. The source document's `signature` fields, generic v1alpha1
verification prose, or a schema-validation success are not a concrete
cryptographic verification profile.

### Minimal Source Document

The input MUST be exactly one UTF-8 YAML 1.2 document with one top-level
`passport` mapping and no other top-level member. Before interpreting fields, a
consumer MUST reject duplicate mapping keys, merge keys, aliases, non-core
tags, non-string mapping keys, cyclic data, multiple YAML documents, and values
that cannot be represented in the I-JSON data model. Parsing MUST use a safe,
non-object-constructing YAML implementation.

The source document MUST contain all of these paths:

```text
passport.apiVersion
passport.kind
passport.metadata.name
passport.metadata.uid
passport.metadata.version
passport.metadata.issueDate
passport.metadata.expiryDate
passport.metadata.issuer
passport.spec.entity.type
passport.spec.capabilities
passport.spec.capabilities[].name
passport.spec.capabilities[].signature
passport.signature.algorithm
passport.signature.value
passport.signature.publicKeyRef
```

`passport.apiVersion` MUST be `agent-passport.io/v1alpha1` and
`passport.kind` MUST be `AgentPassport`. Every listed scalar MUST be a non-empty
string. `issueDate` and `expiryDate` MUST be RFC 3339 timestamps; `issueDate`
MUST precede `expiryDate`, and issuance requires
`issueDate <= now < expiryDate` under the verification profile's clock-skew
rules. This profile promotes `expiryDate` from optional in the source draft to
required for ASP Grant issuance.

`spec.capabilities` MUST be an array. Capability names MUST be unique by exact
string equality, and every entry MUST satisfy the source schema for its callable
`signature` object. That object describes parameters and returns; it is not the
Passport's cryptographic signature. An empty capability array can identify an
agent but cannot make an ASP action compatible.

All optional source sections, including resources, security policies,
`agentIntegrity`, signature metadata, and extension fields, remain part of the
retrieved artifact and its cryptographic verification. A consumer MUST NOT drop
unknown fields before signature verification or artifact hashing. An unknown
field has no ASP authority or enforcement semantics unless the selected
verification or integrity profile explicitly defines it.

`metadata.uid` identifies the agent described by the Passport. It is not a
runtime id, OAuth client id, user id, executable hash, or proof that the
currently connected process is that agent.

### Exact Artifact Hash

For a local file, `artifact_octets` is the exact file byte sequence. For a
retrieved representation, it is the exact representation data after transport
framing and content-encoding have been removed and before character decoding,
YAML parsing, newline conversion, or other normalization. The consumer MUST
enforce the advertised `max_artifact_bytes` before buffering or parsing it.

The hash profile computes:

```text
digest = SHA-256(
  UTF8("ASP agent-passport artifact v1") || 0x00 || artifact_octets
)

passport_hash = "sha-256:" || BASE64URL-NOPAD(digest)
```

`BASE64URL-NOPAD` uses the RFC 4648 URL-safe alphabet without `=` padding. The
digest portion is exactly 43 characters decoding to 32 octets; padding,
whitespace, another alphabet, or a different decoded length is invalid.

For the 13 artifact octets consisting of the UTF-8 text `passport: {}` followed
by one LF byte, the result is:

```text
sha-256:218YMarWJ5KKssblgnAdgryNm_8JGmVt4sAkYPeq9Mk
```

This vector exercises only the hash layer; the empty Passport later fails the
minimal source-document checks. Omitting the final LF instead produces
`sha-256:YOwAV1bQimyIkP1UI06EYZRXqi4Eua5DF8yPN-5-EOA`, demonstrating that line
ending normalization is forbidden.

The hash therefore covers the complete artifact, including its top-level
`signature` object, comments, whitespace, YAML presentation choices, and
unknown extensions. It does not parse and reserialize the document. Any byte
change, including re-signing or semantically equivalent YAML reformatting,
produces a different `passport_hash`.

`passport_hash` is an integrity commitment to bytes only. It does not prove a
valid signature, a trusted issuer, current lifecycle status, truthful
capabilities, enforceable policy, or a match to executable code.
`passport_ref` is an optional locator only; recognizing its scheme or fetching
bytes from it is not verification. Redirects, content negotiation, caches, and
local aliases MUST NOT cause a consumer to accept bytes whose exact hash differs
from the Grant-bound value.
An application MUST NOT dereference an arbitrary client-supplied URI. It accepts
only a pre-registered artifact or a locator scheme, origin, redirect policy,
media type, and authentication method explicitly allowed by the selected
verification profile and local SSRF policy.

### Passport Verification Profile

`passport_verification_profile` MUST be a collision-resistant identifier
selected from the applicable manifest entry. Its defining specification MUST
completely define:

- allowed signature algorithms and parameters, with algorithm-confusion and
  downgrade behavior;
- the exact signed byte sequence, including how the top-level `signature`
  object and YAML presentation are handled;
- authenticated `publicKeyRef` resolution, key type checks, issuer-to-key
  binding, trust anchors, key rotation, and historical verification;
- exact issuer identity semantics and any federation or delegation rules;
- signature decoding and verification;
- clock source, accepted skew, issue and expiry validation;
- an authenticated Passport status mechanism, stable status key, response
  binding, freshness, replay handling, and revoked, unknown, and unavailable
  states; and
- fail-closed behavior when keys, trust state, or fresh status cannot be
  obtained.

A profile that leaves any of those items implementation-defined is not usable
for production Grant issuance. In particular, the current Agent Passport
v1alpha1 draft does not itself specify canonical signing bytes, a common trust
store, or an interoperable status protocol. A validator that checks required
fields and base64 syntax but does not cryptographically verify the signature is
schema validation, not Passport verification.

The runtime and authorization server MUST independently support the exact
verification-profile identifier. Neither may substitute a profile with the
same algorithm name, key, issuer, or source `apiVersion`. Status freshness is
mutable verifier state and is not copied into `grant_hash`; every enforcing
component retains the selected profile and checks current status before use.

### Verification and Admission

Verification follows this order:

1. Retrieve no more than `max_artifact_bytes` through an authenticated or
   locally trusted resolution path.
2. Compute the exact-artifact `passport_hash` before parsing and compare it with
   any expected value using a constant-time digest comparison.
3. Perform the safe YAML and minimal source-document checks above.
4. Select the exact consuming, hash, and verification profiles without
   fallback.
5. Resolve an authenticated key, verify the exact signed bytes and issuer trust,
   and reject any algorithm or key mismatch.
6. Validate issue and expiry time and obtain fresh authenticated lifecycle
   status.
7. Treat optional resource, policy, integrity, and extension declarations only
   according to explicitly supported profiles; unsupported declarations do not
   become authority.
8. Extract the unique capability-name set for advisory capability matching.
9. Bind the Passport uid and hash to the runtime-local agent identifier and,
   when claimed, independently verify executable integrity.
10. Derive the Consent Preview and only then request or accept a Grant.

Failure at any step invalidates the admission result. A component MUST NOT keep
a later step's successful result after an earlier binding, trust, time, or
status input changes.

A verifier SHOULD retain a local admission projection such as:

```json
{
  "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
  "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
  "passport_hash": "sha-256:<base64url-digest>",
  "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01",
  "api_version": "agent-passport.io/v1alpha1",
  "uid": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "version": "1.0.0",
  "issuer": "TrustedAgentIssuers Inc.",
  "public_key_ref": "https://issuer.example/keys/passport-key.jwk",
  "issued_at": "2026-07-01T00:00:00Z",
  "expires_at": "2026-08-01T00:00:00Z",
  "status_checked_at": "2026-07-14T10:00:00Z",
  "status_valid_until": "2026-07-14T10:05:00Z",
  "capability_names": ["comment.create", "pull_request.get"],
  "agent_binding": "document_only"
}
```

This is verifier-local state, not a portable Grant member or attestation. Raw
artifacts, external issuer subjects, key-resolution credentials, and status
responses MUST NOT be copied into an Agent Grant, receipt, event, trace, or
agent-visible context.
`status_valid_until` MUST be no later than Passport expiry, key-validity expiry,
or the selected status profile's maximum freshness deadline.

`agent_binding` is `document_only` unless a separately named integrity profile
has verified a complete, unambiguous mapping from the Passport to the executable
artifacts actually launched under the local agent identifier. A present
`agentIntegrity.codeHashes` array or one matching file is insufficient by
itself: the integrity profile must define path roots, algorithm and encoding,
required artifact inventory, symlink and file-replacement behavior, measurement
time, and failure semantics. When all of those checks succeed, the local value
MAY be `code_hash_verified` and MUST also retain the integrity-profile
identifier. The authorization server MUST NOT present a runtime-local
`code_hash_verified` value as application-verified evidence unless it has a
separate attestation profile that proves that claim.

### Legacy Passport Grant Binding

When this concrete Passport format is carried by the generic envelope, its
verified issuer, uid-derived subject, artifact digest, key binding, freshness,
and status projection follow the Pluggable Agent Identity Evidence Profile; no
Passport-specific delegate field is emitted. The remainder of this subsection
defines only the legacy wire shape accepted for existing Grants and explicit
migration.

A legacy semantic Grant request's `delegate` contains:

```json
{
  "runtime": "application_runtime_456",
  "agent": "local_agent_789",
  "passport_ref": "agent-passport://local-agent",
  "passport_profile": "https://github.com/0al-spec/agent-surface/profiles/agent-passport-minimal/v1",
  "passport_hash_profile": "https://github.com/0al-spec/agent-surface/hash/agent-passport-artifact/v1",
  "passport_hash": "sha-256:<base64url-digest>",
  "passport_verification_profile": "https://example.com/profiles/agent-passport-verification/2026-01"
}
```

`passport_profile`, `passport_hash_profile`, `passport_hash`, and
`passport_verification_profile` are REQUIRED and form one exact tuple.
`passport_ref` remains optional. The runtime supplies only values from its
successful local verification. The authorization server independently obtains
the exact artifact, recomputes the hash, verifies the selected profile and fresh
status, and binds its app-scoped `delegate.agent` record to the verified
Passport uid. It MUST NOT accept the runtime's admission projection as a
substitute for those checks.
When `passport_ref` is absent, the authorization server MUST already possess an
authenticated registration for the exact artifact hash and profile tuple; the
authorization request does not carry raw Passport bytes.

`credential_binding` MUST repeat all four required Passport tuple values. The
complete delegate and credential-binding copies are included in `grant_hash`
and MUST remain exact in Rich Authorization Request results, token exchange,
introspection, sessions, child Grants for the same agent, and action
verification. Any missing or mismatched copy is `integrity_mismatch`.

The local and grant-issuer consent views MUST display the profile identifiers,
artifact hash, Passport name, uid, version, issuer, expiration, status freshness,
capability names relevant to the requested actions, and whether executable
binding is `document_only`, locally `code_hash_verified`, or unavailable. Local
integrity and operator claims MUST be labeled as local evidence. A changed
artifact byte, profile identifier, issuer trust result, lifecycle state,
capability set, agent binding, or executable-integrity result makes the Consent
Preview stale.

Passport capabilities, callable signatures, `accessControl`, resources,
security policies, and extensions are signed declarations and policy evidence.
They can make an action incompatible or add a local restriction, but they MUST
NOT add an action, location, scope, resource, approval bypass, or credential
release to an Agent Grant. A valid Passport signature proves only that the
selected key signed the profile-defined bytes; it does not prove the truth of a
claim or that the runtime is executing the described code.

### Passport Lifecycle and Privacy

The exact Passport tuple and fresh status MUST be checked at issuance, before
storing a returned Grant, during introspection, and before every action. A
status refresh for the same artifact and profile does not change `grant_hash`.
Expiry, revocation, unknown status beyond the profile's freshness window, or a
trust/key invalidation makes the Passport unusable and triggers the failure and
session behavior defined by Agent Identity Evidence Invalid or Unavailable.

Renewal, re-signing, reserialization, an extension change, or any other byte
change creates a new `passport_hash`, invalidates pending previews, and requires
new Grant issuance. An implementation MUST NOT silently replace a Grant-bound
artifact with a semantically similar or newer Passport. An updated
`passport_ref` is also a Grant change when that locator is present in the
authoritative delegate.

Consent and management interfaces SHOULD minimize retention of Passport names,
uids, issuers, capability inventories, and local integrity results. Under the
legacy wire shape, the Grant and its protocol projections contain only the
opaque agent id, optional locator, and four Passport tuple values. Generic
Grants instead carry the privacy-safe envelope projection. Raw artifacts,
signatures, external issuer subjects, status responses, executable paths, and
code hashes remain inside the applicable verifier or runtime boundary.

## Runtime Identity Profile

The base protocol identifies a runtime with the application-scoped
`delegate.runtime` value. Applications that need interoperable information
about how that runtime was authenticated, managed, or deployed MAY additionally
use the Runtime Identity Profile defined here. Its collision-resistant profile
identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1
```

The profile separates five properties that implementations MUST NOT flatten
into one ranked "identity class":

1. the stable application binding for the runtime;
2. the authentication method used for that binding;
3. the runtime's verified management posture;
4. the declared or verified execution locality; and
5. optional assurance results such as hardware-backed attestation.

Authentication, management, locality, and assurance are evidence inputs to
authorization policy. They do not grant actions, locations, scopes, resources,
or approval bypasses. A policy MAY require an exact combination, but this
profile defines no ordering such as SPIFFE being stronger than device
registration or enterprise management implying hardware assurance.

### Runtime Identity Projection

When this profile is selected, the authorization server MUST derive the
following output-only `delegate.runtime_identity` object from its authenticated
runtime record:

```json
{
  "profile": "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1",
  "binding_id": "rbind_01J2D7M2V6Z91Y2R3B4C5D6E7F",
  "claims_revision": 3,
  "authentication": {
    "method": "spiffe",
    "format": "x509_svid"
  },
  "management": {
    "posture": "enterprise_managed",
    "authority_id": "org_7f3a"
  },
  "execution": {
    "locality": "shared_remote",
    "verification": "registered"
  },
  "assurance": []
}
```

`binding_id` MUST be a collision-resistant, opaque, application-and-tenant
scoped identifier. It is immutable and MUST NOT be reassigned to another
runtime identity. `claims_revision` MUST be a positive integer no greater than
`9007199254740991`. It changes only when a material projected claim changes;
ordinary rotation of a short-lived credential with the same verified subject
and projection does not change it.

The authorization server MUST maintain an authoritative record that maps the
pair (`delegate.runtime`, `binding_id`) to the exact external issuer and
subject, current authentication credentials, complete projected object,
revision, and active, suspended, or revoked state. External subjects and raw
credentials are not Grant Object fields. The same `binding_id` MUST NOT be
accepted under another runtime, tenant, or application.

The profile object is closed. `profile`, `binding_id`, `claims_revision`,
`authentication`, `management`, `execution`, and `assurance` are REQUIRED, and
unknown members are forbidden. An extension that adds members or enum values
MUST use a different collision-resistant profile identifier and define its
complete validation and comparison rules.

### Authentication Methods

`authentication.method` is exactly one of `registered_device`, `spiffe`, or
`oidc_workload`. A new method requires a new collision-resistant Runtime
Identity Profile identifier with complete validation rules. One Grant selects
exactly one active authentication binding. A runtime or application MUST NOT
fall back to a different method or subject while retaining the Grant; it
requires renewal and fresh consent.

For `registered_device`, `authentication.format` MUST be `public_key`. The
`authentication` object MUST contain exactly `method` and `format`. The
enrollment procedure MUST bind `delegate.runtime` and `binding_id` to a public
key after proof of possession and explicit confirmation by the authenticated
application account or user. A display name, model, serial number, cookie, or
OAuth Device Authorization Grant alone is not proof of device identity or key
possession. RFC 8628 MAY supply the user interaction for enrollment, but the
application still performs the binding and proof checks. Key rotation preserves
the binding only through an authenticated continuity or recovery procedure;
otherwise the application creates a new `binding_id`.

For `spiffe`, `authentication.format` MUST be `x509_svid` or `jwt_svid`, the
`authentication` object MUST contain exactly `method` and `format`, and the
stable external subject in the authoritative record is the exact SPIFFE ID. An
X.509-SVID validator MUST validate the certificate chain against the applicable
trust-domain bundle, the leaf constraints, and the requirement for exactly one
URI SAN containing the SPIFFE ID. It MUST also authenticate proof of possession
of the corresponding private key through successful mutual TLS at the intended
authorization-server endpoint or through another negotiated profile that binds
a fresh challenge, endpoint context, and selected SPIFFE ID. Merely receiving a
copy of a valid certificate does not authenticate a runtime. A JWT-SVID
validator MUST validate the signature, exact `sub`, narrowly scoped exact
`aud`, and expiration under the applicable trust domain. A JWT-SVID is a bearer
credential and MUST NOT be represented as sender-constrained merely because it
is an SVID. The SPIFFE path is opaque to ASP: an implementation MUST NOT infer
tenant, operator, management posture, locality, or hardware assurance from path
segments or arbitrary claims.

For `oidc_workload`, `authentication.assertion_profile` is REQUIRED and MUST be
a collision-resistant identifier for a concrete workload or client-assertion
profile. The `authentication` object MUST contain exactly `method` and
`assertion_profile` and MUST omit `format`. A generic OpenID Connect ID Token is
defined for End-User authentication and MUST NOT by itself be accepted as
workload identity. The
named assertion profile MUST define trusted issuer or federation-anchor
resolution, allowed signature algorithms, exact `iss`, stable exact `sub`,
narrow exact `aud`, time validation, and replay handling. Email addresses,
display names, and other mutable claims MUST NOT be stable runtime subjects. An
RFC 7523 client assertion or another explicitly profiled workload assertion can
satisfy this method; an arbitrary signed JWT cannot.

The selected runtime authentication key and the Grant Credential
proof-of-possession key are logically separate. They MAY be the same key only
when both profiles permit that use, but implementations MUST NOT assume or infer
that equality.

### Management, Locality, and Assurance

`management.posture` is exactly one of `unmanaged`, `user_managed`,
`enterprise_managed`, `application_managed`, or `third_party_managed`.
`enterprise_managed`, `application_managed`, and `third_party_managed` require
an opaque, application-scoped `authority_id` derived from verified management
evidence. The `management` object MUST contain exactly `posture` and, for those
three values, `authority_id`. `unmanaged` and `user_managed` MUST omit
`authority_id`; self-asserted management labels MUST NOT produce a managed
posture.

`execution.locality` is exactly one of `user_device`, `dedicated_remote`,
`shared_remote`, or `application_embedded`. `execution.verification` is exactly
one of `declared`, `registered`, or `attested`. `declared` cannot satisfy a
policy that requires verified locality. `registered` means only that the
application has recorded and authenticated the locality claim; it is not
continuous attestation. `attested` requires at least one current `assurance`
entry whose named profile explicitly covers execution locality.
The `execution` object MUST contain exactly `locality` and `verification`.

`assurance` is a unique array of objects ordered lexicographically by the UTF-8
values of `type`, then `profile`, then `verifier_id`. An assurance object MUST
contain exactly those three non-empty strings and no raw evidence. The reserved
`hardware_attested` type can appear only when the application has evaluated a
separately negotiated Runtime Attestation Profile that defines the verifier,
evidence format, freshness, reference values, and revocation behavior. SPIFFE,
device registration, an MDM record, a TPM-backed key, or a managed posture alone
MUST NOT produce `hardware_attested`.

### Issuance and Grant Binding

A client selects this profile in a semantic Grant request with the request-only
member:

```json
{
  "delegate": {
    "runtime": "application_runtime_456",
    "runtime_identity_profile": "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1",
    "agent": "local_agent_789",
    "identity_evidence_hash": "sha-256:<base64url-digest>"
  }
}
```

The client MUST NOT supply `delegate.runtime_identity`, `binding_id`,
`claims_revision`, a management posture, locality verification, or assurance.
The authorization server authenticates the runtime, verifies that the requested
profile was advertised, derives the exact projection, removes the request-only
`runtime_identity_profile` selector, and returns `delegate.runtime_identity` in
the authoritative Grant Object. It MUST reject a selector it cannot satisfy;
it MUST NOT silently issue an unprofiled or differently profiled Grant.

When `delegate.runtime_identity` is present, `credential_binding` MUST repeat
its `binding_id` as `runtime_identity_binding_id` and its `claims_revision` as
`runtime_identity_claims_revision`. The server MUST include the complete
projection and both repeated values in `grant_hash`. Returned Rich Authorization
Request details, token-exchange responses, introspection responses, and
server-side session state MUST preserve the exact projection. A mismatch among
those copies is `integrity_mismatch`.

Before issuance, the authorization server MUST verify that the exact
(`delegate.runtime`, `binding_id`) record is active, belongs to the authenticated
client and tenant context, and has the projected revision and claims. It MUST
perform the same current-state check before every protected action. Identity
evidence can deny or constrain a Grant, but the issuer MUST NOT add scopes,
actions, resources, or approval exceptions because a method, posture, locality,
or assurance appears stronger.

A child Grant for the same runtime MAY retain the exact projection subject to
ordinary attenuation. A child Grant that names a different runtime MUST have
that runtime's independently authenticated `runtime_identity`; it MUST NOT copy
the parent runtime's binding, claims, management posture, or assurance.

### Rotation, Suspension, and Revocation

Refreshing a credential, SVID, or assertion for the same verified external
subject and exact projected claims retains `binding_id` and `claims_revision`.
A change of authentication method or external subject creates a new binding. A
change of management posture or authority, locality, verification level, or
assurance creates a new revision at minimum. A material downgrade MUST suspend
affected Grants and sessions until the user completes renewal and fresh
consent; it MUST NOT be treated as a transparent refresh.

Expired or temporarily unavailable identity evidence makes the binding
inactive and causes protected actions and introspection to fail closed. A later
successful refresh for the same subject and projection MAY restore the same
binding and Grant without changing `grant_hash`. Permanent revocation of the
runtime binding MUST reject new actions, fence or cancel affected sessions,
apply the Semantic Grant Revocation Transition to every bound Grant and derived
Grant, and make introspection return `{"active":false}`. Revocation of one
binding MUST NOT affect an unrelated runtime merely because both use the same
authentication method or management authority.

### Runtime Identity Privacy

The Grant, introspection response, receipts, events, traces, consent records,
and ordinary logs MUST NOT contain the external workload subject, raw SVID,
certificate, JWT, MDM record, attestation evidence, device serial, hardware key
handle, or reusable enrollment or recovery material. The application MAY expose
only the app-scoped runtime identifier, opaque binding identifier, sanitized
facets, claims revision, and a user-meaningful operator label derived from its
authenticated local state. A display label is not authority and MUST NOT replace
`authority_id` or another verified machine value.

## Runtime Attestation Optional Profile

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

### Attestation Discovery and Concrete Profiles

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

### Attestation Requirement and Stable Grant Binding

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

### Challenge, Evidence, and Appraisal

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

### Mutable Appraisal State

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

### Attestation Authority, Security, and Privacy

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

## Agent Grant

### Grant Object

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

### Grant Hash

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

### Budget Caveats and Accounting

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

### Grant Lifecycle

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

### Grant Issuance Models

#### Model A: App-Issued Grant

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

#### Model B: Runtime-Held Grant Plus App Token

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

#### Model C: Signed Delegation Object

The grant is a signed object with caveats. It MAY be signed by the app, user,
runtime, enterprise authority, or some combination.

Pros:

- Portable and cryptographically strong.
- Can support offline verification and third-party audit.

Cons:

- Requires a signed-grant profile, trust stores, signer-key lifecycle,
  revocation semantics, and stronger interop work beyond the receipt profile.
- Too large for the first MVP.

### OAuth Grant Lifecycle Profile

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

#### Rich Authorization Request Profile

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

#### OAuth Token Exchange Profile

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

#### Grant Introspection Profile

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

### Grant Credentials and Proof

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

### Subdelegation

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

### Grant Verification

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

## Purpose- and Task-Bound Agent Grant Profile

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

### Purpose Binding Object and Authority Boundary

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

### Issuance, Consent, and Returned Grant

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

### Session and Action Enforcement

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

### Attenuation, Subdelegation, Exchange, and Renewal

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

### Lifecycle, Revocation, Recovery, and Replay

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

### Security and Privacy Requirements

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

## Capability Matching

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

### Semantic Grant Request Hash

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

### Capability Match Result Object

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

### Candidate Status and Reasons

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

### Freshness, Privacy, and Consent Boundary

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

## Session Authority and Lifecycle

An ASP session is a bounded orchestration record for work performed under one
Agent Grant. A session does not mint authority, widen a grant, keep an expired
grant alive, or make an agent a protocol principal. Every session is bound to
exactly one authoritative tuple consisting of:

- the grant `subject.user`, `grant_id`, and `grant_hash`
- the grant-bound `runtime`, `agent`, and `identity_evidence_hash`
- the application `app_id`, `surface_version`, and `surface_hash`
- when selected, the complete exact `constraints.purpose_binding`

The application is authoritative for the application-side session record and
state. The runtime is authoritative for whether the corresponding local worker
is still running, but a local process state MUST NOT cause the application to
accept an action for a session that is absent, interrupted, or terminal in the
application record. The application MUST either assign `session_id` or validate
a caller-proposed value for uniqueness before creating the record. A
`session_id` is a correlation identifier, not a credential, and MUST NOT be
accepted as evidence of the bound user or delegate tuple.

The Portable Replay Bundle Profile can carry exact historical
`session.transition` records for one generation. Such a record remains passive
evidence: loading, validating, or displaying it MUST NOT create, interrupt,
cancel, complete, fail, or resume an application session, and MUST NOT replace
a current authenticated state query.

The application record MUST contain the bound tuple, `session_id`, a positive
integer `session_generation`, the initiating role, the current state, and the
latest transition reason. The initial generation is `1`. Every accepted resume
increments the generation by exactly one. All session-scoped bridge messages,
Action Requests, Action Responses, and receipts MUST carry the current
`session_generation`. The application and runtime MUST reject a message from an
older or future generation rather than copying its generation into local state.

ASP assigns the following authority to session participants:

| Participant | Session authority |
| --- | --- |
| User | MAY request start, observe state, cancel, or approve resume through an authenticated application or runtime UI. A user-facing gesture is not itself a bridge credential. |
| Application | Creates or accepts the authoritative record, verifies every transition and action against the current grant and tuple, exposes an authorized user view, and MAY cancel or interrupt a session to enforce application policy. |
| Runtime | MAY request start for its authenticated grant-bound tuple, observe that tuple's sessions, stop local work, request an application fence for an authoritative local budget or a durable runaway guard, request cancellation, and request resume after interruption. It MUST enforce application state in addition to local policy. |
| Agent | MAY express task intent only through its runtime. It has no direct authority to start, enumerate, observe, cancel, or resume application sessions, and MUST receive session data only through runtime-mediated, exposure-authorized paths. |

An application-started session MUST arise from an authenticated user action or
an application policy that the user authorized independently of the agent. The
application MUST deliver any proposed task through an authorized event path;
it MUST NOT use `session.start` to bypass the Data Exposure Contract. A runtime
MUST identify itself as the initiator for a runtime-originated request and MUST
NOT assert `initiated_by: "user"` merely because it observed a local gesture.
The receiving application derives the authoritative initiating role from its
authenticated context and verified policy evidence.

The normative application-side states and transitions are:

| Current state | Trigger | Next state | Requirements |
| --- | --- | --- | --- |
| absent | accepted start | `active` | Current grant, tuple, surface, authenticated channel, and an available parallel-session slot across the grant lineage all verify; generation becomes `1`. |
| `active` | channel loss, runtime pause, or application safety fence | `interrupted` | New agent work is rejected until an explicit resume succeeds; the closed safety and cleanup path remains available, and the slot is released only after the fence. |
| `interrupted` | accepted resume | `active` | Same tuple, current grant and surface, fresh channel authentication, exact prior generation, and a newly acquired lineage slot; generation increments by one. |
| `active` or `interrupted` | accepted cancel | `cancelled` | Application fences new actions before acknowledging the transition and the runtime stops local work. |
| `active` | successful task completion | `completed` | Runtime reports completion and the application reconciles any outstanding action outcomes. |
| `active` | unrecoverable task failure | `failed` | Runtime or application records a stable reason without treating unknown action outcomes as rolled back. |

`cancelled`, `completed`, and `failed` are terminal. A terminal `session_id`
MUST NOT be resumed or reused for new work. A duplicate request for an already
accepted transition is idempotent only when its session id, prior generation,
target state, bound hashes, and any reason-specific `guard_id` and
`guard_resolution_id` are identical. A conflicting reuse MUST fail as
`session_transition_invalid` and MUST NOT move the session.

When `max_parallel_sessions` is present, the application MUST acquire or
release its occupancy atomically with the authoritative transition. A full
limit leaves a proposed start absent and a proposed resume `interrupted`; it
does not increment generation, expose the occupying sessions, or disturb work
already active under the grant. Credential rotation, reconnect, or a duplicate
transition request MUST NOT allocate another slot or reset lineage occupancy.

An accepted resume does not by itself clear runtime budget or runaway state.
The runtime MUST resolve its own authoritative blocker first. A resumed
generation after channel loss, a budget pause, or another non-runaway
interruption continues the same runaway-guard epoch and counts. A new epoch can
start only after the explicit runaway resolution rules below; historical guard
and event-deduplication records are not rewritten as if the earlier generation
never ran.

When a Purpose Binding record is suspended or current authenticated state is
unavailable, the application MUST fence the affected session before accepting
another action and the runtime MUST stop local work. Resume requires the exact
same purpose and optional task ids and revisions, the same relationship, and a
current active result; it cannot change the binding or revive a terminal
record. Terminal closure follows Semantic Grant Revocation rather than session
resume.

`session.pause`, `session.cancel`, and `session.resume` requests MUST contain
`session_id`, the caller's current `session_generation`, `grant_id`,
`grant_hash`, and `surface_hash`. The channel authenticates the runtime or
application actor; an agent-supplied field inside the payload does not. A
`session.state` response MUST repeat those binding fields, report the
authoritative state and generation, and include a stable transition reason.
Receipt or event transport can record the transition, but neither is authority
to create it.

Cancellation fences future work; it is not a transactional rollback. Before
acknowledging `cancelled`, the application MUST reject new Action Requests for
the session and invalidate unconsumed execution tokens and reservations bound
to it. An already-started irreversible effect retains its Action Response and
receipt outcome, including `unknown` or `partially_applied`; cancellation MUST
NOT rewrite that outcome as if no effect occurred. Cancelling a session does
not by itself revoke its Agent Grant or cancel another session under that grant.

Observation is also scoped authority. The application MAY show a user sessions
for that user's authenticated account. A runtime MAY observe only sessions for
its verified grant-bound tuple. Responses to an unauthorized or mismatched
observer MUST NOT reveal whether a guessed `session_id` exists. An agent can
receive only the current task, authorized event or action data, and state needed
for its local execution; ASP does not grant it a session-list operation.

## Revocation Semantics

The protocol MUST define what happens when authority changes.

Revocation MUST be possible from both sides. The application-managed and
runtime-managed user paths are defined below and converge on the same
authoritative grant transition.

### Active Grant Management

A Surface Publisher used by a Grant Issuer MUST publish an HTTPS
`revocation.grant_management_url` in the manifest used for issuance. The URL
identifies the application's human-facing active-grant management page, not
the RFC 7009 runtime revocation endpoint and not an authority-bearing
capability URL. Its
origin MUST match the manifest issuer origin. The published URL MUST be a
generic issuer-wide entry point shared by all users and grants. It MUST NOT
encode a grant id, token, user id, or other user- or grant-specific sensitive
value in its path, query, fragment, user information, host, or any other URL
component. Selection of a user or grant happens only after authentication from
server-side state, not through the manifest URL.

The application management page is the authoritative user view of current
grant state. It MUST authenticate the resource owner through the application's
ordinary user-authentication mechanism, derive the subject from that session,
and list only grants belonging to that subject. It MUST NOT accept a caller-
supplied subject selector, treat an Agent Grant Credential as user
authentication, or let a runtime or agent enumerate another user's grants.
Responses containing grant details MUST use `Cache-Control: no-store` and
`Referrer-Policy: no-referrer`.

For each active grant, the page MUST make these semantics visible and
inspectable:

- application and issuer, grant id and hash, pinned surface mode, version and
  hash, and authoritative active or expiry state;
- runtime id, agent id, passport hash, and available verified identity labels;
- when Runtime Attestation is selected, its concrete profile, opaque verifier
  id, proof-key binding, sanitized assurance, freshness deadline, and coarse
  current accepted or inactive state without raw Evidence or diagnostics;
- exact actions, scopes, locations, resource filters, expiration, immutable
  budget limits, application-authoritative current budget states, and approval
  caveats;
- maximum effects, execution stages, and recovery limitations;
- effective data-exposure classes, redaction, and retention obligations;
- when selected, the exact Remote Processing Privacy profile, path commitment,
  and deterministic classification ceiling without implying verified provider
  behavior;
- when selected, the exact Agent Training Use Policy profile and permitted and
  prohibited effective classes, shown separately from plaintext retention and
  with no claim that revocation or deletion causes model unlearning;
- when selected, the exact Purpose Binding profile, purpose id and revision,
  optional task id and revision, purpose-only or task-bound mode, current
  coarse active, suspended, terminal, or unavailable state, effective
  expiration, and an authenticated safe issuer label when available;
- credential profile and receipt requirements;
- when Approval Receipt is selected, each action's accepted producer roles and
  maximum approval age without exposing individual approval decisions;
- whether revocation cascades to derived grants and the known number of
  affected descendants.

The summary MUST be derived from the stored authoritative Grant Object and the
exact pinned manifest snapshot that the grant references. It MUST NOT silently
reinterpret an old grant using the current manifest. If the pinned snapshot or
some historical display metadata is unavailable, the page MUST mark those
details unavailable, preserve the stored machine identifiers and hashes, and
still allow immediate revocation. Missing display metadata never makes a grant
look less privileged.

Current runtime-authoritative tool, token, time, and runtime-cost states MAY be
shown only when obtained from a mutually authenticated accounting profile. In
its absence the application page MUST label those current states unavailable;
it MUST NOT derive or estimate them from observed Action Requests. Conversely,
the runtime local view is authoritative only for its runtime-owned dimensions
and MAY show current application-owned states only from authenticated
application accounting or introspection. Both views MUST still show every
immutable limit from the Grant Object.

The page MUST NOT expose Grant Credentials, refresh tokens, cookies, raw
credential-binding material, receipt-signing private material, application
resource content, or passport data beyond what the user needs to identify the
delegate. Every active entry MUST provide a direct inspect-and-revoke path; a
user MUST NOT need the runtime, agent, or an active Grant Credential to use it.

An Application Runtime MUST also provide a local view of the grants and
credentials it stores, including their last known state and the trusted
`grant_management_url`. The application remains authoritative. If the local
view and an authenticated application view or introspection result disagree,
the runtime MUST stop new use, mark its state uncertain or inactive, and
resynchronize rather than treating cached `active` state as authority.

### User Revocation Intent and Confirmation

Before accepting a user-facing revocation, the application MUST show the
current grant using the common grant- and manifest-derived semantics listed in
Active Grant Management. It does not need runtime-local assertions from the
Consent Preview Contract and MUST NOT represent the old preview as portable
consent evidence. The application MUST additionally explain:

- that new actions will stop under this grant and its derived grants;
- which known child grants, sessions, execution tokens, and reservations are
  affected by the cascade;
- that queued or in-flight actions which have not passed the final atomic
  grant-state check will be rejected, while effects irreversibly committed
  before revocation remain authoritative and receiptable;
- that already committed effects are not undone and require separately
  authorized compensation or revert when available; and
- which `delete_on_grant_end` exposure obligations become effective, without
  claiming deletion of application source data or model unlearning.

When Agent Training Use Policy is selected, the confirmation MUST also state
that revocation stops every new training use under the Grant but does not undo
a permitted training use already completed or prove deletion from a reusable
model, adapter, index, dataset, or other derived artifact.

The confirmation MUST be bound server-side to the exact `grant_id` and
`grant_hash` displayed to the user. That binding prevents target substitution;
it is not a fail-open precondition when authority changes concurrently. On
confirmation, the application MUST atomically freeze new use of the displayed
grant and every derived, renewed, exchanged, or superseding grant that preserves
its delegation lineage, then apply the Semantic Grant Revocation Transition.
New lineage members discovered during that transition are included in the
cascade. The application MUST show updated impact after authority has stopped,
but MUST NOT keep the lineage active while waiting for another confirmation.
An unrelated grant with a different lineage is never silently included and
requires its own user action. The user cannot disable the required cascade or
select only one credential of the semantic grant.

The management action uses the ordinary authenticated user session, not an
Agent Grant Credential. Implementations MUST apply their normal protections
against CSRF, clickjacking, session fixation, and confused-account actions, and
SHOULD require recent or step-up user authentication when local risk policy
warrants it. A missing grant and a grant belonging to another subject MUST
produce the same non-enumerating user-visible result.

User-facing revocation invokes the transport-neutral Semantic Grant Revocation
Transition; it is not a second authority mechanism.
Repeating an already confirmed request for the same grant state is idempotent
and MUST NOT repeat cascade side effects or emit duplicate control events.

### Revocation Timing and Concurrency

Revocation is logically immediate: before the application presents success to
the user, authoritative grant state MUST already be inactive and every
application enforcement point MUST reject a newly linearized action under the
grant. The application records an `effective_at` instant for that transition
and a `confirmed_at` instant for the user-visible success;
`confirmed_at` MUST NOT precede `effective_at`.

For a state-changing action, the effect linearization point is the final
authoritative grant-state check performed atomically with the first irreversible
application mutation or external-effect dispatch. Queued or in-flight work that
has not crossed that point before `effective_at` MUST be cancelled or fail as
`grant_revoked`. Work that crossed it before `effective_at` MAY finish only the
consequences already irreversibly committed at that point and MUST receipt its
actual outcome; it MUST NOT initiate another effect afterward without a new
current grant check. An implementation that cannot fence its effect dispatch
against revocation MUST NOT confirm success until the fence is established.
Cached introspection, an in-flight session, or an outstanding execution token
or reservation cannot move this boundary.

After success, the authenticated management page MUST provide read-your-writes
behavior: the grant MUST no longer appear active, and its detail view MUST show
the authoritative revoked state and `effective_at`. Event delivery, runtime
notification, session cleanup, credential deletion, and exposure-retention
cleanup MAY finish asynchronously, but none is the enforcement transition or a
precondition for success confirmation.

If the application cannot confirm the authoritative transition, it MUST show
revocation as unconfirmed and MUST NOT claim success. A runtime that initiates
revocation locally MUST stop new actions as soon as the user confirms intent;
on timeout or a binding-specific unavailable response it keeps the credential
frozen, labels confirmation as unknown, and retries or resynchronizes according
to the selected authenticated revocation binding. For OAuth, HTTP 503 and
`Retry-After` provide that signal. `pending` or `confirmation_unknown` are local
presentation states, not active-grant authority states.

This specification intentionally defines no universal wall-clock UI deadline.
Deployment latency is an operational SLO; the interoperable security invariant
is that application-side invalidation precedes success confirmation and later
authorization decisions observe it. Delivery of `grant.revoked` is notification,
not user confirmation, and loss of the event never reactivates a grant.

### Semantic Grant Revocation Transition

Every issuance and transport binding uses one transport-neutral semantic
transition. For a located active grant, the application MUST atomically mark the
grant inactive, reject every credential derived from it, invalidate refresh
tokens and proof-bound sessions, invalidate outstanding execution tokens and
reservations, and cascade revocation to child, exchanged, renewed, or
superseding grants whose authority preserves its delegation lineage. The
transition establishes `effective_at` and the concurrency fence defined above.

When a Purpose Binding purpose becomes terminal, the Grant Issuer MUST invoke
this transition for every Grant bound to that exact purpose and every
descendant. When only a task becomes terminal, it invokes the transition for
the exact task-bound Grants and their descendants without revoking sibling
tasks or independently consented lineages. A purpose-only Grant can remain
active for other work that current purpose policy permits. Suspension or
temporary status unavailability fences sessions and actions as defined by the
profile but is not falsely recorded as terminal revocation.

The transition is idempotent. Reapplying it to an inactive grant MUST NOT emit
duplicate control events, repeat cleanup side effects, or change the original
effective instant. It does not erase receipts or undo committed effects.
Transport profiles define how a runtime or user authenticates a request and how
success is represented; they MUST NOT weaken this inactive state, cascade, or
timing boundary. A non-OAuth issuance model claiming Grant Issuer Profile
conformance MUST define an authenticated revocation binding that invokes this
same transition.

### OAuth Grant Revocation Profile

The manifest `agent_api.grant_revocation_url` MAY identify the same endpoint as
`auth.revocation_url`. When it does, a runtime requests revocation using RFC
7009: an authenticated form-encoded `POST` containing the Grant Credential in
the required `token` parameter and, optionally, an `access_token`
`token_type_hint`.

The endpoint MUST authenticate the runtime client and, for a credential it can
locate, verify that the credential was issued to that client. A successful
request and a request containing an unknown or already invalid credential both
return HTTP 200 with no response body, as required by RFC 7009. The runtime MUST
stop using the credential after that response. An HTTP 503 response means
revocation is not confirmed; the runtime MUST continue treating the credential
as sensitive, MUST NOT initiate new actions with it, and SHOULD retry according
to `Retry-After`.

For the Agent Grant profile, a successful request for a located credential MUST
invoke the Semantic Grant Revocation Transition for the semantic Agent Grant,
not only that token. A user-facing request invokes the same transition through
Active Grant Management and its confirmation and timing requirements.

When an active grant changes to revoked and the manifest declares an event
subscription endpoint, the application MUST emit a `grant.revoked` control event
with this minimum envelope:

```json
{
  "specversion": "1.0",
  "id": "event_01J2ABCDEF",
  "source": "https://code.example.com",
  "type": "grant.revoked",
  "time": "2026-06-25T18:30:00Z",
  "datacontenttype": "application/json",
  "dataschema": "https://code.example.com/schemas/grant-revoked.event.schema.json",
  "aspcontrol": true,
  "aspaudience": "application_runtime_456",
  "aspsurfacehash": "sha-256:<base64url-digest>",
  "aspeventhash": "sha-256:<event-digest>",
  "aspsubid": "control_application_runtime_456",
  "aspdeliveryid": "delivery_01J2REVOKED",
  "aspattempt": 1,
  "aspstream": "runtime:application_runtime_456",
  "aspsequence": 7,
  "aspcursor": "opaque:control-position-after-7",
  "data": {
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "app_id": "code.example.com",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "identity_evidence_hash": "sha-256:<base64url-digest>",
    "revoked_at": "2026-06-25T18:30:00Z",
    "effective_at": "2026-06-25T18:30:00Z",
    "reason": "user_revoked",
    "parent_grant_id": null,
    "cascade": true
  }
}
```

The event MUST satisfy the CloudEvents 1.0.2 Event Binding and control-event
extension rules. `source` is the manifest issuer, `time` is the revocation
occurrence time, `aspaudience` identifies the target runtime, and
`aspsurfacehash` identifies the retained manifest snapshot. `data` MUST contain
`grant_id`, `grant_hash`, `app_id`, `runtime_id`, `agent_id`, `identity_evidence_hash`,
`revoked_at`, `effective_at`, `reason`, and `cascade`; `parent_grant_id` is
REQUIRED for a child grant and otherwise MAY be null. `data.runtime_id` MUST
equal `aspaudience`. Defined reason values are `user_revoked`, `application_revoked`,
`runtime_revoked`, `credential_compromise`, `parent_revoked`, `policy_changed`,
`purpose_closed`, `task_closed`, and `superseded`. `purpose_closed` and
`task_closed` indicate the terminal Purpose Binding transitions defined by
that profile and reveal no record identifier beyond the Grant the runtime
already possesses. A runtime MUST still enforce revocation when it receives an
unknown future reason value and MAY preserve that value as opaque audit data.

The event MUST be delivered over an application-authenticated event channel
bound to the manifest issuer and target runtime. The runtime MUST verify
`source`, `aspaudience`, tuple binding, and channel authenticity before acting on
it. Delivery of this control event MUST use event-channel authority independent
of the revoked grant and MUST disclose no more grant data than the target
runtime already possessed. Under the Event Delivery Semantics profile it is
carried in `event.delivery` on the logically separate control subscription and
retains the same event and delivery identity across retries. A future signing
profile MAY additionally define an application signature for portable event
verification.

The runtime MUST compare `data.grant_hash` and `aspsurfacehash` with its retained
grant and manifest snapshot. If an authenticated event matches the stored
`grant_id` and delegate tuple but either hash differs, the runtime MUST fail
closed: mark the stored grant inactive, record `integrity_mismatch`, and
resynchronize authoritative state. It MUST NOT replace its stored hash
projections from the event, but it also MUST NOT ignore the revocation and keep
using the grant.

After accepting the event, the runtime MUST atomically mark the grant inactive,
discard cached active introspection state, stop new actions and credential use,
discard cached execution tokens and reservation state, cancel or downgrade
affected sessions according to app policy, cascade the state to locally tracked
child grants, and record a runtime receipt. Event processing is idempotent by
`source` and `id`, while transport retry is deduplicated by `aspsubid` and
`aspdeliveryid`. A duplicate event MUST NOT create duplicate receipts or repeat
external side effects. The runtime terminally acknowledges the control delivery
only after this fail-closed transition or authoritative resynchronization has
begun.

The event is notification, not the enforcement mechanism. The application MUST
reject the revoked grant immediately even if delivery is delayed or lost. A
runtime that misses the event learns the inactive state from introspection or a
rejected action. General event ordering, acknowledgement, replay cursor,
retention, and backpressure follow Event Delivery Semantics. Loss or expiry of
the control delivery never reactivates the grant.

### Grant Revoked

If a grant is revoked:

- runtime MUST stop initiating new actions under that grant
- app MUST reject new actions under that grant
- app MUST invalidate outstanding execution tokens and active reservations
  bound to that grant
- active sessions SHOULD be cancelled or downgraded to read-only according to
  app policy
- receipt generation SHOULD record the revocation event
- when the manifest declares an event subscription endpoint, the app MUST emit
  `grant.revoked` on the runtime control subscription according to the OAuth
  Grant Revocation Profile; closing the affected grant's non-control
  subscription MUST NOT close or suppress that control path

### Runtime Disconnected

If the runtime disconnects:

- when the app detects loss of the authenticated runtime channel, it MUST mark
  sessions bound to that channel as `interrupted` before accepting an action on
  a replacement channel
- app MUST NOT treat pending runtime approvals as approved
- app MUST apply each acquisition declaration's `disconnect_behavior`; a
  retained reservation remains bounded by its existing expiry and MUST NOT be
  consumed until the same tuple reconnects with a current Grant Credential and
  required proof
- app MAY accept `session.resume` only for an `interrupted` session when the
  same tuple reconnects with a current Grant Credential, matching surface, exact
  prior generation, and required proof; acceptance increments the generation
- a reconnect or local worker restart by itself MUST NOT reactivate a session
- unacknowledged event deliveries remain pending subject to retention and are
  retried with their original identities after the runtime restores the same
  subscription or requests replay from its last durable cursor

### Agent Identity Evidence Invalid or Unavailable

If the exact Grant-bound identity evidence becomes suspended, revoked,
expired, trust-invalid, key-invalid, or no longer bound to the selected agent:

- runtime MUST stop launching that agent for new sessions
- runtime and application MUST reject new actions before idempotency lookup,
  budget admission, receipt creation, or effect
- runtime and application MUST fence or cancel active sessions rather than let
  policy silently complete under invalid evidence
- application MUST apply the Semantic Grant Revocation Transition to every Grant
  and derived Grant bound to the exact identity-evidence envelope

When fresh authenticated status is `unknown`, `unavailable`, or stale but the
evidence is not known to be invalid, enforcing components MUST fail closed and
fence affected sessions while status is unresolved. A later fresh `active`
result for the same exact envelope MAY restore use without changing
`grant_hash`; an implementation MUST NOT substitute another format, artifact,
issuer, subject, key binding, status reference, or profile. Legacy Grants using
the Passport-specific tuple follow the equivalent rules in the Minimal Agent
Passport Grant-Issuance Profile.

### Surface Version Changed

If the Agent Surface changes incompatibly:

- app SHOULD publish a new `surface_version`
- runtime SHOULD re-fetch and re-validate schemas
- app MUST invalidate execution tokens and reservations bound to an
  incompatible old action declaration
- grants bound to incompatible actions SHOULD require renewal

### User Session Expired

If the user's ordinary app session expires, app policy decides whether existing
agent grants continue. High-risk grants SHOULD expire with or before the user
session unless explicitly configured otherwise. If policy ends the grant or
session, the app MUST cancel the affected ASP sessions and fence new actions.
If policy allows them to continue, the ordinary login expiry does not change the
ASP session generation. A later user login MAY observe or cancel those sessions
only after authenticating the same application subject; it is not session-resume
authority for a runtime with a different tuple.
