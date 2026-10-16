# ABOUTME: Runs the established plugin integration modules on a fixed HTTP candidate.
# ABOUTME: Records module identities and progress with qualified synthetic native fixtures.
import json
import os
from pathlib import Path
import subprocess
import sys
import time

cache = Path('/home/outsider/.cache/lifeos-http-mcp-20261015')
source = cache / 'integration-source-1c50bbc4'
base = Path('/home/outsider/.cache/lifeos-daily-promotion-20261014')
package = Path('/home/outsider/.cache/lifeos-memory-portability-20261015/removal-workflow-packages/0.6.0-c86b5887')
native = Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014/candidate-fixture-04efe633/account/.hermes/.lifeos-releases/6118299dea37462094bcb7d411effb73/reference-home/.claude')
historical = base / 'historical-fixture-040/account/.hermes/.lifeos-releases/98ecab3f82ed4689a59a965a04ba7b2c'
python = base / 'frozen-test-environment/bin/python'
previous = json.loads(Path('/home/outsider/.cache/lifeos-memory-portability-20261015/archive-integration-c86b5887-launch.txt').read_bytes())
names = list(dict.fromkeys(previous['command'][6:] + [
    'test_memory_remote', 'test_memory_remote_host', 'test_memory_remote_dashboard',
    'test_memory_oauth_security', 'test_memory_mcp', 'test_memory_dashboard', 'test_sharing_component']))
environment = dict(os.environ, TZ='UTC', PYTHONDONTWRITEBYTECODE='1',
    PATH='/home/outsider/.cache/lifeos-pulse-editor-20261014/tool-bin' + os.pathsep + os.environ['PATH'],
    PYTHONPATH=os.pathsep.join(map(str, (source / 'tests', source, package / 'hermes'))),
    LIFEOS_HERMES_SOURCE=str(package / 'hermes'), LIFEOS_MEMORY_SOURCE=str(native),
    LIFEOS_TASK_HOOK_PATH=str(native / 'hooks/TaskGovernance.hook.ts'), LIFEOS_FRESH_SOURCE=str(package / 'lifeos'),
    LIFEOS_TAB_STATE_SOURCE=str(native), LIFEOS_LATEST_HERMES_SOURCE=str(base / 'upstream-hermes'),
    LIFEOS_TEST_PYTHON=str(python), LIFEOS_HARVEST_CONTROL_SOURCE=str(base / 'control-lifeos-install'),
    LIFEOS_HERMES_REBUILD_SOURCE=str(package / 'hermes'), LIFEOS_MANAGED_FRESH_OPERATION=str(historical),
    LIFEOS_MANAGED_REFERENCE=str(native),
    LIFEOS_MANAGED_TEMPLATE_ORIGINALS=str(native.parent.parent / 'fresh-templates/template-originals'),
    LIFEOS_QUALIFICATION_BUILD='/home/outsider/.cache/lifeos-memory-portability-20261015/archive-integration-prg8x318/build.json',
    PYTHON=str(python))
if '--worker' in sys.argv:
    import unittest
    os.chdir(source)
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    def flatten(tests):
        for test in tests:
            if isinstance(test, unittest.TestSuite):
                yield from flatten(test)
            else:
                yield test
    identities = [test.id() for test in flatten(suite)]
    assert all(identity.split('.')[0] in names for identity in identities), 'Foreign native test namespace collected'
    (cache / 'explicit-integration-identities.json').write_text(json.dumps(identities, indent=2) + '\n')
    class Result(unittest.TextTestResult):
        def stopTest(self, test):
            super().stopTest(test)
            (cache / 'explicit-integration-progress.json').write_text(json.dumps({
                'tests_run': self.testsRun, 'last_test': test.id(), 'failures': len(self.failures),
                'errors': len(self.errors), 'skips': len(self.skipped), 'total_tests': len(identities),
                'elapsed_seconds': time.monotonic() - started}, indent=2) + '\n')
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    receipt = {'status': 'PASS' if result.wasSuccessful() else 'FAIL', 'commit': '1c50bbc4f03dee337b432225a042c85b01df32f7',
        'immutable_test_worktree': True, 'test_modules': len(names), 'tests_run': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped),
        'elapsed_seconds': time.monotonic() - started, 'production_qualified': False, 'daily_changed': False,
        'native_fixture': 'Qualified 0.6.0 public program reference with unchanged 10 Hermes and 25 LifeOS patches',
        'archive_recovery_fixture': 'Qualified 0.6.0 archive; no 0.7.0 archive or installed release is claimed',
        'command_modules': names}
    (cache / 'explicit-integration.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (cache / 'explicit-integration.done').write_text('0\n' if result.wasSuccessful() else '1\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
with (cache / 'explicit-integration.stdout').open('w') as stdout, (cache / 'explicit-integration.stderr').open('w') as stderr:
    result = subprocess.run([str(python), '-W', 'error::ResourceWarning', __file__, '--worker'],
        cwd=source, env=environment, stdout=stdout, stderr=stderr, timeout=7200)
raise SystemExit(result.returncode)
