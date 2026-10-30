"""Guard the bounded disposable-runner OCI trial; never run selected code."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "rootless-fixture-probe.yml"


class RootlessProbeWorkflowTests(unittest.TestCase):
    @staticmethod
    def guarded(source):
        required = (
            "permissions:\n  contents: read", "runs-on: ubuntu-latest",
            "timeout-minutes: 15", 'python-version: "3.11"',
            "inspect_rootless_oci_candidate()", "busybox-static",
            "FROM scratch", "COPY busybox /bin/busybox", "COPY health /srv/health",
            "USER 65534:65534", '"127.0.0.1:8080"',
            "podman --remote=false build --pull=never --network=none",
            "podman --remote=false run -d", "--pull=never --network=none --read-only",
            "--cap-drop=all --security-opt=no-new-privileges",
            "--pids-limit=64 --memory=64m --user=65534:65534",
            "podman --remote=false stop", "podman --remote=false start",
            "podman --remote=false rm -f", "trap cleanup EXIT",
            "OWNED_FIXTURE_RESULT:", "no_selected_app",
        )
        forbidden = (
            "podman pull", "docker pull", "docker run", "--privileged",
            "--network=host", "sudo podman", "sysctl -w", "curl | sh",
            "wget | sh", "secrets.", "workflow_dispatch", "schedule:",
            "pull_request_target", "CONTAINER_HOST", "FROM docker.io",
            "FROM quay.io", "--device", "--volume", "--mount",
        )
        return all(part in source for part in required) and not any(part in source for part in forbidden)

    def test_workflow_is_bounded_rootless_owned_fixture(self):
        self.assertTrue(self.guarded(WORKFLOW.read_text(encoding="utf-8")))

    def test_reject_missing_isolation_or_cleanup_guards(self):
        original = WORKFLOW.read_text(encoding="utf-8")
        for marker in ("--pull=never", "--network=none", "--read-only",
                       "--cap-drop=all", "--security-opt=no-new-privileges",
                       "--pids-limit=64", "--memory=64m", "trap cleanup EXIT",
                       "podman --remote=false stop", "podman --remote=false rm -f"):
            with self.subTest(marker=marker):
                self.assertFalse(self.guarded(original.replace(marker, "")))

    def test_reject_remote_registry_or_privileged_variants(self):
        original = WORKFLOW.read_text(encoding="utf-8")
        for variant in ("\npodman pull alpine", "\n--privileged", "\nsudo podman run",
                        "\nFROM docker.io/library/alpine", "\npull_request_target:"):
            with self.subTest(variant=variant):
                self.assertFalse(self.guarded(original + variant))

    def test_never_executes_selected_application(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("printf 'cloudforge-owned-fixture-ok", source)
        self.assertIn("/bin/busybox wget -q -O - http://127.0.0.1:8080/health", source)
        self.assertNotIn("demo_selected_artifact", source)
        self.assertNotIn("demo_selected_execution_permit", source)


if __name__ == "__main__":
    unittest.main()
