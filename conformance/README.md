# ASP Conformance Suite

This directory contains the versioned, declarative Agent Surface Protocol
conformance catalog. Version 1 targets `agent-surface/0.1` and the six role
profiles defined by the RFC. The catalog is test evidence infrastructure; it is
not a Grant, credential, attestation, certification, trust anchor, or authority
object.

## Version 1 artifacts

`conformance/v1/suite.json` is the authoritative role, feature, requirement,
and vector matrix. `conformance/v1/vectors.json` contains the closed
declarative scenarios. `conformance/v1/fixtures.json` binds every scenario to
one exact semantic baseline and one closed mutation patch.
`conformance/v1/schema-cases.json` carries 40 executable positive and negative
cases for the Operational Limits declaration, capacity-error envelope, and
Human Elicitation messages. Human cases use their RFC 8785-compatible parser;
`ASP-SC-HE-002` exercises binary64 and UTF-16 member-order hash boundaries,
while `ASP-SC-HE-102` rejects negative zero. The adjacent JSON Schemas define
those protocol objects and the catalog, fixtures, subject, observation, and
report wire shapes.

HTTP capacity vectors keep the common capacity envelope in
`operational.capacity_response` and represent only the parsed transport facts
in an optional closed `transport` fixture section. That normalized projection
selects the authenticated HTTP path, status, parsed `no-store` result, and
parsed `Retry-After` form. It is test input for adapters and probes, not a JSON
encoding of an HTTP response or a new ASP wire object.

ASP-over-AHP vectors similarly use an optional closed `ahp` fixture section as
a normalized harness projection, not as an AHP wire format. It binds the
negotiated profile and authenticated carrier, monotonic AHP representation
revision, presentation control, and the complete ASP session/grant/surface/action
tuple. The vectors reject tuple substitution, conflicting revision replay,
profile downgrade, unauthenticated carriage, action substitution, and any
attempt to treat AHP receipt presentation as ASP authority.

Human Elicitation vectors use the standalone closed
`human-elicitation.schema.json` wire schema plus an optional closed
`elicitation` fixture section. The fixture pairs the exact request and response
with authenticated participant identities, current authority tuple, immutable
replay state and terminal acceptance time, candidate validation, authoritative
step-up result, authenticated subject, and secret-material state. It is harness
evidence, not a UI format. Runtime Mediator rows cover clarification, closed
option selection, externally verified step-up, and exact retained terminal
replay; Action Executor rows cover edit and JSON-redline rebinding. No row lets
an elicitation implicitly approve or dispatch an action.

Each run evaluates one exact profile for one named deployment boundary. A
product that implements several profiles runs and reports each profile
independently. A Receipt Producer run additionally names exactly one
`producer_role`, `application` or `runtime`. Counterparts used by an interop
scenario are fixtures or separately identified implementations; their presence
does not give them, or the target, another role claim.

## Digest domains

All digests use SHA-256 and the text representation
`sha-256:<base64url-without-padding>`. The single `catalog_sha256` digest uses
the exact RFC-defined `ASP-CONFORMANCE-CATALOG-V1` domain. Hash the ASCII domain
string, one zero octet, and then each of these fourteen canonical repo-relative
paths in lexicographic order:

1. `conformance/v1/capacity-error.schema.json`
2. `conformance/v1/fixtures.json`
3. `conformance/v1/fixtures.schema.json`
4. `conformance/v1/human-elicitation.schema.json`
5. `conformance/v1/observation.schema.json`
6. `conformance/v1/operational-limits.schema.json`
7. `conformance/v1/report.schema.json`
8. `conformance/v1/schema-cases.json`
9. `conformance/v1/schema-cases.schema.json`
10. `conformance/v1/subject.schema.json`
11. `conformance/v1/suite.json`
12. `conformance/v1/suite.schema.json`
13. `conformance/v1/vectors.json`
14. `conformance/v1/vectors.schema.json`

For each file, hash its path as UTF-8, a zero octet, its exact raw bytes, and a
final zero octet. No newline, whitespace, Unicode, or JSON member-order
normalization is performed.

