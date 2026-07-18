# ASP Reference Mock App / Mock Runtime

This directory contains deterministic synthetic participants for exercising the
ASP conformance harness without a real agent or production application data.
They are test fixtures, not protocol authorities or conformance certificates.

The Mock App implements four atomic boundaries: Surface Publisher, Grant
Issuer, Action Executor, and application-role Receipt Producer. The Mock
Runtime implements Runtime Mediator, Agent Adapter, and runtime-role Receipt
Producer. Each role remains an independent boundary and must be reported
separately.

## Security boundary

The bundle manifest has `claim_effect: suite_fixture_only`. The adapter rejects
any subject whose `subject_kind` is not `suite_fixture`; a successful mock run
therefore cannot become implementation or interoperability evidence.

`behavior.py` is deliberately oracle-independent. It receives only a profile,
producer role, operation, resolved semantic document, and initial authoritative
state. It does not read the conformance suite, vectors, fixture labels, expected
errors, or expected observations. Decisions are derived from semantic fields.
The Operational Limits feature paths cover manifest binding, atomic action
admission, fail-closed limiter-state loss, idempotent replay precedence,
first-delivery versus retransmission accounting, and runtime `rate_limited`
retry policy. It also keeps `capacity_state_unavailable` retries deferred until
authoritative limiter recovery, requires a new capacity decision for retryable
`service_unavailable`, and routes ambiguous outcomes to reconciliation instead
of treating them as definite overload rejections. The HTTP capacity paths bind
application responses to `429` or `503` plus `no-store`, validate
`Retry-After` against the body hint where required, and reject inconsistent
runtime inputs before local admission state is released. The fixture's
normalized `transport` section is harness data, not a simulated HTTP wire
format. The ASP-over-AHP paths validate the explicitly negotiated profile,
authenticated carrier, monotonic representation revision, complete bound ASP
tuple, exact action, and informational-only receipt use. They never derive ASP
authority from AHP UI state; invalid bindings are rejected before presentation
or forwarding. The normalized `ahp` section is likewise harness data rather
than a base AHP wire specification.

The internal `asp-mock-participant/1` protocol is test control plumbing, not an
ASP wire binding. `mock_app.py` and `mock_runtime.py` accept one closed envelope
on standard input:

```json
{
  "participant_protocol": "asp-mock-participant/1",
  "operation": "inventory",
  "request": {}
}
```

The operation is `inventory`, `execute`, or `observe`; `request` is the
corresponding conformance probe or adapter invocation. The canonical
`adapter.py` and `probe.py` entrypoints expose the existing
`asp-conformance-adapter/1` and `asp-conformance-probe/1` processes directly.

## Authoritative state

Every execute operation initializes exactly one journal scoped by `run_id`,
`vector_id`, and `boundary_id`. App and Runtime use separate family stores.
State is written to a private temporary file, flushed, and atomically renamed.
A repeated initialization, stale binding, partial write, extra file, symlink,
duplicate JSON member, malformed value, or missing journal fails closed. The
probe reports only the exact states requested by the runner.

The harness creates a fresh working directory for each vector, so the mocks do
not retain credentials or real user data. Only synthetic catalog documents may
be used. The process limits in the conformance runner are not a sandbox;
operators must still isolate the test environment.

## Validation

```sh
.venv/bin/python -B mocks/check.py validate
.venv/bin/python -B -m unittest discover -s mocks/tests -p 'test_*.py'
```

`mocks/check.py` validates the versioned manifest, exact role and feature
closure, executable modes, and the raw-byte SHA-256 digest of every shipped
bundle artifact. The manifest intentionally excludes its own bytes to avoid a
self-referential digest.

Mock-vs-mock execution can validate plumbing and deterministic behavior, but it
is not independent interoperability evidence. An external implementation must
use its own authoritative probe and separately bound artifact/configuration
before any higher maturity claim is considered.
