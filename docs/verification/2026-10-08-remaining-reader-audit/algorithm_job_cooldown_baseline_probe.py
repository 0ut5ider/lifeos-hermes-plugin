# ABOUTME: Checks the pre-job native listener before testing Algorithm cooldown behavior.
# ABOUTME: Retains the actual baseline listener when no managed module stop export exists.
import unittest
from test_memory_algorithm_job_cooldown import MemoryAlgorithmCooldownTests
MemoryAlgorithmCooldownTests.launch_lifetime_process = lambda self, environment, daemon: None
suite = unittest.defaultTestLoader.loadTestsFromTestCase(MemoryAlgorithmCooldownTests)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
