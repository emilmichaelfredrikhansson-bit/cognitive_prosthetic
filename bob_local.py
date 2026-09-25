#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests

from bob.process_supervision import ProcessSupervisor
from bob.workspaces import WorkspaceRegistry
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
    env.setdefault("BOB_CHATGPT_PROJECT_NAME", "Bob")
    env.setdefault("BOB_CHATGPT_PROJECT_URL", "")
    env.setdefault("CHATGPT_TARGET_URL", "")
    env.setdefault("CHATGPT_CAPTURE_MODE", "copy")
    env.setdefault("CHATGPT_RESPONSE_TIMEOUT_SECONDS", "360")
    env.setdefault("CHATGPT_SUBMISSION_TIMEOUT_SECONDS", "12")
    env.setdefault("CHATGPT_BRIDGE_TIMEOUT_SECONDS", "600")
    env.setdefault("CHATGPT_FRESH_CHAT_MIN_INTERVAL_SECONDS", "10")
    env.setdefault("CHATGPT_TRAFFIC_JITTER_SECONDS", "3")
    env.setdefault("CHATGPT_RATE_LIMIT_BACKOFF_SECONDS", "15,30,60,120")
    env.setdefault("BOB_MAX_PARALLEL_RUNS_PER_REPOSITORY", "3")
    env.setdefault("BOB_CANONICAL_REF", "feat/bob-core-v1")
    env.setdefault("BOB_REPOSITORY_BINDINGS_JSON", "")
    env.setdefault(
        "BOB_PROCESS_SUPERVISOR_PATH",
        str(ROOT / ".bob" / "runtime" / "process_supervisor.json"),
    )
    env.setdefault(
        "BOB_CONTINUATION_STORE_PATH",
        str(ROOT / ".bob" / "runtime" / "blocked_continuations.json"),
    )
    env.setdefault(
        "BOB_PENDING_EFFECT_STORE_PATH",
        str(ROOT / ".bob" / "runtime" / "pending_effects.json"),
    )
    env.setdefault(
        "BOB_SELFDEV_QUEUE_PATH",
        str(ROOT / ".bob" / "runtime" / "self_development.json"),
    )
    assert_local_only(env)
    assert_chatgpt_traffic_budget(env)
    return env


def assert_chatgpt_traffic_budget(env: dict[str, str]) -> None:
    try:
        response = float(env.get("CHATGPT_RESPONSE_TIMEOUT_SECONDS") or "360")
        submission = float(env.get("CHATGPT_SUBMISSION_TIMEOUT_SECONDS") or "12")
        bridge = float(env.get("CHATGPT_BRIDGE_TIMEOUT_SECONDS") or "600")
        interval = float(env.get("CHATGPT_FRESH_CHAT_MIN_INTERVAL_SECONDS") or "10")
        jitter = float(env.get("CHATGPT_TRAFFIC_JITTER_SECONDS") or "3")
        backoff = [
            float(part.strip())
            for part in (env.get("CHATGPT_RATE_LIMIT_BACKOFF_SECONDS") or "15,30,60,120").split(",")
            if part.strip()
        ]
    except ValueError as exc:
        raise RuntimeError("ChatGPT traffic-control timing values must be numeric") from exc
    if not backoff or any(value <= 0 for value in backoff):
        raise RuntimeError("CHATGPT_RATE_LIMIT_BACKOFF_SECONDS must contain positive values")
    if not 1 <= submission <= 60:
        raise RuntimeError("CHATGPT_SUBMISSION_TIMEOUT_SECONDS must be within 1..60")
    required = response + submission + max(backoff) + interval + (2 * jitter) + 30
    if bridge < required:
        raise RuntimeError(
            "CHATGPT_BRIDGE_TIMEOUT_SECONDS is too small for the configured "
            f"response + traffic-control budget; need at least {required:g} seconds"
        )


def assert_runtime_ports_free(env: dict[str, str]) -> None:
    """Fail closed if another local Bob/bridge already owns the loopback ports."""
    for host_key, port_key, label in (
        ("BOB_HOST", "BOB_PORT", "Bob API"),
        ("CHATGPT_BRIDGE_HOST", "CHATGPT_BRIDGE_PORT", "ChatGPT bridge"),
    ):
        host = (env.get(host_key) or "127.0.0.1").strip()
        port = int(env.get(port_key) or ("5002" if port_key == "BOB_PORT" else "5001"))
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        probe = socket.socket(family, socket.SOCK_STREAM)
        try:
            probe.bind((host, port))
        except OSError as exc:
            raise RuntimeError(
                f"{label} loopback port {host}:{port} is already in use; "
                "another Bob Local Companion may already be running"
            ) from exc
        finally:
            probe.close()


def configured_project_url(env: dict[str, str]) -> str:
    return (env.get("BOB_CHATGPT_PROJECT_URL") or env.get("CHATGPT_TARGET_URL") or "").strip()


def assert_project_bound(env: dict[str, str]) -> None:
    value = configured_project_url(env)
    parts = urlsplit(value)
    if not value:
        raise RuntimeError("Set BOB_CHATGPT_PROJECT_URL to the dedicated Bob ChatGPT Project before normal startup")
    if parts.scheme != "https" or (parts.hostname or "").lower() not in {"chatgpt.com", "www.chatgpt.com"}:
        raise RuntimeError("BOB_CHATGPT_PROJECT_URL must be an https://chatgpt.com/ URL")
    if parts.path in {"", "/"}:
        raise RuntimeError("Bob must target a dedicated ChatGPT Project URL, not the ChatGPT home page")


