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

## Authentication-dependent policy evidence (2026-09-06)

The official [Codex authentication documentation](https://developers.openai.com/codex/auth/)
distinguishes ChatGPT subscription login from API-key access: the applicable
workspace controls or API organization data settings depend on that choice.
It also allows custom providers/proxies. These are product capabilities, not
evidence of this deployment's effective settings. Current documentation is not
proof that every control is supported by the demo's pinned CLI version.

| Selected route | Evidence needed from the owner | Do not infer |
| --- | --- | --- |
| Personal ChatGPT login | Account category, applicable data controls and documented handling of task/tool output | Enterprise retention, API retention or no training from the word Codex |
| Managed ChatGPT workspace | Workspace category and administrator-confirmed applicable retention/processing controls | That an available enterprise control is enabled for this workspace |
| API key | Effective organization/project data-sharing and retention controls, actual endpoint/provider path | Zero retention from API authentication or ephemeral thread creation |
| Custom provider or proxy | Each additional processor/logging hop and its applicable policy | That OpenAI account settings govern an independent proxy or provider |

No authentication file, account identifier, API key, token or workspace secret
is needed in this public record. The owner can report just the route and policy
categories; sensitive deployment evidence should stay outside the repository.

### Smallest next decision

First identify the actual login route. Then choose whether the next experiment
uses **synthetic, non-sensitive arithmetic tasks only** or must support private
tasks. Synthetic-only is a proposed experiment restriction, not an approved
policy, input classifier or an exemption from mandatory ASP privacy controls.
Arbitrary numbers/task text cannot automatically be classified as public.

The record stays unresolved until required retention and processing constraints
can be matched to real capabilities. If a selected restriction cannot be
enforced, keep that live migration blocked; do not silently relax the Grant or
replace the provider. This document neither changes the demo nor starts a live
Codex task.
