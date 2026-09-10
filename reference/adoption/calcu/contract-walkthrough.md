# Calcu contract walkthrough and implementation decision

Example update (2026-09-08): `contract_example.py` now pins ASP `b2d7e36`, uses
explicit `user_managed`, a fresh example surface version and an unconfirmed
source-specific notice. See the [current design](user-managed-design.md).
The baseline below describes the original walkthrough, not current live support.

Date: 2026-09-06. Non-normative, offline design example.
Baseline: ASP `aa1db9926ef9c17bc440b3a2d76a81bdc95ddfbe`; observed Calcu
`5e5a23f04bad649a23eedaad4f83126b2ec3ff7e`.

## What this delivers, and what it does not

The [applicability decision](mode-and-applicability.md) retains one non-persisted
`calculation.propose` action. This walkthrough materializes its manifest,
schemas, semantic request, illustrative returned Grant and local session
record, plus a consent worksheet. It fixes their cross-object relationships
without extracting more SDK types or implementing another runtime.

Run from the repository root using the existing review dependencies:

```sh
.venv/bin/python -B reference/adoption/calcu/contract_example.py
.venv/bin/python -B -m unittest discover -s reference/adoption/calcu -p 'test_*.py' -v
```

[The example](contract_example.py) prints all objects and computes their exact
JCS/domain-separated hashes; there are no hand-copied digest placeholders. It
does not open a listener, use Codex, read credentials, sign identity, obtain
consent, issue a credential, or change application state. The outer container,
`consent_worksheet` and `session_record_example` are local teaching artifacts,
not newly standardized wire envelopes. Manifest/request/Grant fields follow
the existing contracts, but the deliberately unsupported synthetic identity
makes this **not a valid issuance or live conformance fixture**. The outer
`publishable: false` marker and `manifest_example` name identify a
manifest-shaped teaching object, not a discovery artifact. Do not serve it at
its example `surface_url`: publishing `agent_identity_evidence_profiles` would
claim support for verification/status capabilities that this example does not
implement. A real manifest can advertise only actually implemented profiles.

The sample has a fixed, already expired time window. Its identity artifact is
explicitly not a signed Passport, its key digest is not a public key, and its
`.invalid` verification/status profiles have no implementation. Do not replace
this with an always-success verifier. Successful construction and green tests
must leave `live_path_status` blocked and consent unconfirmed.

## 1. Endpoint trust: no hidden alias

The example chooses `https://127.0.0.1:7443` as its explicit origin. This is a
design value, not a claim that a service currently owns that port.

| Purpose | Exact example value |
| --- | --- |
| Issuer | `https://127.0.0.1:7443` |
| Canonical discovery | `https://127.0.0.1:7443/.well-known/agent-surface.json` |
| Logical credential audience | `https://127.0.0.1:7443/agent-api` |
| Action location | `https://127.0.0.1:7443/agent-actions` |
| Session safety control | `https://127.0.0.1:7443/agent-sessions/control` |
| Grant request / introspection / revocation | The three exact `/agent-grants/…` URLs in `manifest_example.agent_api` |
| Authenticated user Grant management | `https://127.0.0.1:7443/settings/agent-grants` |

For a future random-port demo, bind the listener first, obtain the actual
origin, then construct/version/hash the manifest and obtain fresh consent and
issuance. Do not rehash an already-issued Grant to follow a new port. The
application must maintain the authoritative discovery lifecycle and retire old
issuance state; changing a URL cannot leave an independently active old issuer.

The trusted launcher supplies the exact origin and CA pin to the mediator
outside model/browser-controlled input. TLS must verify that pin and the
`127.0.0.1` SAN; strict Host/path checks and no redirects prevent accidental
endpoint substitution. Port occupancy alone proves no application identity.
A different CA, port, audience or manifest is a new binding decision, never an
implicit `calcu.local` alias.

The audience is not an invocation URL. Only `/agent-actions` appears in Grant
`locations`; the same audience authenticates closed safety operations without
granting them domain-action authority. The app-issued model is identified by
its grant endpoints and documented deployment binding; no invented `auth.type`
enum or OAuth claim is needed. A future implementation must define the
authenticated principal/issuer channel and session start/state carrier as
well as the already-required HTTP session-control operation. A local record
or this endpoint inventory alone does not implement those exchanges.

Required containers are still present: manifest `auth: {}` and `audit: {}`,
plus request/Grant `audit: {}`. Empty objects select no optional OAuth or
receipt/signing requirements; they do not waive authentication or local audit.
The closed identity discovery entry includes `migration_profiles: []` to
explicitly select no legacy migration, rather than omit the required member.

## 2. Exact construction and consent sources

The [generator](contract_example.py) follows this dependency order:

1. Build closed binary-operation input/output schemas. Pin the self-contained
   input schema hash; remote output-schema hosting must independently preserve
   the versioned bytes, since its URL alone does not hash transitive content.
2. Build the full selected manifest inventory: schemas, one scope/action,
   operation family, exposure, identity-profile declarations, required grant
   and session-control URLs, management URL, and no resources/events.
