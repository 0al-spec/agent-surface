# Agent Surface Manifest

## Discovery

Applications SHOULD publish a manifest at:

```text
https://example.com/.well-known/agent-surface.json
```

For multi-tenant SaaS systems, the public well-known manifest SHOULD describe
tenant-independent capabilities. Tenant-specific surfaces MAY be discovered
through authenticated application metadata or through tenant-specific origins,
such as:

```text
https://tenant.example.com/.well-known/agent-surface.json
```

If the manifest contains sensitive tenant-specific affordances, it MUST require
ordinary authenticated app access.

The manifest MUST be served over HTTPS and SHOULD be served with:

```http
Content-Type: application/json
Cache-Control: max-age=300
```

For surface lifecycle decisions, the application MUST define a surface
lifecycle key as (server-authenticated tenant context or a public-context
marker, `issuer`, `app_id`, canonical `surface_url`) and maintain exactly one
issuer-authoritative current discovery snapshot for that key. Tenant context
is server state, never a caller-supplied selector. Except for the Authorized
Discovery Bootstrap Descriptor defined below, an Agent Surface Manifest served
at the canonical URL MUST be the designated snapshot. This designation
is application state shared with the authorization server; it is not inferred
by ordering opaque `surface_version` values. Changing the canonical URL for the
same tenant, issuer, and app id MUST atomically migrate the lifecycle state and
supersede the prior location; it MUST NOT create an independent issuance
history. A cached or retained object can remain valid for an already-issued
Grant without remaining eligible for new issuance.

The snapshot above is the **base snapshot** for its lifecycle key. The
application MAY serve that complete base directly when its inventory is safe
for the authenticated or public context at the canonical URL. When disclosing
the complete base would reveal affordances that are not appropriate for a
particular user, runtime, or agent context, the application MUST either deny
that discovery request or use the Authorized Surface Projection Profile below.
When it uses the profile while withholding the base, it serves the profile's
non-inventory bootstrap descriptor at the canonical URL. It MUST NOT improvise
an unmarked partial manifest.

### Authorized Surface Projection Profile

The optional Authorized Surface Projection Profile defines a minimized
manifest for one server-authenticated authorization context. Its identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1
```

The profile preserves exactly one issuer-authoritative base snapshot for each
ordinary surface lifecycle key. A projection never becomes another base and
never creates an independent issuance history.

A base manifest advertises support only by including the exact identifier above
in `compatibility.authorized_discovery_profiles` and by publishing an absolute
HTTPS `agent_api.authorized_surface_url`. Absence of either member in the base
means that the profile is unsupported. A client learns those values either from
a complete base it is permitted to receive or from the bootstrap descriptor
below. It MUST NOT infer support from an authentication challenge, a
tenant-specific origin, a filtered response, an OAuth scope, or ordinary
application behavior.

When the complete base is not disclosed, an authenticated or public `GET` of
its canonical `surface_url` returns this closed **Authorized Discovery
Bootstrap Descriptor** instead:

```json
{
  "document_type": "agent-surface-authorized-discovery-bootstrap/1",
  "profile": "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1",
  "surface_url": "https://example.com/.well-known/agent-surface.json",
  "authorized_surface_url": "https://example.com/agent-surfaces/authorized",
  "base": {
    "issuer": "https://example.com",
    "app_id": "com.example.project-tool",
    "surface_version": "2026-06-25",
    "surface_hash": "sha-256:<base64url-digest>"
  }
}
```

`document_type` and `profile` MUST equal the literals above. Descriptor
retrieval in version 1 MUST NOT redirect, and `surface_url` MUST equal the exact
canonical HTTPS URL requested by the client.
`authorized_surface_url` MUST be the absolute HTTPS endpoint declared as
`agent_api.authorized_surface_url` in the exact base. `base` MUST identify the
issuer-authoritative current base selected from the server-authenticated
lifecycle key and MUST be structurally identical to the corresponding base
manifest fields. A mismatch between the descriptor and base is
`surface_incompatible` and makes the descriptor unusable for issuance.

The descriptor contains no resources, actions, events, scopes, data classes,
schemas, operational limits, compatibility inventory, policy names, subject or
tenant identifiers, runtime or agent identifiers, entitlement facts, alternate
URLs, or counts. Unknown or additional members are invalid. It is discovery
metadata only: HTTPS and issuer binding remain required, and the descriptor,
its base hash, and possession of its endpoint grant no ASP authority and do not
prove that a later projection is an attenuation.

The descriptor response MUST send `Content-Type: application/json`,
`Cache-Control: private, no-store`, and `Referrer-Policy: no-referrer`. A public
descriptor still uses `private, no-store` so one URL cannot become a shared
cache path when the deployment later requires an authenticated tenant context.
The application selects its lifecycle key only from authenticated server state
or the public marker; a query parameter, path template supplied by the caller,
request header, or untrusted cookie MUST NOT select another tenant, subject, or
base. If no descriptor is available for the applicable context, the endpoint
returns `404 Not Found` without stating whether another base or context exists.

The client copies `profile`, `authorized_surface_url`, and the complete `base`
object verbatim into the projection request below. A descriptor becomes stale
as soon as its base is no longer current. The application MUST compare the
request with current server state and MUST NOT redirect, upgrade, or substitute
the request to another base. A client MAY repeat canonical discovery after a
generic stale failure, but it MUST NOT enumerate candidate base versions or
projection endpoints.

The projection endpoint accepts an authenticated `POST` with
`Content-Type: application/json`. The request is the following closed object:

```json
{
  "profile": "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1",
  "base": {
    "issuer": "https://example.com",
    "app_id": "com.example.project-tool",
    "surface_version": "2026-06-25",
    "surface_hash": "sha-256:<base64url-digest>"
  }
}
```

`profile` MUST equal the identifier above. `base` MUST identify the exact
current base snapshot for the server-derived surface lifecycle key. The request
MUST NOT contain a tenant id, user id, runtime id, agent id, role, group,
affordance name, desired projection id, or another authorization selector. The
application derives the applicable tenant and application subject from its
authenticated session and derives runtime and agent bindings only from the
independently authenticated or verified state used by its Grant flow. A
caller-supplied header, query value, cookie value not issued by the
application, request-body extension, display label, or previous projection is
not such state.

Version 1 does not define a new discovery credential. The deployment uses its
ordinary authenticated application-subject session and independently
authenticated runtime or verified agent state when available. Those mechanisms
identify the projection context but do not themselves grant an ASP action. If
the application cannot authenticate a dimension required by its projection
policy, it fails or uses the explicit `unbound` behavior below; it MUST NOT
trust the requested base tuple as identity evidence.

For this profile, the application defines the **projection lifecycle key** as:

```text
(
  base surface lifecycle key,
  server-side application-subject key,
  authenticated runtime-binding key,
  verified agent-evidence key,
  authorized-discovery profile identifier
)
```

The keys are application state and MUST NOT be serialized into the manifest.
The application maintains at most one current projection snapshot for that
complete key. It MUST use a distinct key when any element differs or is
unknown; it MUST NOT substitute a public marker, another subject, another
runtime, or another agent merely to obtain a cache hit. If the deployment does
not distinguish one of the runtime or agent dimensions before Grant issuance,
it uses an explicit server-side `unbound` marker for that dimension and MUST
re-evaluate the projection when the dimension becomes bound.

A successful response is a complete Agent Surface Manifest with this REQUIRED
top-level member:

```json
{
  "authorized_projection": {
    "profile": "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1",
    "projection_id": "prj_V7pQ2uQ0gVM7mVnR3Dck2w",
    "base_surface_version": "2026-06-25",
    "base_surface_hash": "sha-256:<base64url-digest>",
    "expires_at": "2026-07-21T21:00:00Z"
  }
}
```

`authorized_projection` is a closed object and part of the projected manifest
hashing view. `profile` MUST equal the identifier above. `projection_id` is an
opaque, non-empty, issuer-generated identifier for exactly one materialized
projection snapshot. It MUST contain at least 128 bits of unpredictable output
from a cryptographically secure generator, MUST NOT encode a tenant, subject,
runtime, agent, role, entitlement, or affordance, and MUST NOT be treated as a
credential. `base_surface_version` and `base_surface_hash` MUST equal the exact
base snapshot used to derive the projection. `expires_at` is a required RFC
3339 UTC timestamp with no fractional seconds and MUST be later than issuance.

The projected manifest has its own opaque `surface_version` and computed
`surface_hash`. The publisher MUST allocate a new projection id, surface
version, and surface hash whenever the projection hashing view, base snapshot,
projection lifecycle key, or authorization result changes. It MUST NOT reuse a
base or another projection's surface version for different bytes. The
projection retains the base manifest's `protocol`, `issuer`, `app_id`,
`surface_url`, and `surface_mode` exactly.

Version 1 permits attenuation only by omission:

1. `resources`, `actions`, and non-control `events` MAY contain only complete
   entries structurally identical to entries in the exact base snapshot;
2. every base control event remains present and structurally identical;
3. `scopes` and `data_classes` MAY remove only entries no retained declaration
   references;
4. when base `operational_limits` is present, its `actions` and `events` arrays
   remove every entry for an omitted affordance and retain every other entry
   structurally unchanged; if both projected arrays are empty, the projection
   omits the complete `operational_limits` object;
5. every retained reference, companion-action relationship, schema,
   operational-limit relationship, endpoint requirement, receipt requirement,
   and selected-profile dependency MUST remain closed and valid; and
6. every other base member remains structurally identical except the projected
   manifest's `surface_version`, `surface_hash`, and the added
   `authorized_projection` member.

A projection MUST NOT add an affordance absent from the base; change an id,
schema, scope, risk, approval, execution, effect, exposure, retention,
redaction, endpoint, audit, revocation, or compatibility semantic; weaken
`surface_mode`; or retain a declaration whose references are no longer closed.
Data exposure is narrowed only by omitting whole sources and their now-unused
classes. Version 1 does not permit rewriting a retained source to claim a
smaller class set, stronger redaction, or shorter retention; the publisher must
define a distinct base affordance when those semantics differ.

The Grant Issuer MUST possess and verify the complete exact base before it
accepts a projection for issuance. It recomputes both hashes, applies the
omission rules, verifies that the base and projection are current for their
respective lifecycle keys, and verifies that the authenticated context still
maps to `projection_id`. A runtime that also possesses the base SHOULD perform
the same verification. A runtime that possesses only the projection can verify
its manifest hash and authenticated issuer binding, but MUST NOT represent
`base_surface_hash` alone as a cryptographic proof that attenuation was
correct.

When this profile is selected, the Agent Grant `resource_server` object MUST
contain the following closed object copied exactly from the retained projected
manifest:

```json
{
  "authorized_projection": {
    "profile": "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1",
    "projection_id": "prj_V7pQ2uQ0gVM7mVnR3Dck2w",
    "base_surface_version": "2026-06-25",
    "base_surface_hash": "sha-256:<base64url-digest>"
  }
}
```

The Grant copy omits `expires_at`; projection freshness is checked at issuance,
renewal, exchange, and derivation rather than converted into Grant expiry. The
complete copy is part of the Grant hashing view. The runtime, Grant Issuer, and
Action Executor MUST require exact equality of every copied field with the
retained projected manifest and MUST reject a missing, extra, mismatched,
expired-at-issuance, or unknown projection as `surface_incompatible`. A child Grant can retain the
exact projection only for the same complete projection lifecycle key and can
only attenuate its Grant authority. A different subject, runtime, agent, or
base requires a newly derived projection and a new Grant; copying the prior
projection object never authorizes that transition.

An authorized response MUST send:

```http
Content-Type: application/json
Cache-Control: private, no-store
Referrer-Policy: no-referrer
```

An intermediary, browser HTTP cache, service worker, runtime discovery cache,
or application cache MUST NOT key an authorized response only by URL, bearer
token, projection id, issuer, app id, or base hash. A runtime that retains the
verified object as Grant authority state uses the complete projection cache
key: its local authenticated tenant, subject, runtime, and agent keys plus
`issuer`, `app_id`, canonical `surface_url`, profile, `projection_id`, projected
surface version and hash, and base surface version and hash. Those local
identity keys MUST remain outside agent-visible context, URLs, logs, receipts,
and the manifest. A missing or unresolved key disables reuse. HTTP `no-store`
does not prohibit retaining the exact verified manifest as bounded Grant state;
it prohibits using a general HTTP response cache as that authority store.

If the base is superseded, the projection expires, authenticated context
changes, entitlement state becomes unavailable, or the projection is no longer
current, the application MUST reject new issuance, renewal, exchange, and
derivation through that projection. It MUST NOT fall back to a cached base,
public surface, wider projection, or another context. Existing Grants retain
their exact projected manifest semantics until their own expiry or revocation;
an application policy that intends the authorization change to end existing
authority MUST perform the Semantic Grant Revocation Transition.

Failure responses use `surface_projection_unavailable` and MUST NOT distinguish
an unknown base, hidden affordance, unknown subject, wrong tenant, unauthorized
agent, stale projection, expired projection, or unavailable entitlement state.
They MUST contain no inventory counts, candidate ids, base diff, policy name,
membership fact, or alternate URL and MUST send `Cache-Control: no-store` and
`Referrer-Policy: no-referrer`. Implementations SHOULD make status, response
shape, and observable timing as uniform as operationally practical. A semantic
Grant request for an absent or hidden member continues to use
`invalid_authorization_details`; an Action Request is interpreted only against
its Grant's retained projection and returns `action_unknown` for an absent
action without searching the base or another projection.

After successful transport authentication and syntactic validation, every
profile failure above uses HTTP `404 Not Found` with the common ASP error
envelope and `code: "surface_projection_unavailable"`. Missing or invalid
transport authentication uses the deployment's ordinary `401` or `403`
challenge without projection detail. Malformed JSON, duplicate members, an
unknown member, or a value of the wrong type uses `400 Bad Request` with the
same ASP code and no projection detail. These transport distinctions describe
caller-correctable authentication or syntax state and MUST NOT vary according
to whether a hidden affordance or entitlement exists.

The required fail-closed outcomes are:

| Condition | Required outcome |
| --- | --- |
| Sensitive base is withheld but no valid bootstrap descriptor is available | Return generic `404 Not Found`; do not disclose or partially filter the base. |
| Bootstrap descriptor redirects, contains inventory, has an unknown member, or disagrees with the exact base | Reject it; do not send a projection request or infer another endpoint. |
| Caller supplies a tenant, subject, runtime, agent, role, or affordance selector | Reject the closed request as `surface_projection_unavailable`; do not use the selector. |
| Base hash is unknown, stale, superseded, or mismatched | Return `surface_projection_unavailable`; do not derive from another base. |
| Projection adds or rewrites a base declaration or has incomplete reference closure | Reject it as `surface_incompatible`; do not expose a partial result. |
| Cached projection key lacks or mismatches any authenticated context component | Treat it as a cache miss and perform fresh authenticated discovery. |
| Projection is expired or no longer current at issuance | Reject issuance without revealing which context or entitlement changed. |
| Hidden or nonexistent member is requested for a Grant | Return the same `invalid_authorization_details` outcome and disclosure shape. |
| Existing Grant is presented after the discovery context changes | Enforce the exact retained projection and current Grant state; revoke explicitly when policy requires existing authority to end. |

## Curated Surface Boundary

An Agent Surface is an explicit, application-selected allow-list of affordances
for agent delegation. It is not a requirement to publish the application's full
API, route table, RPC service, MCP tool inventory, UI command set, or
administrative interface. A publisher MAY expose a very small surface, such as
one read resource and one proposal action, while leaving billing, account
administration, bulk export, destructive maintenance, and other application
operations outside ASP.

The curated inventory defines which affordances are eligible for ASP discovery
and delegation; it is not authority by itself. A valid Agent Grant and every
ordinary runtime-side and application-side check remain required.

For every included resource, action, or event, the publisher MUST provide the
complete ASP declaration required by this specification. That completeness
requirement applies to the selected surface inventory and its references; it
does not require completeness relative to any underlying application API. An
underlying operation's existence, visibility, or authentication policy is not
by itself an ASP declaration.

A publisher MUST NOT treat membership in an OpenAPI document, AsyncAPI
document, route table, RPC schema, MCP server, SDK, or UI registry as sufficient
for inclusion in the Agent Surface. It MUST NOT mechanically mirror an
underlying interface merely because those operations exist; every resulting ASP
member MUST independently declare every field and semantic required for its
member type, including the applicable scope, risk, approval, exposure,
execution, idempotency, effect, receipt, endpoint, and lifecycle semantics. A
publisher MAY deliberately map every operation from an underlying interface
only when it explicitly selects each operation and every resulting ASP
declaration independently satisfies this specification. One ASP action MAY
compose multiple application operations, and multiple ASP actions MAY map to
different safety stages of one application operation.

Only declarations in the exact verified manifest snapshot define its ASP
inventory. A runtime, Grant Issuer, Action Executor, or Agent Adapter MUST NOT
synthesize additional ASP resources, actions, events, scopes, or authority from
endpoint naming, ordinary API documentation, SDK metadata, MCP discovery, UI
availability, or a credential's broader capabilities. A request for an action
absent from the Grant's pinned surface remains `action_unknown`; the component
MUST NOT search another API description, call an ordinary application endpoint,
or substitute a similarly named operation.

Publishing a previously omitted affordance is a manifest change and therefore
requires a new `surface_version` and `surface_hash`. It does not add authority
to a Grant pinned to the prior snapshot. The ordinary compatibility,
fresh-consent, renewal, and attenuation rules determine whether a new Grant can
include it. Conversely, adding or removing an underlying application operation
that was never part of the Agent Surface does not by itself change the manifest,
unless that change alters the implementation or semantics of a published
affordance.

Applications and non-agent integrations MAY continue to use ordinary
application APIs under their own authority models. Such access is outside ASP
and MUST NOT be represented as an ASP Grant, ASP action, ASP receipt, or ASP
conformance evidence. The separate runtime-mediation rule still prohibits an
agent, adapter, or subagent from using that alternative path to bypass the
Agent Surface authority boundary.

The boundary has these required fail-closed outcomes:

| Condition | Required outcome |
| --- | --- |
| An API route, RPC method, MCP tool, SDK method, or UI command exists but is absent from the exact manifest snapshot | It remains outside ASP; do not infer or synthesize a resource, action, event, scope, or authority. |
| A semantic Grant request names an action absent from the current verified manifest | Reject issuance; the OAuth profile uses `invalid_authorization_details`. |
| An Action Request names an action absent from the Grant's retained pinned manifest | Return `action_unknown` before idempotency lookup, budget admission, receipt creation, workload dispatch, or effect; do not search another interface or snapshot. |
| A selected affordance lacks required ASP semantics or the publisher cannot enforce its declaration | Reject the manifest as `surface_incompatible`; do not expose the member as partially usable. |
| The application adds a backend operation without publishing a new manifest snapshot | Do not change ASP discovery or any active Grant. |

## OpenAPI and AsyncAPI Import Profile

The optional OpenAPI and AsyncAPI Import Profile lets a publisher generate one
ordinary Agent Surface Manifest from deliberately placed `x-agent-surface`
specification extensions. Its profile identifier is
`https://github.com/0al-spec/agent-surface/profiles/api-import/v1`.
The profile is a publishing-time authoring transform, not an ASP runtime
discovery, authorization, or invocation wire protocol, conformance handshake,
or certification mechanism. An API description, an annotation, importer output
that has not passed complete manifest validation, or an importer report is
never Agent Grant or action authority.

