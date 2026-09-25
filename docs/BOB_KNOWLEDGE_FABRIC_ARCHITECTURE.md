# Bob Knowledge Fabric Architecture

This document defines Bob's canonical external knowledge system for compounding ChatGPT-class cognition over long-lived projects.

It complements `docs/BOB_RECURSIVE_SELF_IMPROVEMENT_ARCHITECTURE.md`, `docs/BOB_CHUNKING_CONTEXT_ARCHITECTURE.md` and `docs/BOB_MODULE_COGNITION_ARCHITECTURE.md`.

## Core idea

ChatGPT cognition is powerful but context-bounded.

Bob should not try to solve that by placing an ever-growing project encyclopedia into every prompt.

Instead:

> **Bob may maintain an enormous external body of verified reference material while only compiling the smallest relevant slice into each cognition request.**

Most knowledge should cost zero cognition tokens until it is selected.

Conceptually:

```text
durable Bob Knowledge Fabric
├─ product principles
├─ architecture and contracts
├─ verified facts
├─ decisions + rationale
├─ skills / playbooks
├─ verified patterns
├─ reference implementations
├─ positive/negative examples
├─ failure signatures
├─ debugging playbooks
├─ provider/tool knowledge
├─ experiments and outcomes
├─ eval cases
└─ source/evidence pointers
          │
          ▼
Context Compiler / retriever
          │
selects only relevant material
          │
          ▼
fresh ChatGPT cognition
```

The Knowledge Fabric is external cognitive infrastructure, not model memory.

## Compounding principle

> **No good thought should need to be thought from zero twice.**

When a cognition cycle discovers a reusable, verified lesson, Bob should preserve it in a form future cognition can retrieve.

The goal is not to prevent fresh reasoning. The goal is to avoid spending fresh reasoning on rediscovering already-established facts, traps, techniques and reference solutions.

## What compounds

Bob should accumulate at least four high-value classes of reusable cognition support.

### 1. Knowledge

Verified project/tool/world facts that materially help future work.

Examples:

- provider behavior;
- operating-system quirks;
- repository/runtime contracts;
- protocol semantics;
- deployment constraints;
- product invariants.

### 2. Skills / playbooks

Reusable problem-solving procedures.

Examples:

- split an oversized module without breaking contracts;
- qualify a provider identity;
- debug flaky browser automation;
- perform an approval-bound migration;
- verify a branch write with read-back;
- recover from an interrupted background self-development cycle.

### 3. Examples / reference implementations

Concrete working implementations and useful counterexamples.

A reference implementation should point to real source/evidence rather than duplicate entire codebases unnecessarily.

Useful examples include:

- known-good module structures;
- adapters with strong stale-state handling;
- working tests;
- known-bad approaches plus explanation of why they failed.

### 4. Failure memory

Compact descriptions of failures that future cognition can recognize early.

A failure item should ideally contain:

```text
SYMPTOM
CONTEXT
ROOT_CAUSE
BAD_FIXES / FALSE_LEADS
VERIFIED_FIX
EVIDENCE
APPLIES_WHEN
DOES_NOT_APPLY_WHEN
SOURCE_POINTERS
```

Failure memory is especially valuable because it converts expensive debugging into future prevention.

## Additional useful item classes

The Fabric may also contain:

- canonical decisions and rationale;
- heuristics;
- module/template archetypes;
- evaluation cases;
- invariants;
- freshness-sensitive provider notes;
- compatibility matrices;
- unresolved hypotheses clearly marked as such.

## Knowledge item contract

A durable knowledge item should be compact and provenance-rich.

Conceptually:

```text
ID
TYPE
DOMAIN
TITLE
STATEMENT / PROCEDURE
WHEN_APPLICABLE
WHEN_NOT_APPLICABLE
RELATED_MODULES
RELATED_CONTRACTS
RELATED_PATTERNS
RELATED_FAILURES
REFERENCE_IMPLEMENTATIONS
SOURCE_REFS
EVIDENCE_REFS
VERIFICATION_LEVEL
FRESHNESS
LAST_VERIFIED
TOKEN_COST
PRIORITY
SUPERSEDES / SUPERSEDED_BY
```

Not every field must be populated for every item, but important claims should remain traceable.

## Verification ladder

Bob must not promote something into reusable canon merely because one ChatGPT response asserted it.

A useful maturity model is:

```text
OBSERVATION
↓ evidence/repetition
CANDIDATE_LESSON
↓ direct verification
VERIFIED_PATTERN
↓ successful reuse across appropriate cases
CANONICAL_PRACTICE
```

Definitions:

- **OBSERVATION** — something happened or was suggested; not yet generalized.
- **CANDIDATE_LESSON** — plausible reusable explanation with evidence but insufficient validation.
- **VERIFIED_PATTERN** — supported by direct tests/reality and safe to retrieve as guidance.
- **CANONICAL_PRACTICE** — repeatedly successful and explicitly accepted as a default practice.

Negative evidence can demote or supersede an item.

## Provenance over confidence theater

Every important reusable claim should answer:

> Why does Bob believe this?

Prefer evidence such as:

- exact commit/ref;
- test/eval receipt;
- provider read-back;
- runtime observation;
- reproduced failure;
- successful reuse count;
- canonical human decision.

Avoid vague confidence labels without evidence.

## Context Compiler integration

The Knowledge Fabric is useful only if retrieval is selective.

For each cognition task, the Context Compiler should conceptually consider:

