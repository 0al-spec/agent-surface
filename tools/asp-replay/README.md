# ASP Replay Tool

`asp-replay` performs a deterministic, offline consistency and integrity replay
of one portable ASP session evidence bundle.

```sh
cargo run --locked -p asp-replay-tool -- verify bundle.json
cargo run --locked -p asp-replay-tool -- verify - < bundle.json
cargo run --locked -p asp-replay-tool -- self-check --root .
```

The verifier parses strict I-JSON, checks the embedded historical Surface and
Grant hashes, validates the record hash chain, reduces session transitions,
checks event delivery and acknowledgement identity, and verifies receipt
hashes and links. It never follows a URI, opens a socket, invokes an action,
sends a replay request, changes a session, or resolves remote schema content.

Exit status `0` means the present evidence is valid and complete. Status `1`
means the deterministic report is incomplete or invalid. Status `2` means the
input or tool could not be evaluated safely; no report is written to standard
output.

Every emitted report has one exact `evaluation_state`:

- `preflight_failed`: a structure, context, secret, record-envelope, hash,
  ordinal, or prior-link check failed; dependent semantic checks are
  `not_evaluated`.
- `semantic_invalid`: preflight passed and an evaluated lifecycle, event,
  acknowledgement, gap, or receipt check failed.
- `incomplete`: all integrity checks passed, but an explicit permitted evidence
  gap prevents a complete conclusion.
- `valid`: all checks in the selected bounded check profile passed.

Both invalid states use a neutral replay summary and empty
`assurance.verified`. Only `preflight_failed` can carry a null `bundle_id` or
`bundle_hash`; those values are required for every semantically evaluated
report. Diagnostics are capped at 256 entries. `diagnostics_truncated` and
`diagnostics_omitted` make any path/message truncation or omitted findings
explicit without hiding the check-level failure counts.

## Evidence boundary

A `valid` report establishes only the checks enumerated, in order, by the exact
`tool.check_profile` embedded in the report. `self-check` requires that ordered
set to match the 12 compiled check definitions and requires executable
diagnostic coverage for every check. A local `pass` is not a complete-profile
conformance claim.

Within that bounded profile, a valid report establishes internal consistency
for the exact bytes supplied.
It does not authenticate an exporter or producer, verify receipt signatures,
establish current Grant, Surface, or session state, provide trusted time, prove
that an external effect occurred, or validate remote schemas. A bundle hash is
tamper-evident only relative to an independently trusted value or signature.
The bounded replay checks required historical binding fields, hashes, and links;
it is not a complete native semantic-schema validator for every Surface, Grant,
CloudEvent payload, or receipt variant.

Callers that require complete native Surface, Grant, or receipt validation must
run the authoritative validators for those object profiles as a separate gate.
The CLI checks the historical Grant-local Approval Receipt role and
`max_age_seconds` projection and a carried Grant expiry, but receiver-local
first-authenticated time, preview/reservation expiry, full native receipt
semantics, producer keys, and JWS verification remain outside this bounded
tool.
When any integrity check fails, `replay.status` is `not_evaluated` and lifecycle
and receipt summary fields are neutralized rather than presented as replayed
state.

Event payloads can contain sensitive application data because an exact
CloudEvent is required to recompute `aspeventhash`. Reports never copy payload
values into diagnostics. Operators remain responsible for protected storage,
access, retention, and deletion of bundle bytes.
