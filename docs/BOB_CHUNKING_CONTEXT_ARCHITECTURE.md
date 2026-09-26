# Bob Chunking and Context Architecture

This document defines the canonical large-project cognition architecture for Bob.

The concrete module/cognition specialization is canonicalized in `docs/BOB_MODULE_COGNITION_ARCHITECTURE.md`.

It exists because ChatGPT conversations are bounded cognition surfaces. Bob must be able to drive projects far larger and longer-lived than any one model conversation can hold.

## Fundamental rule

> **No chat owns the project. Bob owns durable project state. Chats own bounded work.**

A ChatGPT thread is a replaceable cognition workspace, not the canonical memory of a project.

Bob must be able to discard a cognition thread, open a fresh one, reconstruct the relevant work context from durable project truth, and continue without requiring the old conversation transcript.

## Bob carries structure so cognition does not have to

One of Bob's primary large-project functions is to act as **externalized structural working memory** for ChatGPT cognition.

A single cognition thread should not have to simultaneously remember:

- the whole architecture;
- every domain and workstream;
- all dependency relationships;
- every shared contract;
- current status across the project;
- waiting conditions;
- historical decisions;
- verification state.

Bob carries that durable structure between cognition calls.

The canonical division is:

```text
Bob
→ stores the project/work graph
→ stores contracts, dependencies, status and provenance
→ keeps it durable and current
→ selects the relevant structural neighborhood
→ compiles it into bounded context

ChatGPT cognition
→ reasons deeply inside that bounded world
→ may recognize that the existing structure is wrong
→ proposes semantic restructuring when needed

Bob
→ persists the accepted/reconciled new structure
→ carries it forward for future cognition
```

This means **Bob owns carrying structural state; cognition owns the semantic reasoning used to create or revise it.**

The purpose is cognitive offloading. ChatGPT should spend its limited context and attention on the problem currently being solved rather than repeatedly reconstructing and remembering the entire project organization.

Bob Core must therefore avoid two opposite failures:

1. **chat-owned structure** — forcing one model conversation to remember the global project;
2. **dumb fixed structure** — hard-coding a task tree that cognition cannot revise when understanding changes.

The correct model is a durable Bob-maintained map whose semantic contents can be authored and reorganized through bounded cognition.

Structural maintenance itself may be a bounded cognition task. For example, Bob can compile an architecture-level packet for a dedicated planning/restructuring thread, receive a proposed graph change, validate/reconcile it, and then persist the result without requiring later implementation threads to replay that architectural reasoning.


## Design objective

Project size should scale primarily through **more well-bounded nodes and contracts**, not through larger prompts.

The desired topology is recursive:

```text
PROJECT
├─ DOMAIN
│  ├─ WORKSTREAM
│  │  ├─ WORK UNIT
│  │  └─ WORK UNIT
│  └─ WORKSTREAM
├─ DOMAIN
└─ SHARED CONTRACTS
```

The labels are semantic conveniences, not rigid database types. Any node may contain child nodes when useful.

The underlying model is a graph:

```text
nodes
+ parent/child structure
+ dependency edges
+ interface/contract edges
+ evidence/state references
+ cross-cutting workstreams
```

This permits a project to grow from tens to thousands of files without requiring a single cognition context to grow proportionally.

## Canonical node contract

Each durable project node should be compact and machine-readable enough for Bob to compile context from it.

Minimum conceptual fields:

```text
ID
PURPOSE
OWNS
DOES_NOT_OWN
INTERFACES
DEPENDENCIES
INVARIANTS
CURRENT_STATE
OPEN_WORK
VERIFICATION
LAST_VERIFIED
EVIDENCE_REFS
```

These fields describe the node's role and boundary, not an exhaustive history.

Node canon should stay concise. Large transcripts, raw logs and complete file bodies belong in referenced evidence/reality sources, not inside the node summary.

## Module-first semantic chunking

Bob should not divide work primarily by arbitrary line count, file count or transcript length.

For Bob-designed software, the default cognitive atom is a **module**: a bounded input -> responsibility -> output transformation connected to neighboring modules through explicit contracts/adapters.

Every Bob-designed module is subject to the canonical **15,000-token hard module cap** defined in `docs/BOB_MODULE_COGNITION_ARCHITECTURE.md`.

This cap is deterministic and lifecycle-wide, not merely a pre-implementation estimate. A module may not cross it as implementation grows.

If a proposed change would exceed the cap, Bob must reject that module shape and route a fresh architecture-cognition problem that reorganizes responsibilities/contracts until all affected modules are compliant. This is backend orchestration; the operator is involved only when the reorganization creates a genuine product/vision decision.

The surrounding compiled cognition packet retains a separate 20,000-token target and 25,000-token hard ceiling.


## Shared contracts

