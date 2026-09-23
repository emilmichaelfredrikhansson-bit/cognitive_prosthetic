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
- Product behavior canon: `PRODUCT_PRINCIPLES.md`
- Large-project cognition canon: `docs/BOB_CHUNKING_CONTEXT_ARCHITECTURE.md`
- Module/stateless cognition canon: `docs/BOB_MODULE_COGNITION_ARCHITECTURE.md`
- Bob protocol: `docs/BOB_PROTOCOL_V1.md`
- Manual relay: `docs/BOB_MANUAL_RELAY_V1.md`
- ChatGPT Project instructions: `docs/BOB_CHATGPT_PROJECT_INSTRUCTIONS.md`

## CURRENT_MODE

`DEVELOPMENT`

## CURRENT_EXECUTOR

`CHAT_INTERACTIVE`

## CURRENT_ARCHITECTURE

Bob is a bidirectional closed-loop coordination layer. Its product behavior is governed by `PRODUCT_PRINCIPLES.md`: simple conversational surface, advanced internal orchestration, verified reality, and safe self-hosting.

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
current V1 ChatGPT conversation transport
```

No component is globally smart.

- ChatGPT owns semantic reasoning and code generation.
- Bob owns deterministic I/O, identity/authority checks, execution and verified feedback.
- providers own external state;
- the operator owns material approvals.

The inherited ChatGPT browser bridge is a replaceable cognition transport. **Canonical large-project cognition is nevertheless stateless: one cognition question -> one fresh ChatGPT conversation, with Bob carrying all continuity. The current same-conversation V1 READ/RESULT loop is a temporary transport implementation until Context Compiler continuation exists.** **V1 response capture is canonically the visible ChatGPT Copy action -> clipboard; DOM scraping is legacy-only, while Windows UI Automation is deferred unless real-world robustness requires it.** **Bob V1 runs as Local Companion on the operator's own PC using the operator's existing ChatGPT account/subscription but a separate Bob-managed Chromium profile. All Bob cognition is confined to one dedicated private ChatGPT Project named `Bob`, with Project-only memory as the V1 isolation setting.** Bob API and bridge remain loopback-only, the Bob Project/ChatGPT tab lives in the background, and the Bob UI is brought to the foreground in the same managed browser. DigitalOcean/persistent remote cognition is deferred to V2.

## LAST_COMPLETED

`BOB_MODULE_STATELESS_COGNITION_CANON`

Bob now has a canonical **module-first, stateless cognition architecture** in `docs/BOB_MODULE_COGNITION_ARCHITECTURE.md`.

For Bob-designed software, a module is the pre-implementation cognitive atom: explicit input -> bounded responsibility -> explicit output, connected through contracts/adapters. Bob must not knowingly create a new module that is already too large for one fresh cognition request to understand with its immediate contract neighborhood.

Initial compiled-input policy is codified in `bob/cognition_policy.py`:

```text
new-module design gate = 20,000 tokens
target = 20,000 tokens
hard ceiling = 25,000 tokens
fresh chat per cognition request = required
```

The limits apply to the whole compiled world: relevant mission/invariants + current module + summarized direct producer/consumer neighborhood + exact contracts/reality + current question. The numeric envelope is a learnable engineering parameter; bounded cognition and fresh requests are architectural invariants.

The ChatGPT bridge now exposes `POST /cognition`, which atomically starts a fresh conversation inside the configured Bob Project and sends one prompt. `ChatGPTBridge.cognition(...)` exposes that primitive to Bob Core. The current V1 `_drive` READ/RESULT loop remains intentionally stateful for now because the Context Compiler/durable continuation layer does not yet exist; switching it prematurely would make later fresh chats receive incomplete context.

Canonical large-project cadence is now:

```text
technical problem
-> fresh cognition
-> technical answer

