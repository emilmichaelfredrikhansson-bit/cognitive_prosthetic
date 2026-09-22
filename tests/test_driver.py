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

    def read(self, workspace, tool, args):
        return {"path": args["path"], "sha": "abc", "content": "hello"}

    def effect(self, workspace, tool, args):
        return {"commit_sha": "def", "verified": True}


def make_workspace(tmp):
    Path(tmp, "x.json").write_text(json.dumps({
        "schema": "BUILDER_WORKSPACE_V1",
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


if __name__ == "__main__":
    unittest.main()
