# Bob V1 Implementation Plan

## Objective

Create the smallest production-useful Bob that can develop a real repository through ChatGPT-generated code while writing accepted changes directly to GitHub, preserving the existing SL/AB infrastructure model.

V1 is successful when the operator can:

```text
select workspace
→ request a change
→ provide/obtain ChatGPT result
→ see exact proposed file changes
→ see deterministic diff
→ approve
→ create branch/commits/PR in the correct GitHub repository
```

without using GitHub Actions as the coding/execution engine.

## ChatGPT account/project contract

V1 uses the operator's existing ChatGPT account/subscription through a dedicated Bob-managed browser profile. All automated cognition lives in one private ChatGPT Project named **Bob**, configured with Project-only memory when available. Normal Bob startup requires the exact project URL and must fail closed rather than target the generic ChatGPT home page or an unrelated personal chat.

This isolates Bob's working conversations without requiring a second subscription. Account-level usage limits are still shared.

## Design principles

1. Repo-first current truth.
2. Stable identity before privileged effects.
3. Broad cognition, narrow effects.
4. Model output is proposal, not state.
5. Whole-file deterministic writes before fuzzy patch cleverness.
6. Fail closed on stale SHAs or identity mismatch.
7. Existing infrastructure remains authoritative.
8. Build only what SL/AB immediately need.

## Work package 1 — Restructure the inherited prototype

Goal: isolate browser transport from product logic.

Create modules conceptually equivalent to:

```text
bob/
  cognition/
  workspaces/
  changesets/
  integrations/github/
  integrations/huggingface/
  integrations/supabase/
  integrations/cloudflare/
  api/
```

Keep the existing ChatGPT browser bridge working while moving it behind a `CognitionAdapter`.

Acceptance:
- existing simple chat call still works;
- product code no longer depends directly on Playwright selectors;
- response capture can later be replaced without changing GitHub/change-set logic.

## Work package 2 — Workspace contract

Define a versioned workspace schema.

Required fields:
- name/code;
- GitHub full name;
- stable GitHub repository ID;
- default/base branch;
- canonical entry documents;
- enabled providers and immutable provider identifiers;
- allowed effect classes.

Implement schema validation and identity verification.

Acceptance:
- a wrong repository ID fails closed;
- SL and AB can be represented without Bob-specific code branches;
- no provider credentials are stored in workspace files.

## Work package 3 — Repository context reader

Implement bounded GitHub reads for:
- repository metadata;
- branch/base SHA;
- exact files;
- search results;
- current-work/canonical entry documents.

Do not dump whole repositories by default.

Acceptance:
- context bundle records immutable provenance;
- current-state questions can be grounded in actual repo state;
- read scope is inspectable.

## Work package 4 — Structured change-set contract

Define `BOB_CHANGESET_V1`.

Initial operations:
- `create`;
- `replace` with expected prior SHA;
- `delete` with expected prior SHA.

Every change set binds:
- workspace identity;
- base ref/SHA;
- task ID;
- model response provenance;
- file operations;
- optional verification request.

Acceptance:
- invalid paths/schema are rejected;
- writes outside the selected workspace are impossible;
- stale file SHA prevents mutation.

## Work package 5 — Diff and approval

Render:
- files affected;
- create/replace/delete class;
- textual diff;
- base commit;
- warnings/conflicts.

Approval must bind to the exact candidate hash/change-set version.

Acceptance:
- changing the candidate invalidates prior approval;
- operator can reject without external effect;
- approval does not imply merge/deploy.

## Work package 6 — GitHub writer

Implement:
- branch creation from exact base;
- ordered file writes;
- commit messages;
- PR creation;
- read-back verification.

Prefer a dedicated branch per semantic work unit.

Acceptance:
- end-to-end canary PR from a Bob-generated change set;
- duplicate/replay behavior is explicit;
- partial failure is visible and recoverable;
- no silent write to `main`.

## Work package 7 — Cognition capture V1

