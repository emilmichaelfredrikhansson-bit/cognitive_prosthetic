import subprocess
import tempfile
import unittest
from pathlib import Path

from bob.errors import ProtocolError
from bob.selfdev_checkpoints import SelfDevelopmentCheckpoints
from bob.selfdev_queue import SelfDevelopmentQueue
from bob.worktree_coordination import ExecutionCoordinator


REPO = "owner/repo"
REPO_ID = 77
CANONICAL = "main"


def git(cwd: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout.strip()


def init_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", CANONICAL)
    git(repo, "config", "user.name", "Bob Test")
    git(repo, "config", "user.email", "bob@example.invalid")
    (repo / "README.md").write_text("root\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "init")
    git(repo, "remote", "add", "origin", f"https://github.com/{REPO}.git")
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


def bind_item(
    queue: SelfDevelopmentQueue,
    execution: ExecutionCoordinator,
    *,
    item_id: str = "item",
):
    queue.enqueue(
        goal="bounded experiment",
        leases=["work:selfdev-checkpoint"],
        item_id=item_id,
    )
    item = queue.claim_next()
    run = execution.create_run(
        goal=item["goal"],
        workspace="BOB",
        base_ref=CANONICAL,
        leases=item["leases"],
        lane="selfdev",
        authority={
            "selfdev_item_id": item_id,
            "promotion_authority": "NONE",
        },
    )
    queue.bind_execution_run(item_id, run["run_id"])
    return run


class SelfDevelopmentCheckpointTests(unittest.TestCase):
    def test_clean_checkpoint_is_durable_and_repo_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue = make_queue(root / "queue.json")
            execution = make_execution(root, repo)
            run = bind_item(queue, execution)
            store_path = root / "checkpoints.json"
            manager = SelfDevelopmentCheckpoints(
                store_path,
                queue,
                execution,
            )

            checkpoint = manager.create(
                "item",
                label="known-good",
                verification={"tests": "PASS"},
            )

            self.assertEqual(checkpoint["run_id"], run["run_id"])
            self.assertEqual(checkpoint["branch"], run["branch"])
            self.assertEqual(
                checkpoint["head_sha"],
                execution.worktrees.branch_head(run["branch"]),
            )
            restarted = SelfDevelopmentCheckpoints(
                store_path,
                queue,
                execution,
            )
            snapshot = restarted.snapshot()
            self.assertEqual(snapshot["count"], 1)
            self.assertEqual(
                snapshot["checkpoints"][0]["checkpoint_id"],
                checkpoint["checkpoint_id"],
            )
    def test_revert_discards_committed_and_untracked_experiment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue = make_queue(root / "queue.json")
            execution = make_execution(root, repo)
            run = bind_item(queue, execution)
            manager = SelfDevelopmentCheckpoints(
                root / "checkpoints.json",
                queue,
                execution,
            )
            checkpoint = manager.create("item", label="before experiment")
            worktree = Path(run["worktree_path"])

            (worktree / "README.md").write_text(
                "experimental\n",
                encoding="utf-8",
            )
            git(worktree, "add", "README.md")
            git(worktree, "commit", "-m", "experimental")
            (worktree / "scratch.tmp").write_text("discard me", encoding="utf-8")
            self.assertNotEqual(
                git(worktree, "rev-parse", "HEAD"),
                checkpoint["head_sha"],
            )

            receipt = manager.revert(
                "item",
                checkpoint["checkpoint_id"],
            )

            self.assertEqual(receipt["head_sha"], checkpoint["head_sha"])
            self.assertTrue(receipt["worktree_clean"])
            self.assertEqual(
                (worktree / "README.md").read_text(encoding="utf-8"),
                "root\n",
            )
            self.assertFalse((worktree / "scratch.tmp").exists())
            self.assertEqual(
                manager.snapshot()["checkpoints"][0]["revert_count"],
                1,
            )

    def test_checkpoint_rejects_dirty_or_busy_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue = make_queue(root / "queue.json")
            execution = make_execution(root, repo)
            run = bind_item(queue, execution)
            manager = SelfDevelopmentCheckpoints(
                root / "checkpoints.json",
                queue,
                execution,
            )
            worktree = Path(run["worktree_path"])
            (worktree / "README.md").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(ProtocolError, "clean worktree"):
                manager.create("item")

            git(worktree, "checkout", "--", "README.md")
            cognition = execution.ledger.begin_cognition(
                run["run_id"],
                purpose="experiment",
            )
            with self.assertRaisesRegex(ProtocolError, "safe cognition boundary"):
                manager.create("item")
            execution.ledger.finish_cognition(
                cognition["cognition_id"],
                success=True,
            )
    def test_discard_restores_base_cancels_run_and_removes_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue = make_queue(root / "queue.json")
            execution = make_execution(root, repo)
            run = bind_item(queue, execution)
            manager = SelfDevelopmentCheckpoints(
                root / "checkpoints.json",
                queue,
                execution,
            )
            worktree = Path(run["worktree_path"])
            (worktree / "README.md").write_text("bad experiment\n", encoding="utf-8")
            git(worktree, "add", "README.md")
            git(worktree, "commit", "-m", "bad experiment")
            (worktree / "untracked.txt").write_text("discard", encoding="utf-8")

            receipt = manager.discard(
                "item",
                reason="verification failed",
            )

            self.assertEqual(receipt["action"], "DISCARDED")
            self.assertEqual(receipt["item"]["state"], "DISCARDED")
            self.assertEqual(receipt["run"]["state"], "CANCELLED")
            self.assertTrue(receipt["worktree_removed"])
            self.assertFalse(worktree.exists())
            self.assertEqual(
                execution.worktrees.branch_head(run["branch"]),
                run["base_sha"],
            )
            self.assertEqual(
                receipt["item"]["verification"]["execution"][
                    "promotion_authority"
                ],
                "NONE",
            )
            self.assertEqual(execution.snapshot()["active_run_count"], 0)


if __name__ == "__main__":
    unittest.main()
