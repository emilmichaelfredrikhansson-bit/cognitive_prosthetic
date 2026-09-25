import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bob_local
import chatgpt_api_server
from bob.driver import ChatGPTBridge


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
            self.assertEqual(env["CHATGPT_CAPTURE_MODE"], "copy")
            self.assertEqual(env["CHATGPT_RESPONSE_TIMEOUT_SECONDS"], "360")
            self.assertEqual(env["CHATGPT_BRIDGE_TIMEOUT_SECONDS"], "420")

    def test_local_launcher_rejects_non_loopback_bindings(self):
        env = {
            "BOB_HOST": "0.0.0.0",
            "CHATGPT_BRIDGE_HOST": "127.0.0.1",
            "BOB_COMPANION_UI_URL": "http://127.0.0.1:5002/",
        }
        with self.assertRaises(RuntimeError):
            bob_local.assert_local_only(env)

    def test_normal_runtime_requires_dedicated_chatgpt_project_url(self):
        env = {
            "BOB_HOST": "127.0.0.1",
            "CHATGPT_BRIDGE_HOST": "127.0.0.1",
            "BOB_COMPANION_UI_URL": "http://127.0.0.1:5002/",
            "BOB_CHATGPT_PROJECT_URL": "",
        }
        with self.assertRaises(RuntimeError):
            bob_local.assert_project_bound(env)

        env["BOB_CHATGPT_PROJECT_URL"] = "https://chatgpt.com/"
        with self.assertRaises(RuntimeError):
            bob_local.assert_project_bound(env)

    def test_bridge_accepts_explicit_non_root_chatgpt_project_target(self):
        target = "https://chatgpt.com/g/g-p-example/project"
        self.assertEqual(chatgpt_api_server.validate_chatgpt_project_url(target), target)

        with self.assertRaises(ValueError):
            chatgpt_api_server.validate_chatgpt_project_url("https://chatgpt.com/")

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

    def test_bridge_exposes_fresh_cognition_endpoint(self):
        routes = {rule.rule for rule in chatgpt_api_server.app.url_map.iter_rules()}
        self.assertIn("/cognition", routes)

    def test_response_timeout_is_bounded_and_bridge_has_headroom(self):
        self.assertEqual(chatgpt_api_server.parse_timeout_seconds("360"), 360)
        with self.assertRaises(RuntimeError):
            chatgpt_api_server.parse_timeout_seconds("29")
        with self.assertRaises(RuntimeError):
            chatgpt_api_server.parse_timeout_seconds("901")
        with patch.dict(
            os.environ,
            {"CHATGPT_BRIDGE_TIMEOUT_SECONDS": "420"},
            clear=False,
        ):
            self.assertEqual(ChatGPTBridge().timeout, 420)

    def test_single_instance_gate_rejects_occupied_runtime_port(self):
        env = {
            "BOB_HOST": "127.0.0.1",
            "BOB_PORT": "5002",
            "CHATGPT_BRIDGE_HOST": "127.0.0.1",
            "CHATGPT_BRIDGE_PORT": "5001",
        }
        with patch("bob_local.socket.socket") as socket_factory:
            socket_factory.return_value.bind.side_effect = OSError("in use")
            with self.assertRaises(RuntimeError):
                bob_local.assert_runtime_ports_free(env)

    def test_only_stateless_tasks_retry_after_browser_loss(self):
        self.assertTrue(
            chatgpt_api_server.task_allows_transparent_browser_retry(
                "cognition_request"
            )
        )
        self.assertFalse(
            chatgpt_api_server.task_allows_transparent_browser_retry("send_message")
        )

    def test_browser_liveness_uses_active_round_trip(self):
        class FakeContext:
            pass

        class LivePage:
            def __init__(self):
                self.probes = 0

            def is_closed(self):
                return False

            def evaluate(self, expression):
                self.probes += 1
                self.last_expression = expression
                return True

        page = LivePage()
        self.assertTrue(
            chatgpt_api_server.browser_session_is_live(page, FakeContext())
        )
        self.assertEqual(page.probes, 1)
        self.assertEqual(page.last_expression, "() => true")

        class DeadPage(LivePage):
            def evaluate(self, expression):
                raise RuntimeError(
                    "Target page, context or browser has been closed"
                )

        self.assertFalse(
            chatgpt_api_server.browser_session_is_live(DeadPage(), FakeContext())
        )

    def test_closed_browser_errors_are_recoverable_but_capture_timeout_is_not(self):
        self.assertTrue(chatgpt_api_server.is_browser_closed_error(
            "Page.goto: Target page, context or browser has been closed"
        ))
        self.assertTrue(chatgpt_api_server.browser_result_needs_recovery({
            "success": False,
            "error": "ChatGPT page is closed",
        }))
        self.assertFalse(chatgpt_api_server.browser_result_needs_recovery({
            "success": False,
            "error": "Timed out waiting for completed assistant response",
        }))

    def test_wait_for_copy_surfaces_closed_page_immediately(self):
        class ClosedPage:
            def is_closed(self):
                return True

        with self.assertRaises(RuntimeError):
            chatgpt_api_server.wait_for_new_assistant_copy(
                ClosedPage(),
                baseline_assistant_count=0,
                timeout=30,
            )

    def test_health_fails_closed_when_worker_knows_browser_is_dead(self):
        class LiveThread:
            def is_alive(self):
                return True

        with (
            patch.object(chatgpt_api_server, "browser_thread", LiveThread()),
            patch.object(chatgpt_api_server, "is_ready", False),
            patch.object(chatgpt_api_server, "startup_error", None),
            patch.object(chatgpt_api_server, "runtime_error", "browser context closed"),
        ):
            response = chatgpt_api_server.app.test_client().get("/health")
            self.assertEqual(response.status_code, 503)
            self.assertFalse(response.get_json()["ready"])
            self.assertEqual(response.get_json()["status"], "recovering")

    def test_live_worker_accepts_task_while_browser_session_needs_recovery(self):
        class LiveThread:
            def is_alive(self):
                return True

        with (
            patch.object(chatgpt_api_server, "browser_thread", LiveThread()),
            patch.object(chatgpt_api_server, "is_ready", False),
            patch.object(chatgpt_api_server, "startup_error", None),
            patch.object(chatgpt_api_server, "runtime_error", "ChatGPT page closed"),
        ):
            self.assertTrue(chatgpt_api_server.bridge_can_accept_tasks())


if __name__ == "__main__":
    unittest.main()
