
## ASP-over-MCP Binding Profile

The ASP-over-MCP Binding Profile identifier is
`https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1`. The
profile binds the MCP specification version `2025-11-25` to ASP discovery,
action invocation, structured results, errors, and receipt retrieval. It is an
ASP-governed binding, not an official MCP extension. In the pinned MCP revision
the value for both its experimental capability and namespaced `_meta` key is
`io.github.zeroal-spec/asp-over-mcp-v1`.

This binding uses MCP as an application-facing carrier. It does not translate
MCP discovery, transport authentication, tool metadata, model selection, or
tool execution into ASP authority. A different MCP protocol revision, even one
that appears wire-compatible, requires a different ASP binding profile unless
this specification is updated to name it explicitly.

Version 1 selects MCP Streamable HTTP as its only transport. Stdio and custom
transports are outside this profile because they do not share one defined
credential, peer-identity, audience, confidentiality, and HTTP-header
composition. A future transport-specific binding requires another profile id.
The Runtime Mediator begins only from the exact verified
`agent_api.bindings` descriptor in the ordinary ASP manifest and an active
Grant whose `locations` contain that descriptor's endpoint. It MUST NOT use
MCP itself to discover an unpinned endpoint or bootstrap authority.

### Role Topology and Authority Boundary

In the direct topology, the Runtime Mediator is the MCP client and the
application-controlled Surface Publisher and Action Executor are exposed by the
MCP server:

```text
Agent -> Agent Adapter -> Runtime Mediator / MCP client
                                  |
                                  | authenticated MCP channel
                                  v
                     application MCP server / gateway
                                  |
                                  v
                    Surface Publisher + Action Executor
```

The Agent Adapter can propose a tool selection and action input, but the
Runtime Mediator owns MCP negotiation, the binding view, ASP request
construction, credential custody, approval, policy, idempotency, and outcome
reconciliation. The MCP server either is inside the Action Executor's
application authority boundary or forwards to an Action Executor that performs
all ordinary ASP checks independently. A generic MCP proxy, model provider,
secondary MCP server, or tool router does not become an Action Executor or a
Runtime Mediator merely by carrying a message.

ASP continues to own:

- the exact base or authorized projected manifest and its lifecycle;
- Grant, credential, delegate, session, and revocation authority;
- action identifiers, modes, normalized input, hashes, approval, policy,
  budgets, operational limits, idempotency, and effect admission;
- application results, effect outcomes, receipts, and authoritative recovery;
  and
- data exposure, retention, remote-processing, and training-use constraints.

MCP owns its initialization, capability negotiation, JSON-RPC framing,
transport, resources, tool listing, tool calls, progress, cancellation, and
protocol errors. An MCP session id, JSON-RPC request id, pagination cursor,
progress token, task id, resource URI, tool name, annotation, OAuth scope, or
access token is not an ASP session, Grant, approval, action id, idempotency key,
effect, or receipt. Implementations MUST keep those namespaces separate and
map them only through the closed records below.

An MCP server reached as a subordinate tool of an agent is not the
application-facing server in this profile. Routing an ASP action to another MCP
server, runtime, agent, or application requires the ordinary separately
authorized ASP delegation or subdelegation semantics. Parent-runtime mediation
and cascade revocation remain in force.

### Exact Negotiation

The MCP `initialize` exchange MUST negotiate the exact protocol version
`2025-11-25`, the `resources` server capability with both `subscribe: true`
and `listChanged: true`, the `tools` server capability with
`listChanged: true`, and the exact
experimental capability key `io.github.zeroal-spec/asp-over-mcp-v1` in both
peers' `capabilities.experimental` maps. The binding is disabled by default. A
client and server claim it only when both settings objects select the exact ASP
profile above. The server settings additionally return the absolute
`manifest_resource_uri` for the selected ASP manifest snapshot:

```json
{
  "capabilities": {
    "resources": {
      "subscribe": true,
      "listChanged": true
    },
    "tools": {
      "listChanged": true
    },
    "experimental": {
      "io.github.zeroal-spec/asp-over-mcp-v1": {
        "profile": "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1",
        "mcp_protocol_version": "2025-11-25",
        "authorization_composition": "asp-native",
        "manifest_resource_uri": "https://example.com/.well-known/agent-surface.json"
      }
    }
  }
}
```

This is a dedicated MCP session. The server capability set contains only
`resources`, `tools`, and `experimental`; the client capability set contains
only `experimental`; and each experimental map contains only the binding key.
Prompts, roots, sampling, elicitation, logging, completions, MCP Tasks, and
ordinary non-binding tools or resources MUST NOT be negotiated or invoked on
this session. A future composite profile must define any safe coexistence and
credential-use rules explicitly.

Both peers' settings repeat the exact manifest-selected
`authorization_composition`; the client settings omit only
`manifest_resource_uri`, and the server MUST reject a client-supplied URI
rather than let it select another application or surface.
The initialize request uses the fixed `clientInfo.name` value
`asp-runtime-mediator`; the result uses the fixed `serverInfo.name` value
`asp-action-executor`. Each `version` is a 1-to-64-character token containing
only ASCII letters, digits, period, underscore, or hyphen. Both implementation
records MUST omit `title`, `description`, `websiteUrl`, `icons`, and unknown
members, and the
`InitializeResult` MUST omit `instructions`. The Runtime Mediator MUST NOT pass
implementation identity text to the agent or model. These restrictions close
MCP's model-facing instruction and display-metadata channels; they do not turn
the remaining names or versions into authenticated ASP identity.
The returned resource identifier is an absolute URI but is only an MCP locator;
the client MUST NOT infer its issuer, application, or surface from that URI.
After reading it, the client requires the content's issuer, application,
canonical `surface_url`, surface hash, and projection tuple to equal the exact
ordinary ASP manifest snapshot selected before MCP initialization. A deployment
using an Authorized Surface Projection can therefore return that exact
projected manifest through an opaque authenticated MCP resource URI, while the
resource content still repeats its canonical `surface_url` and complete
`authorized_projection` binding.

