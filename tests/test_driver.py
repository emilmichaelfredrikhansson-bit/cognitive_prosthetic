import json
import tempfile
import unittest
from pathlib import Path

from bob.driver import BobRuntime


class FakeBridge:
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []

    def send(self, prompt):
        self.sent.append(prompt)
        return self.responses.pop(0)

    def new_chat(self):
        self.sent.clear()


class FakeGitHub:
    def capabilities(self):
        return ["github.read_file", "github.create_file"]

    def verify_workspace(self, workspace):
        return {
            "repository": workspace.github_repository,
            "repository_id": workspace.github_repository_id,
        }

    def read(self, workspace, tool, args):
        return {"path": args["path"], "sha": "abc", "content": "hello"}

    def effect(self, workspace, tool, args):
        return {"commit_sha": "def", "verified": True}


def make_workspace(tmp):
    Path(tmp, "x.json").write_text(json.dumps({
        "schema": "BOB_WORKSPACE_V1",
        "project": {"name": "X", "code": "X"},
        "github": {
            "repository": "owner/repo",
            "repository_id": 123,
            "default_branch": "main"
        },
        "effects": {"write_branch": True, "open_pr": True}
    }))


class DriverTests(unittest.TestCase):
    def test_closed_loop_read_then_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            bridge = FakeBridge([
                '```bob\n{"type":"BOB.READ","id":"r1","tool":"github.read_file","args":{"path":"README.md"}}\n```',
                "The file says hello."
            ])
            runtime = BobRuntime(workspace_dir=tmp, bridge=bridge)
            runtime.adapters = {"github": FakeGitHub()}
            result = runtime.turn("X", "What does the README say?")
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["visible_messages"], ["The file says hello."])
            self.assertIn("BOB.RESULT", bridge.sent[1])

    def test_manual_relay_read_effect_and_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            runtime = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            runtime.adapters = {"github": FakeGitHub()}

            read = runtime.relay_model_response(
                "X",
                'Checking reality.\n```bob\n{"type":"BOB.READ","id":"r1","tool":"github.read_file","args":{"path":"README.md"}}\n```'
            )
            self.assertEqual(read["status"], "RESULT_READY")
            self.assertEqual(read["visible_text"], "Checking reality.")
            self.assertIn("BOB.RESULT", read["feedback"])

            effect = runtime.relay_model_response(
                "X",
                '```bob\n{"type":"BOB.EFFECT","id":"e1","tool":"github.create_file","args":{"path":"x.txt","content":"x","branch":"bob/test"}}\n```'
            )
            self.assertEqual(effect["status"], "AWAITING_APPROVAL")
            pending_id = effect["pending"][0]["pending_id"]

            approved = runtime.relay_approve(pending_id)
            self.assertEqual(approved["status"], "PASS")
            self.assertIn("BOB.RESULT", approved["feedback"])

            done = runtime.relay_model_response(
                "X",
                'All done.\n```bob\n{"type":"BOB.DONE","id":"done-1","args":{"summary":"complete"}}\n```'
            )
            self.assertEqual(done["status"], "DONE")
            self.assertEqual(done["visible_text"], "All done.")

    def test_effect_stops_for_approval_then_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            bridge = FakeBridge([
                '```bob\n{"type":"BOB.EFFECT","id":"e1","tool":"github.create_file","args":{"path":"x.txt","content":"x","branch":"bob/test"}}\n```',
                "Applied and verified."
            ])
            runtime = BobRuntime(workspace_dir=tmp, bridge=bridge)
            runtime.adapters = {"github": FakeGitHub()}
            first = runtime.turn("X", "Create x")
            self.assertEqual(first["status"], "AWAITING_APPROVAL")
            pending_id = first["pending"][0]["pending_id"]
            second = runtime.approve(pending_id)
            self.assertEqual(second["status"], "COMPLETE")
            self.assertEqual(second["visible_messages"], ["Applied and verified."])


    def test_workspace_qualification_requires_every_configured_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "x.json").write_text(json.dumps({
                "schema": "BOB_WORKSPACE_V1",
                "project": {"name": "X", "code": "X"},
                "github": {
                    "repository": "owner/repo",
                    "repository_id": 123,
                    "default_branch": "main"
                },
                "providers": {
                    "supabase": {"project_id": "project-ref"}
                },
                "effects": {}
            }))
            runtime = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            runtime.adapters = {"github": FakeGitHub()}

            result = runtime.qualify_workspace("X")

            self.assertFalse(result["qualified"])
            self.assertEqual(result["checks"]["github"]["status"], "PASS")
            self.assertEqual(result["checks"]["supabase"]["status"], "UNAVAILABLE")

    def test_workspace_qualification_passes_verified_bindings(self):
        class FakeSupabase:
            def capabilities(self):
                return ["supabase.project"]

            def verify_workspace(self, workspace):
                return {
                    "project_id": workspace.providers["supabase"]["project_id"],
                    "organization_id": "org",
                    "status": "ACTIVE_HEALTHY",
                }

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "x.json").write_text(json.dumps({
                "schema": "BOB_WORKSPACE_V1",
                "project": {"name": "X", "code": "X"},
                "github": {
                    "repository": "owner/repo",
                    "repository_id": 123,
                    "default_branch": "main"
                },
                "providers": {
                    "supabase": {"project_id": "project-ref"}
                },
                "effects": {}
            }))
            runtime = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            runtime.adapters = {
                "github": FakeGitHub(),
                "supabase": FakeSupabase(),
            }

            result = runtime.qualify_workspace("X")

            self.assertTrue(result["qualified"])
            self.assertEqual(result["checks"]["github"]["status"], "PASS")
            self.assertEqual(result["checks"]["supabase"]["status"], "PASS")


    def test_manual_relay_start_returns_workspace_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            runtime = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            runtime.adapters = {"github": FakeGitHub()}

            result = runtime.relay_start("X", "Inspect current work")

            self.assertEqual(result["status"], "PROMPT_READY")
            self.assertIn("BOB.WORKSPACE", result["prompt"])
            self.assertIn("Inspect current work", result["prompt"])
            self.assertIn("github.read_file", result["prompt"])


if __name__ == "__main__":
    unittest.main()
