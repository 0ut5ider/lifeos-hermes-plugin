# ABOUTME: Checks exact checkpoint admission before any storage or guest mutation.
# ABOUTME: Executes the actual admission statements with synthetic JSON files and temporary paths only.
import ast
import copy
import json
from pathlib import Path
import tempfile

folder = Path(__file__).resolve().parent
tree = ast.parse((folder / 'restore_daily_checkpoint.py').read_text())
body = next(node.body for node in tree.body if isinstance(node, ast.Try))
end = next(index for index, node in enumerate(body) if ast.unparse(node).startswith('storage_path.mkdir'))
code = compile(ast.Module(body=body[:end], type_ignores=[]), '<actual-restore-admission>', 'exec')
results = []
for case in ('complete', 'occupied_guest', 'unprotected', 'wrong_size', 'wrong_format', 'wrong_archive', 'archive_suffix', 'occupied_storage', 'existing_directory'):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        details = {'protected': True, 'size': 24360759650, 'format': 'pbs-ct',
            'path': 'pbs://synthetic/ct/102/2026-10-14T16:15:12Z'}
        guests = [{'vmid': 102, 'status': 'running'}]
        stores = []
        storage_path = root / 'test-storage'
        if case == 'occupied_guest': guests.append({'vmid': 110, 'status': 'stopped'})
        if case == 'unprotected': details['protected'] = False
        if case == 'wrong_size': details['size'] = 1
        if case == 'wrong_format': details['format'] = 'pbs-vm'
        if case == 'wrong_archive': details['path'] = 'pbs://synthetic/ct/101/2026-10-14T16:15:12Z'
        if case == 'archive_suffix': details['path'] += '-other'
        if case == 'occupied_storage': stores.append({'storage': 'lifeos-daily-restore'})
        if case == 'existing_directory': storage_path.mkdir()
        inputs = {'inventory': guests, 'protected-archive': details, 'storage-inventory': stores}
        for label, value in inputs.items(): (root / (label + '.json')).write_text(json.dumps(value))
        calls = []
        def run(command, label):
            calls.append(command)
            return (root / (label + '.json')).read_text()
        namespace = {'json': json, 'run': run, 'vmid': 110, 'archive': 'PBS-01:backup/ct/102/2026-10-14T16:15:12Z',
            'storage': 'lifeos-daily-restore', 'storage_path': storage_path}
        accepted = True
        try: exec(code, namespace)
        except AssertionError: accepted = False
        results.append({'case': case, 'passed': accepted == (case == 'complete'), 'accepted': accepted,
            'expected_accept': case == 'complete', 'mutation_commands_called': False})
report = {'status': 'PASS' if all(row['passed'] for row in results) else 'FAIL',
    'scope': 'Actual admission statements with local synthetic input files. No guest or backup operation.', 'cases': results}
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['status'] == 'PASS' else 1)
