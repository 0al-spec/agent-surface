<a id="asp-conformance"></a>
# ASP Conformance

> [!NOTE]
> This is the authoritative conformance module selected by the ASP Document
> Set Catalog. `drafts/agent-surface.md` is a generated aggregate reading view.

- Document ID: `https://github.com/0al-spec/agent-surface/documents/conformance`
- Exact version: `0.1.0-draft.1`
- Canonical path: `drafts/modules/conformance.md`

## Exact Normative Dependencies

- `https://github.com/0al-spec/agent-surface/documents/core` at `0.1.0-draft.1` (canonical `drafts/modules/core.md`)
- `https://github.com/0al-spec/agent-surface/documents/authorization` at `0.1.0-draft.1` (canonical `drafts/modules/authorization.md`)
- `https://github.com/0al-spec/agent-surface/documents/safe-effects` at `0.1.0-draft.1` (canonical `drafts/modules/safe-effects.md`)
- `https://github.com/0al-spec/agent-surface/documents/evidence` at `0.1.0-draft.1` (canonical `drafts/modules/evidence.md`)
- `https://github.com/0al-spec/agent-surface/documents/privacy` at `0.1.0-draft.1` (canonical `drafts/modules/privacy.md`)
- `https://github.com/0al-spec/agent-surface/documents/bindings/asp-over-mcp` at `0.1.0-draft.1` (canonical `drafts/modules/bindings/asp-over-mcp.md`)


## Conformance

This draft defines six independent role profiles instead of one
all-or-nothing application profile:

| Role profile | Profile identifier | Responsibility boundary |
| --- | --- | --- |
| Surface Publisher | `https://github.com/0al-spec/agent-surface/conformance/surface-publisher/v1` | Manifest discovery, integrity, lifecycle, schemas, and advertised surface semantics. |
| Grant Issuer | `https://github.com/0al-spec/agent-surface/conformance/grant-issuer/v1` | Consent, authoritative Grant construction, credential binding, attenuation, lifecycle, and revocation. |
| Action Executor | `https://github.com/0al-spec/agent-surface/conformance/action-executor/v1` | Protected-resource verification, session and event enforcement, and final effect admission. |
| Receipt Producer | `https://github.com/0al-spec/agent-surface/conformance/receipt-producer/v1` | Immutable role-scoped receipt evidence for authoritative observations made by that producer. |
| Runtime Mediator | `https://github.com/0al-spec/agent-surface/conformance/runtime-mediator/v1` | Local consent, credential custody, agent mediation, policy, runtime safety, and revocation handling. |
| Agent Adapter | `https://github.com/0al-spec/agent-surface/conformance/agent-adapter/v1` | Typed translation between an agent and a Runtime Mediator without receiving or creating authority. |

The identifiers above name the exact role-profile versions defined by this
draft. A similar name, an older version, an implementation-specific label, or
an unknown profile identifier MUST NOT be substituted. This draft does not
define a manifest `conformance` member, a signed conformance certificate, or a
certification authority. It defines the descriptive machine-readable test
report below, but that report is not protocol authority. If a future profile
adds claim metadata to a manifest, that metadata MUST use a closed versioned
shape and be included in the manifest hashing view.

In the current modular publication, the conformance harness derives
`specification_sha256` from the generated aggregate selected by the exact
Document Set Catalog. Each generated report also binds the exact
`document_set_id` and `document_set_version`. The suite catalog records the
aggregate source path and hash domain, not a mutable default branch. A report
for one document set MUST NOT be reused as evidence for another merely because
their `protocol_version` values match.

### Conformance Claim and Composition Rules

A conformance claim is descriptive. It is not a Grant, credential, approval,
attestation result, certification, trust anchor, or evidence that another role
performed its checks. A participant MUST NOT skip manifest, Grant, credential,
session, selected-profile, receipt, lifecycle, or current-state verification
because another participant claims a conformance role.

Conformance is atomic for one role-profile version and one named implementation
or deployment boundary. A claim MUST identify that boundary, the exact profile
identifier, the supported ASP protocol version, and every optional profile or
feature included in its scope. A Receipt Producer claim MUST additionally name
exactly one `producer_role`, `application` or `runtime`. This documentation is
not a protocol authority object and MUST NOT be copied into a Grant or receipt
as proof of conformance.

An implementation that omits an unconditional requirement, or a conditional
requirement for a feature it advertises, selects, accepts, invokes, or produces,
MUST NOT claim that role profile for the affected boundary. It MAY instead
claim a smaller deployment boundary that does not expose the feature. A claim
MUST NOT use terms such as "partial", "mostly", or "compatible" as if they
were the role profile identifier.

Each claim names exactly one role. A process, product, or deployment MAY claim
multiple roles only by satisfying and documenting each role independently.
Conformance to one role does not imply conformance to another role, even when
one binary or operator implements both. In particular:

- a Surface Publisher claim does not prove Grant Issuer or Action Executor
  behavior;
- a Grant Issuer claim does not let an Action Executor trust a credential or
  cached Grant state without its own checks;
- an Action Executor claim does not make that component a Grant Issuer or
  Receipt Producer;
- a signature service does not become a Receipt Producer merely by signing
  bytes; and
- a Runtime Mediator or Agent Adapter does not become an application-side
  authority by observing a request or response.

A conforming deployment can compose independently operated roles. The consumer
of another role's output MUST validate that output under the ordinary protocol
rules; the producer's self-claim is not sufficient. Delegating an internal
task, endpoint, signing operation, schema host, database, or policy engine does
not dilute the externally observable requirements of the claiming role. If a
required delegate or authoritative state is unavailable, the composed service
MUST fail closed before Grant issuance, application-originated disclosure,
effect admission, or an authoritative receipt claim.

Active Grants remain bound to their exact manifest and Grant semantics when a
deployment changes its claimed roles or implementation topology. A role change
MUST NOT reinterpret an old Grant, weaken a selected optional profile, or make
an unsupported profile look conforming. The ordinary versioning, renewal,
revocation, and fresh-consent rules continue to apply.

The role boundaries have these required fail-closed cases:

| Role | Invalid claim or operation |
| --- | --- |
| Surface Publisher | Reusing a surface version with another hash, publishing incomplete references, producing a non-attenuating or cross-context Authorized Surface Projection, or advertising semantics that the exposed surface cannot provide. |
| Grant Issuer | Issuing against a stale or superseded base or projection, accepting a projection for another authenticated context, widening a request, returning an unclosed action set, or treating unknown Passport or selected-profile state as accepted. |
| Action Executor | Trusting the issuer claim instead of independently validating audience, active Grant state, exact base/projection, surface and delegate tuple, session generation, policy, budget, approval, idempotency, and effect preconditions. |
| Receipt Producer | Claiming another producer role's observation, producing a receipt outside the authoritative decision record, downgrading an invalid signature, or treating a receipt as action authority. |
| Runtime Mediator | Reusing an Authorized Surface Projection across cache partitions, using a stale match or Consent Preview, storing a wider Grant, releasing a Grant Credential, or continuing while revocation state is unknown. |
| Agent Adapter | Receiving credentials, selecting stronger authority, fabricating approval/effect/receipt evidence, or blindly retrying a partial or unknown outcome. |

### Adoption-Oriented Conformance Bundles

An adoption-oriented conformance bundle is a small, named, machine-readable
test plan assembled from the atomic role profiles and optional features above.
It does not create a seventh role, a partial role claim, a deployment profile,
or a linear conformance level. In particular, bundle names, array order, and
the labels `foundation` and `feature_overlay` express adoption intent only.
They are not security ranks, maturity levels, prerequisites, certification,
or authority to perform an ASP operation.

The versioned bundle registry identifier is:

```text
https://github.com/0al-spec/agent-surface/conformance/bundles/v1
```

Its canonical registry and closed JSON Schema are published as
`conformance/v1/bundles.json` and `conformance/v1/bundles.schema.json`. The
registry is bound into the Conformance Catalog digest. It contains only the
exact `foundation` and `feature_overlay` labels defined here; implementations
MUST NOT infer a total order, higher-is-better relationship, or implicit
inclusion between entries.

Each bundle contains a collision-resistant `bundle_id`, a human-readable title
and description, a kind, and one or more role claims. Each role claim contains
exactly one role-profile identifier, the complete selected `feature_ids` for
that bundle claim, the derived `requirement_ids`, and the derived `vector_ids`.
A Receipt Producer claim additionally contains exactly one `producer_role`.
The same (`profile_id`, `producer_role`) pair MUST NOT occur twice in one
bundle. Identifiers and claims use the canonical registry order.

For every role claim, a validator MUST derive closure from the selected suite
version as follows:

1. Include every `always` requirement of the selected role profile.
2. Include every requirement whose feature is selected by that claim.
3. For a Receipt Producer, include every requirement for the exact selected
   producer role.
4. Reject a selected feature for which the suite has no matrix requirement for
   that role; it cannot be represented as covered or silently skipped.
5. Include the canonical ordered union of every vector referenced by the
   resulting requirements and require both positive and negative coverage.

The registry's `requirement_ids` and `vector_ids` MUST equal that derived
closure exactly. An omitted, added, duplicated, or reordered applicable
requirement or vector invalidates the complete registry. A bundle therefore
cannot use a shorter test plan to waive an unconditional role obligation or a
conditional obligation for a selected feature.

The v1 registry defines these independent adoption targets:

