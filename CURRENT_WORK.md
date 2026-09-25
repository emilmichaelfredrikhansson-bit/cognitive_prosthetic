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
- Recursive self-improvement canon: `docs/BOB_RECURSIVE_SELF_IMPROVEMENT_ARCHITECTURE.md`
- Knowledge Fabric canon: `docs/BOB_KNOWLEDGE_FABRIC_ARCHITECTURE.md`
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

The inherited ChatGPT browser bridge is a replaceable cognition transport. **Canonical large-project cognition is stateless: one cognition question -> one fresh ChatGPT conversation, with Bob carrying all continuity. Bob now has an executable stateless module path (`/bob/module-turn`) that recompiles the complete bounded module problem after Bob-owned READ/effect results and calls fresh `/cognition` each round. The ordinary `/bob/turn` path remains legacy/stateful until module selection and context compilation become the default orchestration path.** **V1 response capture is canonically the visible ChatGPT Copy action -> clipboard; DOM scraping is legacy-only, while Windows UI Automation is deferred unless real-world robustness requires it.** **Bob V1 runs as Local Companion on the operator's own PC using the operator's existing ChatGPT account/subscription but a separate Bob-managed Chromium profile. All Bob cognition is confined to one dedicated private ChatGPT Project named `Bob`, with Project-only memory as the V1 isolation setting.** Bob API and bridge remain loopback-only, the Bob Project/ChatGPT tab lives in the background, and the Bob UI is brought to the foreground in the same managed browser. DigitalOcean/persistent remote cognition is deferred to V2. **Recursive self-development is now canonicalized as a low-priority daytime background lane: interactive work always wins, background mutation uses isolated worktree/branch state plus semantic leases, and promotion remains a separate authority boundary. Bob's compounding cognition model is a provenance-rich Knowledge Fabric whose relevant verified patterns/failures/playbooks/examples/source pointers are selected into the existing bounded context envelope rather than dumped wholesale into prompts.**

## LAST_COMPLETED

`BOB_REPOSITORY_EXECUTION_AND_PROCESS_SUPERVISION_V1`

Status: **IMPLEMENTED / DETERMINISTIC_GREEN / LIVE_EXECUTION_GREEN / LIVE_COGNITION_TRANSPORT_GREEN**.

Active local development branch for this tranche:
- `feat/bob-execution-ledger-v1`
- tranche base/recovery commit: `42bfa1e7a1a71ade25cb4d845149d5af2c4d52d4`
- canonical `feat/bob-core-v1` remained at `098e6ac9f2adb47e7174c4db8ad2d0b1639d1279` during qualification;
- **no merge/push/promotion to canonical was performed**.

Three execution layers are now mechanically separate:

```text
Repository Execution
  <= 3 ACTIVE/AWAITING_APPROVAL runs per repository
  repository-scoped ledger / leases / worktrees / FIFO integration queue

Cognition
  <= 1 RUNNING cognition per run
  run_id -> cognition_id -> request_id
  request-private browser response queues

Local Process Lifecycle
  ProcessSupervisor-owned Bob children / ports / logs / cleanup
  RDC is control transport, not process ownership
```

Repository execution:
- every `ExecutionLedger` persists and validates `repository_full_name`, stable `repository_id`, resolved `repo_root` and `canonical_ref`; identity mismatch fails closed;
- every `ExecutionCoordinator` verifies local Git `origin` and canonical ref before opening its repo domain;
- `max_parallel_runs_per_repository=3`; a fourth eligible run is durable `QUEUED/CAPACITY`;
- semantic leases, worktree root and serialized integration queue are repository-local;
- `RepositoryCoordinatorRegistry` maps workspaces onto stable repository IDs, so two workspaces targeting one repository share one coordinator/ledger/cap;
- repositories without a configured local binding cannot start local execution;
- queued runs do not receive worktrees; attempting integration readiness while non-active fails semantically before branch resolution;
- stale integration candidates still require re-ground/rebase + deterministic reverification;
- ledger/coordinator never merge, push or promote.

