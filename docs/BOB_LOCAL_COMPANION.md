# Bob V1 Local Companion

Bob V1 runs entirely on the operator's own computer. DigitalOcean is deferred to V2.

## Product model

```text
Windows PC
└─ Bob managed Chromium
   ├─ Bob UI                foreground tab
   └─ ChatGPT               background tab
       ↕
   local ChatGPT bridge     127.0.0.1:5001
       ↕
   Bob API / Core           127.0.0.1:5002
       ↕
   GitHub / Supabase / HF / Cloudflare adapters
```

The ChatGPT tab uses a dedicated persistent Bob browser profile, signed into the operator's **same ChatGPT account/Plus subscription**. The operator's normal browser remains independent and can continue using ChatGPT normally. The Bob browser profile is not fake history and it does not copy browser cookies into the repository.

Both credential-bearing Python services are loopback-only. V1 has no public Bob endpoint, tunnel, Cloudflare Access dependency or DigitalOcean runtime.

## Dedicated ChatGPT Project contract

Create one private ChatGPT Project named **Bob** in the same account and set its Memory setting to **Project-only memory**. Bob's browser bridge is allowed to create/use cognition chats only inside that project.

Canonical rules:

- same ChatGPT account/subscription as the operator;
- separate Bob-managed browser profile;
- dedicated private ChatGPT Project named `Bob`;
- Project-only memory preferred/required for V1 qualification when available;
- `BOB_CHATGPT_PROJECT_URL` stores the exact project URL locally;
- Bob must not target the ChatGPT home page, a personal chat, or another project;
- each Bob New Chat starts by navigating to the configured Bob Project URL;
- future Bob history may expose only real ChatGPT thread URLs/identities from this project.

This gives product separation without a second subscription. Account-level usage/rate limits are still shared with normal ChatGPT use.

## Windows first run

From a fresh checkout of `feat/bob-core-v1`:

1. Run `setup_bob.bat`.
2. Copy/edit `.env.local` as needed. Never commit it.
3. Put only the provider credentials Bob actually needs into `.env.local`.
4. In your normal ChatGPT, create/open the private project **Bob**, set Memory to **Project-only memory**, and copy its exact URL.
5. Put that URL in `.env.local` as `BOB_CHATGPT_PROJECT_URL=...`.
6. Run `first_run_bob.bat` and sign in with the **same ChatGPT account** in the Bob browser profile.
7. Bob starts both local services, verifies the dedicated project target and browser health, opens Bob in the same browser, and brings the Bob tab to the front.

After the first run, use `start_bob.bat`.

Equivalent commands:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium
copy .env.local.example .env.local
.venv\Scripts\python.exe bob_local.py --login
```

Normal later start:

```powershell
.venv\Scripts\python.exe bob_local.py
```

## What the launcher does

`bob_local.py`:

1. reads optional machine-local `.env.local`;
2. refuses non-loopback Bob/bridge binding;
3. refuses a non-loopback companion UI URL;
4. starts `bob_api_server.py`;
5. waits for Bob health;
6. starts `chatgpt_api_server.py`;
7. waits for the authenticated ChatGPT bridge to be ready;
8. calls the bridge's loopback-only `POST /show-ui`;
9. the bridge opens/focuses Bob in the same persistent Chromium context, leaving the ChatGPT target available in the background;
10. Ctrl+C stops both child processes.

## ChatGPT response capture

Bob V1 reads assistant responses through ChatGPT's normal visible **Copy** action:

```text
latest assistant response
-> visible Copy action
-> clipboard
-> Bob bridge
```

This is the canonical V1 path. It deliberately avoids making ChatGPT DOM structure the primary interface.

`CHATGPT_CAPTURE_MODE=copy` is the normal setting. `legacy_dom` exists only as an explicit compatibility escape hatch and must not be treated as an automatic fallback. If Copy capture fails during qualification or later use, surface it as a transport problem first.

Windows UI Automation/accessibility remains a possible future hardening path if repeated live failures justify it; it is not required before V1 can ship or be useful.

## ChatGPT traffic control

The managed ChatGPT session is a shared external resource, separate from repository execution capacity. Bob may keep up to three active runs per repository, and different repositories may have independent coordinators, while all ChatGPT browser writes still pass through one serialized Playwright worker.

The bridge adds a dedicated traffic-control policy at that shared choke point:

- fresh-chat attempts are spaced by at least `CHATGPT_FRESH_CHAT_MIN_INTERVAL_SECONDS` (default 10 s) plus bounded random jitter (default 0..3 s);
- visible `RATE_LIMITED` or `USAGE_LIMIT` UI states do not trigger transparent retry;
- a transient-limit observation starts exponential cooldown using `CHATGPT_RATE_LIMIT_BACKOFF_SECONDS` (default 15,30,60,120 s), with bounded jitter;
- successful ChatGPT writes reset the transient-limit streak;
- after Enter, Bob requires observable user/conversation state within `CHATGPT_SUBMISSION_TIMEOUT_SECONDS` (default 12 s) before entering the long assistant-response wait;
- if no turn materializes, the request fails distinctly as `CHATGPT_SUBMISSION_FAILED:NO_CONVERSATION_TURN` rather than being misclassified as a multi-minute assistant timeout;
- repository/Shell/provider work continues independently while cognition waits;
- request diagnostics and `GET /status` expose only sanitized pacing/cooldown or turn-count metadata, never prompt or response content.

This is intentionally conservative. The initial values are qualification defaults for the hypothesis that short fresh-chat bursts contribute to recurring `Too many requests` failures. Submission materialization is tracked separately because live evidence has also shown prompts that appeared to be submitted but produced zero conversation turns. The two failure classes must not be conflated.

## Security and authority

Local does not mean unlimited.

- Access is not authority.
- Workspace identity and provider bindings remain mandatory.
- Existing Bob effect policy still controls branch writes, PR creation, production mutation, spend and deploy.
- The local launcher does not expand any workspace effect class.
- `.env.local`, browser profiles and profile configuration remain machine-local.
- The browser-facing UI receives no provider secrets.
- `BOB_HOST` and `CHATGPT_BRIDGE_HOST` must stay loopback in V1.
- `BOB_COMPANION_UI_URL` must point to localhost/loopback.

## Conversation history

V1 does not invent a Bob-side persistent conversation history. The real ChatGPT browser session may retain its own threads, but Bob only advertises resumable history after it can persist and reopen the exact underlying ChatGPT thread identity/URL.

## Failure behavior

If the browser profile is missing, the bridge is not ready, UI capture fails, or either local service exits, the launcher surfaces the failure and stops its child processes. A transport failure does not turn a proposed Bob effect into PASS.

## V2

V2 moves the cognition/browser runtime off the operator PC to a persistent remote host (currently planned as DigitalOcean) and adds authenticated remote/mobile access. Bob Core, workspace rules, provider adapters and approval semantics should remain the same.
