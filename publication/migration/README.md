# Archived Modular Activation Rehearsal

This directory contains the non-authoritative planning contract for task #79A
and the completed 79B–79C rehearsal artifacts.
It assigns every heading subtree, current public anchor, identifier namespace,
and registry in the canonical monolith to exactly one reserved modular
document.

The nearest explicit heading ancestor owns a heading. The document title and
every level-two section require an explicit assignment; level-three or deeper
assignments are deliberate cross-module overrides.

The active publication has moved to `modular`. These files remain historical
migration evidence and are not selected as sources by
`publication/document-set.json`.

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

## 79C standalone documents and relocation plan

`standalone.json` promotes the seven fragment closures into seven independently
readable candidate documents under `publication/migration/documents/`.
Generation is still non-authoritative and keeps every reserved
`drafts/modules/*` target absent.

Each document receives:

- the exact reserved document ID and version;
- its planned canonical path;
- the exact pinned normative dependency list;
- its owned content in canonical order;
- heading repair for a subtree whose original parent belongs to another
  module.

The aggregate table of contents is replaced by a document-set navigation index
with 48 checked candidate-local links. These navigation slugs are explicitly
non-public and do not expand the protocol anchor namespace.

The relocation plan covers exactly the nine current public anchors. Every
record maps the old monolith document/version/anchor tuple to its future exact
module tuple and declares two transition-only compatibility aliases:

- the old aggregate path plus fragment;
- the old aggregate fragment alone.

The following commands apply only when reproducing the historical rehearsal
against its transitional input state:

```sh
make publication-standalone-generate
make publication-standalone-check
make publication-ownership-check
```

79D activated the corresponding canonical sources under `drafts/modules/`,
copied the relocation records into the normative catalog, and replaced these
migration checks in the default publication gate with the authoritative modular
build check.