Cognition/bridge correlation:
- browser requests use unique request IDs and private result queues rather than one global consumable result queue;
- duplicate request IDs fail closed;
- late/timed-out results cannot be consumed by a later request;
- run/cognition/request tags survive the bridge boundary;
- restart converts any ledger cognition still `RUNNING` to `INTERRUPTED`.

Process supervision:
- `bob/process_supervision.py` owns only explicitly started Bob children;
- durable records include process/run/repository identity, purpose, PID + creation identity, class, ports, log path and cleanup policy;
- executable allowlisting and argv spawning replace arbitrary shell ownership;
- unknown external processes/port owners are never auto-killed;
- PID reuse/identity mismatch fails closed;
- long-lived output goes to bounded-tail log files;
- completed probes/tests are explicitly reaped;
- no automatic restart loop exists;
- Windows venv redirectors are handled as owned process trees: after health, each declared port is bound to the exact listener PID + creation-time identity; stop verifies ownership and terminates the verified root tree; terminated process objects are not considered live unless Windows reports `STILL_ACTIVE`.

Deterministic verification on the operator PC:
- full suite: **115/115 PASS** before final documentation-only edits;
- execution/worktree/server focused suite: **17/17 PASS**;
- process supervision + Local Companion focused suite: **26/26 PASS**;
- queued-run integration-readiness regression: PASS;
- `git diff --check`: PASS.

Current bounded-module measurements under `BOB_TOKEN_ESTIMATE_V1` are all below the 15k hard cap; remeasure after any source/test/contract edit before promotion.

Live acceptance evidence:
- Local Companion was stopped and restarted through `ProcessSupervisor`;
- Bob API and ChatGPT bridge health returned ready/running;
- supervisor state showed exactly two active long-lived runtime records, each with exact listener ownership for ports 5002/5001;
- old runtime process trees were stopped without leaving listener children; ports became free before restart;
- Bob repo: three runs became `ACTIVE`; run four became `QUEUED/CAPACITY`;
- an overlapping lease became `QUEUED/SCOPE_CONFLICT:<run>`;
- active runs had distinct branches and distinct external worktree paths;
- a logically separate local Git fixture repository admitted its own three active runs independently;
- FIFO integration planning returned `READY_TO_INTEGRATE` for queue head and `WAIT_FOR_EARLIER_INTEGRATION` for the next candidate;
- restart recovery converted the intentionally interrupted live cognition from `RUNNING` to `INTERRUPTED`;
- acceptance runs were cancelled, acceptance worktrees removed, final Bob execution state returned to **0 active / 0 integration queue**;
- RDC reported **no active terminal sessions** after cleanup.

Fresh-cognition / visible-Copy live qualification:
- the earlier 16:36 canary reached "message sent" but never reached the assistant-completion/Copy signal before operator abort; its exact root cause remains unproven;
- the failure is **not reproducible on the current transport**: six bounded fresh-cognition probes completed successfully through the canonical visible Copy -> browser clipboard path, including Bob UI foreground / ChatGPT background operation;
- returned tokens were exact and request-correlated; the final normal-runtime probe returned `BOB_FINAL_COPY_QUALIFIED` in 10.64 s with Bob API and bridge health green;
- a three-request consecutive fresh-chat series completed 3/3 in 10.45-11.86 s, and the two preceding diagnostic/background probes also completed exactly;
- `wait_for_new_assistant_copy` now emits bounded structural diagnostics every 15 s and records the final snapshot on timeout: assistant count, visible author roles, message-level Copy count and conversation-turn count. It logs no message content;
- current executable verification after this hardening: `py_compile` PASS, focused Local Companion **18/18 PASS**, full suite **115/115 PASS**, `git diff --check` PASS;
- treat the old stall as a historical intermittent transport/UI/model stall unless new evidence localizes it. If it recurs, the structural snapshot should distinguish "no assistant turn", "assistant without message-level Copy", and later capture/clipboard failure without guessing.

