# Builder

Builder is a project-agnostic development control plane for ChatGPT-native software work.

It is being built from the `CodeMongerrr/cognitive_prosthetic` fork as a thin cockpit over the infrastructure already used by real projects:

- **ChatGPT** — cognition, diagnostics and code generation
- **GitHub** — source of truth, branches, commits and pull requests
- **Hugging Face** — portable compute, tests and ML jobs
- **Supabase** — runtime, database and durable project state
- **Cloudflare** — responsive web interface and project hosting/runtime surfaces

The aim is not to recreate those systems. The aim is to connect them into one operator-facing development workflow usable from PC and mobile.

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

The inherited upstream code currently provides a local ChatGPT browser/API prototype.

Builder architecture and operating model are now defined, but the V1 GitHub development loop is not implemented yet.

Start here:

1. `PROJECT_IDENTITY.md`
2. `CURRENT_WORK.md`
3. `AGENTS.md`
4. `ARCHITECTURE.md`
5. `ROADMAP.md`
6. `docs/BUILDER_V1_PLAN.md`

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

## Important architecture boundary

Direct GitHub, HF, Supabase and Cloudflare integrations can be server-side and work from both PC and mobile.

Subscription-backed ChatGPT browser cognition requires a reachable authenticated browser session. The inherited browser bridge is therefore treated as a replaceable `CognitionAdapter`, not as the product architecture itself.

## Lineage

Builder is derived from:

- `CodeMongerrr/cognitive_prosthetic` — MIT licensed upstream browser/API prototype
- `emilmichaelfredrikhansson-bit/project-foundation` — operating-model inspiration, Foundation 0.3.0

See `LICENSE` and `docs/FOUNDATION_ADOPTION.md`.

## Status

Active work and the exact next implementation step live in `CURRENT_WORK.md`.
