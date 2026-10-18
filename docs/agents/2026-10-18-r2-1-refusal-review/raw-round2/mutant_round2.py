# ABOUTME: Runs the preparation tests with the transition's launcher check or its replaced-gateway exemption mutated.
# ABOUTME: Patches module attributes in memory only; product files stay unchanged.
import sys, unittest
from optional.lifeos_release_manager import inplace_preparation as p
mode = sys.argv[1]
original = p.check_service_launchers
if mode == 'no-call':
    p.check_service_launchers = lambda home, **kw: None
elif mode == 'never-replaced':
    p.check_service_launchers = lambda home, replaced=(): original(home)
suite = unittest.defaultTestLoader.discover('tests', pattern='test_inplace_preparation.py')
result = unittest.TextTestRunner(verbosity=0).run(suite)
print(mode, 'failures', len(result.failures), 'errors', len(result.errors))
