# CURRENT_WORK

`CURRENT_WORK.md` is Builder's primary operational handoff.

## ROOT_OF_TRUST

- GitHub repository: `emilmichaelfredrikhansson-bit/cognitive_prosthetic`
- GitHub repository ID: `1374229539`
- Project identity: `governance/project-identity.json`
- Constitution: `PROJECT_CONSTITUTION.md`
- Agent protocol: `AGENTS.md`
- Architecture: `ARCHITECTURE.md`
- Strategic direction: `ROADMAP.md`
- Implementation plan: `docs/BUILDER_V1_PLAN.md`

## CURRENT_MODE

`DEVELOPMENT`

## CURRENT_EXECUTOR

`CHAT_INTERACTIVE`

## CURRENT_ARCHITECTURE

Builder is being established as a thin project-agnostic development control plane over ChatGPT + GitHub + Hugging Face + Supabase + Cloudflare.

The inherited repository currently supplies only a ChatGPT browser/local-API prototype. It does not yet implement workspace management, GitHub direct writes, structured change sets, provider adapters, or the Builder UI.

## LAST_COMPLETED

- fork identity verified against `CodeMongerrr/cognitive_prosthetic`;
- Project Foundation 0.3.0 principles reviewed and selectively adopted;
- Builder root-of-trust, constitution, agent protocol and product architecture defined;
- V1 explicitly rejects an unnecessary always-on general-purpose Builder Core;
- compute placement preserves existing SL/AB infrastructure and minimizes GitHub Actions dependency.

## ACTIVE_WORK

`BUILDER_V1_FOUNDATION_AND_ARCHITECTURE`

Complete the project bootstrap and land the architecture/implementation plan before coding the product.

## NEXT_INTENDED_WORK

Implement **GitHub Development Loop V1**:

```text
workspace config
→ bounded repo reads
→ structured ChatGPT change-set contract
→ diff/stale-state checks
→ operator approval
→ direct GitHub branch/commit/PR
```

Do this before adding broad provider orchestration.

## OPEN_FINDINGS

- ChatGPT response transport must be separated from product logic. Current upstream DOM extraction is not the desired long-term capture path.
- Windows UI Automation/accessibility is the preferred first PC capture experiment.
- Full mobile ChatGPT cognition needs a reachable authenticated browser bridge or another cognition transport; direct GitHub/HF/Supabase/Cloudflare controls do not have this limitation.
- The final Cloudflare authentication/session model is not yet selected.
- SL and AB workspace contracts must be derived from their actual current root-of-trust, not reconstructed from memory.

## FIRST_ACTION

After this foundation PR is accepted, implement the workspace schema and GitHub adapter with a canary repository before connecting SL or AB write authority.

## HARD_BLOCKERS

- No target-project privileged write without exact workspace identity verification.
- No production deploy/merge/destructive mutation implied by ordinary development approval.
- No secrets committed to Builder or target repositories.
- No model-generated target path or repository identifier may expand authority beyond the selected verified workspace.
- No GitHub Actions job is added merely as generic compute if an existing qualified backend can perform the work.
