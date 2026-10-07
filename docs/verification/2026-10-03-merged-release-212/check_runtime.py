# ABOUTME: Loads the candidate plugin through the actual Hermes manager and middleware API.
# ABOUTME: Checks dependency versions and confirms registration preserves profile and SSH state.
import hashlib
import importlib.metadata
import json
import os
import site
import sys
from pathlib import Path

active_host, tested_host, plugin_root = map(Path, sys.argv[1:])
profile = Path(os.environ['HERMES_HOME'])
key = hashlib.sha256(str(active_host.resolve()).encode()).hexdigest()[:16]
facts = json.loads((profile / 'installs' / key / 'facts.json').read_text())
environment = Path(facts['packages']['venv']['environment'])
sites = list((environment / 'lib').glob('python*/site-packages'))
assert len(sites) == 1
site.addsitedir(str(sites[0]))
sys.path.insert(0, str(tested_host))
from hermes_cli.plugins import PluginManager, parse_manifest_file
from hermes_cli.middleware import REQUIRED_MIDDLEWARE_API_VERSION
from packaging.requirements import Requirement

paths = [profile / 'config.yaml', profile / '.env', profile / 'lifeos-memory.json',
         Path.home() / '.ssh/authorized_keys']
snapshot = lambda: {str(path): hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None for path in paths}
before = snapshot()
assert REQUIRED_MIDDLEWARE_API_VERSION == 1
manifest = parse_manifest_file(plugin_root / 'plugin.yaml', plugin_root, 'user', '')
manager = PluginManager(scope_key=str(profile))
manager._load_plugin(manifest)
loaded = manager._plugins['lifeos-hook-bridge']
assert loaded.enabled and not loaded.error, loaded.error
required = {}
for kind in ['llm_execution', 'llm_admission']:
    callbacks = manager._middleware.get(kind, [])
    required[kind] = any(getattr(callback, '_hermes_required_middleware', False) for callback in callbacks)
assert all(required.values()), required
expected = {'pre_tool_call', 'post_tool_call', 'pre_prompt_admission', 'pre_command_approval',
            'augment_tool_result', 'pre_turn_stop', 'on_session_finalize', 'api_request_error', 'on_turn_result'}
assert expected <= set(loaded.hooks_registered), loaded.hooks_registered
dependencies = {}
for spec in manifest.python_dependencies:
    requirement = Requirement(spec)
    version = importlib.metadata.version(requirement.name)
    assert version in requirement.specifier, (requirement.name, version)
    dependencies[requirement.name] = version
assert snapshot() == before, 'Registration changes existing state'
print(json.dumps({'loaded': True, 'required_middleware': required, 'hooks': sorted(expected),
                  'dependencies': dependencies, 'profile_and_ssh_state_unchanged': True}))
for registration in reversed(manager._registration_order):
    registration.dispose()
