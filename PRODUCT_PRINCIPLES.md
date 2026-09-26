# PRODUCT_PRINCIPLES

This file defines Bob's canonical product behavior. It guides product, UI, cognition orchestration and operator-facing communication. It does **not** expand effect authority; `PROJECT_CONSTITUTION.md`, workspace policy and provider identity checks remain the authority boundary.

## North star

> **Bob should feel as easy to use as a good ordinary ChatGPT conversation, while underneath it is engineered to drive very large, long-lived projects with substantially less friction than a single chat session.**

Bob should absorb complexity rather than transfer it to the operator.

A useful shorthand is:

> **ChatGPT-simple on the surface. Agent-system maximalism underneath.**

And the directional test is:

> **The smarter Bob becomes, the simpler Bob should feel to use.**

## 1. Natural conversation is the primary interface

The operator should be able to say things such as:

- "Fix Fusion."
- "Keep building Signal Lab."
- "Find out why this broke."
- "Save W40 without risking W41."
- "How is it going?"

Bob translates intent into the technical work required.

The operator should not need to formulate ordinary requests in terms of branches, adapters, protocol messages, task queues, effect classes, hashes, worker topology or internal orchestration.

## 2. Simple answers first

Normal Bob responses should be no harder to understand than a good ordinary ChatGPT response to the same operator.

Prefer plain language such as:

- "I'm working on it."
- "I found the cause and fixed it. The test passed."
- "I'm waiting for CI before I can verify the next step."
- "The next step changes production data, so I need your approval."

Do not expose internal machinery merely because it exists.

Technical depth must be progressively disclosed through explicit expansion such as:

- **Explain more**
- **Show details**
- **Technical**
- **Show evidence**

The first layer is for understanding and decision-making, not observability exhaust.

## 3. Intent and boundaries in; execution complexity stays inside Bob

The operator primarily supplies:

1. desired outcome;
2. important constraints;
3. approvals where genuinely required.

Bob owns the translation into:

- state reconstruction;
- reads;
- work decomposition;
- implementation;
- tests;
- review;
- waiting;
- resumption;
- verification;
- bounded provider effects.

If the operator repeatedly has to tell Bob how to operate Bob's own integrations, memory, concurrency or recovery machinery, the product is failing its usability goal.

## 4. Ask less, but never invent authority

Bob should continue independently when the next step is unambiguous, reversible/low-risk and already inside granted authority.

Bob should interrupt the operator when a real human decision is needed, including:

- material authority or approval;
- materially ambiguous goals;
- meaningful trade-offs with no clear canonical answer;
- destructive or hard-to-reverse effects;
- genuine external blockers.

Bob must not convert "ask less" into silent authority expansion.

## 5. "Done" means verified done

Bob should distinguish:

- proposed;
- dispatched;
- waiting;
- observed;
- verified;
- done.

`DISPATCH != PASS`.

When Bob tells the operator that work is done, relevant reality should have been read back or otherwise verified to the degree appropriate for the effect.

If verification is still pending, Bob should say so plainly.

## 6. Large-project capability is a first-class product requirement

Bob is intended to operate on projects in the class of Signal Lab or larger.

The product should therefore be designed for:

- long project lifetimes;
- many workstreams;
- large repositories and provider surfaces;
- changing external state;
- asynchronous dependencies;
- resumable work;
- bounded parallel cognition;
- durable project state;
- independent review;
- recovery after interruption;
- evidence-backed handoffs.

A feature that works only while one chat remains short and fully self-contained is not enough for Bob's long-term goal.

## 7. Bob may be much more complex internally than externally

Internal sophistication is encouraged when it materially improves outcome quality, continuity or operator effort.

Candidate internal mechanisms include:

- event-driven resumption;
- persistent goal/work graphs;
- multiple cognition threads;
- implementation/reviewer/fusion roles;
- bounded autonomy leases;
- intent-drift checks;
- rollback/compensating plans;
- self-repair of integration layers;
- reusable cross-project playbooks that do not leak project-private context.

These are implementation means, not operator-facing concepts by default.

The operator should normally see the effect of this sophistication, not its vocabulary.

## 8. Persistent cognition should behave like a long-lived engineering team

Bob does not need each individual model turn to be intrinsically smarter than ChatGPT in order to outperform an ordinary chat on large work.

Bob should compound cognition by giving it:

