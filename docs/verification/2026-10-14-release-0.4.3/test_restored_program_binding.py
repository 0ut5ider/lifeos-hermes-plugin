# ABOUTME: Exercises the restore verifier with real sealed plans and synthetic program journals.
# ABOUTME: Refuses changed entry lists and changed retained artifacts without guest or personal data.
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.release_operation import validate_plan
from optional.lifeos_release_manager.release_programs import ProgramConflict, ProgramTransaction, fingerprint


class RestoredProgramBinding(unittest.TestCase):
    def verify(self, mutation):
        script = Path(__file__).with_name('verify_restored_programs.py')
        tree = ast.parse(script.read_text())
        begin = next(i for i, node in enumerate(tree.body)
                     if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == 'plan')
        end = next(i for i, node in enumerate(tree.body)
                   if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == 'units')
        block = compile(ast.Module(body=tree.body[begin:end], type_ignores=[]), str(script), 'exec')
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory)
            snapshot = job / 'program-snapshot'
            snapshot.mkdir(mode=0o700)
            target = job / 'selected-program'
            target.write_text('qualified program')
            target.chmod(0o600)
            before = snapshot / 'before-0'
            before.write_text('prior program')
            before.chmod(0o600)
            entries = [{'target': str(target), 'source': str(target), 'kind': 'file',
                        'allow_links': False, 'before': fingerprint(before), 'after': fingerprint(target)}]
            plan_path = job / 'plan.json'
            plan_path.write_text(json.dumps({'native_mount_required': False,
                'program_entries_sha256': ProgramTransaction._entries_digest(entries)}))
            plan_path.chmod(0o600)
            request = {'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest()}
            if mutation == 'empty':
                entries = []
            elif mutation == 'substituted':
                substitute = job / 'substitute'
                substitute.write_text('qualified program')
                substitute.chmod(0o600)
                entries[0]['target'] = str(substitute)
            elif mutation == 'retained':
                before.write_text('changed prior program')
            journal = snapshot / 'programs.json'
            journal.write_text(json.dumps({'format': 1, 'state': 'applied', 'entries': entries}))
            journal.chmod(0o600)
            exec(block, {'job': job, 'request': request, 'json': json, 'Path': Path,
                         'validate_plan': validate_plan, 'fingerprint': fingerprint,
                         'ProgramTransaction': ProgramTransaction})

    def test_current_sealed_programs_pass(self):
        self.verify(None)

    def test_empty_entries_refused(self):
        with self.assertRaisesRegex(ProgramConflict, 'reviewed program entries change'):
            self.verify('empty')

    def test_substituted_target_refused(self):
        with self.assertRaisesRegex(ProgramConflict, 'reviewed program entries change'):
            self.verify('substituted')

    def test_changed_retained_program_refused(self):
        with self.assertRaisesRegex(ProgramConflict, 'retained program differs'):
            self.verify('retained')


if __name__ == '__main__':
    unittest.main(verbosity=2)
