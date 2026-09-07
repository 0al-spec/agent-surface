# Proposal: explicit user-managed retention

Status: **non-authoritative design candidate**, 2026-09-08.
Primary RFC card: #36 Data Exposure Contract; related #37/#38/#46/#50.
No new card number, protocol version, conformance claim or wire support is
created by this document. Current implementations must reject the candidate
mode until the coordinated normative and executable change is delivered.

## Objective

Make the minimal BYOA promise precise: an application controls what a chosen
agent can access and execute, without necessarily promising to control that
agent's memory after authorized disclosure. A publisher may still require a
stricter handling contract; user preference cannot override it.

This follows the [owner decision](../../reference/adoption/calcu/byoa-responsibility-decision.md).
The retention experiment is stopped. This proposal is not an instruction to
inspect agents, run collectors or modify Calcu/SDK yet.

## Selected design

Extend the existing source-level `retention` tagged union with one explicit mode:

```json
{"mode":"user_managed"}
```

Do not make `retention` optional, infer the mode from BYOA, introduce an unlimited
numeric lifetime, or create a Calcu-only exception. `user_managed` is a proposed
wire spelling, not a value accepted by the current RFC.

Keep the current two shapes and semantics unchanged:

```json
{"mode":"transient","delete_on_grant_end":true}
{"mode":"bounded","max_seconds":7200,"delete_on_grant_end":true}
```

Existing permitted boolean choices remain permitted for those two modes.
The new branch allows only `mode`; `max_seconds`, `delete_on_grant_end`, unknown
members and implicit/null variants are invalid. In particular, a deletion flag
must not suggest a guarantee that this branch does not make.

## Candidate normative rules

These requirements are proposed replacements/additions, not yet authoritative.

1. **Meaning and ownership.** A publisher selecting `user_managed` for a source
   makes no ASP duration or grant-end deletion commitment for runtime-controlled
   copies of that application-originated source: prompts, context, tool arguments,
   caches, diagnostics and agent-visible logs. It does not redefine the ownership
   boundary, application storage of agent-supplied input or external/provider
   storage. No provider/model-memory property is established. The user chooses that
   implementation and accepts its handling risk. This is neither an affirmative
   training permission nor a warranty of the agent's security or legal behavior.
2. **Publisher choice, not caller override.** The mode MUST be explicitly pinned
   in the source's manifest declaration. The issuer MUST copy it into the exact
   source-closure projection; the runtime MUST recompute that projection before
   consent and use. A caller MUST NOT choose it through action input, prose,
   a feature flag or a modified Grant projection. Existing classification,
   source ordering, empty-source and control-event closure rules remain intact.
3. **Consent.** The exact source-level mode MUST appear in the derived consent
   projection. Presentation MUST distinguish sources with no protocol deletion
   promise from sources with transient/bounded obligations. The notice MUST say
   revocation stops future authorized access, not recall of already delivered
   copies. A mixed-source Grant MUST NOT be presented as entirely user-managed.
   This uses the existing consent mechanism; it adds no consent token or receipt.
4. **Mandatory boundary.** Classification, authorization to every application
   resource, exact action/session admission, pre-delivery redaction, immutable
   binding and credential non-release MUST remain enforced for every mode.
   `user_managed` MUST NOT authorize database reads, wider output, credential
   release, onward delegation or bypass of any selected policy/profile.
5. **Runtime capability.** For `user_managed` only, runtime suitability MUST NOT
   depend on proving agent-local deletion or absence of persistence. It still
   depends on understanding the mode, verifying the complete exposure contract,
   performing the disclosure/consent checks and satisfying every other effective
   constraint. A required local/enterprise deletion policy remains enforceable
   or causes refusal; it is not waived by the source's permissive declaration.
6. **No downgrade.** Exposure projection remains structurally identical to the
   pinned source. No retention-mode change is a Grant attenuation operation.
   A publisher changing a source from transient/bounded to user-managed MUST
   publish a new surface version/hash and obtain fresh consent and issuance;
   an old Grant MUST NOT adopt the replacement. Local stricter overlays MAY
   restrict handling without rewriting the source projection. They MUST NOT
   claim deletion unless enforceable for the actual selected path.
7. **Mixed data and other profiles.** A user-managed source MUST NOT be used to
   launder data received under a stricter source contract. Copies and outputs
   derived from disclosed sources, including summaries, encodings, cached values,
   previews and error representations, preserve the conjunction of their known
   source obligations: no durable persistence where any contributing source is
   transient, and every applicable receipt-based deadline/revocation condition.
   Derivation MUST NOT restart a bounded source's clock. User-managed contributes
   no deadline and removes none. There is no declassification exception in this
   slice. This governs known provenance, not semantic inference about arbitrary
   user input. If copies cannot be separated or obligations jointly satisfied,
   the implementation MUST refuse the combination. Remote
   Processing Privacy's recipient/path checks and Agent Training Use's explicit
   class permissions remain independent. Omission of training policy remains
   unspecified, not permission inferred from this mode. Controls required by
   either selected profile MUST NOT be suppressed to obtain compatibility.
   For a source with this mode alone, a remote recipient has no source-retention
   deadline to demonstrate; any stricter effective policy still requires its
   capability check. Path, recipient and training-policy checks remain mandatory.