Version 1 consumes the parsed I-JSON data model of exactly one of:

- an OpenAPI Description whose `openapi` value is `3.1.<patch>` or
  `3.2.<patch>`; or
- an AsyncAPI document whose `asyncapi` value is `3.0.<patch>` or
  `3.1.<patch>`.

`<patch>` is one or more ASCII decimal digits. A document containing both
version fields, neither field, another major or minor version, a pre-release
label, or a non-string version is unsupported and MUST fail without output.
The importer does not establish that the remaining source document conforms to
OpenAPI or AsyncAPI; the publisher remains responsible for validating it under
the selected source specification.

The input can originate from JSON or a YAML 1.2 representation only when the
frontend produces the same unambiguous I-JSON data model. A frontend MUST
reject duplicate mapping keys, non-string mapping keys, non-JSON tags,
every number that is not a finite IEEE 754 binary64 value, JSON negative zero,
every mathematically integral number outside
`[-9007199254740991, 9007199254740991]`, every alias, every merge key, and
any string or member name containing an unpaired surrogate or Unicode
Noncharacter forbidden by I-JSON. These restrictions apply even to unannotated
source metadata. Numeric source spellings otherwise identify their parsed
binary64 value; v1 does not retain decimal lexemes. Version 1 does not define
alias expansion or merge precedence, even when a frontend could produce one
deterministic expansion. A frontend MUST NOT resolve ambiguity by last-key-wins
parsing. The reference importer below intentionally accepts strict JSON only.

### Annotation Objects and Locations

The source root MUST contain exactly one `x-agent-surface` root annotation.
That annotation is a closed object containing exactly:

- `profile`, REQUIRED and equal to the profile identifier above;
- `manifest_base`, REQUIRED and containing the complete ordinary manifest
  top-level members other than the four importer-owned output members
  `surface_hash`, `resources`, `actions`, and `events`; and
- `members`, OPTIONAL, a non-empty array of member mappings.

`manifest_base` MUST contain `protocol`, `app_id`, `issuer`, `surface_mode`,
`surface_version`, `surface_url`, `auth`, `agent_api`, `scopes`,
`data_classes`, `audit`, and `revocation` with their ordinary meanings. It MUST
NOT contain any importer-owned output member, even with an empty, null,
placeholder, or allegedly precomputed value. In particular, the importer
always computes `surface_hash`; accepting a caller-supplied value would permit
a stale or unrelated integrity claim.

Every operation annotation is a closed object containing exactly one
non-empty `members` array. Each entry in a root or operation array is a closed
object containing exactly:

- `kind`: `resource`, `action`, or `event`; and
- `declaration`: the complete ASP declaration for that kind, including a
  non-empty `id`.

The root `members` array MAY contain any of the three kinds. It is the explicit
escape hatch for resources, composed actions, events derived from more than one
source operation, and other mappings that are not one-to-one. An absent root
array is equivalent to no root members, but the complete document MUST select
at least one member.

Operation annotations are accepted only at these direct, inline locations:

| Source | Eligible location | Permitted member kind |
| --- | --- | --- |
| OpenAPI | an inline HTTP Operation Object at `/paths/{path-template}/{method}`, where `{method}` is exactly `get`, `put`, `post`, `delete`, `options`, `head`, `patch`, or `trace` | `action` |
| AsyncAPI | an inline Operation Object at `/operations/{operation-id}` whose exact `action` is `send` | `event` |

An annotated Reference Object, OpenAPI callback, webhook, 3.2 `query` or
`additionalOperations` entry, AsyncAPI `receive` operation or trait, reusable
component, or any other location is unsupported in v1. The importer MUST reject
the complete input when the exact `x-agent-surface` name occurs anywhere other
than the root or an eligible inline operation. It MUST NOT ignore a misplaced
annotation, merge siblings into a referenced object, or infer that an
annotation elsewhere was only documentation.

The importer scans only the supplied root document. It MUST NOT fetch a URI,
follow a `$ref`, load another file, expand a callback, apply a trait, contact an
API endpoint, or inspect implementation code to discover more annotations.
An unannotated operation, including one reached through a reference, remains
unselected.

### Projection Algorithm

A v1 publishing pipeline using this profile MUST perform these steps in order:

1. Parse the complete source into one duplicate-free I-JSON object and validate
   the supported source version, exact root profile, annotation shapes, and
   annotation locations.
2. Validate every member as a complete declaration of its stated ASP kind.
   The annotation location supplies build provenance only; it supplies no
   declaration default.
3. Collect root members and eligible operation members. Reject a repeated
   `(kind, declaration.id)` pair even when the declarations are byte-identical.
4. Sort each resulting `resources`, `actions`, and `events` array by ascending
   unsigned lexicographic order of the UTF-8 bytes of `declaration.id`. Array
   order is hash-significant, so a source map's serialization order MUST NOT
   select the output hash.
5. Deep-copy `manifest_base`, insert the three complete arrays, validate the
   resulting object under every ordinary Agent Surface Manifest requirement,
   and verify that all scopes, data classes, schemas, companions, endpoints,
   modes, effects, exposure contracts, and other references resolve.
6. Compute `surface_hash` with the Agent Surface Manifest hashing view in the
   Canonical Object Hash Profile, insert it, and revalidate the complete
   publishable manifest.
7. Emit that one manifest only after every prior step succeeds.

Any parse, profile, version, location, shape, reference, duplicate,
completeness, lint, validation, or hashing failure aborts the complete
projection. The importer MUST NOT emit a partial manifest, retain an earlier
array, skip only the invalid member, or label an unvalidated candidate as
publishable. Import failure is a local publishing-tool error, not an ASP error
response. If an invalid generated object is nevertheless served, ordinary
consumers reject it as `surface_incompatible`.

The importer MUST NOT derive an ASP identifier, scope, resource, schema, risk,
approval mode, execution mode, idempotency rule, effect, exposure class,
retention rule, event direction, endpoint, authentication policy, or authority
from an OpenAPI HTTP method, `operationId`, server, security requirement,
parameter, request or response schema, tag, callback, or from an AsyncAPI
channel, message, payload, `schemaFormat`, binding, or trait. Such source
metadata can help an author prepare an explicit declaration, but it has no
standardized ASP meaning.

The emitted manifest is the only runtime object produced by this profile.
It contains neither `x-agent-surface` annotations nor an implicit source
binding. A publisher MAY add a separately defined collision-resistant
provenance extension to `manifest_base`; if it does, that extension is part of
the manifest hashing view and does not become authority merely because it is
hash-bound.

Changing a projected declaration or any other emitted member changes the
manifest hashing view and requires a new `surface_version` and
`surface_hash`. Reordering source maps or changing an unannotated source
operation does not by itself change the output. The publisher still MUST update
the manifest when an underlying change alters the implementation or semantics
of a published affordance. A previously unannotated operation becomes eligible
for ASP only after an explicit annotation or root mapping produces a new valid
snapshot and the ordinary consent and Grant lifecycle completes.

At issuance and execution time, import provenance has no fallback semantics. A
source operation that is absent from the Grant's pinned generated manifest
remains outside ASP and follows the Curated Surface Boundary:
`invalid_authorization_details` during OAuth issuance and `action_unknown`
before idempotency lookup, dispatch, receipt creation, or effect during action
execution.

## Required Top-Level Fields

```json
{
  "protocol": "agent-surface/0.1",
  "app_id": "com.example.project-tool",
  "issuer": "https://example.com",
  "surface_mode": "standard",
  "surface_version": "2026-06-25",
  "surface_hash": "sha-256:<base64url-digest>",
  "surface_url": "https://example.com/.well-known/agent-surface.json",
  "auth": {},
  "agent_api": {},
  "scopes": [],
  "data_classes": [],
  "resources": [],
  "actions": [],
  "events": [],
  "audit": {},
  "revocation": {}
}
```

`surface_mode` is REQUIRED and MUST be either `standard` or `proposal_only`.
`standard` means that the independently declared action modes and issued Grant
remain the authority boundary; it does not itself authorize a write or require
that the surface expose one. `proposal_only` adds the surface-wide upper bound
defined in Proposal-Only Surface Mode. An implementation that does not
understand the value MUST reject the manifest as `surface_incompatible` rather
than ignore it.

This version defines the exact protocol identifier `agent-surface/0.1`.
Publishers, consumers, conformance claims, and conformance reports MUST compare
that value case-sensitively and MUST NOT substitute an alias or a compatible-
looking version label.

The optional top-level `operational_limits` member declares only the
hash-bound load-planning ceilings defined in Rate Limits and Quotas. Its
absence means that the surface publishes no standardized operational capacity
contract; it MUST NOT be interpreted as unlimited capacity or as permission to
ignore a `rate_limited` response.