Remaining work / boundaries:
- next live stateless-module qualification is a forced Bob-owned `BOB.READ -> BOB.RESULT -> recompile -> second fresh cognition` continuation;
- SL/AB obtain independent repo coordinators only after their local repo paths are explicitly configured (for example through repository bindings); they do not consume Bob's slots;
- a future `BOB_MACHINE_SCHEDULER` may impose a separate higher machine resource cap for CPU/RAM/browser/API pressure; it is not the repository safety cap and is not implemented here;
- the browser transport remains one serialized Playwright worker, so three repository workers do not yet mean three simultaneous model generations;
- the oversized `BOB_RUNTIME_ORCHESTRATION` recursive self-repair canary is no longer blocked by basic fresh-cognition Copy capture, but should follow the remaining READ/effect continuation qualification rather than skipping it.

Previous completed/canonical work remains below.

`BOB_RECURSIVE_SELF_IMPROVEMENT_AND_KNOWLEDGE_FABRIC_CANON`

The long-term recursive objective is now explicit:

> **Every useful cognition cycle should raise the starting floor for future relevant cognition by converting transient reasoning into durable, verified cognitive infrastructure.**

Two new canonical architecture documents are source-of-truth for this direction:

- `docs/BOB_RECURSIVE_SELF_IMPROVEMENT_ARCHITECTURE.md`
- `docs/BOB_KNOWLEDGE_FABRIC_ARCHITECTURE.md`

Canonical recursive/background behavior:
- Bob may work quietly while the operator PC is awake; shutdown/restart must not lose continuity because durable state, not a chat/process, carries the loop;
- self-development is a low-priority lane and **interactive work always wins**;
- background mutation uses an isolated worktree/branch or equivalent isolated mutable state;
- semantic module/work-node leases prevent interactive and background workers from mutating the same scope concurrently;
- unattended work may explore, test, checkpoint, commit and discard candidates only inside existing granted authority;
- promotion/merge into canonical Bob state is a separate authority class;
- repository deletion, protected-branch force push/deletion, repository/ruleset administration, secrets administration and unauthorized production mutation/deploy/spend stay outside the normal self-development capability surface and should also be denied provider-side with least-privilege credentials;
- unattended safety target: **even worst-plausible cognition must not be sufficient to destroy or silently promote canonical project state**;
- every non-trivial cycle should reflect on expected vs observed outcome and distill reusable evidence-backed learning.

Canonical Knowledge Fabric behavior:
- Bob may accumulate a very large external knowledge body because most items cost **zero cognition tokens until selected**;
- first-class reusable classes are verified knowledge/decisions, skills/playbooks, reference implementations/examples and failure memory;
- maturity is `OBSERVATION -> CANDIDATE_LESSON -> VERIFIED_PATTERN -> CANONICAL_PRACTICE`;
- model output alone is never verified reusable knowledge;
- provenance, freshness, source/evidence pointers and supersession lineage are first-class;
- the module/work graph tells Bob **where** a problem lives; the Knowledge Fabric tells Bob **what prior verified experience may help**;
- the Context Compiler retrieves only the smallest relevant knowledge slice inside the existing 20k target / 25k hard ceiling and prefers source pointers/direct GitHub inspection over injecting large bodies when practical;
- Bob may learn recurring cognition failure modes and selectively include concise corrective warnings/checklists when evidence says they apply;
- the compounding principle is: **no good thought should need to be thought from zero twice**.

Product Principles, Constitution, Architecture, Roadmap, AGENTS, ChatGPT Project instructions, chunking/context canon and module/stateless canon now point at these contracts. No authority was expanded.

The dedicated Bob ChatGPT Project now also has an **exact canonical cognition bootloader payload** in `docs/BOB_CHATGPT_PROJECT_INSTRUCTIONS.md`, versioned as `BOB_COGNITION_CONTRACT_VERSION=1`. It is intentionally limited to stable invariants; dynamic state remains in Bob/GitHub/Knowledge Fabric and compiled context. Current payload length is 6,064 characters. Runtime version-sync enforcement is still pending.

`BOB_LOCAL_STATELESS_LIVE_QUALIFICATION`

