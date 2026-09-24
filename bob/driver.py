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

from .context_compiler import ContextCompiler
from .errors import AuthorityError, BobError, ConfigurationError, ProtocolError
from .integrations import CloudflareAdapter, GitHubAdapter, HuggingFaceAdapter, SupabaseAdapter
from .module_graph import ModuleGraph, measure_module
from .protocol import BobMessage, make_result, make_workspace_packet, parse_model_response
from .workspaces import Workspace, WorkspaceRegistry


@dataclass
class PendingEffect:
    pending_id: str
    workspace_code: str
    message: BobMessage
    candidate_hash: str
    effect_class: str
    preview: dict[str, Any] | None
    continuation: dict[str, Any] | None = None


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

    def cognition(self, prompt: str) -> str:
        """Run one cognition request in a fresh ChatGPT conversation.

        This is the canonical primitive for the future stateless Context Compiler
        path. Existing closed-loop V1 work still uses send() until durable
        compiled-context continuation is implemented.
        """
        with self._lock:
            response = requests.post(
                self.base_url + "/cognition",
                json={"prompt": prompt},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("success"):
                raise BobError(payload.get("error") or "fresh cognition request failed")
            text = payload.get("response")
            if not isinstance(text, str):
                raise BobError("fresh cognition request returned no response text")
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

    def module_turn(
        self,
        workspace_code: str,
        module_id: str,
        human_message: str,
        ref: str | None = None,
    ) -> dict[str, Any]:
        """Run one bounded module problem through fresh cognition only."""
        workspace = self.registry.get(workspace_code)
        problem = human_message.strip()
        if not problem:
            raise ProtocolError("human message must not be empty")
        resolved_ref = str(ref or workspace.default_branch).strip()
        if not resolved_ref:
            raise ProtocolError("module ref must not be empty")
        return self._drive_module(
            workspace,
            module_id.strip(),
            problem,
            resolved_ref,
            continuation=(),
        )

    def module_graph_status(
        self,
        workspace_code: str,
        ref: str | None = None,
    ) -> dict[str, Any]:
        """Read the durable graph and deterministically measure every declared module."""
        workspace = self.registry.get(workspace_code)
        resolved_ref = str(ref or workspace.default_branch).strip()
        graph = self._load_module_graph(workspace, resolved_ref)
        github = self._adapter_for("github.read_file")
        modules = []
        for module in graph.modules:
            footprint = measure_module(workspace, module, github, resolved_ref)
            modules.append({
                **module.summary_dict(),
                "footprint": footprint.public_dict(),
                "compliant": (
                    footprint.token_count
                    <= self.context_compiler.policy.module_hard_cap_tokens
                ),
            })
        return {
            "workspace": workspace.code,
            "repository": workspace.github_repository,
            "repository_id": workspace.github_repository_id,
            "ref": resolved_ref,
            "graph_path": workspace.module_graph_path,
            "coverage": graph.coverage,
            "module_hard_cap_tokens": self.context_compiler.policy.module_hard_cap_tokens,
            "modules": modules,
        }

    def approve(self, pending_id: str) -> dict[str, Any]:
        pending = self.pending.pop(pending_id, None)
        if pending is None:
            raise ProtocolError("unknown or already-consumed pending approval")
        workspace = self.registry.get(pending.workspace_code)
        current_preview = self._preview_effect(workspace, pending.message)
        actual_hash = self._candidate_hash(workspace, pending.message, current_preview)
        if actual_hash != pending.candidate_hash:
            raise AuthorityError("pending effect or bound workspace state changed after approval request")

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

        continuation = pending.continuation or {}
        if continuation.get("kind") == "module":
            prior = tuple(str(x) for x in continuation.get("results") or ())
            return self._drive_module(
                workspace,
                str(continuation["module_id"]),
                str(continuation["problem"]),
                str(continuation["ref"]),
                continuation=prior + (feedback,),
            )
        return self._drive(workspace, feedback)

    def reject(self, pending_id: str) -> dict[str, Any]:
        """Discard one staged effect without executing it."""
        pending = self.pending.pop(pending_id, None)
        if pending is None:
            raise ProtocolError("unknown or already-consumed pending approval")
        return {
            "status": "REJECTED",
            "request_id": pending.message.id,
            "tool": pending.message.tool,
            "pending": [],
        }

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

    def relay_approve(self, pending_id: str) -> dict[str, Any]:
        """Execute one staged effect and return feedback without invoking ChatGPT."""
        pending = self.pending.pop(pending_id, None)
        if pending is None:
            raise ProtocolError("unknown or already-consumed pending approval")
        workspace = self.registry.get(pending.workspace_code)
        current_preview = self._preview_effect(workspace, pending.message)
        actual_hash = self._candidate_hash(workspace, pending.message, current_preview)
        if actual_hash != pending.candidate_hash:
            raise AuthorityError("pending effect or bound workspace state changed after approval request")

        try:
            data = self._execute_effect(workspace, pending.message)
            feedback = make_result(
                pending.message.id,
                pending.message.tool or "",
                "PASS",
                data=data,
            )
            status = "PASS"
        except Exception as exc:
            feedback = make_result(
                pending.message.id,
                pending.message.tool or "",
                "FAIL",
                error=str(exc),
            )
            status = "FAIL"

        return {
            "status": status,
            "feedback": feedback,
            "request_id": pending.message.id,
            "tool": pending.message.tool,
            "pending": [],
        }

    def _load_module_graph(self, workspace: Workspace, ref: str) -> ModuleGraph:
        github = self._adapter_for("github.read_file")
        raw = github.read_file(workspace, workspace.module_graph_path, ref)
        content = raw.get("content") if isinstance(raw, dict) else None
        if not isinstance(content, str):
            raise ConfigurationError(
                f"module graph has no text content: {workspace.module_graph_path}"
            )
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"invalid module graph JSON at {workspace.module_graph_path}: {exc}"
            ) from exc
        graph = ModuleGraph.from_dict(data)
        graph.require_workspace(workspace)
        return graph

    def _drive_module(
        self,
        workspace: Workspace,
        module_id: str,
        problem: str,
        ref: str,
        *,
        continuation: tuple[str, ...],
    ) -> dict[str, Any]:
        """Stateless module loop: every tool continuation recompiles into a fresh chat."""
        visible: list[str] = []
        tool_rounds: list[dict[str, Any]] = []
        durable_results = tuple(continuation)

        for _ in range(self.MAX_TOOL_ROUNDS):
            graph = self._load_module_graph(workspace, ref)
            module = graph.get(module_id)
            github = self._adapter_for("github.read_file")
            footprint = measure_module(workspace, module, github, ref)
            repair = (
                footprint.token_count
                > self.context_compiler.policy.module_hard_cap_tokens
            )
            compiled = self.context_compiler.compile_module_problem(
                workspace=workspace,
                graph=graph,
                module=module,
                footprint=footprint,
                problem=problem,
                ref=ref,
                continuation=durable_results,
                architecture_repair=repair,
            )

            model_text = self.bridge.cognition(compiled.prompt)
            parsed = parse_model_response(model_text)
            if parsed.visible_text:
                visible.append(parsed.visible_text)

            if not parsed.messages:
                if repair:
                    raise ProtocolError(
                        "oversized module requires an actionable architecture repair"
                    )
                return {
                    "status": "COMPLETE",
                    "mode": "STATELESS_MODULE",
                    "module": module.module_id,
                    "footprint": footprint.public_dict(),
                    "compiled_context": compiled.public_dict(),
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
                if len(effects) != 1:
                    raise ProtocolError(
                        "stateless module cognition must stage one effect per fresh request"
                    )
                self._validate_module_effect(
                    workspace,
                    graph,
                    module,
                    effects[0],
                    ref,
                    architecture_repair=repair,
                )
                state = {
                    "kind": "module",
                    "module_id": module.module_id,
                    "problem": problem,
                    "ref": ref,
                    "results": list(durable_results),
                }
                pending_item = self._stage_effect(
                    workspace,
                    effects[0],
                    continuation=state,
                )
                return {
                    "status": "AWAITING_APPROVAL",
                    "mode": "STATELESS_MODULE",
                    "module": module.module_id,
                    "footprint": footprint.public_dict(),
                    "compiled_context": compiled.public_dict(),
                    "visible_messages": visible,
                    "tool_rounds": tool_rounds,
                    "pending": [pending_item],
                }

            if reads:
                results: list[str] = []
                round_record = {"reads": [], "fresh_cognition": True}
                for message in reads:
                    try:
                        data = self._execute_read(workspace, message)
                        result = make_result(message.id, message.tool or "", "PASS", data=data)
                        round_record["reads"].append({
                            "id": message.id,
                            "tool": message.tool,
                            "status": "PASS",
                        })
                    except Exception as exc:
                        result = make_result(
                            message.id, message.tool or "", "FAIL", error=str(exc)
                        )
                        round_record["reads"].append({
                            "id": message.id,
                            "tool": message.tool,
                            "status": "FAIL",
                            "error": str(exc),
                        })
                    results.append(result)
                tool_rounds.append(round_record)
                durable_results = durable_results + tuple(results)
                continue

            if terminal:
                terminal_msg = terminal[-1]
                if repair and terminal_msg.type == "BOB.DONE":
                    raise ProtocolError(
                        "oversized module cannot be marked done before cap compliance"
                    )
                return {
                    "status": "DONE" if terminal_msg.type == "BOB.DONE" else "ASK_USER",
                    "mode": "STATELESS_MODULE",
                    "module": module.module_id,
                    "footprint": footprint.public_dict(),
                    "compiled_context": compiled.public_dict(),
                    "visible_messages": visible,
                    "tool_rounds": tool_rounds,
                    "terminal": terminal_msg.raw,
                    "pending": [],
                }

            raise ProtocolError("BOB response contained no actionable message")

        raise ProtocolError(
            f"stateless module loop exceeded {self.MAX_TOOL_ROUNDS} rounds"
        )

    def _validate_module_effect(
        self,
        workspace: Workspace,
        graph: ModuleGraph,
        module: Any,
        message: BobMessage,
        ref: str,
        *,
        architecture_repair: bool,
    ) -> None:
        """Keep normal module writes inside manifest ownership and one working ref."""
        tool = message.tool or ""
        if tool == "github.create_branch":
            raise ProtocolError(
                "stateless module work requires an existing working ref; "
                "create the branch first, then rerun module_turn with that ref"
            )

        if tool in {
            "github.create_file",
            "github.replace_file",
            "github.delete_file",
        }:
            branch = str(message.args.get("branch") or "")
            if branch != ref:
                raise AuthorityError(
                    f"module effect branch must equal working ref: {branch!r} != {ref!r}"
                )
            path = str(message.args.get("path") or "")
            if not architecture_repair and path not in module.owned_paths:
                raise AuthorityError(
                    f"module {module.module_id} does not own effect path: {path}"
                )

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

    def _stage_effect(
        self,
        workspace: Workspace,
        message: BobMessage,
        continuation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        effect_class = self.EFFECT_CLASS.get(message.tool or "")
        if not effect_class:
            raise AuthorityError(f"effect has no declared effect class: {message.tool}")
        if not workspace.effects.get(effect_class, False):
            raise AuthorityError(
                f"workspace {workspace.code} does not allow effect class {effect_class}"
            )
        preview = self._preview_effect(workspace, message)
        pending_id = str(uuid.uuid4())
        candidate_hash = self._candidate_hash(workspace, message, preview)
        self.pending[pending_id] = PendingEffect(
            pending_id=pending_id,
            workspace_code=workspace.code,
            message=message,
            candidate_hash=candidate_hash,
            effect_class=effect_class,
            preview=preview,
            continuation=continuation,
        )
        return {
            "pending_id": pending_id,
            "request_id": message.id,
            "tool": message.tool,
            "effect_class": effect_class,
            "args": message.args,
            "candidate_hash": candidate_hash,
            "preview": preview,
        }

    def _preview_effect(self, workspace: Workspace, message: BobMessage) -> dict[str, Any] | None:
        tool = message.tool or ""
        if not tool.startswith("github."):
            return None
        adapter = self._adapter_for(tool)
        adapter.verify_workspace(workspace)
        args = message.args

        if tool == "github.create_branch":
            base = str(args.get("base") or workspace.default_branch)
            base_sha = adapter.branch_head(workspace, base)
            expected = args.get("expected_base_sha")
            if expected and str(expected) != base_sha:
                raise AuthorityError(
                    f"stale base before approval: expected {expected}, got {base_sha}"
                )
            return {
                "kind": "summary",
                "tool": tool,
                "args": args,
                "base": base,
                "base_sha": base_sha,
            }

        if tool == "github.create_file":
            path = str(args.get("path") or "")
            branch = str(args.get("branch") or "")
            if not path or not branch:
                raise ProtocolError("github.create_file preview requires path and branch")
            branch_sha = adapter.branch_head(workspace, branch)
            content = str(args.get("content") or "")
            diff = "".join(difflib.unified_diff(
                [],
                content.splitlines(keepends=True),
                fromfile="/dev/null",
                tofile=path,
            ))
            return {
                "kind": "diff",
                "diff": diff,
                "branch": branch,
                "branch_sha": branch_sha,
            }

        if tool in {"github.replace_file", "github.delete_file"}:
            path = str(args.get("path") or "")
            branch = str(args.get("branch") or "")
            if not path or not branch:
                raise ProtocolError(f"{tool} preview requires path and branch")
            branch_sha = adapter.branch_head(workspace, branch)
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
            return {
                "kind": "diff",
                "diff": diff,
                "current_sha": current["sha"],
                "branch": branch,
                "branch_sha": branch_sha,
            }

        if tool == "github.open_pr":
            head = str(args.get("head") or "")
            base = str(args.get("base") or workspace.default_branch)
            if not head:
                raise ProtocolError("github.open_pr preview requires head")
            if ":" in head:
                raise ProtocolError(
                    "cross-repository PR heads are not supported by Bob V1 approval binding"
                )
            return {
                "kind": "summary",
                "tool": tool,
                "args": args,
                "head": head,
                "head_sha": adapter.branch_head(workspace, head),
                "base": base,
                "base_sha": adapter.branch_head(workspace, base),
            }

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
    def _candidate_hash(
        workspace: Workspace,
        message: BobMessage,
        preview: dict[str, Any] | None,
    ) -> str:
        authority_binding = {
            "code": workspace.code,
            "github": {
                "repository": workspace.github_repository,
                "repository_id": workspace.github_repository_id,
                "default_branch": workspace.default_branch,
            },
            "providers": workspace.providers,
            "effects": workspace.effects,
        }
        canonical = json.dumps(
            {
                "workspace": authority_binding,
                "type": message.type,
                "id": message.id,
                "tool": message.tool,
                "args": message.args,
                "staged_state": preview,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
