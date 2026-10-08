# ABOUTME: Observes actual filesystem times during repeated synthetic Work retirement checks.
# ABOUTME: Retains cutoff timestamps and outcomes without changing policy or recording source bodies.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import unittest

import lifeos_hook_bridge.memory_access as memory_access
from lifeos_hook_bridge.memory_access import NativeMemory
from test_memory_life_work import MemoryLifeWorkTests

original_now = memory_access._now
original_utime = os.utime
observations = []
cutoff = None


def observe_now():
    global cutoff
    cutoff = original_now()
    return cutoff


def observe_utime(path, *args, **options):
    result = original_utime(path, *args, **options)
    if cutoff and str(path).endswith(('work.json', 'PROJECTS.md', 'TELOS/CURRENT.md')):
        info = Path(path).stat()
        source_time = datetime.fromtimestamp(info.st_mtime_ns // 1000000000, timezone.utc).replace(microsecond=(info.st_mtime_ns // 1000) % 1000000)
        observations.append({'source': Path(path).name, 'timestamp': source_time.isoformat(),
            'retirement': cutoff, 'age_us': (source_time - datetime.fromisoformat(cutoff)).total_seconds() * 1000000})
    return result


memory_access._now = observe_now
os.utime = observe_utime
suite = unittest.TestSuite(MemoryLifeWorkTests('test_current_escaped_retired_session_cannot_return') for _ in range(40))
result = unittest.TextTestRunner(verbosity=1).run(suite)
Path(__file__).with_name('time-probe.json').write_text(json.dumps({'runs': result.testsRun,
    'failures': len(result.failures), 'errors': len(result.errors), 'observations': observations}, indent=2) + '\n')
sys.exit(0 if result.wasSuccessful() else 1)
