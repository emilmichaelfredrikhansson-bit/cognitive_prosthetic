import unittest

from bob.errors import IdentityMismatch, ProtocolError
from bob.integrations.cloudflare import CloudflareAdapter
from bob.workspaces import Workspace


class FakeHttp:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def request(self, method, path, params=None, json_body=None):
        self.calls.append((method, path, params, json_body))
        key = (method, path)
        if key not in self.responses:
            raise AssertionError(f"unexpected request: {key}")
        return self.responses[key]


def make_workspace(cloudflare):
    return Workspace.from_dict({
        "schema": "BOB_WORKSPACE_V1",
        "project": {"name": "X", "code": "X"},
        "github": {
            "repository": "owner/repo",
            "repository_id": 123,
            "default_branch": "main",
        },
        "providers": {"cloudflare": cloudflare},
        "effects": {},
    })


class CloudflareIdentityTests(unittest.TestCase):
    def test_worker_binding_is_verified_against_remote_state(self):
        adapter = CloudflareAdapter("test-token")
        adapter.http = FakeHttp({
            ("GET", "/accounts/acct/workers/scripts"): [
                {"id": "autoblog-canary", "modified_on": "2026-09-22T00:00:00Z"}
            ]
        })
        workspace = make_workspace({
            "account_id": "acct",
            "worker_script": "autoblog-canary",
        })

        identity = adapter.verify_workspace(workspace)

        self.assertEqual(identity["account_id"], "acct")
        self.assertEqual(identity["identity_anchor"]["kind"], "worker")
        self.assertTrue(identity["identity_anchor"]["verified"])

    def test_wrong_worker_binding_fails_closed(self):
        adapter = CloudflareAdapter("test-token")
        adapter.http = FakeHttp({
            ("GET", "/accounts/acct/workers/scripts"): [{"id": "other-worker"}]
        })
        workspace = make_workspace({
            "account_id": "acct",
            "worker_script": "autoblog-canary",
        })

        with self.assertRaises(IdentityMismatch):
            adapter.verify_workspace(workspace)

    def test_bare_account_id_is_not_sufficient_for_identity_pass(self):
        adapter = CloudflareAdapter("test-token")
        adapter.http = FakeHttp({})
        workspace = make_workspace({"account_id": "acct"})

        with self.assertRaises(ProtocolError):
            adapter.verify_workspace(workspace)


if __name__ == "__main__":
    unittest.main()
