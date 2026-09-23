import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "frontend/index.html").read_text()
JS = (ROOT / "frontend/app.js").read_text()
CSS = (ROOT / "frontend/styles.css").read_text()


class FrontendShellTests(unittest.TestCase):
    def test_chatgpt_like_project_shell_is_present(self):
        for marker in (
            'id="projectList"',
            'id="newChat"',
            'id="chat"',
            'id="composer"',
            'id="inspector"',
        ):
            self.assertIn(marker, HTML)

    def test_bob_specific_reality_authority_and_approval_surfaces_are_present(self):
        for marker in ('id="realityChecks"', 'id="authorityList"', 'id="pending"'):
            self.assertIn(marker, HTML)
        self.assertIn("/bob/qualify", JS)
        self.assertIn("/bob/approve", JS)
        self.assertIn("/bob/reject", JS)

    def test_frontend_does_not_fake_persistent_chat_history(self):
        self.assertIn("Conversation history will become persistent", HTML)
        self.assertNotIn('localStorage.setItem("bob.messages"', JS)
        self.assertNotIn('localStorage.setItem("bob.history"', JS)

    def test_project_authority_distinguishes_material_effect_classes(self):
        for effect in (
            "write_branch",
            "open_pr",
            "mutate_production_state",
            "material_spend",
            "deploy",
        ):
            self.assertIn(effect, JS)

    def test_mobile_shell_has_sidebar_and_inspector_drawers(self):
        self.assertIn("@media (max-width: 760px)", CSS)
        self.assertIn(".app-shell.sidebar-open .sidebar", CSS)
        self.assertIn(".app-shell.inspector-open .inspector", CSS)


if __name__ == "__main__":
    unittest.main()