`specification_sha256` hashes the ASCII domain
`ASP-SPECIFICATION-SOURCE-V1`, a zero octet, and the exact raw bytes of
`drafts/agent-surface.md`.

A per-vector `vector_sha256` hashes the ASCII domain
`ASP-CONFORMANCE-VECTOR-V1`, a zero octet, and the UTF-8 encoding of the RFC
8785 JCS serialization of the complete vector object selected from the
`vectors` array. The surrounding catalog and array position are not part of
that digest.

Each observation carries `subject_sha256`, computed from the ASCII domain
`ASP-CONFORMANCE-SUBJECT-V1`, a zero octet, and the RFC 8785 JCS serialization
of the complete subject object, including counterpart bindings. It also carries
the exact `run_id`; changing the report's subject or run invalidates the
observation binding.

Counterpart entries use `ASP-CONFORMANCE-COUNTERPART-V1`; the complete runner,
adapter, probe, artifact-digest, and environment object uses
`ASP-CONFORMANCE-HARNESS-V1`. The canonical runner entry point and configured
adapter and probe entry points are byte-hashed under
`ASP-CONFORMANCE-RUNNER-V1`, `ASP-CONFORMANCE-ADAPTER-V1`, and
`ASP-CONFORMANCE-PROBE-V1`, respectively. Every domain is followed by one zero
octet before its RFC 8785 object or raw entry-point bytes.

- `artifact_sha256` and `configuration_sha256` bind the subject or counterpart
  implementation and effective test configuration. They do not attest to what
  those bytes execute.
- `evidence_sha256` may bind separately retained evidence. Evidence bytes are
  outside the report and MUST NOT be fetched automatically from an
  observation.

A report is valid only for the exact combined catalog, RFC bytes, vector
objects, subject artifact, and configuration named by its digests. Digest
equality proves byte identity only.

## Requirement and applicability rules

Requirement identifiers are stable and MUST NOT be reused for another
obligation. Each requirement points to a normative RFC anchor and lists every
vector that exercises it. Each vector reciprocally lists its requirement
identifiers. Catalog validation fails on a missing reference, a duplicate
identifier, an empty mapping, or a non-reciprocal mapping.

Applicability is deliberately closed:

- `always` applies to every run of the named role profile;
- `feature` applies only when that exact registered feature is in the subject
  scope; and
- `producer_role` applies only to the matching Receipt Producer role.

An optional feature is not applicable only when it is absent from the declared
scope and the target does not advertise, select, accept, invoke, or produce it
during the run. An observed undeclared feature is a scope failure. An unknown
profile, feature, requirement, vector, operation, input variant, observation,
state, error, or verdict invalidates the run rather than becoming a skip.

## Declarative adapter and probe protocols

The catalog never embeds an executable, shell command, script, callback, or
network location. A runner supplies separately configured stimulus and probe
executables and uses this deterministic exchange:

1. Validate all catalog files and their semantic cross-references before
   contacting the target.
2. Ask the probe for an observed feature inventory and require it to equal the
   subject's complete declared scope.
3. Select one subject profile and derive applicability, including uncovered
   selected features, from the matrix and optional Receipt Producer role.
4. Reset or namespace target and probe state to the run and vector identifiers.
5. Resolve the vector to its digest-bound baseline fixture and closed mutation.
6. Send only that setup and stimulus view to the adapter. Expected errors,
   reason codes, tokens, and state deltas remain private to the runner.
7. Ask the separate probe for sanitized observations and requested state names,
   without disclosing expected values.
8. Compare the exact observed token set, namespaced error/reason values, and
   every before/after state value.
9. Emit one result and one observation for every completed applicable vector.

Adapters translate catalog fixtures to an implementation API. Probes observe
the resulting authoritative state independently. They MUST NOT reinterpret a
token, apply an unregistered default, execute catalog-provided text, or
synthesize missing authoritative state. If a required state cannot be observed,
the vector result is `error` and the suite verdict is `incomplete`.

The configured adapter and probe are trusted test components, not sandboxed
untrusted code. The reference runner gives each invocation a fresh working
directory, a minimal environment, a process-group timeout, file-size,
file-descriptor, and CPU limits, and bounded captured output, but it does not
block filesystem or network access. Operators MUST isolate the harness and
subject at the deployment
boundary appropriate to their risk model.

