# ABOUTME: Prevents partial or changed scenario evidence from passing Step 1 completion.
# ABOUTME: Checks registration scope, retained hashes, duplicate identities, and release separation.
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_hook_evidence import check_acceptance


class Step1AcceptanceTests(unittest.TestCase):
    def fixture(self, root):
        inventory = root / 'registrations.csv'
        inventory.write_text('id,event,handler\nStopFailure.1.1,StopFailure,logger\n')
        result = root / 'result.txt'
        result.write_text('Actual retained control result\n')
        ledger = root / 'effects.json'
        ledger.write_text(json.dumps({'artifacts': {'result.txt': hashlib.sha256(result.read_bytes()).hexdigest()}}))
        acceptance = root / 'acceptance.json'
        document = {'complete': False,
                    'registration_inventory_sha256': hashlib.sha256(inventory.read_bytes()).hexdigest(),
                    'requirements': [{'id': 'failures', 'package': 4, 'registrations': ['StopFailure.1.1'],
                                      'status': 'in_progress', 'release_acceptance': False,
                                      'scenarios': [{'id': 'failures-01', 'expected': 'Publish the actual error.',
                                                     'status': 'unverified', 'evidence': []}]}]}
        return inventory, ledger, acceptance, document

    def check(self, root, document, complete=False):
        inventory, ledger, acceptance, _ = self.fixture(root)
        acceptance.write_text(json.dumps(document))
        return check_acceptance(inventory, ledger, acceptance, root, require_complete=complete)

    def test_partial_progress_is_valid_but_cannot_pass_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            *_, document = self.fixture(root)
            self.assertEqual(self.check(root, document), [])
            self.assertIn('unverified acceptance: failures-01', self.check(root, document, True))
            document['complete'] = True
            self.assertIn('complete acceptance includes partial scenario: failures-01', self.check(root, document))

    def test_verified_evidence_requires_retained_unchanged_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            *_, document = self.fixture(root)
            group = document['requirements'][0]
            group['status'] = 'verified'
            scenario = group['scenarios'][0]
            scenario.update(status='verified', evidence=['result.txt'])
            self.assertEqual(self.check(root, document, True), [])
            inventory, ledger, acceptance, _ = self.fixture(root)
            acceptance.write_text(json.dumps(document))
            (root / 'result.txt').write_text('Changed result\n')
            self.assertIn('changed acceptance artifact: result.txt',
                          check_acceptance(inventory, ledger, acceptance, root))
            scenario['evidence'] = ['../outside.txt']
            self.assertTrue(any('not retained' in error for error in self.check(root, document)))

    def test_duplicate_ids_and_unregistered_or_missing_scope_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            *_, document = self.fixture(root)
            document['requirements'].append(copy.deepcopy(document['requirements'][0]))
            errors = self.check(root, document)
            self.assertIn('duplicate acceptance group: failures', errors)
            self.assertIn('duplicate acceptance scenario: failures-01', errors)
            document['requirements'][0]['registrations'] = ['StopFailure.9.1']
            document['requirements'].pop()
            errors = self.check(root, document)
            self.assertIn('unregistered acceptance scope: StopFailure.9.1', errors)
            self.assertIn('missing acceptance scope: StopFailure.1.1', errors)

    def test_verified_group_cannot_hide_unverified_scenarios(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            *_, document = self.fixture(root)
            document['requirements'][0]['status'] = 'verified'
            self.assertIn('verified group includes partial scenario: failures', self.check(root, document))

    def test_combined_release_scenario_remains_an_explicit_separate_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            *_, document = self.fixture(root)
            document['requirements'][0]['release_acceptance'] = True
            self.assertEqual(self.check(root, document, True), [])
            inventory, ledger, acceptance, _ = self.fixture(root)
            acceptance.write_text(json.dumps(document))
            self.assertIn('unverified release acceptance: failures-01', check_acceptance(
                inventory, ledger, acceptance, root, require_complete=True, require_release=True))
