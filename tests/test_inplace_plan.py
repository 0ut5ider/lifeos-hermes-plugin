# ABOUTME: Checks the in-place plan: host publication entries, the owner review data, and the refusals of a stale job.
# ABOUTME: Builds a real job from this repository's plugins, a disposable Git checkout, and real staged files.
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from optional.lifeos_release_manager.release_catalog import ReleaseRejected
from optional.lifeos_release_manager.release_programs import publish


REPOSITORY = Path(__file__).resolve().parents[1]
IGNORED = shutil.ignore_patterns('__pycache__', '*.pyc')
STOCK = "VALID_HOOKS = {'pre_tool_call'}\n"
PATCHED = "VALID_HOOKS = {'pre_tool_call', 'pre_turn_stop'}\n"
ADDED = "ENABLED = True\n"


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


class InplaceJob(unittest.TestCase):
    """A prepared in-place job for a disposable stock Hermes checkout, as preparation leaves it."""

    def setUp(self):
        from optional.lifeos_release_manager.host_compatibility import load_manifest
        from optional.lifeos_release_manager.inplace_plan import archive_name
        from optional.lifeos_release_manager.integration_package import COMPATIBILITY, MANIFEST_NAME, file_map
        from optional.lifeos_release_manager.release_stage import runtime_source_fingerprint, sha
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name).resolve()
        self.home = root / 'home'
        self.home.mkdir(mode=0o755)
        self.profile = self.home / '.hermes'
        self.profile.mkdir(mode=0o700)
        (self.profile / 'config.yaml').write_text('model:\n  default: m1\n')
        self.source = self.profile / 'hermes-agent'
        self.source.mkdir(mode=0o755)
        git('init', '-q', '-b', 'main', cwd=self.source)
        (self.source / 'hermes_cli').mkdir()
        (self.source / 'hermes_cli/__init__.py').write_text('')
        (self.source / 'hermes_cli/plugins.py').write_text(STOCK)
        (self.source / 'run_agent.py').write_text('')
        (self.source / 'pyproject.toml').write_text("[project]\nname = 'hermes-agent'\n")
        (self.source / 'uv.lock').write_text('version = 1\n')
        # Hermes selects a resolved lock outside the tracked tree; an ignored lock stands in for it here.
        (self.source / '.gitignore').write_text('.hermes/\nuv.lock\n')
        git('add', '.', cwd=self.source)
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'base', cwd=self.source)
        launcher = self.source / '.hermes/bin/hermes'
        launcher.parent.mkdir(parents=True)
        launcher.write_text('#!/bin/sh\nexit 0\n')
        launcher.chmod(0o755)
        self.commit = git('rev-parse', 'HEAD', cwd=self.source)
        self.entry = {'label': 'v0.0.1', 'commit': self.commit, 'patches': [{'name': 'host.patch', 'sha256': 'e' * 64}],
                      'files': {'hermes_cli/plugins.py': {'stock': digest(STOCK), 'patched': digest(PATCHED)},
                                'hermes_cli/new_hook.py': {'stock': None, 'patched': digest(ADDED)}},
                      'python': '%d.%d' % sys.version_info[:2],
                      'capabilities': {'hooks': ['pre_turn_stop'], 'middleware_api': 1},
                      'known_conflicts': ['The example-relay plugin replaces the delivery hook.']}
        self.manifest = load_manifest({'format': 1, 'dependencies': [], 'hermes': [self.entry]})
        releases = self.profile / '.lifeos-releases'
        releases.mkdir(mode=0o700)
        self.job = releases / ('a' * 32)
        self.job.mkdir(mode=0o700)
        package = self.job / 'package'
        package.mkdir(mode=0o700)
        shutil.copytree(REPOSITORY / 'lifeos_hook_bridge', package / 'lifeos_hook_bridge', ignore=IGNORED)
        shutil.copytree(REPOSITORY / 'optional/lifeos_release_manager', package / 'optional/lifeos_release_manager',
                        ignore=IGNORED)
        for name in ('VERSION', 'CHANGELOG.md'):
            shutil.copy2(REPOSITORY / name, package / name)
        (package / COMPATIBILITY).write_text(json.dumps(self.manifest))
        version = (REPOSITORY / 'VERSION').read_text().strip()
        lifeos = {'upstream': 'https://github.com/danielmiessler/LifeOS.git', 'commit': 'c' * 40, 'tree_sha256': 'd' * 64}
        integration = {'format': 2, 'version': version, 'head': 'b' * 40,
                       'plugin_files': file_map(package / 'lifeos_hook_bridge'),
                       'manager_files': file_map(package / 'optional/lifeos_release_manager'),
                       'host_compatibility_sha256': sha(package / COMPATIBILITY), 'lifeos': lifeos}
        (package / MANIFEST_NAME).write_text(json.dumps(integration))
        certificate = {'format': 2, 'status': 'QUALIFIED', 'version': version, 'program_commit': 'b' * 40,
                       'host_compatibility_sha256': integration['host_compatibility_sha256'], 'lifeos': dict(lifeos)}
        self.request = {'format': 2, 'identifier': self.job.name, 'profile': str(self.profile),
                        'account_home': str(self.home), 'installed': str(self.home / '.claude'),
                        'version': version, 'commit': 'b' * 40, 'certificate': certificate}
        archive = self.job / 'download' / archive_name(self.request)
        archive.parent.mkdir(mode=0o700)
        archive.write_bytes(b'synthetic integration archive')
        preview = self.job / 'hermes-preview'
        (preview / 'hermes_cli').mkdir(parents=True)
        (preview / 'hermes_cli/plugins.py').write_text(PATCHED)
        for kind, files in (('stock', {'hermes_cli/plugins.py': STOCK}),
                            ('patched', {'hermes_cli/plugins.py': PATCHED, 'hermes_cli/new_hook.py': ADDED})):
            for relative, text in files.items():
                path = self.job / 'host' / kind / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
        self.request.update(
            package_sha256=sha(archive), runtime_fingerprint=runtime_source_fingerprint(preview),
            configuration_sha256=sha(self.profile / 'config.yaml'),
            host={'source': str(self.source), 'commit': self.commit, 'label': 'v0.0.1', 'state': 'compatible',
                  'state_directory': str(self.job / 'installs-state'), 'transition': False, 'transition_units': {},
                  'record_sha256': None},
            runtime={'python': sys.executable, 'bun': str(self.job / 'tools/bun'), 'hermes': str(launcher),
                     'source': str(preview), 'reference': str(self.job / 'reference-home/.claude'),
                     'lifeos': str(self.job / 'lifeos'), 'host_files': str(self.job / 'host')},
            dependencies={'seed_sha256': sha(self.source / 'uv.lock'), 'added': {}})

    def inspect(self, request=None):
        from optional.lifeos_release_manager.inplace_plan import inspect_inplace
        return inspect_inplace(self.job, self.request if request is None else request)

    def staged(self):
        from optional.lifeos_release_manager.inplace_plan import staged_files
        return staged_files(self.job, self.entry)


