# Bob Execution Ledger V1

This document defines the durable execution-state contract for bounded parallel Bob work.

## Core rule

> Bob may keep several independent work runs alive, but no chat/process is allowed to be the memory of that work.

V1 permits at most **3 active runs per repository**. Additional work for that repository is durable and queued. A different repository has its own three-slot domain and never consumes these slots.

Every ledger is mechanically bound to `repository_full_name`, stable `repository_id`, resolved `repo_root` and `canonical_ref`. Those values are persisted in ledger state. Opening the same ledger path with a different repository identity fails closed.

A run records:

- `run_id`;
- goal/workspace/lane;
- exact base ref + base SHA;
- isolated branch/worktree identity;
- semantic leases;
- dependencies;
- authority snapshot for audit only;
- cognition IDs;
- verification evidence;
- integration state.

The authority snapshot never grants authority. Existing workspace/provider policy remains authoritative.

## Parallelism contract

Parallel work is allowed only when leases do not conflict.

Lease classes are:

- `module:<id>`
- `work:<id>`
- `contract:<id>`
- `path:<repo-relative-path>`

Exact semantic leases conflict. Path leases also conflict hierarchically, so `path:bob` conflicts with `path:bob/driver.py`.

A run holding `ACTIVE`, `AWAITING_APPROVAL`, `READY_FOR_INTEGRATION` or `INTEGRATING` keeps its leases. Queued work owns no lease.

The active-run cap is 3 **inside one repository ledger**. The fourth eligible run in that repository remains `QUEUED` with a durable reason such as `CAPACITY`, `SCOPE_CONFLICT:<run>` or `DEPENDENCY:<run>`. Semantic leases and the FIFO integration queue are likewise repository-local domains.

A repository-scoped coordinator registry maps `workspace -> repository identity -> configured local repo root -> ExecutionCoordinator`. Two workspaces that resolve to the same stable repository ID share the same coordinator, ledger, leases, worktree root and three-slot cap. A workspace whose repository has no configured local path cannot start local execution.

## Cognition correlation

Each run may have at most one running cognition at a time.

Every cognition has:

```text
run_id
cognition_id
request_id
state
purpose
started_at
finished_at
```

The browser bridge must preserve `request_id` correlation end to end. Late completion from one request must never be consumable by another request.

V1's managed-browser transport still executes browser cognition tasks through one serialized Playwright worker. This is deliberate until multi-page/provider concurrency is separately qualified. The execution layer can still maintain up to three independent active runs/worktrees and interleave their bounded cognition plus deterministic work without losing identity. Raising actual simultaneous model-generation concurrency is a transport-capacity change, not a ledger change.

## Restart semantics

The ledger is durable JSON written atomically under local `.bob/runtime/` state.

After Bob restart:

- a cognition that was `RUNNING` becomes `INTERRUPTED`;
- an `INTEGRATING` run returns to `READY_FOR_INTEGRATION`;
- recovered integration requires re-verification;
- queued/active run identity, leases, dependency state and integration order survive.

## Integration contract

Parallel execution converges through **serialized integration**.

A qualified run enters `READY_FOR_INTEGRATION` with:

- verified candidate head SHA;
- canonical/base SHA against which it was verified;
- deterministic verification evidence.

The integration queue is FIFO.

Before a queue-head run may enter `INTEGRATING`, its `verified_base_sha` must equal the **current canonical SHA**. Otherwise Bob returns `REBASE_REVERIFY_REQUIRED`.

Therefore:

```text
parallel A/B/C work
→ A ready
→ B ready
→ C ready
→ integrate A
→ canonical changes
→ B rebase/re-ground/reverify
→ integrate B
→ C rebase/re-ground/reverify
→ integrate C
```

Only one run can own the integration gate.

The ledger does not perform merge/push/promotion. Promotion remains a separate authority boundary.

## Failure rule

State transitions fail closed. A run may not:

- begin cognition while non-active;
- run two cognitions simultaneously;
- bypass an earlier integration candidate;
- integrate against stale canonical state;
- claim successful integration merely because its own cognition says it succeeded.
