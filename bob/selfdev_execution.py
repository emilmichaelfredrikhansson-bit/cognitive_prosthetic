from __future__ import annotations

from typing import Any

from .errors import ConfigurationError, ProtocolError
from .execution_ledger import LEASE_HOLDING_STATES, PARKED_RUN_STATE, TERMINAL_RUN_STATES
from .selfdev_queue import ACTIVE_STATE, RESUMABLE_STATES, SelfDevelopmentQueue
from .worktree_coordination import ExecutionCoordinator


LIVE_EXECUTION_STATES = LEASE_HOLDING_STATES | {"QUEUED", PARKED_RUN_STATE}


class SelfDevelopmentExecution:
    """Bind durable self-development intent to the existing repo coordinator.

    This layer does not schedule background work and does not integrate/promote
    candidates. It only creates/reconciles lane=selfdev execution runs.
    """

    def __init__(
        self,
        queue: SelfDevelopmentQueue,
        execution: ExecutionCoordinator,
        *,
        workspace: str = "BOB",
    ):
        self.queue = queue
        self.execution = execution
        self.workspace = str(workspace or "").strip()
        if not self.workspace:
            raise ConfigurationError("self-development execution requires workspace")
        if (
            queue.repository_id != execution.repository_id
            or queue.repository_full_name.casefold()
            != execution.repository_full_name.casefold()
            or queue.canonical_ref != execution.canonical_ref
        ):
            raise ConfigurationError(
                "self-development queue/execution repository binding mismatch"
            )

    def _item(self, item_id: str) -> dict[str, Any]:
        for item in self.queue.snapshot()["items"]:
            if item["item_id"] == str(item_id):
                return item
        raise ProtocolError(f"unknown self-development item: {item_id}")

    def _matching_runs(self, item_id: str) -> list[dict[str, Any]]:
        runs = self.execution.ledger.snapshot()["runs"].values()
        return [
            run
            for run in runs
            if run.get("lane") == "selfdev"
            and (run.get("authority") or {}).get("selfdev_item_id") == item_id
        ]

    def _validated_run(
        self,
        item: dict[str, Any],
        matches: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if len(matches) > 1:
            raise ProtocolError(
                f"multiple self-development execution runs match {item['item_id']}"
            )
        bound_id = item.get("execution_run_id")
        if bound_id:
            try:
                run = self.execution.ledger.get_run(bound_id)
            except ProtocolError as exc:
                raise ProtocolError(
                    f"bound self-development execution run missing: {bound_id}"
                ) from exc
            if (
                run.get("lane") != "selfdev"
                or (run.get("authority") or {}).get("selfdev_item_id")
                != item["item_id"]
            ):
                raise ProtocolError(
                    "bound execution run does not belong to self-development item"
                )
            if matches and matches[0]["run_id"] != bound_id:
                raise ProtocolError(
                    "self-development execution authority disagrees with queue binding"
                )
            return run
        return matches[0] if matches else None

    def reconcile_item(self, item_id: str) -> dict[str, Any]:
        item = self._item(item_id)
        run = self._validated_run(item, self._matching_runs(item["item_id"]))

        if item["state"] in {"QUALIFIED", "DISCARDED", "FAILED"}:
            if run and run.get("state") not in TERMINAL_RUN_STATES:
                raise ProtocolError(
                    "terminal self-development item still has live execution run"
                )
            return {"action": "TERMINAL", "item": item, "run": run}
        if run is None:
            if item["state"] == ACTIVE_STATE:
                return {"action": "UNBOUND_ACTIVE", "item": item, "run": None}
            if item["state"] in RESUMABLE_STATES:
                return {"action": "REQUEUE_REQUIRED", "item": item, "run": None}
            return {"action": "QUEUED", "item": item, "run": None}

        run_state = str(run.get("state"))
        if run_state in TERMINAL_RUN_STATES:
            return {
                "action": "TERMINAL_EXECUTION_REQUIRES_DECISION",
                "item": item,
                "run": run,
            }
        if run_state not in LIVE_EXECUTION_STATES:
            raise ProtocolError(
                f"unsupported self-development execution state: {run_state}"
            )

        if item["state"] in RESUMABLE_STATES:
            item = self.queue.resume_reconciled_execution(
                item["item_id"], run["run_id"]
            )
        elif item["state"] == ACTIVE_STATE and not item.get("execution_run_id"):
            item = self.queue.bind_execution_run(item["item_id"], run["run_id"])
        elif item["state"] == "QUEUED":
            raise ProtocolError(
                "queued self-development item already has an execution run"
            )
        if run_state in LEASE_HOLDING_STATES:
            self.execution.ensure_active_worktrees()
            run = self.execution.ledger.get_run(run["run_id"])
        return {
            "action": (
                "WAITING_EXECUTION_CAPACITY"
                if run_state == "QUEUED"
                else (
                    "PARKED_FOR_INTERACTIVE"
                    if run_state == PARKED_RUN_STATE
                    else "LIVE_EXECUTION_RECONCILED"
                )
            ),
            "item": item,
            "run": run,
        }

    def reconcile(self) -> list[dict[str, Any]]:
        results = []
        for item in self.queue.snapshot()["items"]:
            if item["state"] == "QUEUED" and not item.get("execution_run_id"):
                continue
            results.append(self.reconcile_item(item["item_id"]))
        return results

    def claim_next(self, *, base_ref: str) -> dict[str, Any]:
        base_ref = str(base_ref or "").strip()
        if not base_ref:
            raise ProtocolError(
                "self-development claim requires explicit base_ref"
            )

        reconciliation = self.reconcile()
        unresolved = [
            entry
            for entry in reconciliation
            if entry["action"]
            in {
                "REQUEUE_REQUIRED",
                "UNBOUND_ACTIVE",
                "TERMINAL_EXECUTION_REQUIRES_DECISION",
            }
        ]
        if unresolved:
            raise ProtocolError(
                "self-development reconciliation requires operator decision before "
                "claiming another item"
            )
        active = [
            entry
            for entry in reconciliation
            if entry["item"]["state"] == ACTIVE_STATE
            and entry["action"]
            in {"LIVE_EXECUTION_RECONCILED", "WAITING_EXECUTION_CAPACITY"}
        ]
        if active:
            return {**active[0], "action": "RESUMED_EXISTING"}

        item = self.queue.claim_next()
        if item is None:
            return {"action": "EMPTY", "item": None, "run": None}

        try:
            run = self.execution.create_run(
                goal=item["goal"],
                workspace=self.workspace,
                base_ref=base_ref,
                leases=list(item["leases"]),
                lane="selfdev",
                authority={
                    "selfdev_item_id": item["item_id"],
                    "promotion_authority": "NONE",
                },
            )
        except Exception as exc:
            self.queue.block(
                item["item_id"],
                f"EXECUTION_CREATE_FAILED:{type(exc).__name__}",
            )
            raise

        try:
            item = self.queue.bind_execution_run(item["item_id"], run["run_id"])
        except Exception:
            self.execution.cancel_run(
                run["run_id"], reason="SELFDEV_QUEUE_BIND_FAILED"
            )
            try:
                self.queue.block(item["item_id"], "EXECUTION_BIND_FAILED")
            except Exception:
                pass
            raise
        return {"action": "CLAIMED", "item": item, "run": run}

    def preempt_for_interactive(self, item_id: str, *, reason: str) -> dict[str, Any]:
        """Park idle ACTIVE selfdev execution so interactive work can take its leases."""
        item = self._item(item_id)
        run = self._validated_run(item, self._matching_runs(item["item_id"]))
        if item["state"] != ACTIVE_STATE or run is None:
            raise ProtocolError("only ACTIVE bound self-development can be preempted")
        run = self.execution.park_selfdev_run(run["run_id"], reason=reason)
        return {"action": "PARKED_FOR_INTERACTIVE", "item": item, "run": run}

    def resume_preempted(self, item_id: str) -> dict[str, Any]:
        """Resume a parked selfdev run through ordinary repo lease/capacity arbitration."""
        item = self._item(item_id)
        run = self._validated_run(item, self._matching_runs(item["item_id"]))
        if run is None or run.get("state") != PARKED_RUN_STATE:
            raise ProtocolError("self-development item has no parked execution run")
        run = self.execution.resume_parked_run(run["run_id"])
        return {
            "action": "LIVE_EXECUTION_RECONCILED" if run["state"] == "ACTIVE" else "WAITING_EXECUTION_CAPACITY",
            "item": item,
            "run": run,
        }

    def finish_item(
        self,
        item_id: str,
        *,
        state: str,
        verification: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Finish queue lifecycle only after any bound execution is terminal."""
        item = self._item(item_id)
        run = self._validated_run(item, self._matching_runs(item["item_id"]))
        state = str(state or "").strip().upper()

        if run is not None and run.get("state") not in TERMINAL_RUN_STATES:
            raise ProtocolError(
                "self-development execution run must be terminal before item finish"
            )
        receipt = dict(verification or {})
        if state == "QUALIFIED":
            if run is None or run.get("state") != "CANCELLED":
                raise ProtocolError(
                    "QUALIFIED self-development requires a preserved cancelled "
                    "execution run; promotion remains separate"
                )
            if not receipt:
                raise ProtocolError(
                    "QUALIFIED self-development requires verification evidence"
                )
            head_sha = self.execution.worktrees.branch_head(run["branch"])
            receipt["execution"] = {
                "run_id": run["run_id"],
                "state": run["state"],
                "branch": run["branch"],
                "head_sha": head_sha,
                "promotion_authority": (
                    (run.get("authority") or {}).get("promotion_authority")
                ),
            }
        finished = self.queue.finish(
            item["item_id"],
            state=state,
            verification=receipt or None,
            reason=reason,
        )
        return {"action": "FINISHED", "item": finished, "run": run}
