# ContextBuilder export: transaction boundary decision

Status: proposed experiment design, not implemented or normative ASP text.

Deferred after [operation selection](operation-selection.md). Keep this as the
design for a possible later export test; do not execute the spike as the next
step. The selected first slice is a private raw-idea draft.

## Keep the product operation fixed

The operation remains replacement of the existing sentinel-owned export
directory for a selected graph target. It produces multiple files. Do not
substitute a new immutable export API and count that as successful adaptation.
Do not implement a general transaction framework for this experiment.

The question is whether one existing application can expose an exact approved
effect at an acceptable integration cost. Application transaction changes and
ASP-specific changes must be counted separately, but both count toward cost.

## First implementation slice

Before adding Grants, implement and test the following boundary in an isolated
ContextBuilder branch, on synthetic data only:

1. Capture the selected source graph and the existing destination revision.
   Stage the complete export away from its live destination using existing
   rendering logic. Preview must not invoke destructive live export. Hash the
   actual output file set and bytes, including provenance and generated paths.
2. At commit, acquire the application's export/mutation coordination boundary,
   check that the source and destination still match the preview, and verify
   ownership. Reject drift before changing the destination. A lock used only by
   the ASP adapter is insufficient: existing export and relevant source writers
   must participate, or the experiment must explicitly exclude and enforce
   those write paths while running.
3. Record the intended replacement and recovery locations durably before
   publication. Keep the old complete generation until the new generation and
   execution outcome are durable. The journal tracks this operation, not a
   new public ASP wire object.
4. Recover an interrupted replacement before admitting another operation.
   Never infer success solely from the existence of a directory or sentinel.
   Exact retry returns the recorded execution result without a second export;
   a reused key with different bound input is rejected.

Two directory renames plus a journal are **not** an atomic replacement for
arbitrary filesystem observers. Participating readers must be coordinated too;
uncoordinated readers can observe a gap. Likewise a journal alone cannot make a
source revision check atomic with mutations by external editors. These are
design gates to resolve, not guarantees supplied by this document. If preserving
the application's actual access model requires a broad storage redesign, stop
this slice rather than silently weakening the ASP claim.

## Verification before authority integration

| Case | Required observable result |
| --- | --- |
| Preview | Live export unchanged; exact staged file set available for inspection. |
| Source or destination drift | Commit rejected; live export unchanged by this operation. |
| Missing ownership marker | Rejected without deleting existing output. |
| Failure during staging | Previous complete export still usable. |
| Process exit at each publication/journal boundary | Restart reconciles to a known complete generation or blocks admission pending recovery; no fabricated successful receipt. |
| Lost response after completion | Retry returns the original execution/result identity without rendering or replacing again. |
| Conflicting writer/reader | Demonstrated coordination or explicit, enforced exclusion; no claim based only on sequential tests. |

I/O fault injection in the baseline is not evidence for process-crash recovery.
The recovery tests must terminate a child process at controlled boundaries and
inspect state from a fresh process. Power-loss durability is a separate claim
and must not be inferred from process-exit tests.

## Then add the minimum ASP path

Select one supported identity/transport profile and complete its requirement
closure. Add distinct read, preview and commit actions, app-verified constrained
authority, a real human approval step, exact idempotency and App Receipt output.
Test changed approval input, expired/revoked authority and response-loss retry.
Do not treat a local function call, scripted approval or content provenance as
evidence that these contracts have already been implemented.

The Application-Audited Effects foundation bundle is a starting matrix, not a
shortcut around normative requirements. Its default selection does not include
every optional Approval Receipt feature. Choose and document applicable
features before claiming coverage. Exported Markdown is application content,
not an ASP manifest: Surface Publisher publication rules do not automatically
apply to that content, nor does an export require portable Replay Tool support.

## Timebox and decision

The approved experiment has a 16-active-engineer-hour ceiling. Earlier setup
was not timed reliably; do not report a precise remaining balance. Record
subsequent active implementation/test time and keep that uncertainty explicit.
Spend at most two additional active hours on the transaction-boundary spike
before a go/no-go review; this is a cap within the original ceiling, not a new
budget or an estimate that the full integration will take two hours.

- **Continue:** one bounded application change coordinates actual access paths
  and passes the failure/retry tests without changing the baseline action.
- **Simplify explicitly:** a different operation or weaker experimental scope
  would be useful, but requires updating the comparison and its claims first.
- **Stop:** safe replacement requires broad storage/access redesign or cannot
  fit the original ceiling. Report this as adoption cost for this application,
  not proof that ASP is universally impractical.

Do not expand normative RFC requirements, bindings or publication machinery to
solve this experiment. The next evidence should come from application behavior.
