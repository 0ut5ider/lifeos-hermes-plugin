# ABOUTME: Executes file and shell permission decisions through the installed Hermes dispatcher.
# ABOUTME: Checks actual fixture effects and approval callbacks without synthetic model responses.
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = os.environ.get('LIFEOS_HERMES_SOURCE')
SAFETY = os.environ.get('LIFEOS_PERMISSION_HOOK')
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(SOURCE and SAFETY, 'Prepared Hermes and native Safety are required')
class InstalledPermissionControlTests(unittest.TestCase):
    def test_real_mcp_transport_respects_a_denied_tool(self):
        with tempfile.TemporaryDirectory(prefix='mcp-permission-controls-') as directory:
            home = Path(directory)
            profile = home / '.hermes'
            profile.mkdir()
            shutil.copytree(ROOT / 'lifeos_hook_bridge', profile / 'plugins/lifeos-hook-bridge',
                            ignore=shutil.ignore_patterns('__pycache__'))
            env = {**os.environ, 'HOME': str(home), 'HERMES_HOME': str(profile),
                   'LIFEOS_DIR': str(home / '.claude/LIFEOS'),
                   'LIFEOS_HOOK_SETTINGS': str(home / '.claude/settings.json'),
                   'HERMES_INTERACTIVE': '1', 'TERMINAL_CWD': str(home), 'PYTHONPATH': str(SOURCE),
                   'PAIR_NATIVE_SAFETY': str(SAFETY)}
            result = subprocess.run([sys.executable, str(ROOT / 'tests/permission_controls_process.py'), 'mcp'],
                                    env=env, cwd=home, text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((home / 'mcp-results.json').read_text())
            self.assertEqual(len(report['cases']), 4)
            evidence = os.environ.get('LIFEOS_PERMISSION_EVIDENCE')
            if evidence:
                target = Path(evidence)
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(home / 'mcp-results.json', target / 'mcp-results.json')

    def test_real_dispatcher_preserves_allow_ask_and_deny_effects(self):
        with tempfile.TemporaryDirectory(prefix='permission-controls-') as directory:
            home = Path(directory)
            profile = home / '.hermes'
            profile.mkdir()
            shutil.copytree(ROOT / 'lifeos_hook_bridge', profile / 'plugins/lifeos-hook-bridge',
                            ignore=shutil.ignore_patterns('__pycache__'))
            env = {**os.environ, 'HOME': str(home), 'HERMES_HOME': str(profile),
                   'LIFEOS_DIR': str(home / '.claude/LIFEOS'),
                   'LIFEOS_HOOK_SETTINGS': str(home / '.claude/settings.json'),
                   'HERMES_WRITE_SAFE_ROOT': str(home), 'TERMINAL_CWD': str(home),
                   'HERMES_INTERACTIVE': '1', 'PYTHONPATH': str(SOURCE),
                   'PAIR_NATIVE_SAFETY': str(SAFETY)}
            result = subprocess.run([sys.executable, str(ROOT / 'tests/permission_controls_process.py')],
                                    env=env, cwd=home, text=True, capture_output=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((home / 'permission-results.json').read_text())
            self.assertEqual(len(report['cases']), 16)
            self.assertTrue(all(row['verified'] for row in report['cases']))
            evidence = os.environ.get('LIFEOS_PERMISSION_EVIDENCE')
            if evidence:
                target = Path(evidence)
                target.mkdir(parents=True, exist_ok=True)
                for name in ('permission-results.json', 'permission-trace.jsonl'):
                    shutil.copy2(home / name, target / name)
