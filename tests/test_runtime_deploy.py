import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOB_UNIT = (ROOT / "deploy/systemd/bob-api.service").read_text()
BRIDGE_UNIT = (ROOT / "deploy/systemd/chatgpt-bridge.service").read_text()
INSTALLER = (ROOT / "deploy/install_runtime.sh").read_text()
ROLLBACK = (ROOT / "deploy/rollback_release.sh").read_text()
ACCEPTANCE = (ROOT / "deploy/runtime_acceptance.py").read_text()

spec = importlib.util.spec_from_file_location("runtime_doctor", ROOT / "deploy/runtime_doctor.py")
runtime_doctor = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runtime_doctor)


class RuntimeDeployTests(unittest.TestCase):
    def test_systemd_units_are_real_multiline_files(self):
        self.assertNotIn(r"\n", BOB_UNIT)
        self.assertNotIn(r"\n", BRIDGE_UNIT)
        self.assertTrue(BOB_UNIT.startswith("[Unit]\n"))
        self.assertTrue(BRIDGE_UNIT.startswith("[Unit]\n"))

    def test_bridge_has_headless_host_display_and_shared_browser_path(self):
        self.assertIn("ExecStart=/usr/bin/xvfb-run -a ", BRIDGE_UNIT)
        self.assertIn("Environment=PLAYWRIGHT_BROWSERS_PATH=/opt/bob/ms-playwright", BRIDGE_UNIT)

    def test_installer_requires_exact_commit_and_never_starts_services(self):
        self.assertIn("BOB_RELEASE_SHA must be a full 40-character Git commit SHA", INSTALLER)
        self.assertIn("does not match requested BOB_RELEASE_SHA", INSTALLER)
        self.assertIn("systemctl enable bob-api.service chatgpt-bridge.service", INSTALLER)
        self.assertNotIn("systemctl start ", INSTALLER)
        self.assertNotIn("systemctl restart ", INSTALLER)

    def test_installer_creates_root_owned_secret_file(self):
        self.assertIn('install -m 0600 -o root -g root /dev/null "$ENV_DIR/bob.env"', INSTALLER)
        self.assertIn("GITHUB_TOKEN=", INSTALLER)
        self.assertNotIn("hf_", INSTALLER)

    def test_doctor_accepts_offline_ready_fixture_without_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = root / "opt/bob"
            env = root / "etc/bob/bob.env"
            state = root / "var/lib/bob"
            units = root / "etc/systemd/system"
            (app / "current").mkdir(parents=True)
            (app / "venv/bin").mkdir(parents=True)
            (app / "venv/bin/python").write_text("")
            (state / "chatgpt-profile").mkdir(parents=True)
            units.mkdir(parents=True)
            (units / "bob-api.service").write_text(BOB_UNIT)
            (units / "chatgpt-bridge.service").write_text(BRIDGE_UNIT)
            env.parent.mkdir(parents=True)
            env.write_text("BOB_HOST=127.0.0.1\nCHATGPT_BRIDGE_HOST=127.0.0.1\n")
            env.chmod(0o600)
            old = runtime_doctor.shutil.which
            runtime_doctor.shutil.which = lambda name: "/usr/bin/xvfb-run" if name == "xvfb-run" else old(name)
            try:
                result = runtime_doctor.inspect_runtime(app, env, state, units)
            finally:
                runtime_doctor.shutil.which = old
            self.assertTrue(result["ok"], result)

    def test_doctor_fails_closed_for_missing_credentials_and_non_loopback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = root / "opt/bob"
            env = root / "etc/bob/bob.env"
            state = root / "var/lib/bob"
            units = root / "etc/systemd/system"
            (app / "current").mkdir(parents=True)
            (app / "venv/bin").mkdir(parents=True)
            (app / "venv/bin/python").write_text("")
            (state / "chatgpt-profile").mkdir(parents=True)
            units.mkdir(parents=True)
            (units / "bob-api.service").write_text(BOB_UNIT)
            (units / "chatgpt-bridge.service").write_text(BRIDGE_UNIT)
            env.parent.mkdir(parents=True)
            env.write_text("BOB_HOST=0.0.0.0\nCHATGPT_BRIDGE_HOST=127.0.0.1\n")
            env.chmod(0o600)
            old = runtime_doctor.shutil.which
            runtime_doctor.shutil.which = lambda name: "/usr/bin/xvfb-run" if name == "xvfb-run" else old(name)
            try:
                result = runtime_doctor.inspect_runtime(app, env, state, units, require_credentials=True)
            finally:
                runtime_doctor.shutil.which = old
            self.assertFalse(result["ok"])
            failed = {item["name"] for item in result["checks"] if item["status"] == "FAIL"}
            self.assertIn("bob_host-loopback", failed)
            self.assertIn("credential:GITHUB_TOKEN", failed)

    def test_rollback_requires_exact_installed_release_and_restart_is_opt_in(self):
        self.assertIn("release not installed", ROLLBACK)
        self.assertIn("BOB_RESTART_AFTER_ROLLBACK:-0", ROLLBACK)
        self.assertNotIn("BOB_RESTART_AFTER_ROLLBACK:-1", ROLLBACK)

    def test_acceptance_is_offline_by_default_and_live_is_explicit(self):
        self.assertIn('parser.add_argument("--live", action="store_true"', ACCEPTANCE)
        self.assertIn("SKIPPED: rerun with --live on the installed host", ACCEPTANCE)
        self.assertIn("provider-preflight", ACCEPTANCE)
        self.assertIn("http://127.0.0.1:5002/bob/health", ACCEPTANCE)
        self.assertIn("http://127.0.0.1:5001/health", ACCEPTANCE)


if __name__ == "__main__":
    unittest.main()
