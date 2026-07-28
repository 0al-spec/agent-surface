# Observability Context

ASP uses W3C Trace Context for cross-component diagnostic correlation. An ASP
session, action, event, and receipt MAY participate in a distributed trace, but
trace context is never authorization, identity, idempotency, or proof that two
objects belong to the same grant.

JSON envelopes that carry observability context use `trace_id` and `span_id`.
`trace_id` MUST be 32 lowercase hexadecimal characters representing 16 bytes
and MUST NOT be all zero. `span_id` MUST be 16 lowercase hexadecimal characters
representing 8 bytes and MUST NOT be all zero. These are projections of the W3C
`trace-id` and `parent-id` formats. `session_id` and `session_generation` remain
the ASP lifecycle and accounting context and MUST continue to be validated
independently.

The CloudEvents event binding is the exception to those JSON projection names:
an event uses the standard CloudEvents `traceparent` and optional `tracestate`
extensions and MUST NOT also carry `trace_id` or `span_id`. A runtime derives
the starting trace and producer span from valid `traceparent` when it records
the event locally.

When an implementation claims the Runtime Mediator or Receipt Producer
Profile, its `session.start`, `action.request`, `action.result`, and receipt
envelopes MUST carry `session_id`, `session_generation`, `trace_id`, and the
producer's `span_id` as shown below. Each runtime and application MUST record
the identifiers from the envelope or receipt it produces in the corresponding
local log entry so those logs can be joined without parsing human-readable
messages. Trace and session ids can match across components while each producer
records its own span id. This draft defines correlation fields, not a telemetry
export protocol or vendor backend.

For an HTTP binding, a component carrying valid ASP observability context MUST
send `traceparent`. A component participating in an incoming W3C trace MUST
propagate `traceparent` and `tracestate` according to W3C Trace Context, subject
to its defined trust-boundary privacy policy. It preserves a valid incoming
`trace_id`, creates a fresh `span_id` for its own operation, and propagates that
child context downstream. A receipt records the span of the component that
produced it. Runtime and application receipts for one action therefore normally
share `trace_id`, `session_id`, and `session_generation` but have different
`span_id` values.

An intermediary is allowed to create another span, so a receiver MUST NOT
require the JSON `span_id` to equal the `parent-id` in the HTTP header after
intermediation. For non-CloudEvent ASP JSON, a valid `traceparent` takes
precedence over the JSON projection. If no valid header exists and a verified
parent receipt is available, the receiver continues the parent receipt's
`trace_id` with a new span. Otherwise it uses a valid JSON `trace_id` or starts
a new trace, in that order. Direct CloudEvents delivery instead follows the
single-hop and multi-hop consistency rules in Binding Validation and Security.

If the selected processing trace differs from a verified parent receipt's
trace because an intermediary or trust boundary restarted it, the child receipt
MUST include `linked_trace_id` equal to the parent `trace_id`. Without such a
documented restart, parent and child receipts MUST use the same `trace_id`.
`linked_trace_id` uses the same format as `trace_id` and is included in the
receipt hash. Invalid or conflicting trace context MUST NOT cause an otherwise
unauthorized action to be accepted, and it MUST NOT bypass grant, session, or
receipt-link verification.

Trace identifiers MUST be generated without embedding user, agent, resource,
tenant, or policy semantics. Producers MUST apply the same disclosure and
retention controls to `tracestate` and correlated telemetry as to other audit
metadata. An Agent Adapter preserves `session_id` and a valid `trace_id` across
its boundary and creates a new `span_id` for each adapter operation.
