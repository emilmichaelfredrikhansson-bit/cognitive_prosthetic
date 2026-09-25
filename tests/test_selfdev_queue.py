import json
import tempfile
import unittest
from pathlib import Path

from bob.errors import ConfigurationError, ProtocolError
from bob.selfdev_queue import SelfDevelopmentQueue


REPO = "emilmichaelfredrikhansson-bit/cognitive_prosthetic"
REPO_ID = 1374229539
CANONICAL = "feat/bob-core-v1"


def make_queue(path: Path) -> SelfDevelopmentQueue:
    return SelfDevelopmentQueue(
        path,
        repository_full_name=REPO,
        repository_id=REPO_ID,
        canonical_ref=CANONICAL,
    )


class SelfDevelopmentQueueTests(unittest.TestCase):
    def test_enqueue_is_durable_and_repo_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "selfdev.json")
            queue = make_queue(path)
            item = queue.enqueue(
                goal="harden restart durability",
                leases=["module:BOB_SELF_DEVELOPMENT_STATE", "work:restart"],
                expected_outcome="restart preserves intent",
                item_id="selfdev-one",
            )
            self.assertEqual(item["state"], "QUEUED")
            self.assertEqual(
                item["leases"],
                ["module:BOB_SELF_DEVELOPMENT_STATE", "work:restart"],
            )

            restarted = make_queue(path)
            snapshot = restarted.snapshot()
            self.assertEqual(snapshot["repository"]["id"], REPO_ID)
            self.assertEqual(snapshot["items"][0]["item_id"], "selfdev-one")

            with self.assertRaises(ConfigurationError):
                SelfDevelopmentQueue(
                    path,
                    repository_full_name="other/repo",
                    repository_id=999,
                    canonical_ref=CANONICAL,
                )

    def test_restart_interrupts_active_item_instead_of_replaying(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "selfdev.json")
            queue = make_queue(path)
            queue.enqueue(
                goal="candidate",
                leases=["module:BOB_RUNTIME_ORCHESTRATION"],
                item_id="selfdev-active",
            )
            active = queue.claim_next()
            self.assertEqual(active["state"], "ACTIVE")

            restarted = make_queue(path)
            item = restarted.snapshot()["items"][0]
            self.assertEqual(item["state"], "INTERRUPTED")
            self.assertEqual(
                item["blocked_reason"],
                "RUNTIME_RESTART_RECONCILE_REQUIRED",
            )
            self.assertEqual(item["attempt_count"], 1)

    def test_only_one_item_can_be_active_and_queue_is_fifo(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = make_queue(Path(tmp, "selfdev.json"))
            queue.enqueue(goal="first", leases=["work:first"], item_id="first")
            queue.enqueue(goal="second", leases=["work:second"], item_id="second")
            self.assertEqual(queue.claim_next()["item_id"], "first")
            with self.assertRaisesRegex(ProtocolError, "already has an ACTIVE item"):
                queue.claim_next()

            queue.finish("first", state="QUALIFIED", verification={"tests": "PASS"})
            second = queue.claim_next()
            self.assertEqual(second["item_id"], "second")
            self.assertEqual(second["attempt_count"], 1)

    def test_execution_binding_is_single_owner_and_blocks_blind_requeue(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = make_queue(Path(tmp, "selfdev.json"))
            queue.enqueue(goal="bind run", leases=["work:bind"], item_id="bind")
            queue.claim_next()
            bound = queue.bind_execution_run("bind", "run-123")
            self.assertEqual(bound["execution_run_id"], "run-123")
            self.assertEqual(
                queue.bind_execution_run("bind", "run-123")["execution_run_id"],
                "run-123",
            )
            with self.assertRaisesRegex(ProtocolError, "already bound"):
                queue.bind_execution_run("bind", "run-456")

            queue.block("bind", "provider unavailable")
            with self.assertRaisesRegex(ProtocolError, "requires reconciliation"):
                queue.requeue("bind")

    def test_restart_can_resume_externally_reconciled_bound_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "selfdev.json")
            queue = make_queue(path)
            queue.enqueue(goal="resume", leases=["work:resume"], item_id="resume")
            queue.claim_next()
            queue.bind_execution_run("resume", "run-123")

            restarted = make_queue(path)
            interrupted = restarted.snapshot()["items"][0]
            self.assertEqual(interrupted["state"], "INTERRUPTED")
            resumed = restarted.resume_reconciled_execution("resume", "run-123")
            self.assertEqual(resumed["state"], "ACTIVE")
            self.assertEqual(resumed["execution_run_id"], "run-123")
            self.assertEqual(resumed["attempt_count"], 1)

    def test_blocked_unbound_item_can_requeue_explicitly(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = make_queue(Path(tmp, "selfdev.json"))
            queue.enqueue(goal="retry", leases=["path:bob/example.py"], item_id="retry")
            queue.claim_next()
            queue.block("retry", "temporary local blocker")
            requeued = queue.requeue("retry")
            self.assertEqual(requeued["state"], "QUEUED")
            self.assertIsNone(requeued["blocked_reason"])
            self.assertEqual(queue.claim_next()["attempt_count"], 2)

    def test_corrupt_order_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "selfdev.json")
            queue = make_queue(path)
            queue.enqueue(goal="one", leases=["work:one"], item_id="one")
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["order"] = []
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ConfigurationError, "order"):
                make_queue(path)


if __name__ == "__main__":
    unittest.main()
