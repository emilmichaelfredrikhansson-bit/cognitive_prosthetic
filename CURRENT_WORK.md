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
- Manual relay: `docs/BOB_MANUAL_RELAY_V1.md`
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

`BOB_PERSISTENT_RUNTIME_SYSTEMD_CONTRACT`

Bob now has deployment templates for `bob-api.service` and `chatgpt-bridge.service` under `deploy/systemd/`. Both force loopback binding independently of the runtime env file, run as a dedicated unprivileged `bob` identity, use `/etc/bob/bob.env`, and apply basic systemd hardening. The browser bridge gets an explicit writable profile scope at `/var/lib/bob` and launches its headed Chromium inside an ephemeral Xvfb display (`xvfb-run -a`), so a headless Ubuntu host can actually start it. Initial interactive ChatGPT login still requires a separately authenticated temporary display path; remote access remains outside these units and must use a separately authenticated proxy/tunnel boundary.\n\nBob now includes a read-only runtime preflight entry point at `python -m bob.preflight`. It fails closed when either credential-bearing Python service is configured on a non-loopback host, then delegates provider identity checks to the existing `BobRuntime.qualify_workspace(...)` path for selected or all registered workspaces. The report exposes qualification/capability metadata but never credential values.

Bob is now the canonical product identity across root identity, governance schemas, workspace schema, operator routes and documentation. The historical foundation branch name `feat/builder-foundation-architecture` is intentionally unchanged.

AutoBlog is now registered as the second real target workspace from current external truth:

```text
GitHub repo = emilmichaelfredrikhansson-bit/autoblog-foundation
GitHub repo ID = 1347272122
Supabase project = ofnzyuosysdycrdxalve
Supabase organization = wiibxuccedkxrvgruccq
Supabase live status = ACTIVE_HEALTHY
HF namespace = Reallothesecond
HF account ID = 6a986fdd2e846637191b1c5e
Cloudflare account = 7eb16181070aa18ecb28a1719fea7773
Cloudflare Worker identity anchor = autoblog-canary
```

GitHub metadata, Supabase project/org and HF account were independently read back live during the binding work. The Cloudflare account/Worker identifiers came from current AutoBlog repository truth; live Cloudflare API read-back remains a runtime qualification step because this interactive session does not hold the Cloudflare runtime token.

Cloudflare identity handling was hardened at the same time: a bare account ID can no longer produce an identity PASS. Bob now requires a remotely verifiable R2 bucket, Worker or Pages resource anchor. AB uses its canonical `autoblog-canary` Worker as that anchor.

AB currently allows only approval-bound GitHub branch writes and PR creation. Supabase production mutation, HF spend and Cloudflare deploy remain disabled.

Bob now also exposes a read-only workspace qualification surface through `BobRuntime.qualify_workspace(...)` and `POST /bob/qualify`. It verifies GitHub plus every provider configured for that workspace. A missing runtime adapter/credential is reported as `UNAVAILABLE`; provider mismatch/errors are `FAIL`; only all-PASS results set `qualified=true`. The web cockpit exposes this as **Verify workspace**, so identity/runtime diagnostics do not depend on the ChatGPT browser bridge.

Manual relay is now a complete explicit HTTP transport: `POST /bob/relay/start` returns the exact initial `BOB.WORKSPACE` + human prompt, `POST /bob/relay` processes external model responses, and `POST /bob/relay/approve` executes an exact staged candidate after approval. The loop is documented in `docs/BOB_MANUAL_RELAY_V1.md`.

The approval boundary has also been hardened: candidate hashes now bind the authority-relevant workspace configuration (repository full name/ID/default branch, provider bindings and effect policy) plus the staged GitHub branch/file state used for the preview. Bob re-reads that state immediately before execution. Branch drift, file drift or workspace/provider rebinding after staging invalidates the approval and requires a fresh candidate.

The local credential-bearing control surfaces are now hardened for runtime wiring: both the Bob API and ChatGPT browser bridge bind to `127.0.0.1` by default, permissive Flask-CORS was removed, and host/port exposure requires explicit environment configuration. Remote/mobile access must therefore arrive through the separately authenticated proxy/tunnel boundary rather than accidental LAN/public binding.

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

The Bob naming/schema canonicalization and subsequent AB binding, workspace qualification, manual-relay HTTP completion, approval-state binding and local control-plane hardening occurred after the latest HF job. The prior 7/7 result remains baseline runtime evidence, but a fresh execution-suite result has not yet been recorded for current head; do not mislabel the older job as current-head verification.

Current external read-only reconciliation on 2026-09-22 independently confirmed:

```text
Bob GitHub = emilmichaelfredrikhansson-bit/cognitive_prosthetic / 1374229539
SL GitHub = emilmichaelfredrikhansson-bit/signal-lab-pro / 1306946195
AB GitHub = emilmichaelfredrikhansson-bit/autoblog-foundation / 1347272122

SL Supabase = ttycbqaueeaedcrtcpuw / wiibxuccedkxrvgruccq / ACTIVE_HEALTHY
AB Supabase = ofnzyuosysdycrdxalve / wiibxuccedkxrvgruccq / ACTIVE_HEALTHY

HF = Reallothesecond / 6a986fdd2e846637191b1c5e
HF job 6ab2c4d651992417dfcd3e7d = COMPLETED
HF job 6ab2c73251992417dfcd3ec2 = COMPLETED
```

