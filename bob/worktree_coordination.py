from __future__ import annotations

import json
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .errors import AuthorityError, ConfigurationError, IdentityMismatch, ProtocolError
from .execution_ledger import (
    DEFAULT_MAX_PARALLEL_RUNS_PER_REPOSITORY,
    LEASE_HOLDING_STATES,
    TERMINAL_RUN_STATES,
    ExecutionLedger,
)
from .workspaces import Workspace, WorkspaceRegistry

_SAFE_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")


def _new_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def _repository_name_from_origin(origin: str) -> str | None:
    value = str(origin or "").strip()
    if value.startswith("git@github.com:"):
        name = value.split(":", 1)[1]
    else:
        parts = urlsplit(value)
        if (parts.hostname or "").casefold() != "github.com":
            return None
        name = parts.path.lstrip("/")
    if name.endswith(".git"):
        name = name[:-4]
    name = name.strip("/")
    return name or None


class GitWorktreeManager:
    """Local Git isolation only: never merge, push, force-push or delete branches."""

    def __init__(
        self,
        repo_root: str | Path,
        worktree_root: str | Path | None = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.worktree_root = (
            Path(worktree_root).resolve()
            if worktree_root is not None
            else self.repo_root.parent / f".{self.repo_root.name}-bob-worktrees"
        )

    def _git(self, *args: str, cwd: Path | None = None) -> str:
        process = subprocess.run(
            ["git", *args],
            cwd=str(cwd or self.repo_root),
            check=False,
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            message = (process.stderr or process.stdout or "git command failed").strip()
            raise ConfigurationError(message)
        return process.stdout.strip()

    def resolve_ref(self, ref: str) -> str:
        return self._git("rev-parse", "--verify", str(ref))

    def branch_head(self, branch: str) -> str:
        return self.resolve_ref(branch)

    def branch_exists(self, branch: str) -> bool:
        process = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=str(self.repo_root),
            check=False,
        )
        return process.returncode == 0

    def worktree_path(self, run_id: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", str(run_id)).strip("-")
        if not safe:
            raise ProtocolError("invalid run_id for worktree")
        return self.worktree_root / safe

    def ensure_worktree(self, *, run_id: str, branch: str, base_sha: str) -> Path:
        if not _SAFE_BRANCH.fullmatch(branch) or ".." in branch:
            raise ProtocolError(f"unsafe worktree branch: {branch!r}")
        path = self.worktree_path(run_id)
        self.worktree_root.mkdir(parents=True, exist_ok=True)

        if path.exists():
            try:
                actual = self._git("branch", "--show-current", cwd=path)
            except ConfigurationError as exc:
                raise ConfigurationError(
                    f"existing run worktree is invalid: {path}"
                ) from exc
            if actual != branch:
                raise AuthorityError(
                    f"worktree branch mismatch: expected {branch}, got {actual}"
                )
            return path

        if self.branch_exists(branch):
            self._git("worktree", "add", str(path), branch)
        else:
            self._git("worktree", "add", "-b", branch, str(path), base_sha)

        actual = self._git("branch", "--show-current", cwd=path)
        if actual != branch:
            raise AuthorityError(
                f"created worktree branch mismatch: expected {branch}, got {actual}"
            )
        return path

    def remove_worktree(self, run_id: str) -> None:
        path = self.worktree_path(run_id)
        if not path.exists():
            return
        dirty = self._git("status", "--porcelain", cwd=path)
        if dirty:
            raise AuthorityError(f"refusing to remove dirty run worktree: {path}")
        self._git("worktree", "remove", str(path))


class ExecutionCoordinator:
    """Repository-bound ledger + isolated worktrees + serialized integration gate."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        repository_full_name: str,
        repository_id: int,
        canonical_ref: str,
        state_path: str | Path | None = None,
        worktree_root: str | Path | None = None,
        max_parallel_runs_per_repository: int = DEFAULT_MAX_PARALLEL_RUNS_PER_REPOSITORY,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.repository_full_name = str(repository_full_name or "").strip().strip("/")
        self.repository_id = int(repository_id)
        self.canonical_ref = str(canonical_ref or "").strip()
        self.worktrees = GitWorktreeManager(self.repo_root, worktree_root)
        self._verify_repository_identity()
        self.ledger = ExecutionLedger(
            state_path
            or self.repo_root / ".bob" / "runtime" / "execution_ledger.json",
            repository_full_name=self.repository_full_name,
            repository_id=self.repository_id,
            repo_root=self.repo_root,
            canonical_ref=self.canonical_ref,
            max_parallel_runs_per_repository=max_parallel_runs_per_repository,
        )

    def _verify_repository_identity(self) -> None:
        origin = self.worktrees._git("remote", "get-url", "origin")
        actual = _repository_name_from_origin(origin)
        if actual is None or actual.casefold() != self.repository_full_name.casefold():
            raise IdentityMismatch(
                "local Git origin does not match configured repository: "
                f"expected={self.repository_full_name!r} actual={actual!r}"
            )
        self.worktrees.resolve_ref(self.canonical_ref)

    def _bound_canonical_ref(self, requested: str | None = None) -> str:
        value = str(requested or self.canonical_ref).strip()
        if value != self.canonical_ref:
            raise IdentityMismatch(
                f"coordinator canonical_ref mismatch: expected {self.canonical_ref!r}, got {value!r}"
            )
        return self.canonical_ref

    def create_run(
        self,
        *,
        goal: str,
        workspace: str,
        base_ref: str,
        leases: list[str],
        depends_on: list[str] | None = None,
        lane: str = "interactive",
        authority: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_id = _new_run_id()
        branch = f"bob/run/{run_id}"
        base_sha = self.worktrees.resolve_ref(base_ref)
        worktree_path = str(self.worktrees.worktree_path(run_id))
        self.ledger.create_run(
            run_id=run_id,
            goal=goal,
            workspace=workspace,
            base_ref=base_ref,
            base_sha=base_sha,
            branch=branch,
            worktree_path=worktree_path,
            leases=leases,
            depends_on=depends_on,
            lane=lane,
            authority=authority,
        )
        self.ensure_active_worktrees()
        return self.ledger.get_run(run_id)

    def ensure_active_worktrees(self) -> list[str]:
        prepared: list[str] = []
        snapshot = self.ledger.snapshot()
        for run_id, run in snapshot["runs"].items():
            if run.get("state") not in LEASE_HOLDING_STATES:
                continue
            try:
                self.worktrees.ensure_worktree(
                    run_id=run_id,
                    branch=run["branch"],
                    base_sha=run["base_sha"],
                )
                prepared.append(run_id)
            except Exception as exc:
                if run.get("state") not in TERMINAL_RUN_STATES:
                    self.ledger.fail_run(
                        run_id,
                        error=f"worktree preparation failed: {exc}",
                    )
                raise
        return prepared

    def mark_ready_for_integration(
        self,
        run_id: str,
        *,
        verified_base_sha: str,
        verification: dict[str, Any],
    ) -> dict[str, Any]:
        run = self.ledger.get_run(run_id)
        if run["state"] not in {"ACTIVE", "AWAITING_APPROVAL"}:
            raise ProtocolError(
                f"run must be active before integration readiness: {run['state']}"
            )
        head_sha = self.worktrees.branch_head(run["branch"])
        result = self.ledger.mark_ready_for_integration(
            run_id,
            verified_base_sha=verified_base_sha,
            verified_head_sha=head_sha,
            verification=verification,
        )
        self.ensure_active_worktrees()
        return result

    def record_rebase_verification(
        self,
        run_id: str,
        *,
        canonical_ref: str,
        verification: dict[str, Any],
    ) -> dict[str, Any]:
        run = self.ledger.get_run(run_id)
        canonical_ref = self._bound_canonical_ref(canonical_ref)
        canonical_sha = self.worktrees.resolve_ref(canonical_ref)
        branch_head = self.worktrees.branch_head(run["branch"])
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", canonical_sha, branch_head],
            cwd=str(self.repo_root),
            check=False,
        )
        if ancestor.returncode != 0:
            raise ProtocolError(
                "run branch is not based on current canonical sha; "
                "rebase before reverification"
            )
        return self.ledger.record_rebase_verification(
            run_id,
            verified_base_sha=canonical_sha,
            verified_head_sha=branch_head,
            verification=verification,
        )

    def integration_plan(self, canonical_ref: str | None = None) -> dict[str, Any]:
        canonical_ref = self._bound_canonical_ref(canonical_ref)
        canonical_sha = self.worktrees.resolve_ref(canonical_ref)
        return self.ledger.integration_plan(canonical_sha)

    def begin_integration(
        self,
        run_id: str,
        *,
        canonical_ref: str | None = None,
    ) -> dict[str, Any]:
        canonical_ref = self._bound_canonical_ref(canonical_ref)
        canonical_sha = self.worktrees.resolve_ref(canonical_ref)
        return self.ledger.begin_integration(run_id, canonical_sha=canonical_sha)

    def complete_integration(
        self,
        run_id: str,
        *,
        canonical_ref: str | None = None,
    ) -> dict[str, Any]:
        run = self.ledger.get_run(run_id)
        canonical_ref = self._bound_canonical_ref(canonical_ref)
        canonical_sha = self.worktrees.resolve_ref(canonical_ref)
        verified_head = str(run.get("verified_head_sha") or "")
        if not verified_head:
            raise ProtocolError("integration completion requires a verified candidate head")
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", verified_head, canonical_sha],
            cwd=str(self.repo_root),
            check=False,
        )
        if ancestor.returncode != 0:
            raise ProtocolError(
                "cannot record integration: verified candidate head is not contained "
                "in current canonical ref"
            )
        result = self.ledger.complete_integration(
            run_id,
            canonical_sha=canonical_sha,
        )
        self.ensure_active_worktrees()
        return result

    def cancel_run(
        self,
        run_id: str,
        *,
        reason: str = "cancelled",
    ) -> dict[str, Any]:
        result = self.ledger.cancel_run(run_id, reason=reason)
        self.ensure_active_worktrees()
        return result

    def snapshot(self) -> dict[str, Any]:
        result = self.ledger.snapshot()
        result["repo_root"] = str(self.repo_root)
        result["worktree_root"] = str(self.worktrees.worktree_root)
        return result


class RepositoryCoordinatorRegistry:
    """Map workspaces onto one coordinator per stable GitHub repository identity."""

    def __init__(
        self,
        workspace_registry: WorkspaceRegistry,
        *,
        repository_bindings: dict[int | str, dict[str, Any]] | None = None,
        max_parallel_runs_per_repository: int = DEFAULT_MAX_PARALLEL_RUNS_PER_REPOSITORY,
    ):
        self.workspace_registry = workspace_registry
        self.max_parallel_runs_per_repository = int(max_parallel_runs_per_repository)
        self._bindings: dict[int, dict[str, Any]] = {}
        self._coordinators: dict[int, ExecutionCoordinator] = {}
        for raw_key, raw_binding in (repository_bindings or {}).items():
            binding = dict(raw_binding or {})
            repository_id = int(binding.get("repository_id") or raw_key)
            self.configure_repository(
                repository_full_name=str(binding["repository_full_name"]),
                repository_id=repository_id,
                repo_root=binding["repo_root"],
                canonical_ref=str(binding["canonical_ref"]),
                state_path=binding.get("state_path"),
                worktree_root=binding.get("worktree_root"),
            )

    @classmethod
    def from_json(
        cls,
        workspace_registry: WorkspaceRegistry,
        payload: str | None,
        *,
        default_bindings: dict[int | str, dict[str, Any]] | None = None,
        max_parallel_runs_per_repository: int = DEFAULT_MAX_PARALLEL_RUNS_PER_REPOSITORY,
    ) -> "RepositoryCoordinatorRegistry":
        bindings = dict(default_bindings or {})
        raw = str(payload or "").strip()
        if raw:
            try:
                extra = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ConfigurationError(f"invalid repository bindings JSON: {exc}") from exc
            if not isinstance(extra, dict):
                raise ConfigurationError("repository bindings JSON must be an object")
            bindings.update(extra)
        return cls(
            workspace_registry,
            repository_bindings=bindings,
            max_parallel_runs_per_repository=max_parallel_runs_per_repository,
        )

    def configure_repository(
        self,
        *,
        repository_full_name: str,
        repository_id: int,
        repo_root: str | Path,
        canonical_ref: str,
        state_path: str | Path | None = None,
        worktree_root: str | Path | None = None,
    ) -> None:
        repository_id = int(repository_id)
        root = Path(repo_root).resolve()
        binding = {
            "repository_full_name": str(repository_full_name).strip().strip("/"),
            "repository_id": repository_id,
            "repo_root": root,
            "canonical_ref": str(canonical_ref).strip(),
            "state_path": None if state_path is None else Path(state_path).resolve(),
            "worktree_root": None if worktree_root is None else Path(worktree_root).resolve(),
        }
        existing = self._bindings.get(repository_id)
        if existing is not None and existing != binding:
            raise ConfigurationError(
                f"repository {repository_id} has conflicting local coordinator bindings"
            )
        for other_id, other in self._bindings.items():
            if (
                other_id != repository_id
                and other["repository_full_name"].casefold()
                == binding["repository_full_name"].casefold()
            ):
                raise ConfigurationError(
                    "same repository_full_name configured with multiple repository IDs"
                )
        self._bindings[repository_id] = binding

    def _coordinator(self, repository_id: int) -> ExecutionCoordinator:
        repository_id = int(repository_id)
        if repository_id in self._coordinators:
            return self._coordinators[repository_id]
        binding = self._bindings.get(repository_id)
        if binding is None:
            raise ConfigurationError(
                f"no local repository path configured for repository_id={repository_id}"
            )
        coordinator = ExecutionCoordinator(
            binding["repo_root"],
            repository_full_name=binding["repository_full_name"],
            repository_id=repository_id,
            canonical_ref=binding["canonical_ref"],
            state_path=binding["state_path"],
            worktree_root=binding["worktree_root"],
            max_parallel_runs_per_repository=self.max_parallel_runs_per_repository,
        )
        self._coordinators[repository_id] = coordinator
        return coordinator

    def coordinator_for_workspace(self, workspace_code: str) -> ExecutionCoordinator:
        workspace = self.workspace_registry.get(workspace_code)
        binding = self._bindings.get(workspace.github_repository_id)
        if binding is None:
            raise ConfigurationError(
                f"workspace {workspace.code} has no configured local repository path"
            )
        if (
            binding["repository_full_name"].casefold()
            != workspace.github_repository.casefold()
        ):
            raise IdentityMismatch(
                "workspace repository identity does not match local coordinator binding"
            )
        return self._coordinator(workspace.github_repository_id)

    def coordinator_for_run(self, run_id: str) -> ExecutionCoordinator:
        matches = []
        for repository_id in self._bindings:
            coordinator = self._coordinator(repository_id)
            if run_id in coordinator.ledger.snapshot()["runs"]:
                matches.append(coordinator)
        if len(matches) != 1:
            raise ProtocolError(f"execution run not found or ambiguous: {run_id}")
        return matches[0]

    def coordinator_for_cognition(self, cognition_id: str) -> ExecutionCoordinator:
        matches = []
        for repository_id in self._bindings:
            coordinator = self._coordinator(repository_id)
            if cognition_id in coordinator.ledger.snapshot()["cognitions"]:
                matches.append(coordinator)
        if len(matches) != 1:
            raise ProtocolError(f"cognition not found or ambiguous: {cognition_id}")
        return matches[0]

    def snapshot(self) -> dict[str, Any]:
        repositories = {}
        for repository_id in self._bindings:
            repositories[str(repository_id)] = self._coordinator(repository_id).snapshot()
        return {
            "max_parallel_runs_per_repository": self.max_parallel_runs_per_repository,
            "repositories": repositories,
        }
