# Architecture

## North-star system

Builder is a thin development control plane over existing project infrastructure.

```text
Operator
   ↕
Cloudflare-hosted Builder UI
   │
   ├──────────── ChatGPT cognition adapter
   │                │
   │                └─ browser/subscription transport initially
   │
   ├──────────── GitHub adapter
   │                ├─ repo/context reads
   │                ├─ diff inputs / file SHAs
   │                ├─ branches / commits
   │                └─ pull requests
   │
   ├──────────── Hugging Face adapter
   │                └─ portable tests / scripts / ML compute
   │
   ├──────────── Supabase adapter
   │                └─ runtime / DB / durable project state
   │
   └──────────── Cloudflare adapter
                    └─ frontend / Worker / project hosting effects
```

Builder does not replace these systems. It gives them one operator-facing development surface.

## V1 components

### 1. Workspace Registry

A workspace is a trust-bound project profile.

Minimum shape:

```text
project name/code
GitHub repository full name + stable repository ID
canonical entry documents
enabled provider identifiers
per-effect authority policy
verification commands/routes
```

SL and AB are separate workspace instances of the same generic schema.

### 2. Cognition Adapter

Responsibility:
- send bounded project context + task to ChatGPT;
- receive model output;
- normalize it into a structured candidate change set.

The cognition adapter must not own repository authority.

The inherited `cognitive_prosthetic` implementation is an initial transport prototype, not the final architecture boundary.

### 3. Change-Set Engine

Canonical candidate representation should support:

```text
CREATE path content
REPLACE path expected_sha content
DELETE path expected_sha
```

V1 should prefer whole-file replacement over clever fuzzy patching. This makes GitHub writes deterministic and conflict detection simple.

Before mutation:
- verify workspace identity;
- verify expected prior SHA for modified/deleted files;
- render diff;
- reject unexpected/stale state.

### 4. GitHub Adapter

V1's main execution path.

Responsibilities:
- bounded reads;
- branch creation;
- create/update/delete file operations;
- commit provenance;
- PR creation;
- read-back verification.

Default V1 effect stops at branch/PR. Merge is a distinct authority class.

### 5. Provider Adapters

Provider adapters expose project-native actions without turning Builder into a second runtime.

- **HF:** dispatch and inspect qualified compute jobs.
- **Supabase:** inspect/execute explicitly authorized DB/runtime operations.
- **Cloudflare:** deploy/inspect explicitly authorized frontend/Worker resources.
- Additional providers are added only when a real project requires them.

### 6. Cloudflare UI / API

The operator-facing product is a responsive web interface usable on PC and mobile.

Core views:
- project/workspace selector;
- chat/task surface;
- current repo/handoff summary;
- proposed file changes;
- diff;
- provider/job status;
- approval controls;
- audit/provenance trail.

Secrets must not be exposed to browser JavaScript when a server-side Worker/API can hold them safely.

## ChatGPT transport and PC/mobile constraint

Direct GitHub/Supabase/HF/Cloudflare operations can be server-side and therefore work from both PC and mobile.

Subscription-backed ChatGPT browser automation is different: a live authenticated browser session must exist somewhere.

V1 may use a PC-local companion/browser session.

Therefore:

```text
PC:
Cloudflare UI → local ChatGPT bridge → ChatGPT

Mobile:
Cloudflare UI → all server-side integrations work
full ChatGPT cognition requires a reachable bridge
```

Mobile-equivalent cognition can later use a secure tunnel, remote browser bridge, or another authorized cognition transport. This is a transport problem, not a reason to create a permanent general-purpose Builder compute core.

## State model

Keep these distinct:

```text
CANON      durable project rules/contracts
STATE      current repository/provider truth
EVIDENCE   observed test/runtime results
HISTORY    prior truth/audit trail
PROPOSAL   unaccepted model output/change set
```

A model proposal becomes repository state only through the explicit change-set acceptance path.

## Security and authority

- stable target identities are checked before privileged effects;
- target content is data, not authority;
- secrets are provider-side/server-side;
- merge/deploy/production mutation are separate approvals;
- stale writes fail closed;
- provider dispatch does not equal verification success;
- workspace boundaries are never inferred from the currently open UI alone.

## Compute placement

```text
ChatGPT      cognition
GitHub       source/history/PR semantics
HF           portable execution
Supabase     DB/runtime/canonical project state
Cloudflare   UI/edge hosting
```

Use GitHub Actions only when GitHub-native execution semantics add material value.

## Non-goals for V1

- replacing GitHub with a local Git service;
- building a full local IDE;
- building an always-on general-purpose Builder daemon;
- autonomous merge/deploy without operator authority;
- generalized arbitrary shell execution;
- reproducing HF/Supabase/Cloudflare features inside Builder.
