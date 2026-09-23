import unittest

from bob.cognition_policy import (
    DEFAULT_COGNITION_POLICY,
    DEFAULT_COMPILED_CONTEXT_HARD_LIMIT_TOKENS,
    DEFAULT_COMPILED_CONTEXT_TARGET_TOKENS,
    CognitionPolicy,
)


class CognitionPolicyTests(unittest.TestCase):
    def test_canonical_defaults_preserve_headroom(self):
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

    def test_fresh_chat_is_invariant_not_optional_tuning(self):
        with self.assertRaises(ValueError):
            CognitionPolicy(fresh_chat_per_request=False)


if __name__ == "__main__":
    unittest.main()