The operator-PC Local Companion achieved the first real stateless-cognition proof before later branch changes:

- Windows setup/runtime was made portable and the then-current full suite reached **79/79 PASS** at exact commit `008728c82138b6abb6ddfa5fe7e42d4b63c43242`;
- the dedicated Bob ChatGPT Project started successfully through the managed Chromium profile;
- `POST /bob/module-graph` returned 200 against real local runtime/GitHub state;
- a real `POST /bob/module-turn` on compliant `BOB_PROTOCOL` opened fresh ChatGPT cognition, re-grounded against connected GitHub, returned through visible Copy/clipboard transport, parsed a raw copied `BOB.DONE`, and completed with HTTP 200 / `status=DONE`;
- live runtime work discovered and fixed Windows stdio encoding, slow per-character prompt typing, locale-sensitive Copy capture, user-vs-assistant Copy ambiguity and Copy transport stripping markdown fences;
- the live cognition review itself identified real protocol/documentation inconsistencies, which were then corrected and tested.

This historical proof established that the architecture can close the loop in reality. The later execution-ledger head has now separately passed a fresh operator-PC full suite and basic fresh-cognition visible-Copy qualification; Bob-owned READ and approval-bound effect continuations still require their own current-head live qualification.

Previous completed implementation/canon remains below for historical handoff continuity.

`BOB_MODULE_GRAPH_CONTEXT_COMPILER_V1`

The first executable vertical slice of Bob's module/stateless architecture is now implemented.

Repo-native durable state:
- `.bob/module_graph.json` uses `BOB_MODULE_GRAPH_V1`;
- Bob's workspace points to that graph through `context.module_graph`;
- graph identity is bound to workspace code + stable GitHub repository ID;
- module paths have single ownership inside the graph;
- producer/consumer references are validated.

Module footprint:
- `bob/module_graph.py` reads every manifest-owned source/test/contract path from current GitHub reality;
- `BOB_TOKEN_ESTIMATE_V1` deterministically measures `ceil(UTF-8 bytes / 3)` per file and sums the module;
- this is a versioned conservative V1 measurement proxy, **not** a claim to use ChatGPT's exact tokenizer;
- the active hard rule is <=15,000 tokens under the active canonical measurement contract.

Context compilation:
- `bob/context_compiler.py` emits `BOB_COMPILED_CONTEXT_V1`;
- packets contain repository/ref identity, module summary/footprint, direct-neighbor summaries, source pointers, the original bounded problem, hard invariants and durable continuation results;
- cognition is explicitly instructed that connected GitHub is implementation truth and Bob summaries are navigation/compression.

Stateless runtime:
- `POST /bob/module-turn` starts bounded module work;
- `POST /bob/module-graph` exposes measured graph/module status;
- `BobRuntime._drive_module(...)` uses only `bridge.cognition(...)`, never legacy `send(...)`;
- after every Bob-owned READ result, Bob recompiles the original problem + current graph/reality + durable results and opens another fresh cognition request;
- after an approved effect, the effect receipt is likewise folded into a newly compiled fresh request;
- >15k modules enter `ARCHITECTURE_REPAIR` mode and cannot claim `BOB.DONE` while still oversized.

Bob's initial graph intentionally has `coverage=PARTIAL`. Current measured footprint evidence using the exact V1 measurement rule on current branch content:

```text
BOB_PROTOCOL              3,236   compliant
BOB_MODULE_COGNITION      13,824   compliant
BOB_RUNTIME_ORCHESTRATION 19,040  NON-COMPLIANT / MIGRATION_REQUIRED
```

The oversized runtime node is inherited/legacy architecture and is now explicitly marked `MIGRATION_REQUIRED`; it is the natural first self-hosting decomposition target.

Important current boundary: this tranche does **not** make every Bob chat stateless. Ordinary `/bob/turn` remains stateful, graph coverage is partial, product-vision bootstrap/durable work distillation are not implemented, and an architecture repair that writes GitHub still remains subject to Bob's existing approval authority. No authority was expanded.

