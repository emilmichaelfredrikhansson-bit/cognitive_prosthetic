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

## Pre-implementation cognition-fit gate

Bob must not intentionally create a new module that is already too large for one fresh cognition request to understand with its relevant neighborhood.

Before implementation begins, Bob must be able to compile:

- the current module in sufficient detail;
- summarized direct producer/consumer modules;
- exact relevant input/output contracts;
- relevant shared invariants;
- a compact mission/product slice;
- the current problem/question;

inside the canonical cognition envelope.

If that design does not fit, **module design is not ready for implementation**.

The normal response is to return to architecture/flow design before code is written. Bob should not knowingly build a cognitively oversized module and rely on a later emergency split.

Legacy/external systems may already contain oversized components; those are migration/refactoring problems, not the target Bob design pattern.

## Initial cognition envelope

The initial canonical engineering defaults are:

~~~text
COMPILED_CONTEXT_TARGET = 20,000 tokens
COMPILED_CONTEXT_HARD_CEILING = 25,000 tokens
~~~

These limits apply to the **whole compiled input world**, not only source code.

That includes the relevant combination of:

- mission/product constraints;
- module implementation/context;
- direct contract neighborhood;
- current reality/evidence;
- the problem/question itself.

The target exists to preserve cognitive headroom. Bob should prefer staying at or below 20k rather than packing the context to the technical maximum.

20k/25k are initial learnable engineering parameters, not claims about an eternal model limit. Bob may later improve them from measured evidence, but a running policy must never silently exceed its configured hard ceiling.

The runtime defaults live in bob/cognition_policy.py.

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

This is why the current V1 stateful READ/RESULT loop cannot simply be switched to fresh chats without the Context Compiler. The dedicated fresh /cognition bridge primitive exists now, while full orchestration is gated on durable compiled continuation.

## Technical answer + consequence answer

A technical solution is not globally complete until Bob has evaluated what it means for the project.

Canonical pattern:

~~~text
TECHNICAL QUESTION
problem + module context
→ fresh cognition
→ technical answer

CONSEQUENCE QUESTION
technical answer + relevant mission/system/decision context
→ fresh cognition
→ NONE / STRUCTURAL / OPERATOR
~~~

The consequence pass asks whether the new technical reality changes:

- feasibility;
- architecture;
- module contracts;
- sequence/plan;
- product behavior;
- cost/latency/quality;
- safety/risk;
- scope;
- an operator-owned tradeoff.

Suggested classifications:

~~~text
NONE
No material global consequence. Continue.

STRUCTURAL
The durable graph/plan/contracts should change,
but the change remains inside already established operator intent/authority.

OPERATOR
A product/vision/end-goal/tradeoff decision belongs to the operator.
Bob surfaces it in ordinary language before proceeding past that decision.
~~~

## Steward cognition

"Steward" is a cognition role, not a persistent all-knowing chat.

Bob can invoke fresh Steward cognition for consequence evaluation.

Bob supplies a compressed global view such as:

~~~text
MISSION
PRODUCT VISION / SUCCESS CRITERIA
SYSTEM/MODULE MAP
DECISION LEDGER
CURRENT STRATEGIC STATE
RELEVANT MODULE + CONTRACT NEIGHBORHOOD
NEW TECHNICAL ANSWER / DISCOVERY
~~~

The Steward receives enough global structure to understand consequence, not the whole implementation.

If the first consequence pass identifies a wider possible impact, Bob expands only the implicated structural neighborhood and asks another fresh bounded question.

## Product-vision bootstrap

Before large autonomous implementation, the operator and Bob establish enough durable direction for consequence evaluation.

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

Changes are distilled upward so Steward cognition can see the product/system state without loading every module implementation.

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

## Recursive improvement

Bob should measure whether this architecture actually improves outcomes.

Useful signals may include:

- first-pass implementation success;
- rework rate;
- missed constraints;
- contract regressions;
- consequence escalations missed/caught;
- context size;
- verification failures;
- operator interruptions;
- time/cognition cost.

Those observations may improve:

- the 20k/25k envelope;
- module archetypes;
- contract design;
- neighborhood selection;
- Steward packets;
- consequence routing;
- adapter patterns.

Hard invariants such as fresh cognition, durable state and operator authority remain separate from learnable tuning parameters.

## Canonical summary

> **A large Bob project is a graph of bounded transformation modules.**
>
> **Every module is designed to fit, together with its contract neighborhood, inside a fresh cognition envelope before implementation starts.**
>
> **Initial envelope: 20k target, 25k hard ceiling.**
>
> **One cognition question uses one fresh ChatGPT conversation.**
>
> **Bob carries all continuity and structure between questions.**
>
> **Every technical answer receives a separate consequence evaluation so local engineering cannot silently drift away from product intent.**
