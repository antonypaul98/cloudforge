"""Static safety gates for the disposable selected-source Python OCI fixture."""
from pathlib import Path
import hashlib
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/selected-python-oci-fixture.yml"
FIXTURE = ROOT / "scripts/fixtures/owned_python_health_app.py"
ALT_FIXTURE = ROOT / "scripts/fixtures/owned_python_health_alt_app.py"
PINNED_ALT_SOURCE_SHA256 = "2c5424193e2d9b76aa9cc241462a37bb8df024525539983e12b49f0bc5bc8f1d"
PINNED_SOURCE_SHA256 = "071b232d0bbf04c2a46bf7538120efc5214f76d7f8dfb921c0d5627c295eed39"


class SelectedPythonOCIWorkflowTests(unittest.TestCase):
    @staticmethod
    def guarded(source: str) -> bool:
        required = (
            "permissions:\n  contents: read", "runs-on: ubuntu-latest",
            "fail-fast: false", "variant: primary", "variant: alternate",
            "CF_OWNED_VARIANT: ${{ matrix.fixture.variant }}",
            "EXPECTED_HEALTH_BODY: ${{ matrix.fixture.health }}",
            "unapproved first-party fixture variant",
            "owned_python_health_alt_app.py",
            "2c5424193e2d9b76aa9cc241462a37bb8df024525539983e12b49f0bc5bc8f1d",
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
            'container_id="$(podman --remote=false run -d',
            '[[ "$container_id" =~ ^[0-9a-f]{64}$ ]]',
            'inspected_id="$(podman --remote=false container inspect --format \'{{.Id}}\' "$container")" || return 1',
            '[[ "$inspected_id" == "$container_id" ]] || return 1',
            'inspected_image="$(podman --remote=false container inspect --format \'{{.Image}}\' "$container")" || return 1',
            '[[ "${inspected_image#sha256:}" == "${image_id#sha256:}" ]] || return 1',
            '[[ "$(podman --remote=false container inspect --format \'{{.State.Running}}\' "$container")" == "true" ]] || return 1',
            'post_state="$(podman --remote=false container inspect --format \'{{.Id}} {{.Image}} {{.State.Running}}\' "$container")" || return 1',
            'read -r post_id post_image post_running <<< "$post_state"',
            '[[ "$post_id" == "$container_id" ]] || return 1',
            '[[ "${post_image#sha256:}" == "${image_id#sha256:}" ]] || return 1',
            '[[ "$post_running" == "true" ]] || return 1',
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



    def test_private_staging_changes_trigger_real_oci_ci(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for marker in ('"src/cloudforge/demo_selected_oci_stage.py"',
                       '"tests/test_demo_selected_oci_stage.py"'):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)
                self.assertFalse(self.guarded(source.replace(marker, "")))


    def test_health_observation_is_bound_to_running_container_identity_and_image(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        health = source.split("          check_health() {", 1)[1].split("          }", 1)[0]
        for marker in (
            'inspected_id="$(podman --remote=false container inspect --format \'{{.Id}}\' "$container")" || return 1',
            '[[ "$inspected_id" == "$container_id" ]] || return 1',
            'inspected_image="$(podman --remote=false container inspect --format \'{{.Image}}\' "$container")" || return 1',
            '[[ "${inspected_image#sha256:}" == "${image_id#sha256:}" ]] || return 1',
            '[[ "$(podman --remote=false container inspect --format \'{{.State.Running}}\' "$container")" == "true" ]] || return 1',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, health)
                self.assertFalse(self.guarded(source.replace(marker, "", 1)))
        self.assertLess(health.index("inspected_id="), health.index("if actual="))
        self.assertLess(health.index("inspected_image="), health.index("if actual="))
        self.assertLess(health.index("State.Running"), health.index("if actual="))
        self.assertIn('container_id="$(podman --remote=false run -d', source)
        self.assertIn('[[ "$container_id" =~ ^[0-9a-f]{64}$ ]]', source)



    def test_health_response_rechecks_identity_after_probe(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        health = source.split("          check_health() {", 1)[1].split("          }", 1)[0]
        post = 'post_state="$(podman --remote=false container inspect --format \'{{.Id}} {{.Image}} {{.State.Running}}\' "$container")" || return 1'
        self.assertLess(health.index("if actual="), health.index(post))
        self.assertLess(health.index(post), health.index("return 0"))
        for marker in (
            post,
            'read -r post_id post_image post_running <<< "$post_state"',
            '[[ "$post_id" == "$container_id" ]] || return 1',
            '[[ "${post_image#sha256:}" == "${image_id#sha256:}" ]] || return 1',
            '[[ "$post_running" == "true" ]] || return 1',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, health)
                self.assertFalse(self.guarded(source.replace(marker, "", 1)))



    def test_second_first_party_fixture_is_pinned_and_distinguishable(self):
        self.assertEqual(hashlib.sha256(ALT_FIXTURE.read_bytes()).hexdigest(),
                         PINNED_ALT_SOURCE_SHA256)
        self.assertNotEqual(PINNED_ALT_SOURCE_SHA256, PINNED_SOURCE_SHA256)
        self.assertIn(b"cloudforge-owned-python-alt-ok", ALT_FIXTURE.read_bytes())
        self.assertNotIn(b"cloudforge-owned-python-alt-ok", FIXTURE.read_bytes())

    def test_bounded_source_selection_precedes_package_and_health(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(source.count("          - variant:"), 2)
        self.assertLess(source.index('if variant == "primary":'),
                        source.index('package_selected_source('))
        self.assertLess(source.index('elif variant == "alternate":'),
                        source.index('package_selected_source('))
        self.assertLess(source.index('raise SystemExit("unapproved first-party fixture variant")'),
                        source.index('package_selected_source('))
        self.assertIn('[[ "$actual" == "$EXPECTED_HEALTH_BODY" ]]', source)
        self.assertNotIn('github.event.inputs', source)
        for marker in (
            'elif variant == "alternate":',
            'raise SystemExit("unapproved first-party fixture variant")',
            '[[ "$actual" == "$EXPECTED_HEALTH_BODY" ]]',
            "CF_OWNED_VARIANT: ${{ matrix.fixture.variant }}",
        ):
            with self.subTest(marker=marker):
                self.assertFalse(self.guarded(source.replace(marker, "")))


if __name__ == "__main__":
    unittest.main()
