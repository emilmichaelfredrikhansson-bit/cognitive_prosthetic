from __future__ import annotations

import base64
from typing import Any

from bob.errors import ExternalEffectError, IdentityMismatch, ProtocolError
from bob.workspaces import Workspace
from .http import JsonHttp


class GitHubAdapter:
    def __init__(self, token: str):
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.http = JsonHttp("https://api.github.com", headers=headers)

    def capabilities(self) -> list[str]:
        return [
            "github.repo",
            "github.read_file",
            "github.read_files",
            "github.list_contents",
            "github.create_branch",
            "github.create_file",
            "github.replace_file",
            "github.delete_file",
            "github.open_pr",
        ]

    def verify_workspace(self, workspace: Workspace) -> dict[str, Any]:
        repo = self.http.request("GET", f"/repos/{workspace.github_repository}")
        actual_id = int(repo["id"])
        if actual_id != workspace.github_repository_id:
            raise IdentityMismatch(
                f"GitHub repository ID mismatch: expected {workspace.github_repository_id}, got {actual_id}"
            )
        return {
            "repository": repo["full_name"],
            "repository_id": actual_id,
            "default_branch": repo["default_branch"],
            "private": bool(repo.get("private")),
        }

    def branch_head(self, workspace: Workspace, branch: str) -> str:
        self.verify_workspace(workspace)
        ref = self.http.request(
            "GET",
            f"/repos/{workspace.github_repository}/git/ref/heads/{branch}",
        )
        obj = ref.get("object") if isinstance(ref, dict) else None
        sha = obj.get("sha") if isinstance(obj, dict) else None
        if not sha:
            raise ProtocolError(f"GitHub branch ref contained no commit SHA: {branch}")
        return str(sha)

    def read(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        self.verify_workspace(workspace)
        if tool == "github.repo":
            return self.verify_workspace(workspace)
        if tool == "github.read_file":
            return self.read_file(workspace, args["path"], args.get("ref"))
        if tool == "github.read_files":
            paths = args.get("paths")
            if not isinstance(paths, list) or not paths:
                raise ProtocolError("github.read_files requires non-empty paths")
            return [self.read_file(workspace, str(path), args.get("ref")) for path in paths]
        if tool == "github.list_contents":
            path = str(args.get("path") or "")
            params = {"ref": args["ref"]} if args.get("ref") else None
            return self.http.request(
                "GET",
                f"/repos/{workspace.github_repository}/contents/{path}",
                params=params,
            )
        raise ProtocolError(f"unsupported GitHub read tool: {tool}")

    def effect(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        self.verify_workspace(workspace)
        if tool == "github.create_branch":
            base = str(args.get("base") or workspace.default_branch)
            branch = self._required(args, "branch")
            ref = self.http.request(
                "GET",
                f"/repos/{workspace.github_repository}/git/ref/heads/{base}",
            )
            base_sha = ref["object"]["sha"]
            expected = args.get("expected_base_sha")
            if expected and expected != base_sha:
                raise IdentityMismatch(f"stale base: expected {expected}, got {base_sha}")
            created = self.http.request(
                "POST",
                f"/repos/{workspace.github_repository}/git/refs",
                json_body={"ref": f"refs/heads/{branch}", "sha": base_sha},
            )
            actual = self.http.request(
                "GET",
                f"/repos/{workspace.github_repository}/git/ref/heads/{branch}",
            )
            if actual["object"]["sha"] != base_sha:
                raise IdentityMismatch(
                    f"GitHub branch read-back mismatch: expected {base_sha}, got {actual['object']['sha']}"
                )
            return {
                "branch": branch,
                "base_sha": base_sha,
                "ref": created.get("ref"),
                "read_back_verified": True,
            }

        if tool == "github.create_file":
            path = self._required(args, "path")
            content = self._required(args, "content")
            branch = self._required(args, "branch")
            payload = {
                "message": str(args.get("message") or f"Bob: create {path}"),
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "branch": branch,
            }
            result = self.http.request(
                "PUT",
                f"/repos/{workspace.github_repository}/contents/{path}",
                json_body=payload,
            )
            receipt = self._write_receipt(result, path, branch)
            actual = self.read_file(workspace, path, branch)
            if actual["content"] != content or actual["sha"] != receipt["content_sha"]:
                raise IdentityMismatch(f"GitHub read-back mismatch after create: {path}")
            receipt["read_back_verified"] = True
            return receipt

        if tool == "github.replace_file":
            path = self._required(args, "path")
            content = self._required(args, "content")
            branch = self._required(args, "branch")
            expected_sha = self._required(args, "expected_sha")
            current = self.read_file(workspace, path, branch)
            if current["sha"] != expected_sha:
                raise IdentityMismatch(f"stale file {path}: expected {expected_sha}, got {current['sha']}")
            payload = {
                "message": str(args.get("message") or f"Bob: update {path}"),
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "sha": expected_sha,
                "branch": branch,
            }
            result = self.http.request(
                "PUT",
                f"/repos/{workspace.github_repository}/contents/{path}",
                json_body=payload,
            )
            receipt = self._write_receipt(result, path, branch)
            actual = self.read_file(workspace, path, branch)
            if actual["content"] != content or actual["sha"] != receipt["content_sha"]:
                raise IdentityMismatch(f"GitHub read-back mismatch after replace: {path}")
            receipt["read_back_verified"] = True
            return receipt

        if tool == "github.delete_file":
            path = self._required(args, "path")
            branch = self._required(args, "branch")
            expected_sha = self._required(args, "expected_sha")
            current = self.read_file(workspace, path, branch)
            if current["sha"] != expected_sha:
                raise IdentityMismatch(f"stale file {path}: expected {expected_sha}, got {current['sha']}")
            result = self.http.request(
                "DELETE",
                f"/repos/{workspace.github_repository}/contents/{path}",
                json_body={
                    "message": str(args.get("message") or f"Bob: delete {path}"),
                    "sha": expected_sha,
                    "branch": branch,
                },
            )
            try:
                self.read_file(workspace, path, branch)
            except ExternalEffectError as exc:
                if exc.status_code != 404:
                    raise
                deleted = True
            else:
                deleted = False
            if not deleted:
                raise IdentityMismatch(f"GitHub read-back shows file still exists after delete: {path}")
            return {
                "path": path,
                "branch": branch,
                "commit_sha": result["commit"]["sha"],
                "verified": True,
                "read_back_verified": True,
            }

        if tool == "github.open_pr":
            head = self._required(args, "head")
            base = str(args.get("base") or workspace.default_branch)
            result = self.http.request(
                "POST",
                f"/repos/{workspace.github_repository}/pulls",
                json_body={
                    "title": self._required(args, "title"),
                    "body": str(args.get("body") or ""),
                    "head": head,
                    "base": base,
                    "draft": bool(args.get("draft", False)),
                },
            )
            actual = self.http.request(
                "GET",
                f"/repos/{workspace.github_repository}/pulls/{result['number']}",
            )
            if actual["head"]["ref"] != head or actual["base"]["ref"] != base:
                raise IdentityMismatch("GitHub PR read-back mismatch")
            return {
                "number": actual["number"],
                "url": actual["html_url"],
                "head": actual["head"]["ref"],
                "base": actual["base"]["ref"],
                "state": actual["state"],
                "verified": True,
                "read_back_verified": True,
            }

        raise ProtocolError(f"unsupported GitHub effect tool: {tool}")

    def read_file(self, workspace: Workspace, path: str, ref: str | None = None) -> dict[str, Any]:
        params = {"ref": ref} if ref else None
        result = self.http.request(
            "GET",
            f"/repos/{workspace.github_repository}/contents/{path}",
            params=params,
        )
        if result.get("type") != "file":
            raise ProtocolError(f"path is not a file: {path}")
        raw = base64.b64decode(result["content"]).decode("utf-8")
        return {
            "path": path,
            "sha": result["sha"],
            "ref": ref,
            "content": raw,
            "size": result.get("size"),
        }

    @staticmethod
    def _required(args: dict[str, Any], key: str) -> Any:
        value = args.get(key)
        if value in (None, ""):
            raise ProtocolError(f"missing required argument: {key}")
        return value

    @staticmethod
    def _write_receipt(result: dict[str, Any], path: str, branch: str) -> dict[str, Any]:
        return {
            "path": path,
            "branch": branch,
            "commit_sha": result["commit"]["sha"],
            "content_sha": result["content"]["sha"],
            "verified": True,
        }
