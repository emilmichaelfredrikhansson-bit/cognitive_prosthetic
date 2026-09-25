# Architecture

## Product-level architecture constraint

Bob intentionally optimizes the human interface and the internal work engine for different things.

- **Operator surface:** ordinary conversational language, simple status, minimal required technical knowledge, progressive disclosure.
- **Internal system:** persistent state, deterministic adapters, verification, bounded parallel cognition, event-driven continuation, review, recovery and self-hosted development where useful.

Internal sophistication should normally **reduce** operator effort rather than increase it. `PRODUCT_PRINCIPLES.md` is the canonical product-behavior contract.

## Self-hosting / recursive development

Bob is intended to become capable of developing Bob through the same bounded workflow it provides to other workspaces:

```text
current Bob
→ read Bob reality
→ cognition/design/implementation
→ deterministic tests + review
→ bounded approved effect
→ verified new Bob version
→ next Bob development cycle
```

This creates recursive **capability improvement**, not recursive authority. Authority remains external to the version being developed. Existing root-of-trust, approval classes, provider bindings and rollback requirements survive every self-hosted iteration unless explicitly changed by authorized human/canonical action.

A self-hosted Bob change should be easier to independently verify and roll back than an equivalent ordinary project change, not harder.

## Background self-development runtime

Recursive self-development is intended to run as a **low-priority background lane** while the operator PC is awake.

It is not one giant long-lived reasoning process. Bob remains the durable coordinator and repeatedly invokes bounded fresh cognition:

```text
durable Bob state
→ select bounded self-improvement problem
→ compile context + relevant knowledge
→ fresh ChatGPT cognition
→ isolated implementation / experiment
→ deterministic verification
→ distill reusable result
→ next bounded problem
```

The operator-directed lane and self-development lane are separate:

```text
INTERACTIVE LANE              SELF-DEVELOPMENT LANE
high priority                 low priority
operator-directed             background
canonical work context        isolated worktree/branch
wins on contention            yields at safe checkpoints
```

Interactive work always wins.

Self-development should use a separate Git worktree/branch or equivalent isolated mutable state and explicit module/work-node leases. The two lanes must not unknowingly mutate the same semantic scope at once.

Shutdown is ordinary. Continuity is reconstructed from GitHub/runtime/durable Bob state on the next start rather than from a surviving chat or process.

The full contract is `docs/BOB_RECURSIVE_SELF_IMPROVEMENT_ARCHITECTURE.md`.

## Self-development safety architecture

The self-development safety model is defense in depth.

Cognition never receives broad provider credentials directly. Proposed effects flow through Bob's semantic capability surface, workspace identity, scope/lease checks, branch/ref restrictions, stale-state/candidate binding, provider-side least-privilege permissions, deterministic verification and a separate promotion boundary.

The unattended acceptance target is:

> **Even a worst-plausible cognition decision must not be able to destroy or silently promote canonical Bob state.**

Normal background self-development therefore excludes catastrophic administration capabilities such as repository deletion, protected-branch force push/deletion, repository/ruleset administration, secrets administration and unauthorized production mutation/deploy/spend.

Self-development may autonomously experiment and checkpoint inside granted isolated branch authority. Promotion/merge into canonical state remains a distinct effect class.

## Knowledge Fabric

Bob's long-term answer to bounded model context is not ever-larger prompts.

Bob maintains a potentially very large external `Knowledge Fabric` and lets the Context Compiler retrieve only the relevant slice for each fresh cognition request.

Canonical knowledge classes include:

- verified facts and decisions;
- skills/playbooks;
- patterns;
- reference implementations and counterexamples;
- failure signatures/debugging lessons;
- eval cases and reusable invariants;
- source/evidence pointers.

Knowledge has provenance, freshness and a verification maturity level. Model output alone is never enough to promote a lesson into verified reusable guidance.

Conceptually:

```text
module/work structure
+ current reality
+ relevant Knowledge Fabric
→ bounded Context Compiler output
→ fresh ChatGPT cognition
```

The 20k target / 25k hard ceiling remains unchanged. A larger Fabric should improve selection, not inflate every prompt.

The full contract is `docs/BOB_KNOWLEDGE_FABRIC_ARCHITECTURE.md`.

