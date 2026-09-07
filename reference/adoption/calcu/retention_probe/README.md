# ADP-03: bounded real-CLI retention probe preparation

**Prepared, not run.** This directory contains the execution plan and an offline
report interpreter. It contains no live launcher, credential reader, filesystem
crawler or automated login. The live collector and disposable environment must
be prepared under the approval gate below; running `probe.py` does not run Codex.

Pinned targets: Calcu `a059d77`, Codex CLI `0.145.0`, `gpt-5.6-luna`, effort
`low`; one `calculation.propose` tool call through LocalBackend → loopback HTTPS
→ executor. No model/version fallback. ASP baseline: `b6f750f`, Privacy
`0.1.0-draft.3`. Different CLI/platform behavior needs a separately labeled run.

## Question and evidence limit

The [pinned source audit](source-audit.md) identifies a separate SQLite tool-response
logging path despite ephemeral thread persistence being disabled. Read it before
designing a collector: the next proposed experiment targets that path with one
success run, not a general crawler or an automatic three-scenario campaign.
It is static evidence only; the live approval gate below remains unchanged.

Can we observe application-output plaintext persisted by the selected CLI
during or after one ephemeral task, within a precisely inventoried disposable
environment? A positive retained marker is evidence of that observed copy;
absence is only a bounded observation, never proof of complete deletion.
Transient prohibits durable persistence, so a write later deleted is still
relevant. Post-exit snapshots alone miss it.

The current adapter uses a temporary working directory and `TMPDIR`, but passes
`HOME`, `CODEX_HOME` and selected configuration/proxy variables from its allowed
environment. The CLI can therefore have state outside the task directory.
An isolated probe changes that environment: its findings do not automatically
establish behavior in the user's ordinary home, caches or keychain.

