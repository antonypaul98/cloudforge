from cloudforge.inspector import inspect_application


def test_inspects_python_manifest_without_executing_code():
    files = {
        "pyproject.toml": '[project]\ndependencies = ["redis", "postgresql"]\n',
        "app.py": 'raise RuntimeError("must never execute")',
    }
    result = inspect_application("api", files)
    assert result.profile.runtime == "python"
    assert result.profile.dependencies == ("postgresql", "redis")
    assert result.warnings == ()
    assert {(item.fact, item.value) for item in result.evidence} >= {
        ("runtime", "python"),
        ("dependency", "postgresql"),
        ("dependency", "redis"),
    }


def test_inspection_is_deterministic_across_file_order():
    a = inspect_application("api", {"requirements.txt": "redis\n", "README.md": "x"})
    b = inspect_application("api", {"README.md": "x", "requirements.txt": "redis\n"})
    assert a == b


def test_unknown_application_fails_closed_to_unknown_runtime():
    result = inspect_application("mystery", {"README.md": "no manifest"})
    assert result.profile.runtime == "unknown"
    assert result.profile.dependencies == ()
    assert result.warnings == ("runtime could not be determined from supported manifests",)


def test_dependency_names_are_token_bounded():
    result = inspect_application("api", {"requirements.txt": "redis-client-helper\npostgrest\n"})
    assert result.profile.dependencies == ()
