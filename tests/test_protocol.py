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

    def test_accepts_raw_protocol_json_when_copy_strips_fences(self):
        parsed = parse_model_response(
            '{"type":"BOB.DONE","id":"done-1","args":{"summary":"complete"}}'
        )
        self.assertEqual(parsed.visible_text, "")
        self.assertEqual(len(parsed.messages), 1)
        self.assertEqual(parsed.messages[0].type, "BOB.DONE")

    def test_preserves_non_protocol_raw_json_as_visible_text(self):
        text = '{"status":"ok","value":1}'
        parsed = parse_model_response(text)
        self.assertEqual(parsed.visible_text, text)
        self.assertEqual(parsed.messages, ())

    def test_rejects_unknown_raw_bob_type(self):
        with self.assertRaises(ProtocolError):
            parse_model_response('{"type":"BOB.MAGIC","id":"x","args":{}}')

    def test_rejects_unknown_type(self):
        with self.assertRaises(ProtocolError):
            parse_model_response(
                '```bob\n{"type":"BOB.MAGIC","id":"x","args":{}}\n```'
            )


if __name__ == "__main__":
    unittest.main()
