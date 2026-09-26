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
- Effect authority: `docs/BOB_EFFECT_AUTHORITY_V1.md`
- Stateless module runtime: `docs/BOB_STATELESS_MODULE_RUNTIME_V1.md`
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

## ACTIVE_EXECUTOR_QUALIFICATION_2026_09_26

Campaign work execution is now implemented locally on `feat/bob-execution-ledger-v1` as two separate bounded modules:

- `BOB_CAMPAIGN_REPO_ADAPTER`: exact coordinator-owned worktree confinement, bounded repository reads, hash-bound isolated branch effects, verified commits and deterministic verification;
- `BOB_CAMPAIGN_WORK_EXECUTOR`: consumes only exact `BOB_WORK_CAMPAIGN_WORKER.ready` bindings, carries `run_id -> cognition_id -> request_id`, uses fresh cognition, persists pending effects/outcomes, yields to queued interactive work at clean cognition boundaries and calls successful `queue.finish` only after deterministic verification;
- executor owns no run creation, execution capacity, merge, push, integration or promotion authority;
- model output cannot widen workspace write authority;
- cognition/submission failure is durable and is not transparently retried;
- restart can adopt only an exact already-prepared/committed pending effect; dirty or ambiguous recovery fails closed;
- Bob API exposes `GET /bob/campaigns/<campaign_id>/executor` and `POST /bob/campaigns/<campaign_id>/executor/cycle`;
- Bob-internal successful executor verification is configured to run the full unittest suite inside the exact isolated worktree.

Deterministic pre-live qualification:
- focused executor/adapter/cognition/server tranche: **27/27 PASS**;
- full suite: **207/207 PASS** in 69.351 s;
- module graph parses with 17 modules;
- measured footprints: `BOB_CAMPAIGN_REPO_ADAPTER=8,525/15,000`, `BOB_CAMPAIGN_WORK_EXECUTOR=14,264/15,000`, `BOB_EXECUTION_LEDGER=14,800/15,000`, `BOB_WORK_CAMPAIGN_QUEUE=14,570/15,000`, `BOB_WORK_CAMPAIGN_WORKER=13,061/15,000`;
- `git diff --check`: PASS.

Live qualification status:
- the deterministic-green executor implementation is checkpointed locally at `5345fc53ee8333c5233563a472ae3b1d9126b153` (`Implement bounded campaign work executor`); this local branch is ahead of `origin/feat/bob-execution-ledger-v1`, which remains at `9afd018c6d6d66c6604a7e51106a2e46ac7f13c9`;
- Local Companion was restarted and the executor routes were live without any transport-only cognition probe;
- bounded live canary `campaign-246969189d2b` admitted `campaign-work-57919fb59b21` as exact run `run-4ee13a8c6040` from base `5345fc53...`;
- its first fresh cognition `cog-332cf878c9b5` / request `req-3ddf6dd42002` failed before any observed ChatGPT conversation turn with `CHATGPT_SUBMISSION_FAILED:NO_CONVERSATION_TURN`;
- executor persisted exact `BLOCKED_COGNITION` with `effect_count=0`, `pending_effect=false`, `verification_count=0`; the intended canary file was never created, the isolated worktree remained clean at `5345fc53...`, and the run was explicitly parked with `promotion_authority=NONE` / `auto_merge=false`;
- restart persistence of that blocked executor outcome is LIVE GREEN: after supervisor stop/start, the same executor outcome/run/checkpoint remained durable and the ChatGPT bridge returned `ready=true`; no cognition was replayed;
- follow-up submission-materialization hardening now observes sanitized conversation-ID transition and a previously populated composer clearing in addition to message/turn counters. It is wired into the send path, remains covered by transient/rate-limit detection, and has deterministic qualification **53/53 PASS** focused + **209/209 PASS** full suite, `py_compile` PASS and `git diff --check` PASS;
- Local Companion has been restarted onto that deterministically qualified transport code, still without issuing another cognition request.

Latest reconciled live qualification:
- V8 proved the transport/capture path was completing cognition, but the fresh model repeated the same completed `BOB.READ id=v8-status-1` for six rounds, producing `effect_count=0`. Root cause was continuation framing/protocol progression, not basic ChatGPT submission.
- The reconciled executor prompt now supplies structured `continuation_results`, explicitly instructs fresh cognition to continue rather than restart, and rejects a repeated completed READ id fail-closed.
- DEV CANARY V12 `campaign-0f0e61877df7` / `campaign-work-cd46dc5916ef` / `run-aab176b805d3` is the first genuine autonomous executor E2E GREEN: four fresh-cognition rounds progressed `repo.status READ -> repo.create_file EFFECT -> repo.verify READ -> BOB.DONE`; the effect created only `docs/BOB_CAMPAIGN_EXECUTOR_DEV_CANARY_V12.md` on isolated branch `bob/run/run-aab176b805d3`, verified commit `612ccfbc40f8945979f9025bb678931fe919242c`, and performed no merge/push/PR/promotion.
- V12 deterministic verification passed clean worktree, `git diff --check`, exact branch-head binding and full unittest suite **207/207 PASS** inside the isolated worktree.
- After reconciliation, the current working copy passes focused executor **6/6**, focused Local Companion **34/34**, full suite **218/218 PASS**, and `git diff --check`.
- The earlier blocked/parked canaries remain durable evidence and must not be replayed merely as transport probes.

Self-hosting architecture-repair qualification:
- first genuine canary `campaign-d9a4105bb8ca` / `run-31a63f6970de` started from exact pre-repair base `c5102a9aacce349c9e5aded950daaa8c3ce825b1` with `promotion_authority=NONE`;
- Bob used all 12 cognition rounds for repository evidence gathering, performed **0 effects**, left the isolated worktree clean at the exact base and failed only with `CAMPAIGN_EXECUTOR_ROUND_BUDGET_EXHAUSTED`;
- this exposed a control-plane defect for large work: the 12-round slice was terminal instead of a resumable safe boundary;
- the working copy now converts clean round-slice exhaustion into durable `ROUND_YIELD`: worker-owned checkpoint `executor-round-yield`, queue item remains `ADMITTED`, execution run remains `ACTIVE`, and a later executor cycle can continue from durable `continuation_results`;
- dirty worktree exhaustion still fails closed as `RECOVERY_BLOCKED_DIRTY`; cognition/effect failures remain terminal/blocking under their existing rules;
- module hard caps remain enforced without exception: executor/worker focused suites PASS, packaged module graph cap regression PASS, full suite **219/219 PASS**, `git diff --check` PASS.