The top-level `authorized_projection` member is REQUIRED only for a manifest
produced under the Authorized Surface Projection Profile and is otherwise
forbidden. Its presence selects that exact profile and all of its base binding,
attenuation, lifecycle, caching, anti-enumeration, and Grant-copy rules; a
consumer MUST NOT ignore the member and process the object as an ordinary base
manifest.

## Surface Hash

Every manifest MUST contain `surface_hash` computed with the Canonical Object
Hash Profile over the complete manifest hashing view. A runtime MUST recompute
and verify it before using the manifest for capability matching, consent, grant
issuance, or action validation. The authorization server MUST perform the same
check before embedding the value in a grant.

`surface_version` remains the application's opaque compatibility label;
`surface_hash` identifies the exact manifest object published under that label,
including schema URLs and any explicit schema hashes. It does not commit
transitive schema content for which the manifest declares no content hash. A
runtime MUST key cached surface state by issuer, app id, surface version, and
surface hash. A publisher MUST issue a new `surface_version` whenever the
manifest hashing view changes, including for a backward-compatible addition.
If the same issuer, app id, and `surface_version` appears with a different
`surface_hash`, the runtime MUST treat it as an integrity failure and MUST NOT
silently replace the pinned object.

For an Authorized Surface Projection, that ordinary key is necessary but not
sufficient: the runtime MUST also apply the complete authenticated-context and
base-snapshot cache partition defined by the selected profile. The projected
`surface_hash` commits to `authorized_projection`, while
`base_surface_hash` identifies the derivation source. Neither digest proves
that the projection is an attenuation unless the verifier possesses and checks
the exact base snapshot.

The hash authenticates neither the issuer nor the transport. Runtimes MUST
still enforce HTTPS, issuer and app-id binding, and any local pinning policy.

## Endpoints

The manifest MUST declare enough endpoint information for a runtime to obtain or
validate a grant and invoke typed actions.

This draft separates OAuth-style authorization endpoints from application action
endpoints.

Example:

```json
{
  "auth": {
    "type": "oauth2",
    "authorization_url": "https://example.com/oauth/authorize",
    "token_url": "https://example.com/oauth/token",
    "introspection_url": "https://example.com/oauth/introspect",
    "revocation_url": "https://example.com/oauth/revoke"
  },
  "agent_api": {
    "credential_audience": "https://example.com/agent-api",
    "bindings": [
      {
        "profile": "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1",
        "transport": "streamable-http",
        "mcp_protocol_version": "2025-11-25",
        "authorization_composition": "asp-native",
        "endpoint": "https://example.com/mcp"
      }
    ],
    "grant_request_url": "https://example.com/agent-grants/request",
    "grant_introspection_url": "https://example.com/agent-grants/introspect",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "action_url": "https://example.com/agent-actions",
    "budget_state_url": "https://example.com/agent-budgets/state",
    "budget_query_retention_seconds": 300,
    "session_control_url": "https://example.com/agent-sessions/control",
    "event_subscription_url": "https://example.com/agent-events",
    "event_delivery": {
      "profile": "at_least_once",
      "ack_deadline_seconds": 30,
      "max_in_flight": 32,
      "retention_seconds": 86400
    },
    "receipt_url": "https://example.com/agent-receipts"
  },
  "revocation": {
    "grant_management_url": "https://example.com/settings/agent-grants",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "event": "grant.revoked"
  }
}
```

`agent_api.credential_audience` is REQUIRED and MUST be an absolute HTTPS URI
identifying the application's logical ASP protected resource. The authorization
server issues every Agent Grant Credential with exactly this audience, and each
credential-protected endpoint in `agent_api` MUST reject a credential for
another audience. The URI need not be an invocation endpoint: DPoP still binds
each proof to the actual request method and target URI. One audience lets the
same exact grant tuple authenticate Action Requests and the closed budget and
session safety operations without treating those control operations as granted
actions. Changing it changes the manifest hashing view and requires a new
`surface_version` and `surface_hash`.

`agent_api.bindings`, when present, is a non-empty array of closed
profile-specific application-facing carrier descriptors. A manifest selecting
the ASP-over-MCP Binding Profile contains exactly one entry for that profile
with `transport: "streamable-http"`, `mcp_protocol_version: "2025-11-25"`,
`authorization_composition` equal to `asp-native` or
`mcp-oauth-dual-use`, and an absolute HTTPS `endpoint` without a fragment.
The endpoint MUST NOT contain a query component or URI userinfo. These
restrictions make that exact URI string both the canonical MCP server URI and,
when DPoP is selected, the RFC 9449 `htu` request target for this profile;
implementations MUST NOT drop a query or otherwise normalize it into a
different comparison or credential audience value. A DPoP-bound
Grant requires `asp-native`; `mcp-oauth-dual-use` is valid only under the
Bearer and audience-equality rules in the binding profile. The runtime discovers and verifies
the manifest through ordinary ASP HTTPS discovery before opening MCP; MCP
resource discovery is a verification of that pinned snapshot, not a bootstrap
mechanism. A runtime using an Authorized Surface Projection obtains and
verifies it through the ordinary authenticated projection flow before opening
the projected MCP channel.

The authorization request names the selected MCP endpoint in `locations`, and
the issued Grant MUST retain that exact location. Consequently the endpoint,
profile descriptor, and surface are included in the Grant hashing view through
`locations` and `resource_server.surface_hash`. The Runtime Mediator
authenticates the endpoint's TLS identity and rejects every endpoint-changing
redirect, including a same-origin path change. It never forwards a credential
or proof to a target absent from the Grant's exact `locations`,
and requires initialize metadata, the manifest resource, every mapped call,
and every receipt read to use that exact selected MCP endpoint and the current
active binding session. Stable receipt identity and retention survive the
transport-session replacement defined by the profile. A server-provided URI or successful MCP authorization cannot replace
the manifest-pinned endpoint. For MCP-OAuth dual use, the existing additional
rule requires `credential_audience` to equal this canonical server URI.
Both initialize peers and every transport attempt MUST repeat or implement the
manifest-selected composition exactly; omission, substitution, or fallback is
a binding downgrade and fails before ASP reconstruction.

`agent_api.authorized_surface_url` is REQUIRED exactly when
`compatibility.authorized_discovery_profiles` is present. It MUST be an
absolute HTTPS URL and MUST implement only the authenticated projection
contract defined by the selected profile. It is not an action endpoint, does
not accept a Grant Credential as authority to widen discovery, and MUST NOT be
included in a Grant's `locations` allow-list. Changing the URL changes the base
manifest hashing view, invalidates every derived projection for new issuance,
and requires a new base `surface_version` and `surface_hash`.

When `event_subscription_url` is present, `agent_api.event_delivery` is
REQUIRED. This draft defines only the `at_least_once` profile. Its
`ack_deadline_seconds`, `max_in_flight`, and `retention_seconds` members MUST be
positive integers. `ack_deadline_seconds` is the retry deadline,
`max_in_flight` is the largest negotiable application-event window, and
`retention_seconds` is the conditional replay commitment defined below. A
runtime MAY request a smaller in-flight window. An `event.subscribed` response
MUST repeat the advertised acknowledgement deadline and retention window and
MUST NOT return a larger in-flight window. Changing any of these values changes
the manifest hashing view and requires a new `surface_version` and
`surface_hash`.

`agent_api.budget_state_url` and `agent_api.budget_query_retention_seconds` are
REQUIRED when the application can accept `max_write_actions`,
`max_parallel_sessions`, or the application-cost partition in an Agent Grant.
The URL MUST be absolute HTTPS. The retention value MUST be a positive integer
and fixes how long an accepted `budget.query` idempotency record remains
replayable. Together they expose the authenticated `budget.query` /
`budget.state` contract defined below. An already negotiated Runtime Bridge MAY
carry the identical typed messages, but support remains discoverable through
the manifest and cannot be inferred from an action or event endpoint. Changing
either value changes the manifest hashing view and requires a new
`surface_version` and `surface_hash`.

`agent_api.session_control_url` is REQUIRED when the application accepts a
Runtime participant in an ASP session or a Grant containing `max_tool_calls`,
`max_model_tokens`, `max_runtime_seconds`, or the runtime-cost partition. It
MUST be an absolute HTTPS URL, accept the `runaway_guard` reason and, when the
application supports a runtime-authoritative budget dimension, the
`budget_exceeded` reason, and return `session.state` as defined below. An already
negotiated Runtime Bridge MAY carry the identical messages, but it does not
replace this discoverable HTTP binding. The endpoint uses the Grant Credential
and its required credential-binding proof; fields inside a message are not
authentication. Changing the URL changes the manifest hashing view and requires
a new `surface_version` and `surface_hash`.

Implementations MAY collapse these endpoints when the application already has
equivalent OAuth or API infrastructure, but the manifest MUST make the wire-level
surface discoverable.

## Example Manifest

```json
{
  "protocol": "agent-surface/0.1",
  "app_id": "com.example.project-tool",
  "issuer": "https://example.com",
  "surface_mode": "standard",
  "surface_version": "2026-06-25",
  "surface_hash": "sha-256:<base64url-digest>",
  "surface_url": "https://example.com/.well-known/agent-surface.json",
  "compatibility": {
    "min_runtime": "application-runtime/0.1",
    "schema_dialect": "https://json-schema.org/draft/2020-12/schema",
    "runtime_identity_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/runtime-identity/v1"
    ],
    "remote_processing_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/remote-processing-privacy/v1"
    ],
    "training_use_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/agent-training-use/v1"
    ],
    "purpose_binding_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1"
    ],
    "approval_receipt_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1"
    ],
    "human_elicitation_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/human-elicitation/v1"
    ],
    "authorized_discovery_profiles": [
      "https://github.com/0al-spec/agent-surface/profiles/authorized-discovery/v1"
    ],
    "human_elicitation_replay_retention_seconds": 86400,
    "agent_identity_evidence_profiles": [
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
    ]
  },
  "auth": {
    "type": "oauth2",
    "authorization_url": "https://example.com/oauth/authorize",
    "token_url": "https://example.com/oauth/token",
    "introspection_url": "https://example.com/oauth/introspect",
    "revocation_url": "https://example.com/oauth/revoke",
    "grant_types_supported": [
      "authorization_code",
      "urn:ietf:params:oauth:grant-type:token-exchange"
    ],
    "authorization_details_types_supported": [
      "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant"
    ],
    "token_binding": ["runtime", "agent_identity_evidence"],
    "pkce_required": true,
    "runtime_attestation": {
      "framework": "https://github.com/0al-spec/agent-surface/profiles/runtime-attestation/v1",
      "attestation_url": "https://example.com/runtime-attestation",
      "profiles_supported": [
        "https://verifier.example/profiles/eat-tpm-runtime/v1"
      ],
      "verifiers": [
        {
          "verifier_id": "verifier_7f3a",
          "profiles": [
            "https://verifier.example/profiles/eat-tpm-runtime/v1"
          ]
        }
      ]
    }
  },
  "agent_api": {
    "credential_audience": "https://example.com/agent-api",
    "authorized_surface_url": "https://example.com/agent-surfaces/authorized",
    "bindings": [
      {
        "profile": "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1",
        "transport": "streamable-http",
        "mcp_protocol_version": "2025-11-25",
        "authorization_composition": "asp-native",
        "endpoint": "https://example.com/mcp"
      }
    ],
    "grant_request_url": "https://example.com/agent-grants/request",
    "grant_introspection_url": "https://example.com/agent-grants/introspect",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "action_url": "https://example.com/agent-actions",
    "budget_state_url": "https://example.com/agent-budgets/state",
    "budget_query_retention_seconds": 300,
    "session_control_url": "https://example.com/agent-sessions/control",
    "event_subscription_url": "https://example.com/agent-events",
    "event_delivery": {
      "profile": "at_least_once",
      "ack_deadline_seconds": 30,
      "max_in_flight": 32,
      "retention_seconds": 86400
    },
    "receipt_url": "https://example.com/agent-receipts"
  },
  "scopes": [
    {
      "id": "tasks.read",
      "description": "Read tasks visible to the user."
    },
    {
      "id": "comments.propose",
      "description": "Prepare comments without committing them."
    },
    {
      "id": "comments.write",
      "description": "Create comments in the application."
    }
  ],
  "data_classes": [
    {
      "id": "grant.metadata",
      "classification": "sensitive",
      "label": "Grant metadata",
      "description": "Identifiers and lifecycle state for an Agent Grant."
    },
    {
      "id": "repository.content",
      "classification": "private",
      "label": "Repository content",
      "description": "Content visible to the connected repository user."
    },
    {
      "id": "session.metadata",
      "classification": "sensitive",
      "label": "Session metadata",
      "description": "Identifiers and lifecycle state for an ASP session."
    },
    {
      "id": "user.identifier",
      "classification": "sensitive",
      "label": "User identifiers",
      "description": "Stable account identifiers associated with repository content."
    }
  ],
  "resources": [
    {
      "id": "task",
      "read_scope": "tasks.read",
      "schema": "https://example.com/schemas/task.schema.json",
      "data_exposure": {
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
    }
  ],
  "actions": [
    {
      "id": "comment.propose",
      "scope": "comments.propose",
      "risk": "propose",
      "side_effect": false,
      "approval": "none",
      "idempotency": "required",
      "idempotency_normalization": {
        "profile": "asp-json-normalization-v1"
      },
      "input_hash_profile": "asp-jcs-sha-256",
      "execution": {
        "mode": "propose",
        "operation_id": "comment.publish",
        "persisted": true,
        "commit_action": "comment.create"
      },
      "input_schema": "https://example.com/schemas/comment-propose.input.schema.json",
      "input_schema_hash": "sha-256:<input-schema-digest>",
      "output_schema": "https://example.com/schemas/comment-propose.output.schema.json",
      "data_exposure": {
        "classes": ["repository.content"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    },
    {
      "id": "comment.create",
      "scope": "comments.write",
      "risk": "public_side_effect",
      "risk_explanation": {
        "default_language": "en",
        "localizations": [
          {
            "language": "en",
            "summary": "Publishes a comment for other repository users.",
            "effect_summaries": [
              {
                "effect_id": "comment-publish",
                "summary": "Creates an irreversible shared communication record."
              }
            ]
          }
        ]
      },
      "side_effect": true,
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
      ],
      "approval": "user_or_app",
      "idempotency": "required",
      "idempotency_normalization": {
        "profile": "asp-json-normalization-v1"
      },
      "input_hash_profile": "asp-jcs-sha-256",
      "execution_hash_profile": "asp-jcs-sha-256",
      "execution": {
        "mode": "commit",
        "operation_id": "comment.publish",
        "proposal_action": "comment.propose"
      },
      "input_schema": "https://example.com/schemas/comment-create.input.schema.json",
      "input_schema_hash": "sha-256:<input-schema-digest>",
      "output_schema": "https://example.com/schemas/comment-create.output.schema.json",
      "data_exposure": {
        "classes": ["repository.content"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      },
      "receipt": "required"
    }
  ],
  "operational_limits": {
    "profile": "https://github.com/0al-spec/agent-surface/profiles/operational-limits/v1",
    "actions": [
      {
        "action_id": "comment.create",
        "partition": "grant",
        "windows": [
          {
            "limit_id": "comment-create-per-minute",
            "max_admissions": 20,
            "window_seconds": 60
          },
          {
            "limit_id": "comment-create-per-day",
            "max_admissions": 1000,
            "window_seconds": 86400
          }
        ],
        "in_flight": {
          "limit_id": "comment-create-in-flight",
          "max": 4
        }
      }
    ],
    "events": [
      {
        "event_id": "task.created",
        "partition": "subscription",
        "windows": [
          {
            "limit_id": "task-created-per-minute",
            "max_first_deliveries": 120,
            "window_seconds": 60
          }
        ]
      }
    ]
  },
  "events": [
    {
      "id": "task.created",
      "scope": "tasks.read",
      "schema": "https://example.com/schemas/task-created.event.schema.json",
      "data_exposure": {
        "classes": ["repository.content", "user.identifier"],
        "redaction": {
          "mode": "policy",
          "policy_id": "repository-visible-fields-only",
          "summary": "Only fields visible to the connected repository user are returned."
        },
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    },
    {
      "id": "review.requested",
      "scope": "tasks.read",
      "schema": "https://example.com/schemas/review-requested.event.schema.json",
      "data_exposure": {
        "classes": ["repository.content", "user.identifier"],
        "redaction": {
          "mode": "policy",
          "policy_id": "repository-visible-fields-only",
          "summary": "Only fields visible to the connected repository user are returned."
        },
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    },
    {
      "id": "budget.warning",
      "control": true,
      "schema": "https://example.com/schemas/budget-warning.event.schema.json",
      "data_exposure": {
        "classes": ["grant.metadata"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    },
    {
      "id": "budget.exceeded",
      "control": true,
      "schema": "https://example.com/schemas/budget-exceeded.event.schema.json",
      "data_exposure": {
        "classes": ["grant.metadata"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    },
    {
      "id": "grant.revoked",
      "control": true,
      "schema": "https://example.com/schemas/grant-revoked.event.schema.json",
      "data_exposure": {
        "classes": ["grant.metadata"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    },
    {
      "id": "session.paused_budget",
      "control": true,
      "schema": "https://example.com/schemas/session-paused-budget.event.schema.json",
      "data_exposure": {
        "classes": ["grant.metadata", "session.metadata"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    }
  ],
  "audit": {
    "hash_profile": "asp-jcs-sha-256",
    "receipt_schema": "https://example.com/schemas/action-receipt.schema.json",
    "receipt_signing": {
      "profiles_supported": ["asp-jws-detached"],
      "algorithms_supported": ["ES256"],
      "jwks_uri": "https://example.com/.well-known/agent-surface-receipt-jwks.json"
    },
    "required_fields": [
      "receipt_id",
      "receipt_type",
      "receipt_hash",
      "grant_id",
      "grant_hash",
      "session_id",
      "session_generation",
      "trace_id",
      "span_id",
      "action_id",
      "app_id",
      "surface_version",
      "surface_hash",
      "runtime",
      "actor_agent",
      "subject",
      "idempotency_key",
      "input_hash",
      "execution",
      "execution_hash",
      "policy_decision",
      "policy_decision_hash",
      "timestamp",
      "result"
    ]
  },
  "revocation": {
    "grant_management_url": "https://example.com/settings/agent-grants",
    "grant_revocation_url": "https://example.com/agent-grants/revoke",
    "event": "grant.revoked"
  }
}
```

