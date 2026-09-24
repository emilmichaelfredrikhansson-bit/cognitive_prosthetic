import json
import tempfile
import unittest
from pathlib import Path

from bob.driver import BobRuntime
from bob.errors import AuthorityError, ConfigurationError, ProtocolError
from bob.module_graph import ModuleGraph, estimate_tokens


def graph_json():
    return json.dumps({
        "schema": "BOB_MODULE_GRAPH_V1",
        "workspace_code": "X",
        "repository_id": 123,
        "coverage": "PARTIAL",
        "modules": [{
            "id": "M",
            "purpose": "Test bounded module",
            "source_paths": ["m.py"],
            "test_paths": [],
            "contract_paths": [],
            "producers": [],
            "consumers": [],
            "invariants": ["stay bounded"],
            "status": "WORKING",
        }],
    })


def make_workspace(tmp):
    Path(tmp, "x.json").write_text(json.dumps({
        "schema": "BOB_WORKSPACE_V1",
        "project": {"name": "X", "code": "X"},
        "github": {
            "repository": "owner/repo",
            "repository_id": 123,
            "default_branch": "main",
        },
        "context": {"module_graph": ".bob/module_graph.json"},
        "effects": {"write_branch": True},
    }), encoding="utf-8")


class FreshBridge:
    def __init__(self, responses):
        self.responses = list(responses)
        self.cognition_prompts = []
        self.stateful_prompts = []

    def cognition(self, prompt):
        self.cognition_prompts.append(prompt)
        return self.responses.pop(0)

    def send(self, prompt):
        self.stateful_prompts.append(prompt)
        raise AssertionError("stateless module path must never call send()")

    def new_chat(self):
        pass


class FakeGitHub:
    def __init__(self, module_content="print('ok')\n"):
        self.files = {
            ".bob/module_graph.json": graph_json(),
            "m.py": module_content,
            "extra.txt": "extra reality",
        }
        self.effects = []

    def capabilities(self):
        return ["github.read_file", "github.replace_file"]

    def verify_workspace(self, workspace):
        return {
            "repository": workspace.github_repository,
            "repository_id": workspace.github_repository_id,
        }

    def branch_head(self, workspace, branch):
        return "head-1"

    def read_file(self, workspace, path, ref=None):
        if path not in self.files:
            raise RuntimeError(f"missing {path}")
        return {
            "path": path,
            "sha": f"sha-{path}",
            "ref": ref,
            "content": self.files[path],
            "size": len(self.files[path]),
        }

    def read(self, workspace, tool, args):
        return self.read_file(workspace, args["path"], args.get("ref"))

    def effect(self, workspace, tool, args):
        self.effects.append((tool, dict(args)))
        if tool == "github.replace_file":
            self.files[args["path"]] = args["content"]
        return {"commit_sha": "commit-1", "verified": True}


class ModuleGraphTests(unittest.TestCase):
    def test_graph_rejects_duplicate_path_ownership(self):
        data = json.loads(graph_json())
        duplicate = dict(data["modules"][0])
        duplicate["id"] = "M2"
        data["modules"].append(duplicate)
        with self.assertRaises(ConfigurationError):
            ModuleGraph.from_dict(data)

    def test_token_measurement_is_deterministic(self):
        self.assertEqual(estimate_tokens("abc"), 1)
        self.assertEqual(estimate_tokens("abcd"), 2)
        self.assertEqual(estimate_tokens("abc"), estimate_tokens("abc"))


