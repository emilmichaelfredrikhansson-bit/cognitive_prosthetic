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


SCHEMA = "BOB_BLOCKED_CONTINUATIONS_V1"


class ContinuationStore:
    """Durable receipts for cognition that must resume after an executed effect."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self._lock = threading.RLock()
        self._state = self._load()

    @property
    def _backup_path(self) -> Path:
        return self.path.with_name(self.path.name + ".bak")

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"schema": SCHEMA, "continuations": {}}

    @staticmethod
    def _write_text_fsync(path: Path, payload: str) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    def _validate(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise ConfigurationError("blocked continuation store schema mismatch")
        continuations = data.get("continuations")
        if not isinstance(continuations, dict):
            raise ConfigurationError("blocked continuation store requires a continuations object")
        for continuation_id, state in continuations.items():
            if not isinstance(continuation_id, str) or not continuation_id:
                raise ConfigurationError("blocked continuation id must be a non-empty string")
            if not isinstance(state, dict):
                raise ConfigurationError("blocked continuation state must be an object")
        return data

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if os.name != "nt" or not self._backup_path.exists():
                raise ConfigurationError(f"invalid blocked continuation store: {exc}") from exc
            try:
                data = json.loads(self._backup_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as backup_exc:
                raise ConfigurationError(
                    f"invalid blocked continuation store and backup: {backup_exc}"
                ) from exc
            logging.warning("Recovered blocked continuation store from Windows fallback backup")
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
                        "Windows blocked continuation fallback persistence verification failed"
                    )
                logging.warning("Blocked continuation store used verified Windows in-place fallback")
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._state["continuations"])

    def put(self, continuation_id: str, state: dict[str, Any]) -> None:
        continuation_id = str(continuation_id).strip()
        if not continuation_id:
            raise ProtocolError("blocked continuation id must not be empty")
        if not isinstance(state, dict):
            raise ProtocolError("blocked continuation state must be an object")
        try:
            durable = json.loads(json.dumps(state))
        except (TypeError, ValueError) as exc:
            raise ProtocolError("blocked continuation state must be JSON serializable") from exc
        with self._lock:
            self._state["continuations"][continuation_id] = durable
            self._persist()

    def remove(self, continuation_id: str) -> None:
        with self._lock:
            if self._state["continuations"].pop(str(continuation_id), None) is not None:
                self._persist()
