# Bob Worktree Coordination V1

This document defines local mutable-state isolation for execution runs.

## Isolation

Every active mutating run gets its own local Git worktree and branch.

Default branch form:

```text
bob/run/<run_id>
```

Default worktree storage is outside the canonical checkout:

```text
.<repository-name>-bob-worktrees/<run_id>
```

The canonical/interactive checkout is therefore not shared as mutable state between parallel runs.

## Repository binding

An `ExecutionCoordinator` belongs to exactly one stable GitHub repository identity. Before opening its ledger it verifies that the configured local `repo_root` has an `origin` matching `repository_full_name` and that the bound `canonical_ref` resolves locally. A caller cannot switch that coordinator to a different canonical ref for integration.

Repository ID, full name, local root and canonical ref are part of ledger identity. Workspaces sharing one repository reuse one coordinator; distinct repositories receive distinct worktree roots and integration queues.

## Safety

The worktree coordinator may:

- resolve refs;
- create a local run branch;
- create/reuse the matching isolated worktree;
- inspect branch heads and ancestry;
- refuse unsafe cleanup.

It does **not**:

- merge;
- push;
- force-push;
- delete branches;
- promote a candidate;
- expand workspace/provider authority.

A pre-existing worktree whose actual branch does not match the ledger record fails closed.

Dirty worktrees are never removed automatically.

## Serialized promotion preparation

When a run is marked ready, the coordinator reads the actual run-branch head and binds that SHA to verification evidence.

After another run changes canonical state, the next candidate must be rebased/re-grounded and reverified. The coordinator verifies that the current canonical SHA is an ancestor of the rebased candidate before recording refreshed verification.

Recording `INTEGRATED` is allowed only after the verified candidate head is actually contained in the current canonical ref. This records observed reality; it does not perform the merge.

## Relationship to leases

Worktrees isolate filesystem/Git mutation. Semantic leases isolate responsibility.

Both are required:

```text
different worktree
+ non-overlapping semantic lease
+ bounded authority
+ request correlation
+ serialized integration
```

A separate checkout alone is not permission to mutate the same semantic scope concurrently.
