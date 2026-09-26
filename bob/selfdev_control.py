from __future__ import annotations

from typing import Any

from .errors import ProtocolError
from .execution_ledger import TERMINAL_RUN_STATES
from .selfdev_checkpoints import SelfDevelopmentCheckpoints
from .selfdev_execution import SelfDevelopmentExecution
from .worktree_coordination import ExecutionCoordinator


_PREEMPTION_LABEL = "interactive-preemption:"


class SelfDevelopmentControl:
    """Interactive-first arbitration plus reversible selfdev sandbox controls."""

    def __init__(
        self,
        selfdev: SelfDevelopmentExecution,
        checkpoints: SelfDevelopmentCheckpoints,
    ):
        self.selfdev = selfdev
        self.checkpoints = checkpoints

    def _same_repository(self, execution: ExecutionCoordinator) -> bool:
        return execution.repository_id == self.selfdev.execution.repository_id

    def _selfdev_item_for_run(self, run: dict[str, Any]) -> str | None:
        if run.get("lane") != "selfdev":
            return None
        value = (run.get("authority") or {}).get("selfdev_item_id")
        return None if value in (None, "") else str(value)

    def _candidate_for_blocker(
        self,
        execution: ExecutionCoordinator,
        run: dict[str, Any],
    ) -> dict[str, Any] | None:
        reason = str(run.get("blocked_reason") or "")
        snapshot = execution.ledger.snapshot()
        runs = snapshot["runs"]
        if reason.startswith("SCOPE_CONFLICT:"):
            blocker_ids = [
                value.strip()
                for value in reason.split(":", 1)[1].split(",")
                if value.strip()
            ]
            blockers = [runs.get(blocker_id) for blocker_id in blocker_ids]
            if not blockers or any(blocker is None for blocker in blockers):
                return None
            # Do not disturb selfdev if another interactive/non-selfdev run would
            # still block the operator run. When every blocker is selfdev, park
            # one at a time and let the ledger recompute the remaining conflict.
            if any(self._selfdev_item_for_run(blocker) is None for blocker in blockers):
                return None
            return blockers[0]
        if reason != "CAPACITY":
            return None
        candidates = [
            item
            for item in runs.values()
            if item.get("state") == "ACTIVE"
            and self._selfdev_item_for_run(item)
        ]
        candidates.sort(
            key=lambda item: (
                str(item.get("activated_at") or item.get("created_at") or ""),
                item["run_id"],
            ),
            reverse=True,
        )
        return candidates[0] if candidates else None
    def create_interactive(
        self,
        execution: ExecutionCoordinator,
        *,
        goal: str,
        workspace: str,
        base_ref: str,
        leases: list[str],
        depends_on: list[str] | None = None,
        authority: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run = execution.create_run(
            goal=goal,
            workspace=workspace,
            base_ref=base_ref,
            leases=leases,
            depends_on=depends_on,
            lane="interactive",
            authority=authority,
        )
        if not self._same_repository(execution):
            return {
                "run": run,
                "preempted": [],
                "preemption_status": "NOT_SELFDEV_REPOSITORY",
            }

        preempted: list[dict[str, Any]] = []
        seen: set[str] = set()
        max_attempts = len(execution.ledger.snapshot()["runs"]) + 1
        for _ in range(max_attempts):
            run = execution.ledger.get_run(run["run_id"])
            if run["state"] != "QUEUED":
                break
            blocker = self._candidate_for_blocker(execution, run)
            if blocker is None or blocker["run_id"] in seen:
                break
            seen.add(blocker["run_id"])
            item_id = self._selfdev_item_for_run(blocker)
            if item_id is None:
                break
            try:
                checkpoint = self.checkpoints.create(
                    item_id,
                    label=_PREEMPTION_LABEL + run["run_id"],
                    verification={
                        "reason": run.get("blocked_reason"),
                        "interactive_run_id": run["run_id"],
                    },
                )
                parked = self.selfdev.preempt_for_interactive(
                    item_id,
                    reason=f"interactive:{run['run_id']}",
                )
            except ProtocolError:
                break
            preempted.append({
                "item_id": item_id,
                "run_id": parked["run"]["run_id"],
                "checkpoint_id": checkpoint["checkpoint_id"],
            })
            execution.ensure_active_worktrees()

        run = execution.ledger.get_run(run["run_id"])
        return {
            "run": run,
            "preempted": preempted,
            "preemption_status": (
                "PREEMPTED_SELFDEV"
                if preempted
                else (
                    "NOT_NEEDED"
                    if run["state"] == "ACTIVE"
                    else "NO_SAFE_PREEMPTION"
                )
            ),
        }
    def resume_after_interactive(self, interactive_run_id: str) -> dict[str, Any]:
        run = self.selfdev.execution.ledger.get_run(interactive_run_id)
        if run.get("lane") != "interactive":
            raise ProtocolError("preemption release requires an interactive run")
        if run.get("state") not in TERMINAL_RUN_STATES:
            raise ProtocolError(
                "preempted self-development may resume only after interactive run is terminal"
            )
        label = _PREEMPTION_LABEL + run["run_id"]
        item_ids = []
        for checkpoint in self.checkpoints.snapshot()["checkpoints"]:
            if checkpoint.get("label") == label:
                item_ids.append(checkpoint["item_id"])

        resumed = []
        seen = set()
        for item_id in item_ids:
            if item_id in seen:
                continue
            seen.add(item_id)
            try:
                result = self.selfdev.resume_preempted(item_id)
            except ProtocolError:
                continue
            resumed.append({
                "item_id": item_id,
                "run_id": result["run"]["run_id"],
                "state": result["run"]["state"],
            })
        return {
            "interactive_run_id": run["run_id"],
            "resumed": resumed,
            "count": len(resumed),
        }
