import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from bob.errors import AuthorityError, IdentityMismatch, ProtocolError
from bob.workspaces import WorkspaceRegistry
from bob.worktree_coordination import (
    ExecutionCoordinator,
    GitWorktreeManager,
    RepositoryCoordinatorRegistry,
)


class GitWorktreeManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Bob Test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "bob@example.invalid"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("root\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.repo, check=True, capture_output=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_worktree_isolated_branch_and_dirty_cleanup_fails_closed(self):
        manager = GitWorktreeManager(
            self.repo,
            self.root / "worktrees",
        )
        base = manager.resolve_ref("main")
        path = manager.ensure_worktree(
            run_id="run-1",
            branch="bob/run/run-1",
            base_sha=base,
        )
        self.assertNotEqual(path.resolve(), self.repo.resolve())
        self.assertEqual(
            subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "bob/run/run-1",
        )

        (path / "new.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(AuthorityError):
            manager.remove_worktree("run-1")


class ExecutionCoordinatorTests(unittest.TestCase):
    def test_fourth_run_is_durable_but_does_not_get_worktree_until_capacity(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Bob Test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "bob@example.invalid"], cwd=repo, check=True)
            (repo / "README.md").write_text("root\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/owner/repo-a.git"],
                cwd=repo,
                check=True,
            )

            coordinator = ExecutionCoordinator(
                repo,
                repository_full_name="owner/repo-a",
                repository_id=1,
                canonical_ref="main",
                state_path=Path(root) / "ledger.json",
                worktree_root=Path(root) / "worktrees",
                max_parallel_runs_per_repository=3,
            )
            runs = [
                coordinator.create_run(
                    goal=f"goal {index}",
                    workspace="BOB",
                    base_ref="main",
                    leases=[f"work:item-{index}"],
                )
                for index in range(1, 5)
            ]
            self.assertEqual([run["state"] for run in runs[:3]], ["ACTIVE"] * 3)
            self.assertEqual(runs[3]["state"], "QUEUED")
            self.assertTrue(Path(runs[0]["worktree_path"]).exists())
            self.assertFalse(Path(runs[3]["worktree_path"]).exists())
            with self.assertRaisesRegex(ProtocolError, "run must be active"):
                coordinator.mark_ready_for_integration(
                    runs[3]["run_id"],
                    verified_base_sha=coordinator.worktrees.resolve_ref("main"),
                    verification={"tests": "PASS"},
                )


    def test_origin_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Bob Test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "bob@example.invalid"], cwd=repo, check=True)
            (repo / "README.md").write_text("root\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/owner/wrong.git"],
                cwd=repo,
                check=True,
            )
            with self.assertRaises(IdentityMismatch):
                ExecutionCoordinator(
                    repo,
                    repository_full_name="owner/repo-a",
                    repository_id=1,
                    canonical_ref="main",
                    state_path=Path(root) / "ledger.json",
                )

    def test_two_workspaces_same_repository_share_coordinator_and_capacity(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            repo = root_path / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Bob Test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "bob@example.invalid"], cwd=repo, check=True)
            (repo / "README.md").write_text("root\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/owner/shared.git"],
                cwd=repo,
                check=True,
            )
            workspace_dir = root_path / "workspaces"
            workspace_dir.mkdir()
            for code in ("ONE", "TWO"):
                payload = {
                    "schema": "BOB_WORKSPACE_V1",
                    "project": {"name": code, "code": code},
                    "github": {
                        "repository": "owner/shared",
                        "repository_id": 77,
                        "default_branch": "main",
                    },
                    "context": {},
                    "providers": {},
                    "effects": {},
                }
                (workspace_dir / f"{code.lower()}.json").write_text(
                    json.dumps(payload), encoding="utf-8"
                )
            registry = RepositoryCoordinatorRegistry(
                WorkspaceRegistry(workspace_dir),
                repository_bindings={
                    77: {
                        "repository_full_name": "owner/shared",
                        "repository_id": 77,
                        "repo_root": repo,
                        "canonical_ref": "main",
                        "state_path": root_path / "shared-ledger.json",
                        "worktree_root": root_path / "shared-worktrees",
                    }
                },
            )
            one = registry.coordinator_for_workspace("ONE")
            two = registry.coordinator_for_workspace("TWO")
            self.assertIs(one, two)
            runs = []
            for index in range(1, 4):
                runs.append(one.create_run(
                    goal=f"one {index}", workspace="ONE", base_ref="main",
                    leases=[f"work:one-{index}"],
                ))
            fourth = two.create_run(
                goal="fourth", workspace="TWO", base_ref="main",
                leases=["work:two-4"],
            )
            self.assertEqual([run["state"] for run in runs], ["ACTIVE"] * 3)
            self.assertEqual(fourth["state"], "QUEUED")
            self.assertEqual(fourth["blocked_reason"], "CAPACITY")


if __name__ == "__main__":
    unittest.main()
