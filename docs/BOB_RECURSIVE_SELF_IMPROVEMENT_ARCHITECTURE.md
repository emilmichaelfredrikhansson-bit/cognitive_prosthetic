# Bob Recursive Self-Improvement Architecture

This document defines Bob's canonical recursive self-improvement model.

It is a capability-compounding architecture, not an authority-compounding architecture. It complements `PRODUCT_PRINCIPLES.md`, `PROJECT_CONSTITUTION.md`, `docs/BOB_MODULE_COGNITION_ARCHITECTURE.md` and `docs/BOB_KNOWLEDGE_FABRIC_ARCHITECTURE.md`.

## Objective

The purpose of recursive self-improvement is not merely to make Bob write more Bob code.

The objective is:

> **Every useful cognition cycle should make future relevant cognition better prepared, cheaper, safer or more reliable.**

A successful cycle converts transient ChatGPT cognition into durable, verified capability.

Conceptually:

```text
Bob Vn
→ observes current Bob reality
→ selects one bounded capability problem
→ compiles the best known context
→ fresh ChatGPT cognition
→ bounded implementation / experiment
→ deterministic verification
→ reflection and lesson extraction
→ durable knowledge / tests / patterns / structure
→ qualified candidate
→ Bob Vn+1 starts from a higher floor
```

The compounding target is the environment around cognition: structure, context selection, tests, patterns, tools, evidence and reusable knowledge. Bob does not require model-weight training to compound.

## Canonical recursive loop

The default self-development loop is:

```text
OBSERVE
→ DIAGNOSE
→ SELECT
→ COMPILE
→ COGNITION
→ BUILD / EXPERIMENT
→ VERIFY
→ REFLECT
→ DISTILL
→ CHECKPOINT / CANDIDATE
→ NEXT
```

Each stage has a distinct purpose.

- **OBSERVE** — read current GitHub/runtime/test/module/knowledge reality.
- **DIAGNOSE** — identify concrete friction, failure, missing capability or measurable opportunity.
- **SELECT** — choose one bounded work unit with a clear expected benefit.
- **COMPILE** — assemble the smallest sufficient cognition world, including relevant knowledge and known failure modes.
- **COGNITION** — use one fresh ChatGPT conversation for the bounded question.
- **BUILD / EXPERIMENT** — make a reversible candidate change inside the authorized sandbox.
- **VERIFY** — run deterministic tests/read-back/evals appropriate to the change.
- **REFLECT** — compare expected versus observed outcome.
- **DISTILL** — persist reusable lessons, failure signatures, patterns, tests, source pointers or reference implementations.
- **CHECKPOINT / CANDIDATE** — preserve a known-good state and mark qualified work for human/canonical promotion where required.
- **NEXT** — choose the next bounded improvement from durable state, not from transcript momentum.

Activity is not success. A loop that generates many changes but no durable validated capability improvement is failing.

## Compounding performance target

Bob should optimize toward better outcomes with less repeated cognition and less operator effort.

A useful directional objective is:

```text
solution quality
────────────────────────────────────────────
tokens × cognition calls × human effort × failure rate
```

This is not a literal single production score. It expresses the desired direction:

- better first-pass solutions;
- less rediscovery;
- fewer known mistakes;
- smaller/better context packets;
- fewer unnecessary cognition calls;
- fewer operator interruptions;
- stronger deterministic verification;
- lower rollback/rework rate.

## Daytime background operation

Recursive self-development is intended to run quietly while the operator's computer is awake.

It does **not** require the computer to remain online overnight. Durable state must make shutdown/restart ordinary:

```text
PC starts
→ Bob reconstructs durable self-development state
→ background loop resumes

PC shuts down
→ no special continuity loss

next start
→ Bob re-grounds in GitHub/runtime/knowledge/evidence
→ continues from durable state
```

A long-running chat is never the continuity mechanism.

### Background must stay in the background

Unattended self-development must not steal focus from ordinary operator use.

In Local Companion mode the background lane should:

- keep its ChatGPT cognition surface in the background;
- never call foreground/show-UI behavior merely because a cognition cycle starts;
- avoid opening disruptive visible windows when the same work can happen in the managed background browser context;
- emit durable logs/receipts rather than continuous operator-facing chatter;
- surface only a concise digest, a real blocker, or an approval/decision that genuinely requires the operator.

The operator should be able to use ChatGPT, the browser and the rest of the computer normally while background self-development runs.

Resource contention should be treated like any other scheduling constraint: interactive work gets priority and background work yields or pauses at a safe checkpoint.

## Two execution lanes

Bob should separate operator-directed work from recursive background work.

### Interactive lane

High priority.

Used when the operator is actively working with Bob.

The interactive lane may pre-empt background cognition at the next safe checkpoint.

### Self-development lane

Low priority and normally invisible.

Used for bounded recursive Bob improvement while spare local/provider capacity is available.

The operator should normally see the results, not continuous agent chatter.

Canonical rule:

> **Interactive work always wins.**

## Isolation for parallel work

Interactive and self-development work must not share an unsafe mutable checkout.

The preferred model is:

```text
canonical / interactive checkout
→ ordinary operator work

separate self-development worktree
→ dedicated selfdev branch
→ reversible experimental commits
```

The self-development lane should use:

- a dedicated Git worktree or equivalent isolated checkout;
- a dedicated self-development branch/ref;
- explicit base/head provenance;
- deterministic checkpoints;
- module/work-node leases;
- conflict detection before integration.

## Module/work leases

One semantic work item should have one active mutating executor.