Large projects require canonical shared contracts that individual work units can depend on without loading the entire project.

Examples:

- API contracts;
- data schemas;
- security invariants;
- naming/identity rules;
- deployment contracts;
- event formats;
- compatibility constraints.

A work unit should receive the contracts it depends on, not every contract in the project.

Changing a shared contract is a cross-cutting change and must trigger impact analysis over dependent nodes.

## Context Compiler

The **Context Compiler** is the canonical mechanism that turns durable project state into a bounded cognition packet.

The compiler should answer:

> What is the smallest sufficient world this cognition thread needs in order to do this work correctly?

A compiled context packet should contain only the relevant subset of:

```text
workspace identity
work-node identity
human goal / current objective
scope boundary
relevant node summaries
shared contracts
dependency state
exact relevant files or bounded excerpts
current external/provider reality
known blockers
authority/effect constraints
verification requirements
exit criteria
freshness/provenance markers
relevant verified Knowledge Fabric items / failure signatures / source pointers
```

The compiler must prefer current canonical/reality state over old conversation text.

## Context compilation algorithm

Conceptually:

```text
1. identify or create the target work node
2. resolve its direct dependency/interface closure
3. include only contracts required by that closure
4. fetch fresh reality for facts that may have changed
5. select exact files/excerpts required for the task
6. retrieve only the relevant verified Knowledge Fabric patterns/failures/examples/decisions
7. include current blockers, authority and exit criteria
8. rank/deduplicate source material and fit the packet to a bounded cognition budget
9. send the packet to a fresh cognition thread
```

If the packet exceeds the hard cognition ceiling, Bob must fail closed and route a bounded architecture/context problem rather than silently dropping critical context. Separately, no individual Bob module may exceed its 15k hard cap.

## Bounded cognition packets

Every substantial cognition task should receive a bounded compiled context.

Bob should not dump an entire repository, entire project history, or all prior chats into a model "just in case."

Context should be:

- sufficient;
- relevant;
- current;
- provenance-aware;
- bounded.

The current engineering target is 20k tokens with a 25k hard ceiling for the whole compiled input world. These numbers may evolve from evidence; the bounded-context rule itself does not.

## Stateless cognition threads

The canonical large-project rule is:

> **One cognition question = one fresh ChatGPT conversation.**

A cognition thread is a disposable reasoning process, not durable state and not a resource Bob tries to extend.

A long-running Bob job therefore MUST NOT be implemented as a long-running ChatGPT conversation. A persistent campaign is decomposed into many short-lived cognition slices. Each slice receives the smallest sufficient compiled world, performs one bounded reasoning step, and exits after returning a durable result, request/effect, blocker, or continuation checkpoint.

Conceptually:

```text
persistent Bob campaign/work item
→ short fresh cognition slice
→ durable result/checkpoint
→ short fresh cognition slice
→ durable result/checkpoint
→ ...
→ deterministic verification / DONE
```

The campaign may live for hours or days while each individual ChatGPT conversation remains deliberately short. Increasing campaign duration therefore increases the number of bounded cognition slices, not the intended lifespan or transcript size of any one chat.

Anything required by the next question must be recompiled from Bob's durable canon/state/evidence. A fresh thread must never depend on having seen the previous transcript.

Therefore:

> **Anything required to continue the project later must leave the chat and become durable canon, state, evidence or a resumable work record.**

Conversation artifacts may remain for audit/debugging, but they do not outrank current repository/provider truth and are not the continuity mechanism.

## Work completion and distillation

When a work unit finishes, Bob should not merely keep the resulting conversation.

Bob should distill the useful result back into durable structures:

```text
implementation/effect
+ verified evidence
+ updated node state
+ updated contracts if needed
+ discovered follow-up work
+ reusable learning where appropriate
```

This is the write-back half of the Context Compiler architecture.

The loop is:

```text
durable project graph
→ compile bounded context
→ cognition
→ effects / verification
→ distill durable result
→ updated project graph
```

## Cross-cutting workstreams

Some changes legitimately span many chunks.

Examples:

- authentication redesign;
- database migration;
- new permissions model;
- framework upgrade;
- observability migration.

Bob should represent these as explicit **cross-cutting workstreams** rather than forcing one cognition thread to own all affected domains.

Example:

```text
AUTH_V2_MIGRATION
├─ auth node changes
├─ API contract changes
├─ frontend changes
├─ data migration
└─ integration verification
```

Each child may execute in a separate cognition thread with its own compiled context.

The cross-cutting parent owns coordination, dependency order and completion criteria.

## Fusion

When parallel or cross-cutting work must converge, Bob should create a bounded **Fusion** cognition task.

Fusion should receive:

- child results;
- changed contracts;
- conflicts;
- unresolved decisions;
- verification evidence;
- integration exit criteria.

