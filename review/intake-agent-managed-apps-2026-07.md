# Agent-managed applications research intake — 2026-07

## TL;DR

The research note was treated as an input to review, not as a ready-made plan.
Against the current RFC and the existing 62-card backlog, the result is:

- **15 new cards accepted:** #63–#77;
- **5 proposals absorbed by existing work:** no duplicate card;
- **2 proposals deliberately narrowed:** linear conformance levels became
  composable bundles, and external standards became mappings rather than ASP
  authority;
- **2 proposals declined as standalone work:** a generic approval-UI binding
  and wholesale replacement of ASP primitives.

The highest-value new slices are #63, #65, #69, and #76. #74 is the first
delivery-maturity milestone. Platform-specific mappings remain lower-priority
until the core bindings and an independent vertical slice exist.

## Review method

Each proposal was tested against four questions:

1. Is the capability already present in the RFC or represented by an existing
   backlog card?
2. Does the proposal strengthen ASP's unique authority boundary, or merely add
   another vocabulary for an already-defined concept?
3. Is the referenced external specification stable enough for a normative
   dependency, or should the result be informative or experimental?
4. Can the work be expressed with a bounded acceptance boundary, dependencies,
   negative cases, and conformance evidence?

`partial` means that the RFC contains a useful precursor but not the proposed
interoperable contract. `missing` means that only a relationship or adjacent
mechanism exists today.

## Accepted cards

| ID | Proposal | Priority | Coverage | Critical boundary |
| --- | --- | --- | --- | --- |
| #63 | Authorization-Dependent Surface Discovery | P1 | partial | Preserve one canonical base snapshot; every principal-specific projection has its own key, is hash-bound, cache-partitioned, and can only attenuate the base inventory. |
| #64 | Purpose- and Task-Bound Agent Grants | P2 | partial | A digest binds bytes, not semantics; use issuer-owned task identity plus session/action/app-side enforcement, attenuation, expiry, and fresh consent on widening. |
| #65 | Adoption-Oriented Conformance Bundles | P1 | partial | Use named bundles of whole role profiles and selected optionals, not a security ladder; no bundle may exclude unconditional or applicable requirements. |
| #66 | Modular RFC Publication Architecture | P2 | partial | Splitting files is insufficient; define normative-reference ownership, registries, version pinning, and independent lifecycle rules. |
| #67 | WoT Thing Description Mapping | P3 | missing | Base the stable mapping on TD 1.1, prohibit automatic Resource↔Property conversion and remote-context/form fetching; WoT security metadata is not ASP authority. |
| #68 | Arazzo Workflow Mapping | P3 | missing | Generic workflows cannot infer ASP contracts; import requires explicit ASP metadata, supplied documents only, and no expression/action execution. |
| #69 | ASP-over-MCP Binding | P1 | missing | Pin MCP 2025-11-25 and test downgrade/version confusion; MCP authentication and annotations do not replace ASP app-side verification. |
| #70 | ASP-over-WebMCP Binding | P2 | missing | Keep it source-revision-pinned and experimental; define origin, document lifecycle, execution-mode mapping, and app-side enforcement. |
| #71 | Apple App Intents Mapping | P3 | missing | Treat platform authentication and confirmation as local mechanisms, not portable proof of ASP authority or effects. |
| #72 | Android AppFunctions Mapping | P3 | missing | Keep it experimental while AppFunctions is preview-only; OS permission and registry visibility are not ASP authority. |
| #73 | A2A Agent Card and Task Mapping | P3 | missing | Signed Agent Cards remain claims until trust/freshness/status verification; A2A task/context IDs are correlation only, never ASP identifiers or authority. |
| #74 | Independent Reference Vertical Slice | P1 | present | Normative independence rules exist; delivery maturity still needs distinct artifacts/deployments, an exact #65 bundle, agents, and machine-readable reports. |
| #75 | ASP Typed SDK and Core Code Generation | P2 | partial | Build one validated canonical model with deterministic manifest/schema/validator output; keep external adapters outside the core SDK. |
| #76 | Pluggable Agent Identity Evidence | P1 | partial | Replace Passport-specific Grant fields with a versioned envelope for issuer/subject, digest, key binding, freshness, status, verification, revocation, and migration. |
| #77 | External Mapping Adapter Generators | P3 | missing | Generate an adapter only after its exact mapping profile exists; pin upstream versions, report loss, perform no network I/O, and never synthesize authority. |

## Proposals absorbed by existing work

