# Workspace Contract

A Bob workspace is the smallest unit of project identity, context routing and effect authority.

## Goals

The same Bob Core must support Signal Lab, AutoBlog and future projects without project-specific branches in product code.

A workspace is configuration plus verified external identity. It is not a source of new authority.

## Required identity

Each workspace must bind:

```json
{
  "schema": "BOB_WORKSPACE_V1",
  "project": {
    "name": "Signal Lab",
    "code": "SL"
  },
  "github": {
    "repository": "owner/repo",
    "repository_id": 123456789,
    "default_branch": "main"
  }
}
```

The stable repository ID is the primary GitHub trust boundary.

## Context entry points

A workspace may declare bounded canonical entry documents, for example:

```json
{
  "context": {
    "entry_documents": [
      "CURRENT_WORK.md",
      "AGENTS.md",
      "ARCHITECTURE.md"
    ]
  }
}
```

These are navigation hints, not permission to ingest the entire repository.

## Provider bindings

Providers are explicit and optional.

```json
{
  "providers": {
    "hugging_face": {
      "enabled": true,
      "namespace": "..."
    },
    "supabase": {
      "enabled": true,
      "project_id": "..."
    },
    "cloudflare": {
      "enabled": true,
      "resource": "..."
    }
  }
}
```

Credentials do not belong in the workspace file.

## Effect policy

A workspace may narrow Bob's global effect policy, never broaden it.

Example:

```json
{
  "effects": {
    "read_diagnose": true,
    "propose_changeset": true,
    "write_branch": true,
    "open_pr": true,
    "merge": false,
    "deploy": false,
    "mutate_production_state": false
  }
}
```

Runtime authority is the intersection of:
- Bob global effect boundary;
- workspace policy;
- current operator approval;
- provider/repository identity verification.

## Verification

Before privileged GitHub effects:

```text
configured repository ID
=
actual GitHub repository ID
```

Before provider effects, equivalent immutable project/resource identity must be checked where the provider exposes one.

A UI-selected workspace name is never sufficient proof of identity.

## Change-set binding

Every candidate change set must bind:
- workspace code;
- stable repository ID;
- base branch;
- base commit SHA;
- exact candidate hash;
- proposed operations.

An approval is invalid if any of these change.

## Isolation invariant

No data read from one workspace may cause an effect in another workspace unless the operator explicitly initiates a separately verified cross-workspace operation.

SL and AB are distinct authority domains even if the same operator and integrations can access both.
