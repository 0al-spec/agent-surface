# SpecSpace draft: bounded executable ASP scenario

This is an isolated development experiment, not an SDK, new RFC feature,
production rollout or completed conformance/maturity claim. The existing
export baseline is retained; export is not the operation tested here.

## Choices fixed by the implementation

| Boundary | Choice |
| --- | --- |
| Transport | Direct ASP JSON envelopes over verified HTTPS on `127.0.0.1`, inside SpecSpace's existing ViewerHandler. No MCP/WebMCP binding. |
| Credentials | Compatibility Bearer, app-issued Model A, 300-second scenario Grant. Operator auth is separate from runtime credentials. |
| Identity | Generic Agent Identity Evidence with one local pinned Ed25519 issuer/subject registration. Runtime independently verifies it and challenges the agent key. This is not executable attestation. |
| Operation | Workspace-scoped read and create-only persisted `propose` using existing native raw-idea save, always `status: draft`. |
| Approval | App-local exact invocation approval, separate from Grant consent. Not Approval Receipt v1 and not normative `dry_run`. |
| Storage | New private synthetic SQLite directory; ASP and native save share `BEGIN IMMEDIATE`. No migration or external Platform backend. |

SpecSpace's `docs/ASP_DRAFT_ADOPTION.md` defines the opt-in configuration and the
concrete local identity format/verification/freshness/status choices. Normal
SpecSpace routes and production configuration remain unchanged when opt-in is
absent. In the experimental deployment all routes except the bounded ASP API
and the existing operator-only raw-idea API are disabled.

