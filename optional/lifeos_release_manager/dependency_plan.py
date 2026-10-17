# ABOUTME: Resolves and synchronizes the bridge's Python dependencies through Hermes's own environment manager.
# ABOUTME: Runs under the host interpreter; preparation locks a throwaway workspace and installs nothing.
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib


BRIDGE = 'lifeos-hook-bridge'
WORKSPACE_SOURCES = ('editable', 'virtual', 'directory')


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def locked_packages(lock):
    """Return ``{name: [versions]}`` for the registry packages of a uv lock, excluding workspace members."""
    data = tomllib.loads(Path(lock).read_text(encoding='utf-8'))
    packages = {}
    for package in data.get('package', []):
        source = package.get('source', {})
        if any(kind in source for kind in WORKSPACE_SOURCES):
            continue
        packages.setdefault(package['name'], set()).add(package.get('version'))
    return {name: sorted(versions) for name, versions in sorted(packages.items())}


def compare(before, after):
    """Return the packages a new lock changes or removes, and the packages it adds."""
    changed = {name: {'before': versions, 'after': after.get(name)} for name, versions in before.items()
               if after.get(name) != versions}
    added = {name: versions for name, versions in after.items() if name not in before}
    return {'changed': changed, 'added': added}


def selected_lock(source):
    """Return the resolved lock of the environment Hermes selected, or the project lock before the first sync."""
    from pm.environments import runtime_facts_path
    from pm.lock import Facts
    fact = Facts(runtime_facts_path(source)).get('venv') or {}
    lock = fact.get('resolved_lock')
    return Path(lock) if lock else Path(source) / 'uv.lock'


def resolve(source, profile, bridge, workspace):
    """Lock the enabled plugin members plus ``bridge`` in ``workspace`` against the selected lock."""
    from pm.environment import managed_environment
    from pm.native_build import source_build_environment
    from pm.workspace import _generate_pyproject, enabled_member_dirs
    source, profile, bridge, workspace = map(Path, (source, profile, bridge, workspace))
    seed = selected_lock(source)
    members = {Path(path): Path(path) for path in enabled_member_dirs()}
    members[profile / 'plugins' / BRIDGE] = bridge
    _generate_pyproject(members, workspace, source=source)
    (workspace / 'uv.lock').write_bytes(seed.read_bytes())
    environment = managed_environment(workspace / 'venv', env=source_build_environment(source), explicit=True,
                                      output=sys.stderr)
    environment.lock(workspace)
    return {'seed': str(seed), 'seed_sha256': _digest(seed), 'lock_sha256': _digest(workspace / 'uv.lock'),
            **compare(locked_packages(seed), locked_packages(workspace / 'uv.lock'))}


def synchronize(source):
    """Commit a generation for the plugin members that the current configuration enables, without eviction."""
    import pm.client
    pm.client.sync_venv(explicit=True, project_root=Path(source))
    return {'lock_sha256': _digest(selected_lock(Path(source)))}


def main(arguments):
    action = arguments[0]
    if action == 'resolve':
        value = resolve(*arguments[1:5])
        output = Path(arguments[5])
    elif action == 'synchronize':
        value = synchronize(arguments[1])
        output = Path(arguments[2])
    else:
        raise SystemExit('Choose resolve or synchronize')
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)


if __name__ == '__main__':
    main(sys.argv[1:])
