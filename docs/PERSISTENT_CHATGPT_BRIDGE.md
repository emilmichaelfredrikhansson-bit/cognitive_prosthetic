# Persistent ChatGPT Browser Bridge

## Purpose

Bob needs one persistent authenticated ChatGPT browser session so the same development cockpit can be used from both PC and mobile.

The target runtime is a small DigitalOcean host with a deliberately narrow responsibility:

> keep the ChatGPT browser/session available and expose the Bob CognitionAdapter.

It is **not** the general-purpose Bob execution engine.

## Target topology

```text
PC / mobile
    ↓
Cloudflare Bob UI/API
    ↓
authenticated cognition request
    ↓
DigitalOcean
persistent browser/session
    ↓
secure encrypted tunnel
    ↓
home network/router
    ↓
selected home-IP egress
    ↓
ChatGPT
```

GitHub, Hugging Face, Supabase and Cloudflare integrations are separate from this path.

## Responsibilities

DigitalOcean bridge:
- maintain a persistent browser profile/session;
- send the operator-selected prompt to ChatGPT;
- capture the response through the configured UI/accessibility transport;
- return model output and transport provenance;
- report browser/session/tunnel health.

The browser-control HTTP service is loopback-only by default and exposes no permissive CORS surface. A later remote bridge must add an authenticated Bob-to-bridge transport before network exposure; changing the bind address alone is not authentication.

It must not automatically gain:
- arbitrary target-repository write authority;
- merge/deploy authority;
- Supabase production mutation authority;
- HF spending authority;
- generic shell/build authority exposed to the frontend.

## Home-network egress

The bridge may route ChatGPT traffic through a secure tunnel terminating on the home network/router so the browser uses the selected home public IP.

The tunnel is transport only. It does not grant or expand Bob authority.

Implementation details should be selected during qualification based on:
- router capabilities;
- tunnel reliability;
- least-privilege networking;
- recoverability;
- observability;
- avoidance of accidental routing of unrelated provider traffic.

## Device model

With the persistent bridge:

```text
PC client     ┐
              ├→ same Cloudflare Bob UI → same cognition bridge
Mobile client ┘
```

The operator's PC does not need to remain online for normal use.

A local PC bridge remains useful for development, diagnosis and fallback.

## Failure model

Fail closed.

If:
- browser session expires;
- UI capture fails;
- tunnel is unavailable;
- cognition response is incomplete or ambiguous;

then no candidate change set may advance into a GitHub write merely because the transport partially succeeded.

Repository effects are downstream of a complete validated cognition result and explicit Bob approval.

## Runtime preflight

Once least-privilege runtime credentials are installed as environment variables, run:

```bash
python -m bob.preflight --pretty
```

The command is read-only. It exits successfully only when:
- both credential-bearing Python services are configured on loopback hosts; and
- every selected workspace independently passes the existing Bob workspace qualification path.

By default it checks every registered workspace. Use repeated `--workspace` flags for a bounded canary, for example:

```bash
python -m bob.preflight --workspace BOB --workspace SL --pretty
```

The report contains binding, capability and qualification metadata only. It must never print credential values. A preflight PASS proves configured provider identity/readability for that runtime; it does **not** prove the live ChatGPT browser/clipboard transport, the home-egress tunnel, or any write/deploy effect.

## Qualification sequence

1. prove cognition adapter with local browser;
2. provision DigitalOcean canary runtime;
3. prove persistent login/session;
4. prove accessibility/copy capture;
5. add authenticated Bob-to-bridge transport;
6. establish home-network tunnel;
7. verify selected egress;
8. exercise restart/session-expiry/tunnel-failure paths;
9. verify from PC;
10. verify from mobile;
11. only then treat remote cognition as the normal path.

## Non-goal

Do not turn the DigitalOcean host into a second HF, Supabase, GitHub Actions runner, or general-purpose permanent Bob Core without a separately demonstrated need.
