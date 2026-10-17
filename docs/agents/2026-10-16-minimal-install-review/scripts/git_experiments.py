# ABOUTME: Tests Git worktree overlays and stash-based update interaction against disposable Hermes clones.
# ABOUTME: Simulates Git behavior only; it does not run the Hermes updater or contact any network service.
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

CLEAN, PATCHES, WORK, OUT = map(Path, sys.argv[1:5])
BASE = '71d34bad1045610252eda02ee79549436896e784'
SERIES = ['hermes-plugin-events.patch', 'hermes-turn-gates.patch', 'hermes-command-policy.patch',
    'hermes-session-lifecycle.patch', 'hermes-child-routing.patch', 'hermes-strict-inference.patch',
    'hermes-remote-files.patch', 'hermes-cron-bootstrap.patch', 'hermes-required-middleware.patch',
    'hermes-web-result-status.patch']
log = {'commands': [], 'results': {}}
GIT = ['git', '-c', 'user.name=review', '-c', 'user.email=review@example.invalid', '-c', 'commit.gpgsign=false']


def run(args, cwd):
    started = time.monotonic()
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    log['commands'].append({'cwd': str(cwd), 'args': [str(a) for a in args], 'rc': result.returncode,
        'seconds': round(time.monotonic() - started, 3), 'stderr': result.stderr[-1200:], 'stdout': result.stdout[-600:]})
    return result


def clone(name):
    target = WORK / name
    if target.exists():
        shutil.rmtree(target)
    run(['git', 'clone', '-q', '--no-checkout', str(CLEAN), str(target)], WORK)
    run(['git', 'checkout', '-q', '--detach', BASE], target)
    return target


# E8: a detached worktree at the base commit plus the patch series, leaving the primary checkout clean.
primary = clone('e8-primary')
started = time.monotonic()
worktree = WORK / 'e8-overlay'
if worktree.exists():
    shutil.rmtree(worktree)
added = run(['git', 'worktree', 'add', '--detach', str(worktree), BASE], primary)
worktree_seconds = time.monotonic() - started
applied = [run(['git', 'apply', str(PATCHES / name)], worktree).returncode for name in SERIES]
log['results']['E8_worktree_overlay'] = {'worktree_rc': added.returncode, 'worktree_seconds': round(worktree_seconds, 2),
    'apply_rcs': applied,
    'primary_status_lines_after': len(run(['git', 'status', '--porcelain'], primary).stdout.splitlines()),
    'overlay_status_lines_after': len(run(['git', 'status', '--porcelain'], worktree).stdout.splitlines()),
    'note': 'Worktree shares the object store with the primary checkout; a primary gc or deletion affects it.'}

# E9a: autostash round trip with no upstream change.
same = clone('e9a-autostash-same-base')
for name in SERIES:
    run(['git', 'apply', str(PATCHES / name)], same)
before = run(['git', 'status', '--porcelain'], same).stdout + run(['git', 'diff', 'HEAD'], same).stdout
stash = run([*GIT, 'stash', 'push', '--include-untracked', '-m', 'hermes-update-autostash-simulated'], same)
clean_after_stash = run(['git', 'status', '--porcelain'], same).stdout == ''
pop = run([*GIT, 'stash', 'apply'], same)
after = run(['git', 'status', '--porcelain'], same).stdout + run(['git', 'diff', 'HEAD'], same).stdout
log['results']['E9a_autostash_same_base'] = {'stash_rc': stash.returncode, 'clean_after_stash': clean_after_stash,
    'apply_rc': pop.returncode, 'patch_diff_identical_after_restore': before == after}

