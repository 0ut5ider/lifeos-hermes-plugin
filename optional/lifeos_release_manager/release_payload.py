# ABOUTME: Assembles qualified dependency inputs through the native Hermes sealed payload builder.
# ABOUTME: Records the actual installed feature graph and keeps launchers bound to the operation directory.
import json
from pathlib import Path


def assemble_runtime(job, source, package, web, profile):
    from pm import stage_manager_runtime
    from pm.environments import site_packages
    from pm.features import installed_extras, write_features
    from pm.lock import Facts
    from pm.packages import Venv
    from pm.registry import get_package
    from pm.store import current_target
    from scripts.build.agent import assemble
    from scripts.build.inputs import AgentInputs
    from scripts.bundles.payload import seal_pm_runtime

    job, source, package, web, profile = map(Path, (job, source, package, web, profile))
    store = job / 'dependency-profile/tools'
    facts = Facts(store / 'facts.json', strict=True)
    fact = facts.get('python')
    if fact is None:
        raise ValueError('The native package manager has no prepared Python record')
    python = get_package('python').binary(store / fact['entry'], current_target())
    if python is None or not python.resolve().is_relative_to(job):
        raise ValueError('The prepared Python interpreter leaves the operation directory')
    stage_manager_runtime(python=python, destination=job / 'pm-runtime', project=source / 'pm')
    seal_pm_runtime(job, python)
    environment = job / 'python-environment'
    features = installed_extras(source, environment, python_exe=python)
    if 'discord' not in features:
        raise ValueError('The qualified runtime lacks the Discord feature')
    write_features(features, job)
    inputs = AgentInputs(project=source / 'pyproject.toml', code=source, repo='hermes',
        placement='contained', target=current_target(), python=python,
        site_packages=site_packages(environment), environment=environment,
        tools=store, pm_runtime=job / 'pm-runtime', features=job / 'enabled-features.json',
        frontends={'web': web})
    manifest = assemble(inputs, job)
    members = {profile / 'plugins/lifeos-hook-bridge': package / 'lifeos_hook_bridge'}
    facts.record_state('venv', Venv(source).expected_stamp(features, plugin_dirs=members), features)
    if not (job / manifest['runtime']['commands']['hermes']).is_file():
        raise ValueError('Native assembly does not publish the required Hermes launcher')
    return manifest
