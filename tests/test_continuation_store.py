import tempfile
import unittest
from pathlib import Path

from bob.continuation_store import ContinuationStore
from bob.errors import ProtocolError


class ContinuationStoreTests(unittest.TestCase):
    def test_put_reload_and_remove_are_durable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "continuations.json")
            first = ContinuationStore(path)
            first.put("c1", {
                "workspace_code": "BOB",
                "module_id": "M",
                "problem": "p",
                "ref": "dev",
                "results": ["BOB.RESULT"],
                "effect": {"request_id": "e1", "tool": "github.replace_file"},
            })
            second = ContinuationStore(path)
            self.assertIn("c1", second.snapshot())
            second.remove("c1")
            self.assertEqual(ContinuationStore(path).snapshot(), {})

    def test_put_rejects_non_json_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ContinuationStore(Path(tmp, "continuations.json"))
            with self.assertRaises(ProtocolError):
                store.put("c1", {"bad": object()})


if __name__ == "__main__":
    unittest.main()
