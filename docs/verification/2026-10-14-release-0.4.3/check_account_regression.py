# ABOUTME: Confirms that the account-launcher regression detects the measured native HOME defect.
# ABOUTME: Changes only the loaded test-process function and records the expected refusal.
import inspect
import json
from pathlib import Path
import unittest

from optional.lifeos_release_manager import release_plan
from test_release_accounts import ReleaseAccountTests

source = inspect.getsource(release_plan.inspect_operation)
predicate = 'not executable.is_relative_to(home)'
assert source.count(predicate) == 1
namespace = release_plan.__dict__
exec(compile(source.replace(predicate, 'not executable.is_relative_to(Path.home())'),
             '<native-home-defect-mutation>', 'exec'), namespace)
release_plan.inspect_operation = namespace['inspect_operation']
suite = unittest.TestSuite([ReleaseAccountTests(
    'test_installed_inspector_accepts_the_account_launcher_under_native_home')])
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun == 1 and len(result.errors) == 1 and not result.failures
assert 'ReleaseRejected: The bound service launcher is not a regular account program' in result.errors[0][1]
Path(__file__).with_suffix('.json').write_text(json.dumps({
    'mutation': 'Restore the native HOME launcher predicate in the test process',
    'tests_run': result.testsRun, 'expected_errors': len(result.errors),
    'regression_detects_original_defect': True, 'product_files_changed': False}, indent=2) + '\n')
