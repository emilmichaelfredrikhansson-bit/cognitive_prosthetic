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
from .execution_ledger import PARKED_RUN_STATE, TERMINAL_RUN_STATES
from .work_campaign_queue import (
    ADMITTED,
    STOP_REQUESTED,
    TERMINAL_ITEM_STATES,
    WorkCampaignQueue,
)
from .work_campaigns import (
    CANCELLED as CAMPAIGN_CANCELLED,
    COMPLETED as CAMPAIGN_COMPLETED,
    DEADLINE_REACHED,
    RUNNING,
    WorkCampaignManager,
)
from .worktree_coordination import ExecutionCoordinator, RepositoryCoordinatorRegistry


SCHEMA = "BOB_WORK_CAMPAIGN_WORKER_V1"
CHECKPOINTABLE_RUN_STATES = {"ACTIVE", PARKED_RUN_STATE}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _checkpoint_id() -> str:
    return f"campaign-checkpoint-{uuid.uuid4().hex[:12]}"


class WorkCampaignWorker:
    """Durable worker control above campaign queue and existing coordinators.

    This module selects/advises work, checkpoints safe boundaries and parks/resumes
    low-priority campaign runs. It never creates an alternative execution path and
    never merges, pushes, promotes or performs cognition by itself.
    """

    def __init__(
        self,
        path: str | Path,
        campaigns: WorkCampaignManager,
        queue: WorkCampaignQueue,
        executions: RepositoryCoordinatorRegistry,
    ):
        self.path = Path(path)
        self.campaigns = campaigns
        self.queue = queue
        self.executions = executions
        self._lock = threading.RLock()
        self._state = self._load()

    def _empty(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "campaigns": {},
            "checkpoints": {},
            "preemptions": {},
            "updated_at": _now(),
        }

    def _validate(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise ConfigurationError("work campaign worker schema mismatch")
        for key in ("campaigns", "checkpoints", "preemptions"):
            if not isinstance(data.get(key), dict):
                raise ConfigurationError(
                    f"work campaign worker {key} state must be an object"
                )
        return data

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"invalid work campaign worker store: {self.path}"
            ) from exc
        return self._validate(data)

    @staticmethod
    def _write_fsync(path: Path, payload: str) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
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
                        "Windows campaign worker persistence verification failed"
                    )
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def _campaign(self, campaign_id: str) -> dict[str, Any]:
        matches = [
            campaign
            for campaign in self.campaigns.snapshot()["campaigns"]
            if campaign["campaign_id"] == str(campaign_id)
        ]
        if len(matches) != 1:
            raise ProtocolError(f"unknown work campaign: {campaign_id}")
        return matches[0]

    def _item(self, item_id: str) -> dict[str, Any]:
        matches = [
            item
            for item in self.queue.snapshot()["items"]
            if item["item_id"] == str(item_id)
        ]
        if len(matches) != 1:
            raise ProtocolError(f"unknown campaign work item: {item_id}")
        return matches[0]

    def _execution(self, item: dict[str, Any]) -> ExecutionCoordinator:
        return self.executions.coordinator_for_workspace(item["workspace"])

    def _bound_run(self, item: dict[str, Any]) -> dict[str, Any]:
        run_id = str(item.get("run_id") or "").strip()
        if not run_id:
            raise ProtocolError("campaign work item has no bound execution run")
        execution = self._execution(item)
        run = execution.ledger.get_run(run_id)
        authority = run.get("authority") or {}
        if (
            run.get("lane") != "campaign"
            or authority.get("campaign_id") != item["campaign_id"]
            or authority.get("work_item_id") != item["item_id"]
            or authority.get("promotion_authority") != "NONE"
            or authority.get("auto_merge") is not False
        ):
            raise ProtocolError("campaign worker execution authority mismatch")
        return run

    def _has_running_cognition(
        self,
        execution: ExecutionCoordinator,
        run: dict[str, Any],
    ) -> bool:
        snapshot = execution.ledger.snapshot()
        return any(
            snapshot["cognitions"].get(cognition_id, {}).get("state") == "RUNNING"
            for cognition_id in (run.get("cognition_ids") or [])
        )

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

    def _safe_worktree(
        self,
        execution: ExecutionCoordinator,
        run: dict[str, Any],
    ) -> Path:
        expected = execution.worktrees.worktree_path(run["run_id"]).resolve()
        recorded = Path(run["worktree_path"]).resolve()
        if recorded != expected:
            raise ProtocolError("campaign run worktree path does not match coordinator")
        path = execution.worktrees.ensure_worktree(
            run_id=run["run_id"],
            branch=run["branch"],
            base_sha=run["base_sha"],
        ).resolve()
        if path != expected:
            raise ProtocolError("campaign worktree escaped expected path")
        return path

    def checkpoint(
        self,
        item_id: str,
        *,
        label: str | None = None,
        verification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        item = self._item(item_id)
        if item["state"] not in {ADMITTED, STOP_REQUESTED}:
            raise ProtocolError(
                f"campaign work is not checkpointable from {item['state']}"
            )
        execution = self._execution(item)
        run = self._bound_run(item)
        if run.get("state") not in CHECKPOINTABLE_RUN_STATES:
            raise ProtocolError(
                f"campaign run is not checkpointable: {run.get('state')}"
            )
        if self._has_running_cognition(execution, run):
            raise ProtocolError(
                "campaign checkpoint requires a safe cognition boundary"
            )
        path = self._safe_worktree(execution, run)
        if self._git(path, "status", "--porcelain"):
            raise ProtocolError(
                "campaign checkpoint requires a clean worktree; commit or discard first"
            )
        actual_branch = self._git(path, "branch", "--show-current")
        if actual_branch != run["branch"]:
            raise ProtocolError("campaign checkpoint worktree branch mismatch")
        head_sha = self._git(path, "rev-parse", "HEAD")
        if head_sha != execution.worktrees.branch_head(run["branch"]):
            raise ProtocolError("campaign checkpoint branch/worktree head mismatch")
        checkpoint = {
            "checkpoint_id": _checkpoint_id(),
            "campaign_id": item["campaign_id"],
            "item_id": item["item_id"],
            "workspace": item["workspace"],
            "run_id": run["run_id"],
            "branch": run["branch"],
            "head_sha": head_sha,
            "base_sha": run["base_sha"],
            "label": None if label in (None, "") else str(label),
            "verification": copy.deepcopy(verification or {}),
            "created_at": _now(),
        }
        with self._lock:
            prior = self._state["checkpoints"].get(item["item_id"]) or {}
            checkpoint["checkpoint_count"] = int(prior.get("checkpoint_count") or 0) + 1
            self._state["checkpoints"][item["item_id"]] = checkpoint
            self._persist()
        return copy.deepcopy(checkpoint)

    def park(
        self,
        item_id: str,
        *,
        reason: str,
        interactive_run_id: str | None = None,
    ) -> dict[str, Any]:
        reason = str(reason or "").strip()
        if not reason:
            raise ProtocolError("campaign parking requires a reason")
        item = self._item(item_id)
        execution = self._execution(item)
        run = self._bound_run(item)
        if run["state"] == PARKED_RUN_STATE:
            checkpoint = self._state["checkpoints"].get(item["item_id"])
            if not checkpoint or checkpoint.get("run_id") != run["run_id"]:
                raise ProtocolError("parked campaign run lacks durable checkpoint")
            return {
                "action": "ALREADY_PARKED",
                "item": item,
                "run": run,
                "checkpoint": copy.deepcopy(checkpoint),
            }
        checkpoint = self.checkpoint(
            item["item_id"],
            label=(
                f"interactive-preemption:{interactive_run_id}"
                if interactive_run_id
                else "campaign-safe-stop"
            ),
            verification={"reason": reason},
        )
        run = execution.park_campaign_run(
            run["run_id"],
            reason=reason,
            preempted_by_run_id=interactive_run_id,
        )
        if interactive_run_id:
            with self._lock:
                entries = self._state["preemptions"].setdefault(
                    str(interactive_run_id), []
                )
                if not any(entry["item_id"] == item["item_id"] for entry in entries):
                    entries.append(
                        {
                            "campaign_id": item["campaign_id"],
                            "item_id": item["item_id"],
                            "workspace": item["workspace"],
                            "run_id": run["run_id"],
                            "checkpoint_id": checkpoint["checkpoint_id"],
                            "head_sha": checkpoint["head_sha"],
                            "parked_at": _now(),
                            "resumed_at": None,
                            "held_reason": None,
                        }
                    )
                self._persist()
        return {
            "action": "PARKED",
            "item": item,
            "run": run,
            "checkpoint": checkpoint,
        }

    def resume(self, item_id: str) -> dict[str, Any]:
        item = self._item(item_id)
        campaign = self._campaign(item["campaign_id"])
        if campaign["state"] != RUNNING:
            raise ProtocolError(
                f"campaign work cannot resume while campaign is {campaign['state']}"
            )
        execution = self._execution(item)
        run = self._bound_run(item)
        if run["state"] != PARKED_RUN_STATE:
            raise ProtocolError("campaign work has no parked execution run")
        run = execution.resume_parked_run(run["run_id"])
        return {"action": "RESUMED", "item": item, "run": run}

    @staticmethod
    def _blocker_ids(run: dict[str, Any]) -> list[str] | None:
        reason = str(run.get("blocked_reason") or "")
        if reason.startswith("SCOPE_CONFLICT:"):
            return [
                value.strip()
                for value in reason.split(":", 1)[1].split(",")
                if value.strip()
            ]
        if reason == "CAPACITY":
            return []
        return None

    def _campaign_preemption_candidate(
        self,
        execution: ExecutionCoordinator,
        interactive: dict[str, Any],
    ) -> dict[str, Any] | None:
        blocker_ids = self._blocker_ids(interactive)
        if blocker_ids is None:
            return None
        snapshot = execution.ledger.snapshot()
        runs = snapshot["runs"]
        if blocker_ids:
            blockers = [runs.get(run_id) for run_id in blocker_ids]
            if not blockers or any(run is None for run in blockers):
                return None
            if any(run.get("lane") != "campaign" for run in blockers):
                return None
            active = [run for run in blockers if run.get("state") == "ACTIVE"]
            return active[0] if active else None
        candidates = [
            run
            for run in runs.values()
            if run.get("state") == "ACTIVE" and run.get("lane") == "campaign"
        ]
        candidates.sort(
            key=lambda run: (
                str(run.get("activated_at") or run.get("created_at") or ""),
                run["run_id"],
            ),
            reverse=True,
        )
        return candidates[0] if candidates else None

    def preempt_for_interactive(
        self,
        execution: ExecutionCoordinator,
        interactive_run_id: str,
    ) -> dict[str, Any]:
        interactive = execution.ledger.get_run(interactive_run_id)
        if interactive.get("lane") != "interactive":
            raise ProtocolError("campaign preemption requires an interactive run")
        if interactive["state"] != "QUEUED":
            return {
                "interactive_run_id": interactive_run_id,
                "preempted": [],
                "status": "NOT_NEEDED",
            }
        preempted: list[dict[str, Any]] = []
        seen: set[str] = set()
        max_attempts = len(execution.ledger.snapshot()["runs"]) + 1
        for _ in range(max_attempts):
            interactive = execution.ledger.get_run(interactive_run_id)
            if interactive["state"] != "QUEUED":
                break
            candidate = self._campaign_preemption_candidate(execution, interactive)
            if candidate is None or candidate["run_id"] in seen:
                break
            seen.add(candidate["run_id"])
            authority = candidate.get("authority") or {}
            item_id = str(authority.get("work_item_id") or "")
            if not item_id:
                break
            try:
                parked = self.park(
                    item_id,
                    reason=f"interactive:{interactive_run_id}",
                    interactive_run_id=interactive_run_id,
                )
            except ProtocolError:
                break
            preempted.append(
                {
                    "campaign_id": authority.get("campaign_id"),
                    "item_id": item_id,
                    "run_id": candidate["run_id"],
                    "checkpoint_id": parked["checkpoint"]["checkpoint_id"],
                }
            )
        interactive = execution.ledger.get_run(interactive_run_id)
        return {
            "interactive_run_id": interactive_run_id,
            "interactive_state": interactive["state"],
            "preempted": preempted,
            "status": (
                "PREEMPTED_CAMPAIGN"
                if preempted
                else (
                    "NOT_NEEDED"
                    if interactive["state"] != "QUEUED"
                    else "NO_SAFE_CAMPAIGN_PREEMPTION"
                )
            ),
        }

    def resume_after_interactive(self, interactive_run_id: str) -> dict[str, Any]:
        execution = self.executions.coordinator_for_run(interactive_run_id)
        interactive = execution.ledger.get_run(interactive_run_id)
        if interactive.get("lane") != "interactive":
            raise ProtocolError("preemption release requires an interactive run")
        if interactive.get("state") not in TERMINAL_RUN_STATES:
            raise ProtocolError(
                "campaign work may resume only after interactive run is terminal"
            )
        with self._lock:
            records = copy.deepcopy(
                self._state["preemptions"].get(str(interactive_run_id), [])
            )
        resumed = []
        held = []
        changed = False
        for record in records:
            if record.get("resumed_at"):
                continue
            item = self._item(record["item_id"])
            campaign = self._campaign(item["campaign_id"])
            campaign_execution = self._execution(item)
            run = self._bound_run(item)
            if run["state"] != PARKED_RUN_STATE:
                record["held_reason"] = f"RUN_STATE:{run['state']}"
                held.append(record["item_id"])
                changed = True
                continue
            if campaign["state"] != RUNNING:
                record["held_reason"] = f"CAMPAIGN_STATE:{campaign['state']}"
                held.append(record["item_id"])
                changed = True
                continue
            resumed_run = campaign_execution.resume_parked_run(run["run_id"])
            record["resumed_at"] = _now()
            record["held_reason"] = None
            resumed.append(
                {
                    "item_id": record["item_id"],
                    "run_id": resumed_run["run_id"],
                    "state": resumed_run["state"],
                }
            )
            changed = True
        if changed:
            by_item = {record["item_id"]: record for record in records}
            with self._lock:
                stored = self._state["preemptions"].get(
                    str(interactive_run_id), []
                )
                for index, record in enumerate(stored):
                    updated = by_item.get(record["item_id"])
                    if updated is not None:
                        stored[index] = updated
                self._persist()
        return {
            "interactive_run_id": interactive_run_id,
            "resumed": resumed,
            "held_item_ids": held,
            "count": len(resumed),
        }

    def _ready_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        if item["state"] != ADMITTED or not item.get("run_id"):
            return None
        run = self._bound_run(item)
        if run["state"] != "ACTIVE":
            return None
        return {
            "item_id": item["item_id"],
            "workspace": item["workspace"],
            "goal": item["goal"],
            "run_id": run["run_id"],
            "branch": run["branch"],
            "worktree_path": run["worktree_path"],
            "base_sha": run["base_sha"],
        }

    def cycle(
        self,
        campaign_id: str,
        *,
        max_admissions: int = 3,
    ) -> dict[str, Any]:
        tick = self.queue.tick(campaign_id, max_admissions=max_admissions)
        safe_stopped = []
        waiting_safe_boundary = []
        for item in tick["items"]:
            if item["state"] != STOP_REQUESTED or not item.get("run_id"):
                continue
            run = self._bound_run(item)
            if run["state"] == PARKED_RUN_STATE:
                safe_stopped.append(item["item_id"])
                continue
            if run["state"] != "ACTIVE":
                waiting_safe_boundary.append(item["item_id"])
                continue
            try:
                parked = self.park(
                    item["item_id"],
                    reason=f"campaign-stop:{campaign_id}",
                )
            except (ProtocolError, ConfigurationError):
                waiting_safe_boundary.append(item["item_id"])
                continue
            safe_stopped.append(parked["item"]["item_id"])

        snapshot = self.queue.snapshot(campaign_id)
        ready = [
            result
            for item in snapshot["items"]
            if (result := self._ready_item(item)) is not None
        ]
        parked = []
        for item in snapshot["items"]:
            if not item.get("run_id"):
                continue
            run = self._bound_run(item)
            if run["state"] == PARKED_RUN_STATE:
                checkpoint = self._state["checkpoints"].get(item["item_id"])
                parked.append(
                    {
                        "item_id": item["item_id"],
                        "workspace": item["workspace"],
                        "run_id": run["run_id"],
                        "branch": run["branch"],
                        "checkpoint": copy.deepcopy(checkpoint),
                    }
                )

        campaign = self._campaign(campaign_id)
        completed = False
        if (
            snapshot["items"]
            and campaign["state"] in {RUNNING, DEADLINE_REACHED}
            and all(item["state"] in TERMINAL_ITEM_STATES for item in snapshot["items"])
        ):
            run_states = self.campaigns.run_states(campaign_id)
            if not run_states["nonterminal_run_ids"]:
                campaign = self.campaigns.complete(campaign_id)["campaign"]
                completed = True

        summary = {
            "campaign_state": campaign["state"],
            "counts": snapshot["counts"],
            "ready_item_ids": [item["item_id"] for item in ready],
            "parked_item_ids": [item["item_id"] for item in parked],
            "safe_stopped_item_ids": safe_stopped,
            "waiting_safe_boundary_item_ids": waiting_safe_boundary,
            "admitted_item_ids": list(tick["admitted_item_ids"]),
            "completed": completed,
        }
        with self._lock:
            worker = self._state["campaigns"].setdefault(
                campaign_id,
                {
                    "campaign_id": campaign_id,
                    "cycle_count": 0,
                    "last_cycle_at": None,
                    "last_summary": None,
                },
            )
            worker["cycle_count"] = int(worker.get("cycle_count") or 0) + 1
            worker["last_cycle_at"] = _now()
            worker["last_summary"] = copy.deepcopy(summary)
            self._persist()
        return {
            "campaign": campaign,
            "summary": summary,
            "ready": ready,
            "parked": parked,
        }

    def digest(self, campaign_id: str) -> dict[str, Any]:
        queue_digest = self.queue.digest(campaign_id)
        snapshot = self.queue.snapshot(campaign_id)
        paused_candidates = []
        for item in snapshot["items"]:
            if not item.get("run_id"):
                continue
            run = self._bound_run(item)
            if run["state"] != PARKED_RUN_STATE:
                continue
            checkpoint = self._state["checkpoints"].get(item["item_id"])
            paused_candidates.append(
                {
                    "item_id": item["item_id"],
                    "workspace": item["workspace"],
                    "goal": item["goal"],
                    "run_id": run["run_id"],
                    "branch": run["branch"],
                    "head_sha": None if not checkpoint else checkpoint.get("head_sha"),
                    "checkpoint_id": (
                        None if not checkpoint else checkpoint.get("checkpoint_id")
                    ),
                    "promotion_authority": (
                        (run.get("authority") or {}).get("promotion_authority")
                    ),
                    "auto_merge": (run.get("authority") or {}).get("auto_merge"),
                }
            )
        with self._lock:
            worker = copy.deepcopy(self._state["campaigns"].get(campaign_id))
        return {
            **queue_digest,
            "worker": worker,
            "paused_candidates": paused_candidates,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)