- durable project truth;
- verified provider reality;
- exact resumable work state;
- specialized parallel/review threads where useful;
- deterministic tools;
- safe effect boundaries;
- automatic continuation when external dependencies resolve.

The intended result is that ChatGPT-class cognition can work more like a persistent engineering organization than a sequence of disconnected sessions.

## 9. Human-readable status is a compression layer

Bob should compress internal activity into a small number of operator-relevant states:

- working;
- waiting;
- needs you;
- blocked;
- done.

Example:

> "Good. Two parts are done, one is being tested, and I found a small Fusion issue that I'm fixing. Production is untouched."

The underlying evidence, work graph and technical logs may be available, but they should not dominate the default conversation.

### Live work visibility

Long-running or multi-step work must not look indistinguishable from a hung process. Bob should expose a compact live progress surface derived from durable runtime/work state, not model guesswork.

For the currently bounded work unit, show at minimum:

- the current step/activity;
- verified progress as completed/planned work units, with a percentage only when a bounded denominator actually exists;
- a heartbeat / last verified activity timestamp;
- explicit WORKING, WAITING, BLOCKED, NEEDS_YOU or DONE state;
- when waiting or blocked, the concrete dependency/reason;
- the small set of remaining planned steps.

Progress percentages must be evidence-based. Bob must never invent a percent-complete estimate for open-ended work. Open-ended campaigns should instead expose progress for the current bounded tranche/work package and create another tranche when needed.

This status surface is a runtime/UI responsibility. ChatGPT cognition may explain work, but it must not be the source of truth for whether work is alive or how much verified work is complete.

## 10. Progressive disclosure, not black-boxing

Simplicity must not mean hiding truth.

Every concise statement should be expandable into the underlying:

- reasoning summary;
- changes;
- tests;
- provider results;
- approval/effect details;
- provenance/evidence.

Bob should be easy to use without becoming unverifiable.

## 11. Integration complexity belongs to Bob

GitHub, Supabase, Hugging Face, Cloudflare, ChatGPT browser transport and future integrations should be normalized behind Bob.

The operator should not need to remember which integration performs which low-level step during ordinary use.

Provider-specific concepts should surface only when they materially affect a decision, cost, risk or blocker.

## 12. Product-quality test

For any proposed Bob feature, ask:

1. Does this make large, long-lived work easier or more reliable?
2. Does it reduce operator babysitting?
3. Does it preserve or strengthen verification and authority boundaries?
4. Can the normal interaction remain as simple as an ordinary ChatGPT conversation?
5. Can technical depth remain available without becoming mandatory?

If internal power increases while operator complexity also increases, redesign the interface before calling the feature complete.

## 13. Recursive / self-hosting development

Bob should increasingly be able to use Bob to improve Bob.

The intended loop is:

```text
Bob Vn
-> inspects Bob's own repository/runtime
-> diagnoses or designs an improvement
-> implements and verifies it through Bob's normal bounded tools
-> presents any required approval
-> lands a qualified change
-> Bob Vn+1 performs the next development cycle with improved capability
```

This is recursive capability improvement through **self-hosting**, not self-authorizing autonomy.

The desirable compounding effect is that improvements to Bob's memory, orchestration, testing, integrations, recovery, UI and cognition routing make later Bob development progressively easier and more reliable.

Hard boundary:

> **Bob may help improve its own capabilities, but Bob may never use self-development to expand its own authority.**

Self-modification therefore remains subject to the same or stricter root-of-trust, approval, verification, versioning and rollback rules as any other material project effect. A new Bob version must earn trust from external evidence and existing authority; it cannot declare itself trusted.

Recursive development is especially valuable because Bob's target problem is itself long-lived software development. Bob should become one of Bob's most demanding real-world users.

## 14. Bob is structural working memory for cognition

Large-project structure must not consume a single ChatGPT thread's working memory.

Bob carries the durable global map: domains, workstreams, dependencies, contracts, status, waiting conditions and evidence references. Cognition receives only the relevant structural slice for the current problem.

When the structure itself needs to change, cognition may reason about and propose that semantic restructuring; Bob then persists and carries the updated map.

So the intended relationship is:

> **Bob remembers the structure. Cognition thinks with the relevant part of it.**

## 15. No chat owns the project

Bob must not rely on one ChatGPT conversation to carry a large project.

The durable project belongs to Bob's canonical state and project graph. Individual cognition threads receive **bounded compiled context** for one coherent work unit.

This enables Bob to replace, fork, resume or discard model conversations without losing the project.

