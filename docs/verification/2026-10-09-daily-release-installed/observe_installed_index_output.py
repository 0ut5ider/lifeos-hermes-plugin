# ABOUTME: Measures the actual installed indexing output at its existing history admission boundary.
# ABOUTME: Records only sizes, result fields, and exception types without changing the filter outcome.
import importlib
import json
import os
from pathlib import Path
import sys

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
os.environ.update(HOME=str(root.parent), HERMES_HOME=str(profile),
    PATH=str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    PYTHONPATH=str(stage / 'package/hermes'), LANG='C.UTF-8', TZ='America/Toronto',
    LIFEOS_DIR=str(root / 'LIFEOS'), LIFEOS_HOOK_SETTINGS=str(root / 'settings.json'),
    LIFEOS_NOTIFICATION_CHANNEL='headless', BUN_CONFIG_NO_AUTO_INSTALL='1',
    PYTHONDONTWRITEBYTECODE='1')
sys.path[:0] = [str(profile / 'plugins'), str(stage / 'package/hermes')]
access = importlib.import_module('lifeos-hook-bridge.memory_access')
original = access.NativeMemory.filter_history
observations = []
def observed(self, scope, content, timestamp):
    row = {'characters': len(content), 'utf8_bytes': len(content.encode()),
        'history_character_limit': 65536, 'read_category_count': len(scope.read)}
    try:
        result = original(self, scope, content, timestamp)
        row.update(result_fields=sorted(result), excluded=result.get('excluded'))
        return result
    except BaseException as error:
        row['exception_type'] = type(error).__name__
        raise
    finally:
        observations.append(row)
        (stage / 'installed-index-output-boundary.json').write_text(json.dumps(observations, indent=2) + '\n')
access.NativeMemory.filter_history = observed
from ruamel.yaml import YAML
configured = YAML(typ='safe').load((profile / 'config.yaml').read_text())
model = configured['model']
settings = configured['plugins']['entries']['lifeos-hook-bridge']['settings']
route = {'provider': 'custom', 'model': model['default'], 'base_url': model['base_url'],
    'api_mode': model.get('api_mode', 'chat_completions')}
tiers = importlib.import_module('lifeos-hook-bridge.model_tiers')
mapping = tiers.configured_model_map(lambda key, default=None: settings.get(key, default),
    route['provider'], route['model'])
jobs = importlib.import_module('lifeos-hook-bridge.memory_owner_jobs')
result = jobs.OwnerJobs(profile / 'lifeos-memory.json').run('user-index', route=route, mapping=mapping)
print(json.dumps({'status': result['status'], 'job': result['job']}))
assert observations, 'The actual backend does not reach the instrumented output boundary'
