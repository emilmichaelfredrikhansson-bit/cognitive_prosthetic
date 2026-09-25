import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOB = (ROOT / "deploy/systemd/bob-api.service").read_text()
BRIDGE = (ROOT / "deploy/systemd/chatgpt-bridge.service").read_text()


class SystemdUnitTests(unittest.TestCase):
    def test_units_force_loopback_bindings(self):
        self.assertIn("Environment=BOB_HOST=127.0.0.1", BOB)
        self.assertIn("Environment=CHATGPT_BRIDGE_HOST=127.0.0.1", BRIDGE)
        self.assertNotIn("0.0.0.0", BOB + BRIDGE)

    def test_units_share_protected_environment_file(self):
        self.assertIn("EnvironmentFile=/etc/bob/bob.env", BOB)
        self.assertIn("EnvironmentFile=/etc/bob/bob.env", BRIDGE)

    def test_units_run_as_dedicated_runtime_identity(self):
        for unit in (BOB, BRIDGE):
            self.assertIn("User=bob", unit)
            self.assertIn("Group=bob", unit)
            self.assertIn("UMask=0077", unit)

    def test_units_apply_basic_systemd_hardening(self):
        for unit in (BOB, BRIDGE):
            self.assertIn("NoNewPrivileges=true", unit)
            self.assertIn("PrivateTmp=true", unit)
            self.assertIn("ProtectSystem=full", unit)
            self.assertIn("ProtectHome=true", unit)

    def test_browser_profile_write_scope_is_explicit(self):
        self.assertIn("Environment=CHATGPT_PROFILE_PATH=/var/lib/bob/chatgpt-profile", BRIDGE)
        self.assertIn("ReadWritePaths=/var/lib/bob", BRIDGE)
        self.assertIn("ExecStart=/usr/bin/xvfb-run -a ", BRIDGE)


if __name__ == "__main__":
    unittest.main()