Self-hosting V2 / long-context finding:
- after round-yield hardening was committed/pushed at `ecc2da2fc52c153dde8431d61876a07e82a4bf0f`, V2 `campaign-fc8010321446` / `campaign-work-5183bb278080` / `run-02b654ab1469` restarted the same exact architecture-repair problem from `c5102a9...`;
- slice 1 reached 12 cognition rounds with zero effects and LIVE yielded as `ROUND_YIELD` at durable checkpoint `campaign-checkpoint-081c821a889e`; campaign remained RUNNING, item ADMITTED, same run ACTIVE and exact base head clean;
- slice 2 continued the same run/continuation and independently created three verified architecture commits: `bob/runtime_effects.py` at `e003063a...`, `bob/runtime_module.py` at `aacb3a46...`, and `bob/runtime_bridge.py` at `fab7f268...`;
- round 24 then blocked cognition. Sanitized network diagnostics proved the submission POST itself returned **HTTP 413**, while later unrelated conversation-list traffic returned 429. The prior `NO_CONVERSATION_TURN` label therefore hid a payload-size failure, not a selector/capture failure;
- exact durable continuation history was 23 results / **136,358 chars**. Full durable history remains authoritative, but it must not be reinjected verbatim forever;
- working copy now adds separate bounded campaign cognition-context compilation: small histories remain exact; oversized history keeps recent full evidence plus compact older request/tool/status/lineage summaries under a 40k-char hard budget. The real V2 history compiles to **25,425 chars** without mutating durable state;
- bridge network diagnostics now fail fast on conversation POST 413 as `CHATGPT_SUBMISSION_FAILED:PAYLOAD_TOO_LARGE` rather than collapsing it into `NO_CONVERSATION_TURN`;
- the context compiler is a separate declared `BOB_CAMPAIGN_COGNITION_CONTEXT` module so the executor remains within the 15k module cap;
- focused context/executor/bridge tests and package cap regression PASS; full suite **223/223 PASS** and `git diff --check` PASS.

Still required before Priority A is complete:
- checkpoint/push/restart the bounded-context + 413-classification hardening; no canonical/main promotion;
- continue the **same** V2 run from clean isolated head `fab7f268...` and its three durable verified effects, across as many bounded slices as needed, until deterministic verification succeeds or a genuine fail-closed blocker/deadline occurs;
- only after that self-hosting canary is green, close Priority A and proceed directly toward `FULL_REPLACEMENT_GATE`.

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
- Windows state persistence now prefers atomic temp-file `os.replace`; if Windows denies replacement because another process permits file writes but not delete/rename sharing, ProcessSupervisor preserves the previous valid state to `.bak`, fsyncs an in-place write, verifies exact read-back, and fails closed if exact persistence cannot be proven. `_load` may recover a valid Windows fallback backup only when the primary state is unreadable/invalid.

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
- current executable verification after the original capture hardening: `py_compile` PASS, focused Local Companion **18/18 PASS**, full suite **115/115 PASS**, `git diff --check` PASS.

Stateless READ continuation live qualification on 2026-09-25:
- `BOB_PROTOCOL` was measured live at 4,152 tokens and used as the bounded canary;
- first fresh cognition was forced to emit `BOB.READ` id `read-protocol-live-1` for `github.read_file` on `bob/protocol.py` at `feat/bob-execution-ledger-v1`;
- Bob executed the read with `PASS`, durably folded the `BOB.RESULT` into the original problem, recompiled context, and opened a second fresh ChatGPT conversation;
- the second fresh cognition returned `BOB.DONE` id `read-protocol-live-done` and correctly identified all four `ALLOWED_TYPES`: `BOB.READ`, `BOB.EFFECT`, `BOB.ASK`, `BOB.DONE`;
- `/bob/module-turn` returned HTTP 200 / `status=DONE` with one recorded `fresh_cognition=true` read round. **READ continuation is LIVE GREEN.**

Approval-bound effect canary / transient-limit finding on 2026-09-25:
- Bob staged one exact `github.replace_file` effect on non-canonical `feat/bob-execution-ledger-v1`, bound to branch SHA `01381e84edff4b9987ac857363a27a7e784e45be`, file SHA `1ac1fd691f7b346c4b4f892c4d1ab2004a4c2e11` and candidate hash `5a9a6ac62e8568cb6e561ce3d2173f985500c261e3bbfab4f8c676dcff2ebbba`;
- after explicit operator approval, Bob created remote commit `966f1d0f7d343c914976908b23965203493ead98`; independent GitHub read-back returned the new file SHA `7bdeaffbd17a55f09d56ffb875cca3761a21cf71` with the exact canary marker, so **effect execution + verified after-state are LIVE GREEN**;
- Bob then opened the required post-effect fresh cognition, but that request produced no ChatGPT conversation turn at all (`assistant=0`, `author_roles=[]`, `conversation_turn=0`) for the entire 360 s response budget and timed out. The operator suspected/observed the recurring ChatGPT `Too many requests` condition; the bridge version running that request did not yet classify transient UI surfaces, so the exact UI cause is not independently proven from that historical request;
- bridge hardening now detects visible rate-limit/usage-limit alerts/live regions as sanitized `RATE_LIMITED` / `USAGE_LIMIT` categories, logs no raw UI text, fails fast, and **does not transparently retry**;
- approval continuation hardening now preserves an already-executed effect receipt as `CONTINUATION_BLOCKED` and exposes `POST /bob/continuations/<continuation_id>/resume`; resuming cognition cannot replay the effect. This state is intentionally still process-local and restart persistence remains separate work;
- deterministic verification after transient-limit hardening was **117/117 PASS**; after the Windows supervisor persistence hardening the full suite is **119/119 PASS** and focused ProcessSupervisor is **10/10 PASS**.
- transient cognition/continuation hardening is pushed at `404438219e0daac402f1e87f947564575fa46ab3`; Windows supervisor persistence hardening is pushed at `f2351a1fd1228ee64dc4edd1aa45058e5b5f925a`; canonical `feat/bob-core-v1` remains unchanged at `098e6ac9f2adb47e7174c4db8ad2d0b1639d1279`.
- restart qualification exposed a reproducible Windows `WinError 5` at `os.replace(temp,state)` before any owned process was signalled. File ACL/read-only checks were clean; direct fsynced writes to the same state file succeeded, localizing the problem to Windows replace/delete-sharing semantics rather than ownership or permissions.
- with the verified Windows fallback active, the exact same `bob_local.py --stop` stopped **2 supervisor-owned Bob processes**; ports 5001/5002 became free; `bob_local.py --detach --no-open-ui` then restarted cleanly.
- current runtime health is green without another cognition request: Bob API running, ChatGPT bridge `ready=true`, and supervisor state contains exactly two new `RUNNING` long-lived records with exact listener ownership for ports 5002/5001.
- read-only `/bob/execution` is HTTP 200 with **0 active runs / 0 integration queue**.
- authoritative live branch measurements from `POST /bob/module-graph` after the persistence hardening are `BOB_PROTOCOL=4,169`, `BOB_MODULE_COGNITION=12,856`, `BOB_RUNTIME_ORCHESTRATION=22,628 MIGRATION_REQUIRED`, `BOB_EXECUTION_LEDGER=13,041`, `BOB_WORKTREE_COORDINATION=9,992`, `BOB_PROCESS_SUPERVISION=13,661`; all non-migration modules remain <=15k.

