from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, ProtocolError
from .execution_ledger import TERMINAL_RUN_STATES
from .selfdev_queue import SelfDevelopmentQueue
from .worktree_coordination import ExecutionCoordinator


SCHEMA = "BOB_SELF_DEVELOPMENT_CHECKPOINTS_V1"
CHECKPOINTABLE_RUN_STATES = {"ACTIVE", "PARKED"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"checkpoint-{uuid.uuid4().hex[:12]}"


class SelfDevelopmentCheckpoints:
    """Durable reversible checkpoints for Bob-owned isolated selfdev worktrees."""

    def __init__(
        self,
        path: str | Path,
        queue: SelfDevelopmentQueue,
        execution: ExecutionCoordinator,
    ):
        self.path = Path(path)
        self.queue = queue
        self.execution = execution
        self._lock = threading.RLock()
        if (
            queue.repository_id != execution.repository_id
            or queue.repository_full_name.casefold()
            != execution.repository_full_name.casefold()
            or queue.canonical_ref != execution.canonical_ref
        ):
            raise ConfigurationError(
                "self-development checkpoint repository binding mismatch"
            )
        self._state = self._load()
    def _identity(self) -> dict[str, Any]:
        return {
            "id": self.queue.repository_id,
            "full_name": self.queue.repository_full_name,
            "canonical_ref": self.queue.canonical_ref,
        }

    def _empty(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "repository": self._identity(),
            "checkpoints": {},
            "order": [],
            "updated_at": _now(),
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"invalid self-development checkpoint store: {self.path}"
            ) from exc
        if data.get("schema") != SCHEMA:
            raise ConfigurationError(
                f"self-development checkpoint schema mismatch: {data.get('schema')!r}"
            )
        if data.get("repository") != self._identity():
            raise ConfigurationError(
                "self-development checkpoint repository identity mismatch"
            )
        data.setdefault("checkpoints", {})
        data.setdefault("order", [])
        if set(data["order"]) != set(data["checkpoints"]):
            raise ConfigurationError(
                "self-development checkpoint order/state mismatch"
            )
        return data

    def _write_fsync(self, path: Path, payload: str) -> None:
        with path.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state["updated_at"] = _now()
        payload = json.dumps(self._state, indent=2, sort_keys=True) + "\n"
        fd, temp_name = tempfile.mkstemp(
            prefix=self.path.name + ".",
            suffix=".tmp",
            dir=str(self.path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.replace(temp_name, self.path)
            except PermissionError:
                if os.name != "nt":
                    raise
                self._write_fsync(self.path, payload)
                if self.path.read_text(encoding="utf-8") != payload:
                    raise ConfigurationError(
                        "Windows checkpoint persistence verification failed"
                    )
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
    def _item(self, item_id: str) -> dict[str, Any]:
        for item in self.queue.snapshot()["items"]:
            if item["item_id"] == str(item_id):
                return item
        raise ProtocolError(f"unknown self-development item: {item_id}")

    def _bound_run(self, item: dict[str, Any]) -> dict[str, Any]:
        run_id = str(item.get("execution_run_id") or "").strip()
        if not run_id:
            raise ProtocolError("self-development item has no bound execution run")
        run = self.execution.ledger.get_run(run_id)
        authority = run.get("authority") or {}
        if (
            run.get("lane") != "selfdev"
            or authority.get("selfdev_item_id") != item["item_id"]
            or authority.get("promotion_authority") != "NONE"
        ):
            raise ProtocolError(
                "checkpoint target is not the item's isolated no-promotion selfdev run"
            )
        return run

    def _has_running_cognition(self, run: dict[str, Any]) -> bool:
        snapshot = self.execution.ledger.snapshot()
        for cognition_id in run.get("cognition_ids") or []:
            cognition = snapshot["cognitions"].get(cognition_id)
            if cognition and cognition.get("state") == "RUNNING":
                return True
        return False

    def _safe_worktree(self, run: dict[str, Any]) -> Path:
        expected = self.execution.worktrees.worktree_path(run["run_id"]).resolve()
        recorded = Path(run["worktree_path"]).resolve()
        if recorded != expected:
            raise ProtocolError(
                "self-development run worktree path does not match coordinator"
            )
        path = self.execution.worktrees.ensure_worktree(
            run_id=run["run_id"],
            branch=run["branch"],
            base_sha=run["base_sha"],
        ).resolve()
        if path != expected:
            raise ProtocolError("self-development worktree escaped expected path")
        return path

    def _git(self, path: Path, *args: str) -> str:
        process = subprocess.run(
            ["git", *args],
            cwd=str(path),
            check=False,
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            message = (process.stderr or process.stdout or "git command failed").strip()
            raise ConfigurationError(message)
        return process.stdout.strip()

    def _assert_checkpointable(self, run: dict[str, Any]) -> None:
        if run.get("state") not in CHECKPOINTABLE_RUN_STATES:
            raise ProtocolError(
                f"self-development run is not checkpointable: {run.get('state')}"
            )
        if self._has_running_cognition(run):
            raise ProtocolError(
                "self-development checkpoint requires a safe cognition boundary"
            )
    def create(
        self,
        item_id: str,
        *,
        label: str | None = None,
        verification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        item = self._item(item_id)
        run = self._bound_run(item)
        self._assert_checkpointable(run)
        path = self._safe_worktree(run)
        if self._git(path, "status", "--porcelain"):
            raise ProtocolError(
                "checkpoint requires a clean worktree; commit or discard experiment first"
            )
        actual_branch = self._git(path, "branch", "--show-current")
        if actual_branch != run["branch"]:
            raise ProtocolError("checkpoint worktree branch mismatch")
        head_sha = self._git(path, "rev-parse", "HEAD")
        if head_sha != self.execution.worktrees.branch_head(run["branch"]):
            raise ProtocolError("checkpoint branch/worktree head mismatch")
        checkpoint = {
            "checkpoint_id": _new_id(),
            "item_id": item["item_id"],
            "run_id": run["run_id"],
            "branch": run["branch"],
            "head_sha": head_sha,
            "base_sha": run["base_sha"],
            "label": None if label in (None, "") else str(label),
            "verification": copy.deepcopy(verification or {}),
            "created_at": _now(),
            "revert_count": 0,
            "last_reverted_at": None,
        }
        with self._lock:
            self._state["checkpoints"][checkpoint["checkpoint_id"]] = checkpoint
            self._state["order"].append(checkpoint["checkpoint_id"])
            self._persist()
        return copy.deepcopy(checkpoint)

    def _checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        with self._lock:
            checkpoint = self._state["checkpoints"].get(str(checkpoint_id))
            if checkpoint is None:
                raise ProtocolError(
                    f"unknown self-development checkpoint: {checkpoint_id}"
                )
            return copy.deepcopy(checkpoint)

    def revert(self, item_id: str, checkpoint_id: str) -> dict[str, Any]:
        item = self._item(item_id)
        run = self._bound_run(item)
        self._assert_checkpointable(run)
        checkpoint = self._checkpoint(checkpoint_id)
        if (
            checkpoint["item_id"] != item["item_id"]
            or checkpoint["run_id"] != run["run_id"]
            or checkpoint["branch"] != run["branch"]
        ):
            raise ProtocolError("checkpoint does not belong to this selfdev run")
        path = self._safe_worktree(run)
        self._git(path, "cat-file", "-e", checkpoint["head_sha"] + "^{commit}")
        self._git(path, "reset", "--hard", checkpoint["head_sha"])
        self._git(path, "clean", "-fd")
        actual_head = self._git(path, "rev-parse", "HEAD")
        dirty = self._git(path, "status", "--porcelain")
        if actual_head != checkpoint["head_sha"] or dirty:
            raise ConfigurationError("checkpoint revert verification failed")
        with self._lock:
            stored = self._state["checkpoints"][checkpoint["checkpoint_id"]]
            stored["revert_count"] = int(stored.get("revert_count") or 0) + 1
            stored["last_reverted_at"] = _now()
            self._persist()
            checkpoint = copy.deepcopy(stored)
        return {
            "checkpoint": checkpoint,
            "run_id": run["run_id"],
            "branch": run["branch"],
            "head_sha": actual_head,
            "worktree_clean": True,
        }
    def discard(self, item_id: str, *, reason: str) -> dict[str, Any]:
        reason = str(reason or "").strip()
        if not reason:
            raise ProtocolError("self-development discard requires a reason")
        item = self._item(item_id)
        run = self._bound_run(item)
        if run.get("state") in TERMINAL_RUN_STATES:
            raise ProtocolError(
                "self-development execution is already terminal; finish item explicitly"
            )
        if self._has_running_cognition(run):
            raise ProtocolError(
                "discard requires a safe cognition boundary; finish cognition first"
            )
        path = self._safe_worktree(run)
        self._git(path, "reset", "--hard", run["base_sha"])
        self._git(path, "clean", "-fd")
        if self._git(path, "rev-parse", "HEAD") != run["base_sha"]:
            raise ConfigurationError("discard reset did not restore run base")
        if self._git(path, "status", "--porcelain"):
            raise ConfigurationError("discard reset left worktree dirty")

        terminal_run = self.execution.cancel_run(
            run["run_id"],
            reason=f"SELFDEV_DISCARDED:{reason}",
        )
        self.execution.worktrees.remove_worktree(run["run_id"])
        finished = self.queue.finish(
            item["item_id"],
            state="DISCARDED",
            verification={
                "execution": {
                    "run_id": terminal_run["run_id"],
                    "state": terminal_run["state"],
                    "branch": terminal_run["branch"],
                    "restored_head_sha": run["base_sha"],
                    "promotion_authority": (
                        (terminal_run.get("authority") or {}).get(
                            "promotion_authority"
                        )
                    ),
                }
            },
            reason=reason,
        )
        return {
            "action": "DISCARDED",
            "item": finished,
            "run": terminal_run,
            "worktree_removed": not path.exists(),
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            ordered = [
                copy.deepcopy(self._state["checkpoints"][checkpoint_id])
                for checkpoint_id in self._state["order"]
            ]
            return {
                "schema": SCHEMA,
                "repository": copy.deepcopy(self._state["repository"]),
                "checkpoints": ordered,
                "count": len(ordered),
                "updated_at": self._state.get("updated_at"),
            }
