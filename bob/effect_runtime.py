from __future__ import annotations

import difflib
import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any

from .errors import AuthorityError, ConfigurationError, ProtocolError
from .protocol import BobMessage, make_result
from .workspaces import Workspace


@dataclass
class PendingEffect:
    pending_id: str
    workspace_code: str
    message: BobMessage
    candidate_hash: str
    effect_class: str
    preview: dict[str, Any] | None
    continuation: dict[str, Any] | None = None

    def durable_dict(self) -> dict[str, Any]:
        return {
            "pending_id": self.pending_id,
            "workspace_code": self.workspace_code,
            "message": {
                "type": self.message.type,
                "id": self.message.id,
                "tool": self.message.tool,
                "args": self.message.args,
            },
            "candidate_hash": self.candidate_hash,
            "effect_class": self.effect_class,
            "preview": self.preview,
            "continuation": self.continuation,
        }

    @classmethod
    def from_durable(cls, data: dict[str, Any]) -> "PendingEffect":
        if not isinstance(data, dict):
            raise ConfigurationError("durable pending effect must be an object")
        raw = data.get("message")
        if not isinstance(raw, dict) or raw.get("type") != "BOB.EFFECT":
            raise ConfigurationError("durable pending effect requires a BOB.EFFECT message")
        msg_id, tool, args = raw.get("id"), raw.get("tool"), raw.get("args") or {}
        if not isinstance(msg_id, str) or not msg_id or not isinstance(tool, str) or not tool:
            raise ConfigurationError("durable pending effect message identity is invalid")
        if not isinstance(args, dict):
            raise ConfigurationError("durable pending effect args must be an object")
        pending_id = data.get("pending_id")
        workspace_code = data.get("workspace_code")
        candidate_hash = data.get("candidate_hash")
        effect_class = data.get("effect_class")
        if not all(isinstance(value, str) and value for value in (
            pending_id, workspace_code, candidate_hash, effect_class
        )):
            raise ConfigurationError("durable pending effect metadata is invalid")
        preview = data.get("preview")
        continuation = data.get("continuation")
        if preview is not None and not isinstance(preview, dict):
            raise ConfigurationError("durable pending effect preview must be an object or null")
        if continuation is not None and not isinstance(continuation, dict):
            raise ConfigurationError("durable pending effect continuation must be an object or null")
        return cls(
            pending_id=pending_id,
            workspace_code=workspace_code,
            message=BobMessage("BOB.EFFECT", msg_id, tool, args, raw),
            candidate_hash=candidate_hash,
            effect_class=effect_class,
            preview=preview,
            continuation=continuation,
        )


class EffectRuntimeMixin:
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

    def approval_status(self) -> dict[str, Any]:
            items = []
            for pending_id, pending in sorted(self.pending.items()):
                items.append({
                    "pending_id": pending_id,
                    "request_id": pending.message.id,
                    "tool": pending.message.tool,
                    "effect_class": pending.effect_class,
                    "args": pending.message.args,
                    "candidate_hash": pending.candidate_hash,
                    "preview": pending.preview,
                })
            return {"count": len(items), "pending": items}

    def _consume_pending(self, pending_id: str) -> PendingEffect:
            pending = self.pending.get(pending_id)
            if pending is None:
                raise ProtocolError("unknown or already-consumed pending approval")
            self.pending_effect_store.remove(pending_id)
            return self.pending.pop(pending_id)

    def approve(self, pending_id: str) -> dict[str, Any]:
            pending = self._consume_pending(pending_id)
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
                continuation_id = str(uuid.uuid4())
                state = {
                    "workspace_code": workspace.code,
                    "module_id": str(continuation["module_id"]),
                    "problem": str(continuation["problem"]),
                    "ref": str(continuation["ref"]),
                    "results": list(prior + (feedback,)),
                    "effect": {
                        "request_id": pending.message.id,
                        "tool": pending.message.tool,
                        "result": feedback,
                    },
                }
                return self._drive_or_block_module_continuation(
                    continuation_id,
                    state,
                )
            return self._drive(workspace, feedback)

    def reject(self, pending_id: str) -> dict[str, Any]:
            """Discard one staged effect without executing it."""
            pending = self._consume_pending(pending_id)
            return {
                "status": "REJECTED",
                "request_id": pending.message.id,
                "tool": pending.message.tool,
                "pending": [],
            }

    def relay_approve(self, pending_id: str) -> dict[str, Any]:
            """Execute one staged effect and return feedback without invoking ChatGPT."""
            pending = self._consume_pending(pending_id)
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
            pending = PendingEffect(
                pending_id=pending_id,
                workspace_code=workspace.code,
                message=message,
                candidate_hash=candidate_hash,
                effect_class=effect_class,
                preview=preview,
                continuation=continuation,
            )
            self.pending_effect_store.put(pending_id, pending.durable_dict())
            self.pending[pending_id] = pending
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
            local_preview = getattr(adapter, "can_preview_from_local_git", lambda _workspace: False)(
                workspace
            )
            if not local_preview:
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
