# Bob Remote Access V1

Bob's Python services remain loopback-only. Remote/mobile access is provided by an authenticated edge transport, not by rebinding Flask.

## Preferred architecture

Use a Cloudflare Tunnel published application mapping the future Bob hostname to:

```text
http://127.0.0.1:5002
```

Current Cloudflare guidance recommends remotely managed tunnels for most deployments. Configure the tunnel and published application in Cloudflare, then put a Cloudflare Access self-hosted application in front of the same hostname.

Before the tunnel is allowed to carry operator traffic:
- create an Access application and explicit allow policy for the operator identity;
- enable Access protection/token validation for the tunnel/origin path;
- confirm the origin remains reachable only on loopback;
- do not create inbound firewall exposure for port 5002;
- do not use a Quick Tunnel for production.

The ChatGPT bridge on port 5001 is never published. Only Bob API/UI on port 5002 is eligible for the authenticated tunnel.

## Locally managed fallback

`deploy/cloudflare/config.yml.example` is a fallback template only. Cloudflare currently recommends remotely managed tunnels for most use cases.

A locally managed configuration must end with a catch-all rule and should be validated before service start:

```bash
cloudflared tunnel ingress validate
cloudflared tunnel ingress rule https://bob.example.com/
```

Do not start the tunnel merely because the config validates. Access policy must already exist.

## Authentication boundary

Cloudflare Access is part of Bob's security boundary for remote use.

Tunnel connectivity by itself is not authentication. The deployment is not qualified until an unauthenticated request is rejected and an authenticated operator request reaches Bob.

Where available, configure cloudflared/Access to validate the Access token at the origin boundary as defense in depth.

## Mobile/PC acceptance

After local live acceptance is green:
1. verify unauthenticated access is denied from an unrelated browser/session;
2. verify authenticated desktop access to the Bob UI;
3. verify authenticated mobile access to the same Bob UI;
4. verify `/bob/health` reports the expected workspace set;
5. perform no write effect during remote-access qualification.

Only after those checks should remote access be considered normal.

## Optional home-network egress

Home-network egress for the ChatGPT browser remains an optional transport layer. It is not required for Bob Core semantics and must not broaden provider traffic or Bob authority.

The concrete tunnel/router implementation is intentionally deferred until the actual router/network capabilities are available. Qualification must prove that only the intended browser traffic takes that route and that tunnel failure stops cognition transport rather than rerouting silently through an unintended path.
