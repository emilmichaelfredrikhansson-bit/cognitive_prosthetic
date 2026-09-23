# ROADMAP

## North Star

Make Bob the low-friction development cockpit for ChatGPT-native projects. **V1 is local-first on the operator's own PC** so the product and cognition loop can be proven in daily use before adding remote infrastructure. **V2** may add DigitalOcean-backed persistence and authenticated mobile access.

## Phase 0 — Foundation and architecture

Goal: establish a safe, minimal and reusable project operating model.

Exit criteria:
- [x] repository identity bound;
- [x] constitution and agent protocol defined;
- [x] product architecture defined;
- [x] existing infrastructure roles preserved;
- [x] always-on general-purpose Bob Core rejected;
- [x] V1 implementation plan written;
- [ ] architecture PR reviewed/merged.

## Phase 1 — Closed-loop Bob Core

Goal: make Bob a real two-way I/O layer between normal ChatGPT cognition and project infrastructure.

Exit criteria:
- [x] workspace schema with stable repository ID;
- [x] bounded repository reads and project search;
- [x] machine-readable Bob protocol;
- [x] closed-loop READ -> RESULT -> cognition continuation;
- [x] deterministic GitHub create/replace/delete primitives;
- [x] stale-SHA fail-closed behavior;
- [x] human-readable diff before GitHub effect;
- [x] operator approval/reject boundary;
- [x] branch + file + PR API implementation;
- [x] Supabase adapter;
- [x] Hugging Face Jobs adapter;
- [x] Cloudflare Workers/R2 + Pages adapter;
- [x] browser-independent manual relay transport;
- [ ] one end-to-end approved GitHub PR produced through Bob itself.

## Phase 2 — Bob V1 Local Companion

Goal: use Bob on the operator PC with ChatGPT in a background managed browser tab and Bob in the foreground.

Exit criteria:
- [x] loopback-only Bob API and ChatGPT bridge;
- [x] dedicated persistent ChatGPT browser profile;
- [x] same-account/dedicated-project cognition model canonicalized;
- [x] normal runtime fails closed without an explicit Bob ChatGPT Project URL;
- [x] visible ChatGPT Copy -> clipboard canonicalized as V1 response capture;
- [x] direct DOM extraction retained only as explicit legacy compatibility mode;
- [ ] evaluate Windows UI Automation only if live Copy capture proves materially unreliable;
- [ ] private ChatGPT Project `Bob` created on the operator account with Project-only memory;
- [x] one-time local login flow;
- [x] Windows setup/first-run/start launchers;
- [x] local launcher health-gates both services;
- [x] bridge can open/focus Bob in the same browser while retaining the ChatGPT tab;
- [x] non-loopback local companion configuration fails closed;
- [ ] live ChatGPT Copy/clipboard capture qualified on the operator PC;
- [ ] live Bob -> ChatGPT -> BOB.READ/RESULT loop qualified;
- [ ] live approval/reject flow qualified from the local Bob UI;
- [ ] one approved Bob-repository branch/PR canary completed through Local Companion.

## Phase 3 — Real workspace qualification

Goal: connect real projects while preserving their existing infrastructure and authority.

Order:
1. read-only Bob self-workspace;
2. Bob branch/PR canary;
3. SL read-only qualification;
4. SL branch/PR qualification;
5. AB read-only qualification;
6. AB branch/PR qualification;
7. provider-specific HF/Supabase/Cloudflare effects only when explicitly needed.

Exit criteria:
- [x] SL and AB identities are independently bound;
- [ ] no cross-workspace authority leakage;
- [ ] existing provider/runtime contracts remain source of truth;
- [ ] provider dispatch and verification are visibly distinct;
- [ ] V1 ordinary work is usable without DigitalOcean.

## Phase 4 — Product parity and hardening

Goal: make local Bob feel like a first-class ChatGPT workspace.

Exit criteria:
- [x] project/workspace sidebar;
- [x] central chat/composer;
- [x] project inspector for Reality/Authority/Providers/context/settings;
- [x] bounded project search;
- [x] first-class approvals;
- [x] responsive shell and appearance controls;
- [ ] project health/drift indicators;
- [ ] richer activity/audit surfaces;
- [ ] truthful file/attachment affordances where backend support exists;
- [ ] exact ChatGPT thread identity persistence before any resumable history UI is claimed;
- [ ] reconnect/session-expiry failure path qualified.

## Phase 5 — Bob V2 Persistent Remote

Goal: remove the requirement for the operator PC to remain online after V1 has proven its value.

Candidate topology:

```text
PC / mobile
→ authenticated Bob boundary
→ replaceable CognitionAdapter
→ DigitalOcean persistent browser/session
→ ChatGPT
```

Exit criteria:
- [ ] DigitalOcean browser runtime provisioned with least privilege;
- [ ] persistent authenticated ChatGPT session validated;
- [ ] authenticated Bob-to-bridge transport;
- [ ] remote/mobile access cannot expose credential-bearing loopback services directly;
- [ ] optional home-network egress evaluated only if still needed;
- [ ] V1 local bridge retained as fallback/canary path;
- [ ] browser/tunnel/session failure cannot create ambiguous external effects.

## Later

- repair loops driven by deterministic test evidence;
- multi-repo workspaces when a real project needs them;
- optional provider adapters beyond the current SL/AB stack;
- richer audit/history and reusable work recipes;
- optional on-demand execution sandbox only if existing infrastructure proves insufficient.

## Parked

- full custom IDE/editor;
- autonomous production merge/deploy;
- broad GitHub Actions orchestration as the normal development engine;
- speculative plugin ecosystem before SL/AB earn it.

## Rejected / retired directions

- requiring DigitalOcean before Bob can be usefully tested;
- treating GitHub Actions as default compute merely because code is hosted on GitHub;
- duplicating HF/Supabase/Cloudflare functionality inside Bob;
- treating ChatGPT output as accepted repository state without an explicit deterministic write boundary.
