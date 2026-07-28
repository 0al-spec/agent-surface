## Proposal Flow

Proposal mode separates drafting from committing.

```text
Agent -> comment.propose
Runtime -> local policy check
App -> stores draft/proposal
Runtime/App -> optional dry_run and reservation
User/App -> approves exact input and expected effects
App -> comment.create commit
Runtime/App -> receipt
```

This is the RECOMMENDED default for early integrations on a `standard`
surface. The proposal and commit are separate actions and authorities even
when they share one `operation_id`.

For a proposal-only surface, the ASP flow terminates with the non-authoritative
artifact:

```text
Agent -> typed propose action
Runtime/App -> policy, validation, optional draft persistence
App -> proposal result and optional receipt
User -> reviews or applies through independently authenticated app-native UI
```

If the publisher later wants the agent to commit through ASP, it MUST publish a
new `standard` surface version and hash containing a separate commit action.
The runtime MUST perform a new capability match and Consent Preview, and the
authorization server MUST obtain fresh consent and issue a new independent
Grant that explicitly contains the commit action. Renewal, token exchange,
subdelegation, an old proposal approval, or reuse of the proposal's id,
operation id, receipt, or input hash MUST NOT widen the proposal-only Grant.
