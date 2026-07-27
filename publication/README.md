# ASP Specification Publication Contract

`document-set.json` is the normative machine-readable catalog for the ASP
specification document set. Its closed schema and semantic validator distinguish
active canonical sources from documents that are only reserved for a future
modular publication.

Active source, aggregate, and registry entries bind their exact bytes with
SHA-256. Public anchors and local compatibility aliases are explicit,
source-checked, globally unique catalog entries. Internal normative references require a
declared exact dependency edge and a resolvable source-anchor/target-export
record.

The current publication mode is deliberately transitional:

- `drafts/agent-surface.md` remains the only active canonical source;
- Core, Authorization, Safe Effects, Evidence, Privacy, Conformance, and the
  ASP-over-MCP binding have reserved document identities and an exact planned
  dependency graph;
- reserved paths have no normative authority and MUST NOT exist until an atomic
  catalog transition activates their complete source set;
- Hyperprompt manifest and source-map artifacts are build provenance, not
  owners of ASP semantics, identifiers, registries, or compatibility.
- the current validator rejects `modular` mode until #78 supplies the complete
  Hyperprompt provenance, source-map, anchor, digest, and readiness resolver.

Validate the contract with:

```sh
make publication-check
```

Non-authoritative extraction fixtures can be prepared under
`publication/candidates/`. #79 changes `publication_mode` to `modular` only
when all canonical module sources, an exact-revision Hyperprompt assembly, its
manifest and source map, the generated aggregate, legacy-reference resolution,
and every validation gate are ready together. Moving only some prose or creating a
reserved target file without that transition fails closed.
