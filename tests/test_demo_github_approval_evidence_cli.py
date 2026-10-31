"""Offline CLI regressions: never confuse account evidence with permission."""
import json
import subprocess
import sys

import pytest

from cloudforge import demo_github_approval_evidence_cli as cli


ARGS = [
    "--repository", "antonypaul98/cloudforge",
    "--run-id", "17",
    "--head-sha", "a" * 40,
    "--artifact-sha256", "b" * 64,
    "--reviewer-account-id", "200",
]


def test_cli_success_is_still_non_authorizing(monkeypatch, capsys):
    captured = {}
    def fake_verify(**kwargs):
        captured.update(kwargs)
        return {
            "github_account_review_evidence_verified": True,
            "human_identity_verified": False,
            "execution_permitted": False,
            "application_executed": False,
        }
    monkeypatch.setattr(cli, "verify_selected_github_approval_evidence", fake_verify)
    assert cli.main(ARGS) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["github_account_review_evidence_verified"] is True
    assert receipt["execution_permitted"] is False
    assert receipt["human_identity_verified"] is False
    assert receipt["application_executed"] is False
    assert captured == {
        "repository_full_name": "antonypaul98/cloudforge",
        "run_id": 17,
        "expected_head_sha": "a" * 40,
        "expected_artifact_sha256": "b" * 64,
        "trusted_reviewer_id": 200,
    }


def test_cli_unavailable_or_unapproved_fails_closed_without_leaking(monkeypatch, capsys):
    def unavailable(**kwargs):
        raise ValueError("private API response should never appear in output")
    monkeypatch.setattr(cli, "verify_selected_github_approval_evidence", unavailable)
    assert cli.main(ARGS) == 1
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result == {
        "github_account_review_evidence_verified": False,
        "human_identity_verified": False,
        "execution_permitted": False,
        "application_executed": False,
    }
    assert "private API" not in output.out + output.err


@pytest.mark.parametrize("replacement", [
    ["--run-id", "0"], ["--run-id", "-1"],
    ["--reviewer-account-id", "0"], ["--head-sha", "c" * 39],
    ["--artifact-sha256", "d" * 63], ["--repository", "bad/path/extra"],
])
def test_invalid_pins_fail_before_network_in_real_module(replacement):
    args = ARGS.copy()
    flag, value = replacement
    args[args.index(flag) + 1] = value
    proc = subprocess.run(
        [sys.executable, "-m", "cloudforge.demo_github_approval_evidence_cli", *args],
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert proc.returncode == 1
    result = json.loads(proc.stdout)
    assert result["execution_permitted"] is False
    assert result["github_account_review_evidence_verified"] is False
    assert "Traceback" not in proc.stderr


def test_missing_required_pins_rejected_before_fetch(monkeypatch, capsys):
    monkeypatch.setattr(cli, "verify_selected_github_approval_evidence",
                        lambda **kwargs: pytest.fail("must not fetch"))
    with pytest.raises(SystemExit) as exc:
        cli.main(["--repository", "antonypaul98/cloudforge"])
    assert exc.value.code == 2
    assert "required" in capsys.readouterr().err


def test_help_is_read_only(monkeypatch, capsys):
    monkeypatch.setattr(cli, "verify_selected_github_approval_evidence",
                        lambda **kwargs: pytest.fail("must not fetch"))
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "never authorize execution" in capsys.readouterr().out
