# ABOUTME: Builds private native fixtures and runs the final complete regression at one revision.
# ABOUTME: Saves command outcomes and exact remaining fixture skips without hiding failures.
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
OUT = ROOT / 'docs/verification/2026-10-02-sol-review-fixes/final'
CACHE = Path('/home/outsider/.cache/lifeos-plugin-memory/sol-review-fixes-final-diagnostics')
SOURCE = Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release')
PYTHON = '/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'
OUT.mkdir(exist_ok=True)
CACHE.mkdir(mode=0o700)
fixture_home = CACHE / 'home'
fixture_home.mkdir(mode=0o700)
(fixture_home / 'tmp').mkdir(mode=0o700)
(fixture_home / '.cache').mkdir(mode=0o700)
(fixture_home / '.bun/bin').mkdir(parents=True)
(fixture_home / '.bun/bin/bun').symlink_to(shutil.which('bun'))
shutil.copytree(SOURCE / 'lifeos/LifeOS/install', fixture_home / '.claude', symlinks=True)
rebuild_source = CACHE / 'hermes-rebuild'
subprocess.run(['cp', '-a', '--reflink=auto', str(SOURCE / 'hermes'), str(rebuild_source)], check=True)
sys.path.insert(0, str(ROOT))
from scripts.rebuild_hermes_patches import GROUPS
tracked = set(subprocess.check_output(['git', '-C', str(rebuild_source), 'ls-files'], text=True).splitlines())
added = sorted({path for paths in GROUPS.values() for path in paths} - tracked)
subprocess.run(['git', '-C', str(rebuild_source), 'add', '-N', '--', *added], check=True)
workspace = fixture_home / 'workspace'
workspace.mkdir()
lifeos_repository = workspace / 'LifeOS'
subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(SOURCE / 'lifeos'), str(lifeos_repository)], check=True)
(workspace / 'lifeos-candidate').symlink_to(lifeos_repository, target_is_directory=True)
subprocess.run(['git', '-C', str(lifeos_repository), 'tag', 'readiness-base-36727e5'], check=True)
if not subprocess.check_output(['git', '-C', str(lifeos_repository), 'tag', '--list', 'v*'], text=True).strip():
    subprocess.run(['git', '-C', str(lifeos_repository), 'tag', 'v7.40.4'], check=True)
tagged_install = CACHE / 'tagged-install'
shutil.copytree(SOURCE / 'lifeos/LifeOS/install', tagged_install, symlinks=True)
subprocess.run(['git', 'init', '--quiet', '--initial-branch=fixture', str(tagged_install)], check=True)
subprocess.run(['git', '-C', str(tagged_install), 'add', '--', 'hooks'], check=True)
subprocess.run(['git', '-C', str(tagged_install), '-c', 'user.name=Readiness fixture',
                '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet', '-m', 'Native installation fixture'], check=True)
subprocess.run(['git', '-C', str(tagged_install), 'tag', 'v7.40.4'], check=True)
env = dict(os.environ, HOME=str(fixture_home), TMPDIR=str(fixture_home / 'tmp'),
           PYTHONPATH='.:tests:' + str(SOURCE / 'hermes'), PYTHONDONTWRITEBYTECODE='1',
           LIFEOS_MEMORY_SOURCE=str(SOURCE / 'lifeos/LifeOS/install'),
           LIFEOS_HERMES_SOURCE=str(SOURCE / 'hermes'),
           LIFEOS_HERMES_REBUILD_SOURCE=str(rebuild_source),
           LIFEOS_PREPARE_HERMES_REPO='/home/outsider/Projects/Hermes_agent/upstream/final-gate-baseline',
           LIFEOS_PREPARE_LIFEOS_REPO='/home/outsider/.cache/lifeos-plugin-memory/managed-source',
           HERMES_POLICY_SOURCE=str(SOURCE / 'hermes'),
           LIFEOS_COMMAND_HERMES_SOURCE=str(SOURCE / 'hermes'),
           LIFEOS_COMMAND_DEPENDENCIES='/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env',
           LIFEOS_VERSION_DRIFT_TAGGED_REPO_PATH=str(tagged_install))
hooks = {
    'TASK_HOOK_PATH': 'TaskGovernance', 'CHECKPOINT_HOOK_PATH': 'CheckpointPerISC',
    'ALGORITHM_NUDGE_PATH': 'AlgorithmNudge', 'DRIFT_REMINDER_PATH': 'DriftReminder',
    'EVENT_LOGGER_HOOK_PATH': 'EventLogger',
    'HOOK_HEALER_PATH': 'HookHealer', 'KITTY_HOOK_PATH': 'KittyEnvPersist',
    'LOOP_DETECTOR_PATH': 'LoopDetector', 'MODEL_RUNG_GUARD_PATH': 'ModelRungGuard',
    'PROMPT_PROCESSING_PATH': 'PromptProcessing', 'REMINDER_ROUTER_PATH': 'ReminderRouter',
    'SESSION_CLEANUP_PATH': 'SessionCleanup', 'WORK_COMPLETION_PATH': 'WorkCompletionLearning',
    'VERSION_DRIFT_PATH': 'VersionDrift', 'VOICE_HOOK_PATH': 'VoiceCompletion', 'PERMISSION_HOOK': 'Safety',
}
for key, name in hooks.items():
    path = SOURCE / 'lifeos/LifeOS/install/hooks' / (name + '.hook.ts')
    assert path.is_file(), path
    env['LIFEOS_' + key] = str(path)
for key, name in {'FAILURE_CAPTURE_PATH': 'FailureCapture', 'WATCHDOG_PATH': 'AgentWatchdog',
                  'FRESHNESS_CACHE_PATH': 'FreshnessCache',
                  'MERGE_SETTINGS_PATH': 'MergeSettings', 'SETTINGS_BACKPORT_PATH': 'SettingsBackport'}.items():
    path = SOURCE / 'lifeos/LifeOS/install/LIFEOS/TOOLS' / (name + '.ts')
    assert path.is_file(), path
    env['LIFEOS_' + key] = str(path)
env['LIFEOS_SESSION_END_HOOK_DIR'] = str(SOURCE / 'lifeos/LifeOS/install/hooks')
manifest = json.loads((SOURCE / 'source-manifest.json').read_text())
for component in manifest.values():
    for patch in component['patches']:
        assert hashlib.sha256((ROOT / 'patches' / patch['name']).read_bytes()).hexdigest() == patch['sha256']
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
(OUT / 'source-identity.json').write_text(json.dumps({'plugin': revision, 'prepared_sources': manifest,
    'native_environment': {key: value for key, value in env.items() if key.startswith(('LIFEOS_', 'HERMES_POLICY'))}}, indent=2) + '\n')
commands = {
    'regression': [PYTHON, '-W', 'error::ResourceWarning', '-m', 'unittest', 'discover', '-v', '-s', 'tests'],
    'recorder': [PYTHON, '-W', 'error::ResourceWarning', '-m', 'unittest', 'discover', '-v', '-s', 'development/tests'],
    'dashboard': ['node', '--test', 'tests/test_dashboard_ui.cjs', 'tests/test_memory_dashboard_ui.cjs'],
}

recorded_keys=[key for key in env if key.startswith(('LIFEOS_', 'HERMES_POLICY')) or key in ('HOME','TMPDIR','PYTHONPATH','PYTHONDONTWRITEBYTECODE')]
(OUT/'commands.json').write_text(json.dumps({'commands':commands,'environment':{key:env[key] for key in recorded_keys}},indent=2)+'\n')
