# Agent Surface RFC Plan and Debt

- Status: active planning snapshot
- Snapshot date: 2026-07-29
- Snapshot base: task `#79D` atomic activation state
- Canonical machine-readable source: [`review-data.json`](review-data.json)

## Purpose and authority

This document records the current human-readable execution plan and the
remaining specification and delivery debt for Agent Surface Protocol (ASP).
It is a planning view, not a second backlog and not a normative protocol
artifact.

The following authority rules apply:

1. The active sources selected by `publication/document-set.json` are the
   canonical normative protocol text. In the current modular mode those are the
   seven sources under `drafts/modules/`; `drafts/agent-surface.md` is a
   generated aggregate reading view.
2. `publication/document-set.json` is normative only for publication
   selection, exact source digests, dependencies, ownership, and transition
   state; it cannot override protocol semantics. A conflict makes the
   publication invalid rather than giving either artifact silent precedence.
3. `review/review-data.json` is the canonical source for card coverage,
   priority, profile, dependencies, target release, maturity, and evidence.
4. This document explains the intended sequencing and groups the canonical
   cards into reviewable work slices.
5. If this document conflicts with the publication contract, active RFC
   sources, or review data, this snapshot MUST be updated.

## Current snapshot

### Coverage

| Coverage | Cards | Meaning |
| --- | ---: | --- |
| `present` | 71 | The proposal is represented in normative prose. |
| `partial` | 1 | A precursor exists, but the interoperable contract is incomplete. |
| `missing` | 7 | The proposed contract or mapping is not specified. |
| **Total** | **79** | |

The active coverage debt is therefore **8 cards**: 2 P2 and 6 P3.

### Delivery maturity

| Maturity | Cards |
| --- | ---: |
| `proposal` | 9 |
| `specified` | 52 |
| `machine_validated` | 17 |
| `implementation_tested` | 1 |
| `interop_tested` | 0 |
| `stable` | 0 |

No card currently has a `target_release`. Coverage completion must not be
mistaken for implementation or interoperability maturity.

## Normative RFC architecture state

The publication-architecture card is now covered and machine-validated. No
additional uncovered architecture card remains in this lane.

| Card | Priority | Coverage | Maturity | Delivered outcome |
| --- | --- | --- | --- | --- |
| #66 Modular RFC Publication Architecture | P2 | `present` | `machine_validated` | Immutable exact versions and source digests, required-role DAG, registry and explicit-anchor ownership, transitive exact-pin republishing, Hyperprompt provenance boundaries, and fail-closed relocation/activation rules are defined and active. |

### Normative boundaries

- An authorized Surface projection may only attenuate its canonical base
  inventory; it must not silently add authority.
- Identity evidence remains evidence, not application authority. Agent Passport
  becomes one evidence profile rather than a mandatory wire format.
- A conformance bundle cannot omit unconditional or applicable requirements
  from the role profiles it selects.
- A task digest binds bytes, not human meaning. The issuer owns task identity
  and widening requires a new authorization decision.
- Splitting the RFC into files does not create independent specifications until
  ownership, references, registries, versioning, and compatibility are defined.

### Publication implementation state

The atomic activation is complete:

| Card | Coverage | Maturity | Required delivery |
| --- | --- | --- | --- |
| #78 Reproducible RFC Assembly Pipeline | `present` | `proposal` | Historical rehearsal fixed Hyperprompt v0.2.0, full source maps, clean staging, and Linux/macOS reproducibility evidence. |
| #79 Atomic Modular RFC Activation | `present` | `machine_validated` | Seven canonical modules, exact dependencies and references, ownership, nine relocation records, generated aggregate and provenance sidecars are active and fail-closed. |

Historical candidates remain under `publication/candidates/` and
`publication/migration/` without normative authority. The active catalog has
no reservations.

## Binding and mapping specification debt

These cards should normally produce separate, version-pinned binding or mapping
documents rather than expand ASP Core indefinitely.