```text
current bounded problem
+ target module/work node
+ direct contracts/neighbors
+ failure signatures matching the symptom
+ verified patterns matching the task
+ 1–2 strong reference implementations when useful
+ relevant recent decisions
+ hard invariants
+ source pointers
+ current reality/evidence
→ rank / deduplicate / budget
→ bounded compiled context
```

The existing 20k context target / 25k hard ceiling remain in force.

A larger Knowledge Fabric should **not** imply a larger prompt.

## Source pointers are first-class compression

If cognition can inspect connected GitHub directly, Bob often does not need to inject an entire reference implementation.

It can supply:

```text
PATTERN-017
purpose: idempotent verified GitHub branch mutation
reference: bob/integrations/github.py
tests: tests/test_github_adapter.py
evidence: commit / qualification receipt
```

Fresh cognition may open the exact source when needed.

This allows very large durable knowledge to remain practically available without consuming the prompt up front.

## Hierarchical resolution

Knowledge should exist at multiple useful resolutions.

```text
canonical principle
↓
pattern / playbook
↓
reference implementation
↓
exact source/evidence
```

The compiler chooses the cheapest level sufficient for the current problem.

## Model-specific failure compensation

Bob should learn recurring failure modes of the cognition system it uses.

Examples might include a tendency to:

- make modules too large;
- assume provider behavior without read-back;
- forget platform-specific encoding;
- overbuild abstraction;
- miss stale-state races;
- treat dispatch as success.

When current evidence says a known failure mode is relevant, the Context Compiler may include a concise warning or checklist in the fresh cognition packet.

This is not a claim that model behavior is immutable. It is evidence-driven scaffolding around the current cognition provider.

Bob therefore acts as corrective external working memory:

> **Bob should arrange the problem so cognition is less likely to repeat mistakes already observed and understood.**

## Anti-poisoning rules

Knowledge accumulation can compound errors as easily as truth. The Fabric therefore fails closed on promotion.

Rules:

- model output alone is not verified knowledge;
- repository/provider/runtime truth outranks summaries;
- observations and hypotheses must be labeled;
- important patterns require direct evidence;
- stale facts must carry freshness metadata;
- contradictory evidence must be retained/reconciled rather than silently discarded;
- superseded practices must stop being selected by default;
- private workspace knowledge must not leak across trust domains merely because it is useful elsewhere.

Generic cross-project patterns may be distilled only after project-specific/private details are removed.

## Reuse before invention

Before asking cognition to design a new mechanism, Bob should check whether a verified pattern/reference implementation already solves the same class of problem.

This does not mean blindly copying old code.

The compiler should surface:

- why the pattern may apply;
- where the reference lives;
- known constraints;
- counterexamples/failure cases where relevant.

Fresh cognition remains responsible for semantic fit.

## From solved problem to reusable infrastructure

After a difficult problem is solved, Bob should ask whether the result should become:

- a regression test;
- a failure signature;
- a reusable pattern;
- a playbook/skill;
- a template;
- a reference implementation;
- a contract/invariant;
- a Context Compiler heuristic.

Example:

```text
incident:
large compiled prompt times out while Playwright types character by character

verified fix:
atomic fill()

distilled pattern:
large machine-generated prompts should use atomic field population rather than human-speed keystroke simulation unless typing semantics are specifically required

evidence:
exact failing runtime + commit + passing qualification
```

The next relevant automation task should begin with that lesson available.

## Knowledge is not authority

A knowledge item can recommend an action; it cannot grant permission to perform it.

The Fabric never expands:

- workspace scope;
- effect classes;
- provider permissions;
- approval authority;
- production access.

Authority remains governed by the Constitution/workspace/provider boundary.

## Knowledge lifecycle

Bob should periodically:

- detect duplicates;
- merge equivalent patterns without losing provenance;
- mark stale facts;
- revalidate high-value freshness-sensitive items;
- identify contradictory evidence;
- demote weak items;
- promote repeatedly successful patterns;
- remove dead source pointers;
- preserve historical lineage when items are superseded.

This maintenance itself may use bounded fresh cognition plus deterministic validation.

## Metrics

Useful Knowledge Fabric signals include:

- retrieval frequency;
- successful reuse count;
- prevented recurrence of known failure;
- context tokens spent per useful item;
- false-positive retrieval rate;
- stale/contradicted retrievals;
- first-pass success with versus without a pattern;
- operator/cognition effort saved;
- reference implementation survival across later changes.

Metrics guide retrieval and curation; they do not autonomously rewrite hard authority or product canon.

## Relationship to module/context architecture

The module graph tells Bob **where the current problem lives**.

The Knowledge Fabric tells Bob **what prior verified experience may help solve it**.

The Context Compiler combines both:

```text
project/module structure
+ current reality
+ relevant durable knowledge
→ smallest sufficient world
→ fresh cognition
```

This is the intended answer to bounded model context: scale external knowledge and improve selection, rather than forcing the whole knowledge base into one prompt.

## Canonical long-term outcome

Bob should gradually transform consumed cognition into permanent cognitive infrastructure.

Over time:

```text
better knowledge + better retrieval
→ better compiled context
→ better cognition outcomes
→ better verified lessons
→ better knowledge + better retrieval
→ ...
```

The intended compounding loop is:

> **Every verified solution should raise the floor for future relevant cognition.**

The model may remain stateless and context-bounded. Bob supplies the accumulating institution around it.
