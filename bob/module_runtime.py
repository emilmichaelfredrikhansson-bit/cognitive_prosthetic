from __future__ import annotations

import json
from typing import Any

from .errors import AuthorityError, ConfigurationError, ProtocolError
from .module_graph import ModuleGraph, measure_module
from .protocol import BobMessage, make_result, parse_model_response
from .workspaces import Workspace


class ModuleRuntimeMixin:
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

    def resume_continuation(self, continuation_id: str) -> dict[str, Any]:
            """Resume cognition after an already-executed effect without replaying it."""
            state = self.blocked_continuations.get(continuation_id)
            if state is None:
                raise ProtocolError("unknown or already-consumed blocked continuation")
            return self._drive_or_block_module_continuation(continuation_id, state)

    def _drive_or_block_module_continuation(
            self,
            continuation_id: str,
            state: dict[str, Any],
        ) -> dict[str, Any]:
            workspace = self.registry.get(str(state["workspace_code"]))
            try:
                result = self._drive_module(
                    workspace,
                    str(state["module_id"]),
                    str(state["problem"]),
                    str(state["ref"]),
                    continuation=tuple(str(x) for x in state.get("results") or ()),
                )
            except Exception as exc:
                state["last_error"] = str(exc)
                self.blocked_continuations[continuation_id] = state
                return {
                    "status": "CONTINUATION_BLOCKED",
                    "mode": "STATELESS_MODULE",
                    "module": str(state["module_id"]),
                    "continuation_id": continuation_id,
                    "effect": state.get("effect"),
                    "error": str(exc),
                    "pending": [],
                }
            self.blocked_continuations.pop(continuation_id, None)
            return result

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
