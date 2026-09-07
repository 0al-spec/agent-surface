# ADP-03: pinned CLI local-persistence source audit

> Follow-up decision, 2026-09-08: [user-selected agent responsibility](../byoa-responsibility-decision.md)
> stops live retention work. The findings below remain static evidence; the
> experiment suggested here is no longer the selected next step.

**Static evidence only; no live run.** ASP PR #86 merged as `73c78fc`.
This audit reads the official `openai/codex` tag `rust-v0.145.0`, peeled
commit `25af12f7e61572b0bc18ddb1008be543b91519b0`. No binary was built or
launched, no authentication store was accessed and no account settings changed.
Source-tag identity does not establish the provenance of an installed binary.

## Decision

Do not treat `ephemeral: true` as evidence of transient application-output
handling. The pinned source contains a separate app-server diagnostic path that
can persist incoming JSON-RPC tool responses in SQLite, independent of the
thread's rollout persistence. This is a concrete source-level feasibility
objection, not a report that the user's machine retained any particular data.

The next experiment should target this path first, rather than start by building
a general filesystem crawler. The existing [approval gate](README.md#approval-gate-no-authentication-action-yet)
still applies. Nothing here authorizes a live run or closes ADP-03/ADP-02.

## Evidence chain

All references below are pinned to the audited commit, not current `main`.

1. **Thread configuration:** `thread/start` copies `ephemeral` into its typed
   configuration overrides ([thread processor, lines 997–1008](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/app-server/src/request_processors/thread_processor.rs#L997-L1008)).
   Session creation skips the live-thread persistence object when ephemeral
   ([session, lines 599–610](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/core/src/session/session.rs#L599-L610))
   and omits that session's state DB handle
   ([lines 680–690](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/core/src/session/session.rs#L680-L690)).
   These checks are not a process-wide storage prohibition.
2. **Separate process initialization:** app-server initializes its SQLite state
   runtime before installing logging
   ([startup, lines 564–573](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/app-server/src/lib.rs#L564-L573)).
   Its tracing subscriber attaches a DB logger using that process-level handle
   ([logging, lines 629–644](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/app-server/src/lib.rs#L629-L644)).
   This is distinct from the per-session handle above.
3. **Payload-bearing event:** `process_response` logs the incoming peer response
   at INFO with Debug formatting before forwarding its result
   ([processor, lines 741–746](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/app-server/src/message_processor.rs#L741-L746)).
   `JSONRPCResponse` derives Debug and contains `result`
   ([RPC type, lines 67–72](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/app-server-protocol/src/rpc.rs#L67-L72)),
   whose alias is ordinary JSON Value
   ([line 32](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/app-server-protocol/src/rpc.rs#L32)).
   The pinned Calcu adapter sends its application result in precisely such a
   peer response ([Calcu `a059d77`, lines 498–506](https://github.com/SoundBlaster/Calcu/blob/a059d777405579f64a24af96aa1119e1950beee8/server/codexAdapter.ts#L498-L506)).
   Thus application tool-result content can enter the diagnostic message;
   this is not merely a call-ID log.
4. **Logging admission and sink:** the DB logger's default target filter enables
   TRACE, with specific exclusions that do not exclude this app-server INFO
   event ([filter, lines 53–64](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/state/src/log_db.rs#L53-L64)).
   Its event handler stores the message and formatted feedback body without an
   ephemeral-thread guard
   ([handler, lines 203–248](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/state/src/log_db.rs#L203-L248)).
   Buffered entries reach `insert_logs`
   ([flush, lines 430–436](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/state/src/log_db.rs#L430-L436)).
5. **Storage root:** rollout initialization supplies `sqlite_home` to the state
   runtime ([initialization, lines 105–119](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/rollout/src/state_db.rs#L105-L119)),
   which opens a separate logs database
   ([runtime, lines 192–224](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/state/src/runtime.rs#L192-L224)).
   Its filename is `logs_2.sqlite`
   ([constant, line 95](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/state/src/lib.rs#L95));
   `sqlite_home` defaults to the Codex home unless overridden by configuration
   or its supported environment setting
   ([config, lines 3756–3761](https://github.com/openai/codex/blob/25af12f7e61572b0bc18ddb1008be543b91519b0/codex-rs/core/src/config/mod.rs#L3756-L3761)).
   A temporary task cwd/TMPDIR alone does not relocate this root.

## What this does and does not establish

The source establishes a payload-to-durable-storage path under successful
initialization, event delivery and log flushing. Queue pressure, process
termination, storage errors and build/config differences can affect an actual
write. We have not observed a marker on disk, measured persistence duration or
verified cleanup in a real run. A stderr filter alone is not evidence that the
separately filtered DB subscriber is disabled.

Debug output need not preserve the exact JSON serialization used as the probe
marker. An exact-byte scan can therefore miss this path. A future observer must
attribute the tool response and compare its decoded synthetic result fields,
not silently label a raw-marker miss as absence. SQLite/WAL and transient writes
need explicit coverage; inaccessible or unparsed storage stays incomplete.

This is not an exhaustive cache, feedback, memory, telemetry or provider audit.
It neither asserts provider retention nor demonstrates a cross-user disclosure.
No source finding is fed into `probe.py` as if it were a live observation.

## Smallest next step

1. Review whether this static counterexample is already sufficient to reject
   reliance on ephemeral mode for the proposed transient contract. Keep that
   capability unestablished; do not silently relax the contract or change the RFC.
2. If empirical confirmation is useful, separately approve one isolated success
   run with one synthetic tool output, using the existing authentication gate.
   Observe only the resolved test SQLite logs root and its journal/WAL sidecars,
   with observer controls and the existing bounds. No personal-home scan.
3. Account for the logger's buffered writes; distinguish a completed observation
   from termination before flushing. A positive result can stop further testing;
   a negative result cannot establish transient conformance. Cancel/timeout
   variants remain later optional work, not an automatic three-run campaign.
4. Record only sanitized findings. Choose a supported mitigation or reconsider
   runtime suitability separately; no patched CLI, new login, collector or
   Calcu/SDK migration is introduced by this audit.

All other ADP-03 gates remain open: classification/redaction enforcement design,
Grant projection, copy ownership and UI lifecycle, principal/disclosure, selected
route applicability and outstanding-reference lifecycle. ADP-02's independent
adoption-cost decision is unchanged.
