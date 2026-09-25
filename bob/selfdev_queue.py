from __future__ import annotations

import copy
import json
import logging
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, ProtocolError


SCHEMA = "BOB_SELF_DEVELOPMENT_QUEUE_V1"
ACTIVE_STATE = "ACTIVE"
RESUMABLE_STATES = {"INTERRUPTED", "BLOCKED"}
TERMINAL_STATES = {"QUALIFIED", "DISCARDED", "FAILED"}
ITEM_STATES = {"QUEUED", ACTIVE_STATE, *RESUMABLE_STATES, *TERMINAL_STATES}
_SAFE_LEASE = re.compile(r"^(module|work|contract|path):.+$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"selfdev-{uuid.uuid4().hex[:12]}"


def _normalize_lease(value: str) -> str:
    lease = str(value or "").strip().replace("\\", "/")
    if not lease:
        raise ProtocolError("self-development lease must not be empty")
    if ":" not in lease:
        lease = "work:" + lease
    if not _SAFE_LEASE.fullmatch(lease):
        raise ProtocolError(f"invalid self-development lease: {value!r}")
    prefix, payload = lease.split(":", 1)
    payload = payload.strip().strip("/") if prefix == "path" else payload.strip()
    if not payload or ".." in payload.split("/"):
        raise ProtocolError(f"invalid self-development lease: {value!r}")
    return f"{prefix}:{payload}"


class SelfDevelopmentQueue:
    """Durable repo-bound backlog for background Bob self-development.

    This store owns self-development intent/lifecycle only. It does not create
    execution runs, worktrees, effects, approvals or promotions.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        repository_full_name: str,
        repository_id: int,
        canonical_ref: str,
    ):
        self.path = Path(path).expanduser().resolve()
        self.repository_full_name = str(repository_full_name or "").strip().strip("/")
        self.repository_id = int(repository_id)
        self.canonical_ref = str(canonical_ref or "").strip()
        if not self.repository_full_name or self.repository_id <= 0 or not self.canonical_ref:
            raise ConfigurationError(
                "self-development queue requires repository identity and canonical_ref"
            )
        self._lock = threading.RLock()
        self._state = self._load()
        self._recover_interrupted_work()

    @property
    def _backup_path(self) -> Path:
        return self.path.with_name(self.path.name + ".bak")

    def _identity(self) -> dict[str, Any]:
        return {
            "full_name": self.repository_full_name,
            "id": self.repository_id,
            "canonical_ref": self.canonical_ref,
        }

    def _empty(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "repository": self._identity(),
            "items": {},
            "order": [],
            "updated_at": _now(),
        }

    @staticmethod
    def _write_text_fsync(path: Path, payload: str) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    def _validate(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise ConfigurationError("self-development queue schema mismatch")
        if data.get("repository") != self._identity():
            raise ConfigurationError(
                "self-development queue repository identity mismatch"
            )
        items = data.get("items")
        order = data.get("order")
        if not isinstance(items, dict) or not isinstance(order, list):
            raise ConfigurationError(
                "self-development queue requires items object and order array"
            )
        if len(order) != len(set(order)) or set(order) != set(items):
            raise ConfigurationError(
                "self-development queue order must contain every item exactly once"
            )
        active_count = 0
        for item_id, item in items.items():
            if not isinstance(item_id, str) or not item_id or not isinstance(item, dict):
                raise ConfigurationError("invalid self-development queue item")
            if item.get("item_id") != item_id:
                raise ConfigurationError("self-development queue key/id mismatch")
            if item.get("state") not in ITEM_STATES:
                raise ConfigurationError(
                    f"invalid self-development item state: {item.get('state')!r}"
                )
            if item.get("state") == ACTIVE_STATE:
                active_count += 1
            leases = item.get("leases")
            if not isinstance(leases, list) or not leases:
                raise ConfigurationError(
                    "self-development queue item requires leases"
                )
        if active_count > 1:
            raise ConfigurationError(
                "self-development queue permits at most one ACTIVE item"
            )
        return data

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if os.name != "nt" or not self._backup_path.exists():
                raise ConfigurationError(
                    f"invalid self-development queue: {exc}"
                ) from exc
            try:
                data = json.loads(self._backup_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as backup_exc:
                raise ConfigurationError(
                    f"invalid self-development queue and backup: {backup_exc}"
                ) from exc
            logging.warning(
                "Recovered self-development queue from Windows fallback backup"
            )
        return self._validate(data)

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
                if self.path.exists():
                    previous = self.path.read_text(encoding="utf-8")
                    self._write_text_fsync(self._backup_path, previous)
                self._write_text_fsync(self.path, payload)
                if self.path.read_text(encoding="utf-8") != payload:
                    raise ConfigurationError(
                        "Windows self-development queue fallback persistence verification failed"
                    )
                logging.warning(
                    "Self-development queue used verified Windows in-place fallback"
                )
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def _recover_interrupted_work(self) -> None:
        changed = False
        with self._lock:
            for item in self._state["items"].values():
                if item.get("state") != ACTIVE_STATE:
                    continue
                item["state"] = "INTERRUPTED"
                item["blocked_reason"] = "RUNTIME_RESTART_RECONCILE_REQUIRED"
                item["updated_at"] = _now()
                changed = True
            if changed:
                self._persist()

    def _require_item_locked(self, item_id: str) -> dict[str, Any]:
        item = self._state["items"].get(str(item_id))
        if item is None:
            raise ProtocolError(f"unknown self-development item: {item_id}")
        return item

    def enqueue(
        self,
        *,
        goal: str,
        leases: list[str],
        expected_outcome: str | None = None,
        item_id: str | None = None,
    ) -> dict[str, Any]:
        goal = str(goal or "").strip()
        if not goal:
            raise ProtocolError("self-development goal must not be empty")
        normalized = sorted({_normalize_lease(value) for value in leases})
        if not normalized:
            raise ProtocolError("self-development item requires at least one lease")
        item_id = str(item_id or _new_id()).strip()
        if not item_id:
            raise ProtocolError("self-development item id must not be empty")
        now = _now()
        record = {
            "item_id": item_id,
            "goal": goal,
            "expected_outcome": (
                None if expected_outcome in (None, "") else str(expected_outcome).strip()
            ),
            "leases": normalized,
            "state": "QUEUED",
            "attempt_count": 0,
            "execution_run_id": None,
            "blocked_reason": None,
            "created_at": now,
            "updated_at": now,
            "claimed_at": None,
            "finished_at": None,
            "verification": None,
        }
        with self._lock:
            if item_id in self._state["items"]:
                raise ProtocolError(f"duplicate self-development item: {item_id}")
            self._state["items"][item_id] = record
            self._state["order"].append(item_id)
            self._persist()
            return copy.deepcopy(record)

    def claim_next(self) -> dict[str, Any] | None:
        with self._lock:
            if any(
                item.get("state") == ACTIVE_STATE
                for item in self._state["items"].values()
            ):
                raise ProtocolError(
                    "self-development queue already has an ACTIVE item"
                )
            for item_id in self._state["order"]:
                item = self._state["items"][item_id]
                if item.get("state") != "QUEUED":
                    continue
                now = _now()
                item["state"] = ACTIVE_STATE
                item["attempt_count"] = int(item.get("attempt_count") or 0) + 1
                item["claimed_at"] = now
                item["updated_at"] = now
                item["blocked_reason"] = None
                self._persist()
                return copy.deepcopy(item)
            return None

    def bind_execution_run(self, item_id: str, run_id: str) -> dict[str, Any]:
        run_id = str(run_id or "").strip()
        if not run_id:
            raise ProtocolError("self-development execution run id must not be empty")
        with self._lock:
            item = self._require_item_locked(item_id)
            if item["state"] != ACTIVE_STATE:
                raise ProtocolError(
                    "only ACTIVE self-development items can bind an execution run"
                )
            existing = item.get("execution_run_id")
            if existing not in (None, run_id):
                raise ProtocolError(
                    f"self-development item already bound to execution run {existing}"
                )
            item["execution_run_id"] = run_id
            item["updated_at"] = _now()
            self._persist()
            return copy.deepcopy(item)

    def block(self, item_id: str, reason: str) -> dict[str, Any]:
        reason = str(reason or "").strip()
        if not reason:
            raise ProtocolError("self-development block reason must not be empty")
        with self._lock:
            item = self._require_item_locked(item_id)
            if item["state"] != ACTIVE_STATE:
                raise ProtocolError("only ACTIVE self-development items can block")
            item["state"] = "BLOCKED"
            item["blocked_reason"] = reason
            item["updated_at"] = _now()
            self._persist()
            return copy.deepcopy(item)

    def requeue(self, item_id: str) -> dict[str, Any]:
        with self._lock:
            item = self._require_item_locked(item_id)
            if item["state"] not in RESUMABLE_STATES:
                raise ProtocolError(
                    "only BLOCKED/INTERRUPTED self-development items can requeue"
                )
            if item.get("execution_run_id"):
                raise ProtocolError(
                    "bound execution run requires reconciliation before requeue"
                )
            item["state"] = "QUEUED"
            item["blocked_reason"] = None
            item["updated_at"] = _now()
            self._persist()
            return copy.deepcopy(item)

    def finish(
        self,
        item_id: str,
        *,
        state: str,
        verification: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        state = str(state or "").strip().upper()
        if state not in TERMINAL_STATES:
            raise ProtocolError(
                "self-development terminal state must be QUALIFIED, DISCARDED or FAILED"
            )
        with self._lock:
            item = self._require_item_locked(item_id)
            if item["state"] not in {ACTIVE_STATE, "BLOCKED", "INTERRUPTED"}:
                raise ProtocolError(
                    f"cannot finish self-development item from state {item['state']}"
                )
            item["state"] = state
            item["blocked_reason"] = None if reason in (None, "") else str(reason)
            item["verification"] = copy.deepcopy(verification)
            item["finished_at"] = _now()
            item["updated_at"] = item["finished_at"]
            self._persist()
            return copy.deepcopy(item)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            items = copy.deepcopy(self._state["items"])
            ordered = [items[item_id] for item_id in self._state["order"]]
            counts: dict[str, int] = {state: 0 for state in sorted(ITEM_STATES)}
            for item in ordered:
                counts[item["state"]] += 1
            return {
                "schema": SCHEMA,
                "repository": copy.deepcopy(self._state["repository"]),
                "items": ordered,
                "counts": counts,
                "updated_at": self._state.get("updated_at"),
            }
