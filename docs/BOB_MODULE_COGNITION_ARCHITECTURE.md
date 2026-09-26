# Bob Module and Stateless Cognition Architecture

This document defines Bob's canonical software-development unit and cognition cadence for large projects.

It specializes the broader rules in docs/BOB_CHUNKING_CONTEXT_ARCHITECTURE.md.

## Core model

> **A large project is a graph of cognitively bounded modules connected by explicit contracts/adapters.**

The simplest form is a chain:

~~~text
data X
→ Module A
→ data Y
→ Module B
→ data Z
→ Module C
→ ...
~~~

Real systems may branch or join, but the rule is the same:

~~~text
input contract
→ bounded responsibility
→ output contract
~~~

Bob carries the global graph. No ChatGPT conversation has to carry the whole project.

## Module = cognitive atom

A Bob module is defined **before implementation** as an independently understandable transformation boundary.

A module must state:

~~~text
ID
PURPOSE
INPUT
OUTPUT
INPUT_CONTRACT
OUTPUT_CONTRACT
FAILURE_CONTRACT
INVARIANTS
ADAPTERS / INTERFACES
VERIFICATION
~~~

Its semantic responsibility should remain stable. New unrelated responsibility should normally become another module rather than silently enlarging the existing one.

## Absolute module-size invariant

A Bob module has an absolute hard cap:

~~~text
MODULE_HARD_CAP = 15,000 tokens
~~~

This is not an alert threshold, recommendation or operator decision. It is a backend invariant known to both Bob and ChatGPT from the beginning.

A valid module must remain at or below 15k throughout its lifecycle, including when it is nearly complete. This preserves enough surrounding cognition space for a fresh ChatGPT conversation to understand, debug, modify and finish the module together with contracts, neighboring summaries and current evidence.

Bob enforces the numerical boundary deterministically. ChatGPT owns the semantic response when a proposed change would violate it.

Canonical backend behavior:

~~~text
proposed module/change
→ deterministic module token count

<= 15k
→ continue

> 15k
→ proposed module/change is invalid
→ fresh architecture cognition receives the module/flow/contracts + hard-cap invariant
→ cognition proposes a compliant reorganization
→ Bob persists/rechecks the resulting module graph
→ continue only when every affected module is <= 15k
~~~

This normally happens without operator interruption. Bob must involve the operator only if the required reorganization creates a genuine operator-owned product/vision/end-goal tradeoff, not merely because a module crossed the size boundary.

Bob should therefore never intentionally create a module that is expected to need an operator conversation merely to stay within the cap.

### Design-time effect

The 15k hard cap is supplied to architecture cognition **before module boundaries are chosen**.

ChatGPT should design the initial module graph with the expectation that each module must still be <=15k when substantially/fully implemented, not merely while the module is an empty scaffold.

This means the cap actively shapes architecture from the beginning:

~~~text
product flow + 15k invariant
→ fresh architecture cognition
→ choose bounded responsibilities
→ define module contracts/adapters
→ implement
~~~

A module plan that is reasonably expected to exceed 15k at maturity is an invalid design even if its initial scaffold is tiny. Architecture cognition should instead choose narrower responsibilities or additional neighboring modules up front.

Bob does not need to make that semantic forecast. Bob carries the invariant and later measures actual module size deterministically; ChatGPT performs the semantic module design with the invariant already in context.

Legacy/external systems may already contain oversized components; those are migration/refactoring problems, but Bob-designed target modules must satisfy the same 15k invariant before being accepted as compliant.

## Initial cognition envelope

The initial canonical engineering defaults are:

~~~text
MODULE_HARD_CAP = 15,000 tokens
COMPILED_CONTEXT_TARGET = 20,000 tokens
COMPILED_CONTEXT_HARD_CEILING = 25,000 tokens
~~~

The **15k module cap** applies to the module itself as canonically measured by Bob's module manifest/token-counting contract. It is a hard architectural invariant.

The **20k target / 25k hard ceiling** apply to the whole compiled cognition input world, which may include:

- mission/product constraints;
- the module;
- direct contract neighborhood;
- current reality/evidence;
- the problem/question itself.

