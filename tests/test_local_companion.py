import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bob_local
import chatgpt_api_server


class LocalCompanionTests(unittest.TestCase):
    def test_env_parser_is_optional_and_bounded_to_key_value_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, ".env.local")
            self.assertEqual(bob_local.parse_env_file(path), {})
            path.write_text(
                "# local only\nBOB_HOST=127.0.0.1\nEMPTY=\nQUOTED='value'\n",
                encoding="utf-8",
            )
            self.assertEqual(
                bob_local.parse_env_file(path),
                {"BOB_HOST": "127.0.0.1", "EMPTY": "", "QUOTED": "value"},
            )

    def test_local_launcher_defaults_to_loopback(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            env = bob_local.build_env(Path(tmp, "missing.env"))
            self.assertEqual(env["BOB_HOST"], "127.0.0.1")
            self.assertEqual(env["CHATGPT_BRIDGE_HOST"], "127.0.0.1")
            self.assertEqual(env["BOB_COMPANION_UI_URL"], "http://127.0.0.1:5002/")

    def test_local_launcher_rejects_non_loopback_bindings(self):
        env = {
            "BOB_HOST": "0.0.0.0",
            "CHATGPT_BRIDGE_HOST": "127.0.0.1",
            "BOB_COMPANION_UI_URL": "http://127.0.0.1:5002/",
        }
        with self.assertRaises(RuntimeError):
            bob_local.assert_local_only(env)

    def test_bridge_accepts_only_loopback_companion_ui(self):
        self.assertEqual(
            chatgpt_api_server.validate_companion_ui_url("http://localhost:5002/"),
            "http://localhost:5002/",
        )
        self.assertEqual(
            chatgpt_api_server.validate_companion_ui_url("http://127.0.0.1:5002/"),
            "http://127.0.0.1:5002/",
        )

    def test_bridge_rejects_remote_companion_ui(self):
        with self.assertRaises(ValueError):
            chatgpt_api_server.validate_companion_ui_url("https://example.com/bob")


if __name__ == "__main__":
    unittest.main()
