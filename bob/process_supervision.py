from __future__ import annotations

import ctypes
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, IdentityMismatch, ProtocolError

SCHEMA = "BOB_PROCESS_SUPERVISOR_V1"
PROCESS_CLASSES = {
    "LONG_LIVED_RUNTIME",
    "UNTIL_EXIT",
    "COGNITION_CLIENT",
    "TEST",
    "PROBE",
}
ACTIVE_STATES = {"RUNNING", "STOPPING"}
TERMINAL_STATES = {"EXITED", "FAILED", "STOPPED", "STALE_IDENTITY"}
CLEANUP_POLICIES = {"KEEP_RECORD", "REAP_COMPLETED"}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"proc-{uuid.uuid4().hex[:12]}"


def _windows_process_identity(pid: int) -> str | None:
    if os.name != "nt":
        return None
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid)
    )
    if not handle:
        return None
    try:
        exit_code = ctypes.c_ulong()
        if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return None
        if exit_code.value != 259:  # STILL_ACTIVE
            return None
        creation = ctypes.c_ulonglong()
        exit_time = ctypes.c_ulonglong()
        kernel = ctypes.c_ulonglong()
        user = ctypes.c_ulonglong()
        ok = ctypes.windll.kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        )
        if not ok:
            return None
        return f"windows-filetime:{creation.value}"
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _proc_process_identity(pid: int) -> str | None:
    stat_path = Path(f"/proc/{int(pid)}/stat")
    if not stat_path.exists():
        return None
    try:
        parts = stat_path.read_text(encoding="utf-8").split()
        return f"proc-start:{parts[21]}"
    except (OSError, IndexError):
        return None


def process_identity(pid: int) -> str | None:
    if int(pid) <= 0:
        return None
    identity = _windows_process_identity(pid)
    if identity is not None:
        return identity
    identity = _proc_process_identity(pid)
    if identity is not None:
        return identity
    try:
        os.kill(int(pid), 0)
    except (OSError, ProcessLookupError):
        return None
    return None


def _windows_parent_map() -> dict[int, int]:
    if os.name != "nt":
        return {}
    command = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,ParentProcessId | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise ConfigurationError(
            (completed.stderr or completed.stdout or "process tree query failed").strip()
        )
    raw = completed.stdout.strip()
    if not raw:
        return {}
    data = json.loads(raw)
    rows = data if isinstance(data, list) else [data]
    return {
        int(row["ProcessId"]): int(row["ParentProcessId"])
        for row in rows
        if row.get("ProcessId") is not None
    }


def _is_descendant(root_pid: int, candidate_pid: int, parents: dict[int, int]) -> bool:
    current = int(candidate_pid)
    root_pid = int(root_pid)
    seen: set[int] = set()
    while current and current not in seen:
        if current == root_pid:
            return True
        seen.add(current)
        current = int(parents.get(current, 0))
    return False


def _listening_pids(port: int) -> set[int]:
    completed = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise ConfigurationError(
            (completed.stderr or completed.stdout or "netstat failed").strip()
        )
    result: set[int] = set()
    suffix = f":{int(port)}"
    for raw in completed.stdout.splitlines():
        fields = raw.split()
        if len(fields) < 5 or fields[0].upper() != "TCP":
            continue
        if fields[3].upper() != "LISTENING" or not fields[1].endswith(suffix):
            continue
        try:
            result.add(int(fields[4]))
        except ValueError:
            continue
    return result


