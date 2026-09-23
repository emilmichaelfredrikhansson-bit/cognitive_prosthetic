# Architecture

## North-star system

Bob is a thin development control plane over existing project infrastructure.

```text
Operator PC
   ↕
Bob UI (V1: loopback)
   │
   ├──────────── ChatGPT cognition adapter
   │                │
   │                └─ managed persistent Chromium
   │                     ├─ Bob tab: foreground
   │                     └─ ChatGPT tab: background
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

V1 deliberately runs on the operator's own computer. V2 may move the replaceable ChatGPT cognition transport to a persistent DigitalOcean host and add authenticated remote/mobile access without changing Bob Core authority semantics.

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

### 6. Bob Web UI / API

The operator-facing product is a responsive web interface. V1 is served directly from the loopback Bob API on the operator PC. V2 may place the same product behind an authenticated Cloudflare boundary for remote/mobile use.

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

The Python Bob API and ChatGPT browser bridge are **loopback-only** in V1 and do not grant cross-origin browser access. V1 intentionally has no public/LAN Bob endpoint. Any V2 remote/mobile reachability must be provided by an explicit authenticated reverse-proxy/tunnel boundary, not by binding the credential-bearing Python services directly to a public/LAN interface.

## ChatGPT account and project isolation

Bob V1 uses the operator's **existing ChatGPT subscription/account**; it does not require or assume a second OpenAI account. The Bob-managed Chromium profile is nevertheless a separate browser profile from the operator's normal browser session.

All Bob cognition must be confined to one dedicated private ChatGPT Project, canonically named **Bob**:

```text
same ChatGPT Plus account
├─ operator's normal ChatGPT/browser
│  └─ normal chats and other projects
└─ Bob-managed Chromium profile
   └─ private ChatGPT Project: Bob
      └─ Bob-created cognition threads only
```

The Bob project should use **Project-only memory** when the account offers it. Bob must never deliberately target the ChatGPT home page, a normal personal chat, or another project for cognition. New Bob conversations begin from the exact configured Bob Project URL. Project instructions belong in that project and define the ChatGPT side of the Bob protocol.

The same-account model means normal human ChatGPT use can continue in parallel, but subscription/account usage limits are shared rather than multiplied.

## ChatGPT transport and runtime evolution

Direct GitHub/Supabase/HF/Cloudflare operations remain independent provider adapters.

### V1 — Local Companion

Subscription-backed ChatGPT cognition uses a dedicated persistent browser profile on the operator PC:

```text
Bob UI (foreground tab)
   ↓
Bob API 127.0.0.1:5002
   ↓
CognitionAdapter
   ↓
ChatGPT bridge 127.0.0.1:5001
   ↓
ChatGPT (background tab in the same managed Chromium context)
```

The local launcher starts both services, waits for health, then asks the bridge to bring the Bob tab to the front. The ChatGPT tab stays available for the cognition loop. Browser profile/session state is machine-local and is never repository authority.

### V2 — Persistent Remote

After V1 is proven useful, the same replaceable cognition transport may move to DigitalOcean so the operator PC no longer needs to remain online and mobile can use the same Bob product. Remote access must add an authenticated transport boundary and must not expand workspace authority.

DigitalOcean remains a narrow browser/session runtime, not a second general-purpose Bob Core.

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
ChatGPT       cognition
Local PC V1   Bob UI/API + authenticated browser/session transport
GitHub        source/history/PR semantics
HF            portable execution
Supabase      DB/runtime/canonical project state
Cloudflare    project hosting/effects; optional V2 authenticated UI boundary
DigitalOcean  optional V2 persistent ChatGPT browser/session runtime
```

Use GitHub Actions only when GitHub-native execution semantics add material value.

## Non-goals for V1

- replacing GitHub with a local Git service;
- building a full local IDE;
- building an always-on **general-purpose** Bob daemon (a narrow persistent ChatGPT browser bridge is allowed);
- autonomous merge/deploy without operator authority;
- generalized arbitrary shell execution;
- reproducing HF/Supabase/Cloudflare features inside Bob.
