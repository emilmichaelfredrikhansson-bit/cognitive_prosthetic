from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import requests

from .context_compiler import ContextCompiler
from .continuation_store import ContinuationStore
from .errors import BobError, ConfigurationError, ProtocolError
from .effect_runtime import EffectRuntimeMixin, PendingEffect
from .module_runtime import ModuleRuntimeMixin
from .pending_effect_store import PendingEffectStore
from .selfdev_queue import SelfDevelopmentQueue
from .integrations import CloudflareAdapter, GitHubAdapter, HuggingFaceAdapter, SupabaseAdapter
from .protocol import BobMessage, make_result, make_workspace_packet, parse_model_response
from .workspaces import Workspace, WorkspaceRegistry


class ChatGPTBridge:
    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or os.environ.get("CHATGPT_BRIDGE_URL") or "http://127.0.0.1:5001").rstrip("/")
        self.timeout = timeout or int(os.environ.get("CHATGPT_BRIDGE_TIMEOUT_SECONDS", "600"))
        self._lock = threading.Lock()

    @staticmethod
    def _payload_or_raise(response: requests.Response, fallback: str) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            response.raise_for_status()
            raise BobError(fallback)
        if not response.ok or not payload.get("success"):
            raise BobError(str(payload.get("error") or fallback))
        return payload

    def send(self, prompt: str) -> str:
        with self._lock:
            response = requests.post(
                self.base_url + "/chat",
                json={"prompt": prompt},
                timeout=self.timeout,
            )
            payload = self._payload_or_raise(response, "ChatGPT bridge failed")
            text = payload.get("response")
            if not isinstance(text, str):
                raise BobError("ChatGPT bridge returned no response text")
            return text

    def cognition(
        self,
        prompt: str,
        *,
        request_id: str | None = None,
        run_id: str | None = None,
        cognition_id: str | None = None,
    ) -> str:
        """Run one fresh, optionally execution-correlated cognition request."""
        body = {"prompt": prompt}
        for key, value in (
            ("request_id", request_id),
            ("run_id", run_id),
            ("cognition_id", cognition_id),
        ):
            if value not in (None, ""):
                body[key] = str(value)
        with self._lock:
            response = requests.post(
                self.base_url + "/cognition",
                json=body,
                timeout=self.timeout,
            )
            payload = self._payload_or_raise(response, "fresh cognition request failed")
            if request_id not in (None, "") and payload.get("request_id") != str(request_id):
                raise BobError("fresh cognition response request_id mismatch")
            text = payload.get("response")
            if not isinstance(text, str):
                raise BobError("fresh cognition request returned no response text")
            return text

    def new_chat(self) -> None:
        with self._lock:
            response = requests.post(self.base_url + "/new-chat", json={}, timeout=self.timeout)
            response.raise_for_status()