| Bundle | Kind | Scope |
| --- | --- | --- |
| Surface Catalog | `foundation` | Surface Publisher discovery and integrity without an execution-role claim. |
| Mediated Proposal | `foundation` | Proposal-only publication plus Grant, executor, runtime, and adapter boundaries without commit, compensate, or revert authority. |
| Application-Audited Effects | `foundation` | Mediated effect admission with an application-role Receipt Producer. |
| Operational Capacity | `feature_overlay` | Operational Limits publication, application admission, event delivery, HTTP binding, and runtime recovery. |
| Human Elicitation | `feature_overlay` | Action Executor, Runtime Mediator, and Agent Adapter handling of bound human input without approval authority. |
| Risk Communication | `feature_overlay` | Effect-bound publisher hints and inert runtime presentation beside canonical risk semantics. |
| Impact Planning | `feature_overlay` | Runtime-local deterministic Impact Simulation kept separate from execution and authority. |
| Remote Data Governance | `feature_overlay` | Runtime enforcement of Remote Processing Privacy and Agent Training Use constraints. |

Omission of a role from a bundle makes no statement about whether that role is
needed by a deployment operation. For example, Surface Catalog does not grant
action authority, and Application-Audited Effects does not imply a runtime-role
Receipt Producer. The ordinary protocol and composition rules still determine
which roles and producer boundaries an actual operation requires.

A deployment satisfies one bundle only through separate current conformance
reports for every role claim in that bundle. Each report MUST bind the same
suite version, catalog digest, specification digest, protocol version, and the
named implementation boundary; MUST use the exact profile and producer role;
MUST select at least the claim's feature set; and MUST pass every applicable
vector for its complete reported feature scope. A suite-fixture, incomplete,
stale, failed, uncovered-feature, wrong-boundary, or self-asserted report does
not satisfy a bundle claim. Reports remain descriptive evidence and MUST NOT be
embedded in a Grant, credential, approval, receipt, or action request as
authority.

Satisfying a bundle means only that the exact catalog revision's selected
high-risk vectors passed for those reports. It MUST NOT be represented as
complete role-profile conformance, arbitrary-implementation interoperability,
certification, production readiness, or proof that an untested normative
requirement is implemented.

Bundles compose only by grouping claims with the same (`profile_id`,
`producer_role`) key, taking the set union of their selected features, and
re-deriving the complete requirement and vector closure from the exact suite
version. A composer MUST NOT concatenate stale stored closures or drop a
shared unconditional requirement. The resulting composition is not another
registered bundle, does not inherit a new name, and does not imply that one
source bundle is stronger than another.

### Interoperability Test Suite

The versioned suite identifier
`https://github.com/0al-spec/agent-surface/conformance/suite/v1` targets the
exact protocol identifier `agent-surface/0.1` and the six role-profile
identifiers above. Its canonical matrix, vectors, semantic fixtures, schemas,
adoption bundle registry, and runner contract are published under
`conformance/v1/` in this specification repository. Stable bundle,
requirement, vector, fixture, and mutation identifiers MUST NOT be reused with
different semantics.

The v1 matrix is an executable high-risk coverage subset. It covers manifest
integrity and proposal-only bounds, exact Grant attenuation and revocation,
Grant verification, idempotent replay and conflicts, denied actions, receipt
role integrity, runtime mediation, adapter authority boundaries, and the
Operational Limits declaration, action-admission, logical event-delivery, and
retry contracts. It also covers the core Risk Explanation UI Hints manifest
shape and the boundary between inert publisher prose and runtime-derived
machine semantics, plus the bounded local Impact Simulation projection and its
separation from execution, consent, and authority. It does not enumerate every
normative requirement in every role profile. Consequently,
a `pass` suite verdict means only that every applicable vector in the exact
catalog revision passed. It MUST NOT be represented as complete role-profile
conformance, certification, interoperability with arbitrary implementations,
or current operational security.

One test run and one report evaluate exactly one profile identifier for one
named deployment boundary and one implementation artifact and configuration.
The subject binds their digests, the exact protocol identifier, and the complete
set of optional features in scope. A Receipt Producer subject additionally
binds exactly one `producer_role`, `application` or `runtime`; that field is
invalid for every other role. Co-located roles require separate reports. A
counterpart participating in an `interop` vector MUST match every exact profile
and Receipt Producer role required by that vector, use another deployment
boundary and implementation artifact, and be bound into the observation. An
unrelated, same-boundary, suite-fixture, or self-asserted counterpart does not
satisfy the vector and gives no conformance credit to any role.

Each matrix requirement has closed applicability: unconditional, selected
optional feature, or Receipt Producer role. Before deriving applicability, the
runner obtains a feature inventory from the separately configured probe and
requires it to equal the subject's complete declared feature scope. An operator
or subject MUST NOT hide a supported, advertised, selected, accepted, invoked,
or produced feature or mark an applicable case as not applicable. A selected
feature with no matrix row for the target role is reported as uncovered and
makes the suite verdict `incomplete`. Unknown profiles, features, producer
roles, requirement ids, vector ids, results, members, or applicability states
invalidate the run rather than weakening its closure.

Vectors use only the suite's closed declarative operation, fixture, mutation,
assertion, observation, and state-delta vocabulary. Each case resolves to one
digest-bound semantic baseline and an exact closed `replace` patch. Vectors
MUST NOT contain executable code, shell commands, or target URLs.

The versioned `schema-cases.json` corpus executes positive and negative cases
for the Operational Limits declaration, operational-capacity error envelope,
Risk Explanation UI Hint object, and Impact Simulation Result.
Each candidate is carried as an inert JSON string so malformed I-JSON,
duplicate-member, unsafe-integer, schema-invalid, and semantic binding failures
can be represented without making the corpus itself invalid. The validator
parses each candidate with the suite's strict I-JSON rules, validates it against
its versioned JSON Schema, and, for a declaration, checks action and event
resolution, idempotency eligibility, globally unique `limit_id` values, and the
core control event plus manifest-declared control-event exclusion against the
case's closed manifest context. For a risk explanation it additionally checks
canonical sorted languages, exact default-language presence, bounded inert
text, and complete declaration-order effect coverage against the case's closed
parent-action context. For an impact simulation it additionally checks exact
surface, request, delegate, match and revision bindings, complete requested
coverage, bounded deterministic unrequested selection, outcome/reason
consistency with the exact selected-candidate decision, omission of advisory
reasons, canonical action projections, exact derived recovery limitations, and
absence of resource instances or publisher prose. For a capacity envelope it
additionally
requires every disclosed `limit_id` to be both manifest-declared and safe for
the authenticated active partition. The common capacity envelope remains open
to extension members as required by the Error Model, while its `limit` member
remains closed.
A positive case that fails or a negative case that passes invalidates the
catalog.

The separately configured stimulus adapter receives the resolved fixture,
setup, operation, subject, and required counterpart topology, but it MUST NOT
receive expected errors, policy or match reasons, observation tokens, or state
values. A separate authoritative probe discovers feature inventory and returns
sanitized observations after execution. The runner alone compares those
observations with its oracle and decides the result.

The runner invokes fresh adapter and probe processes with a fresh working
directory, constrained environment, process-group timeout, file-size,
file-descriptor, and CPU limits, and bounded captured output for every vector.
Both executables are trusted test components; these limits do not sandbox them
or block filesystem and network
access. Operators MUST isolate the harness and non-production subject
environment for their risk model. Concurrency tests use deterministic barriers
around the specified linearization point rather than timing sleeps.

A negative vector passes only when the observed ASP decision and namespaced ASP
error, Policy Decision reason, or Capability Match reason, where the RFC defines
one, match the expected values and every declared
postcondition holds. Error status alone is insufficient. The vector can require
zero new effects, budget revisions, idempotency records, credentials, receipts,
Grant records, or control events, or the exact receipt and lifecycle deltas
required by that denial phase. A crash, timeout, malformed response,
unavailable authoritative probe, or unknown state is an execution error, never
a successful rejection. An HTTP status is an assertion only when a vector
explicitly selects a binding for which this draft defines a normative mapping.
The HTTP Capacity Error Binding vectors use a closed normalized fixture
projection of the authenticated response path, status, parsed cache directive
result, and parsed `Retry-After` form. That projection is test-harness input,
not an ASP wire object. The transport-neutral Operational Limits vectors
continue to validate the common capacity envelope without inferring an HTTP
status from an ASP error code alone.

The ASP-over-AHP vectors likewise use a closed normalized projection of profile
selection, authenticated carrier state, AHP representation identity and
revision, and the embedded ASP tuple. The projection exercises the binding
contract without defining the base AHP wire format. Positive cases prove that
presentation and exact action translation preserve ASP authority; negative
cases cover profile downgrade, unauthenticated transport, session-generation
substitution, conflicting representation replay, action substitution, and an
AHP receipt summary presented as authority.

The ASP-over-MCP vectors use a closed normalized projection of exact MCP
revision and experimental-capability negotiation, the authenticated manifest
resource, pagination-stable binding view, deterministic tool mapping,
runtime-constructed request metadata, structured result, receipt resource, and
ambiguous-outcome state. Positive cases prove exact action reconstruction,
independent application admission, credential custody, structured error
mapping, complete receipt verification, and idempotent reconciliation.
Negative cases cover MCP revision or profile downgrade, mixed surface pages,
stale view reuse, action or input substitution, annotation-derived authority,
OAuth token passthrough, text/structured-result disagreement, cancellation
reported as no effect, and a receipt link or hash presented as complete
evidence. No passing vector turns MCP discovery, authentication, progress,
cancellation, or a task into ASP authority.

