# ABOUTME: Compares managed scan output with the pinned original native scanner.
# ABOUTME: Preserves synthetic source bytes and complete output for every selected native mode.
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_interview_scan import MemoryInterviewScanTests


def main():
    test = MemoryInterviewScanTests()
    test.setUp()
    try:
        test.identity.write_text('---\ncore:\n  name: SyntheticNativeScanName\n---\n# Synthetic assistant\n')
        original = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/InterviewScan.ts'
        managed = test.root / 'LIFEOS/TOOLS/InterviewScan.ts'
        cases = []
        for args in (['--json'], [], ['--next'], ['--file', 'DA_IDENTITY'], ['--json', '--phase', '2'],
                     ['--file', 'SyntheticUnsupportedTarget']):
            outputs = []
            for module, context in ((managed, True), (original, False)):
                result = subprocess.run(['bun', '--no-install', str(module), *args],
                    env=test.fixture.fixture.environment(context=context), capture_output=True, text=True, timeout=60)
                outputs.append({'status': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
            case = {'args': args, 'actual': outputs[0], 'expected': outputs[1], 'equal': outputs[0] == outputs[1]}
            cases.append(case)
        sources = {str(path.relative_to(test.root)): path.read_text()
            for path in [test.identity, test.projects, test.env, test.pulse, test.work,
                         *list((test.root / 'LIFEOS/USER/TELOS').rglob('*.md'))]}
        record = {'original': str(original), 'managed': str(managed), 'sources': sources, 'cases': cases}
        Path(sys.argv[1]).write_text(json.dumps(record, indent=2) + '\n')
        assert all(case['equal'] for case in cases), 'The managed output differs from its pinned native control'
        print('All six scan output modes match the pinned original native implementation')
    finally:
        test.doCleanups()


if __name__ == '__main__':
    main()
