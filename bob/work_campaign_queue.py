from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, ProtocolError
from .execution_ledger import TERMINAL_RUN_STATES
from .work_campaigns import (
    CANCELLED as CAMPAIGN_CANCELLED,
    COMPLETED as CAMPAIGN_COMPLETED,
    DEADLINE_REACHED,
    PLANNED,
    RUNNING,
    WorkCampaignManager,
)
from .worktree_coordination import RepositoryCoordinatorRegistry


SCHEMA = "BOB_WORK_CAMPAIGN_QUEUE_V1"
QUEUED = "QUEUED"
BLOCKED = "BLOCKED"
ADMITTED = "ADMITTED"
STOP_REQUESTED = "STOP_REQUESTED"
SUCCEEDED = "SUCCEEDED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"
SKIPPED_DEADLINE = "SKIPPED_DEADLINE"
ITEM_STATES = {
    QUEUED, BLOCKED, ADMITTED, STOP_REQUESTED,
    SUCCEEDED, FAILED, CANCELLED, SKIPPED_DEADLINE,
}
TERMINAL_ITEM_STATES = {SUCCEEDED, FAILED, CANCELLED, SKIPPED_DEADLINE}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"campaign-work-{uuid.uuid4().hex[:12]}"


class WorkCampaignQueue:
    """Durable campaign backlog that admits work through existing coordinators."""

    def __init__(
        self,
        path: str | Path,
        campaigns: WorkCampaignManager,
        executions: RepositoryCoordinatorRegistry,
    ):
        self.path = Path(path)
        self.campaigns = campaigns
        self.executions = executions
        self._lock = threading.RLock()
        self._state = self._load()

    def _empty(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "items": {},
            "order": [],
            "updated_at": _now(),
        }

    def _validate(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise ConfigurationError("work campaign queue schema mismatch")
        items = data.get("items")
        order = data.get("order")
        if not isinstance(items, dict) or not isinstance(order, list):
            raise ConfigurationError("work campaign queue requires items/order")
        if len(order) != len(set(order)) or set(order) != set(items):
            raise ConfigurationError("work campaign queue order/state mismatch")
        for item_id, item in items.items():
            if item.get("item_id") != item_id:
                raise ConfigurationError("campaign work key/id mismatch")
            if item.get("state") not in ITEM_STATES:
                raise ConfigurationError("invalid campaign work state")
            if not item.get("campaign_id") or not item.get("workspace"):
                raise ConfigurationError("campaign work requires campaign/workspace")
            if not isinstance(item.get("leases"), list) or not item["leases"]:
                raise ConfigurationError("campaign work requires leases")
            if not isinstance(item.get("depends_on"), list):
                raise ConfigurationError("campaign work dependencies must be an array")
        return data

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"invalid work campaign queue store: {self.path}"
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
                        "Windows campaign queue persistence verification failed"
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

    def _require_locked(self, item_id: str) -> dict[str, Any]:
        item = self._state["items"].get(str(item_id))
        if item is None:
            raise ProtocolError(f"unknown campaign work item: {item_id}")
        return item

    def _target_workspace(self, campaign: dict[str, Any], workspace: str) -> str:
        matches = [
            target["workspace"]
            for target in campaign["targets"]
            if target["workspace"].casefold() == str(workspace).casefold()
        ]
        if len(matches) != 1:
            raise ProtocolError(
                f"workspace {workspace} is not a campaign target"
            )
        return matches[0]

    def enqueue(
        self,
        campaign_id: str,
        *,
        workspace: str,
        goal: str,
        base_ref: str,
        leases: list[str],
        depends_on: list[str] | None = None,
        item_id: str | None = None,
    ) -> dict[str, Any]:
        campaign = self._campaign(campaign_id)
        if campaign["state"] not in {PLANNED, RUNNING}:
            raise ProtocolError(
                f"campaign does not accept backlog work: {campaign['state']}"
            )
        workspace = self._target_workspace(campaign, workspace)
        goal = str(goal or "").strip()
        base_ref = str(base_ref or "").strip()
        normalized_leases = sorted({
            str(value or "").strip() for value in leases if str(value or "").strip()
        })
        if not goal or not base_ref or not normalized_leases:
            raise ProtocolError("campaign work requires goal/base_ref/leases")
        dependencies = list(dict.fromkeys(
            str(value).strip() for value in (depends_on or []) if str(value).strip()
        ))
        item_id = str(item_id or _new_id()).strip()
        now = _now()
        with self._lock:
            if item_id in self._state["items"]:
                raise ProtocolError(f"duplicate campaign work item: {item_id}")
            for dependency in dependencies:
                other = self._state["items"].get(dependency)
                if other is None or other.get("campaign_id") != campaign_id:
                    raise ProtocolError(
                        f"campaign work dependency missing or cross-campaign: {dependency}"
                    )
            record = {
                "item_id": item_id,
                "campaign_id": str(campaign_id),
                "workspace": workspace,
                "goal": goal,
                "base_ref": base_ref,
                "leases": normalized_leases,
                "depends_on": dependencies,
                "state": QUEUED,
                "blocked_reason": None,
                "run_id": None,
                "attempt_count": 0,
                "last_execution_updated_at": None,
                "created_at": now,
                "updated_at": now,
                "admitted_at": None,
                "finished_at": None,
                "verification": None,
                "outcome_reason": None,
            }
            self._state["items"][item_id] = record
            self._state["order"].append(item_id)
            self._persist()
            return copy.deepcopy(record)

    def _execution_for_item(self, item: dict[str, Any]):
        return self.executions.coordinator_for_workspace(item["workspace"])

    def _run_for_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        run_id = item.get("run_id")
        if not run_id:
            return None
        execution = self._execution_for_item(item)
        run = execution.ledger.get_run(run_id)
        authority = run.get("authority") or {}
        if (
            run.get("lane") != "campaign"
            or authority.get("campaign_id") != item["campaign_id"]
            or authority.get("work_item_id") != item["item_id"]
        ):
            raise ProtocolError("campaign work run authority mismatch")
        return run

    def _adopt_unbound_run_locked(
        self,
        item: dict[str, Any],
    ) -> None:
        if item.get("run_id"):
            return
        execution = self._execution_for_item(item)
        matches = []
        snapshot = execution.ledger.snapshot()
        for run in snapshot["runs"].values():
            authority = run.get("authority") or {}
            if (
                run.get("lane") == "campaign"
                and authority.get("campaign_id") == item["campaign_id"]
                and authority.get("work_item_id") == item["item_id"]
                and run.get("state") not in TERMINAL_RUN_STATES
            ):
                matches.append(run)
        if len(matches) > 1:
            raise ProtocolError(
                f"multiple live execution runs match campaign work item {item['item_id']}"
            )
        if not matches:
            return
        run = matches[0]
        item["run_id"] = run["run_id"]
        item["attempt_count"] = int(item.get("attempt_count") or 0) + 1
        item["admitted_at"] = item.get("admitted_at") or run.get("created_at") or _now()
        item["last_execution_updated_at"] = snapshot.get("updated_at")
        item["state"] = ADMITTED
        item["blocked_reason"] = None
        item["updated_at"] = _now()

    def _dependency_status_locked(self, item: dict[str, Any]) -> tuple[bool, str | None]:
        waiting = []
        failed = []
        for dependency_id in item["depends_on"]:
            dependency = self._require_locked(dependency_id)
            if dependency["state"] == SUCCEEDED:
                continue
            if dependency["state"] in TERMINAL_ITEM_STATES:
                failed.append(dependency_id)
            else:
                waiting.append(dependency_id)
        if failed:
            return False, "DEPENDENCY_TERMINAL_NOT_SUCCESS:" + ",".join(failed)
        if waiting:
            return False, "DEPENDENCY_WAIT:" + ",".join(waiting)
        return True, None

    def _mark_terminal_locked(
        self,
        item: dict[str, Any],
        *,
        state: str,
        reason: str | None = None,
        verification: dict[str, Any] | None = None,
    ) -> None:
        item["state"] = state
        item["blocked_reason"] = None
        item["outcome_reason"] = reason
        item["verification"] = copy.deepcopy(verification)
        item["finished_at"] = _now()
        item["updated_at"] = item["finished_at"]

    def _reconcile_bound_locked(
        self,
        campaign: dict[str, Any],
        item: dict[str, Any],
    ) -> None:
        if not item.get("run_id"):
            return
        run = self._run_for_item(item)
        if run is None:
            raise ProtocolError("campaign work bound run missing")
        if item["state"] in {ADMITTED, STOP_REQUESTED}:
            if campaign["state"] in {DEADLINE_REACHED, CAMPAIGN_CANCELLED}:
                item["state"] = STOP_REQUESTED
                item["blocked_reason"] = (
                    "CAMPAIGN_DEADLINE"
                    if campaign["state"] == DEADLINE_REACHED
                    else "CAMPAIGN_CANCELLED"
                )
                item["updated_at"] = _now()
            if run["state"] in TERMINAL_RUN_STATES:
                item["state"] = BLOCKED
                item["blocked_reason"] = (
                    "TERMINAL_RUN_REQUIRES_OUTCOME:" + run["state"]
                )
                item["last_execution_updated_at"] = (
                    self._execution_for_item(item).ledger.snapshot()["updated_at"]
                )
                item["updated_at"] = _now()

    def _retry_blocked_locked(self, item: dict[str, Any]) -> None:
        if item["state"] != BLOCKED or item.get("run_id"):
            return
        reason = str(item.get("blocked_reason") or "")
        if reason.startswith("DEPENDENCY_TERMINAL_NOT_SUCCESS:"):
            return
        execution = self._execution_for_item(item)
        current = execution.ledger.snapshot().get("updated_at")
        previous = item.get("last_execution_updated_at")
        if previous is None or current != previous:
            item["state"] = QUEUED
            item["blocked_reason"] = None
            item["updated_at"] = _now()

    def tick(
        self,
        campaign_id: str,
        *,
        max_admissions: int = 3,
    ) -> dict[str, Any]:
        try:
            max_admissions = int(max_admissions)
        except (TypeError, ValueError) as exc:
            raise ProtocolError("max_admissions must be an integer") from exc
        if not 1 <= max_admissions <= 16:
            raise ProtocolError("max_admissions must be between 1 and 16")

        self.campaigns.reconcile_runs(campaign_id)
        campaign = self._campaign(campaign_id)
        admitted: list[str] = []
        with self._lock:
            campaign_items = [
                self._state["items"][item_id]
                for item_id in self._state["order"]
                if self._state["items"][item_id]["campaign_id"] == campaign_id
            ]
            for item in campaign_items:
                self._adopt_unbound_run_locked(item)
                self._reconcile_bound_locked(campaign, item)
                self._retry_blocked_locked(item)

            if campaign["state"] == DEADLINE_REACHED:
                for item in campaign_items:
                    if item["state"] in {QUEUED, BLOCKED} and not item.get("run_id"):
                        self._mark_terminal_locked(
                            item,
                            state=SKIPPED_DEADLINE,
                            reason="campaign wall-clock deadline reached before admission",
                        )
                self._persist()
                return self._tick_result_locked(campaign, admitted)

            if campaign["state"] == CAMPAIGN_CANCELLED:
                for item in campaign_items:
                    if item["state"] in {QUEUED, BLOCKED} and not item.get("run_id"):
                        self._mark_terminal_locked(
                            item,
                            state=CANCELLED,
                            reason="campaign cancelled before admission",
                        )
                self._persist()
                return self._tick_result_locked(campaign, admitted)

            if campaign["state"] != RUNNING:
                self._persist()
                return self._tick_result_locked(campaign, admitted)

            for item in campaign_items:
                if len(admitted) >= max_admissions:
                    break
                if item["state"] != QUEUED:
                    continue
                ready, reason = self._dependency_status_locked(item)
                if not ready:
                    if reason and reason.startswith("DEPENDENCY_TERMINAL_NOT_SUCCESS:"):
                        item["state"] = BLOCKED
                    item["blocked_reason"] = reason
                    item["updated_at"] = _now()
                    continue

                execution = self._execution_for_item(item)
                snapshot = execution.ledger.snapshot()
                if snapshot["active_run_count"] >= snapshot[
                    "max_parallel_runs_per_repository"
                ]:
                    item["state"] = BLOCKED
                    item["blocked_reason"] = "CAPACITY"
                    item["last_execution_updated_at"] = snapshot.get("updated_at")
                    item["updated_at"] = _now()
                    continue

                item["attempt_count"] = int(item.get("attempt_count") or 0) + 1
                try:
                    result = self.campaigns.create_run(
                        campaign_id,
                        workspace_code=item["workspace"],
                        goal=item["goal"],
                        base_ref=item["base_ref"],
                        leases=list(item["leases"]),
                        work_item_id=item["item_id"],
                    )
                except ProtocolError as exc:
                    current = execution.ledger.snapshot().get("updated_at")
                    item["state"] = BLOCKED
                    item["blocked_reason"] = "ADMISSION_BLOCKED:" + str(exc)
                    item["last_execution_updated_at"] = current
                    item["updated_at"] = _now()
                    continue
                run = result["run"]
                item["state"] = ADMITTED
                item["blocked_reason"] = None
                item["run_id"] = run["run_id"]
                item["admitted_at"] = _now()
                item["updated_at"] = item["admitted_at"]
                admitted.append(item["item_id"])
            self._persist()
            return self._tick_result_locked(campaign, admitted)

    def _tick_result_locked(
        self,
        campaign: dict[str, Any],
        admitted: list[str],
    ) -> dict[str, Any]:
        items = [
            copy.deepcopy(self._state["items"][item_id])
            for item_id in self._state["order"]
            if self._state["items"][item_id]["campaign_id"]
            == campaign["campaign_id"]
        ]
        counts = {state: 0 for state in sorted(ITEM_STATES)}
        for item in items:
            counts[item["state"]] += 1
        return {
            "campaign": copy.deepcopy(campaign),
            "admitted_item_ids": list(admitted),
            "items": items,
            "counts": counts,
        }

    def finish(
        self,
        item_id: str,
        *,
        success: bool,
        verification: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            item = self._require_locked(item_id)
            if item["state"] not in {ADMITTED, STOP_REQUESTED, BLOCKED}:
                raise ProtocolError(
                    f"campaign work cannot finish from state {item['state']}"
                )
            if not item.get("run_id"):
                raise ProtocolError("campaign work has no admitted run")
            if success and not verification:
                raise ProtocolError(
                    "successful campaign work requires verification evidence"
                )
            if not success and not str(reason or "").strip():
                raise ProtocolError("failed campaign work requires a reason")

            execution = self._execution_for_item(item)
            run = self._run_for_item(item)
            if run is None:
                raise ProtocolError("campaign work bound run missing")
            if run["state"] not in TERMINAL_RUN_STATES:
                run = execution.cancel_run(
                    run["run_id"],
                    reason=(
                        "CAMPAIGN_WORK_VERIFIED_COMPLETE"
                        if success
                        else "CAMPAIGN_WORK_FAILED"
                    ),
                )
            head_sha = execution.worktrees.branch_head(run["branch"])
            receipt = copy.deepcopy(verification or {})
            receipt["execution"] = {
                "run_id": run["run_id"],
                "state": run["state"],
                "branch": run["branch"],
                "head_sha": head_sha,
                "promotion_authority": (
                    (run.get("authority") or {}).get("promotion_authority")
                ),
                "auto_merge": (run.get("authority") or {}).get("auto_merge"),
            }
            self._mark_terminal_locked(
                item,
                state=SUCCEEDED if success else FAILED,
                reason=None if success else str(reason),
                verification=receipt,
            )
            self._persist()
            return copy.deepcopy(item)

    def cancel_unadmitted(self, item_id: str, *, reason: str) -> dict[str, Any]:
        reason = str(reason or "").strip()
        if not reason:
            raise ProtocolError("campaign work cancellation requires a reason")
        with self._lock:
            item = self._require_locked(item_id)
            if item.get("run_id") or item["state"] not in {QUEUED, BLOCKED}:
                raise ProtocolError(
                    "only unadmitted queued/blocked campaign work can cancel"
                )
            self._mark_terminal_locked(
                item,
                state=CANCELLED,
                reason=reason,
            )
            self._persist()
            return copy.deepcopy(item)

    def snapshot(self, campaign_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            items = [
                copy.deepcopy(self._state["items"][item_id])
                for item_id in self._state["order"]
                if campaign_id is None
                or self._state["items"][item_id]["campaign_id"] == campaign_id
            ]
            counts = {state: 0 for state in sorted(ITEM_STATES)}
            for item in items:
                counts[item["state"]] += 1
            return {
                "schema": SCHEMA,
                "campaign_id": campaign_id,
                "items": items,
                "counts": counts,
                "updated_at": self._state.get("updated_at"),
            }

    def digest(self, campaign_id: str) -> dict[str, Any]:
        campaign = self._campaign(campaign_id)
        snapshot = self.snapshot(campaign_id)
        candidates = []
        for item in snapshot["items"]:
            if item["state"] != SUCCEEDED:
                continue
            execution = (item.get("verification") or {}).get("execution") or {}
            candidates.append({
                "item_id": item["item_id"],
                "workspace": item["workspace"],
                "goal": item["goal"],
                "run_id": execution.get("run_id"),
                "branch": execution.get("branch"),
                "head_sha": execution.get("head_sha"),
                "promotion_authority": execution.get("promotion_authority"),
                "auto_merge": execution.get("auto_merge"),
            })
        return {
            "campaign": campaign,
            "counts": snapshot["counts"],
            "review_candidates": candidates,
            "pending_stop_item_ids": [
                item["item_id"]
                for item in snapshot["items"]
                if item["state"] == STOP_REQUESTED
            ],
            "blocked_item_ids": [
                item["item_id"]
                for item in snapshot["items"]
                if item["state"] == BLOCKED
            ],
        }