Missing, unknown, downgraded, or conflicting MCP versions, binding settings,
resources, or tools capabilities make the channel unbound. The peers MUST NOT
fall back to core MCP tool behavior and call it ASP. In particular, an HTTP
server MUST NOT apply MCP's missing-version compatibility assumption of
`2025-03-26`: every post-initialization request in this binding carries
`MCP-Protocol-Version: 2025-11-25`, and omission or mismatch fails before ASP
interpretation. Reconnect or MCP session replacement performs a fresh
initialization and revalidates the current manifest, Grant, ASP session,
binding view, and revocation state. It never restores ASP authority from the
previous MCP session. Because version 1 binds its application-facing
authenticated runtime channel to the mandatory MCP session, terminal MCP
session loss also invokes the ordinary Runtime Disconnected transition defined
below. Fresh initialization can establish a replacement carrier for the
closed interrupted-session operations, but new agent work requires an
explicitly accepted `session.resume` and the resulting incremented ASP session
generation.

The binding requires `execution.taskSupport: "forbidden"` on every mapped
tool, and a call MUST omit the MCP `task` member. This version does not map MCP
Tasks to ASP action or receipt state. A future asynchronous binding requires a
new profile.

After validating the `InitializeResult`, the client MUST send MCP's required
`notifications/initialized` notification before any subscription, resource
read, tool listing, or mapped call. The server MUST NOT serve an ASP manifest
resource, binding view, or mapped action before that lifecycle transition.
Receiving `notifications/initialized` completes MCP initialization only; it
does not establish an ASP session, binding view, Grant, or authority.

Version 1 makes Streamable HTTP session management mandatory. The HTTP response
carrying `InitializeResult` includes a fresh globally unique,
cryptographically secure `MCP-Session-Id` containing 1 to 128 visible ASCII
characters (`0x21` through `0x7e`). The Runtime Mediator protects it as an
opaque transport secret and repeats it exactly on every subsequent POST, GET,
and DELETE request together with `MCP-Protocol-Version: 2025-11-25` and the
selected per-request authentication. The server binds the initialized
capabilities, authenticated context, manifest subscription, binding views, and
current resource access to that exact id. The id does not enter an ASP object
or shorten an application receipt's retention lifecycle. Missing the required
header returns HTTP `400`; an unknown, authentication-mismatched, expired, or
terminated id returns HTTP `404`. Either response is transport evidence only.
On `404`, the runtime invalidates the view and subscription, stops new work on
that carrier, and starts a fresh InitializeRequest without a session id. An
unknown or authentication-mismatched presented id MUST NOT mutate or reveal
the existence or state of any stored MCP or ASP session. Only
server-authoritative expiry or termination of an existing session, an
owner-authenticated accepted `DELETE`, or detected shutdown of its authenticated
owner invokes Runtime Disconnected and marks the ASP sessions actually bound
to that MCP session `interrupted`. The application retains that binding
durably enough that a fresh MCP session cannot claim an apparently active ASP
generation after loss of volatile MCP state.

Fresh initialization alone does not reactivate an interrupted ASP session. It
can establish a replacement carrier for receipt retrieval, authoritative
outcome reconciliation, and an exact completed idempotent replay only through
the ordinary closed interrupted-session path; unrelated work remains fenced
until an explicit resume succeeds. Before requesting resume, the Runtime
Mediator MUST consume every available late result and exact completed-record
replay for the interrupted generation. Existing receipt or audit retrieval and
explicit operator reconciliation MAY additionally establish an authoritative
outcome; this binding defines no new outcome-query message. A record whose
outcome remains unknown or whose recovery could dispatch another effect keeps
the session interrupted and makes resume fail closed, potentially until
operator resolution. Neither peer rebinds its original idempotency record or
Action Request to the next generation. After all such records are terminal or
authoritatively known to have admitted no effect, an accepted `session.resume`
increments the generation; old-generation evidence then remains available
through receipt and audit retrieval without admitting another call.

At application admission, one active ASP `(session_id, session_generation)` is
bound to at most one active `MCP-Session-Id` for mapped calls. One dedicated MCP
session MAY carry multiple independently bound ASP sessions under the same
authenticated application context, but a second MCP session MUST NOT claim an
already bound active generation. Only the terminal-loss to `interrupted`
transition followed by explicit resume can bind the incremented generation to
a replacement MCP session. The replacement can use the old interrupted
generation only for the closed operations above.

After the initialized notification receives HTTP `202` with an empty body, the
runtime opens an authenticated HTTP GET event stream on the exact MCP endpoint
before subscribing to the manifest resource. This profile requires the server
to return `text/event-stream`, not `405`, so resource and tool update
notifications have a defined delivery path. The runtime uses at most one such
listener per binding session. Stream loss invalidates the cached binding view;
the runtime re-establishes the listener on the same active session, retains its
existing server-side subscription, and repeats manifest verification and
complete tool pagination before dispatch. After `404` it starts a fresh session
and creates a fresh subscription before that verification. SSE event ids,
`Last-Event-ID`, and redelivery are
transport correlation only and cannot preserve or restore ASP authority.

### Manifest Resource and Tool View

After initialization, the Runtime Mediator first sends `resources/subscribe`
for `manifest_resource_uri` and then reads that URI through the negotiated MCP
resources capability. Subscribing before the first read prevents an update at
the stable URI from being missed between discovery and retention. The
subscription request contains only that URI and its successful MCP result is
the empty object; the runtime waits for that result before `resources/read`.
The read request likewise contains only the exact URI. The
`ReadResourceResult` contains only `contents`, whose array MUST contain exactly one MCP
`TextResourceContents`, never a blob. Its `uri` is exactly the requested
`manifest_resource_uri`, its `mimeType` is exactly `application/json`, its
`text` is exactly one complete strict I-JSON Agent Surface Manifest for the
authenticated application context, and its optional `_meta` is absent. The
runtime applies the ordinary manifest, schema, issuer, lifecycle, base or
authorized-projection, and `surface_hash` verification rules. A resource name,
description, annotation, MIME label, URI, TLS connection, or successful MCP
authorization is not manifest integrity evidence.

