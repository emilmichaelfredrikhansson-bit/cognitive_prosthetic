import tempfile
import unittest
from pathlib import Path

from bob.errors import ProtocolError
from bob.selfdev_checkpoints import SelfDevelopmentCheckpoints
from bob.selfdev_control import SelfDevelopmentControl
from bob.selfdev_execution import SelfDevelopmentExecution
from tests.test_selfdev_checkpoints import (
    bind_item,
    init_repo,
    make_execution,
    make_queue,
)


class SelfDevelopmentControlTests(unittest.TestCase):
    def make_control(self, root: Path):
        repo = init_repo(root)
        queue = make_queue(root / "queue.json")
        execution = make_execution(root, repo)
        selfdev_run = bind_item(queue, execution)
        checkpoints = SelfDevelopmentCheckpoints(
            root / "checkpoints.json",
            queue,
            execution,
        )
        service = SelfDevelopmentExecution(queue, execution)
        return (
            queue,
            execution,
            selfdev_run,
            checkpoints,
            SelfDevelopmentControl(service, checkpoints),
        )

    def test_scope_conflict_checkpoints_and_preempts_for_interactive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue, execution, selfdev_run, checkpoints, control = (
                self.make_control(root)
            )

            result = control.create_interactive(
                execution,
                goal="operator work",
                workspace="BOB",
                base_ref="main",
                leases=["work:selfdev-checkpoint"],
                authority={"operator": True},
            )

            self.assertEqual(result["run"]["state"], "ACTIVE")
            self.assertEqual(result["preemption_status"], "PREEMPTED_SELFDEV")
            self.assertEqual(len(result["preempted"]), 1)
            self.assertEqual(
                execution.ledger.get_run(selfdev_run["run_id"])["state"],
                "PARKED",
            )
            self.assertEqual(checkpoints.snapshot()["count"], 1)
            self.assertEqual(queue.snapshot()["items"][0]["state"], "ACTIVE")

            execution.cancel_run(
                result["run"]["run_id"],
                reason="operator work complete",
            )
            resumed = control.resume_after_interactive(
                result["run"]["run_id"]
            )
            self.assertEqual(resumed["count"], 1)
            self.assertEqual(
                execution.ledger.get_run(selfdev_run["run_id"])["state"],
                "ACTIVE",
            )
    def test_dirty_selfdev_fails_closed_instead_of_preempting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, execution, selfdev_run, checkpoints, control = self.make_control(root)
            worktree = Path(selfdev_run["worktree_path"])
            (worktree / "README.md").write_text("dirty\n", encoding="utf-8")

            result = control.create_interactive(
                execution,
                goal="operator conflict",
                workspace="BOB",
                base_ref="main",
                leases=["work:selfdev-checkpoint"],
            )

            self.assertEqual(result["run"]["state"], "QUEUED")
            self.assertEqual(
                result["run"]["blocked_reason"],
                f"SCOPE_CONFLICT:{selfdev_run['run_id']}",
            )
            self.assertEqual(result["preemption_status"], "NO_SAFE_PREEMPTION")
            self.assertEqual(result["preempted"], [])
            self.assertEqual(checkpoints.snapshot()["count"], 0)
            self.assertEqual(
                execution.ledger.get_run(selfdev_run["run_id"])["state"],
                "ACTIVE",
            )

    def test_capacity_pressure_preempts_one_safe_selfdev_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, execution, selfdev_run, _, control = self.make_control(root)
            execution.create_run(
                goal="interactive one",
                workspace="BOB",
                base_ref="main",
                leases=["work:one"],
            )
            execution.create_run(
                goal="interactive two",
                workspace="BOB",
                base_ref="main",
                leases=["work:two"],
            )
            self.assertEqual(execution.snapshot()["active_run_count"], 3)

            result = control.create_interactive(
                execution,
                goal="operator capacity",
                workspace="BOB",
                base_ref="main",
                leases=["work:three"],
            )

            self.assertEqual(result["run"]["state"], "ACTIVE")
            self.assertEqual(result["preemption_status"], "PREEMPTED_SELFDEV")
            self.assertEqual(
                execution.ledger.get_run(selfdev_run["run_id"])["state"],
                "PARKED",
            )
            self.assertEqual(execution.snapshot()["active_run_count"], 3)

    def test_mixed_scope_conflict_does_not_unnecessarily_preempt_selfdev(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, execution, selfdev_run, checkpoints, control = self.make_control(root)
            other = execution.create_run(
                goal="other operator work",
                workspace="BOB",
                base_ref="main",
                leases=["work:other-operator"],
            )
            self.assertEqual(other["state"], "ACTIVE")

            result = control.create_interactive(
                execution,
                goal="operator needs both scopes",
                workspace="BOB",
                base_ref="main",
                leases=["work:selfdev-checkpoint", "work:other-operator"],
            )

            self.assertEqual(result["run"]["state"], "QUEUED")
            self.assertEqual(result["preemption_status"], "NO_SAFE_PREEMPTION")
            self.assertEqual(result["preempted"], [])
            self.assertEqual(checkpoints.snapshot()["count"], 0)
            self.assertEqual(
                execution.ledger.get_run(selfdev_run["run_id"])["state"],
                "ACTIVE",
            )

    def test_resume_requires_terminal_interactive_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, execution, _, _, control = self.make_control(root)
            result = control.create_interactive(
                execution,
                goal="operator work",
                workspace="BOB",
                base_ref="main",
                leases=["work:selfdev-checkpoint"],
            )
            with self.assertRaisesRegex(ProtocolError, "terminal"):
                control.resume_after_interactive(result["run"]["run_id"])


if __name__ == "__main__":
    unittest.main()