Current [official authentication documentation](https://learn.chatgpt.com/docs/auth#credential-storage)
describes file and OS credential-store caching and separate ChatGPT/API routes.
Do not infer pinned `0.145.0` behavior from current documentation; verify supported
settings in the disposable environment before login. The
[app-server documentation](https://learn.chatgpt.com/docs/app-server) is a
protocol reference, not evidence of all local persistence paths.

## Approval gate: no authentication action yet

Recommended: a disposable OS account/VM with no host home mount, no shared host
keychain, no unrelated projects and no existing credentials. A separate
`CODEX_HOME` alone is not OS isolation. The user signs into ChatGPT themselves
inside that environment, after explicitly approving this strategy. Keep the
personal subscription route; do not switch to an API key, provider or plan.
Confirm pinned-version support before selecting file/keyring behavior.

Never copy, inspect, print or hash the normal auth store. Auth artifacts and
login logs are excluded from content scanning/export even inside the disposable
environment. Note those exclusions as unobserved coverage, not as clean files.
Do not change account data controls or log out the user's normal session.
After the probe, the user ends the dedicated login and the disposable environment
is destroyed; no backup or retained VM snapshot containing authentication.

Approval must cover: the isolated environment and login route, at most three
synthetic tasks on the existing subscription, allowed non-auth observation
paths, temporary observer storage and its deletion. Until then, only the
offline commands below are authorized by this preparation.

## Bounded procedure after approval

1. **Preflight (no model call):** verify exact binary version and record its
   artifact digest, Calcu commit, platform and sanitized configuration. Inventory
   writable CLI state/cache/log roots, working directory and scratch storage.
   Identify auth exclusions without opening them. Abort on unexpected provider,
   tool, writable host mount or unsupported pinned setting.
2. **Observer controls:** in a separate observer-only fixture area, seed a
   synthetic marker in plain text and a file with a SQLite-like extension;
   verify detection. Verify unreadable/oversized paths become incomplete, not
   clean. Include a create-then-delete control for the chosen write observer;
   if it misses it, `write_observation_complete` stays false. No recursive
   scanning of the user's home. Collector implementation must enforce scope,
   reject symlinks/out-of-root paths, bound bytes/time and redact errors.
3. **Clean baseline:** remove controls, start a fresh measured task area and
   record baseline marker absence. Auth setup is complete before this baseline.
   Observer-owned protocol captures are separate from measured CLI artifacts.
4. **One success run:** submit a synthetic arithmetic task with fresh finite
   operands. Record a separate task-input marker and the exact returned four-field
   output serialization as application-output marker. Do not add fields to the
   tool schema or bypass the executor. Confirm one admitted backend call and
   actual tool-output delivery before interpreting retention evidence.
5. **Two terminal variants, at most:** cancellation after tool delivery, then
   timeout after tool delivery, each with a new process and fresh markers. If
   the turn completes before the trigger, record the scenario as inconclusive;
   do not fabricate the event or loop until it happens. Stop the batch on an
   unexpected authority path or failed cleanup.
6. **Observe:** monitor approved non-auth writes while running; take bounded
   snapshots after process-group termination and once 5 seconds later, before
   deleting the environment. The 5 seconds is an observation point, not an ASP
   permitted retention period. Grant-end/cancel timestamps must be recorded.
   Keep input and application-output findings distinct. Follow Calcu's existing
   30-second task timeout and TERM→KILL lifecycle; confirm termination instead
   of treating a sent signal as proof. Each scan: at most 10 seconds, 256 files,
   32 MiB total, 4 MiB per file; any limit or read/observer failure is incomplete.
7. **Sanitize and stop:** emit only the closed observations below plus a
   manually reviewed scope/limitations record. No raw protocol, task, operands,
   absolute paths, token, identity artifact, auth hash or account identifier in
   committed reports. Dispose of observer captures after their booleans are
   recorded. No automatic retries or prolonged background monitoring.

The future observer must distinguish output marker bytes from the observer's
own captures and control fixtures. Exact-byte scans can miss JSON escapes,
fragmentation, compression, encryption, SQLite WAL/deleted pages, memory, swap,
crash dumps, OS backups or paths outside its scope. Record these limitations;
do not claim decoded/whole-disk coverage. Confirmed write-to-disk evidence needs
source attribution; file-extension guesses or an unrelated marker are not enough.

## Offline observation/report contract

`probe.py` accepts one sanitized JSON object on stdin (maximum 8 KiB). Required
members are `scenario` and these exact booleans:

```json
{
  "scenario": "success",
  "baseline_clean": false,
  "output_delivered": false,
  "terminal_observed": false,
  "process_stopped": false,
  "scan_complete": false,
  "write_observation_complete": false,
  "temporary_write_seen": false,
  "retained_after_exit": false,
  "retained_after_grace": false
}
```

This not-run template evaluates to `inconclusive`. The other scenarios are
`cancel_after_tool` and `timeout_after_tool`. For them `terminal_observed` means
the requested cancellation/timeout actually occurred after output delivery.
Write/retention booleans refer only to attributed **application-output** markers
in measured CLI-owned storage, never task-input or observer copies.

`scan_complete` and `write_observation_complete` mean completion only within the
declared observer scope/bounds, not all storage or all encodings. An incomplete
scan can still report positive persistence when attribution prerequisites hold.
No output delivery, unclean baseline or unconfirmed process/terminal state makes
the result inconclusive. The interpreter trusts supplied booleans structurally;
it does not verify evidence authenticity or perform collection.

```sh
.venv/bin/python -B -m unittest discover \
  -s reference/adoption/calcu/retention_probe -p 'test_*.py'
# Later, only with a sanitized observation prepared by the approved collector:
.venv/bin/python -B reference/adoption/calcu/retention_probe/probe.py < observation.json
```

Exit 0 means only `no_residue_observed_in_scope`; exit 1 means inconclusive or
observed persistence; exit 2 means malformed observation. Every report retains
`conformance: not_established`, provider retention unknown and memory erasure
not measured. This helper must not be used as a conformance CI gate.

## Delivery and closure

Prepared now: runbook, closed offline interpreter and synthetic regression tests.
Not prepared/executed: approved isolated authentication, live collector, real
CLI runs or evidence report. A filesystem finding informs ADP-03 feasibility;
no result here closes its classification, projection, ownership, route or other
gates, nor the independent ADP-02 decision. Next approval is the isolated login
and three-run scope above, not permission to inspect the existing auth store.
