# Bob Stateless Module Runtime V1

This module drives one bounded module problem through fresh cognition, deterministic reads, approval-bound effects and durable result recompilation.

## Invariants

- Every cognition step starts in a fresh ChatGPT conversation.
- `BOB.READ` results are folded into durable continuation context before the next fresh cognition.
- A fresh cognition may stage at most one effect.
- Effects are delegated to Effect Authority and remain approval-bound.
- Verified-effect continuation state is durably persisted before post-effect cognition begins.
- If cognition fails or Bob restarts after a verified effect, the continuation may resume without replaying that effect.
- A module above the 15k hard cap may perform architecture repair but may not claim `BOB.DONE` until the measured module is compliant.
- Normal module writes stay on the selected working ref and inside manifest-owned paths.

## Boundary

This module does not own provider credentials, workspace authority, canonical promotion or execution-ledger scheduling.
