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
        self.assertIn(
            "/bob/self-development/items/<item_id>/finish",
            rules,
        )
        self.assertIn("/bob/self-development/checkpoints", rules)
        self.assertIn(
            "/bob/self-development/items/<item_id>/checkpoints",
            rules,
        )
        self.assertIn(
            "/bob/self-development/items/<item_id>/checkpoints/<checkpoint_id>/revert",
            rules,
        )
        self.assertIn(
            "/bob/self-development/items/<item_id>/discard",
            rules,
        )
        self.assertIn(
            "/bob/self-development/items/<item_id>/resume-preempted",
            rules,
        )

    def test_selfdev_control_bad_payloads_fail_as_protocol_errors(self):
        client = bob_api_server.app.test_client()
        missing_reason = client.post(
            "/bob/self-development/items/not-an-item/discard",
            json={},
        )
        self.assertEqual(missing_reason.status_code, 400)
        self.assertEqual(missing_reason.get_json()["type"], "ProtocolError")

        bad_verification = client.post(
            "/bob/self-development/items/not-an-item/checkpoints",
            json={"verification": "not-an-object"},
        )
        self.assertEqual(bad_verification.status_code, 400)
        self.assertEqual(bad_verification.get_json()["type"], "ProtocolError")

    def test_selfdev_promotion_routes_are_exposed(self):
        rules = {rule.rule for rule in bob_api_server.app.url_map.iter_rules()}
        expected = {
            "/bob/self-development/promotions",
            "/bob/self-development/items/<item_id>/promotion-proposals",
            "/bob/self-development/promotions/<proposal_id>/revalidate",
            "/bob/self-development/promotions/<proposal_id>/approve",
            "/bob/self-development/promotions/<proposal_id>/reject",
        }
        self.assertTrue(expected.issubset(rules))

    def test_work_campaign_routes_are_exposed(self):
        rules = {rule.rule for rule in bob_api_server.app.url_map.iter_rules()}
        expected = {
            "/bob/campaigns",
            "/bob/campaigns/<campaign_id>/start",
            "/bob/campaigns/<campaign_id>/runs",
            "/bob/campaigns/<campaign_id>/reconcile",
            "/bob/campaigns/<campaign_id>/complete",
            "/bob/campaigns/<campaign_id>/cancel",
        }
        self.assertTrue(expected.issubset(rules))

    def test_work_campaign_queue_routes_are_exposed(self):
        rules = {rule.rule for rule in bob_api_server.app.url_map.iter_rules()}
        expected = {
            "/bob/campaigns/<campaign_id>/work",
            "/bob/campaigns/<campaign_id>/tick",
            "/bob/campaigns/<campaign_id>/digest",
            "/bob/campaign-work/<item_id>/finish",
            "/bob/campaign-work/<item_id>/cancel",
        }
        self.assertTrue(expected.issubset(rules))

    def test_work_campaign_worker_routes_are_exposed(self):
        rules = {rule.rule for rule in bob_api_server.app.url_map.iter_rules()}
        expected = {
            "/bob/campaigns/<campaign_id>/worker",
            "/bob/campaigns/<campaign_id>/worker/cycle",
            "/bob/campaign-work/<item_id>/checkpoint",
            "/bob/campaign-work/<item_id>/park",
            "/bob/campaign-work/<item_id>/resume",
        }
        self.assertTrue(expected.issubset(rules))

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
