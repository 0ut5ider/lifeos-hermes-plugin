# ABOUTME: Repeats the independent promotion admission and failed drain controls against reviewed operator source.
# ABOUTME: Uses actual statement blocks with real local files and children, without service or guest operations.
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types

folder = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=folder / 'independent-operator-controls.json')
args = parser.parse_args()
operators = folder.parents[2] / 'docs/verification/2026-10-14-release-0.4.3'
reviewed = json.loads((folder / 'reviewed-state.json').read_text())
for name in ('postpromotion_backup.py', 'verify_promotion.py'):
    assert hashlib.sha256((operators / name).read_bytes()).hexdigest() == reviewed['files'][name], name


def compile_block(nodes, name):
    return compile(ast.Module(body=nodes, type_ignores=[]), str(operators / name), 'exec')


def backup_controls():
    tree = ast.parse((operators / 'postpromotion_backup.py').read_text())
    block = next(node for node in tree.body if isinstance(node, ast.Try))
    code = compile_block([block], 'postpromotion_backup.py')
    results = []
    for case in ('partial-drain', 'preflight-denied', 'drain-before-journal', 'resume-failed'):
        with tempfile.TemporaryDirectory(prefix='pr24-r2-control-', dir='/tmp') as directory:
            root = Path(directory)
            state = root / 'writer-state'
            calls = []
            if case == 'preflight-denied':
                state.write_text('stopped-before-admission')

            def services(action):
                if 's.drain(' in action:
                    calls.append('drain')
                    script = 'import sys;from pathlib import Path;p=Path(sys.argv[1]);'
                    if case != 'drain-before-journal':
                        script += 'p.write_text("stopped");'
                    script += 'sys.exit(1)'
                    subprocess.run([sys.executable, '-B', '-c', script, str(state)],
                        check=True, capture_output=True, text=True)
                elif 's.resume()' in action:
                    calls.append('recovery-check')
                    if state.exists() and state.read_text() == 'stopped':
                        calls.append('resume')
                        script = 'import sys;from pathlib import Path;'
                        script += 'sys.exit(1)' if case == 'resume-failed' else 'Path(sys.argv[1]).write_text("active")'
                        subprocess.run([sys.executable, '-B', '-c', script, str(state)],
                            check=True, capture_output=True, text=True)
                else:
                    calls.append('preflight')
                    if case == 'preflight-denied':
                        raise RuntimeError('Unrelated existing recovery refuses admission')

            def unavailable_backup(*arguments, **keywords):
                raise AssertionError('No backup starts after this fixture failure')

            namespace = {'services': services, 'run': unavailable_backup, 'out': root,
                'drain_attempted': False, 'completed': False}
            try:
                exec(code, namespace)
                error = None
            except Exception as exception:
                error = type(exception).__name__
            observed = state.read_text() if state.exists() else 'unchanged'
            done = (root / 'process.done').read_text().strip()
            expected = {'partial-drain': 'active', 'preflight-denied': 'stopped-before-admission',
                'drain-before-journal': 'unchanged', 'resume-failed': 'stopped'}[case]
            results.append({'case': case, 'passed': observed == expected and done == '1',
                'state': observed, 'expected_state': expected, 'process_done': done,
                'calls': calls, 'exception': error})
    return results


def baseline_controls():
    tree = ast.parse((operators / 'verify_promotion.py').read_text())
    start = next(index for index, node in enumerate(tree.body) if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'baseline' for target in node.targets)) + 1
    end = next(index for index in range(start, len(tree.body)) if isinstance(tree.body[index], ast.Expr)
        and ast.unparse(tree.body[index]).startswith('os.environ.update'))
    admission = compile_block(tree.body[start:end], 'verify_promotion.py')
    loop = next(node for node in tree.body if isinstance(node, ast.For)
        and ast.unparse(node.iter) == "baseline['configuration_file_sha256'].items()")
    digests = compile_block([loop], 'verify_promotion.py')
    names = ('hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service')
    results = []
    for case in ('complete', 'empty-maps', 'missing-credential', 'missing-service',
            'home-outside-account', 'parent-traversal-home', 'changed-config'):
        with tempfile.TemporaryDirectory(prefix='pr24-r2-baseline-', dir='/tmp') as directory:
            profile = Path(directory)
            for name in ('.env', 'lifeos-memory.json'):
                (profile / name).write_bytes(b'synthetic original bytes')
            baseline = {'status': 'PASS', 'server': 'development', 'model_selection_sha256': 'a' * 64,
                'configuration_file_sha256': {name: hashlib.sha256((profile / name).read_bytes()).hexdigest()
                    for name in ('.env', 'lifeos-memory.json')},
                'services': {name: {'active': True, 'profile': '/home/lifeos-hermes/.hermes',
                    'home': '/home/lifeos-hermes/native-home'} for name in names}}
            if case == 'empty-maps':
                baseline['configuration_file_sha256'] = {}
                baseline['services'] = {}
            elif case == 'missing-credential':
                baseline['configuration_file_sha256'].pop('.env')
            elif case == 'missing-service':
                baseline['services'].pop(names[0])
            elif case == 'home-outside-account':
                baseline['services'][names[0]]['home'] = '/tmp/outside'
            elif case == 'parent-traversal-home':
                baseline['services'][names[0]]['home'] = '/home/lifeos-hermes/../outside'
            elif case == 'changed-config':
                (profile / '.env').write_bytes(b'synthetic changed bytes')
            namespace = {'baseline': baseline, 'args': types.SimpleNamespace(server='development'),
                'home': Path('/home/lifeos-hermes'), 'profile': Path('/home/lifeos-hermes/.hermes'),
                'Path': Path, 'hashlib': hashlib}
            try:
                exec(admission, namespace)
                namespace['profile'] = profile
                exec(digests, namespace)
                accepted, error = True, None
            except Exception as exception:
                accepted, error = False, type(exception).__name__
            results.append({'case': case, 'accepted': accepted, 'expected_accept': case == 'complete',
                'passed': accepted == (case == 'complete'), 'exception': error})
    return results


report = {'scope': 'Exact current operator blocks with real local child processes and files; unavailable guest boundaries isolated. No guest/service/backup qualification.',
    'backup_controls': backup_controls(), 'baseline_controls': baseline_controls()}
args.output.write_text(json.dumps(report, indent=2) + '\n')
assert all(row['passed'] for row in report['backup_controls'] + report['baseline_controls'])
print('Independent bounded controls PASS', len(report['backup_controls']) + len(report['baseline_controls']))
