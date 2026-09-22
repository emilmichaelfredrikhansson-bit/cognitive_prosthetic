import unittest

from bob.preflight import binding_checks, is_loopback_host, run_preflight


class FakeWorkspace:
    def __init__(self, code):
        self.code = code


class FakeRegistry:
    def __init__(self, codes):
        self._codes = codes

    def list(self):
        return [FakeWorkspace(code) for code in self._codes]


class FakeRuntime:
    def __init__(self, qualifications):
        self.qualifications = qualifications
        self.registry = FakeRegistry(list(qualifications))

    def capabilities(self):
        return {"github": ["github.repo"]}

    def qualify_workspace(self, code):
        result = self.qualifications[code]
        if isinstance(result, Exception):
            raise result
        return result


class RuntimePreflightTests(unittest.TestCase):
    def test_loopback_hosts_are_accepted(self):
        for host in ("127.0.0.1", "127.10.20.30", "::1", "localhost"):
            with self.subTest(host=host):
                self.assertTrue(is_loopback_host(host))

    def test_non_loopback_hosts_fail(self):
        for host in ("0.0.0.0", "192.168.1.20", "10.0.0.2", "example.com"):
            with self.subTest(host=host):
                self.assertFalse(is_loopback_host(host))

    def test_binding_checks_default_to_loopback(self):
        checks = binding_checks({})
        self.assertEqual(checks["bob_api"]["status"], "PASS")
        self.assertEqual(checks["chatgpt_bridge"]["status"], "PASS")

    def test_preflight_passes_only_when_all_selected_workspaces_qualify(self):
        runtime = FakeRuntime({
            "BOB": {"qualified": True},
            "SL": {"qualified": True},
        })
        result = run_preflight(runtime, env={})
        self.assertTrue(result["ok"])
        self.assertEqual(result["available_adapters"], ["github"])

    def test_preflight_fails_closed_for_unqualified_or_erroring_workspace(self):
        runtime = FakeRuntime({
            "BOB": {"qualified": True},
            "SL": {"qualified": False},
            "AB": RuntimeError("credential missing"),
        })
        result = run_preflight(runtime, env={})
        self.assertFalse(result["ok"])
        self.assertEqual(result["workspaces"]["SL"]["status"], "FAIL")
        self.assertEqual(result["workspaces"]["AB"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
