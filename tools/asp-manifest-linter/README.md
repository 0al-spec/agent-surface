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
| `ASP-LINT-RISK-001` | A non-empty action `risk` label. |
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

The linter checks declarations only. It does not verify remote schema bytes,
`surface_hash`, issuer identity, runtime behavior, Grant state, approval,
effects, receipts, or interoperability.