The Human Elicitation vectors use the standalone closed profile schema and a
closed normalized projection of authenticated requester and presenter state,
the current session, Grant, surface, context, immutable replay record, and any
candidate validation state. Positive cases cover clarification, closed choice,
step-up verification, normalized edit, base-bound redline results, and exact
retained terminal replay. Negative cases cover stale session generations,
conflicting terminal replay, agent-asserted or secret-bearing step-up results,
stale edit bindings, and redline result substitution. Agent Adapter cases
separately prove minimized, purpose-bound answer projection and rejection of
agent-originated resolutions or secret-bearing envelopes. No passing Human
Elicitation vector establishes approval, consent, Grant, dispatch, effect,
receipt, or authentication-factor authority.

The Risk Explanation UI Hints cases use a closed parent-action context and
publisher object plus a normalized Runtime Mediator presentation observation.
Positive cases cover a sorted multilingual object, RFC 4647 Lookup and default
fallback, exact effect-summary order, literal isolated presentation, and
display alongside canonical risk and effects. Negative cases cover a missing
default, duplicate or non-canonical languages, control characters, unknown,
missing, duplicate, or reordered effect ids, a stale surface or action cache
binding, an incomplete retained manifest projection, missing output-context
escaping or presenter-controlled bidirectional isolation, use of prose in
matching or approval, and projection into an agent instruction. A passing case
establishes only structural and boundary behavior; it cannot prove that
human-authored prose is truthful or complete beyond its machine-checkable
effect-id coverage.

The Impact Simulation cases use a closed normalized verified-manifest semantic
projection produced from an exact manifest, semantic Grant request, selected
delegate, normalized matching check facts, complete authoritative binding and
freshness facts, plus a normalized Runtime Mediator presentation observation.
Positive schema and direct semantic cases cover complete
requested action projection, deterministic highest-risk unrequested selection,
covered, not-covered, and indeterminate outcomes, empty and truncated
unrequested sets, exact companion, effect, exposure, and recovery data, and
atomic fallback to the canonical Consent Preview. Negative catalog cases cover
an omitted requested action, more than 64 requested actions represented as a
partial result, incorrect high-risk selection or coverage counts, stale
surface, request, match or revision bindings, outcome/reason conflicts, closed
Grant and Action carrier embedding, and post-issuance reuse. Direct semantic
and state-isolation checks additionally prove that accepted and suppressed
paths do not contact the application, run an application dry run, or project
the result into approval, receipt, Policy Decision, or agent state. Detached
publisher prose and fabricated concrete resource examples remain prohibited
normative inputs but are outside the executable input subset of this v1
harness. Closed-carrier vectors and direct semantic cases duplicate the
complete Result into Grant and Action objects, reuse an active post-issuance
Grant, and exercise exact-action replay. Each Grant Issuer, Runtime Mediator,
Action Executor, and Agent Adapter case rejects the duplicate before changing
state whenever that operation actually consumes the affected closed object. A
passing case establishes local projection behavior only; it does not establish
consent, issuance, current authority, approval, or successful execution.

The report binds the exact suite and specification sources, ordered applicable
requirements and vectors, each vector digest, subject and counterpart artifacts,
runner, adapter and probe entry-point digests, configuration digests and
versions, execution environment, run identifier, and run interval. Each
observation binds that run identifier, the complete subject, harness, and exact
participating counterparts.
The report contains one result for every applicable vector. The validator
recomputes all applicability, digests, vector closure, result counts, and the
suite verdict:

- any assertion failure produces `fail`;
- otherwise any missing result, execution error, unavailable probe, uncovered
  selected feature, suite-fixture subject, or stale binding produces
  `incomplete`;
- only a complete applicable set of passing results produces `pass`.

The catalog digest is SHA-256 over the ASCII domain
`ASP-CONFORMANCE-CATALOG-V1` followed by a zero octet, then each canonical
catalog path in lexicographic order as UTF-8, a zero octet, its raw file bytes,
and a final zero octet. The canonical set is exactly
`bundles.json`, `bundles.schema.json`, `capacity-error.schema.json`,
`fixtures.json`, `fixtures.schema.json`,
`human-elicitation.schema.json`, `impact-simulation.schema.json`,
`mcp-binding.schema.json`,
`observation.schema.json`,
`operational-limits.schema.json`,
`report.schema.json`, `risk-explanation.schema.json`, `schema-cases.json`,
`schema-cases.schema.json`,
`subject.schema.json`, `suite.json`, `suite.schema.json`, `vectors.json`, and
`vectors.schema.json`, each under `conformance/v1/`. The specification
digest uses the ASCII domain
`ASP-SPECIFICATION-SOURCE-V1`, a zero octet, and the raw bytes of
`drafts/agent-surface.md`. A vector digest uses the ASCII domain
`ASP-CONFORMANCE-VECTOR-V1`, a zero octet, and the RFC 8785 serialization of
the vector object. The subject digest uses the ASCII domain
`ASP-CONFORMANCE-SUBJECT-V1`, a zero octet, and the RFC 8785 serialization of
the complete subject object, including counterpart bindings. A counterpart
entry and the complete runner object use the same form with domains
`ASP-CONFORMANCE-COUNTERPART-V1` and `ASP-CONFORMANCE-HARNESS-V1`.
The canonical runner entry point and configured adapter and probe entry points
use raw bytes under `ASP-CONFORMANCE-RUNNER-V1`,
`ASP-CONFORMANCE-ADAPTER-V1`, and `ASP-CONFORMANCE-PROBE-V1`. Each digest is
encoded as `sha-256:` followed by canonical unpadded base64url. These digests
bind bytes and catalog selection; they do not authenticate an implementation,
runner, operator, or report.

Reports and observations MUST NOT contain Grant Credentials, execution tokens,
private keys, raw Attestation Evidence, hidden policy text, or real sensitive
application payloads. A report is descriptive test evidence only. It is not a
Grant, credential, receipt, approval, attestation result, trust anchor, action
authority, or permission to skip ordinary current-state verification. A
repository self-test subject MUST declare `subject_kind: suite_fixture`; its
verdict remains `incomplete` even when every assertion matches. A suite
self-check can establish machine validation of its catalog; `interop_tested`
maturity requires successful use with independently implemented participant
boundaries and cannot be derived from the repository's own fixtures.

### Reference Mock Participants

This repository publishes a reference Mock App and Mock Runtime under `mocks/`
so an operator can exercise the conformance harness without a real agent or a
production application. The closed participant manifest
`mocks/v1/manifest.json` binds the exact mock protocol version, participant
identifiers, boundary identifiers, role assignments, feature inventory,
entry points, and artifact digests. The adjacent JSON Schema and the repository
mock validator define the machine-checked bundle shape.
Its `claim_effect` value MUST be exactly `suite_fixture_only` and MUST NOT be
overridden by an operator, adapter, probe, subject document, or report.

The reference participants are conformance-suite fixtures, not ASP
implementations. Every subject or counterpart backed by this bundle MUST use
`subject_kind: suite_fixture`. A report that uses either participant therefore
remains `incomplete` with the `suite_fixture` reason even when every applicable
assertion passes. Such a report gives no implementation-conformance,
interoperability, certification, deployment-readiness, or production-security
credit. In particular, the two participants are maintained together and MUST
NOT be represented as independently implemented boundaries.

The versioned mock participant protocol is an internal harness control
protocol. It carries deterministic setup, stimulus, and sanitized observation
messages between the runner and the mock entry points. It is not an ASP wire
protocol, transport binding, discovery mechanism, Grant, credential, receipt,
or authority channel, and implementations MUST NOT expose it as any of those.
Changing the mock protocol does not change ASP wire semantics or establish a
new ASP compatibility claim.

The Mock App and Mock Runtime MUST keep disjoint authority stores. The Mock App
owns only synthetic application-side manifest, Grant, action-admission, effect,
and App Receipt state. The Mock Runtime owns only synthetic runtime-side local
policy, credential-custody, mediation, safety, and Runtime Receipt state.
Each participant MUST NOT read or mutate the other's authority store to satisfy
an assertion. Cross-participant behavior uses only the typed mock exchange
declared by the manifest, while the probe returns privacy-minimized observations
derived from the owning participant's resulting state.

For HTTP capacity tests, the Mock App derives the `429` or `503`, `no-store`,
and optional `Retry-After` observations from the transport-neutral envelope.
The Mock Runtime validates the normalized authenticated HTTP projection before
it invokes the ordinary capacity recovery state machine. A failed binding
preserves local admission and semantic retry state and produces a deterministic
negative observation; it is not converted into an adapter execution error.

For ASP-over-AHP tests, the Mock Runtime validates negotiated profile,
authenticated carrier, representation replay state, and the complete ASP tuple
before changing presentation state. The Mock Agent Adapter forwards only an
exact action binding. Profile downgrade, unauthenticated carrier state, tuple or
action substitution, conflicting replay, and receipt-authority claims preserve
the prior ASP and AHP state and produce deterministic negative observations.

For ASP-over-MCP tests, the Mock Runtime owns exact MCP negotiation, manifest
and tool-view verification, request construction, credential custody, result
validation, and ambiguous-outcome reconciliation. The Mock App owns the
synthetic manifest resource, paginated tool mapping, Action Request
reconstruction, application admission, Action Response, and authenticated
receipt resource. The Mock Agent Adapter proposes only the mapped tool and
input. Fixtures contain no production credential. Any execution token is fixed
synthetic, non-authoritative test data used only to prove the private
`dry_run` custody path; downgrade,
mixed-view, substitution, annotation-authority, token-passthrough,
result-split, cancellation, and receipt-link failures preserve prior authority,
idempotency, budget, effect, and receipt state and produce deterministic
negative observations.

