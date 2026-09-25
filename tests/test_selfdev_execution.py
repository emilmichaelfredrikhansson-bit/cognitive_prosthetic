import subprocess
import tempfile
import unittest
from pathlib import Path

from bob.errors import ProtocolError
from bob.selfdev_execution import SelfDevelopmentExecution
from bob.selfdev_queue import SelfDevelopmentQueue
from bob.worktree_coordination import ExecutionCoordinator


REPO = "owner/repo"
REPO_ID = 77
CANONICAL = "main"


def init_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", CANONICAL],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "config", "user.name", "Bob Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "bob@example.invalid"],
        cwd=repo,
        check=True,
    )
    (repo / "README.md").write_text("root\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", f"https://github.com/{REPO}.git"],
        cwd=repo,
        check=True,
    )
    return repo


def make_queue(path: Path) -> SelfDevelopmentQueue:
    return SelfDevelopmentQueue(
        path,
        repository_full_name=REPO,
        repository_id=REPO_ID,
        canonical_ref=CANONICAL,
    )


def make_execution(root: Path, repo: Path) -> ExecutionCoordinator:
    return ExecutionCoordinator(
        repo,
        repository_full_name=REPO,
        repository_id=REPO_ID,
        canonical_ref=CANONICAL,
        state_path=root / "ledger.json",
        worktree_root=root / "worktrees",
    )


