# ABOUTME: Measures staged editor admission against existing installation serialization and invalid configurations.
# ABOUTME: Uses real native and authenticated owner HTTP servers with disposable synthetic sources.
import json
from pathlib import Path
import unittest
import httpx
from test_memory_core_editor import MemoryCoreEditorTests
from lifeos_hook_bridge.installation_lock import installation_lock


class EditorReviewProbe(MemoryCoreEditorTests):
    def stop_pulse(self):
        self.process.terminate()
        output, error = self.process.communicate(timeout=10)
        Path(__file__).with_name('native-limit-response.stderr').write_text(error)
        self.assertIn('The native memory service returned an invalid result', error)

    def runTest(self):
        source = self.seed()
        profile = self.fixture.configuration.path.parent
        result = {}
        with httpx.Client(timeout=60) as client:
            self.login(client)
            read = self.read(client)
            original = source.read_bytes()
            with installation_lock(profile):
                response = client.put(self.native + '/api/hermes/file/principal-identity', json={
                    'content': '# Synthetic save during installation transaction\n',
                    'reference': read.json()['reference'], 'request_id': 'review-installation-lock'})
                result['installation_lock'] = {'status': response.status_code,
                    'response': response.json(), 'source_changed_while_lock_held': source.read_bytes() != original}
            read = self.read(client)
            large = '# Synthetic bounded native core edit\n' + 'public synthetic prose ' * 7000
            response = client.put(self.native + '/api/hermes/file/principal-identity', json={
                'content': large, 'reference': read.json()['reference'], 'request_id': 'review-native-core-limit'})
            result['native_core_limit'] = {'content_bytes': len(large.encode()), 'status': response.status_code,
                'response': response.text[:1000], 'content_type': response.headers.get('content-type'),
                'source_matches_requested_content': source.read_text() == large}
            config = profile / 'config.yaml'
            config.write_text('model: [synthetic-incomplete\n')
            response = self.read(client, 'config')
            result['malformed_yaml'] = {'status': response.status_code, 'response': response.json()}
            response = client.get(self.native + '/api/hermes')
            result['overview_with_malformed_yaml'] = {'status': response.status_code, 'response': response.json()}
        Path(__file__).with_name('backend-probes.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    suite = unittest.TestSuite([EditorReviewProbe()])
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not outcome.wasSuccessful())
