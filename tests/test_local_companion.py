import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bob_local
import chatgpt_api_server
from bob.driver import ChatGPTBridge
from bob.errors import IdentityMismatch


class LocalCompanionTests(unittest.TestCase):
    def test_cleanup_does_not_mask_primary_failure_on_stale_process_identity(self):
        class StaleSupervisor:
            def __init__(self):
                self.calls = []

            def stop(self, process_id):
                self.calls.append(process_id)
                raise IdentityMismatch("stale child identity")

        supervisor = StaleSupervisor()
        self.assertFalse(
            bob_local.stop_supervised_process(supervisor, "proc-stale")
        )
        self.assertEqual(supervisor.calls, ["proc-stale"])
        self.assertFalse(bob_local.stop_supervised_process(supervisor, None))

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
            self.assertEqual(env["CHATGPT_SUBMISSION_TIMEOUT_SECONDS"], "12")
            self.assertEqual(env["CHATGPT_BRIDGE_TIMEOUT_SECONDS"], "600")
            self.assertEqual(env["CHATGPT_FRESH_CHAT_MIN_INTERVAL_SECONDS"], "10")
            self.assertEqual(env["CHATGPT_TRAFFIC_JITTER_SECONDS"], "3")
            self.assertEqual(env["CHATGPT_RATE_LIMIT_BACKOFF_SECONDS"], "15,30,60,120")
            self.assertEqual(env["BOB_MAX_PARALLEL_RUNS_PER_REPOSITORY"], "3")
            self.assertEqual(env["BOB_CANONICAL_REF"], "feat/bob-core-v1")
            self.assertTrue(env["BOB_PROCESS_SUPERVISOR_PATH"].endswith("process_supervisor.json"))
            self.assertTrue(env["BOB_CONTINUATION_STORE_PATH"].endswith("blocked_continuations.json"))
            self.assertTrue(env["BOB_PENDING_EFFECT_STORE_PATH"].endswith("pending_effects.json"))
            self.assertTrue(env["BOB_SELFDEV_QUEUE_PATH"].endswith("self_development.json"))

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
        self.assertEqual(
            chatgpt_api_server.parse_nonnegative_seconds(
                "10", default=5, name="TEST_DELAY"
            ),
            10.0,
        )
        self.assertEqual(
            chatgpt_api_server.parse_backoff_seconds("15,30,60,120"),
            (15.0, 30.0, 60.0, 120.0),
        )
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

    def test_launcher_rejects_bridge_timeout_smaller_than_traffic_budget(self):
        env = {
            "CHATGPT_RESPONSE_TIMEOUT_SECONDS": "360",
            "CHATGPT_BRIDGE_TIMEOUT_SECONDS": "420",
            "CHATGPT_FRESH_CHAT_MIN_INTERVAL_SECONDS": "10",
            "CHATGPT_TRAFFIC_JITTER_SECONDS": "3",
            "CHATGPT_RATE_LIMIT_BACKOFF_SECONDS": "15,30,60,120",
        }
        with self.assertRaisesRegex(RuntimeError, "traffic-control budget"):
            bob_local.assert_chatgpt_traffic_budget(env)

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
        self.assertFalse(chatgpt_api_server.browser_result_needs_recovery({
            "success": False,
            "error": "CHATGPT_TRANSIENT_UI:RATE_LIMITED",
        }))

    def test_transient_rate_limit_ui_is_detected_without_logging_raw_text(self):
        class Item:
            def is_visible(self):
                return True

            def inner_text(self, timeout=None):
                return "Too many requests. Please try again later."

        class Items:
            def __init__(self, values):
                self.values = values

            def count(self):
                return len(self.values)

            def nth(self, index):
                return self.values[index]

        class Page:
            def locator(self, selector):
                if selector == '[role="alert"]':
                    return Items([Item()])
                return Items([])

        page = Page()
        self.assertEqual(
            chatgpt_api_server.detect_chatgpt_transient_ui_error(page),
            "RATE_LIMITED",
        )
        page.is_closed = lambda: False
        with self.assertRaisesRegex(RuntimeError, "CHATGPT_TRANSIENT_UI:RATE_LIMITED"):
            chatgpt_api_server.wait_for_new_assistant_copy(
                page,
                baseline_assistant_count=0,
                timeout=30,
            )

    def test_transient_rate_limit_ui_is_detected_on_text_error_surface(self):
        class Item:
            def is_visible(self):
                return True

            def inner_text(self, timeout=None):
                return "Too many requests. Please try again later."

        class Items:
            def __init__(self, values):
                self.values = values

            def count(self):
                return len(self.values)

            def nth(self, index):
                return self.values[index]

        class Page:
            def locator(self, selector):
                if selector == '[class*="text-token-text-error"]':
                    return Items([Item()])
                return Items([])

        self.assertEqual(
            chatgpt_api_server.detect_chatgpt_transient_ui_error(Page()),
            "RATE_LIMITED",
        )

    def test_network_diagnostics_keep_only_sanitized_metadata(self):
        class Request:
            method = "POST"

        class Response:
            url = "https://chatgpt.com/backend-api/conversation/1234567890abcdef1234567890abcdef?secret=x"
            status = 429
            request = Request()

        chatgpt_api_server.network_diagnostics.clear()
        chatgpt_api_server.record_chatgpt_network_response(Response())
        self.assertEqual(len(chatgpt_api_server.network_diagnostics), 1)
        event = chatgpt_api_server.network_diagnostics[0]
        self.assertEqual(event["status"], 429)
        self.assertEqual(event["method"], "POST")
        self.assertNotIn("secret", event["path"])
        self.assertIn(":id", event["path"])

    def test_browser_diagnostics_are_structural_and_sanitized(self):
        class Composer:
            def evaluate(self, _expression):
                return "abc"

        class Page:
            url = "https://chatgpt.com/c/example"

        with (
            patch.object(chatgpt_api_server, "find_textarea", return_value=Composer()),
            patch.object(chatgpt_api_server, "find_send_button", return_value=(object(), False)),
            patch.object(chatgpt_api_server, "user_message_count", return_value=1),
            patch.object(chatgpt_api_server, "assistant_count", return_value=0),
            patch.object(chatgpt_api_server, "conversation_turn_count", return_value=1),
            patch.object(chatgpt_api_server, "assistant_copy_candidates", return_value=[]),
            patch.object(chatgpt_api_server, "detect_chatgpt_transient_ui_error", return_value="RATE_LIMITED"),
        ):
            snapshot = chatgpt_api_server.browser_diagnostic_snapshot(Page())

        self.assertTrue(snapshot["success"])
        self.assertTrue(snapshot["conversation_route"])
        self.assertEqual(snapshot["user_count"], 1)
        self.assertEqual(snapshot["composer_length"], 3)
        self.assertTrue(snapshot["send_enabled"])
        self.assertEqual(snapshot["transient_ui"], "RATE_LIMITED")
        self.assertNotIn("prompt", snapshot)
        self.assertNotIn("response", snapshot)

    def test_populate_composer_uses_keyboard_insert_for_contenteditable(self):
        class Composer:
            def __init__(self):
                self.pressed = []
                self.focused = []

            def focus(self, timeout=None):
                self.focused.append(timeout)

            def evaluate(self, _expression):
                return {"tag": "div", "contenteditable": "true"}

            def press(self, key, timeout=None):
                self.pressed.append((key, timeout))

            def fill(self, _value):
                raise AssertionError("contenteditable must not use fill")

        class Keyboard:
            def __init__(self):
                self.inserted = []

            def insert_text(self, value):
                self.inserted.append(value)

        class Page:
            keyboard = Keyboard()

        composer = Composer()
        page = Page()
        mode = chatgpt_api_server.populate_composer(page, composer, "abc")

        self.assertEqual(mode, "contenteditable_insert_text")
        self.assertEqual(composer.focused, [5_000])
        self.assertEqual(
            composer.pressed,
            [("Control+A", 5_000), ("Backspace", 5_000)],
        )
        self.assertEqual(page.keyboard.inserted, ["abc"])

    def test_submission_actuation_uses_enter_when_send_control_is_enabled(self):
        class Button:
            def __init__(self, enabled=True):
                self.enabled = enabled
                self.clicked = False

            def is_visible(self):
                return True

            def is_enabled(self):
                return self.enabled

            def evaluate(self, _expression):
                return '<button data-testid="send-button"></button>'

            def click(self, timeout=None):
                self.clicked = True

        class Items:
            def __init__(self, button):
                self.button = button

            def all(self):
                return [self.button]

        class Page:
            def __init__(self, button):
                self.button = button

            def locator(self, _selector):
                return Items(self.button)

        class Textarea:
            def __init__(self):
                self.pressed = False

            def press(self, _key):
                self.pressed = True

        button = Button()
        textarea = Textarea()
        with patch.object(
            chatgpt_api_server,
            "detect_chatgpt_transient_ui_error",
            return_value=None,
        ):
            actuator = chatgpt_api_server.actuate_submission(Page(button), textarea)
        self.assertEqual(actuator, "input_enter")
        self.assertFalse(button.clicked)
        self.assertTrue(textarea.pressed)

    def test_submission_actuation_refuses_visible_disabled_send_control(self):
        class Button:
            def is_visible(self):
                return True

            def is_enabled(self):
                return False

            def evaluate(self, _expression):
                return '<button data-testid="send-button" disabled></button>'

        class Items:
            def all(self):
                return [Button()]

        class Page:
            def locator(self, _selector):
                return Items()

        with (
            patch.object(chatgpt_api_server, "detect_chatgpt_transient_ui_error", return_value=None),
            self.assertRaisesRegex(RuntimeError, "SEND_CONTROL_DISABLED"),
        ):
            chatgpt_api_server.actuate_submission(
                Page(),
                object(),
                timeout=0,
            )

    def test_submission_actuation_waits_for_temporarily_disabled_send_control(self):
        class Button:
            def __init__(self):
                self.enabled_checks = 0

            def is_visible(self):
                return True

            def is_enabled(self):
                self.enabled_checks += 1
                return self.enabled_checks >= 3

            def evaluate(self, _expression):
                return '<button data-testid="send-button"></button>'

        class Items:
            def __init__(self, button):
                self.button = button

            def all(self):
                return [self.button]

        class Page:
            def __init__(self, button):
                self.button = button

            def locator(self, _selector):
                return Items(self.button)

        class Textarea:
            def __init__(self):
                self.pressed = []

            def press(self, key):
                self.pressed.append(key)

        button = Button()
        textarea = Textarea()
        with (
            patch.object(
                chatgpt_api_server,
                "detect_chatgpt_transient_ui_error",
                return_value=None,
            ),
            patch.object(
                chatgpt_api_server,
                "detect_chatgpt_processing_ui",
                return_value=False,
            ),
            patch.object(chatgpt_api_server.time, "sleep", return_value=None),
        ):
            actuator = chatgpt_api_server.actuate_submission(
                Page(button),
                textarea,
                timeout=1,
            )

        self.assertEqual(actuator, "input_enter")
        self.assertEqual(textarea.pressed, ["Enter"])
        self.assertGreaterEqual(button.enabled_checks, 3)

    def test_processing_status_is_detected_without_becoming_transient_error(self):
        class Status:
            def is_visible(self):
                return True

            def inner_text(self, timeout=None):
                return "Våra system bearbetar den här begäran lite till innan de svarar."

        class Items:
            def count(self):
                return 1

            def nth(self, _index):
                return Status()

        class Page:
            def locator(self, _selector):
                return Items()

        page = Page()
        self.assertTrue(chatgpt_api_server.detect_chatgpt_processing_ui(page))
        self.assertIsNone(chatgpt_api_server.detect_chatgpt_transient_ui_error(page))

    def test_submission_materialization_accepts_new_conversation_state(self):
        class OpenPage:
            def is_closed(self):
                return False

        page = OpenPage()
        with (
            patch.object(chatgpt_api_server, "detect_chatgpt_transient_ui_error", return_value=None),
            patch.object(chatgpt_api_server, "user_message_count", return_value=1),
            patch.object(chatgpt_api_server, "conversation_turn_count", return_value=1),
            patch.object(chatgpt_api_server, "assistant_count", return_value=0),
        ):
            snapshot = chatgpt_api_server.wait_for_submission_materialization(
                page,
                baseline_user_count=0,
                baseline_turn_count=0,
                baseline_assistant_count=0,
                timeout=1,
            )
        self.assertEqual(snapshot["user"], 1)
        self.assertEqual(snapshot["conversation_turn"], 1)

    def test_submission_materialization_uses_bounded_playwright_probe(self):
        class Handle:
            def json_value(self):
                return {
                    "user": 1,
                    "conversation_turn": 1,
                    "assistant": 0,
                    "transient": None,
                }

        class OpenPage:
            url = "https://chatgpt.com/c/example"

            def __init__(self):
                self.timeouts = []

            def is_closed(self):
                return False

            def wait_for_function(
                self,
                _expression,
                *,
                arg,
                timeout,
                polling,
            ):
                self.timeouts.append((timeout, polling, arg))
                return Handle()

        page = OpenPage()
        with (
            patch.object(
                chatgpt_api_server,
                "backend_submission_error_since",
                return_value=None,
            ),
            patch.object(
                chatgpt_api_server,
                "backend_submission_accepted_since",
                return_value=False,
            ),
        ):
            snapshot = chatgpt_api_server.wait_for_submission_materialization(
                page,
                baseline_user_count=0,
                baseline_turn_count=0,
                baseline_assistant_count=0,
                timeout=0.5,
            )

        self.assertEqual(snapshot["user"], 1)
        self.assertEqual(snapshot["conversation_turn"], 1)
        self.assertEqual(len(page.timeouts), 1)
        timeout_ms, polling_ms, args = page.timeouts[0]
        self.assertLessEqual(timeout_ms, 500)
        self.assertLessEqual(polling_ms, 250)
        self.assertEqual(args["user"], 0)

    def test_submission_materialization_accepts_backend_before_dom_probe(self):
        class OpenPage:
            def is_closed(self):
                raise AssertionError("DOM probe should not run after backend acceptance")

            def wait_for_function(self, *_args, **_kwargs):
                raise AssertionError("DOM probe should not run after backend acceptance")

        with (
            patch.object(
                chatgpt_api_server,
                "backend_submission_error_since",
                return_value=None,
            ),
            patch.object(
                chatgpt_api_server,
                "backend_submission_accepted_since",
                return_value=True,
            ),
        ):
            snapshot = chatgpt_api_server.wait_for_submission_materialization(
                OpenPage(),
                baseline_user_count=0,
                baseline_turn_count=0,
                baseline_assistant_count=0,
                baseline_network_at=123.0,
                timeout=0.5,
            )

        self.assertTrue(snapshot["backend_accepted"])

    def test_submission_materialization_accepts_verified_backend_post(self):
        class OpenPage:
            url = "https://chatgpt.com/g/g-example/project"

            def is_closed(self):
                return False

        with (
            patch.object(chatgpt_api_server, "detect_chatgpt_transient_ui_error", return_value=None),
            patch.object(chatgpt_api_server, "user_message_count", return_value=0),
            patch.object(chatgpt_api_server, "conversation_turn_count", return_value=0),
            patch.object(chatgpt_api_server, "assistant_count", return_value=0),
            patch.object(chatgpt_api_server, "backend_submission_accepted_since", return_value=True),
        ):
            snapshot = chatgpt_api_server.wait_for_submission_materialization(
                OpenPage(),
                baseline_user_count=0,
                baseline_turn_count=0,
                baseline_assistant_count=0,
                baseline_network_at=123.0,
                timeout=1,
            )
        self.assertTrue(snapshot["backend_accepted"])

    def test_backend_submission_error_classifies_payload_too_large(self):
        chatgpt_api_server.network_diagnostics.clear()
        chatgpt_api_server.network_diagnostics.append(
            {
                "at": 200.0,
                "method": "POST",
                "path": "/backend-api/f/conversation",
                "status": 413,
            }
        )
        try:
            self.assertEqual(
                chatgpt_api_server.backend_submission_error_since(100.0),
                "PAYLOAD_TOO_LARGE",
            )
        finally:
            chatgpt_api_server.network_diagnostics.clear()

    def test_submission_materialization_surfaces_backend_payload_too_large(self):
        class OpenPage:
            url = "https://chatgpt.com/c/example"

            def is_closed(self):
                return False

        with (
            patch.object(chatgpt_api_server, "detect_chatgpt_transient_ui_error", return_value=None),
            patch.object(chatgpt_api_server, "backend_submission_error_since", return_value="PAYLOAD_TOO_LARGE"),
            self.assertRaisesRegex(RuntimeError, "PAYLOAD_TOO_LARGE"),
        ):
            chatgpt_api_server.wait_for_submission_materialization(
                OpenPage(),
                baseline_user_count=0,
                baseline_turn_count=0,
                baseline_assistant_count=0,
                baseline_network_at=123.0,
                timeout=1,
            )

    def test_submission_materialization_does_not_accept_conversation_transition_alone(self):
        class OpenPage:
            url = "https://chatgpt.com/c/new-conversation"

            def is_closed(self):
                return False

        with (
            patch.object(chatgpt_api_server, "detect_chatgpt_transient_ui_error", return_value=None),
            patch.object(chatgpt_api_server, "user_message_count", return_value=0),
            patch.object(chatgpt_api_server, "conversation_turn_count", return_value=0),
            patch.object(chatgpt_api_server, "assistant_count", return_value=0),
        ):
            snapshot = chatgpt_api_server.wait_for_submission_materialization(
                OpenPage(),
                baseline_user_count=0,
                baseline_turn_count=0,
                baseline_assistant_count=0,
                baseline_url="https://chatgpt.com/g/g-example/project",
                timeout=0.02,
            )
        self.assertIsNone(snapshot)

    def test_submission_materialization_does_not_accept_composer_clear_alone(self):
        class OpenPage:
            url = "https://chatgpt.com/c/same-conversation"

            def is_closed(self):
                return False

        class Composer:
            def evaluate(self, _expression):
                return ""

        with (
            patch.object(chatgpt_api_server, "detect_chatgpt_transient_ui_error", return_value=None),
            patch.object(chatgpt_api_server, "user_message_count", return_value=0),
            patch.object(chatgpt_api_server, "conversation_turn_count", return_value=0),
            patch.object(chatgpt_api_server, "assistant_count", return_value=0),
        ):
            snapshot = chatgpt_api_server.wait_for_submission_materialization(
                OpenPage(),
                baseline_user_count=0,
                baseline_turn_count=0,
                baseline_assistant_count=0,
                baseline_url="https://chatgpt.com/c/same-conversation",
                composer=Composer(),
                baseline_composer_length=4,
                timeout=0.02,
            )
        self.assertIsNone(snapshot)

    def test_send_message_surfaces_distinct_submission_failure(self):
        class Textarea:
            def focus(self, timeout=None):
                return None

            def fill(self, _value, timeout=None):
                return None

        class Keyboard:
            def press(self, _key):
                return None

        class Page:
            keyboard = Keyboard()

        with (
            patch.object(chatgpt_api_server, "find_textarea", return_value=Textarea()),
            patch.object(chatgpt_api_server, "assistant_count", return_value=0),
            patch.object(chatgpt_api_server, "user_message_count", return_value=0),
            patch.object(chatgpt_api_server, "conversation_turn_count", return_value=0),
            patch.object(chatgpt_api_server, "actuate_submission", return_value="test_actuator"),
            patch.object(chatgpt_api_server, "wait_for_submission_materialization", return_value=None),
            patch.object(chatgpt_api_server.time, "sleep", return_value=None),
        ):
            result = chatgpt_api_server.send_message(Page(), "test")
        self.assertFalse(result["success"])
        self.assertEqual(
            result["error"],
            "CHATGPT_SUBMISSION_FAILED:NO_CONVERSATION_TURN",
        )

    def test_send_message_replays_once_after_blank_project_transition(self):
        class Textarea:
            def __init__(self):
                self.fills = []
                self.focus_timeouts = []

            def focus(self, timeout=None):
                self.focus_timeouts.append(timeout)

            def fill(self, value, timeout=None):
                self.fills.append(value)

        class Page:
            url = "https://chatgpt.com/g/g-example/project"

        page = Page()
        initial = Textarea()
        recovery = Textarea()
        materialization_calls = []

        def materialize(*_args, **_kwargs):
            materialization_calls.append(True)
            if len(materialization_calls) == 1:
                page.url = "https://chatgpt.com/c/new-conversation"
                return None
            return {"user": 1, "conversation_turn": 1, "assistant": 0}

        with (
            patch.object(chatgpt_api_server, "find_textarea", side_effect=[initial, recovery]),
            patch.object(chatgpt_api_server, "assistant_count", return_value=0),
            patch.object(chatgpt_api_server, "user_message_count", return_value=0),
            patch.object(chatgpt_api_server, "conversation_turn_count", return_value=0),
            patch.object(chatgpt_api_server, "composer_text_length", side_effect=[4, 0, 4]),
            patch.object(chatgpt_api_server, "actuate_submission", side_effect=["input_enter", "input_enter"]),
            patch.object(chatgpt_api_server, "wait_for_submission_materialization", side_effect=materialize),
            patch.object(chatgpt_api_server, "detect_chatgpt_transient_ui_error", return_value=None),
            patch.object(chatgpt_api_server, "wait_for_new_assistant_copy", return_value=True),
            patch.object(chatgpt_api_server, "capture_response", return_value="ok"),
            patch.object(chatgpt_api_server.time, "sleep", return_value=None),
        ):
            result = chatgpt_api_server.send_message(page, "same prompt")

        self.assertTrue(result["success"])
        self.assertEqual(len(materialization_calls), 2)
        self.assertEqual(initial.fills, ["same prompt"])
        self.assertEqual(recovery.fills, ["same prompt"])

    def test_wait_for_copy_accepts_new_global_message_copy_control(self):
        class OpenPage:
            def is_closed(self):
                return False

        with (
            patch.object(chatgpt_api_server, "detect_chatgpt_transient_ui_error", return_value=None),
            patch.object(chatgpt_api_server, "assistant_count", return_value=0),
            patch.object(chatgpt_api_server, "global_message_copy_candidates", return_value=[object()]),
        ):
            self.assertTrue(
                chatgpt_api_server.wait_for_new_assistant_copy(
                    OpenPage(),
                    baseline_assistant_count=0,
                    baseline_copy_count=0,
                    timeout=1,
                )
            )

    def test_capture_response_falls_back_to_global_message_copy(self):
        class Candidate:
            def is_visible(self):
                return True

            def click(self, timeout=None, force=False):
                return None

        class Page:
            def evaluate(self, _expression):
                return "copied response"

        with (
            patch.object(chatgpt_api_server, "assistant_copy_candidates", return_value=[]),
            patch.object(chatgpt_api_server, "global_message_copy_candidates", return_value=[Candidate()]),
            patch.object(chatgpt_api_server.time, "sleep", return_value=None),
        ):
            self.assertEqual(
                chatgpt_api_server.capture_response(Page()),
                "copied response",
            )

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

    def test_browser_tasks_have_private_result_channels(self):
        with patch.object(chatgpt_api_server, "request_registry", {}):
            first, first_queue = chatgpt_api_server.make_browser_task(
                "cognition_request",
                request_id="req-one",
                tags={"run_id": "run-one"},
                prompt="one",
            )
            second, second_queue = chatgpt_api_server.make_browser_task(
                "cognition_request",
                request_id="req-two",
                tags={"run_id": "run-two"},
                prompt="two",
            )

            chatgpt_api_server.deliver_browser_result(
                second,
                {"success": True, "response": "two"},
            )
            self.assertTrue(first_queue.empty())
            delivered = second_queue.get_nowait()
            self.assertEqual(delivered["request_id"], "req-two")
            self.assertEqual(delivered["run_id"], "run-two")

            chatgpt_api_server.deliver_browser_result(
                first,
                {"success": True, "response": "one"},
            )
            delivered_first = first_queue.get_nowait()
            self.assertEqual(delivered_first["request_id"], "req-one")
            self.assertEqual(delivered_first["run_id"], "run-one")

    def test_duplicate_browser_request_id_is_rejected(self):
        with patch.object(chatgpt_api_server, "request_registry", {}):
            chatgpt_api_server.make_browser_task(
                "cognition_request",
                request_id="same-request",
                prompt="one",
            )
            with self.assertRaises(ValueError):
                chatgpt_api_server.make_browser_task(
                    "cognition_request",
                    request_id="same-request",
                    prompt="two",
                )



if __name__ == "__main__":
    unittest.main()
