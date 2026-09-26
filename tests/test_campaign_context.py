import json
import unittest

from bob.campaign_context import (
    MAX_CONTINUATION_CONTEXT_CHARS,
    bounded_continuation_results,
)


def result(request_id, *, content="x"):
    return (
        "```bob-result\n"
        + json.dumps(
            {
                "type": "BOB.RESULT",
                "request_id": request_id,
                "tool": "repo.read_file",
                "status": "PASS",
                "data": {
                    "path": "bob/driver.py",
                    "start_line": 1,
                    "end_line": 250,
                    "content": content,
                    "content_sha256": "a" * 64,
                },
            }
        )
        + "\n```"
    )


class CampaignContextTests(unittest.TestCase):
    def test_small_history_is_unchanged(self):
        values = [result("r1", content="small"), result("r2", content="small")]
        self.assertEqual(bounded_continuation_results(values), values)

    def test_large_history_is_bounded_and_keeps_lineage(self):
        values = [
            result(f"r{index}", content=str(index) * 9000)
            for index in range(1, 18)
        ]

        bounded = bounded_continuation_results(values)

        self.assertLessEqual(
            sum(len(value) for value in bounded),
            MAX_CONTINUATION_CONTEXT_CHARS,
        )
        joined = "\n".join(bounded)
        self.assertIn("continuation compacted", joined)
        self.assertIn("request_id=r1", joined)
        self.assertIn('"request_id": "r17"', joined)
        self.assertEqual(values, list(values))


if __name__ == "__main__":
    unittest.main()
