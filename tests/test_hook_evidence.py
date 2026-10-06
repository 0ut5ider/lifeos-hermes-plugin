# ABOUTME: Prevents registration evidence from claiming effects that were not compared.
# ABOUTME: Checks complete inventory, equal paired outcomes, and retained artifact hashes.
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_hook_evidence import check_evidence


class HookEvidenceTests(unittest.TestCase):
    def fixture(self, root):
        inventory = root / 'registrations.csv'
        inventory.write_text('id,event,handler\nStopFailure.1.1,StopFailure,logger\n')
        raw = root / 'result.json'
        raw.write_text('{"synthetic":true}\n')
        ledger = root / 'effects.json'
        document = {'registrations_sha256': hashlib.sha256(inventory.read_bytes()).hexdigest(),
                    'complete': False, 'artifacts': {'result.json': hashlib.sha256(raw.read_bytes()).hexdigest()},
                    'registrations': [{'id': 'StopFailure.1.1', 'expected_effect': 'Record terminal API failure.',
                                       'effect_status': 'unverified', 'paired_cases': []}]}
        ledger.write_text(json.dumps(document))
        return inventory, ledger, document

    def test_incomplete_inventory_cannot_pass_completion_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory, ledger, document = self.fixture(root)
            self.assertEqual(check_evidence(inventory, ledger, root), [])
            errors = check_evidence(inventory, ledger, root, require_complete=True)
            self.assertIn('unverified effects: StopFailure.1.1', errors)
            document['registrations'] = []
            ledger.write_text(json.dumps(document))
            self.assertIn('missing evidence: StopFailure.1.1', check_evidence(inventory, ledger, root))

    def test_paired_effect_claim_requires_equal_recorded_sides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory, ledger, document = self.fixture(root)
            row = document['registrations'][0]
            row['effect_status'] = 'paired_case_verified'
            row['paired_cases'] = [{'id': 'failure', 'artifacts': ['result.json'],
                                    'native': {'error': 'authentication_failed'},
                                    'hermes': {'error': 'unknown'}}]
            ledger.write_text(json.dumps(document))
            self.assertIn('unequal paired case: StopFailure.1.1/failure', check_evidence(inventory, ledger, root))
            row['paired_cases'][0]['hermes'] = row['paired_cases'][0]['native']
            ledger.write_text(json.dumps(document))
            self.assertEqual(check_evidence(inventory, ledger, root), [])
            (root / 'result.json').write_text('changed')
            self.assertIn('changed artifact: result.json', check_evidence(inventory, ledger, root))

    def test_partial_case_cannot_be_presented_as_complete_handler_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory, ledger, document = self.fixture(root)
            document['complete'] = True
            document['registrations'][0]['effect_status'] = 'paired_case_verified'
            ledger.write_text(json.dumps(document))
            errors = check_evidence(inventory, ledger, root)
            self.assertIn('complete claim includes partial effects: StopFailure.1.1', errors)
            self.assertIn('paired case is missing: StopFailure.1.1', errors)

    def lifecycle_fixture(self, root):
        inventory, ledger, document = self.fixture(root)
        inventory.write_text('id,event,handler\nSessionEnd.1.3,SessionEnd,counts\n')
        document['registrations_sha256'] = hashlib.sha256(inventory.read_bytes()).hexdigest()
        side = {'before': {'credentials_present': False},
                'after': {'credentials_present': False, 'usage_cache_present': False},
                'hook_exit_codes': [0], 'event': 'SessionEnd', 'cli_exit_code': 0,
                'model_generation_requests': 0}
        result = {'id': 'update-counts-no-oauth', 'registrations': ['SessionEnd.1.3'],
                  'native': side, 'hermes': dict(side)}
        row = document['registrations'][0]
        row.update(id='SessionEnd.1.3', effect_status='paired_case_verified', paired_cases=[{
            'id': result['id'], 'kind': 'paired_lifecycle', 'result_artifact': 'result.json',
            'artifacts': ['result.json'], 'native': side, 'hermes': dict(side)}])
        return inventory, ledger, document, result

    def save_lifecycle(self, root, ledger, document, result):
        raw = root / 'result.json'
        raw.write_text(json.dumps({'cases': [result]}))
        document['artifacts']['result.json'] = hashlib.sha256(raw.read_bytes()).hexdigest()
        ledger.write_text(json.dumps(document))

    def test_lifecycle_assertions_reject_equal_but_invalid_retained_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory, ledger, document, result = self.lifecycle_fixture(root)
            self.save_lifecycle(root, ledger, document, result)
            self.assertEqual(check_evidence(inventory, ledger, root), [])
            result['native']['model_generation_requests'] = 1
            result['hermes']['model_generation_requests'] = 1
            self.save_lifecycle(root, ledger, document, result)
            self.assertTrue(any('model generation was attempted' in error for error in
                                check_evidence(inventory, ledger, root)))

    def test_lifecycle_case_must_cover_the_registration_and_match_ledger_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory, ledger, document, result = self.lifecycle_fixture(root)
            result['registrations'] = ['SessionEnd.1.2']
            result['native'] = {**result['native'], 'cli_exit_code': 1}
            self.save_lifecycle(root, ledger, document, result)
            errors = check_evidence(inventory, ledger, root)
            self.assertTrue(any('does not cover registration' in error for error in errors))
            self.assertTrue(any('ledger outcome differs' in error for error in errors))


class TrackedEvidenceTests(unittest.TestCase):
    def test_every_ledger_artifact_is_tracked_by_git(self):
        import json
        import subprocess
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        if not (root / '.git').exists():
            self.skipTest('A Git checkout is required')
        tracked = set(subprocess.run(['git', 'ls-files', '-z'], cwd=root, check=True,
                                     capture_output=True, text=True).stdout.split('\0'))
        ledger = json.loads((root / 'docs/parity/handler-effects.json').read_text())
        self.assertEqual(sorted(name for name in ledger['artifacts'] if name not in tracked), [])


class ModelChosenCallTests(unittest.TestCase):
    def test_only_model_chosen_call_counts_may_differ_between_sides(self):
        from scripts.check_hook_evidence import comparable
        side = {'after': {'ok': True}, 'hook_exit_codes': [0], 'event': 'PostToolUse',
                'model_generation_requests': 2, 'model_successful_responses': 2}
        other = {**side, 'model_generation_requests': 3, 'model_successful_responses': 3}
        self.assertEqual(comparable('knowledge-index-file', side), comparable('knowledge-index-file', other))
        self.assertNotEqual(comparable('version-drift-count', side), comparable('version-drift-count', other))
        changed = {**other, 'after': {'ok': False}}
        self.assertNotEqual(comparable('knowledge-index-file', side), comparable('knowledge-index-file', changed))
