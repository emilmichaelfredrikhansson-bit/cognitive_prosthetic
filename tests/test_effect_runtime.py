import tempfile
import unittest

from bob.driver import BobRuntime
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


if __name__ == "__main__":
    unittest.main()
