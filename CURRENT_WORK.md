# CURRENT_WORK

`CURRENT_WORK.md` is Bob's primary operational handoff.

## ROOT_OF_TRUST

- GitHub repository: `emilmichaelfredrikhansson-bit/cognitive_prosthetic`
- GitHub repository ID: `1374229539`
- Implementation branch: `feat/bob-core-v1`
- Foundation/base branch: `feat/builder-foundation-architecture`
- Project identity: `governance/project-identity.json`
- Constitution: `PROJECT_CONSTITUTION.md`
- Agent protocol: `AGENTS.md`
- Architecture: `ARCHITECTURE.md`
- Strategic direction: `ROADMAP.md`
- Bob protocol: `docs/BOB_PROTOCOL_V1.md`
- ChatGPT Project instructions: `docs/BOB_CHATGPT_PROJECT_INSTRUCTIONS.md`

## CURRENT_MODE

`DEVELOPMENT`

## CURRENT_EXECUTOR

`CHAT_INTERACTIVE`

## CURRENT_ARCHITECTURE

Bob is a bidirectional closed-loop coordination layer:

```text
human
↕
normal ChatGPT cognition
↕
BOB protocol
↕
deterministic adapters
↕
GitHub / Supabase / Hugging Face / Cloudflare
↕
verified reality feedback
↕
same ChatGPT conversation
```

No component is globally smart.

- ChatGPT owns semantic reasoning and code generation.
- Bob owns deterministic I/O, identity/authority checks, execution and verified feedback.
- providers own external state;
- the operator owns material approvals.

The inherited ChatGPT browser bridge is now a replaceable cognition transport. The intended persistent runtime remains DigitalOcean with optional secure home-network egress; that runtime is not a general-purpose Bob compute core.

## LAST_COMPLETED

`BOB_PRODUCT_IDENTITY_CANONICALIZATION`

Bob is now the canonical product identity across root identity, governance schemas, workspace schema, operator routes and documentation. The historical foundation branch name `feat/builder-foundation-architecture` is intentionally unchanged.

The already-completed Core V1 runtime tranche on `feat/bob-core-v1` includes:

- versioned `BOB_WORKSPACE_V1` registry;
- `BOB.READ / BOB.EFFECT / BOB.RESULT / BOB.ASK / BOB.DONE` protocol;
- closed-loop conversation driver that reinjects verified results into the same ChatGPT conversation;
- effect staging with candidate hashes and explicit approval;
- GitHub adapter with stable repo-ID verification, stale-SHA protection, diff preview and write read-back;
- Supabase Management API adapter with project + organization identity binding, logs, read-only SQL and gated SQL effects;
- Hugging Face Jobs adapter with authenticated account/namespace binding;
- Cloudflare adapter for R2 identity anchors, Workers versions/deployments and Pages;
- basic responsive Bob web UI with workspace selection, natural chat and approval/diff cards;
- ChatGPT bridge targetable to a specific ChatGPT Project via `CHATGPT_TARGET_URL`;
- preferred response capture changed to visible Copy -> clipboard; DOM extraction is explicit legacy fallback only;
- Bob self-workspace and Signal Lab workspace added.

Signal Lab workspace is bound from current repository truth:

```text
GitHub repo = emilmichaelfredrikhansson-bit/signal-lab-pro
GitHub repo ID = 1306946195
Supabase project = ttycbqaueeaedcrtcpuw
Supabase organization = wiibxuccedkxrvgruccq
HF namespace = Reallothesecond
HF account ID = 6a986fdd2e846637191b1c5e
Cloudflare identity anchor = R2 bucket signal-lab-snapshots-prod
Cloudflare Worker = signal-lab-mission-control-preview
```

SL workspace currently allows branch writes and PR creation only after Bob approval. Production Supabase mutation, HF spend and Cloudflare deploy remain disabled.

## VERIFICATION

HF Job `6ab2c4d651992417dfcd3e7d` cloned the exact implementation branch, installed pinned dependencies, and ran:

```text
python -m unittest discover -s tests -v
```

Initial HF verification:

```text
job = 6ab2c4d651992417dfcd3e7d
6 tests
6 PASS
job stage = COMPLETED
```

A second HF verification added **manual LLM relay mode**, where an external interactive LLM can play ChatGPT without the browser bridge:

```text
job = 6ab2c73251992417dfcd3ec2
7 tests
7 PASS
```

The manual relay proof covers:

```text
LLM emits BOB.READ
→ Bob executes read
→ Bob returns BOB.RESULT
→ external LLM continues
→ LLM emits BOB.EFFECT
→ Bob stages exact effect
→ approval
→ Bob executes/verifies
→ Bob returns BOB.RESULT
→ LLM emits BOB.DONE
```

This means development and protocol qualification can continue with the current ChatGPT conversation acting as the cognition side until the real browser runtime is available.

This still does not prove the live browser/clipboard transport or installed runtime credentials.

The Bob naming/schema canonicalization occurred after the latest HF job. The prior 7/7 result remains baseline runtime evidence, but a fresh execution-suite result has not yet been recorded for the canonicalized head; do not mislabel the older job as current-head verification.

## ACTIVE_WORK

`BOB_CORE_V1_RUNTIME_WIRING`

The code architecture exists and is unit-green. The next coherent work is to turn it into a real always-available Bob runtime.

## NEXT_INTENDED_WORK

Manual relay is available now, so use it for protocol/integration development when the browser runtime is unavailable.

1. Add/verify the second real workspace (AB) from its actual repository/provider identities.
2. Provision/qualify the persistent DigitalOcean browser runtime.
3. Install the Bob ChatGPT Project instructions and bind `CHATGPT_TARGET_URL`.
4. Configure least-privilege runtime credentials for GitHub, Supabase, HF and Cloudflare.
5. Run read-only live qualification through Bob against Bob + SL.
6. Qualify one approved Bob-repo branch/PR write end to end.
7. Deploy the responsive Bob UI/API behind authenticated Cloudflare access.
8. Only after these are green, consider enabling any project-specific production effect classes.

## OPEN_FINDINGS

- Browser Copy-button selectors must be live-qualified against the current ChatGPT UI.
- DigitalOcean runtime and home-egress tunnel are designed but not provisioned.
- Cloudflare runtime account ID remains secret/runtime-bound; SL verifies it through the canonical R2 bucket before Worker state is trusted.
- The current UI is functional scaffolding, not final product design.
- Bob effect approvals currently live in process memory; persistence/resume is a later hardening item.
- One Bob runtime currently assumes one active ChatGPT browser conversation at a time; multi-session concurrency is intentionally not yet implemented.

## FIRST_ACTION

Continue `BOB_CORE_V1_RUNTIME_WIRING` from actual branch state. Do not rebuild the protocol or adapters from chat memory.

## HARD_BLOCKERS

- No privileged target-project effect before exact workspace identity verification.
- No external effect is PASS until Bob has verified returned/after-state.
- No model response may expand workspace authority.
- No SL production mutation/deploy/spend is authorized by the current workspace.
- No secret may be committed to the repository or sent to browser JavaScript.
- Do not make DigitalOcean a general-purpose execution engine merely because it hosts the ChatGPT browser.
