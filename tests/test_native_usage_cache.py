# ABOUTME: Measures native usage-cache behavior with absent and invalid synthetic credentials.
# ABOUTME: Uses an optional isolated network namespace for actual fetch failure without external authentication.
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native usage handler and Bun are required')
class NativeUsageCacheTests(unittest.TestCase):
    def run_case(self, credentials, *, prior=True):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home/'.claude'
            state = root/'LIFEOS/MEMORY/STATE'
            state.mkdir(parents=True)
            cache = state/'usage-cache.json'
            previous = b'{"five_hour":{"utilization":17},"synthetic_prior":true}\n'
            if prior:
                cache.write_bytes(previous)
            if credentials is not None:
                (root/'.credentials.json').write_text(credentials)
            environment = {**os.environ,'HOME':str(home),'LIFEOS_DIR':str(root/'LIFEOS')}
            for key in ('ANTHROPIC_ADMIN_API_KEY','LIFEOS_MEMORY_CONTEXT','LIFEOS_MEMORY_INTERNAL',
                        'LIFEOS_CONFIG_DIR','CLAUDE_CONFIG_DIR','HTTPS_PROXY','HTTP_PROXY','ALL_PROXY'):
                environment.pop(key,None)
            command = ['bun',str(Path(SOURCE)/'hooks/UpdateCounts.hook.ts')]
            trace = None
            if credentials and 'SYNTHETIC_EXPIRED_TEST_TOKEN' in credentials:
                self.assertIsNotNone(shutil.which('strace'), 'Actual network failure requires syscall tracing')
                trace = Path(os.environ.get('LIFEOS_USAGE_NETWORK_TRACE', str(home/'network.log')))
                command = ['strace','-f','-e','trace=network','-o',str(trace),*command]
            result = subprocess.run(command,
                env=environment,capture_output=True,text=True,timeout=15)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
            if trace:
                actual_network = trace.read_text()
                self.assertIn('AF_INET',actual_network)
                self.assertIn('ENETUNREACH',actual_network)
            if prior:
                self.assertEqual(cache.read_bytes(),previous)
            else:
                self.assertFalse(cache.exists())

    def test_absent_invalid_and_missing_token_preserve_prior_cache(self):
        for credentials in (None, '{', '{}', '{"claudeAiOauth":{}}'):
            with self.subTest(credentials=credentials):
                self.run_case(credentials)

    def test_absent_credentials_do_not_create_a_usage_cache(self):
        self.run_case(None,prior=False)

    @unittest.skipUnless(os.environ.get('LIFEOS_USAGE_NETWORK_ISOLATED')=='1',
                         'Actual usage fetch failure requires the disposable isolated network namespace')
    def test_expired_synthetic_token_and_actual_network_failure_preserve_prior_cache(self):
        # The caller runs this complete process under unshare -n. No external API is contacted.
        self.run_case(json.dumps({'claudeAiOauth':{'accessToken':'SYNTHETIC_EXPIRED_TEST_TOKEN','expiresAt':1}}))
