# ABOUTME: Checks native program baseline completion against real immutable archive bytes.
# ABOUTME: Refuses edited programs, unrelated collisions, and changed or redirected archives.
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

from lifeos_hook_bridge import update_plan
from optional.lifeos_release_manager.release_baseline import reviewed_baseline


class ReleaseBaselineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.profile = self.root / 'account/.hermes'
        self.installed = self.root / 'native/.claude'
        self.package = self.root / '0.4.3-aaaaaaaa'
        self.source = self.package / 'lifeos/LifeOS/install'
        self.next_source = self.root / 'next-source'
        self.reference = self.root / 'next-reference'
        self.name = 'LIFEOS/HERMES/LogAnalysis.ts'
        for path in (self.profile, self.installed, self.source, self.next_source, self.reference):
            path.mkdir(parents=True, mode=0o700)
        self.before = b'export const generation = "accepted";\n'
        self.after = b'export const generation = "candidate";\n'
        self.put(self.installed, self.name, self.before)
        self.put(self.next_source, self.name, self.after)
        self.put(self.reference, self.name, self.after)
        for root in (self.installed, self.source, self.next_source, self.reference):
            self.put(root, 'hooks/hooks.json', b'{"hooks":{}}')
        self.baseline = {'installed_root': str(self.installed), 'source_root': str(self.source),
            'files': {'hooks/hooks.json': self.digest(b'{"hooks":{}}')}}
        self.original = json.dumps(self.baseline, sort_keys=True)
        self.archive = Path(str(self.package) + '.tgz')
        self.write_archive([(self.name, self.before, 'file')])
        self.active = {'version': '0.4.3', 'commit': 'a' * 40,
            'package_sha256': self.digest(self.archive.read_bytes()), 'verification': 'verified'}
        (self.profile / 'baseline.json').write_text(self.original)
        self.desired = update_plan.deployed_system_files(self.next_source, self.reference)

    @staticmethod
    def digest(data):
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def put(root, name, data):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def write_archive(self, rows):
        with tarfile.open(self.archive, 'w:gz') as archive:
            for name, data, kind in rows:
                info = tarfile.TarInfo('lifeos/LifeOS/install/' + name)
                info.mode = 0o600
                if kind == 'link':
                    info.type = tarfile.SYMTYPE
                    info.linkname = '/outside'
                    archive.addfile(info)
                else:
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
        self.archive.chmod(0o600)

    def review(self):
        return reviewed_baseline(self.profile, self.baseline, self.installed,
            self.desired, self.active, update_plan)

    def test_accepted_untracked_program_enters_review_without_rewriting_the_baseline(self):
        reviewed = self.review()
        plan = update_plan.plan_system_files(self.installed, reviewed, self.next_source, self.reference)
        self.assertEqual(plan['replace'], [self.name])
        self.assertEqual(reviewed['files'][self.name], self.digest(self.before))
        self.assertEqual(json.dumps(self.baseline, sort_keys=True), self.original)
        self.assertEqual((self.profile / 'baseline.json').read_text(), self.original)
        self.assertEqual((self.installed / self.name).read_bytes(), self.before)

    def test_later_edit_cannot_be_adopted_as_an_accepted_program(self):
        (self.installed / self.name).write_text('later owner edit')
        with self.assertRaises(update_plan.UpdateConflict):
            self.review()
        self.assertEqual((self.installed / self.name).read_text(), 'later owner edit')

    def test_edit_after_review_refuses_the_actual_system_plan(self):
        reviewed = self.review()
        (self.installed / self.name).write_text('edit after review')
        with self.assertRaises(update_plan.UpdateConflict):
            update_plan.plan_system_files(self.installed, reviewed, self.next_source, self.reference)

    def test_unrelated_new_file_collision_has_no_archive_proof(self):
        other = 'LIFEOS/HERMES/Unrelated.ts'
        self.put(self.installed, other, b'owner file')
        self.put(self.next_source, other, b'candidate')
        self.put(self.reference, other, b'candidate')
        self.desired = update_plan.deployed_system_files(self.next_source, self.reference)
        with self.assertRaises(update_plan.UpdateConflict):
            self.review()

    def test_changed_recorded_program_keeps_its_original_refusal(self):
        (self.installed / 'hooks/hooks.json').write_text('later hook edit')
        reviewed = self.review()
        with self.assertRaisesRegex(update_plan.UpdateConflict, 'changed since baseline'):
            update_plan.plan_system_files(self.installed, reviewed, self.next_source, self.reference)

    def test_changed_archive_refuses_before_using_its_program_bytes(self):
        with self.archive.open('ab') as stream:
            stream.write(b'changed accepted archive')
        with self.assertRaises(update_plan.UpdateConflict):
            self.review()

    def test_missing_archive_keeps_the_collision_closed(self):
        self.archive.unlink()
        with self.assertRaises(update_plan.UpdateConflict):
            self.review()

    def test_shared_write_archive_refuses(self):
        self.archive.chmod(0o622)
        with self.assertRaises(update_plan.UpdateConflict):
            self.review()

    def test_archive_alias_refuses(self):
        retained = self.archive.with_name('retained.tgz')
        self.archive.rename(retained)
        self.archive.symlink_to(retained)
        with self.assertRaises(update_plan.UpdateConflict):
            self.review()

    def test_archive_hardlink_refuses(self):
        os.link(self.archive, self.archive.with_name('second-link.tgz'))
        with self.assertRaises(update_plan.UpdateConflict):
            self.review()

    def test_redirected_installed_program_refuses(self):
        target = self.root / 'outside'
        target.write_bytes(self.before)
        (self.installed / self.name).unlink()
        (self.installed / self.name).symlink_to(target)
        with self.assertRaises(update_plan.UpdateConflict):
            self.review()

    def test_duplicate_and_nonregular_archive_programs_refuse(self):
        for rows in ([(self.name, self.before, 'file')] * 2, [(self.name, b'', 'link')]):
            with self.subTest(rows=rows):
                self.write_archive(rows)
                self.active['package_sha256'] = self.digest(self.archive.read_bytes())
                with self.assertRaises(update_plan.UpdateConflict):
                    self.review()

    def test_existing_current_bytes_need_no_additional_proof(self):
        (self.installed / self.name).write_bytes(self.after)
        self.archive.unlink()
        reviewed = self.review()
        self.assertEqual(reviewed, self.baseline)
        self.assertEqual(update_plan.plan_system_files(self.installed, reviewed,
            self.next_source, self.reference)['replace'], [])

    def test_managed_operation_download_supplies_the_accepted_archive(self):
        job = self.profile / '.lifeos-releases' / ('b' * 32)
        package = job / 'package'
        source = package / 'lifeos/LifeOS/install'
        source.mkdir(parents=True)
        download = job / 'download'
        download.mkdir()
        self.archive.rename(download / '0.4.3-aaaaaaaa.tgz')
        self.baseline['source_root'] = str(source)
        self.assertEqual(self.review()['files'][self.name], self.digest(self.before))
