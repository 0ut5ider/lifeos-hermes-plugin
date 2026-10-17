# ABOUTME: Measures component sizes and Hermes patch admission behavior on disposable copies of the 0.7.3 package.
# ABOUTME: Records every command, exit code, and result in one JSON file without touching the source archive.
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time

EXTRACT, STOCK, WORK, OUT = map(Path, sys.argv[1:5])
PATCHES = EXTRACT / 'lifeos_hook_bridge/patches'
HERMES_PATCHES = ['hermes-plugin-events.patch', 'hermes-turn-gates.patch', 'hermes-command-policy.patch',
    'hermes-session-lifecycle.patch', 'hermes-child-routing.patch', 'hermes-strict-inference.patch',
    'hermes-remote-files.patch', 'hermes-cron-bootstrap.patch', 'hermes-required-middleware.patch',
    'hermes-web-result-status.patch']
log = {'inputs': {k: str(v) for k, v in dict(extract=EXTRACT, stock=STOCK, work=WORK).items()}, 'commands': [],
       'results': {}}


def run(args, cwd, check=False):
    started = time.monotonic()
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    entry = {'cwd': str(cwd), 'args': [str(a) for a in args], 'rc': result.returncode,
             'seconds': round(time.monotonic() - started, 3),
             'stderr': result.stderr[-1500:], 'stdout': result.stdout[-800:]}
    log['commands'].append(entry)
    if check and result.returncode:
        raise RuntimeError(entry)
    return result


def file_map(root, skip=('.git',), skip_files=('hermes-source-manifest.json',)):
    value = {}
    for directory, names, files in os.walk(root):
        names[:] = [n for n in names if n not in skip and n != '__pycache__']
        for name in files:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if relative in skip_files:
                continue
            value[relative] = hashlib.sha256(path.read_bytes()).hexdigest() if not path.is_symlink() else 'link:' + os.readlink(path)
    return value


def compare(left, right):
    return {'only_left': sorted(set(left) - set(right)), 'only_right': sorted(set(right) - set(left)),
            'different': sorted(k for k in set(left) & set(right) if left[k] != right[k])}


def gz_size(paths, base, level=9):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz', compresslevel=level) as archive:
        for path in paths:
            archive.add(base / path, arcname=str(path), recursive=False)
    return len(buffer.getvalue())


def tree_files(root, exclude_git=True):
    result = []
    for directory, names, files in os.walk(root):
        if exclude_git:
            names[:] = [n for n in names if n != '.git']
        for name in files:
            result.append((Path(directory) / name).relative_to(root))
    return sorted(result)


def fresh_copy(source, name):
    target = WORK / name
    if target.exists():
        shutil.rmtree(target)
    run(['cp', '-a', '--reflink=auto', str(source), str(target)], WORK, check=True)
    return target


def apply_series(tree, names, reverse=False, extra=()):
    steps = []
    for name in (list(reversed(names)) if reverse else names):
        flags = ['-R'] if reverse else []
        check = run(['git', 'apply', '--check', *flags, *extra, str(PATCHES / name)], tree)
        applied = None
        if check.returncode == 0:
            applied = run(['git', 'apply', *flags, *extra, str(PATCHES / name)], tree).returncode
        steps.append({'patch': name, 'check_rc': check.returncode, 'apply_rc': applied,
                      'error': check.stderr.strip().splitlines()[:3]})
        if check.returncode:
            break
    return steps


# 1. Changed-file set between stock base and qualified patched Hermes.
stock_map = file_map(STOCK)
patched_map = file_map(EXTRACT / 'hermes')
delta = compare(stock_map, patched_map)
changed = sorted(set(delta['only_right']) | set(delta['different']))
category = {}
packages = ('agent/', 'tools/', 'hermes_cli/', 'gateway/', 'tui_gateway/', 'cron/', 'acp_adapter/', 'plugins/',
            'providers/', 'hermes_platform/', 'pm/')
for path in changed:
    if path.startswith('tests/'):
        kind = 'tests'
    elif path.startswith(packages):
        kind = 'wheel_package'
    elif '/' not in path and path.endswith('.py'):
        kind = 'root_module'
    else:
        kind = 'other'
    category.setdefault(kind, []).append(path)
