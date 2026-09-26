import tempfile
import unittest
from pathlib import Path

from bob.errors import ProtocolError
from bob.work_campaign_queue import (
    ADMITTED,
    BLOCKED,
    CANCELLED,
    SKIPPED_DEADLINE,
    STOP_REQUESTED,
    SUCCEEDED,
    WorkCampaignQueue,
)
from bob.work_campaigns import WorkCampaignManager
from tests.test_work_campaigns import FakeClock, make_environment


def make_running(root: Path, *, duration=3600):
    workspaces, executions = make_environment(root)
    clock = FakeClock()
    campaigns = WorkCampaignManager(
        root / "campaigns.json",
        workspaces,
        executions,
        clock=clock,
    )
    campaign = campaigns.create(
        goal="campaign queue test",
        workspace_codes=["ONE"],
        duration_seconds=duration,
    )
    campaigns.start(campaign["campaign_id"])
    queue = WorkCampaignQueue(
        root / "campaign-work.json",
        campaigns,
        executions,
    )
    return clock, campaigns, executions, campaign, queue


class WorkCampaignQueueTests(unittest.TestCase):
    def test_capacity_waits_in_campaign_queue_not_execution_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, executions, campaign, queue = make_running(root)
            items = [
                queue.enqueue(
                    campaign["campaign_id"],
                    workspace="ONE",
                    goal=f"task {index}",
                    base_ref="main",
                    leases=[f"work:item-{index}"],
                )
                for index in range(4)
            ]
            tick = queue.tick(campaign["campaign_id"], max_admissions=4)
            self.assertEqual(tick["counts"][ADMITTED], 3)
            self.assertEqual(tick["counts"][BLOCKED], 1)
            blocked = next(i for i in tick["items"] if i["state"] == BLOCKED)
            self.assertEqual(blocked["blocked_reason"], "CAPACITY")
            self.assertIsNone(blocked["run_id"])

            ledger = executions.coordinator_for_workspace("ONE").ledger.snapshot()
            campaign_runs = [
                run for run in ledger["runs"].values()
                if (run.get("authority") or {}).get("campaign_id")
                == campaign["campaign_id"]
            ]
            self.assertEqual(len(campaign_runs), 3)
            self.assertTrue(all(run["state"] == "ACTIVE" for run in campaign_runs))

            again = queue.tick(campaign["campaign_id"], max_admissions=4)
            self.assertEqual(again["counts"][BLOCKED], 1)
            ledger2 = executions.coordinator_for_workspace("ONE").ledger.snapshot()
            self.assertEqual(len(ledger2["runs"]), len(ledger["runs"]))
            self.assertEqual(
                {item["item_id"] for item in items},
                {item["item_id"] for item in again["items"]},
            )

    def test_blocked_capacity_retries_only_after_execution_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, executions, campaign, queue = make_running(root)
            items = [
                queue.enqueue(
                    campaign["campaign_id"],
                    workspace="ONE",
                    goal=f"task {index}",
                    base_ref="main",
                    leases=[f"work:item-{index}"],
                )
                for index in range(4)
            ]
            first = queue.tick(campaign["campaign_id"], max_admissions=4)
            active = [i for i in first["items"] if i["state"] == ADMITTED]
            blocked = next(i for i in first["items"] if i["state"] == BLOCKED)

            queue.finish(
                active[0]["item_id"],
                success=True,
                verification={"tests": "PASS"},
            )
            retried = queue.tick(campaign["campaign_id"], max_admissions=4)
            now = next(i for i in retried["items"] if i["item_id"] == blocked["item_id"])
            self.assertEqual(now["state"], ADMITTED)
            self.assertIsNotNone(now["run_id"])
            self.assertEqual(retried["counts"][ADMITTED], 3)
            self.assertEqual(retried["counts"][SUCCEEDED], 1)

            ledger = executions.coordinator_for_workspace("ONE").ledger.snapshot()
            self.assertEqual(ledger["active_run_count"], 3)
            self.assertEqual(len(items), 4)

    def test_dependencies_gate_admission_until_verified_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, _, campaign, queue = make_running(root)
            first = queue.enqueue(
                campaign["campaign_id"],
                workspace="ONE",
                goal="first",
                base_ref="main",
                leases=["work:first"],
                item_id="first",
            )
            queue.enqueue(
                campaign["campaign_id"],
                workspace="ONE",
                goal="second",
                base_ref="main",
                leases=["work:second"],
                depends_on=["first"],
                item_id="second",
            )
            tick = queue.tick(campaign["campaign_id"], max_admissions=3)
            self.assertEqual(
                next(i for i in tick["items"] if i["item_id"] == "first")["state"],
                ADMITTED,
            )
            second = next(i for i in tick["items"] if i["item_id"] == "second")
            self.assertEqual(second["state"], "QUEUED")
            self.assertEqual(second["blocked_reason"], "DEPENDENCY_WAIT:first")

            queue.finish(
                first["item_id"],
                success=True,
                verification={"tests": "PASS"},
            )
            tick2 = queue.tick(campaign["campaign_id"], max_admissions=3)
            second2 = next(i for i in tick2["items"] if i["item_id"] == "second")
            self.assertEqual(second2["state"], ADMITTED)

    def test_deadline_requests_safe_stop_and_skips_unadmitted_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clock, _, _, campaign, queue = make_running(root, duration=10)
            first = queue.enqueue(
                campaign["campaign_id"],
                workspace="ONE",
                goal="active",
                base_ref="main",
                leases=["work:active"],
            )
            second = queue.enqueue(
                campaign["campaign_id"],
                workspace="ONE",
                goal="queued",
                base_ref="main",
                leases=["work:queued"],
            )
            tick = queue.tick(campaign["campaign_id"], max_admissions=1)
            self.assertEqual(
                next(i for i in tick["items"] if i["item_id"] == first["item_id"])["state"],
                ADMITTED,
            )
            clock.advance(11)
            expired = queue.tick(campaign["campaign_id"], max_admissions=3)
            first_after = next(
                i for i in expired["items"] if i["item_id"] == first["item_id"]
            )
            second_after = next(
                i for i in expired["items"] if i["item_id"] == second["item_id"]
            )
            self.assertEqual(first_after["state"], STOP_REQUESTED)
            self.assertEqual(first_after["blocked_reason"], "CAMPAIGN_DEADLINE")
            self.assertEqual(second_after["state"], SKIPPED_DEADLINE)
            self.assertIsNone(second_after["run_id"])

    def test_verified_finish_creates_review_digest_without_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, _, campaign, queue = make_running(root)
            item = queue.enqueue(
                campaign["campaign_id"],
                workspace="ONE",
                goal="candidate",
                base_ref="main",
                leases=["work:candidate"],
            )
            queue.tick(campaign["campaign_id"])
            with self.assertRaisesRegex(ProtocolError, "verification evidence"):
                queue.finish(item["item_id"], success=True)

            finished = queue.finish(
                item["item_id"],
                success=True,
                verification={"tests": "PASS", "lint": "PASS"},
            )
            self.assertEqual(finished["state"], SUCCEEDED)
            receipt = finished["verification"]["execution"]
            self.assertEqual(receipt["state"], "CANCELLED")
            self.assertEqual(receipt["promotion_authority"], "NONE")
            self.assertFalse(receipt["auto_merge"])

            digest = queue.digest(campaign["campaign_id"])
            self.assertEqual(len(digest["review_candidates"]), 1)
            candidate = digest["review_candidates"][0]
            self.assertEqual(candidate["item_id"], item["item_id"])
            self.assertEqual(candidate["promotion_authority"], "NONE")
            self.assertFalse(candidate["auto_merge"])

    def test_restart_adopts_crash_window_run_without_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, campaigns, executions, campaign, queue = make_running(root)
            item = queue.enqueue(
                campaign["campaign_id"],
                workspace="ONE",
                goal="crash window",
                base_ref="main",
                leases=["work:crash-window"],
                item_id="crash-window",
            )
            created = campaigns.create_run(
                campaign["campaign_id"],
                workspace_code="ONE",
                goal=item["goal"],
                base_ref=item["base_ref"],
                leases=list(item["leases"]),
                work_item_id=item["item_id"],
            )
            before = queue.snapshot(campaign["campaign_id"])["items"][0]
            self.assertIsNone(before["run_id"])

            restarted = WorkCampaignQueue(
                root / "campaign-work.json",
                campaigns,
                executions,
            )
            tick = restarted.tick(campaign["campaign_id"])
            current = tick["items"][0]
            self.assertEqual(current["state"], ADMITTED)
            self.assertEqual(current["run_id"], created["run"]["run_id"])
            self.assertEqual(current["attempt_count"], 1)

            ledger = executions.coordinator_for_workspace("ONE").ledger.snapshot()
            matching = [
                run for run in ledger["runs"].values()
                if (run.get("authority") or {}).get("work_item_id")
                == item["item_id"]
            ]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["run_id"], created["run"]["run_id"])

    def test_restart_preserves_backlog_and_bound_run_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, campaigns, executions, campaign, queue = make_running(root)
            item = queue.enqueue(
                campaign["campaign_id"],
                workspace="ONE",
                goal="restart",
                base_ref="main",
                leases=["work:restart"],
            )
            admitted = queue.tick(campaign["campaign_id"])
            before = next(
                i for i in admitted["items"] if i["item_id"] == item["item_id"]
            )
            restarted = WorkCampaignQueue(
                root / "campaign-work.json",
                campaigns,
                executions,
            )
            after = restarted.snapshot(campaign["campaign_id"])["items"][0]
            self.assertEqual(after["state"], ADMITTED)
            self.assertEqual(after["run_id"], before["run_id"])
            tick = restarted.tick(campaign["campaign_id"])
            current = tick["items"][0]
            self.assertEqual(current["run_id"], before["run_id"])
            ledger = executions.coordinator_for_workspace("ONE").ledger.snapshot()
            matching = [
                run for run in ledger["runs"].values()
                if (run.get("authority") or {}).get("campaign_id")
                == campaign["campaign_id"]
            ]
            self.assertEqual(len(matching), 1)

    def test_campaign_cancel_cancels_backlog_and_requests_active_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, campaigns, _, campaign, queue = make_running(root)
            active = queue.enqueue(
                campaign["campaign_id"],
                workspace="ONE",
                goal="active",
                base_ref="main",
                leases=["work:active"],
            )
            queued = queue.enqueue(
                campaign["campaign_id"],
                workspace="ONE",
                goal="queued",
                base_ref="main",
                leases=["work:queued"],
            )
            queue.tick(campaign["campaign_id"], max_admissions=1)
            campaigns.cancel(campaign["campaign_id"], reason="operator stop")
            tick = queue.tick(campaign["campaign_id"])
            active_after = next(
                i for i in tick["items"] if i["item_id"] == active["item_id"]
            )
            queued_after = next(
                i for i in tick["items"] if i["item_id"] == queued["item_id"]
            )
            self.assertEqual(active_after["state"], STOP_REQUESTED)
            self.assertEqual(queued_after["state"], CANCELLED)


if __name__ == "__main__":
    unittest.main()