def wait_json(
    process: subprocess.Popen,
    url: str,
    timeout: float,
    ready_key: str | None = None,
) -> dict:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Local Bob process exited with code {process.returncode} while waiting for {url}")
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


def make_process_supervisor(env: dict[str, str]) -> ProcessSupervisor:
    return ProcessSupervisor(
        env.get("BOB_PROCESS_SUPERVISOR_PATH")
        or ROOT / ".bob" / "runtime" / "process_supervisor.json",
        allowed_executables=[sys.executable],
    )


def stop_supervised_runtime(env: dict[str, str]) -> list[str]:
    supervisor = make_process_supervisor(env)
    stopped = supervisor.stop_all_owned(timeout=5)
    supervisor.reap_completed()
    return stopped


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
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Leave supervisor-owned runtime children running after this control command exits.",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop only Bob processes recorded as owned by ProcessSupervisor, then exit.",
    )
    args = parser.parse_args()

    env_file = Path(args.env_file).expanduser().resolve()
    env = build_env(env_file)

    if args.stop:
        if args.login or args.detach:
            raise RuntimeError("--stop cannot be combined with --login or --detach")
        stopped = stop_supervised_runtime(env)
        print(f"Stopped {len(stopped)} supervisor-owned Bob process(es).")
        return 0

    if args.login:
        run_login(env)
        if not configured_project_url(env):
            print("")
            print("ChatGPT login saved.")
            print("Create/open your private ChatGPT project 'Bob', set it to Project-only memory,")
            print("paste its exact URL into BOB_CHATGPT_PROJECT_URL in .env.local, then run start_bob.bat.")
            return 0

    assert_project_bound(env)

    profile_override = env.get("CHATGPT_PROFILE_PATH", "").strip()
    if profile_override:
        profile = Path(profile_override).expanduser()
        if not profile.is_absolute():
            profile = (ROOT / profile).resolve()
    else:
        profile = Path(load_profile_path())
    if not profile.exists():
        print(f"Bob cannot find a ChatGPT browser profile at: {profile}")
        print("Run: python bob_local.py --login")
        return 2

    assert_runtime_ports_free(env)

    workspace_registry = WorkspaceRegistry(env["BOB_WORKSPACE_DIR"])
    bob_workspace = workspace_registry.get("BOB")
    supervisor = make_process_supervisor(env)
    bob_api_id: str | None = None
    bridge_id: str | None = None
    leave_running = False
    try:
        print("Starting Bob V1 Local Companion...")
        api_record = supervisor.start(
            purpose="BOB_API",
            command_class="LONG_LIVED_RUNTIME",
            command=[sys.executable, str(ROOT / "bob_api_server.py")],
            cwd=ROOT,
            repository_id=bob_workspace.github_repository_id,
            owns_ports=[int(env["BOB_PORT"])],
            env=env,
        )
        bob_api_id = api_record["process_id"]
        bob_api = supervisor.process_handle(bob_api_id)
        if bob_api is None:
            raise RuntimeError("ProcessSupervisor lost Bob API child handle during startup")
        wait_json(bob_api, BOB_HEALTH, 20)
        supervisor.bind_owned_ports(bob_api_id)

        bridge_record = supervisor.start(
            purpose="CHATGPT_BRIDGE",
            command_class="LONG_LIVED_RUNTIME",
            command=[sys.executable, str(ROOT / "chatgpt_api_server.py")],
            cwd=ROOT,
            repository_id=bob_workspace.github_repository_id,
            owns_ports=[int(env["CHATGPT_BRIDGE_PORT"])],
            env=env,
        )
        bridge_id = bridge_record["process_id"]
        bridge = supervisor.process_handle(bridge_id)
        if bridge is None:
            raise RuntimeError("ProcessSupervisor lost ChatGPT bridge child handle during startup")
        wait_json(bridge, BRIDGE_HEALTH, 90, ready_key="ready")
        supervisor.bind_owned_ports(bridge_id)

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
        if args.detach:
            leave_running = True
            print("Runtime children are supervisor-owned; this control command may exit.")
            return 0
        print("Press Ctrl+C here to stop Bob.")
        print("")

        while True:
            supervisor.refresh()
            api_state = supervisor.get(bob_api_id)
            bridge_state = supervisor.get(bridge_id)
            if api_state["state"] != "RUNNING":
                raise RuntimeError(f"Bob API stopped unexpectedly: {api_state['state']}")
            if bridge_state["state"] != "RUNNING":
                raise RuntimeError(
                    f"ChatGPT bridge stopped unexpectedly: {bridge_state['state']}"
                )
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Bob...")
        return 0
    finally:
        if not leave_running:
            for process_id in (bridge_id, bob_api_id):
                if process_id is None:
                    continue
                try:
                    supervisor.stop(process_id)
                except ProtocolError:
                    pass
            supervisor.reap_completed()


if __name__ == "__main__":
    raise SystemExit(main())
