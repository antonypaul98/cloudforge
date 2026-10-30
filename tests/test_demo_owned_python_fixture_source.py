"""Owned Python fixture is an exact-byte staged package, not caller-selected execution."""
import hashlib
from pathlib import Path

from cloudforge.demo_selected_artifact import prepare_selected_artifact
from cloudforge.demo_selected_oci_stage import stage_verified_selected_source
from cloudforge.demo_source_package import package_selected_source

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/fixtures/owned_python_health_app.py"
MANIFESTS = {"requirements.txt": "# first-party Python stdlib only\n"}


def test_owned_python_fixture_package_stages_exact_source_and_cleans():
    source = SOURCE.read_bytes()
    package = package_selected_source("owned-python-health", MANIFESTS,
                                      "disposable-ci-owned-python", "app.py", source)
    review = prepare_selected_artifact("owned-python-health", MANIFESTS,
                                       "disposable-ci-owned-python", "app.py", source)
    with stage_verified_selected_source(
        package,
        expected_package_sha256=hashlib.sha256(package).hexdigest(),
        expected_review_binding_digest=review["selected_source_binding"]["digest"],
        expected_target_id="disposable-ci-owned-python",
    ) as staged:
        path = staged.directory
        assert (path / "app.py").read_bytes() == source
        assert (path / "requirements.txt").read_bytes() == MANIFESTS["requirements.txt"].encode()
        assert staged.source_sha256 == hashlib.sha256(source).hexdigest()
    assert not path.exists()


def test_owned_python_fixture_changed_source_invalidates_expected_digest():
    source = SOURCE.read_bytes()
    package = package_selected_source("owned-python-health", MANIFESTS,
                                      "disposable-ci-owned-python", "app.py", source)
    review = prepare_selected_artifact("owned-python-health", MANIFESTS,
                                       "disposable-ci-owned-python", "app.py", source)
    import pytest
    with pytest.raises(ValueError):
        with stage_verified_selected_source(
            package + b" ", expected_package_sha256=hashlib.sha256(package).hexdigest(),
            expected_review_binding_digest=review["selected_source_binding"]["digest"],
            expected_target_id="disposable-ci-owned-python",
        ):
            pass