For Human Elicitation tests, the Mock Runtime mediates the authenticated
presenter boundary and immutable request/response replay record. The Mock App
owns application-requested edit and redline candidate validation. Both
participants preserve the prior proposal, approval, dispatch, effect,
credential, and receipt state when a binding, hash, option, assurance, base, or
result check fails. The Mock Agent Adapter projects only the minimized,
purpose-bound synthetic answer and rejects agent-originated resolutions,
unbound envelopes, and secret-bearing data. Synthetic step-up fixtures contain
only opaque verifier results and MUST NOT carry authentication factors.

For Risk Explanation UI Hint tests, the Mock App publishes only deterministic
synthetic closed hint objects bound to its exact manifest actions. The Mock
Runtime validates the complete object, resolves one language or the default,
renders an inert normalized observation beside independently derived risk and
effect values, and preserves its matching, approval, admission, and agent
projection state when a hint is malformed, stale, detached, or hostile. The
Mock Agent Adapter MUST NOT receive the hint as an instruction or authority.

For Impact Simulation tests, the Mock Runtime derives a deterministic closed
result only from a synthetic normalized verified-manifest semantic projection,
request, delegate, runner-owned Capability Match check facts, complete current
binding facts, and per-source freshness deadlines. It derives candidate-wide
status and decisive blocking reason codes from those check facts, maps them to
every requested example, omits advisory and overridden indeterminate reasons,
and derives the exact recovery limitation set from the retained effects and
recovery relationships. It includes every requested
action or atomically suppresses the feature above the bound, selects only the
required highest-risk unrequested actions, and keeps all examples local. The
Mock App MUST NOT provide an example or be contacted for a dry run or resource
probe, and the Mock Agent Adapter MUST NOT receive a result. Malformed, stale,
detached, incomplete, or authority-bearing candidates preserve all Grant,
approval, dispatch, effect, receipt, policy-decision, and agent-projection
state while the Mock Runtime returns the canonical Consent Preview fallback
observation. Before dispatch, every mock consumer checks each closed Grant or
Action object it actually consumes and rejects an embedded Result; the direct
semantic matrix includes Grant issue and revocation, Grant and action
mediation, action invocation and replay, and native and AHP action translation.

All mock inputs, identifiers, payloads, keys, credentials, evidence, and state
are deterministic synthetic test values. The bundle MUST NOT accept or retain
production secrets, user content, tenant data, private keys, live Grant
Credentials, execution tokens, cookies, or raw Runtime Attestation Evidence.
The synthetic agent-side input is a fixed typed fixture and is not evidence of
agent identity, capability, intent, approval, or successful agent execution.

### Reference API Importer

This repository publishes the `asp-api-import` reference CLI under
`tools/asp-api-importer/` for the deterministic projection defined by the
OpenAPI and AsyncAPI Import Profile. The tool accepts strict JSON, operates
offline, recognizes only the source versions and annotation locations defined
by the profile, sorts emitted members deterministically, computes the manifest
hash with the Canonical Object Hash Profile, and rejects the complete
projection when any annotation or generated declaration fails its implemented
checks.

The adjacent annotation JSON Schema defines the closed root, operation, and
member objects. The versioned case registry and its schema bind positive
OpenAPI and AsyncAPI inputs, exact generated outputs, and negative parse,
version, location, reference, duplicate, reserved-member, and incomplete-
declaration cases. In particular, the positive OpenAPI case contains an
ordinary unannotated destructive operation and requires it to be absent from
all generated ASP inventories.

`generate` returns status `0` and writes one hash-bound JSON candidate only after
the transform, the case-registry-pinned reference-linter ruleset,
deterministic ordering, and hashing succeed. A ruleset identifier or version
mismatch fails closed rather than silently changing importer acceptance. The
command returns status `2` and writes no candidate when it cannot evaluate the
input safely. `self-check` requires the compiled schemas and case registry to
equal the selected repository artifacts, validates the registry, ruleset
binding, and schemas, executes every bound case, and compares positive output
byte-for-byte with its golden manifest.

The reference importer deliberately does not parse YAML, validate the complete
OpenAPI or AsyncAPI specification, fetch or resolve a reference, validate
remote ASP schema bytes, or replace a complete Agent Surface Manifest
validator. Its successful output is machine evidence for this bounded
authoring transform, not permission to serve the candidate automatically. The
publisher MUST complete every ordinary manifest, implementation-semantic,
version, and deployment check from the profile before designating and serving
the output as its issuer-authoritative current surface.

The tool never consumes credentials, Grants, user data, live endpoints,
implementation code, private keys, or network resources. A generated hash
commits to candidate bytes under the manifest hash profile; it does not
authenticate the publisher, prove that an annotation is truthful, establish
source-spec conformance, or authorize an omitted or included operation.

### Reference Manifest Linter

This repository publishes the `asp-lint` reference CLI under
`tools/asp-manifest-linter/` for deterministic static checking of an Agent
Surface Manifest. The versioned rule registry and its JSON Schema define stable
rule identifiers, severity, RFC anchors, and operator help. The adjacent
diagnostics JSON Schema defines the machine-readable report contract. A rule
identifier MUST NOT be reused with different semantics within the same
ruleset version.

The v1 ruleset contains exactly these checks:

| Rule | Static requirement |
| --- | --- |
| `ASP-LINT-SCHEMA-001` | Every resource and event declares a non-empty `schema`; every action declares non-empty `input_schema` and `output_schema`. |
| `ASP-LINT-RISK-001` | Every action declares one standard `risk` label or an extension identifier in the reference linter's conservative RFC 3986 URI subset; runtime support for the URI's defining conservative mapping remains a separate compatibility check. |
| `ASP-LINT-RISK-EXPLANATION-001` | Every present `risk_explanation` uses the closed bounded shape, canonical language order and default, inert text, and exact declaration-order coverage of the parent action effects. |
| `ASP-LINT-IDEMPOTENCY-001` | A side-effecting, state-changing-mode, or persisted proposal action declares required idempotency, fixed-point normalization, the required input hash profile, and `input_schema_hash`. |
| `ASP-LINT-SCOPE-001` | Scope identifiers are unique; resource, action, and non-control event references resolve exactly; control events omit `scope`. |

The CLI MUST parse the complete input before applying rules and MUST fail
closed on duplicate object members, floating-point values, integers outside
the I-JSON safe range, malformed Unicode, trailing JSON, a non-object root, or
non-array `scopes`, `resources`, `actions`, or `events`. It returns status `0`
only when no finding exists, status `1` when one or more lint findings exist,
and status `2` when input or tool integrity prevents a safe result. A JSON
report binds the exact tool and ruleset versions, input source label, counts,
stable rule identifiers, severity, JSON Pointer, message, and operator help.

Reference linting is offline. It MUST NOT execute manifest content, contact a
schema host, follow a network reference, inspect production credentials or
state, or infer a missing declaration. `self-check` validates the rule registry
against its schema, requires the registry to match the implemented rule set,
validates a generated report against the diagnostics schema, and requires the
compiled schema and registry bytes to equal the selected repository artifacts.

A clean lint report is static evidence about those exact v1 declarations only.
It does not validate remote schema bytes, `surface_hash`, issuer identity,
current Grant state, authorization, approval, effects, receipts, runtime
behavior, interoperability, conformance, certification, or deployment
security. Consumers MUST continue every ordinary protocol and current-state
check defined by this specification.

### Reference Replay Tool

This repository publishes the `asp-replay` reference CLI under
`tools/asp-replay/` for the Portable Replay Bundle Profile. The tool accepts
strict I-JSON and performs deterministic offline validation of one passive
session-generation bundle. It verifies the embedded historical Surface and
semantic Grant hashes, the ordered replay-record hash chain, exact session
transitions, event delivery and acknowledgement identity, event gaps,
receipt hashes and links, capture gaps, and the enclosing bundle hash.

For every input that can be parsed as strict I-JSON and safely evaluated,
`verify` emits the bounded Replay Validation Report identified by the exact
`tool.check_profile`. A strict-parse or local evaluation failure returns status
`2` and emits no report. An `incomplete` or `invalid` report returns status `1`;
only `valid` returns status `0`. `self-check` requires the compiled schemas,
case registry, and implementation behavior to match the selected repository
artifacts.

The reference CLI implements only the checks enumerated by that exact check
profile. It is not the complete native-object validator required for a complete
Portable Replay Bundle Profile validation claim. Even a `valid` CLI verdict
MUST NOT be represented as complete profile conformance or substituted for the
authoritative Surface, Grant, CloudEvent, acknowledgement, gap, receipt, and
required-signature validators. A composed complete-profile validator MUST
combine those gates fail closed.

A successful bounded result therefore describes only the internal integrity
and declared completeness checked for the exact bundle bytes. It is not a
conformance claim for any of the six ASP roles, exporter authentication,
producer authentication, current-state proof, trusted time, proof of an
external effect, or permission to perform an operation.

The reference tool is inert and offline. It MUST NOT follow a URI, resolve a
remote schema or key, open a network connection, send `event.replay`,
`event.ack`, or `event.flow`, mutate or resume a session, dispatch an action,
invoke an agent, model, tool, approval, compensation, or revert path, or copy
application payloads into diagnostics. It accepts no Grant Credential, bearer
token, cookie, proof-of-possession material, private key, raw execution token,
prompt, Action Request, Action Response, or executable content. An invalid or
incomplete bundle MUST NOT cause partial execution or best-effort recovery.

### Surface Publisher Profile

A component conforms to the Surface Publisher Profile when it:

- publishes an Agent Surface Manifest
- publishes an explicitly curated ASP inventory and does not infer exposure
  merely from an underlying API, route, RPC, MCP, SDK, or UI inventory; every
  selected affordance has complete ASP semantics and every omitted operation
  remains outside that surface snapshot