ChatGPT traffic-control hardening on 2026-09-25:
- V1 already had one serialized Playwright browser worker; the missing control was pacing/cooldown at that shared ChatGPT choke point, not another repository-worker cap;
- `bob/chatgpt_traffic.py` now enforces one fail-closed ChatGPT write lane, fresh-chat spacing of at least 10 s plus 0..3 s jitter, and sanitized transient-limit cooldown of 15 -> 30 -> 60 -> 120 s plus jitter;
- `RATE_LIMITED` / `USAGE_LIMIT` still fail the current cognition request and are never transparently retried; the cooldown applies to later ChatGPT writes while repository/Shell/provider work remains independent;
- bridge request telemetry records sanitized pacing/backoff metadata, and `GET /status` exposes controller state without prompt/response content;
- Local Companion validates that the bridge client timeout covers response time plus worst configured traffic-control wait; the default client budget is now 600 s for a 360 s response budget;
- deterministic verification after the traffic-control change is **143/143 PASS**, focused traffic/Local Companion **25/25 PASS**, `py_compile` PASS and `git diff --check` PASS;
- live two-request `/new-chat` qualification proved pacing: request 2 arrived only 3.313 s after the previous fresh-chat attempt, Bob inserted 7.095 s of wait (with 0.408 s jitter) and both starts completed successfully;
- a subsequent live cognition canary began with a 19.140 s fresh-chat gap and zero cooldown, submitted the prompt, but still produced `assistant=0`, `author_roles=[]`, `turn_copy=0`, `conversation_turn=0` for >3 minutes with no detected `RATE_LIMITED`/`USAGE_LIMIT` surface. The canary was stopped by clean supervisor restart; it had no effects;
- therefore fresh-chat burst pressure remains a plausible contributor to transient limits, but **it is not a sufficient explanation for the separate no-conversation-turn stall**. Do not collapse those failure classes. The next transport diagnostic should verify that submission creates a user/conversation turn within a short bounded interval and surface a distinct sanitized submission failure when it does not.

Remaining work / boundaries:
- full post-effect fresh continuation still needs one clean live completion after ChatGPT is accepting requests again; **do not replay the already-verified canary effect merely to recover cognition**. A distinct benign cleanup effect (for example removing the canary marker) can be separately staged/approved to qualify the hardened continuation path;
- SL/AB obtain independent repo coordinators only after their local repo paths are explicitly configured (for example through repository bindings); they do not consume Bob's slots;
- a future `BOB_MACHINE_SCHEDULER` may impose a separate higher machine resource cap for CPU/RAM/browser/API pressure; it is not the repository safety cap and is not implemented here;
- `BOB_SCHEDULER_V1` is an explicit planned first-class component: Bob should own a durable, effectively unbounded scheduled-task registry independent of ChatGPT native Scheduled Tasks, with one-shot `run_at`, recurring schedules (RRULE/cron-equivalent), condition/dependency triggers, durable claims/leases, retries/backoff, task history/results, cancellation, budgets/rate limits and task-to-task spawning. Scheduler backlog size stays separate from active execution capacity: existing per-repository coordinators remain authoritative for actual runs, while any machine-wide cap is a distinct resource-control layer. Native ChatGPT Scheduled Tasks may optionally act as wake-up/bootstrap only, not as scheduler source of truth;
- the browser transport remains one serialized Playwright worker, so three repository workers do not yet mean three simultaneous model generations;
- the oversized `BOB_RUNTIME_ORCHESTRATION` recursive self-repair canary should follow the remaining post-effect continuation qualification rather than skipping it.

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
- current deterministic verification at working head `2a55a84…` is **147/147 PASS**; the submission-diagnostic tranche was **145/145 PASS** before the visible-send actuator hardening; focused current Local Companion is **24/24 PASS**; `py_compile` and `git diff --check` PASS;
- Bob-owned `BOB.READ -> BOB.RESULT -> recompile -> second fresh cognition` is **LIVE GREEN**;
- approval-bound effect staging/execution/verified read-back is **LIVE GREEN**, but one clean post-effect fresh continuation still remains to be live-qualified after the observed transient ChatGPT request-limit episode;
- the former oversized runtime monolith has been manually decomposed into bounded runtime, effect-authority and stateless-module-runtime modules without changing the public `BobRuntime` API or widening authority;
- this local repair is a **reference implementation**, not a self-hosting proof. When cognition is available again, run the genuine architecture-repair canary from pre-repair commit `c5102a9aacce349c9e5aded950daaa8c3ce825b1` in an isolated worktree/branch and require normal verification/approval before any integration.
- repair commit `4533be665523a77ffaab29f7ed900e51f6253b8a` is the bounded-module reference implementation; subsequent durability and snapshot-hardening commits are recorded below. Canonical `feat/bob-core-v1` remains unchanged at `098e6ac9f2adb47e7174c4db8ad2d0b1639d1279`.
- Local Companion was stopped/restarted from the repaired head without issuing another cognition request. Bob API is running, bridge is `ready=true`, execution is **0 active / 0 integration queue**, exactly two supervisor-owned long-lived processes own ports 5002/5001, and live `POST /bob/module-graph` reported all eight modules `compliant=true` before the later persistence-only working-tree changes.
- verified-effect continuation state is now written to `.bob/runtime/blocked_continuations.json` **before** post-effect cognition starts; a new `BobRuntime` loads it after restart, `/bob/continuations` exposes sanitized pending-resume metadata, and the regression test proves restart -> resume reaches DONE with the provider effect count still exactly one.
- durability commit `5cffa6d8e5cc8f8c94680727ae776227cb3c0d5b` (`Persist blocked post-effect continuations`) is pushed exactly to `origin/feat/bob-execution-ledger-v1`; canonical remains unchanged.
- Local Companion was then stopped/restarted from `5cffa6d…` without issuing cognition. Live read-only qualification: Bob API running; bridge `ready=true`; execution **0 active / 0 integration queue**; `GET /bob/continuations` HTTP 200 with `count=0`; exactly two supervisor-owned runtime process trees own ports 5002/5001; `POST /bob/module-graph` HTTP 200 with all eight modules `compliant=true`.
- pending approvals now have a separate durable `.bob/runtime/pending_effects.json` store. A staged effect is persisted before it is exposed to the operator; a restarted Bob reloads it; `GET /bob/approvals` returns the approval preview; approve/reject/relay consume the durable record before any effect can execute; restarted approvals are re-previewed/re-hashed against current provider state. Regression tests prove restart -> approval executes exactly once and restart + moved branch -> stale approval fails with zero effects.
- approval durability is pushed at `8115692fe95db3fcecd247c85c4d9fe56b80ac90` (`Persist pending effect approvals`). Module-graph snapshot optimization is pushed at `eaad1e41f82c6f483cb45379295a2b258e82372f` (`Speed verified module graph snapshots`), which exactly matches `origin/feat/bob-execution-ledger-v1`.
- Local Companion was cleanly restarted from `eaad1e4…` without cognition. Live read-only qualification: Bob API running; bridge `ready=true`; approvals `count=0`; continuations `count=0`; execution **0 active / 0 integration queue**; exactly two supervisor-owned process trees own 5002/5001; three consecutive `POST /bob/module-graph` calls returned HTTP 200 in **5.375 s / 4.960 s / 5.243 s** versus the prior ~18–36 s observed latency.
- snapshot acceleration preserves identity: authenticated local Git is used only after GitHub repository identity is verified and the requested remote ref commit SHA exactly matches the local commit; stale local refs fall back to remote reads. Effect execution/read-back semantics are unchanged and remain remote/provider verified.
- the working branch is **23 commits ahead / 0 behind** canonical at `8de216dd4ccc868f9f650750df34ed4ab191a23f`; `feat/bob-core-v1` remains unchanged at `098e6ac9f2adb47e7174c4db8ad2d0b1639d1279`.