class ProcessSupervisor:
    """Durable lifecycle owner for explicitly started Bob child processes."""

    def __init__(
        self,
        state_path: str | Path,
        *,
        allowed_executables: list[str | Path] | None = None,
        log_root: str | Path | None = None,
    ):
        self.state_path = Path(state_path)
        self.log_root = (
            Path(log_root)
            if log_root is not None
            else self.state_path.parent / "process_logs"
        )
        configured = allowed_executables or [sys.executable]
        self.allowed_executables = {
            str(Path(item).expanduser().resolve()).casefold() for item in configured
        }
        self._lock = threading.RLock()
        self._handles: dict[str, subprocess.Popen] = {}
        self._state = self._load()
        self.refresh()

    def _empty_state(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "processes": {},
            "updated_at": _now(),
        }

    @property
    def _backup_path(self) -> Path:
        return self.state_path.with_name(self.state_path.name + ".bak")

    @staticmethod
    def _write_text_fsync(path: Path, payload: str) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    def _load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._empty_state()
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if os.name != "nt" or not self._backup_path.exists():
                raise ConfigurationError(f"invalid process supervisor state: {exc}") from exc
            try:
                data = json.loads(self._backup_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as backup_exc:
                raise ConfigurationError(
                    f"invalid process supervisor state and backup: {backup_exc}"
                ) from exc
            logging.warning(
                "Recovered ProcessSupervisor state from Windows fallback backup"
            )
        if data.get("schema") != SCHEMA:
            raise ConfigurationError(
                f"process supervisor schema mismatch: {data.get('schema')!r}"
            )
        data.setdefault("processes", {})
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
            try:
                os.replace(temp_name, self.state_path)
            except PermissionError:
                if os.name != "nt":
                    raise
                # Some Windows processes open JSON state with read/write sharing
                # but without delete-sharing, so ReplaceFile/rename is denied even
                # though an in-place write is allowed. Preserve the previous valid
                # state first, then fsync + verify an exact direct write. Never
                # silently continue if persistence cannot be proven exact.
                if self.state_path.exists():
                    previous = self.state_path.read_text(encoding="utf-8")
                    self._write_text_fsync(self._backup_path, previous)
                self._write_text_fsync(self.state_path, payload)
                if self.state_path.read_text(encoding="utf-8") != payload:
                    raise ConfigurationError(
                        "Windows process supervisor fallback persistence verification failed"
                    )
                logging.warning(
                    "ProcessSupervisor used verified Windows in-place persistence fallback"
                )
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def _require(self, process_id: str) -> dict[str, Any]:
        record = self._state["processes"].get(str(process_id))
        if record is None:
            raise ProtocolError(f"unknown supervised process: {process_id}")
        return record

    def _validate_command(self, command: list[str]) -> list[str]:
        if not isinstance(command, list) or not command:
            raise ProtocolError("supervised command must be a non-empty argv list")
        argv = [str(item) for item in command]
        executable = str(Path(argv[0]).expanduser().resolve()).casefold()
        if executable not in self.allowed_executables:
            raise ProtocolError(
                f"executable is not allowed by ProcessSupervisor: {argv[0]!r}"
            )
        return argv

    @staticmethod
    def _normalize_ports(ports: list[int] | None) -> list[int]:
        normalized = sorted({int(port) for port in (ports or [])})
        if any(port < 1 or port > 65535 for port in normalized):
            raise ProtocolError("owned ports must be between 1 and 65535")
        return normalized

    @staticmethod
    def _port_is_available(port: int) -> bool:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.bind(("127.0.0.1", int(port)))
            return True
        except OSError:
            return False
        finally:
            probe.close()

    def _registered_port_owner(self, port: int) -> str | None:
        for process_id, record in self._state["processes"].items():
            if (
                record.get("state") in ACTIVE_STATES
                and int(port) in (record.get("owns_ports") or [])
            ):
                return process_id
        return None

    def assert_ports_available(self, ports: list[int]) -> None:
        self.refresh()
        for port in self._normalize_ports(ports):
            if self._port_is_available(port):
                continue
            owner = self._registered_port_owner(port)
            if owner:
                raise ProtocolError(
                    f"port {port} is already owned by supervised process {owner}"
                )
            raise ConfigurationError(
                f"port {port} is in use by an unowned process; refusing to replace it"
            )

    def start(
        self,
        *,
        purpose: str,
        command_class: str,
        command: list[str],
        cwd: str | Path,
        run_id: str | None = None,
        repository_id: int | None = None,
        owns_ports: list[int] | None = None,
        cleanup_policy: str = "REAP_COMPLETED",
        env: dict[str, str] | None = None,
        process_id: str | None = None,
    ) -> dict[str, Any]:
        purpose = str(purpose or "").strip()
        if not purpose:
            raise ProtocolError("supervised process requires purpose")
        command_class = str(command_class or "").strip().upper()
        if command_class not in PROCESS_CLASSES:
            raise ProtocolError(f"unsupported process class: {command_class!r}")
        cleanup_policy = str(cleanup_policy or "").strip().upper()
        if cleanup_policy not in CLEANUP_POLICIES:
            raise ProtocolError(f"unsupported cleanup policy: {cleanup_policy!r}")
        argv = self._validate_command(command)
        ports = self._normalize_ports(owns_ports)
        cwd_path = Path(cwd).resolve()
        if not cwd_path.is_dir():
            raise ConfigurationError(f"supervised cwd does not exist: {cwd_path}")

        with self._lock:
            self.assert_ports_available(ports)
            process_id = str(process_id or _new_id())
            if process_id in self._state["processes"]:
                raise ProtocolError(f"duplicate process_id: {process_id}")
            self.log_root.mkdir(parents=True, exist_ok=True)
            log_path = self.log_root / f"{process_id}.log"
            log_handle = log_path.open("ab", buffering=0)
            creationflags = 0
            start_new_session = False
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                if command_class == "LONG_LIVED_RUNTIME":
                    creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
                else:
                    creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
            else:
                start_new_session = True
            try:
                handle = subprocess.Popen(
                    argv,
                    cwd=str(cwd_path),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags,
                    start_new_session=start_new_session,
                )
            finally:
                log_handle.close()

            identity = process_identity(handle.pid)
            if identity is None:
                handle.terminate()
                try:
                    handle.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                raise ConfigurationError(
                    f"could not establish process identity for pid={handle.pid}"
                )
            record = {
                "process_id": process_id,
                "run_id": None if run_id is None else str(run_id),
                "repository_id": None if repository_id is None else int(repository_id),
                "purpose": purpose,
                "pid": int(handle.pid),
                "process_identity": identity,
                "command_class": command_class,
                "command": argv,
                "cwd": str(cwd_path),
                "started_at": _now(),
                "state": "RUNNING",
                "owns_ports": ports,
                "port_owners": {},
                "log_path": str(log_path),
                "cleanup_policy": cleanup_policy,
                "exit_code": None,
                "error": None,
                "finished_at": None,
                "reaped_at": None,
                "restart_count": 0,
            }
            self._state["processes"][process_id] = record
            self._handles[process_id] = handle
            self._persist()
            return deepcopy(record)

    def bind_owned_ports(self, process_id: str) -> dict[str, Any]:
        """Bind declared ports to exact live listener identities after startup health."""
        with self._lock:
            record = self._require(process_id)
            if record.get("state") != "RUNNING":
                raise ProtocolError("ports can only be bound for a RUNNING process")
            self._assert_owned_identity(record)
            root_pid = int(record["pid"])
            parents = _windows_parent_map() if os.name == "nt" else {}
            owners: dict[str, dict[str, Any]] = {}
            for port in record.get("owns_ports") or []:
                listeners = _listening_pids(int(port))
                if len(listeners) != 1:
                    raise ConfigurationError(
                        f"expected exactly one listener for supervised port {port}; "
                        f"found {sorted(listeners)}"
                    )
                listener_pid = next(iter(listeners))
                if listener_pid != root_pid and not (
                    os.name == "nt"
                    and _is_descendant(root_pid, listener_pid, parents)
                ):
                    raise IdentityMismatch(
                        f"listener pid {listener_pid} for port {port} is not owned "
                        f"by supervised root pid {root_pid}"
                    )
                identity = process_identity(listener_pid)
                if identity is None:
                    raise ConfigurationError(
                        f"could not establish listener identity for port {port}"
                    )
                owners[str(port)] = {
                    "pid": listener_pid,
                    "process_identity": identity,
                }
            record["port_owners"] = owners
            self._persist()
            return deepcopy(record)

    def process_handle(self, process_id: str) -> subprocess.Popen | None:
        return self._handles.get(str(process_id))

    def _mark_dead(self, process_id: str, record: dict[str, Any]) -> None:
        handle = self._handles.get(process_id)
        exit_code = handle.poll() if handle is not None else None
        record["exit_code"] = exit_code
        record["finished_at"] = record.get("finished_at") or _now()
        if record.get("state") == "STOPPING":
            record["state"] = "STOPPED"
        elif record.get("command_class") in {
            "LONG_LIVED_RUNTIME",
            "COGNITION_CLIENT",
        }:
            record["state"] = "FAILED"
        else:
            record["state"] = "EXITED"

    def refresh(self) -> dict[str, Any]:
        changed = False
        with self._lock:
            for process_id, record in self._state["processes"].items():
                if record.get("state") not in ACTIVE_STATES:
                    continue
                pid = int(record["pid"])
                actual_identity = process_identity(pid)
                expected_identity = record.get("process_identity")
                if actual_identity is None:
                    self._mark_dead(process_id, record)
                    changed = True
                    continue

                if actual_identity != expected_identity:
                    record["state"] = "STALE_IDENTITY"
                    record["finished_at"] = _now()
                    record["identity_observed"] = actual_identity
                    changed = True
                    continue
                port_failed = False
                for port, owner in (record.get("port_owners") or {}).items():
                    owner_actual = process_identity(int(owner["pid"]))
                    owner_expected = owner.get("process_identity")
                    if owner_actual is None:
                        record["state"] = "FAILED"
                        record["finished_at"] = _now()
                        record["error"] = f"owned listener for port {port} exited"
                        changed = True
                        port_failed = True
                        break
                    if owner_actual != owner_expected:
                        record["state"] = "STALE_IDENTITY"
                        record["finished_at"] = _now()
                        record["error"] = f"owned listener identity changed for port {port}"
                        record["identity_observed"] = owner_actual
                        changed = True
                        port_failed = True
                        break
                if port_failed:
                    continue
                handle = self._handles.get(process_id)
                if handle is not None and handle.poll() is not None:
                    self._mark_dead(process_id, record)
                    changed = True
            if changed:
                self._persist()
            return self.snapshot(refresh=False)

    def snapshot(self, *, refresh: bool = True) -> dict[str, Any]:
        if refresh:
            return self.refresh()
        with self._lock:
            processes = deepcopy(self._state["processes"])
            active_ids = sorted(
                process_id
                for process_id, record in processes.items()
                if record.get("state") in ACTIVE_STATES
            )
            return {
                "schema": SCHEMA,
                "active_process_ids": active_ids,
                "processes": processes,
                "updated_at": self._state.get("updated_at"),
            }

    def _assert_owned_identity(self, record: dict[str, Any]) -> None:
        actual = process_identity(int(record["pid"]))
        expected = record.get("process_identity")
        if actual != expected:
            record["state"] = "STALE_IDENTITY"
            record["finished_at"] = _now()
            record["identity_observed"] = actual
            self._persist()
            raise IdentityMismatch(
                "refusing to signal process because PID identity no longer matches "
                f"registered ownership: pid={record['pid']}"
            )

    def _assert_owned_port_identities(self, record: dict[str, Any]) -> None:
        for port, owner in (record.get("port_owners") or {}).items():
            actual = process_identity(int(owner["pid"]))
            expected = owner.get("process_identity")
            if actual != expected:
                record["state"] = "STALE_IDENTITY"
                record["finished_at"] = _now()
                record["identity_observed"] = actual
                record["error"] = f"listener ownership changed for port {port}"
                self._persist()
                raise IdentityMismatch(
                    f"refusing to stop process tree because listener identity for "
                    f"port {port} no longer matches registered ownership"
                )

    def stop(self, process_id: str, *, timeout: float = 5.0) -> dict[str, Any]:
        with self._lock:
            record = self._require(process_id)
            if record.get("state") in TERMINAL_STATES:
                return deepcopy(record)
            self._assert_owned_identity(record)
            self._assert_owned_port_identities(record)
            record["state"] = "STOPPING"
            self._persist()
            handle = self._handles.get(str(process_id))
            if os.name == "nt":
                # The venv python.exe on Windows may be a redirector whose child owns
                # the actual server socket.  The owned unit is therefore the verified
                # root process tree, not only the redirector PID.  /T is safe here
                # because root ownership was just verified by creation-time identity.
                subprocess.run(
                    ["taskkill", "/PID", str(record["pid"]), "/T", "/F"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=max(1.0, min(float(timeout), 5.0)),
                    check=False,
                )
            elif handle is not None:
                handle.terminate()
            else:
                os.kill(int(record["pid"]), signal.SIGTERM)

        deadline = time.monotonic() + max(0.1, float(timeout))
        while time.monotonic() < deadline:
            root_alive = not (
                handle is not None and handle.poll() is not None
            ) and (
                process_identity(int(record["pid"])) == record.get("process_identity")
            )
            listener_alive = any(
                process_identity(int(owner["pid"])) == owner.get("process_identity")
                for owner in (record.get("port_owners") or {}).values()
            )
            if not root_alive and not listener_alive:
                break
            time.sleep(0.05)

        with self._lock:
            root_alive = not (
                handle is not None and handle.poll() is not None
            ) and (
                process_identity(int(record["pid"])) == record.get("process_identity")
            )
            listener_alive = any(
                process_identity(int(owner["pid"])) == owner.get("process_identity")
                for owner in (record.get("port_owners") or {}).values()
            )
            if root_alive or listener_alive:
                record["state"] = "FAILED"
                record["finished_at"] = _now()
                record["error"] = "owned process tree did not stop within bounded timeout"
                self._persist()
                raise ProtocolError(
                    f"owned process tree did not stop within bounded timeout: {process_id}"
                )
            self._mark_dead(str(process_id), record)
            if record["state"] != "STOPPED":
                record["state"] = "STOPPED"
            self._persist()
            return deepcopy(record)

    def stop_all_owned(self, *, timeout: float = 5.0) -> list[str]:
        stopped = []
        for process_id in list(self.snapshot()["active_process_ids"]):
            self.stop(process_id, timeout=timeout)
            stopped.append(process_id)
        return stopped

    def reap_completed(self) -> list[str]:
        self.refresh()
        reaped = []
        with self._lock:
            for process_id, record in self._state["processes"].items():
                if record.get("state") not in TERMINAL_STATES:
                    continue
                if record.get("cleanup_policy") != "REAP_COMPLETED":
                    continue
                if record.get("reaped_at"):
                    continue
                handle = self._handles.get(process_id)
                if handle is not None:
                    try:
                        handle.wait(timeout=0)
                    except subprocess.TimeoutExpired:
                        continue
                    self._handles.pop(process_id, None)
                record["reaped_at"] = _now()
                reaped.append(process_id)
            if reaped:
                self._persist()
        return reaped

    def tail_log(
        self,
        process_id: str,
        *,
        max_bytes: int = 32768,
        max_lines: int = 100,
    ) -> str:
        max_bytes = max(1, min(int(max_bytes), 262144))
        max_lines = max(1, min(int(max_lines), 1000))

        with self._lock:
            record = deepcopy(self._require(process_id))
        path = Path(record["log_path"])
        if not path.exists():
            return ""
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes), os.SEEK_SET)
            data = handle.read(max_bytes)
        text = data.decode("utf-8", errors="replace")
        return "\n".join(text.splitlines()[-max_lines:])

    def get(self, process_id: str) -> dict[str, Any]:
        self.refresh()
        with self._lock:
            return deepcopy(self._require(process_id))
