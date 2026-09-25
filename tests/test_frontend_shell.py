import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "frontend/styles.css").read_text(encoding="utf-8")


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

    def test_project_context_files_use_bob_read_and_real_document_viewer(self):
        self.assertIn('id="documentViewer"', HTML)
        self.assertIn("/bob/read", JS)
        self.assertIn('tool: "github.read_file"', JS)

    def test_appearance_is_local_ui_state_not_project_authority(self):
        self.assertIn('id="themeToggle"', HTML)
        self.assertIn('localStorage.setItem("bob.theme"', JS)
        self.assertIn('body[data-theme="dark"]', CSS)

    def test_read_activity_is_rendered_as_collapsible_project_reality(self):
        self.assertIn("function renderActivity", JS)
        self.assertIn("Checked project reality", JS)

    def test_project_search_uses_bounded_bob_backend_not_demo_index(self):
        self.assertIn('id="projectSearchDialog"', HTML)
        self.assertIn("/bob/project-search", JS)
        self.assertIn("configured entry documents", HTML)
        self.assertNotIn('localStorage.setItem("bob.search', JS)

    def test_project_settings_show_read_only_identity_and_instructions_surface(self):
        self.assertIn('id="settingsList"', HTML)
        self.assertIn("Project settings", HTML)
        self.assertIn("Repository ID", JS)
        self.assertIn("ChatGPT Project instructions", JS)

    def test_approval_inbox_is_first_class_without_changing_authority(self):
        self.assertIn('id="approvalInbox"', HTML)
        self.assertIn('id="approvalCount"', HTML)
        self.assertIn("approvalInboxEl.classList.toggle", JS)
        self.assertIn("/bob/approve", JS)

    def test_mobile_shell_has_sidebar_and_inspector_drawers(self):
        self.assertIn("@media (max-width: 760px)", CSS)
        self.assertIn(".app-shell.sidebar-open .sidebar", CSS)
        self.assertIn(".app-shell.inspector-open .inspector", CSS)


if __name__ == "__main__":
    unittest.main()
