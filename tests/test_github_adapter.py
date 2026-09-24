import subprocess
import tempfile
import unittest
from pathlib import Path

from bob.integrations.github import GitHubAdapter
from bob.workspaces import Workspace


def run_git(root, *args):
    result = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def workspace(repository="owner/repo"):
    return Workspace(
        code="X",
        name="X",
        github_repository=repository,
        github_repository_id=123,
        default_branch="main",
        entry_documents=(),
        module_graph_path=".bob/module_graph.json",
        providers={},
        effects={"write_branch": True},
    )


class LocalGitReadTests(unittest.TestCase):
    def make_repo(self, tmp):
        root = Path(tmp, "repo")
        root.mkdir()
        run_git(root, "init")
        run_git(root, "config", "user.email", "bob@example.invalid")
        run_git(root, "config", "user.name", "Bob Test")
        Path(root, "hello.txt").write_text("hello\nworld\n", encoding="utf-8")
        Path(root, "nested").mkdir()
        Path(root, "nested", "item.txt").write_text("item\n", encoding="utf-8")
        run_git(root, "add", ".")
        run_git(root, "commit", "-m", "fixture")
        run_git(root, "branch", "-M", "main")
        run_git(root, "remote", "add", "origin", "https://github.com/owner/repo.git")
        return root

    def test_unauthenticated_matching_repo_reads_exact_local_git_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_repo(tmp)
            adapter = GitHubAdapter("", local_repo_root=str(root))

            result = adapter.read_file(workspace(), "hello.txt", "main")

            self.assertEqual(result["content"], "hello\nworld\n")
            self.assertEqual(result["source"], "local_git")
            self.assertEqual(
                result["sha"],
                run_git(root, "rev-parse", "main:hello.txt"),
            )

    def test_local_read_requires_matching_origin_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_repo(tmp)
            adapter = GitHubAdapter("", local_repo_root=str(root))

            self.assertFalse(adapter._use_local_read(workspace("other/repo")))

    def test_local_list_contents_uses_git_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_repo(tmp)
            adapter = GitHubAdapter("", local_repo_root=str(root))

            items = adapter.read(
                workspace(),
                "github.list_contents",
                {"path": "nested", "ref": "main"},
            )

            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["path"], "nested/item.txt")
            self.assertEqual(items[0]["type"], "file")
            self.assertEqual(items[0]["source"], "local_git")


if __name__ == "__main__":
    unittest.main()
