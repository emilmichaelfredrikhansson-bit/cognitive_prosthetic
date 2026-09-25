from __future__ import annotations

import difflib
import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from .errors import AuthorityError, ProtocolError
from .protocol import BobMessage
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


class EffectCoordinator:
    """Own approval binding, stale-state checks, and authorized effect execution."""

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

    def __init__(self, adapter_for: Callable[[str | None], Any]):
        self._adapter_for = adapter_for
        self.pending: dict[str, PendingEffect] = {}

    def consume(self, pending_id: str) -> PendingEffect:
        pending = self.pending.pop(pending_id, None)
        if pending is None:
            raise ProtocolError("unknown or already-consumed pending approval")
        return pending

    def require_current(self, workspace: Workspace, pending: PendingEffect) -> None:
        current_preview = self.preview(workspace, pending.message)
        actual_hash = self.candidate_hash(workspace, pending.message, current_preview)
        if actual_hash != pending.candidate_hash:
            raise AuthorityError(
                "pending effect or bound workspace state changed after approval request"
            )

    def execute(self, workspace: Workspace, message: BobMessage) -> Any:
        effect_class = self.EFFECT_CLASS.get(message.tool or "")
        if not effect_class:
            raise AuthorityError(f"effect has no declared effect class: {message.tool}")
        if not workspace.effects.get(effect_class, False):
            raise AuthorityError(
                f"workspace {workspace.code} does not allow effect class {effect_class}"
            )
        adapter = self._adapter_for(message.tool)
        return adapter.effect(workspace, message.tool, message.args)

    def stage(
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
        preview = self.preview(workspace, message)
        pending_id = str(uuid.uuid4())
        candidate_hash = self.candidate_hash(workspace, message, preview)
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

    def preview(self, workspace: Workspace, message: BobMessage) -> dict[str, Any] | None:
        tool = message.tool or ""
        if not tool.startswith("github."):
            return None

        adapter = self._adapter_for(tool)
        local_preview = getattr(
            adapter, "can_preview_from_local_git", lambda _workspace: False
        )(workspace)
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
            diff = "".join(
                difflib.unified_diff(
                    [],
                    content.splitlines(keepends=True),
                    fromfile="/dev/null",
                    tofile=path,
                )
            )
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
            new_content = (
                "" if tool == "github.delete_file" else str(args.get("content") or "")
            )
            diff = "".join(
                difflib.unified_diff(
                    current["content"].splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=path,
                    tofile=path if new_content else "/dev/null",
                )
            )
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
    def candidate_hash(
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