# E9b: upstream commit that edits a line adjacent to a patched hunk, then stash apply onto it.
moved = clone('e9b-autostash-upstream-adjacent')
plugins = moved / 'hermes_cli/plugins.py'
text = plugins.read_text()
marker = 'VALID_HOOKS: set[str] = {\n'
plugins.write_text(text.replace(marker, marker + '    "upstream_new_hook",\n', 1))
run([*GIT, 'commit', '-q', '-am', 'simulated upstream change'], moved)
upstream = run(['git', 'rev-parse', 'HEAD'], moved).stdout.strip()
run(['git', 'checkout', '-q', '--detach', BASE], moved)
for name in SERIES:
    run(['git', 'apply', str(PATCHES / name)], moved)
run([*GIT, 'stash', 'push', '--include-untracked', '-m', 'hermes-update-autostash-simulated'], moved)
run(['git', 'checkout', '-q', '--detach', upstream], moved)
conflict = run([*GIT, 'stash', 'apply'], moved)
unmerged = run(['git', 'diff', '--name-only', '--diff-filter=U'], moved).stdout.split()
log['results']['E9b_autostash_upstream_adjacent'] = {'apply_rc': conflict.returncode, 'unmerged_paths': unmerged,
    'note': 'A three-way merge combines the adjacent upstream line with the patch without a conflict.'}

# E9d: upstream commit that edits a line the patch also replaces, then stash apply onto it.
overlap = clone('e9d-autostash-upstream-overlap')
plugins = overlap / 'hermes_cli/plugins.py'
text = plugins.read_text()
line = 'from hermes_cli.middleware import VALID_MIDDLEWARE\n'
plugins.write_text(text.replace(line, 'from hermes_cli.middleware import VALID_MIDDLEWARE  # upstream\n', 1))
run([*GIT, 'commit', '-q', '-am', 'simulated overlapping upstream change'], overlap)
upstream = run(['git', 'rev-parse', 'HEAD'], overlap).stdout.strip()
run(['git', 'checkout', '-q', '--detach', BASE], overlap)
for name in SERIES:
    run(['git', 'apply', str(PATCHES / name)], overlap)
run([*GIT, 'stash', 'push', '--include-untracked', '-m', 'hermes-update-autostash-simulated'], overlap)
run(['git', 'checkout', '-q', '--detach', upstream], overlap)
clash = run([*GIT, 'stash', 'apply'], overlap)
log['results']['E9d_autostash_upstream_overlap'] = {'apply_rc': clash.returncode,
    'unmerged_paths': run(['git', 'diff', '--name-only', '--diff-filter=U'], overlap).stdout.split(),
    'note': 'Hermes update resets the tree to clean upstream and parks the stash on a conflicted restore '
            '(stock hermes_cli/update_cmd_stash.py lines 450-496).'}

# E9c: upstream commit outside every patched file, then stash apply: patches silently carry onto an untested base.
quiet = clone('e9c-autostash-upstream-clean')
(quiet / 'README.md').write_text((quiet / 'README.md').read_text() + '\nsimulated upstream line\n')
run([*GIT, 'commit', '-q', '-am', 'simulated unrelated upstream change'], quiet)
upstream = run(['git', 'rev-parse', 'HEAD'], quiet).stdout.strip()
run(['git', 'checkout', '-q', '--detach', BASE], quiet)
for name in SERIES:
    run(['git', 'apply', str(PATCHES / name)], quiet)
run([*GIT, 'stash', 'push', '--include-untracked', '-m', 'hermes-update-autostash-simulated'], quiet)
run(['git', 'checkout', '-q', '--detach', upstream], quiet)
carried = run([*GIT, 'stash', 'apply'], quiet)
log['results']['E9c_autostash_upstream_clean'] = {'apply_rc': carried.returncode,
    'head_is_base': run(['git', 'rev-parse', 'HEAD'], quiet).stdout.strip() == BASE,
    'patched_files_present': len(run(['git', 'status', '--porcelain'], quiet).stdout.splitlines()),
    'note': 'The patched files are restored on a commit that differs from the qualified base.'}

(OUT / 'git-experiments-raw.json').write_text(json.dumps(log, indent=2) + '\n')
print(json.dumps(log['results'], indent=1))
