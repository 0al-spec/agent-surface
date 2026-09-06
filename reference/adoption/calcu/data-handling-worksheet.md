# ADP-03: Calcu data-handling evidence and decision worksheet

Status: evidence pass, **policy unresolved** (2026-09-06).
Inspected Calcu SDK-consumer revision `5e5a23f04bad649a23eedaad4f83126b2ec3ff7e`.
This is not consent, a provider attestation or authorization to migrate live.

## Observed paths

Paths below are relative to the Calcu repository. They identify implementation
evidence, not contractual promises by the CLI, provider or operating system.

| Data | Path / code evidence | Observed control | Remaining owner/evidence |
| --- | --- | --- | --- |
| User task | `src/features/agent-task/AgentTaskPanel.tsx`, `server/taskHost.ts` | React snapshot; same-origin task POST; bounded body; no application history/persistence API found | Deployment owner defines task retention separately from application-output exposure. Browser/OS capture is unverified. |
| Task sent to model | `server/codexAdapter.ts` thread/turn startup | Fresh CLI process, temporary working directory, `ephemeral: true`, allowlisted environment | CLI/account/provider retention and processing capabilities are unknown. Local CLI is not local inference. |
| Protocol stdout / stderr | `server/codexAdapter.ts`, `server/demo.ts` | Bounded in-memory protocol; normal stderr discarded; optional debug diagnostics go to process stderr | Deployment owns stderr sink, logging, crash dumps and proxy policy; debug output requires separate inventory. |
| Operands / application output | `server/localBackend.ts`, `server/executor.ts`, adapter tool response | Closed calculator input; independent engine execution; result returns through mediator to model | Classify output before delivery; establish enforceable runtime retention and redaction. Model/provider downstream storage is not established. |
| Result, task, trace and prose | `AgentTaskPanel.tsx`, `src/features/agent-task/protocol.ts` | Bounded stream; separate verified action/unverified prose; React state, no app persistence found | Browser extensions, devtools, session capture and future exports/history are outside this evidence. |
| Temporary directory | `server/codexAdapter.ts` cleanup | Process-group termination and recursive per-task directory removal | This does not establish erasure from filesystem journals, backups, CLI caches or files outside that directory. |
| Grant/session/credential | `server/demo.ts`, `server/executor.ts` | Per-task issuance/revocation; in-memory server ownership; not in browser/model payload | No durable deletion or audit claim; implementation remains a development demonstration. |

## Applicable distinctions

[Data Exposure Contract](../../../drafts/modules/privacy.md) requires explicit
application source exposure and derived Grant projection. Action-output
retention does not define retention of the user's task or agent-supplied input.
Application redaction occurs before release, not after a provider receives data.
Base runtime/agent retention is not a whole-provider-path guarantee; that needs
the separately applicable Remote Processing Privacy obligations.

Consequently, no application persistence observed is **not** evidence of
provider-wide `transient` handling. Neither process exit nor `ephemeral` proves
deletion. No provider account/settings were inspected in this pass.

## Required decision record before ADP-05

The deployment owner must fill and approve the following, supported by actual
capability evidence rather than defaults invented by the SDK:

1. Task, operand, output and trace classification; application redaction rules.
2. Selected processing path and actual provider/CLI/account configuration.
3. Separate task-input and application-output retention periods, deletion owner
   and evidence; include diagnostic, proxy, history, backup and crash channels.
4. Whether whole-path remote-processing restrictions apply and can be enforced;
   reject unsupported restrictions before releasing application data.
5. Principal/tenant ownership, disclosure and consent wording; no multi-user
   deployment implied by the single-user demo.
6. UI display lifecycle and whether export/history is permitted (not added here).

Until resolved, ADP-03 remains in progress and live contract migration blocked.
The existing demo is not reclassified as conforming and is not changed by this
worksheet. See the [delivery backlog](../../../review/adoption-delivery-backlog.md).
