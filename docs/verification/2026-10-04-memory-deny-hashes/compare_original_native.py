# ABOUTME: Compares native hash payloads and token review with the pinned original tool.
# ABOUTME: Records synthetic sources and hashes without retaining generated salt values.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_deny_hashes import MemoryDenyHashesTests


def main():
    test = MemoryDenyHashesTests()
    test.setUp()
    try:
        original = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/DeriveDenyHashes.ts'
        managed_review = test.successful('--dry-run', '--show-tokens')
        environment = dict(os.environ, HOME=str(test.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        raw_review = subprocess.run(['bun', '--no-install', str(original), '--dry-run', '--show-tokens'],
            env=environment, capture_output=True, text=True, timeout=40)
        test.successful()
        payload = test.output.read_bytes()
        env_digest = hashlib.sha256(test.env.read_bytes()).hexdigest()
        raw_write = subprocess.run(['bun', '--no-install', str(original)], env=environment,
            capture_output=True, text=True, timeout=40)
        equal = {'review': managed_review.stdout == raw_review.stdout,
            'payload': payload == test.output.read_bytes(),
            'environment': env_digest == hashlib.sha256(test.env.read_bytes()).hexdigest()}
        record = {'source': test.identity.read_text(), 'original': str(original),
            'original_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
            'native_review': {'status': raw_review.returncode, 'stdout': raw_review.stdout, 'stderr': raw_review.stderr},
            'native_write': {'status': raw_write.returncode, 'stdout': raw_write.stdout, 'stderr': raw_write.stderr},
            'managed_review': managed_review.stdout, 'payload': json.loads(payload),
            'environment_sha256': env_digest, 'equal': equal}
        Path(sys.argv[1]).write_text(json.dumps(record, indent=2) + '\n')
        assert raw_review.returncode == 0 and not raw_review.stderr, record['native_review']
        assert raw_write.returncode == 0 and not raw_write.stderr, record['native_write']
        assert all(equal.values()), equal
        print('Managed token review, hash payload, and environment bytes match the pinned native tool')
    finally:
        test.doCleanups()


if __name__ == '__main__':
    main()
