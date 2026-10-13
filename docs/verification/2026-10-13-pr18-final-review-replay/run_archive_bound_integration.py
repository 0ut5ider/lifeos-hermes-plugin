# ABOUTME: Runs the complete integration controls from the sealed managed-release package.
# ABOUTME: Records measured failures without selecting either live guest or reading existing user records.
import json
import hashlib
import tempfile
import os
from pathlib import Path
import subprocess
import time
out = Path(__file__).resolve().parent
cache = Path('/home/outsider/.cache/lifeos-hermes-managed-20261012')
build = json.loads(Path(os.environ['LIFEOS_QUALIFICATION_BUILD']).read_bytes())
from qualification_artifacts import archive_files, package_matches, file_map_digest
from optional.lifeos_release_manager.release_catalog import extract_package
archive = Path(build['archive'])
assert hashlib.sha256(archive.read_bytes()).hexdigest() == build['archive_sha256']
assert archive.stat().st_size == build['archive_bytes']
expected = archive_files(archive)
workspace = Path(tempfile.mkdtemp(prefix='integration-bound-', dir='/home/outsider/.cache/lifeos-ui-install-20261013'))
package = workspace / 'package'
extract_package(archive, package)
package_matches(package, expected)
bound_build = workspace / 'build.json'
bound_build.write_text(json.dumps(dict(build, package=str(package))))
identity = build['head'][:8]
previous = json.loads((Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-11-release-0.3.0/combined-031-final.json')).read_bytes())
names = previous['command'][6:] + ['test_morning_observation', 'test_latest_hermes', 'test_release_catalog',
    'test_release_programs', 'test_release_stage', 'test_release_manager_cli', 'test_release_operation',
    'test_release_fresh', 'test_release_configuration', 'test_release_native_config', 'test_release_dashboard', 'test_config_inventory', 'test_release_preparation', 'test_release_services']
python = str(cache / 'native-test-environment/bin/python')
native = Path('/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install')
fixture = cache / 'fresh-qualification-5ad7570f-repeat/.hermes/.lifeos-releases/cbc25b64b2db479384788eeb5827a6be'
env = dict(os.environ, TZ='UTC', PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(package)+':'+str(package/'tests')+':'+str(package/'hermes'),
    LIFEOS_HERMES_SOURCE=str(package/'hermes'), LIFEOS_MEMORY_SOURCE=str(native),
    LIFEOS_TASK_HOOK_PATH=str(native/'hooks/TaskGovernance.hook.ts'), LIFEOS_FRESH_SOURCE=str(package/'lifeos'),
    LIFEOS_TAB_STATE_SOURCE=str(native), LIFEOS_LATEST_HERMES_SOURCE=str(cache/'upstream'),
    LIFEOS_TEST_PYTHON=python, LIFEOS_HARVEST_CONTROL_SOURCE='/home/outsider/.cache/lifeos-plugin-memory/source/LifeOS/install',
    LIFEOS_HERMES_REBUILD_SOURCE=str(cache/'regeneration-whitespace'),
    LIFEOS_MANAGED_FRESH_OPERATION=str(cache/'fresh-qualification-d4bff560-repeat/.hermes/.lifeos-releases/148fa606a5ae4eb3a436cd523b6ed8ee'),
    LIFEOS_MANAGED_REFERENCE=str(fixture/'reference-home/.claude'),
    LIFEOS_MANAGED_TEMPLATE_ORIGINALS=str(fixture/'fresh-templates/template-originals'), LIFEOS_QUALIFICATION_BUILD=str(bound_build))
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