Current authoritative `BOB_TOKEN_ESTIMATE_V1` measurement at `3bc3c02…`; graph-cap regression is green in the **181/181** full suite:

```text
BOB_RUNTIME_ORCHESTRATION 13,344   compliant
BOB_EFFECT_AUTHORITY       9,259   compliant
BOB_STATELESS_MODULE_RUNTIME 10,526 compliant
BOB_PROTOCOL               4,169   compliant
BOB_MODULE_COGNITION      13,103   compliant
BOB_EXECUTION_LEDGER      14,477   compliant (523 tokens headroom)
BOB_WORKTREE_COORDINATION 10,122   compliant
BOB_SELF_DEVELOPMENT_STATE 7,979   compliant
BOB_SELF_DEVELOPMENT_EXECUTION 8,264 compliant
BOB_SELF_DEVELOPMENT_SANDBOX 13,595 compliant
BOB_SELF_DEVELOPMENT_PROMOTION 9,624 compliant
BOB_WORK_CAMPAIGN_CONTROL 12,612 compliant
BOB_PROCESS_SUPERVISION   13,661   compliant
```

The package regression loads the real `.bob/module_graph.json`, verifies unique path ownership and asserts every declared module remains <=15,000 measured tokens. The graph still has explicit `coverage=PARTIAL`. Phase 3.75 now has durable state, execution binding, reversible sandbox/control and a separate durable promotion-review gate. Isolated lifecycle, interactive-first pre-emption, checkpoint, revert, discard and promotion review are live-qualified; background scheduling and Knowledge Fabric runtime remain pending.

## LATEST_CHECKPOINT_2026-09-25

- Working branch `feat/bob-execution-ledger-v1` is pushed through `8de216dd4ccc868f9f650750df34ed4ab191a23f` (`Close self-development execution lifecycle`) and is **23 ahead / 0 behind** canonical. Canonical `origin/feat/bob-core-v1` remains unchanged at `098e6ac9f2adb47e7174c4db8ad2d0b1639d1279`.
- Concurrent operator work was reconciled, not overwritten: `b349c3a6d3ed8a7fe40f838f2dc8a3f7c48feeca` (`Plan bounded autonomous work campaigns`) landed between the transport commits and only changes `CURRENT_WORK.md` / `ROADMAP.md`.
- `712ef02` (`Detect failed ChatGPT submissions`) split submission acceptance from assistant completion. After submit actuation Bob now requires observable user/conversation/assistant state within **12 s** and otherwise returns sanitized `CHATGPT_SUBMISSION_FAILED:NO_CONVERSATION_TURN` instead of waiting ~360 s for an assistant response that never began.
- Live canary `submission-probe-20260925-1` proved the historical long hang is a real submit/materialization failure: the old Enter actuator produced exact sanitized baseline/final counts `user=0 / conversation_turn=0 / assistant=0` and failed quickly as `NO_CONVERSATION_TURN`; no visible `RATE_LIMITED` / `USAGE_LIMIT` state was detected and no retry was sent.
- `2a55a84` then changed actuation to prefer ChatGPT's visible enabled Send control, fail closed on a visible disabled send control, and use input-local Enter only when no send control can be discovered. Deterministic verification is **147/147 PASS**, focused Local Companion **24/24 PASS**, `py_compile` PASS and `git diff --check` PASS.
- Local Companion was restarted from exact `2a55a84`. Live canary `submission-probe-20260925-2` logged `Submission actuated via send_button` but again remained exactly `0 -> 0` for user/conversation/assistant state and returned `CHATGPT_SUBMISSION_FAILED:NO_CONVERSATION_TURN`. Therefore the current failure is **not explained by page-level Enter or failure to click the visible Send control**. No further cognition probes should be sent until new evidence justifies one.
- Runtime remains healthy after that failure: Bob API running; bridge `browser_ready=true`, `runtime_error=null`, `active_count=0`, no traffic cooldown/throttle state.
- Phase 3.75 durable state remains repo/canonical-ref bound, FIFO, V1 single-active and restart-safe. `BOB_SELF_DEVELOPMENT_STATE` owns intent/lifecycle only (**7,978 / 15,000**); `BOB_SELF_DEVELOPMENT_EXECUTION` owns queue↔execution binding/reconciliation only (**7,163 / 15,000**). Execution ledger/worktree authority and promotion authority remain separate.
- `dd40658fee32826e2d791d0509f3f1dbbc7e241d` (`Bind self-development to isolated execution`) introduced bounded module `BOB_SELF_DEVELOPMENT_EXECUTION`, explicit `claim`/`reconcile` APIs and crash-window adoption of an existing `lane=selfdev` run. It reuses the existing `ExecutionCoordinator`; it is not a second scheduler and records `promotion_authority=NONE`.
- Deterministic qualification after that tranche was **152/152 PASS**. Live claim of `selfdev-b624525477b7` created exactly one run `run-e16c686791c8`, base `dd40658…`, branch `bob/run/run-e16c686791c8`, clean isolated worktree `C:\\Users\\emilm\\.cognitive_prosthetic-bob-worktrees\\run-e16c686791c8`, with attempt_count=1 and no integration/promotion authority.
- Restart proof is LIVE GREEN: queue state became `INTERRUPTED` with `RUNTIME_RESTART_RECONCILE_REQUIRED` while the execution run remained ACTIVE; explicit reconcile restored the same item/run to ACTIVE, attempt_count remained 1, and exactly one matching selfdev run existed. No duplicate run was created.
- `8de216dd4ccc868f9f650750df34ed4ab191a23f` (`Close self-development execution lifecycle`) added fail-closed terminalization. A bound item cannot finish while execution owns a live slot; `QUALIFIED` requires a preserved CANCELLED run plus explicit verification evidence and records exact branch head + `promotion_authority=NONE`.
- Live terminalization is GREEN: `run-e16c686791c8` was CANCELLED with no promotion requested, then `selfdev-b624525477b7` became `QUALIFIED`; receipt records branch head `dd40658fee32826e2d791d0509f3f1dbbc7e241d`, run state CANCELLED, exactly one matching run and promotion `NOT_REQUESTED`. Execution is now **0 active / 0 integration queue**.
- Full deterministic verification after terminalization: **153/153 PASS**; `py_compile` and `git diff --check` PASS. All ten declared modules remain <=15k; new `BOB_SELF_DEVELOPMENT_EXECUTION` is **7,163 / 15,000**.
- Because cognition is still not materializing submissions, the active local next step is Phase 3.75 semantic leases + interactive pre-emption. It must park/pre-empt low-priority selfdev work durably without losing intent, duplicating runs or adding promotion authority.

