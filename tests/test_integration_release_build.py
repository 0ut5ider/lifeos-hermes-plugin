# ABOUTME: Checks that the integration release builder makes a reproducible archive with exact file identities.
# ABOUTME: Builds twice from a disposable Git copy of this repository; only the LifeOS fetch is replaced.
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from scripts import build_integration_release as builder
from optional.lifeos_release_manager.integration_package import COMPATIBILITY, MANIFEST_NAME, file_map


REPOSITORY = Path(__file__).resolve().parents[1]
LIFEOS = {'upstream_commit': builder.install_source.SUPPORTED_LIFEOS_COMMIT, 'tree_sha256': 'd' * 64}


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True).stdout


class IntegrationReleaseBuildTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        self.repository = self.root / 'repository'
        self.repository.mkdir()
        data = git('archive', 'HEAD', '--', *builder.SELECTED, cwd=REPOSITORY)
        with tarfile.open(fileobj=io.BytesIO(data)) as source:
            source.extractall(self.repository, filter='data')
        git('init', '-q', '-b', 'main', cwd=self.repository)
        git('add', '.', cwd=self.repository)
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'release', cwd=self.repository)
        self.head = git('rev-parse', 'HEAD', cwd=self.repository).decode().strip()
        self.fetches = []

    def build(self, output):
        def prepare_lifeos(source, target, commit, patches, names, **options):
            self.fetches.append((source, commit, tuple(names)))
            return dict(LIFEOS)
        with mock.patch.object(builder, 'REPOSITORY', self.repository), \
                mock.patch.object(builder.install_source, 'prepare_lifeos', side_effect=prepare_lifeos):
            return builder.build(self.root / output)

    def test_two_builds_give_the_same_archive(self):
        first, second = self.build('first'), self.build('second')
        self.assertEqual(first, second)
        self.assertEqual((self.root / 'first' / first['archive_name']).read_bytes(),
                         (self.root / 'second' / second['archive_name']).read_bytes())
        self.assertEqual(first['archive_sha256'],
                         hashlib.sha256((self.root / 'first' / first['archive_name']).read_bytes()).hexdigest())
        self.assertEqual(self.fetches[0], (builder.install_source.UPSTREAM_LIFEOS, LIFEOS['upstream_commit'],
                                           tuple(builder.install_source.LIFEOS_PATCHES)))

    def test_archive_manifest_binds_the_plugins_the_compatibility_manifest_and_lifeos(self):
        record = self.build('output')
        version = (self.repository / 'VERSION').read_text().strip()
        self.assertEqual(record['archive_name'], 'lifeos-integration-' + version + '-' + self.head[:8] + '.tgz')
        extracted = self.root / 'extracted'
        with tarfile.open(self.root / 'output' / record['archive_name']) as archive:
            members = archive.getmembers()
            archive.extractall(extracted, filter='data')
        self.assertEqual([member.name for member in members], sorted(member.name for member in members))
        self.assertTrue(all(member.mtime == 0 and member.uid == 0 and member.gid == 0 for member in members))
        self.assertFalse([member.name for member in members if '__pycache__' in member.name or member.name.endswith('.pyc')])
        manifest = json.loads((extracted / MANIFEST_NAME).read_text())
        self.assertEqual(manifest, {
            'format': 2, 'version': version, 'head': self.head,
            'plugin_files': file_map(self.repository / 'lifeos_hook_bridge'),
            'manager_files': file_map(self.repository / 'optional/lifeos_release_manager'),
            'host_compatibility_sha256': hashlib.sha256((self.repository / COMPATIBILITY).read_bytes()).hexdigest(),
            'lifeos': {'upstream': builder.install_source.UPSTREAM_LIFEOS, 'commit': LIFEOS['upstream_commit'],
                       'tree_sha256': LIFEOS['tree_sha256']}})
        self.assertEqual(record['host_compatibility_sha256'], manifest['host_compatibility_sha256'])
        self.assertEqual(record['lifeos'], manifest['lifeos'])
        self.assertEqual(record['archive_bytes'], (self.root / 'output' / record['archive_name']).stat().st_size)

    def test_uncommitted_tracked_change_is_refused(self):
        (self.repository / 'VERSION').write_text('9.9.9\n')
        with self.assertRaisesRegex(ValueError, 'Commit tracked changes'):
            self.build('output')
        self.assertFalse((self.root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
