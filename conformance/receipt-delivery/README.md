# HTTP inline receipt carrier vectors

The normative delivery contract is **HTTP Inline Receipt Delivery** in
`drafts/modules/evidence.md`. This focused artifact supplements the main
conformance catalog; it is not a seventh conformance role or a full-profile
interoperability report.

`v1/carrier.schema.json` provides closed manifest declaration, request-carrier,
and response-carrier shapes. The extension lives at
`payload["https://github.com/0al-spec/agent-surface/extensions/http-inline-receipts/v1"]`.
The schema's receipt identity/role guards deliberately do **not** replace the
existing complete Receipt, Policy Decision, Approval Receipt, or signing
profiles. Passing a carrier schema with a partial receipt is not acceptance.

`v1/cases.json` contains positive/negative structural vectors. The focused test
also exercises strict duplicate-member rejection using the existing parser.
These cases prove structure only: they do not verify real HTTPS, producer
authentication, hash recomputation, tuple agreement, freshness, current
authority, persistence, or exact retry. Those remain implementation gates for
the subsequent SDK and application integration slices.

Run the bounded check with:

```sh
.venv/bin/python -B -m unittest discover -s conformance/tests -p 'test_inline_receipt_delivery.py' -v
```

The ordinary `make conformance-test` and GitHub RFC quality job discover the
same tests without another workflow or a network dependency.

## Implementation qualification still required

| Requirement | This RFC slice | Next SDK/application gate |
| --- | --- | --- |
| Closed carrier, role guard, no URL/hash-only substitution | Executable structural vectors | Parse the namespaced extension at the real request/response boundary. |
| Manifest selection and required Grant audit fields | Normative definition | Reject unsupported, unlisted or undeclared selection before dispatch/admission. |
| Complete receipt/profile validation and exact hashes | Existing rules retained, carrier schema deliberately insufficient | Reject missing Policy Decision, mutated hashes, role/tuple/input/output/parent mismatches. |
| Producer authentication and signing | Normative trust separation | Bind TLS to the selected application and credential/proof to the selected runtime; verify required and present signatures. |
| HTTPS body delivery | Normative HTTP requirements | Real trusted-CA TLS; invalid CA/host, redirect, malformed/oversized body, timeout and cancellation vectors. |
| Replayable terminal outcomes | Ordinary durable lifecycle retained | Lost response, restart, exact retry and immutable denial/failure receipt tests. |
| Disclosure boundary | No new model/UI permission | Confirm complete receipts and authority material do not reach unapproved recipients. |

Keep the first SDK integration bounded to the existing non-persisted proposal
contract. Do not advertise support for approval, durable effect recovery, MCP
inline delivery, or all profile-listed action modes from that first integration.
Calcu is one implementation exercise, not the definition of this generic binding.