The application materializes a **binding view** through `tools/list`. A binding
view is one complete, authenticated, pagination-stable selection of ASP actions
from the exact manifest resource. Every page's `ListToolsResult._meta` contains
exactly the namespaced binding key and no other member; that key contains the
following closed binding record:

```json
{
  "io.github.zeroal-spec/asp-over-mcp-v1": {
    "profile": "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1",
    "mcp_protocol_version": "2025-11-25",
    "authorization_composition": "asp-native",
    "binding_view_id": "mcp_view_01J2A7M8J3V6",
    "manifest_resource_uri": "https://example.com/.well-known/agent-surface.json",
    "surface_version": "2026-06-25",
    "surface_hash": "sha-256:<base64url-digest>"
  }
}
```

The first `tools/list` request omits `params`; each continuation request
contains only the exact non-empty `cursor` returned by the preceding page. A
page contains only `tools`, optional `nextCursor`, and the required result
`_meta`; an empty final page is permitted, but a cursor cycle or repeated page
is invalid.

When the selected manifest is an Authorized Surface Projection, the record
also copies its complete `authorized_projection` object. The
`binding_view_id` is an opaque, non-empty server value for one materialized
view. It is correlation and stale-view protection, not authority. Every page in
one cursor lineage MUST repeat an identical record. The server MUST keep the
view stable until pagination reaches a page without `nextCursor`; the runtime
rejects a missing page record, mixed view, duplicate tool name, duplicate
action mapping, conflicting cursor replay, or surface mismatch as
`binding_invalid` and exposes none of that view to the agent.

Each action selected for the binding view maps to exactly one MCP Tool. The
tool name is derived mechanically as:

```text
"asp.action." + lowercase-hex(SHA-256(UTF-8(action_id)))
```

The digest is the full 64-character lowercase hexadecimal digest and MUST NOT
be truncated. This mapping is only a collision-resistant MCP-safe name; it is
not an ASP object hash, signature, Grant, or authority commitment. If two
distinct action ids produce the same name, the complete binding view is
invalid. A receiver MUST NOT select one of them.

Every mapped Tool contains exactly `name`, `inputSchema`, `execution`, and
`_meta`; `execution` contains exactly `taskSupport: "forbidden"`. It repeats
the page binding record in `Tool._meta`, whose only top-level member is the same
namespaced key, and adds the
exact wire member `execution_mode` copied from the manifest action's
`execution.mode`, together with `action_id`, `input_schema`, optional
manifest `input_schema_hash`, `output_schema`, and the required binding-local
`binding_input_schema_hash` and `binding_output_schema_hash`. A bare manifest `execution_mode`
member is undefined and MUST NOT be used as the source. The runtime recomputes
the tool name, resolves the action only in the exact pinned manifest, and
requires every repeated value and fetched schema to match. Every Tool in the
bound `tools/list` view MUST be one valid mapped ASP Tool. The server MUST NOT
mix ordinary or unprofiled MCP tools into that view, and the runtime suppresses
and rejects the complete view if it finds one. It never exposes or calls such a
tool on a channel carrying an ASP credential.

The Tool `inputSchema` is the complete self-contained schema retrieved from the
action's `input_schema`. Because MCP `2025-11-25` tool arguments and root input
schemas are JSON objects, version 1 can expose only an ASP action whose exact
normalized wire input is an object and whose schema has object root type. The
schema document MUST contain an explicit root `$schema` whose value exactly
equals the manifest's `compatibility.schema_dialect`; omission or mismatch
invalidates the mapped Tool. This prevents MCP's default Draft 2020-12 dialect
from silently reinterpreting a schema selected by another ASP dialect. The
publisher MUST NOT wrap, flatten, coerce, default, rename, or omit members to
make another ASP schema fit MCP. It verifies `input_schema_hash` whenever the
manifest requires that hash. An incompatible action remains available through
other declared ASP bindings but MUST NOT appear in this binding view.

Mapped Tools MUST omit MCP `outputSchema` in version 1. This draft does not
publish a second JSON Schema that could diverge from the ordinary ASP Action
Response and common error contracts. The Runtime Mediator instead validates the
closed `structuredContent` envelope below and then applies the manifest
`output_schema` to the output inside the ordinary ASP Action Response. Both
peers MUST support the schema dialect declared by each manifest schema and MUST
fail the binding rather than reinterpret an unsupported dialect. A future
binding version can name one exact reusable MCP output schema.

When materializing a view, the publisher retrieves and strictly validates the
complete input and output schema documents and computes each binding-local hash
as SHA-256 over the RFC 8785 serialization of this wrapper, encoded as the
usual unpadded base64url `sha-256:` value:

```json
{
  "domain": "https://github.com/0al-spec/agent-surface/hash/asp-over-mcp-schema/v1",
  "object": {}
}
```

`object` is the complete schema JSON data model; the empty object above is only
a placeholder. Both documents MUST be JSON objects with an explicit root
`$schema` exactly equal to the manifest dialect and MUST be self-contained.
Every reference-bearing keyword defined by that dialect, including `$ref` and
`$dynamicRef` when applicable, resolves entirely within the same hashed
document. An external, unresolved, unsupported-vocabulary, or fetch-dependent
reference makes view materialization fail; neither peer follows it. The Tool `inputSchema` MUST equal that exact validated input
schema data model, and both binding hashes MUST equal the publisher's pinned
documents. The Runtime Mediator retrieves the declared output schema, verifies
both hashes, and retains both exact data models with the complete binding view.
The Action Executor resolves the same server-side snapshot by
`binding_view_id`; neither party refetches mutable schema bytes while using the
view.

