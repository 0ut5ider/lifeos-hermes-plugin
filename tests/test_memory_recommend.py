# ABOUTME: Runs the native recommendation command with admitted and unbound disposable sources.
# ABOUTME: Preserves actual ranking and output while checking complete owner source admission.
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_manual_state as state_fixture
from test_memory_native import OWNER


class MemoryRecommendTests(unittest.TestCase):
    setUp = state_fixture.MemoryManualStateTests.setUp
    call = state_fixture.MemoryManualStateTests.call

    def seed(self, marker='SyntheticRecommendCurrent'):
        self.restaurant = self.directory.parent / 'RESTAURANTS.md'
        self.restaurant.write_text('# Restaurants\n- name: "' + marker + '"\n  cuisine: thai\n  rating: 9\n'
            '- name: "SyntheticRecommendOther"\n  cuisine: french\n  rating: 4\n'
            '## Blocklist\n- name: "SyntheticRecommendBlocked"\n  cuisine: thai\n  rating: 10\n')
        self.consumption = self.directory / 'CONSUMPTION.md'
        self.consumption.write_text('# Consumption\n- name: "' + marker + '"\n  category: restaurant\n  visited: 2000-01-01\n')
        self.movie = self.directory.parent / 'MOVIES.md'
        self.movie.write_text('# Movies\n- name: "SyntheticMovieName"\n  title: SyntheticMovieTitle\n  genre: sci-fi\n  rating: 8\n')
        self.book = self.directory.parent / 'BOOKS.md'
        self.book.write_text('# Books\n- name: "SyntheticBookName"\n  title: SyntheticBookTitle\n  themes: philosophy\n  rating: 7\n')

    def original(self, *args):
        tool = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/Recommend.ts'
        env = dict(os.environ, HOME=str(self.fixture.fixture.home), LIFEOS_DIR=str(self.root / 'LIFEOS'),
            LIFEOS_MEMORY_INTERNAL='1', BUN_CONFIG_NO_AUTO_INSTALL='1')
        return subprocess.run(['bun', '--no-install', str(tool), *args], capture_output=True, text=True,
            timeout=40, env=env, cwd=self.fixture.fixture.home)

    def recommend(self, category='restaurant', *args, context=True):
        return self.call('Recommend.ts', '--category', category, *args, context=context)

    def test_native_categories_filters_blocklist_and_output_characterization(self):
        self.seed()
        for category, args, name in [('restaurant', ['--cuisine', 'thai'], 'SyntheticRecommendCurrent'),
                ('movie', ['--genre', 'sci-fi'], 'SyntheticMovieTitle'),
                ('book', ['--theme', 'philosophy'], 'SyntheticBookTitle')]:
            with self.subTest(category=category):
                raw = self.original('--category', category, *args, '--json')
                self.assertEqual(raw.returncode, 0, raw.stderr)
                self.assertEqual(raw.stderr, '')
                rows = json.loads(raw.stdout)
                self.assertEqual([row['name'] for row in rows], [name])
                governed = self.recommend(category, *args, '--json')
                self.assertEqual(governed.returncode, 0, governed.stderr)
                self.assertEqual(governed.stderr, '')
                self.assertEqual(json.loads(governed.stdout), rows)
                human = self.recommend(category, *args)
                self.assertEqual(human.returncode, 0, human.stderr)
                self.assertEqual(human.stdout, self.original('--category', category, *args).stdout)

    def test_native_missing_and_unseeded_movie_entry_characterization(self):
        self.seed()
        self.movie.write_text('# Movies\n- title: SyntheticIgnoredTitle\n  genre: sci-fi\n')
        self.assertEqual(json.loads(self.original('--category', 'movie', '--json').stdout), [])
        self.assertEqual(json.loads(self.recommend('movie', '--json').stdout), [])
        self.book.unlink()
        self.assertEqual(json.loads(self.recommend('book', '--json').stdout), [])
        result = self.recommend('book')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.original('--category', 'book').stdout)

    def test_unbound_reader_cannot_disclose_recommendation_or_consumption(self):
        self.seed()
        result = self.recommend('restaurant', '--json', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticRecommendCurrent', result.stdout + result.stderr)

    def test_private_selected_source_refuses_complete_recommendation(self):
        for selected in ('restaurant', 'consumption'):
            with self.subTest(selected=selected):
                self.seed()
                path = getattr(self, selected)
                path.write_text(path.read_text() + '\n<private>SyntheticRecommendHidden</private>\n')
                result = self.recommend('restaurant', '--json')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('SyntheticRecommendCurrent', result.stdout + result.stderr)
                self.assertNotIn('SyntheticRecommendHidden', result.stdout + result.stderr)

    def test_actual_retirement_refuses_retained_preference_and_recency(self):
        self.seed()
        saved = self.fixture.fixture.memory.remember(OWNER, category='principal', content='RULE: SyntheticRecommendCurrent',
            title='', project='', request_id='recommend-retained')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'recommend-forget')
        result = self.recommend('restaurant', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticRecommendCurrent', result.stdout + result.stderr)

    def test_redirected_invalid_and_excessive_source_cannot_use_raw_fallback(self):
        self.seed()
        original = self.restaurant.read_bytes()
        outside = self.fixture.fixture.home / 'synthetic-recommend-outside.md'
        outside.write_bytes(original)
        for mode in ('symlink', 'hardlink', 'utf8', 'oversize', 'connector'):
            with self.subTest(mode=mode):
                self.restaurant.unlink()
                if mode == 'symlink': self.restaurant.symlink_to(outside)
                elif mode == 'hardlink': os.link(outside, self.restaurant)
                elif mode == 'utf8': self.restaurant.write_bytes(original + b'\xff')
                elif mode == 'oversize': self.restaurant.write_bytes(original + b'x' * (256 * 1024))
                else:
                    self.restaurant.write_bytes(original)
                    (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
                result = self.recommend('restaurant', '--json')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('SyntheticRecommendCurrent', result.stdout + result.stderr)

    def test_selected_category_ignores_unrelated_private_preferences(self):
        self.seed()
        self.book.write_text('<private>SyntheticUnselectedBook</private>')
        result = self.recommend('restaurant', '--cuisine', 'thai', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]['name'], 'SyntheticRecommendCurrent')
        self.assertNotIn('SyntheticUnselectedBook', result.stdout)

    def test_revoked_owner_cannot_disclose(self):
        self.seed()
        self.fixture.configuration.update(lambda config: config['accounts'].clear())
        result = self.recommend('restaurant', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticRecommendCurrent', result.stdout + result.stderr)

    def test_actual_native_render_withholds_changed_source_identity_absence_or_authority(self):
        from lifeos_hook_bridge import memory_recommend as module
        from lifeos_hook_bridge.memory_access import MemoryUnavailable, MemoryConflict
        from lifeos_hook_bridge.memory_service import MemoryService
        self.seed()
        service = MemoryService(self.fixture.configuration)
        configuration = self.fixture.configuration.path.read_bytes()
        original = module.render
        for mode in ('bytes', 'inode', 'mtime', 'created', 'authority'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                self.seed()
                if mode == 'created': self.consumption.unlink()
                admitted_configuration = self.fixture.configuration.load()
                scope = service.scope(self.fixture.context)
                observed = []
                def observe(memory, args, contents):
                    output = original(memory, args, contents)
                    self.assertIn('SyntheticRecommendCurrent', output)
                    observed.append(True)
                    if mode == 'bytes': self.restaurant.write_text(self.restaurant.read_text() + '\nSyntheticChangedSource\n')
                    elif mode == 'inode':
                        replacement = self.restaurant.with_suffix('.replacement')
                        replacement.write_bytes(self.restaurant.read_bytes())
                        os.replace(replacement, self.restaurant)
                    elif mode == 'mtime':
                        before = self.restaurant.stat()
                        os.utime(self.restaurant, ns=(before.st_atime_ns, before.st_mtime_ns + 1000000))
                    elif mode == 'created': self.consumption.write_text('# Newly present consumption\n')
                    else: self.fixture.configuration.update(lambda config: config['accounts'].clear())
                    return output
                module.render = observe
                try:
                    with self.assertRaises((MemoryUnavailable, MemoryConflict)):
                        module.run(self.fixture.fixture.memory, scope, args=['--category', 'restaurant', '--json'],
                            check_current=lambda: service._check_current_context(admitted_configuration, self.fixture.context, scope))
                finally: module.render = original
                self.assertEqual(observed, [True])

    def test_native_picker_keeps_source_bytes_and_timestamps(self):
        self.seed()
        paths = [self.restaurant, self.consumption, self.movie, self.book]
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
        for category in ('restaurant', 'movie', 'book'):
            result = self.recommend(category, '--json')
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in paths], before)

    def test_exact_source_review_admits_safe_old_preferences_without_rewriting(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        from lifeos_hook_bridge.memory_service import MemoryService
        self.seed()
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticUnrelatedRecommendRetirement',
            title='', project='', request_id='recommend-review-save')
        memory.forget(OWNER, saved['reference'], 'recommend-review-forget')
        paths = ['LIFEOS/USER/TELOS/RESTAURANTS.md', 'LIFEOS/USER/TELOS/CURRENT_STATE/CONSUMPTION.md']
        for relative in paths: os.utime(self.root / relative, (1577836800, 1577836800))
        before = [((self.root / path).read_bytes(), (self.root / path).stat().st_mtime_ns) for path in paths]
        self.assertNotEqual(self.recommend('restaurant', '--json').returncode, 0)
        service = MemoryService(self.fixture.configuration)
        configuration = self.fixture.configuration.load()
        scope = service.scope(self.fixture.context)
        snapshot = preview(memory, scope, paths)
        self.assertTrue(all(row['accepted'] for row in snapshot['sources']), snapshot)
        result = approve(memory, scope, paths, snapshot['signature'],
            check_current=lambda: service._check_current_context(configuration, self.fixture.context, scope))
        self.assertEqual(result['status'], 'committed', result)
        result = self.recommend('restaurant', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SyntheticRecommendCurrent', result.stdout)
        self.assertEqual([((self.root / path).read_bytes(), (self.root / path).stat().st_mtime_ns) for path in paths], before)

    def test_invalid_or_repeated_selector_cannot_choose_arbitrary_sources(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        self.seed()
        service = MemoryService(self.fixture.configuration)
        for args in (None, [], [['restaurant']], ['--category', 'invalid'], ['--category', 'restaurant', '--path', str(self.book)],
                ['--category', 'restaurant', '--category', 'book'], ['--category', 'book', '--json', '--json'],
                ['--category', 'restaurant', '--cuisine'], ['--category', 'restaurant', '--cuisine', 'x' * 257]):
            with self.subTest(args=args):
                result = service.native(self.fixture.context, 'recommend', {'args': args})
                self.assertFalse(result['ok'], result)
                self.assertNotIn('SyntheticRecommendCurrent', json.dumps(result))

    def test_read_only_owner_can_recommend_without_publication(self):
        self.seed()
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(write=[]))
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in (self.restaurant, self.consumption)]
        result = self.recommend('restaurant', '--cuisine', 'thai', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]['name'], 'SyntheticRecommendCurrent')
        self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in (self.restaurant, self.consumption)], before)

    def test_unconfigured_command_keeps_original_native_behavior(self):
        self.seed()
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').unlink()
        result = self.recommend('restaurant', '--cuisine', 'thai', '--json', context=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), json.loads(self.original('--category', 'restaurant', '--cuisine', 'thai', '--json').stdout))


if __name__ == '__main__': unittest.main()