class BobRuntime(ModuleRuntimeMixin, EffectRuntimeMixin):
    MAX_TOOL_ROUNDS = 12


    def __init__(self, workspace_dir: str = "workspaces", bridge: ChatGPTBridge | None = None):
        self.registry = WorkspaceRegistry(workspace_dir)
        self.bridge = bridge or ChatGPTBridge()
        self.adapters: dict[str, Any] = {}
        workspace_path = Path(workspace_dir).expanduser().resolve()
        runtime_root = workspace_path.parent if workspace_path.name.lower() == "workspaces" else workspace_path
        pending_path = os.environ.get("BOB_PENDING_EFFECT_STORE_PATH") or str(
            runtime_root / ".bob" / "runtime" / "pending_effects.json"
        )
        self.pending_effect_store = PendingEffectStore(pending_path)
        self.pending: dict[str, PendingEffect] = {}
        for pending_id, durable in self.pending_effect_store.snapshot().items():
            pending = PendingEffect.from_durable(durable)
            if pending.pending_id != pending_id:
                raise ConfigurationError("pending effect store key/id mismatch")
            self.pending[pending_id] = pending
        continuation_path = os.environ.get("BOB_CONTINUATION_STORE_PATH") or str(
            runtime_root / ".bob" / "runtime" / "blocked_continuations.json"
        )
        self.continuation_store = ContinuationStore(continuation_path)
        self.blocked_continuations: dict[str, dict[str, Any]] = self.continuation_store.snapshot()
        self.selfdev_queue: SelfDevelopmentQueue | None = None
        try:
            bob_workspace = self.registry.get("BOB")
        except ConfigurationError:
            # BobRuntime is project-agnostic and is used with non-BOB registries in
            # tests/target workspaces. Self-development state exists only in the
            # Bob control-plane workspace and must not become a global dependency.
            pass
        else:
            selfdev_path = os.environ.get("BOB_SELFDEV_QUEUE_PATH") or str(
                runtime_root / ".bob" / "runtime" / "self_development.json"
            )
            self.selfdev_queue = SelfDevelopmentQueue(
                selfdev_path,
                repository_full_name=bob_workspace.github_repository,
                repository_id=bob_workspace.github_repository_id,
                canonical_ref=os.environ.get("BOB_CANONICAL_REF", "feat/bob-core-v1"),
            )
        self.initialized_workspace: str | None = None
        self.context_compiler = ContextCompiler()
        self._configure_adapters()

    def _configure_adapters(self) -> None:
        # Public GitHub reads are useful even without a token. The adapter itself
        # withholds write capabilities and rejects effects unless authenticated.
        self.adapters["github"] = GitHubAdapter(os.environ.get("GITHUB_TOKEN"))
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

    def qualify_workspace(self, workspace_code: str) -> dict[str, Any]:
        """Verify the selected workspace against all configured external identities.

        Qualification is read-only. Every configured provider must have a runtime
        adapter and must independently verify its bound identity. Missing credentials
        are reported as UNAVAILABLE rather than being treated as an implicit PASS.
        """
        workspace = self.registry.get(workspace_code)
        checks: dict[str, dict[str, Any]] = {}

        bindings = [("github", "github")]
        for adapter_name, provider_key in (
            ("supabase", "supabase"),
            ("hf", "hugging_face"),
            ("cloudflare", "cloudflare"),
        ):
            if provider_key in workspace.providers:
                bindings.append((adapter_name, provider_key))

        for adapter_name, _provider_key in bindings:
            adapter = self.adapters.get(adapter_name)
            if adapter is None:
                checks[adapter_name] = {
                    "status": "UNAVAILABLE",
                    "error": f"adapter '{adapter_name}' unavailable; required credential may be missing",
                }
                continue
            try:
                data = adapter.verify_workspace(workspace)
                checks[adapter_name] = {"status": "PASS", "data": data}
            except Exception as exc:
                checks[adapter_name] = {
                    "status": "FAIL",
                    "error": str(exc),
                    "type": type(exc).__name__,
                }

        qualified = bool(checks) and all(
            check.get("status") == "PASS" for check in checks.values()
        )
        return {
            "workspace": workspace.public_dict(),
            "qualified": qualified,
            "checks": checks,
        }

    def _require_selfdev_queue(self) -> SelfDevelopmentQueue:
        if self.selfdev_queue is None:
            raise ConfigurationError(
                "Bob self-development state requires a configured BOB workspace"
            )
        return self.selfdev_queue

    def self_development_status(self) -> dict[str, Any]:
        """Return durable Bob self-development backlog state without executing work."""
        return self._require_selfdev_queue().snapshot()

    def enqueue_self_development(
        self,
        *,
        goal: str,
        leases: list[str],
        expected_outcome: str | None = None,
    ) -> dict[str, Any]:
        """Persist one bounded self-development intent; execution remains separate."""
        return self._require_selfdev_queue().enqueue(
            goal=goal,
            leases=leases,
            expected_outcome=expected_outcome,
        )

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







    def direct_read(self, workspace_code: str, tool: str, args: dict[str, Any]) -> Any:
        workspace = self.registry.get(workspace_code)
        msg = BobMessage("BOB.READ", "direct", tool, args, {})
        return self._execute_read(workspace, msg)

    def search_project_context(
        self,
        workspace_code: str,
        query: str,
        limit: int | str = 20,
    ) -> dict[str, Any]:
        """Search only the workspace's configured entry documents via real Bob READs."""
        workspace = self.registry.get(workspace_code)
        needle = str(query or "").strip()
        if len(needle) < 2:
            raise ProtocolError("project search query must contain at least 2 characters")
        if len(needle) > 120:
            raise ProtocolError("project search query must be at most 120 characters")
        try:
            bounded_limit = int(limit)
        except (TypeError, ValueError) as exc:
            raise ProtocolError("project search limit must be an integer") from exc
        bounded_limit = max(1, min(bounded_limit, 50))

        results: list[dict[str, Any]] = []
        reads: list[dict[str, Any]] = []
        total_matches = 0
        folded_needle = needle.casefold()

        for index, path in enumerate(workspace.entry_documents, start=1):
            message = BobMessage(
                "BOB.READ",
                f"project-search-{index}",
                "github.read_file",
                {"path": path},
                {},
            )
            try:
                data = self._execute_read(workspace, message)
                content = data.get("content") if isinstance(data, dict) else None
                if not isinstance(content, str):
                    raise ProtocolError(f"github.read_file returned no text content for {path}")
                reads.append({
                    "path": path,
                    "tool": "github.read_file",
                    "status": "PASS",
                })
            except Exception as exc:
                reads.append({
                    "path": path,
                    "tool": "github.read_file",
                    "status": "FAIL",
                    "error": str(exc),
                })
                continue

            lines = content.splitlines()
            for line_number, line in enumerate(lines, start=1):
                if folded_needle not in line.casefold():
                    continue
                total_matches += 1
                if len(results) >= bounded_limit:
                    continue
                start = max(0, line_number - 2)
                end = min(len(lines), line_number + 1)
                snippet = "\n".join(lines[start:end]).strip()
                results.append({
                    "path": path,
                    "line": line_number,
                    "snippet": snippet[:700],
                })

        return {
            "workspace": workspace.code,
            "query": needle,
            "scope": "entry_documents",
            "documents": list(workspace.entry_documents),
            "reads": reads,
            "results": results,
            "total_matches": total_matches,
            "truncated": total_matches > len(results),
        }

    def relay_start(self, workspace_code: str, human_message: str) -> dict[str, Any]:
        """Build the exact first prompt for a manual/external cognition loop."""
        workspace = self.registry.get(workspace_code)
        if not human_message.strip():
            raise ProtocolError("human message must not be empty")
        prompt = (
            self.workspace_packet(workspace)
            + "\n\nThe human says:\n"
            + human_message.strip()
        )
        return {
            "workspace": workspace.public_dict(),
            "prompt": prompt,
            "status": "PROMPT_READY",
        }

    def relay_model_response(self, workspace_code: str, model_text: str) -> dict[str, Any]:
        """Process one model response without calling the browser bridge.

        This is the development/manual-relay seam: any external LLM (including
        an interactive ChatGPT conversation) can play the cognition role while
        Bob still owns all deterministic reads/effects and approval boundaries.
        """
        workspace = self.registry.get(workspace_code)
        parsed = parse_model_response(model_text)
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
                "visible_text": parsed.visible_text,
                "feedback": None,
                "pending": pending_items,
            }

        if reads:
            results: list[str] = []
            receipts: list[dict[str, Any]] = []
            for message in reads:
                try:
                    data = self._execute_read(workspace, message)
                    results.append(make_result(message.id, message.tool or "", "PASS", data=data))
                    receipts.append({"id": message.id, "tool": message.tool, "status": "PASS"})
                except Exception as exc:
                    results.append(make_result(message.id, message.tool or "", "FAIL", error=str(exc)))
                    receipts.append({
                        "id": message.id,
                        "tool": message.tool,
                        "status": "FAIL",
                        "error": str(exc),
                    })
            return {
                "status": "RESULT_READY",
                "visible_text": parsed.visible_text,
                "feedback": "\n\n".join(results),
                "receipts": receipts,
                "pending": [],
            }

        if terminal:
            message = terminal[-1]
            return {
                "status": "DONE" if message.type == "BOB.DONE" else "ASK_USER",
                "visible_text": parsed.visible_text,
                "feedback": None,
                "terminal": message.raw,
                "pending": [],
            }

        return {
            "status": "NO_TOOL_REQUEST",
            "visible_text": parsed.visible_text,
            "feedback": None,
            "pending": [],
        }





        # Architecture repair intentionally has broader path scope because a valid
        # split may need to create new files and rewrite the graph. Workspace
        # authority + normal approval/read-back boundaries still apply.

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
