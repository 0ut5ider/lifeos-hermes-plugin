# ABOUTME: Checks denial precedence and malformed review with actual installed Hermes operations.
# ABOUTME: Retains measured file effects, shell refusal, and fixture policy source identity.
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = os.environ.get('LIFEOS_HERMES_SOURCE')
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(SOURCE, 'Prepared Hermes is required')
class InstalledPolicyPrecedenceTests(unittest.TestCase):
    def test_policy_sources_and_command_targets_control_actual_effects(self):
        with tempfile.TemporaryDirectory(prefix='policy-effects-') as directory:
            home = Path(directory)
            profile = home / '.hermes'
            profile.mkdir()
            shutil.copytree(ROOT / 'lifeos_hook_bridge', profile / 'plugins/lifeos-hook-bridge',
                            ignore=shutil.ignore_patterns('__pycache__'))
            environment = {**os.environ, 'HOME': str(home), 'HERMES_HOME': str(profile),
                'LIFEOS_DIR': str(home / '.claude/LIFEOS'),
                'LIFEOS_HOOK_SETTINGS': str(home / '.claude/settings.json'),
                'HERMES_WRITE_SAFE_ROOT': str(home), 'HERMES_INTERACTIVE': '1',
                'TERMINAL_CWD': str(home / 'project'), 'PYTHONPATH': str(SOURCE),
                }
            result = subprocess.run([sys.executable, str(ROOT / 'tests/policy_precedence_process.py')],
                cwd=home, env=environment, text=True, capture_output=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, '')
            report = json.loads((home / 'policy-results.json').read_text())
            self.assertEqual(len(report['cases']), 15)
            self.assertTrue(all(row['verified'] for row in report['cases']))
            evidence = os.environ.get('LIFEOS_POLICY_EVIDENCE')
            if evidence:
                target = Path(evidence)
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(home / 'policy-results.json', target / 'policy-results.json')
