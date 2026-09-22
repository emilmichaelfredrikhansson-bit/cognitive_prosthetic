# Builder V1 Implementation Plan

## Objective

Create the smallest production-useful Builder that can develop a real repository through ChatGPT-generated code while writing accepted changes directly to GitHub, preserving the existing SL/AB infrastructure model.

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
builder/
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
- SL and AB can be represented without Builder-specific code branches;
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

Define `BUILDER_CHANGESET_V1`.

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
- end-to-end canary PR from a Builder-generated change set;
- duplicate/replay behavior is explicit;
- partial failure is visible and recoverable;
- no silent write to `main`.

## Work package 7 — Cognition capture V1

Replace preferred response extraction path with a UI/accessibility copy transport while preserving the `CognitionAdapter` contract.

First qualify the mechanism locally on Windows if useful, then run the production-oriented browser bridge on DigitalOcean.

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
- Builder frontend deployment/status;
- target-project deploy/status when authorized.

Provider adapters must not become new sources of authority.

## Work package 12 — Cloudflare web UI

Build the responsive operator surface after the GitHub development loop is proven.

Views:
- workspace selector;
- chat/task;
- context/state;
- proposed change set;
- diff;
- approval;
- PR/job/provider status;
- provenance/audit.

PC and mobile share one web application.

## Work package 13 — Persistent remote cognition bridge

Goal: remove the requirement for the operator's PC to host the ChatGPT session.

Target topology:

```text
Cloudflare Builder UI/API
→ authenticated CognitionAdapter call
→ DigitalOcean persistent browser/session
→ secure tunnel to home network/router
→ ChatGPT via selected home-IP egress
```

Responsibilities of the DigitalOcean component are intentionally narrow:
- maintain the authenticated browser/session;
- perform the UI/accessibility cognition transport;
- report health/session state;
- expose no generic shell/build authority to the UI.

The home tunnel is an egress mechanism, not a Builder authority source.

Acceptance:
- cognition works from both PC and mobile through the same Builder UI;
- no operator PC needs to remain online;
- tunnel/browser restart is recoverable;
- bridge failure cannot trigger repository writes;
- GitHub/HF/Supabase/Cloudflare remain independently reachable when the cognition bridge is unavailable.

## Mobile cognition milestone

Once the Cloudflare UI and persistent DigitalOcean cognition bridge exist, PC and mobile become equivalent control clients for the normal Builder development loop.

## V1 completion definition

V1 is complete when:
- one canary and one real workspace can complete the GitHub development loop safely;
- SL can use Builder for ordinary branch/PR development;
- GitHub Actions are not required as the coding engine;
- project identity and authority boundaries fail closed;
- ChatGPT transport is replaceable;
- existing HF/Supabase/Cloudflare infrastructure remains intact and separately authoritative.

## First implementation slice

Start with exactly:

```text
workspace schema
+ GitHub identity verifier
+ bounded file reader
+ BUILDER_CHANGESET_V1 parser
+ diff renderer
+ branch/file/PR writer
+ canary tests
```

Do not start with the polished UI or broad provider orchestration.
