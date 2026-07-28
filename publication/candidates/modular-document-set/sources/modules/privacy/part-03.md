# Privacy Considerations

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
