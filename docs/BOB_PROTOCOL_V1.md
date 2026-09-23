# BOB Protocol V1

BOB Protocol V1 is the narrow machine language between a normal ChatGPT conversation and Bob's deterministic project I/O.

## Principle

```text
human ↔ ChatGPT cognition ↔ Bob protocol ↔ deterministic adapters ↔ external reality
                                      ↑                          ↓
                                      └──── verified result ─────┘
```

The protocol is intentionally smaller than the underlying provider APIs.

ChatGPT asks for semantic tools. Bob owns credentials, identity binding, mechanical execution, authority and verification.

## Model-to-Bob messages

Each request is a fenced `bob` JSON object with a unique `id`.

### Read

```bob
{
  "type": "BOB.READ",
  "id": "read-1",
  "tool": "github.read_file",
  "args": {"path": "CURRENT_WORK.md"}
}
```

Reads may execute automatically inside the selected verified workspace.

### Effect

```bob
{
  "type": "BOB.EFFECT",
  "id": "effect-1",
  "tool": "github.replace_file",
  "args": {
    "branch": "feat/example",
    "path": "src/example.py",
    "expected_sha": "...",
    "content": "..."
  }
}
```

Effects are checked against:
- selected workspace;
- stable provider identity;
- declared effect class;
- workspace effect policy;
- authority-relevant workspace binding;
- staged external state for the target GitHub refs/files;
- exact candidate hash;
- operator approval.

Bob recomputes the candidate binding immediately before execution. If a bound
branch/file state or workspace/provider/effect-policy binding changed after
staging, the approval is invalid and the effect fails closed.

### Ask human

```bob
{
  "type": "BOB.ASK",
  "id": "ask-1",
  "args": {"question": "...", "reason": "..."}
}
```

### Done

```bob
{
  "type": "BOB.DONE",
  "id": "done-1",
  "args": {"summary": "..."}
}
```

## Bob-to-model messages

Bob injects results back into the **same ChatGPT conversation**:

```bob-result
{
  "type": "BOB.RESULT",
  "request_id": "read-1",
  "tool": "github.read_file",
  "status": "PASS",
  "data": {}
}
```

A failure uses `status: FAIL` and an `error` field.

The model must continue from the returned state. Requesting an effect never makes the effect true.

## Runtime workspace packet

On the first turn in a workspace Bob injects:
- workspace identity;
- stable GitHub repository ID;
- provider bindings without secrets;
- allowed effect classes;
- currently available tools.

Capabilities are runtime data and may differ between installations.

## V1 tools

### GitHub reads
- `github.repo`
- `github.read_file`
- `github.read_files`
- `github.list_contents`

### GitHub effects
- `github.create_branch`
- `github.create_file`
- `github.replace_file`
- `github.delete_file`
- `github.open_pr`

### Supabase reads
- `supabase.project`
- `supabase.functions`
- `supabase.logs`
- `supabase.read_only_query`

### Supabase effects
- `supabase.query`

### Hugging Face reads
- `hf.list_jobs`
- `hf.inspect_job`
- `hf.job_logs`

### Hugging Face effects
- `hf.run_job`
- `hf.cancel_job`

### Cloudflare reads
- `cloudflare.identity`
- `cloudflare.r2_buckets`
- `cloudflare.worker`
- `cloudflare.worker_versions`
- `cloudflare.worker_deployments`
- `cloudflare.worker_deployment`
- `cloudflare.pages_project`
- `cloudflare.pages_deployments`
- `cloudflare.pages_deployment`

### Cloudflare effects
- `cloudflare.worker_deploy_version`
- `cloudflare.pages_retry`
- `cloudflare.pages_rollback`

Cloudflare workspaces may bind an R2 bucket as their account identity anchor.
The account id may be supplied only at runtime; Bob verifies the anchor before
trusting Worker/Pages state or performing an effect.

The vocabulary will grow only when a real project needs another semantic tool.

## Large-work context envelope

BOB Protocol V1 currently injects a workspace packet and verified tool results into a cognition conversation. For large-project orchestration, the canonical architecture additionally requires a **bounded compiled context envelope** around a coherent work node.

This is an architecture contract, not a claim that the current runtime already implements the full Context Compiler.

Conceptually the envelope carries:

- work-node identity and goal;
- explicit scope / ownership boundary;
- relevant contracts and dependencies;
- bounded current files/reality;
- blockers and waiting conditions;
- authority/effect constraints;
- verification and exit criteria;
- freshness/provenance references.

The envelope must be derived from durable Bob project state, not from a transcript being treated as canonical memory.

When the runtime implements this fully, protocol evolution should preserve the same principle: a cognition thread receives the smallest sufficient world for its work, not the whole project.

## Closed-loop rule

Every dependent cognition step follows:

```text
request
→ execute
→ verify actual state
→ BOB.RESULT
→ continue cognition
```

No external effect is considered successful before verified reality feedback returns to the same cognition loop.