technical answer + relevant mission/system/decision state
-> fresh consequence/Steward cognition
-> NONE / STRUCTURAL / OPERATOR
```

Bob carries all continuity and structure between requests. Operator-owned product/vision/end-goal tradeoffs must be surfaced rather than silently resolved as local engineering choices.

This tranche adds policy/runtime primitives and canon. It does **not** yet implement the durable module graph, Context Compiler, product-vision bootstrap, automatic Steward routing or production replacement of the current stateful driver.

`BOB_RECURSIVE_CHUNKING_AND_CONTEXT_CANON`

Bob now has a canonical large-project cognition architecture in `docs/BOB_CHUNKING_CONTEXT_ARCHITECTURE.md`.

Foundational rule: **no chat owns the project**. Bob owns durable project/work state; ChatGPT threads own bounded cognition work. Large projects are represented as a recursive semantic graph of project/domain/workstream/work-unit nodes plus explicit dependency/interface/contract edges.

A future **Context Compiler** compiles the smallest sufficient context packet for each cognition task from current durable truth: workspace/work-node identity, scope, relevant node summaries/contracts, dependencies, exact relevant files/reality, blockers, authority, provenance/freshness and exit criteria. For new Bob-designed modules, cognition-fit is a pre-implementation gate: the whole module neighborhood must fit the 20k design target before coding starts; Bob must not knowingly build an oversized module and plan to split it later for cognitive reasons.

Cross-cutting changes become explicit parent workstreams with bounded child tasks. Parallel child outcomes converge through bounded Fusion using durable results/contracts/conflicts/evidence rather than entire child transcripts. Completed cognition is distilled back into durable node state, implementation, evidence and follow-up work.

Chunking is semantic rather than arbitrary file/token slicing, and chunking/context strategy itself is a recursively improvable Bob capability. Bob should eventually be able to replace cognition threads deliberately and continue from compiled durable context without loss of project continuity.

A clarified ownership rule now also applies: **Bob carries the global project structure so cognition does not have to.** The durable graph, contracts, dependencies, statuses and provenance live in Bob; each ChatGPT thread receives only the relevant structural slice. Cognition is used when semantic judgment is needed to create or revise that structure, after which Bob persists and carries the result forward. This is deliberate cognitive offloading, not a fixed deterministic task tree.

This tranche is canon/documentation only. It does not change current effect authority or the active Local Companion live-qualification sequence.

`BOB_PRODUCT_PRINCIPLES_AND_SELF_HOSTING_CANON`

Bob now has a dedicated `PRODUCT_PRINCIPLES.md` defining the canonical operator experience and long-term performance target.

The product rule is: **as easy to use as a good ordinary ChatGPT conversation on the surface; as sophisticated as useful underneath.** Operator-facing answers should stay simple by default, with technical depth/evidence progressively disclosed when requested. The operator supplies goals, constraints and material approvals; Bob absorbs orchestration, provider and continuity complexity.

A first-class performance target is now explicit: Bob should be able to drive Signal Lab-scale projects or larger with materially less continuity/tooling/coordination friction than ordinary single-chat work.

Bob is also explicitly **self-hosting**: Bob may use its own bounded workflow to inspect, diagnose, implement, test and improve Bob itself. This creates a recursive capability-improvement loop where better Bob versions can make subsequent development easier. Self-hosting never means self-authorizing: a new Bob version cannot expand its own authority, weaken approval/verification boundaries or declare itself trusted.

`AGENTS.md` now points product/UX/orchestration work to the product canon, and the Bob ChatGPT Project instructions now require simple operator-facing communication plus safe self-hosting semantics.

`BOB_CHATGPT_CAPTURE_V1`

Bob V1's canonical response-capture path is now **ChatGPT's visible Copy action -> browser clipboard**. This is the normal product path and the path to qualify on the operator PC. Direct DOM/text scraping from ChatGPT remains an explicit `legacy_dom` compatibility escape hatch only; it is not a preferred architecture and must not silently become the default again.

Windows UI Automation/accessibility is deferred as a future robustness option only if the Copy->clipboard path proves unreliable in real use. It is not required for V1 and should not displace a working Copy path merely for architectural purity.

This direction matches the current implementation: `CHATGPT_CAPTURE_MODE=copy` is the default, `capture_response(...)` locates ChatGPT's visible Copy control, activates it and reads the resulting clipboard text. No provider authority changed.

`BOB_CHATGPT_PROJECT_ISOLATION_V1`

Bob's ChatGPT-side product boundary is now canonical: use the operator's **same ChatGPT account/Plus subscription**, but through a separate persistent Bob browser profile and one dedicated private ChatGPT Project named **Bob**. Project-only memory remains the current V1 isolation setting, but it is **not** canonical project memory: stateless cognition must be correct without cross-chat recall, and Bob should prefer disabling cross-chat memory influence later if the product allows that while preserving Bob project instructions/isolation.

Normal Local Companion runtime now requires an explicit `BOB_CHATGPT_PROJECT_URL` (legacy `CHATGPT_TARGET_URL` remains compatibility-only). The bridge rejects an empty target, the ChatGPT home page, and non-ChatGPT hosts; every Bob New Chat navigates back to the configured project target before creating another cognition thread. The runtime no longer treats the generic ChatGPT home page as an acceptable cognition target.

The operator may keep using normal ChatGPT in another browser/session at the same time. Bob does not receive authority to inspect or reuse unrelated personal chats or projects. Subscription/account usage limits remain shared because the account is shared.

Two additional Local Companion tests declare the dedicated-project boundary. No provider authority changed and no external provider effect was performed.

`BOB_LOCAL_COMPANION_V1_FOUNDATION`

Bob V1 has been pivoted from remote-first to local-first. `bob_local.py` now starts the loopback Bob API and ChatGPT bridge as child processes, health-gates both, fails fast if either exits, and asks the bridge to open/focus the loopback Bob UI in the same managed Chromium context. The ChatGPT target remains a background tab used for cognition. `setup_bob.bat`, `first_run_bob.bat`, `start_bob.bat` and `.env.local.example` provide the Windows setup/first-run/normal-start path. `.env.local` is gitignored.

The bridge exposes loopback-only `POST /show-ui` and rejects non-loopback companion URLs. Startup now fails closed if the authenticated ChatGPT chat input cannot actually be found instead of reporting a false-ready state. `manual_login.py` uses the configured `CHATGPT_TARGET_URL`. Five new unittest methods declare the Local Companion configuration/safety contract.

Architecture, roadmap, V1 plan, README and remote-runtime docs now state that Local Companion is V1 and DigitalOcean is V2. No provider authority was expanded, no secrets were added, no HF/GitHub Actions compute was dispatched, and no Cloudflare/SL/AB production effect was performed.

`BOB_PROJECT_SEARCH_SETTINGS_INBOX_V1`

Bob now has a real project-scoped search surface backed by a bounded server-side search over only the selected workspace's configured `entry_documents`. Each searched document is read through the existing `github.read_file` Bob READ path; PASS/FAIL is retained per document, results are snippet/line bounded, and no browser-side demo index or fake persistent search state is used. Ctrl/Cmd-K now opens this search instead of pretending to search conversation history.

The Project inspector now exposes read-only project identity/default-branch settings plus a direct read-only ChatGPT Project instructions surface when that document is configured. Existing Providers and Authority sections remain distinct, preserving the access != authority boundary. Pending approvals also have a first-class topbar inbox/count that jumps to the existing approval cards without changing approval semantics.

`BOB_CHATGPT_LIKE_PROJECT_SURFACES`

The ChatGPT-like shell now includes truthful project-context file viewing through Bob's existing `github.read_file` path, local light/dark/system appearance, and collapsible READ activity so project-reality checks are visible without exposing protocol noise. The responsive inspector/scrim behavior was headlessly rendered at desktop and mobile widths; that visual pass caught and fixed a desktop scrim breakpoint bug plus mobile composer send-button alignment.

`BOB_CHATGPT_LIKE_FRONTEND_V1`

Bob now has a ChatGPT-like application shell rather than the earlier form-style cockpit. Workspaces render as Projects in a persistent sidebar; the main surface is a familiar chat/composer; a responsive Project inspector exposes Reality, Authority, Providers and context documents; qualification is rendered as human-readable provider status instead of raw JSON; and pending effects are first-class approval cards with diff/summary plus explicit Approve and Reject actions. The Reject path now consumes the staged pending effect server-side without executing it.

The frontend deliberately does **not** fake persistent conversation history. Recent currently represents only the active UI conversation; true history/resume remains blocked until the browser/runtime can persist and reopen the exact underlying ChatGPT thread.

`BOB_OFFLINE_RUNTIME_CLOSURE_V1`

Bob is now offline-deploy-ready. `deploy/install_runtime.sh` installs an exact Git SHA into an immutable release directory, prepares the venv/Playwright/Xvfb runtime, installs and enables (but deliberately does not start) the loopback-only services, and creates a root-owned empty credential file. `deploy/runtime_doctor.py` verifies local host prerequisites without exposing secrets and can fail closed on missing credentials/profile when those are required. During this work a real serialization defect was found in the committed ChatGPT bridge unit: it contained literal `\\n` sequences. The unit is now a real multiline systemd file, and tests explicitly reject literal escaped newlines.

The persistent runtime credential floor remains staged least-privilege: read-only provider qualification first, then a bounded GitHub write credential only for the approved branch/PR canary. Supabase/Cloudflare/HF write or spend credentials are not required by the current workspaces. Current live Supabase project responses were re-read and contain the expected organization ID directly, so no account-wide project-list permission is required for the normal qualification path.

`BOB_PERSISTENT_RUNTIME_SYSTEMD_CONTRACT`

Bob now has deployment templates for `bob-api.service` and `chatgpt-bridge.service` under `deploy/systemd/`. Both force loopback binding independently of the runtime env file, run as a dedicated unprivileged `bob` identity, use `/etc/bob/bob.env`, and apply basic systemd hardening. The browser bridge gets an explicit writable profile scope at `/var/lib/bob` and launches its headed Chromium inside an ephemeral Xvfb display (`xvfb-run -a`), so a headless Ubuntu host can actually start it. Initial interactive ChatGPT login still requires a separately authenticated temporary display path; remote access remains outside these units and must use a separately authenticated proxy/tunnel boundary.

Bob now includes a read-only runtime preflight entry point at `python -m bob.preflight`. It fails closed when either credential-bearing Python service is configured on a non-loopback host, then delegates provider identity checks to the existing `BobRuntime.qualify_workspace(...)` path for selected or all registered workspaces. The report exposes qualification/capability metadata but never credential values.

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

The branch now declares **58 unittest methods**: the previous 51 plus 7 Local Companion tests in `tests/test_local_companion.py`.

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

The runtime-preflight and systemd-contract isolated checks remain useful narrow evidence, but the HF current-implementation run supersedes them as the main execution-suite evidence.

Post-HF runtime packaging changed after the 29/29 application-suite run. The current deployment tranche was checked independently in the interactive sandbox: `tests/test_runtime_deploy.py` = **8/8 PASS**, `bash -n deploy/install_runtime.sh` = PASS, `py_compile` for the doctor/test = PASS, and `systemd-analyze verify` parsed both unit files; its only diagnostic was the expected absent `/opt/bob/venv/bin/python` because the sandbox is not an installed Bob host. This is deployment-tranche evidence, not a new full-suite run. The new frontend shell was separately checked before commit: `tests/test_frontend_shell.py` = **8/8 PASS**, `node --check frontend/app.js` = PASS and HTML parser validation = PASS. The new Reject backend path is covered by a declared driver test but the full current-head Python suite has not been rerun after that backend change. Any later documentation-only reconciliation commit must not be misrepresented as having been independently re-executed; the executable implementation tree remains the tested one unless code/runtime files change.

The project-search/settings/inbox tranche changes executable frontend and Python code after those earlier checks. In this interactive session, the connector-fetched current `frontend/app.js` parsed successfully in V8; the 11 current frontend contract groups were re-evaluated against the fetched HTML/JS/CSS and passed **11/11**; duplicate HTML IDs were absent and CSS/dialog/form structural balances were clean. The exact new bounded project-search algorithm plus empty-query fail-closed behavior was exercised in an isolated sandbox smoke harness: **2/2 PASS**; the new API route block also compiled as valid Python syntax. This is targeted tranche evidence only. The full current-head Python suite has **not** been rerun, and no HF/GitHub Actions compute was dispatched.

The Local Companion tranche was then reconciled directly from the current branch through the GitHub connector. The branch declares exactly **56** unittest methods, including **5** Local Companion tests. Connector-fetched `bob_local.py`, `chatgpt_api_server.py`, the three Windows batch launchers, `.env.local.example`, README and V1 plan contain no committed secret-like tokens, no V1 `0.0.0.0` bind configuration, and no accidental literal escaped-newline serialization. Isolated copies of the committed Local Companion loopback helper logic and companion-URL validator compiled and passed smoke checks for localhost/IPv4/IPv6 loopback plus rejection of public/wildcard targets. This is targeted helper evidence, not a full current-head suite or a live Playwright/ChatGPT qualification.

The dedicated ChatGPT Project isolation tranche was then reconciled from current branch state. The branch now declares exactly **58** unittest methods, including **7** Local Companion tests. The new runtime contract requires `BOB_CHATGPT_PROJECT_URL`, rejects an empty target, the generic ChatGPT home page and non-ChatGPT hosts, while preserving a separate Bob-managed browser profile on the same account. Connector inspection found no wildcard V1 bind configuration and no committed secret-like tokens in the touched runtime/config files. Project-only memory remains a live operator-side ChatGPT setting to verify during the Windows canary; Bob cannot truthfully claim that account setting from repository code alone.

## ACTIVE_WORK

`BOB_LOCAL_COMPANION_V1_LIVE_QUALIFICATION`

The code/config/documentation foundation for Local Companion is landed. The next meaningful work is no longer remote host provisioning; it is live qualification on the operator's Windows PC where a real authenticated ChatGPT session can exist.

## NEXT_INTENDED_WORK

1. On the operator PC, check out the current `feat/bob-core-v1` head and run `setup_bob.bat`.
2. In the operator's normal ChatGPT account, create/open the private project `Bob`, set its Memory to **Project-only memory**, and copy its exact project URL.
3. Put that URL in machine-local `.env.local` as `BOB_CHATGPT_PROJECT_URL=...`.
4. Run `first_run_bob.bat`, authenticate the Bob browser profile with the **same ChatGPT account**, and verify Bob opens in the foreground while the dedicated Bob Project remains the background cognition surface.
5. Qualify one ordinary Bob chat turn, then a real `BOB.READ -> BOB.RESULT -> cognition` loop.
6. Verify a second Bob New Chat is created inside the same Bob Project and never on the ChatGPT home page/personal history.
7. Qualify approval and reject from the local UI, then perform one approved Bob-repository branch/PR canary with read-back evidence.
8. Only after Local Companion is useful in daily work, resume V2 DigitalOcean/mobile design.
9. Continue frontend parity in parallel only where it improves the local product; do not fake conversation history, uploads or authority.

## OPEN_FINDINGS

- The current interactive development environment cannot run the real local managed browser against the operator's authenticated ChatGPT account. The canonical Copy-button -> clipboard capture, background-tab behavior and exact ChatGPT Project targeting therefore remain operator-PC qualification items. Windows UI Automation is not a V1 blocker.
- Seven Local Companion unittest methods are declared on the branch, including the dedicated ChatGPT Project boundary. The full current-head Python suite has not been rerun after this tranche. No paid/remote compute was dispatched.
- The connected HF account was previously verified as `Reallothesecond` / `6a986fdd2e846637191b1c5e`; a fresh HF suite remains a material-spend effect and is not necessary before the first local canary.
- True resumable Bob conversation history remains blocked until Bob can persist and reopen the exact underlying ChatGPT thread identity/URL. Do not substitute localStorage history.
- Bob effect approvals remain in process memory. Restart persistence is later hardening; current approvals are still bound to workspace authority + staged GitHub state and fail closed on drift.
- One Bob runtime assumes one active ChatGPT browser conversation at a time. Multi-session concurrency is intentionally not part of V1.
- The V2 systemd/Xvfb/remote-host package remains preserved as future infrastructure; it is not required to test or use V1 locally.

## FIRST_ACTION

Run the Local Companion live canary on the operator's Windows PC from the current branch: `setup_bob.bat` -> create/configure private ChatGPT Project `Bob` with Project-only memory -> set `BOB_CHATGPT_PROJECT_URL` -> `first_run_bob.bat` -> verify foreground Bob/background Bob Project -> one read-only chat loop. Do not move to DigitalOcean unless V1 has first been proven useful locally.

## HARD_BLOCKERS

- No privileged target-project effect before exact workspace identity verification.
- No external effect is PASS until Bob has verified returned/after-state.
- No model response may expand workspace authority.
- No SL or AB production mutation/deploy/spend is authorized by the current workspaces.
- No secret may be committed to the repository or sent to browser JavaScript.
- Do not make DigitalOcean a general-purpose execution engine merely because it hosts the ChatGPT browser.
