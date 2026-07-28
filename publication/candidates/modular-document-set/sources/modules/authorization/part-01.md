# Pluggable Agent Identity Evidence Profile

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

## Discovery and Exact Profile Selection

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

## Agent Identity Evidence Envelope

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

## Verification and Mutable Lifecycle State

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

## Grant, Credential, Consent, and Projection Binding

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

## Migration and Legacy Passport Wire Shape

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

## Revocation, Failure, and Privacy

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

# Minimal Agent Passport Grant-Issuance Profile

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

## Minimal Source Document

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

## Exact Artifact Hash

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

## Passport Verification Profile

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

## Verification and Admission

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

## Legacy Passport Grant Binding

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

## Passport Lifecycle and Privacy

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

# Runtime Identity Profile

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

## Runtime Identity Projection

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

## Authentication Methods

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

## Management, Locality, and Assurance

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

## Issuance and Grant Binding

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

## Rotation, Suspension, and Revocation

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

## Runtime Identity Privacy

The Grant, introspection response, receipts, events, traces, consent records,
and ordinary logs MUST NOT contain the external workload subject, raw SVID,
certificate, JWT, MDM record, attestation evidence, device serial, hardware key
handle, or reusable enrollment or recovery material. The application MAY expose
only the app-scoped runtime identifier, opaque binding identifier, sanitized
facets, claims revision, and a user-meaningful operator label derived from its
authenticated local state. A display label is not authority and MUST NOT replace
`authority_id` or another verified machine value.