- when using the OpenAPI and AsyncAPI Import Profile, accepts only its exact
  source versions and annotation locations, projects complete declarations
  atomically without inference, validates the complete generated manifest, and
  treats the served manifest rather than source annotations as the authority
- when selecting the ASP-over-MCP Binding Profile, serves exactly one complete
  verified manifest resource on the manifest-pinned dedicated endpoint and one
  stable, fully paginated binding view whose mapped tools preserve the exact
  action, pinned self-contained schemas, mode, surface, authorization
  composition, and authorized-projection semantics; rotates and notifies on
  manifest or schema drift without deriving ASP affordances from an underlying
  MCP inventory
- when publishing an Authorized Surface Projection, derives every projection
  from the exact current base and server-authenticated lifecycle key, permits
  only structurally identical closed declarations or omission, allocates fresh
  opaque projection identity on every material change, serves the exact closed
  no-store bootstrap descriptor when withholding the base, partitions
  retention, and exposes no cross-context or hidden-inventory oracle
- computes and publishes a valid `surface_hash` and changes
  `surface_version` whenever the manifest hashing view changes
- does not publish an Impact Simulation Result or feature identifier as a
  manifest semantic; the result is derived only inside a claiming Runtime
  Mediator
- declares a supported `surface_mode` and, for `proposal_only`, exposes only a
  closed `read`/`propose` action inventory with at least one proposal action,
  no effects, and no state-changing companion relationship
- declares actions, resources, events, scopes, and schemas
- when advertising Purpose- and Task-Bound Agent Grant, advertises only the
  exact profile whose issuer records, lifecycle, relationship, attenuation,
  and protected-resource policy it can enforce completely
- declares every referenced data class and complete exposure contracts for
  resources, actions, and events
- declares risk labels for actions
- when publishing a Risk Explanation UI Hint, emits the exact closed,
  size-bounded, sorted localization shape, covers every declared effect in
  every language, changes the surface version and hash with the prose, and does
  not represent that prose as narrower machine semantics
- declares one static execution mode and operation id per action
- declares valid fixed-point input-normalization rules for every
  idempotency-required action and publishes a valid hash of its self-contained
  input schema
- declares maximum effects for state-changing actions and internally consistent
  companion-action, precondition, reservation, and recovery metadata
- declares the required endpoints for every invocable action, including a
  proposal-only action
- when publishing operational limits, uses the exact supported profile,
  resolves every referenced action and non-control event exactly once, declares
  only positive safe-integer windows and slots, and changes the surface version
  and hash whenever that contract changes
- declares the `at_least_once` delivery contract whenever it publishes an event
  subscription endpoint
- declares every event type and schema so it can be mapped without ambiguity to
  the CloudEvents 1.0.2 ASP binding
- provides `propose` actions or read-only resources

### Grant Issuer Profile

A component conforms to the Grant Issuer Profile when it:

- consumes the exact verified, issuer-authoritative current manifest snapshot
  for the applicable surface lifecycle key and rejects stale, superseded,
  hash-invalid, or unsupported surface semantics
- when accepting an Authorized Surface Projection, possesses and verifies the
  exact base, recomputes both hashes and omission closure, checks the current
  complete projection lifecycle key and expiry, copies the exact projection
  binding into the Grant, and fails without revealing context membership
- authenticates the resource owner and obtains issuer-side consent from the
  exact semantic Grant request, manifest semantics, delegate tuple, effects,
  constraints, and effective data-exposure projection
- rejects the complete closed protocol object when a client embeds an Impact
  Simulation Result or feature identifier in an undefined member, discards a
  detached out-of-band supplement as consent, authority, request semantics, or
  evidence, and independently derives its own consent presentation from the
  verified primary sources
- validates requested actions, locations, scopes, resources, surface mode,
  required companion closure, expiration, budgets, credential-release policy,
  audit requirements, and every selected optional profile before issuance
- when selecting the ASP-over-MCP Binding Profile, copies the exact selected
  manifest `agent_api.bindings` endpoint into Grant `locations`, binds its
  authorization composition to a compatible credential profile and audience,
  and rejects a client-supplied substitute, redirect target, DPoP dual-use
  composition, or dual-use audience mismatch before issuance
- constructs the authoritative Agent Grant Object without adding authority,
  derives only permitted output fields and attenuations, computes `grant_hash`,
  and persists the complete hashing view for the Grant lifetime and audit period
- binds the Grant and Grant Credential to the user, application, exact surface,
  runtime, agent, identity evidence, credential audience, and selected
  credential-binding method
- provides the Action Executor an app-verifiable way to obtain current
  authoritative Grant state; co-location, signed delegation, and authenticated
  introspection are deployment choices, not permission to trust a caller's
  assertion
- when it selects the Pluggable Agent Identity Evidence Profile, independently
  retrieves, digests, parses, verifies, key-binds, status-checks, projects, and
  binds the exact envelope; treats mutable freshness and status as verifier
  state; and performs only explicit fail-closed migration
- when the selected concrete format is the Minimal Agent Passport
  Grant-Issuance Profile,
  independently retrieves, hashes, parses, verifies, status-checks, and binds
  the exact Passport tuple without treating declarations as authority or an
  artifact hash as signature or executable proof
- when it selects the Runtime Identity Profile, derives only server-side
  projections, binds the exact active revision into the Grant and credential,
  and maintains the authoritative identity lifecycle
- when it selects the Remote Processing Privacy Profile, validates the exact
  requested path, derives and hash-binds only its deterministic ceiling, and
  makes no application-verified downstream-compliance claim
- when it selects the Agent Training Use Policy Profile, validates the
  canonical requested set against the complete exposure union, obtains consent
  for the returned subset, preserves every authoritative copy, and makes no
  provider-compliance or unlearning claim
- when it selects the Purpose- and Task-Bound Agent Grant Profile, resolves the
  exact issuer-owned purpose and optional task records for the authenticated
  subject and app, verifies revisions, relationship, active state, policy, and
  lifetime, obtains consent for the exact binding, hash-binds it, and maintains
  its suspension, terminal-revocation, and non-enumeration behavior
- when it selects the Approval Receipt Profile, validates and hash-binds the
  exact per-action producer roles and maximum ages without treating an approval
  receipt as issuance authority
- when it selects Runtime Attestation, performs the issuance-time duties of the
  Grant Issuer in Runtime Attestation Role Requirements below
- preserves required constraints, optional-profile bindings, companion closure,
  member-wise budget attenuation, cumulative lineage accounting, and
  cross-runtime restrictions through renewal, exchange, supersession, and
  child derivation
- denies credential-release authority unless the explicit capability and its
  complete constraints are valid, and always denies it for a proposal-only
  surface
- maintains authoritative active, expired, and revoked Grant state; makes
  revocation converge on the Semantic Grant Revocation Transition; and defines
  an authenticated revocation binding when it does not select the OAuth Grant
  Issuer Profile
- operates the authenticated user-facing active-grant management boundary and
  issues only against a verified manifest that advertises its generic
  issuer-bound management URL
- fails closed before issuance, renewal, exchange, derivation, introspection,
  or revocation confirmation when required manifest, identity evidence,
  appraisal, consent, lineage, or Grant state is unavailable or inconsistent

A Grant Issuer claim does not claim that the component publishes the manifest,
executes actions, delivers events, or produces receipts. Those are independent
role claims even when the same application deployment performs them.

### Action Executor Profile

A protected-resource component conforms to the Action Executor Profile when it:

- consumes the exact verified manifest snapshot and current app-verifiable
  Grant state selected by the request, without trusting a Surface Publisher,
  Grant Issuer, runtime, or caller conformance claim as verification evidence
- when the Grant selects Authorized Surface Discovery, verifies the complete
  Grant projection binding against the retained projected manifest and current
  app-verifiable Grant state without searching its base or another projection
- enforces the pinned surface mode during every Action Request and rejects an
  inconsistent proposal-only inventory before idempotency lookup or any effect
- validates the manifest-pinned `credential_audience` at every
  credential-protected `agent_api` endpoint
- when accepting a new request under the ASP-over-MCP Binding Profile, verifies
  the exact MCP revision, manifest-selected endpoint and authorization
  composition, transport session, negotiated experimental capability, current
  schema-pinned binding view, and deterministic tool-to-action mapping;
  reconstructs the ordinary Action Request without exposing credentials in
  JSON-RPC data; performs every normal application-side Grant, ASP session,
  approval, idempotency, policy, budget, effect, and receipt check
  independently; and persists immutable receipt resources before returning a
  conditionally complete closed result with its deep-equal text copy, without
  deriving authority from MCP authentication, annotations, progress, or
  cancellation
- when returning an exact completed idempotent replay under a retained
  ASP-over-MCP binding view, authenticates the current caller and exact Grant,
  ASP session, action, key, input, and execution tuple; verifies the immutable
  completed record, retained view and schema snapshots, and current disclosure
  authorization; returns only the original result, old `binding_view_id`, and
  receipt resources; and does not rerun admission, reservation, policy, budget,
  effect, charge, or receipt production
- validates active Grant state, `grant_hash`, the exact retained
  `surface_hash`, credential proof, user-runtime-agent-evidence binding, action
  allow-list, scopes, resource constraints, expiration, and current lifecycle
  state for every action
- rejects an Impact Simulation Result presented as Action Request input,
  approval, policy evidence, receipt evidence, or authority
- when the Grant selects the Pluggable Agent Identity Evidence Profile,
  independently revalidates the complete envelope, exact compact hash, current
  key/agent binding, and fresh authenticated lifecycle state before every
  action without treating identity claims as authority
- when the envelope selects the Minimal Agent Passport format,
  independently revalidates the exact Passport tuple and current authenticated
  lifecycle state before every action without treating declarations or
  artifact hashes as signature or executable proof
