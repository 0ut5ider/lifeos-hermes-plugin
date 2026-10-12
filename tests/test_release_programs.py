# ABOUTME: Tests durable complete-release program publication with actual files.
# ABOUTME: Verifies interruption recovery and refusal to overwrite later owner edits.
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.release_programs import ProgramTransaction, ProgramConflict


class ProgramTransactionTests(unittest.TestCase):
    def test_reviewed_entry_digest_refuses_journal_target_substitution(self):
        import json
        from optional.lifeos_release_manager.release_programs import fingerprint
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            transaction, current, launcher, receipt = self.fixture(root)
            expected = transaction.entries_digest()
            victim = root / 'outside-planned-programs'
            victim.write_text('Synthetic preserve')
            value = json.loads(transaction.journal.read_bytes())
            row = next(entry for entry in value['entries'] if entry['target'] == str(launcher))
            row['target'] = str(victim)
            row['before'] = fingerprint(victim)
            transaction.journal.write_text(json.dumps(value))
            with self.assertRaisesRegex(ProgramConflict, 'reviewed program'):
                ProgramTransaction(transaction.snapshot, expected_entries_sha256=expected).apply()
            self.assertEqual(victim.read_text(), 'Synthetic preserve')
            self.assertEqual((current / 'program.py').read_text(), 'before')

    def fixture(self, root):
        current, incoming = root / 'bridge', root / 'incoming'
        current.mkdir(); incoming.mkdir()
        (current / 'program.py').write_text('before')
        (incoming / 'program.py').write_text('after')
        launcher = root / 'hermes'
        launcher.write_text('before-launcher')
        launcher.chmod(0o700)
        staged = root / 'staged-launcher'
        staged.write_text('after-launcher')
        receipt = root / 'release.json'
        selected = root / 'selected.json'
        selected.write_text('qualified release')
        transaction = ProgramTransaction(root / 'snapshot')
        transaction.prepare(directories={current: incoming}, files={launcher: staged, receipt: selected})
        return transaction, current, launcher, receipt

    def test_complete_publication_and_restore_keep_later_personal_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            transaction, current, launcher, receipt = self.fixture(root)
            private = root / 'personal'
            private.write_text('before')
            transaction.apply()
            self.assertEqual((current / 'program.py').read_text(), 'after')
            self.assertEqual(launcher.read_text(), 'after-launcher')
            private.write_text('later')
            transaction.restore()
            self.assertEqual((current / 'program.py').read_text(), 'before')
            self.assertEqual(launcher.read_text(), 'before-launcher')
            self.assertEqual(launcher.stat().st_mode & 0o777, 0o700)
            self.assertFalse(receipt.exists())
            self.assertEqual(private.read_text(), 'later')

    def test_changed_candidate_refuses_before_any_program_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            transaction, current, launcher, receipt = self.fixture(root)
            (root / 'incoming/program.py').write_text('changed')
            with self.assertRaises(ProgramConflict):
                transaction.apply()
            self.assertEqual((current / 'program.py').read_text(), 'before')
            self.assertEqual(launcher.read_text(), 'before-launcher')
            self.assertFalse(receipt.exists())

    def test_interrupted_directory_swap_recovers_after_actual_process_exit(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            transaction, current, launcher, receipt = self.fixture(root)
            child = os.fork()
            if child == 0:
                def terminate(point):
                    if point == 'directory-retained':
                        os._exit(73)
                transaction.apply(checkpoint=terminate)
                os._exit(74)
            _, status = os.waitpid(child, 0)
            self.assertEqual(os.waitstatus_to_exitcode(status), 73)
            ProgramTransaction(root / 'snapshot').restore()
            self.assertEqual((current / 'program.py').read_text(), 'before')
            self.assertEqual(launcher.read_text(), 'before-launcher')
            self.assertFalse(receipt.exists())

    def test_restore_refuses_later_program_or_launcher_edits_before_any_restore(self):
        for changed in ('program', 'launcher', 'receipt-deletion'):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                transaction, current, launcher, receipt = self.fixture(root)
                transaction.apply()
                path = current / 'program.py' if changed == 'program' else launcher
                if changed == 'receipt-deletion':
                    receipt.unlink()
                else:
                    path.write_text('later edit')
                with self.assertRaises(ProgramConflict):
                    transaction.restore()
                if changed == 'receipt-deletion':
                    self.assertFalse(receipt.exists())
                else:
                    self.assertEqual(path.read_text(), 'later edit')
                    self.assertEqual(receipt.read_text(), 'qualified release')

    def test_directory_links_and_overlapping_targets_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            current, incoming = root / 'bridge', root / 'incoming'
            current.mkdir(); incoming.mkdir()
            (incoming / 'link').symlink_to('/etc/passwd')
            with self.assertRaises(ProgramConflict):
                ProgramTransaction(root / 'snapshot').prepare(directories={current: incoming}, files={})

    def test_removed_system_program_restores_and_refuses_a_later_replacement(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            retired = root / 'retired.py'
            retired.write_text('retained')
            transaction = ProgramTransaction(root / 'snapshot')
            transaction.prepare(directories={}, files={retired: None})
            transaction.apply()
            self.assertFalse(retired.exists())
            retired.write_text('later owner program')
            with self.assertRaises(ProgramConflict):
                transaction.restore()
            self.assertEqual(retired.read_text(), 'later owner program')
            retired.unlink()
            transaction.restore()
            self.assertEqual(retired.read_text(), 'retained')

    def test_dependency_directories_keep_internal_links_but_refuse_external_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            current, incoming = root / 'dependencies', root / 'incoming'
            for folder in (current, incoming):
                (folder / '.bin').mkdir(parents=True)
                (folder / 'program.js').write_text(folder.name)
                (folder / '.bin/program').symlink_to('../program.js')
            transaction = ProgramTransaction(root / 'snapshot')
            transaction.prepare(directories={}, files={}, dependencies={current: incoming})
            transaction.apply()
            self.assertEqual((current / '.bin/program').read_text(), 'incoming')
            transaction.restore()
            self.assertEqual((current / '.bin/program').read_text(), 'dependencies')
            (incoming / '.bin/external').symlink_to('/etc/passwd')
            with self.assertRaises(ProgramConflict):
                ProgramTransaction(root / 'external').prepare(directories={}, files={}, dependencies={current: incoming})
