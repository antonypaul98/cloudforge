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


def test_conflicting_path_aliases_are_rejected_in_either_order():
    import pytest
    items = [('requirements.txt', 'redis'), ('./requirements.txt', 'postgres')]
    for ordered in (items, items[::-1]):
        with pytest.raises(ValueError, match='conflicting normalized paths'):
            inspect_application('api', dict(ordered))


def test_comments_and_scripts_are_not_dependency_evidence():
    result = inspect_application('api', {
        'requirements.txt': '# redis\nrequests # postgres\n',
        'package.json': '{"scripts":{"start":"echo redis postgres"}}',
    })
    assert result.profile.dependencies == ()


def test_node_manifest_has_exact_source_provenance():
    result = inspect_application('api', {'package.json': '{"dependencies":{"redis":"^5"}}'})
    assert result.profile.runtime == 'node'
    assert result.profile.dependencies == ('redis',)
    assert any(e.path == 'package.json' and e.fact == 'dependency' for e in result.evidence)


def test_malformed_manifest_is_reported_without_execution():
    result = inspect_application('api', {'package.json': 'not json'})
    assert result.profile.dependencies == ()
    assert result.warnings == ('could not parse dependencies in package.json',)


def test_inspection_preserves_deployment_approval_boundary():
    from cloudforge.planner import derive_requirements
    result = inspect_application('api', {'requirements.txt': 'redis'})
    assert derive_requirements(result.profile).requires_approval is True
