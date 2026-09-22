# Bob Persistent Runtime Credential Contract

This document defines the least-privilege credential floor for the persistent Bob runtime.

Secrets never belong in Git, browser JavaScript, Bob protocol messages, logs, or documentation. Runtime values live in `/etc/bob/bob.env`, owned by the dedicated `bob` user and readable only by that identity.

## Two-stage rollout

Do not begin with mutation-capable credentials merely because Bob may need them later.

### Stage A — read-only qualification

Install only enough authority to run:

```bash
python -m bob.preflight --pretty
```

against BOB, SL and AB.

### Stage B — Bob GitHub write canary

Only after Stage A passes, rotate the GitHub credential to the bounded write permission required for one approved Bob-repository branch/PR canary.

Supabase production mutation, Hugging Face Jobs spend and Cloudflare deploy remain disabled by workspace policy and do not require write credentials.

## GitHub — GITHUB_TOKEN

Use a fine-grained personal access token or installation credential restricted to these repositories only:

- `emilmichaelfredrikhansson-bit/cognitive_prosthetic`
- `emilmichaelfredrikhansson-bit/signal-lab-pro`
- `emilmichaelfredrikhansson-bit/autoblog-foundation`

Stage A permissions:

- Metadata: Read
- Contents: Read

Stage B adds:

- Contents: Write
- Pull requests: Write

Do not grant Administration, Actions, Secrets, Environments or Workflows write. GitHub documents Contents Write as sufficient for normal Git ref/content writes; deliberately omitting Workflows Write also creates a provider-side barrier against changing workflow files with this credential.

Bob still enforces workspace identity, effect class, staged-state binding, explicit approval and read-back. Provider access is not Bob authority.

## Supabase — SUPABASE_ACCESS_TOKEN

Prefer a scoped personal access token restricted to exactly these projects:

- SL: `ttycbqaueeaedcrtcpuw`
- AB: `ofnzyuosysdycrdxalve`

Stage A requires:

- Project Settings: Read

Current live `Get project` responses for both projects include the bound `organization_id`, so qualification can verify project + organization without account-wide project-list access.

Optional read diagnostics may add only when needed:

- Edge Functions: Read
- Logs: Read
- Database: Read

Do not grant any Read-write permission for Bob V1 qualification. In particular, do not grant Database Read-write, Project Settings Read-write, Edge Functions Read-write, Storage write or organization-management permissions.

If a future Supabase API shape stops returning `organization_id` from the project response and the narrowly scoped token cannot satisfy Bob's fallback identity check, treat qualification as FAIL and fix the adapter. Do not solve that failure by silently broadening the runtime token to account-wide administration.

## Hugging Face — HF_TOKEN

Stage A needs identity verification only. Use a user token that can authenticate `whoami` for:

```text
Reallothesecond / 6a986fdd2e846637191b1c5e
```

A standard read token is preferred for qualification.

Do not give the persistent Bob runtime Jobs-management authority merely to make preflight pass. If Bob later needs `hf.list_jobs`, `hf.inspect_job` or `hf.job_logs`, use the narrowest token that Hugging Face supports for Jobs access at that time and re-qualify the runtime.

`hf.run_job` and `hf.cancel_job` remain `material_spend` effects and are disabled in the current SL/AB workspaces regardless of token capability.

## Cloudflare — CLOUDFLARE_API_TOKEN

Use an account-scoped API token with read permissions only.

Required current anchors:

- SL identity: R2 bucket `signal-lab-snapshots-prod`
- AB identity: Worker `autoblog-canary`

Minimum permissions:

- Workers R2 Storage: Read
- Workers Scripts: Read

Do not grant Workers Scripts Write, Workers R2 Storage Write, Pages Write, DNS Write, API Tokens Write or account administration.

For SL, provide the exact account ID through `CLOUDFLARE_ACCOUNT_ID`. AB already binds its canonical account ID in its workspace definition. The token itself must be restricted to the actual account resource(s) required by those bindings.

## Runtime secret file

Expected shape:

```dotenv
GITHUB_TOKEN=<secret>
SUPABASE_ACCESS_TOKEN=<secret>
HF_TOKEN=<secret>
CLOUDFLARE_API_TOKEN=<secret>
CLOUDFLARE_ACCOUNT_ID=<sl-account-id>
```

The systemd units also force the credential-bearing HTTP services to loopback independently of this file.

Recommended host controls:

```text
owner = bob:bob
mode = 0600
path = /etc/bob/bob.env
```

Never echo the file in deployment logs or copy it into the repository checkout.

## Qualification rule

A credential is not accepted because it exists.

The runtime is qualified only after Bob independently reads the bound external identities and `python -m bob.preflight --pretty` returns success for BOB, SL and AB.

`DISPATCH != PASS`.
