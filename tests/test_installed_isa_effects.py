# ABOUTME: Compares actual file mutations with native and installed Hermes hook effects.
# ABOUTME: Verifies ISA registry transitions, rendered files, views, and checkpoint identity.
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


@unittest.skipUnless(SOURCE and LIFEOS, 'Prepared Hermes and native file hooks are required')
class InstalledISAEffectTests(unittest.TestCase):
    def test_isa_transitions_and_checkpoint_identity_use_applied_files(self):
        results = []
        for side in ('native', 'hermes'):
            with tempfile.TemporaryDirectory(prefix='isa-effects-') as directory:
                home = Path(directory)
                profile = home / '.hermes'
                profile.mkdir()
                shutil.copytree(ROOT / 'lifeos_hook_bridge', profile / 'plugins/lifeos-hook-bridge',
                                ignore=shutil.ignore_patterns('__pycache__'))
                env = {**os.environ, 'HOME': str(home), 'HERMES_HOME': str(profile),
                       'LIFEOS_DIR': str(home / '.claude/LIFEOS'),
                       'LIFEOS_HOOK_SETTINGS': str(home / '.claude/settings.json'),
                       'PYTHONPATH': str(SOURCE), 'HERMES_WRITE_SAFE_ROOT': str(home),
                       'TERMINAL_CWD': str(home), 'LIFEOS_NOTIFICATION_CHANNEL': 'headless',
                       'PAIR_FILE_SOURCE': str(LIFEOS), 'PAIR_FILE_SIDE': side}
                process = subprocess.run([sys.executable, str(ROOT / 'tests/isa_effect_controls_process.py')],
                                         env=env, cwd=home, capture_output=True, text=True, timeout=150)
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
                report = json.loads((home / 'isa-results.json').read_text())
                comparable = [{key: value for key, value in row.items() if key not in ('arguments', 'result', 'native_tool', 'context')}
                              for row in report['cases']]
                self.assertEqual(len(comparable), 4)
                results.append(comparable)
                evidence = os.environ.get('LIFEOS_ISA_EFFECT_EVIDENCE')
                if evidence:
                    target = Path(evidence)
                    target.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(home / 'isa-results.json', target / (side + '.json'))
        self.assertEqual(results[0], results[1])
