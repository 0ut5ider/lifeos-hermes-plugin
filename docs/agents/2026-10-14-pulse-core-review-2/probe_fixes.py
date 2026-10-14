# ABOUTME: Measures fixed core editor limits, installation serialization, and unrelated-route interruption recovery.
# ABOUTME: Uses real native and authenticated owner HTTP listeners with synthetic profile and source files.
import json
from pathlib import Path
import unittest
import httpx
from test_memory_core_editor import MemoryCoreEditorTests
from lifeos_hook_bridge.installation_lock import installation_lock
from lifeos_hook_bridge.program_lock import exclusive


class FixesProbe(MemoryCoreEditorTests):
    def runTest(self):
        result = {}
        source = self.seed()
        self.seed_programs()
        profile = self.fixture.configuration.path.parent
        (self.fixture.home / '.hermes').symlink_to(profile, target_is_directory=True)
        with httpx.Client(timeout=120) as client:
            self.login(client)
            reference = self.read(client).json()['reference']
            for name, lock in [('installation', installation_lock(profile)), ('program', exclusive(profile, timeout=0))]:
                with lock:
                    before = source.read_bytes()
                    response = client.put(self.native + '/api/hermes/file/principal-identity', json={
                        'content': '# Synthetic refused concurrent edit\n', 'reference': reference, 'request_id': 'round2-' + name})
                    result[name + '_save'] = {'status': response.status_code, 'unchanged': source.read_bytes() == before}
                    response = self.read(client)
                    result[name + '_read'] = {'status': response.status_code, 'content_present': 'content' in response.json()}
            for name, content in [('ascii-near-limit', '# Synthetic bounded source\n' + 'public synthetic prose\n' * 43000),
                                  ('unicode-near-limit', '# Synthetic UTF-8 source\n' + 'Évidence publique.\n' * 49000),
                                  ('over-byte-limit', 'é' * 500001)]:
                reference = self.read(client).json()['reference']
                before = source.read_bytes()
                response = client.put(self.native + '/api/hermes/file/principal-identity', json={
                    'content': content, 'reference': reference, 'request_id': 'round2-limit-' + name})
                result[name] = {'bytes': len(content.encode()), 'characters': len(content), 'status': response.status_code,
                    'content_type': response.headers.get('content-type'), 'matches': source.read_text() == content,
                    'unchanged': source.read_bytes() == before, 'error': response.json().get('error')}
            path = profile / 'config.yaml'
            path.write_text('model: synthetic-original\n')
            self.interrupt_save('config', path, client)
            before = path.read_text()
            with installation_lock(profile), exclusive(profile, timeout=0):
                response = client.post(self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/review', json={
                    'tool': 'lifeos_memory_search', 'arguments': {'query': 'authenticated PULSE'}})
                result['recovery_while_both_locks_held'] = {'http_status': response.status_code, 'response': response.json(),
                    'before': before, 'after': path.read_text()}
            response = client.post(self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/review', json={
                'tool': 'lifeos_memory_search', 'arguments': {'query': 'authenticated PULSE'}})
            result['recovery_after_lock_release'] = {'http_status': response.status_code, 'tool_status': response.json().get('status'),
                'after': path.read_text()}
            path.write_text('model: [synthetic-incomplete\n')
            response = client.get(self.native + '/api/hermes')
            rows = {row['id']: row for row in response.json()['files']} if response.status_code == 200 else {}
            result['malformed_yaml_overview'] = {'status': response.status_code, 'rows': len(rows),
                'config_readable': rows.get('config', {}).get('readable'),
                'identity_readable': rows.get('principal-identity', {}).get('readable')}
        Path(__file__).with_name('backend-fixes.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    outcome = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([FixesProbe()]))
    raise SystemExit(not outcome.wasSuccessful())
