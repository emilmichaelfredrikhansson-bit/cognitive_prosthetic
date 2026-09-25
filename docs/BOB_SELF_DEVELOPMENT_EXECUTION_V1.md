# Bob Self-Development Execution V1

This module binds durable self-development intent to Bob's existing repository execution coordinator.

It is deliberately not a scheduler. It does not choose work in the background, run cognition, integrate branches, or promote Bob state.

## Ownership

The self-development queue remains authoritative for intent/lifecycle.

The repository execution ledger remains authoritative for:
- run identity and state;
- semantic leases;
- per-repository capacity;
- isolated branch/worktree identity;
- cognition correlation;
- integration readiness state.

This module owns only the binding and reconciliation between those two authorities.
## Claim contract

A claim requires an explicit `base_ref`.

For one queued item the binding layer:
1. marks the queue item `ACTIVE`;
2. creates one execution run with `lane=selfdev`;
3. copies the item's semantic leases into that run;
4. records `selfdev_item_id` in run authority metadata;
5. records `promotion_authority=NONE`;
6. durably binds the resulting `run_id` back to the queue item.

If run creation fails, the item becomes `BLOCKED` rather than being silently retried.

If the run exists but queue binding fails, the run is cancelled and the item is blocked where possible.
## Restart and crash reconciliation

`ACTIVE` queue state still becomes `INTERRUPTED` at Bob restart.

The execution run is not replayed. Explicit reconciliation:
- finds a run only when `lane=selfdev` and `authority.selfdev_item_id` match;
- fails closed if more than one run matches;
- fails closed if a durable queue binding disagrees with execution authority;
- reactivates the same queue attempt when the bound/matching run is still live;
- can adopt the matching run after the crash window where run creation persisted but queue binding did not;
- never increments `attempt_count` when resuming the same execution;
- never creates a second run merely because Bob restarted.

Terminal execution state requires a later explicit lifecycle decision; it is not silently converted into `QUALIFIED`. Finishing a bound self-development item requires the execution run to be terminal first. `QUALIFIED` additionally requires a preserved cancelled run plus explicit verification evidence; the binding layer records the branch head and `promotion_authority=NONE` in the qualification receipt.

## Worktree and promotion boundary

The existing `ExecutionCoordinator` creates the isolated branch/worktree and owns worktree validation.

This module never:
- merges or rebases a candidate;
- pushes or deletes a branch;
- marks a run integrated;
- changes provider/effect authority;
- grants canonical promotion;
- interprets model output as successful verification.

`QUALIFIED` self-development state and canonical promotion remain separate decisions.
