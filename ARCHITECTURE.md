# Architecture

## North-star system

Bob is a thin development control plane over existing project infrastructure.

```text
Operator
   ↕
Cloudflare-hosted Bob UI
   │
   ├──────────── ChatGPT cognition adapter
   │                │
   │                └─ persistent authenticated browser bridge
   │                     ├─ target runtime: DigitalOcean
   │                     └─ secure tunnel via home network for home-IP egress
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

Bob does not replace these systems. It gives them one operator-facing development surface.

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

Provider adapters expose project-native actions without turning Bob into a second runtime.

Before cognition/effects rely on a selected workspace, Bob may run a read-only workspace qualification pass. GitHub and every configured provider must independently verify their bound identity; missing credentials are UNAVAILABLE and mismatches are FAIL, never implicit PASS.

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

## ChatGPT transport and device independence

Direct GitHub/Supabase/HF/Cloudflare operations are server-side and therefore work from both PC and mobile.

Subscription-backed ChatGPT cognition requires a live authenticated browser session somewhere. The target architecture is a **persistent remote cognition bridge**:

```text
PC or mobile
   ↓
Cloudflare Bob UI/API
   ↓
CognitionAdapter
   ↓
DigitalOcean browser bridge
   ↓
encrypted tunnel
   ↓
home network / router
   ↓
normal home-IP egress
   ↓
ChatGPT
```

DigitalOcean is not a general-purpose Bob Core. Its narrow responsibility is to keep the authenticated ChatGPT browser/session available and expose the replaceable cognition transport.

The home-network tunnel exists only to provide the selected network egress path. GitHub, HF, Supabase and Cloudflare integrations remain independent of it.

A PC-local browser bridge remains useful as a development/canary fallback, but it is not the north-star device model.

This makes Bob device-independent: PC and mobile use the same Cloudflare UI and the same remote cognition bridge.

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
DigitalOcean persistent ChatGPT browser/session runtime
Home tunnel   selected ChatGPT egress path
```

Use GitHub Actions only when GitHub-native execution semantics add material value.

## Non-goals for V1

- replacing GitHub with a local Git service;
- building a full local IDE;
- building an always-on **general-purpose** Bob daemon (a narrow persistent ChatGPT browser bridge is allowed);
- autonomous merge/deploy without operator authority;
- generalized arbitrary shell execution;
- reproducing HF/Supabase/Cloudflare features inside Bob.