| Card | Priority | Coverage | Dependencies | Required boundary |
| --- | --- | --- | --- | --- |
| #69 ASP-over-MCP Binding | P1 | `present` | #1, #4, #5, #13, #14, #15, #19, #30, #36, #40, #60, #63 | MCP revision `2025-11-25`, manifest-pinned discovery, Grant location issuance, dedicated session lifecycle, schema-bound calls, credential custody, cancellation/recovery, app-side verification, receipts, and executable negative vectors are machine-validated. |
| #70 ASP-over-WebMCP Binding | P2 | `present` / `specified` | #6, #13, #14, #15, #16, #19, #36, #46, #63, #69 | Experimental profile is pinned to immutable WebMCP revision `1aece7c…`; it defines minimized document-scoped projection, a Runtime Bridge bound to exact `grant_hash`, browser-only single-use invocation proof, lifecycle invalidation, static modes, and app-side enforcement. Executable browser vectors remain follow-up work. |
| #67 WoT Thing Description Mapping | P3 | `missing` | #13, #14, #16, #17, #60 | Map ASP affordances to TD 1.1 without inferring authority or automatically converting Resource and Property semantics. |
| #68 Arazzo Workflow Mapping | P3 | `missing` | #17, #19, #22, #23, #24, #60 | Require explicit ASP metadata for import; do not infer modes, Grants, approvals, effects, or receipts from a generic workflow. |
| #71 Apple App Intents Mapping | P3 | `missing` | #16, #19, #20, #22, #46 | Treat platform authentication and confirmation as local mechanisms, not portable ASP authority or evidence. |
| #72 Android AppFunctions Mapping | P3 | `missing` | #16, #19, #20, #22, #46 | Keep the mapping experimental while AppFunctions remains preview-only; OS permissions and registry visibility are not ASP authority. |
| #73 A2A Agent Card and Task Mapping | P3 | `missing` | #2, #5, #41, #44, #76 | Treat Agent Cards as claims until trust, freshness, status, and key binding are verified; use A2A task IDs only for correlation. |

Mappings compose adjacent standards with ASP. They MUST NOT promote external
discovery, workflow, authentication, confirmation, or metadata objects into an
ASP Grant, approval, effect claim, or receipt.

## Delivery and tooling debt

| Card | Priority | Coverage | Maturity | Delivery outcome |
| --- | --- | --- | --- | --- |
| #74 Independent Reference Vertical Slice | P1 | `present` | `implementation_tested` | Exact Application-Audited Effects reports and two executable local/remote lanes now pass through a card-specific resolver. Independent interoperability remains deliberately unclaimed. |
| #75 ASP Typed SDK and Core Code Generation | P2 | `partial` | `proposal` | Build one validated canonical authoring model with deterministic manifest, schema, validator, and diagnostic generation. Keep external adapters outside the core SDK. |
| #78 Reproducible RFC Assembly Pipeline | P2 | `present` | `proposal` | Preserve the historical rehearsal and exact toolchain lock as migration provenance. |
| #79 Atomic Modular RFC Activation | P2 | `present` | `machine_validated` | Maintain the active seven-document closure and reproducible aggregate gate. |
| #77 External Mapping Adapter Generators | P3 | `missing` | `proposal` | Generate adapters only for completed mapping profiles; pin upstream versions, report semantic loss, perform no network I/O, and never synthesize authority. |

### Broader maturity debt

The current 52 `specified` cards still need card-appropriate executable schemas,
registries, validators, and positive and negative vectors before they can move
to `machine_validated`. The 16 `machine_validated` cards need evidence from
real implementations before they can move to `implementation_tested`.

The project still needs:

- reusable evidence resolvers for additional `implementation_tested` cards and
  authoritative resolvers for `interop_tested` and `stable`;
- at least two independent implementations for interoperability claims;
- release assignment and exit criteria for planned cards;
- versioned conformance reports tied to exact artifacts and configurations;
- compatibility and migration tests across released protocol versions;
- a documented stability and deprecation policy.

## Dependency-ordered execution plan

Work proceeds by dependency-closed protocol slice, not by an arbitrary number
of cards.

### Lane A: discovery and browser projection

