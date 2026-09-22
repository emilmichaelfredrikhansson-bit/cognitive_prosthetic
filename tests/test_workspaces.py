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
                "schema": "BUILDER_WORKSPACE_V1",
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
            self.assertTrue(workspace.effects["write_branch"])

    def test_requires_stable_repo_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "x.json").write_text(json.dumps({
                "schema": "BUILDER_WORKSPACE_V1",
                "project": {"name": "X", "code": "X"},
                "github": {"repository": "owner/repo"}
            }))
            with self.assertRaises(ConfigurationError):
                WorkspaceRegistry(tmp).get("X")


if __name__ == "__main__":
    unittest.main()