The server keeps the view and both schema snapshots stable beyond pagination
until it rotates or invalidates the view. A content change at either referenced
schema URI, even when the manifest bytes and URI are unchanged, rotates
`binding_view_id`, emits `notifications/tools/list_changed`, and fences old
calls before idempotency lookup or effect. If the manifest also changes, the
ordinary manifest resource notification is required as well. A failed schema
fetch or unsupported dialect makes the view unavailable; it never falls back
to cached bytes from another view.

Rotation prevents only new admission under the old view. For every request
already admitted into an idempotency record, the server retains the immutable
old view and both schema snapshots through terminal result, receipt, and
reconciliation retention. In-flight work completes or reconciles against that
snapshot, and its result repeats the old `binding_view_id`; rotation neither
cancels it nor substitutes the new schemas. The Runtime Mediator likewise
removes the old view from new selection but retains its pending-call snapshot
solely to validate and reconcile that exact admitted request. Before dispatch,
the runtime durably binds both schema snapshots and the view to its logical
idempotency/reconciliation record; that state survives runtime-process and MCP
session restart until terminal result and receipt verification. The server
retains the same old view snapshots with each admitted or completed
idempotency record for the corresponding reconciliation-retention period.

After authenticating the current caller and exact Grant, ASP session, action,
key, input, and execution tuple, the server can consult an immutable completed
idempotency record under a retained old view. An exact match returns only the
original result, old `binding_view_id`, and receipt resources without another
admission, reservation, policy decision, charge, effect, or receipt. An absent,
incomplete, unknown-outcome, or conflicting record does not qualify: the stale
view is rejected before any new idempotency reservation or semantic admission.
Current authorization policy can still forbid disclosure as in the core
idempotency rules; view staleness alone does not erase the completed record.

A Surface Publisher MAY omit an action from the authenticated binding view.
Omission makes that action unavailable through this MCP channel; it does not
remove it from the manifest or revoke a Grant. Conversely, listing a tool does
not add an action to the Grant. The Action Executor still requires the exact
action allow-list, scopes, constraints, current state, and all other ordinary
admission checks.

If the content at `manifest_resource_uri` changes, the server MUST emit
`notifications/resources/updated` for that URI, rotate `binding_view_id`, and
emit `notifications/tools/list_changed` before it accepts another mapped call.
The resource notification contains only the exact subscribed `uri`; the tools
notification has no parameters. Neither carries `_meta`, display text, or
another URI.
`notifications/resources/list_changed` alone is insufficient because MCP uses
that notification for resource-inventory changes, not content changes at an
existing URI. After either required notification, surface supersession,
authorized-projection change, authenticated-context change, or revocation
relevant to the view, the runtime invalidates the complete cached view and
repeats manifest-resource verification and full tool pagination before another
call. It MUST NOT merge old and new pages or retain a tool merely because its
name is unchanged. This invalidation applies to new selection; an already
admitted request retains the immutable reconciliation snapshot defined above.
The server rejects a new call carrying a stale
`binding_view_id` before an effect, budget charge, idempotency reservation, or
receipt is created. Missing, reordered, or lost notifications cannot restore
authority: the Action Executor independently rejects a view that is no longer
current for the presented Grant and authenticated context.

Mapped Tools MUST omit MCP `title`, `description`, `icons`, and `annotations`.
The agent selects the action from the already verified ASP manifest; this
profile does not create a second model-facing prose or icon channel that an MCP
gateway could use for instruction or data injection. In particular, MCP
`readOnlyHint`, `destructiveHint`, `idempotentHint`, and `openWorldHint` are
never policy, behavior, or authority evidence, even when the MCP server and
application share an operator. A future profile can define exact, bounded,
data-exposure-checked projections of manifest display metadata.

### Action Request Mapping

The agent or Agent Adapter can propose only the mapped tool name and the action
input object. The Runtime Mediator validates that proposal against its exact
pinned manifest and binding view, applies the manifest-pinned normalization,
approval, policy, budget, operational-limit, runaway-guard, input-hash, and
execution-hash rules, and constructs the ordinary ASP Action Request. It MUST
discard any agent-supplied MCP `_meta`, JSON-RPC id, progress token, binding
record, Grant field, session field, idempotency key, receipt reference, or
credential rather than copy it into authority state.

The `tools/call` `params` object contains exactly `name`, `arguments`, and
`_meta`; the MCP `task` member is absent. Its `arguments` object is exactly the resulting ordinary
Action Request `payload.input`. The runtime places the complete Action Request
except `payload.input` in `params._meta` under the namespaced binding key and
adds the exact profile, MCP version, binding view id, surface version, and
surface hash, plus the negotiated `authorization_composition`. When the view
uses an Authorized Surface Projection, the call record also copies its complete
`authorized_projection` object exactly. The omitted input position is fixed; an `action_request` that
already contains `payload.input` is invalid rather than merged with
`arguments`.

