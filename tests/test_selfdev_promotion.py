import subprocess
import tempfile
import unittest
from pathlib import Path

from bob.errors import ConfigurationError, ProtocolError
from bob.selfdev_execution import SelfDevelopmentExecution
from bob.selfdev_promotion import (
    APPROVED,
    PENDING,
    REBASE,
    REJECTED,
    STALE,
    SelfDevelopmentPromotionGate,
)
from tests.test_selfdev_checkpoints import (
    CANONICAL,
    init_repo,
    make_execution,
    make_queue,
)


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=path,
        text=True,
    ).strip()


def make_qualified(root: Path):
    repo = init_repo(root)
    queue = make_queue(root / "queue.json")
    execution = make_execution(root, repo)
    service = SelfDevelopmentExecution(queue, execution)
    queue.enqueue(
        goal="qualified candidate",
        leases=["work:promotion-test"],
        item_id="candidate",
    )
    claimed = service.claim_next(base_ref=CANONICAL)
    run = claimed["run"]
    worktree = Path(run["worktree_path"])
    readme = worktree / "README.md"
    readme.write_text("root\ncandidate\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=worktree, check=True)
    subprocess.run(
        ["git", "commit", "-m", "candidate"],
        cwd=worktree,
        check=True,
        capture_output=True,
    )
    candidate_head = git(worktree, "rev-parse", "HEAD")
    execution.cancel_run(run["run_id"], reason="qualification complete")
    finished = service.finish_item(
        "candidate",
        state="QUALIFIED",
        verification={"tests": "PASS", "review": "deterministic"},
    )
    return repo, queue, execution, service, finished["item"], candidate_head


class SelfDevelopmentPromotionGateTests(unittest.TestCase):
    def test_proposal_and_approval_bind_exact_heads_without_merging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, queue, execution, _, item, candidate_head = make_qualified(root)
            canonical_before = execution.worktrees.resolve_ref(CANONICAL)
            gate = SelfDevelopmentPromotionGate(
                root / "promotions.json",
                queue,
                execution,
            )

            proposal = gate.create(item["item_id"])
            self.assertEqual(proposal["state"], PENDING)
            self.assertEqual(proposal["candidate_head_sha"], candidate_head)
            self.assertEqual(proposal["canonical_sha_current"], canonical_before)
            self.assertEqual(proposal["merge_authority"], "NONE")
            self.assertFalse(proposal["provider_effect_performed"])

            approved = gate.approve(
                proposal["proposal_id"],
                expected_candidate_head_sha=candidate_head,
                expected_canonical_sha=canonical_before,
            )
            self.assertEqual(approved["state"], APPROVED)
            self.assertEqual(approved["merge_authority"], "NONE")
            self.assertFalse(approved["provider_effect_performed"])
            self.assertEqual(
                execution.worktrees.resolve_ref(CANONICAL),
                canonical_before,
            )

    def test_candidate_move_after_qualification_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, queue, execution, _, item, _ = make_qualified(root)
            gate = SelfDevelopmentPromotionGate(
                root / "promotions.json",
                queue,
                execution,
            )
            proposal = gate.create(item["item_id"])
            run = execution.ledger.get_run(item["execution_run_id"])
            worktree = Path(run["worktree_path"])
            (worktree / "moved.txt").write_text("moved\n", encoding="utf-8")
            subprocess.run(["git", "add", "moved.txt"], cwd=worktree, check=True)
            subprocess.run(
                ["git", "commit", "-m", "move candidate"],
                cwd=worktree,
                check=True,
                capture_output=True,
            )

            stale = gate.revalidate(proposal["proposal_id"])
            self.assertEqual(stale["state"], STALE)
            self.assertIn("QUALIFICATION_STALE", stale["stale_reason"])
            with self.assertRaises(ProtocolError):
                gate.approve(
                    proposal["proposal_id"],
                    expected_candidate_head_sha=proposal["candidate_head_sha"],
                    expected_canonical_sha=proposal["canonical_sha_current"],
                )

    def test_canonical_move_requires_rebase_reverification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, queue, execution, _, item, _ = make_qualified(root)
            gate = SelfDevelopmentPromotionGate(
                root / "promotions.json",
                queue,
                execution,
            )
            proposal = gate.create(item["item_id"])
            (repo / "canonical.txt").write_text("new canonical\n", encoding="utf-8")
            subprocess.run(["git", "add", "canonical.txt"], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "canonical moved"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            stale = gate.revalidate(proposal["proposal_id"])
            self.assertEqual(stale["state"], REBASE)
            self.assertEqual(
                stale["stale_reason"],
                "CANONICAL_NOT_ANCESTOR_OF_CANDIDATE",
            )

    def test_rejection_is_durable_and_has_no_merge_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, queue, execution, _, item, _ = make_qualified(root)
            path = root / "promotions.json"
            gate = SelfDevelopmentPromotionGate(path, queue, execution)
            proposal = gate.create(item["item_id"])

            rejected = gate.reject(
                proposal["proposal_id"],
                reason="operator declined",
            )
            self.assertEqual(rejected["state"], REJECTED)
            self.assertEqual(rejected["merge_authority"], "NONE")

            restarted = SelfDevelopmentPromotionGate(path, queue, execution)
            stored = restarted.snapshot()["proposals"][0]
            self.assertEqual(stored["state"], REJECTED)
            self.assertEqual(stored["review_reason"], "operator declined")
            with self.assertRaises(ProtocolError):
                restarted.approve(
                    proposal["proposal_id"],
                    expected_candidate_head_sha=proposal["candidate_head_sha"],
                    expected_canonical_sha=proposal["canonical_sha_current"],
                )

    def test_store_repository_identity_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, queue, execution, _, item, _ = make_qualified(root)
            path = root / "promotions.json"
            gate = SelfDevelopmentPromotionGate(path, queue, execution)
            gate.create(item["item_id"])

            other_queue = type(queue)(
                root / "other-queue.json",
                repository_full_name="other/repo",
                repository_id=999,
                canonical_ref=CANONICAL,
            )
            with self.assertRaises(ConfigurationError):
                SelfDevelopmentPromotionGate(path, other_queue, execution)

    def test_nonqualified_item_cannot_open_proposal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = init_repo(root)
            queue = make_queue(root / "queue.json")
            execution = make_execution(root, repo)
            queue.enqueue(
                goal="not qualified",
                leases=["work:not-qualified"],
                item_id="queued",
            )
            gate = SelfDevelopmentPromotionGate(
                root / "promotions.json",
                queue,
                execution,
            )
            with self.assertRaisesRegex(ProtocolError, "QUALIFIED"):
                gate.create("queued")


if __name__ == "__main__":
    unittest.main()
