import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from bob.errors import ConfigurationError, IdentityMismatch, ProtocolError
from bob.process_supervision import ProcessSupervisor, process_identity


class ProcessSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.supervisor = ProcessSupervisor(
            self.root / "processes.json",
            allowed_executables=[sys.executable],
        )

    def tearDown(self):
        snapshot = self.supervisor.snapshot()
        for process_id in snapshot["active_process_ids"]:
            try:
                self.supervisor.stop(process_id, timeout=2)
            except Exception:
                handle = self.supervisor.process_handle(process_id)
                if handle is not None and handle.poll() is None:
                    handle.terminate()
                    handle.wait(timeout=5)
        self.temp.cleanup()

    def wait_terminal(self, process_id, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            record = self.supervisor.get(process_id)
            if record["state"] not in {"RUNNING", "STOPPING"}:
                return record
            time.sleep(0.05)
        self.fail(f"process did not become terminal: {process_id}")

    def wait_port_busy(self, port, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.supervisor._port_is_available(port):
                return
            time.sleep(0.05)
        self.fail(f"port never became busy: {port}")

    def test_registered_child_start_exit_reap_and_bounded_log_tail(self):
        record = self.supervisor.start(
            purpose="test-output",
            command_class="TEST",
            command=[
                sys.executable,
                "-c",
                "for i in range(40): print(f'line-{i}', flush=True)",
            ],
            cwd=self.root,
        )
        finished = self.wait_terminal(record["process_id"])
        self.assertEqual(finished["state"], "EXITED")
        tail = self.supervisor.tail_log(record["process_id"], max_lines=5)
        self.assertLessEqual(len(tail.splitlines()), 5)
        self.assertIn("line-39", tail)
        reaped = self.supervisor.reap_completed()
        self.assertIn(record["process_id"], reaped)
        self.assertIsNotNone(self.supervisor.get(record["process_id"])["reaped_at"])

    def test_unknown_external_pid_is_never_auto_killed(self):
        external = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"]
        )
        try:
            self.supervisor.refresh()
            self.assertIsNone(external.poll())
            with self.assertRaises(ProtocolError):
                self.supervisor.stop("proc-not-owned")
            self.assertIsNone(external.poll())
        finally:
            external.terminate()
            external.wait(timeout=5)

    def test_stale_pid_identity_fails_closed_without_signal(self):
        record = self.supervisor.start(
            purpose="stale-identity",
            command_class="PROBE",
            command=[sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=self.root,
        )
        handle = self.supervisor.process_handle(record["process_id"])
        with patch(
            "bob.process_supervision.process_identity",
            return_value="different-start-identity",
        ):
            with self.assertRaises(IdentityMismatch):
                self.supervisor.stop(record["process_id"])
        self.assertIsNone(handle.poll())
        handle.terminate()
        handle.wait(timeout=5)

    def test_external_port_collision_is_detected_without_killing_owner(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        try:
            with self.assertRaises(ConfigurationError):
                self.supervisor.start(
                    purpose="must-not-replace-external",
                    command_class="PROBE",
                    command=[sys.executable, "-c", "print('never')"],
                    cwd=self.root,
                    owns_ports=[port],
                )
            listener.getsockname()
        finally:
            listener.close()

    def test_second_owned_runtime_on_same_port_is_blocked(self):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        script = (
            "import socket,time; "
            f"s=socket.socket(); s.bind(('127.0.0.1',{port})); "
            "s.listen(); print('READY', flush=True); time.sleep(30)"
        )
        first = self.supervisor.start(
            purpose="runtime-one",
            command_class="LONG_LIVED_RUNTIME",
            command=[sys.executable, "-c", script],
            cwd=self.root,
            owns_ports=[port],
        )
        self.wait_port_busy(port)
        bound = self.supervisor.bind_owned_ports(first["process_id"])
        port_owner = bound["port_owners"][str(port)]
        self.assertGreater(port_owner["pid"], 0)
        self.assertTrue(port_owner["process_identity"])
        with self.assertRaises(ProtocolError):
            self.supervisor.start(
                purpose="runtime-two",
                command_class="LONG_LIVED_RUNTIME",
                command=[sys.executable, "-c", "import time; time.sleep(30)"],
                cwd=self.root,
                owns_ports=[port],
            )
        self.assertEqual(self.supervisor.get(first["process_id"])["state"], "RUNNING")
        stopped = self.supervisor.stop(first["process_id"], timeout=3)
        self.assertEqual(stopped["state"], "STOPPED")
        self.assertTrue(self.supervisor._port_is_available(port))

    def test_restart_reconstructs_live_owned_process(self):
        record = self.supervisor.start(
            purpose="survive-supervisor-restart",
            command_class="PROBE",
            command=[sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=self.root,
        )
        restarted = ProcessSupervisor(
            self.root / "processes.json",
            allowed_executables=[sys.executable],
        )
        recovered = restarted.get(record["process_id"])
        self.assertEqual(recovered["pid"], record["pid"])
        self.assertEqual(recovered["process_identity"], record["process_identity"])
        self.assertEqual(recovered["state"], "RUNNING")

    def test_dead_runtime_becomes_failed_and_is_not_restarted(self):
        record = self.supervisor.start(
            purpose="crash-once",
            command_class="LONG_LIVED_RUNTIME",
            command=[sys.executable, "-c", "raise SystemExit(7)"],
            cwd=self.root,
        )
        finished = self.wait_terminal(record["process_id"])
        self.assertEqual(finished["state"], "FAILED")
        original_pid = finished["pid"]
        for _ in range(3):
            current = self.supervisor.refresh()["processes"][record["process_id"]]
            self.assertEqual(current["state"], "FAILED")
            self.assertEqual(current["pid"], original_pid)
            self.assertEqual(current["restart_count"], 0)

    def test_stop_owned_process_is_bounded_and_marks_stopped(self):
        record = self.supervisor.start(
            purpose="bounded-stop",
            command_class="PROBE",
            command=[sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=self.root,
        )
        stopped = self.supervisor.stop(record["process_id"], timeout=3)
        self.assertEqual(stopped["state"], "STOPPED")
        self.assertNotIn(
            record["process_id"],
            self.supervisor.snapshot()["active_process_ids"],
        )


if __name__ == "__main__":
    unittest.main()
