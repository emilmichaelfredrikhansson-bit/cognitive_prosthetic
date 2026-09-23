#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests

from profile_config import load_profile_path

ROOT = Path(__file__).resolve().parent
DEFAULT_ENV_FILE = ROOT / ".env.local"
BOB_HEALTH = "http://127.0.0.1:5002/bob/health"
BRIDGE_HEALTH = "http://127.0.0.1:5001/health"
BRIDGE_SHOW_UI = "http://127.0.0.1:5001/show-ui"


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def is_loopback_host(value: str) -> bool:
    host = str(value or "").strip()
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def assert_local_only(env: dict[str, str]) -> None:
    for key in ("BOB_HOST", "CHATGPT_BRIDGE_HOST"):
        host = env.get(key, "127.0.0.1").strip() or "127.0.0.1"
        if not is_loopback_host(host):
            raise RuntimeError(f"{key} must stay on loopback for Bob V1 Local Companion")

    ui_url = env.get("BOB_COMPANION_UI_URL", "http://127.0.0.1:5002/").strip()
    parts = urlsplit(ui_url)
    if parts.scheme not in {"http", "https"} or not parts.hostname or not is_loopback_host(parts.hostname):
        raise RuntimeError("BOB_COMPANION_UI_URL must be an absolute loopback http(s) URL")


def build_env(env_file: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update(parse_env_file(env_file))
    env.setdefault("BOB_HOST", "127.0.0.1")
    env.setdefault("BOB_PORT", "5002")
    env.setdefault("BOB_WORKSPACE_DIR", str(ROOT / "workspaces"))
    env.setdefault("CHATGPT_BRIDGE_HOST", "127.0.0.1")
    env.setdefault("CHATGPT_BRIDGE_PORT", "5001")
    env.setdefault("CHATGPT_BRIDGE_URL", "http://127.0.0.1:5001")
    env.setdefault("BOB_COMPANION_UI_URL", "http://127.0.0.1:5002/")
    env.setdefault("CHATGPT_TARGET_URL", "https://chatgpt.com/")
    env.setdefault("CHATGPT_CAPTURE_MODE", "copy")
    assert_local_only(env)
    return env


def wait_json(url: str, timeout: float, ready_key: str | None = None) -> dict:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=2)
            payload = response.json()
            if response.ok and (ready_key is None or payload.get(ready_key) is True):
                return payload
        except Exception as exc:
            last_error = exc
        time.sleep(0.35)
    suffix = f": {last_error}" if last_error else ""
    raise RuntimeError(f"Timed out waiting for {url}{suffix}")


def stop_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_login(env: dict[str, str]) -> None:
    result = subprocess.run([sys.executable, str(ROOT / "manual_login.py")], cwd=ROOT, env=env)
    if result.returncode != 0:
        raise RuntimeError("ChatGPT login setup did not complete successfully")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Bob V1 locally with ChatGPT in a background managed browser tab."
    )
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open the one-time ChatGPT login flow before starting Bob.",
    )
    parser.add_argument(
        "--no-open-ui",
        action="store_true",
        help="Start both local services but do not open/focus the Bob browser tab.",
    )
    args = parser.parse_args()

    env_file = Path(args.env_file).expanduser().resolve()
    env = build_env(env_file)

    if args.login:
        run_login(env)

    profile = Path(load_profile_path())
    if not profile.exists():
        print(f"Bob cannot find a ChatGPT browser profile at: {profile}")
        print("Run: python bob_local.py --login")
        return 2

    bob_api: subprocess.Popen | None = None
    bridge: subprocess.Popen | None = None
    try:
        print("Starting Bob V1 Local Companion...")
        bob_api = subprocess.Popen(
            [sys.executable, str(ROOT / "bob_api_server.py")],
            cwd=ROOT,
            env=env,
        )
        wait_json(BOB_HEALTH, 20)

        bridge = subprocess.Popen(
            [sys.executable, str(ROOT / "chatgpt_api_server.py")],
            cwd=ROOT,
            env=env,
        )
        wait_json(BRIDGE_HEALTH, 90, ready_key="ready")

        if not args.no_open_ui:
            response = requests.post(
                BRIDGE_SHOW_UI,
                json={"url": env["BOB_COMPANION_UI_URL"]},
                timeout=20,
            )
            payload = response.json()
            if not response.ok or not payload.get("success"):
                raise RuntimeError(payload.get("error") or "Could not open Bob UI")

        print("")
        print("Bob is ready.")
        print(f"UI: {env['BOB_COMPANION_UI_URL']}")
        print("ChatGPT is running in the background tab of the managed browser.")
        print("Press Ctrl+C here to stop Bob.")
        print("")

        while True:
            if bob_api.poll() is not None:
                raise RuntimeError(f"Bob API exited with code {bob_api.returncode}")
            if bridge.poll() is not None:
                raise RuntimeError(f"ChatGPT bridge exited with code {bridge.returncode}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Bob...")
        return 0
    finally:
        stop_process(bridge)
        stop_process(bob_api)


if __name__ == "__main__":
    raise SystemExit(main())
