# ASP Manifest Linter

`asp-lint` performs deterministic, offline checks over one Agent Surface
Manifest. It does not contact schema hosts, execute manifest content, evaluate
live authorization state, or make a conformance or deployment-readiness claim.

## Usage

```sh
cargo run --locked -p asp-manifest-linter -- check manifest.json
cargo run --locked -p asp-manifest-linter -- check manifest.json --format json
```

Use `-` as the manifest path to read standard input. Exit status `0` means no
findings, `1` means one or more lint findings, and `2` means the input or tool
could not be evaluated safely.

## Version 1 rules

| Rule | Checks |
| --- | --- |
| `ASP-LINT-SCHEMA-001` | Resource and event `schema`; action `input_schema` and `output_schema`. |
| `ASP-LINT-RISK-001` | One of the eight core `risk` labels or a non-empty ASCII URI valid under RFC 3986 generic syntax. |
| `ASP-LINT-RISK-EXPLANATION-001` | Closed and bounded `risk_explanation`, restricted language/script/region/unique-variant tags, canonical ordering, C0/C1/Bidi_Control-free summary text, and exact parent-effect coverage. |
| `ASP-LINT-IDEMPOTENCY-001` | Required idempotency, normalization, input hashing, and schema hash for state-changing and persisted proposal actions. |
| `ASP-LINT-SCOPE-001` | Unique declared scopes and consistent resource, action, and event references. |

The canonical registry is `rules/v1/rules.json`. JSON diagnostics conform to
`schema/diagnostics.schema.json` and use stable rule identifiers and JSON
Pointers.

## Security boundary

The parser rejects duplicate object members, floating-point values, integers
outside the I-JSON safe range, malformed Unicode, trailing JSON, and non-object
manifest roots. Rule and diagnostic schemas are embedded in the binary and
checked against their repository copies by `self-check`.

The linter checks declarations only. A valid `risk_explanation` remains
untrusted publisher prose and does not establish risk, effects, approval,
consent, policy, or authority. For an extension risk label, the linter validates
only the generic URI syntax, including component delimiters and percent
encoding. It does not establish collision resistance, scheme registration, or
the existence of a defining specification. The runtime remains responsible for
supporting that specification and verifying its conservative core-risk mapping.
The linter does not verify remote schema bytes, `surface_hash`, issuer identity,
runtime behavior, Grant state, receipts, or interoperability.