Current-head execution tests have not yet been run in this development session because the available local container cannot resolve github.com and no material-spend remote job was dispatched. New contract tests declare fresh READ continuation, fresh post-approval continuation, oversize-DONE rejection, module status measurement, route exposure and workspace graph binding.

`BOB_MODULE_STATELESS_COGNITION_CANON`

Bob now has a canonical **module-first, stateless cognition architecture** in `docs/BOB_MODULE_COGNITION_ARCHITECTURE.md`.

For Bob-designed software, a module is the pre-implementation cognitive atom: explicit input -> bounded responsibility -> explicit output, connected through contracts/adapters. Bob must not knowingly create a new module that is already too large for one fresh cognition request to understand with its immediate contract neighborhood.

Cognition/module policy is codified in `bob/cognition_policy.py`:

```text
module hard cap = 15,000 tokens
compiled-context target = 20,000 tokens
compiled-context hard ceiling = 25,000 tokens
fresh chat per cognition request = required
```

The 15k cap is known to architecture cognition **before module boundaries are designed**. ChatGPT should therefore choose responsibilities/contracts so each module is expected to remain <=15k when mature, not merely while its initial scaffold is small. Bob later enforces the actual size deterministically.

If implementation would push a module above 15k, that module shape is invalid. Bob should route a fresh architecture-cognition problem and recheck the resulting graph until all affected modules are compliant. This is backend work and should not interrupt the operator unless the reorganization creates a genuine product/vision/end-goal decision.

The 20k/25k limits apply to the whole compiled cognition world: relevant mission/invariants + current module + summarized direct producer/consumer neighborhood + exact contracts/reality + current question.

The ChatGPT bridge now exposes `POST /cognition`, which atomically starts a fresh conversation inside the configured Bob Project and sends one prompt. `ChatGPTBridge.cognition(...)` exposes that primitive to Bob Core. The current V1 `_drive` READ/RESULT loop remains intentionally stateful for now because the Context Compiler/durable continuation layer does not yet exist; switching it prematurely would make later fresh chats receive incomplete context.

Canonical large-project cadence is now:

```text
Bob durable structure + source pointers
-> fresh cognition
-> direct GitHub re-grounding when implementation truth matters
-> solve bounded problem
-> check relevant contract/module/product impact
-> Bob verifies/persists
-> next fresh cognition
```

There is no mandatory second-stage reviewer. A separate review/meta cognition request is optional for difficult, cross-cutting, security or integration work.

Bob carries continuity and structural routing; GitHub carries implementation truth; ChatGPT may inspect that truth directly. Operator-owned product/vision/end-goal tradeoffs must still be surfaced rather than silently resolved as local engineering choices.

That earlier canon tranche has now been partially realized by `BOB_MODULE_GRAPH_CONTEXT_COMPILER_V1` above. The remaining gaps are default module routing for ordinary Bob chat, full graph coverage, product-vision bootstrap, durable work-result distillation, and live end-to-end qualification.

`BOB_RECURSIVE_CHUNKING_AND_CONTEXT_CANON`

Bob now has a canonical large-project cognition architecture in `docs/BOB_CHUNKING_CONTEXT_ARCHITECTURE.md`.

Foundational rule: **no chat owns the project**. Bob owns durable project/work state; ChatGPT threads own bounded cognition work. Large projects are represented as a recursive semantic graph of project/domain/workstream/work-unit nodes plus explicit dependency/interface/contract edges.

The first **Context Compiler V1** now compiles module-scoped source-grounded packets; the broader project/workstream compiler remains incomplete. Its target contract is to compile the smallest sufficient context packet for each cognition task from current durable truth: workspace/work-node identity, scope, relevant node summaries/contracts, dependencies, exact relevant files/reality, blockers, authority, provenance/freshness and exit criteria. For new Bob-designed modules, the 15k hard module cap is supplied to architecture cognition before boundaries are chosen, so mature module size is constrained from inception rather than repaired only after growth.

Cross-cutting changes become explicit parent workstreams with bounded child tasks. Parallel child outcomes converge through bounded Fusion using durable results/contracts/conflicts/evidence rather than entire child transcripts. Completed cognition is distilled back into durable node state, implementation, evidence and follow-up work.

