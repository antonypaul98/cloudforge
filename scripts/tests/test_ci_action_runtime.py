"""Guard CI action runtimes and the read-only PR execution boundary."""

import re
import unittest
from pathlib import Path


class CIActionRuntimeTests(unittest.TestCase):
    @staticmethod
    def _workflow():
        return (Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml").read_text()

    @staticmethod
    def _has_read_only_pr_boundary(workflow):
        # Avoid a YAML dependency in the pre-install infrastructure guard.
        # Fail closed on structural changes rather than guessing their safety.
        triggers = re.search(r"(?m)^on:\s*\n((?:[ \t]+[^\n]*\n)+)", workflow)
        if not triggers:
            return False
        events = re.findall(r"(?m)^  ([a-z_]+):\s*$", triggers.group(1))
        if events != ["push", "pull_request"]:
            return False
        if len(re.findall(r"(?m)^\s*permissions:\s*$", workflow)) != 1:
            return False
        grants = re.search(r"(?m)^permissions:\s*\n((?:[ \t]+[^\n]*\n)+)", workflow)
        return bool(grants and grants.group(1).strip() == "contents: read")

    def test_ci_uses_node24_compatible_checkout_and_python_actions(self):
        uses = re.findall(
            r"(?m)^\s*-\s*uses:\s*(actions/(?:checkout|setup-python))@v(\d+)\s*$",
            self._workflow(),
        )
        self.assertEqual(len(uses), 2, "Expected one checkout and one setup-python action")
        majors = {name: int(version) for name, version in uses}
        self.assertEqual(set(majors), {"actions/checkout", "actions/setup-python"})
        self.assertGreaterEqual(majors["actions/checkout"], 5)
        self.assertGreaterEqual(majors["actions/setup-python"], 6)

    def test_ci_prs_use_read_only_permissions_and_unprivileged_trigger(self):
        self.assertTrue(self._has_read_only_pr_boundary(self._workflow()))

    def test_ci_rejects_synthetic_privilege_escalations(self):
        original = self._workflow()
        variants = {
            "privileged-pr-trigger": original.replace("  pull_request:\n", "  pull_request_target:\n"),
            "write-token": original.replace("  contents: read\n", "  contents: write\n"),
            "job-level-override": original.replace("  test:\n", "  test:\n    permissions:\n      contents: write\n"),
            "extra-token-scope": original.replace("  contents: read\n", "  contents: read\n  actions: write\n"),
        }
        for name, workflow in variants.items():
            with self.subTest(name=name):
                self.assertNotEqual(workflow, original)
                self.assertFalse(self._has_read_only_pr_boundary(workflow))


if __name__ == "__main__":
    unittest.main()
