# ABOUTME: Compares managed evidence with the pinned original native implementation.
# ABOUTME: Records complete synthetic inputs and native outputs at the same calculation date.
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_state_evidence import MemoryStateEvidenceTests


def main():
    test = MemoryStateEvidenceTests()
    test.setUp()
    try:
        original = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/StateEvidence.ts'
        managed = test.root / 'LIFEOS/TOOLS/StateEvidence.ts'
        now = test.day + 'T12:00:00Z'
        program = 'const m=await import(process.argv[1]);console.log(JSON.stringify(m.gatherEvidence(new Date(process.argv[2]))));'
        current = subprocess.run(['bun', '--no-install', '-e', program, str(managed), now],
            env=test.fixture.environment(), capture_output=True, text=True, timeout=30)
        native = subprocess.run(['bun', '--no-install', '-e', program, str(original), now],
            env=test.fixture.environment(context=False), capture_output=True, text=True, timeout=30)
        if current.returncode or native.returncode:
            raise RuntimeError(current.stderr + native.stderr)
        actual, expected = json.loads(current.stdout), json.loads(native.stdout)
        sources = {str(path.relative_to(test.root)): path.read_text()
            for directory in ['LIFEOS/USER/HEALTH', 'LIFEOS/USER/CONDUIT', 'LIFEOS/USER/FINANCES']
            for path in (test.root / directory).rglob('*.json')}
        sources['LIFEOS/MEMORY/STATE/work.json'] = test.work.read_text()
        record = {'original_source': str(original), 'managed_source': str(managed), 'now': now,
                  'sources': sources, 'actual': actual, 'expected': expected, 'equal': actual == expected}
        Path(sys.argv[1]).write_text(json.dumps(record, indent=2) + '\n')
        assert actual == expected, 'The managed payload differs from the pinned native implementation'
        print('All four domain payloads match the pinned original native implementation')
    finally:
        test.doCleanups()


if __name__ == '__main__':
    main()
