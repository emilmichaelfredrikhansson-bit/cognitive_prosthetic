import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from bob.campaign_work_executor import CampaignWorkExecutor
from bob.protocol import parse_model_response
from bob.work_campaign_queue import ADMITTED, SUCCEEDED
from tests.test_work_campaign_worker import enqueue, make_worker


class FakeBridge:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def cognition(
        self,
        prompt,
        *,
        request_id=None,
        run_id=None,
        cognition_id=None,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "request_id": request_id,
                "run_id": run_id,
                "cognition_id": cognition_id,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(prompt)
        return response


class FakeRuntime:
    def __init__(self, registry, bridge):
        self.registry = registry
        self.bridge = bridge


def message(payload):
    return json.dumps(payload)


def allow_writes(root: Path):
    path = root / "workspaces" / "one.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["effects"] = {"write_branch": True}
    path.write_text(json.dumps(payload), encoding="utf-8")


def environment(root: Path, bridge, *, writes=False):
    _, campaigns, executions, campaign, queue, worker = make_worker(root)
    if writes:
        allow_writes(root)
    executor = CampaignWorkExecutor(
        root / "executor.json",
        FakeRuntime(executions.workspace_registry, bridge),
        campaigns,
        queue,
        worker,
        executions,
    )
    return campaigns, executions, campaign, queue, worker, executor


def replace_from_read(prompt):
    match = re.search(
        r"content_sha256[^0-9a-f]+([0-9a-f]{64})",
        prompt,
    )
    if not match:
        raise AssertionError("read sha missing")
    return message(
        {
            "type": "BOB.EFFECT",
            "id": "e1",
            "tool": "repo.replace_file",
            "args": {
                "path": "README.md",
                "content": "candidate\n",
                "expected_sha256": match.group(1),
            },
        }
    )


class CampaignWorkExecutorTests(unittest.TestCase):
    def test_ready_run_carries_run_cognition_request_correlation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bridge = FakeBridge(
                [
                    message(
                        {
                            "type": "BOB.READ",
                            "id": "r1",
                            "tool": "repo.status",
                            "args": {},
                        }
                    ),
                    message(
                        {
                            "type": "BOB.DONE",
                            "id": "d1",
                            "args": {"summary": "done"},
                        }
                    ),
                ]
            )
            campaigns, executions, campaign, queue, worker, executor = environment(
                root, bridge
            )
            enqueue(queue, campaign)

            first = executor.cycle(campaign["campaign_id"])["outcomes"][0]
            self.assertEqual(first["status"], "ROUND_YIELD")
            self.assertEqual(len(bridge.calls), 1)

            restarted = CampaignWorkExecutor(
                root / "executor.json", executor.runtime, campaigns, queue, worker, executions
            )
            outcome = restarted.cycle(campaign["campaign_id"])["outcomes"][0]

            self.assertEqual(outcome["status"], "SUCCEEDED")
            item = queue.snapshot(campaign["campaign_id"])["items"][0]
            self.assertEqual(item["state"], SUCCEEDED)
            self.assertEqual(len(bridge.calls), 2)
            self.assertNotEqual(bridge.calls[0]["cognition_id"], bridge.calls[1]["cognition_id"])
            self.assertIn("NEXT ACTION: Continue", bridge.calls[1]["prompt"])
            self.assertIn("request_id", bridge.calls[1]["prompt"])
            self.assertIn("r1", bridge.calls[1]["prompt"])
            for call in bridge.calls:
                self.assertEqual(call["run_id"], item["run_id"])
                self.assertTrue(call["cognition_id"])
                self.assertTrue(call["request_id"])
            ledger = executions.coordinator_for_run(
                item["run_id"]
            ).ledger.snapshot()
            bound = [
                cognition
                for cognition in ledger["cognitions"].values()
                if cognition["run_id"] == item["run_id"]
            ]
            self.assertEqual(len(bound), 2)
            self.assertTrue(all(c["state"] == "COMPLETE" for c in bound))
            receipt = item["verification"]["execution"]
            self.assertEqual(receipt["promotion_authority"], "NONE")
            self.assertFalse(receipt["auto_merge"])
            self.assertEqual(
                campaigns.snapshot()["campaigns"][0]["state"],
                "COMPLETED",
            )

    def test_effect_round_uses_read_hash_and_keeps_main_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bridge = FakeBridge(
                [
                    message(
                        {
                            "type": "BOB.READ",
                            "id": "r1",
                            "tool": "repo.read_file",
                            "args": {"path": "README.md"},
                        }
                    ),
                    replace_from_read,
                    message(
                        {
                            "type": "BOB.DONE",
                            "id": "d1",
                            "args": {"summary": "done"},
                        }
                    ),
                ]
            )
            _, executions, campaign, queue, _, executor = environment(
                root, bridge, writes=True
            )
            enqueue(queue, campaign)

            self.assertEqual(executor.cycle(campaign["campaign_id"])["outcomes"][0]["status"], "ROUND_YIELD")
            self.assertEqual(executor.cycle(campaign["campaign_id"])["outcomes"][0]["status"], "ROUND_YIELD")
            outcome = executor.cycle(campaign["campaign_id"])["outcomes"][0]

            self.assertEqual(outcome["status"], "SUCCEEDED")
            item = queue.snapshot(campaign["campaign_id"])["items"][0]
            execution = executions.coordinator_for_run(item["run_id"])
            worktree = execution.worktrees.worktree_path(item["run_id"])
            self.assertEqual(
                (worktree / "README.md").read_text(encoding="utf-8"),
                "candidate\n",
            )
            self.assertEqual(
                (execution.repo_root / "README.md").read_text(encoding="utf-8"),
                "root\n",
            )
            record = executor.snapshot()["items"][item["item_id"]]
            self.assertEqual(len(record["effects"]), 1)
            self.assertTrue(record["effects"][0]["verified"])

    def test_cognition_failure_is_durable_and_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bridge = FakeBridge([RuntimeError("submission failed")])
            _, executions, campaign, queue, _, executor = environment(root, bridge)
            enqueue(queue, campaign)

            outcome = executor.cycle(campaign["campaign_id"])["outcomes"][0]

            self.assertEqual(outcome["status"], "BLOCKED_COGNITION")
            self.assertEqual(len(bridge.calls), 1)
            item = queue.snapshot(campaign["campaign_id"])["items"][0]
            self.assertEqual(item["state"], ADMITTED)
            cognition = executions.coordinator_for_run(
                item["run_id"]
            ).ledger.snapshot()["cognitions"][
                bridge.calls[0]["cognition_id"]
            ]
            self.assertEqual(cognition["state"], "FAILED")

    def test_duplicate_completed_read_returns_correction_without_reexecuting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repeated = message(
                {
                    "type": "BOB.READ",
                    "id": "same-read",
                    "tool": "repo.status",
                    "args": {},
                }
            )
            done = message(
                {
                    "type": "BOB.DONE",
                    "id": "done-after-correction",
                    "args": {"summary": "done"},
                }
            )
            bridge = FakeBridge([repeated, repeated, done])
            _, _, campaign, queue, _, executor = environment(root, bridge)
            enqueue(queue, campaign)

            self.assertEqual(executor.cycle(campaign["campaign_id"])["outcomes"][0]["status"], "ROUND_YIELD")
            self.assertEqual(executor.cycle(campaign["campaign_id"])["outcomes"][0]["status"], "ROUND_YIELD")
            outcome = executor.cycle(campaign["campaign_id"])["outcomes"][0]

            self.assertEqual(outcome["status"], "SUCCEEDED")
            self.assertEqual(len(bridge.calls), 3)
            item = queue.snapshot(campaign["campaign_id"])["items"][0]
            record = executor.snapshot()["items"][item["item_id"]]
            self.assertEqual(len(record["results"]), 2)
            self.assertIn('"tool": "repo.protocol"', record["results"][1])
            self.assertIn("already completed", record["results"][1])

    def test_safe_boundary_yields_to_queued_interactive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bridge = FakeBridge([])
            _, executions, campaign, queue, worker, executor = environment(
                root, bridge
            )
            enqueue(queue, campaign, lease="work:shared")
            ready = worker.cycle(
                campaign["campaign_id"], max_admissions=1
            )["ready"][0]
            execution = executions.coordinator_for_run(ready["run_id"])
            interactive = execution.create_run(
                goal="operator priority",
                workspace="ONE",
                base_ref="main",
                leases=["work:shared"],
                lane="interactive",
                authority={"operator": True},
            )
            self.assertEqual(interactive["state"], "QUEUED")

            outcome = executor.execute_ready(ready)

            self.assertEqual(outcome["status"], "PREEMPTED_INTERACTIVE")
            self.assertEqual(bridge.calls, [])
            self.assertEqual(
                execution.ledger.get_run(ready["run_id"])["state"],
                "PARKED",
            )
            self.assertEqual(
                execution.ledger.get_run(interactive["run_id"])["state"],
                "ACTIVE",
            )

    def test_restart_adopts_prepared_effect_then_finishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bridge = FakeBridge(
                [
                    message(
                        {
                            "type": "BOB.DONE",
                            "id": "d1",
                            "args": {"summary": "done"},
                        }
                    )
                ]
            )
            campaigns, executions, campaign, queue, worker, executor = environment(
                root, bridge, writes=True
            )
            enqueue(queue, campaign)
            ready = worker.cycle(
                campaign["campaign_id"], max_admissions=1
            )["ready"][0]
            item = queue.snapshot(campaign["campaign_id"])["items"][0]
            execution = executions.coordinator_for_run(item["run_id"])
            run = execution.ledger.get_run(item["run_id"])
            adapter = executor._adapter(item, execution, run)
            source_sha = hashlib.sha256(
                (adapter.worktree / "README.md").read_bytes()
            ).hexdigest()
            effect = parse_model_response(
                message(
                    {
                        "type": "BOB.EFFECT",
                        "id": "e-prepared",
                        "tool": "repo.replace_file",
                        "args": {
                            "path": "README.md",
                            "content": "recovered\n",
                            "expected_sha256": source_sha,
                        },
                    }
                )
            ).messages[0]
            pending = adapter.prepare_effect(effect, item_id=item["item_id"])
            record = executor._record_for(item, run)
            executor._update(
                record,
                pending_effect=pending,
                status="APPLYING_EFFECT",
            )

            restarted = CampaignWorkExecutor(
                root / "executor.json",
                FakeRuntime(executions.workspace_registry, bridge),
                campaigns,
                queue,
                worker,
                executions,
            )
            outcome = restarted.execute_ready(ready, max_rounds=1)

            self.assertEqual(outcome["status"], "SUCCEEDED")
            stored = restarted.snapshot()["items"][item["item_id"]]
            self.assertEqual(len(stored["effects"]), 1)
            self.assertIsNone(stored["pending_effect"])
            self.assertEqual(
                (adapter.worktree / "README.md").read_text(encoding="utf-8"),
                "recovered\n",
            )


if __name__ == "__main__":
    unittest.main()