The call `params._meta` contains exactly that namespaced member and, when the
Runtime Mediator requests progress, one runtime-generated `progressToken` that
is either an I-JSON-safe integer or a non-empty string of at most 128 Unicode
scalar values. The token never occurs inside the binding record or ASP Action
Request and is correlation only. Agent-supplied tokens are discarded. A
corresponding `notifications/progress` repeats the exact token, carries a
finite non-negative `progress`, MAY carry a finite non-negative `total` not
smaller than `progress`, and MUST omit `message` and unknown members. A runtime
that supplies the token accepts progress only on the SSE response stream of
that exact `tools/call` POST and requires the final JSON-RPC response on the
same stream; progress is not sent on the unrelated GET listener. A runtime
rejects any other progress notification and never exposes its fields to the
agent or model as instructions, authority, or outcome evidence.

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "tools/call",
  "params": {
    "name": "asp.action.<64-lowercase-hex-digest>",
    "arguments": {
      "repository": "example-org/example-repo",
      "pull_request": 13,
      "body": "The proposed review comment text."
    },
    "_meta": {
      "io.github.zeroal-spec/asp-over-mcp-v1": {
        "profile": "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1",
        "mcp_protocol_version": "2025-11-25",
        "authorization_composition": "asp-native",
        "binding_view_id": "mcp_view_01J2A7M8J3V6",
        "surface_version": "2026-06-25",
        "surface_hash": "sha-256:<base64url-digest>",
        "action_request": {
          "type": "action.request",
          "payload": {
            "session_id": "sess_456",
            "session_generation": 1,
            "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
            "span_id": "b7ad6b7169203331",
            "grant_id": "grant_123",
            "grant_hash": "sha-256:<base64url-digest>",
            "surface_hash": "sha-256:<base64url-digest>",
            "action_id": "comment.create",
            "idempotency_key": "idem_01HX7DS8AC6G9",
            "parent_receipt_hash": "sha-256:<runtime-receipt-digest>",
            "input_hash": "sha-256:<action-input-digest>",
            "execution": {
              "mode": "commit",
              "execution_id": "exec_01J2COMMENT"
            },
            "execution_hash": "sha-256:<action-execution-digest>"
          }
        }
      }
    }
  }
}
```

The example omits optional ordinary Action Request members only for brevity;
the binding does not make them optional. The MCP server reconstructs exactly
one Action Request by inserting `params.arguments` as `payload.input`. Before
dispatch or effect, it and the Action Executor validate the closed binding
record, exact tool-to-action mapping, current view, schemas, normalized input,
`input_hash`, execution context and hash, session generation, Grant and surface
tuple, approval evidence, idempotency state, and all ordinary ASP checks. A
gateway MUST preserve the reconstructed request exactly; it cannot translate
it into a wider internal call or treat its own MCP authentication decision as
application admission.

The enclosing Streamable HTTP request MUST omit `Idempotency-Key`: it carries
an MCP JSON-RPC exchange, not a direct ASP HTTP Action Request. The nested
`action_request.payload.idempotency_key` is the sole semantic idempotency
identity in this binding. The MCP server reconstructs that member before the
Action Executor applies the ordinary ASP idempotency rules. An exact replay
retains the nested key, normalized input, and execution binding while using a
new JSON-RPC request id and fresh per-attempt transport proof when those are
required. An outer header MUST NOT override, duplicate, or repair the nested
identity. A server receiving an outer `Idempotency-Key` rejects the MCP
exchange before ASP reconstruction, idempotency lookup, semantic admission,
or effect with HTTP `400`; it MUST NOT ignore or copy the header into the
Action Request. That transport rejection is not an ASP Error.

MCP `_meta` carries correlation and integrity inputs, not Grant authority. When
the ordinary Action Request requires a confidential raw `execution_token`, the
Runtime Mediator MUST place it only at its existing
`action_request.payload.execution.execution_token` position in the
runtime-constructed `_meta` over the authenticated confidential
application-facing channel. That exception is necessary for the Action
Executor to verify the token against `execution_token_hash`; it does not make
the token authority. For that incoming commit token, the server removes it
before receipt production, structured output, diagnostics, or persistence
outside the ordinary protected preview and idempotency lifecycle. It MUST NOT
appear at another `_meta` position or in a resource, tool definition,
`arguments`, content block, resource link, progress event, error, log, prompt,
model context, process argument, or agent-visible environment.

A successful mapped `dry_run` is the sole result-side exception. Its complete
ordinary Action Response carries the newly issued raw token only at
`structuredContent.message.payload.preview.execution_token`. Because this
profile requires one deep-equal JSON TextContent compatibility copy, that copy
contains the same value at the same relative payload path; these are two
representations of one runtime-only result, not two disclosure channels. The
server MUST NOT place the token in `payload.output`, another result member,
`_meta`, a receipt or resource link, or any other content block. The Runtime
Mediator validates the token syntax, `execution_token_hash`, preview tuple,
input, action family, Grant, surface, session, and expiry, then stores it only
in protected runtime preview state. Before creating an Agent Adapter result or
any model-, user-, log-, prompt-, event-, receipt-, process-, or
environment-visible projection, it MUST remove the raw token while preserving
the non-secret preview id and hashes required by that projection. Any raw token
in another result type or path invalidates the complete result.

A Grant Credential, bearer token, proof key, DPoP proof, cookie, private key,
private receipt material, or upstream application credential has no such
exception and MUST NOT appear in MCP resources, tool definitions, `arguments`,
`_meta`, structured or text content, resource links, progress, errors, logs,
prompts, model context, process arguments, or an agent-visible environment.

This profile defines no new credential transport. The deployment MUST select
an existing ASP credential-binding profile that delivers the credential and
per-attempt proof to the Action Executor over an authenticated confidential
channel outside JSON-RPC data. The MCP endpoint MUST be the exact endpoint in
the verified manifest binding and Grant location. Under `asp-native`, the
credential audience remains the manifest's exact logical
`agent_api.credential_audience`, while the selected credential profile applies
its request-target or channel binding to the actual MCP endpoint; for example,
a DPoP proof binds its `htu` to that endpoint. Only the dual-use composition
below additionally requires `credential_audience` to equal the canonical MCP
endpoint.

A Streamable HTTP deployment MUST select exactly one of these authorization
compositions:

- **ASP-native authorization**: the endpoint does not use the MCP OAuth
  authorization framework and instead uses the custom authentication strategy
  permitted by MCP. It applies the selected ASP HTTP credential profile
  directly, including `Authorization: DPoP` plus the request-bound `DPoP`
  header, mTLS, or the explicitly selected Compatibility Bearer Credential
  Profile.
- **MCP-OAuth dual use**: the endpoint uses MCP's required
  `Authorization: Bearer` form, and the same audience-bound access token is
  also the ASP Grant Credential. This is conforming only for the Compatibility
  Bearer Credential Profile or an mTLS-bound bearer token whose certificate
  and complete Grant binding the Action Executor independently verifies. The
  token audience MUST equal both the canonical MCP server URI selected by MCP
  authorization and the manifest-pinned ASP `credential_audience`; if those
  identifiers differ, dual use is impossible in version 1.

A DPoP-bound ASP Grant Credential cannot use the dual-use composition because
RFC 9449 requires the `DPoP` authorization scheme while MCP `2025-11-25`
requires `Bearer` for its OAuth framework. Version 1 MUST NOT place a second
Grant Credential in `_meta`, a custom JSON-RPC field, a query parameter, or a
second authorization value to work around that conflict. A separately issued
MCP bearer used only for transport alongside a DPoP Grant Credential is likewise
outside this profile until a future binding defines a non-conflicting channel.

Every HTTP request in the binding, including initialization and the event
listener, carries the selected authentication; no credential is moved to a URI
or JSON-RPC member. Every POST uses `Content-Type: application/json` and accepts
both `application/json` and `text/event-stream`; every listener GET accepts
`text/event-stream`. Every post-initialization request also carries the exact
`MCP-Protocol-Version` and `MCP-Session-Id` headers. Binding responses send
`Cache-Control: no-store`. The server validates any received `Origin` according
to MCP Streamable HTTP and rejects a disallowed origin before ASP processing.

MCP transport authorization is necessary when selected but never sufficient
ASP authority. A dual-use token becomes ASP authority only after its exact
audience, resource, subject, runtime, agent, Grant, surface, and credential
bindings satisfy the selected ASP profile and the application verifies them as
such. An intermediary MCP server MUST NOT pass its inbound access token to an
upstream application; it obtains a separately issued or exchanged
audience-bound credential under the ordinary Grant rules. Successful MCP OAuth,
an MCP scope, or an MCP server allow-list never substitutes for the Agent
Grant.

Validation follows producer lifecycle rather than one all-at-once projection.
The Surface Publisher owns negotiation, manifest-resource, and binding-view
production only. The Runtime Mediator validates discovery and the outbound
request before dispatch. The Action Executor then reconstructs, admits, and
executes the request and produces the application result. Only after dispatch
does the Runtime Mediator validate the returned result and receipt resources.
A post-dispatch validation failure preserves the dispatch and possible-effect
state; it cannot be reported as a pre-dispatch rejection merely because the
same component validates both phases.

### Structured Results and Receipt Resources

A mapped call returns a `CallToolResult` containing exactly `content`,
`structuredContent`, and explicit `isError`; top-level `_meta` and unknown
members are absent. Its `structuredContent` is this closed transport envelope:

```json
{
  "profile": "https://github.com/0al-spec/agent-surface/profiles/asp-over-mcp/v1",
  "mcp_protocol_version": "2025-11-25",
  "binding_view_id": "mcp_view_01J2A7M8J3V6",
  "message": {
    "type": "action.result",
    "payload": {
      "session_id": "sess_456",
      "session_generation": 1,
      "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
      "span_id": "6f2c4a91b7380d25",
      "grant_id": "grant_123",
      "grant_hash": "sha-256:<base64url-digest>",
      "surface_hash": "sha-256:<base64url-digest>",
      "action_id": "comment.create",
      "idempotency_key": "idem_01HX7DS8AC6G9",
      "execution": {
        "mode": "commit",
        "execution_id": "exec_01J2COMMENT"
      },
      "execution_hash": "sha-256:<action-execution-digest>",
      "result": "success",
      "effect_outcome": "applied",
      "actual_effects": [
        {
          "effect_id": "comment-publish",
          "operation": "publish",
          "resource_type": "comment",
          "resource_key": "comment_789",
          "visibility": "shared",
          "boundary": "internal",
          "reversibility": "irreversible",
          "domain": "communication"
        }
      ],
      "actual_effects_hash": "sha-256:<actual-effects-digest>",
      "output": {
        "resource": {
          "type": "comment",
          "id": "comment_789"
        }
      },
      "receipt_id": "receipt_app_abc",
      "receipt_hash": "sha-256:<app-receipt-digest>"
    }
  },
  "receipt_resource_uris": [
    "https://example.com/agent-receipts/receipt_app_abc"
  ]
}
```

`message` is exactly one of the three closed variants defined here:

- `action.result` is one complete ordinary ASP Action Response. Every
  successful result in this binding contains `payload.output`, and that member
  validates against the exact `output_schema` of the mapped manifest action.
  The core tuple, result, execution, effect, approval, and receipt members are
  siblings of `output`, not part of the action-specific schema.
- `action.error` is the application-originated error projection defined below.
- `binding.error` is the pre-admission binding rejection defined below.

The success example omits only mode-specific Action Response members that do
not apply to its illustrated action. The binding envelope MUST repeat the
accepted profile, MCP version, and view id; the runtime rejects a mismatch
before exposing any result to the agent or updating local outcome state.

An application error after reconstruction uses this shape:

```json
{
  "type": "action.error",
  "payload": {
    "session_id": "sess_456",
    "session_generation": 1,
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "6f2c4a91b7380d25",
    "grant_id": "grant_123",
    "grant_hash": "sha-256:<base64url-digest>",
    "surface_hash": "sha-256:<base64url-digest>",
    "action_id": "comment.create",
    "idempotency_key": "idem_01HX7DS8AC6G9",
    "error": {
      "code": "scope_denied",
      "description": "The Grant does not permit this action.",
      "retryable": false
    }
  }
}
```

The `action.error` payload requires the repeated session, producer trace and
span, Grant, surface, and action tuple and the closed `error` object. It echoes
the exact `idempotency_key` if and only if the reconstructed request contained
one. When ordinary ASP response rules require execution context, it carries the
sanitized `execution` and matching `execution_hash` together; otherwise both
are absent. If an effect was attempted or might have occurred, it MUST carry
the complete `effect_outcome`, `actual_effects`, and `actual_effects_hash`
triple; a definite pre-effect rejection omits all three. An application
error produced after valid request-side Approval Receipt evidence was accepted
MUST repeat the request's exact role-indexed `approval_receipt_hashes` map. It
MAY add the `application` role only when application approval completed and the
final application action receipt contains that same final map. The
pre-admission `rate_limited`, `capacity_state_unavailable`, and
`service_unavailable` errors MUST omit `approval_receipt_hashes`. An application
`approval_denied` separately carries the paired `approval_receipt_id` and
`approval_receipt_hash`; other errors omit them. A failure receipt required or
produced by ordinary ASP policy appears as paired `receipt_id` and
`receipt_hash`, with its complete resource URI in the outer envelope; when no
receipt exists, all three references are absent. No error contains `output` or
any payload member not enumerated here. The error object contains exactly a
registered ASP `code`, a
non-empty description of at most 1024 Unicode scalar values safe for the
authenticated caller, and boolean `retryable`, plus only these code-specific
members:

- `rate_limited` MAY carry the exact closed `limit` object from the Error
  Model;
- `capacity_state_unavailable` or `service_unavailable` MAY carry a positive
  I-JSON-safe integer `retry_after_seconds` only when `retryable` is true; and
- every other code carries no additional error-object member in version 1.

The producer validates its candidate output before emitting `action.result`.
If that validation fails, it returns `action.error` with `schema_invalid` and
the ordinary effect and receipt state rather than declaring success. If the
Runtime Mediator instead receives an already-declared success whose output is
missing or schema-invalid, that is a post-dispatch local `binding_invalid`
condition: it suppresses the result, preserves the original idempotency
identity, treats outcome and evidence as unresolved, and reconciles. It MUST
NOT fabricate an application error, infer no effect, or retry with a new key.

The complete `CallToolResult`, including its TextContent, structured tuple,
receipt references, and resource links, terminates at the Runtime Mediator. It
MUST NOT be copied automatically into agent or model context. Only after all
binding, ASP, output-schema, receipt, and Data Exposure checks succeed can the
runtime create a separate purpose-minimized adapter result containing the
action-specific `payload.output` or a safe error projection. That projection
omits transport metadata, Grant and session identifiers or hashes,
idempotency identity, receipt locations, and other fields not independently
declared and required for the agent's current task.

`content` contains exactly one JSON TextContent serialization of the complete
`structuredContent` envelope, followed by at most one `resource_link` block
for each declared receipt URI and no other block. After strict I-JSON parsing,
the TextContent `text` MUST have the same JSON data model as
`structuredContent`; duplicate members, invalid I-JSON, or a mismatch
invalidates the complete result. Its optional `annotations` and `_meta` are
absent. The text copy is compatibility output and is never independently
authoritative. Every link
URI occurs exactly once in `receipt_resource_uris` and exactly once among the
link blocks. A receipt ResourceLink uses the fixed `name` value `asp-receipt`
and MUST omit `title`, `description`, `icons`, `annotations`, `_meta`,
`mimeType`, and `size`; the runtime consumes it internally and MUST NOT pass it to the
agent or model as instructions or evidence.

Version 1 carries every complete application or approval receipt returned by
this binding as an MCP resource named by `receipt_resource_uris`; it defines no
inline receipt alternative. The array contains unique absolute resource URIs
and is absent or empty only when the result references no receipt and ordinary
ASP policy requires none. When the Action Response references a receipt, or
the `action.error` references an application, failure, or approval receipt, or
ordinary ASP policy requires a complete receipt, the server MUST make every
complete receipt available through the same authenticated MCP resources
capability and include exactly one corresponding URI in the array. A receipt resource is available
only through the same authenticated application context and effective Data
Exposure Contract. Its `ReadResourceResult` contains only `contents`, whose
array contains exactly one TextResourceContents, never a blob, whose `uri` equals the requested
receipt URI, whose `mimeType` is exactly `application/json`, whose `text` is
one complete strict I-JSON receipt, and whose optional `_meta` is absent. A
resource URI, link, receipt id, receipt hash, status text, icon, annotation, or
MCP server signature is correlation only. The runtime retrieves the complete
receipt when policy requires it and applies the ordinary producer-role, tuple,
hash, signature, parent-chain, approval-link, effect, budget, and lifecycle
checks. It MUST NOT send the complete receipt to the model merely because MCP
represented it as content.

Before emitting a result that references a receipt resource, the application
atomically persists the immutable receipt bytes and stable resource URI for at
least the ordinary receipt-retention period. `MCP-Session-Id` is never part of
that URI or receipt identity. If the transport session is lost after the
result, a freshly initialized dedicated session authenticated for the same
application subject, runtime, agent, Grant, and Data Exposure context MUST
re-materialize the exact URI and bytes without creating another action,
effect, charge, or receipt. If the Grant can no longer authenticate retrieval,
the ordinary independently authenticated audit-retrieval policy at
`agent_api.receipt_url` governs access; a hash alone still does not satisfy a
complete-receipt requirement.

The server MUST preserve immutable Action Response and receipt behavior across
an exact idempotent replay. MCP redelivery, reconnect, or another JSON-RPC id
does not authorize a new response, charge, effect, or receipt. Resource loss
does not let a runtime accept the hash alone when the ordinary profile requires
the complete receipt.

### Error, Progress, Cancellation, and Recovery Mapping

MCP protocol errors are used for MCP framing failures, unsupported methods,
unknown tool names, malformed `tools/call` messages, failure to negotiate this
binding, or an MCP-layer server failure before one valid ASP request is
reconstructed and accepted. They are not ASP Error objects, application
denials, or proof that no effect occurred, and an intermediary MUST NOT
synthesize ASP `service_unavailable` from such a failure. An otherwise
well-formed MCP call missing `_meta`, the namespaced record, or a valid non-empty
`binding_view_id` is malformed for this profile and uses JSON-RPC Invalid
Params; there is no value that a binding result could safely echo. A complete
MCP `tools/call` whose `arguments` fail the advertised action input schema is
not a malformed MCP request: after exact reconstruction it returns an
`action.error` carrying `schema_invalid` in a `CallToolResult`.

A JSON-RPC error accepted by this profile contains exactly `jsonrpc`, the
matching string or I-JSON-safe integer request `id` when known, and `error`.
For an MCP transport rejection that has no request id, the `id` member is
omitted rather than set to null. `error`
contains exactly an I-JSON-safe integer `code` and a non-empty `message` of at
most 256 Unicode scalar values and omits `data`. The Runtime Mediator consumes
that message, every HTTP error body, status explanation, and non-profile header
internally. It exposes only a locally generated bounded classification to the
Agent Adapter or user and MUST NOT forward raw server text to the agent or
model or treat it as retry, admission, effect, receipt, or authority evidence.

A gateway that parses the complete closed binding record but deterministically
detects a stale or conflicting view, tool mapping, duplicate, or schema
projection before ASP reconstruction or any semantic admission returns a
`CallToolResult` with `isError: true` and this closed message variant:

```json
{
  "type": "binding.error",
  "payload": {
    "code": "binding_invalid",
    "description": "The MCP binding view is not current.",
    "retryable": false,
    "admission_outcome": "not_admitted"
  }
}
```

The payload has exactly those four members, the description has the same
bounded safe-text rule as `action.error`, and the outer result omits
`receipt_resource_uris` and ResourceLinks. The outer `binding_view_id` echoes
only the rejected request's value for correlation; it does not disclose or
authorize the current view. This pre-admission result is permitted only when the
gateway can prove that no ASP idempotency record, budget charge, reservation,
workload, receipt, or effect was admitted. A result-side binding, tuple,
output-schema, receipt, or text/structured-content mismatch is instead a local
post-dispatch `binding_invalid` condition with unresolved outcome and
reconciliation; it MUST NOT be represented retroactively as this no-effect
wire result.

After the Action Executor accepts a reconstructed Action Request for ordinary
ASP processing, an ASP validation, authority, policy, approval, capacity,
business, effect, or recovery failure is returned as the closed
`action.error` message with `isError: true`. A successful `action.result` uses
`isError: false`; `binding.error` also requires `isError: true`. Any
message/bit disagreement invalidates the post-dispatch result and requires
reconciliation. HTTP or MCP authorization failure remains a transport failure.
An MCP protocol error, transport status, retry hint, log message, or `isError`
bit MUST NOT override the application error's retryability, effect outcome,
idempotency identity, capacity semantics, or receipt requirements.

MCP progress notifications are advisory liveness signals only. They do not
prove admission, approval, reservation, an effect, a budget charge, receipt
production, cancellation, or final outcome. A runtime MAY extend a bounded
local wait after valid progress, but it still enforces its maximum timeout,
operational limits, budgets, and runaway guards.

An MCP cancellation notification, call timeout, call response-stream loss,
HTTP request disconnect, or GET-listener loss while the same MCP session
remains active means only that the sender stopped waiting or requested
best-effort transport cancellation. It MUST NOT be translated to ASP session
cancellation, action cancellation, compensation, revert, denial, or proof of
no effect. In contrast, an owner-authenticated accepted MCP session `DELETE`,
server-authoritative expiry or termination of an existing session, or detected
shutdown of its authenticated owner is loss of this profile's runtime channel
and invokes the ordinary Runtime Disconnected transition; it is not action
cancellation or proof of no effect. An unknown or authentication-mismatched id
still produces only the non-mutating `404` defined above. In this profile
`notifications/cancelled` is generated only by the
Runtime Mediator, repeats the exact outstanding MCP request id, and omits
`reason` and unknown members; an unknown or completed id is ignored as
transport state and never selects an ASP action. Before application dispatch or any semantic admission,
the receiver SHOULD honor MCP cancellation by stopping work when it can
deterministically prove that no ASP idempotency record, budget charge,
reservation, workload, receipt, or effect was admitted. It records only that
local pre-admission disposition; the notification itself is not the proof.
After dispatch, admission, or any ambiguity, the Action Executor continues or
records the authoritative ASP outcome according to the action's ordinary
contract, and the Runtime Mediator reconciles that outcome. This preserves
MCP's best-effort cancellation behavior without converting transport state into
ASP effect state.

This profile deliberately narrows MCP's recommendation that a cancellation
sender ignore a later response. The Runtime Mediator does not deliver a late
response as the cancelled caller's ordinary completion, but it MUST consume and
validate a valid late `CallToolResult` and its receipts internally to converge
the original idempotency and outcome record. A missing or invalid late result
leaves reconciliation pending. Neither case permits a new key or duplicate
effect merely because caller-facing waiting ended.

After any ambiguous outcome, the Runtime Mediator preserves the original ASP
idempotency key, normalized input, hashes, execution identity, Grant and
session tuple, and receipt linkage. It reconciles authoritative application
state or performs only an exact idempotent replay with fresh per-attempt
transport proof. It MUST NOT allocate a new key, choose another mapped tool,
change input, retry from an MCP annotation, or report success, failure, or
cancellation until the ASP outcome is known. All transport attempts and exact
replays remain counted by the ordinary operational and runaway guards.

MCP prompts, roots, sampling, elicitation, logging, and other negotiated
capabilities are outside this binding. If a deployment uses them under another
profile, it does so on a separate session; their content remains subject to ASP
data-exposure and runtime policy, and none can create or satisfy a Grant,
consent, approval, action, effect, receipt, or recovery decision.
