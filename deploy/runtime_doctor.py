#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any

SECRET_KEYS = (
    "GITHUB_TOKEN",
    "SUPABASE_ACCESS_TOKEN",
    "HF_TOKEN",
    "CLOUDFLARE_API_TOKEN",
)


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def loopback(value: str) -> bool:
    value = value.strip()
    if value.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def inspect_runtime(
    app_root: Path,
    env_file: Path,
    state_dir: Path,
    systemd_dir: Path,
    require_credentials: bool = False,
    require_profile: bool = False,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append(check("xvfb-run", shutil.which("xvfb-run") is not None, "headed Chromium display wrapper"))
    checks.append(check("current-release", (app_root / "current").exists(), str(app_root / "current")))
    checks.append(check("venv-python", (app_root / "venv/bin/python").is_file(), str(app_root / "venv/bin/python")))
    checks.append(check("bob-unit", (systemd_dir / "bob-api.service").is_file(), str(systemd_dir / "bob-api.service")))
    checks.append(check("bridge-unit", (systemd_dir / "chatgpt-bridge.service").is_file(), str(systemd_dir / "chatgpt-bridge.service")))

    env_values: dict[str, str] = {}
    if env_file.is_file():
        mode = stat.S_IMODE(env_file.stat().st_mode)
        secure_mode = mode & 0o077 == 0
        checks.append(check("env-file-mode", secure_mode, f"{env_file} mode={mode:04o}"))
        try:
            env_values = parse_env_file(env_file)
            checks.append(check("env-file-parse", True, "parsed without exposing values"))
        except Exception as exc:
            checks.append(check("env-file-parse", False, f"{type(exc).__name__}: {exc}"))
    else:
        checks.append(check("env-file", False, f"missing {env_file}"))

    for key, default in (("BOB_HOST", "127.0.0.1"), ("CHATGPT_BRIDGE_HOST", "127.0.0.1")):
        host = env_values.get(key, default)
        checks.append(check(f"{key.lower()}-loopback", loopback(host), f"{key} must be loopback"))

    if require_credentials:
        for key in SECRET_KEYS:
            checks.append(check(f"credential:{key}", bool(env_values.get(key)), "present" if env_values.get(key) else "missing"))
        checks.append(check("credential:CLOUDFLARE_ACCOUNT_ID", bool(env_values.get("CLOUDFLARE_ACCOUNT_ID")), "present" if env_values.get("CLOUDFLARE_ACCOUNT_ID") else "missing"))

    profile = state_dir / "chatgpt-profile"
    if require_profile:
        populated = profile.is_dir() and any(profile.iterdir())
        checks.append(check("chatgpt-profile", populated, "persistent authenticated profile must be populated"))
    else:
        checks.append(check("chatgpt-profile-path", profile.is_dir(), str(profile)))

    return {"ok": all(item["status"] == "PASS" for item in checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only Bob host readiness doctor.")
    parser.add_argument("--app-root", default=os.environ.get("BOB_APP_ROOT", "/opt/bob"))
    parser.add_argument("--env-file", default=os.environ.get("BOB_ENV_FILE", "/etc/bob/bob.env"))
    parser.add_argument("--state-dir", default=os.environ.get("BOB_STATE_DIR", "/var/lib/bob"))
    parser.add_argument("--systemd-dir", default=os.environ.get("BOB_SYSTEMD_DIR", "/etc/systemd/system"))
    parser.add_argument("--require-credentials", action="store_true")
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = inspect_runtime(
        Path(args.app_root),
        Path(args.env_file),
        Path(args.state_dir),
        Path(args.systemd_dir),
        args.require_credentials,
        args.require_profile,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
