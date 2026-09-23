# Bob Chunking and Context Architecture

This document defines the canonical large-project cognition architecture for Bob.

It exists because ChatGPT conversations are bounded cognition surfaces. Bob must be able to drive projects far larger and longer-lived than any one model conversation can hold.

## Fundamental rule

> **No chat owns the project. Bob owns durable project state. Chats own bounded work.**

A ChatGPT thread is a replaceable cognition workspace, not the canonical memory of a project.

Bob must be able to discard a cognition thread, open a fresh one, reconstruct the relevant work context from durable project truth, and continue without requiring the old conversation transcript.

## Cognition owns semantic structure

The project graph is **not** a rigid deterministic decomposition imposed by Bob Core.

Semantic cognition owns decisions such as:

- what the meaningful domains are;
- where workstream boundaries belong;
- which concepts should be coupled or separated;
- which shared contracts exist;
- when a node should split, merge, be superseded or be reorganized;
- which dependencies matter;
- which cross-cutting workstream best represents a change;
- when the existing project structure itself has become wrong.

Bob Core owns the mechanics around that structure:

- durable persistence;
- schema validation;
- stable identities;
- provenance;
- freshness;
- bounded context compilation;
- graph traversal;
- authority boundaries;
- deterministic effects;
- verification and read-back.

The canonical division is therefore:

```text
ChatGPT cognition
→ understands the project
→ proposes/maintains semantic structure

Bob
→ persists that structure
→ validates its mechanical integrity
→ compiles bounded context from it
→ verifies reality against it
```

Bob must not confuse deterministic durability with semantic ownership.

A fixed orchestration engine that permanently decides the project's decomposition would recreate one of the limitations Bob is intended to overcome.

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

## Semantic chunking, not arbitrary size chunking

Bob should not divide work primarily by line count, file count or token count.

A good chunk has:

- one coherent responsibility;
- a clear ownership boundary;
- explicit interfaces to neighboring chunks;
- bounded dependencies;
- a concrete outcome;
- verifiable exit criteria.

Context/token limits are constraints on compilation, not the definition of architecture.

If a work unit cannot be described with a stable responsibility and boundary, Bob should consider whether the underlying software/project structure is too entangled.

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
6. include current blockers, authority and exit criteria
7. fit the packet to a bounded cognition budget
8. send the packet to a fresh or existing cognition thread
```

If the packet is still too large, Bob should decompose the work node further rather than silently dropping critical context.

## Bounded cognition packets

Every substantial cognition task should receive a bounded compiled context.

Bob should not dump an entire repository, entire project history, or all prior chats into a model "just in case."

Context should be:

- sufficient;
- relevant;
- current;
- provenance-aware;
- bounded.

The exact budget may evolve with future models. The architectural rule does not depend on a fixed token number.

## Disposable cognition threads

A cognition thread may be useful, but it is not durable state.

Bob should assume any thread can eventually be lost because of:

- context length;
- model/runtime changes;
- browser/session failure;
- deliberate replacement;
- project evolution.

Therefore:

> **Anything required to continue the project later must leave the chat and become durable canon, state, evidence or a resumable work record.**

Conversation summaries may assist transition, but they do not outrank current repository/provider truth.

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

When the dependency resolves, Bob should compile a fresh context packet and resume the correct work node.

The old cognition thread may be reused when still healthy, but correctness must not depend on it.

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

Bob may distill cross-project lessons into abstract reusable playbooks when they are genuinely generic.

Example:

```text
rehearsal migration
→ immutable before-state
→ isolated run
→ read-back
→ cutover gate
→ rollback receipt
```

Reusable knowledge must not leak project-private data or silently grant cross-workspace authority.

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

## Three non-negotiable rules

> **1. No chat owns the project. Bob owns durable project state.**

> **2. Every substantial cognition task receives a bounded compiled context rather than the whole project.**

> **3. Every chunk has explicit contracts/boundaries to the rest of the system, and cross-cutting changes are coordinated explicitly.**

These are foundational Bob architecture, not optional optimizations to add only after context limits become painful.
