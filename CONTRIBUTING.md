# Contributing to Agent Surface RFC

Thank you for considering contributing to this specification.

This repository contains the canonical draft of the **Agent Surface Protocol**:
a user-mediated delegation protocol for connecting user-owned agents to
application-defined, app-enforced, typed action surfaces through a
policy-enforcing runtime.

## Repository Structure

```text
agent-surface/
  drafts/                  Source RFCs written in Markdown.
  conformance/             Executable role matrix, vectors, schemas, and runner.
  schema/                  Optional JSON/YAML schemas.
  generated/               Optional generated XML, TXT, or PDF artifacts.
  examples/                Optional example manifests, grants, and receipts.
```

## How to Contribute

1. Fork this repository.
2. Create a branch from `main`:

   ```bash
   git checkout -b feature/my-change
   ```

3. Edit the RFC in Markdown:

   ```text
   drafts/agent-surface.md
   ```

4. Submit a pull request to `main`.

## Style Guidelines

- Write in clear, formal English.
- Use normative language (`MUST`, `SHOULD`, `MAY`, etc.) consistently with RFC
  2119 and RFC 8174.
- Preserve the central authority model:

  ```text
  User is the principal.
  Agent Passport is evidence, not authority.
  Agent Grant is the semantic authorization.
  Runtime enforces local policy.
  App enforces app-side authorization.
  ```

- Keep terminology stable:
  - `Agent Surface`
  - `Agent Surface Manifest`
  - `Agent Grant`
  - `Grant Credential`
  - `Runtime`
  - `Agent Passport`
  - `Runtime Receipt`
  - `App Receipt`

- Keep schemas and examples in sync with the RFC text when they are added.
- Keep conformance matrix, vector, fixture, schema, runner, and report changes mutually
  consistent and run `make conformance-check`.
- Prefer proposal-first workflows for risky actions:

  ```text
  read -> propose -> approve -> write -> receipt
  ```

## License

By contributing, you agree to license your specification and documentation
contributions under the Creative Commons Attribution 4.0 International License
(CC BY 4.0), and source code or tooling contributions under the MIT License.