If the interactive lane acquires a module/work-node lease, the self-development lane must not mutate that scope until the lease is released or explicitly handed off.

A background worker encountering an interactive lease should select other work or wait.

Leases coordinate mutation; they do not create authority.

## Promotion boundary

Self-development may autonomously explore, edit, test, commit and discard work inside its authorized sandbox.

Promotion into canonical Bob state is a separate effect.

By default unattended self-development may:

- read Bob reality;
- create/recreate its isolated worktree;
- modify files on its dedicated branch within granted scope;
- run bounded local tests/evals;
- commit checkpoints/candidates;
- revert/discard failed experiments;
- produce diffs, receipts and candidate summaries.

By default it may **not**:

- merge into a protected/canonical branch;
- force-push a protected/canonical branch;
- delete the repository;
- delete protected branches;
- change repository administration/rulesets/branch protection;
- change secrets or credential policy;
- expand its own provider permissions;
- deploy production;
- mutate production data;
- incur material spend outside separately granted authority.

Opening a PR may be allowed only when the workspace policy explicitly grants that effect class.

A new Bob version cannot promote itself merely by declaring itself better.

## Safety objective

The unattended safety acceptance test is stronger than "the model is likely to behave":

> **Bob should be able to work unattended all day while remaining incapable of destroying the canonical project, even if every cognition call makes the worst plausible decision.**

This requires mechanical boundaries below cognition.

## Defense in depth

Self-development effects should pass through independent layers:

```text
model proposal
↓
Bob protocol
↓
semantic effect allowlist
↓
workspace identity
↓
module/work scope + lease
↓
branch/worktree restriction
↓
candidate hash / stale-state check
↓
credential permission boundary
↓
provider branch/ruleset protection
↓
checkpoint + deterministic verification
↓
promotion gate
```

The model should never receive broad provider credentials directly.

A dangerous proposal should fail because the required capability is absent, not because a language model happened to decide against using it.

## Credential design

Self-development credentials should be least-privilege and structurally unable to perform catastrophic administration.

Prefer separate credentials or app installations whose provider-side permissions exclude:

- repository administration;
- repository deletion;
- ruleset/branch-protection mutation;
- secrets administration;
- protected-branch force push;
- production deploy/mutation unless specifically required.

Bob's software authority checks are one layer; provider-side permission denial is another independent layer.

## Destructive effects

Destructive operations require stronger treatment than ordinary edits.

Repository deletion, broad recursive file deletion, protected-branch deletion, destructive production mutation and equivalent effects should not be present in the normal self-development capability surface.

If a future legitimate workflow needs a destructive class, it must be introduced explicitly with its own authority, preview, blast-radius analysis, rollback story and human approval contract.

## Checkpoints and rollback

Every bounded self-development batch should begin from a known Git identity and end with evidence.

Before material experimentation:

- record base commit/ref;
- ensure the worktree is isolated;
- ensure expected module/work leases;
- establish a reversible checkpoint.

After the batch:

- inspect diff;
- run relevant tests/evals;
- remeasure module/context invariants;
- read back resulting Git state;
- compare expected versus actual outcome.

Failed or ambiguous experiments should be reverted/discarded rather than accumulated into the next loop.

## Recursive architecture repair

Bob's own 15k module cap is a first-class self-improvement signal.

An oversized Bob module is not merely a warning. It is an architecture problem for a fresh bounded cognition cycle.

The self-development loop may therefore use Bob itself to:

```text
detect >15k module
→ compile architecture-repair context
→ fresh ChatGPT architecture cognition
→ implement split on selfdev branch
→ remeasure all affected modules
→ verify contracts/tests
→ produce qualified candidate
```

The operator is interrupted only if the repair requires a genuine product/vision/end-goal or authority decision.

## Reflection and distillation

Every successful or failed cycle should ask:

- What changed?
- What was the real cause?
- What evidence supports the conclusion?
- Was the lesson specific or reusable?
- Did a known pattern help?
- Did a known pattern fail?
- Is there a new failure signature?
- Should a test, invariant, skill, template or reference implementation be persisted?
- Did the Context Compiler provide too much, too little or the wrong context?

The output of reflection feeds the Knowledge Fabric rather than a permanent chat transcript.

## No authority recursion

Recursive capability improvement and recursive authority expansion are categorically different.

Bob may improve:

- context compilation;
- decomposition;
- testing;
- diagnosis;
- provider integration;
- recovery;
- UI;
- reference libraries;
- verification;
- self-development efficiency.

Bob may not autonomously improve itself by weakening or bypassing:

- root-of-trust;
- approval requirements;
- effect-class boundaries;
- workspace isolation;
- credential boundaries;
- provider protections;
- rollback requirements.

Authority changes remain operator/canon decisions.

## Operator experience

Background self-development should be quiet by default.

The useful interaction is:

```text
operator: "What did Bob improve today?"

Bob:
- what was attempted;
- what was kept;
- what was discarded;
- what is verified;
- what candidates need approval/promotion;
- what was learned.
```

Do not force the operator to supervise every cognition call.

## Canonical success condition

Recursive self-improvement is successful when:

1. future cognition begins from a measurably higher capability/knowledge floor;
2. the same class of solved problem increasingly does not require rediscovery;
3. context becomes more selective rather than simply larger;
4. operator intervention decreases without authority silently increasing;
5. failed experiments remain bounded and reversible;
6. canonical project destruction remains mechanically unavailable to unattended cognition.

The recursive loop and the Knowledge Fabric are coupled:

> **Self-improvement produces verified reusable knowledge; reusable knowledge improves future self-improvement.**
