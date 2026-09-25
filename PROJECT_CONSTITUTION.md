# Project Constitution

This document is Bob's durable normative core.

## Source of truth and handoff

- **CURRENT REPO STATE > CHAT MEMORY.**
- **CURRENT_WORK = PRIMARY HANDOFF.**
- **ROADMAP = STRATEGIC DIRECTION, NOT CURRENT STATE.**
- **AGENTS = OPERATING PROTOCOL.**
- **CANON != STATE != EVIDENCE != HISTORY.**

## Product boundary

Bob is an orchestration and development interface over existing systems.

It should not recreate mature infrastructure already supplied by:
- ChatGPT for cognition and code generation;
- GitHub for source control and repository semantics;
- Hugging Face for portable compute and ML execution;
- Supabase for database/runtime/canonical project state;
- Cloudflare for the web interface and project hosting/runtime where used.

The default architectural question is:

> Can this capability be added as a thin, explicit integration instead of creating a new permanent subsystem?

## Development model

- Operator-present interactive development is the default for operator-directed work. Unattended self-development may run only inside an explicitly bounded self-development mode with isolated work state, least-privilege capabilities and no autonomous authority expansion.
- Broad cognition is encouraged; external effects stay narrow.
- Access is not authority.
- Candidate model output is not automatically accepted code.
- A proposed change becomes actionable only after identity checks, deterministic validation appropriate to the effect, and operator approval where required.
- One semantic work item should have one active executor unless explicitly handed off or superseded.

## Recursive self-development boundary

Bob may recursively improve its own capabilities, but self-development is never self-authorization.

Unattended self-development must be structurally constrained so that a bad cognition decision cannot directly destroy or promote canonical project state.

Minimum constitutional rules:

- interactive work has priority over background self-development;
- unattended mutation uses isolated work state such as a dedicated worktree/branch;
- one semantic mutating scope has one active executor/lease;
- provider credentials remain least-privilege and should independently deny catastrophic administration;
- normal self-development capability does not include repository deletion, protected-branch force push/deletion, repository/ruleset administration, secrets administration or unauthorized production mutation/deploy/spend;
- promotion/merge into canonical Bob state is a separate effect class from experimentation/branch work;
- checkpoints, deterministic verification and rollback/discard are required around material self-development changes;
- recursive changes may improve capability, context, knowledge and verification, but may not weaken root-of-trust, workspace isolation, approval classes or provider protections without explicit authorized canon.

Canonical details live in `docs/BOB_RECURSIVE_SELF_IMPROVEMENT_ARCHITECTURE.md`.

The Knowledge Fabric defined in `docs/BOB_KNOWLEDGE_FABRIC_ARCHITECTURE.md` is cognition support only. Knowledge never grants authority.

## Bob V1 contract

The V1 development loop is intentionally small:

```text
target workspace
→ bounded repository/context read
→ ChatGPT cognition/code proposal
→ structured change set
→ deterministic diff/validation
→ operator approval
→ direct GitHub branch/commit/PR effect
```

No always-on general-purpose Bob compute service is required for V1.

When code must actually execute, use existing qualified project infrastructure:
- Hugging Face for portable tests, scripts, ML and batch compute;
- Supabase for database/runtime verification when relevant;
- GitHub-hosted execution only when GitHub-native semantics materially require it.

## Compute placement

Use the cheapest qualified backend with no assurance regression.

GitHub Actions are not the default CPU layer merely because the source lives on GitHub. Avoid paid Actions for development work that can be performed through direct repository writes plus existing HF/Supabase/Cloudflare infrastructure.

Do not combine distinct authority domains merely to reduce cost.

## Effect boundaries

The following are separate effect classes:
- read/diagnose;
- create proposed changes;
- write branch commits;
- open pull requests;
- merge;
- deploy;
- mutate production data/state;
- incur material external spend.

Authority for one class never implies authority for another.

Default:
- reads and local proposal construction may be automatic;
- branch writes may be operator-approved per work unit;
- merge, production deploy, destructive state mutation, secrets changes, and material spend require explicit authority.

## Workspace isolation

Each target project is a separate trust domain.

A Bob workspace must bind at minimum:
- project name/code;
- stable GitHub repository ID;
- repository full name;
- relevant canonical/handoff documents;
- enabled integration identifiers;
- permitted effect classes.

SL authority must not become AB authority, and vice versa.

## ChatGPT transport

ChatGPT is a cognition provider, not the source of repository authority.

The transport used to move prompts and model output may evolve independently from the development protocol.

The current inherited implementation uses browser automation. The intended Bob design replaces DOM response extraction with a user-facing UI/accessibility copy path where practical, while keeping cognition transport behind an adapter boundary.

## Good-enough rule

Do not build a speculative IDE framework before the next real project need earns it.

Prefer the smallest architecture that makes the end-to-end development loop reliable and reusable.
