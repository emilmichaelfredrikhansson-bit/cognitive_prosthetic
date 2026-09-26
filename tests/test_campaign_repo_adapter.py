import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bob.campaign_repo_adapter import CampaignRepoAdapter
from bob.errors import AuthorityError
from bob.protocol import parse_model_response
from tests.test_work_campaign_worker import enqueue, make_worker


def effect_message(payload):
    return parse_model_response(json.dumps(payload)).messages[0]


def admitted(root: Path):
    _, _, executions, campaign, queue, worker = make_worker(root)
    enqueue(queue, campaign)
    ready = worker.cycle(campaign["campaign_id"], max_admissions=1)[
        "ready"
    ][0]
    execution = executions.coordinator_for_run(ready["run_id"])
    run = execution.ledger.get_run(ready["run_id"])
    return execution, run


class CampaignRepoAdapterTests(unittest.TestCase):
    def test_read_file_returns_hash_of_exact_worktree_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            execution, run = admitted(Path(tmp))
            adapter = CampaignRepoAdapter(
                execution,
                run,
                write_authorized=False,
            )
            message = effect_message(
                {
                    "type": "BOB.READ",
                    "id": "r1",
                    "tool": "repo.read_file",
                    "args": {"path": "README.md"},
                }
            )

            result = adapter.read(message)

            actual = hashlib.sha256(
                (adapter.worktree / "README.md").read_bytes()
            ).hexdigest()
            self.assertEqual(result["content_sha256"], actual)
            self.assertTrue(result["path"].endswith("README.md"))

    def test_verified_effect_commits_only_isolated_run_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            execution, run = admitted(Path(tmp))
            adapter = CampaignRepoAdapter(
                execution,
                run,
                write_authorized=True,
            )
            source = hashlib.sha256(
                (adapter.worktree / "README.md").read_bytes()
            ).hexdigest()
            message = effect_message(
                {
                    "type": "BOB.EFFECT",
                    "id": "e1",
                    "tool": "repo.replace_file",
                    "args": {
                        "path": "README.md",
                        "content": "candidate\n",
                        "expected_sha256": source,
                    },
                }
            )

            pending = adapter.prepare_effect(message, item_id="work")
            receipt = adapter.apply_pending(pending)

            self.assertTrue(receipt["verified"])
            self.assertEqual(
                (adapter.worktree / "README.md").read_text(
                    encoding="utf-8"
                ),
                "candidate\n",
            )
            self.assertEqual(
                (execution.repo_root / "README.md").read_text(
                    encoding="utf-8"
                ),
                "root\n",
            )
            self.assertEqual(
                execution.worktrees.branch_head(run["branch"]),
                receipt["head_sha"],
            )
            self.assertNotEqual(receipt["head_sha"], run["base_sha"])
            self.assertTrue(adapter.is_clean())

    def test_apply_pending_adopts_exact_already_committed_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            execution, run = admitted(Path(tmp))
            adapter = CampaignRepoAdapter(
                execution,
                run,
                write_authorized=True,
            )
            source = hashlib.sha256(
                (adapter.worktree / "README.md").read_bytes()
            ).hexdigest()
            message = effect_message(
                {
                    "type": "BOB.EFFECT",
                    "id": "e1",
                    "tool": "repo.replace_file",
                    "args": {
                        "path": "README.md",
                        "content": "candidate\n",
                        "expected_sha256": source,
                    },
                }
            )
            pending = adapter.prepare_effect(message, item_id="work")
            first = adapter.apply_pending(pending)

            second = adapter.apply_pending(pending)

            self.assertEqual(second["head_sha"], first["head_sha"])
            self.assertEqual(
                execution.worktrees.branch_head(run["branch"]),
                first["head_sha"],
            )

    def test_write_authority_and_protected_paths_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            execution, run = admitted(Path(tmp))
            adapter = CampaignRepoAdapter(
                execution,
                run,
                write_authorized=False,
            )
            message = effect_message(
                {
                    "type": "BOB.EFFECT",
                    "id": "e1",
                    "tool": "repo.create_file",
                    "args": {"path": "new.txt", "content": "no\n"},
                }
            )
            with self.assertRaises(AuthorityError):
                adapter.prepare_effect(message, item_id="work")

            adapter = CampaignRepoAdapter(
                execution,
                run,
                write_authorized=True,
            )
            secret = effect_message(
                {
                    "type": "BOB.EFFECT",
                    "id": "e2",
                    "tool": "repo.create_file",
                    "args": {"path": ".env", "content": "SECRET=x\n"},
                }
            )
            with self.assertRaises(AuthorityError):
                adapter.prepare_effect(secret, item_id="work")


if __name__ == "__main__":
    unittest.main()
