import json
import tempfile
import unittest
from pathlib import Path

from bob.driver import BobRuntime
from bob.errors import AuthorityError, ProtocolError


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
    def __init__(self):
        self.branch_sha = "branch-abc"
        self.effects = []
        self.reads = []

    def capabilities(self):
        return ["github.read_file", "github.create_file"]

    def verify_workspace(self, workspace):
        return {
            "repository": workspace.github_repository,
            "repository_id": workspace.github_repository_id,
        }

    def branch_head(self, workspace, branch):
        return self.branch_sha

    def read(self, workspace, tool, args):
        path = args["path"]
        self.reads.append(path)
        content = {
            "CURRENT_WORK.md": "Needle alpha\ncontext line",
            "docs/INSTRUCTIONS.md": "Instructions without the target term",
        }.get(path, "hello")
        return {"path": path, "sha": "abc", "content": content}

    def effect(self, workspace, tool, args):
        self.effects.append((tool, dict(args)))
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
        "context": {
            "entry_documents": ["CURRENT_WORK.md", "docs/INSTRUCTIONS.md"]
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


    def test_reject_consumes_pending_without_executing_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            runtime = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            github = FakeGitHub()
            runtime.adapters = {"github": github}

            effect = runtime.relay_model_response(
                "X",
                '```bob\n{"type":"BOB.EFFECT","id":"e-reject","tool":"github.create_file","args":{"path":"x.txt","content":"x","branch":"bob/test"}}\n```'
            )
            pending_id = effect["pending"][0]["pending_id"]

            rejected = runtime.reject(pending_id)

            self.assertEqual(rejected["status"], "REJECTED")
            self.assertEqual(github.effects, [])
            with self.assertRaises(ProtocolError):
                runtime.relay_approve(pending_id)


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


    def test_project_context_search_reads_only_configured_entry_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            runtime = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            github = FakeGitHub()
            runtime.adapters = {"github": github}

            result = runtime.search_project_context("X", "needle")

            self.assertEqual(result["scope"], "entry_documents")
            self.assertEqual(github.reads, ["CURRENT_WORK.md", "docs/INSTRUCTIONS.md"])
            self.assertEqual(result["total_matches"], 1)
            self.assertEqual(result["results"][0]["path"], "CURRENT_WORK.md")
            self.assertEqual(result["results"][0]["line"], 1)
            self.assertTrue(all(item["status"] == "PASS" for item in result["reads"]))

    def test_project_context_search_rejects_unbounded_empty_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            runtime = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            github = FakeGitHub()
            runtime.adapters = {"github": github}

            with self.assertRaises(ProtocolError):
                runtime.search_project_context("X", " ")

            self.assertEqual(github.reads, [])


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


    def test_approval_invalidates_when_git_branch_moves_after_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            runtime = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            github = FakeGitHub()
            runtime.adapters = {"github": github}

            effect = runtime.relay_model_response(
                "X",
                '```bob\n{"type":"BOB.EFFECT","id":"e-drift","tool":"github.create_file","args":{"path":"x.txt","content":"x","branch":"bob/test"}}\n```'
            )
            pending_id = effect["pending"][0]["pending_id"]
            github.branch_sha = "branch-moved"

            with self.assertRaises(AuthorityError):
                runtime.relay_approve(pending_id)

    def test_approval_invalidates_when_workspace_provider_binding_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            runtime = BobRuntime(workspace_dir=tmp, bridge=FakeBridge([]))
            runtime.adapters = {"github": FakeGitHub()}

            effect = runtime.relay_model_response(
                "X",
                '```bob\n{"type":"BOB.EFFECT","id":"e-binding","tool":"github.create_file","args":{"path":"x.txt","content":"x","branch":"bob/test"}}\n```'
            )
            pending_id = effect["pending"][0]["pending_id"]

            path = Path(tmp, "x.json")
            data = json.loads(path.read_text())
            data["providers"] = {"supabase": {"project_id": "different-project"}}
            path.write_text(json.dumps(data))

            with self.assertRaises(AuthorityError):
                runtime.relay_approve(pending_id)


if __name__ == "__main__":
    unittest.main()
