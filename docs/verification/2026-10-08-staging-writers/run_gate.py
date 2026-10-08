# ABOUTME: Runs native staging, authority, source-race, and recovery controls against the prepared candidate.
# ABOUTME: Records a durable completion marker for disconnected harness sessions.
from pathlib import Path
import sys
import unittest

root=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(root),str(root/'tests')]
modules=('test_memory_staging_writers','test_memory_staging','test_memory_native',
         'test_memory_publication_authority','test_memory_knowledge_render',
         'test_memory_publication_modes','test_memory_publication_recovery',
         'test_patch_bundle','test_hermes_install_source','test_lifeos_install_source')
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in modules)
result=unittest.TextTestRunner(verbosity=2).run(suite)
code=0 if result.wasSuccessful() and not result.skipped else 1
Path(__file__).with_name('focused.done').write_text(str(code)+'\n')
sys.exit(code)