`compatibility.runtime_identity_profiles`, when present, MUST be a non-empty
array of unique collision-resistant profile identifiers. It advertises the
runtime identity profiles the authorization server can authenticate, project
into an Agent Grant, and revalidate at protected-resource time. A runtime MUST
NOT infer support from an OAuth client registration, a credential format, or a
human-readable deployment label. Absence means that this manifest requires only
the base app-scoped `delegate.runtime` binding; it does not mean that the
runtime is anonymous or attested.

`compatibility.remote_processing_profiles`, when present, MUST be a non-empty
array of unique collision-resistant profile identifiers. It advertises only
profiles whose request commitment, issuer-derived disclosure ceiling, Grant
binding, and protected-resource checks the application implements completely.
A runtime MUST NOT infer support from a Runtime Identity locality, management
posture, network location, provider label, or an application privacy notice.
Absence means that the application makes no Remote Processing Privacy Profile
claim; it MUST NOT be interpreted as either allowing or prohibiting remote
processing.

`compatibility.training_use_profiles`, when present, MUST be a non-empty array
of unique collision-resistant profile identifiers. It advertises only profiles
whose class-set validation, issuer-side attenuation, Grant binding, downstream
enforcement, and consent semantics the application implements completely. A
runtime MUST NOT infer support or policy from a retention mode, privacy notice,
provider label, model setting, or Remote Processing path. Absence means training
use is unspecified, not prohibited and not permitted.

`compatibility.purpose_binding_profiles`, when present, MUST be a non-empty
array of unique collision-resistant profile identifiers. This draft defines
`https://github.com/0al-spec/agent-surface/profiles/purpose-task-bound-grant/v1`.
The member advertises only profiles for which the Grant Issuer and every
protected-resource enforcement point can resolve the exact issuer-owned purpose
and optional task records, enforce their revisions, lifecycle, relationship,
attenuation order, and action policy, and fail closed when current state is
unavailable. Absence means that the application does not support purpose-bound
issuance. A runtime MUST NOT infer support or authority from
`session.start.payload.task`, an A2A task identifier, an application workflow,
human-readable goal text, a label, or a digest.

`compatibility.approval_receipt_profiles`, when present, MUST be a non-empty
array of unique collision-resistant profile identifiers. It advertises only
profiles for which the application can validate per-action Grant requirements,
authenticate complete runtime Approval Receipts, produce application Approval
Receipts, bind their hashes into action evidence, and enforce replay and expiry
rules completely. Advertising a receipt schema or signing algorithm alone is
not support. Absence means the application implements only the base opaque
approval-reference behavior and MUST reject a Grant selecting this profile.

`compatibility.human_elicitation_profiles`, when present, MUST be a non-empty
array of unique collision-resistant profile identifiers and MUST be accompanied
by `compatibility.human_elicitation_replay_retention_seconds`, a positive safe
integer. The two members advertise only profiles the application can negotiate
on an authenticated participant channel, validate under the current surface
and Grant tuple, and retain with the terminal replay guarantees defined by the
Human Elicitation Events Profile. The retention value starts at terminal
acceptance and changes the manifest hashing view. Absence of either member
means that the application does not support Human Elicitation; a runtime MUST
NOT infer support from UI capabilities, an AHP carrier, or receipt behavior.

`compatibility.authorized_discovery_profiles`, when present, MUST be a
non-empty array of unique collision-resistant profile identifiers. This draft
defines only the exact Authorized Surface Projection Profile identifier. The
member MUST be accompanied by an absolute HTTPS
`agent_api.authorized_surface_url`, and that endpoint MUST implement the
profile's closed request, attenuation, lifecycle, anti-enumeration, and cache
rules. Advertising a filtered UI, OAuth scope, tenant endpoint, or generic
authorization service is not support. Absence means that callers can consume
only the ordinary manifest response permitted for their discovery context.

`compatibility.agent_identity_evidence_profiles`, when present, MUST satisfy
the closed discovery contract in the Pluggable Agent Identity Evidence Profile.
The member advertises only atomic combinations the application can retrieve,
independently verify, status-check, project, migrate when named, and bind into a
Grant. A runtime MUST NOT infer production verification support from a source
format version, signature algorithm label, file extension, public key, Agent
Card, DID, validator, or legacy Passport advertisement.

`compatibility.agent_passport_profiles` is the legacy advertisement for the
Passport-specific Grant wire shape. It retains the previous closed-object
contract (`profile`, `hash_profile`, `verification_profiles`, and
`max_artifact_bytes`) only for unexpired legacy Grants and explicit migration.
It MUST NOT be interpreted as support for a new generic envelope. An
application that issues a new `identity_evidence` envelope MUST advertise the
generic member, and one that supports migration MUST name the exact migration
profile in that generic entry. New deployments SHOULD omit the legacy member.

`audit.required_fields` advertises the non-conditional minimum for application
receipts and MUST NOT weaken the Receipt Requirements profile. Conditional
fields such as `parent_receipt_hash`, `output_hash`, approval evidence, error
classification, producer-authoritative budget charges, and required signatures
remain mandatory when their receipt semantics require them even if they are not
repeated in this list.

## Resources

Resources describe data the agent MAY read, reference, or attach to an action.

Each resource MUST include:

- `id`
- `read_scope`
- `schema`
- optional `query_actions`
- `data_exposure`

Example:

```json
{
  "id": "pull_request",
  "read_scope": "pull_request.read",
  "schema": "https://github.example/schemas/pull-request.schema.json",
  "query_actions": ["pull_request.get", "pull_request.list_files"],
  "data_exposure": {
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
}
```

## Actions

Actions are typed operations the app allows agents to request through a runtime.

Each action SHOULD include the following fields as applicable.
`data_exposure` is REQUIRED for every action:

- `id`
- `scope`
- `risk`
- optional `risk_explanation`
- `approval`
- `input_schema`
- `input_schema_hash` for every idempotency-required action and linked dry run
- `output_schema`
- `side_effect`
- `effects` for actions that change domain or coordination state
- `execution`
- optional `capability_hint`
- `idempotency` for side-effecting actions
- `idempotency_normalization` whenever `idempotency` is `required`
- `receipt` for side-effecting actions
- `input_hash_profile` for every idempotency-required action and every action
  requiring receipt- or preview-linked input evidence
- `execution_hash_profile` for `reserve`, `commit`, `compensate`, and `revert`
- `data_exposure`

An action whose receipt chain binds the exact request input MUST set
`input_hash_profile` to `asp-jcs-sha-256`. Other profile identifiers are not
defined by this draft.

An action with `idempotency: "required"` MUST declare an
`idempotency_normalization` object whose `profile` is
`asp-json-normalization-v1` and MUST set `input_hash_profile` to
`asp-jcs-sha-256`, including when the action is a persisted proposal that does
not require a receipt. It MUST also publish `input_schema_hash` for the
self-contained schema document. The optional `defaults` and
`unordered_arrays` members and their fail-closed processing rules are defined
in Idempotency Input Normalization. Other profile identifiers are not defined
by this draft; a runtime that does not understand the declared profile MUST
treat the surface as incompatible for that action rather than guess
equivalence.

Every action MUST declare exactly one standard `execution.mode` and a stable
`execution.operation_id`. The mode, companion-action references, effect model,
and mode-specific schemas are defined by the Action Execution Model. An action
in mode `reserve`, `commit`, `compensate`, or `revert` MUST set
`execution_hash_profile` to `asp-jcs-sha-256`; other profile identifiers are not
defined by this draft.

A publisher MAY declare per-action operational admission windows and
concurrency through the top-level `operational_limits` profile. Such a
declaration is a load-planning ceiling, not action authority, approval, a Grant
budget, an idempotency rule, or a capacity reservation.

Example:

```json
{
  "id": "pull_request.review.submit",
  "scope": "pull_request.review.write",
  "risk": "public_side_effect",
  "risk_explanation": {
    "default_language": "en",
    "localizations": [
      {
        "language": "en",
        "summary": "Publishes a review for other repository users.",
        "effect_summaries": [
          {
            "effect_id": "review-publish",
            "summary": "Creates an irreversible shared communication record."
          }
        ]
      }
    ]
  },
  "side_effect": true,
  "effects": [
    {
      "effect_id": "review-publish",
      "operation": "publish",
      "resource_type": "pull_request.review",
      "visibility": "shared",
      "boundary": "internal",
      "reversibility": "irreversible",
      "domain": "communication"
    }
  ],
  "approval": "user_or_app",
  "idempotency": "required",
  "idempotency_normalization": {
    "profile": "asp-json-normalization-v1"
  },
  "input_hash_profile": "asp-jcs-sha-256",
  "execution_hash_profile": "asp-jcs-sha-256",
  "execution": {
    "mode": "commit",
    "operation_id": "pull_request.review.publish",
    "proposal_action": "pull_request.review.propose"
  },
  "input_schema": "https://example.com/schemas/pr-review-submit.input.schema.json",
  "input_schema_hash": "sha-256:<input-schema-digest>",
  "output_schema": "https://example.com/schemas/pr-review-submit.output.schema.json",
  "data_exposure": {
    "classes": ["repository.content"],
    "redaction": {"mode": "none"},
    "retention": {"mode": "transient", "delete_on_grant_end": true}
  },
  "receipt": "required"
}
```

## Proposal-Only Surface Mode

Applications that are not ready to allow direct agent writes SHOULD expose a
surface with `surface_mode: "proposal_only"`. This value is a hash-bound,
surface-wide upper bound on ASP authority, not an action mode, risk label,
approval shortcut, or grant. `surface_mode: "standard"` leaves the upper bound
to each independently declared action and issued Grant; it does not itself
authorize a write.

A proposal-only manifest MUST contain at least one action whose
`execution.mode` is `propose`. Every action in the manifest MUST use mode
`read` or `propose`, MUST declare `side_effect: false`, and MUST omit `effects`.
Mode `dry_run` is excluded because this draft defines it as validation of a
possible later commit; `reserve`, `commit`, `compensate`, and `revert` are
excluded because they change domain or coordination state. No action in a
proposal-only manifest may declare a companion-action relationship to a
state-changing stage, including `commit_action`, `dry_run_action`,
`proposal_action`, `reservation_action`, `recovery_actions`, `target_actions`,
or a reservation acquisition, renewal, or release action.