- Commit 99e43c3 (Park self-development for interactive work) implements the first semantic-lease pre-emption primitive: idle ACTIVE selfdev runs can durably enter PARKED, releasing worker-slot and semantic-lease ownership so conflicting interactive work activates through the existing ledger. Resume reuses the same run/branch/worktree binding and returns through normal QUEUED lease/capacity arbitration; no attempt/run duplication and no promotion authority are added. Running cognition, non-selfdev lanes and non-ACTIVE states fail closed.
- Deterministic verification for this tranche: 156/156 PASS, focused execution+selfdev 16/16 PASS, py_compile PASS and git diff --check PASS. Browser bridge read-only status remained healthy/idle; no cognition probe was sent.
- Next local Phase 3.75 step: expose/qualify interactive-first pre-emption at the orchestration/API boundary, then implement explicit checkpoint/revert/discard semantics.

- `9018a362a5f1add4decd46bb620ac15339f8b44e` (`Add reversible self-development sandbox`) reconciles the concurrent sandbox work and hardens it. The new `BOB_SELF_DEVELOPMENT_SANDBOX` module owns durable checkpoints, exact same-run revert/discard and interactive-first API/orchestration; it does not merge or promote.
- Deterministic qualification: **166/166 PASS**, focused sandbox/server **15/15 PASS**, `py_compile` PASS, `git diff --check` PASS. All eleven declared modules remain <=15k; the closest cap is `BOB_EXECUTION_LEDGER=14,477`.
- Live interactive-pre-emption canary is GREEN: selfdev `run-7b9d5ed5cca7` was checkpointed and moved `ACTIVE -> PARKED`; conflicting interactive `run-3c2a57e014d3` became ACTIVE; cancelling the interactive run resumed the exact same selfdev run; discard then cancelled it, removed only its worktree and returned execution to **0 active / 0 integration queue**.
- Separate live revert canary is GREEN: checkpoint `checkpoint-b1c8a2b7b079` captured head `9018a36…`; an experimental commit moved the isolated branch to `efd3601…`; API revert restored exact head `9018a36…`, removed untracked experiment state and verified a clean worktree; subsequent discard cleaned the sandbox.
- Restart persistence is GREEN: after a clean Local Companion stop/start the durable checkpoint store still contains both live-canary checkpoints, execution remains **0 active / 0 integration queue**, and no cognition request was issued.
- Next Phase 3.75 boundary is the separate promotion gate. It may produce/revalidate an operator-review proposal, but must not merge, push, or convert model/selfdev success into canonical promotion authority.

- `9ea9b62` (`Add self-development promotion review gate`) adds `BOB_SELF_DEVELOPMENT_PROMOTION`: exact candidate/qualification/canonical binding, stale/rebase detection, restart-durable operator review state and API surface. The module has no merge/push/PR/integration effect capability and persists `merge_authority=NONE` + `provider_effect_performed=false`.
- Deterministic qualification: **173/173 PASS**, focused promotion/server **13/13 PASS**, `py_compile` PASS and `git diff --check` PASS. Promotion module = **9,624 / 15,000**; execution ledger remains **14,477 / 15,000**.
- Live promotion-gate canary on previously qualified lifecycle item `selfdev-b624525477b7`: proposal `promotion-79274f608428` bound candidate `dd40658…` against canonical `098e6ac9…`, revalidated fresh, then was explicitly **REJECTED** as canary-only. No approval, merge, push, PR, integration or provider effect occurred.
- Promotion review restart persistence is LIVE GREEN: after clean Local Companion restart the rejected proposal remains durable, execution is **0 active / 0 integration queue**, and canonical `feat/bob-core-v1` remains unchanged.
- Phase 3.75 next local foundation is background scheduling/campaign control: durable bounded work windows, safe stop-at-deadline semantics and interactive-first parking, reusing existing repo coordinators rather than creating a second execution authority.

## LATEST_CHECKPOINT_2026-09-26