| Research proposal | Disposition | Existing coverage |
| --- | --- | --- |
| Make the risk model multidimensional | No new card | #20 Effect Model, #22 Preconditions and Effects Schemas, and #47 Impact Simulation already separate mutation, audience, boundary, confidentiality, reversibility, value, volume, and current-state simulation. |
| Add an `operation_family` to fixed execution stages | No new card | #19 already defines immutable modes, `execution.operation_id`, reciprocal companion references, closure, and independent authority per action. Renaming it would add churn, not semantics. |
| Reuse OpenAPI rather than inventing another HTTP schema | No new card | #17 already defines a closed publishing-time OpenAPI/AsyncAPI import profile and forbids imported metadata from becoming authority. |
| Build negative executable tests and reference mock participants | No new card | #58–#60 already provide Mock App/Runtime, Replay Tool, the conformance matrix, positive/negative vectors, and machine-readable reports. #74 adds the still-missing independent implementation evidence. |
| Define a minimal interoperable adoption path | Folded into #65 and #66 | The existing six role profiles remain the normative responsibility boundaries; bundles and modular publication provide smaller adoption units without inventing a second conformance model. |

## Proposals narrowed or declined

### External standards are mappings, not delegated authority

WoT, Arazzo, MCP, WebMCP, App Intents, AppFunctions, and A2A each solve useful
adjacent problems. None of their discovery, workflow, caller-authentication, or
platform-policy objects can be promoted automatically into an ASP Grant,
approval, effect claim, or receipt. Cards #67–#73 therefore require explicit
loss reporting and preserve ASP app-side enforcement; #77 automates only those
approved mappings.

Wholesale replacement of ASP resources/actions/events, Grants, or receipts with
one of those standards is declined. That would erase the user-to-agent
delegation boundary that differentiates ASP.

### No generic A2UI approval binding yet

A2UI could render one approval experience, but ASP deliberately does not
standardize every approval UI. #29 Human Elicitation Events, #46 Consent Preview,
and #48 Risk Explanation UI Hints already define the transport-independent
semantic content. A separate UI binding should be reconsidered only after a
concrete interoperability failure demonstrates that these contracts are
insufficient.

### Research-only governance protocols are prior art, not dependencies

OpenPort, AP2, SUDP, and individual Internet-Drafts are useful design evidence,
but they are either domain-specific, research proposals, or unstable drafts.
They should inform threat analysis and terminology. A new mapping card requires
a stable artifact plus a concrete ASP integration target; the research note did
not establish both.

## Standards maturity snapshot

Checked against primary sources on 2026-07-21:

| Source | Maturity used for this intake | Consequence |
| --- | --- | --- |
| [Model Context Protocol, revision 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic) | Released protocol revision | #69 can target an exact revision and executable vectors. |
| [WebMCP, Draft Community Group Report, 20 July 2026](https://github.com/webmachinelearning/webmcp/commit/1aece7c5258dbd17d4e50a7753132790c8d7925b) | Community Group draft snapshot `1aece7c` | #70 remains experimental and pins an exact source revision rather than the moving editor's draft. |
| [W3C WoT Thing Description 1.1](https://www.w3.org/TR/2023/REC-wot-thing-description11-20231205/) | W3C Recommendation | #67 uses TD 1.1 as its stable mapping base. |
| [W3C WoT Thing Description 2.0](https://www.w3.org/TR/wot-thing-description-2.0/) | First Public Working Draft | TD 2.0 is informative research only for now. |
| [Arazzo Specification 1.1.0](https://spec.openapis.org/arazzo/v1.1.0.html) | Published OpenAPI Initiative specification | #68 pins 1.1.0 and requires explicit ASP metadata for any import. |
| [Apple App Intents](https://developer.apple.com/documentation/appintents/appintent) | Production, moving platform API | #71 is informative and must pin the mapped OS/SDK generation. |
| [Android AppFunctions](https://developer.android.com/ai/appfunctions) | Experimental preview | #72 is exploratory and must not be a Core dependency. |
| [A2A Protocol 1.0.0](https://a2a-protocol.org/v1.0.0/specification/) | Released protocol with Agent Card and Task models | #73 maps claims and correlation state, not authority or ASP identifiers. |

External specification text should be referenced or mapped, not copied into ASP.
Any future implementation must preserve upstream license and attribution terms.

## Recommended execution order

1. **#63 Authorization-Dependent Surface Discovery** — closes a direct privacy
   and capability-enumeration gap in the current discovery model.
2. **#76 Pluggable Agent Identity Evidence** — removes the remaining
   Passport-format hard dependency before A2A or other evidence mappings.
3. **#65 Adoption-Oriented Conformance Bundles** — defines a realistic minimal
   implementation target without weakening role conformance.
4. **#69 ASP-over-MCP Binding** — gives the most important adjacent ecosystem a
   concrete, testable composition boundary.
5. **#74 Independent Reference Vertical Slice** — executes after #65 and proves
   that the selected bundle interoperates across distinct implementations.
6. **#64 Purpose-/Task-Bound Grants** and **#66/#75 publication/tooling** — harden
   long-lived delegation and developer ergonomics.
7. **#67/#68/#70–#73 mappings**, then **#77 adapter generators** — progress
   individually as upstream maturity and real adopter demand justify them.

The dashboard dependency graph is canonical for readiness; this document
records the intake decisions and the reasoning behind them.
