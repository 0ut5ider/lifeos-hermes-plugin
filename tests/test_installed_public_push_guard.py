# ABOUTME: Measures installed publication policy under ordinary and bypass approval modes.
# ABOUTME: Retains actual dispatcher results without running an external publication command.
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = os.environ.get('LIFEOS_HERMES_SOURCE')
GUARD = os.environ.get('LIFEOS_GUARD_SOURCE')
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(SOURCE and GUARD, 'Prepared Hermes and native guards are required')
class InstalledPublicPushGuardTests(unittest.TestCase):
    def test_public_policy_survives_all_approval_modes(self):
        for mode in ('manual', 'off', 'yolo', 'permanent'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='public-guard-') as directory:
                home = Path(directory)
                profile = home / '.hermes'
                profile.mkdir()
                shutil.copytree(ROOT / 'lifeos_hook_bridge', profile / 'plugins/lifeos-hook-bridge',
                                ignore=shutil.ignore_patterns('__pycache__'))
                env = {**os.environ, 'HOME': str(home), 'HERMES_HOME': str(profile),
                       'LIFEOS_DIR': str(home / '.claude/LIFEOS'),
                       'LIFEOS_HOOK_SETTINGS': str(home / '.claude/settings.json'),
                       'HERMES_INTERACTIVE': '1', 'PYTHONPATH': str(SOURCE), 'TERMINAL_CWD': str(home),
                       'PAIR_NATIVE_GUARD': str(Path(GUARD) / 'hooks/PreToolGuard.hook.ts'),
                       'PAIR_APPROVAL_MODE': mode, 'HERMES_YOLO_MODE': '1' if mode == 'yolo' else '0'}
                process = subprocess.run([sys.executable, str(ROOT / 'tests/public_push_controls_process.py')],
                                         env=env, cwd=home, capture_output=True, text=True, timeout=80)
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
                rows = json.loads((home / 'public-results.json').read_text())['cases']
                self.assertEqual(len(rows), 4)
                evidence = os.environ.get('LIFEOS_PUBLIC_GUARD_EVIDENCE')
                if evidence:
                    target = Path(evidence)
                    target.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(home / 'public-results.json', target / (mode + '.json'))
