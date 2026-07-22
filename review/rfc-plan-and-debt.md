# Agent Surface RFC Plan and Debt

- Status: active planning snapshot
- Snapshot date: 2026-07-22
- Snapshot base: `7fdc9f73b50a0aa493eb448504bfddcd455765f7`
- Canonical machine-readable source: [`review-data.json`](review-data.json)

## Purpose and authority

This document records the current human-readable execution plan and the
remaining specification and delivery debt for Agent Surface Protocol (ASP).
It is a planning view, not a second backlog and not a normative protocol
artifact.

The following precedence rules apply:

1. `drafts/agent-surface.md` is the canonical normative protocol text.
2. `review/review-data.json` is the canonical source for card coverage,
   priority, profile, dependencies, target release, maturity, and evidence.
3. This document explains the intended sequencing and groups the canonical
   cards into reviewable work slices.
4. If this document conflicts with the RFC or review data, the RFC and review
   data win and this snapshot MUST be updated.

## Current snapshot

### Coverage

| Coverage | Cards | Meaning |
| --- | ---: | --- |
| `present` | 65 | The proposal is represented in normative prose. |
| `partial` | 4 | A precursor exists, but the interoperable contract is incomplete. |
| `missing` | 8 | The proposed contract or mapping is not specified. |
| **Total** | **77** | |

The active coverage debt is therefore **12 cards**: 2 P1, 4 P2, and 6 P3.

### Delivery maturity

| Maturity | Cards |
| --- | ---: |
| `proposal` | 13 |
| `specified` | 52 |
| `machine_validated` | 12 |
| `implementation_tested` | 0 |
| `interop_tested` | 0 |
| `stable` | 0 |

No card currently has a `target_release`. Coverage completion must not be
mistaken for implementation or interoperability maturity.

## Normative RFC debt

These cards change the core normative model or its conformance and publication
architecture.

| Order | Card | Priority | Coverage | Required outcome |
| ---: | --- | --- | --- | --- |
| 1 | #64 Purpose- and Task-Bound Agent Grants | P2 | `partial` | Add optional issuer-owned purpose/task binding, attenuation, expiry, session and action enforcement, and fresh consent when authority is widened. |
| 2 | #66 Modular RFC Publication Architecture | P2 | `partial` | Define document ownership, normative references, version pinning, registries, compatibility, and independent release lifecycles for Core and extension documents. |

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

## Binding and mapping specification debt

These cards should normally produce separate, version-pinned binding or mapping
documents rather than expand ASP Core indefinitely.

| Card | Priority | Coverage | Dependencies | Required boundary |
| --- | --- | --- | --- | --- |
| #69 ASP-over-MCP Binding | P1 | `missing` | #1, #4, #5, #13, #14, #15, #19, #30, #36, #40 | Pin MCP revision `2025-11-25`; map discovery, calls, results, and receipts; test downgrade and version confusion; preserve ASP Grant and app-side verification. |
| #70 ASP-over-WebMCP Binding | P2 | `missing` | #6, #13, #14, #15, #16, #19, #36, #46, #63, #69 | Keep the binding experimental and source-revision-pinned; define origin and document lifecycle, projection, execution-mode mapping, and app-side enforcement. |
| #67 WoT Thing Description Mapping | P3 | `missing` | #13, #14, #16, #17, #60 | Map ASP affordances to TD 1.1 without inferring authority or automatically converting Resource and Property semantics. |
| #68 Arazzo Workflow Mapping | P3 | `missing` | #17, #19, #22, #23, #24, #60 | Require explicit ASP metadata for import; do not infer modes, Grants, approvals, effects, or receipts from a generic workflow. |
| #71 Apple App Intents Mapping | P3 | `missing` | #16, #19, #20, #22, #46 | Treat platform authentication and confirmation as local mechanisms, not portable ASP authority or evidence. |
| #72 Android AppFunctions Mapping | P3 | `missing` | #16, #19, #20, #22, #46 | Keep the mapping experimental while AppFunctions remains preview-only; OS permissions and registry visibility are not ASP authority. |
| #73 A2A Agent Card and Task Mapping | P3 | `missing` | #2, #5, #41, #44, #76 | Treat Agent Cards as claims until trust, freshness, status, and key binding are verified; use A2A task IDs only for correlation. |

Mappings compose adjacent standards with ASP. They MUST NOT promote external
discovery, workflow, authentication, confirmation, or metadata objects into an
ASP Grant, approval, effect claim, or receipt.

## Delivery and tooling debt

| Card | Priority | Coverage | Delivery outcome |
| --- | --- | --- | --- |
| #74 Independent Reference Vertical Slice | P1 | `present` | Run one exact #65 bundle across distinct application and runtime deployments, agents, positive and negative scenarios, and machine-readable conformance reports. This is the first independent delivery-maturity milestone. |
| #75 ASP Typed SDK and Core Code Generation | P2 | `partial` | Build one validated canonical authoring model with deterministic manifest, schema, validator, and diagnostic generation. Keep external adapters outside the core SDK. |
| #77 External Mapping Adapter Generators | P3 | `missing` | Generate adapters only for completed mapping profiles; pin upstream versions, report semantic loss, perform no network I/O, and never synthesize authority. |

### Broader maturity debt

The current 52 `specified` cards still need card-appropriate executable schemas,
registries, validators, and positive and negative vectors before they can move
to `machine_validated`. The 12 `machine_validated` cards need evidence from
real implementations before they can move to `implementation_tested`.

The project still needs:

- authoritative evidence resolvers for `implementation_tested`,
  `interop_tested`, and `stable`;
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

#69 can begin independently of #63, but #70 requires both contracts.

### Lane B: identity evidence and A2A

```text
#76 Pluggable Agent Identity Evidence (specified)
  -> #73 A2A Agent Card and Task Mapping
```

### Lane C: adoption proof

```text
#65 Adoption-Oriented Conformance Bundles (machine-validated)
  -> #74 Independent Reference Vertical Slice
```

### Lane D: delegation hardening

```text
#64 Purpose- and Task-Bound Agent Grants
```

### Lane E: publication and authoring tooling

```text
#66 Modular RFC Publication Architecture
  -> #75 ASP Typed SDK and Core Code Generation
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

The next selected P1 slice is **#69 ASP-over-MCP Binding**. #74 is now
structurally unblocked by the machine-validated #65 bundle registry. Lower-priority mappings
should advance only when their upstream specification is sufficiently stable
and there is concrete adopter demand.

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
