import os
import unittest
from unittest.mock import patch

import bob_api_server
import chatgpt_api_server


class LocalServerSurfaceTests(unittest.TestCase):
    def test_bob_api_does_not_grant_cross_origin_access(self):
        client = bob_api_server.app.test_client()
        response = client.get(
            "/bob/health",
            headers={"Origin": "https://untrusted.example"},
        )
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_chatgpt_bridge_does_not_grant_cross_origin_access(self):
        client = chatgpt_api_server.app.test_client()
        response = client.get(
            "/health",
            headers={"Origin": "https://untrusted.example"},
        )
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_stateless_module_routes_are_exposed(self):
        rules = {rule.rule for rule in bob_api_server.app.url_map.iter_rules()}
        self.assertIn("/bob/module-turn", rules)
        self.assertIn("/bob/module-graph", rules)
        self.assertIn("/bob/approvals", rules)
        self.assertIn("/bob/continuations", rules)
        self.assertIn("/bob/continuations/<continuation_id>/resume", rules)
        self.assertIn("/bob/self-development", rules)
        self.assertIn("/bob/self-development/items", rules)
        self.assertIn("/bob/self-development/claim", rules)
        self.assertIn(
            "/bob/self-development/items/<item_id>/reconcile",
            rules,
        )

    def test_execution_coordination_routes_are_exposed(self):
        rules = {rule.rule for rule in bob_api_server.app.url_map.iter_rules()}
        expected = {
            "/bob/execution",
            "/bob/execution/runs",
            "/bob/execution/runs/<run_id>",
            "/bob/execution/runs/<run_id>/cognitions",
            "/bob/execution/cognitions/<cognition_id>/finish",
            "/bob/execution/runs/<run_id>/ready",
            "/bob/execution/integration/plan",
            "/bob/execution/integration/claim",
            "/bob/execution/runs/<run_id>/integrated",
            "/bob/execution/runs/<run_id>/cancel",
        }
        self.assertTrue(expected.issubset(rules))

    def test_loopback_defaults_are_documented_runtime_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(os.environ.get("BOB_HOST", "127.0.0.1"), "127.0.0.1")
            self.assertEqual(
                os.environ.get("CHATGPT_BRIDGE_HOST", "127.0.0.1"),
                "127.0.0.1",
            )


if __name__ == "__main__":
    unittest.main()
