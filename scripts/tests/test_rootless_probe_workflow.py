"""Keep the disposable rootless runtime capability probe non-executing."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "rootless-fixture-probe.yml"


class RootlessProbeWorkflowTests(unittest.TestCase):
    def test_probe_has_read_only_permissions_and_bounded_runner(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", source)
        self.assertIn("runs-on: ubuntu-latest", source)
        self.assertIn("timeout-minutes: 15", source)
        self.assertIn('python-version: "3.11"', source)
        self.assertIn("inspect_rootless_oci_candidate()", source)

    def test_probe_cannot_launch_or_pull_an_image(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for forbidden in ("podman run", "podman pull", "docker run", "docker pull",
                          "--privileged", "sysctl -w", "curl | sh", "wget | sh",
                          "secrets.", "workflow_dispatch", "schedule:"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
