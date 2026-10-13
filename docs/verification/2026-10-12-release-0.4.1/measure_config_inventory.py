# ABOUTME: Compares actual configuration inventory signatures with a single-pass filesystem prototype.
# ABOUTME: Measures program-file metadata without reading file contents or changing the installed bridge.
import json
import os
from pathlib import Path
import stat
import sys
import time

job = Path(sys.argv[1])
folder = Path(sys.argv[2])
request = json.loads((job / 'request.json').read_bytes())
sys.path[:0] = [str(job / 'package'), request['runtime']['source']]
from optional.lifeos_release_manager.release_stage import load_bridge
helpers = load_bridge(job / 'package/lifeos_hook_bridge')
module = helpers.memory_module('bridge')
selected = helpers.memory_module('lifeos_installation').selection(Path(request['profile']))

def signature(info):
    return (info.st_mtime_ns, info.st_size, info.st_ctime_ns, info.st_dev, info.st_ino)

def prototype(bridge):
    result = {}
    def add(path):
        try:
            result[path] = signature(path.stat())
        except OSError:
            pass
    def walk(root):
        try:
            with os.scandir(root) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            walk(Path(entry.path))
                        elif entry.is_file():
                            result[Path(entry.path)] = signature(entry.stat())
                    except OSError:
                        pass
        except OSError:
            pass
    add(bridge.settings_path)
    add(module.POLICY_DIRECTORY / 'managed-settings.json')
    for project in bridge.project_dirs:
        add(project / '.claude/settings.json')
        add(project / '.claude/settings.local.json')
        walk(project / '.claude/skills')
    for path in (module.POLICY_DIRECTORY / 'managed-settings.d').glob('*.json'):
        if path.is_file():
            add(path)
    walk(bridge.settings_path.parent / 'skills')
    return result

reports = []
try:
    for label, cwd in [('account-home', Path(request['account_home'])), ('native-home', selected.home)]:
        bridge = object.__new__(module.HookBridge)
        bridge.settings_path = selected.installed / 'settings.json'
        bridge.project_dirs = (cwd,)
        started = time.monotonic()
        baseline = bridge._config_files()
        baseline_seconds = time.monotonic() - started
        started = time.monotonic()
        candidate = prototype(bridge)
        prototype_seconds = time.monotonic() - started
        reports.append({'case': label, 'baseline_seconds': baseline_seconds,
            'prototype_seconds': prototype_seconds, 'baseline_files': len(baseline),
            'prototype_files': len(candidate), 'exact_inventory_and_signatures': baseline == candidate,
            'project_skill_files': sum(path.is_relative_to(cwd / '.claude/skills') for path in baseline),
            'selected_user_skill_files': sum(path.is_relative_to(selected.installed / 'skills') for path in baseline)})
    (folder / 'configuration-inventory-measurement.json').write_text(json.dumps({
        'program_commit': request['commit'], 'file_contents_read': False,
        'production_code_changed': False, 'cases': reports}, indent=2) + '\n')
    assert all(row['exact_inventory_and_signatures'] for row in reports)
finally:
    (folder / 'configuration-inventory-measurement.done').write_text(
        '0\n' if len(reports) == 2 and all(row['exact_inventory_and_signatures'] for row in reports) else '1\n')