- Working branch is pushed through `3bc3c02` (`Add bounded work campaign control`); canonical `feat/bob-core-v1` remains unchanged at `098e6ac9f2adb47e7174c4db8ad2d0b1639d1279`.
- `BOB_WORK_CAMPAIGN_CONTROL` is now a separate bounded module (**12,612 / 15,000**) owning durable campaign goal/targets/duration/deadline/admission/run bindings only. Existing repository coordinators still exclusively own run/worktree/lease/capacity state.
- Campaign deadline semantics are fail-closed: reaching the wall-clock deadline changes RUNNING -> DEADLINE_REACHED and stops all new run admission. Already nonterminal work is not asynchronously killed mid-cognition/effect; it must reach a safe boundary for checkpoint/park/cancel by higher orchestration.
- A deadline race between admission and durable run binding is closed: a just-created run is cancelled and left unbound if the campaign deadline closes in that narrow window.
- Campaign runs use lane=campaign, normal per-repository cap/leases/worktrees, `promotion_authority=NONE` and `auto_merge=false`. Campaign state itself has no merge/promotion authority.
- Deterministic qualification after campaign-control implementation: **181/181 PASS**, campaign-focused **7/7 PASS**, prior campaign+server surface **14/14 PASS**, `py_compile` PASS and `git diff --check` PASS. All declared modules remain <=15k; `BOB_EXECUTION_LEDGER` remains the tightest at **14,477 / 15,000**.
- Live campaign canary is GREEN: `campaign-7f7576215263` targeted BOB, started with an absolute deadline, created isolated campaign run `run-8e233ad6a57f` as ACTIVE with no promotion authority, reconciled it, cancelled it at a safe boundary, and completed the campaign. Execution returned to **0 active / 0 integration queue**.
- Live multi-repo safety check is GREEN: a planned SL+AB campaign refused START with `ProtocolError: campaign targets lack local repository bindings: AB,SL`; it was then cancelled as canary cleanup. Bob does not pretend those repos can run locally until explicit bindings exist.
- Restart persistence is LIVE GREEN: after clean Local Companion stop/start, campaign counts remain **COMPLETED=1 / CANCELLED=1 / RUNNING=0**, execution remains **0 active / 0 integration queue**, and no cognition request was issued.
- Important scope boundary: this proves durable wall-clock campaign control, **not yet an autonomous eight-hour worker**. Automatic safe task selection, repeated work admission, blocked-work reallocation, deadline checkpoint/parking and final operator digest remain to implement.
- Next local tranche: campaign worker/orchestrator that consumes an explicit safe work backlog, admits bounded runs while before deadline/capacity, pauses at safe boundaries, and produces durable outcome/digest state without auto-merge/promotion.

## LATEST_CHECKPOINT_2026-09-26_CAMPAIGN_QUEUE

- Qualified implementation commit: `5f750a6e3664e0fb8cc05a49c58c534d7cc8b1dd` (`Add durable campaign work queue`). This commit is on `feat/bob-execution-ledger-v1`; canonical `feat/bob-core-v1` remains untouched at `098e6ac9f2adb47e7174c4db8ad2d0b1639d1279`.
- `BOB_WORK_CAMPAIGN_QUEUE` is now the durable explicit backlog above campaign control. It owns FIFO work items, dependencies, capacity/blocker waiting, exact run bindings, safe-stop request state, explicit verified outcomes and final review digest. It does not perform cognition, repo mutation, merge, push, PR or promotion.
- Execution authority remains singular: admission still goes through `WorkCampaignManager` -> existing per-repository `ExecutionCoordinator`; queue capacity waits do not create latent execution runs that could activate after deadline.
- Crash-window hardening is implemented: each queue-created campaign run carries exact `work_item_id` in existing run authority. Restart adopts at most one matching live run if a crash occurred after coordinator admission but before queue `run_id` persistence; multiple live matches fail closed. This prevents duplicate work without creating another scheduler/execution authority.
- Deterministic qualification is **190/190 PASS** full suite; focused queue/campaign/server/module-cap tranche is **27/27 PASS**; `py_compile` and `git diff --check` PASS.
- Current module measurements remain compliant: `BOB_WORK_CAMPAIGN_QUEUE=14,570 / 15,000`, `BOB_EXECUTION_LEDGER=14,477 / 15,000`, `BOB_WORK_CAMPAIGN_CONTROL=13,185 / 15,000`. The queue has little remaining growth room; the worker/orchestrator must therefore be a separate declared module.
- Live queue canary is GREEN without cognition: campaign `campaign-2c4a234f45f8` admitted item `campaign-work-05434ac1cb91` as run `run-f331d4c86feb`, explicit verified finish produced `SUCCEEDED`, review digest preserved exact branch/head with `promotion_authority=NONE` and `auto_merge=false`, campaign completed, and execution returned to **0 active / 0 integration queue**.
- Restart persistence is LIVE GREEN: after clean Local Companion stop/start the same completed campaign/item/digest remained durable, the exact run authority includes its `work_item_id`, and execution remained **0 active / 0 integration queue**. No ChatGPT cognition request was sent.
- Concurrent remote commit `f49075d80fec001c8a740edf3074eb4970daaa29` (`Plan Bob persistent scheduler`) was reconciled before implementation. Its scheduler intent is preserved here as `BOB_SCHEDULER_V1`; accidental text-encoding changes from that commit are not treated as architecture truth.
- Next local tranche is the actual campaign worker/orchestrator: repeated safe selection from this durable backlog -> bounded execution -> blocker reallocation -> interactive-first parking -> stop admitting at deadline -> safe-boundary checkpoint/park/cancel -> durable outcome -> concise operator digest. It must not auto-merge/promote.

## LATEST_CHECKPOINT_2026-09-26_CAMPAIGN_WORKER

