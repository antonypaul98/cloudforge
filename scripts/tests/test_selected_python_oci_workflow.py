"""Static safety gates for the disposable selected-source Python OCI fixture."""
from pathlib import Path
import hashlib
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/selected-python-oci-fixture.yml"
FIXTURE = ROOT / "scripts/fixtures/owned_python_health_app.py"
PINNED_SOURCE_SHA256 = "071b232d0bbf04c2a46bf7538120efc5214f76d7f8dfb921c0d5627c295eed39"


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
            "stage_synthetically_admitted_selected_source(", "verify_staged_selected_source(staged)",
            '"src/cloudforge/demo_selected_oci_stage.py"', '"tests/test_demo_selected_oci_stage.py"',
            "issue_selected_sandbox_permit(", "issue_selected_sandbox_approval(",
            "ledger_path=str(Path(ledger_dir) / \"permit.sqlite\")",
            "now_unix=1100", "expected_package_sha256=",
            "expected_owned_source_sha256 = \"071b232d0bbf04c2a46bf7538120efc5214f76d7f8dfb921c0d5627c295eed39\"",
            "hashlib.sha256(source).hexdigest() != expected_owned_source_sha256",
            "expected_review_binding_digest=", "expected_target_id=target",
            "COPY --chmod=0444 app.py /srv/app.py", 'ENTRYPOINT ["python3","-B","/srv/app.py"]',
            '"--pull=never", "--network=none"',
            "--pull=never --network=none --read-only", "--cap-drop=all",
            "--security-opt=no-new-privileges", "--pids-limit=64 --memory=128m",
            "--user=65534:65534", '--network="container:$container"',
            "--entrypoint=/bin/busybox", "check_health", "podman --remote=false stop",
            "podman --remote=false start", "podman --remote=false kill --signal KILL",
            "'{{.State.ExitCode}}'", '"137"', "podman --remote=false rm -f",
            "trap cleanup EXIT", "OWNED_SELECTED_PYTHON_RESULT:",
            "graceful_stop=pass", "no_external_selected_app", "no_human_approval",
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
            "stage_synthetically_admitted_selected_source(", "expected_review_binding_digest=",
            "COPY --chmod=0444 app.py /srv/app.py",
            "--pull=never --network=none --read-only", "--cap-drop=all",
            "--security-opt=no-new-privileges", "--pids-limit=64 --memory=128m",
            "--user=65534:65534", "trap cleanup EXIT",
            "podman --remote=false kill --signal KILL", "'{{.State.ExitCode}}'",
            "podman --remote=false rm -f",
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
        self.assertLess(source.index("stage_synthetically_admitted_selected_source("),
                        source.index('"podman", "--remote=false", "build"'))
        self.assertLess(source.index('podman --remote=false run -d'),
                        source.index('          check_health\n'))
        self.assertEqual(source.count('          check_health\n'), 3)

    def test_actual_crash_recovery_is_checked_before_cleanup(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        kill = source.index('podman --remote=false kill --signal KILL "$container"')
        exit_code = source.index("{{.State.ExitCode}}", kill)
        recovery_start = source.index('podman --remote=false start "$container"', kill)
        recovered_health = source.index('          check_health\n', recovery_start)
        cleanup = source.index('          podman --remote=false rm -f "$container" >/dev/null', recovered_health)
        self.assertLess(kill, exit_code)
        self.assertLess(exit_code, recovery_start)
        self.assertLess(recovery_start, recovered_health)
        self.assertLess(recovered_health, cleanup)
        self.assertIn("sigkill_exit_137=pass crash_recovery_health=pass", source)

    def test_crash_recovery_guards_reject_missing_kill_or_exit_code(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for marker in ('podman --remote=false kill --signal KILL',
                       "{{.State.ExitCode}}", '"137"'):
            with self.subTest(marker=marker):
                self.assertFalse(self.guarded(source.replace(marker, "")))

    def test_pinned_owned_fixture_digest_matches_exact_checked_in_bytes(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
                         PINNED_SOURCE_SHA256)
        self.assertNotEqual(hashlib.sha256(FIXTURE.read_bytes() + b"# drift").hexdigest(),
                            PINNED_SOURCE_SHA256)

    def test_owned_source_digest_check_precedes_package_and_build(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertLess(source.index("hashlib.sha256(source).hexdigest() != expected_owned_source_sha256"),
                        source.index("package_selected_source("))
        self.assertLess(source.index("package_selected_source("),
                        source.index('"podman", "--remote=false", "build"'))
        for marker in (
            "expected_owned_source_sha256 = \"071b232d0bbf04c2a46bf7538120efc5214f76d7f8dfb921c0d5627c295eed39\"",
            "hashlib.sha256(source).hexdigest() != expected_owned_source_sha256",
        ):
            with self.subTest(marker=marker):
                self.assertFalse(self.guarded(source.replace(marker, "")))

    def test_prebuild_recheck_is_before_containerfile_and_build(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        check = source.index("verify_staged_selected_source(staged)")
        self.assertLess(source.index("stage_synthetically_admitted_selected_source("), check)
        self.assertLess(check, source.index('              containerfile = ('))
        self.assertLess(check, source.index('"podman", "--remote=false", "build"'))
        self.assertFalse(self.guarded(source.replace("verify_staged_selected_source(staged)", "")))

    def test_synthetic_admission_precedes_first_party_build_and_cannot_be_bypassed(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        permit = source.index("issue_selected_sandbox_permit(")
        approval = source.index("issue_selected_sandbox_approval(")
        stage = source.index("stage_synthetically_admitted_selected_source(")
        verify = source.index("verify_staged_selected_source(staged)")
        build = source.index('"podman", "--remote=false", "build"')
        self.assertLess(permit, approval)
        self.assertLess(approval, stage)
        self.assertLess(stage, verify)
        self.assertLess(verify, build)
        self.assertIn("human_authenticated=false", source)
        for marker in (
            "issue_selected_sandbox_permit(",
            "issue_selected_sandbox_approval(",
            "stage_synthetically_admitted_selected_source(",
            'ledger_path=str(Path(ledger_dir) / "permit.sqlite")',
            "now_unix=1100",
        ):
            with self.subTest(marker=marker):
                self.assertFalse(self.guarded(source.replace(marker, "")))

    def test_only_fixed_owned_fixture_is_selected(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('Path("scripts/fixtures/owned_python_health_app.py").read_bytes()', source)
        self.assertIn('"requirements.txt": "# first-party Python stdlib only\\n"', source)
        self.assertNotIn('github.event.inputs', source)
        self.assertNotIn('pull_request.head.repo', source)


    def test_owned_fixture_sigterm_handler_and_clean_exit_are_required(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        fixture = FIXTURE.read_text(encoding="utf-8")
        for marker in (
            "signal.signal(signal.SIGTERM, _stop_on_sigterm)",
            "raise SystemExit(0)",
            "finally:\\n        server.server_close()",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker.replace("\\n", "\n"), fixture)
        stop = source.index('podman --remote=false stop -t 3 "$container"')
        clean_exit = source.index(
            '[[ "$(podman --remote=false inspect --format \'{{.State.ExitCode}}\' "$container")" == "0" ]]',
            stop,
        )
        restart = source.index('podman --remote=false start "$container"', stop)
        self.assertLess(stop, clean_exit)
        self.assertLess(clean_exit, restart)
        self.assertIn("graceful_stop=pass", source)
        self.assertFalse(self.guarded(source.replace("graceful_stop=pass", "")))


if __name__ == "__main__":
    unittest.main()

    def test_private_staging_changes_trigger_real_oci_ci(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for marker in ('"src/cloudforge/demo_selected_oci_stage.py"',
                       '"tests/test_demo_selected_oci_stage.py"'):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)
                self.assertFalse(self.guarded(source.replace(marker, "")))
