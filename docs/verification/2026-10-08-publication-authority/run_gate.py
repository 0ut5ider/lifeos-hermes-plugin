# ABOUTME: Runs the native writer and permission regression against prepared release sources.
# ABOUTME: Saves the process result for recovery after a disconnected harness session.
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(root), str(root / 'tests')]
modules = ('test_memory_publication_authority', 'test_memory_native', 'test_memory_proposals',
           'test_memory_proposal_delegation', 'test_memory_delegation', 'test_memory_service',
           'test_memory_sharing', 'test_memory_runtime', 'test_memory_publication_modes',
           'test_memory_publication_recovery', 'test_memory_proposal_gc', 'test_memory_session_harvest')
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in modules)
result = unittest.TextTestRunner(verbosity=2).run(suite)
code = 0 if result.wasSuccessful() and not result.skipped else 1
Path(__file__).with_name('focused.done').write_text(str(code) + '\n')
sys.exit(code)
