# ASP API Importer

`asp-api-import` is a publishing-time candidate generator for deliberately
annotated OpenAPI and AsyncAPI documents. It copies complete ASP members from
`x-agent-surface` annotations into a manifest base, sorts the resulting
inventories, computes `surface_hash`, and runs the bounded ASP manifest linter
before emitting a candidate.

```sh
cargo run -p asp-api-importer -- generate api.json
cargo run -p asp-api-importer -- generate - < api.json
cargo run -p asp-api-importer -- self-check --root .
```

The v1 importer is intentionally JSON-only. It does not parse YAML, access the
network, resolve `$ref`, expand OpenAPI callbacks or webhooks, apply AsyncAPI
traits, or infer ASP fields from operation names, schemas, routes, channels,
tags, security declarations, or other source metadata. An annotated reference
is rejected instead of being partially interpreted.

## Security and authority boundary

Importing an annotation is a deterministic publication convenience, not an
authorization decision. API existence, an OpenAPI security scheme, an AsyncAPI
channel, and successful import do not grant an agent authority. Publishers
must deliberately author every complete ASP member and remain responsible for
the resulting manifest, consent flow, Grant enforcement, runtime checks, and
receipt behavior.

Unannotated operations are ignored, including operations that would be
dangerous if exposed. The importer fails closed on unsupported versions or
annotation placements, duplicate members, incomplete annotation envelopes,
reserved output fields in `manifest_base`, and every final linter diagnostic.
It writes no partial manifest to standard output on failure.

The importer uses an RFC 8785 canonicalizer for the complete manifest hashing
view, including finite binary64 values in publisher extensions. It passes the
exact generated value to the adjacent linter's value API, without reparsing or
masking extension numbers. The current lint rules remain bounded checks rather
than complete manifest validation. Publishers must apply a complete validator
before serving the candidate.

The annotation profile is
`https://github.com/0al-spec/agent-surface/profiles/api-import/v1`. Its
Draft 2020-12 schema and executable positive and negative cases are stored
beside the tool and verified by `self-check`. The case registry also pins the
exact manifest-linter ruleset accepted by generation; ruleset id or version
drift fails closed until the binding and cases are deliberately updated.
