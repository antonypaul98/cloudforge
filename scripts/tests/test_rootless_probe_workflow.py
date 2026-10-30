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
            "podman --remote=false kill --signal KILL",
            "'{{.State.ExitCode}}'", '== "137"',
            "crashed=confirmed crash_exit=137 crash_restarted_health=pass",
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
                       "podman --remote=false stop", "podman --remote=false rm -f",
                       "podman --remote=false kill --signal KILL",
                       "'{{.State.ExitCode}}'", '== "137"'):
            with self.subTest(marker=marker):
                self.assertFalse(self.guarded(original.replace(marker, "")))

    def test_reject_remote_registry_or_privileged_variants(self):
        original = WORKFLOW.read_text(encoding="utf-8")
        for variant in ("\npodman pull alpine", "\n--privileged", "\nsudo podman run",
                        "\nFROM docker.io/library/alpine", "\npull_request_target:"):
            with self.subTest(variant=variant):
                self.assertFalse(self.guarded(original + variant))

    def test_crash_recovery_is_ordered_and_observed(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        initial_stop = source.index('podman --remote=false stop -t 2')
        crash = source.index('podman --remote=false kill --signal KILL')
        exit_code = source.index("'{{.State.ExitCode}}'")
        cleanup = source.rindex('          podman --remote=false rm -f "$container" >/dev/null\n')
        self.assertLess(initial_stop, crash)
        self.assertLess(crash, exit_code)
        self.assertLess(exit_code, cleanup)
        self.assertEqual(source.count('          check_health\n'), 3)

    def test_reject_missing_crash_exit_confirmation(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertFalse(self.guarded(source.replace("'{{.State.ExitCode}}'", "")))
        self.assertFalse(self.guarded(source.replace('== "137"', '== "0"')))

    def test_never_executes_selected_application(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("printf 'cloudforge-owned-fixture-ok", source)
        self.assertIn("/bin/busybox wget -q -O - http://127.0.0.1:8080/health", source)
        self.assertNotIn("demo_selected_artifact", source)
        self.assertNotIn("demo_selected_execution_permit", source)


if __name__ == "__main__":
    unittest.main()
