# Transitional Module Ownership Map

This directory contains the non-authoritative planning contract for task #79A.
It assigns every heading subtree, current public anchor, identifier namespace,
and registry in the canonical monolith to exactly one reserved modular
document.

The nearest explicit heading ancestor owns a heading. The document title and
every level-two section require an explicit assignment; level-three or deeper
assignments are deliberate cross-module overrides.

The map does not activate modular publication, create authoritative module
sources, or move protocol text. `drafts/agent-surface.md` remains the sole
normative source while `publication_mode` is `transitional_monolith`.

Run:

```sh
make publication-ownership-check
```

## 79B complete candidate materialization

`materialization.json` binds every ownership run to the executable
`publication/candidates/modular-document-set/` candidate. The generator:

- partitions the canonical RFC at heading boundaries;
- coalesces consecutive headings with the same future document owner;
- commits 25 derived Markdown fragments under all seven module source
  closures;
- keeps every `drafts/modules/*` target absent and non-authoritative;
- uses the exactly locked Hyperprompt compiler to assemble the fragments;
- requires the aggregate to equal the canonical monolith byte-for-byte;
- records reproducible manifest and full source-map digests.

Hyperprompt treats the first child boundary differently from sibling
boundaries. The materializer therefore moves the first canonical blank line
into the first child and replaces later boundary blank lines with source-map
`generated_separator` entries. The generated aggregate still preserves every
canonical byte.

Refresh or verify the committed candidate:

```sh
make publication-materialization-generate
make publication-materialization-check
```

The complete publication gate runs the freshness check, rebuilds both assembly
candidates twice, and validates the ownership/materialization contract:

```sh
make publication-check
```

This remains a rehearsal. It does not create canonical module files, relocate
public anchors, rewrite cross-document references, or change
`publication_mode`.
