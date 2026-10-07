# ABOUTME: Runs native audit through the installed Hermes dispatcher and actual tool operations.
# ABOUTME: Keeps audit, skill execution, and work reconciliation state isolated.
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = os.environ.get('LIFEOS_HERMES_SOURCE')
LIFEOS = os.environ.get('LIFEOS_GUARD_SOURCE')
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(SOURCE and LIFEOS, 'Prepared Hermes and native audit are required')
class InstalledAuditControlsTests(unittest.TestCase):
    def test_actual_tool_facts_drive_audit_and_work_reconciliation(self):
        with tempfile.TemporaryDirectory(prefix='audit-controls-') as directory:
            home = Path(directory)
            profile = home / '.hermes'
            profile.mkdir()
            shutil.copytree(ROOT / 'lifeos_hook_bridge', profile / 'plugins/lifeos-hook-bridge',
                            ignore=shutil.ignore_patterns('__pycache__'))
            env = {**os.environ, 'HOME': str(home), 'HERMES_HOME': str(profile), 'HERMES_KANBAN_HOME': str(home / 'board'),
                   'LIFEOS_DIR': str(home / '.claude/LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(home / '.claude/settings.json'),
                   'PYTHONPATH': str(SOURCE), 'PAIR_FILE_SOURCE': str(LIFEOS)}
            result = subprocess.run([sys.executable, str(ROOT / 'tests/event_audit_controls_process.py')], env=env, cwd=home,
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, 'MCP tool audit/ping call failed: PAIR_ACTUAL_MCP_FAILURE\n')
            data = json.loads((home / 'audit-results.json').read_text())
            self.assertTrue(data['heartbeat_advanced'])
            evidence = os.environ.get('LIFEOS_AUDIT_CONTROL_EVIDENCE')
            if evidence:
                target = Path(evidence)
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(home / 'audit-results.json', target / 'audit.json')
