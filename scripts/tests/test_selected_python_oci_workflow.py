"""Static safety gates for the disposable selected-source Python OCI fixture."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/selected-python-oci-fixture.yml"


class SelectedPythonOCIWorkflowTests(unittest.TestCase):
    @staticmethod
    def guarded(source: str) -> bool:
        required = (
            "permissions:\n  contents: read", "runs-on: ubuntu-latest",
            "timeout-minutes: 18", 'python-version: "3.11"',
            "inspect_rootless_oci_candidate()", "busybox-static",
            "docker.io/library/python@sha256:09d17d5e4c16d0a7a1eea690bcb7c6ab8616b211f8421e429e97c1bef5bd0ed2",
            'podman --remote=false pull --platform linux/amd64 "$base_ref"',
            "package_selected_source(", "prepare_selected_artifact(",
            "stage_verified_selected_source(", "expected_package_sha256=",
            "expected_review_binding_digest=", "expected_target_id=target",
            "COPY --chmod=0444 app.py /srv/app.py", 'ENTRYPOINT ["python3","-B","/srv/app.py"]',
            '"--pull=never", "--network=none"',
            "--pull=never --network=none --read-only", "--cap-drop=all",
            "--security-opt=no-new-privileges", "--pids-limit=64 --memory=128m",
            "--user=65534:65534", '--network="container:$container"',
            "--entrypoint=/bin/busybox", "check_health", "podman --remote=false stop",
            "podman --remote=false start", "podman --remote=false rm -f",
            "trap cleanup EXIT", "OWNED_SELECTED_PYTHON_RESULT:",
            "no_external_selected_app", "no_human_approval",
        )
        forbidden = (
            "--privileged", "--network=host", "sudo podman", "sysctl -w",
            "curl | sh", "wget | sh", "secrets.", "workflow_dispatch",
            "schedule:", "pull_request_target", "--device", "--volume", "--mount",
            "podman --remote=false exec", "pip install", "npm install",
        )
        return all(s in source for s in required) and not any(s in source for s in forbidden)

    def test_rootless_selected_source_trial_is_bounded(self):
        self.assertTrue(self.guarded(WORKFLOW.read_text(encoding="utf-8")))

    def test_reject_removal_of_authorization_boundary_and_sandbox_guards(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for marker in (
            "stage_verified_selected_source(", "expected_review_binding_digest=",
            "--pull=never --network=none --read-only", "--cap-drop=all",
            "--security-opt=no-new-privileges", "--pids-limit=64 --memory=128m",
            "--user=65534:65534", "trap cleanup EXIT", "podman --remote=false rm -f",
        ):
            with self.subTest(marker=marker):
                self.assertFalse(self.guarded(source.replace(marker, "")))

    def test_reject_privileged_and_external_selected_source_variants(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for extra in ("\nsudo podman run", "\n--privileged", "\n--network=host",
                      "\npip install -r requirements.txt", "\nworkflow_dispatch:",
                      "\n--volume /:/host"):
            with self.subTest(extra=extra):
                self.assertFalse(self.guarded(source + extra))

    def test_source_staged_before_build_and_observed_after_run(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertLess(source.index("stage_verified_selected_source("),
                        source.index('"podman", "--remote=false", "build"'))
        self.assertLess(source.index('podman --remote=false run -d'),
                        source.index('          check_health\n'))
        self.assertEqual(source.count('          check_health\n'), 2)

    def test_only_fixed_owned_fixture_is_selected(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('Path("scripts/fixtures/owned_python_health_app.py").read_bytes()', source)
        self.assertIn('"requirements.txt": "# first-party Python stdlib only\\n"', source)
        self.assertNotIn('github.event.inputs', source)
        self.assertNotIn('pull_request.head.repo', source)


if __name__ == "__main__":
    unittest.main()
