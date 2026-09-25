import tempfile
import unittest
from pathlib import Path

from bob.errors import ConfigurationError, ProtocolError
from bob.execution_ledger import ExecutionLedger


class ExecutionLedgerTests(unittest.TestCase):
    def make_ledger(
        self,
        root,
        max_parallel_runs=3,
        *,
        repository_full_name="owner/repo-a",
        repository_id=1,
        state_name="ledger.json",
    ):
        return ExecutionLedger(
            Path(root) / state_name,
            repository_full_name=repository_full_name,
            repository_id=repository_id,
            repo_root=Path(root),
            canonical_ref="main",
            max_parallel_runs_per_repository=max_parallel_runs,
        )

    def create(self, ledger, index, lease=None, depends_on=None):
        return ledger.create_run(
            run_id=f"run-{index}",
            goal=f"goal {index}",
            workspace="BOB",
            base_ref="feat/bob-core-v1",
            base_sha="base-sha",
            branch=f"bob/run/run-{index}",
            worktree_path=f"C:/tmp/run-{index}",
            leases=[lease or f"work:item-{index}"],
            depends_on=depends_on or [],
        )

    def test_three_parallel_runs_cap_and_fourth_waits(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self.make_ledger(root)
            first = self.create(ledger, 1)
            second = self.create(ledger, 2)
            third = self.create(ledger, 3)
            fourth = self.create(ledger, 4)

            self.assertEqual(first["state"], "ACTIVE")
            self.assertEqual(second["state"], "ACTIVE")
            self.assertEqual(third["state"], "ACTIVE")
            self.assertEqual(fourth["state"], "QUEUED")
            self.assertEqual(fourth["blocked_reason"], "CAPACITY")
            self.assertEqual(ledger.snapshot()["active_run_count"], 3)

            ledger.mark_ready_for_integration(
                "run-1",
                verified_base_sha="base-sha",
                verified_head_sha="head-1",
                verification={"tests": "PASS"},
            )
            self.assertEqual(ledger.get_run("run-4")["state"], "ACTIVE")

    def test_overlapping_semantic_scope_waits_even_with_capacity(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self.make_ledger(root)
            self.create(ledger, 1, lease="path:bob/driver.py")
            blocked = self.create(ledger, 2, lease="path:bob")

            self.assertEqual(blocked["state"], "QUEUED")
            self.assertEqual(blocked["blocked_reason"], "SCOPE_CONFLICT:run-1")

            ledger.cancel_run("run-1", reason="test")
            self.assertEqual(ledger.get_run("run-2")["state"], "ACTIVE")

    def test_dependency_waits_for_actual_integration(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self.make_ledger(root)
            self.create(ledger, 1)
            dependent = self.create(
                ledger,
                2,
                depends_on=["run-1"],
            )
            self.assertEqual(dependent["state"], "QUEUED")
            self.assertEqual(dependent["blocked_reason"], "DEPENDENCY:run-1")

            ledger.mark_ready_for_integration(
                "run-1",
                verified_base_sha="base-sha",
                verified_head_sha="head-1",
                verification={"tests": "PASS"},
            )
            self.assertEqual(ledger.get_run("run-2")["state"], "QUEUED")

            ledger.begin_integration("run-1", canonical_sha="base-sha")
            ledger.complete_integration("run-1", canonical_sha="canonical-after-1")
            self.assertEqual(ledger.get_run("run-2")["state"], "ACTIVE")

    def test_one_running_cognition_per_run_has_stable_request_correlation(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self.make_ledger(root)
            self.create(ledger, 1)

            cognition = ledger.begin_cognition(
                "run-1",
                purpose="repair browser",
                request_id="req-explicit-1",
            )
            self.assertEqual(cognition["run_id"], "run-1")
            self.assertEqual(cognition["request_id"], "req-explicit-1")
            self.assertEqual(cognition["state"], "RUNNING")

            with self.assertRaises(ProtocolError):
                ledger.begin_cognition("run-1", purpose="overlap")

            ledger.finish_cognition(
                cognition["cognition_id"],
                success=True,
                summary="done",
            )
            next_cognition = ledger.begin_cognition(
                "run-1",
                purpose="next bounded question",
            )
            self.assertNotEqual(
                cognition["request_id"],
                next_cognition["request_id"],
            )

    def test_integration_queue_is_serial_and_stale_candidates_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self.make_ledger(root)
            self.create(ledger, 1)
            self.create(ledger, 2)
            for run_id, head in (("run-1", "head-1"), ("run-2", "head-2")):
                ledger.mark_ready_for_integration(
                    run_id,
                    verified_base_sha="old-canonical",
                    verified_head_sha=head,
                    verification={"tests": "PASS"},
                )

            plan = ledger.integration_plan("new-canonical")
            self.assertEqual(
                plan["queue"][0]["action"],
                "REBASE_REVERIFY_REQUIRED",
            )
            self.assertEqual(
                plan["queue"][1]["action"],
                "WAIT_FOR_EARLIER_INTEGRATION",
            )
            with self.assertRaises(ProtocolError):
                ledger.begin_integration("run-1", canonical_sha="new-canonical")
            with self.assertRaises(ProtocolError):
                ledger.begin_integration("run-2", canonical_sha="old-canonical")

            ledger.record_rebase_verification(
                "run-1",
                verified_base_sha="new-canonical",
                verified_head_sha="rebased-head-1",
                verification={"tests": "PASS", "rebase": "PASS"},
            )
            claimed = ledger.begin_integration(
                "run-1",
                canonical_sha="new-canonical",
            )
            self.assertEqual(claimed["state"], "INTEGRATING")

    def test_repository_caps_and_integration_queues_are_independent(self):
        with tempfile.TemporaryDirectory() as root:
            repo_a = self.make_ledger(root, state_name="repo-a.json")
            repo_b = self.make_ledger(
                root,
                repository_full_name="owner/repo-b",
                repository_id=2,
                state_name="repo-b.json",
            )
            for index in range(1, 5):
                self.create(repo_a, index)
            for index in range(101, 104):
                self.create(repo_b, index)

            self.assertEqual(repo_a.get_run("run-4")["state"], "QUEUED")
            self.assertEqual(repo_a.get_run("run-4")["blocked_reason"], "CAPACITY")
            self.assertEqual(repo_b.snapshot()["active_run_count"], 3)

            repo_a.mark_ready_for_integration(
                "run-1",
                verified_base_sha="base-sha",
                verified_head_sha="head-a",
                verification={"tests": "PASS"},
            )
            repo_b.mark_ready_for_integration(
                "run-101",
                verified_base_sha="base-sha",
                verified_head_sha="head-b",
                verification={"tests": "PASS"},
            )
            self.assertEqual(repo_a.snapshot()["integration_queue"], ["run-1"])
            self.assertEqual(repo_b.snapshot()["integration_queue"], ["run-101"])

    def test_ledger_repository_identity_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self.make_ledger(root, state_name="shared.json")
            self.create(ledger, 1)
            with self.assertRaises(ConfigurationError):
                self.make_ledger(
                    root,
                    repository_full_name="owner/repo-b",
                    repository_id=2,
                    state_name="shared.json",
                )

    def test_restart_interrupts_running_cognition_and_reopens_integration_gate(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self.make_ledger(root)
            self.create(ledger, 1)
            cognition = ledger.begin_cognition("run-1", purpose="work")
            ledger.finish_cognition(cognition["cognition_id"], success=True)
            ledger.mark_ready_for_integration(
                "run-1",
                verified_base_sha="base-sha",
                verified_head_sha="head-1",
                verification={"tests": "PASS"},
            )
            ledger.begin_integration("run-1", canonical_sha="base-sha")

            restarted = self.make_ledger(root)
            run = restarted.get_run("run-1")
            self.assertEqual(run["state"], "READY_FOR_INTEGRATION")
            self.assertEqual(run["blocked_reason"], "RECOVERED_REVERIFY_REQUIRED")

            active = restarted.create_run(
                run_id="run-2",
                goal="goal 2",
                workspace="BOB",
                base_ref="feat/bob-core-v1",
                base_sha="base-sha",
                branch="bob/run/run-2",
                worktree_path="C:/tmp/run-2",
                leases=["work:item-2"],
            )
            cognition2 = restarted.begin_cognition("run-2", purpose="interrupted")
            reloaded = self.make_ledger(root)
            recovered = reloaded.snapshot()["cognitions"][cognition2["cognition_id"]]
            self.assertEqual(recovered["state"], "INTERRUPTED")
            self.assertEqual(active["state"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
