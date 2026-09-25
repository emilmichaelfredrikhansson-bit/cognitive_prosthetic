from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlsplit

from bob.errors import ExternalEffectError, IdentityMismatch, ProtocolError
from bob.workspaces import Workspace
from .http import JsonHttp


class GitHubAdapter:
    def __init__(self, token: str | None = None, local_repo_root: str | None = None):
        token = str(token or "").strip()
        self.authenticated = bool(token)
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.http = JsonHttp("https://api.github.com", headers=headers)

        candidate = Path(
            local_repo_root
            or os.environ.get("BOB_GITHUB_LOCAL_REPO", "")
            or os.getcwd()
        ).resolve()
        self.local_repo_root = candidate if (candidate / ".git").exists() else None
        self.local_repository = self._detect_local_repository()

    def _git(self, *args: str, allow_failure: bool = False) -> str:
        if self.local_repo_root is None:
            raise ProtocolError("local Git repository is unavailable")
        completed = subprocess.run(
            ["git", *args],
            cwd=str(self.local_repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        if completed.returncode != 0 and not allow_failure:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise ProtocolError(f"local git {' '.join(args)} failed: {detail}")
        return completed.stdout

    def _detect_local_repository(self) -> str | None:
        if self.local_repo_root is None:
            return None
        try:
            remote = self._git("remote", "get-url", "origin").strip()
        except Exception:
            return None
        value = remote.strip()
        if value.startswith("git@github.com:"):
            name = value.split(":", 1)[1]
        else:
            parts = urlsplit(value)
            if (parts.hostname or "").lower() != "github.com":
                return None
            name = parts.path.lstrip("/")
        if name.endswith(".git"):
            name = name[:-4]
        name = name.strip("/")
        return name or None

    def _matches_local_repository(self, workspace: Workspace) -> bool:
        return (
            self.local_repo_root is not None
            and isinstance(self.local_repository, str)
            and self.local_repository.casefold() == workspace.github_repository.casefold()
        )

    def _use_local_read(self, workspace: Workspace) -> bool:
        return not self.authenticated and self._matches_local_repository(workspace)

    @staticmethod
    def _safe_repo_path(path: str) -> str:
        value = str(path or "").replace("\\", "/").strip("/")
        parsed = PurePosixPath(value)
        if not value or parsed.is_absolute() or ".." in parsed.parts:
            raise ProtocolError(f"invalid repository path: {path!r}")
        return value

    def _local_ref(self, workspace: Workspace, ref: str | None) -> str:
        requested = str(ref or workspace.default_branch).strip()
        if not requested:
            raise ProtocolError("Git ref must not be empty")
        for candidate in (requested, f"origin/{requested}"):
            resolved = self._git(
                "rev-parse",
                "--verify",
                f"{candidate}^{{commit}}",
                allow_failure=True,
            ).strip()
            if resolved:
                return candidate
        raise ProtocolError(f"local Git ref unavailable: {requested}")

    def _read_local_file_at_ref(
        self,
        path: str,
        resolved_ref: str,
        requested_ref: str | None,
    ) -> dict[str, Any]:
        safe_path = self._safe_repo_path(path)
        spec = f"{resolved_ref}:{safe_path}"
        content = self._git("show", spec)
        sha = self._git("rev-parse", spec).strip()
        return {
            "path": safe_path,
            "sha": sha,
            "ref": requested_ref,
            "content": content,
            "size": len(content.encode("utf-8")),
            "source": "local_git",
        }

    def _read_local_file(
        self,
        workspace: Workspace,
        path: str,
        ref: str | None,
    ) -> dict[str, Any]:
        resolved_ref = self._local_ref(workspace, ref)
        return self._read_local_file_at_ref(path, resolved_ref, ref)

    def _list_local_contents(
        self,
        workspace: Workspace,
        path: str,
        ref: str | None,
    ) -> list[dict[str, Any]]:
        normalized = str(path or "").replace("\\", "/").strip("/")
        if normalized:
            normalized = self._safe_repo_path(normalized)
        resolved_ref = self._local_ref(workspace, ref)
        treeish = resolved_ref if not normalized else f"{resolved_ref}:{normalized}"
        raw = self._git("ls-tree", treeish)
        items: list[dict[str, Any]] = []
        for line in raw.splitlines():
            try:
                metadata, name = line.split("\t", 1)
                _mode, obj_type, sha = metadata.split(" ", 2)
            except ValueError:
                continue
            full_path = f"{normalized}/{name}".strip("/")
            items.append({
                "name": name,
                "path": full_path,
                "sha": sha,
                "type": "file" if obj_type == "blob" else "dir",
                "source": "local_git",
            })
        return items

    def can_preview_from_local_git(self, workspace: Workspace) -> bool:
        """Allow approval staging from a matching local checkout without granting writes."""
        return self._use_local_read(workspace)

    def capabilities(self) -> list[str]:
        capabilities = [
            "github.repo",
            "github.read_file",
            "github.read_files",
            "github.list_contents",
        ]
        if self.authenticated:
            capabilities.extend([
                "github.create_branch",
                "github.create_file",
                "github.replace_file",
                "github.delete_file",
                "github.open_pr",
            ])
        return capabilities

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
        if self._use_local_read(workspace):
            resolved_ref = self._local_ref(workspace, branch)
            return self._git("rev-parse", f"{resolved_ref}^{{commit}}").strip()
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
            if self._use_local_read(workspace):
                return self._list_local_contents(workspace, path, args.get("ref"))
            self.verify_workspace(workspace)
            params = {"ref": args["ref"]} if args.get("ref") else None
            return self.http.request(
                "GET",
                f"/repos/{workspace.github_repository}/contents/{path}",
                params=params,
            )
        raise ProtocolError(f"unsupported GitHub read tool: {tool}")

    def effect(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        if not self.authenticated:
            raise ProtocolError("GitHub write effects require GITHUB_TOKEN")
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

    def read_files_snapshot(
        self,
        workspace: Workspace,
        paths: list[str] | tuple[str, ...],
        ref: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read one coherent repository snapshot, preferring verified exact local Git."""
        requested_paths = [self._safe_repo_path(path) for path in paths]
        if not requested_paths:
            return []
        if self._matches_local_repository(workspace):
            resolved_ref = self._local_ref(workspace, ref)
            local_commit = self._git("rev-parse", f"{resolved_ref}^{{commit}}").strip()
            exact_local = not self.authenticated
            if self.authenticated:
                self.verify_workspace(workspace)
                requested_ref = str(ref or workspace.default_branch).strip()
                remote = self.http.request(
                    "GET",
                    f"/repos/{workspace.github_repository}/commits/{quote(requested_ref, safe='')}",
                )
                exact_local = isinstance(remote, dict) and str(remote.get("sha") or "") == local_commit
            if exact_local:
                return [
                    self._read_local_file_at_ref(path, resolved_ref, ref)
                    for path in requested_paths
                ]
        return [self.read_file(workspace, path, ref) for path in requested_paths]

    def read_file(self, workspace: Workspace, path: str, ref: str | None = None) -> dict[str, Any]:
        if self._use_local_read(workspace):
            return self._read_local_file(workspace, path, ref)
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