class InspectInplaceTests(InplaceJob):
    def test_unchanged_job_passes_every_host_check_and_reaches_the_lifeos_check(self):
        with self.assertRaisesRegex(Exception, 'LifeOS candidate manifest'):
            self.inspect()

    def test_changed_package_is_refused(self):
        (self.job / 'package/lifeos_hook_bridge/plugin.yaml').write_text('changed\n')
        with self.assertRaises(ReleaseRejected):
            self.inspect()

    def test_changed_archive_is_refused(self):
        from optional.lifeos_release_manager.inplace_plan import archive_name
        (self.job / 'download' / archive_name(self.request)).write_bytes(b'other archive')
        with self.assertRaisesRegex(ReleaseRejected, 'integration archive'):
            self.inspect()

    def test_changed_runtime_path_is_refused(self):
        request = {**self.request, 'runtime': {**self.request['runtime'], 'hermes': '/usr/bin/hermes'}}
        with self.assertRaisesRegex(ReleaseRejected, 'fixed paths'):
            self.inspect(request)

    def test_changed_preview_is_refused(self):
        (self.job / 'hermes-preview/hermes_cli/plugins.py').write_text('edited\n')
        with self.assertRaisesRegex(ReleaseRejected, 'preview'):
            self.inspect()

    def test_new_host_commit_is_refused(self):
        (self.source / 'run_agent.py').write_text('# upstream change\n')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qam', 'next', cwd=self.source)
        with self.assertRaisesRegex(ReleaseRejected, 'changes after preparation'):
            self.inspect()

    def test_host_edit_after_preparation_is_refused(self):
        (self.source / 'hermes_cli/plugins.py').write_text(STOCK + '# owner edit\n')
        with self.assertRaisesRegex(ReleaseRejected, 'Hermes installation changes after preparation'):
            self.inspect()

    def test_host_record_created_after_preparation_is_refused(self):
        from optional.lifeos_release_manager.host_record import build_record, record_path
        publish(record_path(self.profile), json.dumps(build_record(
            self.profile, self.source, self.entry, operation='b' * 32, version='0.8.0')).encode())
        with self.assertRaisesRegex(ReleaseRejected, 'changes after preparation'):
            self.inspect()

    def test_changed_dependency_lock_is_refused(self):
        (self.source / 'uv.lock').write_text('version = 2\n')
        with self.assertRaisesRegex(ReleaseRejected, 'Python environment changes after preparation'):
            self.inspect()

    def test_changed_staged_file_is_refused_with_its_path(self):
        (self.job / 'host/patched/hermes_cli/new_hook.py').write_text('ENABLED = False\n')
        with self.assertRaisesRegex(ReleaseRejected, 'hermes_cli/new_hook.py'):
            self.inspect()
        (self.job / 'host/patched/hermes_cli/new_hook.py').write_text(ADDED)
        (self.job / 'host/stock/hermes_cli/plugins.py').write_text('changed original\n')
        with self.assertRaisesRegex(ReleaseRejected, 'original Hermes file changed after preparation: hermes_cli/plugins.py'):
            self.staged()


