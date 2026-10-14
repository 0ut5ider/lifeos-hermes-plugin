# ABOUTME: Exercises promotion admission and backup recovery using the actual operator statements.
# ABOUTME: Uses local files and child processes without invoking guest services or creating backups.
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
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
results = []


def run_block(nodes, namespace):
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual-operator-statements>', 'exec'), namespace)


def backup_control(failure):
    tree = ast.parse((folder / 'postpromotion_backup.py').read_text())
    block = next(node for node in tree.body if isinstance(node, ast.Try))
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        state = root / 'state'
        calls = []

        def services(action):
            if "assert not s.status()['recovery_required']" in action and 's.resume()' not in action and failure == 'preflight':
                calls.append('preflight')
                raise RuntimeError('Existing recovery state refuses admission')
            if 's.drain(' in action:
                step = 'drain'
                child = "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('stopped'); sys.exit(int(sys.argv[2]))"
                code = 1 if failure == 'drain' else 0
                subprocess.run([sys.executable, '-c', child, str(state), str(code)], check=True,
                    capture_output=True, text=True)
                calls.append(step)
            elif 's.resume()' in action:
                if "if s.status()['recovery_required']" in action and not state.exists():
                    return
                calls.append('resume')
                subprocess.run([sys.executable, '-c',
                    "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('active')", str(state)],
                    check=True, capture_output=True, text=True)
            else:
                calls.append('preflight')
                if failure == 'preflight':
                    raise RuntimeError('Existing recovery state refuses admission')

        def run(command, label):
            if label == 'backup-daily' and failure == 'backup':
                raise RuntimeError('Synthetic backup failure')
            return json.dumps([{'volid': 'PBS-01:backup/ct/102/synthetic', 'ctime': 1, 'size': 1}])

        namespace = {'services': services, 'run': run, 'out': root, 'json': json,
            'operations': [], 'drained': False, 'drain_attempted': False, 'completed': False}
        exception = None
        try:
            run_block([block], namespace)
        except (RuntimeError, subprocess.CalledProcessError) as error:
            exception = type(error).__name__
        observed = state.read_text() if state.exists() else 'unchanged'
        expected = 'unchanged' if failure == 'preflight' else 'active'
        done = (root / 'process.done').read_text().strip()
        passed = observed == expected and done == ('0' if failure is None else '1')
        return {'case': 'backup_' + str(failure), 'passed': passed, 'state': observed,
            'expected_state': expected, 'calls': calls, 'exception': exception, 'process_done': done}


def baseline_control(case):
    tree = ast.parse((folder / 'verify_promotion.py').read_text())
    start = next(index for index, node in enumerate(tree.body) if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'baseline' for target in node.targets)) + 1
    end = next(index for index in range(start, len(tree.body))
        if isinstance(tree.body[index], ast.Expr) and ast.unparse(tree.body[index]).startswith('os.environ.update'))
    admission = tree.body[start:end]
    config_loop = next(node for node in tree.body if isinstance(node, ast.For)
        and ast.unparse(node.iter) == "baseline['configuration_file_sha256'].items()")
    baseline = json.loads((folder / 'development-promotion-baseline.json').read_bytes())
    with tempfile.TemporaryDirectory() as directory:
        profile = Path(directory)
        for name in ('.env', 'lifeos-memory.json'):
            (profile / name).write_bytes(b'synthetic baseline bytes')
            baseline['configuration_file_sha256'][name] = hashlib.sha256((profile / name).read_bytes()).hexdigest()
        if case == 'empty_maps':
            baseline['configuration_file_sha256'] = {}
            baseline['services'] = {}
        elif case == 'missing_config':
            baseline['configuration_file_sha256'].pop('.env')
        elif case == 'missing_service':
            baseline['services'].pop('hermes-dashboard.service')
        elif case == 'bad_digest':
            baseline['configuration_file_sha256']['.env'] = 'not-a-digest'
        elif case == 'bad_model_digest':
            baseline['model_selection_sha256'] = ''
        elif case == 'inactive_service':
            baseline['services']['hermes-dashboard.service']['active'] = False
        elif case == 'wrong_profile':
            baseline['services']['hermes-dashboard.service']['profile'] = '/wrong-profile'
        elif case == 'relative_home':
            baseline['services']['hermes-dashboard.service']['home'] = 'relative'
        elif case == 'changed_config':
            (profile / '.env').write_bytes(b'changed synthetic bytes')
        namespace = {'baseline': baseline, 'args': types.SimpleNamespace(server='development'),
            'profile': Path('/home/lifeos-hermes/.hermes'), 'home': Path('/home/lifeos-hermes'),
            'Path': Path, 'hashlib': hashlib}
        accepted = True
        try:
            run_block(admission, namespace)
            namespace['profile'] = profile
            run_block([config_loop], namespace)
        except (AssertionError, KeyError, TypeError, ValueError):
            accepted = False
        expected = case == 'complete'
        return {'case': 'baseline_' + case, 'passed': accepted == expected,
            'accepted': accepted, 'expected_accept': expected}


results.extend(backup_control(failure) for failure in ('drain', 'backup', 'preflight', None))
results.extend(baseline_control(case) for case in ('empty_maps', 'missing_config', 'missing_service',
    'bad_digest', 'bad_model_digest', 'inactive_service', 'wrong_profile', 'relative_home', 'changed_config', 'complete'))
report = {'status': 'PASS' if all(item['passed'] for item in results) else 'FAIL',
    'scope': 'Local operator controls with actual statement blocks, real child processes, and real temporary files. No guest or backup verification.',
    'results': results}
args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
sys.exit(0 if report['status'] == 'PASS' else 1)
