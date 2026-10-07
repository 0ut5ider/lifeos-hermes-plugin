# ABOUTME: Exercises native freshness reads with synthetic current owner sources.
# ABOUTME: Verifies native grades and dates without exposing excluded text or redirected files.
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER


class MemoryFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.memory = self.fixture.fixture.memory
        self.source('LIFEOS/USER/TELOS/TELOS.md',
            '# Synthetic TELOS\n## Mission\n<!-- updated: 2026-10-01 by:synthetic -->\n'
            'Synthetic freshness mission\n## Goals\nSynthetic freshness goal\n')
        self.source('LIFEOS/USER/TELOS/GOALS.md', 'Synthetic legacy goal\n')
        self.source('LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md', '# Synthetic assistant\n')
        self.source('LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md', '# Synthetic principal\n')
        self.source('LIFEOS/USER/PROJECTS.md', '# Synthetic projects\n')
        self.source('LIFEOS/LIFEOS_SYSTEM_PROMPT.md', '# Synthetic system\n')
        self.source('LIFEOS/DOCUMENTATION/LifeosSystemArchitecture.md', '# Synthetic architecture\n')
        self.source('LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md', '# Synthetic architecture summary\n')
        self.source('LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md', '# Synthetic principal summary\n')
        self.source('LIFEOS/USER/TELOS/CURRENT_STATE/SYNTHETIC_CUSTOM.md', '# Synthetic custom dimension\n',
                    extra='review_cadence: 11d\n')
        self.source('LIFEOS/USER/TELOS/IDEAL_STATE/HEALTH.md', '# Synthetic ideal health\n')

    def source(self, relative, body, *, extra='', reviewed='2026-10-01'):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\nlast_updated: 2026-10-02\nlast_reviewed: ' + reviewed
            + '\nlast_reviewed_by: synthetic-owner\n' + extra + '---\n' + body)
        return path

    def environment(self, *, context=True):
        env = dict(os.environ, HOME=str(self.fixture.fixture.home),
            LIFEOS_DIR=str(self.root / 'LIFEOS'), BUN_CONFIG_NO_AUTO_INSTALL='1', TZ='UTC')
        for name in ('LIFEOS_MEMORY_INTERNAL', 'LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_ADMINISTRATION'):
            env.pop(name, None)
        if context:
            env['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return env

    def call(self, *args, context=True):
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/TelosFreshness.ts'), *args],
            env=self.environment(context=context), capture_output=True, text=True, timeout=30)

    def successful(self, *args):
        result = self.call(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def library(self, function, *args, context=True, check_dates=False):
        module = self.root / 'LIFEOS/TOOLS/TelosFreshness.ts'
        program = 'const m=await import(process.argv[1]); const value=m[process.argv[2]](...JSON.parse(process.argv[3]));'
        if check_dates:
            program += 'if(!(value.fileUpdated instanceof Date) || !(value.sections[0].updated instanceof Date)) throw new Error("Native Date objects are missing");'
        program += 'console.log(JSON.stringify(value));'
        return subprocess.run(['bun', '--no-install', '-e', program, str(module), function, json.dumps(args)],
            env=self.environment(context=context), capture_output=True, text=True, timeout=30)

    def test_owner_preserves_native_cli_shapes_and_review_grades(self):
        telos = json.loads(self.successful('--json').stdout)
        self.assertEqual(telos['totalSections'], 2)
        self.assertEqual(telos['sections'][0]['preview'], 'Synthetic freshness mission')
        self.assertEqual(telos['sections'][1]['updated'], '2026-10-02T00:00:00.000Z')
        context = json.loads(self.successful('--context').stdout)
        self.assertEqual(context['total'], 8)
        self.assertTrue(all(row['grade'] == 'A' for row in context['files']))
        state = json.loads(self.successful('--state').stdout)
        self.assertEqual(state['total'], 2)
        custom = next(row for row in state['files'] if row['slug'] == 'current_state_synthetic_custom')
        self.assertEqual(custom['threshold_days'], 11)
        self.assertEqual(custom['reviewed_by'], 'synthetic-owner')
        self.assertIn('Mission', self.successful().stdout)

    def test_owner_and_standalone_cli_outputs_match(self):
        managed = {mode: self.successful(mode).stdout for mode in ('--json', '--context', '--state')}
        human = self.successful().stdout
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        for mode, output in managed.items():
            with self.subTest(mode=mode):
                own, original = json.loads(output), json.loads(self.call(mode, context=False).stdout)
                own.pop('generated_at', None); original.pop('generated_at', None)
                self.assertEqual(own, original)
        self.assertEqual(self.call(context=False).stdout, human)

    def test_native_library_keeps_date_objects(self):
        result = self.library('readTelosFreshness', check_dates=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')

    def test_missing_context_refuses_all_cli_reads(self):
        for mode in ('--json', '--context', '--state'):
            with self.subTest(mode=mode):
                result = self.call(mode, context=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Synthetic', result.stdout)

    def test_revoked_and_restricted_owner_cannot_read_unclassified_sources(self):
        self.fixture.configuration.update(lambda c: c['destinations']['chat-a:200'].update(
            read=['project'], projects=['lab']))
        restricted = self.call('--json')
        self.assertNotEqual(restricted.returncode, 0)
        self.assertNotIn('Synthetic freshness mission', restricted.stdout)
        self.fixture.configuration.update(lambda c: c['accounts'].pop('chat-a:100'))
        revoked = self.call('--context')
        self.assertNotEqual(revoked.returncode, 0)
        self.assertNotIn('Synthetic', revoked.stdout)

    def retired(self, marker):
        return self.memory.remember(OWNER, category='principal', content='RULE: ' + marker,
            title='', project='', request_id='freshness-retired')['reference']

    def test_retired_telos_does_not_restore_section_previews(self):
        marker = 'Synthetic retired freshness mission'
        reference = self.retired(marker)
        path = self.source('LIFEOS/USER/TELOS/TELOS.md', '# Synthetic TELOS\n## Mission\n' + marker + '\n')
        before = path.read_bytes()
        self.memory.forget(OWNER, reference, 'freshness-forget')
        body = json.loads(self.successful('--json').stdout)
        self.assertEqual(body['sections'], [])
        self.assertTrue(body['hasStale'])
        self.assertEqual(path.read_bytes(), before)

    def test_excluded_state_dimension_body_and_label_leave_dynamic_registry(self):
        marker = 'Synthetic retired dimension'
        reference = self.retired(marker)
        self.source('LIFEOS/USER/TELOS/CURRENT_STATE/Synthetic-retired-dimension.md', '# Unrelated clean body\n')
        self.memory.forget(OWNER, reference, 'freshness-state-forget')
        # Rewrite a clean dimension after retirement so its current timestamp is admitted.
        self.source('LIFEOS/USER/TELOS/CURRENT_STATE/SYNTHETIC_CUSTOM.md', '# Synthetic custom current\n')
        body = json.loads(self.successful('--state').stdout)
        self.assertEqual([row['slug'] for row in body['files']], ['current_state_synthetic_custom'])
        self.assertNotIn(marker, json.dumps(body))

    def test_private_legacy_source_cannot_date_an_admitted_section(self):
        self.source('LIFEOS/USER/TELOS/GOALS.md', '<private>SYNTHETIC_PRIVATE_LEGACY</private>\n')
        body = json.loads(self.successful('--json').stdout)
        self.assertIsNone(body['sections'][1]['updated'])
        self.assertTrue(body['sections'][1]['stale'])

    def test_custom_dimension_source_can_receive_exact_owner_review(self):
        from lifeos_hook_bridge.memory_source_review import approve, preview
        reference = self.retired('Synthetic unrelated retirement')
        self.memory.forget(OWNER, reference, 'freshness-review-forget')
        relative = 'LIFEOS/USER/TELOS/CURRENT_STATE/SYNTHETIC_CUSTOM.md'
        plan = preview(self.memory, OWNER, [relative])
        self.assertTrue(plan['sources'][0]['accepted'])
        self.assertEqual(approve(self.memory, OWNER, [relative], plan['signature'])['status'], 'committed')
        body = json.loads(self.successful('--state').stdout)
        self.assertEqual(body['total'], 1)
        self.assertEqual(body['files'][0]['threshold_days'], 11)

    def test_foreign_source_link_refuses_before_content_delivery(self):
        path = self.root / 'LIFEOS/USER/TELOS/TELOS.md'
        foreign = self.fixture.fixture.home / 'foreign-freshness.md'
        foreign.write_text('# Synthetic foreign\n## Mission\nSYNTHETIC_FOREIGN_FRESHNESS\n')
        path.unlink(); path.symlink_to(foreign)
        result = self.call('--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SYNTHETIC_FOREIGN_FRESHNESS', result.stdout)

    def test_foreign_dimension_directory_refuses_before_collection(self):
        directory = self.root / 'LIFEOS/USER/TELOS/CURRENT_STATE'
        foreign = self.fixture.fixture.home / 'foreign-dimensions'
        directory.rename(foreign); directory.symlink_to(foreign)
        self.assertNotEqual(self.call('--state').returncode, 0)

    def test_missing_connector_durable_marker_refuses_after_restart(self):
        marker = self.root / 'LIFEOS/USER/CONFIG/memory-http.json'
        marker.write_text('{"version":1,"managed":true}')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = self.call('--json', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic', result.stdout)

    def test_direct_frontmatter_and_legacy_helpers_require_current_authority(self):
        for function, args in [
                ('readFileFrontmatter', [str(self.root / 'LIFEOS/USER/TELOS/TELOS.md')]),
                ('legacyTelosFilePath', ['goals']), ('legacyTelosFileDate', ['goals']),
                ('stateFreshnessRegistry', [])]:
            with self.subTest(function=function):
                result = self.library(function, *args, context=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('synthetic-owner', result.stdout)

    def test_legacy_mtime_fallback_preserves_native_date(self):
        path = self.root / 'LIFEOS/USER/TELOS/GOALS.md'
        path.write_text('Synthetic legacy body without frontmatter\n')
        instant = datetime(2026, 9, 30, 12, 1, 2, 123000, tzinfo=timezone.utc)
        os.utime(path, (instant.timestamp(), instant.timestamp()))
        body = json.loads(self.successful('--json').stdout)
        self.assertEqual(body['sections'][1]['updated'], '2026-09-30T12:01:02.123Z')

    def test_machine_write_clock_does_not_mark_principal_review_fresh(self):
        self.source('LIFEOS/USER/PROJECTS.md', '# Synthetic recently written projects\n', reviewed='2020-01-01')
        context = json.loads(self.successful('--context').stdout)
        row = next(row for row in context['files'] if row['slug'] == 'projects')
        self.assertTrue(row['stale'])
        self.assertEqual(row['grade'], 'F')
        self.assertLess(row['age_days'], row['reviewed_age_days'])

    def test_all_native_legacy_freshness_sections_keep_frontmatter_dates(self):
        names = {'Mission': 'MISSION', 'Goals': 'GOALS', 'Problems': 'PROBLEMS',
            'Strategies': 'STRATEGIES', 'Challenges': 'CHALLENGES', 'Narratives': 'NARRATIVES',
            'Traumas': 'TRAUMAS', 'Wrong': 'WRONG', 'Models': 'MODELS', 'Beliefs': 'BELIEFS',
            'Frames': 'FRAMES', 'Wisdom': 'WISDOM', 'Predictions': 'PREDICTIONS', 'Ideas': 'IDEAS',
            'Sparks': 'SPARKS', 'Books': 'BOOKS', 'Authors': 'AUTHORS', 'Bands': 'BANDS',
            'Movies': 'MOVIES', 'Restaurants': 'RESTAURANTS', 'Food': 'FOOD_PREFERENCES',
            'Meetups': 'MEETUPS', 'Civic': 'CIVIC', 'Learning Interests': 'LEARNING', 'Team': 'TEAM'}
        self.source('LIFEOS/USER/TELOS/TELOS.md', '# Synthetic legacy index\n'
            + ''.join('## ' + heading + '\nSynthetic index preview\n' for heading in names))
        for heading, filename in names.items():
            self.source('LIFEOS/USER/TELOS/' + filename + '.md', 'Synthetic legacy ' + heading + '\n')
        body = json.loads(self.successful('--json').stdout)
        self.assertEqual(body['totalSections'], 25)
        self.assertEqual({row['updated'] for row in body['sections']}, {'2026-10-02T00:00:00.000Z'})

    def test_missing_telos_keeps_native_empty_freshness_shape(self):
        (self.root / 'LIFEOS/USER/TELOS/TELOS.md').unlink()
        body = json.loads(self.successful('--json').stdout)
        self.assertEqual(body['totalSections'], 0)
        self.assertEqual(body['staleSections'], [])
        self.assertIsNone(body['fileUpdated'])
        self.assertTrue(body['hasStale'])

    def test_state_registry_excludes_documentation_and_nested_files(self):
        for name in ('README.md', 'INDEX.md', 'nested/dimension.md'):
            self.source('LIFEOS/USER/TELOS/CURRENT_STATE/' + name, '# Synthetic structure\n')
        body = json.loads(self.successful('--state').stdout)
        self.assertEqual(body['total'], 2)
        self.assertEqual({row['slug'] for row in body['files']},
                         {'current_state_synthetic_custom', 'ideal_state_health'})

    def test_private_system_source_cannot_supply_review_metadata(self):
        self.source('LIFEOS/DOCUMENTATION/LifeosSystemArchitecture.md',
                    '<private>SYNTHETIC_PRIVATE_ARCHITECTURE</private>\n')
        body = json.loads(self.successful('--context').stdout)
        for row in body['files']:
            if row['slug'] in ('architecture_summary', 'lifeos_system_architecture'):
                self.assertIsNone(row['effective_reviewed'])
                self.assertEqual(row['grade'], 'F')
        self.assertNotIn('SYNTHETIC_PRIVATE_ARCHITECTURE', json.dumps(body))

    def test_owner_read_without_write_can_read_freshness(self):
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(write=[]))
        body = json.loads(self.successful('--json').stdout)
        self.assertEqual(body['totalSections'], 2)

    def test_registry_source_alias_refuses_without_damaging_current_facts(self):
        saved = self.fixture.fixture.remember('Synthetic freshness registry guard', 'freshness-alias')
        path = self.root / 'LIFEOS/USER/TELOS/TELOS.md'
        path.unlink(); os.link(self.memory.database, path)
        self.assertNotEqual(self.call('--json').returncode, 0)
        self.assertEqual(self.memory.get(OWNER, saved['reference'])['content'], 'Synthetic freshness registry guard')

    def test_direct_helper_cannot_read_configuration_outside_freshness_sources(self):
        path = self.root / 'LIFEOS/USER/CONFIG/synthetic-private.md'
        path.write_text('---\nsynthetic_secret: SYNTHETIC_FRESHNESS_CONFIGURATION\n---\n')
        result = self.library('readFileFrontmatter', str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SYNTHETIC_FRESHNESS_CONFIGURATION', result.stdout)
