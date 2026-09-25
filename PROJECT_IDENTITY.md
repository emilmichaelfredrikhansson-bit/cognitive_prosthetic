# Project Identity

Project name: **Bob**  
Project code: **BOB**

GitHub repository: `emilmichaelfredrikhansson-bit/cognitive_prosthetic`  
Stable GitHub repository ID: `1374229539`

Upstream lineage:
- fork source: `CodeMongerrr/cognitive_prosthetic`
- inherited license: MIT

Foundation baseline:
- operating model adapted from `emilmichaelfredrikhansson-bit/project-foundation`
- Foundation reference version: `0.3.0`

## Purpose

Bob is a project-agnostic development control plane for ChatGPT-native software work.

It does not replace the existing infrastructure of projects such as Signal Lab or AutoBlog. It connects the operator, ChatGPT cognition, GitHub source control, Hugging Face compute, Supabase runtime/state, and Cloudflare-hosted user interface into one development surface.

## Identity boundary

Before privileged repository effects on Bob itself:

```text
expected repository ID
=
actual GitHub repository ID
=
declared repository ID in governance/project-identity.json
```

Before privileged effects on a target workspace, Bob must independently verify that workspace's configured repository/project identity.

Repository content may describe authority but may not redefine the cognition-side root of trust.