A proposal-only action is a typed action whose output is a draft, suggestion,
patch, review body, or other non-committed artifact. The proposal artifact,
its identifier or hash, approval of it, and any receipt are evidence only.
None of them is transferable ASP authority. Another API MAY accept the
artifact only after applying its own independent authentication and
authorization; for example, the application MAY let a human apply it through
an ordinary UI under that human's app-native authority.

Persisting a proposal as a draft is protocol bookkeeping, not a
domain-visible commit. Repeated proposal requests can nevertheless accumulate
duplicate drafts under retries and agent loops. An action that persists
proposals MUST declare `execution.persisted: true` and
`idempotency: "required"`, accept idempotency keys, declare
`idempotency_normalization` using `asp-json-normalization-v1`, set
`input_hash_profile` to `asp-jcs-sha-256`, and deduplicate stored drafts by the
resulting hash. A non-persisted proposal MUST omit `execution.persisted` or set
it to `false`.

A proposal action, including any proposal persistence, MUST NOT mutate the
proposed target object, reserve or exclude a resource, publish or send domain
content, trigger an external operation, or return bearer authority. An
operation with any such effect is state-changing and cannot be declared as
`propose`. The action's Data Exposure Contract governs proposal content
returned to the runtime or agent; it does not govern application-side storage
of agent-supplied draft input. Idempotency, audit, and the application's own
storage and retention obligations still apply to a persisted draft.

The proposal-only bound also excludes direct credential authority. A runtime
MUST NOT request, and an authorization server MUST NOT issue, the separately
authorized `credential.release` capability for a Grant pinned to such a
surface. The semantic Grant request and authoritative Grant MUST contain
`constraints.credential_release` as exactly `{"mode":"deny"}` with no other
member. A contradictory or extension member is invalid rather than an
attenuation. A released credential for a non-Agent-Surface audience would
bypass the claimed bound even though Agent Surface endpoints correctly reject
it.

A runtime MUST validate the complete proposal-only invariant before capability
matching or consent preview. An authorization server MUST validate it before
issuing, renewing, exchanging, or attenuating a Grant, and the application MUST
validate it from the exact retained manifest snapshot before accepting every
Action Request. An inconsistent manifest fails as `surface_incompatible`
before idempotency lookup, budget admission, receipt creation, or any effect.
Because a valid proposal-only inventory contains no state-changing action, a
request for such an action id is `action_unknown`; a request that relabels a
known proposal action is `execution_mode_invalid`. `proposal_required` is
reserved for the separately defined case where a `standard` surface contains a
state-changing action but the effective Grant authorizes only its proposal
companion. No component may silently change a requested mode or substitute a
similarly named proposal action.

Required fail-closed cases are:

| Condition | Required outcome |
| --- | --- |
| Unknown `surface_mode`, missing proposal action, forbidden mode, effect, or companion relationship | Reject the manifest as `surface_incompatible`. |
| Proposal-only semantic Grant request or returned Grant does not contain exactly `constraints.credential_release: {"mode":"deny"}` | Reject issuance; the OAuth profile uses `invalid_authorization_details`. |
| State-changing action id is absent from the pinned proposal-only manifest | Return `action_unknown`; do not search another snapshot. |
| Request repeats `commit` for a manifest-declared `propose` action | Return `execution_mode_invalid`; do not reinterpret the input. |
| Pinned standard manifest contains a commit, but the Grant authorizes only its reciprocal proposal companion | Return `proposal_required`; do not invoke the proposal implicitly. |
| Proposal id, artifact, approval, or receipt is presented as commit authority | Reject before effect under the ordinary Grant, action, approval, and integrity checks. |
| Superseded standard snapshot is used for new issuance after a proposal-only snapshot becomes current | Reject through the authoritative surface lifecycle gate. |

The Grant does not repeat `surface_mode`; its exact
`resource_server.surface_hash` selects the retained manifest and therefore
binds the mode. A scope, action name, proposal result, old Grant, refresh token,
or token exchange MUST NOT override that binding.

An Impact Simulation for a proposal-only surface can project only the exact
known `read` and `propose` action inventory and the proposal-only upper bound.
It MUST NOT fabricate a state-changing companion as a denied example or claim
that the application has no human-operated or non-ASP write path.

The bound forbids application-domain or external write authority through an
ASP action and forbids raw credential release. Closed Grant lifecycle,
revocation, budget-query, session start/pause/resume/cancel, event
subscribe/ack/replay, receipt retrieval, audit, deduplication, and stored-draft
operations remain available under their own authenticated
contracts. They are protocol control or bookkeeping operations, not granted
application actions, and MUST NOT widen a Grant, mutate the proposed target, or
provide a domain-write path. A purported control operation that does so is a
state-changing application action and is invalid on a proposal-only surface.

Example proposal-only fragment:

```json
{
  "surface_mode": "proposal_only",
  "actions": [
    {
      "id": "pull_request.review.propose",
      "scope": "pull_request.review.propose",
      "risk": "propose",
      "side_effect": false,
      "approval": "none",
      "idempotency": "required",
      "idempotency_normalization": {
        "profile": "asp-json-normalization-v1"
      },
      "input_hash_profile": "asp-jcs-sha-256",
      "execution": {
        "mode": "propose",
        "operation_id": "pull_request.review.publish",
        "persisted": true
      },
      "input_schema": "https://example.com/schemas/pr-review-propose.input.schema.json",
      "input_schema_hash": "sha-256:<input-schema-digest>",
      "output_schema": "https://example.com/schemas/pr-review-propose.output.schema.json",
      "data_exposure": {
        "classes": ["repository.content"],
        "redaction": {"mode": "none"},
        "retention": {"mode": "transient", "delete_on_grant_end": true}
      }
    }
  ]
}
```

On a `standard` surface, a proposal action that leads to an ASP commit MUST
declare `commit_action`, and the commit MUST reciprocally identify the
proposal action:

```json
{
  "id": "pull_request.review.submit",
  "execution": {
    "mode": "commit",
    "operation_id": "pull_request.review.publish",
    "proposal_action": "pull_request.review.propose"
  }
}
```

The proposal declaration independently contains:

```json
{
  "id": "pull_request.review.propose",
  "execution": {
    "mode": "propose",
    "operation_id": "pull_request.review.publish",
    "commit_action": "pull_request.review.submit"
  }
}
```

Those companion references are invalid on a proposal-only surface. This
distinction lets early adopters expose useful proposal flows without creating
latent ASP write authority.

## Events

Events let applications notify runtimes and agents about app context changes.

Every event declaration MUST contain a non-empty `id` and an absolute `schema`
URI. The CloudEvents binding uses them without aliasing as `type` and
`dataschema`.

Every non-control event MUST declare a non-empty `scope`. A grant that permits
`pull_request.read` MAY receive `pull_request.updated`, but MUST NOT receive an
unrelated financial, HR, or admin event or an event whose scope is absent. An
unscoped non-control event declaration is an invalid surface, not an event
implicitly available to every grant.

Example:

```json
{
  "id": "ci.failed",
  "scope": "pull_request.read",
  "schema": "https://example.com/schemas/ci-failed.event.schema.json",
  "data_exposure": {
    "classes": ["repository.content"],
    "redaction": {"mode": "none"},
    "retention": {"mode": "transient", "delete_on_grant_end": true}
  }
}
```

Grant constraints filter events the same way they filter actions: a grant
constrained to one repository SHOULD NOT receive events about other
repositories, even when the event scope matches.

An event declaration MAY set `control: true` only for an application control
event whose delivery authority and closure are defined by this specification or
another profile understood by the runtime. A control event omits `scope`; it is
not authorized by the affected grant. This draft defines `budget.warning`,
`budget.exceeded`, `session.paused_budget`, and `grant.revoked` as core control
events. A manifest that advertises one of them MUST list it in `events` with
`control: true` and a `data_exposure` contract.

`grant.revoked` is an application control event rather than an event authorized
by the revoked grant. Its payload, authentication, and processing requirements
are defined in the OAuth Grant Revocation Profile.

The three budget-related control events are application events. Their producer
MUST be the application bound by the manifest `issuer`; a runtime MUST NOT
fabricate them from its local counters because the CloudEvents `source` binding
would falsely attribute that state to the application. Their payload and
session-fencing requirements are defined in Budget Control Events.

A publisher MAY declare a first-delivery throughput ceiling for a non-control
event through `operational_limits`. Event retry, replay, retention, negotiated
`max_in_flight`, and runtime-directed `event.flow` remain governed by Event
Delivery Semantics and are not replaced by that planning declaration. Core
control events MUST NOT be subject to an operational-limit entry.

## Rate Limits and Quotas

The optional Operational Limits Profile publishes deterministic upper ceilings
that a runtime can use to plan Action Requests and application-event intake.
Its identifier is:

```text
https://github.com/0al-spec/agent-surface/profiles/operational-limits/v1
```

`operational_limits` is a closed object containing exactly `profile`, `actions`,
and `events`. `profile` MUST equal the identifier above. `actions` and `events`
are arrays, at least one of which is non-empty. An action or event id appears at
most once in its respective array, resolves exactly in the same manifest, and
every `limit_id` is a non-empty string unique across the complete object.
Unknown members, duplicate ids, unresolved references, an unsupported profile,
or an invalid target make the surface `surface_incompatible`.

An action limit entry has this closed shape:

```json
{
  "action_id": "comment.create",
  "partition": "grant",
  "windows": [
    {
      "limit_id": "comment-create-per-minute",
      "max_admissions": 20,
      "window_seconds": 60
    }
  ],
  "in_flight": {
    "limit_id": "comment-create-in-flight",
    "max": 4
  }
}
```

`partition` MUST be the literal `grant`. `windows`, when present, is a
non-empty array of closed objects containing `limit_id`, `max_admissions`, and
`window_seconds`. `in_flight`, when present, is a closed object containing
`limit_id` and `max`. At least one of `windows` or `in_flight` is REQUIRED.
Every numeric value is a positive I-JSON safe integer. Every referenced action
MUST declare `idempotency: "required"`, so one durable logical record identifies
the window admission and any slot across retry and reconciliation. A short
window describes a rate ceiling; longer conjunctive windows express operational
quotas without calendar, timezone, or reset-boundary ambiguity.

For one authoritative request time `t`, a window counts distinct new logical
admissions in the half-open monotonic interval `(t - window_seconds, t]`. The
application MUST NOT admit the request when doing so would make the count exceed
`max_admissions`. Every applicable window is conjunctive. The partition key is
the server-selected tuple `(issuer, app_id, surface_hash, grant_hash, action_id)`;
no caller-supplied subject, tenant, Grant id, or resource key can select another
partition. `in_flight.max` counts distinct admitted idempotency records without
an authoritative terminal outcome. Connection loss, timeout, an unknown
effect, or a caller assertion does not release a slot; reconciliation or an
authoritative terminal result does. The application uses one logically
consistent monotonic duration source for each partition and MUST fail closed as
`capacity_state_unavailable` without resetting or guessing when authoritative
limiter state is unavailable.

Each successful admission durably records its `limit_id` and elapsed-time
evidence with, or atomically linked to, the idempotency record until every
applicable window has expired; slot state remains until the authoritative
terminal outcome. A distributed deployment MUST serialize competing admissions
through one authoritative state machine. After restart, failover, clock
rollback, or uncertain elapsed time, it retains possibly live admissions
conservatively until it can prove expiry. It MUST NOT reset a window or slot
because process-local monotonic state was lost.

An event limit entry has this closed shape:

```json
{
  "event_id": "task.created",
  "partition": "subscription",
  "windows": [
    {
      "limit_id": "task-created-per-minute",
      "max_first_deliveries": 120,
      "window_seconds": 60
    }
  ]
}
```

`partition` MUST be the literal `subscription`. `windows` is REQUIRED and is a
non-empty array of closed objects containing `limit_id`,
`max_first_deliveries`, and `window_seconds`, all with the same string and
positive-safe-integer requirements above. The partition key is
`(issuer, app_id, surface_hash, subscription_id, event_id)`. A window counts
only the first transmission of a new stable `delivery_id`; retransmission and
replay of that delivery consume no new first-delivery unit. The negotiated
event in-flight window remains the only core event-concurrency limit.

Before first transmission, the application atomically persists the delivery
record, its first-delivery admission marker and elapsed-time evidence, and every
window update. A crash after that transaction is treated as an admitted first
delivery even when the application cannot prove that bytes reached the runtime;
the next transmission is a retry of the same `delivery_id`. A crash before the
transaction sends nothing. Uncertain or unavailable window state queues the
delivery fail closed and never creates an uncharged alternate identity.

The application is the enforcement authority. It MUST atomically evaluate all
applicable windows and any action in-flight slot with creation of the new
logical admission; partial acquisition is forbidden. A runtime SHOULD use each
declared action window as a conservative local scheduling ceiling across every
worker that can dispatch under the same Grant. Such a scheduler uses its own
monotonic sliding history and tentatively counts each fresh logical dispatch
until a definite pre-admission rejection proves that no admission occurred; an
ambiguous outcome remains counted until reconciliation or local window expiry.
For `in_flight.max`, the runtime MUST maintain one local outstanding set keyed
by complete idempotency binding across every such worker. It acquires one
tentative slot before first dispatch, reuses that slot for exact retries, and
releases it only after a definite pre-admission rejection or authoritative
terminal reconciliation. Timeout, connection loss, or an ambiguous outcome
retains the slot; uncertain local slot state MUST NOT be treated as available.
These planning counters and slots neither duplicate application authority nor
prove that capacity is available. A declaration is not a Grant, an SLA, a
promise that the next request will succeed, or permission to exceed local
policy.
Application-authoritative adaptive, anti-abuse, or emergency controls MAY be
stricter without a surface-version change. They MUST NOT be represented as a
wider declared ceiling or used to expose another Grant, subscription, tenant,
or caller's occupancy. The standardized partition is a planning boundary, not
a promise that Grant rotation bypasses independent subject- or tenant-level
defenses.