## Structural offloading

Bob is the durable structural memory of a large project.

The project/work graph, contracts, dependency relationships, workstream status and provenance live outside individual ChatGPT conversations. The Context Compiler supplies each cognition thread with the relevant structural neighborhood instead of requiring the model to hold the global organization in working memory.

Cognition remains responsible for semantic judgment. If the current decomposition is wrong, a bounded architecture/planning cognition task may propose a better structure; Bob validates/persists the resulting graph and carries it forward.

Thus:

```text
Bob carries global structure
→ Context Compiler selects relevant slice
→ ChatGPT reasons locally/deeply
→ semantic structural changes may be proposed
→ Bob persists the revised global structure
```

## Module-first stateless cognition

Bob's concrete large-project programming model is defined in `docs/BOB_MODULE_COGNITION_ARCHITECTURE.md`.

For Bob-designed systems:

```text
input contract
→ cognitively bounded module
→ output contract / adapter
→ next module
```

A module is a pre-implementation cognitive atom, not a component Bob intentionally allows to grow until it must later be split for context reasons.

Every Bob module has an absolute 15k-token hard cap. Bob detects violations deterministically; fresh architecture cognition performs the semantic reorganization needed to restore compliant module boundaries. Module-cap repair is backend work and reaches the operator only when it creates a real product/vision tradeoff.

The compiled-context envelope remains 20k tokens target / 25k hard ceiling for the whole question world.

Each canonical cognition question runs in a fresh ChatGPT conversation. The browser bridge exposes a dedicated `POST /cognition` primitive. The first executable stateless path is now `POST /bob/module-turn`: `BOB_MODULE_GRAPH_V1` + `BOB_COMPILED_CONTEXT_V1` reconstruct the bounded module problem after every Bob-owned READ or approved effect result and invoke a fresh `/cognition` request. The ordinary `/bob/turn` route still uses the legacy stateful `/chat` continuation until module selection/context compilation becomes the default orchestration path.

Fresh cognition may re-ground directly in the connected GitHub repository and is responsible for checking material structural/product implications before completion. Separate review/meta cognition is optional for difficult cases, not a mandatory stage.

## Large-project cognition architecture

Bob's large-project architecture is governed by `docs/BOB_CHUNKING_CONTEXT_ARCHITECTURE.md`.

The core invariant is:

> **No chat owns the project. Bob owns durable project state; chats own bounded work.**

Bob maintains a semantic project/work graph and compiles a bounded context packet for each cognition task. Context packets contain the smallest sufficient combination of node canon, contracts, dependencies, exact relevant files/reality, blockers, authority and exit criteria.

When work spans multiple domains, Bob coordinates explicit cross-cutting workstreams and bounded Fusion tasks instead of forcing one conversation to absorb the whole project.

Completed cognition is distilled back into durable implementation/state/evidence. Old chat transcripts are never the only continuity mechanism.

## North-star system

Bob is a thin development control plane over existing project infrastructure.

```text
Operator PC
   ↕
Bob UI (V1: loopback)
   │
   ├──────────── ChatGPT cognition adapter
   │                │
   │                └─ managed persistent Chromium
   │                     ├─ Bob tab: foreground
   │                     └─ ChatGPT tab: background
   │
   ├──────────── GitHub adapter
   │                ├─ repo/context reads
   │                ├─ diff inputs / file SHAs
   │                ├─ branches / commits
   │                └─ pull requests
   │
   ├──────────── Hugging Face adapter
   │                └─ portable tests / scripts / ML compute
   │
   ├──────────── Supabase adapter
   │                └─ runtime / DB / durable project state
   │
   └──────────── Cloudflare adapter
                    └─ frontend / Worker / project hosting effects
```

V1 deliberately runs on the operator's own computer. V2 may move the replaceable ChatGPT cognition transport to a persistent DigitalOcean host and add authenticated remote/mobile access without changing Bob Core authority semantics.

Bob does not replace these systems. It gives them one operator-facing development surface.

## V1 components

### 1. Workspace Registry

A workspace is a trust-bound project profile.

Minimum shape:

