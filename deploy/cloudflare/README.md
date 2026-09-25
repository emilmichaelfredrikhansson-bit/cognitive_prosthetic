# Cloudflare Tunnel fallback template

Prefer a remotely managed Cloudflare Tunnel plus a Cloudflare Access self-hosted application.

This directory contains a locally managed fallback template for cases where local configuration is deliberately chosen later.

Never commit a real tunnel credential JSON file or tunnel token.

Before starting cloudflared:
1. replace the placeholder UUID and hostname outside Git;
2. create the Cloudflare Access application/policy first;
3. enable Access protection/token validation for the route;
4. validate the ingress configuration;
5. confirm Bob still binds only to 127.0.0.1:5002.

The final catch-all 404 rule is intentional.
