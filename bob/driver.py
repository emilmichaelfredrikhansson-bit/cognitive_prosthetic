from __future__ import annotations

import difflib
import hashlib
import json
import os
import threading
import uuid
from dataclasses import dataclass
from typing import Any

import requests

from .errors import AuthorityError, BobError, ConfigurationError, ProtocolError
from .integrations import CloudflareAdapter, GitHubAdapter, HuggingFaceAdapter, SupabaseAdapter
from .protocol import BobMessage, make_result, make_workspace_packet, parse_model_response
from .workspaces import Workspace, WorkspaceRegistry


@dataclass
class PendingEffect:
    pending_id: str
    workspace_code: str
    message: BobMessage
    candidate_hash: str
    effect_class: str


class ChatGPTBridge:
    def __init__(self, base_url: str | None = None, timeout: int = 220):
        self.base_url = (base_url or os.environ.get("CHATGPT_BRIDGE_URL") or "http://127.0.0.1:5001").rstrip("/")
        self.timeout = timeout
        self._lock = threading.Lock()

    def send(self, prompt: str) -> str:
        with self._lock:
            response = requests.post(
                self.base_url + "/chat",
                json={"prompt": prompt},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("success"):
                raise BobError(payload.get("error") or "ChatGPT bridge failed")
            text = payload.get("response")
            if not isinstance(text, str):
                raise BobError("ChatGPT bridge returned no response text")
            return text

    def new_chat(self) -> None:
        with self._lock:
            response = requests.post(self.base_url + "/new-chat", json={}, timeout=30)
            response.raise_for_status()


class BobRuntime:
    MAX_TOOL_ROUNDS = 12

    EFFECT_CLASS = {
        "github.create_branch": "write_branch",
        "github.create_file": "write_branch",
        "github.replace_file": "write_branch",
        "github.delete_file": "write_branch",
        "github.open_pr": "open_pr",
        "supabase.query": "mutate_production_state",
        "hf.run_job": "material_spend",
        "hf.cancel_job": "material_spend",
        "cloudflare.worker_deploy_version": "deploy",
        "cloudflare.pages_retry": "deploy",
        "cloudflare.pages_rollback": "deploy",
    }

    def __init__(self, workspace_dir: str = "workspaces", bridge: ChatGPTBridge | None = None):
        self.registry = WorkspaceRegistry(workspace_dir)
        self.bridge = bridge or ChatGPTBridge()
        self.adapters: dict[str, Any] = {}
        self.pending: dict[str, PendingEffect] = {}
        self.initialized_workspace: str | None = None
        self._configure_adapters()

    def _configure_adapters(self) -> None:
        if os.environ.get("GITHUB_TOKEN"):
            self.adapters["github"] = GitHubAdapter(os.environ["GITHUB_TOKEN"])
        if os.environ.get("SUPABASE_ACCESS_TOKEN"):
            self.adapters["supabase"] = SupabaseAdapter(os.environ["SUPABASE_ACCESS_TOKEN"])
        if os.environ.get("HF_TOKEN"):
            self.adapters["hf"] = HuggingFaceAdapter(os.environ["HF_TOKEN"])
        if os.environ.get("CLOUDFLARE_API_TOKEN"):
            self.adapters["cloudflare"] = CloudflareAdapter(os.environ["CLOUDFLARE_API_TOKEN"])

    def capabilities(self) -> dict[str, list[str]]:
        return {name: adapter.capabilities() for name, adapter in self.adapters.items()}

    def workspace_capabilities(self, workspace: Workspace) -> dict[str, list[str]]:
        provider_keys = {
            "supabase": "supabase",
            "hf": "hugging_face",
            "cloudflare": "cloudflare",
        }
        result: dict[str, list[str]] = {}
        for name, adapter in self.adapters.items():
            if name == "github" or provider_keys.get(name) in workspace.providers:
                result[name] = adapter.capabilities()
        return result

    def workspace_packet(self, workspace: Workspace) -> str:
        return make_workspace_packet(workspace.public_dict(), self.workspace_capabilities(workspace))

    def start_chat(self, workspace_code: str) -> dict[str, Any]:
        workspace = self.registry.get(workspace_code)
        self.bridge.new_chat()
        self.initialized_workspace = None
        return {"workspace": workspace.public_dict(), "status": "NEW_CHAT"}

    def turn(self, workspace_code: str, human_message: str) -> dict[str, Any]:
        workspace = self.registry.get(workspace_code)
        if not human_message.strip():
            raise ProtocolError("human message must not be empty")

        if self.initialized_workspace != workspace.code:
            prompt = (
                self.workspace_packet(workspace)
                + "\n\nThe human says:\n"
                + human_message.strip()
            )
            self.initialized_workspace = workspace.code
        else:
            prompt = human_message.strip()

        return self._drive(workspace, prompt)

    def approve(self, pending_id: str) -> dict[str, Any]:
        pending = self.pending.pop(pending_id, None)
        if pending is None:
            raise ProtocolError("unknown or already-consumed pending approval")
        workspace = self.registry.get(pending.workspace_code)
        actual_hash = self._candidate_hash(workspace, pending.message)
        if actual_hash != pending.candidate_hash:
            raise AuthorityError("pending effect changed after approval request")

        try:
            data = self._execute_effect(workspace, pending.message)
            feedback = make_result(
                pending.message.id,
                pending.message.tool or "",
                "PASS",
                data=data,
            )
        except Exception as exc:
            feedback = make_result(
                pending.message.id,
                pending.message.tool or "",
                "FAIL",
                error=str(exc),
            )
        return self._drive(workspace, feedback)

    def direct_read(self, workspace_code: str, tool: str, args: dict[str, Any]) -> Any:
        workspace = self.registry.get(workspace_code)
        msg = BobMessage("BOB.READ", "direct", tool, args, {})
        return self._execute_read(workspace, msg)

    def _drive(self, workspace: Workspace, prompt: str) -> dict[str, Any]:
        visible: list[str] = []
        tool_rounds: list[dict[str, Any]] = []
        next_prompt = prompt

        for _ in range(self.MAX_TOOL_ROUNDS):
            model_text = self.bridge.send(next_prompt)
            parsed = parse_model_response(model_text)
            if parsed.visible_text:
                visible.append(parsed.visible_text)

            if not parsed.messages:
                return {
                    "status": "COMPLETE",
                    "visible_messages": visible,
                    "tool_rounds": tool_rounds,
                    "pending": [],
                }

            kinds = {m.type for m in parsed.messages}
            if "BOB.READ" in kinds and "BOB.EFFECT" in kinds:
                raise ProtocolError("model must not mix BOB.READ and BOB.EFFECT in one turn")

            reads = [m for m in parsed.messages if m.type == "BOB.READ"]
            effects = [m for m in parsed.messages if m.type == "BOB.EFFECT"]
            terminal = [m for m in parsed.messages if m.type in {"BOB.DONE", "BOB.ASK"}]

            if effects:
                pending_items = [self._stage_effect(workspace, message) for message in effects]
                return {
                    "status": "AWAITING_APPROVAL",
                    "visible_messages": visible,
                    "tool_rounds": tool_rounds,
                    "pending": pending_items,
                }

            if reads:
                results: list[str] = []
                round_record = {"reads": []}
                for message in reads:
                    try:
                        data = self._execute_read(workspace, message)
                        result = make_result(message.id, message.tool or "", "PASS", data=data)
                        round_record["reads"].append({"id": message.id, "tool": message.tool, "status": "PASS"})
                    except Exception as exc:
                        result = make_result(message.id, message.tool or "", "FAIL", error=str(exc))
                        round_record["reads"].append({"id": message.id, "tool": message.tool, "status": "FAIL", "error": str(exc)})
                    results.append(result)
                tool_rounds.append(round_record)
                next_prompt = "\n\n".join(results)
                continue

            if terminal:
                terminal_msg = terminal[-1]
                return {
                    "status": "DONE" if terminal_msg.type == "BOB.DONE" else "ASK_USER",
                    "visible_messages": visible,
                    "tool_rounds": tool_rounds,
                    "terminal": terminal_msg.raw,
                    "pending": [],
                }

            raise ProtocolError("BOB response contained no actionable message")

        raise ProtocolError(f"tool loop exceeded {self.MAX_TOOL_ROUNDS} rounds")

    def _execute_read(self, workspace: Workspace, message: BobMessage) -> Any:
        adapter = self._adapter_for(message.tool)
        return adapter.read(workspace, message.tool, message.args)

    def _execute_effect(self, workspace: Workspace, message: BobMessage) -> Any:
        effect_class = self.EFFECT_CLASS.get(message.tool or "")
        if not effect_class:
            raise AuthorityError(f"effect has no declared effect class: {message.tool}")
        if not workspace.effects.get(effect_class, False):
            raise AuthorityError(
                f"workspace {workspace.code} does not allow effect class {effect_class}"
            )
        adapter = self._adapter_for(message.tool)
        return adapter.effect(workspace, message.tool, message.args)

    def _stage_effect(self, workspace: Workspace, message: BobMessage) -> dict[str, Any]:
        effect_class = self.EFFECT_CLASS.get(message.tool or "")
        if not effect_class:
            raise AuthorityError(f"effect has no declared effect class: {message.tool}")
        if not workspace.effects.get(effect_class, False):
            raise AuthorityError(
                f"workspace {workspace.code} does not allow effect class {effect_class}"
            )
        pending_id = str(uuid.uuid4())
        candidate_hash = self._candidate_hash(workspace, message)
        self.pending[pending_id] = PendingEffect(
            pending_id=pending_id,
            workspace_code=workspace.code,
            message=message,
            candidate_hash=candidate_hash,
            effect_class=effect_class,
        )
        return {
            "pending_id": pending_id,
            "request_id": message.id,
            "tool": message.tool,
            "effect_class": effect_class,
            "args": message.args,
            "candidate_hash": candidate_hash,
            "preview": self._preview_effect(workspace, message),
        }

    def _preview_effect(self, workspace: Workspace, message: BobMessage) -> dict[str, Any] | None:
        tool = message.tool or ""
        if not tool.startswith("github."):
            return None
        adapter = self._adapter_for(tool)
        args = message.args
        if tool == "github.create_file":
            path = str(args.get("path") or "")
            content = str(args.get("content") or "")
            diff = "".join(difflib.unified_diff(
                [],
                content.splitlines(keepends=True),
                fromfile="/dev/null",
                tofile=path,
            ))
            return {"kind": "diff", "diff": diff}
        if tool in {"github.replace_file", "github.delete_file"}:
            path = str(args.get("path") or "")
            branch = str(args.get("branch") or workspace.default_branch)
            current = adapter.read_file(workspace, path, branch)
            expected_sha = args.get("expected_sha")
            if expected_sha and current["sha"] != expected_sha:
                raise AuthorityError(
                    f"stale file before approval: expected {expected_sha}, got {current['sha']}"
                )
            new_content = "" if tool == "github.delete_file" else str(args.get("content") or "")
            diff = "".join(difflib.unified_diff(
                current["content"].splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=path,
                tofile=path if new_content else "/dev/null",
            ))
            return {"kind": "diff", "diff": diff, "current_sha": current["sha"]}
        return {"kind": "summary", "tool": tool, "args": args}

    def _adapter_for(self, tool: str | None) -> Any:
        if not tool or "." not in tool:
            raise ProtocolError(f"invalid tool name: {tool}")
        prefix = tool.split(".", 1)[0]
        adapter = self.adapters.get(prefix)
        if adapter is None:
            raise ConfigurationError(
                f"adapter '{prefix}' unavailable; required credential may be missing"
            )
        return adapter

    @staticmethod
    def _candidate_hash(workspace: Workspace, message: BobMessage) -> str:
        canonical = json.dumps(
            {
                "workspace": workspace.code,
                "repository_id": workspace.github_repository_id,
                "type": message.type,
                "id": message.id,
                "tool": message.tool,
                "args": message.args,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