runtime_changed = [p for p in changed if not p.startswith('tests/')]
log['results']['hermes_delta'] = {
    'stock_files': len(stock_map), 'patched_files_without_git_and_manifest': len(patched_map),
    'removed': delta['only_left'], 'added_count': len(delta['only_right']), 'modified_count': len(delta['different']),
    'changed_total': len(changed), 'by_category': {k: len(v) for k, v in category.items()},
    'other_paths': category.get('other', []), 'root_modules': category.get('root_module', []),
    'runtime_changed_bytes_after': sum((EXTRACT / 'hermes' / p).stat().st_size for p in runtime_changed),
    'runtime_changed_bytes_before': sum((STOCK / p).stat().st_size for p in runtime_changed if (STOCK / p).exists()),
    'all_changed_bytes_after': sum((EXTRACT / 'hermes' / p).stat().st_size for p in changed),
    'stock_tree_bytes': sum((STOCK / p).stat().st_size for p in stock_map),
}
(OUT / 'hermes-changed-files.json').write_text(json.dumps({'changed': changed, 'by_category': category,
    'after_sha256': {p: patched_map[p] for p in changed},
    'before_sha256': {p: stock_map.get(p) for p in changed}}, indent=2) + '\n')

# 2. E1 forward apply on an unversioned stock copy and comparison with the qualified tree.
e1 = fresh_copy(STOCK, 'e1-forward')
steps = apply_series(e1, HERMES_PATCHES)
log['results']['E1_forward_apply_unversioned_stock'] = {'steps': steps,
    'all_applied': all(s['apply_rc'] == 0 for s in steps) and len(steps) == len(HERMES_PATCHES),
    'comparison_with_qualified_tree': {k: len(v) for k, v in compare(file_map(e1), patched_map).items()},
    'comparison_detail': compare(file_map(e1), patched_map)}

# 3. E2 already-patched detection and E3 reverse to stock.
e2 = fresh_copy(EXTRACT / 'hermes', 'e2-already-patched')
shutil.rmtree(e2 / '.git')
(e2 / 'hermes-source-manifest.json').unlink()
forward_checks = [{'patch': n, 'forward_check_rc': run(['git', 'apply', '--check', str(PATCHES / n)], e2).returncode}
                  for n in HERMES_PATCHES]
reverse_whole = run(['git', 'apply', '--check', '-R', *[str(PATCHES / n) for n in reversed(HERMES_PATCHES)]], e2)
log['results']['E2_already_patched_detection'] = {'forward_checks': forward_checks,
    'reverse_series_check_rc_single_invocation': reverse_whole.returncode,
    'reverse_series_error': reverse_whole.stderr.strip().splitlines()[:3]}
steps = apply_series(e2, HERMES_PATCHES, reverse=True)
log['results']['E3_reverse_to_stock'] = {'steps': steps,
    'comparison_with_stock': {k: len(v) for k, v in compare(file_map(e2), stock_map).items()},
    'comparison_detail': compare(file_map(e2), stock_map)}

# 4. E4 local edit inside a patched hunk in a stock copy.
e4 = fresh_copy(STOCK, 'e4-edit-inside-hunk')
target = e4 / 'hermes_cli/plugins.py'
text = target.read_text()
marker = 'VALID_HOOKS: set[str] = {\n'
target.write_text(text.replace(marker, marker + '    "local_operator_hook",\n', 1))
steps = apply_series(e4, HERMES_PATCHES)
log['results']['E4_local_edit_inside_hunk'] = {'edited': 'hermes_cli/plugins.py VALID_HOOKS first line', 'steps': steps}

# 5. E5 local edit outside hunks in a touched file: forward apply, then reverse while preserving the edit.
e5 = fresh_copy(STOCK, 'e5-edit-outside-hunk')
target = e5 / 'model_tools.py'
original = target.read_text()
target.write_text(original + '\n# local operator note\n')
edited_hash = hashlib.sha256(target.read_bytes()).hexdigest()
forward = apply_series(e5, HERMES_PATCHES)
after_forward = hashlib.sha256(target.read_bytes()).hexdigest()
reverse = apply_series(e5, HERMES_PATCHES, reverse=True)
after_reverse = hashlib.sha256(target.read_bytes()).hexdigest()
log['results']['E5_local_edit_outside_hunk'] = {'edited': 'model_tools.py appended comment',
    'forward_steps': forward, 'forward_all_applied': all(s['apply_rc'] == 0 for s in forward) and len(forward) == 10,
    'patched_file_matches_qualified_hash': after_forward == patched_map['model_tools.py'],
    'reverse_steps': reverse, 'reverse_restores_local_edit_exactly': after_reverse == edited_hash,
    'other_files_match_stock_after_reverse': {k: len(v) for k, v in compare(
        {k: v for k, v in file_map(e5).items() if k != 'model_tools.py'},
        {k: v for k, v in stock_map.items() if k != 'model_tools.py'}).items()}}

# 6. E6 wheel-like runtime subset: only setuptools packages and root modules, tests and scripts absent.
e6 = WORK / 'e6-wheel-like'
if e6.exists():
    shutil.rmtree(e6)
