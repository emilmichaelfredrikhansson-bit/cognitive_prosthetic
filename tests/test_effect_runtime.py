import tempfile
import unittest

from bob.driver import BobRuntime
from bob.errors import AuthorityError
from bob.protocol import BobMessage
from tests.test_driver import FakeBridge, FakeGitHub, make_workspace


class EffectAuthorityTests(unittest.TestCase):
    def _runtime(self, tmp):
        make_workspace(tmp)
        runtime = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
        github = FakeGitHub()
        runtime.adapters = {"github": github}
        return runtime, github, runtime.registry.get("X")

    def test_candidate_hash_binds_staged_branch_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, github, workspace = self._runtime(tmp)
            message = BobMessage(
                "BOB.EFFECT",
                "e1",
                "github.create_file",
                {"path": "x.txt", "content": "hello", "branch": "main"},
                {},
            )
            first_preview = runtime._preview_effect(workspace, message)
            first_hash = runtime._candidate_hash(workspace, message, first_preview)
            github.branch_sha = "branch-def"
            second_preview = runtime._preview_effect(workspace, message)
            second_hash = runtime._candidate_hash(workspace, message, second_preview)
            self.assertNotEqual(first_hash, second_hash)

    def test_reject_consumes_staged_effect_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, github, workspace = self._runtime(tmp)
            message = BobMessage(
                "BOB.EFFECT",
                "e2",
                "github.create_file",
                {"path": "x.txt", "content": "hello", "branch": "main"},
                {},
            )
            staged = runtime._stage_effect(workspace, message)
            result = runtime.reject(staged["pending_id"])
            self.assertEqual(result["status"], "REJECTED")
            self.assertEqual(github.effects, [])

    def test_pending_effect_survives_restart_and_executes_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, github, workspace = self._runtime(tmp)
            message = BobMessage(
                "BOB.EFFECT",
                "e3",
                "github.create_file",
                {"path": "x.txt", "content": "hello", "branch": "main"},
                {},
            )
            staged = first._stage_effect(workspace, message)
            self.assertEqual(first.approval_status()["count"], 1)

            second = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            second.adapters = {"github": github}
            self.assertEqual(second.approval_status()["count"], 1)
            result = second.relay_approve(staged["pending_id"])
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(len(github.effects), 1)

            third = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            third.adapters = {"github": github}
            self.assertEqual(third.approval_status()["count"], 0)
            self.assertEqual(len(github.effects), 1)

    def test_restarted_pending_effect_revalidates_and_fails_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, github, workspace = self._runtime(tmp)
            message = BobMessage(
                "BOB.EFFECT",
                "e4",
                "github.create_file",
                {"path": "x.txt", "content": "hello", "branch": "main"},
                {},
            )
            staged = first._stage_effect(workspace, message)
            github.branch_sha = "branch-moved"
            second = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            second.adapters = {"github": github}
            with self.assertRaises(AuthorityError):
                second.relay_approve(staged["pending_id"])
            self.assertEqual(github.effects, [])
            self.assertEqual(second.approval_status()["count"], 0)


if __name__ == "__main__":
    unittest.main()
