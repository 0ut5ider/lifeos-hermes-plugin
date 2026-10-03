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