class SelfDevelopmentExecutionTests(unittest.TestCase):
    def test_claim_creates_bound_selfdev_run_and_isolated_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue = make_queue(root / "selfdev.json")
            execution = make_execution(root, repo)
            queue.enqueue(
                goal="build lifecycle",
                leases=["module:SELFDEV", "path:bob/example.py"],
                item_id="selfdev-one",
            )

            result = SelfDevelopmentExecution(queue, execution).claim_next(
                base_ref=CANONICAL
            )

            self.assertEqual(result["action"], "CLAIMED")
            self.assertEqual(result["item"]["state"], "ACTIVE")
            self.assertEqual(
                result["item"]["execution_run_id"], result["run"]["run_id"]
            )
            self.assertEqual(result["run"]["lane"], "selfdev")
            self.assertEqual(
                result["run"]["authority"]["selfdev_item_id"], "selfdev-one"
            )
            self.assertEqual(
                result["run"]["authority"]["promotion_authority"], "NONE"
            )
            worktree = Path(result["run"]["worktree_path"])
            self.assertTrue(worktree.exists())
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=worktree,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(branch, result["run"]["branch"])
            self.assertNotEqual(worktree.resolve(), repo.resolve())

    def test_restart_reconciles_same_bound_run_without_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue_path = root / "selfdev.json"
            queue = make_queue(queue_path)
            execution = make_execution(root, repo)
            queue.enqueue(
                goal="restart safe",
                leases=["work:restart"],
                item_id="restart",
            )
            claimed = SelfDevelopmentExecution(queue, execution).claim_next(
                base_ref=CANONICAL
            )
            run_id = claimed["run"]["run_id"]

            restarted_queue = make_queue(queue_path)
            restarted_execution = make_execution(root, repo)
            bridge = SelfDevelopmentExecution(
                restarted_queue, restarted_execution
            )
            result = bridge.reconcile_item("restart")

            self.assertEqual(result["action"], "LIVE_EXECUTION_RECONCILED")
            self.assertEqual(result["item"]["state"], "ACTIVE")
            self.assertEqual(result["item"]["execution_run_id"], run_id)
            self.assertEqual(result["item"]["attempt_count"], 1)
            self.assertEqual(
                list(restarted_execution.ledger.snapshot()["runs"]), [run_id]
            )
            resumed = bridge.claim_next(base_ref=CANONICAL)
            self.assertEqual(resumed["action"], "RESUMED_EXISTING")
            self.assertEqual(resumed["run"]["run_id"], run_id)
            self.assertEqual(
                len(restarted_execution.ledger.snapshot()["runs"]),
                1,
            )

    def test_crash_window_adopts_matching_unbound_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue_path = root / "selfdev.json"
            queue = make_queue(queue_path)
            execution = make_execution(root, repo)
            queue.enqueue(
                goal="adopt orphan",
                leases=["work:adopt"],
                item_id="adopt",
            )
            item = queue.claim_next()
            run = execution.create_run(
                goal=item["goal"],
                workspace="BOB",
                base_ref=CANONICAL,
                leases=item["leases"],
                lane="selfdev",
                authority={
                    "selfdev_item_id": item["item_id"],
                    "promotion_authority": "NONE",
                },
            )
            restarted_queue = make_queue(queue_path)
            bridge = SelfDevelopmentExecution(
                restarted_queue,
                make_execution(root, repo),
            )
            result = bridge.reconcile_item("adopt")

            self.assertEqual(result["action"], "LIVE_EXECUTION_RECONCILED")
            self.assertEqual(
                result["item"]["execution_run_id"], run["run_id"]
            )
            self.assertEqual(result["item"]["attempt_count"], 1)

    def test_qualified_finish_requires_terminal_run_and_records_branch_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue = make_queue(root / "selfdev.json")
            execution = make_execution(root, repo)
            queue.enqueue(
                goal="qualify",
                leases=["work:qualify"],
                item_id="qualify",
            )
            bridge = SelfDevelopmentExecution(queue, execution)
            claimed = bridge.claim_next(base_ref=CANONICAL)
            with self.assertRaisesRegex(ProtocolError, "must be terminal"):
                bridge.finish_item(
                    "qualify",
                    state="QUALIFIED",
                    verification={"tests": "PASS"},
                )

            execution.cancel_run(
                claimed["run"]["run_id"],
                reason="qualification proof complete",
            )
            result = bridge.finish_item(
                "qualify",
                state="QUALIFIED",
                verification={"tests": "PASS"},
            )
            self.assertEqual(result["item"]["state"], "QUALIFIED")
            receipt = result["item"]["verification"]
            self.assertEqual(receipt["tests"], "PASS")
            self.assertEqual(
                receipt["execution"]["run_id"], claimed["run"]["run_id"]
            )
            self.assertEqual(
                receipt["execution"]["promotion_authority"], "NONE"
            )
            self.assertEqual(
                receipt["execution"]["head_sha"],
                execution.worktrees.branch_head(claimed["run"]["branch"]),
            )

    def test_claim_requires_explicit_base_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue = make_queue(root / "selfdev.json")
            queue.enqueue(
                goal="explicit base",
                leases=["work:base"],
                item_id="base",
            )
            bridge = SelfDevelopmentExecution(
                queue,
                make_execution(root, repo),
            )
            with self.assertRaisesRegex(ProtocolError, "explicit base_ref"):
                bridge.claim_next(base_ref="")


    def test_preempt_and_resume_preserves_item_attempt_and_run_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue = make_queue(root / "selfdev.json")
            coordinator = make_execution(root, repo)
            service = SelfDevelopmentExecution(queue, coordinator)
            queue.enqueue(goal="background", leases=["path:bob/example.py"], item_id="preempt")
            claimed = service.claim_next(base_ref="main")
            run_id = claimed["run"]["run_id"]
            attempt = claimed["item"]["attempt_count"]
            parked = service.preempt_for_interactive("preempt", reason="operator work")
            self.assertEqual(parked["run"]["state"], "PARKED")
            reconciled = service.reconcile_item("preempt")
            self.assertEqual(reconciled["action"], "PARKED_FOR_INTERACTIVE")
            resumed = service.resume_preempted("preempt")
            self.assertEqual(resumed["run"]["run_id"], run_id)
            self.assertEqual(resumed["run"]["state"], "ACTIVE")
            self.assertEqual(resumed["item"]["attempt_count"], attempt)


if __name__ == "__main__":
    unittest.main()
