# ABOUTME: Exercises native LocalIntelligence source resolution through current owner admission.
# ABOUTME: Requires bound and admitted identity and source configuration before refresh preparation.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import unittest
import test_memory_manual_state as state_fixture
from lifeos_hook_bridge.memory_service import MemoryService

IDENTITY = 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
SOURCES = 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/sources.json'


class MemoryLocalRefreshTests(unittest.TestCase):
    def setUp(self):
        self.fixture = state_fixture.MemoryManualStateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.owner = self.fixture.fixture
        self.root = self.fixture.root
        self.configuration = self.owner.configuration
        self.service = MemoryService(self.configuration)
        self.skill = Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'skills/LocalIntelligence'
        (self.root / 'skills').mkdir(exist_ok=True)
        (self.root / 'skills/LocalIntelligence').symlink_to(self.skill, target_is_directory=True)
        self.identity = self.root / IDENTITY
        self.identity.write_text('- **Hometown:** SyntheticCity, TX (ZIP 78701, Synthetic County)\n')
        self.sources = self.root / SOURCES
        self.sources.parent.mkdir(parents=True, exist_ok=True)
        self.sources.write_text(json.dumps({'sources': [{'section': 'news', 'name': 'Synthetic Local Source',
            'type': 'rss', 'url': 'https://synthetic.invalid/local'}]}))

    def native(self, tool, *, context=True):
        source = self.root / 'skills/LocalIntelligence/Tools' / tool
        operation = 'await module.readHometown()' if tool == 'Hometown.ts' else 'await module.loadUserSources()'
        script = 'import * as module from ' + json.dumps(str(source)) + ';console.log(JSON.stringify(' + operation + '));'
        environment = dict(os.environ, HOME=str(self.owner.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        for name in ('LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_INTERNAL', 'LIFEOS_PRINCIPAL_IDENTITY'):
            environment.pop(name, None)
        if context: environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.owner.context))
        return subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            env=environment, timeout=30)

    def test_native_hometown_preserves_current_parsing_and_refuses_unbound_reader(self):
        owner = self.native('Hometown.ts')
        self.assertEqual((owner.returncode, owner.stderr), (0, ''), owner.stdout)
        self.assertEqual(json.loads(owner.stdout)['city'], 'SyntheticCity')
        refused = self.native('Hometown.ts', context=False)
        self.assertNotEqual(refused.returncode, 0, refused.stdout)
        self.assertNotIn('SyntheticCity', refused.stdout)

    def test_native_user_sources_refuse_private_decoded_configuration(self):
        self.sources.write_text(self.sources.read_text().replace('Synthetic Local Source', '<private>SyntheticLocalHidden</private>'))
        refused = self.native('UserSources.ts')
        self.assertNotEqual(refused.returncode, 0, refused.stdout)
        self.assertNotIn('SyntheticLocalHidden', refused.stdout)

    def call(self, operation='local_refresh_prepare', **arguments):
        return self.service.native(self.owner.context, operation, arguments)

    def test_read_only_owner_retains_inputs_but_cannot_prepare_generation(self):
        self.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        for kind in ('hometown', 'sources'):
            self.assertTrue(self.call('local_inputs', kind=kind)['ok'])
        self.assertFalse(self.call()['ok'])

    def test_missing_sources_preserve_native_empty_selection(self):
        self.sources.unlink()
        result = self.call()
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['plan']['sources'], [])
        self.assertEqual(json.loads(self.native('UserSources.ts').stdout), [])

    def test_missing_hometown_refuses_before_network_or_publication(self):
        self.identity.write_text('# Synthetic owner without a hometown\n')
        self.assertFalse(self.call()['ok'])
        self.assertFalse((self.root / 'LIFEOS/MEMORY/DATA/LocalIntelligence').exists())

    def test_unbound_revoked_and_partial_reader_cannot_read_inputs(self):
        self.configuration.update(lambda value: value['destinations']['chat-a:200'].update(read=['principal']))
        self.assertFalse(self.call('local_inputs', kind='hometown')['ok'])
        self.configuration.update(lambda value: value['accounts'].clear())
        self.assertFalse(self.call('local_inputs', kind='sources')['ok'])

    def test_linked_invalid_and_excessive_sources_refuse(self):
        original = self.sources.read_bytes()
        for mode in ('symlink', 'hardlink', 'utf8', 'malformed', 'oversize'):
            with self.subTest(mode=mode):
                self.sources.unlink(missing_ok=True)
                outside = self.owner.fixture.home / 'synthetic-local-sources'
                outside.write_bytes(original)
                if mode == 'symlink': self.sources.symlink_to(outside)
                elif mode == 'hardlink': os.link(outside, self.sources)
                elif mode == 'utf8': self.sources.write_bytes(original + b'\xff')
                elif mode == 'malformed': self.sources.write_text('{')
                else: self.sources.write_text(' ' * (256 * 1024 + 1))
                self.assertFalse(self.call()['ok'])
                self.assertFalse((self.root / 'LIFEOS/MEMORY/DATA/LocalIntelligence').exists())

    def test_private_identity_and_escaped_private_configuration_refuse(self):
        self.identity.write_text('- **Hometown:** <private>SyntheticLocalHidden</private>, TX\n')
        self.assertFalse(self.call()['ok'])
        self.identity.write_text('- **Hometown:** SyntheticCity, TX\n')
        self.sources.write_text(self.sources.read_text().replace('Synthetic Local Source',
            r'\u003cprivate\u003eSyntheticLocalHidden\u003c/private\u003e'))
        result = self.call()
        self.assertFalse(result['ok'])
        self.assertNotIn('SyntheticLocalHidden', json.dumps(result))

    def test_actual_native_render_rechecks_sources_and_authority(self):
        from lifeos_hook_bridge.memory_access import NativeMemory
        original = NativeMemory._native
        source = self.sources.read_bytes()
        for mode in ('source', 'metadata', 'authority'):
            with self.subTest(mode=mode):
                observed = []
                def mutate(memory, action, **arguments):
                    result = original(memory, action, **arguments)
                    if action == 'local_refresh_inputs' and not observed:
                        observed.append(result)
                        if mode == 'source': self.sources.write_text('{"sources":[]}')
                        elif mode == 'metadata': os.utime(self.sources, ns=(self.sources.stat().st_atime_ns, self.sources.stat().st_mtime_ns + 1000000))
                        else: self.configuration.update(lambda value: value['accounts'].clear())
                    return result
                NativeMemory._native = mutate
                try: result = self.call()
                finally: NativeMemory._native = original
                self.assertEqual(len(observed), 1)
                self.assertFalse(result['ok'], result)
                self.sources.write_bytes(source)
                self.configuration.update(lambda value: value['accounts'].update({'chat-a:100': 'owner'}))

    def test_exact_review_restores_safe_old_config_without_changing_bytes(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        from test_memory_native import OWNER
        memory = self.owner.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated local retirement',
            title='', project='', request_id='local-review-unrelated')
        memory.forget(OWNER, saved['reference'], 'local-review-forget')
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in (self.identity, self.sources)]
        self.assertFalse(self.call()['ok'])
        selected = preview(memory, OWNER, [IDENTITY, SOURCES])
        self.assertTrue(all(row['accepted'] for row in selected['sources']), selected)
        approve(memory, OWNER, [IDENTITY, SOURCES], selected['signature'])
        self.assertTrue(self.call()['ok'])
        self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in (self.identity, self.sources)], before)

    def test_current_owner_prepares_native_hometown_and_source_selection(self):
        result = self.service.native(self.owner.context, 'local_refresh_prepare', {})
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['plan']['home']['city'], 'SyntheticCity')
        self.assertEqual(result['plan']['sources'][0]['name'], 'Synthetic Local Source')
        self.assertRegex(result['signature'], '^[0-9a-f]{64}$')
        self.assertFalse((self.root / 'LIFEOS/MEMORY/DATA/LocalIntelligence').exists())

    def test_invalid_input_selectors_return_refusal_without_unhandled_errors(self):
        for kind in (None, [], {}, True, 'other'):
            with self.subTest(kind=kind):
                self.assertFalse(self.call('local_inputs', kind=kind)['ok'])
