# ABOUTME: Captures source and retirement times after an actual failed Work HTTP response.
# ABOUTME: Adds no instrumentation before the tested request or synthetic file timestamp changes.
from datetime import datetime
import json
from pathlib import Path
import sys
import unittest
from lifeos_hook_bridge.memory_sources import _source_time
from test_memory_life_work import MemoryLifeWorkTests

observations = []
class Probe(MemoryLifeWorkTests):
    def test_current_escaped_retired_session_cannot_return(self):
        try:
            super().test_current_escaped_retired_session_cannot_return()
        except AssertionError:
            memory = self.fixture.fixture.fixture.fixture.fixture.memory
            with memory._transaction() as connection:
                cutoff = max(row[0] for row in connection.execute("SELECT updated FROM records WHERE status IN ('forgotten','superseded')"))
            sources = []
            for relative in ('LIFEOS/MEMORY/STATE/work.json','LIFEOS/USER/PROJECTS.md','LIFEOS/USER/TELOS/CURRENT.md'):
                timestamp = _source_time((self.root / relative).stat())
                sources.append({'relative': relative, 'timestamp': timestamp, 'retirement': cutoff,
                    'age_us': (datetime.fromisoformat(timestamp)-datetime.fromisoformat(cutoff)).total_seconds()*1000000})
            observations.append(sources)
            raise

result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(Probe('test_current_escaped_retired_session_cannot_return') for _ in range(50)))
Path(__file__).with_name('failed-time-probe.json').write_text(json.dumps({'runs': result.testsRun,
    'failures': len(result.failures),'errors': len(result.errors),'failed_observations': observations},indent=2)+'\n')
sys.exit(0 if result.wasSuccessful() else 1)
