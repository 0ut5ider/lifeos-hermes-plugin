# ABOUTME: Verifies native configuration audit paths and independent source baselines.
# ABOUTME: Runs EventLogger against real settings and skill files in disposable homes.

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = os.environ.get('LIFEOS_CONFIG_AUDIT_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Native EventLogger and Bun are required')
class NativeConfigAuditTests(unittest.TestCase):
    def test_each_configuration_source_uses_its_actual_file(self):
        with tempfile.TemporaryDirectory(prefix='config-audit-') as directory:
            home = Path(directory)
            root = home / '.claude'
            root.mkdir()
            (root / 'settings.json').write_text('{}')
            environment = {**os.environ, 'HOME': str(home), 'LIFEOS_DIR': str(root / 'LIFEOS'),
                           'LIFEOS_CONFIG_DIR': str(root)}
            audit = root / 'LIFEOS/MEMORY/OBSERVABILITY/config-changes.jsonl'
            for source, relative in (('user_settings', '.claude/settings.json'),
                                     ('project_settings', 'project/.claude/settings.json'),
                                     ('local_settings', 'project/.claude/settings.local.json'),
                                     ('skills', '.claude/skills/fixture/SKILL.md')):
                with self.subTest(source=source):
                    path = home / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('Fixture zero\n' if source == 'skills' else '{"env":{"FIXTURE":"zero"}}')
                    payload = {'hook_event_name': 'ConfigChange', 'session_id': 'config-session',
                               'source': source, 'file_path': str(path)}

                    def run():
                        result = subprocess.run(['bun', str(Path(SOURCE) / 'hooks/EventLogger.hook.ts')],
                                                input=json.dumps(payload), text=True, capture_output=True,
                                                timeout=15, env=environment)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout, '')
                        self.assertIn('[ConfigAudit] Logged:', result.stderr)
                        return json.loads(audit.read_text().splitlines()[-1])

                    first = run()
                    self.assertEqual(first['config_path'], str(path))
                    self.assertEqual(first['source'], source)
                    self.assertEqual(first['config_key'], 'initial')
                    path.write_text('Fixture one\n' if source == 'skills' else '{"env":{"FIXTURE":"one"}}')
                    second = run()
                    self.assertEqual(second['config_key'], 'content' if source == 'skills' else 'env')
                    self.assertNotIn('no diff', second['change_summary'])
                    self.assertNotIn('Fixture one', second['change_summary'])
                    self.assertEqual(run()['config_key'], 'unchanged')
