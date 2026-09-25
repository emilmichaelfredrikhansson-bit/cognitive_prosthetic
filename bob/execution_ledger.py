from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, ProtocolError


SCHEMA = "BOB_EXECUTION_LEDGER_V1"
DEFAULT_MAX_PARALLEL_RUNS_PER_REPOSITORY = 3
# Compatibility name for callers that have not yet adopted the explicit repo scope.
DEFAULT_MAX_PARALLEL_RUNS = DEFAULT_MAX_PARALLEL_RUNS_PER_REPOSITORY

TERMINAL_RUN_STATES = {"INTEGRATED", "FAILED", "CANCELLED"}
WORKER_SLOT_STATES = {"ACTIVE", "AWAITING_APPROVAL"}
LEASE_HOLDING_STATES = {
    "ACTIVE",
    "AWAITING_APPROVAL",
    "READY_FOR_INTEGRATION",
    "INTEGRATING",
}
RUN_STATES = TERMINAL_RUN_STATES | LEASE_HOLDING_STATES | {"QUEUED"}
COGNITION_TERMINAL_STATES = {"COMPLETE", "FAILED", "CANCELLED", "INTERRUPTED"}
COGNITION_STATES = COGNITION_TERMINAL_STATES | {"RUNNING"}

_SAFE_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _normalize_lease(value: str) -> str:
    lease = str(value or "").strip().replace("\\", "/")
    if not lease:
        raise ProtocolError("execution lease must not be empty")
    if lease.startswith("path:"):
        raw = lease[5:].strip().strip("/")
        parts = [part for part in raw.split("/") if part not in ("", ".")]
        if not parts or any(part == ".." for part in parts):
            raise ProtocolError(f"invalid path lease: {value!r}")
        return "path:" + "/".join(parts)
    if ":" not in lease:
        return "work:" + lease
    prefix, payload = lease.split(":", 1)
    prefix = prefix.strip().lower()
    payload = payload.strip()
    if prefix not in {"module", "work", "contract", "path"} or not payload:
        raise ProtocolError(f"invalid semantic lease: {value!r}")
    return f"{prefix}:{payload}"


def _leases_conflict(left: str, right: str) -> bool:
    if left == right:
        return True
    if left.startswith("path:") and right.startswith("path:"):
        a = left[5:].rstrip("/")
        b = right[5:].rstrip("/")
        return a.startswith(b + "/") or b.startswith(a + "/")
    return False


