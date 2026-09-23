# Bob Remote Runtime Operations V2

This runbook is the deterministic operating sequence for the optional **V2 persistent remote host**. It is not required for Bob V1 Local Companion; local V1 setup is documented in `docs/BOB_LOCAL_COMPANION.md`.

## Install an exact release

Work from a clean checkout at the exact commit intended for deployment.

```bash
git rev-parse HEAD
sudo BOB_RELEASE_SHA="$(git rev-parse HEAD)" deploy/install_runtime.sh
python deploy/runtime_doctor.py --pretty
```

The installer refuses a requested SHA that does not match the checkout. It installs the release under `/opt/bob/releases/<sha>`, points `/opt/bob/current` at it, installs pinned Python/Playwright dependencies, installs and enables the two systemd units, and creates an empty `/etc/bob/bob.env` if needed.

It deliberately does not start or restart Bob services.

## Credentials

Install real values as root in `/etc/bob/bob.env` according to `docs/BOB_RUNTIME_CREDENTIALS.md`.

The file must remain root-owned and mode 0600. Never print it in logs.

## Initial ChatGPT browser profile

The persistent Chromium context is headed and runs under Xvfb during normal service operation. Initial authentication still requires a temporary operator-only interactive display.

Run `manual_login.py` as the `bob` runtime identity with `CHATGPT_PROFILE_PATH=/var/lib/bob/chatgpt-profile` through a separately authenticated display path such as SSH X forwarding or a loopback-only remote-desktop helper carried through SSH.

Never expose VNC/noVNC or the browser bridge directly to the Internet. Remove/stop the temporary display helper after the profile is created.

Then run:

```bash
python deploy/runtime_doctor.py --require-credentials --require-profile --pretty
```

## Read-only provider qualification

Before starting remote access or attempting a write:

```bash
sudo /opt/bob/venv/bin/python /opt/bob/current/deploy/runtime_acceptance.py --live --pretty
```

The live acceptance runner:
1. checks local host prerequisites, credential presence and profile presence;
2. loads the root-owned env file without printing secret values;
3. runs Bob preflight for BOB, SL and AB;
4. only after provider preflight passes, checks loopback Bob API and bridge health.

For the first live run, start the services locally immediately before acceptance:

```bash
sudo systemctl start chatgpt-bridge.service
sudo systemctl start bob-api.service
```

A healthy process is not provider qualification.

## Bob GitHub write canary

Only after read-only qualification passes:
1. rotate the GitHub credential to the bounded Stage B permissions;
2. use Bob's own approval boundary to create a dedicated Bob canary branch;
3. create/replace a harmless canary file;
4. open a PR;
5. require Bob read-back receipts for every effect;
6. delete/close cleanup state only through a separately approved effect or manual operator action.

No SL/AB production mutation, HF spend or Cloudflare deployment is implied by this canary.

## Upgrade

1. check out the exact new commit;
2. run the full verification appropriate to the change;
3. run `install_runtime.sh` with that exact SHA;
4. run the offline doctor;
5. install/retain credentials without copying them into the release;
6. run live acceptance;
7. only then restart services onto the new `/opt/bob/current` release.

The release directories are immutable snapshots. Do not edit code in place under `/opt/bob/current`.

## Rollback

Rollback only to an already-installed immutable release:

```bash
sudo deploy/rollback_release.sh <40-character-sha>
```

By default rollback moves the `current` symlink and does not restart services. After local checks, explicitly request restart:

```bash
sudo BOB_RESTART_AFTER_ROLLBACK=1 deploy/rollback_release.sh <40-character-sha>
```

Then rerun live acceptance.

## Failure drills

Before calling the host qualified, prove fail-closed behavior for:
- missing provider credential;
- wrong Cloudflare account/anchor;
- expired ChatGPT session;
- bridge stopped;
- Bob API stopped;
- non-loopback host override;
- staged GitHub branch/file drift before approval;
- tunnel unavailable.

No partial transport success may become an external effect PASS.
