import tempfile
import unittest

from bob.driver import BobRuntime
from bob.errors import AuthorityError, ProtocolError
from tests.test_module_context import FakeGitHub, FreshBridge, make_workspace


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

    def test_effect_continuation_can_resume_without_replaying_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            bridge = FreshBridge([
                '```bob\n{"type":"BOB.EFFECT","id":"e1","tool":"github.replace_file","args":{"path":"m.py","content":"print(2)\\n","branch":"dev","expected_sha":"sha-m.py"}}\n```',
                RuntimeError("CHATGPT_TRANSIENT_UI:RATE_LIMITED"),
                '```bob\n{"type":"BOB.DONE","id":"d1","args":{"summary":"verified"}}\n```',
            ])
            github = FakeGitHub()
            runtime = BobRuntime(workspace_dir=tmp, bridge=bridge)
            runtime.adapters = {"github": github}

            first = runtime.module_turn("X", "M", "Change module safely", ref="dev")
            blocked = runtime.approve(first["pending"][0]["pending_id"])

            self.assertEqual(blocked["status"], "CONTINUATION_BLOCKED")
            self.assertEqual(blocked["error"], "CHATGPT_TRANSIENT_UI:RATE_LIMITED")
            self.assertEqual(len(github.effects), 1)
            self.assertEqual(github.files["m.py"], "print(2)\n")

            resumed = runtime.resume_continuation(blocked["continuation_id"])

            self.assertEqual(resumed["status"], "DONE")
            self.assertEqual(len(github.effects), 1)
            self.assertEqual(len(bridge.cognition_prompts), 3)
            self.assertNotIn(blocked["continuation_id"], runtime.blocked_continuations)

    def test_effect_continuation_survives_runtime_restart_without_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_workspace(tmp)
            github = FakeGitHub()
            first_bridge = FreshBridge([
                '```bob\n{"type":"BOB.EFFECT","id":"e1","tool":"github.replace_file","args":{"path":"m.py","content":"print(2)\\n","branch":"dev","expected_sha":"sha-m.py"}}\n```',
                RuntimeError("CHATGPT_TRANSIENT_UI:RATE_LIMITED"),
            ])
            first_runtime = BobRuntime(workspace_dir=tmp, bridge=first_bridge)
            first_runtime.adapters = {"github": github}
            staged = first_runtime.module_turn("X", "M", "Change module safely", ref="dev")
            blocked = first_runtime.approve(staged["pending"][0]["pending_id"])
            self.assertEqual(blocked["status"], "CONTINUATION_BLOCKED")
            self.assertEqual(len(github.effects), 1)

            second_bridge = FreshBridge([
                '```bob\n{"type":"BOB.DONE","id":"d1","args":{"summary":"verified"}}\n```'
            ])
            second_runtime = BobRuntime(workspace_dir=tmp, bridge=second_bridge)
            second_runtime.adapters = {"github": github}
            self.assertEqual(second_runtime.continuation_status()["count"], 1)
            resumed = second_runtime.resume_continuation(blocked["continuation_id"])
            self.assertEqual(resumed["status"], "DONE")
            self.assertEqual(len(github.effects), 1)
            self.assertEqual(second_runtime.continuation_status()["count"], 0)

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
