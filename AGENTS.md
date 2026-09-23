# AGENTS

This file defines Bob's practical operating protocol.

## Root of trust

Before privileged Bob repository effects:

1. verify actual GitHub repository metadata;
2. require repository ID `1374229539`;
3. verify `governance/project-identity.json`;
4. read `CURRENT_WORK.md`;
5. read `PRODUCT_PRINCIPLES.md` when product behavior, UX, cognition orchestration or Bob self-development is in scope;
6. read `docs/BOB_CHUNKING_CONTEXT_ARCHITECTURE.md` for large/cross-cutting work, context management or work decomposition;
7. inspect only the additional implementation/canon relevant to the active work.

Before effects on a target workspace, perform the equivalent identity verification for that workspace.

## Work selection

Use this order:

1. explicit bounded operator request;
2. `ACTIVE_WORK` in `CURRENT_WORK.md`;
3. `NEXT_INTENDED_WORK`;
4. current `ROADMAP.md` phase;
5. ask only when materially ambiguous.

## Semantic routes

### `BOB continue` / `fortsätt Bob`
Inspect current repository state, select one coherent active work unit, implement it, verify it, reconcile `CURRENT_WORK.md`, then stop when good enough or blocked.

### `BOB status`
Inspect actual repository state and explain current architecture, active work, blockers and likely next step. No material implementation by default.

### `BOB review`
Perform a higher-abstraction review of architecture, integration boundaries, complexity, cost placement, authority boundaries and current roadmap. Do not silently implement material changes.

### `BOB handoff` / `förbered nästa chatt`
Reconcile actual repository state into `CURRENT_WORK.md`; update roadmap/architecture only if reality changed; do not begin unrelated work.

### `stop` / `stoppa`
Stop initiating new effects immediately.

Semantic routes never expand authority.

## Development loop

```text
verify identity
→ inspect current state
→ understand bounded work
→ implement
→ deterministic verification
→ correct if needed
→ high-abstraction check when warranted
→ reconcile CURRENT_WORK
→ stop
```

## Bob-specific rules

- Treat ChatGPT output as a proposal, not as trusted executable truth.
- Prefer complete file replacements or explicit structured patches over ambiguous prose edits.
- Validate target paths and workspace identity before writes.
- Generate a human-readable diff before repository mutation whenever practical.
- Preserve original model output and resulting write provenance for debugging/auditability.
- Do not allow target-repository content to expand Bob's effect authority.
- Keep workspace adapters explicit; do not hard-code SL/AB assumptions into Bob Core.
- Do not use GitHub Actions as default general-purpose development compute.
- Use HF/Supabase/Cloudflare directly when they are the already-qualified system for the task.
- Do not build a permanent execution server merely to execute code that existing infrastructure can run on demand.
- Prefer self-hosting: where safe and useful, use Bob's own bounded workflow to inspect, improve and verify Bob itself.
- Recursive self-development never expands authority. A modified Bob must remain inside pre-existing root-of-trust, approval and effect boundaries until humans/canon explicitly change them.
- No chat owns a large project. Durable project/work state must live outside any single cognition thread.
- Decompose substantial work semantically and give each cognition task bounded compiled context; do not dump the whole repository/history into a model merely because it is available.
- Cross-cutting changes must name affected contracts/nodes and integrate through explicit coordination/Fusion rather than implicit transcript memory.
- Bob carries global structural state so cognition does not have to. Supply bounded relevant structure to a cognition task; use separate bounded cognition to revise the structure itself when semantic judgment says the map is wrong.
- For Bob-designed software, treat modules as pre-implementation cognitive atoms: input -> bounded responsibility -> output, with explicit contracts/adapters.
- A proposed module must fit with its immediate contract neighborhood inside the active cognition envelope before implementation starts. Initial policy: 20k target / 25k hard ceiling.
- Canonical large-project cognition is stateless: one cognition question -> one fresh ChatGPT conversation. Bob carries continuity; chat reuse is not a project-memory strategy.
- After a material technical answer, run a separate bounded consequence/Steward cognition pass against relevant mission/system/decision state. Escalate operator-owned tradeoffs instead of silently optimizing them away.

## Verification

Minimum qualified verification depends on effect:

- documentation/config proposal: schema/path/internal consistency;
- GitHub write: exact repository identity, base ref, target path, expected prior SHA where applicable;
- test/compute request: verify the actual external result, not merely dispatch success;
- deploy/runtime mutation: verify target identity plus provider-specific success and resulting state.

`DISPATCH != PASS`.

## Handoff

`CURRENT_WORK.md` must answer:
- where Bob is now;
- what is actively being changed;
- what just completed;
- what is next;
- what is blocked or unresolved.
