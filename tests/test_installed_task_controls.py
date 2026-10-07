# ABOUTME: Runs native task governance through the installed Hermes dispatcher and real task storage.
# ABOUTME: Keeps the board and profile isolated from existing kanban projects.
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


@unittest.skipUnless(SOURCE and LIFEOS, 'Prepared Hermes and native governance are required')
class InstalledTaskControlsTests(unittest.TestCase):
    def test_actual_task_storage_obeys_native_quality_limit_and_child_rules(self):
        with tempfile.TemporaryDirectory(prefix='task-controls-') as directory:
            home = Path(directory)
            profile = home / '.hermes'
            profile.mkdir()
            shutil.copytree(ROOT / 'lifeos_hook_bridge', profile / 'plugins/lifeos-hook-bridge',
                            ignore=shutil.ignore_patterns('__pycache__'))
            env = {**os.environ, 'HOME': str(home), 'HERMES_HOME': str(profile), 'HERMES_KANBAN_HOME': str(home / 'board'),
                   'LIFEOS_DIR': str(home / '.claude/LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(home / '.claude/settings.json'),
                   'PYTHONPATH': str(SOURCE), 'PAIR_FILE_SOURCE': str(LIFEOS)}
            result = subprocess.run([sys.executable, str(ROOT / 'tests/task_controls_process.py')], env=env, cwd=home,
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, '')
            data = json.loads((home / 'task-results.json').read_text())
            self.assertEqual(data['actual_board_tasks'], 51)
            evidence = os.environ.get('LIFEOS_TASK_CONTROL_EVIDENCE')
            if evidence:
                target = Path(evidence)
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(home / 'task-results.json', target / 'tasks.json')
