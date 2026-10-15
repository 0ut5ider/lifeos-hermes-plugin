# ABOUTME: Runs independent archive refusal and actual publication-plan probes for PR27.
# ABOUTME: Uses only synthetic private files and records measured results without guest access.
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
from unittest.mock import patch

from test_release_baseline import ReleaseBaselineTests
from lifeos_hook_bridge import update_plan, version_drift, update_hooks, update_dependencies
from optional.lifeos_release_manager import release_baseline
from optional.lifeos_release_manager.release_programs import ProgramTransaction
from optional.lifeos_release_manager.release_worker import _program_plan

results = []

def run(name, operation):
    fixture = ReleaseBaselineTests()
    fixture.setUp()
    try:
        operation(fixture)
        results.append({'case': name, 'status': 'PASS'})
    finally:
        fixture.doCleanups()

def refuses(fixture):
    try:
        fixture.review()
    except update_plan.UpdateConflict:
        return
    raise AssertionError('Expected exact archive proof refusal')

for key, bad in [('verification', 'unrecorded'), ('version', '../0.4.3'), ('commit', 'a'*39),
                 ('package_sha256', 'b'*64)]:
    def invalid(f, key=key, bad=bad):
        f.active[key] = bad
        refuses(f)
    run('refuse-invalid-active-' + key, invalid)

for attr, limit in [('MAX_ARCHIVE_BYTES', 1), ('MAX_MEMBERS', 0), ('MAX_EXTRACTED_BYTES', 1)]:
    def bounded(f, attr=attr, limit=limit):
        with patch.object(release_baseline, attr, limit):
            refuses(f)
    run('refuse-' + attr.lower(), bounded)

def wrong_source(f):
    f.baseline['source_root'] = str(f.source.parent / 'other-install')
    refuses(f)
run('refuse-nonfixed-source-layout', wrong_source)

def owner_collision(f):
    other = 'LIFEOS/USER/private.md'
    f.desired[other] = 'a' * 64
    f.put(f.installed, other, b'synthetic user data')
    refuses(f)
run('refuse-personal-destination', owner_collision)

def alias_parent(f):
    physical = f.package.parent
    alias = physical.parent / (physical.name + '-alias')
    alias.symlink_to(physical, target_is_directory=True)
    try:
        f.baseline['source_root'] = str(alias / f.package.name / 'lifeos/LifeOS/install')
        refuses(f)
    finally:
        alias.unlink()
run('refuse-source-parent-alias', alias_parent)

for mode in ('append', 'same-bytes-new-inode'):
    def race(f, mode=mode):
        digest = release_baseline._digest
        first = True
        def after_first_read(stream):
            nonlocal first
            value = digest(stream)
            if first:
                first = False
                if mode == 'append':
                    with f.archive.open('ab') as output:
                        output.write(b'mutation')
                else:
                    data = f.archive.read_bytes()
                    f.archive.unlink()
                    f.archive.write_bytes(data)
                    f.archive.chmod(0o600)
            return value
        with patch.object(release_baseline, '_digest', after_first_read):
            refuses(f)
    run('refuse-archive-race-' + mode, race)

def publication(f):
    package = f.root / 'candidate'
    native = package / 'lifeos/LifeOS/install'
    native.parent.mkdir(parents=True)
    shutil.move(f.next_source, native)
    job = f.root / 'operation'
    job.mkdir(mode=0o700)
    tools = job / 'tools'
    tools.mkdir()
    (tools / 'bun').write_text('#!/bin/sh\nexit 0\n')
    (tools / 'bun').chmod(0o700)
    (f.profile / 'config.yaml').write_text('_config_version: 46\nmodel:\n  default: synthetic-model\n')
    (f.installed / 'settings.json').write_text('{"hooks":{}}')
    (package / 'DAILY-CANDIDATE.json').write_text('{"plugin_files":{}}')
    for name in ('lifeos_hook_bridge', 'optional/lifeos_release_manager'):
        path = package / name
        path.mkdir(parents=True)
        (path / '__init__.py').write_text('# synthetic reviewed program\n')
    commands = {name: 'bin/' + name for name in ('hermes', 'hermes-agent', 'hermes-acp')}
    (job / 'manifest.json').write_text(json.dumps({'runtime': {'commands': commands}}))
    baseline_path = f.profile / 'baseline.json'
    original = baseline_path.read_bytes()
    request = {'profile': str(f.profile), 'account_home': str(f.profile.parent),
        'installed': str(f.installed),
        'runtime': {'python': sys.executable,
            'source': str(Path(__import__('hermes_cli').__file__).resolve().parents[1]),
            'hermes': str(job / 'bin/hermes'), 'bun': str(tools / 'bun'), 'reference': str(f.reference)},
        'certificate': {'hermes_base': 'synthetic', 'lifeos_base': 'synthetic',
            'hermes_patch_count': 10, 'lifeos_patch_count': 25},
        'version': '0.5.0', 'commit': 'b'*40, 'package_sha256': 'c'*64}
    reviewed = f.review()
    modules = {'version_drift': version_drift, 'update_plan': update_plan,
        'update_hooks': update_hooks, 'update_dependencies': update_dependencies}
    selected = {'profile': f.profile, 'installed': f.installed, 'package': package,
        'bridge': f.profile / 'plugins/lifeos-hook-bridge',
        'launchers': [f.profile.parent / '.local/bin/hermes'],
        'current': SimpleNamespace(memory_module=modules.__getitem__), 'fresh': False,
        'native_changes': True, 'baseline': baseline_path, 'reviewed_baseline': reviewed,
        'prior_source': f.source}
    dirs, files, deps = _program_plan(job, request, selected)
    assert files[f.installed / f.name] == native / f.name
    assert baseline_path.read_bytes() == original
    transaction = ProgramTransaction(job / 'program-snapshot')
    transaction.prepare(directories=dirs, files=files, dependencies=deps)
    transaction.check_prepared()
    # Removing the augmentation must restore the collision refusal in the actual publication planner.
    selected['reviewed_baseline'] = f.baseline
    try:
        _program_plan(job, request, selected)
    except update_plan.UpdateConflict:
        pass
    else:
        raise AssertionError('Actual publication planner bypasses the reviewed baseline')
    selected['reviewed_baseline'] = reviewed
    (f.installed / f.name).write_text('synthetic later program edit')
    try:
        _program_plan(job, request, selected)
    except update_plan.UpdateConflict:
        pass
    else:
        raise AssertionError('Actual publication planner adopts later program edit')
    assert baseline_path.read_bytes() == original
run('actual-publication-plan-uses-augmentation-and-refuses-later-edit', publication)

print(json.dumps({'status': 'PASS', 'cases': len(results), 'results': results}, indent=2))
