from .models import ApplicationProfile, InfrastructurePlan, ResourceRequirement

def derive_requirements(app: ApplicationProfile) -> InfrastructurePlan:
    resources = [ResourceRequirement('compute', f'run {app.runtime} application', {'runtime': app.runtime})]
    if app.port is not None:
        resources.append(ResourceRequirement('network', 'application exposes a service port', {'port': app.port}))
    deps = {d.lower() for d in app.dependencies}
    if deps & {'postgres', 'postgresql'}:
        resources.append(ResourceRequirement('database', 'application declares PostgreSQL dependency', {'engine': 'postgresql'}))
    if 'redis' in deps:
        resources.append(ResourceRequirement('cache', 'application declares Redis dependency', {'engine': 'redis'}))
    return InfrastructurePlan(app.name, tuple(resources), True)