20k is a preferred cognition target and 25k is the absolute compiled-context ceiling. The module cap leaves deliberate room between 15k and the cognition envelope for surrounding context and difficult end-stage work.

The cognition-envelope numbers may later improve from measured evidence. The 15k module cap remains canonical until explicitly changed in Bob's architecture; Bob may not tune it upward on its own.

The runtime defaults live in bob/cognition_policy.py.

### V1 measurement contract

The first executable module-size contract is versioned as `BOB_TOKEN_ESTIMATE_V1`.

V1 measures each manifest-owned UTF-8 text file as:

~~~text
ceil(UTF-8 bytes / 3)
~~~

and sums the result across the module's declared source, test and contract paths.

This is deliberately deterministic and conservative for ordinary source/code, but it is **not** presented as the exact tokenizer used by ChatGPT. The measurement schema is versioned so a later exact or better-calibrated tokenizer can replace it without silently changing historical footprint receipts.

The hard architectural rule is therefore: **a module must remain <=15,000 tokens under the active canonical measurement contract.**

## ChatGPT project-memory independence

Fresh cognition means correctness must be independent of prior ChatGPT chat history **and** of any implicit project-memory recall.

Bob may currently use a dedicated ChatGPT Project for account/UI isolation and project instructions, but project-level memory is never authoritative project state.

Every cognition request must be sufficiently self-contained to remain correct if no prior project chat is recalled.

If the ChatGPT product/runtime later provides a practical way to retain Bob's project instructions while disabling cross-chat memory influence, the stateless cognition path should prefer that configuration.

## Immediate contract neighborhood

"Previous/next module" is shorthand for a graph concept.

A module cognition packet receives:

- the current module;
- direct producers it consumes from, summarized;
- direct consumers that depend on its output, summarized;
- exact relevant contracts/adapters;
- relevant global invariants.

It does **not** receive the entire project graph unless the question itself is an architecture-level question.

## Stateless cognition

The canonical cognition rule is:

> **One cognition question = one fresh ChatGPT conversation.**

A ChatGPT conversation is a disposable reasoning process.

It is not:

- project memory;
- workstream memory;
- module memory;
- a place Bob tries to preserve merely because it already exists.

Bob holds durable state and compiles every new cognition request from that state.

Conceptually:

~~~text
durable Bob state
→ compile bounded problem world
→ fresh ChatGPT conversation
→ answer
→ verify / interpret / persist
→ next bounded problem
→ fresh ChatGPT conversation
~~~

Fresh cognition is the default. Conversation reuse is not part of the canonical large-project architecture.

### Long-running campaign cadence

A long Bob work session is persistent at the campaign/work-item layer, not at the ChatGPT-conversation layer.

Canonical runtime shape:

~~~text
hours-long campaign
→ many short fresh cognition slices
→ durable continuation/result after every slice
→ deterministic effects and verification between slices as needed
→ resume from Bob-owned state, never from chat-memory dependence
~~~

Bob should deliberately prefer relatively short individual cognition conversations. A slice should solve the next bounded semantic problem and then terminate; later cognition receives a newly compiled context from durable state. If more work remains, Bob creates another fresh slice rather than extending the existing conversation merely to preserve continuity.

There is no canonical fixed slice count per campaign. A four/eight-hour job may require dozens or more fresh conversations. The invariant is that continuity, progress, decisions, evidence, effect lineage and resumability live outside the chat.

This turns ChatGPT conversations into short-lived cognition workers while Bob remains the persistent process coordinator and memory substrate.

## Tool/reality continuation

A cognition answer may discover that more reality is required.

Example:

~~~text
Question 1:
"What is causing this failure?"
→ answer: need files A and B plus runtime result C

Bob obtains A/B/C deterministically.

Question 2:
"Given this original problem plus A/B/C, what is the cause?"
→ fresh conversation
→ answer
~~~

Bob must recompile the relevant problem/context for the next request. The new conversation must not depend on seeing the old transcript.