e6.mkdir()
for path in stock_map:
    if path.startswith(packages) or ('/' not in path and path.endswith('.py')):
        (e6 / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STOCK / path, e6 / path)
e6b = fresh_copy(e6, 'e6b-wheel-like-runtime-only')
plain = apply_series(e6, HERMES_PATCHES)
filtered = apply_series(e6b, HERMES_PATCHES, extra=('--exclude=tests/*', '--exclude=scripts/*'))
log['results']['E6_wheel_like_layout'] = {
    'note': 'Simulated from pyproject setuptools include list; not an actual built wheel or site-packages tree.',
    'files_in_subset': sum(1 for _ in e6.rglob('*') if _.is_file()),
    'unfiltered_steps': plain, 'runtime_only_steps': filtered,
    'runtime_only_all_applied': all(s['apply_rc'] == 0 for s in filtered) and len(filtered) == 10,
    'runtime_only_matches_qualified_runtime_files': {k: len(v) for k, v in compare(
        {k: v for k, v in file_map(e6b).items() if k in runtime_changed},
        {k: patched_map[k] for k in runtime_changed if k.startswith(packages) or '/' not in k}).items()}}

# 7. E7 reflink copy timing on this filesystem.
started = time.monotonic()
reflink = run(['cp', '-a', '--reflink=always', str(STOCK), str(WORK / 'e7-reflink')], WORK)
reflink_seconds = time.monotonic() - started
started = time.monotonic()
plain_copy = run(['cp', '-a', '--reflink=never', str(STOCK), str(WORK / 'e7-plain')], WORK)
plain_seconds = time.monotonic() - started
log['results']['E7_copy_timing'] = {'filesystem': run(['findmnt', '-T', str(WORK), '-no', 'FSTYPE'], WORK).stdout.strip(),
    'reflink_rc': reflink.returncode, 'reflink_seconds': round(reflink_seconds, 2),
    'plain_rc': plain_copy.returncode, 'plain_seconds': round(plain_seconds, 2),
    'note': 'Single warm-cache run; on-disk sharing not measured.'}

# 8. Compressed sizes of individual components at the builder gzip level (tarfile default 9).
sizes = {}
hermes = EXTRACT / 'hermes'
sizes['hermes_worktree_without_git'] = gz_size(tree_files(hermes), hermes)
sizes['hermes_git_metadata'] = gz_size([p.relative_to(hermes) for p in sorted((hermes / '.git').rglob('*')) if p.is_file()], hermes)
lifeos = EXTRACT / 'lifeos'
sizes['lifeos_worktree_without_git'] = gz_size(tree_files(lifeos), lifeos)
sizes['lifeos_git_metadata'] = gz_size([p.relative_to(lifeos) for p in sorted((lifeos / '.git').rglob('*')) if p.is_file()], lifeos)
for name in ('lifeos_hook_bridge', 'optional', 'tests', 'scripts', 'python-runtime', 'docs'):
    sizes[name] = gz_size(tree_files(EXTRACT / name), EXTRACT / name)
sizes['lifeos_hook_bridge_patches_only'] = gz_size(tree_files(PATCHES), PATCHES)
sizes['stock_hermes_tgz_as_stored'] = (EXTRACT / 'stock-hermes.tgz').stat().st_size
sizes['hermes_overlay_runtime_changed_files'] = gz_size([Path(p) for p in runtime_changed], hermes)
sizes['hermes_overlay_all_changed_files'] = gz_size([Path(p) for p in changed], hermes)
sizes['hermes_patch_series_only'] = gz_size([Path(n) for n in HERMES_PATCHES], PATCHES)
small = [Path(n) for n in ('VERSION', 'README.md', 'CHANGELOG.md', 'DAILY-CANDIDATE.json')]
for name in ('lifeos_hook_bridge', 'optional', 'python-runtime', 'docs', 'scripts'):
    small += [Path(name) / p for p in tree_files(EXTRACT / name)]
sizes['integration_only_no_hermes_lifeos_stock_tests'] = gz_size(small, EXTRACT)
log['results']['compressed_component_bytes_gzip9'] = sizes
log['results']['uncompressed_component_bytes'] = {
    'hermes_worktree_without_git': sum((hermes / p).stat().st_size for p in tree_files(hermes)),
    'lifeos_worktree_without_git': sum((lifeos / p).stat().st_size for p in tree_files(lifeos)),
}
(OUT / 'measure-raw.json').write_text(json.dumps(log, indent=2) + '\n')
print(json.dumps(log['results'], indent=1)[:8000])