8. **Revocation and safety state.** Grant/session revocation still fences future
   admissions and deliveries. Mandatory durable safety-state, replay/dedup and
   independent audit-minimization rules remain unchanged. User-managed handling
   grants no new right to persist application credentials or verifier artifacts.
9. **Compatibility.** An implementation not supporting the new branch MUST
   fail closed before disclosure. Capability matching consumes runtime-owned,
   revision-bound knowledge of the selected adapter/runtime implementation's
   supported exposure grammar, never a model claim. Its local decision is
   supported, known unsupported, or unknown/stale; absence is not support.
   Bind it through the existing adapter-inventory/policy revisions and freshness
   checks, with no new Grant field or public discovery registry. Known unsupported
   grammar uses `schema_unsupported`; unknown/stale support uses blocking
   `input_unknown`. A supported grammar with an unenforceable stricter deletion
   obligation uses `retention_unsupported`; direct policy denial uses
   `policy_denied`. Malformed shapes use existing layer-specific schema/integrity
   errors. Do not add a silent
   fallback to transient, bounded, omission or permissive handling.

## Acceptance matrix for the implementation

| Case | Required result |
| --- | --- |
| Explicit new mode, matching projection, informed user, compatible app/runtime policies | May admit, subject to all other ordinary checks; no deletion promise |
| New mode with either deletion field or any extra member | Reject shape |
| Missing/null/unknown mode | Reject; never infer user-managed |
| Old runtime does not support the mode | Refuse before data delivery |
| Missing/stale authoritative mode-support knowledge | Blocking `input_unknown`, never compatible by default |
| User requests new mode against a transient/bounded manifest | Reject mismatch; no downgrade |
| Reuse old Grant after publisher changes mode | No silent adoption; new manifest binding/consent/issuance required |
| Subdelegated child tries to rewrite retention | Reject projection mismatch; narrower authority does not rewrite source policy |
| New mode plus stricter enterprise deletion requirement that the path cannot enforce | Refuse |
| Derived/encoded/preview output joins user-managed and bounded data | Preserve original bounded deadline and revocation rule; no clock reset or laundering |
| Combined transient and bounded data | No durable persistence and all applicable deadlines/conditions; refuse if unsatisfiable |
| New mode with selected remote/training restrictions | Enforce those restrictions independently |
| Revoked Grant with previously disclosed user-managed output | Deny new access; do not claim recall of old copies |
| Correct mode but unauthorized resource/action or credential release | Reject before protected read/engine execution/disclosure |
| Existing transient and bounded fixtures | Preserve existing acceptance and rejection behavior |

These are required future vectors, not tests reported as passed by this proposal.

## Implementation plan and atomic delivery

1. **Normative contract:** update Privacy Data Exposure, projection enforcement,
   Remote/Training interactions and Privacy Considerations; align Core's
   definition and Conformance Runtime Mediator wording. Review Authorization's
   consent/capability wording for unconditional deletion assumptions. Preserve
   all stricter existing contracts and fixed source-closure rules.
2. **Executable surfaces:** update `conformance/v1/impact-simulation.schema.json`,
   the exposure validation in `conformance/check.py` and `mocks/behavior.py`,
   plus schema cases and behavioral positive/negative vectors for the matrix.
   Inventory advertised feature coverage honestly; an Impact Simulation schema
   test alone does not prove runtime disclosure enforcement. Do not create a
   duplicate general-purpose privacy framework or imply a full manifest schema
   exists where it does not.
3. **Publish one consistent snapshot:** bump changed module and transitive exact
   dependency versions, affected registry/suite versions and document-set pins;
   regenerate with `make publication-modular-build`, update card #36 evidence
   and the dashboard, and run publication/review/conformance/mock checks plus
   history/freshness validation. Do not edit the generated aggregate manually.
   Normative and executable support must land together, not as contradictory
   intermediate published commits. No immutable version is reused.
4. **Return to adoption:** after review/merge, reassess ADP-03 using the explicit
   new contract, then obtain ADP-02's independent continue decision. Only then
   implement Calcu and extract stable SDK behavior. No retention probe restarts.

Exit from this proposal is a reviewed mode/compatibility decision and the above
closed implementation scope, not a declaration that ADP-03 or RFC conformance
is complete. Full-profile certification, legal guarantees, agent attestation,
collector tooling and new mobile/browser bindings are out of scope.
