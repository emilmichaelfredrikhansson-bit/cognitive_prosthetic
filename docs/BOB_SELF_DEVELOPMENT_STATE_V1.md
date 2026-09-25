# Bob Self-Development State V1

This module owns durable intent and lifecycle state for Bob's low-priority self-development lane.

It is a backlog/state layer, not an execution engine. Repository execution, worktrees, semantic lease enforcement, cognition, effects, approvals and promotion remain owned by their existing bounded subsystems.

## Invariants

- The queue is bound to exact Bob repository identity and canonical ref; identity drift fails closed.
- Queue items carry a bounded goal plus one or more semantic leases.
- V1 permits at most one `ACTIVE` self-development item at a time.
- A runtime restart never silently replays active work. Any persisted `ACTIVE` item becomes `INTERRUPTED` with `RUNTIME_RESTART_RECONCILE_REQUIRED`.
- An item may bind at most one execution run identity.
- An item already bound to an execution run may not be blindly requeued; execution reality must be reconciled first.
- State transitions are durably persisted with verified Windows fallback semantics.
- Queue state never grants repository/provider authority and never performs an external effect.
- `QUALIFIED` means the self-development candidate satisfied its recorded verification; it does not mean canonical promotion occurred.

## Lifecycle

```text
QUEUED
  -> ACTIVE
      -> BLOCKED
      -> QUALIFIED
      -> DISCARDED
      -> FAILED

ACTIVE at Bob restart
  -> INTERRUPTED

BLOCKED / INTERRUPTED
  -> QUEUED only through explicit requeue
  -> terminal state
```

The later background scheduler may claim queue items and create repository execution runs with `lane=selfdev`. The execution ledger remains authoritative for run/worktree/lease state.

## Boundary

This module must not merge, push, delete branches, execute provider effects, change credentials, expand authority or promote into canonical Bob state.
