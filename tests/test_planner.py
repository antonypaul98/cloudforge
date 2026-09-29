from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def test_derives_compute_and_network_requirements():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    assert [resource.kind for resource in plan.resources] == ["compute", "network"]
    assert plan.resources[1].properties == {"port": 8080}
    assert plan.requires_approval is True


def test_derives_postgresql_and_redis_case_insensitively():
    plan = derive_requirements(
        ApplicationProfile("api", "python", dependencies=("PostgreSQL", "REDIS"))
    )
    kinds = [resource.kind for resource in plan.resources]
    assert kinds == ["compute", "database", "cache"]
    assert plan.resources[1].properties == {"engine": "postgresql"}
    assert plan.resources[2].properties == {"engine": "redis"}


def test_unknown_dependencies_do_not_invent_infrastructure():
    plan = derive_requirements(
        ApplicationProfile("worker", "python", dependencies=("unknown-service",))
    )
    assert [resource.kind for resource in plan.resources] == ["compute"]
