# Bob Work Campaigns V1

Work Campaigns give the operator a durable wall-clock boundary for bounded work across one or more configured repositories.

This tranche is campaign control and admission. It is not yet the autonomous worker loop that chooses the next task by itself.

## Authority split

Campaign state owns:
- campaign goal and target workspaces;
- duration, start time and absolute deadline;
- whether new work may be admitted;
- durable bindings to campaign execution runs;
- campaign completion/cancellation state.

Existing repository coordinators remain authoritative for:
- repository identity;
- per-repository capacity;
- semantic leases;
- branches and worktrees;
- execution-run state;
- integration state.

Campaign control is not a second execution scheduler.

## Start contract

A campaign is created as PLANNED with one or more workspace targets and a bounded duration.

V1 permits at most one workspace per repository in one campaign so repository identity remains unambiguous.

Start fails closed unless every target workspace has an explicit local repository coordinator binding. Starting records an absolute timezone-aware deadline from the durable duration.

Every campaign and campaign run records promotion_authority=NONE; campaign state also records auto_merge=false.

## Deadline semantics

The wall-clock deadline is a hard admission boundary:

- before the deadline, new campaign runs may be admitted;
- at or after the deadline, RUNNING becomes DEADLINE_REACHED;
- after the deadline, no new campaign run may be created;
- an already active run is not killed asynchronously in the middle of a cognition, write or verification step.

Existing work must reach a safe boundary and then be parked, cancelled or terminalized by orchestration above this module.

This preserves the operator's requested wall-clock budget without inventing unsafe mid-effect process cancellation.

## Execution binding

Campaign work is created through the existing repository ExecutionCoordinator with lane=campaign.

The run therefore inherits ordinary repository rules:
- max three worker slots per repository;
- semantic lease conflicts;
- isolated branch/worktree state;
- dependency handling;
- no implicit integration.

A campaign stores only the resulting workspace, repository ID and run ID.

Restart reconciliation discovers campaign runs from execution authority metadata (lane=campaign + exact campaign_id) and can recover the narrow crash window after run creation but before campaign binding persistence.

## Completion and cancellation

A campaign can become COMPLETED only when every bound run is terminal.

Cancellation closes new admission but deliberately does not kill nonterminal runs. The returned run summary tells higher-level orchestration which work still needs a safe checkpoint/park/cancel boundary.

Campaign completion/cancellation never means candidate promotion.

## Explicit non-capabilities

Work Campaigns V1 does not yet:
- choose or prioritize work items autonomously;
- invoke cognition on its own;
- checkpoint or park active runs automatically at deadline;
- redistribute blocked tasks automatically;
- merge, push or promote candidates;
- produce the final operator digest.

Those are higher orchestration steps built on this durable campaign boundary.

## Safety invariant

A bounded campaign may coordinate many hours of repository work, but time pressure never widens authority.

The deadline can stop admission; it cannot grant merge, production, spend or provider permissions, and it cannot bypass repository isolation or semantic leases.