Chunking is semantic rather than arbitrary file/token slicing, and chunking/context strategy itself is a recursively improvable Bob capability. Bob should eventually be able to replace cognition threads deliberately and continue from compiled durable context without loss of project continuity.

A clarified ownership rule now also applies: **Bob carries the global project structure so cognition does not have to.** The durable graph, contracts, dependencies, statuses and provenance live in Bob; each ChatGPT thread receives only the relevant structural slice. Cognition is used when semantic judgment is needed to create or revise that structure, after which Bob persists and carries the result forward. This is deliberate cognitive offloading, not a fixed deterministic task tree.

The original recursive chunking tranche was canon/documentation only; the module graph/compiler vertical slice is now executable as described above. Effect authority remains unchanged.

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

The dedicated ChatGPT Project isolation tranche was then reconciled from its branch state at that time. Since then the module/stateless vertical slice has expanded the current branch to exactly **74** declared unittest methods, including **8** module-context tests and **4** server-surface tests. The new runtime contract requires `BOB_CHATGPT_PROJECT_URL`, rejects an empty target, the generic ChatGPT home page and non-ChatGPT hosts, while preserving a separate Bob-managed browser profile on the same account. Connector inspection found no wildcard V1 bind configuration and no committed secret-like tokens in the touched runtime/config files. Project-only memory remains a live operator-side ChatGPT setting to verify during the Windows canary; Bob cannot truthfully claim that account setting from repository code alone.

## ACTIVE_WORK

`BOB_MODULE_STATELESS_VERTICAL_QUALIFICATION`

The first executable module graph + Context Compiler + fresh-cognition path is landed and its basic live `module-turn -> fresh ChatGPT -> GitHub re-ground -> BOB.DONE` path has been proven on the operator PC at exact earlier commit `008728c82138b6abb6ddfa5fe7e42d4b63c43242`.

Remaining qualification before the stateless vertical can be considered closed:
- rerun the full suite and Local Companion on **current head** after later implementation/canon changes;
- force at least one Bob-owned `BOB.READ -> BOB.RESULT -> recompile -> second fresh cognition` continuation live;
- qualify one approval-bound module effect and its post-effect fresh continuation live;
- use the oversized runtime module as the first end-to-end self-hosting architecture-repair canary.

Current deterministic `BOB_TOKEN_ESTIMATE_V1` measurement on branch content after the new canon:

```text
BOB_PROTOCOL               4,152   compliant
BOB_MODULE_COGNITION      14,766   compliant (234 tokens headroom)
BOB_RUNTIME_ORCHESTRATION 19,374   MIGRATION_REQUIRED
```

`BOB_MODULE_COGNITION` is now very close to the 15k hard cap. Do not add further responsibility to that module without remeasurement/reorganization.

The graph still has explicit `coverage=PARTIAL`. Recursive self-development and Knowledge Fabric are canonical architecture/roadmap now, but their runtime modules, durable queue, worktree/lease machinery, knowledge store and retrieval pipeline are **not yet implemented**.

## NEXT_INTENDED_WORK