```text
project name/code
GitHub repository full name + stable repository ID
canonical entry documents
enabled provider identifiers
per-effect authority policy
verification commands/routes
```

SL and AB are separate workspace instances of the same generic schema.

### 2. Cognition Adapter

Responsibility:
- send bounded project context + task to ChatGPT;
- receive model output;
- normalize it into a structured candidate change set.

The cognition adapter must not own repository authority.

The inherited `cognitive_prosthetic` implementation is an initial transport prototype, not the final architecture boundary.

### 3. Change-Set Engine

Canonical candidate representation should support:

```text
CREATE path content
REPLACE path expected_sha content
DELETE path expected_sha
```

V1 should prefer whole-file replacement over clever fuzzy patching. This makes GitHub writes deterministic and conflict detection simple.

Before mutation:
- verify workspace identity;
- verify expected prior SHA for modified/deleted files;
- render diff;
- reject unexpected/stale state.

### 4. GitHub Adapter

V1's main execution path.

Responsibilities:
- bounded reads;
- branch creation;
- create/update/delete file operations;
- commit provenance;
- PR creation;
- read-back verification.

Default V1 effect stops at branch/PR. Merge is a distinct authority class.

### 5. Provider Adapters

Provider adapters expose project-native actions without turning Bob into a second runtime.

Before cognition/effects rely on a selected workspace, Bob may run a read-only workspace qualification pass. GitHub and every configured provider must independently verify their bound identity; missing credentials are UNAVAILABLE and mismatches are FAIL, never implicit PASS.

- **HF:** dispatch and inspect qualified compute jobs.
- **Supabase:** inspect/execute explicitly authorized DB/runtime operations.
- **Cloudflare:** deploy/inspect explicitly authorized frontend/Worker resources.
- Additional providers are added only when a real project requires them.

### 6. Bob Web UI / API

The operator-facing product is a responsive web interface. V1 is served directly from the loopback Bob API on the operator PC. V2 may place the same product behind an authenticated Cloudflare boundary for remote/mobile use.

Core views:
- project/workspace selector;
- chat/task surface;
- current repo/handoff summary;
- proposed file changes;
- diff;
- provider/job status;
- approval controls;
- audit/provenance trail.

Secrets must not be exposed to browser JavaScript when a server-side Worker/API can hold them safely.

The Python Bob API and ChatGPT browser bridge are **loopback-only** in V1 and do not grant cross-origin browser access. V1 intentionally has no public/LAN Bob endpoint. Any V2 remote/mobile reachability must be provided by an explicit authenticated reverse-proxy/tunnel boundary, not by binding the credential-bearing Python services directly to a public/LAN interface.

## ChatGPT account and project isolation

Bob V1 uses the operator's **existing ChatGPT subscription/account**; it does not require or assume a second OpenAI account. The Bob-managed Chromium profile is nevertheless a separate browser profile from the operator's normal browser session.

All Bob cognition must be confined to one dedicated private ChatGPT Project, canonically named **Bob**:

```text
same ChatGPT Plus account
├─ operator's normal ChatGPT/browser
│  └─ normal chats and other projects
└─ Bob-managed Chromium profile
   └─ private ChatGPT Project: Bob
      └─ Bob-created cognition threads only
```

The Bob project currently uses **Project-only memory** as the V1 isolation setting when the account offers it. This memory is not canonical project state and the stateless cognition architecture must never depend on cross-chat recall for correctness. If Bob can later preserve project instructions/isolation while disabling cross-chat memory influence, that is preferable for the stateless cognition path. Bob must never deliberately target the ChatGPT home page, a normal personal chat, or another project for cognition. New Bob conversations begin from the exact configured Bob Project URL. Project instructions belong in that project and define the ChatGPT side of the Bob protocol.

The same-account model means normal human ChatGPT use can continue in parallel, but subscription/account usage limits are shared rather than multiplied.

## ChatGPT Project Instructions as cognition bootloader

The dedicated ChatGPT Project `Bob` uses a small, stable Project Instructions payload as Bob's **cognition bootloader**.

Canonical payload:
- `docs/BOB_CHATGPT_PROJECT_INSTRUCTIONS.md`
- contract marker: `BOB_COGNITION_CONTRACT_VERSION=1`