Bob now has a first executable stateless module path: `BOB_MODULE_GRAPH_V1` + `BOB_COMPILED_CONTEXT_V1` feed `POST /bob/module-turn`. On this path, every Bob-owned READ or approved effect result is carried forward as durable continuation data, the full bounded module problem is recompiled, and the next call uses a fresh `/cognition` conversation. The legacy ordinary `/bob/turn` path remains stateful until module selection/context compilation becomes the default orchestration path.

## Source-grounded cognition and impact checking

A fresh ChatGPT cognition request is not limited to Bob's summaries.

Because Bob cognition runs through the operator's connected ChatGPT account, cognition may re-ground directly in the selected GitHub repository whenever implementation truth matters.

Canonical responsibility split:

~~~text
Bob
→ carries mission, module graph, contracts, status, limits and source pointers
→ selects the current bounded problem

fresh ChatGPT cognition
→ receives the bounded problem world
→ inspects connected GitHub source/history/tests when semantic correctness requires it
→ solves the technical problem
→ checks whether the solution affects neighboring modules/contracts/product intent
→ returns the solution or BOB.ASK only when a genuine operator decision is required

Bob
→ deterministically verifies/persists effects and durable state
→ selects the next bounded problem
~~~

This direct source re-grounding is specifically intended to prevent summary-of-summary drift.

Bob summaries are routing/compression artifacts. They are not substitutes for repository truth when the code itself can answer the question.

A cognition request should receive useful source pointers such as:

~~~text
repository identity
branch / commit
current module paths
relevant contract paths
neighbor module paths
test/evidence paths
decision/canon references
~~~

ChatGPT may expand from those pointers through the connected GitHub integration as needed.

The current V1 substrate is repo-native:

~~~text
.bob/module_graph.json     BOB_MODULE_GRAPH_V1
→ deterministic footprint measurement
→ ContextCompiler          BOB_COMPILED_CONTEXT_V1
→ POST /bob/module-turn
→ fresh /cognition request
~~~

`POST /bob/module-graph` exposes measured module status for inspection. The graph may initially have `coverage=PARTIAL`; partial coverage is explicit and must not be misrepresented as a complete project graph.

For normal `MODULE_WORK`, GitHub file effects are constrained to paths owned by the target module manifest and to the selected working ref. Creating/switching branches is outside a module turn in V1. `ARCHITECTURE_REPAIR` deliberately has broader path scope because a valid split may require creating new files and rewriting the module graph; workspace authority, explicit approval and read-back verification still apply.

### Optional review/meta cognition

Bob does **not** require a persistent or mandatory separate meta-cognition stage.

Impact analysis belongs inside ordinary source-grounded cognition by default.

A separate fresh review/meta cognition request remains available when it materially improves reliability—for example for a broad cross-cutting change, architecture dispute, security review or difficult integration failure—but it is an optional cognition pattern, not a permanent system role.

If source-grounded cognition discovers a genuine operator-owned product/vision/end-goal tradeoff, it should surface that through Bob's normal human-decision boundary rather than silently deciding it.

## Product-vision bootstrap

Before large autonomous implementation, the operator and Bob establish enough durable direction for source-grounded cognition to recognize material product/system implications.

The bootstrap should capture, at useful resolution:

- what is being built and for whom;
- desired end state;
- important product qualities;
- success criteria;
- hard constraints;
- major stages/flows;
- operator-owned tradeoffs;
- known "revisit if" conditions where appropriate.

Bob should help derive this through ordinary conversation. The operator should not have to author a formal architecture specification manually.

The structure may evolve as implementation reveals reality.

## Bob as structural working memory

Bob stores and maintains:

- mission/product vision;
- module graph;
- contracts/adapters;
- module summaries;
- current statuses;
- dependencies;
- decisions and reasons;
- verification/evidence;
- open operator decisions.

ChatGPT receives only the projection needed for the current question.

Therefore:

> **Bob remembers the structure. ChatGPT thinks with the relevant slice.**

## Knowledge-assisted module cognition

The module graph tells Bob where the problem lives. The Knowledge Fabric tells Bob which prior verified experience may help solve it.

