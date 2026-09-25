# Bob Manual Relay V1

Manual relay is the qualified browser-independent cognition path for Bob Core V1.

It keeps the same authority model as the browser loop:

```text
human
→ external/interactive ChatGPT cognition
→ BOB.READ / BOB.EFFECT
→ Bob deterministic adapters
→ verified BOB.RESULT
→ same cognition loop
```

The external LLM never performs provider effects directly. It only emits Bob protocol requests.

## HTTP loop

### 1. Start

Call:

```http
POST /bob/relay/start
```

with:

```json
{
  "workspace": "BOB",
  "message": "Continue the current work from repository truth."
}
```

Bob returns `status=PROMPT_READY` and an exact `prompt` containing the
`BOB.WORKSPACE` packet plus the human request.

Paste/send that prompt unchanged to the cognition model.

### 2. Process a model response

Send the complete model response to:

```http
POST /bob/relay
```

with:

```json
{
  "workspace": "BOB",
  "model_response": "<complete model response>"
}
```

Possible outcomes:

- `RESULT_READY` — Bob executed one or more read requests and returned verified `feedback`. Send that feedback unchanged back to the same cognition loop.
- `AWAITING_APPROVAL` — Bob staged exact effects. The operator must inspect the candidate/diff and explicitly approve the exact `pending_id`.
- `DONE` — the cognition loop emitted `BOB.DONE`.
- `ASK_USER` — the cognition loop emitted `BOB.ASK`.
- `NO_TOOL_REQUEST` — no Bob protocol request was present.

### 3. Approve an effect

Call:

```http
POST /bob/relay/approve
```

with the exact pending ID.

Bob recomputes the candidate hash before execution. If the pending candidate
changed, approval fails closed. After execution Bob returns a verified
`BOB.RESULT` feedback block. Send that block unchanged back to the same
cognition loop.

## Workspace qualification

Before relying on a workspace, call:

```http
POST /bob/qualify
```

with its workspace code.

GitHub and every configured provider must independently PASS. A missing runtime
credential/adapter is `UNAVAILABLE`; identity mismatch/provider errors are
`FAIL`. Neither state is qualification.

## Invariants

- READ and EFFECT are never mixed in one model turn.
- External dispatch is not PASS.
- Effects require the workspace effect class plus exact operator approval.
- Provider/repository state must be read back before effect success is reported.
- Model output cannot expand authority.
- Manual relay is a cognition transport seam, not a bypass around Bob.
