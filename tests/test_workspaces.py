import json
import tempfile
import unittest
from pathlib import Path

from bob.errors import ConfigurationError
from bob.workspaces import WorkspaceRegistry


class WorkspaceTests(unittest.TestCase):
    def test_loads_valid_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "x.json").write_text(json.dumps({
                "schema": "BOB_WORKSPACE_V1",
                "project": {"name": "X", "code": "X"},
                "github": {
                    "repository": "owner/repo",
                    "repository_id": 123,
                    "default_branch": "main"
                },
                "effects": {"write_branch": True}
            }))
            workspace = WorkspaceRegistry(tmp).get("X")
            self.assertEqual(workspace.github_repository_id, 123)
            self.assertEqual(workspace.module_graph_path, ".bob/module_graph.json")
            self.assertTrue(workspace.effects["write_branch"])

    def test_requires_stable_repo_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "x.json").write_text(json.dumps({
                "schema": "BOB_WORKSPACE_V1",
                "project": {"name": "X", "code": "X"},
                "github": {"repository": "owner/repo"}
            }))
            with self.assertRaises(ConfigurationError):
                WorkspaceRegistry(tmp).get("X")

    def test_packaged_real_workspaces_are_isolated(self):
        registry = WorkspaceRegistry(Path(__file__).resolve().parents[1] / "workspaces")
        bob = registry.get("BOB")
        sl = registry.get("SL")
        ab = registry.get("AB")

        self.assertEqual(bob.github_repository_id, 1374229539)
        self.assertEqual(bob.module_graph_path, ".bob/module_graph.json")
        self.assertEqual(sl.github_repository_id, 1306946195)
        self.assertEqual(ab.github_repository_id, 1347272122)
        self.assertEqual(
            len({bob.github_repository_id, sl.github_repository_id, ab.github_repository_id}),
            3,
        )
        for workspace in (sl, ab):
            self.assertTrue(workspace.effects["write_branch"])
            self.assertTrue(workspace.effects["open_pr"])
            self.assertFalse(workspace.effects["mutate_production_state"])
            self.assertFalse(workspace.effects["material_spend"])
            self.assertFalse(workspace.effects["deploy"])


if __name__ == "__main__":
    unittest.main()
