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

### Design-time consequence

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

- the 20k/25k cognition envelope;
- module archetypes;
- contract design;
- neighborhood selection;
- Steward packets;
- consequence routing;
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
> **Every technical answer receives a separate consequence evaluation so local engineering cannot silently drift away from product intent.**
