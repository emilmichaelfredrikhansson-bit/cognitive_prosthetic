# Bob Work Campaign Worker V1

## Purpose

`BOB_WORK_CAMPAIGN_WORKER` is the bounded orchestration layer above the durable
campaign backlog. It turns campaign queue state into repeated safe work
selection, safe-boundary checkpoint/parking, interactive-first pre-emption and
a concise operator digest.

It is **not** an execution scheduler. Repository execution remains exclusively
owned by the existing `ExecutionCoordinator`/execution ledger.

## Control flow

```text
campaign deadline/scope
→ durable campaign queue
→ WorkCampaignWorker.cycle
→ existing per-repository coordinator
→ isolated campaign run/worktree
→ explicit verified queue outcome
→ review / paused-candidate digest
```

A worker cycle:

1. asks the campaign queue to reconcile and admit dependency-ready work;
2. exposes ACTIVE admitted runs as bounded ready work;
3. leaves blockers in the durable queue so other independent work can proceed;
4. after deadline/cancellation, never starts new work;
5. converts `STOP_REQUESTED` runs to a durable checkpoint + PARKED state only
   when there is no running cognition and the worktree is clean;
6. leaves unsafe runs pending until a safe boundary exists;
7. completes a campaign only after every queued item already has an explicit
   terminal outcome and no campaign run remains nonterminal.

The worker does not infer success from a terminal execution run.

## Durable checkpoint

A campaign checkpoint binds:

- exact campaign ID and work-item ID;
- exact existing execution run;
- workspace, branch, base SHA and current head SHA;
- optional label and verification metadata.

Checkpoint creation fails closed unless the run is the exact
`lane=campaign`, no-promotion/no-auto-merge run for the queue item, has no
running cognition, is in ACTIVE/PARKED state, and its isolated worktree is
clean with branch/head identity verified.

The worker keeps the latest checkpoint per item plus a monotonic checkpoint
count. Queue outcomes remain authoritative for success/failure.

## Interactive-first behavior

Interactive work is created through the normal execution path. Existing
self-development pre-emption runs first. If the interactive run is still
queued because of campaign scope/capacity, the worker may checkpoint and park
an idle ACTIVE campaign run.

Parking:

- releases the campaign run's worker slot and semantic leases;
- preserves the same run, branch and worktree;
- records the interactive run that caused pre-emption;
- is forbidden while campaign cognition is running;
- requires a clean committed checkpoint.

When the interactive run becomes terminal, the worker resumes the exact parked
campaign run through ordinary coordinator capacity/lease arbitration **only if
the campaign is still RUNNING**. If the campaign reached deadline/cancelled in
the meantime, the run remains safely parked for operator review.

Pre-emption relationships are durable across Bob restart.

## Deadline semantics

Deadline remains owned by `BOB_WORK_CAMPAIGN_CONTROL`.

The worker never asynchronously kills cognition/effect work. It only parks at
a verified safe boundary. If no safe boundary exists yet, the digest reports
the item in `waiting_safe_boundary_item_ids`.

A parked deadline candidate retains branch/head checkpoint information in
`paused_candidates`, even though it is not a successful merge candidate.

## Digest

The worker digest extends the campaign queue digest with:

- worker cycle count and last cycle summary;
- successful verified review candidates from the queue;
- paused/checkpointed candidates;
- blocked items and pending safe stops.

All review/paused candidates retain `promotion_authority=NONE` and
`auto_merge=false`.

## Authority boundary

The worker may:

- reconcile queue state;
- request queue admission through existing campaign/coordinator authority;
- inspect isolated campaign worktrees;
- record checkpoints;
- park/resume `lane=campaign` runs through the execution ledger.

The worker may not:

- create a second execution ledger/coordinator;
- bypass repository capacity or semantic leases;
- perform cognition by itself;
- infer success without explicit verification;
- merge, push, open PRs, integrate or promote;
- mutate canonical/main automatically;
- widen workspace/provider authority.
