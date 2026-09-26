# Bob Self-Development Promotion Gate V1

The promotion gate separates a verified self-development candidate from canonical promotion authority.

It is a review boundary, not a merge engine.

## Preconditions

A proposal can be created only for a self-development item that is already QUALIFIED.

The gate re-reads the durable qualification receipt and requires:
- the exact bound lane=selfdev execution run;
- execution state CANCELLED;
- promotion_authority=NONE in both run authority and qualification receipt;
- exact branch identity;
- exact candidate head SHA;
- unchanged qualification evidence hash.

## Proposal binding

A proposal durably binds:
- repository identity and canonical ref;
- self-development item and execution run IDs;
- candidate branch and exact candidate head SHA;
- qualification evidence hash;
- canonical SHA observed when the proposal was created;
- fresh canonical SHA observed during later revalidation;
- explicit merge_authority=NONE;
- explicit provider_effect_performed=false.

A candidate equal to canonical is not promotable work.

If current canonical is not an ancestor of the candidate, the proposal is REBASE_REVERIFY_REQUIRED.

## Operator review

Only a PENDING_OPERATOR_REVIEW proposal may be approved.

Approval requires the caller to echo the exact:
- candidate head SHA;
- current canonical SHA.

The gate revalidates the candidate immediately before recording approval.

Approval produces APPROVED_FOR_MANUAL_PROMOTION.
This state means only that an operator reviewed this exact candidate/canonical pair.
It grants no merge, push, integration or provider authority.

A later promotion executor, if implemented, must independently revalidate this receipt before any effect.

## Stale state

Revalidation fails closed when:
- the qualification receipt changes;
- the candidate branch moves;
- the candidate is already canonical;
- canonical moves outside the candidate ancestry;
- an already-approved proposal no longer refers to the exact approved canonical SHA.

Stale or rebase-required proposals cannot be approved in place.

Rejected proposals are durable and cannot later be approved.

## Explicit non-capabilities

This module never:
- merges, rebases or cherry-picks;
- pushes or force-pushes;
- opens a pull request;
- changes execution integration state;
- changes workspace or provider authority;
- promotes a candidate because model/selfdev output says it is better.

## Safety invariant

The promotion gate is capability-compounding without authority-compounding.

A worst-plausible unattended cognition may produce a qualified candidate and a review proposal, but cannot use this module to alter canonical Bob state.

Canonical promotion remains a separate operator-controlled effect boundary.
