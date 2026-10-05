# ABOUTME: Experiment 5 for the PR 3 follow-up review: error paths that escape the new code.
# ABOUTME: Covers an unreadable component during status() and enabled() raising during provider registration.
import os
from pathlib import Path
import shutil
import sys
import types

sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/pr3review/src')
base = Path('/tmp/pr3review/exp5')
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True, mode=0o700)

# 5a: unreadable but otherwise valid component file: status() raises instead of reporting unavailable.
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
component = base / 'profile/lifeos-memory-sharing'
component.mkdir(parents=True, mode=0o700)
shutil.copyfile('/tmp/pr3review/src/optional/lifeos-memory-sharing/memory_sharing.py', component / 'memory_sharing.py')
os.chmod(component / 'memory_sharing.py', 0o200)
preferences = MemoryPreferences(base / 'profile/lifeos-memory.json', base / 'root', Path(sys.executable), base / 'prog')
try:
    preferences.status()
    print('5a status() returned normally')
except Exception as error:
    print('5a status() raised', type(error).__name__, '-', error,
          '(plugin_api maps PermissionError to 403 "no installation owner binding")')

# 5b: register_provider on a host with middleware version 2 and a config that load() rejects.
for name in ('agent', 'agent.memory_provider', 'hermes_constants', 'hermes_cli', 'hermes_cli.middleware'):
    sys.modules[name] = types.ModuleType(name)
sys.modules['agent'].__path__ = []; sys.modules['hermes_cli'].__path__ = []
sys.modules['agent.memory_provider'].MemoryProvider = object
profile = base / 'hermes'
profile.mkdir(mode=0o700)
sys.modules['hermes_constants'].get_hermes_home = lambda: profile
sys.modules['hermes_cli.middleware'].REQUIRED_MIDDLEWARE_API_VERSION = 2
from lifeos_hook_bridge import memory_provider


class Context:
    def register_memory_provider(self, provider): self.provider = provider
    def register_middleware(self, *a, **k): pass


config = profile / 'lifeos-memory.json'
for label, content, mode in (('absent', None, None),
                             ('valid, ownership disabled', '{"version":1,"root":"/x","principal":"p","ownership_enabled":false}', 0o600),
                             ('group-readable 0644, ownership disabled', '{"version":1,"root":"/x","principal":"p","ownership_enabled":false}', 0o644),
                             ('truncated JSON', '{"version":', 0o600)):
    config.unlink(missing_ok=True)
    if content is not None:
        config.write_text(content); os.chmod(config, mode)
    try:
        memory_provider.register_provider(Context())
        print(f'5b [{label}] register_provider returned')
    except Exception as error:
        print(f'5b [{label}] register_provider raised {type(error).__name__}: {error}')
