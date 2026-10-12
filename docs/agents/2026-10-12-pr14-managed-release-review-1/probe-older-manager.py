# ABOUTME: Compares actual older-manager and frozen-candidate program plans.
# ABOUTME: Demonstrates admission of an incomplete older plan with real staging and journal files.
import importlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import types
from optional.lifeos_release_manager.release_worker import _program_plan as current_plan
from optional.lifeos_release_manager.release_programs import ProgramTransaction, publish
from optional.lifeos_release_manager.release_operation import seal_plan, write_admission, validate_admission
from optional.lifeos_release_manager.cli import write_state

archive = Path(__file__).with_name('older-manager-0deb335e.tar')
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    old = root / 'old'
    old.mkdir(mode=0o700)
    with tarfile.open(archive) as source:
        source.extractall(old, filter='data')
    namespace = types.ModuleType('prior_release_manager')
    namespace.__path__ = [str(old / 'optional/lifeos_release_manager')]
    sys.modules[namespace.__name__] = namespace
    prior = importlib.import_module(namespace.__name__ + '.release_worker')
    job, profile, package = root / 'job', root / '.hermes', root / 'package'
    for path in (job, profile, package, package / 'lifeos_hook_bridge', package / 'optional/lifeos_release_manager'):
        path.mkdir(parents=True, mode=0o700)
    for directory in ('lifeos_hook_bridge', 'optional/lifeos_release_manager'):
        (package / directory / 'program.py').write_text('qualified synthetic program')
    (profile / 'config.yaml').write_text('_config_version: 46\nmodel:\n  default: synthetic-model\n')
    (package / 'DAILY-CANDIDATE.json').write_text('{"plugin_files":{}}')
    commands = {name: 'bin/' + name for name in ('hermes', 'hermes-agent', 'hermes-acp')}
    (job / 'manifest.json').write_text(json.dumps({'runtime': {'commands': commands}}))
    bun = job / 'bun'
    bun.write_text('qualified synthetic bun')
    request = {'identifier': job.name, 'profile': str(profile), 'account_home': str(root),
               'runtime': {'python': sys.executable, 'source': str(Path(importlib.import_module('hermes_cli').__file__).resolve().parents[1]), 'hermes': str(job / 'bin/hermes'), 'bun': str(bun)},
               'certificate': {'hermes_base': 'synthetic', 'lifeos_base': 'synthetic', 'hermes_patch_count': 10, 'lifeos_patch_count': 25},
               'version': '0.4.0-dev.1', 'commit': 'a' * 40, 'package_sha256': 'b' * 64}
    selected = {'profile': profile, 'installed': root / '.claude', 'package': package,
                'bridge': profile / 'plugins/lifeos-hook-bridge', 'launchers': [root / '.local/bin/hermes'],
                'current': None, 'fresh': True}
    directories, files, dependencies = prior._program_plan(job, request, selected)
    transaction = ProgramTransaction(job / 'program-snapshot')
    transaction.prepare(directories=directories, files=files, dependencies=dependencies)
    old_targets = sorted(str(path.relative_to(root)) for path in files)
    publish(job / 'request.json', json.dumps(request).encode())
    write_state(job, 'ready')
    plan = {'fresh': True, 'native_mount_required': True, 'services': None,
            'launchers': [str(root / '.local/bin/hermes')], 'program_entries_sha256': transaction.entries_digest()}
    seal_plan(job, request, plan)
    write_admission(job, request, 'apply')
    write_state(job, 'queued-apply')
    validate_admission(job, request, 'apply')
    ProgramTransaction(transaction.snapshot, expected_entries_sha256=plan['program_entries_sha256']).check_prepared()
    print('current candidate admission and prepared journal checks: PASS')
    print('older manager targets:', json.dumps(old_targets))
    _, current_files, _ = current_plan(job, request, selected)
    new_targets = sorted(str(path.relative_to(root)) for path in current_files)
    print('candidate manager targets:', json.dumps(new_targets))
    print('missing candidate targets in accepted older journal:', json.dumps(sorted(set(new_targets) - set(old_targets))))
    print('candidate native verification launchers:', json.dumps(plan['launchers']))