For a bounded module problem, the Context Compiler may retrieve a small number of relevant:

- verified patterns;
- failure signatures;
- playbooks;
- decisions;
- reference implementations;
- source/evidence pointers;
- known cognition failure-mode warnings.

This retrieval is selective and budgeted inside the existing 20k target / 25k hard ceiling. A larger durable knowledge base must not enlarge the prompt by default.

Fresh cognition should use current GitHub/provider/runtime reality to validate fit. A retrieved knowledge item is guidance with provenance, not a substitute for source truth and never an authority grant.

The detailed contract is `docs/BOB_KNOWLEDGE_FABRIC_ARCHITECTURE.md`.

## Hierarchical compression

For large systems Bob should maintain several resolution levels.

Conceptually:

~~~text
MISSION / PRODUCT
↓
SYSTEM / FLOWS
↓
MODULES / CONTRACTS
↓
IMPLEMENTATION / EVIDENCE
~~~

Changes are distilled upward so fresh cognition can see the product/system state without loading every module implementation, while retaining source pointers for direct GitHub re-grounding.

Summaries accelerate cognition but never replace source truth. Material decisions should re-ground from canonical contracts, repository/runtime reality and verification evidence when needed.

## Adapters and contracts

Module boundaries should be explicit and mechanically testable where practical.

A module may change internally without forcing global cognition when it still satisfies its contract.

Adapters may translate between independently versioned contracts:

~~~text
Module A
→ A_OUT_V1
→ adapter
→ B_IN_V2
→ Module B
~~~

Boundary stability is valuable because it allows Bob to improve or replace one module using bounded cognition.

## Contract testing

Each module should have verification shaped around its transformation promise.

Conceptually:

~~~text
given valid X
→ Module
→ must produce valid Y

given invalid/edge X
→ Module
→ must satisfy failure contract
~~~

Integration verification then checks adjacent contracts/adapters and selected end-to-end flows.

## Growth rule

For Bob-designed systems, scale should normally come from:

- more modules;
- better contracts;
- better composition;
- better orchestration;

not from modules accumulating unbounded responsibility.

> **Bob scales cognition through composability, not longer chats.**

## Self-development use

Bob should use the same module/stateless architecture for recursive self-development.

Background self-development selects one bounded module/work problem, compiles a fresh cognition packet, experiments only in isolated authorized work state, verifies the result, and distills reusable learning. Interactive work has priority and may pre-empt the background lane at a safe checkpoint.

Self-development must not use module repair or fresh cognition as a route to expand authority or promote itself into canonical state. The runtime/safety contract is `docs/BOB_RECURSIVE_SELF_IMPROVEMENT_ARCHITECTURE.md`.

## Recursive improvement

Bob should measure whether this architecture actually improves outcomes.

Useful signals may include:

- first-pass implementation success;
- rework rate;
- missed constraints;
- contract regressions;
- source-grounding/impact issues missed or caught;
- context size;
- verification failures;
- operator interruptions;
- time/cognition cost.

Those observations may improve:

- the 20k/25k cognition envelope;
- module archetypes;
- contract design;
- neighborhood selection;
- source-pointer selection;
- optional review/meta-cognition routing;
- adapter patterns.

Hard invariants such as the 15k module cap, fresh cognition, durable state and operator authority remain separate from learnable tuning parameters. Bob may collect evidence suggesting a future cap change, but only explicit canon/operator authority may change the cap.

## Canonical summary

> **A large Bob project is a graph of bounded transformation modules.**
>
> **Every Bob module is absolutely capped at 15k tokens throughout its lifecycle.**
>
> **Compiled cognition envelope: 20k target, 25k hard ceiling.**
>
> **If a change would push a module above 15k, Bob + fresh architecture cognition reorganize it in the backend; the operator is involved only for genuine product/vision tradeoffs.**
>
> **One cognition question uses one fresh ChatGPT conversation.**
>
> **Bob carries all continuity and structure between questions.**
>
> **Each fresh cognition request may re-ground directly in GitHub and must consider material local/system impact before completion; separate review cognition is optional, not mandatory.**
