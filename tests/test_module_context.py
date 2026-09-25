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
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

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

    def test_packaged_module_graph_is_path_unique_and_bounded(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / ".bob" / "module_graph.json").read_text(encoding="utf-8"))
        graph = ModuleGraph.from_dict(data)
        for module in graph.modules:
            measured = sum(
                estimate_tokens((root / path).read_text(encoding="utf-8"))
                for path in module.owned_paths
            )
            self.assertLessEqual(
                measured,
                15_000,
                f"{module.module_id} exceeds 15k: {measured}",
            )


if __name__ == "__main__":
    unittest.main()
