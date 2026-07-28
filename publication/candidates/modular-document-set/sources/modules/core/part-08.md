# Open Questions

- Does the first MVP use app-issued grants only, or also support
  runtime-held grants for compatibility with existing OAuth APIs?
- Is `/.well-known/agent-surface.json` public, authenticated, or both
  depending on app tenancy?
- What is the minimal sender-constrained grant credential profile?
- How do users compare two agents with overlapping Agent Passport
  capabilities during grant consent?
- What happens to active sessions when an app changes surface versions?

# References

- Model Context Protocol Specification 2025-11-25:
  <https://modelcontextprotocol.io/specification/2025-11-25>
- Agent Client Protocol Overview:
  <https://agentclientprotocol.com/protocol/v1/overview>
- OpenAPI Specification 3.2.0:
  <https://spec.openapis.org/oas/v3.2.0.html>
- OpenAPI Specification 3.1.2:
  <https://spec.openapis.org/oas/v3.1.2.html>
- AsyncAPI Specification 3.1.0:
  <https://www.asyncapi.com/docs/reference/specification/v3.1.0>
- AsyncAPI Specification 3.0.0:
  <https://www.asyncapi.com/docs/reference/specification/v3.0.0>
- CloudEvents 1.0.2:
  <https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md>
- CloudEvents JSON Event Format 1.0.2:
  <https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/formats/json-format.md>
- CloudEvents HTTP Protocol Binding 1.0.2:
  <https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/bindings/http-protocol-binding.md>
- CloudEvents Distributed Tracing extension 1.0.2:
  <https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/extensions/distributed-tracing.md>
- HTTP Semantics:
  <https://www.rfc-editor.org/rfc/rfc9110>
- Additional HTTP Status Codes:
  <https://www.rfc-editor.org/rfc/rfc6585>
- OAuth 2.0:
  <https://www.rfc-editor.org/rfc/rfc6749>
- OAuth 2.0 Proof Key for Code Exchange:
  <https://www.rfc-editor.org/rfc/rfc7636>
- OAuth 2.0 Device Authorization Grant:
  <https://www.rfc-editor.org/rfc/rfc8628>
- JSON Web Token (JWT) Profile for OAuth 2.0 Client Authentication and
  Authorization Grants:
  <https://www.rfc-editor.org/rfc/rfc7523>
- OAuth 2.0 Token Revocation:
  <https://www.rfc-editor.org/rfc/rfc7009>
- OAuth 2.0 Token Introspection:
  <https://www.rfc-editor.org/rfc/rfc7662>
- OAuth 2.0 Token Exchange:
  <https://www.rfc-editor.org/rfc/rfc8693>
- OAuth 2.0 Resource Indicators:
  <https://www.rfc-editor.org/rfc/rfc8707>
- OAuth 2.0 Rich Authorization Requests:
  <https://www.rfc-editor.org/rfc/rfc9396>
- OAuth 2.0 Pushed Authorization Requests:
  <https://www.rfc-editor.org/rfc/rfc9126>
- Best Current Practice for OAuth 2.0 Security:
  <https://www.rfc-editor.org/rfc/rfc9700>
- OAuth 2.0 Mutual-TLS Client Authentication and Certificate-Bound Access
  Tokens:
  <https://www.rfc-editor.org/rfc/rfc8705>
- OAuth 2.0 Demonstrating Proof-of-Possession at the Application Layer (DPoP):
  <https://www.rfc-editor.org/rfc/rfc9449>
- OpenID Connect Core 1.0:
  <https://openid.net/specs/openid-connect-core-1_0-final.html>
- Remote ATtestation procedureS (RATS) Architecture:
  <https://www.rfc-editor.org/rfc/rfc9334>
- The Entity Attestation Token (EAT):
  <https://www.rfc-editor.org/rfc/rfc9711>
- Entity Attestation Token (EAT) Media Types:
  <https://www.rfc-editor.org/rfc/rfc9782>
- An Architecture for Trustworthy and Transparent Digital Supply Chains:
  <https://www.rfc-editor.org/rfc/rfc9943>
- SPIFFE Identity and Verifiable Identity Document specifications:
  <https://spiffe.io/docs/latest/spiffe-specs/spiffe-id/>
- SPIFFE X.509-SVID specification:
  <https://spiffe.io/docs/latest/spiffe-specs/x509-svid/>
- SPIFFE JWT-SVID specification:
  <https://spiffe.io/docs/latest/spiffe-specs/jwt-svid/>
