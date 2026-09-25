import unittest

from bob.chatgpt_traffic import ChatGPTTrafficController, throttle_category


class FakeTime:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class ChatGPTTrafficControllerTests(unittest.TestCase):
    def make_controller(self, fake, **kwargs):
        return ChatGPTTrafficController(
            fresh_chat_min_interval_seconds=kwargs.get("interval", 10),
            jitter_seconds=kwargs.get("jitter", 0),
            backoff_seconds=kwargs.get("backoff", (15, 30, 60, 120)),
            clock=fake.clock,
            sleep_fn=fake.sleep,
            jitter_fn=lambda low, high: high,
        )

    def test_fresh_chat_attempts_are_spaced(self):
        fake = FakeTime()
        controller = self.make_controller(fake, interval=10, jitter=3)

        controller.begin_task("cognition_request")
        first = controller.before_fresh_chat()
        controller.finish_task("cognition_request", {"success": True})
        self.assertEqual(first["fresh_chat_wait_seconds"], 0.0)

        controller.begin_task("cognition_request")
        second = controller.before_fresh_chat()
        controller.finish_task("cognition_request", {"success": True})

        self.assertEqual(second["fresh_chat_wait_seconds"], 13.0)
        self.assertEqual(fake.sleeps, [13.0])

    def test_rate_limit_applies_exponential_cooldown_without_retry(self):
        fake = FakeTime()
        controller = self.make_controller(fake)

        controller.begin_task("cognition_request")
        metadata = controller.finish_task(
            "cognition_request",
            {"success": False, "error": "CHATGPT_TRANSIENT_UI:RATE_LIMITED"},
        )
        self.assertEqual(metadata["backoff_seconds"], 15.0)
        self.assertEqual(metadata["throttle_streak"], 1)

        next_start = controller.begin_task("cognition_request")
        self.assertEqual(next_start["cooldown_wait_seconds"], 15.0)
        second = controller.finish_task(
            "cognition_request",
            {"success": False, "error": "CHATGPT_TRANSIENT_UI:RATE_LIMITED"},
        )
        self.assertEqual(second["backoff_seconds"], 30.0)
        self.assertEqual(second["throttle_streak"], 2)

        controller.begin_task("cognition_request")
        self.assertEqual(fake.sleeps, [15.0, 30.0])
        reset = controller.finish_task("cognition_request", {"success": True})
        self.assertEqual(reset["throttle_streak"], 0)
        self.assertEqual(controller.snapshot()["cooldown_remaining_seconds"], 0.0)

    def test_write_overlap_fails_closed(self):
        fake = FakeTime()
        controller = self.make_controller(fake)
        controller.begin_task("send_message")
        with self.assertRaisesRegex(RuntimeError, "overlapping writes"):
            controller.begin_task("new_chat")
        controller.finish_task("send_message", {"success": True})
        controller.begin_task("new_chat")
        controller.finish_task("new_chat", {"success": True})

    def test_non_write_task_does_not_occupy_write_lane(self):
        fake = FakeTime()
        controller = self.make_controller(fake)
        metadata = controller.begin_task("show_ui")
        self.assertFalse(metadata["write_serialized"])
        self.assertFalse(controller.snapshot()["active_write"])

    def test_only_sanitized_transient_errors_trigger_backoff(self):
        self.assertEqual(
            throttle_category({
                "success": False,
                "error": "CHATGPT_TRANSIENT_UI:USAGE_LIMIT",
            }),
            "USAGE_LIMIT",
        )
        self.assertIsNone(
            throttle_category({
                "success": False,
                "error": "Timed out waiting for completed assistant response",
            })
        )


if __name__ == "__main__":
    unittest.main()
