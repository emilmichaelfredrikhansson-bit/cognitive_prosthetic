from __future__ import annotations

import argparse
import ipaddress
import json
import os
from collections.abc import Mapping, Sequence
from typing import Any


def is_loopback_host(host: str) -> bool:
    value = host.strip()
    if value.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def binding_checks(env: Mapping[str, str] | None = None) -> dict[str, dict[str, Any]]:
    values = env if env is not None else os.environ
    hosts = {
        "bob_api": values.get("BOB_HOST", "127.0.0.1"),
        "chatgpt_bridge": values.get("CHATGPT_BRIDGE_HOST", "127.0.0.1"),
    }
    return {
        name: {
            "status": "PASS" if is_loopback_host(host) else "FAIL",
            "host": host,
            "requirement": "loopback-only credential-bearing service",
        }
        for name, host in hosts.items()
    }


def run_preflight(
    runtime: Any,
    workspace_codes: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    bindings = binding_checks(env)
    codes = list(workspace_codes) if workspace_codes else [w.code for w in runtime.registry.list()]
    workspaces: dict[str, dict[str, Any]] = {}

    for code in codes:
        try:
            qualification = runtime.qualify_workspace(code)
            workspaces[code] = {
                "status": "PASS" if qualification.get("qualified") else "FAIL",
                "qualification": qualification,
            }
        except Exception as exc:
            workspaces[code] = {
                "status": "FAIL",
                "error": str(exc),
                "type": type(exc).__name__,
            }

    bindings_ok = all(item["status"] == "PASS" for item in bindings.values())
    workspaces_ok = bool(workspaces) and all(
        item["status"] == "PASS" for item in workspaces.values()
    )
    return {
        "ok": bindings_ok and workspaces_ok,
        "bindings": bindings,
        "workspaces": workspaces,
        "available_adapters": sorted(runtime.capabilities()),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Bob runtime preflight and workspace qualification."
    )
    parser.add_argument(
        "--workspace",
        action="append",
        dest="workspaces",
        help="Workspace code to qualify. Repeat for multiple workspaces; default is all.",
    )
    parser.add_argument(
        "--workspace-dir",
        default=os.environ.get("BOB_WORKSPACE_DIR", "workspaces"),
        help="Workspace registry directory.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)

    from .driver import BobRuntime

    runtime = BobRuntime(workspace_dir=args.workspace_dir)
    result = run_preflight(runtime, workspace_codes=args.workspaces)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
