from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, ProtocolError


SCHEMA = "BOB_PENDING_EFFECTS_V1"


class PendingEffectStore:
    """Durable staged effects that still require explicit operator approval."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self._lock = threading.RLock()
        self._state = self._load()

    @property
    def _backup_path(self) -> Path:
        return self.path.with_name(self.path.name + ".bak")
    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"schema": SCHEMA, "pending": {}}

    @staticmethod
    def _write_text_fsync(path: Path, payload: str) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    def _validate(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise ConfigurationError("pending effect store schema mismatch")
        pending = data.get("pending")
        if not isinstance(pending, dict):
            raise ConfigurationError("pending effect store requires a pending object")
        for pending_id, state in pending.items():
            if not isinstance(pending_id, str) or not pending_id:
                raise ConfigurationError("pending effect id must be a non-empty string")
            if not isinstance(state, dict):
                raise ConfigurationError("pending effect state must be an object")
        return data

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if os.name != "nt" or not self._backup_path.exists():
                raise ConfigurationError(f"invalid pending effect store: {exc}") from exc
            try:
                data = json.loads(self._backup_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as backup_exc:
                raise ConfigurationError(
                    f"invalid pending effect store and backup: {backup_exc}"
                ) from exc
            logging.warning("Recovered pending effect store from Windows fallback backup")
        return self._validate(data)

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
                        "Windows pending effect fallback persistence verification failed"
                    )
                logging.warning("Pending effect store used verified Windows in-place fallback")
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._state["pending"])

    def put(self, pending_id: str, state: dict[str, Any]) -> None:
        pending_id = str(pending_id).strip()
        if not pending_id:
            raise ProtocolError("pending effect id must not be empty")
        if not isinstance(state, dict):
            raise ProtocolError("pending effect state must be an object")
        try:
            durable = json.loads(json.dumps(state))
        except (TypeError, ValueError) as exc:
            raise ProtocolError("pending effect state must be JSON serializable") from exc
        with self._lock:
            self._state["pending"][pending_id] = durable
            self._persist()

    def remove(self, pending_id: str) -> None:
        with self._lock:
            if self._state["pending"].pop(str(pending_id), None) is not None:
                self._persist()