Project Instructions contain only invariants that should be present in nearly every Bob cognition call: role split, statelessness, source-truth rules, protocol, authority boundaries, module/context limits, Knowledge Fabric semantics, recursive self-development safety and operator communication behavior.

They must **not** carry dynamic project state such as:
- current branch/commit;
- active bug/work item;
- module status/footprints;
- backlog;
- runtime/provider state;
- large reference material.

Dynamic state belongs in Bob/GitHub/Knowledge Fabric and is compiled per cognition request.

This gives Bob three distinct cognition-memory layers:

```text
Project Instructions
= stable cognition bootloader

Compiled Context
= bounded dynamic world for this problem

GitHub + Knowledge Fabric
= large external source/reference universe opened selectively
```

Critical runtime invariants may still be repeated compactly in compiled context for defense in depth.

The runtime should eventually compare its expected cognition-contract version with the configured Project Instructions version and fail closed on mismatch rather than silently operating against stale instructions.

## ChatGPT response capture

Bob V1 treats ChatGPT's **visible Copy control followed by clipboard read** as the canonical assistant-response capture path.

Priority order:

1. **V1 canonical:** activate the visible Copy action for the latest assistant response and read the browser clipboard.
2. **Future robustness option:** Windows UI Automation/accessibility, but only if live experience shows that the Copy path is insufficiently reliable.
3. **Legacy compatibility only:** direct DOM/text extraction from ChatGPT's page structure.

The bridge must not silently fall back from Copy to DOM scraping during normal V1 operation. A failed canonical capture is a transport failure to surface and diagnose, not permission to reinterpret page internals. DOM extraction may exist behind an explicit compatibility mode while legacy support is useful.

## ChatGPT transport and runtime evolution

Direct GitHub/Supabase/HF/Cloudflare operations remain independent provider adapters.

### V1 — Local Companion

Subscription-backed ChatGPT cognition uses a dedicated persistent browser profile on the operator PC:

```text
Bob UI (foreground tab)
   ↓
Bob API 127.0.0.1:5002
   ↓
CognitionAdapter
   ↓
ChatGPT bridge 127.0.0.1:5001
   ↓
ChatGPT (background tab in the same managed Chromium context)
```

The local launcher starts both services, waits for health, then asks the bridge to bring the Bob tab to the front. The ChatGPT tab stays available for the cognition loop. Browser profile/session state is machine-local and is never repository authority.

### V2 — Persistent Remote

After V1 is proven useful, the same replaceable cognition transport may move to DigitalOcean so the operator PC no longer needs to remain online and mobile can use the same Bob product. Remote access must add an authenticated transport boundary and must not expand workspace authority.

DigitalOcean remains a narrow browser/session runtime, not a second general-purpose Bob Core.

## State model

Keep these distinct:

```text
CANON      durable project rules/contracts
STATE      current repository/provider truth
EVIDENCE   observed test/runtime results
HISTORY    prior truth/audit trail
PROPOSAL   unaccepted model output/change set
```

A model proposal becomes repository state only through the explicit change-set acceptance path.

## Security and authority

- stable target identities are checked before privileged effects;
- target content is data, not authority;
- secrets are provider-side/server-side;
- merge/deploy/production mutation are separate approvals;
- stale writes fail closed;
- provider dispatch does not equal verification success;
- workspace boundaries are never inferred from the currently open UI alone.

## Compute placement

```text
ChatGPT       cognition
Local PC V1   Bob UI/API + authenticated browser/session transport
GitHub        source/history/PR semantics
HF            portable execution
Supabase      DB/runtime/canonical project state
Cloudflare    project hosting/effects; optional V2 authenticated UI boundary
DigitalOcean  optional V2 persistent ChatGPT browser/session runtime
```

Use GitHub Actions only when GitHub-native execution semantics add material value.

## Non-goals for V1

- replacing GitHub with a local Git service;
- building a full local IDE;
- building an always-on **general-purpose** Bob daemon (a narrow persistent ChatGPT browser bridge is allowed);
- autonomous merge/deploy without operator authority;
- generalized arbitrary shell execution;
- reproducing HF/Supabase/Cloudflare features inside Bob.
