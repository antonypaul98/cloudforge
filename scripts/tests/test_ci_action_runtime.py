"""Ensure CI's JavaScript actions use Node 24-compatible major versions."""

import re
import unittest
from pathlib import Path


class CIActionRuntimeTests(unittest.TestCase):
    def test_ci_uses_node24_compatible_checkout_and_python_actions(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml").read_text()
        uses = re.findall(
            r"(?m)^\s*-\s*uses:\s*(actions/(?:checkout|setup-python))@v(\d+)\s*$",
            workflow,
        )
        self.assertEqual(len(uses), 2, "Expected one checkout and one setup-python action")
        majors = {name: int(version) for name, version in uses}
        self.assertEqual(set(majors), {"actions/checkout", "actions/setup-python"})
        self.assertGreaterEqual(majors["actions/checkout"], 5)
        self.assertGreaterEqual(majors["actions/setup-python"], 6)


if __name__ == "__main__":
    unittest.main()
