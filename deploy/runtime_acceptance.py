#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from runtime_doctor import inspect_runtime, parse_env_file


def record(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def run_checked(command: list[str], cwd: Path, env: dict[str, str]) -> tuple[bool, str]:
    proc = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    detail = (proc.stdout or proc.stderr).strip()
    return proc.returncode == 0, detail


def health(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return 200 <= response.status < 300, body[:500]
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed Bob runtime acceptance runner.")
    parser.add_argument("--app-root", default="/opt/bob")
    parser.add_argument("--env-file", default="/etc/bob/bob.env")
    parser.add_argument("--state-dir", default="/var/lib/bob")
    parser.add_argument("--systemd-dir", default="/etc/systemd/system")
    parser.add_argument("--workspace", action="append", dest="workspaces")
    parser.add_argument("--live", action="store_true", help="Run provider preflight and HTTP health checks.")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    app_root = Path(args.app_root)
    env_file = Path(args.env_file)
    state_dir = Path(args.state_dir)
    systemd_dir = Path(args.systemd_dir)
    local = inspect_runtime(
        app_root,
        env_file,
        state_dir,
        systemd_dir,
        require_credentials=args.live,
        require_profile=args.live,
    )
    checks = [record("local-doctor", local["ok"], "local host readiness")]

    if args.live and local["ok"]:
        runtime_env = os.environ.copy()
        runtime_env.update(parse_env_file(env_file))
        python = app_root / "venv/bin/python"
        current = app_root / "current"
        cmd = [str(python), "-m", "bob.preflight", "--workspace-dir", str(current / "workspaces")]
        for workspace in args.workspaces or ["BOB", "SL", "AB"]:
            cmd.extend(["--workspace", workspace])
        ok, detail = run_checked(cmd, current, runtime_env)
        checks.append(record("provider-preflight", ok, detail))
        if ok:
            for name, url in (
                ("bob-health", "http://127.0.0.1:5002/bob/health"),
                ("bridge-health", "http://127.0.0.1:5001/health"),
            ):
                h_ok, h_detail = health(url)
                checks.append(record(name, h_ok, h_detail))
    elif args.live:
        checks.append(record("provider-preflight", False, "blocked because local doctor failed"))
    else:
        checks.append(record("live-qualification", True, "SKIPPED: rerun with --live on the installed host"))

    result = {"ok": all(item["status"] == "PASS" for item in checks), "checks": checks}
    print(json.dumps(result, indent=2 if args.pretty else None))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