This external reconciliation proves the bindings are still real; it does **not** prove that a deployed Bob process has the required runtime credentials. Cloudflare live account/resource read-back remains unavailable from the interactive development session and must be performed through Bob once `CLOUDFLARE_API_TOKEN` is installed.

The runtime-preflight tranche adds **5 isolated unittest methods**. The exact proposed `bob/preflight.py` + `tests/test_preflight.py` content was executed in the interactive sandbox before commit: **5/5 PASS**, and both files passed `py_compile`. This is narrow evidence for the new preflight logic only; it does not substitute for a full branch-suite run.

The branch declares **29 unittest methods** across protocol/workspace/driver/Cloudflare/server-surface/runtime-preflight/systemd-contract tests.

Current implementation verification is now executable and current:

```text
tested commit = 9bb18a495f4c9ed7acd93e2b1eda4d6ec6319816
HF job = 6ab2e0d151992417dfcd41bd
account = Reallothesecond / 6a986fdd2e846637191b1c5e
hardware = cpu-basic
result = 29 tests / 29 PASS
job stage = COMPLETED
finished = 2026-09-22T20:11:17.345Z
```

The job cloned the public repository, checked out the exact pinned commit, asserted `git rev-parse HEAD` matched that SHA before testing, installed the pinned requirements and ran `python -m unittest discover -s tests -v`. The unittest log ended with `Ran 29 tests` and `OK`.

The runtime-preflight and systemd-contract isolated checks remain useful narrow evidence, but the HF current-implementation run supersedes them as the main execution-suite evidence. Any later documentation-only reconciliation commit must not be misrepresented as having been independently re-executed; the executable implementation tree remains the tested one unless code/runtime files change.

## ACTIVE_WORK

`BOB_CORE_V1_RUNTIME_CREDENTIAL_AND_QUALIFICATION_WIRING`

The implementation is current-suite green. The next coherent work is to install least-privilege credentials on the persistent runtime and prove read-only identity qualification before any Bob-mediated write canary.

## NEXT_INTENDED_WORK

1. Configure least-privilege persistent Bob runtime credentials for GitHub, Supabase, HF and Cloudflare without committing or exposing secret values.
2. Run `python -m bob.preflight --pretty` on the persistent runtime against Bob + SL + AB; require live Cloudflare identity-anchor read-back.
3. Qualify one approved Bob-repo branch/PR write end to end through the Bob approval boundary.
4. Qualify the persistent DigitalOcean browser runtime and authenticated temporary login/bootstrap path without making the host a general-purpose executor.
5. Install the Bob ChatGPT Project instructions and bind `CHATGPT_TARGET_URL`.
6. Put remote/mobile access behind an authenticated Cloudflare/tunnel boundary while keeping the Python services loopback-only.
7. Only after these are green, consider enabling any project-specific production effect classes.

## OPEN_FINDINGS

- The connected HF account is independently verified as `Reallothesecond` / `6a986fdd2e846637191b1c5e`, and no HF jobs are currently running. A fresh `cpu-basic` job is the available qualified path for the full current-head suite, but it was not dispatched because new compute is a material-spend effect requiring explicit operator authority.\n- Browser Copy-button selectors must be live-qualified against the current ChatGPT UI.
- DigitalOcean runtime and home-egress tunnel are designed but not provisioned. The local bridge is now loopback-only by default; remote exposure still requires authenticated transport.
- SL Cloudflare account ID remains runtime-bound and is verified through its canonical R2 bucket. AB binds its canonical account ID directly but must verify the `autoblog-canary` Worker remotely before Cloudflare identity is trusted.
- The current UI is functional scaffolding, not final product design; it now includes explicit read-only workspace qualification.
- Bob effect approvals currently live in process memory; persistence/resume is a later hardening item. In-memory approvals are nevertheless bound to workspace authority + staged GitHub state and fail closed on drift.
- One Bob runtime currently assumes one active ChatGPT browser conversation at a time; multi-session concurrency is intentionally not yet implemented.

## FIRST_ACTION

Continue `BOB_CORE_V1_RUNTIME_CREDENTIAL_AND_QUALIFICATION_WIRING` from actual branch state. Do not rebuild the protocol or adapters from chat memory.

## HARD_BLOCKERS

- No privileged target-project effect before exact workspace identity verification.
- No external effect is PASS until Bob has verified returned/after-state.
- No model response may expand workspace authority.
- No SL or AB production mutation/deploy/spend is authorized by the current workspaces.
- No secret may be committed to the repository or sent to browser JavaScript.
- Do not make DigitalOcean a general-purpose execution engine merely because it hosts the ChatGPT browser.
