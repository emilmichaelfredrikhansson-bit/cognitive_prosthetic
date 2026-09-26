from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from .errors import AuthorityError, ConfigurationError, ProtocolError
from .protocol import BobMessage
from .worktree_coordination import ExecutionCoordinator


MAX_READ_LINES = 250
MAX_READ_CHARS = 40_000
MAX_WRITE_CHARS = 250_000
MAX_SEARCH_RESULTS = 50
BLOCKED_PREFIXES = (
    ".git",
    ".bob/runtime",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class CampaignRepoAdapter:
    """Local isolated-worktree adapter used by the campaign executor only."""

    def __init__(
        self,
        execution: ExecutionCoordinator,
        run: dict[str, Any],
        *,
        write_authorized: bool,
        verification_commands: list[list[str]] | None = None,
    ):
        self.execution = execution
        self.run = run
        self.write_authorized = bool(write_authorized)
        self.verification_commands = [
            list(command) for command in (verification_commands or [])
        ]
        self.worktree = self._safe_worktree()

    @staticmethod
    def _git(path: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            message = (
                completed.stderr or completed.stdout or "git command failed"
            ).strip()
            raise ConfigurationError(message)
        return completed.stdout.strip()

    def _safe_worktree(self) -> Path:
        self.execution._verify_repository_identity()
        expected = self.execution.worktrees.worktree_path(
            self.run["run_id"]
        ).resolve()
        recorded = Path(self.run["worktree_path"]).resolve()
        if expected != recorded:
            raise ProtocolError("campaign executor worktree binding mismatch")
        actual = self.execution.worktrees.ensure_worktree(
            run_id=self.run["run_id"],
            branch=self.run["branch"],
            base_sha=self.run["base_sha"],
        ).resolve()
        if actual != expected:
            raise ProtocolError(
                "campaign executor worktree escaped coordinator root"
            )
        if self._git(actual, "branch", "--show-current") != self.run["branch"]:
            raise ProtocolError("campaign executor worktree branch mismatch")
        head = self._git(actual, "rev-parse", "HEAD")
        if head != self.execution.worktrees.branch_head(self.run["branch"]):
            raise ProtocolError(
                "campaign executor branch/worktree head mismatch"
            )
        return actual

    def refresh(self, run: dict[str, Any]) -> None:
        if run["run_id"] != self.run["run_id"]:
            raise ProtocolError("campaign repo adapter run changed")
        self.run = run
        self.worktree = self._safe_worktree()

    def _resolve_path(
        self,
        raw_path: Any,
        *,
        allow_missing: bool = False,
    ) -> tuple[str, Path]:
        value = str(raw_path or "").replace("\\", "/").strip()
        value = value[2:] if value.startswith("./") else value
        if not value or value.startswith("/") or ":" in value.split("/", 1)[0]:
            raise AuthorityError("repository path must be relative")
        parts = [part for part in value.split("/") if part not in ("", ".")]
        if not parts or any(part == ".." for part in parts):
            raise AuthorityError("repository path traversal is not allowed")
        normalized = "/".join(parts)
        folded = normalized.casefold()
        if any(
            folded == prefix.casefold()
            or folded.startswith(prefix.casefold().rstrip("/") + "/")
            for prefix in BLOCKED_PREFIXES
        ):
            raise AuthorityError(
                f"repository path is executor-protected: {normalized}"
            )
        basename = parts[-1].casefold()
        if basename == ".env" or basename.startswith(".env."):
            raise AuthorityError(
                "environment-secret files are executor-protected"
            )
        root = self.worktree.resolve()
        candidate = (root / Path(*parts)).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise AuthorityError("repository path escaped worktree") from exc
        if not allow_missing and not candidate.exists():
            raise ProtocolError(
                f"repository path does not exist: {normalized}"
            )
        return normalized, candidate

    def is_clean(self) -> bool:
        return not bool(self._git(self.worktree, "status", "--porcelain"))

    def require_clean(self) -> None:
        if not self.is_clean():
            raise ProtocolError(
                "campaign executor requires a clean safe boundary"
            )

    def status(self) -> dict[str, Any]:
        return {
            "branch": self._git(
                self.worktree, "branch", "--show-current"
            ),
            "head_sha": self._git(self.worktree, "rev-parse", "HEAD"),
            "base_sha": self.run["base_sha"],
            "clean": self.is_clean(),
        }

    def _read_file(self, args: dict[str, Any]) -> dict[str, Any]:
        normalized, path = self._resolve_path(args.get("path"))
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError(
                "campaign executor reads UTF-8 text files only"
            ) from exc
        lines = text.splitlines()
        start = max(1, int(args.get("start_line") or 1))
        requested_end = int(
            args.get("end_line") or (start + MAX_READ_LINES - 1)
        )
        end = max(start, min(requested_end, start + MAX_READ_LINES - 1))
        selected = "\n".join(lines[start - 1 : end])
        char_truncated = len(selected) > MAX_READ_CHARS
        if char_truncated:
            selected = selected[:MAX_READ_CHARS]
        return {
            "path": normalized,
            "start_line": start,
            "end_line": min(end, len(lines)),
            "total_lines": len(lines),
            "content": selected,
            "content_sha256": _sha256(data),
            "truncated": char_truncated or end < len(lines),
        }

    def _list_files(self, args: dict[str, Any]) -> dict[str, Any]:
        prefix = str(args.get("prefix") or "").replace("\\", "/").strip("/")
        limit = max(1, min(int(args.get("limit") or 200), 500))
        files = [
            line
            for line in self._git(self.worktree, "ls-files").splitlines()
            if line
        ]
        if prefix:
            folded = prefix.casefold()
            files = [
                path
                for path in files
                if path.casefold() == folded
                or path.casefold().startswith(folded.rstrip("/") + "/")
            ]
        return {
            "prefix": prefix or None,
            "files": files[:limit],
            "truncated": len(files) > limit,
        }

    def _search(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query") or "").strip()
        if not 2 <= len(query) <= 160:
            raise ProtocolError(
                "repo.search query must contain 2..160 characters"
            )
        prefix = str(args.get("prefix") or "").replace("\\", "/").strip("/")
        limit = max(
            1, min(int(args.get("limit") or 20), MAX_SEARCH_RESULTS)
        )
        folded_query = query.casefold()
        results: list[dict[str, Any]] = []
        searched = 0
        for relative in self._git(self.worktree, "ls-files").splitlines():
            if not relative:
                continue
            if prefix:
                folded = prefix.casefold()
                if (
                    relative.casefold() != folded
                    and not relative.casefold().startswith(
                        folded.rstrip("/") + "/"
                    )
                ):
                    continue
            try:
                _, path = self._resolve_path(relative)
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError, ProtocolError, AuthorityError):
                continue
            searched += 1
            for line_number, line in enumerate(
                content.splitlines(), start=1
            ):
                if folded_query not in line.casefold():
                    continue
                results.append(
                    {
                        "path": relative,
                        "line": line_number,
                        "text": line[:500],
                    }
                )
                if len(results) >= limit:
                    return {
                        "query": query,
                        "prefix": prefix or None,
                        "results": results,
                        "searched_files": searched,
                        "truncated": True,
                    }
        return {
            "query": query,
            "prefix": prefix or None,
            "results": results,
            "searched_files": searched,
            "truncated": False,
        }

    def read(self, message: BobMessage) -> dict[str, Any]:
        tool = message.tool or ""
        if tool == "repo.read_file":
            return self._read_file(message.args)
        if tool == "repo.list_files":
            return self._list_files(message.args)
        if tool == "repo.search":
            return self._search(message.args)
        if tool == "repo.status":
            return self.status()
        if tool == "repo.verify":
            return self.verify()
        raise AuthorityError(
            f"campaign executor read tool is not allowed: {tool}"
        )

    def verify(self) -> dict[str, Any]:
        self.execution._verify_repository_identity()
        status = self.status()
        checks: list[dict[str, Any]] = [
            {
                "name": "clean_worktree",
                "status": "PASS" if status["clean"] else "FAIL",
            }
        ]
        diff_check = subprocess.run(
            [
                "git",
                "diff",
                "--check",
                f"{self.run['base_sha']}..HEAD",
            ],
            cwd=str(self.worktree),
            capture_output=True,
            text=True,
            check=False,
        )
        checks.append(
            {
                "name": "git_diff_check",
                "status": (
                    "PASS" if diff_check.returncode == 0 else "FAIL"
                ),
                "returncode": diff_check.returncode,
                "output": (
                    diff_check.stdout + diff_check.stderr
                )[-4000:],
            }
        )
        for index, command in enumerate(
            self.verification_commands, start=1
        ):
            completed = subprocess.run(
                command,
                cwd=str(self.worktree),
                capture_output=True,
                text=True,
                check=False,
            )
            checks.append(
                {
                    "name": f"configured_{index}",
                    "argv": list(command),
                    "status": (
                        "PASS" if completed.returncode == 0 else "FAIL"
                    ),
                    "returncode": completed.returncode,
                    "output": (
                        completed.stdout + completed.stderr
                    )[-6000:],
                }
            )
        head = self._git(self.worktree, "rev-parse", "HEAD")
        branch_head = self.execution.worktrees.branch_head(
            self.run["branch"]
        )
        checks.append(
            {
                "name": "branch_head",
                "status": "PASS" if head == branch_head else "FAIL",
                "head_sha": head,
                "branch_head_sha": branch_head,
            }
        )
        passed = all(check["status"] == "PASS" for check in checks)
        return {
            "status": "PASS" if passed else "FAIL",
            "repository": self.execution.repository_full_name,
            "repository_id": self.execution.repository_id,
            "run_id": self.run["run_id"],
            "branch": self.run["branch"],
            "base_sha": self.run["base_sha"],
            "head_sha": head,
            "checks": checks,
        }

    def prepare_effect(
        self,
        message: BobMessage,
        *,
        item_id: str,
    ) -> dict[str, Any]:
        if not self.write_authorized:
            raise AuthorityError(
                "workspace does not authorize isolated branch writes"
            )
        if message.tool not in {
            "repo.create_file",
            "repo.replace_file",
            "repo.delete_file",
        }:
            raise AuthorityError(
                f"campaign executor effect tool is not allowed: "
                f"{message.tool}"
            )
        self.require_clean()
        normalized, path = self._resolve_path(
            message.args.get("path"),
            allow_missing=message.tool == "repo.create_file",
        )
        content = None
        before_sha = None
        after_sha = None
        if message.tool == "repo.create_file":
            if path.exists():
                raise ProtocolError(
                    f"repo.create_file target already exists: {normalized}"
                )
            content = str(message.args.get("content") or "")
            if len(content) > MAX_WRITE_CHARS:
                raise ProtocolError(
                    "campaign executor write exceeds bounded size"
                )
            after_sha = _sha256(content.encode("utf-8"))
        else:
            if not path.exists():
                raise ProtocolError(
                    f"effect target does not exist: {normalized}"
                )
            before_sha = str(
                message.args.get("expected_sha256") or ""
            ).strip()
            if before_sha != _sha256(path.read_bytes()):
                raise ProtocolError(
                    f"effect source sha256 mismatch for {normalized}"
                )
            if message.tool == "repo.replace_file":
                content = str(message.args.get("content") or "")
                if len(content) > MAX_WRITE_CHARS:
                    raise ProtocolError(
                        "campaign executor write exceeds bounded size"
                    )
                after_sha = _sha256(content.encode("utf-8"))

        return {
            "message_id": message.id,
            "tool": message.tool,
            "path": normalized,
            "content": content,
            "expected_before_sha256": before_sha,
            "expected_after_sha256": after_sha,
            "pre_head_sha": self._git(
                self.worktree, "rev-parse", "HEAD"
            ),
            "commit_message": (
                f"Bob campaign {item_id} effect {message.id}: "
                f"{message.tool} {normalized}"
            ),
        }

    def _verify_effect_after_state(
        self,
        pending: dict[str, Any],
    ) -> dict[str, Any]:
        _, path = self._resolve_path(
            pending["path"],
            allow_missing=pending["tool"] == "repo.delete_file",
        )
        if pending["tool"] == "repo.delete_file":
            if path.exists():
                raise ProtocolError(
                    "delete effect after-state still exists"
                )
            after_sha = None
        else:
            if not path.exists():
                raise ProtocolError(
                    "write effect after-state is missing"
                )
            after_sha = _sha256(path.read_bytes())
            if after_sha != pending["expected_after_sha256"]:
                raise ProtocolError(
                    "write effect after-state sha256 mismatch"
                )
        self.require_clean()
        head = self._git(self.worktree, "rev-parse", "HEAD")
        if head == pending["pre_head_sha"]:
            raise ProtocolError("effect did not advance branch head")
        parent = self._git(self.worktree, "rev-parse", f"{head}^")
        if parent != pending["pre_head_sha"]:
            raise ProtocolError(
                "effect commit parent does not match prepared head"
            )
        subject = self._git(
            self.worktree, "log", "-1", "--format=%s"
        )
        if subject != pending["commit_message"]:
            raise ProtocolError("effect commit marker mismatch")
        return {
            "message_id": pending["message_id"],
            "tool": pending["tool"],
            "path": pending["path"],
            "pre_head_sha": pending["pre_head_sha"],
            "head_sha": head,
            "after_sha256": after_sha,
            "verified": True,
        }

    def apply_pending(
        self,
        pending: dict[str, Any],
    ) -> dict[str, Any]:
        normalized, path = self._resolve_path(
            pending["path"],
            allow_missing=pending["tool"] == "repo.create_file",
        )
        current_head = self._git(
            self.worktree, "rev-parse", "HEAD"
        )
        if current_head != pending["pre_head_sha"]:
            return self._verify_effect_after_state(pending)

        self.require_clean()
        if pending["tool"] == "repo.create_file":
            if path.exists():
                raise ProtocolError(
                    "prepared create target unexpectedly exists"
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                pending["content"], encoding="utf-8", newline="\n"
            )
        elif pending["tool"] == "repo.replace_file":
            if not path.exists():
                raise ProtocolError(
                    "prepared replace target disappeared"
                )
            if _sha256(
                path.read_bytes()
            ) != pending["expected_before_sha256"]:
                raise ProtocolError("prepared replace source changed")
            path.write_text(
                pending["content"], encoding="utf-8", newline="\n"
            )
        elif pending["tool"] == "repo.delete_file":
            if not path.exists():
                raise ProtocolError(
                    "prepared delete target disappeared"
                )
            if _sha256(
                path.read_bytes()
            ) != pending["expected_before_sha256"]:
                raise ProtocolError("prepared delete source changed")
            path.unlink()
        else:
            raise AuthorityError("unknown durable campaign effect")

        self._git(self.worktree, "add", "--", normalized)
        completed = subprocess.run(
            [
                "git",
                "commit",
                "-m",
                pending["commit_message"],
            ],
            cwd=str(self.worktree),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ConfigurationError(
                (
                    completed.stderr
                    or completed.stdout
                    or "git commit failed"
                ).strip()
            )
        return self._verify_effect_after_state(pending)
