# Bob

Bob is a project-agnostic development control plane for ChatGPT-native software work.

It is being built from the `CodeMongerrr/cognitive_prosthetic` fork as a thin cockpit over the infrastructure already used by real projects:

- **ChatGPT** — cognition, diagnostics and code generation
- **GitHub** — source of truth, branches, commits and pull requests
- **Hugging Face** — portable compute, tests and ML jobs
- **Supabase** — runtime, database and durable project state
- **Cloudflare** — responsive web interface and project hosting/runtime surfaces
- **Local PC (V1)** — loopback-only Bob runtime plus a managed authenticated ChatGPT browser session
- **DigitalOcean (V2)** — optional persistent remote cognition runtime for mobile/always-on use

The aim is not to recreate those systems. The aim is to connect them into one operator-facing development workflow usable from PC and mobile.

## Product principle

Bob should feel no harder to use than a good ordinary ChatGPT conversation.

The operator expresses goals, constraints and approvals in normal language. Bob absorbs the complexity of state reconstruction, integrations, work decomposition, testing, waiting, resumption and verification. Technical detail and evidence remain available, but should be progressively disclosed instead of dominating the default conversation.

The long-term performance target is intentionally demanding: **drive projects in the class of Signal Lab or larger with substantially less continuity, tooling and coordination friction than ordinary single-chat development.**

Bob is also designed to become **self-hosting**: Bob can use Bob's own bounded workflow to improve Bob. This is recursive capability improvement, never recursive authority expansion. See `PRODUCT_PRINCIPLES.md`.

## Module-first cognition

For Bob-designed software, the default development atom is a cognitively bounded module:

```text
input
→ bounded transformation
→ output contract / adapter
→ next module
```

New modules should fit, together with their direct contract neighborhood and relevant mission/invariants, inside the initial compiled-input envelope: **20k tokens target / 25k hard ceiling**.

Canonical cognition is stateless: **one cognition question = one fresh ChatGPT conversation**. Bob carries project continuity and source pointers; fresh cognition may re-ground directly in connected GitHub reality and performs its own relevant impact check. Separate review/meta cognition is optional rather than a mandatory second stage.

See `docs/BOB_MODULE_COGNITION_ARCHITECTURE.md`.

## Large-project cognition

Bob is designed around a hard constraint: **no ChatGPT thread owns the project**.

Durable project/work state belongs to Bob. Individual cognition threads receive bounded, semantically compiled context for one coherent work unit. Cross-cutting work is coordinated through explicit child work plus Fusion, and completed cognition is distilled back into durable state/evidence.

This lets project size grow without requiring prompt size to grow proportionally. See `docs/BOB_CHUNKING_CONTEXT_ARCHITECTURE.md`.

## Target development loop

```text
select workspace
→ inspect current project truth
→ reason/code with ChatGPT
→ structured candidate change set
→ deterministic diff + stale-state checks
→ operator approval
→ direct GitHub branch/commit/PR
→ optional HF/Supabase/Cloudflare verification/effects
```

GitHub Actions are not the default development compute layer. Existing qualified infrastructure should be used directly.

## Current state

Bob Core V1 is implemented on `feat/bob-core-v1`: the workspace registry, closed-loop Bob protocol, approval-bound effects, GitHub/Supabase/HF/Cloudflare adapters, manual LLM relay, and a responsive UI scaffold all exist.

The active runtime target is Bob V1 Local Companion on the operator's own PC. DigitalOcean/mobile persistence is V2. Repository/runtime truth in `CURRENT_WORK.md` is authoritative.

Start here:

1. `PROJECT_IDENTITY.md`
2. `CURRENT_WORK.md`
3. `PRODUCT_PRINCIPLES.md`
4. `AGENTS.md`
5. `ARCHITECTURE.md`
6. `ROADMAP.md`
7. `docs/BOB_V1_PLAN.md`

## V1 scope

V1 deliberately focuses on the smallest useful product:

- versioned workspace profiles;
- bounded repository reads;
- structured ChatGPT file-change output;
- deterministic diff and stale-SHA protection;
- operator approval;
- direct GitHub branch/commit/PR writes;
- canary qualification before SL/AB write access.

Provider integrations and the polished Cloudflare UI follow after the GitHub development loop works end to end.

## ChatGPT account model

Bob V1 deliberately uses the operator's **existing ChatGPT account/subscription**, not a second account. Isolation comes from a separate persistent Bob browser profile plus one dedicated private ChatGPT Project named **Bob**. The Bob Project should use **Project-only memory** so Bob's project conversations stay separate from the operator's ordinary ChatGPT conversations.

Normal Bob runtime requires the exact project URL in `BOB_CHATGPT_PROJECT_URL` and will not accept the generic ChatGPT home page as its cognition target. The operator can continue using normal ChatGPT independently in another browser/session; account-level usage limits remain shared.

## ChatGPT response capture

Bob V1 uses ChatGPT's visible **Copy** action and reads the resulting clipboard text. That is the canonical response-capture path. Direct DOM extraction is legacy-only compatibility behavior, not the preferred interface. Windows UI Automation/accessibility may be evaluated later only if the Copy path proves unreliable in real use.

## Important architecture boundary

Direct GitHub, HF, Supabase and Cloudflare integrations can be server-side and work from both PC and mobile.

Subscription-backed ChatGPT browser cognition requires an authenticated browser session. **V1 keeps that session on the operator's own PC**: Bob runs on loopback, a managed persistent Chromium profile keeps ChatGPT in a background tab, and the Bob UI is brought to the foreground in the same browser. The browser bridge remains a replaceable `CognitionAdapter`.

**V2** may move that cognition transport to DigitalOcean and add authenticated remote/mobile access. Core workspace, authority and provider semantics must not depend on that move.

## Lineage

Bob is derived from:

- `CodeMongerrr/cognitive_prosthetic` — MIT licensed upstream browser/API prototype
- `emilmichaelfredrikhansson-bit/project-foundation` — operating-model inspiration, Foundation 0.3.0

See `LICENSE` and `docs/FOUNDATION_ADOPTION.md`.

## Status

Active work and the exact next implementation step live in `CURRENT_WORK.md`.