Fusion should **not** automatically receive every child transcript.

Its purpose is to integrate durable outcomes, detect inconsistency and decide the next bounded work, not to replay all prior cognition.

## Parallel cognition

Bob may use multiple cognition threads where doing so materially improves quality or throughput.

Examples:

- implementation;
- independent review;
- architecture challenge;
- security review;
- UI/visual review;
- alternative prototype;
- fusion.

Parallelism is subordinate to bounded context and explicit contracts. More threads are not automatically better.

## Event-driven resumption

A work node may enter a durable waiting state:

```text
WAITING_FOR:
- CI completion
- provider job
- deployment health
- data arrival
- human approval
- scheduled external event
```

When the dependency resolves, Bob should compile a fresh context packet and ask the next bounded question in a new cognition thread.

## Canonical status model

At node/workstream level, Bob should be able to distinguish at least:

```text
PLANNED
READY
WORKING
WAITING
NEEDS_HUMAN
BLOCKED
VERIFYING
DONE
SUPERSEDED
```

These are internal states. The operator-facing UI should compress them into simple natural language unless more detail is requested.

## Project graph vs. source tree

The project graph is semantic, not a mirror of folders.

One node may own several folders/files. One folder may contain implementation belonging to multiple semantic nodes if unavoidable.

Bob should prefer architecture that makes semantic ownership clear, because clear module boundaries make bounded cognition easier and safer.

## Impact analysis

Before changing a durable contract or invariant, Bob should traverse known dependents and create explicit affected work where needed.

A local cognition task may modify only its authorized scope, but Bob's coordinator must understand when that local change invalidates assumptions elsewhere.

## Freshness and provenance

Compiled context must distinguish:

- durable canon;
- current state;
- observed evidence;
- historical evidence;
- proposal;
- inferred/uncertain information.

Fresh external state should outrank stale summaries.

Every important compiled fact should be traceable to its durable source or current read where practical.

## Recursive learning of chunking itself

Chunking strategy is itself an improvable Bob capability.

Over many projects Bob may learn, through measured outcomes, that certain decompositions, reviewer patterns or contract boundaries produce less rework and better verification.

Bob may therefore improve:

- project archetype templates;
- decomposition heuristics;
- context selection;
- review routing;
- fusion strategy;
- work-size estimation;
- dependency detection.

This improvement should be evidence-driven.

Bob must not blindly preserve a chunking pattern merely because it was used before.

## Reusable knowledge without context leakage

Reusable knowledge is a first-class Bob subsystem defined in `docs/BOB_KNOWLEDGE_FABRIC_ARCHITECTURE.md`.

Bob may distill verified lessons into patterns, playbooks, failure signatures, examples, tests and reference implementations when they are genuinely reusable.

Example:

```text
rehearsal migration
→ immutable before-state
→ isolated run
→ read-back
→ cutover gate
→ rollback receipt
```

The Knowledge Fabric may grow very large because most items consume **zero cognition tokens until selected**. The Context Compiler should retrieve only the smallest relevant set and may prefer source pointers over injected implementation bodies when fresh cognition can inspect GitHub directly.

Knowledge maturity is evidence-driven:

```text
OBSERVATION
→ CANDIDATE_LESSON
→ VERIFIED_PATTERN
→ CANONICAL_PRACTICE
```

Model output alone is never sufficient to promote reusable guidance.

Reusable knowledge must not leak project-private data or silently grant cross-workspace authority. Knowledge is cognition support, never permission.

## Recursive self-hosting consequence

Bob itself should use this architecture.

As Bob grows, no single Bob-development chat should own the whole Bob codebase.

Bob should decompose its own development into semantic nodes, compile context for each cognition task, integrate through contracts/Fusion and use the resulting system to improve the Context Compiler itself.

This creates a bounded recursive loop:

```text
better chunking/context compilation
→ larger and harder projects become tractable
→ more real development evidence
→ better decomposition/orchestration methods
→ better chunking/context compilation
```

Again, capability may compound; authority does not.

## Six non-negotiable rules

> **1. No chat owns the project. Bob owns durable project state.**

> **2. Every substantial cognition task receives a bounded compiled context rather than the whole project.**

> **3. Every module/chunk has explicit contracts/boundaries to the rest of the system, and cross-cutting changes are coordinated explicitly.**

> **4. One cognition question uses one fresh ChatGPT conversation; Bob carries continuity between questions.**

> **5. Long-running work scales through many short-lived cognition slices with durable checkpoints/results, never by stretching one ChatGPT conversation across the campaign.**

> **6. Fresh cognition re-grounds in source truth when needed and checks material contract/module/product impact before completion; a separate review stage is optional, not mandatory.**

These are foundational Bob architecture, not optional optimizations to add only after context limits become painful.