A new Grant hash or event subscription intentionally starts a new standardized
partition. Neither the profile nor a capacity response authorizes creation,
renewal, exchange, or churn of those objects. An application that must preserve
anti-abuse or commercial quota across such lifecycle changes enforces a
separate server-selected lineage, subject, or tenant policy and reports no
cross-partition counts through ASP.

For an Action Request, the application validates current authority, session,
surface, schema, normalized input, and the complete idempotency binding before
a new operational admission. An exact completed replay returns the original
immutable result and receipt reference without consuming another window unit
or slot. An exact in-progress replay refers to the same record and slot; it does
not start a second effect. Conflicting reuse remains `idempotency_conflict` and
MUST NOT be hidden by `rate_limited`.

A fresh operational rejection occurs before a new idempotency record, budget
reservation or charge, app receipt, action effect, or application workload is
created. A runtime receipt already finalized before dispatch remains truthful
runtime evidence, but the application MUST NOT fabricate an app action receipt
for a request it never semantically admitted. Perimeter throttles for malformed,
unauthenticated, or abusive traffic are independent security controls and MUST
NOT use caller-provided identifiers to debit another authenticated partition.

When an event first delivery cannot be admitted, the application queues the
eligible immutable projection within the effective retention window. It does
not allocate a different delivery identity, advance the cursor silently, or
consume control-event capacity. Expiry before first delivery produces the
ordinary authenticated `event.gap`; an operational limit never converts
at-least-once delivery into silent loss.

Changing `operational_limits` changes the manifest hashing view and requires a
new `surface_version` and `surface_hash`. A Grant remains pinned to its retained
surface snapshot. A stricter current defensive throttle can deny work under an
older snapshot, but it does not rewrite the old Grant, become a Grant caveat, or
authorize use under a newer surface.

## CloudEvents 1.0.2 Event Binding

The ASP core event format is the CloudEvents 1.0.2 information model serialized
with the CloudEvents JSON Event Format 1.0.2. Every non-control and control event
delivered by this profile MUST be a valid CloudEvent with `specversion` equal to
the literal `1.0`. CloudEvents defines the interoperable occurrence envelope;
ASP continues to define grant authority, exposure, subscription, delivery,
acknowledgement, replay, and control-event semantics.

The core mapping is:

| ASP meaning | CloudEvents member | ASP requirement |
| --- | --- | --- |
| event identity | `id` | REQUIRED non-empty string; stable across retries and replay |
| application event source | `source` | REQUIRED absolute URI equal to the pinned manifest `issuer` in this core profile |
| manifest event id | `type` | REQUIRED exact match to one declared `events[].id` |
| CloudEvents version | `specversion` | REQUIRED literal `1.0` |
| occurrence time | `time` | REQUIRED RFC 3339 timestamp for the occurrence, not a retry or delivery time |
| declared event schema | `dataschema` | REQUIRED absolute URI exactly equal to the matched declaration's `schema` |
| payload media type | `datacontenttype` | REQUIRED literal `application/json` |
| authorized, redacted payload | `data` | REQUIRED JSON value conforming to `dataschema` |
| application resource key | `subject` | OPTIONAL non-empty string scoped by `source` and covered by exposure rules |

The core profile does not permit `data_base64`, CloudEvents batch mode, or a
non-JSON data content type. A future profile can add those representations only
with explicit schema, exposure, hashing, acknowledgement, and replay rules.
Omitting `datacontenttype` is valid in generic CloudEvents JSON, but is invalid
in ASP because an explicit media type prevents translation ambiguity.

The pair `(source, id)` identifies one immutable ASP event occurrence. The same
pair MUST carry the same `aspeventhash` wherever it is delivered. If
authorization, resource filtering, redaction, or another material member causes
two subscribers to receive different projections of one underlying application
occurrence, the application MUST assign distinct event ids. It MAY reuse one id
across subscriptions only when the complete occurrence hashing view is equal.

CloudEvents `id`, `source`, `type`, `subject`, and extension attributes are
descriptive context, not authority. A runtime still authenticates the channel,
subscription, grant or control binding, and current manifest before acting on
the event.

## ASP CloudEvents Extension Attributes

ASP defines the following CloudEvents 1.0 extension attributes. Their names use
the CloudEvents lower-case attribute namespace and their values use the
CloudEvents type system.

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `aspscope` | String | REQUIRED for non-control; absent for control | Exact scope from the matched manifest event declaration. |
| `aspcontrol` | Boolean | REQUIRED | `false` for grant-authorized application events; `true` only for a defined control event. |
| `aspsurfacehash` | String | REQUIRED | Exact pinned manifest hash used to interpret `type`, schema, scope, and exposure. |
| `aspeventhash` | String | REQUIRED | `asp-jcs-sha-256` hash of the immutable occurrence view. |
| `aspsubid` | String | REQUIRED on delivery | Bound Event Delivery subscription id. |
| `aspdeliveryid` | String | REQUIRED on delivery | Stable per-subscription delivery id. |
| `aspattempt` | Integer | REQUIRED on delivery | Positive transmission attempt, starting at `1` and increasing by one. |
| `aspstream` | String | REQUIRED on delivery | Ordering stream assigned by the application. |
| `aspsequence` | Integer | REQUIRED on delivery | Positive per-stream sequence from Event Delivery Semantics. |
| `aspcursor` | String | REQUIRED on delivery | Opaque replay position accompanying this delivery. |
| `aspaudience` | String | REQUIRED for control; absent for non-control | Authenticated runtime id targeted by the control event. |
| `aspsessionid` | String | conditional | Session correlation when the occurrence belongs to a specific ASP session. |
| `aspsessiongen` | Integer | conditional | Positive generation paired with `aspsessionid`. |

`aspsessionid` and `aspsessiongen` MUST appear together or both be absent. They
are correlation context and MUST match the authoritative session record when a
current session is required; they never resume or create a session. A control
event has `aspcontrol: true`, omits `aspscope`, and carries `aspaudience`. A
non-control event has `aspcontrol: false`, carries `aspscope`, and omits
`aspaudience`. Null does not satisfy any ASP-required attribute.

Every ASP Integer extension MUST be in the CloudEvents signed 32-bit range and,
where defined as positive, between `1` and `2147483647` inclusive. Before an
attempt, stream sequence, or session generation would overflow, the authority
MUST end the affected delivery, subscription, or session and allocate a new
identifier. It MUST NOT wrap or reset the value under the same identifier.

When observability context is present, the event uses the standard CloudEvents
Distributed Tracing `traceparent` and optional `tracestate` extension
attributes. It MUST NOT define duplicate `asptraceid` or `aspspanid`
projections. Trace attributes remain diagnostic and never participate in grant,
session, subscription, or delivery authority.

To compute `aspeventhash`, the producer applies the Canonical Object Hash
Profile to the complete CloudEvent while omitting `aspeventhash`, the
delivery-only attributes `aspsubid`, `aspdeliveryid`, `aspattempt`, `aspstream`,
`aspsequence`, and `aspcursor`, and the diagnostic `traceparent` and
`tracestate` attributes. All other core and extension attributes and the
complete `data` value are included. The consumer MUST recompute the hash before
acknowledging the event as processed.

Only the authenticated application delivery authority may set or change the
excluded delivery attributes, and the receiver still validates them against
subscription state. An intermediary may handle the excluded diagnostic
attributes only as permitted by the CloudEvents Distributed Tracing extension.
Adding, removing, or changing any other member requires a new `id` and
recomputed `aspeventhash`; otherwise the result is an integrity failure.
Unknown extension attributes are never interpreted as ASP authority and MUST
NOT substitute for a required ASP attribute.

## Serialization and Transport Mapping

An HTTP event endpoint conforming to this profile MUST support CloudEvents JSON
structured content mode. Its request or delivery body is the complete
CloudEvent JSON object and its media type is `application/cloudevents+json`.
Transport authentication, Grant Credentials, proof-of-possession, and
acknowledgement responses remain outside the CloudEvent body.

The Runtime Bridge JSON binding carries the same object as the complete
`payload` of the `event.delivery` frame:

```json
{
  "type": "event.delivery",
  "payload": {
    "specversion": "1.0",
    "id": "evt_01J2FAILED",
    "source": "https://code.example.com",
    "type": "ci.failed",
    "time": "2026-06-25T16:20:00Z",
    "subject": "example-org/example-repo/pull/13",
    "datacontenttype": "application/json",
    "dataschema": "https://code.example.com/schemas/ci-failed.event.schema.json",
    "aspscope": "pull_request.read",
    "aspcontrol": false,
    "aspsurfacehash": "sha-256:<base64url-digest>",
    "aspeventhash": "sha-256:<event-digest>",
    "aspsubid": "sub_01J2EVENTS",
    "aspdeliveryid": "delivery_01J2FAILED",
    "aspattempt": 1,
    "aspstream": "repository:example-org/example-repo",
    "aspsequence": 42,
    "aspcursor": "opaque:position-after-42",
    "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    "data": {
      "repository": "example-org/example-repo",
      "pull_request": 13,
      "check": "tests"
    }
  }
}
```

The frame type is Runtime Bridge routing metadata; `payload` itself is the
CloudEvent. A direct HTTP structured delivery sends that payload without the
outer frame. Both forms have identical ASP event and delivery semantics, and an
acknowledgement repeats the values of `aspsubid`, `aspdeliveryid`, and
`aspcursor` as `subscription_id`, `delivery_id`, and `cursor`.

CloudEvents HTTP binary content mode and JSON batch mode are outside the core
ASP binding. An implementation MUST NOT silently translate a structured ASP
event into either form unless a future negotiated profile defines lossless
placement of all required attributes and per-delivery acknowledgement state.

## Binding Validation and Security

Before accepting or acknowledging an ASP CloudEvent, a runtime MUST:

1. reject duplicate JSON members and validate the CloudEvents 1.0 required
   attributes, JSON types, and structured-format rules;
2. require the ASP core members and extension-presence combinations above;
3. require `source` to equal the authenticated pinned manifest issuer and
   `type`, `dataschema`, `aspscope`, and `aspcontrol` to match exactly one event
   declaration;
4. for a non-control event, require `aspsurfacehash` and all delivery attributes
   to match the authenticated grant-bound subscription; for a control event,
   require the delivery attributes to match the issuer/runtime-bound control
   record, then validate `aspsurfacehash` independently against the retained
   affected Grant and manifest snapshot under that event's rules;
5. validate `data` against the exact declared schema, apply the complete
   current grant and resource-filter projection for non-control events, and
   enforce the Data Exposure Contract over `data` and every context attribute
   that contains application, user, tenant, or resource semantics;
6. recompute `aspeventhash`, enforce one hash per `(source, id)`, and apply
   delivery deduplication before exposing the event to an agent.

A malformed CloudEvent or ASP extension combination fails as `schema_invalid`.
A supplied event hash, surface hash, issuer, or immutable binding mismatch fails
as `integrity_mismatch`. Reuse of `(source, id)` with a different valid event
hash, or reuse of `aspdeliveryid` with different source, id, event hash, stream,
sequence, or cursor, fails as `event_delivery_conflict`. None of these failures
MAY fall back to trusting the event payload, a cursor, or a transport header as
authority.

For a direct single-hop HTTP delivery, CloudEvents `traceparent` and
`tracestate`, when present, MUST carry the same trace information as their HTTP
header counterparts. A mismatch makes the tracing binding `schema_invalid`; it
does not select alternate authorization state. On a multi-hop path the
CloudEvents attributes preserve the starting event trace while protocol headers
describe the current hop, as defined by the CloudEvents Distributed Tracing
extension.

Context attributes can disclose data even when `data` is minimal. The
application MUST apply declared redaction before placing semantic values in
`subject`, application-defined extensions, tracing attributes, or other
occurrence metadata, and MUST declare every disclosed data class. Required ASP
delivery metadata MUST be opaque or minimally identifying and remains subject
to the same access-control and retention boundary even when it adds no event
data class. CloudEvents compatibility never permits an intermediary to route an
event to a runtime, agent, subject, or grant that ASP would not authorize.

## Event Subscription Authority

An event subscription is an application-authoritative delivery record bound to
one authenticated runtime and one exact grant tuple. It does not widen the
grant and is not a session. A non-control subscription MUST bind:

- `subscription_id`, application issuer, and pinned `surface_hash`
- grant subject, `grant_id`, and `grant_hash`
- runtime id, agent id, and identity-evidence hash
- the accepted event type allow-list and resource-filter projection
- negotiated delivery profile, acknowledgement deadline, in-flight window, and
  retention window
- the pinned Operational Limits Profile entries for every accepted event type,
  when the manifest declares them

The runtime requests a subscription through the manifest
`event_subscription_url` or an equivalent authenticated bridge operation:

```json
{
  "type": "event.subscribe",
  "payload": {
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "identity_evidence_hash": "sha-256:<base64url-digest>",
    "requested_events": ["ci.failed", "pull_request.updated"],
    "max_in_flight": 16
  }
}
```

The application MUST select the subject and resource filters from the
authoritative grant; caller-supplied identifiers or filters cannot replace
that state. It MUST reject an event type absent from the pinned manifest, a
type outside the grant's scope or constraints, a mismatched tuple or hash, and
an in-flight request above the advertised maximum. It MAY accept a strict
subset but MUST NOT add an event type. An unsuccessful request creates no
subscription.

The application returns the accepted immutable binding and an initial opaque
cursor representing the position before any delivery:

```json
{
  "type": "event.subscribed",
  "payload": {
    "subscription_id": "sub_01J2EVENTS",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "identity_evidence_hash": "sha-256:<base64url-digest>",
    "accepted_events": ["ci.failed", "pull_request.updated"],
    "profile": "at_least_once",
    "ack_deadline_seconds": 30,
    "max_in_flight": 16,
    "retention_seconds": 86400,
    "cursor": "opaque:initial-position"
  }
}
```

Before both enqueue and delivery, the application MUST recheck current grant
state, event scope, resource constraints, surface binding, and the effective
Data Exposure Contract. A queued event that no longer passes MUST NOT cross the
application boundary. Changing the accepted event set, tuple, grant hash,
surface hash, or resource-filter projection requires a new subscription; an
implementation MUST NOT reinterpret an old cursor under wider authority.

