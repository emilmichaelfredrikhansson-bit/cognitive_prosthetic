import unittest

from bob.errors import ProtocolError
from bob.protocol import parse_model_response


class ProtocolTests(unittest.TestCase):
    def test_extracts_bob_read_and_preserves_visible_text(self):
        text = """I will inspect the file.
```bob
{"type":"BOB.READ","id":"r1","tool":"github.read_file","args":{"path":"README.md"}}
```
"""
        parsed = parse_model_response(text)
        self.assertEqual(parsed.visible_text, "I will inspect the file.")
        self.assertEqual(len(parsed.messages), 1)
        self.assertEqual(parsed.messages[0].type, "BOB.READ")
        self.assertEqual(parsed.messages[0].tool, "github.read_file")

    def test_rejects_unknown_type(self):
        with self.assertRaises(ProtocolError):
            parse_model_response(
                '```bob\n{"type":"BOB.MAGIC","id":"x","args":{}}\n```'
            )


if __name__ == "__main__":
    unittest.main()
