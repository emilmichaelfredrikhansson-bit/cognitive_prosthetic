# Bob Effect Authority V1

This module owns effect classification, deterministic preview, candidate binding, approval execution and verified effect receipts.

## Invariants

- No effect executes before explicit authority allows its effect class.
- Approval binds the exact workspace identity, effect request, arguments and staged provider state.
- Pending approvals are durably persisted before they are exposed to the operator and survive Bob restart.
- Restarted approvals are re-previewed and re-hashed against current reality before execution.
- Approval/rejection consumption is durably recorded before effect execution, preventing an approved effect from becoming replayable after a crash.
- A changed branch/file/provider binding invalidates and consumes the pending approval.
- External effect success requires verified provider after-state.
- Rejecting an effect consumes the pending approval without executing it.
- A verified effect is never replayed merely because later cognition is unavailable.

## Boundary

The module does not decide the operator's goal and does not widen workspace authority. Stateless cognition continuation is owned by the stateless module runtime; this module supplies the approval/effect primitive it uses.
