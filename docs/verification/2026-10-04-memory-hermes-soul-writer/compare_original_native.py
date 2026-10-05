# ABOUTME: Compares governed soul and context bytes with the pinned original publisher.
# ABOUTME: Saves complete synthetic source snapshots and actual process results.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_hermes_soul_writer import MemoryHermesSoulWriterTests


def main():
    test = MemoryHermesSoulWriterTests()
    test.setUp()
    try:
        source = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/RenderHermesSoul.ts'
        original = test.root / 'LIFEOS/TOOLS/OriginalHermesSoul.ts'
        original.write_bytes(source.read_bytes())
        environment = test.fixture.fixture.environment(context=False)
        profile, workspace = test.home / 'original-profile', test.home / 'original-workspace'
        environment.update(HERMES_HOME=str(profile), HERMES_WORKSPACE=str(workspace))
        results = []
        for arguments in (['--stdout'], [], ['--check']):
            result = subprocess.run(['bun', '--no-install', str(original), *arguments],
                env=environment, capture_output=True, text=True, timeout=40)
            results.append({'arguments': arguments, 'status': result.returncode,
                'stdout': result.stdout, 'stderr': result.stderr})
            assert result.returncode == 0 and not result.stderr, results[-1]
        managed = test.successful('--stdout')
        test.successful()
        test.successful('--check')
        sources = {str(path.relative_to(test.root)): path.read_text() for path in
            [test.identity, test.root / 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_MEMORY.md',
             test.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md',
             test.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md',
             test.root / 'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md', test.root / 'LIFEOS/USER/PROJECTS.md']}
        equal = {'stdout': managed.stdout == results[0]['stdout'],
            'soul': test.soul.read_bytes() == (profile / 'SOUL.md').read_bytes(),
            'workspace': test.context.read_bytes() == (workspace / '.hermes.md').read_bytes()}
        record = {'original': str(source), 'original_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'sources': sources, 'original_processes': results, 'managed_stdout': managed.stdout,
            'soul': test.soul.read_text(), 'workspace': test.context.read_text(), 'equal': equal}
        Path(sys.argv[1]).write_text(json.dumps(record, indent=2) + '\n')
        assert all(equal.values()), equal
        print('Managed soul, workspace, and stdout bytes match the pinned native publisher')
    finally:
        test.doCleanups()


if __name__ == '__main__':
    main()
