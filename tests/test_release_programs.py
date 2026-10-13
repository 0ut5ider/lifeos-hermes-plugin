# ABOUTME: Tests durable complete-release program publication with actual files.
# ABOUTME: Verifies interruption recovery and refusal to overwrite later owner edits.
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.release_programs import ProgramTransaction, ProgramConflict


class ProgramTransactionTests(unittest.TestCase):
    def test_apply_preserves_the_inode_of_an_unchanged_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            unchanged, target, source = root / 'unchanged', root / 'target', root / 'source'
            unchanged.write_text('Admitted unchanged definition')
            target.write_text('Prior program')
            source.write_text('Candidate program')
            before = unchanged.stat()
            transaction = ProgramTransaction(root / 'snapshot')
            transaction.prepare(directories={}, files={unchanged: unchanged, target: source})
            transaction.apply()
            self.assertEqual(unchanged.stat().st_ino, before.st_ino)
            self.assertEqual(unchanged.stat().st_mtime_ns, before.st_mtime_ns)
            self.assertEqual(target.read_text(), 'Candidate program')
            transaction.check_applied()
            transaction.restore()
            self.assertEqual(unchanged.stat().st_ino, before.st_ino)
            self.assertEqual(target.read_text(), 'Prior program')

    def test_recovery_refuses_missing_prior_copy_before_journal_or_target_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target, source = root / 'target', root / 'source'
            target.write_text('Prior bytes')
            source.write_text('Candidate bytes')
            transaction = ProgramTransaction(root / 'snapshot')
            transaction.prepare(directories={}, files={target: source})
            transaction.apply()
            prior = transaction.snapshot / 'before-0'
            original = prior.read_bytes()
            prior.unlink()
            journal = transaction.journal.read_bytes()
            with self.assertRaisesRegex(ProgramConflict, 'retained prior artifact'):
                transaction.restore()
            self.assertEqual(transaction.journal.read_bytes(), journal)
            self.assertEqual(target.read_text(), 'Candidate bytes')
            prior.write_bytes(original)
            transaction.restore()
            self.assertEqual(target.read_text(), 'Prior bytes')

    def test_applied_preflight_checks_native_overrides_and_retained_programs(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            program, config, source = root / 'program', root / 'config', root / 'source'
            program.write_text('Prior program')
            config.write_text('Prior config')
            source.write_text('Candidate bytes')
            transaction = ProgramTransaction(root / 'snapshot')
            transaction.prepare(directories={}, files={program: source, config: source})
            transaction.apply()
            transaction.check_applied()
            config.write_text('Native mounted config')
            override = {str(config): {'type': 'file', 'mode': config.stat().st_mode & 0o777,
                                     'sha256': hashlib.sha256(config.read_bytes()).hexdigest()}}
            with self.assertRaises(ProgramConflict):
                transaction.check_applied()
            transaction.check_applied(overrides=override)
            transaction.check_recovery(overrides=override)
            program.write_text('Later program edit')
            with self.assertRaises(ProgramConflict):
                transaction.check_applied(overrides=override)
            self.assertEqual(program.read_text(), 'Later program edit')
            program.write_text(source.read_text())
            (transaction.snapshot / 'before-0').write_text('Changed retained program')
            with self.assertRaises(ProgramConflict):
                transaction.check_applied(overrides=override)

    def test_candidate_plan_refuses_missing_or_substituted_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.write_text('Qualified candidate command')
            first, second = root / 'hermes', root / 'hermes-agent'
            transaction = ProgramTransaction(root / 'snapshot')
            transaction.prepare(directories={}, files={first: source})
            with self.assertRaisesRegex(ProgramConflict, 'candidate program plan'):
                transaction.check_plan(directories={}, files={first: source, second: source})
            replacement = root / 'replacement'
            replacement.write_text(source.read_text())
            with self.assertRaisesRegex(ProgramConflict, 'candidate program plan'):
                transaction.check_plan(directories={}, files={first: replacement})
            transaction.check_plan(directories={}, files={first: source, root / 'absent': None})

    def test_resume_completes_an_interrupted_directory_swap_and_keeps_personal_data(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            transaction, current, launcher, receipt = self.fixture(root)
            personal = root / 'personal'
            personal.write_text('Synthetic retained data')
            child = os.fork()
            if child == 0:
                def terminate(point):
                    if point == 'directory-retained':
                        os._exit(73)
                transaction.apply(checkpoint=terminate)
                os._exit(74)
            _, result = os.waitpid(child, 0)
            self.assertEqual(os.waitstatus_to_exitcode(result), 73)
            transaction.resume()
            self.assertEqual((current / 'program.py').read_text(), 'after')
            self.assertEqual(launcher.read_text(), 'after-launcher')
            self.assertEqual(receipt.read_text(), 'qualified release')
            self.assertEqual(personal.read_text(), 'Synthetic retained data')
            transaction.restore()
            self.assertEqual((current / 'program.py').read_text(), 'before')

    def test_resume_refuses_later_edits_before_publishing_other_programs(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            transaction, current, launcher, receipt = self.fixture(root)
            child = os.fork()
            if child == 0:
                transaction.apply(checkpoint=lambda point: os._exit(73) if point == 'artifact-published' else None)
                os._exit(74)
            _, result = os.waitpid(child, 0)
            self.assertEqual(os.waitstatus_to_exitcode(result), 73)
            (current / 'program.py').write_text('later owner edit')
            with self.assertRaisesRegex(ProgramConflict, 'later artifact edit'):
                transaction.resume()
            self.assertEqual((current / 'program.py').read_text(), 'later owner edit')
            self.assertEqual(launcher.read_text(), 'before-launcher')
            self.assertFalse(receipt.exists())

    def test_preparation_retries_after_process_exit_and_retains_partial_copy(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            current, incoming = root / 'bridge', root / 'incoming'
            current.mkdir(); incoming.mkdir()
            (current / 'program.py').write_text('before')
            (incoming / 'program.py').write_text('after')
            snapshot = root / 'snapshot'
            child = os.fork()
            if child == 0:
                def terminate(point):
                    if point == 'artifact-staged':
                        os._exit(73)
                ProgramTransaction(snapshot).prepare(directories={current: incoming}, files={}, checkpoint=terminate)
                os._exit(74)
            _, result = os.waitpid(child, 0)
            self.assertEqual(os.waitstatus_to_exitcode(result), 73)
            self.assertFalse((snapshot / 'programs.json').exists())
            transaction = ProgramTransaction(snapshot)
            transaction.prepare(directories={current: incoming}, files={})
            transaction.check_prepared()
            retained = list(root.glob('snapshot-incomplete-*'))
            self.assertEqual(len(retained), 1)
            self.assertEqual((retained[0] / 'incoming-0/program.py').read_text(), 'after')
            self.assertEqual((current / 'program.py').read_text(), 'before')

    def test_preparation_preserves_a_sealed_or_untrusted_snapshot(self):
        for state in ('sealed', 'linked', 'shared'):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                snapshot = root / 'snapshot'
                if state == 'linked':
                    (root / 'retained').mkdir(mode=0o700)
                    snapshot.symlink_to(root / 'retained')
                else:
                    snapshot.mkdir(mode=0o700 if state == 'sealed' else 0o755)
                    (snapshot / 'keep.txt').write_text('preserve')
                expected = 'a' * 64 if state == 'sealed' else None
                with self.assertRaises(ProgramConflict):
                    ProgramTransaction(snapshot, expected_entries_sha256=expected).prepare(directories={}, files={})
                self.assertFalse(list(root.glob('snapshot-incomplete-*')))

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
