# Bob systemd runtime units

These units are deployment templates for the persistent Bob runtime. They deliberately keep both credential-bearing Python services on loopback.

Expected layout:

```text
/opt/bob/current             repository checkout
/opt/bob/venv                Python virtual environment
/etc/bob/bob.env             runtime secrets/config, mode 0600, owned by bob
/var/lib/bob/chatgpt-profile persistent Chromium profile, owned by bob
```

Install the units under `/etc/systemd/system/`, create a dedicated unprivileged `bob` user/group, install pinned Python dependencies into `/opt/bob/venv`, and copy only real runtime secrets into `/etc/bob/bob.env`.

The committed units enforce:
- `BOB_HOST=127.0.0.1`;
- `CHATGPT_BRIDGE_HOST=127.0.0.1`;
- Bob-to-bridge traffic over `http://127.0.0.1:5001`;
- dedicated `bob` runtime identity;
- restrictive `UMask=0077`;
- `NoNewPrivileges=true`, private temporary storage, and read-only system/home surfaces;
- browser profile writes limited to `/var/lib/bob`.

Do not expose either service by changing its bind address. Remote/mobile access belongs behind a separately authenticated proxy/tunnel boundary.

Before treating a runtime as qualified:

```bash
python -m bob.preflight --pretty
systemctl status chatgpt-bridge.service bob-api.service
curl --fail http://127.0.0.1:5001/health
curl --fail http://127.0.0.1:5002/bob/health
```

A healthy service process is not equivalent to provider identity qualification or an approved external effect.
