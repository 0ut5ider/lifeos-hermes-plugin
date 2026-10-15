# ABOUTME: Tests an exact private portability archive against qualified native fixture programs.
# ABOUTME: Records archive identities and clean integration results without selecting live software.
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

folder = Path(__file__).resolve().parent
repo = folder.parents[2]
sys.path.insert(0, str(repo))
sys.path.insert(0, str(repo / 'docs/verification/2026-10-13-release-ui-install'))
from qualification_artifacts import archive_files, file_map_digest, package_matches
from optional.lifeos_release_manager.release_catalog import extract_package

build_path = Path(sys.argv[1]).resolve()
build = json.loads(build_path.read_bytes())
archive = Path(build['archive'])
assert hashlib.sha256(archive.read_bytes()).hexdigest() == build['archive_sha256']
assert archive.stat().st_size == build['archive_bytes']
cache = Path('/home/outsider/.cache/lifeos-memory-portability-20261015')
workspace = Path(tempfile.mkdtemp(prefix='archive-integration-', dir=cache))
package = workspace / 'package'
expected = archive_files(archive)
extract_package(archive, package)
package_matches(package, expected)
base = Path('/home/outsider/.cache/lifeos-daily-promotion-20261014')
python = base / 'frozen-test-environment/bin/python'
native = Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014/candidate-fixture-04efe633/account/.hermes/.lifeos-releases/6118299dea37462094bcb7d411effb73/reference-home/.claude')
assert (native / 'LIFEOS/PULSE/modules/hermes.ts').is_file()
previous = json.loads((repo / 'docs/verification/2026-10-14-release-0.5.0/integration-04efe633.json').read_bytes())
portability = json.loads((folder / 'portability-combined-current.json').read_bytes())
names = list(dict.fromkeys(previous['command'][6:] + [name for name in portability['command'][6:] if not name.startswith('docs.')] + ['test_removal_execution_source']))
bound_build = workspace / 'build.json'
bound_build.write_text(json.dumps(dict(build, package=str(package))))
historical = base / 'historical-fixture-040/account/.hermes/.lifeos-releases/98ecab3f82ed4689a59a965a04ba7b2c'
environment = dict(os.environ, TZ='UTC', PYTHONDONTWRITEBYTECODE='1',
    PATH='/home/outsider/.cache/lifeos-pulse-editor-20261014/tool-bin' + os.pathsep + os.environ['PATH'],
    PYTHONPATH=os.pathsep.join(map(str, (package, package / 'tests', package / 'hermes'))),
    LIFEOS_HERMES_SOURCE=str(package / 'hermes'), LIFEOS_MEMORY_SOURCE=str(native),
    LIFEOS_TASK_HOOK_PATH=str(native / 'hooks/TaskGovernance.hook.ts'), LIFEOS_FRESH_SOURCE=str(package / 'lifeos'),
    LIFEOS_TAB_STATE_SOURCE=str(native), LIFEOS_LATEST_HERMES_SOURCE=str(base / 'upstream-hermes'),
    LIFEOS_TEST_PYTHON=str(python), LIFEOS_HARVEST_CONTROL_SOURCE=str(base / 'control-lifeos-install'),
    LIFEOS_HERMES_REBUILD_SOURCE=str(package / 'hermes'), LIFEOS_MANAGED_FRESH_OPERATION=str(historical),
    LIFEOS_MANAGED_REFERENCE=str(native),
    LIFEOS_MANAGED_TEMPLATE_ORIGINALS=str(native.parent.parent / 'fresh-templates/template-originals'),
    LIFEOS_QUALIFICATION_BUILD=str(bound_build), PYTHON=str(python))
label = 'archive-integration-' + build['head'][:8]
command = [str(python), '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', *names]
started = time.monotonic()
receipt = {'status': 'FAIL', 'package_commit': build['head'], 'archive_sha256': build['archive_sha256'],
    'archive_bytes': build['archive_bytes'], 'archive_regular_files': len(expected),
    'archive_file_map_sha256': file_map_digest(expected), 'archive_files_match_before': True,
    'tested_package': str(package), 'command': command, 'test_modules': len(names),
    'native_fixture': str(native), 'historical_fresh_operation': str(historical),
    'fixture_limit': 'Prepared native sources use the qualified base with the same native patches. Installed fresh release acceptance is separate.',
    'production_qualified': False, 'daily_changed': False}
try:
    with (folder / (label + '.stdout')).open('w') as stdout, (folder / (label + '.stderr')).open('w') as stderr:
        result = subprocess.run(command, cwd=package, env=environment, stdout=stdout, stderr=stderr, timeout=7200)
    diagnostics = (folder / (label + '.stderr')).read_text()
    unclean = bool(re.search(r'^(?:Exception ignored|ResourceWarning:)', diagnostics, re.MULTILINE))
    generated = package_matches(package, expected, allow_generated=True)
    receipt.update(process_exit_code=result.returncode, unhandled_diagnostics=unclean,
        exit_code=result.returncode or int(unclean), archive_files_match_after=True, generated_test_files=generated)
    if receipt['exit_code'] == 0:
        receipt['status'] = 'PASS'
except Exception as error:
    receipt.update(error_type=type(error).__name__, error=str(error), exit_code=1)
finally:
    receipt['elapsed_seconds'] = time.monotonic() - started
    (folder / (label + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    (folder / (label + '.done')).write_text(str(receipt['exit_code']) + '\n')
print(json.dumps(receipt))
raise SystemExit(receipt['exit_code'])
