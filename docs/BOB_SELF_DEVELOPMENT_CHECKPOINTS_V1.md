# Bob Self-Development Checkpoints V1

This module owns reversible local Git checkpoints for Bob-owned isolated self-development worktrees.

It does not create cognition, schedule work, integrate branches, push branches or grant promotion authority.

## Authority boundary

A checkpoint target must already be a queue-bound `lane=selfdev` execution run whose authority contains the exact `selfdev_item_id` and `promotion_authority=NONE`.

The recorded worktree path must resolve to the existing repository coordinator's run-specific worktree path. Checkpoint operations never target the canonical checkout.
## Establish checkpoint

A checkpoint may be recorded only when the selfdev execution is at a safe local state (`ACTIVE` or `PARKED`) with no RUNNING cognition and the isolated worktree is clean.

The checkpoint records exact item ID, run ID, branch, base SHA and branch/worktree head SHA plus optional deterministic verification evidence. The store is repository/canonical-ref bound and durable.

V1 deliberately does not auto-stage or auto-commit a dirty tree. Mutation/commit authority remains a separate concern; this module checkpoints already-materialized clean Git identities.
## Revert

Revert is allowed only for a checkpoint belonging to the same item, run and branch. Bob verifies the run worktree identity, resolves the checkpoint commit, performs the destructive reset only inside that isolated worktree, removes untracked experiment files, and reads back exact HEAD + clean status.

This operation never changes canonical Bob state and never pushes.

## Discard

Discard is an autonomous sandbox cleanup operation permitted by the recursive self-improvement contract. It requires a safe cognition boundary, restores the isolated run branch to its recorded base SHA, removes untracked experiment files, verifies the clean base state, cancels the execution run, removes the clean worktree, and marks the self-development item `DISCARDED` with a no-promotion receipt.

The branch itself is not deleted; it is left pointing at the safe base identity for auditability. Repository deletion, protected-branch mutation, integration and promotion remain outside this capability.

## Interactive-first orchestration

Ordinary interactive run creation may arbitrate against the same Bob repository. If the new interactive run is QUEUED only because of semantic scope conflict or repository capacity, Bob may pre-empt a bound selfdev run only after this module successfully records a clean safe checkpoint for that exact item/run/branch.

A dirty worktree, RUNNING cognition, non-selfdev blocker or otherwise unsafe checkpoint causes pre-emption to fail closed; the interactive run remains queued and the selfdev lease stays owned. Successful pre-emption parks the existing selfdev run without changing its item attempt, branch or worktree identity. When the corresponding interactive run becomes terminal, the checkpoint label provides durable correlation and Bob may resume the exact parked selfdev run through normal lease/capacity arbitration.

The HTTP control surface exposes checkpoint status/create/revert, discard and explicit resume of a parked item. Interactive run creation itself uses the same safe-checkpoint arbitration before parking selfdev.

## Fail-closed invariants

- checkpoint/revert/discard never operate on a non-selfdev or unbound run;
- checkpoint/revert require no RUNNING cognition;
- checkpoint requires a clean isolated worktree;
- revert can restore only a checkpoint from the same item/run/branch;
- discard resets only the Bob-owned run worktree/branch and verifies the base SHA before terminalizing;
- no operation merges, pushes, deletes a branch, expands provider authority or promotes the candidate.
