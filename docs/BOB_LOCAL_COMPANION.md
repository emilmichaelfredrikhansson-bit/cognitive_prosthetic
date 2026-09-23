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

The ChatGPT tab uses a dedicated persistent Bob browser profile. It is not fake history and it does not copy browser cookies into the repository. The operator signs in once through the explicit local login flow.

Both credential-bearing Python services are loopback-only. V1 has no public Bob endpoint, tunnel, Cloudflare Access dependency or DigitalOcean runtime.

## Windows first run

From a fresh checkout of `feat/bob-core-v1`:

1. Run `setup_bob.bat`.
2. Copy/edit `.env.local` as needed. Never commit it.
3. Put only the provider credentials Bob actually needs into `.env.local`.
4. Set `CHATGPT_TARGET_URL` to the Bob-enabled ChatGPT Project URL when available.
5. Run `first_run_bob.bat`.
6. Sign in to ChatGPT in the browser that opens, then press Enter in the terminal.
7. Bob starts both local services, verifies their health, opens Bob in the same browser, and brings the Bob tab to the front.

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
