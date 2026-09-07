# ADP-03: user-selected agent responsibility boundary

Status: owner direction recorded 2026-09-08; normative compatibility unresolved.
Audit baseline: ASP `73c78fc`, Privacy `0.1.0-draft.3`.
This is an adoption decision, not a change to the published RFC or a legal
allocation of liability.

## Owner decision

For this BYOA example, the user chooses and trusts the agent implementation,
including its memory, diagnostic storage and use of data legitimately disclosed
to it. Calcu should not audit or certify the internals of that chosen agent as
a prerequisite to demonstrating controlled application access.

The application remains responsible for its own boundary: authenticate the
principal, verify the exact Grant and session, authorize every resource access
and action, constrain output before disclosure, and keep credentials outside
agent context. User choice does not grant database, history, account or file
access; possession of user input does not create application authority.

This decision does not waive another principal's restrictions, app/enterprise
policy or an explicitly accepted handling obligation. It does not absolve an
agent implementation of promises it actually makes. No new deletion, no-training,
agent-security or provider-handling guarantee is made by Calcu.

## Work stopped and work retained

- Stop the retention collector/probe lane: no live run, isolated login, cache
  inventory or new Codex persistence investigation is planned. Existing offline
  fixtures and the source audit remain historical evidence, not active gates.
- Withdraw the proposed `transient` / `delete_on_grant_end: true` policy as the
  desired Calcu deployment contract. It was not deployed as a verified promise.
  No replacement wire value is invented and no existing mandatory field is
  silently omitted.
- Retain application-side authorization, pre-delivery exposure control,
  principal/disclosure design, Grant projection and safe cancellation/revocation.
  Ordinary buffer/UI lifecycle hygiene remains useful, but is not proof of agent
  deletion. ADP-02's independent cost decision remains required.
- Keep ADP-03 open for normative compatibility and the remaining application
  design gates. ADP-05/08/09 are not unblocked by user acceptance of agent risk.

## RFC compatibility audit

The current RFC is stricter than the newly chosen boundary. The earlier idea
that retention is merely an optional deployment promise is **not an accurate
description of the current base contract**.

| Current requirement | Consequence for the desired BYOA example |
| --- | --- |
| [Core: Actions](../../../drafts/modules/core.md#actions), line 3147: every action requires `data_exposure` | Proposal-only arithmetic is not exempt. |
| [Privacy: Data Exposure Contract](../../../drafts/modules/privacy.md#data-exposure-contract), lines 93–102: retention is only `transient` or `bounded`; bounded requires a positive lifetime and plaintext deletion | There is no existing unspecified or user-managed retention mode. Setting an arbitrarily large lifetime is not a truthful solution. |
| Same section, lines 119–165: proposal outputs, echoes and derived results remain covered | Returning only caller-supplied operands does not bypass the contract. Changing classification alone does not remove retention. |
| [Privacy Considerations](../../../drafts/modules/privacy.md#privacy-considerations), lines 805–818: runtime-controlled prompts, context, caches and logs are covered; runtime must not select an incapable agent/path | The user choosing an agent does not currently waive runtime enforcement. |
| [Runtime Mediator Profile](../../../drafts/modules/conformance.md#runtime-mediator-profile), lines 1221–1223: effective projection and enforceable retention are required | A passing Mediated Proposal bundle's limited vectors do not establish complete role conformance or override these obligations. |
| [Remote Processing Privacy Profile](../../../drafts/modules/privacy.md#remote-processing-privacy-profile) and [Agent Training Use Policy Profile](../../../drafts/modules/privacy.md#agent-training-use-policy-profile) are additional controls | Not selecting them does not switch off the base retention requirements. Local retention is distinct from provider deletion and model unlearning. |

Line numbers describe the audited baseline; section links target authoritative
modules. No normative text, schemas, vectors, registry or maturity state is
changed here. The existing demo is an adoption experiment with known gaps,
not full ASP conformance or production certification.

## Next bounded normative proposal

Prepare a separate reviewable proposal that distinguishes application access
and disclosure authorization from optional post-disclosure handling guarantees.
Do not implement it through a Calcu-only exception or a prose disclaimer.

Acceptance questions for that proposal:

1. Can a publisher explicitly permit user-managed handling without promising
   deletion, while a stricter application can refuse that path?
2. How are the selected semantics bound to manifest, Grant and consent so that
   a caller cannot downgrade an existing contract or reuse its old hash?
3. Which responsibilities remain unconditional: authorized resource access,
   exact admission, pre-delivery redaction, credential non-release and honest
   disclosure? Revocation blocks future access; it must not imply recall of
   copies already delivered under a non-deletion contract.
4. Which schema, issuer/runtime compatibility, attenuation, conformance and
   positive/negative vectors must change together? Unsupported semantics must
   fail closed, never become an implicit opt-out.

Only after that decision can the Calcu contract and SDK extraction plan be
updated. The owner direction authorizes documenting this gap, not silently
weakening the current standard or claiming a new conformance profile.
