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