class StatelessModuleRuntimeTests(unittest.TestCase):
    def test_compiled_context_includes_protocol_output_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            bridge = FreshBridge([
                '```bob\n{"type":"BOB.DONE","id":"d1","args":{"summary":"done"}}\n```'
            ])
            runtime = BobRuntime(workspace_dir=tmp, bridge=bridge)
            runtime.adapters = {"github": FakeGitHub()}

            runtime.module_turn("X", "M", "Finish it", ref="dev")

            prompt = bridge.cognition_prompts[0]
            self.assertIn("BOB protocol output contract", prompt)
            self.assertIn("non-empty id", prompt)
            self.assertIn("DONE={type:'BOB.DONE'", prompt)

    def test_read_continuation_recompiles_into_fresh_cognition(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            bridge = FreshBridge([
                'Need more reality.\n```bob\n{"type":"BOB.READ","id":"r1","tool":"github.read_file","args":{"path":"extra.txt"}}\n```',
                'Solved.\n```bob\n{"type":"BOB.DONE","id":"d1","args":{"summary":"done"}}\n```',
            ])
            runtime = BobRuntime(workspace_dir=tmp, bridge=bridge)
            runtime.adapters = {"github": FakeGitHub()}

            result = runtime.module_turn("X", "M", "Solve bounded problem", ref="dev")

            self.assertEqual(result["status"], "DONE")
            self.assertEqual(result["mode"], "STATELESS_MODULE")
            self.assertEqual(len(bridge.cognition_prompts), 2)
            self.assertEqual(bridge.stateful_prompts, [])
            self.assertIn('"ref": "dev"', bridge.cognition_prompts[0])
            self.assertIn("BOB.RESULT", bridge.cognition_prompts[1])
            self.assertIn("extra reality", bridge.cognition_prompts[1])

    def test_effect_approval_resumes_in_fresh_cognition(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            bridge = FreshBridge([
                '```bob\n{"type":"BOB.EFFECT","id":"e1","tool":"github.replace_file","args":{"path":"m.py","content":"print(2)\\n","branch":"dev","expected_sha":"sha-m.py"}}\n```',
                'Applied.\n```bob\n{"type":"BOB.DONE","id":"d1","args":{"summary":"verified"}}\n```',
            ])
            github = FakeGitHub()
            runtime = BobRuntime(workspace_dir=tmp, bridge=bridge)
            runtime.adapters = {"github": github}

            first = runtime.module_turn("X", "M", "Change module safely", ref="dev")
            self.assertEqual(first["status"], "AWAITING_APPROVAL")
            pending_id = first["pending"][0]["pending_id"]

            second = runtime.approve(pending_id)

            self.assertEqual(second["status"], "DONE")
            self.assertEqual(len(bridge.cognition_prompts), 2)
            self.assertEqual(bridge.stateful_prompts, [])
            self.assertEqual(github.files["m.py"], "print(2)\n")
            self.assertIn("BOB.RESULT", bridge.cognition_prompts[1])

    def test_normal_module_effect_cannot_escape_manifest_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            bridge = FreshBridge([
                '```bob\n{"type":"BOB.EFFECT","id":"e1","tool":"github.replace_file","args":{"path":"extra.txt","content":"changed","branch":"dev","expected_sha":"sha-extra.txt"}}\n```'
            ])
            runtime = BobRuntime(workspace_dir=tmp, bridge=bridge)
            runtime.adapters = {"github": FakeGitHub()}

            with self.assertRaises(AuthorityError) as ctx:
                runtime.module_turn("X", "M", "Change unrelated file", ref="dev")

            self.assertIn("does not own effect path", str(ctx.exception))

    def test_normal_module_effect_must_stay_on_working_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            bridge = FreshBridge([
                '```bob\n{"type":"BOB.EFFECT","id":"e1","tool":"github.replace_file","args":{"path":"m.py","content":"print(3)\\\\n","branch":"other","expected_sha":"sha-m.py"}}\n```'
            ])
            runtime = BobRuntime(workspace_dir=tmp, bridge=bridge)
            runtime.adapters = {"github": FakeGitHub()}

            with self.assertRaises(AuthorityError) as ctx:
                runtime.module_turn("X", "M", "Change wrong branch", ref="dev")

            self.assertIn("must equal working ref", str(ctx.exception))

    def test_oversized_module_cannot_claim_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            bridge = FreshBridge([
                '```bob\n{"type":"BOB.DONE","id":"d1","args":{"summary":"done"}}\n```'
            ])
            runtime = BobRuntime(workspace_dir=tmp, bridge=bridge)
            runtime.adapters = {"github": FakeGitHub("x" * 45001)}

            with self.assertRaises(ProtocolError):
                runtime.module_turn("X", "M", "Finish it", ref="dev")

            self.assertIn('"mode": "ARCHITECTURE_REPAIR"', bridge.cognition_prompts[0])

    def test_module_graph_status_reports_cap_compliance(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            runtime = BobRuntime(workspace_dir=tmp, bridge=FreshBridge([]))
            runtime.adapters = {"github": FakeGitHub()}

            status = runtime.module_graph_status("X", ref="dev")

            self.assertEqual(status["module_hard_cap_tokens"], 15000)
            self.assertEqual(status["modules"][0]["id"], "M")
            self.assertTrue(status["modules"][0]["compliant"])
            self.assertEqual(
                status["modules"][0]["footprint"]["measurement"],
                "BOB_TOKEN_ESTIMATE_V1",
            )


if __name__ == "__main__":
    unittest.main()