1. Reconnect the operator PC/Remote Desktop Commander, pull current `feat/bob-core-v1`, run the full unittest suite, and restart Local Companion from current head.
2. Re-qualify `POST /bob/module-graph` on current head and record current live footprints.
3. Force one bounded `/bob/module-turn` to emit a Bob-owned READ; verify Bob executes it, recompiles original problem + result, and opens a **second fresh ChatGPT conversation**.
4. Qualify one approval-bound module Git effect on the same working ref and verify post-effect read-back + fresh cognition continuation.
5. Use `BOB_RUNTIME_ORCHESTRATION` (>15k) as the first architecture-repair canary and return all affected target modules to <=15k without authority expansion.
6. Split/reorganize `BOB_MODULE_COGNITION` before meaningful additional responsibility if projected growth would cross 15k.
7. Make module selection/Context Compiler routing the default behind ordinary Bob chat.
8. Add cognition-contract synchronization: runtime/preflight should detect stale/missing `BOB_COGNITION_CONTRACT_VERSION` in the configured Bob Project instructions and fail closed or require re-sync.
9. Implement Phase 3.75 foundations in this order: durable self-development queue/state -> isolated selfdev worktree/branch lifecycle -> semantic leases + interactive pre-emption -> checkpoint/revert/discard -> separate promotion gate.
10. Implement Knowledge Fabric V1: item schema/provenance/freshness/maturity -> first distilled Bob failures/patterns/reference items -> bounded retrieval into Context Compiler -> retrieval/effectiveness metrics.
11. Prove one daytime unattended multi-cycle canary and one PC restart/resume canary, producing a concise operator digest rather than background chatter.
12. Product-vision/bootstrap, richer durable result distillation and reusable module/template extraction remain coupled follow-up work.
13. DigitalOcean/mobile persistence remains V2 and is not a prerequisite.

## OPEN_FINDINGS

- The module graph has explicit `coverage=PARTIAL`; it is not yet a complete semantic map of Bob.
- `BOB_TOKEN_ESTIMATE_V1` is deterministic `ceil(UTF-8 bytes / 3)`, not ChatGPT's exact tokenizer.
- `BOB_MODULE_COGNITION` is currently about **14,766 / 15,000** measured tokens; it is compliant but has almost no growth headroom.
- `BOB_RUNTIME_ORCHESTRATION` is about **19,374 / 15,000** and remains the intended architecture-repair canary.
- Normal module effects remain one effect per fresh cognition request, manifest-owned path/ref constrained; architecture-repair scope is wider but still approval/authority/read-back bounded.
- Ordinary `/bob/turn` is still stateful. Statelessness is executable through `/bob/module-turn`, not yet automatic for every operator message.
- The live operator-PC proof covered module graph and a direct GitHub-grounded DONE turn; a Bob-owned READ continuation and approval-bound effect continuation still need live qualification.
- Current execution-ledger branch has now received a fresh operator-PC full-suite (**115/115 PASS**) plus six successful basic fresh-cognition visible-Copy/clipboard probes; current-head Bob-owned READ continuation and approval-bound effect continuation remain unqualified live.
- Remote Desktop Commander was offline at the latest reconciliation, so current-head local runtime state could not be re-read.
- Self-development background runtime is canon, not implementation: no durable selfdev queue, separate worktree lifecycle, lease manager, background scheduler/pre-emption or promotion gate exists yet.
- Knowledge Fabric is canon, not implementation: no item store/schema, maturity transitions, retrieval/ranking or compiler injection exists yet.
- Project Instructions bootloader text is canonical/versioned, but the runtime does not yet verify that the configured ChatGPT Project actually contains the expected `BOB_COGNITION_CONTRACT_VERSION`.
- Bob effect approvals remain in process memory; restart persistence is still later hardening.
- V2 systemd/Xvfb/remote-host material remains preserved but is not required for V1.

## FIRST_ACTION

When the operator PC connector is available: pull current head -> run full suite -> restart Local Companion -> requalify module graph -> force one Bob-owned READ continuation -> force one approval-bound effect continuation. Then use the >15k runtime module as the self-hosting repair canary before beginning Phase 3.75 runtime implementation.

## HARD_BLOCKERS

- No privileged target-project effect before exact workspace identity verification.
- No external effect is PASS until Bob has verified returned/after-state.
- No model response may expand workspace authority.
- No SL or AB production mutation/deploy/spend is authorized by the current workspaces.
- No secret may be committed to the repository or sent to browser JavaScript.
- Do not make DigitalOcean a general-purpose execution engine merely because it hosts the ChatGPT browser.
- Unattended self-development must not receive repository deletion/admin, protected-branch force-push/deletion, secrets administration or unauthorized production deploy/mutation/spend capability.
- Self-development may not promote/merge itself into canonical Bob state merely because its own cognition reports success.
- Knowledge Fabric content never grants authority and model output alone never becomes verified reusable knowledge.