- when the Grant selects the Runtime Identity Profile, revalidates the exact
  current server-side projection and active claims revision before every action
- when the Grant selects the Remote Processing Privacy Profile, rejects every
  effective application-originated exposure above the exact hash-bound ceiling
  and does not represent the runtime path commitment as verified downstream
  topology
- when the Grant selects the Agent Training Use Policy Profile, enforces the
  complete effective class set at disclosure time and makes no provider-
  compliance or unlearning claim
- when the Grant selects the Purpose- and Task-Bound Agent Grant Profile,
  independently resolves current issuer-owned state at every action, requires
  the exact Grant/session binding and relationship, applies purpose and task
  policy to normalized action semantics before idempotency or effect admission,
  and fails closed without trusting runtime task prose or policy evidence
- when the Grant selects the Approval Receipt Profile, authenticates and
  verifies the complete required role map and maximum age before first effect
  admission; producing an application Approval Receipt additionally requires an
  application-role Receipt Producer claim
- when selecting the Human Elicitation Events Profile, authenticates the
  requester and presenter, retains the exact request and terminal-response
  revision state, validates every session, Grant, surface, context, kind, and
  response binding, and treats any clarification, choice, edit, redline, or
  step-up result only as input to a fresh application policy and action
  decision
- when the Grant selects Runtime Attestation, performs the action-time duties
  of the Action Executor in Runtime Attestation Role Requirements below rather
  than inferring accepted state from hardware, EAT parsing, or a co-located
  Verifier
- creates or accepts an authoritative session record and validates its active
  state, complete tuple binding, and current generation for every action
- creates non-control event subscriptions only as an attenuation of the current
  grant, and binds the logically separate control subscription to the manifest
  issuer and authenticated runtime rather than to an affected grant
- rechecks applicable authority and exposure before delivery and implements
  at-least-once retry, per-stream ordering, acknowledgement, replay, retention,
  explicit gaps, and bounded in-flight delivery
- emits valid CloudEvents 1.0.2 JSON event objects, recomputable
  `aspeventhash` values, and extension attributes consistent with the pinned
  manifest and authoritative subscription or control record
- validates `grant_hash` and binds the grant to the exact verified
  `surface_hash` snapshot
- validates static execution mode, companion authority, execution context and
  hash, preconditions, effect envelope, and any required reservation or
  recovery target before a state change
- rejects any action allow-list that is not closed over required companion
  dependencies in the pinned manifest
- recomputes the complete effective data-exposure projection from the pinned
  manifest and rejects a Grant, request, or disclosure that does not match it
- applies declared redaction before application-originated data crosses the
  application boundary
- enforces cumulative per-target recovery limits independently of request
  idempotency keys
- treats `grant_id` as an identifier, not authority
- supports idempotency for `reserve`, `commit`, `compensate`, and `revert`,
  verifies the pinned input schema, independently checks normalized-wire fixed
  points before lookup or effect, and binds each record to the normalized
  `input_hash` and execution context
- validates and atomically enforces every pinned per-Grant operational action
  window and in-flight slot; resolves exact and conflicting idempotency records
  before new admission; and makes a `rate_limited`,
  `capacity_state_unavailable`, or `service_unavailable` rejection create no new
  idempotency record, budget delta, app receipt, workload, or effect
- enforces pinned per-subscription first-delivery windows without charging a
  retry or replay twice, exceeding the negotiated in-flight window, silently
  dropping an expired queued event, or consuming capacity reserved for control
  events
- durably enforces write, parallel-session, and application-cost budgets across
  the grant lineage and fails closed when ledger state is uncertain
- declares and emits application-authoritative budget control events when an
  event endpoint is present, without fabricating runtime-owned counter state
- when it accepts an application-authoritative budget dimension, advertises
  `budget_state_url` and `budget_query_retention_seconds` and returns
  authenticated, privacy-minimized effective lineage state for `budget.query`
  without exposing ancestor or sibling accounting totals
- when it accepts a Runtime participant in an ASP session, advertises
  `session_control_url`, accepts authenticated `session.pause` with
  `runaway_guard` for the exact active tuple, and also accepts
  `budget_exceeded` when it supports a runtime-authoritative budget dimension
- fences new actions before returning `interrupted`, preserves generation,
  and exactly replays a matching pause; when the manifest declares
  `session.paused_budget`, emits exactly one occurrence for each qualifying
  budget transition, emits none when undeclared, and never emits it for a
  runaway-guard transition
- accepts a guard-aware exact `session.resume` after authenticated lineage
  resolution whether its interrupted state came from the guard pause or
  predated the parent trip, and binds the supplied guard and resolution ids to
  the accepted transition without treating them as detector proof
- invalidates preview evidence and reservations when their grant or surface
  binding becomes invalid
- does not accept `reserve`, `commit`, `compensate`, or `revert` unless the
  deployment composes an application-role Receipt Producer for that action
- rejects expired or authoritatively inactive Grants, fences their sessions and
  outstanding pre-effect work, and fails closed when current Grant or lineage
  state is unavailable

An Action Executor claim does not claim issuance, consent, attenuation,
credential minting, authoritative Grant lifecycle, or receipt production. A
co-located component that performs those functions claims their roles
independently.

### OAuth Grant Issuer Profile

A Grant Issuer additionally conforms to the OAuth Grant Issuer Profile when
it independently satisfies the Grant Issuer Profile and:
- advertises the Agent Grant authorization-details type and supported standard
  OAuth grant types
- uses `agent_api.credential_audience` as the sole OAuth resource indicator and
  issued Grant Credential audience while keeping action `locations` separate
- validates and returns Agent Grant `authorization_details` according to the
  Rich Authorization Request Profile
- preserves the complete selected identity-evidence envelope through authorization, token
  exchange, introspection, credential binding, and Grant hashing
- treats `runtime_identity_profile` only as a request selector and returns the
  exact server-derived runtime identity projection without identity-method
  fallback
- treats `runtime_attestation_requirement` only as a request selector, returns
  the exact stable server-derived attestation binding, preserves its repeated
  credential fields, and keeps mutable appraisal state outside the Grant
- validates the request-only Remote Processing Privacy profile and path, adds
  only the deterministic output ceiling, and preserves the complete effective
  constraint through token responses, introspection, Grant hashing, and consent
- validates the Agent Training Use request profile and canonical class set,
  preserves only a permitted subset through authorization, token exchange,
  introspection, Grant hashing, and consent, and retains an explicit empty set
- validates the exact Purpose Binding request against issuer-owned current
  records, preserves only its defined partial-order attenuation through token
  exchange and child derivation, returns the exact binding through token and
  introspection projections, and links terminal lifecycle to semantic
  revocation
- validates and preserves Approval Receipt requirements through authorization,
  token response, introspection, Grant hashing, and token exchange without
  adding a role, increasing maximum age, or reusing source approval evidence
- implements the OAuth Token Exchange Profile without privilege amplification
- preserves member-wise budget attenuation, lineage accounting, and the
  cross-runtime issuance restriction through authorization and token exchange
- returns the active and inactive Grant Introspection Profile contracts
- returns matching top-level and authorization-details hash projections
- binds RFC 7009 token revocation to the Semantic Grant Revocation Transition
  and emits the authenticated `grant.revoked` control event when an event
  endpoint is declared
- routes user-facing grant management through the same semantic revocation
  transition and preserves its immediate confirmation boundary
- presents authorization-server consent from the exact verified request,
  manifest semantics, and effective exposure projection

### Receipt Producer Profile

A component conforms to the Receipt Producer Profile only for the exact
`producer_role` named by its claim, `application` or `runtime`. It MUST produce
only receipt types assigned to that role and MUST derive every claim from the
role's authoritative decision or observation record. A signing service that
receives already-constructed bytes is not the producer merely because it holds
the signing key.

Every Receipt Producer:

- emits the role-appropriate receipts required by the selected action, Grant,
  approval, and receipt profiles
- emits recomputable `receipt_hash`, `grant_hash`, `surface_hash`,
  `execution_hash`, effect hashes, and `policy_decision_hash` values
- includes the complete typed Policy Decision Object and requires its embedded
  hash to match the receipt's `policy_decision_hash`
- preserves trace id, session id and generation, action id, agent id, runtime
  id, and idempotency key while using a producer-specific span id
- preserves sanitized execution context across the runtime/app receipt edge,
  omits raw execution tokens, and uses `target_receipt_hash` rather than a
  parent edge for recovery causality
- records session id and generation, trace id, and producer span id in the
  corresponding local action and receipt log entry
- binds receipt creation to the immutable idempotency, decision, approval,
  outcome, and accounting records available to its producer role rather than
  constructing authoritative evidence later from mutable logs
- never treats a receipt, signature, proposal, target link, or approval side
  link as authority for an action, retry, commit, or recovery operation

An application-role Receipt Producer additionally:

- emits app receipts for required state-changing actions and denied or failed
  high-risk actions, except for the definite pre-admission `rate_limited`,
  `capacity_state_unavailable`, and `service_unavailable` rejections that the
  Error Model requires to create no application action receipt
- when Approval Receipt is selected, emits immutable application-role approved
  or denied Approval Receipts, binds accepted hashes into the idempotency record
  and app action receipt, and never uses `parent_receipt_hash` for those
  prerequisite side links
- links an app receipt to the verified runtime receipt through
  `parent_receipt_hash` when runtime receipt evidence is required
- records actual effects and distinguishes applied, partial, absent, and
  unknown outcomes without trusting the runtime as effect authority
- records and retains receipt-bound revert evidence for effects advertised as
  reversible
