# ABOUTME: Tests the exact editor archive with an isolated prepared native installation.
# ABOUTME: Records source identities and actual test outcomes without selecting deployed programs.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

folder = Path(__file__).resolve().parent
repo = folder.parents[2]
sys.path.insert(0, str(repo / 'docs/verification/2026-10-13-release-ui-install'))
from qualification_artifacts import archive_files, package_matches, file_map_digest
from optional.lifeos_release_manager.release_catalog import extract_package

build = json.loads(Path(os.environ['LIFEOS_QUALIFICATION_BUILD']).read_bytes())
fixture = Path(os.environ['LIFEOS_EDITOR_FIXTURE'])
prepared = json.loads((fixture / 'fresh-preparation.json').read_bytes())
assert prepared['status'] == 'PASS'
job = Path(prepared['job'])
archive = Path(build['archive'])
assert hashlib.sha256(archive.read_bytes()).hexdigest() == build['archive_sha256']
assert archive.stat().st_size == build['archive_bytes']
cache = Path('/home/outsider/.cache/lifeos-pulse-editor-20261014')
workspace = Path(tempfile.mkdtemp(prefix='integration-', dir=cache))
package = workspace / 'package'
expected = archive_files(archive)
extract_package(archive, package)
package_matches(package, expected)
bound_build = workspace / 'build.json'
bound_build.write_text(json.dumps(dict(build, package=str(package))))
previous = json.loads((repo / 'docs/verification/2026-10-14-release-0.4.3/integration-archive-bound-a1abb579.json').read_bytes())
names = list(dict.fromkeys(previous['command'][6:] + ['test_memory_core_editor', 'test_memory_telos_editor',
    'test_memory_pulse_auth', 'test_mount_transaction', 'test_memory_remount_relay', 'test_update_transaction',
    'test_memory_mounted_soul']))
python = '/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python'
native = job / 'reference-home/.claude'
assert (native / 'LIFEOS/PULSE/modules/hermes.ts').is_file()
env = dict(os.environ, TZ='UTC', PYTHONDONTWRITEBYTECODE='1',
    PATH=str(cache / 'tool-bin') + os.pathsep + os.environ['PATH'],
    PYTHONPATH=str(package) + ':' + str(package / 'tests') + ':' + str(package / 'hermes'),
    LIFEOS_HERMES_SOURCE=str(package / 'hermes'), LIFEOS_MEMORY_SOURCE=str(native),
    LIFEOS_TASK_HOOK_PATH=str(native / 'hooks/TaskGovernance.hook.ts'), LIFEOS_FRESH_SOURCE=str(package / 'lifeos'),
    LIFEOS_TAB_STATE_SOURCE=str(native), LIFEOS_LATEST_HERMES_SOURCE='/home/outsider/.cache/lifeos-daily-promotion-20261014/upstream-hermes',
    LIFEOS_TEST_PYTHON=python, LIFEOS_HARVEST_CONTROL_SOURCE='/home/outsider/.cache/lifeos-daily-promotion-20261014/control-lifeos-install',
    LIFEOS_HERMES_REBUILD_SOURCE='/home/outsider/.cache/lifeos-hermes-managed-20261012/regeneration-whitespace',
    LIFEOS_MANAGED_FRESH_OPERATION=str(job), LIFEOS_MANAGED_REFERENCE=str(native),
    LIFEOS_MANAGED_TEMPLATE_ORIGINALS=str(job / 'fresh-templates/template-originals'),
    LIFEOS_QUALIFICATION_BUILD=str(bound_build))
command = [python, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', *names]
start = time.monotonic()
code = 1
try:
    with (folder / 'candidate-integration.stdout').open('w') as stdout, (folder / 'candidate-integration.stderr').open('w') as stderr:
        result = subprocess.run(command, cwd=package, env=env, stdout=stdout, stderr=stderr, timeout=7200)
    generated = package_matches(package, expected, allow_generated=True)
    code = result.returncode
    report = {'package_commit': build['head'], 'archive_sha256': build['archive_sha256'],
        'archive_bytes': build['archive_bytes'], 'archive_file_map_sha256': file_map_digest(expected),
        'archive_regular_files': len(expected), 'archive_files_match_before': True, 'archive_files_match_after': True,
        'generated_test_files': generated, 'tested_package': str(package), 'command': command,
        'exit_code': code, 'elapsed_seconds': time.monotonic() - start, 'live_selection_changed': False}
    (folder / 'candidate-integration.json').write_text(json.dumps(report, indent=2) + '\n')
finally:
    (folder / 'candidate-integration.done').write_text(str(code) + '\n')