- Qualified implementation commit: `7cb795dc11d7d4d84a70940228fe53954d3bfcbc` (`Add campaign worker orchestration`). It remains on `feat/bob-execution-ledger-v1`; canonical `feat/bob-core-v1` remains untouched at `098e6ac9f2adb47e7174c4db8ad2d0b1639d1279`.
- New bounded module `BOB_WORK_CAMPAIGN_WORKER` owns repeated queue cycles, ready-work selection, durable clean-worktree checkpoints, deadline safe-stop parking, interactive-first campaign pre-emption/resume and paused/review digest composition. It does **not** own execution, cognition, merge, push, PR, integration or promotion.
- Execution authority remains singular. Worker admission still flows `WorkCampaignQueue -> WorkCampaignManager -> existing per-repository ExecutionCoordinator`; PARKED campaign runs release worker slots/leases and resume only through ordinary ledger arbitration.
- Interactive-first is now live at the ordinary execution API: selfdev pre-emption is attempted first; if an interactive run remains queued on campaign scope/capacity, an idle campaign run may be checkpointed and parked. Running cognition or dirty/uncheckpointed work fails closed rather than being killed/discarded.
- Deadline behavior is safe-boundary based: `STOP_REQUESTED` work is checkpointed+parked only when cognition is not RUNNING and the isolated worktree is clean. Otherwise it remains visibly pending in `waiting_safe_boundary_item_ids`.
- Deterministic qualification is **196/196 PASS** full suite and **44/44 PASS** focused worker/server/selfdev/campaign/module tranche; `py_compile` and `git diff --check` PASS.
- Module caps remain compliant: `BOB_EXECUTION_LEDGER=14,800 / 15,000`, `BOB_WORK_CAMPAIGN_QUEUE=14,570 / 15,000`, `BOB_WORK_CAMPAIGN_WORKER=13,061 / 15,000`. The ledger now has only 200 measured tokens headroom and should be treated as frozen for new orchestration logic.
- Live worker canary is GREEN without cognition: campaign `campaign-9e2faf73c0c2`, item `campaign-work-72eb6e383dc1`, campaign run `run-ac9a42b83af0`. Conflicting interactive run `run-0845238861ed` caused `PREEMPTED_CAMPAIGN`; campaign work checkpointed+parked, then resumed the exact same run after interactive cancellation. After deadline it safe-stopped again at checkpoint `campaign-checkpoint-3fd38f810a2d`, then explicit verification produced `SUCCEEDED` and campaign `COMPLETED`. Execution returned to **0 active / 0 integration queue**.
- Restart persistence is LIVE GREEN: the same completed campaign, worker cycle count, checkpoint/head and durable interactive pre-emption/resume record survived Local Companion restart; execution remained **0 active / 0 integration queue**. No ChatGPT cognition request was sent.
- Important scope boundary: Bob now has the durable eight-hour **control plane**, but not yet the autonomous work executor that consumes each `ready` item and performs bounded cognition/effects inside its exact run/worktree. That executor must be a separate module/adaptor, must finish items only from verified reality, and must not bypass the existing coordinator or promotion gates.
- Multi-repo SL+AB execution still additionally requires explicit local repository bindings before campaign START can succeed.

## NEXT_INTENDED_WORK

### Priority A — finish the current Bob execution workstream

1. Reconstruct live local/GitHub/runtime truth before every further step. The bounded campaign executor itself is already implemented and locally checkpointed at `5345fc53ee8333c5233563a472ae3b1d9126b153`; preserve the current uncommitted submission-materialization hardening and this handoff rather than overwriting them.
2. Preserve failed live canary `campaign-246969189d2b` / `campaign-work-57919fb59b21` / `run-4ee13a8c6040` as durable evidence. It is safely parked at clean head `5345fc53...` with executor status `BLOCKED_COGNITION`, zero effects and no pending effect. Do not resume/retry that failed cognition merely to prove transport.
3. The follow-up bridge hardening is deterministically qualified and loaded in Local Companion: submission materialization may be established by message/turn growth, sanitized conversation-ID transition or clearing of a previously populated composer; rate/usage-limit detection still fails closed. Current deterministic result is **209/209 PASS** full suite, focused **53/53 PASS**, `py_compile` PASS and `git diff --check` PASS.
4. Only when there is an independent reason to exercise real cognition again, run a fresh bounded Bob-internal executor canary through `campaign -> ready item -> fresh cognition -> bounded isolated repository work -> deterministic verification -> durable outcome -> concise digest`. A cognition/submission failure remains durable and must not be transparently retried; successful work must still have `promotion_authority=NONE` and `auto_merge=false`.
5. After a genuinely successful executor canary, restart Local Companion and prove durable executor outcome/state plus sane execution state. Preserve interactive-first behavior, deadline safe boundaries and clean worktree guarantees throughout.
6. Then run the genuine self-hosting architecture-repair canary from pre-repair commit `c5102a9aacce349c9e5aded950daaa8c3ce825b1` in an isolated run/worktree. Evaluate invariants/tests rather than an exact textual solution; no automatic promotion.
7. Once both live qualifications are genuinely green, checkpoint/commit/push the stable `feat/bob-execution-ledger-v1` state. Promotion/merge to `feat/bob-core-v1` or `main` still requires explicit operator approval.

### Priority B — finish Bob to full practical ChatGPT replacement before external-project work

8. **Operator decision 2026-09-26: pause Resale Engine work until Bob reaches full practical replacement.** Do not onboard, develop, task-run or use RE as a canary while Bob itself still requires a separate ChatGPT development chat for ordinary operation.
9. Close the autonomous execution loop completely: `operator task -> Bob-owned cognition -> bounded effect -> deterministic verification -> durable outcome/digest`, including multi-round work and clean failure/recovery semantics.
10. Make ordinary Bob chat route through the correct module/context path by default, with persistent project/conversation continuity owned by Bob rather than by the transient ChatGPT conversation.
11. Finish the Bob-first application surface so Projects, conversations, work items, workers, approvals, long-running campaigns, scheduler state, failures/recovery and results can all be operated from Bob without opening ChatGPT as the primary UI.
12. Qualify long-lived work: bounded four/eight-hour campaigns, checkpoint/resume, interactive-first pre-emption, restart recovery and unattended multi-cycle execution.
13. Implement and live-qualify `BOB_SCHEDULER_V1` so recurring/future work is Bob-owned and no longer depends on native ChatGPT Scheduled Tasks for normal operation.
14. Qualify cross-project execution as a Bob capability while keeping repository-scoped authority/ledgers/worktrees. External projects may be bound for infrastructure qualification if strictly necessary, but no substantive RE development begins before the replacement gate below.
15. **FULL_REPLACEMENT_GATE:** Bob is considered ready to replace ChatGPT as the primary working environment only when the operator can use Bob for normal conversations and project work; Bob persistently owns context/state; cognition routing and repo/tool execution are reliable; longer/scheduled work survives restart; failures are surfaced/recoverable without losing continuity; and normal workflows do not require a separate ChatGPT development chat.

### Priority C — Resale Engine after FULL_REPLACEMENT_GATE

16. Only after `FULL_REPLACEMENT_GATE` is live-green, onboard workspace `RE` for `emilmichaelfredrikhansson-bit/resale-engine`, repository ID `1365744245`, canonical/default branch `main`, with its own repository-scoped coordinator, ledger and worktree root.
17. Initial RE authority remains shadow/development only: branch writes and deterministic tests may be authorized; no automated purchase, bidding, auction timing, buyer/seller messaging, money-moving action, material spend, production mutation or automatic promotion. `BUY_CANDIDATE` remains advisory only.
18. RE then becomes the first external production proving ground for the already-complete Bob environment: first builder work, then separate read-only/shadow task-worker work, then a closed task -> builder -> verify -> rerun loop. No separate RE ChatGPT development chat should be needed.
19. Once RE is proven from inside Bob, use that pattern for later SL/AB onboarding. Explicit local repository bindings remain mandatory.

### Deferred but still intended

