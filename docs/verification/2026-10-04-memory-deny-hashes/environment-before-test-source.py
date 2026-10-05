# ABOUTME: Verifies environment publication preserves original line endings and bytes.
# ABOUTME: Uses synthetic environment settings without exposing generated salts.
import unittest

import test_memory_deny_hashes as hash_fixture


class MemoryDenyHashesEnvironmentTests(unittest.TestCase):
    def test_generated_salt_preserves_crlf_environment_prefix(self):
        fixture = hash_fixture.MemoryDenyHashesTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        before = b'SYNTHETIC_KEEP=fixture\r\nSYNTHETIC_SECOND=preserved\r\n'
        fixture.env.write_bytes(before)
        fixture.successful()
        self.assertTrue(fixture.env.read_bytes().startswith(before), 'Environment line endings change during publication')
