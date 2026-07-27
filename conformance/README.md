# ASP Conformance Suite

This directory contains the versioned, declarative Agent Surface Protocol
conformance catalog. Version 1 targets `agent-surface/0.1` and the six role
profiles defined by the RFC. The catalog is test evidence infrastructure; it is
not a Grant, credential, attestation, certification, trust anchor, or authority
object.

## Version 1 artifacts

`conformance/v1/suite.json` is the authoritative Suite 1.10.0 role, feature,
requirement, and vector matrix: six profiles, 55 requirements, and 183 closed
declarative scenarios. `conformance/v1/fixtures.json` resolves them through 48
exact semantic baselines and 128 closed mutation patches.
`conformance/v1/bundles.json` defines eight non-linear adoption bundles as
closed plans over those existing role requirements and vectors; its schema and
semantic validator reject omitted unconditional requirements, unsupported
role-feature pairs, missing vectors, duplicate claims, and non-canonical order.
`conformance/v1/schema-cases.json` carries executable positive and negative
cases for the Operational Limits declaration, capacity-error envelope, Human
Elicitation messages, Impact Simulation results, Risk Explanation hints, and
the ASP-over-MCP wire binding, and the Purpose- and Task-Bound Agent Grant
binding.
Human cases use their RFC
8785-compatible parser;
`ASP-SC-HE-002` exercises binary64 and UTF-16 member-order hash boundaries,
`ASP-SC-HE-102` rejects negative zero, and `ASP-SC-HE-103` rejects a
hash-consistent embedded schema that uses an external `$dynamicRef`. The
adjacent JSON Schemas define those protocol objects and the catalog, fixtures,
subject, observation, and report wire shapes.

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

ASP-over-MCP vectors use the closed `mcp-binding.schema.json` wire schema and
an optional closed `mcp` fixture section as a normalized harness projection.
The binding pins MCP `2025-11-25`, Streamable HTTP, the negotiated experimental
capability, the manifest-selected endpoint, the authorized manifest resource,
and deterministic action-to-tool mappings. Runtime and application rows derive
the complete ASP request tuple independently, keep Grant Credentials and
execution tokens outside agent-visible MCP data, validate typed structured
results and their deep-equal text representation, and link receipt resources
to the exact result. Binding errors remain MCP transport errors; ASP action and
capacity failures remain closed tool results. Session loss, authenticated
termination, safe resume, exact completed replay, schema rotation, advisory
cancellation, and Grant issuance are tested without treating MCP sessions,
OAuth tokens, annotations, progress, resource links, or receipts as ASP
authority.

Purpose Binding vectors use the closed
`purpose-task-bound-grant.schema.json` object and a normalized
`purpose_binding` fixture projection. The wire object contains only the exact
opaque purpose reference and optional task reference; authenticated namespace,
current lifecycle, parent relationship, policy, expiry, consent, returned
Grant, and session facts remain harness-side authoritative inputs. Surface
Publisher, Grant Issuer, Action Executor, and Runtime Mediator rows reject
incomplete advertisement, cross-purpose task substitution, returned or session
drift, widening, unavailable or suspended state, terminal closure, policy
denial, missing lifecycle linkage, and attempts to use task goal prose as
authority. Action checks happen before idempotency, budget, capacity, receipt,
workload, or effect admission, while terminal Action Request replay is rejected
without rewriting historical receipt evidence.

Receipt resources are checked through the bounded `asp-replay
validate-receipts` API for their closed producer shape, hashes, participant and
invocation tuple, approval links, and receipt-local semantics. Its report
deliberately states `signatures_verified: false`; it does not establish a
signature, trusted chain head, unresolved parent-chain completeness, or
producer authority. The binding checker separately requires authoritative
result, error, output, effect, and resource expectations and rejects any
receipt substitution before exposing an action result. Because this bounded
oracle has no authoritative extension reason-code registry, it accepts only
the base Policy Decision reason/outcome pairs and fails closed for extension
reason codes.