Application implementation: [SpecSpace PR #430](https://github.com/0al-spec/SpecSpace/pull/430),
commit `ef7564db255e712ad50e2429551dc449b595ddc2`. The ASP baseline remains
[PR #76](https://github.com/0al-spec/agent-surface/pull/76); this executable
follow-up is a separate review slice.

## Reproduce

Use the SpecSpace implementation revision pinned in
`.github/workflows/asp-draft-adoption.yml` in a trusted clean checkout. Do not
use or clean the original dirty product worktree. Install its `requirements.txt`
in a Python 3.12 virtual environment. OpenSSL **3.x** must be on `PATH`;
Apple's `/usr/bin/openssl` (LibreSSL) is insufficient. No browser, live app,
existing token, production data or private conversation is needed.

```sh
python -B reference/adoption/contextbuilder/https_scenario.py \
  --checkout /absolute/path/to/specspace-checkout \
  --expected-commit ef7564db255e712ad50e2429551dc449b595ddc2 \
  --specspace-python /absolute/path/to/specspace/.venv/bin/python \
  --mock-user
```

On a Homebrew macOS host, prefix the command with
`env PATH="/opt/homebrew/bin:/usr/bin:/bin"` when necessary. The executable path
must point to the virtual environment, not a resolved base Python interpreter.

The driver creates a disposable TLS certificate, issuer/subject keys, one
identity statement, operator credentials and synthetic state with private
permissions. It removes them after the run. The issuer private key is deleted
after signing; app and runtime use only its public key. No secrets or private
draft contents appear in the final machine-readable summary.

It starts the real SpecSpace server, an independent runtime worker and a
deterministic agent process. No SpecSpace module is imported by the runtime.
Only scoped draft context and a challenge cross the agent input boundary.
The driver supplies operator credentials only to app-local consent endpoints.
This demonstrates interface credential separation, not isolation against a
malicious process running as the same OS user.

## What the run checks

1. Verified discovery, manifest/schema/Grant hashes and current identity state.
2. Explicit Grant issuance and authoritative session start.
3. Scoped read: another workspace's synthetic private draft is not exposed.
4. Agent key possession and proposal input production without app credentials.
5. Rejection before app approval, then exact approval of the proposed input.
6. Real HTTPS response loss after app processing, followed by exact retry.
7. Native same-ID edit is preserved; retry returns the immutable original result.
8. Changed input/hash, idempotency conflict and wrong workspace are rejected.
9. Actual SpecSpace process restart preserves the original result.
10. Grant revocation dominates cached retry; a short Grant expires fail-closed.

App-side unit tests additionally cover stale snapshot before/after approval,
expired approval, create-only conflicts, malformed transport input, rollback
after draft save, cross-process native concurrency and a process dying inside
a SQLite transaction. The whole Mediated Proposal conformance bundle is not
executed by this driver; passing it must not raise card maturity.

`snapshot_hash` is an app-defined workspace precondition, not an ASP preview
token or effect commitment. The native save continues to be an operator upsert;
the ASP path is deliberately create-only. The stored draft remains private and
never becomes a submitted intake request or authority to execute another action.

## Mock user and human pass

`--mock-user` runs a small deterministic policy, not an LLM or an always-accept
boolean. `--synthetic-approval` remains a compatibility alias for the same policy.
The mock makes two separate decisions:

- Grant consent: only the fixture workspace, runtime and agent, exactly read and
  propose, Compatibility Bearer, and a requested lifetime of at most 300 seconds.
  The request must match the displayed identity/surface binding and discovery.
- Draft approval: exactly the fixture's draft ID and text, in the fixture workspace,
  with `propose` mode. The entire displayed request must match the runtime proposal;
  input and approval hashes must match. Added authority or substituted text is denied,
  even if a caller recomputes the hashes consistently.

The mock receives only consent/approval views, never operator credentials, Grant
bearers or private keys. The driver translates accepted decisions into the existing
app-local operator calls. App/runtime identity, schema, expiry and authorization
checks still run independently; the mock is not their replacement. In particular,
approval expiry remains app-enforced; the approval view does not expose its deadline.
Unit tests verify both refusal decisions and that refusal sends no operator Grant
or approval call. The real-process HTTPS run checks the allowed path.

Recorded local verification: 14 unit tests pass (11 mock-policy/driver-gate tests
and 3 runtime primitive tests). The full HTTPS run passes with both `--mock-user`
and the compatibility alias against the pinned SpecSpace revision above.

The summary says `approval: mock_user` and includes separate `user_decisions`
with actor, stage, accept and reason only. No text or secrets enter that decision
log. The native edit used in retry tests is also scripted, not a human interaction.
The second Grant decision in the report belongs to the one-second expiry test.

Omit `--mock-user` (and its alias) for the manual pass. The driver first shows the
Grant's scope, lifetime, verified identity and limitations and asks for `GRANT`.
It later shows the exact proposal JSON, hash and invocation binding and asks
for `APPROVE`. Declining either stops the run; the app is terminated and all
synthetic state is removed. The app's approval window is 120 seconds; a delayed
manual response fails closed rather than silently extending it.

The user selected mock-user automation as the current functional test boundary.
It is not evidence of actual human comprehension or consent. The earlier manual
attempt ended with `approval_expired` before saving the ASP draft; it is not a
successful human pass. Human UX and independent second-developer reproduction
remain separate follow-ups, not prerequisites for running the mock-user test.
No active-hour/adoption benchmark is inferred from test runtime.

## Stopping boundary

There are intentionally no signed receipts, OAuth server, remote runtime,
general JSON Schema/JCS package, native UI changes, production state migration,
export, compensation or full runtime-budget implementation. The demo runtime
is a fixed driver, not an open-ended autonomous scheduler. App-side runaway
pause fences new actions and preserves the RFC's exact completed replay
exception; policy does not permit automatic resume.

The next decision is whether this measured integration burden is acceptable
for one private draft operation. Do not add another RFC feature or expand the
experiment merely to turn its partial coverage into a full-profile claim.

The current app-side diff adds roughly 800 lines of isolated protocol/storage
code, plus tests and documentation, while the native business function gains
only a 15-line transaction wrapper. That is already a meaningful adoption-cost
signal for such a small operation. A passing smoke proves this boundary works
in the tested configuration; it does not prove the integration is cheap or
justify expanding the standard. Setup effort, human comprehension and a
second developer's reproduction still need assessment.