class ExecutionLedger:
    """Durable scheduler state for isolated Bob work.

    The ledger coordinates work; it never grants provider authority and it never
    merges a branch. Promotion remains a separate operator/canonical boundary.
    """

    def __init__(
        self,
        state_path: str | Path,
        *,
        repository_full_name: str,
        repository_id: int,
        repo_root: str | Path,
        canonical_ref: str,
        max_parallel_runs_per_repository: int = DEFAULT_MAX_PARALLEL_RUNS_PER_REPOSITORY,
    ):
        self.state_path = Path(state_path)
        self.repository_full_name = str(repository_full_name or "").strip().strip("/")
        self.repository_id = int(repository_id)
        self.repo_root = Path(repo_root).resolve()
        self.canonical_ref = str(canonical_ref or "").strip()
        if not self.repository_full_name or self.repository_id <= 0:
            raise ConfigurationError("execution ledger requires repository identity")
        if not self.canonical_ref:
            raise ConfigurationError("execution ledger requires canonical_ref")
        if not 1 <= int(max_parallel_runs_per_repository) <= 16:
            raise ConfigurationError(
                "max_parallel_runs_per_repository must be between 1 and 16"
            )
        self.max_parallel_runs = int(max_parallel_runs_per_repository)
        self._lock = threading.RLock()
        self._state = self._load()
        self._recover_interrupted_state()

    def _repository_identity(self) -> dict[str, Any]:
        return {
            "full_name": self.repository_full_name,
            "id": self.repository_id,
            "repo_root": str(self.repo_root),
            "canonical_ref": self.canonical_ref,
        }

    def _empty_state(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "repository": self._repository_identity(),
            "max_parallel_runs_per_repository": self.max_parallel_runs,
            "runs": {},
            "cognitions": {},
            "integration_queue": [],
            "updated_at": _now(),
        }

    def _load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._empty_state()
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"invalid execution ledger: {exc}") from exc
        if data.get("schema") != SCHEMA:
            raise ConfigurationError(
                f"execution ledger schema mismatch: {data.get('schema')!r}"
            )
        actual_identity = data.get("repository")
        expected_identity = self._repository_identity()
        if actual_identity != expected_identity:
            raise ConfigurationError(
                "execution ledger repository identity mismatch; refusing to share "
                f"ledger across repositories: expected={expected_identity!r} "
                f"actual={actual_identity!r}"
            )
        data.setdefault("runs", {})
        data.setdefault("cognitions", {})
        data.setdefault("integration_queue", [])
        data["max_parallel_runs_per_repository"] = self.max_parallel_runs
        data.pop("max_parallel_runs", None)
        return data

    def _persist(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state["updated_at"] = _now()
        payload = json.dumps(self._state, indent=2, sort_keys=True) + "\n"
        fd, temp_name = tempfile.mkstemp(
            prefix=self.state_path.name + ".",
            suffix=".tmp",
            dir=str(self.state_path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.state_path)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def _recover_interrupted_state(self) -> None:
        changed = False
        with self._lock:
            for cognition in self._state["cognitions"].values():
                if cognition.get("state") == "RUNNING":
                    cognition["state"] = "INTERRUPTED"
                    cognition["finished_at"] = _now()
                    cognition["error"] = "Bob runtime restarted before cognition completion"
                    changed = True
            for run in self._state["runs"].values():
                if run.get("state") == "INTEGRATING":
                    run["state"] = "READY_FOR_INTEGRATION"
                    run["blocked_reason"] = "RECOVERED_REVERIFY_REQUIRED"
                    run["integration_started_at"] = None
                    changed = True
            if changed:
                self._reconcile_queue_locked()
                self._persist()

    def _worker_slot_count_locked(self) -> int:
        return sum(
            1
            for run in self._state["runs"].values()
            if run.get("state") in WORKER_SLOT_STATES
        )

    def _lease_conflicts_locked(
        self,
        leases: list[str],
        *,
        exclude_run_id: str | None = None,
    ) -> list[str]:
        conflicts: list[str] = []
        for other_id, other in self._state["runs"].items():
            if other_id == exclude_run_id:
                continue
            if other.get("state") not in LEASE_HOLDING_STATES:
                continue
            other_leases = other.get("leases") or []
            if any(
                _leases_conflict(left, right)
                for left in leases
                for right in other_leases
            ):
                conflicts.append(other_id)
        return sorted(conflicts)

    def _unmet_dependencies_locked(self, run: dict[str, Any]) -> list[str]:
        unmet = []
        for dependency in run.get("depends_on") or []:
            other = self._state["runs"].get(dependency)
            if other is None or other.get("state") != "INTEGRATED":
                unmet.append(dependency)
        return unmet

    def _eligibility_locked(self, run_id: str) -> tuple[bool, str | None]:
        run = self._require_run_locked(run_id)
        unmet = self._unmet_dependencies_locked(run)
        if unmet:
            return False, "DEPENDENCY:" + ",".join(unmet)
        conflicts = self._lease_conflicts_locked(
            list(run.get("leases") or []),
            exclude_run_id=run_id,
        )
        if conflicts:
            return False, "SCOPE_CONFLICT:" + ",".join(conflicts)
        if self._worker_slot_count_locked() >= self.max_parallel_runs:
            return False, "CAPACITY"
        return True, None

    def _reconcile_queue_locked(self) -> list[str]:
        activated: list[str] = []
        queued = sorted(
            (
                run
                for run in self._state["runs"].values()
                if run.get("state") == "QUEUED"
            ),
            key=lambda item: (item.get("created_at", ""), item["run_id"]),
        )
        for run in queued:
            eligible, reason = self._eligibility_locked(run["run_id"])
            run["blocked_reason"] = reason
            if not eligible:
                continue
            run["state"] = "ACTIVE"
            run["activated_at"] = _now()
            run["blocked_reason"] = None
            activated.append(run["run_id"])
        return activated

    def reconcile(self) -> list[str]:
        with self._lock:
            activated = self._reconcile_queue_locked()
            if activated:
                self._persist()
            return activated

    def create_run(
        self,
        *,
        goal: str,
        workspace: str,
        base_ref: str,
        base_sha: str,
        branch: str,
        worktree_path: str,
        leases: list[str],
        depends_on: list[str] | None = None,
        lane: str = "interactive",
        authority: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        goal = str(goal or "").strip()
        workspace = str(workspace or "").strip()
        base_ref = str(base_ref or "").strip()
        base_sha = str(base_sha or "").strip()
        branch = str(branch or "").strip()
        if not goal or not workspace or not base_ref or not base_sha or not branch:
            raise ProtocolError("execution run requires goal/workspace/base_ref/base_sha/branch")
        if not _SAFE_BRANCH.fullmatch(branch) or ".." in branch or branch.startswith("/"):
            raise ProtocolError(f"unsafe run branch: {branch!r}")
        normalized_leases = sorted({_normalize_lease(item) for item in leases})
        if not normalized_leases:
            raise ProtocolError("execution run requires at least one semantic lease")
        dependencies = list(dict.fromkeys(str(x) for x in (depends_on or [])))
        run_id = run_id or _new_id("run")

        with self._lock:
            if run_id in self._state["runs"]:
                raise ProtocolError(f"duplicate run_id: {run_id}")
            for dependency in dependencies:
                if dependency == run_id:
                    raise ProtocolError("run cannot depend on itself")
                if dependency not in self._state["runs"]:
                    raise ProtocolError(f"unknown dependency run: {dependency}")

            record = {
                "run_id": run_id,
                "goal": goal,
                "workspace": workspace,
                "lane": str(lane or "interactive"),
                "state": "QUEUED",
                "blocked_reason": None,
                "base_ref": base_ref,
                "base_sha": base_sha,
                "branch": branch,
                "worktree_path": str(worktree_path),
                "leases": normalized_leases,
                "depends_on": dependencies,
                "authority": deepcopy(authority or {}),
                "created_at": _now(),
                "activated_at": None,
                "ready_at": None,
                "integration_started_at": None,
                "finished_at": None,
                "verified_base_sha": None,
                "verified_head_sha": None,
                "verification": None,
                "integrated_canonical_sha": None,
                "cognition_ids": [],
            }
            self._state["runs"][run_id] = record
            self._reconcile_queue_locked()
            self._persist()
            return deepcopy(self._state["runs"][run_id])

    def _require_run_locked(self, run_id: str) -> dict[str, Any]:
        run = self._state["runs"].get(str(run_id))
        if run is None:
            raise ProtocolError(f"unknown execution run: {run_id}")
        return run

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._require_run_locked(run_id))

    def begin_cognition(
        self,
        run_id: str,
        *,
        purpose: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        purpose = str(purpose or "").strip()
        if not purpose:
            raise ProtocolError("cognition purpose must not be empty")
        with self._lock:
            run = self._require_run_locked(run_id)
            if run["state"] != "ACTIVE":
                raise ProtocolError(
                    f"run {run_id} must be ACTIVE before cognition; state={run['state']}"
                )
            for cognition_id in run.get("cognition_ids") or []:
                cognition = self._state["cognitions"].get(cognition_id)
                if cognition and cognition.get("state") == "RUNNING":
                    raise ProtocolError(
                        f"run {run_id} already has running cognition {cognition_id}"
                    )
            cognition_id = _new_id("cog")
            request_id = str(request_id or _new_id("req"))
            cognition = {
                "cognition_id": cognition_id,
                "request_id": request_id,
                "run_id": run_id,
                "purpose": purpose,
                "state": "RUNNING",
                "started_at": _now(),
                "finished_at": None,
                "summary": None,
                "error": None,
            }
            self._state["cognitions"][cognition_id] = cognition
            run["cognition_ids"].append(cognition_id)
            self._persist()
            return deepcopy(cognition)

    def finish_cognition(
        self,
        cognition_id: str,
        *,
        success: bool,
        summary: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            cognition = self._state["cognitions"].get(str(cognition_id))
            if cognition is None:
                raise ProtocolError(f"unknown cognition: {cognition_id}")
            if cognition.get("state") != "RUNNING":
                raise ProtocolError(
                    f"cognition {cognition_id} is not RUNNING: {cognition.get('state')}"
                )
            cognition["state"] = "COMPLETE" if success else "FAILED"
            cognition["finished_at"] = _now()
            cognition["summary"] = None if summary is None else str(summary)
            cognition["error"] = None if error is None else str(error)
            self._persist()
            return deepcopy(cognition)

    def mark_awaiting_approval(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            run = self._require_run_locked(run_id)
            if run["state"] != "ACTIVE":
                raise ProtocolError("only ACTIVE runs can await approval")
            run["state"] = "AWAITING_APPROVAL"
            self._persist()
            return deepcopy(run)

    def resume_after_approval(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            run = self._require_run_locked(run_id)
            if run["state"] != "AWAITING_APPROVAL":
                raise ProtocolError("run is not awaiting approval")
            run["state"] = "ACTIVE"
            self._persist()
            return deepcopy(run)

    def mark_ready_for_integration(
        self,
        run_id: str,
        *,
        verified_base_sha: str,
        verified_head_sha: str,
        verification: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            run = self._require_run_locked(run_id)
            if run["state"] not in {"ACTIVE", "AWAITING_APPROVAL"}:
                raise ProtocolError(
                    f"run must be active before integration readiness: {run['state']}"
                )
            for cognition_id in run.get("cognition_ids") or []:
                cognition = self._state["cognitions"].get(cognition_id)
                if cognition and cognition.get("state") == "RUNNING":
                    raise ProtocolError("run cannot enter integration queue with running cognition")
            run["state"] = "READY_FOR_INTEGRATION"
            run["ready_at"] = _now()
            run["verified_base_sha"] = str(verified_base_sha)
            run["verified_head_sha"] = str(verified_head_sha)
            run["verification"] = deepcopy(verification)
            run["blocked_reason"] = None
            if run_id not in self._state["integration_queue"]:
                self._state["integration_queue"].append(run_id)
            self._reconcile_queue_locked()
            self._persist()
            return deepcopy(run)

    def record_rebase_verification(
        self,
        run_id: str,
        *,
        verified_base_sha: str,
        verified_head_sha: str,
        verification: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            run = self._require_run_locked(run_id)
            if run["state"] != "READY_FOR_INTEGRATION":
                raise ProtocolError("only READY_FOR_INTEGRATION runs can be reverified")
            run["verified_base_sha"] = str(verified_base_sha)
            run["verified_head_sha"] = str(verified_head_sha)
            run["verification"] = deepcopy(verification)
            run["blocked_reason"] = None
            self._persist()
            return deepcopy(run)

    def integration_plan(self, canonical_sha: str) -> dict[str, Any]:
        canonical_sha = str(canonical_sha or "").strip()
        if not canonical_sha:
            raise ProtocolError("canonical_sha is required")
        with self._lock:
            active = [
                run["run_id"]
                for run in self._state["runs"].values()
                if run.get("state") == "INTEGRATING"
            ]
            entries = []
            for index, run_id in enumerate(self._state["integration_queue"]):
                run = self._state["runs"].get(run_id)
                if run is None or run.get("state") not in {
                    "READY_FOR_INTEGRATION",
                    "INTEGRATING",
                }:
                    continue
                action = (
                    "READY_TO_INTEGRATE"
                    if run.get("verified_base_sha") == canonical_sha
                    else "REBASE_REVERIFY_REQUIRED"
                )
                if index > 0:
                    action = "WAIT_FOR_EARLIER_INTEGRATION"
                entries.append({
                    "position": index + 1,
                    "run_id": run_id,
                    "branch": run["branch"],
                    "verified_base_sha": run.get("verified_base_sha"),
                    "verified_head_sha": run.get("verified_head_sha"),
                    "action": action,
                })
            return {
                "canonical_sha": canonical_sha,
                "integrating": active[0] if active else None,
                "queue": entries,
            }

    def begin_integration(self, run_id: str, *, canonical_sha: str) -> dict[str, Any]:
        with self._lock:
            run = self._require_run_locked(run_id)
            queue_ids = [
                item
                for item in self._state["integration_queue"]
                if self._state["runs"].get(item, {}).get("state")
                in {"READY_FOR_INTEGRATION", "INTEGRATING"}
            ]
            if not queue_ids or queue_ids[0] != run_id:
                raise ProtocolError("integration is serialized; run is not queue head")
            if any(
                other.get("state") == "INTEGRATING"
                for other_id, other in self._state["runs"].items()
                if other_id != run_id
            ):
                raise ProtocolError("another run already owns the integration gate")
            if run["state"] != "READY_FOR_INTEGRATION":
                raise ProtocolError(f"run is not ready for integration: {run['state']}")
            if run.get("verified_base_sha") != str(canonical_sha):
                raise ProtocolError(
                    "integration candidate is stale; rebase/re-ground and reverify "
                    "against current canonical sha before integration"
                )
            run["state"] = "INTEGRATING"
            run["integration_started_at"] = _now()
            self._persist()
            return deepcopy(run)

    def complete_integration(
        self,
        run_id: str,
        *,
        canonical_sha: str,
    ) -> dict[str, Any]:
        with self._lock:
            run = self._require_run_locked(run_id)
            if run["state"] != "INTEGRATING":
                raise ProtocolError("run does not own the integration gate")
            run["state"] = "INTEGRATED"
            run["integrated_canonical_sha"] = str(canonical_sha)
            run["finished_at"] = _now()
            self._state["integration_queue"] = [
                item for item in self._state["integration_queue"] if item != run_id
            ]
            self._reconcile_queue_locked()
            self._persist()
            return deepcopy(run)

    def fail_run(self, run_id: str, *, error: str) -> dict[str, Any]:
        return self._finish_run(run_id, state="FAILED", reason=error)

    def cancel_run(self, run_id: str, *, reason: str = "cancelled") -> dict[str, Any]:
        return self._finish_run(run_id, state="CANCELLED", reason=reason)

    def _finish_run(self, run_id: str, *, state: str, reason: str) -> dict[str, Any]:
        if state not in {"FAILED", "CANCELLED"}:
            raise ProtocolError(f"unsupported terminal state: {state}")
        with self._lock:
            run = self._require_run_locked(run_id)
            if run["state"] == "INTEGRATED":
                raise ProtocolError("integrated run cannot be cancelled/failed")
            run["state"] = state
            run["blocked_reason"] = str(reason)
            run["finished_at"] = _now()
            self._state["integration_queue"] = [
                item for item in self._state["integration_queue"] if item != run_id
            ]
            for cognition_id in run.get("cognition_ids") or []:
                cognition = self._state["cognitions"].get(cognition_id)
                if cognition and cognition.get("state") == "RUNNING":
                    cognition["state"] = "CANCELLED"
                    cognition["finished_at"] = _now()
                    cognition["error"] = str(reason)
            self._reconcile_queue_locked()
            self._persist()
            return deepcopy(run)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            runs = deepcopy(self._state["runs"])
            active = sorted(
                run_id
                for run_id, run in runs.items()
                if run.get("state") in WORKER_SLOT_STATES
            )
            return {
                "schema": SCHEMA,
                "repository": deepcopy(self._state["repository"]),
                "max_parallel_runs_per_repository": self.max_parallel_runs,
                "active_run_count": len(active),
                "active_run_ids": active,
                "integration_queue": list(self._state["integration_queue"]),
                "runs": runs,
                "cognitions": deepcopy(self._state["cognitions"]),
                "updated_at": self._state.get("updated_at"),
            }