20. Implement Knowledge Fabric V1 and richer reusable result/pattern distillation after full replacement unless it becomes necessary to satisfy the replacement gate; knowledge never grants authority.
21. Product-vision/bootstrap and reusable module/template extraction remain follow-up work where they are not required for the replacement gate.
22. DigitalOcean/mobile persistence remains V2 and is not a prerequisite for local full replacement.

## OPEN_FINDINGS

- The module graph has explicit `coverage=PARTIAL`; it is not yet a complete semantic map of Bob.
- `BOB_TOKEN_ESTIMATE_V1` is deterministic `ceil(UTF-8 bytes / 3)`, not ChatGPT's exact tokenizer.
- Every currently declared module is <=15,000 measured tokens against exact Git HEAD blobs. The tightest modules are `BOB_EXECUTION_LEDGER` at **14,800**, `BOB_WORK_CAMPAIGN_QUEUE` at **14,570**, `BOB_CAMPAIGN_WORK_EXECUTOR` at **14,264**, `BOB_MODULE_COGNITION` at **13,412**, `BOB_RUNTIME_ORCHESTRATION` at **13,465**, `BOB_PROCESS_SUPERVISION` at **13,661**, `BOB_SELF_DEVELOPMENT_SANDBOX` at **13,595**, `BOB_WORK_CAMPAIGN_CONTROL` at **13,185** and `BOB_WORK_CAMPAIGN_WORKER` at **13,061**. Raw Windows-checkout byte counts are not authoritative for this cap because CRLF normalization can inflate local files.
- The former oversized `BOB_RUNTIME_ORCHESTRATION` remains bounded after extracting `BOB_EFFECT_AUTHORITY` (**9,259**) and `BOB_STATELESS_MODULE_RUNTIME` (**10,526**); Phase 3.75 additionally declares bounded self-development and campaign modules. Treat `BOB_EXECUTION_LEDGER` as effectively frozen at 14,800 / 15,000 and do not grow `BOB_WORK_CAMPAIGN_QUEUE` with executor logic; the campaign work executor should be a separate declared module.
- This repaired branch is a deterministic reference implementation, not evidence that Bob cognition can independently perform the same architecture repair. The live self-hosting proof remains pending on an isolated branch rooted at pre-repair commit `c5102a9aacce349c9e5aded950daaa8c3ce825b1`.
- Normal module effects remain one effect per fresh cognition request, manifest-owned path/ref constrained; architecture-repair scope is wider but still approval/authority/read-back bounded.
- Ordinary `/bob/turn` is still stateful. Statelessness is executable through `/bob/module-turn`, not yet automatic for every operator message.
- The live operator-PC proof covers module graph, direct DONE, and a full Bob-owned READ continuation through a second fresh cognition. Approval-bound effect execution + verified GitHub after-state is also live-proven; only its post-effect fresh cognition remains unclosed. Current evidence now distinguishes the blocker from assistant capture: two later probes failed before any user/conversation turn materialized, including one verified visible Send-button click.
- The bridge now has explicit sanitized `RATE_LIMITED` / `USAGE_LIMIT` UI classification and no automatic retry for those states, plus distinct `CHATGPT_SUBMISSION_FAILED:NO_CONVERSATION_TURN` classification after a bounded 12 s materialization window.
- An already-executed module effect can enter restart-durable `CONTINUATION_BLOCKED` state. Its verified receipt/continuation is persisted before post-effect cognition, discoverable through read-only `/bob/continuations`, and resumable through `/bob/continuations/<continuation_id>/resume` without replaying the effect.
- Remote Desktop Commander is currently online and current local/runtime state has been reconciled.
- Self-development has durable repo-bound queue/state, isolated execution/worktree binding, restart reconciliation, interactive-first pre-emption, durable checkpoint/revert/discard, fail-closed terminalization and a separate no-merge promotion-review gate live-qualified. Work-campaign control, durable backlog and worker/orchestration control plane are LIVE GREEN. The bounded autonomous campaign executor is IMPLEMENTED / DETERMINISTIC GREEN, but its first real closed-loop canary is durably `BLOCKED_COGNITION` before any repository effect; general persistent scheduling remains unimplemented.
- Knowledge Fabric is canon, not implementation: no item store/schema, maturity transitions, retrieval/ranking or compiler injection exists yet.
- Project Instructions bootloader text is canonical/versioned, but the runtime does not yet verify that the configured ChatGPT Project actually contains the expected `BOB_COGNITION_CONTRACT_VERSION`.
- Bob effect approvals are now restart-durable in a separate pending-effect store; operator approval still never survives as implicit execution authority because the candidate is re-previewed/re-hashed before execution and the durable pending record is consumed first.
- V2 systemd/Xvfb/remote-host material remains preserved but is not required for V1.

## FIRST_ACTION

Resume from the latest actual local/GitHub/runtime state on `feat/bob-execution-ledger-v1`, never from this document alone. Latest verified local committed HEAD is `5345fc53ee8333c5233563a472ae3b1d9126b153` (`Implement bounded campaign work executor`), while `origin/feat/bob-execution-ledger-v1` remains at `9afd018c6d6d66c6604a7e51106a2e46ac7f13c9`; canonical `feat/bob-core-v1` remains `098e6ac9f2adb47e7174c4db8ad2d0b1639d1279`. Preserve/reconcile the current uncommitted submission-materialization hardening in `chatgpt_api_server.py`, its tests and this handoff. Existing live executor canary `campaign-246969189d2b` / `run-4ee13a8c6040` is durable `BLOCKED_COGNITION` after `CHATGPT_SUBMISSION_FAILED:NO_CONVERSATION_TURN`, with zero effects, no pending effect, clean isolated worktree and a parked checkpoint; restart persistence is GREEN. Local Companion is currently running the deterministically qualified follow-up transport hardening (**209/209 PASS**) and no cognition request has been issued since that restart. **Do not retry the blocked cognition merely to test transport.** Only when real work independently warrants fresh cognition, run a new bounded executor canary; if it succeeds, prove restart persistence and then run the genuine architecture-repair self-hosting canary rooted at `c5102a9aacce349c9e5aded950daaa8c3ce825b1`. Only after both live qualifications are genuinely GREEN should the stable working-branch state be checkpointed/committed/pushed. No merge/promotion to `feat/bob-core-v1` or `main` without explicit operator approval. After Priority A is complete, continue **Bob itself** toward `FULL_REPLACEMENT_GATE`; Resale Engine is explicitly paused and must not become the next development canary. Resume RE only after Bob is live-green as the operator's primary working environment for normal conversation/project work, persistent continuity, autonomous verified execution, long-running/restartable work, scheduler-owned future work and recoverable failures without requiring a separate ChatGPT development chat.

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
