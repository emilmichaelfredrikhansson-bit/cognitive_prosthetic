import tempfile
import unittest
from pathlib import Path

from bob.work_campaign_queue import ADMITTED, STOP_REQUESTED
from bob.work_campaign_worker import WorkCampaignWorker
from tests.test_work_campaign_queue import make_running


def make_worker(root: Path, *, duration=3600):
    clock, campaigns, executions, campaign, queue = make_running(
        root, duration=duration
    )
    worker = WorkCampaignWorker(
        root / "campaign-worker.json",
        campaigns,
        queue,
        executions,
    )
    return clock, campaigns, executions, campaign, queue, worker


def enqueue(queue, campaign, *, item_id="work", lease="work:campaign"):
    return queue.enqueue(
        campaign["campaign_id"],
        workspace="ONE",
        goal=item_id,
        base_ref="main",
        leases=[lease],
        item_id=item_id,
    )


class WorkCampaignWorkerTests(unittest.TestCase):
    def test_cycle_admits_explicit_backlog_and_exposes_ready_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, executions, campaign, queue, worker = make_worker(root)
            first = enqueue(queue, campaign, item_id="first", lease="work:first")
            second = enqueue(queue, campaign, item_id="second", lease="work:second")

            result = worker.cycle(campaign["campaign_id"], max_admissions=2)

            self.assertEqual(result["summary"]["counts"][ADMITTED], 2)
            self.assertEqual(
                {item["item_id"] for item in result["ready"]},
                {first["item_id"], second["item_id"]},
            )
            for ready in result["ready"]:
                run = executions.coordinator_for_run(ready["run_id"]).ledger.get_run(
                    ready["run_id"]
                )
                self.assertEqual(run["lane"], "campaign")
                self.assertEqual(run["authority"]["promotion_authority"], "NONE")
                self.assertFalse(run["authority"]["auto_merge"])

    def test_deadline_cycle_checkpoints_and_parks_at_safe_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clock, _, executions, campaign, queue, worker = make_worker(
                root, duration=10
            )
            item = enqueue(queue, campaign)
            admitted = worker.cycle(campaign["campaign_id"], max_admissions=1)
            run_id = admitted["ready"][0]["run_id"]

            clock.advance(11)
            stopped = worker.cycle(campaign["campaign_id"])

            self.assertIn(item["item_id"], stopped["summary"]["safe_stopped_item_ids"])
            self.assertEqual(
                queue.snapshot(campaign["campaign_id"])["items"][0]["state"],
                STOP_REQUESTED,
            )
            run = executions.coordinator_for_run(run_id).ledger.get_run(run_id)
            self.assertEqual(run["state"], "PARKED")
            digest = worker.digest(campaign["campaign_id"])
            self.assertEqual(len(digest["paused_candidates"]), 1)
            candidate = digest["paused_candidates"][0]
            self.assertEqual(candidate["item_id"], item["item_id"])
            self.assertIsNotNone(candidate["checkpoint_id"])
            self.assertIsNotNone(candidate["head_sha"])
            self.assertEqual(candidate["promotion_authority"], "NONE")
            self.assertFalse(candidate["auto_merge"])

    def test_deadline_waits_for_running_cognition_before_safe_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clock, _, executions, campaign, queue, worker = make_worker(
                root, duration=10
            )
            item = enqueue(queue, campaign)
            admitted = worker.cycle(campaign["campaign_id"], max_admissions=1)
            run_id = admitted["ready"][0]["run_id"]
            execution = executions.coordinator_for_run(run_id)
            cognition = execution.ledger.begin_cognition(
                run_id, purpose="bounded campaign unit"
            )

            clock.advance(11)
            waiting = worker.cycle(campaign["campaign_id"])
            self.assertIn(
                item["item_id"],
                waiting["summary"]["waiting_safe_boundary_item_ids"],
            )
            self.assertEqual(execution.ledger.get_run(run_id)["state"], "ACTIVE")

            execution.ledger.finish_cognition(
                cognition["cognition_id"],
                success=True,
                summary="safe boundary reached",
            )
            stopped = worker.cycle(campaign["campaign_id"])
            self.assertIn(item["item_id"], stopped["summary"]["safe_stopped_item_ids"])
            self.assertEqual(execution.ledger.get_run(run_id)["state"], "PARKED")

    def test_interactive_preemption_survives_worker_restart_and_resumes_same_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, campaigns, executions, campaign, queue, worker = make_worker(root)
            item = enqueue(queue, campaign, lease="work:shared")
            admitted = worker.cycle(campaign["campaign_id"], max_admissions=1)
            campaign_run_id = admitted["ready"][0]["run_id"]
            execution = executions.coordinator_for_run(campaign_run_id)
            interactive = execution.create_run(
                goal="operator priority",
                workspace="ONE",
                base_ref="main",
                leases=["work:shared"],
                lane="interactive",
                authority={"operator": True},
            )
            self.assertEqual(interactive["state"], "QUEUED")

            preempted = worker.preempt_for_interactive(
                execution, interactive["run_id"]
            )
            self.assertEqual(preempted["status"], "PREEMPTED_CAMPAIGN")
            self.assertEqual(
                execution.ledger.get_run(campaign_run_id)["state"], "PARKED"
            )
            self.assertEqual(
                execution.ledger.get_run(interactive["run_id"])["state"], "ACTIVE"
            )

            restarted = WorkCampaignWorker(
                root / "campaign-worker.json",
                campaigns,
                queue,
                executions,
            )
            execution.cancel_run(interactive["run_id"], reason="operator complete")
            resumed = restarted.resume_after_interactive(interactive["run_id"])
            self.assertEqual(resumed["count"], 1)
            self.assertEqual(resumed["resumed"][0]["run_id"], campaign_run_id)
            self.assertEqual(
                execution.ledger.get_run(campaign_run_id)["state"], "ACTIVE"
            )
            self.assertEqual(
                restarted.snapshot()["preemptions"][interactive["run_id"]][0][
                    "item_id"
                ],
                item["item_id"],
            )

    def test_cycle_completes_campaign_only_after_explicit_verified_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, campaigns, _, campaign, queue, worker = make_worker(root)
            item = enqueue(queue, campaign)
            worker.cycle(campaign["campaign_id"], max_admissions=1)
            queue.finish(
                item["item_id"],
                success=True,
                verification={"tests": "PASS"},
            )

            result = worker.cycle(campaign["campaign_id"])

            self.assertTrue(result["summary"]["completed"])
            self.assertEqual(result["campaign"]["state"], "COMPLETED")
            self.assertEqual(
                campaigns.snapshot()["campaigns"][0]["state"],
                "COMPLETED",
            )


if __name__ == "__main__":
    unittest.main()