class HostEntriesTests(InplaceJob):
    def selected(self):
        return {'profile': self.profile, 'source': self.source, 'entry': self.entry, 'staged': self.staged()}

    def entries(self):
        from optional.lifeos_release_manager.inplace_plan import host_entries
        generated = self.job / 'generated'
        generated.mkdir(mode=0o700, exist_ok=True)
        return generated, host_entries(self.job, self.request, self.selected(), generated)

    def test_first_installation_publishes_patches_originals_record_and_hold(self):
        from optional.lifeos_release_manager.host_record import load_record, originals_path, record_path
        from optional.lifeos_release_manager.inplace_plan import HOLD, HOLD_MESSAGE
        generated, (directories, files) = self.entries()
        host = self.job / 'host'
        self.assertEqual(directories, {})
        self.assertEqual(files, {
            self.source / 'hermes_cli/plugins.py': host / 'patched/hermes_cli/plugins.py',
            self.source / 'hermes_cli/new_hook.py': host / 'patched/hermes_cli/new_hook.py',
            originals_path(self.profile) / 'hermes_cli/plugins.py': host / 'stock/hermes_cli/plugins.py',
            record_path(self.profile): generated / 'lifeos-host.json',
            self.source / '.git' / HOLD: generated / 'update-hold.json'})
        record = json.loads((generated / 'lifeos-host.json').read_text())
        self.assertEqual((record['commit'], record['operation'], record['files']),
                         (self.commit, self.job.name, self.entry['files']))
        self.assertEqual(json.loads((generated / 'update-hold.json').read_text()),
                         {'holder': 'LifeOS', 'message': HOLD_MESSAGE})
        publish(record_path(self.profile), (generated / 'lifeos-host.json').read_bytes())
        self.assertEqual(load_record(self.profile)['label'], 'v0.0.1')

    def test_update_returns_targets_the_new_release_drops_to_their_originals(self):
        from optional.lifeos_release_manager.host_record import build_record, originals_path, record_path
        previous = {**self.entry, 'files': {**self.entry['files'],
                    'run_agent.py': {'stock': digest(''), 'patched': digest('patched\n')},
                    'hermes_cli/old_hook.py': {'stock': None, 'patched': digest('old\n')}}}
        publish(record_path(self.profile), json.dumps(build_record(
            self.profile, self.source, previous, operation='b' * 32, version='0.7.9')).encode())
        retained = originals_path(self.profile)
        for relative, text in (('hermes_cli/plugins.py', STOCK), ('run_agent.py', '')):
            (retained / relative).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            publish(retained / relative, text.encode())
        _, (_, files) = self.entries()
        self.assertEqual(files[self.source / 'run_agent.py'], retained / 'run_agent.py')
        self.assertIsNone(files[self.source / 'hermes_cli/old_hook.py'])
        self.assertIsNone(files[retained / 'run_agent.py'])
        self.assertEqual(files[retained / 'hermes_cli/plugins.py'], self.job / 'host/stock/hermes_cli/plugins.py')

    def test_added_targets_publish_before_the_targets_that_import_them(self):
        _, (_, files) = self.entries()
        order = list(files)
        self.assertLess(order.index(self.source / 'hermes_cli/new_hook.py'), order.index(self.source / 'hermes_cli/plugins.py'))

    def test_update_that_drops_a_target_removes_its_original_and_leaves_removal_admissible(self):
        from optional.lifeos_release_manager.host_record import build_record, load_record, originals_path, record_path
        from optional.lifeos_release_manager.inplace_removal import host_plan
        from optional.lifeos_release_manager.release_programs import ProgramTransaction
        previous = {**self.entry, 'files': {**self.entry['files'],
                    'run_agent.py': {'stock': digest(''), 'patched': digest('patched\n')}}}
        publish(record_path(self.profile), json.dumps(build_record(
            self.profile, self.source, previous, operation='b' * 32, version='0.7.9')).encode())
        retained = originals_path(self.profile)
        for relative, text in (('hermes_cli/plugins.py', STOCK), ('run_agent.py', '')):
            (retained / relative).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            publish(retained / relative, text.encode())
        (self.source / 'run_agent.py').write_text('patched\n')
        _, (directories, files) = self.entries()
        programs = ProgramTransaction(self.job / 'program-snapshot')
        programs.prepare(directories=directories, files=files)
        for entry in programs.entries():
            Path(entry['target']).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        programs.apply()
        self.assertEqual((self.source / 'run_agent.py').read_text(), '')
        self.assertFalse((retained / 'run_agent.py').exists())
        stage = self.home / 'stage'
        stage.mkdir(mode=0o700)
        record = load_record(self.profile)
        host_plan(self.profile, record, {'hermes_cli/plugins.py': retained / 'hermes_cli/plugins.py'}, stage)
        programs.restore()
        self.assertEqual((retained / 'run_agent.py').read_text(), '')
        self.assertEqual((self.source / 'run_agent.py').read_text(), 'patched\n')