```text
#63 Authorization-Dependent Surface Discovery (specified) --\
                                                   +--> #70 ASP-over-WebMCP Binding
#69 ASP-over-MCP Binding --------------------------/
```

#69 is machine-validated and #70 is now specified on top of the completed #63
and #69 contracts. The remaining WebMCP debt is an executable browser-adapter
schema and positive/negative lifecycle vector set.

### Lane B: identity evidence and A2A

```text
#76 Pluggable Agent Identity Evidence (specified)
  -> #73 A2A Agent Card and Task Mapping
```

### Lane C: adoption proof

```text
#65 Adoption-Oriented Conformance Bundles (machine-validated)
  -> #74 Independent Reference Vertical Slice (implementation-tested)
```

### Lane D: delegation hardening

```text
#64 Purpose- and Task-Bound Agent Grants (machine-validated)
```

### Lane E: publication and authoring tooling

```text
#66 Modular RFC Publication Architecture (machine-validated)
  +-> #78 Reproducible RFC Assembly Pipeline
  |     `-> #79 Atomic Modular RFC Activation
  `-> #75 ASP Typed SDK and Core Code Generation
```

### Lane F: external mappings and generation

```text
#67 WoT mapping -----------\
#68 Arazzo mapping ---------\
#69 MCP binding ------------+---> #77 External Mapping Adapter Generators
#70 WebMCP binding ---------/
#71 App Intents mapping ---/
#72 AppFunctions mapping --/
#73 A2A mapping ----------/
#75 Typed SDK ------------/
```

The intake's P1 delivery lane is complete through **#74 Independent Reference
Vertical Slice**. **#66 Modular RFC Publication Architecture** now has
normative prose plus a closed document-set schema, catalog, semantic validator,
negative tests, and CI gate. The next publication step is **#78 Reproducible
RFC Assembly Pipeline**, followed by **#79 Atomic Modular RFC Activation**.
**#70
ASP-over-WebMCP Binding** is specified but remains P2 while WebMCP is
experimental. Its executable browser-vector follow-up should advance before
claiming machine-validated maturity. Lower-priority mappings should advance only when their
upstream specification is sufficiently stable and there is concrete adopter
demand.

## Definition of done for a protocol slice

A slice is complete only when all applicable items below are satisfied:

1. Authority boundaries, invariants, state transitions, wire objects,
   revocation behavior, and negative cases are written before or with the RFC
   change.
2. Normative RFC text and all affected cross-section invariants are updated.
3. Related cards in `review-data.json` have accurate coverage, dependencies,
   maturity, and evidence. A card becomes `present` only when its normative
   contract is actually present.
4. Schemas, registries, examples, validators, and conformance vectors are
   updated when the slice changes machine-readable or wire behavior.
5. The generated dashboard is rebuilt and committed with its source data.
6. `make review-check` and all slice-specific checks pass.
7. The change is delivered as a focused pull request with review threads
   resolved and required CI checks successful.
8. Maturity is raised only when the required authoritative evidence resolver
   accepts the referenced evidence.

## Maintenance procedure

Update this snapshot whenever a merged change does any of the following:

- adds, removes, splits, or closes a backlog card;
- changes a dependency, priority, profile, or execution lane;
- assigns a target release;
- changes maturity or the evidence model;
- changes which protocol slice is selected next.

For every update:

1. edit `review-data.json` first;
2. regenerate and validate the dashboard;
3. recalculate the tables in this document from the canonical data;
4. update the snapshot date and base commit reference;
5. commit the planning document with the backlog change that made it stale.

## Explicit non-goals

The current plan does not include:

- replacing ASP resources, actions, events, Grants, approvals, or receipts
  wholesale with an adjacent standard;
- treating MCP, WoT, Arazzo, A2A, App Intents, AppFunctions, or operating-system
  permissions as delegated ASP authority;
- adding a generic approval-UI binding without a demonstrated interoperability
  gap in the existing Human Elicitation, Consent Preview, and Risk Explanation
  contracts;
- declaring suite fixtures or mock participants to be independent ASP
  implementations.
