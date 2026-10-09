# ABOUTME: Characterizes the real terminal banner and checks owner admission for identity fields.
# ABOUTME: Uses synthetic names and catchphrases without changing an installed profile.
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_manual_state as state_fixture
from test_memory_native import OWNER


class MemoryBannerTests(unittest.TestCase):
    setUp = state_fixture.MemoryManualStateTests.setUp
    call = state_fixture.MemoryManualStateTests.call

    def seed(self, name='SyntheticBannerName', phrase='Ready, {name}'):
        self.assistant = self.root / 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'
        self.assistant.write_text('---\ncore:\n  name: ' + json.dumps(name) + '\n  startup_catchphrase: '
            + json.dumps(phrase) + '\n---\n# Assistant\n')
        (self.root / 'LIFEOS/VERSION').write_text('3.8\n')
        (self.root / 'LIFEOS/ALGORITHM').mkdir(exist_ok=True)
        (self.root / 'LIFEOS/ALGORITHM/LATEST').write_text('v7.9\n')

    def original(self, *args):
        tool = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/Banner.ts'
        env = dict(os.environ, HOME=str(self.fixture.fixture.home), LIFEOS_DIR=str(self.root / 'LIFEOS'),
            LIFEOS_MEMORY_INTERNAL='1', BUN_CONFIG_NO_AUTO_INSTALL='1')
        env.pop('KITTY_WINDOW_ID', None)
        return subprocess.run(['bun', '--no-install', str(tool), *args], capture_output=True, text=True,
            timeout=40, env=env, cwd=self.fixture.fixture.home)

    def banner(self, *args, context=True):
        return self.call('Banner.ts', *args, context=context)

    def test_original_native_designs_name_substitution_and_default_characterization(self):
        self.seed()
        for design in ('navy', 'navy-medium', 'navy-compact', 'navy-minimal', 'navy-ultra'):
            with self.subTest(design=design):
                raw = self.original('--design=' + design)
                self.assertEqual(raw.returncode, 0, raw.stderr)
                self.assertEqual(raw.stderr, '')
                self.assertIn('Ready, SyntheticB' if design == 'navy-compact' else 'SyntheticBannerName', raw.stdout)
                current = self.banner('--design=' + design)
                self.assertEqual(current.returncode, 0, current.stderr)
                self.assertEqual(current.stdout, raw.stdout)
        self.assistant.unlink()
        self.assertEqual(self.banner('--design=navy').stdout, self.original('--design=navy').stdout)

    def test_unbound_reader_cannot_disclose_assistant_identity(self):
        self.seed()
        result = self.banner('--design=navy', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticBannerName', result.stdout + result.stderr)

    def test_private_and_yaml_escaped_catchphrases_cannot_reach_banner(self):
        for phrase in ('<private>SyntheticBannerHidden</private>', '\\u003cprivate\\u003eSyntheticBannerHidden\\u003c/private\\u003e'):
            with self.subTest(phrase=phrase):
                self.seed(phrase=phrase)
                if phrase.startswith('\\u'):
                    self.assistant.write_text(self.assistant.read_text().replace('\\\\u', '\\u'))
                result = self.banner('--design=navy')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('SyntheticBannerHidden', result.stdout + result.stderr)

    def test_actual_retirement_refuses_retained_banner_name(self):
        self.seed()
        saved = self.fixture.fixture.memory.remember(OWNER, category='assistant', content='RULE: SyntheticBannerName',
            title='', project='', request_id='banner-retained')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'banner-forget')
        result = self.banner('--design=navy')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticBannerName', result.stdout + result.stderr)
    def test_revoked_owner_and_missing_connector_refuse(self):
        self.seed()
        self.fixture.configuration.update(lambda config: config['accounts'].clear())
        result = self.banner('--design=navy')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticBannerName', result.stdout + result.stderr)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = self.banner('--design=navy')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticBannerName', result.stdout + result.stderr)

    def test_native_identity_display_name_empty_phrase_and_parse_failure_characterization(self):
        self.seed()
        for content in ('---\ncore:\n  display_name: SyntheticBannerDisplay\n  name: SyntheticIgnoredName\n  startup_catchphrase: "Ready, {name}"\n---\n',
                '---\ncore:\n  name: SyntheticBannerName\n  startup_catchphrase: ""\n---\n',
                '---\ncore: [\n---\n', '# No frontmatter\nSyntheticIgnoredBody\n'):
            with self.subTest(content=content):
                self.assistant.write_text(content)
                raw = self.original('--design=navy')
                self.assertEqual(raw.returncode, 0, raw.stderr)
                self.assertEqual(raw.stderr, '')
                self.assertEqual(self.banner('--design=navy').stdout, raw.stdout)
        (self.root / 'LIFEOS/VERSION').unlink()
        (self.root / 'LIFEOS/ALGORITHM/LATEST').unlink()
        self.assertEqual(self.banner('--design=navy').stdout, self.original('--design=navy').stdout)

    def test_all_design_preview_and_unconfigured_behavior_keep_actual_output(self):
        self.seed()
        result = self.banner('--test')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout, self.original('--test').stdout)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').unlink()
        result = self.banner('--design=navy', context=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.original('--design=navy').stdout)

    def test_import_does_not_render_or_read_personal_identity(self):
        self.seed(name='<private>SyntheticBannerImportHidden</private>')
        script = 'await import(' + json.dumps(str(self.root / 'LIFEOS/TOOLS/Banner.ts')) + ');'
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, HOME=str(self.fixture.fixture.home), LIFEOS_MEMORY_INTERNAL='1', BUN_CONFIG_NO_AUTO_INSTALL='1'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')

    def test_redirected_invalid_and_excessive_identity_refuse(self):
        self.seed()
        raw = self.assistant.read_bytes()
        outside = self.fixture.fixture.home / 'synthetic-banner-outside.md'
        outside.write_bytes(raw)
        for mode in ('symlink', 'hardlink', 'utf8', 'oversize'):
            with self.subTest(mode=mode):
                self.assistant.unlink()
                if mode == 'symlink': self.assistant.symlink_to(outside)
                elif mode == 'hardlink': os.link(outside, self.assistant)
                elif mode == 'utf8': self.assistant.write_bytes(raw + b'\xff')
                else: self.assistant.write_bytes(raw + b'x' * (256 * 1024))
                result = self.banner('--design=navy')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('SyntheticBannerName', result.stdout + result.stderr)

    def test_actual_native_render_rechecks_source_identity_absence_inventory_and_authority(self):
        from lifeos_hook_bridge import memory_banner as module
        from lifeos_hook_bridge.memory_access import MemoryUnavailable, MemoryConflict
        from lifeos_hook_bridge.memory_service import MemoryService
        self.seed()
        service = MemoryService(self.fixture.configuration)
        configuration = self.fixture.configuration.path.read_bytes()
        memory = self.fixture.fixture.memory
        original = memory._native
        for mode in ('bytes', 'inode', 'mtime', 'created', 'counts', 'authority'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                self.seed()
                self.settings.write_text('{}')
                if mode == 'created': self.assistant.unlink()
                admitted_configuration = self.fixture.configuration.load()
                scope = service.scope(self.fixture.context)
                observed = []
                def observe(action, **values):
                    result = original(action, **values)
                    if action == 'banner_view':
                        self.assertIn('SyntheticBannerName' if mode != 'created' else 'LifeOS', result['stdout'])
                        observed.append(True)
                        if mode == 'bytes': self.assistant.write_text(self.assistant.read_text() + '\nSyntheticChangedSource\n')
                        elif mode == 'inode':
                            replacement = self.assistant.with_suffix('.replacement')
                            replacement.write_bytes(self.assistant.read_bytes())
                            os.replace(replacement, self.assistant)
                        elif mode == 'mtime':
                            before = self.assistant.stat()
                            os.utime(self.assistant, ns=(before.st_atime_ns, before.st_mtime_ns + 1000000))
                        elif mode == 'created': self.assistant.write_text('---\ncore:\n  name: NewlyCreatedBannerName\n---\n')
                        elif mode == 'counts': self.settings.write_text('{"hooks":{"Stop":[{"hooks":[{"command":"SyntheticChangedHook"}]}]}}')
                        else: self.fixture.configuration.update(lambda config: config['accounts'].clear())
                    return result
                memory._native = observe
                try:
                    with self.assertRaises((MemoryUnavailable, MemoryConflict)):
                        module.run(memory, scope, args=['--design=navy'], width=100,
                            check_current=lambda: service._check_current_context(admitted_configuration, self.fixture.context, scope))
                finally: memory._native = original
                self.assertEqual(observed, [True])

    def test_exact_review_preserves_safe_old_identity_and_version_sources(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        from lifeos_hook_bridge.memory_service import MemoryService
        from lifeos_hook_bridge.memory_banner import SOURCES
        self.seed()
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticUnrelatedBannerRetirement',
            title='', project='', request_id='banner-review-save')
        memory.forget(OWNER, saved['reference'], 'banner-review-forget')
        paths = sorted(SOURCES)
        for relative in paths: os.utime(self.root / relative, (1577836800, 1577836800))
        before = [((self.root / path).read_bytes(), (self.root / path).stat().st_mtime_ns) for path in paths]
        self.assertNotEqual(self.banner('--design=navy').returncode, 0)
        service = MemoryService(self.fixture.configuration)
        configuration = self.fixture.configuration.load()
        scope = service.scope(self.fixture.context)
        snapshot = preview(memory, scope, paths)
        self.assertTrue(all(row['accepted'] for row in snapshot['sources']), snapshot)
        receipt = approve(memory, scope, paths, snapshot['signature'],
            check_current=lambda: service._check_current_context(configuration, self.fixture.context, scope))
        self.assertEqual(receipt['status'], 'committed', receipt)
        result = self.banner('--design=navy')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SyntheticBannerName', result.stdout)
        self.assertEqual([((self.root / path).read_bytes(), (self.root / path).stat().st_mtime_ns) for path in paths], before)

    def test_source_review_refuses_yaml_escaped_private_catchphrase(self):
        from lifeos_hook_bridge.memory_source_review import preview
        from lifeos_hook_bridge.memory_service import MemoryService
        self.seed(phrase='\\u003cprivate\\u003eSyntheticBannerReviewHidden\\u003c/private\\u003e')
        self.assistant.write_text(self.assistant.read_text().replace('\\\\u', '\\u'))
        memory = self.fixture.fixture.memory
        scope = MemoryService(self.fixture.configuration).scope(self.fixture.context)
        result = preview(memory, scope, ['LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'])
        self.assertFalse(result['sources'][0]['accepted'], result)

    def test_source_review_refuses_yaml_escaped_identity_controls(self):
        from lifeos_hook_bridge.memory_source_review import preview
        from lifeos_hook_bridge.memory_service import MemoryService
        self.seed(phrase='\\u001b[31mSyntheticBannerControlHidden\\u001b[0m')
        self.assistant.write_text(self.assistant.read_text().replace('\\\\u', '\\u'))
        memory = self.fixture.fixture.memory
        scope = MemoryService(self.fixture.configuration).scope(self.fixture.context)
        result = preview(memory, scope, ['LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'])
        self.assertFalse(result['sources'][0]['accepted'], result)
        rendered = self.banner('--design=navy')
        self.assertNotEqual(rendered.returncode, 0)
        self.assertNotIn('SyntheticBannerControlHidden', rendered.stdout + rendered.stderr)

    def test_small_layout_still_admits_the_complete_decoded_identity(self):
        self.seed(phrase='\\u003cprivate\\u003eSyntheticBannerSmallHidden\\u003c/private\\u003e')
        self.assistant.write_text(self.assistant.read_text().replace('\\\\u', '\\u'))
        for design in ('navy-compact', 'navy-minimal', 'navy-ultra'):
            with self.subTest(design=design):
                result = self.banner('--design=' + design)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('SyntheticBannerName', result.stdout + result.stderr)

    def test_read_only_owner_retains_banner_without_source_publication(self):
        self.seed()
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(write=[]))
        before = (self.assistant.read_bytes(), self.assistant.stat().st_mtime_ns)
        result = self.banner('--design=navy')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout, self.original('--design=navy').stdout)
        self.assertEqual((self.assistant.read_bytes(), self.assistant.stat().st_mtime_ns), before)

    def test_bounded_selectors_cannot_choose_arbitrary_sources(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        self.seed()
        service = MemoryService(self.fixture.configuration)
        for args, width in ((None, 100), (['--path=' + str(self.assistant)], 100), (['--design=other'], 100),
                ([], False), ([], 0), ([], 1025), (['--test', '--test'], 100)):
            with self.subTest(args=args, width=width):
                result = service.native(self.fixture.context, 'banner', {'args': args, 'width': width})
                self.assertFalse(result['ok'], result)
                self.assertNotIn('SyntheticBannerName', json.dumps(result))


if __name__ == '__main__': unittest.main()
