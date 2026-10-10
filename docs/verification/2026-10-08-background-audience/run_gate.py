# ABOUTME: Runs current Discord audience controls with existing native learning and Wisdom regressions.
# ABOUTME: Saves a durable result marker for release verification.
from pathlib import Path
import sys
import unittest

root=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(root),str(root/'tests')]
modules=('test_memory_background_audience','test_discord_audience','test_memory_hypotheses',
         'test_memory_recurrence','test_memory_learning_ratings','test_memory_wisdom_readers',
         'test_memory_wisdom_frame')
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in modules)
result=unittest.TextTestRunner(verbosity=2).run(suite)
code=0 if result.wasSuccessful() and not result.skipped else 1
Path(__file__).with_name('focused.done').write_text(str(code)+'\n')
sys.exit(code)
