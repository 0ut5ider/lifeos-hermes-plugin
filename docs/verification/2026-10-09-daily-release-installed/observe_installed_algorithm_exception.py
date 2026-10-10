# ABOUTME: Captures a native Algorithm exception from a diagnostic copy in the synthetic acceptance profile.
# ABOUTME: Preserves incremental caches and the selected model route while measuring the failed command.
import importlib
import json
import os
from pathlib import Path
import sys
import time

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
sys.path.insert(0, str(stage / 'package/hermes'))
sys.argv = ['hermes', 'lifeos-job', 'algorithm-summaries']
configuration = (profile / 'config.yaml').read_bytes()
cache = root / 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json'
def cache_state():
    value = json.loads(cache.read_text()) if cache.exists() else {}
    return {'cards': len(value.get('files', {})),
        'overview_present': bool(value.get('overview')),
        'mode': oct(cache.stat().st_mode & 0o777) if cache.exists() else None}
before = cache_state()
from hermes_cli.plugins import discover_plugins, get_plugin_manager
discover_plugins()
command = get_plugin_manager()._cli_commands['lifeos-job']
namespace = command['handler_fn'].__module__.rsplit('.', 1)[0]
jobs = importlib.import_module(namespace + '.memory_owner_jobs')
native = root / jobs.JOBS['algorithm-summaries'][0][0]
diagnostic = native.with_name('algorithm-tab.acceptance-observation.ts')
assert not diagnostic.exists()
source = native.read_text()
old = 'catch { console.error("Algorithm summaries unavailable"); process.exitCode = 2; }'
new = 'catch (error) { console.error(error instanceof Error ? error.stack : String(error)); process.exitCode = 2; }'
assert source.count(old) == 1
diagnostic.write_text(source.replace(old, new))
jobs.JOBS['algorithm-summaries'] = ((str(diagnostic.relative_to(root)), '--build-summaries'),)
original = jobs._command
observations = []
def measured(arguments, environment, timeout, *, merge_errors=False):
    started = time.monotonic()
    result, output = original(arguments, environment, timeout, merge_errors=True)
    (stage / 'installed-algorithm-native-exception-observed.txt').write_text(output)
    observations.append({'exit_code': result, 'elapsed_seconds': round(time.monotonic() - started, 3),
        'timeout_seconds': timeout, 'output_bytes': len(output.encode())})
    return result, output
jobs._command = measured
from hermes_cli import main
try:
    main.main()
finally:
    diagnostic.unlink()
    assert native.read_text() == source
    report = {'native_source_unchanged': True, 'diagnostic_copy_removed': True, 'before': before, 'after': cache_state(), 'commands': observations,
        'configuration_unchanged': (profile / 'config.yaml').read_bytes() == configuration,
        'synthetic_acceptance_profile_only': True, 'live_profile_changed': False}
    (stage / 'installed-algorithm-job-exception-observation.json').write_text(json.dumps(report, indent=2) + '\n')
    assert observations, 'The actual CLI does not reach the instrumented command'
    assert report['configuration_unchanged']