Control events use a logically separate application-to-runtime control
subscription bound to the application issuer and authenticated runtime, not to
the affected grant. It MAY share one physical connection with non-control
events, but its authority, flow-control capacity, and closure rules remain
separate. A guessed `subscription_id` or cursor is never authority, and an
unauthorized query MUST NOT reveal whether either exists.

## Event Delivery Semantics

The `at_least_once` profile separates an occurrence from its delivery. The
application creates one stable event object for the authorized, redacted
occurrence and one stable `delivery_id` for that event in each subscription.
Every transmission of the same delivery increments the CloudEvents
`aspattempt` value by one but preserves `aspsubid`, `aspdeliveryid`, the
occurrence view and `aspeventhash`, `aspstream`, `aspsequence`, and `aspcursor`.
The canonical Runtime Bridge representation is shown in Serialization and
Transport Mapping.

While the subscription is active and the delivery remains inside its effective
retention window, the application MUST retransmit an unacknowledged delivery
after the acknowledgement deadline. Retries SHOULD use bounded backoff and
MUST NOT change the event projection to include newly available data. If
current authorization or redaction policy can no longer permit the immutable
projection, the application expires that delivery rather than sending a
different object under the same `delivery_id`.

An operational first-delivery window is checked before the first transmission
of a new `delivery_id`. Once admitted, every retry and replay keeps that same
logical admission and consumes no additional first-delivery unit. It still
occupies the same negotiated in-flight slot until terminal acknowledgement.
Thus loss of an acknowledgement cannot multiply either operational admissions
or slots, and a runtime cannot obtain more event authority by reconnecting.

The runtime MUST deduplicate on `(aspsubid, aspdeliveryid)` and retain
enough identity state to distinguish a retry from a conflicting reuse. Seeing
the same delivery id with a different `(source, id)`, `aspeventhash`, stream,
sequence, or cursor is `event_delivery_conflict`; the runtime MUST NOT process
either version as a new occurrence and MUST resynchronize. Duplicate delivery
can still happen after a crash or loss of local deduplication state, so this
profile does not provide exactly-once processing. Any Action Request triggered
by an event remains subject to the action's independent authorization,
idempotency, session, and effect rules.

The runtime MUST complete that validation and durable delivery-deduplication
decision before it allocates an automation root, advances a runaway-guard
counter, or schedules an agent, model, tool, or action. A valid new application
non-control event root is identified by
`(aspsubid, source, id, aspeventhash)`. A core control event never becomes an
automation root. A transport retry or replay of a non-control occurrence reuses
the same root and MUST NOT create another causal branch merely because
`aspattempt`, arrival time, or transport connection changed.

Delivery authentication establishes the application and bound subscription;
fields inside `event` do not. The runtime MUST match the event type to the
pinned manifest and effective grant projection before exposing its data to an
agent. Event content is untrusted application data, not an instruction that can
bypass runtime policy or the Data Exposure Contract.

## Ordering and Acknowledgement

Ordering is defined only inside a `stream` of one subscription. The application
starts at sequence `1`, increments by exactly one for each event eligible for
that stream, and MUST keep an event in the same stream across every retry and
replay. It MUST NOT first-deliver sequence `N + 1` until sequence `N` has a
terminal acknowledgement. Different streams have no defined total order and
MAY progress concurrently up to the negotiated in-flight window. A runtime
MUST NOT infer cross-stream causality from arrival time.

Sequence numbers describe only events authorized for that subscription. Gaps
in an application's source log, filtered events, or events for another subject
MUST NOT be exposed through the subscription sequence. A replay preserves the
original stream and sequence; it does not allocate a new position.

The runtime acknowledges each delivery explicitly:

```json
{
  "type": "event.ack",
  "payload": {
    "subscription_id": "sub_01J2EVENTS",
    "delivery_id": "delivery_01J2FAILED",
    "cursor": "opaque:position-after-42",
    "outcome": "processed",
    "reason": "durably_recorded"
  }
}
```

Defined outcomes are:

- `processed`: the runtime durably recorded its deduplication decision and any
  required local state before acknowledging
- `discarded`: local policy or unsupported event semantics made deliberate
  non-processing terminal; a stable reason is REQUIRED
- `retry`: processing is temporarily unavailable; the delivery remains
  unacknowledged and an optional bounded retry delay is only a hint

`processed` means accepted by the runtime, not that an agent completed a task
or an application action succeeded. `discarded` MUST NOT be used for a valid
core control event before the runtime durably applies its required fail-closed,
scheduling, or reconciliation state. Such an event is normally acknowledged as
`processed` only after that state and its deduplication decision are durable.

A terminal acknowledgement is valid only on the authenticated subscription
and when its delivery id and cursor exactly match the delivery record. It is
idempotent for the same outcome and reason. Conflicting terminal outcomes,
unknown response state, connection loss, or a timeout leave the delivery
unacknowledged. The application MUST NOT advance ordering or discard retained
delivery state merely because it sent a message.

## Replay Cursors and Gaps

A cursor is an opaque, integrity-protected application value bound to the
issuer, applicable subject and delegate tuple, subscription, accepted event and
filter projection, surface hash, and delivery position. It is neither an event
identifier nor a credential. The runtime MUST store and return it unchanged and
MUST NOT infer ordering by comparing cursor bytes.

The runtime requests replay after a previously issued cursor:

```json
{
  "type": "event.replay",
  "payload": {
    "subscription_id": "sub_01J2EVENTS",
    "after_cursor": "opaque:last-durable-position",
    "limit": 100
  }
}
```

The application MUST authenticate the subscription before resolving the
cursor. Replayed records retain their original event and delivery identities,
stream, sequence, and cursor; `aspattempt` increments for another transmission.
The runtime applies ordinary deduplication and acknowledgement rules. Replay
does not reactivate an interrupted or terminal ASP session, and receiving an
event does not authorize a session transition.

Replay also MUST NOT reset a runtime runaway-guard epoch, causal-depth counter,
cycle history, or action-repetition state. The validated root-event reference
above is causal identity for this purpose; `trace_id`, arrival order, a new
connection, or a receipt parent link MUST NOT be substituted for it.

The online `event.replay` operation is distinct from the Portable Replay
Bundle Profile. An online replay remains an authenticated subscription
operation governed by the cursor, retention, deduplication, acknowledgement,
and flow-control rules in this section. A portable bundle is passive historical
evidence and MUST NOT be submitted as an `event.replay` request, used as a
cursor, or interpreted as authority to acknowledge or redeliver an event.

A malformed, tampered, wrong-subscription, wrong-tuple, or wrong-surface cursor
fails as `event_cursor_invalid`. A position no longer available under the
effective retention window fails as `event_cursor_expired`. The application
MUST NOT silently substitute the latest or earliest position. It returns an
authenticated `event.gap` containing the subscription id, last accepted
cursor, earliest currently available cursor when disclosure is permitted, and
reason `retention_expired` or `authorization_changed`. The gap MUST NOT reveal
filtered event identities or counts.

After a gap, the runtime MUST pause automation that depends on complete event
history and reconcile authoritative application state through granted resource
reads or an application-defined snapshot operation. Continuing from the
earliest cursor requires an explicit local policy decision; it cannot be
represented as complete replay. A new or widened grant always requires a new
subscription and initial cursor.

## Retention and Backpressure

For an otherwise active and authorized subscription, the application MUST keep
the delivery record, immutable redacted event projection, and replay position
available for `retention_seconds` after the event first becomes eligible for
that subscription. Earlier deletion is permitted only when required by grant
expiry or revocation, a stricter Data Exposure Contract, subject deletion, or
security response. Such deletion creates an explicit gap; it never permits
silent cursor advancement.

The effective replay window is the shortest applicable delivery-retention,
grant-lifetime, and data-exposure limit. `delete_on_grant_end` applies to queued
and replayable projections when the grant ends. A runtime SHOULD keep compact
deduplication metadata for at least the same effective window but MUST apply
its own retention policy to payloads; acknowledgement does not authorize
indefinite local storage.

`max_in_flight` counts distinct, non-terminally acknowledged deliveries. A
retry of the same `delivery_id` consumes the same slot. The application MUST
NOT exceed the negotiated window. The runtime MAY use authenticated
`event.flow` to lower the window, pause new non-control deliveries with a value
of zero, or restore a value no greater than the negotiated maximum. Pausing
does not terminally acknowledge existing deliveries, extend retention, or
permit the application to ignore their outcomes.

The runtime changes the application-event window with this wire request:

```json
{
  "type": "event.flow",
  "payload": {
    "kind": "request",
    "flow_id": "flow_01J2PAUSE",
    "subscription_id": "sub_01J2EVENTS",
    "max_in_flight": 0
  }
}
```

The request MUST arrive on a channel authenticated as the runtime bound to the
subscription. `flow_id` is unique within that subscription, and
`max_in_flight` MUST be an integer from `0` through the negotiated maximum.
Zero pauses new application-event deliveries. A positive value replaces the
current window; it does not add to it. A request targeting an unknown, closed,
wrong-runtime, or control subscription fails uniformly as
`event_subscription_invalid`. Invalid kinds or values fail as `schema_invalid`.

The application atomically installs the new window before returning its state:

```json
{
  "type": "event.flow",
  "payload": {
    "kind": "state",
    "flow_id": "flow_01J2PAUSE",
    "subscription_id": "sub_01J2EVENTS",
    "effective_max_in_flight": 0,
    "result": "applied"
  }
}
```

Lowering the window below the current in-flight count does not cancel or
terminally acknowledge those deliveries; the application sends no new one
until the count falls below the effective window. An exact duplicate request
with the same `flow_id`, subscription, and value is idempotent and returns the
same state. Conflicting reuse of `flow_id` fails as `schema_invalid` without
changing the window. If the response is lost or ambiguous, the runtime MUST
NOT assume the remote window changed; it MAY repeat the exact request or stop
local consumption and close the channel while it reconciles state.

When the negotiated in-flight window is full, or an applicable operational
first-delivery window has no capacity, the application queues eligible events
within the effective retention window rather than exceeding either limit. If
an event expires before first delivery, the next delivery or replay response
MUST carry an `event.gap`; silent loss is forbidden. Implementations SHOULD
expose bounded metrics for queued, in-flight, operationally delayed, retried,
expired, and gap states without including event payloads.

Application-event backpressure MUST NOT starve the runtime control
subscription. The application MUST reserve independent capacity for
core control events or deliver them on a separate authenticated channel. If the
control path is unavailable, application-side revocation, budget state, and
session fences remain immediately authoritative; the runtime MUST stop affected
new use when it cannot re-establish or introspect authoritative state rather
than assuming that the absence of a control event means capacity or authority
still exists.

## Budget Control Events

`budget.warning`, `budget.exceeded`, and `session.paused_budget` are
application-authored control notifications. They use the logically separate
control subscription, carry `aspcontrol: true` and `aspaudience`, omit
`aspscope`, and satisfy every CloudEvents binding, integrity, exposure,
delivery, replay, and acknowledgement rule above. The affected grant does not
authorize their delivery, but their payload MUST identify only a grant and
delegate tuple already known to the target runtime.

When an application publishes `event_subscription_url` and accepts an
application-authoritative budget, its manifest MUST declare
`budget.exceeded`; it MUST also declare `budget.warning` when it configures a
warning threshold. Independently, an application with
`event_subscription_url` MUST declare `session.paused_budget` when application
policy can interrupt a session for a budget condition or the application
accepts `session.pause` with reason `budget_exceeded`. Accepting only the
`runaway_guard` variant does not require or permit that budget event. Absence or
failure of the control channel never delays the underlying counter or session
transition; delivery is notification, not authority.

An application MUST emit `budget.warning` and `budget.exceeded` only for
application-authoritative `write_actions`, `parallel_sessions`, and
`application_cost` counters. It MUST NOT copy or estimate runtime-authoritative
tool, token, time, or runtime-cost state into an application CloudEvent. A
runtime observes those counters locally and uses the authenticated
`session.pause` operation below when its own budget state requires an
application session fence.

The event-producing state machines are:

```text
consumptive: absent -> available <-> warning <-> exhausted
                            \-----------------> exhausted
occupancy:   absent -> available <-> saturated
session:                active  -> interrupted
```

Every authoritative counter transition occurs whether or not event delivery is
configured. After a local or ancestor transition, the application recomputes
effective lineage state and retryability separately for each affected grant.
When the corresponding event is declared, `budget.warning` is produced exactly
when that effective consumptive state enters `warning`, and `budget.exceeded`
is produced exactly when effective state enters `exhausted` or `saturated`.
`budget.exceeded` is also produced when effective retryability changes while
state remains exhausted or saturated. A counter transition that an already
stricter ledger masks produces no occurrence and no effective state revision
for that affected grant.

Creation directly in a non-available effective state counts as entry from
`absent`, and a transition MAY skip `warning`. The name `budget.exceeded`
reports that no further matching admission currently fits; it does not mean the
hard limit was overdrawn. Because `remaining` includes durable reservations,
releasing unused capacity can move a consumptive counter back to `warning` or
`available`; settled `used` never decreases. Repeated denied attempts without
an effective change MUST NOT create more events.

For each event-producing transition and affected delegate, the application
creates exactly one immutable occurrence with a distinct CloudEvents `id`.
Delivery retry and replay preserve its `(source, id)`, `aspeventhash`, and
stable data; they MUST NOT produce another counter transition, session
transition, charge, or receipt. `effective_at` is the authoritative counter
transition time, `observed_at` is when the immutable event projection was
recorded, and CloudEvents `time` MUST equal `observed_at`.

The application MUST commit the authoritative transition record and a durable
outbox record containing the stable occurrence key and immutable redacted
projection atomically, or with an equivalent recoverable transaction, before it
acknowledges the transition-causing operation or session fence. A crash after
the transition but before network delivery resumes the same occurrence from
that outbox; it MUST NOT omit the event, reconstruct it from later mutable
state, or allocate a second event id. Network delivery remains the independent
at-least-once process defined above.

