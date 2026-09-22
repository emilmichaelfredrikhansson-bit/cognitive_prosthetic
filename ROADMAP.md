# ROADMAP

## North Star

Make Builder the low-friction development cockpit for ChatGPT-native projects: from PC or mobile, the operator can reason with ChatGPT, inspect current project truth, accept code changes, and operate existing GitHub/HF/Supabase/Cloudflare infrastructure without rebuilding that infrastructure inside Builder.

## Phase 0 — Foundation and architecture

Goal: establish a safe, minimal and reusable project operating model before implementation.

Exit criteria:
- [x] repository identity bound;
- [x] constitution and agent protocol defined;
- [x] product architecture defined;
- [x] existing infrastructure roles preserved;
- [x] always-on general-purpose Builder Core rejected for V1;
- [x] V1 implementation plan written;
- [ ] architecture PR reviewed/merged.

## Phase 1 — GitHub Development Loop V1

Goal: make Builder genuinely usable to develop a canary repository.

Exit criteria:
- [ ] workspace schema with stable repository ID;
- [ ] bounded repository reads;
- [ ] structured ChatGPT change-set contract;
- [ ] deterministic create/replace/delete application;
- [ ] stale-SHA fail-closed behavior;
- [ ] human-readable diff before effect;
- [ ] operator approval boundary;
- [ ] branch creation + commits + PR;
- [ ] provenance/audit record;
- [ ] canary end-to-end success without GitHub Actions-based coding compute.

## Phase 2 — Real workspace integration

Goal: connect real projects while preserving their existing infrastructure.

Order:
1. read-only SL workspace;
2. SL branch/PR writes;
3. read-only AB workspace;
4. AB branch/PR writes;
5. HF job integration;
6. Supabase integration;
7. Cloudflare project integration.

Exit criteria:
- [ ] SL and AB identities are independently bound;
- [ ] no cross-workspace authority leakage;
- [ ] existing provider/runtime contracts remain source of truth;
- [ ] provider dispatch and verification are visibly distinct.

## Phase 3 — Persistent cognition bridge

Goal: make subscription-backed ChatGPT cognition available from both PC and mobile through one remote bridge.

Exit criteria:
- [ ] DigitalOcean browser runtime provisioned with least privilege;
- [ ] persistent authenticated ChatGPT session validated;
- [ ] cognition adapter reachable only through authenticated Builder control-plane paths;
- [ ] secure tunnel to the home network/router validated for selected home-IP egress;
- [ ] PC-local bridge retained only as development/fallback path;
- [ ] browser/session/tunnel failure cannot create ambiguous GitHub effects.

## Phase 4 — Builder Web UI

Goal: one responsive Cloudflare-hosted cockpit for PC and mobile.

Exit criteria:
- [ ] authenticated project selector;
- [ ] task/chat surface;
- [ ] current-work/repo summary;
- [ ] proposed changes + diff;
- [ ] approve/reject controls;
- [ ] GitHub/compute/provider status;
- [ ] mobile-quality layout;
- [ ] secrets remain off the client.

## Phase 5 — Cognition transport hardening

Goal: make ChatGPT transport robust without coupling Builder to one capture mechanism.

Exit criteria:
- [ ] cognition adapter interface stable;
- [ ] DOM response extraction removed from preferred path;
- [ ] UI Automation/accessibility copy transport validated in the persistent browser runtime;
- [ ] reconnect/session-expiry behavior defined;
- [ ] DigitalOcean + home-egress transport validated from both PC and mobile clients;
- [ ] transport failures cannot produce ambiguous repository effects.

## Later

- repair loops driven by deterministic test evidence;
- multi-repo workspaces when a real project needs them;
- optional provider adapters beyond the current SL/AB stack;
- richer audit/history and reusable work recipes;
- optional on-demand execution sandbox only if existing infrastructure proves insufficient.

## Parked

- full custom IDE/editor;
- permanent general-purpose local Builder daemon;
- autonomous production merge/deploy;
- broad GitHub Actions orchestration as the normal development engine;
- speculative plugin ecosystem before SL/AB earn it.

## Rejected / retired directions

- treating GitHub Actions as default compute merely because code is hosted on GitHub;
- duplicating HF/Supabase/Cloudflare functionality inside Builder;
- binding product logic directly to Playwright DOM selectors;
- treating ChatGPT output as accepted repository state without an explicit deterministic write boundary.