class ReviewTests(InplaceJob):
    def test_update_difference_lists_added_changed_and_restored_targets(self):
        from optional.lifeos_release_manager.inplace_plan import update_difference
        record = {'files': {'hermes_cli/plugins.py': {'stock': 'a' * 64, 'patched': 'b' * 64},
                            'run_agent.py': {'stock': 'a' * 64, 'patched': 'c' * 64},
                            'hermes_cli/same.py': {'stock': None, 'patched': 'd' * 64}}}
        entry = {'files': {'hermes_cli/plugins.py': {'stock': 'a' * 64, 'patched': 'e' * 64},
                           'hermes_cli/same.py': {'stock': None, 'patched': 'd' * 64},
                           'hermes_cli/new_hook.py': {'stock': None, 'patched': 'f' * 64}}}
        self.assertEqual(update_difference(record, entry), {'added': ['hermes_cli/new_hook.py'],
                                                            'changed': ['hermes_cli/plugins.py'],
                                                            'restored': ['run_agent.py']})
        self.assertIsNone(update_difference(None, entry))

    def test_review_records_every_configuration_key_and_the_update_difference(self):
        from optional.lifeos_release_manager.inplace_plan import review_changes
        from optional.lifeos_release_manager.cli import read_private
        generated = self.job / 'generated'
        generated.mkdir(mode=0o700)
        (self.profile / 'config.yaml').write_text('model:\n  default: m1\nplugins:\n  enabled: [other]\n')
        (generated / 'config.yaml').write_text(
            'model:\n  default: m1\nplugins:\n  enabled: [other, lifeos-hook-bridge]\n  entries:\n'
            '    lifeos-hook-bridge:\n      settings: {lifeos_source_dir: /n}\n')
        value = review_changes(self.job, self.entry, None, self.profile / 'config.yaml', generated / 'config.yaml')
        self.assertEqual(value, {'configuration': ['plugins.enabled', 'plugins.entries'], 'update': None})
        self.assertEqual(read_private(self.job / 'inplace-review.json'), value)


if __name__ == '__main__':
    unittest.main()
