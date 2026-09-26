# Bob Work Campaign Queue V1

This module is the durable backlog and admission scheduler above Work Campaign control.

It still does not perform cognition or code changes itself. It decides which explicit safe work item may receive an existing repository execution slot.

## Ownership

The queue owns:
- explicit campaign work items;
- FIFO order and item dependencies;
- queued/blocked/admitted/stop-requested/outcome state;
- exact execution-run bindings after admission;
- durable verification receipts and final review digest.

Work Campaign control remains authoritative for target scope and wall-clock deadline. Repository coordinators remain authoritative for capacity, semantic leases, branches, worktrees and run state.

## Admission

A work item names one campaign target workspace, goal, base ref, semantic leases and optional dependencies on earlier work items in the same campaign.

A tick may admit only work whose dependencies are verified SUCCEEDED and whose campaign is RUNNING.

Capacity waiting stays in this queue. The queue checks repository worker-slot capacity before admission; if capacity is full, the item becomes BLOCKED without creating an execution run.

If a deeper lease/dependency rule still rejects the attempted run, campaign control cancels that non-ACTIVE run immediately and the backlog stores the blocker. It retries only after the repository ledger changes.

Every admitted execution run carries the exact campaign work item ID in its existing run authority. On restart, the queue adopts a matching live run if a crash happened after coordinator admission but before the queue could persist its run binding; more than one live match fails closed. This closes the duplicate-work crash window without adding another execution authority.

This separation is required so pre-deadline queued execution runs cannot silently activate after a campaign deadline.

## Deadline and cancellation

When the campaign reaches DEADLINE_REACHED:
- unadmitted QUEUED/BLOCKED work becomes SKIPPED_DEADLINE;
- already admitted work becomes STOP_REQUESTED;
- no run is asynchronously killed mid-step.

When the campaign is CANCELLED:
- unadmitted work becomes CANCELLED;
- already admitted work becomes STOP_REQUESTED.

STOP_REQUESTED is a durable handoff to the execution layer: finish the current safe unit, checkpoint where appropriate, then explicitly terminalize the work.

## Outcome contract

A campaign work item never infers success from an execution run merely becoming terminal.

Successful finish requires explicit verification evidence. If the bound run is still nonterminal, explicit finish cancels the run at that caller-declared safe boundary and records the exact branch/head receipt.

A successful receipt records promotion_authority=NONE and auto_merge=false from execution authority.

Unexpected terminal runs become BLOCKED with TERMINAL_RUN_REQUIRES_OUTCOME until an explicit outcome is recorded.

## Digest

The digest summarizes item counts, blocked work, pending safe-stop work and verified review candidates with exact workspace/run/branch/head identity.

A review candidate is not a promotion. The digest cannot merge, push or approve anything.

## Explicit non-capabilities

This module does not:
- invent tasks from a broad goal;
- call ChatGPT/cognition;
- modify repository files itself;
- automatically kill active work at deadline;
- merge, push, open PRs or promote candidates;
- widen provider/effect authority.

The next orchestration layer may use this queue to repeatedly select and execute bounded work, but it must preserve these boundaries.
