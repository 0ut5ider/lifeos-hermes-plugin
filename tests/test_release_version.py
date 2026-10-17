# ABOUTME: Verifies integration versions and installed release identity against actual files.
# ABOUTME: Distinguishes selected code from staged candidates and refuses changed evidence.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from lifeos_hook_bridge import release_version


class ReleaseVersionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.plugin = self.root/'lifeos_hook_bridge'
        (self.plugin/'dashboard').mkdir(parents=True)
        self.profile = self.root/'profile'
        self.profile.mkdir()
        self.version('0.3.0')

    def version(self, value):
        (self.root/'VERSION').write_text(value+'\n')
        (self.plugin/'plugin.yaml').write_text('name: lifeos-hook-bridge\nversion: '+value+'\n')
        (self.plugin/'dashboard/manifest.json').write_text(json.dumps({'version':value}))

    def receipt(self):
        files = {str(p.relative_to(self.plugin)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.plugin.rglob('*') if p.is_file()}
        value = {'format':1,'version':'0.3.0','commit':'1'*40,'package_sha256':'2'*64,
            'installed_at':'2026-10-11T23:30:00+00:00','plugin_files':files,
            'upstream':{'hermes':'3'*40,'lifeos':'4'*40},'patches':{'hermes':11,'lifeos':25}}
        self.publish('integration-release.json', value)
        return value

    def publish(self, name, value):
        path=self.profile/name
        path.write_text(json.dumps(value));path.chmod(0o600)

    def test_stable_development_and_candidate_versions_match_all_three_declarations(self):
        for value in ['0.2.0','0.3.0-dev.1','0.3.0-dev.12','0.3.0-rc.1','0.3.0','1.0.0']:
            with self.subTest(value=value):
                self.version(value)
                self.assertEqual(release_version.versions(self.root),value)

    def test_mismatched_or_malformed_versions_refuse(self):
        for value in ['0.3','0.3.0-dev','0.3.0-dev.01','03.0.0','0.3.0\nother']:
            with self.subTest(value=value):
                self.version(value)
                with self.assertRaises(ValueError):release_version.versions(self.root)
        self.version('0.3.0')
        (self.plugin/'dashboard/manifest.json').write_text('{"version":"0.2.0"}')
        with self.assertRaises(ValueError):release_version.versions(self.root)

    def test_absent_release_receipt_reports_unrecorded_identity(self):
        result=release_version.status(self.profile,self.plugin)
        self.assertEqual(result['active']['version'],'0.3.0')
        self.assertEqual(result['active']['verification'],'unrecorded')
        self.assertNotIn('commit',result['active'])
        self.assertIsNone(result['staged'])

    def test_installed_source_hashes_and_staged_candidate_are_distinct(self):
        self.receipt()
        candidate={'format':1,'version':'0.4.0-dev.2','commit':'5'*40,'package_sha256':'6'*64}
        self.publish('integration-candidate.json',candidate)
        result=release_version.status(self.profile,self.plugin)
        self.assertEqual(result['active']['verification'],'verified')
        self.assertEqual(result['active']['version'],'0.3.0')
        self.assertEqual(result['staged']['version'],'0.4.0-dev.2')
        self.assertEqual(result['active']['commit'],'1'*40)
        (self.plugin/'plugin.yaml').write_text('name: lifeos-hook-bridge\nversion: 0.3.0\ndescription: changed\n')
        result=release_version.status(self.profile,self.plugin)
        self.assertEqual(result['active']['verification'],'modified')
        self.assertEqual(result['active']['modified_files'],['plugin.yaml'])

    def test_receipt_paths_and_aliases_cannot_read_other_files(self):
        value=self.receipt()
        value['plugin_files']={'../outside':'a'*64}
        self.publish('integration-release.json',value)
        with self.assertRaises(ValueError):release_version.status(self.profile,self.plugin)
        self.receipt()
        path=self.profile/'integration-release.json'
        retained=self.profile/'retained.json'
        path.rename(retained);path.symlink_to(retained)
        with self.assertRaises(ValueError):release_version.status(self.profile,self.plugin)

    def test_receipt_version_cannot_mislabel_the_installed_code(self):
        value=self.receipt();value['version']='0.4.0'
        self.publish('integration-release.json',value)
        result=release_version.status(self.profile,self.plugin)
        self.assertEqual(result['active']['version'],'0.3.0')
        self.assertEqual(result['active']['verification'],'modified')

    def test_unrecorded_program_files_do_not_claim_an_exact_release(self):
        self.receipt()
        (self.plugin/'extra.py').write_text('value = 1\n')
        result=release_version.status(self.profile,self.plugin)
        self.assertEqual(result['active']['verification'],'modified')
        self.assertIn('extra.py',result['active']['modified_files'])


class HostDriftTests(unittest.TestCase):
    version = ReleaseVersionTests.version
    publish = ReleaseVersionTests.publish

    def setUp(self):
        ReleaseVersionTests.setUp(self)
        self.source = self.root/'hermes-agent'
        (self.source/'hermes_cli').mkdir(parents=True)
        self.files = {'hermes_cli/plugins.py': b'patched\n', 'hermes_cli/new_hook.py': b'added\n'}
        for relative, data in self.files.items():
            (self.source/relative).write_bytes(data)
        self.record()

    def record(self, **changes):
        value = {'format': 1, 'source': str(self.source), 'commit': '3'*40, 'label': 'v0.0.1', 'patches': [],
                 'files': {'hermes_cli/plugins.py': {'stock': 'a'*64, 'patched': hashlib.sha256(b'patched\n').hexdigest()},
                           'hermes_cli/new_hook.py': {'stock': None, 'patched': hashlib.sha256(b'added\n').hexdigest()}},
                 'originals': str(self.profile/'.lifeos-host/originals'), 'operation': 'e'*32, 'version': '0.3.0'}
        value.update(changes)
        self.publish('lifeos-host.json', value)
        return value

    def host(self):
        return release_version.status(self.profile, self.plugin)['host']

    def test_profile_without_a_host_record_reports_no_host(self):
        (self.profile/'lifeos-host.json').unlink()
        self.assertIsNone(self.host())

    def test_unchanged_host_files_are_installed(self):
        self.assertEqual(self.host(), {'state': 'installed', 'source': str(self.source), 'changed': []})

    def test_changed_missing_or_linked_host_files_are_drift_with_their_paths(self):
        (self.source/'hermes_cli/plugins.py').write_bytes(b'owner edit\n')
        self.assertEqual(self.host(), {'state': 'host_drift', 'source': str(self.source),
                                       'changed': ['hermes_cli/plugins.py']})
        (self.source/'hermes_cli/new_hook.py').unlink()
        (self.source/'hermes_cli/new_hook.py').symlink_to(self.root/'elsewhere.py')
        (self.root/'elsewhere.py').write_bytes(b'added\n')
        self.assertEqual(self.host()['changed'], ['hermes_cli/new_hook.py', 'hermes_cli/plugins.py'])

    def test_damaged_record_is_drift_that_names_the_record(self):
        for damage in ('{not json', json.dumps({'format': 1}),
                       json.dumps(self.record(files={'../outside.py': {'stock': None, 'patched': 'b'*64}}))):
            with self.subTest(damage=damage[:30]):
                path = self.profile/'lifeos-host.json'
                path.write_text(damage);path.chmod(0o600)
                result = self.host()
                self.assertEqual(result['state'], 'host_drift')
                self.assertIn('lifeos-host.json', result['reason'])
        self.record()
        (self.profile/'lifeos-host.json').chmod(0o666)
        self.assertIn('lifeos-host.json', self.host()['reason'])


class ReleaseVersionCommandTests(unittest.TestCase):
    def test_actual_hermes_parser_reports_the_selected_plugin_without_a_model_call(self):
        import test_memory_owner_job_command as commands
        import test_memory_model_calls as models
        fixture=commands.MemoryOwnerJobCommandTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        environment={key:os.environ[key] for key in ('PATH','LANG','TZ') if key in os.environ}
        environment.update(HOME=str(fixture.native.home),HERMES_HOME=str(fixture.fixture.home),
            PYTHONPATH=str(models.HOST),LIFEOS_HOOK_SETTINGS=str(fixture.native.root/'settings.json'),
            BUN_CONFIG_NO_AUTO_INSTALL='1',PYTHONDONTWRITEBYTECODE='1')
        result=subprocess.run([sys.executable,'-m','hermes_cli.main','lifeos-version'],
            env=environment,capture_output=True,text=True,timeout=40)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(result.stderr,'')
        report=json.loads(result.stdout)
        self.assertEqual(report['active']['verification'],'unrecorded')
        self.assertEqual(fixture.fixture.fixture.received,[])
