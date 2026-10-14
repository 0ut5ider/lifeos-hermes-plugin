# ABOUTME: Runs the complete integration controls from the sealed managed-release package.
# ABOUTME: Records measured failures without selecting either live guest or reading existing user records.
import json
import hashlib
import tempfile
import os
import shutil
from pathlib import Path
import subprocess
import time
out = Path(__file__).resolve().parent
cache = Path('/home/outsider/.cache/lifeos-daily-promotion-20261014')
build = json.loads(Path(os.environ['LIFEOS_QUALIFICATION_BUILD']).read_bytes())
from qualification_artifacts import archive_files, package_matches, file_map_digest
from optional.lifeos_release_manager.release_catalog import extract_package
archive = Path(build['archive'])
assert hashlib.sha256(archive.read_bytes()).hexdigest() == build['archive_sha256']
assert archive.stat().st_size == build['archive_bytes']
expected = archive_files(archive)
workspace = Path(tempfile.mkdtemp(prefix='integration-bound-', dir=str(cache / 'integration-workspaces')))
package = workspace / 'package'
extract_package(archive, package)
package_matches(package, expected)
bound_build = workspace / 'build.json'
test_archive = workspace / archive.name
shutil.copy2(archive, test_archive)
assert hashlib.sha256(test_archive.read_bytes()).hexdigest() == build['archive_sha256']
bound_build.write_text(json.dumps(dict(build, package=str(package), archive=str(test_archive))))
identity = build['head'][:8]
previous = json.loads((Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-11-release-0.3.0/combined-031-final.json')).read_bytes())
names = previous['command'][6:] + ['test_morning_observation', 'test_latest_hermes', 'test_release_catalog',
    'test_release_programs', 'test_release_stage', 'test_release_manager_cli', 'test_release_operation',
    'test_release_fresh', 'test_release_configuration', 'test_release_native_config', 'test_release_dashboard', 'test_config_inventory', 'test_release_preparation', 'test_release_services', 'test_release_accounts']
python = str(cache / 'frozen-test-environment/bin/python')
native = cache / 'local-fixture-repeat/account/.hermes/.lifeos-releases/577a8a31d59e49c19d522ed3444e1b31/reference-home/.claude'
historical = json.loads((cache / 'historical-fixture-040/fresh-preparation.json').read_bytes())
assert historical['status'] == 'PASS'
historical_job = Path(historical['job'])
env = dict(os.environ, PYTHON=python, PATH=str(cache/'local-fixture-repeat/account/.hermes/.lifeos-releases/577a8a31d59e49c19d522ed3444e1b31/tools') + os.pathsep + os.environ.get('PATH',os.defpath), TZ='UTC', PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(package)+':'+str(package/'tests')+':'+str(package/'hermes'),
    LIFEOS_HERMES_SOURCE=str(package/'hermes'), LIFEOS_MEMORY_SOURCE=str(native),
    LIFEOS_TASK_HOOK_PATH=str(native/'hooks/TaskGovernance.hook.ts'), LIFEOS_FRESH_SOURCE=str(package/'lifeos'),
    LIFEOS_TAB_STATE_SOURCE=str(native), LIFEOS_LATEST_HERMES_SOURCE=str(cache/'upstream-hermes'),
    LIFEOS_TEST_PYTHON=python, LIFEOS_HARVEST_CONTROL_SOURCE=str(cache/'control-lifeos-install'),
    LIFEOS_HERMES_REBUILD_SOURCE=str(package/'hermes'),
    LIFEOS_MANAGED_FRESH_OPERATION=str(historical_job),
    LIFEOS_MANAGED_REFERENCE=str(native),
    LIFEOS_MANAGED_TEMPLATE_ORIGINALS=str(cache/'local-fixture-repeat/initialization-controls/fresh-templates/template-originals'), LIFEOS_QUALIFICATION_BUILD=str(bound_build))
command = [python, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', *names]
start = time.monotonic()
try:
    with (out/('integration-archive-bound-'+identity+'.stdout')).open('w') as stdout, (out/('integration-archive-bound-'+identity+'.stderr')).open('w') as stderr:
        result = subprocess.run(command, cwd=package, env=env, stdout=stdout, stderr=stderr, timeout=7200)
    generated = package_matches(package, expected, allow_generated=True)
    report = {'package_commit': build['head'], 'archive_sha256': build['archive_sha256'],
              'archive_bytes': build['archive_bytes'], 'archive_file_map_sha256': file_map_digest(expected),
              'archive_regular_files': len(expected), 'archive_files_match_before': True,
              'archive_files_match_after': True, 'generated_test_files': generated,
              'tested_package': str(package), 'command':command,
              'exit_code': result.returncode, 'elapsed_seconds': time.monotonic()-start, 'live_selection_changed':False}
    (out/('integration-archive-bound-'+identity+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    (out/('integration-archive-bound-'+identity+'.done')).write_text(str(result.returncode)+'\n')
except BaseException:
    (out/('integration-archive-bound-'+identity+'.done')).write_text('1\n')
    raise