Replace preferred response extraction path with a UI/accessibility copy transport while preserving the `CognitionAdapter` contract.

Qualify and use the mechanism locally on Windows as the canonical V1 runtime. DigitalOcean is a V2 transport option after local Bob has proven useful.

Keep transport-specific failure separate from repository effect logic.

Acceptance:
- no preferred-path DOM `inner_text()` extraction;
- copied response is captured exactly;
- session-expiry/copy failure cannot accidentally trigger a GitHub write;
- the capture implementation is not coupled to GitHub/change-set logic.

## Work package 8 — Canary qualification

Use a disposable canary repository before SL/AB writes.

Test:
- create;
- replace;
- delete;
- stale SHA conflict;
- wrong repo ID;
- branch collision;
- malformed model output;
- replay;
- interrupted write;
- PR creation.

Acceptance:
- all fail-closed cases proven;
- audit/provenance sufficient to reconstruct what happened.

## Work package 9 — SL read-only integration

Bind actual SL identity and canonical entry files from its current repository.

First expose:
- status/context reads;
- task/context packaging;
- proposed change sets only.

No writes until the read-only path is correct.

## Work package 10 — SL write qualification

Enable branch/PR effects after exact identity and canary-equivalent checks.

Do not imply merge/deploy.

Once stable, repeat the same generic path for AB.

## Work package 11 — Existing-provider adapters

Add only the project operations that are actually needed.

### Hugging Face
- dispatch qualified job;
- inspect status/log/evidence;
- distinguish dispatch from PASS.

### Supabase
- verify project identity;
- bounded inspect/execute operations;
- explicit approval for material mutation.

### Cloudflare
- Bob frontend deployment/status;
- target-project deploy/status when authorized.

Provider adapters must not become new sources of authority.

## Work package 12 — Bob web UI

Build the responsive operator surface so V1 can run from the loopback Bob API on the operator PC. Cloudflare hosting is optional V2 remote-access infrastructure, not a V1 dependency.

Views:
- workspace selector;
- chat/task;
- context/state;
- proposed change set;
- diff;
- approval;
- PR/job/provider status;
- provenance/audit.

V1 targets the operator PC. The same web product should remain portable to PC/mobile in V2.

## Work package 13 — Local Companion runtime

Goal: make V1 runnable as a normal local product on the operator's Windows PC.

Target topology:

```text
Bob UI foreground tab
→ loopback Bob API
→ loopback CognitionAdapter bridge
→ ChatGPT background tab
```

Acceptance:
- one setup command installs local dependencies;
- one explicit first-run flow creates the authenticated ChatGPT profile using the operator's existing account;
- the operator binds one private ChatGPT Project `Bob` with Project-only memory and an exact `BOB_CHATGPT_PROJECT_URL`;
- normal startup refuses the generic ChatGPT home page, then launches Bob API + bridge and health-gates both;
- Bob is brought to the foreground in the same managed browser;
- ChatGPT remains available in the background for cognition;
- non-loopback configuration fails closed;
- transport failure cannot trigger repository writes.

## V2 remote milestone

Only after V1 is useful in practice, move the replaceable cognition transport to a persistent remote host such as DigitalOcean and add authenticated mobile access.

## V1 completion definition

V1 is complete when:
- one canary and one real workspace can complete the GitHub development loop safely;
- SL can use Bob for ordinary branch/PR development;
- GitHub Actions are not required as the coding engine;
- project identity and authority boundaries fail closed;
- ChatGPT transport is replaceable;
- existing HF/Supabase/Cloudflare infrastructure remains intact and separately authoritative;
- the normal V1 product can run on the operator PC without DigitalOcean.

## First implementation slice

Start with exactly:

```text
workspace schema
+ GitHub identity verifier
+ bounded file reader
+ BOB_CHANGESET_V1 parser
+ diff renderer
+ branch/file/PR writer
+ canary tests
```

Do not start with the polished UI or broad provider orchestration.