For each `(affected_grant_hash, budget_id)`, the application maintains a
positive safe-integer `effective_state_revision`, starting at `1` and
increasing by exactly one whenever effective state or effective retryability
changes. It is scoped to the target grant and reveals no ancestor ledger
revision. Every `budget.warning` and `budget.exceeded` occurrence and every
`budget.state` response carries it so a delayed event cannot overwrite a newer
query result. Overflow fails closed as `budget_state_unavailable`; the revision
MUST NOT wrap or reset under the same affected grant and budget id.

The runtime durably retains the highest effective revision seen across budget
events and query responses. A lower revision is historical and cannot change
current scheduling. An equal revision with different effective state or
retryability is `integrity_mismatch` and fails closed; projection detail MAY
differ because an event can contain a complete local counter while
`budget.state` is always lineage-minimized.

This is a minimum `budget.exceeded` delivery:

```json
{
  "specversion": "1.0",
  "id": "event_01J2BUDGET",
  "source": "https://code.example.com",
  "type": "budget.exceeded",
  "time": "2026-06-25T18:20:00Z",
  "datacontenttype": "application/json",
  "dataschema": "https://code.example.com/schemas/budget-exceeded.event.schema.json",
  "aspcontrol": true,
  "aspaudience": "application_runtime_456",
  "aspsurfacehash": "sha-256:<base64url-digest>",
  "aspeventhash": "sha-256:<event-digest>",
  "aspsubid": "control_application_runtime_456",
  "aspdeliveryid": "delivery_01J2BUDGET",
  "aspattempt": 1,
  "aspstream": "grant:grant_123",
  "aspsequence": 7,
  "aspcursor": "opaque:control-position-after-7",
  "data": {
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "app_id": "code.example.com",
    "runtime_id": "application_runtime_456",
    "agent_id": "local_agent_789",
    "identity_evidence_hash": "sha-256:<base64url-digest>",
    "previous_state": "warning",
    "effective_state_revision": 3,
    "budget": {
      "budget_id": "write_actions",
      "authority": "application",
      "scope": "grant",
      "mode": "consumptive",
      "unit": "actions",
      "limit": 20,
      "used": 19,
      "reserved": 1,
      "remaining": 0,
      "state": "exhausted",
      "warning_at_remaining": 2,
      "revision": 42
    },
    "effective_at": "2026-06-25T18:19:59Z",
    "observed_at": "2026-06-25T18:20:00Z",
    "retryable": true
  }
}
```

Both budget event payloads MUST contain `grant_id`, `grant_hash`, `app_id`,
`runtime_id`, `agent_id`, `identity_evidence_hash`, `previous_state`, `budget`,
`effective_state_revision`, `effective_at`, and `observed_at`. The grant and
complete tuple identify the affected grant bound to the target delegate; they
are not part of the grant-agnostic control-subscription authority. The delivery
channel, `source`, `aspaudience`, and `aspsubid` MUST match the control
subscription's application issuer and authenticated target runtime, and
`data.runtime_id` MUST equal `aspaudience`. Independently, the runtime MUST
match the complete payload tuple and `aspsurfacehash` against its retained
authoritative Grant and pinned manifest snapshot. `budget_id` MUST name an
application-authoritative dimension retained in that grant.

When the transitioned counter belongs to the affected grant and its complete
local state and retryability equal the effective lineage result, `budget` MAY be
the complete canonical Budget Counter State with `scope: "grant"`, as shown
above. Otherwise, including when an ancestor or stricter local/ancestor counter
determines the effective result, the event MUST use this minimized projection:

```json
{
  "budget_id": "write_actions",
  "authority": "application",
  "scope": "effective_lineage",
  "mode": "consumptive",
  "unit": "actions",
  "state": "exhausted"
}
```

The minimized projection MUST omit ancestor grant identifiers and hashes,
`limit`, `used`, `reserved`, `remaining`, warning threshold, and ledger
revision. The authenticated application source is authoritative for the
effective application-owned state; the projection is not a reusable ledger
credential. When one ancestor transition affects grants bound to multiple
runtimes, the application emits a separately identified occurrence for each
affected grant and `aspaudience` and MUST NOT disclose ancestor or sibling
delegate identities or aggregate consumption.

The application computes both `previous_state` and the new state over the
complete lineage: consumptive `exhausted` dominates `warning`, which dominates
`available`, and occupancy `saturated` dominates `available`.
If multiple ledgers block admission, non-retryable settled-hard exhaustion
dominates a retryable reservation or occupancy blocker. An ancestor warning
MUST NOT make an already exhausted descendant appear to recover, and releasing
one blocker MUST NOT emit availability while another blocker remains.

For `budget.warning`, state MUST be consumptive `warning`, and a complete local
projection MUST carry `warning_at_remaining`; `previous_state` is `absent`,
`available`, or `exhausted`. For `budget.exceeded`, state MUST be consumptive
`exhausted` or occupancy `saturated`. Its `retryable` is REQUIRED. For a
complete consumptive projection it is `true` exactly when `reserved` is
positive and `used` is smaller than `limit`, and `false` for settled hard
exhaustion where `used` equals `limit` and `reserved` is zero. For a minimized
projection the application derives the same value without disclosing its
inputs. For occupancy saturation it is `true` only when every blocking
occupancy ledger has a positive limit and currently occupied or reserved
capacity that can be authoritatively released; a zero-slot limit is
non-retryable. A true value only says capacity can return after authoritative
reservation or slot release; the runtime still requires a fresher authenticated
`budget.state` before retry. The field never authorizes automatic retry or
reserves future capacity.

The runtime obtains that fresher state without exposing ancestor totals through
an authenticated control-plane query. It sends the complete typed envelope as
an `application/json` POST to the manifest `budget_state_url`, using the grant's
required credential-binding proof, or carries the identical message on an
already authenticated Runtime Bridge:

```json
{
  "type": "budget.query",
  "payload": {
    "query_id": "budget_query_01J2AVAILABLE",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "budget_id": "write_actions"
  }
}
```

Before consulting an idempotency record or returning state, the application
MUST authenticate the runtime and presented credential, resolve an active,
unexpired current grant, and match its subject, runtime, agent, passport,
credential binding, `grant_id`, `grant_hash`, and `surface_hash`. It MUST then
require `budget_id` to name an application-authoritative dimension retained by
that grant. Revocation, expiry, a superseded surface, or any mismatched or
unknown authority dominates an earlier cached response. Every failure of these
checks, including an unknown or runtime-authoritative `budget_id`, returns the
same terminal, non-enumerating `budget_query_invalid` error and no
`budget.state`; the response MUST NOT disclose which check failed. Only after
all checks pass does the application evaluate the local and every ancestor
ledger and return the effective admission state for that target grant:

```json
{
  "type": "budget.state",
  "payload": {
    "query_id": "budget_query_01J2AVAILABLE",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "budget": {
      "budget_id": "write_actions",
      "authority": "application",
      "scope": "effective_lineage",
      "mode": "consumptive",
      "unit": "actions",
      "state": "available"
    },
    "effective_state_revision": 4,
    "observed_at": "2026-06-25T18:21:00Z",
    "query_expires_at": "2026-06-25T18:26:00Z"
  }
}
```

For consumptive state, `exhausted` dominates `warning`, which dominates
`available`; for occupancy, `saturated` dominates `available`. When the
effective state is `exhausted` or `saturated`, the `budget` projection MUST also
carry `retryable`. It is `false` if any currently blocking consumptive ledger
is settled-hard and is `true` only when every blocker can recover through an
authoritative reservation or occupancy release. It is absent for `available`
or `warning`. The response MUST omit every ancestor identifier, hash, limit,
counter value, threshold, and revision. A runtime MUST allocate a `query_id`
unique for the lifetime of the target grant and MUST NOT deliberately reuse an
expired id. On first acceptance, the application binds the complete request to
its response through `query_expires_at`, computed from the manifest
`budget_query_retention_seconds`, and retains that full idempotency record until
the timestamp. After the current-authority checks above, it consults this record
before evaluating live ledger state. An exact duplicate received before expiry
therefore returns the immutable cached response and effective revision even if
the live ledger later becomes unavailable; the response remains only the
point-in-time observation it claims. A caller needing fresher state uses a new
id, whose evaluation fails as `budget_state_unavailable` when current ledger
state is missing or uncertain, never as synthetic availability.

At `query_expires_at`, the application MUST delete the cached state payload and
compact the record to `(query_id, request_hash, query_expires_at)` for one
additional `budget_query_retention_seconds` interval. Any exact or conflicting
reuse during that tombstone interval fails as the same terminal,
non-enumerating `budget_query_invalid` error with no state. After the tombstone
deadline the application MUST evict it; a later occurrence is processed as a
new query, but a conforming runtime never relies on that fallback. A conflicting
reuse before either deadline also fails as `budget_query_invalid`.
`request_hash` is the Canonical Object Hash Profile digest of the complete typed
`budget.query` envelope; it is local bookkeeping and is not inserted into that
envelope. The application MUST enforce finite per-grant
cardinality and authenticated-caller rate limits over live records and
tombstones; rejection at either bound returns `rate_limited` without allocating
a record. Because tombstones have a mandatory eviction deadline, reaching the
bound cannot permanently consume the grant's query namespace.

`budget.state` is point-in-time application authority, not a reservation. A
runtime MAY reconsider an unchanged operation after a response of `available`
or `warning`, subject to local policy and ordinary atomic admission at the
application. It MUST use bounded backoff for another query after a retryable
exhaustion or saturation, MUST stop same-grant recovery queries after a
non-retryable result, and MUST NOT query or retry from an agent-controlled loop.
`budget.query` and `budget.state` use the safety control plane, consume no grant
budget, require no active session, and MUST NOT be exposed to an agent.

Budget exhaustion does not itself interrupt a session. If application policy
chooses to fence an active session because of settled exhaustion of an
application-owned consumptive `write_actions` or `application_cost` counter,
the application MUST first atomically transition that session from `active` to
`interrupted`, without changing its generation, and, when the event is declared,
then emit exactly one `session.paused_budget` occurrence for that transition.
`parallel_sessions` saturation MUST NOT pause or cancel a session that already
owns a slot. A runtime-owned budget can cause an application transition only
through an accepted `session.pause` request. A duplicate pause request or event
delivery does not create a second transition or occurrence.

A `session.paused_budget` event MUST carry matching `aspsessionid` and
`aspsessiongen` attributes. This is the minimum data for the
controlling-runtime variant:

```json
{
  "grant_id": "grant_123",
  "grant_hash": "sha-256:<base64url-digest>",
  "budget_grant_id": "grant_123",
  "budget_grant_hash": "sha-256:<base64url-digest>",
  "app_id": "code.example.com",
  "runtime_id": "application_runtime_456",
  "agent_id": "local_agent_789",
  "identity_evidence_hash": "sha-256:<base64url-digest>",
  "pause_id": "pause_01J2BUDGET",
  "session_id": "sess_456",
  "session_generation": 1,
  "previous_state": "active",
  "state": "interrupted",
  "transition_reason": "budget_exceeded",
  "budget_id": "runtime_seconds",
  "budget_authority": "controlling_runtime",
  "budget_scope": "grant",
  "reported_budget_revision": 31,
  "effective_at": "2026-06-25T18:20:00Z",
  "observed_at": "2026-06-25T18:20:01Z",
  "automatic_resume": false
}
```

Every variant contains `grant_id`, `grant_hash`, `app_id`, `runtime_id`,
`agent_id`, `identity_evidence_hash`, `pause_id`, `session_id`, `session_generation`,
`previous_state`, `state`, `transition_reason`, `budget_id`,
`budget_authority`, `budget_scope`, `effective_at`, `observed_at`, and
`automatic_resume`. The event's session attributes, data, tuple, and hashes
MUST match the authoritative interrupted record. `budget_authority` is
`application` or `controlling_runtime`; `budget_scope` is `grant` or
`ancestor`. For a local application-owned counter, `budget_scope` is `grant`,
`budget_revision` is REQUIRED, and all `budget_grant_*` and
`reported_budget_revision` members are absent. For an ancestor application-owned
counter, `budget_scope` is `ancestor` and every causal ancestor identifier,
hash, counter value, and revision MUST be omitted. The application remains
authoritative for the effective fence without exposing aggregate lineage state.

For a runtime-owned counter, `budget_grant_id` and `budget_grant_hash` MUST
identify the session grant or an ancestor containing `budget_id`,
`budget_scope` reflects which, and `reported_budget_revision` MUST repeat the
causal grant and revision from the accepted pause request. `budget_revision`
is absent, and the application MUST NOT represent that runtime report as its
own counter state. `automatic_resume` is the literal `false`: only an explicit,
independently authorized resume after the budget condition is resolved can
return the session to `active`.
`effective_at` records the authoritative fence, `observed_at` and CloudEvents
`time` record the immutable event projection, and an application-initiated
fence MUST allocate a `pause_id` unique in that session generation.

The runtime MUST validate and durably deduplicate a budget control occurrence
before changing local scheduling. Channel authentication proves only the
application issuer and target runtime. If no locally retained authoritative
Grant matches the event's complete affected tuple, the runtime MUST apply one
non-enumerating unknown-authority disposition, accept no payload state, and
MUST NOT disclose whether the tuple was unknown, ended, or outside local
authority. If `grant_id` resolves locally but any delegate member,
`grant_hash`, or `aspsurfacehash` differs, the runtime MUST stop scheduling on
the affected local grant, record `integrity_mismatch`, and begin authoritative
grant and manifest resynchronization without replacing retained authority from
the event. The control-delivery acknowledgement MUST NOT echo the mismatched
value or distinguish which binding failed.

After those checks, the runtime MUST NOT deliver any core control event to an
agent as a task, treat it as authority for an Action Request, automatically
retry denied work, or infer that pausing rolled back an in-flight effect. A
`budget.warning` or `budget.exceeded` occurrence MUST NOT replace a newer
effective state revision with an older event or query result. A valid duplicate
or older effective revision receives a terminal `processed` acknowledgement
without repeating local side effects. For `session.paused_budget`, the runtime
stops matching local scheduling and reconciles in-flight outcomes before
terminal acknowledgement. A historical pause replay for an older session
generation MUST NOT interrupt or downgrade a later generation; the runtime
validates it against retained transition history and acknowledges it without
changing current session state.
