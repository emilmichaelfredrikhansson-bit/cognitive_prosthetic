from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .campaign_context import bounded_continuation_results
from .campaign_repo_adapter import CampaignRepoAdapter
from .errors import AuthorityError, ConfigurationError, ProtocolError
from .protocol import make_result, parse_model_response
from .work_campaign_queue import ADMITTED, WorkCampaignQueue
from .work_campaign_worker import WorkCampaignWorker
from .work_campaigns import RUNNING, WorkCampaignManager
from .worktree_coordination import ExecutionCoordinator, RepositoryCoordinatorRegistry


SCHEMA = "BOB_CAMPAIGN_WORK_EXECUTOR_V1"
MAX_COGNITION_ROUNDS = 12
MAX_DURABLE_RESULTS = 32


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CampaignWorkExecutor:
    """Fresh-cognition driver for exact campaign worker ready items."""

    def __init__(
        self,
        path: str | Path,
        runtime: Any,
        campaigns: WorkCampaignManager,
        queue: WorkCampaignQueue,
        worker: WorkCampaignWorker,
        executions: RepositoryCoordinatorRegistry,
        *,
        verification_commands_by_repository: dict[int, list[list[str]]] | None = None,
    ):
        self.path = Path(path)
        self.runtime = runtime
        self.campaigns = campaigns
        self.queue = queue
        self.worker = worker
        self.executions = executions
        self.verification_commands_by_repository = {
            int(key): [list(command) for command in commands]
            for key, commands in (verification_commands_by_repository or {}).items()
        }
        self._lock = threading.RLock()
        self._state = self._load()

    def _empty(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "items": {}, "updated_at": _now()}

    def _validate(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise ConfigurationError("campaign work executor schema mismatch")
        if not isinstance(data.get("items"), dict):
            raise ConfigurationError("campaign work executor items must be an object")
        return data

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            return self._validate(
                json.loads(self.path.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"invalid campaign work executor store: {self.path}"
            ) from exc

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
                        "Windows campaign executor persistence verification failed"
                    )
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def _item(self, item_id: str) -> dict[str, Any]:
        matches = [
            item
            for item in self.queue.snapshot()["items"]
            if item["item_id"] == str(item_id)
        ]
        if len(matches) != 1:
            raise ProtocolError(f"unknown campaign work item: {item_id}")
        return matches[0]

    def _campaign(self, campaign_id: str) -> dict[str, Any]:
        matches = [
            campaign
            for campaign in self.campaigns.snapshot()["campaigns"]
            if campaign["campaign_id"] == str(campaign_id)
        ]
        if len(matches) != 1:
            raise ProtocolError(f"unknown work campaign: {campaign_id}")
        return matches[0]

    def _execution(self, item: dict[str, Any]) -> ExecutionCoordinator:
        return self.executions.coordinator_for_workspace(item["workspace"])

    def _validate_binding(
        self,
        item: dict[str, Any],
        execution: ExecutionCoordinator,
        run: dict[str, Any],
    ) -> None:
        workspace = self.runtime.registry.get(item["workspace"])
        authority = run.get("authority") or {}
        if (
            item["state"] != ADMITTED
            or item.get("run_id") != run.get("run_id")
            or run.get("lane") != "campaign"
            or run.get("state") != "ACTIVE"
            or authority.get("campaign_id") != item["campaign_id"]
            or authority.get("work_item_id") != item["item_id"]
            or authority.get("promotion_authority") != "NONE"
            or authority.get("auto_merge") is not False
            or str(authority.get("workspace") or "") != workspace.code
            or int(authority.get("repository_id") or 0)
            != workspace.github_repository_id
            or str(authority.get("repository") or "").casefold()
            != workspace.github_repository.casefold()
            or execution.repository_id != workspace.github_repository_id
            or execution.repository_full_name.casefold()
            != workspace.github_repository.casefold()
        ):
            raise AuthorityError("campaign executor run/workspace authority mismatch")
        execution._verify_repository_identity()

    def _adapter(
        self,
        item: dict[str, Any],
        execution: ExecutionCoordinator,
        run: dict[str, Any],
    ) -> CampaignRepoAdapter:
        workspace = self.runtime.registry.get(item["workspace"])
        return CampaignRepoAdapter(
            execution,
            run,
            write_authorized=workspace.effects.get("write_branch", False),
            verification_commands=self.verification_commands_by_repository.get(
                execution.repository_id, []
            ),
        )

    def _record_for(
        self,
        item: dict[str, Any],
        run: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            record = self._state["items"].get(item["item_id"])
            if record is None:
                record = {
                    "item_id": item["item_id"],
                    "campaign_id": item["campaign_id"],
                    "workspace": item["workspace"],
                    "run_id": run["run_id"],
                    "branch": run["branch"],
                    "status": "READY",
                    "round_count": 0,
                    "last_cognition_id": None,
                    "last_request_id": None,
                    "results": [],
                    "effects": [],
                    "verifications": [],
                    "pending_effect": None,
                    "outcome": None,
                    "created_at": _now(),
                    "updated_at": _now(),
                }
                self._state["items"][item["item_id"]] = record
                self._persist()
            elif (
                record.get("campaign_id") != item["campaign_id"]
                or record.get("workspace") != item["workspace"]
                or record.get("run_id") != run["run_id"]
                or record.get("branch") != run["branch"]
            ):
                raise ProtocolError("campaign executor durable binding mismatch")
            return record

    def _update(self, record: dict[str, Any], **updates: Any) -> None:
        with self._lock:
            record.update(copy.deepcopy(updates))
            record["updated_at"] = _now()
            self._persist()

    def _append_result(self, record: dict[str, Any], result: str) -> None:
        bounded = str(result)
        if len(bounded) > 55_000:
            bounded = bounded[:55_000] + "\n[executor result truncated]"
        with self._lock:
            record["results"].append(bounded)
            if len(record["results"]) > MAX_DURABLE_RESULTS:
                record["results"] = record["results"][-MAX_DURABLE_RESULTS:]
            record["updated_at"] = _now()
            self._persist()

    def _finish_cognition(
        self,
        execution: ExecutionCoordinator,
        cognition_id: str,
        *,
        success: bool,
        summary: str | None = None,
        error: str | None = None,
    ) -> None:
        cognition = execution.ledger.snapshot()["cognitions"].get(cognition_id)
        if cognition and cognition.get("state") == "RUNNING":
            execution.ledger.finish_cognition(
                cognition_id,
                success=success,
                summary=summary,
                error=error,
            )

    def _still_executable(
        self,
        item: dict[str, Any],
        execution: ExecutionCoordinator,
    ) -> bool:
        campaign = self._campaign(item["campaign_id"])
        if campaign["state"] != RUNNING:
            self.worker.cycle(item["campaign_id"], max_admissions=1)
            return False
        current = self._item(item["item_id"])
        if current["state"] != ADMITTED or not current.get("run_id"):
            return False
        return execution.ledger.get_run(current["run_id"])["state"] == "ACTIVE"

    def _yield_to_interactive(
        self,
        item: dict[str, Any],
        execution: ExecutionCoordinator,
    ) -> bool:
        queued = [
            run
            for run in execution.ledger.snapshot()["runs"].values()
            if run.get("lane") == "interactive"
            and run.get("state") == "QUEUED"
        ]
        queued.sort(
            key=lambda run: (
                str(run.get("created_at") or ""),
                run["run_id"],
            )
        )
        for interactive in queued:
            self.worker.preempt_for_interactive(
                execution, interactive["run_id"]
            )
            current = execution.ledger.get_run(item["run_id"])
            if current["state"] != "ACTIVE":
                return True
        return False

    def _recover_pending(
        self,
        record: dict[str, Any],
        adapter: CampaignRepoAdapter,
    ) -> None:
        pending = copy.deepcopy(record.get("pending_effect"))
        if not pending:
            return
        if not adapter.is_clean():
            self._update(record, status="RECOVERY_BLOCKED_DIRTY")
            raise ProtocolError(
                "campaign executor found dirty uncheckpointed work during recovery"
            )
        receipt = adapter.apply_pending(pending)
        with self._lock:
            record["effects"].append(copy.deepcopy(receipt))
            record["pending_effect"] = None
            record["status"] = "READY"
            record["updated_at"] = _now()
            self._persist()
        self._append_result(
            record,
            make_result(
                pending["message_id"],
                pending["tool"],
                "PASS",
                data={"verified_effect": receipt, "recovered": True},
            ),
        )

    def _apply_effect(
        self,
        record: dict[str, Any],
        adapter: CampaignRepoAdapter,
        item: dict[str, Any],
        message: Any,
    ) -> dict[str, Any]:
        pending = adapter.prepare_effect(message, item_id=item["item_id"])
        self._update(
            record,
            pending_effect=pending,
            status="APPLYING_EFFECT",
        )
        receipt = adapter.apply_pending(pending)
        with self._lock:
            record["effects"].append(copy.deepcopy(receipt))
            record["pending_effect"] = None
            record["status"] = "READY"
            record["updated_at"] = _now()
            self._persist()
        return receipt

    def _compile_prompt(
        self,
        item: dict[str, Any],
        execution: ExecutionCoordinator,
        run: dict[str, Any],
        adapter: CampaignRepoAdapter,
        record: dict[str, Any],
    ) -> str:
        workspace = self.runtime.registry.get(item["workspace"])
        envelope = {
            "workspace": workspace.code,
            "repository": execution.repository_full_name,
            "repository_id": execution.repository_id,
            "campaign_id": item["campaign_id"],
            "item_id": item["item_id"],
            "run_id": run["run_id"],
            "branch": run["branch"],
            "base_sha": run["base_sha"],
            "worktree_path": str(adapter.worktree),
            "promotion_authority": "NONE",
            "auto_merge": False,
            "write_branch_authorized": bool(
                workspace.effects.get("write_branch", False)
            ),
            "goal": item["goal"],
            "round": int(record.get("round_count") or 0),
            "continuation_results": bounded_continuation_results(
                record.get("results") or ()
            ),
        }
        return (
            "Continue this Bob campaign work item from the supplied durable "
            "state; do not restart it.\n\n"
            "EXECUTION ENVELOPE\n"
            + json.dumps(envelope, indent=2, sort_keys=True)
            + "\n\nHARD RULES\n"
            "- Work only on this exact repository/run/branch/worktree.\n"
            "- Never request merge, push, promotion, production mutation, spend, "
            "secrets, or authority expansion.\n"
            "- Emit exactly one BOB protocol message per response.\n"
            "- READ tools: repo.read_file, repo.list_files, repo.search, "
            "repo.status, repo.verify.\n"
            "- EFFECT tools: repo.create_file, repo.replace_file, "
            "repo.delete_file. Effects are isolated branch writes only.\n"
            "- Before replace/delete, read the file and use content_sha256 as "
            "expected_sha256.\n"
            "- BOB.DONE is advisory; Bob performs deterministic verification "
            "before successful completion.\n"
            "- continuation_results already happened; do not treat them as requested work.\n"
            "- Use BOB.ASK only for a genuine operator decision.\n\n"
            "Return one raw JSON BOB object or one fenced BOB object. Examples:\n"
            '{"type":"BOB.READ","id":"r1","tool":"repo.read_file",'
            '"args":{"path":"CURRENT_WORK.md"}}\n'
            '{"type":"BOB.EFFECT","id":"e1","tool":"repo.replace_file",'
            '"args":{"path":"x.py","content":"...","expected_sha256":"..."}}\n'
            '{"type":"BOB.DONE","id":"d1","args":{"summary":"candidate ready"}}'
            "\n\nNEXT ACTION: Continue from continuation_results above. "
            "Use a new id, never repeat a PASS READ, and advance toward the goal."
        )

    def _blocked(
        self,
        record: dict[str, Any],
        execution: ExecutionCoordinator,
        cognition_id: str,
        status: str,
        exc: Exception,
    ) -> dict[str, Any]:
        self._finish_cognition(
            execution,
            cognition_id,
            success=False,
            error=str(exc),
        )
        self._update(
            record,
            status=status,
            outcome={"error": str(exc), "at": _now()},
        )
        return {
            "item_id": record["item_id"],
            "status": status,
            "error": str(exc),
        }

    def execute_ready(
        self,
        ready: dict[str, Any],
        *,
        max_rounds: int = MAX_COGNITION_ROUNDS,
    ) -> dict[str, Any]:
        max_rounds = max(1, min(int(max_rounds), MAX_COGNITION_ROUNDS))
        item = self._item(str(ready["item_id"]))
        if (
            item["state"] != ADMITTED
            or item.get("run_id") != ready.get("run_id")
            or item.get("workspace") != ready.get("workspace")
        ):
            raise ProtocolError(
                "executor may consume only the exact current ready binding"
            )
        execution = self._execution(item)
        run = execution.ledger.get_run(item["run_id"])
        self._validate_binding(item, execution, run)
        adapter = self._adapter(item, execution, run)
        record = self._record_for(item, run)
        try:
            self._recover_pending(record, adapter)
        except Exception as exc:
            return {
                "item_id": item["item_id"],
                "status": record["status"],
                "error": str(exc),
            }

        for _ in range(max_rounds):
            if not self._still_executable(item, execution):
                self._update(record, status="SAFE_STOPPED")
                return {
                    "item_id": item["item_id"],
                    "status": "SAFE_STOPPED",
                }
            if self._yield_to_interactive(item, execution):
                self._update(record, status="PREEMPTED_INTERACTIVE")
                return {
                    "item_id": item["item_id"],
                    "status": "PREEMPTED_INTERACTIVE",
                }

            item = self._item(item["item_id"])
            run = execution.ledger.get_run(item["run_id"])
            self._validate_binding(item, execution, run)
            adapter.refresh(run)
            adapter.require_clean()

            cognition = execution.ledger.begin_cognition(
                run["run_id"],
                purpose=(
                    f"campaign-work:{item['item_id']}:round:"
                    f"{int(record.get('round_count') or 0) + 1}"
                ),
            )
            with self._lock:
                record["round_count"] = int(
                    record.get("round_count") or 0
                ) + 1
                record["last_cognition_id"] = cognition["cognition_id"]
                record["last_request_id"] = cognition["request_id"]
                record["status"] = "RUNNING_COGNITION"
                record["updated_at"] = _now()
                self._persist()

            prompt = self._compile_prompt(
                item, execution, run, adapter, record
            )
            try:
                model_text = self.runtime.bridge.cognition(
                    prompt,
                    request_id=cognition["request_id"],
                    run_id=run["run_id"],
                    cognition_id=cognition["cognition_id"],
                )
            except Exception as exc:
                return self._blocked(
                    record,
                    execution,
                    cognition["cognition_id"],
                    "BLOCKED_COGNITION",
                    exc,
                )

            try:
                parsed = parse_model_response(model_text)
                if len(parsed.messages) != 1:
                    raise ProtocolError(
                        "campaign cognition must emit exactly one BOB message"
                    )
                message = parsed.messages[0]
            except Exception as exc:
                return self._blocked(
                    record,
                    execution,
                    cognition["cognition_id"],
                    "BLOCKED_PROTOCOL",
                    exc,
                )

            if message.type == "BOB.READ":
                duplicate = any(
                    f'"request_id": "{message.id}"' in result
                    for result in record.get("results") or ()
                )
                if duplicate:
                    return self._blocked(
                        record,
                        execution,
                        cognition["cognition_id"],
                        "BLOCKED_PROTOCOL",
                        ProtocolError(
                            "campaign cognition repeated completed BOB.READ id"
                        ),
                    )
                try:
                    data = adapter.read(message)
                    result = make_result(
                        message.id,
                        message.tool or "",
                        "PASS",
                        data=data,
                    )
                except Exception as exc:
                    result = make_result(
                        message.id,
                        message.tool or "",
                        "FAIL",
                        error=str(exc),
                    )
                self._append_result(record, result)
                self._finish_cognition(
                    execution,
                    cognition["cognition_id"],
                    success=True,
                    summary="bounded repository read completed",
                )
                self._update(record, status="READY")
                continue

            if message.type == "BOB.EFFECT":
                if self._campaign(item["campaign_id"])["state"] != RUNNING:
                    self._finish_cognition(
                        execution,
                        cognition["cognition_id"],
                        success=True,
                        summary="campaign closed before requested effect",
                    )
                    self.worker.cycle(
                        item["campaign_id"], max_admissions=1
                    )
                    self._update(record, status="SAFE_STOPPED")
                    return {
                        "item_id": item["item_id"],
                        "status": "SAFE_STOPPED",
                    }
                try:
                    receipt = self._apply_effect(
                        record, adapter, item, message
                    )
                except Exception as exc:
                    status = (
                        "RECOVERY_BLOCKED_DIRTY"
                        if not adapter.is_clean()
                        else "BLOCKED_EFFECT"
                    )
                    return self._blocked(
                        record,
                        execution,
                        cognition["cognition_id"],
                        status,
                        exc,
                    )
                self._append_result(
                    record,
                    make_result(
                        message.id,
                        message.tool or "",
                        "PASS",
                        data={"verified_effect": receipt},
                    ),
                )
                self._finish_cognition(
                    execution,
                    cognition["cognition_id"],
                    success=True,
                    summary=(
                        f"verified isolated branch effect "
                        f"{message.tool} {receipt['path']}"
                    ),
                )
                self._update(record, status="READY")
                continue

            if message.type == "BOB.ASK":
                self._finish_cognition(
                    execution,
                    cognition["cognition_id"],
                    success=True,
                    summary="operator decision requested",
                )
                self._update(
                    record,
                    status="AWAITING_OPERATOR",
                    outcome={
                        "terminal": copy.deepcopy(message.raw),
                        "at": _now(),
                    },
                )
                return {
                    "item_id": item["item_id"],
                    "status": "AWAITING_OPERATOR",
                    "terminal": message.raw,
                }

            if message.type != "BOB.DONE":
                return self._blocked(
                    record,
                    execution,
                    cognition["cognition_id"],
                    "BLOCKED_PROTOCOL",
                    ProtocolError(
                        f"unexpected campaign terminal: {message.type}"
                    ),
                )

            verification = adapter.verify()
            with self._lock:
                record["verifications"].append(
                    copy.deepcopy(verification)
                )
                record["updated_at"] = _now()
                self._persist()
            if verification["status"] == "PASS":
                self._finish_cognition(
                    execution,
                    cognition["cognition_id"],
                    success=True,
                    summary=(
                        "model done; deterministic verification PASS"
                    ),
                )
                finished = self.queue.finish(
                    item["item_id"],
                    success=True,
                    verification={
                        "campaign_executor": {
                            "status": "PASS",
                            "round_count": record["round_count"],
                            "effects": copy.deepcopy(
                                record["effects"]
                            ),
                            "verification": verification,
                            "terminal": copy.deepcopy(message.raw),
                        }
                    },
                )
                self._update(
                    record,
                    status="SUCCEEDED",
                    outcome={
                        "verification": verification,
                        "queue_state": finished["state"],
                        "at": _now(),
                    },
                )
                return {
                    "item_id": item["item_id"],
                    "status": "SUCCEEDED",
                    "verification": verification,
                    "queue_item": finished,
                }

            self._append_result(
                record,
                make_result(
                    f"verify-{record['round_count']}",
                    "repo.verify",
                    "FAIL",
                    data=verification,
                    error=(
                        "deterministic verification failed; "
                        "repair before DONE"
                    ),
                ),
            )
            self._finish_cognition(
                execution,
                cognition["cognition_id"],
                success=True,
                summary=(
                    "model done but deterministic verification failed"
                ),
            )
            self._update(record, status="READY")

        item = self._item(item["item_id"])
        run = execution.ledger.get_run(item["run_id"])
        adapter.refresh(run)
        if not adapter.is_clean():
            self._update(record, status="RECOVERY_BLOCKED_DIRTY")
            return {
                "item_id": item["item_id"],
                "status": "RECOVERY_BLOCKED_DIRTY",
                "error": (
                    "round budget exhausted with dirty worktree"
                ),
            }
        checkpoint = self.worker.checkpoint_round_yield(
            item["item_id"],
            round_count=record["round_count"],
        )
        self._update(
            record,
            status="ROUND_YIELD",
            outcome={
                "reason": "COGNITION_ROUND_SLICE_EXHAUSTED",
                "checkpoint_id": checkpoint["checkpoint_id"],
                "at": _now(),
            },
        )
        return {
            "item_id": item["item_id"],
            "status": "ROUND_YIELD",
            "checkpoint": checkpoint,
        }

    def cycle(
        self,
        campaign_id: str,
        *,
        max_admissions: int = 3,
        max_items: int = 1,
        max_rounds: int = MAX_COGNITION_ROUNDS,
    ) -> dict[str, Any]:
        max_admissions = max(1, min(int(max_admissions), 3))
        max_items = max(1, min(int(max_items), 3))
        control = self.worker.cycle(
            str(campaign_id),
            max_admissions=max_admissions,
        )
        outcomes = []
        for ready in list(control["ready"])[:max_items]:
            outcome = self.execute_ready(
                ready,
                max_rounds=max_rounds,
            )
            outcomes.append(outcome)
            if outcome["status"] in {
                "BLOCKED_COGNITION",
                "BLOCKED_PROTOCOL",
                "BLOCKED_EFFECT",
                "RECOVERY_BLOCKED_DIRTY",
                "AWAITING_OPERATOR",
            }:
                break
        final_control = self.worker.cycle(
            str(campaign_id),
            max_admissions=1,
        )
        return {
            "campaign_id": str(campaign_id),
            "consumed_ready_item_ids": [
                outcome["item_id"] for outcome in outcomes
            ],
            "outcomes": outcomes,
            "worker": final_control,
            "digest": self.digest(str(campaign_id)),
        }

    def digest(self, campaign_id: str) -> dict[str, Any]:
        worker_digest = self.worker.digest(str(campaign_id))
        item_ids = {
            item["item_id"]
            for item in self.queue.snapshot(str(campaign_id))["items"]
        }
        with self._lock:
            executor_items = []
            for item_id in sorted(item_ids):
                record = self._state["items"].get(item_id)
                if not record:
                    continue
                executor_items.append(
                    {
                        "item_id": item_id,
                        "run_id": record.get("run_id"),
                        "branch": record.get("branch"),
                        "status": record.get("status"),
                        "round_count": record.get("round_count"),
                        "effect_count": len(
                            record.get("effects") or []
                        ),
                        "verification_count": len(
                            record.get("verifications") or []
                        ),
                        "pending_effect": bool(
                            record.get("pending_effect")
                        ),
                        "outcome": copy.deepcopy(
                            record.get("outcome")
                        ),
                        "updated_at": record.get("updated_at"),
                    }
                )
        return {
            **worker_digest,
            "executor_schema": SCHEMA,
            "executor_items": executor_items,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)
