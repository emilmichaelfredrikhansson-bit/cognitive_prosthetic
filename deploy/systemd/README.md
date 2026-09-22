# Bob systemd runtime units

These units are deployment templates for the persistent Bob runtime. They deliberately keep both credential-bearing Python services on loopback.

Expected layout:

```text
/opt/bob/current             repository checkout
/opt/bob/venv                Python virtual environment
/etc/bob/bob.env             runtime secrets/config, mode 0600, owned by bob
/var/lib/bob/chatgpt-profile persistent Chromium profile, owned by bob
```

Install the units under `/etc/systemd/system/`, create a dedicated unprivileged `bob` user/group, install pinned Python dependencies into `/opt/bob/venv`, install `xvfb` + `xauth`, install the Playwright Chromium runtime, and copy only real runtime secrets into `/etc/bob/bob.env`.

The committed units enforce:
- `BOB_HOST=127.0.0.1`;
- `CHATGPT_BRIDGE_HOST=127.0.0.1`;
- Bob-to-bridge traffic over `http://127.0.0.1:5001`;
- dedicated `bob` runtime identity;
- restrictive `UMask=0077`;
- `NoNewPrivileges=true`, private temporary storage, and read-only system/home surfaces;
- browser profile writes limited to `/var/lib/bob`;\n- headed Chromium launched inside an ephemeral Xvfb display via `xvfb-run -a`.

Do not expose either service by changing its bind address. Remote/mobile access belongs behind a separately authenticated proxy/tunnel boundary.

Before treating a runtime as qualified:

```bash
python -m bob.preflight --pretty
systemctl status chatgpt-bridge.service bob-api.service
curl --fail http://127.0.0.1:5001/health
curl --fail http://127.0.0.1:5002/bob/health
```

A healthy service process is not equivalent to provider identity qualification or an approved external effect.


## Initial ChatGPT login

The bridge uses a headed persistent Chromium context. `xvfb-run` provides a display for unattended runtime, but it does not provide a human login surface.

Create the initial `/var/lib/bob/chatgpt-profile` only through a separately authenticated temporary interactive display path (for example SSH/X forwarding or a tightly scoped temporary remote-desktop tunnel). Do not expose VNC/noVNC or the bridge directly to the public internet. Once the authenticated profile exists, disable the temporary login surface before treating the runtime as persistent.
