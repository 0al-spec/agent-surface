# ADP-02 safety-state SPIKE

This is a deliberately small, offline SQLite prototype. It demonstrates one
durable transaction that checks the supplied Grant id/hash and the prototype's
session id/generation fields, then either reserves an admission or records a
lineage fence. It does not model the complete ASP tuple (principal, runtime,
agent, identity evidence, app, or surface bindings).
The lineage counter and terminal fence are shared by new session IDs and
survive closing and reopening the database connection. This is not a crash or
power-loss test. Revoke races are represented by explicit outcomes;
an admission returned before revocation remains admitted, with no rollback
claim, while a later check is denied.

All values are fixed synthetic test-harness inputs. This is not authentication,
issuance, verification, a receipt, a provider integration, or an SDK.

## Obligation matrix

| SPIKE obligation | Evidence |
| --- | --- |
| Grant validity separate from session state | `test_revoke_is_authoritative...` |
| Exact stale/future generation rejection | `test_stale_and_future_generation_rejected` |
| Resume cannot reactivate revoked/fenced authority | `test_resume_cannot_reactivate_revoked_grant`, `test_resume_cannot_bypass_lineage_fence` |
| Atomic check + admission reservation | concurrent three-connection test; exactly two admissions |
| Durable lineage fence/count across connection reopen/new session | `test_fence_and_count_survive_restart`, `test_partial_count_survives_connection_reopen`, `test_new_session_consumes_same_lineage_counter` |
| Revoke/admit concurrency and subsequent denial | `test_revoke_vs_admit_two_connection_race_then_denies` |
| Failed write releases its transaction | `test_failed_write_rolls_back_and_releases_lock` |
| Corrupt/unavailable storage fails closed | `test_unavailable_or_corrupt_storage_fails_closed` |

## Explicitly out of scope

This does not implement the full `armed -> warning -> fenced` guard record
model, epoch/root/depth/cycle/resolution guards, parent fan-out or pause
protocol, real engine commit/effect reconciliation, transport, profile APIs,
cryptography, real issuance, or conformance. The hard limit is a single local
synthetic lineage counter, not a production policy or a complete guard
state machine. Grant expiry and Grant/integrity verification are also not
implemented; `valid`/`revoked` are test-harness state only.

Run from the repository root with `.venv/bin/python -B -m unittest discover -s
reference/adoption/calcu/safety_spike -p 'test_*.py' -v`.

## Decision input, not a migration approval

The first agent implementation and main-agent corrections were produced in one
short session on 2026-09-06 (initial delegated implementation approximately
five minutes, excluding subsequent review and integration). This is automation
wall-clock evidence, **not** measured developer effort for a live migration.
Eleven local tests pass; they do not exercise process crashes or a real engine.

The useful result is a small transaction boundary and concrete rejection tests.
Most estimated integration work remains: authenticated session control, complete
tuple and Grant verification, full durable guards, provider policy and consent.
The spike does not justify reducing the 13–25 developer-day planning range.
Keep ADP-05…09 gated until the owner chooses whether that cost is worthwhile.