A negative vector references a valid positive baseline. It changes only the
named input variant and fixture state. Passing a negative vector requires both
the expected rejection and all fail-closed postconditions. Merely returning the
expected error is insufficient. In particular, a runner verifies that
forbidden effects, dispatch, budget reservations or charges, idempotency
mutation, credential release, fabricated evidence, and blind retries did not
occur. Denial receipts are expected only where the vector explicitly requires
them.

The HTTP Capacity Error Binding rows use new stable vector identifiers rather
than adding assertions to the transport-neutral recovery vectors. Producer
cases derive `429` or `503`, `no-store`, and optional `Retry-After` observations
from the ASP envelope. Consumer cases reject a wrong status, missing
`no-store`, mismatched `delay-seconds`, or the HTTP-date form on `429` before
releasing local slots or entering the retry state machine.

The ASP-over-AHP rows keep AHP presentation state separate from ASP authority.
Runtime Mediator cases validate and present UI state without dispatching an
action. Agent Adapter cases translate exactly one bound AHP control into the
already-authorized ASP action. Every invalid binding is fenced before UI update
or request forwarding and leaves the ASP state unchanged.

The Human Elicitation rows keep human input separate from approval and effect
authority. They validate RFC 8785 message hashes (including binary64 values and
UTF-16 member ordering), distinct requester/presenter roles, exact
session/Grant/surface bindings, selected-profile and retained terminal replay
state, closed options, bounded clarification, verifier-bound step-up freshness,
authoritative edit schemas and editable paths, and redline patch/base/result
bindings. Clarification `max_bytes` is measured over the RFC 8785 UTF-8 answer,
and step-up freshness is evaluated against the authoritative evaluation time
and exact verified result projection. Replay retention starts at the persisted
`terminal_accepted_at`, not at response construction. Agent Adapter rows
additionally prove that only a
presenter-originated, purpose-bound minimized answer reaches the agent; an
agent-originated resolution, full step-up response, or authentication secret is
suppressed. Invalid responses leave proposal, approval, dispatch, effect,
credential, and receipt state unchanged.

## Verdict computation

Vector results are `pass`, `fail`, or `error`:

- `pass` means every required observation and state delta matched, no forbidden
  observation occurred, and any expected ASP error matched exactly;
- `fail` means observable target behavior contradicted at least one assertion;
  and
- `error` means the harness, adapter, fixture, authoritative probe, or target
  availability did not permit a complete assertion.

The runner computes `suite_verdict` rather than trusting the stored summary:

1. Any applicable `fail` produces `fail`.
2. Otherwise, any missing applicable vector, `error`, uncovered selected
   feature, suite-fixture subject, digest mismatch, unresolved applicability,
   missing observation, or invalid catalog/report produces `incomplete`.
3. Only one successful result for every applicable vector, with every
   non-applicable vector justified by feature or producer-role mismatch,
   produces `pass`.

A passing report means only that the exact pinned suite scenarios passed for
the exact subject boundary. It MUST NOT contain or imply `conformant: true`.
The report's required `claim_effect` value, `descriptive_only`, makes this
boundary explicit.

Repository self-test subjects have `subject_kind: suite_fixture`; even when
every vector assertion matches, their suite verdict is always `incomplete`
and cannot be reused as implementation evidence.

## Security and privacy

Runs use synthetic fixtures and privacy-minimized probes. Reports and
observations MUST NOT contain Grant Credentials, refresh tokens, cookies,
private keys, raw execution tokens, raw Runtime Attestation Evidence, hidden
policy text, user content, tenant data, or unsanitized logs. Identifiers in
catalog artifacts are test tokens, not production identifiers.

Catalog and report parsers reject duplicate JSON keys, non-I-JSON values,
unknown members, and digest mismatches. Their version 1 wire shapes have no
extension members. The protocol capacity-error envelope remains open as the
Error Model requires; the executable subset validates its standard members and
safe `limit_id` binding, but cannot certify the semantic privacy of arbitrary
extension content. Report signatures, if a later profile defines them, can
authenticate report bytes but cannot turn a self-test into protocol authority
or current-state evidence.