- records application-authoritative budget charges and resulting ledger
  revisions without treating receipt evidence as mutable ledger state

A runtime-role Receipt Producer additionally:

- emits runtime receipts only for runtime-observed agent intent, local policy,
  runtime approval, request construction, and runtime-authoritative budget
  state
- never emits an app receipt or claims that an application effect occurred,
  succeeded, failed, or was reversed merely because it sent a request or
  observed a response
- when Approval Receipt is selected, emits immutable runtime-role approved or
  denied Approval Receipts and preserves their prerequisite side-link semantics
- protects raw execution tokens and credentials and records only their required
  hashes or sanitized projections

Receipt Producer conformance is independent of Grant Issuer, Action Executor,
and Runtime Mediator conformance. The producer MUST nevertheless validate the
authoritative input required for its role and fail closed when that input is
missing, conflicting, or outside the claim boundary.

An application or runtime claims the `asp-jws-detached` Receipt Signing Profile
only when it supports the canonical detached payload, ES256 verification,
authenticated key resolution, grant-pinned signer roles and thumbprints,
historical public-key retention, and the no-downgrade behavior defined above.
It MUST emit every signature required for its producer role and reject required
or present signatures that do not verify.

### Proof-Bound Action Executor Profile

An Action Executor conforms to the Proof-Bound Action Executor Profile when it
independently satisfies the Action Executor Profile and:

- accepts Agent Surface actions only under the Proof-Bound Credential Profile
- verifies the per-request proof-of-possession or bound-channel authentication
- applies the method-specific DPoP, mTLS, or proof-bound session checks defined
  in Grant Verification
- rejects a bearer token, cookie, or reusable session identifier as sufficient
  authority by itself

### Runtime Attestation Role Requirements

Selecting Runtime Attestation does not create a combined conformance role. The
following requirements apply independently to every claimed role:

- the Surface Publisher advertises the framework, endpoint, concrete profiles,
  and exact Verifier-to-profile relationships in the pinned manifest
- the Grant Issuer implements the authenticated single-use challenge, requires
  every concrete profile to bind its nonce, application audience, runtime
  identity binding and revision, proof key, and exact `grant_request_hash`, and
  derives stable Grant and credential bindings only from a current accepted
  appraisal with verified proof-key cross-binding
- the Action Executor checks the current authoritative `accepted` state on
  every action and session resume, independently of any issuer or conformance
  claim, and rejects a stale, inactive, mismatched, or unavailable appraisal
- the Runtime Mediator supports the exact selected concrete profile, protects
  its proof key and raw Evidence, authenticates every challenge and binding,
  and rejects a non-accepted, mismatched, downgraded, or fallback result before
  storing or using a Grant

The Grant Issuer authenticates Attestation Results, verifies complete Target
Environment coverage, applies its own Relying Party policy, and never treats raw
Evidence or an Attester self-assertion as an accepted Result. It maintains the
authoritative mutable appraisal state machine outside the Grant, applies the
strictest freshness input, makes every state other than `accepted` inactive,
and fences affected sessions before another effect. No role falls back to
another profile, Verifier, proof key, older Result, or unattested runtime.

An in-place appraisal refresh is distinct from a material identity, profile,
Verifier, proof-key, or coverage change that requires a new Grant and Consent
Preview. A revoked binding triggers semantic revocation. Every role exposes
outside the Verifier boundary only the privacy-minimized stable binding,
assurance, and coarse authorized state, never raw Evidence, measurements,
reference values, hardware identifiers, or diagnostics.

### Runtime Mediator Profile

An application runtime conforms to the Runtime Mediator Profile when it:

- discovers and validates Agent Surface Manifests
- recomputes `surface_hash` and pins the exact manifest snapshot
- when selecting Authorized Surface Discovery, sends no identity or affordance
  selector, validates a no-redirect closed bootstrap descriptor when the base
  is withheld, verifies the projection and its base when available, partitions
  retained state by the complete local authenticated context and both surface
  tuples, and never represents a base hash alone as proof of attenuation
- independently verifies the exact Agent Passport artifact, signature, issuer
  trust, lifecycle status, and local agent binding under the selected profiles
  before delegation
- distinguishes `document_only` Passport admission from a separately profiled
  and locally verified executable-integrity binding
- when selecting the Runtime Identity Profile, shows every locally authenticated
  facet, re-previews and confirms any initially unresolved server projection,
  rejects a returned projection or credential binding that conflicts with known
  state, and treats every material identity change as stale
- when selecting the Remote Processing Privacy Profile, resolves the complete
  data-bearing path rather than only the controlling runtime, verifies every
  effective class against the expected and returned ceiling, labels downstream
  commitments accurately, and fails closed before disclosure on any unknown or
  changed recipient or enforcement state
- when selecting the Agent Training Use Policy Profile, resolves every source's
  complete class set, presents the permitted and prohibited sets separately
  from retention, enforces the whole-source and downstream-recipient rules,
  treats omission as unspecified, and makes no model-unlearning claim
- when selecting the Purpose- and Task-Bound Agent Grant Profile, presents and
  confirms the exact opaque references and revisions, rejects any returned
  substitution, copies the exact binding into session start, enforces current
  authenticated state locally, and fences work while that state is unavailable
- when selecting Runtime Attestation, supports the exact concrete profile,
  protects its proof key and raw Evidence, authenticates every challenge and its
  runtime, request, audience, and freshness bindings, confirms any initially
  unresolved stable binding and assurance, and rejects a non-accepted,
  mismatched, downgraded, or fallback result before storing or using a Grant
- when claiming the Capability Match Result Profile, emits its closed local
  object with the exact manifest, semantic request, identity, Passport,
  inventory, policy, and preference bindings; treats unknowns as indeterminate;
  and discards stale results before selection or consent
- when claiming the Impact Simulation feature, emits only the exact closed,
  bounded, deterministic local result; includes every requested action or
  suppresses the complete optional result; selects unrequested actions by the
  fixed conservative risk order; projects the exact candidate-wide status and
  decisive blocking reason codes to every requested example; treats unknown
  blocking extensions as indeterminate; derives the exact recovery limitation
  set; keeps hints and concrete resources outside the object; and never uses an
  example as execution, consent, approval, policy, receipt, Grant, or agent
  authority
- obtains explicit user consent before storing a grant
- derives and confirms the local Consent Preview Contract projection before
  sending a grant issuance request, regenerates it after any material change,
  and rejects a returned grant that is not equal to or narrower than the exact
  confirmed request
- when claiming the Risk Explanation UI Hints feature, validates the complete
  closed object, selects one localization with the required fallback, retrieves
  it only from the exact pinned action, renders it as inert labeled publisher
  text alongside canonical machine semantics, and excludes it from matching,
  policy, approval, admission, and agent instructions
- recomputes the grant's effective data-exposure projection, refuses missing or
  inconsistent contracts, and selects only runtime-agent paths that can enforce
  redaction and retention obligations
- mediates agent actions instead of exposing raw authority
- enforces the Session Authority and Lifecycle state machine, including
  complete tuple binding, generation changes on resume, and terminal-state
  rejection
- when selecting the ASP-over-AHP Binding Profile, explicitly negotiates the
  exact profile on an authenticated AHP channel, keeps AHP and ASP session
  namespaces separate, validates monotonic representation bindings and every
  embedded ASP tuple before presentation or dispatch, and fences conflicting
  replay or ambiguous outcomes without deriving authority from UI state
- when selecting the ASP-over-MCP Binding Profile, negotiates MCP
  `2025-11-25` and the exact experimental capability without fallback from the
  preverified manifest endpoint and Grant location, maintains the dedicated
  Streamable HTTP session and update listener, verifies the complete manifest
  resource and schema-pinned pagination-stable binding view, constructs `_meta`
  outside agent control, retains credentials and raw transport results outside
  agent/model context, validates structured results and complete receipts, and
  reconciles every post-dispatch ambiguity under the original ASP idempotency
  identity, including after timeout or cancellation, instead of inferring an
  outcome or retrying blindly
- when selecting the Human Elicitation Events Profile, presents only a
  minimized request on an authenticated user channel, persists exact request
  and terminal-response revision state, validates every session, Grant,
  surface, context, kind, expiry, and verifier binding, withholds
  authentication factors from profile and agent-visible data, and never treats
  a clarification, choice, edit, redline, or step-up result as approval or
  action authority
- denies credential release unless an explicit `credential.release` capability
  and its constraints are satisfied
- preserves parent-runtime mediation for subagents, tools, adapters, remote
  models, and ungranted secondary runtimes
- treats a separately granted child runtime as its own controlling runtime and
  preserves parent linkage, attenuation, and cascade revocation
- implements RAR, Token Exchange, introspection, and revocation processing when
  interacting with the OAuth Grant Issuer Profile
- requests and validates the manifest-pinned `credential_audience` without
  treating it as action or control-operation authority
- implements the Proof-Bound Credential Profile when the application requires
  the Proof-Bound Action Executor Profile
- enforces local policy and approval rules
- when selecting the Approval Receipt Profile, constructs the exact Grant
  requirement projection, obtains and records fresh runtime approvals, stops on
  runtime denial, transmits only the verified runtime side link, and verifies
  the final application receipt role map without treating any receipt as action
  authority
- durably enforces `tool_calls`, `model_tokens`, `runtime_seconds`, and
  `runtime_cost` across the grant lineage, retaining conservative reservations
  when usage is uncertain
- stops matching local work before reporting runtime budget exhaustion through
  an exact, idempotent `session.pause` request and requires authoritative
  application state before any resume
- initializes a durable runaway-guard epoch before agent work, enforces
  positive finite transport, action-repetition, epoch-root, epoch-step,
  root-action, causal-depth, and cycle limits independently of Grant budgets,
  and fails closed when guard state is unavailable
