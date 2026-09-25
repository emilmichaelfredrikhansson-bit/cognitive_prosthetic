import tempfile
import unittest
from pathlib import Path

from bob.errors import ProtocolError
from bob.pending_effect_store import PendingEffectStore


class PendingEffectStoreTests(unittest.TestCase):
    def test_put_reload_and_remove_are_durable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "pending.json")
            first = PendingEffectStore(path)
            first.put("p1", {
                "pending_id": "p1",
                "workspace_code": "BOB",
                "message": {
                    "type": "BOB.EFFECT",
                    "id": "e1",
                    "tool": "github.create_file",
                    "args": {"path": "x.txt"},
                },
                "candidate_hash": "hash",
                "effect_class": "write_branch",
                "preview": {"kind": "summary"},
                "continuation": None,
            })
            second = PendingEffectStore(path)
            self.assertIn("p1", second.snapshot())
            second.remove("p1")
            self.assertEqual(PendingEffectStore(path).snapshot(), {})

    def test_put_rejects_non_json_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PendingEffectStore(Path(tmp, "pending.json"))
            with self.assertRaises(ProtocolError):
                store.put("p1", {"bad": object()})


if __name__ == "__main__":
    unittest.main()
