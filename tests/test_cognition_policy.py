import unittest
from unittest.mock import Mock, patch

from bob.driver import ChatGPTBridge

from bob.cognition_policy import (
    DEFAULT_COGNITION_POLICY,
    DEFAULT_MODULE_HARD_CAP_TOKENS,
    DEFAULT_COMPILED_CONTEXT_HARD_LIMIT_TOKENS,
    DEFAULT_COMPILED_CONTEXT_TARGET_TOKENS,
    CognitionPolicy,
)


class CognitionPolicyTests(unittest.TestCase):
    def test_canonical_defaults_preserve_headroom(self):
        self.assertEqual(DEFAULT_MODULE_HARD_CAP_TOKENS, 15_000)
        self.assertEqual(DEFAULT_COMPILED_CONTEXT_TARGET_TOKENS, 20_000)
        self.assertEqual(DEFAULT_COMPILED_CONTEXT_HARD_LIMIT_TOKENS, 25_000)
        self.assertTrue(DEFAULT_COGNITION_POLICY.fresh_chat_per_request)

    def test_budget_classification(self):
        policy = CognitionPolicy()
        self.assertEqual(policy.classify(19_999), "FIT")
        self.assertEqual(policy.classify(20_000), "FIT")
        self.assertEqual(policy.classify(20_001), "ABOVE_TARGET")
        self.assertEqual(policy.classify(25_000), "ABOVE_TARGET")
        self.assertEqual(policy.classify(25_001), "REJECT")

    def test_hard_limit_fails_closed(self):
        policy = CognitionPolicy()
        policy.require_fit(25_000)
        with self.assertRaises(ValueError):
            policy.require_fit(25_001)

    def test_module_size_has_absolute_15k_cap(self):
        policy = CognitionPolicy()
        policy.require_module_size(15_000)
        with self.assertRaises(ValueError):
            policy.require_module_size(15_001)

    def test_fresh_chat_is_invariant_not_optional_tuning(self):
        with self.assertRaises(ValueError):
            CognitionPolicy(fresh_chat_per_request=False)

    @patch("bob.driver.requests.post")
    def test_bridge_has_atomic_fresh_cognition_primitive(self, post):
        response = Mock()
        response.json.return_value = {"success": True, "response": "solution"}
        response.raise_for_status.return_value = None
        post.return_value = response

        bridge = ChatGPTBridge(base_url="http://127.0.0.1:5001")
        result = bridge.cognition("bounded problem")

        self.assertEqual(result, "solution")
        post.assert_called_once_with(
            "http://127.0.0.1:5001/cognition",
            json={"prompt": "bounded problem"},
            timeout=220,
        )


if __name__ == "__main__":
    unittest.main()