- The I-JSON Message Format:
  <https://www.rfc-editor.org/rfc/rfc7493>
- Uniform Resource Identifier (URI): Generic Syntax:
  <https://www.rfc-editor.org/rfc/rfc3986>
- Tags for Identifying Languages:
  <https://www.rfc-editor.org/rfc/rfc5646>
- Matching of Language Tags:
  <https://www.rfc-editor.org/rfc/rfc4647>
- Base-N Encodings:
  <https://www.rfc-editor.org/rfc/rfc4648>
- Date and Time on the Internet: Timestamps:
  <https://www.rfc-editor.org/rfc/rfc3339>
- ISO 4217:2015 — Codes for the representation of currencies:
  <https://www.iso.org/standard/64758.html>
- JSON Web Signature (JWS):
  <https://www.rfc-editor.org/rfc/rfc7515>
- JSON Web Key (JWK):
  <https://www.rfc-editor.org/rfc/rfc7517>
- JSON Web Algorithms (JWA):
  <https://www.rfc-editor.org/rfc/rfc7518>
- JSON Web Key (JWK) Thumbprint:
  <https://www.rfc-editor.org/rfc/rfc7638>
- Deterministic Usage of DSA and ECDSA:
  <https://www.rfc-editor.org/rfc/rfc6979>
- JSON Web Signature Unencoded Payload Option:
  <https://www.rfc-editor.org/rfc/rfc7797>
- JSON Canonicalization Scheme (JCS):
  <https://www.rfc-editor.org/rfc/rfc8785>
- JavaScript Object Notation (JSON) Pointer:
  <https://www.rfc-editor.org/rfc/rfc6901>
- JavaScript Object Notation (JSON) Patch:
  <https://www.rfc-editor.org/rfc/rfc6902>
- Verified erratum 7920 for JSON Canonicalization Scheme:
  <https://www.rfc-editor.org/errata/eid7920>
- JSON Web Token Best Current Practices:
  <https://www.rfc-editor.org/rfc/rfc8725>
- Fully Specified Algorithms for JOSE:
  <https://www.rfc-editor.org/rfc/rfc9864>
- Secure Hash Standard (SHS), FIPS 180-4:
  <https://csrc.nist.gov/pubs/fips/180-4/upd1/final>
- W3C Trace Context:
  <https://www.w3.org/TR/trace-context/>
- Key words for use in RFCs to Indicate Requirement Levels:
  <https://www.rfc-editor.org/rfc/rfc2119>
- Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words:
  <https://www.rfc-editor.org/rfc/rfc8174>
- JSON Schema Draft 2020-12:
  <https://json-schema.org/draft/2020-12>
- YAML 1.2.2:
  <https://github.com/yaml/yaml-spec/blob/main/spec/1.2.2/spec.md>
- DID Core:
  <https://www.w3.org/TR/did-core/>
- Verifiable Credentials Data Model 2.0:
  <https://www.w3.org/TR/vc-data-model-2.0/>
- Agent Passport draft repository:
  <https://github.com/0al-spec/agent-passport>

# Appendix A: Why This Is Not Just an API Token

An API token answers:

```text
Can this bearer call this endpoint?
```

An Agent Grant answers:

```text
Which user delegated which agent, running through which runtime, verified by
which versioned identity evidence, to perform which typed app actions, against which
resources, under which caveats, until when, with which approval and receipt
requirements?
```

The second question is the actual security and product problem.

# Appendix B: Why This Is Not Just Computer Use

Computer use automates a UI from the outside. It is useful when no better
surface exists.

Agent Surface Protocol asks applications to expose an agent-native surface:

- typed reads
- typed proposals
- typed writes
- typed events
- scopes
- schemas
- approvals
- idempotency
- receipts
- revocation

The app remains in control of its resource model, and the user remains in control
of agent delegation.

# Appendix C: Product Positioning

Short form:

```text
Agent Surface Protocol lets users safely bring their own agents to apps.
```

Long form:

```text
Agent Surface Protocol is a user-mediated delegation protocol for connecting
user-owned agents to application-defined, app-enforced, typed action surfaces
through a policy-enforcing runtime.
```

Comparison:

```text
MCP exposes tools.
ACP connects clients to agents.
OAuth delegates access.
Agent Passport proves agent identity and capabilities.
Agent Surface + Agent Grant bind those pieces into safe app-specific delegation.
```
