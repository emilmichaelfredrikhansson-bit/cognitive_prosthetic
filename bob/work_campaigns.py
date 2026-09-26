from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from .errors import ConfigurationError, ProtocolError
from .execution_ledger import TERMINAL_RUN_STATES
from .workspaces import WorkspaceRegistry
from .worktree_coordination import RepositoryCoordinatorRegistry


SCHEMA = "BOB_WORK_CAMPAIGNS_V1"
PLANNED = "PLANNED"
RUNNING = "RUNNING"
DEADLINE_REACHED = "DEADLINE_REACHED"
COMPLETED = "COMPLETED"
CANCELLED = "CANCELLED"
CAMPAIGN_STATES = {PLANNED, RUNNING, DEADLINE_REACHED, COMPLETED, CANCELLED}
TERMINAL_CAMPAIGN_STATES = {COMPLETED, CANCELLED}
MAX_DURATION_SECONDS = 7 * 24 * 60 * 60


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return f"campaign-{uuid.uuid4().hex[:12]}"


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ConfigurationError("campaign timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


class WorkCampaignManager:
    """Durable wall-clock campaign control over existing repo coordinators."""

    def __init__(
        self,
        path: str | Path,
        workspaces: WorkspaceRegistry,
        executions: RepositoryCoordinatorRegistry,
        *,
        clock: Callable[[], datetime] | None = None,
    ):
        self.path = Path(path)
        self.workspaces = workspaces
        self.executions = executions
        self._clock = clock or _utc_now
        self._lock = threading.RLock()
        self._state = self._load()
        self._reconcile_deadlines()

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ConfigurationError("campaign clock must be timezone-aware")
        return value.astimezone(timezone.utc)

    def _now_iso(self) -> str:
        return self._now().isoformat()

    def _empty(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "campaigns": {},
            "order": [],
            "updated_at": self._now_iso(),
        }

    def _validate(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise ConfigurationError("work campaign schema mismatch")
        campaigns = data.get("campaigns")
        order = data.get("order")
        if not isinstance(campaigns, dict) or not isinstance(order, list):
            raise ConfigurationError("work campaign state requires campaigns/order")
        if len(order) != len(set(order)) or set(order) != set(campaigns):
            raise ConfigurationError("work campaign order/state mismatch")
        for campaign_id, campaign in campaigns.items():
            if campaign.get("campaign_id") != campaign_id:
                raise ConfigurationError("work campaign key/id mismatch")
            if campaign.get("state") not in CAMPAIGN_STATES:
                raise ConfigurationError("invalid work campaign state")
            if not isinstance(campaign.get("targets"), list) or not campaign["targets"]:
                raise ConfigurationError("work campaign requires targets")
            if not isinstance(campaign.get("runs"), list):
                raise ConfigurationError("work campaign runs must be an array")
        return data

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"invalid work campaign store: {self.path}") from exc
        return self._validate(data)

    @staticmethod
    def _write_fsync(path: Path, payload: str) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state["updated_at"] = self._now_iso()
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
                        "Windows campaign persistence verification failed"
                    )
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def _require_locked(self, campaign_id: str) -> dict[str, Any]:
        campaign = self._state["campaigns"].get(str(campaign_id))
        if campaign is None:
            raise ProtocolError(f"unknown work campaign: {campaign_id}")
        return campaign

    def _target(self, workspace_code: str) -> dict[str, Any]:
        workspace = self.workspaces.get(workspace_code)
        return {
            "workspace": workspace.code,
            "repository_id": workspace.github_repository_id,
            "repository": workspace.github_repository,
            "default_branch": workspace.default_branch,
        }

    def _binding_ready(self, workspace_code: str) -> bool:
        try:
            self.executions.coordinator_for_workspace(workspace_code)
            return True
        except ConfigurationError:
            return False

    def _reconcile_deadlines(self) -> list[str]:
        changed: list[str] = []
        now = self._now()
        with self._lock:
            for campaign in self._state["campaigns"].values():
                if campaign.get("state") != RUNNING:
                    continue
                deadline = _parse_time(campaign.get("deadline_at"))
                if deadline is None or now < deadline:
                    continue
                campaign["state"] = DEADLINE_REACHED
                campaign["deadline_reached_at"] = now.isoformat()
                campaign["admission_closed_reason"] = "WALL_CLOCK_DEADLINE"
                changed.append(campaign["campaign_id"])
            if changed:
                self._persist()
        return changed

    def create(
        self,
        *,
        goal: str,
        workspace_codes: list[str],
        duration_seconds: int,
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        goal = str(goal or "").strip()
        if not goal:
            raise ProtocolError("work campaign goal must not be empty")
        try:
            duration_seconds = int(duration_seconds)
        except (TypeError, ValueError) as exc:
            raise ProtocolError("campaign duration_seconds must be an integer") from exc
        if not 1 <= duration_seconds <= MAX_DURATION_SECONDS:
            raise ProtocolError(
                f"campaign duration_seconds must be 1..{MAX_DURATION_SECONDS}"
            )
        codes = []
        seen_codes = set()
        for raw in workspace_codes:
            code = str(raw or "").strip()
            if not code or code.casefold() in seen_codes:
                continue
            seen_codes.add(code.casefold())
            codes.append(code)
        if not codes:
            raise ProtocolError("work campaign requires at least one workspace")
        targets = [self._target(code) for code in codes]
        repository_ids = [target["repository_id"] for target in targets]
        if len(repository_ids) != len(set(repository_ids)):
            raise ProtocolError(
                "campaign V1 requires at most one workspace per repository"
            )
        campaign_id = str(campaign_id or _new_id()).strip()
        now = self._now_iso()
        record = {
            "campaign_id": campaign_id,
            "goal": goal,
            "targets": targets,
            "duration_seconds": duration_seconds,
            "state": PLANNED,
            "promotion_authority": "NONE",
            "auto_merge": False,
            "created_at": now,
            "started_at": None,
            "deadline_at": None,
            "deadline_reached_at": None,
            "finished_at": None,
            "admission_closed_reason": None,
            "cancel_reason": None,
            "runs": [],
        }
        with self._lock:
            if campaign_id in self._state["campaigns"]:
                raise ProtocolError(f"duplicate work campaign: {campaign_id}")
            self._state["campaigns"][campaign_id] = record
            self._state["order"].append(campaign_id)
            self._persist()
            return copy.deepcopy(record)

    def start(self, campaign_id: str) -> dict[str, Any]:
        self._reconcile_deadlines()
        with self._lock:
            campaign = self._require_locked(campaign_id)
            if campaign["state"] != PLANNED:
                raise ProtocolError("only PLANNED campaigns can start")
            missing = [
                target["workspace"]
                for target in campaign["targets"]
                if not self._binding_ready(target["workspace"])
            ]
            if missing:
                raise ProtocolError(
                    "campaign targets lack local repository bindings: "
                    + ",".join(sorted(missing))
                )
            now = self._now()
            campaign["state"] = RUNNING
            campaign["started_at"] = now.isoformat()
            campaign["deadline_at"] = (
                now + timedelta(seconds=campaign["duration_seconds"])
            ).isoformat()
            campaign["admission_closed_reason"] = None
            self._persist()
            return copy.deepcopy(campaign)

    def extend(
        self,
        campaign_id: str,
        *,
        additional_seconds: int,
    ) -> dict[str, Any]:
        self._reconcile_deadlines()
        try:
            additional_seconds = int(additional_seconds)
        except (TypeError, ValueError) as exc:
            raise ProtocolError(
                "campaign additional_seconds must be an integer"
            ) from exc
        if additional_seconds < 1:
            raise ProtocolError("campaign additional_seconds must be positive")

        with self._lock:
            campaign = self._require_locked(campaign_id)
            if campaign["state"] not in {RUNNING, DEADLINE_REACHED}:
                raise ProtocolError(
                    "only RUNNING or DEADLINE_REACHED campaigns can extend"
                )
            total_duration = (
                int(campaign.get("duration_seconds") or 0)
                + additional_seconds
            )
            if total_duration > MAX_DURATION_SECONDS:
                raise ProtocolError(
                    f"campaign duration_seconds must remain <= {MAX_DURATION_SECONDS}"
                )

            now = self._now()
            deadline = _parse_time(campaign.get("deadline_at"))
            if campaign["state"] == RUNNING and deadline is not None:
                base = deadline
            else:
                base = now

            campaign["duration_seconds"] = total_duration
            campaign["deadline_at"] = (
                base + timedelta(seconds=additional_seconds)
            ).isoformat()
            campaign["state"] = RUNNING
            campaign["deadline_reached_at"] = None
            campaign["admission_closed_reason"] = None
            self._persist()
            return copy.deepcopy(campaign)

    def _target_for_locked(
        self,
        campaign: dict[str, Any],
        workspace_code: str,
    ) -> dict[str, Any]:
        matches = [
            target
            for target in campaign["targets"]
            if target["workspace"].casefold() == str(workspace_code).casefold()
        ]
        if len(matches) != 1:
            raise ProtocolError(
                f"workspace {workspace_code} is not a campaign target"
            )
        return matches[0]

    def admit(self, campaign_id: str, workspace_code: str) -> dict[str, Any]:
        self._reconcile_deadlines()
        with self._lock:
            campaign = self._require_locked(campaign_id)
            self._target_for_locked(campaign, workspace_code)
            if campaign["state"] != RUNNING:
                raise ProtocolError(
                    f"campaign does not admit new work: {campaign['state']}"
                )
            deadline = _parse_time(campaign["deadline_at"])
            if deadline is None or self._now() >= deadline:
                raise ProtocolError("campaign wall-clock deadline reached")
            return copy.deepcopy(campaign)

    def create_run(
        self,
        campaign_id: str,
        *,
        workspace_code: str,
        goal: str,
        base_ref: str,
        leases: list[str],
        depends_on: list[str] | None = None,
        work_item_id: str | None = None,
    ) -> dict[str, Any]:
        campaign = self.admit(campaign_id, workspace_code)
        target = next(
            target
            for target in campaign["targets"]
            if target["workspace"].casefold() == workspace_code.casefold()
        )
        execution = self.executions.coordinator_for_workspace(workspace_code)
        run = execution.create_run(
            goal=goal,
            workspace=workspace_code,
            base_ref=base_ref,
            leases=leases,
            depends_on=depends_on,
            lane="campaign",
            authority={
                "campaign_id": campaign_id,
                "promotion_authority": "NONE",
                "auto_merge": False,
                "repository_id": target["repository_id"],
                "repository": target["repository"],
                "workspace": target["workspace"],
                "work_item_id": str(work_item_id or "").strip() or None,
            },
        )
        if run["state"] != "ACTIVE":
            blocked_reason = str(run.get("blocked_reason") or run["state"])
            execution.cancel_run(
                run["run_id"],
                reason="CAMPAIGN_NOT_ADMITTED:" + blocked_reason,
            )
            raise ProtocolError(
                "campaign run could not start immediately: " + blocked_reason
            )
        binding = {
            "workspace": target["workspace"],
            "repository_id": target["repository_id"],
            "run_id": run["run_id"],
            "created_at": self._now_iso(),
        }
        # The wall clock can cross the deadline after the initial admission
        # check but before the execution run is durably bound. Reconcile again
        # before accepting the binding and cancel the just-created run if the
        # campaign closed in that narrow window.
        self._reconcile_deadlines()
        with self._lock:
            stored = self._require_locked(campaign_id)
            if stored["state"] != RUNNING:
                execution.cancel_run(
                    run["run_id"],
                    reason="CAMPAIGN_ADMISSION_CLOSED_DURING_BIND",
                )
                raise ProtocolError("campaign admission closed during run bind")
            if not any(
                item["run_id"] == run["run_id"]
                for item in stored["runs"]
            ):
                stored["runs"].append(binding)
                self._persist()
        return {"campaign": copy.deepcopy(stored), "run": run}

    def reconcile_runs(self, campaign_id: str) -> dict[str, Any]:
        self._reconcile_deadlines()
        with self._lock:
            campaign = copy.deepcopy(self._require_locked(campaign_id))
        discovered: list[dict[str, Any]] = []
        bound_run_ids = {binding["run_id"] for binding in campaign["runs"]}
        for target in campaign["targets"]:
            try:
                execution = self.executions.coordinator_for_workspace(
                    target["workspace"]
                )
            except ConfigurationError:
                continue
            for run in execution.ledger.snapshot()["runs"].values():
                authority = run.get("authority") or {}
                matches_campaign = (
                    run.get("lane") == "campaign"
                    and authority.get("campaign_id") == campaign_id
                )
                recoverable = (
                    run["run_id"] in bound_run_ids
                    or run.get("state") not in TERMINAL_RUN_STATES
                )
                if matches_campaign and recoverable:
                    discovered.append({
                        "workspace": target["workspace"],
                        "repository_id": target["repository_id"],
                        "run_id": run["run_id"],
                        "created_at": run.get("created_at"),
                    })
        by_run = {item["run_id"]: item for item in discovered}
        with self._lock:
            stored = self._require_locked(campaign_id)
            for binding in stored["runs"]:
                if binding["run_id"] not in by_run:
                    raise ProtocolError(
                        f"campaign run binding missing from execution ledger: {binding['run_id']}"
                    )
            existing = {item["run_id"] for item in stored["runs"]}
            for binding in discovered:
                if binding["run_id"] not in existing:
                    stored["runs"].append(binding)
            self._persist()
            return copy.deepcopy(stored)

    def run_states(self, campaign_id: str) -> dict[str, Any]:
        campaign = self.reconcile_runs(campaign_id)
        states: dict[str, int] = {}
        active: list[str] = []
        for binding in campaign["runs"]:
            execution = self.executions.coordinator_for_workspace(
                binding["workspace"]
            )
            run = execution.ledger.get_run(binding["run_id"])
            states[run["state"]] = states.get(run["state"], 0) + 1
            if run["state"] not in TERMINAL_RUN_STATES:
                active.append(run["run_id"])
        return {
            "states": states,
            "nonterminal_run_ids": active,
            "count": len(campaign["runs"]),
        }

    def complete(self, campaign_id: str) -> dict[str, Any]:
        summary = self.run_states(campaign_id)
        with self._lock:
            campaign = self._require_locked(campaign_id)
            if campaign["state"] not in {RUNNING, DEADLINE_REACHED}:
                raise ProtocolError("campaign cannot complete from current state")
            if summary["nonterminal_run_ids"]:
                raise ProtocolError(
                    "campaign cannot complete with nonterminal runs"
                )
            campaign["state"] = COMPLETED
            campaign["finished_at"] = self._now_iso()
            campaign["admission_closed_reason"] = "COMPLETED"
            self._persist()
            result = copy.deepcopy(campaign)
        return {"campaign": result, "runs": summary}

    def cancel(self, campaign_id: str, *, reason: str) -> dict[str, Any]:
        reason = str(reason or "").strip()
        if not reason:
            raise ProtocolError("campaign cancellation requires a reason")
        self._reconcile_deadlines()
        with self._lock:
            campaign = self._require_locked(campaign_id)
            if campaign["state"] in TERMINAL_CAMPAIGN_STATES:
                raise ProtocolError("campaign is already terminal")
            campaign["state"] = CANCELLED
            campaign["finished_at"] = self._now_iso()
            campaign["cancel_reason"] = reason
            campaign["admission_closed_reason"] = "CANCELLED"
            self._persist()
            result = copy.deepcopy(campaign)
        return {"campaign": result, "runs": self.run_states(campaign_id)}

    def snapshot(self) -> dict[str, Any]:
        self._reconcile_deadlines()
        with self._lock:
            campaigns = [
                copy.deepcopy(self._state["campaigns"][campaign_id])
                for campaign_id in self._state["order"]
            ]
            counts = {state: 0 for state in sorted(CAMPAIGN_STATES)}
            for campaign in campaigns:
                counts[campaign["state"]] += 1
            return {
                "schema": SCHEMA,
                "campaigns": campaigns,
                "counts": counts,
                "updated_at": self._state.get("updated_at"),
            }