- treats declared operational limits as scheduling ceilings rather than
  authority or availability promises, conservatively accounts fresh dispatches
  and outstanding idempotency tuples across workers, applies the stricter local
  policy, preserves exact idempotency and event-delivery identity while
  refreshing binding-specific per-attempt authentication, and uses bounded
  backoff with jitter without resetting runaway guards
- carries finite lineage-delegate session, root, step, and cycle admission
  guards across new session ids, child Grants, renewal, reconnect, and ordinary
  resume, and does not clear an unresolved parent fence when one session ends
- persists `fenced` before another disallowed scheduling step, preserves
  in-flight outcome reconciliation, requests an exact `runaway_guard` fence for
  every affected or newly observed active session, commits one lineage
  resolution covering every affected session, and requires that resolution
  plus authoritative exact resume before a new generation can start a new
  child epoch
- validates action input against schemas, applies the pinned idempotency
  normalization before approval and hashing, verifies the self-contained input
  schema against `input_schema_hash`, and sends only the fixed-point wire value
  to the app
- validates request mode against the pinned declaration and computes input and
  execution hashes
- presents expected effects and recovery limitations, and binds approval to the
  exact input and preview evidence
- protects raw execution tokens, tracks reservations, and does not treat either
  as authority
- handles stale previews, reservation conflicts, and partial or unknown recovery
  outcomes without blind retry
- records local audit events and emits runtime receipts only when it separately
  claims the runtime-role Receipt Producer Profile
- durably deduplicates event deliveries, acknowledges only after its processing
  decision is stable, preserves opaque cursors, applies explicit gap recovery,
  enforces negotiated event backpressure, and deduplicates before allocating an
  automation root or advancing its runaway guards
- validates the CloudEvents 1.0.2 JSON binding, ASP extension combinations,
  event hash, manifest mapping, schema, authority, and exposure before exposing
  event data to an agent
- durably orders and deduplicates budget control revisions, never exposes a
  core control event as an agent task, and never treats delivery or replay as
  authority for an action, automatic retry, or automatic resume
- uses authenticated `budget.query` with bounded backoff for retryable
  application-owned capacity recovery and rejects any event or query result
  older than its highest retained effective state revision
- computes and validates grant, execution, effect, policy-decision, and receipt
  hashes; propagates session id and generation and W3C-compatible trace context
- records session id and generation, trace id, and producer span id in local
  action and receipt logs
- stops actions when grants are revoked or expired
- provides a local grant view with the trusted application management link,
  freezes local use while revocation confirmation is unknown, and treats
  application state or introspection as authoritative over cached active state

### Agent Adapter Profile

An adapter conforms to the Agent Adapter Profile when it:

- runs under runtime supervision
- does not require raw app credentials
- does not receive a Grant Credential or transfer one to downstream components
- requests app actions through runtime APIs
- does not receive, request, interpret, or forward an Impact Simulation Result
  as agent-visible state or an instruction
- emits typed events
- handles denials and approval waits
- preserves the manifest-declared action id and mode and handles preview,
  reservation, precondition, and recovery errors without selecting stronger
  authority
- preserves session and grant identifiers in audit context
- preserves valid trace ids and creates a new span id for each adapter operation
- when selecting the ASP-over-AHP Binding Profile, translates only the exact
  validated embedded ASP message and control binding, rejects action or tuple
  substitution, and never treats AHP state or a receipt summary as authority
- when selecting the ASP-over-MCP Binding Profile, proposes only a mapped tool
  and schema-valid action input to the Runtime Mediator, never constructs or
  receives the binding `_meta` or credential, and never treats an MCP tool
  annotation, result text, progress event, cancellation, or resource link as
  ASP authority or receipt evidence
- never originates or resolves a Human Elicitation interaction, claims that a
  person answered, or forwards an authentication factor; after the Runtime
  Mediator accepts an exact response, exposes only the minimized,
  type-specific answer required by an independently verified task-purpose and
  Data Exposure Contract, never the profile envelope, verifier-private data,
  or unrelated candidate fields
- never fabricates consent, approval, grant, policy decision, app effect, or
  receipt evidence and never treats a conformance claim as authority
- fails closed instead of blindly retrying when authority, session generation,
  idempotency state, effect outcome, or recovery state is stale or unknown

## Application MVP Mapping

An application implementation can start with a small runtime bridge:

- outbound WebSocket from runtime to control plane
- `runtime.hello`
- typed `session.start`
- normalized `session.event`
- local policy evaluation
- local approvals
- agent adapter boundary

The MVP surface SHOULD begin with a deliberately selected subset of application
affordances rather than an import of the complete route or API inventory. For
example, an application can initially publish `task.read` and
`comment.propose` while keeping account deletion, billing changes, workspace
export, and other operations outside ASP. Each later addition follows the
ordinary manifest version, hash, consent, and Grant rules.

An application that already maintains an OpenAPI or AsyncAPI description MAY
use the import profile to keep those selected declarations near their source
operations. The initial annotation set should remain equally small: leaving an
operation unannotated is the explicit safe default, and the generated diff
should be reviewed as a security-sensitive manifest change before publication.

To support Agent Surface Protocol, the next slices are:

1. Add `AgentSurfaceManifest` TypeScript types and JSON examples.
2. Add `AgentGrant` TypeScript types and validation helpers.
3. Add surface discovery to the demo control plane.
4. Add a grant consent screen in the demo browser UI.
5. Bind session start to a grant id.
6. Add `action.request` and `action.result` events.
7. Assign one static execution mode to every action and split
   `comment.propose` from the `comment.create` commit action.
8. Declare effect envelopes and add preview/precondition schemas for selected
   commit actions.
9. Require manifest-pinned input normalization, idempotency keys, and execution
   hashes for state-changing actions.
10. Add durable grant-lineage accounting for writes, tools, tokens, runtime
    time, parallel sessions, and partitioned cost.
11. Add authenticated budget control events and idempotent `session.pause`
    fencing without exposing control events to agents.
12. Add durable finite retry, repetition, causal-depth, and event-loop guards
    with explicit resolution before resume.
13. Add bounded reservation and recovery actions only where the application can
    enforce their lifecycle and semantics.
14. Produce local runtime receipts and app-visible receipts with execution and
    actual-effect evidence.
15. Integrate Agent Passport verification as an admission precondition.
16. Export and verify passive Portable Replay Bundles for bounded debugging and
    audit without connecting replay validation to live event, session, action,
    approval, or effect paths.

## Example End-to-End Flow

```text
1. App publishes /.well-known/agent-surface.json with `surface_hash`.
2. Application runtime recomputes the hash and pins the exact surface.
3. User chooses "Connect my local agent".
4. Runtime verifies the selected agent's Agent Passport.
5. Runtime derives and the user confirms a local preview from the exact request,
   verified tuple, pinned manifest, effects, exposure contracts, and labeled
   local operator/processing-path assertions, including the exact issuer-owned
   purpose and task references when selected. When it claims Impact Simulation,
   the runtime also shows the complete bounded local action examples and labels
   `covered` as proposed-request coverage rather than execution permission.
6. Runtime sends that exact Agent Grant `authorization_details` request.
7. The app authorization server independently shows consent:
   - app: code.example.com
   - runtime: application-runtime-456
   - agent: local-agent
   - passport: sha-256:<base64url-digest>
   - scopes: pull_request.read, pull_request.comment
   - actions: pull_request.get, comment.create
   - repository: example-org/example-repo
   - purpose: pur_01J2Q7M4K8X5 at rev_3
   - task: tsk_01J2Q7N9C3V6 at rev_7
   - duration: 2 hours
   - budgets: 20 writes, 100 tool calls, 50,000 model tokens, 30 active
     runtime minutes, 2 parallel sessions, and separate runtime/application
     cost partitions
   - commit effects: shared, internal communication
   - commit: requires approval
   - data classes: repository.content, user.identifier
   - retention: 2 hours, delete on grant end
8. User approves a subset or the complete request.
9. App issues or token-exchanges grant_123, its canonical `grant_hash`, and its
   bound Grant Credential after resolving the exact current purpose/task state.
10. Runtime verifies that the result is equal to or narrower than the confirmed
    request, recomputes its exposure projection, and stores the authoritative
    details and credential.
11. App starts a pull-request review session that repeats the exact
    purpose/task binding.
12. Agent reads typed PR context through runtime-mediated resources.
13. Agent proposes a review comment.
14. When declared, runtime requests a dry run and the app returns immutable
    preconditions, expected effects, and time-bounded preview evidence.
15. User or app approves the exact commit input and expected effects; when the
    Approval Receipt Profile is selected, each required producer emits its own
    hash-bound approved receipt.
16. Runtime records its policy decision and action receipt, links any runtime
    Approval Receipt, then sends comment.create with trace context, parent
    receipt hash, idempotency key, execution context and hash, and Grant
    Credential.
17. App verifies current grant, current purpose/task revisions and policy,
    session, surface, decision, input, execution, preview, and complete receipt
    evidence, produces any required application Approval
    Receipt, atomically binds the accepted set to idempotency admission, rechecks
    preconditions, and commits the comment.
18. App returns actual effects and an app receipt with the final role-indexed
    approval links. Runtime and app action receipts form a verified parent-hash
    chain and MAY carry
    detached JWS signatures when required by the grant.
19. User opens the issuer-bound grant management page, inspects the exact
    grant_123 summary, and confirms revocation; the app marks the grant inactive
    before confirming success and invalidates outstanding preview evidence and
    reservations.
20. App emits authenticated `grant.revoked`; runtime stops affected work.
```