Human Elicitation vectors use the standalone closed
`human-elicitation.schema.json` wire schema plus an optional closed
`elicitation` fixture section. The fixture pairs the exact request and response
with authenticated participant identities, current authority tuple, immutable
replay state and terminal acceptance time, candidate validation, authoritative
step-up result, authenticated subject, and secret-material state. It is harness
evidence, not a UI format. Runtime Mediator rows cover clarification, closed
option selection, externally verified step-up, and exact retained terminal
replay; Action Executor rows cover edit and JSON-redline rebinding. No row lets
an elicitation implicitly approve or dispatch an action. Hash-preserving
negative rows additionally reject non-local dynamic schema references,
non-canonical or out-of-range JSON Patch array indexes, and a `resolved_at`
later than the authoritative evaluation time.

Risk Explanation vectors use the standalone closed and bounded
`risk-explanation.schema.json` object plus an optional closed
`risk_explanation` fixture projection. Surface Publisher rows reject missing
defaults and incomplete effect coverage and bind publisher-owned hints to the
candidate surface without evaluating Runtime presentation state. Runtime
Mediator rows apply RFC 4647 Lookup to zero through sixteen ordered language
preferences, bind the hint to the exact complete verified retained Grant
surface and action, and require explicit output-context escaping plus a
presenter-controlled bidirectional-isolation boundary. They render publisher
prose literally alongside canonical risk and effect facts, suppress stale,
incomplete, or invalid hints atomically, and never project hint prose as agent
instruction or authority. The restricted lowercase RFC 5646 subset rejects
repeated variants, extensions, and private-use forms; display prose also
rejects C0/C1 and Bidi_Control characters.

Impact Simulation vectors use the standalone closed
`impact-simulation.schema.json` result plus an optional closed
`impact_simulation` fixture projection of authoritative inputs. Its
`source.actions` are a closed normalized verified-manifest semantic projection
produced from an exact manifest at the verified-surface boundary, not a second
general-purpose manifest validator: the fixture checker revalidates
only Impact-relevant references, fixed-point companion closure, reciprocal
recovery tuples, mode/effect consistency, core risk floors, and conservative
mapping support. Runtime Mediator rows require the pre-issuance phase, a
current exact surface and Grant-request binding, complete requested-action
coverage, deterministic risk-first unrequested selection, independently
derived action/exposure/recovery projections, and one candidate-wide decision
derived from runner-owned normalized Capability Match check facts. All 24 core
checks are present exactly once in UTF-8 order; extension URI checks remain
fail-closed indeterminate because this harness has no authoritative extension
classifier. `current_binding_facts` is the complete normalized authoritative
Result binding tuple, and `freshness_deadlines` bounds `valid_until` by every
available source. Its `grant_request_hash` is a runner-owned normalized hash
fact already recomputed at the Capability Match boundary; the Impact mock does
not rehash the full request or act as a raw policy engine. A retained non-null
match repeats the complete current binding tuple as well as the exact delegate,
request, status, and reasons. Invalid or stale detached supplements are
suppressed atomically while the canonical Consent Preview remains available;
the harness copies the full Result into a Grant or Action carrier for negative
tests, and embedding it rejects that complete closed object. No row issues a
Grant, opens approval, invokes an application
`dry_run`, dispatches an action, records an effect or receipt, or projects the
supplement to the agent.

Carrier rows cover duplicate Results under both Grant and Action during
simulation and active post-issuance Grant reuse during action mediation. Direct
semantic tests apply the same pre-dispatch rule to every consumed carrier for
Grant issue/revocation, Grant/action mediation, action invocation/replay, and
native/AHP translation; an unrelated closed object is not treated as an input
to an operation that does not consume it.

Each run evaluates one exact profile for one named deployment boundary. A
product that implements several profiles runs and reports each profile
independently. A Receipt Producer run additionally names exactly one
`producer_role`, `application` or `runtime`. Counterparts used by an interop
scenario are fixtures or separately identified implementations; their presence
does not give them, or the target, another role claim.