3. Hash the manifest excluding only `surface_hash`. Construct the semantic
   request with the exact delegate, surface tuple, one location/action/scope,
   60-second expiry and `credential_release: {"mode":"deny"}`.
4. Hash the request before any issuer outputs. It contains no `subject`,
   `grant_id`, `grant_hash`, `credential_binding` or `data_exposure`.
5. Illustrate issuer output: authenticated subject, new Grant id, full second
   identity envelope in `credential_binding`, and derived source exposure.
   Hash the complete Grant excluding only `grant_hash`. Raw bearer bytes and
   their server-side verifier stay outside every printed object.
6. Illustrate the complete application-owned session tuple at generation 1.
   Its `active` value is a hypothetical post-start record, not an activation.
   Actual execution must wait for authenticated application `session.state`.

The two identity copies are structurally equal, independently owned values,
not a hash-only replacement. Hashing cannot verify their issuer or lifecycle.
The compact session projection uses exactly
`https://github.com/0al-spec/agent-surface/hash/agent-identity-evidence/v1` from
[Identity Evidence](../../../drafts/modules/authorization.md#agent-identity-evidence-envelope).

**Additional migration finding:** pinned Calcu
[identity.ts](https://github.com/SoundBlaster/Calcu/blob/5e5a23f/server/identity.ts)
uses `…/hash/identity-evidence/v1`, without `agent-`. These domains yield
different hashes for identical envelopes. The generic SDK hash primitive
correctly hashes the caller's supplied domain; it cannot infer the intended
protocol object. Correct Calcu at the future migration boundary, regenerate
compact bindings and freshly issue Grants/sessions; do not accept both domains
as aliases. This PR records and tests the distinction, but changes neither
consumer nor SDK.

The local [Consent Preview Contract](../../../drafts/modules/safe-effects.md#consent-preview-contract)
must expose these values from verified primary sources, not agent prose:

| Visible semantics | Source in the example / live gate |
| --- | --- |
| App, issuer, surface mode/version/hash | `manifest_example`; HTTPS identity and current discovery must verify first. |
| Runtime, agent and complete evidence/profile details | `semantic_grant_request.delegate`; synthetic verification, key and lifecycle are unresolved here, so confirmation cannot proceed. A real Passport preview additionally shows verified name/uid/version/expiry/capabilities and evidence boundary. |
| Exact action, scope, location and operation | The single request allow-lists and pinned action; `propose`, no persistence or companion stages, no effects or per-action approval selected. |
| Credential and constraints | Compatibility Bearer, deny credential release, absolute expiry plus 60-second duration; no Grant budget caps, parent/child grants or receipt requirement selected. Independent safety limits still apply. |
| Exposure and retention | Recomputed single action source, `calculation.sample` classified `private`, no redaction, explicit `user_managed`; no source storage deadline or automatic Grant-end deletion. See the limited sample scope below. |
| Actual processing path | Runtime-local evidence, explicitly not an app-verified claim. Confirm mode support and separately applicable policies; no provider deletion claim or retention probe gate. |

The worksheet is deliberately `not_presented_not_confirmed`. In a real
co-located host, one screen can discharge both runtime preview and issuer
consent only with independently authenticated user context and exact verified
sources for both roles. A matching `grant_request_hash` is necessary binding,
not evidence that a human confirmed it. Any changed endpoint, identity, expiry,
surface, action set or exposure invalidates the prior preview. Reject missing
or unequal identity/exposure projections in the returned Grant before storage.

## 3. Data-flow worksheet: enforce promises, do not infer them

`calculation.sample` is a conservative `private` classification for the fixed
publicly documented `240 * 0.15` fixture. It is **not** the classification of
all arbitrary numbers or free-text tasks: those can encode confidential amounts
or secrets. The future app must define the actual permitted source envelope,
classify its maximum output/error disclosure, and enforce it before replacing
the sample declaration. Neither an empty class set nor a default label solves
that decision.

| Copy / flow | Owner and planned treatment | What is still unproven |
| --- | --- | --- |
| User task: textarea → task host → Codex/provider | User input, not app-originated action output. Disclose the provider path and apply the host's input/privacy policy before submission; never attach ASP authority. | Provider handling and the policy for arbitrary user-entered secrets. |
| Typed operands: adapter → LocalBackend → HTTPS executor | Runtime/app; keep operational payloads out of logs. Authenticate and admit the exact action before calling the engine. | Wire/lifecycle migration; a complete manifest does not update the current executor. |
| Result or structured error: executor → mediator | App-originated exposure. The sample explicitly selects `user_managed`, with no source deletion promise; stricter applicable obligations remain. | Actual result/error maximum classification and pre-delivery enforcement. |
| Tool result: mediator → Codex/provider | Preserve exact source contract and verify mode support before use. No source-level deletion proof is required for this mode alone. | Actual projection/support integration remains absent. No provider deletion/training claim; retention investigation is stopped. |
| Result retained in task UI after completion | Establish whether this is app-owned presentation storage or runtime-controlled plaintext. App-owned storage has a separate policy; a runtime copy remains subject to the Grant contract. | Ownership cannot be changed merely by renaming a component; specify and test the boundary. |
| Logs, crash dumps and audit | Minimize payloads. Independently authorize retention of only necessary hashes/metadata; no raw Grant credential, Passport, task or arithmetic payload in diagnostics. | Concrete audit retention/deletion policy and crash behavior. |
| Durable safety state | Runtime guard records and application session fences, with the fields and lifetime required by the RFC, not a copied transcript. | Durable storage, reconciliation and cleanup tests. Source retention does not remove safety-state requirements. |

Do not advertise `bounded` retention to accommodate an unknown provider: that
still requires a known enforceable bound. Keeping only synthetic local fixture
data makes offline construction possible; it is not a fallback authorization
path for the live demo. The current explicit mode follows the owner decision,
not an invented default; independently applicable route policies still require
design review without reintroducing a provider-retention certification gate.

## 4. Session and safety: estimate before implementation

The [application lifecycle](../../../drafts/modules/authorization.md#session-authority-and-lifecycle)
remains `active / interrupted / cancelled / completed / failed`, independent
of Grant active/revoked/expired state. Accepted start is generation 1; only an
accepted resume increments it. Completion reconciles outstanding actions before
recording `completed`; revoking the Grant afterward is a separate policy step.
Cancel fences new work and does not assert rollback or revoke other sessions.

The first implementation must preserve the
[durable guard contract](../../../drafts/modules/safe-effects.md#runtime-runaway-protection)
across new sessions, reconnects and renewal, not simply persist a per-process
counter. A one-tool-call policy can remain stricter local policy but does not
replace epoch/lineage guards or authenticated app fencing.

The following are **planning estimates**, not measured adoption times or
delivery promises. They assume one experienced developer familiar with Calcu,
existing crypto/TLS libraries, one local host and no production identity work.
Ranges include focused tests but exclude CI wait/review and provider-policy
coordination. The additive range below does not assume unmeasured overlap.

| Work package | Rough effort | Required exit evidence |
| --- | --- | --- |
| Complete manifest/discovery/schema and exact identity/Grant projection migration | 2–4 developer-days | Old abbreviated snapshot rejected; wrong domain/copy/schema/surface rejected; changed snapshot gets fresh consent/issuance. |
| Principal authentication, shared consent UI and Grant management | 2–4 days | Authenticated user/issuer role checks, stale preview rejection, returned projection equality, authoritative revocation confirmation. |
| Application session state and authenticated control | 3–5 days | Atomic fence before acknowledgment; duplicate/conflicting start/transition tests; old/future generations rejected; no terminal resume or invented rollback. |
| Runtime durable epochs/lineage guards and recovery | 4–8 days | Crash/restart does not reset counts; unavailable storage fails closed; renewed/new-session work cannot bypass parent fence; exact resolution/resume tests. |
| Data handling and integrated boundary tests | 2–4 days after policy resolution | No forbidden payload persistence/disclosure; provider path gate; request/response loss and cancellation reconciled; no credentials in model/browser. |

The packages total **13–25 developer-days**, before coordination/review waits,
with low confidence until a small safety-state spike is reviewed. Shared work
may reduce this range, but no overlap reduction has been measured. SDK packaging
can reduce repeated plumbing but does not remove these state/policy obligations.
Production identity, Proof-Bound, receipts and independent interoperability
remain outside this estimate.

## Decision gate and next step

Proceed next with a **bounded safety-state design spike**, not all five work
packages: identify persisted records/atomic boundaries and write restart,
revocation-race and stale-generation cases against one local store. Timebox the
spike separately; stop for a continue/simplify/change-example decision if the
required safety contract dominates the calculator's value.

Before any live contract migration, obtain a concrete exposure/provider policy
and confirm that the mandatory lifecycle cost is acceptable. A reduced profile
would require a separate normative proposal naming the lost guarantee; this
example introduces no exemption. The actionable low-risk correction is the
identity hash domain, to be included in a separately scoped Calcu migration
with fresh issuance, not an in-place rewrite of active state.

## Validation boundary

Eleven [offline tests](test_contract_example.py) check deterministic construction,
schema examples (including `sqrt`/extra-field rejection), correct hash domains,
complete matching identity/exposure copies, absence of issuer-only request
fields, required manifest/request containers, the closed discovery entry,
endpoint distinctions and session tuple coherence. These are fixture
construction assertions, **not** tests that Calcu rejects all these mutations.
JSON Schema does not validate a mathematical result, TLS or a live identity;
raw JSON and finite-number checks remain necessary before runtime validation.
The example hash helper rejects negative-zero values before JCS serialization;
it is still not a raw JSON parser and cannot detect duplicate members or a
lexical `-0` already erased by some earlier parser.
The existing manifest linter can inspect declarations but cannot certify these
objects or their explicitly unresolved operational promises.
