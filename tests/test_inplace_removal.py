# ABOUTME: Checks in-place removal planning against disposable real Git checkouts and retained originals.
# ABOUTME: Publishes and restores the plan with the real program transaction and requires a clean checkout.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from optional.lifeos_release_manager.release_catalog import ReleaseRejected
from optional.lifeos_release_manager.release_programs import ProgramConflict, ProgramTransaction, publish


STOCK = "VALID_HOOKS = {'pre_tool_call'}\n"
PATCHED = "VALID_HOOKS = {'pre_tool_call', 'pre_turn_stop'}\n"
STOCK_TOOL = "#!/bin/sh\necho stock\n"
PATCHED_TOOL = "#!/bin/sh\necho patched\n"
ADDED = "ENABLED = True\n"


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, check=True, text=True, capture_output=True).stdout


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


class InplaceRemovalPlanTests(unittest.TestCase):
    def setUp(self):
        from optional.lifeos_release_manager.host_compatibility import load_manifest
        from optional.lifeos_release_manager.host_record import build_record, originals_path, record_path
        from optional.lifeos_release_manager.inplace_plan import HOLD
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.home = Path(self.folder.name)
        self.profile = self.home / '.hermes'
        self.profile.mkdir(mode=0o700)
        self.source = self.profile / 'hermes-agent'
        self.source.mkdir(mode=0o755)
        self.source.chmod(0o755)
        git('init', '-q', '-b', 'main', cwd=self.source)
        (self.source / 'hermes_cli').mkdir()
        (self.source / 'hermes_cli/__init__.py').write_text('')
        (self.source / 'hermes_cli/plugins.py').write_text(STOCK)
        (self.source / 'scripts').mkdir()
        (self.source / 'scripts/tool.sh').write_text(STOCK_TOOL)
        (self.source / 'scripts/tool.sh').chmod(0o755)
        (self.source / 'run_agent.py').write_text('')
        (self.source / 'pyproject.toml').write_text("[project]\nname = 'hermes-agent'\n")
        git('add', '.', cwd=self.source)
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'base', cwd=self.source)
        commit = git('rev-parse', 'HEAD', cwd=self.source).strip()
        self.manifest = load_manifest({'format': 1, 'dependencies': [], 'hermes': [{
            'label': 'v0.0.1', 'commit': commit, 'patches': [{'name': 'host.patch', 'sha256': 'e' * 64}],
            'files': {'hermes_cli/plugins.py': {'stock': digest(STOCK), 'patched': digest(PATCHED)},
                      'scripts/tool.sh': {'stock': digest(STOCK_TOOL), 'patched': digest(PATCHED_TOOL)},
                      'hermes_cli/new_hook.py': {'stock': None, 'patched': digest(ADDED)}}}]})
        self.record = build_record(self.profile, self.source, self.manifest['hermes'][0], operation='a' * 32,
                                   version='0.8.0')
        retained = originals_path(self.profile)
        for relative, mode in (('hermes_cli/plugins.py', 0o644), ('scripts/tool.sh', 0o755)):
            copy = retained / relative
            copy.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            publish(copy, (self.source / relative).read_bytes(), mode)
        (self.source / 'hermes_cli/plugins.py').write_text(PATCHED)
        (self.source / 'scripts/tool.sh').write_text(PATCHED_TOOL)
        (self.source / 'hermes_cli/new_hook.py').write_text(ADDED)
        publish(record_path(self.profile), json.dumps(self.record).encode())
        self.hold = self.source / '.git' / HOLD
        self.hold.parent.mkdir()
        publish(self.hold, json.dumps({'holder': 'LifeOS', 'message': 'Remove LifeOS first.'}).encode())
        self.stage = self.home / 'stage'
        self.stage.mkdir(mode=0o700)

    def originals(self):
        from optional.lifeos_release_manager.inplace_removal import installed_host
        return installed_host(self.profile, self.record, self.manifest)

    def plan(self):
        from optional.lifeos_release_manager.inplace_removal import host_plan
        return host_plan(self.profile, self.record, self.originals(), self.stage)

    def prepared(self):
        directories, files, expected = self.plan()
        programs = ProgramTransaction(self.stage / 'programs')
        programs.prepare(directories=directories, files=files, expected_before=expected)
        return programs

    def test_installed_host_returns_the_verified_originals(self):
        originals = self.originals()
        self.assertEqual(sorted(originals), ['hermes_cli/plugins.py', 'scripts/tool.sh'])

    def test_later_target_edit_refuses_admission_with_its_path(self):
        (self.source / 'hermes_cli/plugins.py').write_text(PATCHED + '# owner edit\n')
        with self.assertRaisesRegex(ReleaseRejected, 'hermes_cli/plugins.py'):
            self.originals()

    def test_changed_retained_original_refuses_with_its_path(self):
        from optional.lifeos_release_manager.host_record import originals_path
        publish(originals_path(self.profile) / 'scripts/tool.sh', b'#!/bin/sh\necho changed\n', 0o755)
        with self.assertRaisesRegex(ReleaseRejected, 'scripts/tool.sh'):
            self.originals()

    def test_publication_restores_original_files_and_modes_and_restore_returns_the_patches(self):
        from optional.lifeos_release_manager.host_record import originals_path, record_path
        programs = self.prepared()
        programs.apply()
        self.assertEqual(git('status', '--porcelain', '--untracked-files=all', cwd=self.source), '')
        self.assertEqual((self.source / 'scripts/tool.sh').stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.source / 'hermes_cli/plugins.py').stat().st_mode & 0o777, 0o644)
        self.assertFalse((self.source / 'hermes_cli/new_hook.py').exists())
        self.assertFalse(self.hold.exists())
        self.assertFalse(record_path(self.profile).exists())
        self.assertFalse(originals_path(self.profile).parent.exists())
        programs.restore()
        self.assertEqual((self.source / 'hermes_cli/plugins.py').read_text(), PATCHED)
        self.assertEqual((self.source / 'hermes_cli/new_hook.py').read_text(), ADDED)
        self.assertTrue(self.hold.is_file())
        self.assertEqual(self.originals().keys(), {'hermes_cli/plugins.py', 'scripts/tool.sh'})

    def test_edit_after_review_refuses_publication_with_its_path(self):
        from optional.lifeos_release_manager.inplace_removal import check_host_files
        programs = self.prepared()
        later = PATCHED + '# owner edit after review\n'
        (self.source / 'hermes_cli/plugins.py').write_text(later)
        with self.assertRaisesRegex(ReleaseRejected, 'hermes_cli/plugins.py'):
            check_host_files(programs._load()['entries'], self.source)
        with self.assertRaises(ProgramConflict):
            programs.apply()
        self.assertEqual((self.source / 'hermes_cli/plugins.py').read_text(), later)

    def test_unrecorded_file_in_the_retained_originals_refuses(self):
        from optional.lifeos_release_manager.host_record import originals_path
        publish(originals_path(self.profile) / 'owner-notes.txt', b'Synthetic owner file')
        with self.assertRaisesRegex(ReleaseRejected, 'does not name'):
            self.plan()

    def test_hold_of_another_integration_refuses(self):
        publish(self.hold, json.dumps({'holder': 'Other', 'message': 'Wait.'}).encode())
        with self.assertRaisesRegex(ReleaseRejected, 'another integration'):
            self.plan()

    def test_missing_hold_does_not_block_removal(self):
        self.hold.unlink()
        directories, files, expected = self.plan()
        self.assertNotIn(self.hold, files)
        self.assertNotIn(self.hold, expected)
        programs = ProgramTransaction(self.stage / 'programs')
        programs.prepare(directories=directories, files=files, expected_before=expected)
        programs.apply()
        self.assertEqual(git('status', '--porcelain', '--untracked-files=all', cwd=self.source), '')
        self.assertFalse(self.hold.exists())

    def test_missing_host_record_still_refuses_removal(self):
        from optional.lifeos_release_manager.host_record import record_path
        record_path(self.profile).unlink()
        with self.assertRaisesRegex(ReleaseRejected, 'host record'):
            self.plan()

    def test_runtime_requires_the_host_source_launcher(self):
        from optional.lifeos_release_manager.inplace_removal import runtime
        plan = {'host': {'source': str(self.source)}}
        with self.assertRaises(ReleaseRejected):
            runtime(plan)
        launcher = self.source / '.hermes/bin/hermes'
        launcher.parent.mkdir(parents=True)
        launcher.write_text('#!/bin/sh\nexit 0\n')
        launcher.chmod(0o755)
        self.assertEqual(runtime(plan), {'kind': 'host', 'source': str(self.source), 'hermes': str(launcher)})


class InplaceRemovalSelectionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.home = Path(self.folder.name)
        self.profile = self.home / '.hermes'
        self.profile.mkdir(mode=0o700)
        self.installed = self.home / '.claude'
        self.installed.mkdir(mode=0o700)

    def selected(self):
        from optional.lifeos_release_manager.inplace_removal import selected
        class Status:
            def status(self, profile, plugin):
                return {'active': {'verification': 'verified'}}
        class Bridge:
            def memory_module(self, name):
                return Status()
        return selected(self.profile, self.installed, bridge=Bridge())

    def test_profile_without_a_host_record_refuses(self):
        with self.assertRaisesRegex(ReleaseRejected, 'host record'):
            self.selected()

    def test_host_record_must_name_an_applied_in_place_operation(self):
        from optional.lifeos_release_manager.host_compatibility import load_manifest
        from optional.lifeos_release_manager.host_record import build_record, record_path
        entry = {'label': 'v0.0.1', 'commit': 'b' * 40, 'patches': [{'name': 'host.patch', 'sha256': 'e' * 64}],
                 'files': {'hermes_cli/plugins.py': {'stock': 'c' * 64, 'patched': 'd' * 64}}}
        load_manifest({'format': 1, 'dependencies': [], 'hermes': [entry]})
        source = self.profile / 'hermes-agent'
        record = build_record(self.profile, source, entry, operation='a' * 32, version='0.8.0')
        publish(record_path(self.profile), json.dumps(record).encode())
        identity = {'version': '0.8.0', 'commit': 'f' * 40, 'package_sha256': '9' * 64}
        publish(self.profile / 'integration-release.json', json.dumps(identity).encode())
        job = self.profile / '.lifeos-releases' / ('a' * 32)
        job.mkdir(parents=True, mode=0o700)
        self.profile.joinpath('.lifeos-releases').chmod(0o700)
        request = {'format': 2, 'identifier': job.name, 'profile': str(self.profile), 'installed': str(self.installed),
                   'host': {'source': str(source), 'commit': 'b' * 40}, **identity}
        publish(job / 'request.json', json.dumps(request).encode())
        for state in ('applying', 'rolled_back'):
            publish(job / 'status.json', json.dumps({'state': state}).encode())
            with self.subTest(state=state), self.assertRaisesRegex(ReleaseRejected, 'applied in-place operation'):
                self.selected()
        publish(job / 'status.json', json.dumps({'state': 'applied'}).encode())
        publish(job / 'request.json', json.dumps({**request, 'host': {'source': str(source), 'commit': 'c' * 40}}).encode())
        with self.assertRaisesRegex(ReleaseRejected, 'applied in-place operation'):
            self.selected()
        publish(job / 'request.json', json.dumps(request).encode())
        with self.assertRaises(KeyError) as missing:
            self.selected()
        self.assertEqual(missing.exception.args, ('certificate',))


if __name__ == '__main__':
    unittest.main()
