import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bob.errors import ProtocolError
from bob.work_campaigns import (
    CANCELLED,
    COMPLETED,
    DEADLINE_REACHED,
    RUNNING,
    WorkCampaignManager,
)
from bob.workspaces import WorkspaceRegistry
from bob.worktree_coordination import RepositoryCoordinatorRegistry


class FakeClock:
    def __init__(self):
        self.value = datetime(2026, 9, 26, 6, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value

    def advance(self, seconds: int):
        self.value += timedelta(seconds=seconds)


def init_repo(root: Path, name: str, repository: str) -> Path:
    repo = root / name
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"],
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
        ["git", "remote", "add", "origin", f"https://github.com/{repository}.git"],
        cwd=repo,
        check=True,
    )
    return repo


def make_environment(root: Path, *, bind_two: bool = True):
    repo_one = init_repo(root, "repo-one", "owner/one")
    repo_two = init_repo(root, "repo-two", "owner/two")
    workspace_dir = root / "workspaces"
    workspace_dir.mkdir()
    for code, repository, repository_id in (
        ("ONE", "owner/one", 1),
        ("TWO", "owner/two", 2),
    ):
        payload = {
            "schema": "BOB_WORKSPACE_V1",
            "project": {"name": code, "code": code},
            "github": {
                "repository": repository,
                "repository_id": repository_id,
                "default_branch": "main",
            },
            "context": {},
            "providers": {},
            "effects": {},
        }
        (workspace_dir / f"{code.lower()}.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )
    bindings = {
        1: {
            "repository_full_name": "owner/one",
            "repository_id": 1,
            "repo_root": repo_one,
            "canonical_ref": "main",
            "state_path": root / "ledger-one.json",
            "worktree_root": root / "worktrees-one",
        }
    }
    if bind_two:
        bindings[2] = {
            "repository_full_name": "owner/two",
            "repository_id": 2,
            "repo_root": repo_two,
            "canonical_ref": "main",
            "state_path": root / "ledger-two.json",
            "worktree_root": root / "worktrees-two",
        }
    workspaces = WorkspaceRegistry(workspace_dir)
    executions = RepositoryCoordinatorRegistry(
        workspaces,
        repository_bindings=bindings,
    )
    return workspaces, executions


class WorkCampaignTests(unittest.TestCase):
    def test_deadline_closes_new_admission_without_killing_active_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspaces, executions = make_environment(root)
            clock = FakeClock()
            manager = WorkCampaignManager(
                root / "campaigns.json",
                workspaces,
                executions,
                clock=clock,
            )
            campaign = manager.create(
                goal="bounded work",
                workspace_codes=["ONE"],
                duration_seconds=3600,
            )
            started = manager.start(campaign["campaign_id"])
            self.assertEqual(started["state"], RUNNING)
            created = manager.create_run(
                campaign["campaign_id"],
                workspace_code="ONE",
                goal="first task",
                base_ref="main",
                leases=["work:first"],
            )
            self.assertEqual(created["run"]["state"], "ACTIVE")

            clock.advance(3601)
            snapshot = manager.snapshot()["campaigns"][0]
            self.assertEqual(snapshot["state"], DEADLINE_REACHED)
            with self.assertRaisesRegex(ProtocolError, "does not admit"):
                manager.create_run(
                    campaign["campaign_id"],
                    workspace_code="ONE",
                    goal="too late",
                    base_ref="main",
                    leases=["work:late"],
                )
            run = executions.coordinator_for_workspace("ONE").ledger.get_run(
                created["run"]["run_id"]
            )
            self.assertEqual(run["state"], "ACTIVE")

            executions.coordinator_for_workspace("ONE").cancel_run(
                run["run_id"],
                reason="safe deadline boundary",
            )
            completed = manager.complete(campaign["campaign_id"])
            self.assertEqual(completed["campaign"]["state"], COMPLETED)

    def test_deadline_crossing_during_run_creation_cancels_unbound_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspaces, executions = make_environment(root)
            clock = FakeClock()
            manager = WorkCampaignManager(
                root / "campaigns.json",
                workspaces,
                executions,
                clock=clock,
            )
            campaign = manager.create(
                goal="race",
                workspace_codes=["ONE"],
                duration_seconds=10,
            )
            manager.start(campaign["campaign_id"])
            execution = executions.coordinator_for_workspace("ONE")
            original = execution.create_run

            def create_then_cross_deadline(**kwargs):
                run = original(**kwargs)
                clock.advance(11)
                return run

            execution.create_run = create_then_cross_deadline
            with self.assertRaisesRegex(ProtocolError, "closed during run bind"):
                manager.create_run(
                    campaign["campaign_id"],
                    workspace_code="ONE",
                    goal="deadline race",
                    base_ref="main",
                    leases=["work:race"],
                )
            snapshot = execution.ledger.snapshot()
            matching = [
                run for run in snapshot["runs"].values()
                if (run.get("authority") or {}).get("campaign_id")
                == campaign["campaign_id"]
            ]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["state"], "CANCELLED")
            self.assertEqual(
                manager.snapshot()["campaigns"][0]["runs"],
                [],
            )

    def test_restart_preserves_running_campaign_and_expires_after_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspaces, executions = make_environment(root)
            clock = FakeClock()
            path = root / "campaigns.json"
            manager = WorkCampaignManager(path, workspaces, executions, clock=clock)
            campaign = manager.create(
                goal="restart",
                workspace_codes=["ONE"],
                duration_seconds=100,
            )
            manager.start(campaign["campaign_id"])
            clock.advance(50)

            restarted = WorkCampaignManager(
                path,
                workspaces,
                executions,
                clock=clock,
            )
            self.assertEqual(
                restarted.snapshot()["campaigns"][0]["state"],
                RUNNING,
            )
            clock.advance(51)
            expired = WorkCampaignManager(
                path,
                workspaces,
                executions,
                clock=clock,
            )
            self.assertEqual(
                expired.snapshot()["campaigns"][0]["state"],
                DEADLINE_REACHED,
            )

    def test_start_fails_closed_when_target_has_no_local_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspaces, executions = make_environment(root, bind_two=False)
            manager = WorkCampaignManager(
                root / "campaigns.json",
                workspaces,
                executions,
                clock=FakeClock(),
            )
            campaign = manager.create(
                goal="needs two repos",
                workspace_codes=["ONE", "TWO"],
                duration_seconds=3600,
            )
            with self.assertRaisesRegex(ProtocolError, "TWO"):
                manager.start(campaign["campaign_id"])

    def test_campaign_runs_keep_repo_capacity_and_no_promotion_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspaces, executions = make_environment(root)
            manager = WorkCampaignManager(
                root / "campaigns.json",
                workspaces,
                executions,
                clock=FakeClock(),
            )
            campaign = manager.create(
                goal="capacity",
                workspace_codes=["ONE"],
                duration_seconds=3600,
            )
            manager.start(campaign["campaign_id"])
            runs = [
                manager.create_run(
                    campaign["campaign_id"],
                    workspace_code="ONE",
                    goal=f"task {index}",
                    base_ref="main",
                    leases=[f"work:item-{index}"],
                )["run"]
                for index in range(4)
            ]
            self.assertEqual([run["state"] for run in runs[:3]], ["ACTIVE"] * 3)
            self.assertEqual(runs[3]["state"], "QUEUED")
            self.assertEqual(runs[3]["blocked_reason"], "CAPACITY")
            for run in runs:
                self.assertEqual(run["lane"], "campaign")
                self.assertEqual(
                    run["authority"]["promotion_authority"],
                    "NONE",
                )
                self.assertFalse(run["authority"]["auto_merge"])
            summary = manager.run_states(campaign["campaign_id"])
            self.assertEqual(summary["count"], 4)

    def test_cancel_closes_admission_but_does_not_kill_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspaces, executions = make_environment(root)
            manager = WorkCampaignManager(
                root / "campaigns.json",
                workspaces,
                executions,
                clock=FakeClock(),
            )
            campaign = manager.create(
                goal="cancel",
                workspace_codes=["ONE"],
                duration_seconds=3600,
            )
            manager.start(campaign["campaign_id"])
            created = manager.create_run(
                campaign["campaign_id"],
                workspace_code="ONE",
                goal="active",
                base_ref="main",
                leases=["work:active"],
            )
            cancelled = manager.cancel(
                campaign["campaign_id"],
                reason="operator stop",
            )
            self.assertEqual(cancelled["campaign"]["state"], CANCELLED)
            self.assertIn(
                created["run"]["run_id"],
                cancelled["runs"]["nonterminal_run_ids"],
            )
            with self.assertRaisesRegex(ProtocolError, "does not admit"):
                manager.create_run(
                    campaign["campaign_id"],
                    workspace_code="ONE",
                    goal="new",
                    base_ref="main",
                    leases=["work:new"],
                )

    def test_non_target_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspaces, executions = make_environment(root)
            manager = WorkCampaignManager(
                root / "campaigns.json",
                workspaces,
                executions,
                clock=FakeClock(),
            )
            campaign = manager.create(
                goal="one only",
                workspace_codes=["ONE"],
                duration_seconds=3600,
            )
            manager.start(campaign["campaign_id"])
            with self.assertRaisesRegex(ProtocolError, "not a campaign target"):
                manager.create_run(
                    campaign["campaign_id"],
                    workspace_code="TWO",
                    goal="wrong repo",
                    base_ref="main",
                    leases=["work:wrong"],
                )


if __name__ == "__main__":
    unittest.main()