## Adoption bundles

Bundles are convenience plans, not new conformance roles or security levels.
Each claim names one exact role profile, an optional Receipt Producer role, a
selected feature set, and the exact requirement/vector closure derived from the
suite. A foundation does not rank above an overlay, and an omitted role makes
no claim that an actual protocol operation can proceed without that role.

The registry currently provides Surface Catalog, Mediated Proposal,
Application-Audited Effects, Operational Capacity, Human Elicitation, Risk
Communication, Impact Planning, and Remote Data Governance. Composing entries
means grouping claims by profile and producer role, unioning their features,
and deriving closure again; stored requirement and vector arrays are never
concatenated as an authority shortcut.

A satisfied bundle describes only the exact suite revision's executable
high-risk subset. It is not complete role conformance, certification,
production readiness, or arbitrary-implementation interoperability.

## Digest domains

All digests use SHA-256 and the text representation
`sha-256:<base64url-without-padding>`. The single `catalog_sha256` digest uses
the exact RFC-defined `ASP-CONFORMANCE-CATALOG-V1` domain. Hash the ASCII domain
string, one zero octet, and then each of these twenty canonical repo-relative
paths in lexicographic order:

1. `conformance/v1/bundles.json`
2. `conformance/v1/bundles.schema.json`
3. `conformance/v1/capacity-error.schema.json`
4. `conformance/v1/fixtures.json`
5. `conformance/v1/fixtures.schema.json`
6. `conformance/v1/human-elicitation.schema.json`
7. `conformance/v1/impact-simulation.schema.json`
8. `conformance/v1/mcp-binding.schema.json`
9. `conformance/v1/observation.schema.json`
10. `conformance/v1/operational-limits.schema.json`
11. `conformance/v1/purpose-task-bound-grant.schema.json`
12. `conformance/v1/report.schema.json`
13. `conformance/v1/risk-explanation.schema.json`
14. `conformance/v1/schema-cases.json`
15. `conformance/v1/schema-cases.schema.json`
16. `conformance/v1/subject.schema.json`
17. `conformance/v1/suite.json`
18. `conformance/v1/suite.schema.json`
19. `conformance/v1/vectors.json`
20. `conformance/v1/vectors.schema.json`

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

## MCP source provenance

The ASP-over-MCP profile is pinned to the official
[MCP specification revision `2025-11-25`](https://modelcontextprotocol.io/specification/2025-11-25).
The profile schema records the exact upstream repository commit and
generated-schema SHA-256 used during development; it remains an ASP-governed
profile schema and is not an official MCP extension. The copied upstream
license notice is retained in
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

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
non-local `$ref` and `$dynamicRef` values are rejected before schema
evaluation, and redline arrays use RFC 6902 index grammar and bounds. Both
ordinary response chronology and step-up freshness are evaluated against the
authoritative evaluation time and exact verified result projection. Replay
retention starts at the persisted `terminal_accepted_at`, not at response
construction. Agent Adapter rows additionally prove that only a
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
policy text, user content, tenant data, or unsanitized logs. A fixed synthetic
execution token may appear only in the private input/result fixture path needed
to test `dry_run` custody; it is non-authoritative test data and MUST be stripped
before adapter, model, user, event, log, receipt, and report projections.
Identifiers in catalog artifacts are test tokens, not production identifiers.

Catalog and report parsers reject duplicate JSON keys, non-I-JSON values,
unknown members, and digest mismatches. Their version 1 wire shapes have no
extension members. The protocol capacity-error envelope remains open as the
Error Model requires; the executable subset validates its standard members and
safe `limit_id` binding, but cannot certify the semantic privacy of arbitrary
extension content. Report signatures, if a later profile defines them, can
authenticate report bytes but cannot turn a self-test into protocol authority
or current-state evidence.