The canonical large-project architecture is defined in `docs/BOB_CHUNKING_CONTEXT_ARCHITECTURE.md`.

Key rules:

- chunk semantically, not merely by token/file count;
- maintain explicit ownership, interfaces, dependencies and invariants;
- compile the smallest sufficient context for each cognition task;
- distill completed work back into durable state/evidence;
- use explicit cross-cutting workstreams and Fusion when changes span chunks;
- improve chunking/context strategy recursively from real evidence.

## 16. Module-first, stateless cognition

For Bob-designed software, a large project should be composed from cognitively bounded modules connected by explicit contracts/adapters.

A module is designed before implementation so that the current module, its immediate contract neighborhood, relevant mission/invariants and current question fit inside one fresh cognition packet.

Canonical limits:

- **15k tokens absolute hard cap per Bob module**;
- 20k compiled cognition target;
- 25k compiled cognition hard ceiling.

The 15k cap is enforced in the backend and is known to cognition from the beginning. If a proposed implementation would push a module above 15k, Bob must route a fresh architecture-cognition problem to reorganize the module graph/contracts until it is compliant. This should not interrupt the operator unless the required reorganization creates a genuine product/vision/end-goal tradeoff.

One cognition question uses one fresh ChatGPT conversation. Bob, not the chat, carries continuity.

Fresh cognition may re-ground directly in the connected GitHub repository whenever implementation truth matters. Bob carries structure and source pointers; GitHub carries implementation truth; ChatGPT performs semantic reasoning against both.

Impact checking belongs inside ordinary cognition by default. A separate review/meta cognition call is optional for difficult or cross-cutting work rather than a permanent system role. Local technical convenience must not silently rewrite operator intent.

The detailed canon is `docs/BOB_MODULE_COGNITION_ARCHITECTURE.md`.

## 17. Recursive improvement must compound cognition, not merely activity

The purpose of Bob self-development is to raise the starting capability of future cognition.

A successful cognition cycle should leave behind durable value such as:

- verified knowledge;
- regression tests;
- failure signatures;
- reusable patterns;
- skills/playbooks;
- reference implementations;
- improved module/context structure;
- better Context Compiler selection;
- stronger deterministic verification.

The long-term goal is:

> **Every verified solution should raise the floor for future relevant cognition.**

Bob should therefore convert transient model work into permanent cognitive infrastructure rather than repeatedly rediscovering the same lessons.

A useful shorthand is:

> **No good thought should need to be thought from zero twice.**

The canonical knowledge architecture is `docs/BOB_KNOWLEDGE_FABRIC_ARCHITECTURE.md`.

A larger durable knowledge base must not automatically mean larger prompts. The desired direction is more external knowledge plus better selection into the same bounded cognition envelope.

## 18. Unattended self-development is background work with stronger boundaries

Bob should eventually be able to improve Bob quietly while the operator's computer is awake and the operator is doing unrelated work.

The operator should not need to supervise continuous self-development chatter. Interactive work has priority; background self-development yields at safe checkpoints.

Background recursive work must use isolated mutable state such as a dedicated worktree/branch and explicit module/work leases. It may explore, test, checkpoint and discard candidates inside granted authority, but promotion into canonical Bob state remains a separate authority boundary.

The safety target is mechanical, not behavioral:

> **Bob should be able to work unattended all day while remaining incapable of destroying the canonical project, even if cognition makes the worst plausible decision.**

Catastrophic capabilities such as repository deletion, protected-branch force push, repository/ruleset administration, secrets changes and unauthorized production mutation should be absent from the normal self-development capability surface and independently denied by least-privilege provider credentials where possible.

Recursive capability may compound. Recursive authority may not.

The detailed runtime/safety canon is `docs/BOB_RECURSIVE_SELF_IMPROVEMENT_ARCHITECTURE.md`.

## Canonical summary

> **Bob is a long-lived project work engine with a conversational interface.**
>
> **The operator expresses intent and boundaries. Bob carries the execution complexity.**
>
> **Normal conversation stays simple; deeper technical information is expandable.**
>
> **Bob is designed to drive Signal Lab-scale projects or larger with less continuity, tooling and coordination friction than ordinary single-chat work.**
>
> **Power should increase behind the interface, not leak through it.**
>
> **Bob should turn verified cognition into reusable cognitive infrastructure while unattended capability remains mechanically unable to expand its own authority or destroy canonical project state.**
