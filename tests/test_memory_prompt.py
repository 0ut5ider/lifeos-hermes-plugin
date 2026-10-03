# ABOUTME: Pairs native prompt formatting with governed source collection and publication.
# ABOUTME: Exercises actual Bun renderers against synthetic identity, skills, and current facts.
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from test_memory_native import OWNER, SOURCE
import test_memory_delegation as delegation


class MemoryPromptTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.fixture.memory
        self.root = self.fixture.root
        shutil.copytree(SOURCE / 'LIFEOS/HERMES', self.root / 'LIFEOS/HERMES')
        self.sources = {
            'systemPrompt': '# Synthetic constitution\n## Safety\nSyntheticSafetyDoctrine\n## Output Format (CONSTITUTIONAL №1)\nSyntheticBanner\n',
            'daIdentity': '# Synthetic assistant\n**Name:** SyntheticAssistant\n## Personality\nSyntheticPersonality\n## Writing Style\nPlain words\n',
            'principal': '# Synthetic principal\n## Quick Reference\n- SyntheticPrincipal\n',
            'telos': '# Synthetic goals\n## Missions\nSyntheticMission\n',
            'projects': '| **SyntheticProject** | active |\n',
        }
        locations = {'systemPrompt': 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md',
            'daIdentity': 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md',
            'principal': 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md',
            'telos': 'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md', 'projects': 'LIFEOS/USER/PROJECTS.md'}
        for name, relative in locations.items():
            self.write(relative, self.sources[name])
        self.skill = self.write('skills/SyntheticSkill/SKILL.md',
            '---\nname: SyntheticSkill\ndescription: Synthetic skill summary. USE WHEN synthetic.\n---\n# Skill body\n')
        self.connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def native(self, *, managed=True, context=True, declared=False, options=None, sources=None):
        wire = {'declared': declared, 'options': options or {}, 'sources': sources or self.sources,
                'skills': [{'directory': 'SyntheticSkill', 'content': '---\nname: SyntheticSkill\ndescription: Synthetic skill summary. USE WHEN synthetic.\n---\n'}]}
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        if not managed:
            environment['LIFEOS_MEMORY_INTERNAL'] = '1'
        result = subprocess.run([self.memory.bun, '--no-install', str(Path(__file__).with_name('native_soul_calls.ts')), str(self.root)],
            input=json.dumps(wire), text=True, capture_output=True, cwd=self.root, env=environment, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_standalone_formatter_characterization(self):
        rendered = self.native(managed=False)
        self.assertTrue(rendered['ok'], rendered)
        self.assertIn('SyntheticSafetyDoctrine', rendered['soul'])
        self.assertIn('SyntheticPersonality', rendered['soul'])
        self.assertIn('SyntheticMission', rendered['soul'])
        self.assertIn('SyntheticProject', rendered['soul'])
        self.assertIn('Synthetic skill summary', rendered['soul'])
        self.assertNotIn('SyntheticBanner', rendered['soul'])
        self.assertIn('SyntheticBanner', self.native(managed=False, options={'keepOutputFormat': True})['soul'])
        self.assertEqual(rendered['launcherName'], 'SyntheticAssistant')

    def test_managed_renderer_has_no_raw_fallback_without_context(self):
        result = self.native(context=False)
        self.assertFalse(result['ok'], result)
        self.assertNotIn('SyntheticPersonality', json.dumps(result))

    def test_declared_renderer_matches_standalone_without_reopening_sources(self):
        control = self.native(managed=False)
        sources = {**self.sources, 'principalMemory': '', 'daMemory': ''}
        self.write('LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md', '# UnauthorizedChangedIdentity\n')
        declared = self.native(declared=True, sources=sources)
        self.assertTrue(declared['ok'], declared)
        self.assertEqual(declared, control)

    def test_current_owner_renderer_preserves_native_prompt_and_current_hot_facts(self):
        saved = self.memory.remember(OWNER, category='principal', content='RULE: SyntheticCurrentHotFact',
            title='', project='', request_id='prompt-hot')
        self.assertEqual(saved['status'], 'committed', saved)
        control = self.native(managed=False)
        governed = self.native()
        self.assertEqual(governed, control)
        self.assertIn('SyntheticCurrentHotFact', governed['soul'])

    def test_forgotten_identity_is_not_carried_into_a_new_prompt(self):
        saved = self.memory.remember(OWNER, category='principal', content='RULE: SyntheticPersonality',
            title='', project='', request_id='identity')
        self.memory.forget(OWNER, saved['reference'], 'identity-forgotten')
        # Retained sources that predate retirement require review. Refresh only the safe constitution.
        self.write('LIFEOS/LIFEOS_SYSTEM_PROMPT.md', self.sources['systemPrompt'])
        rendered = self.native()
        self.assertTrue(rendered['ok'], rendered)
        self.assertNotIn('SyntheticPersonality', json.dumps(rendered))
        self.assertIn('SyntheticSafetyDoctrine', rendered['soul'])
        self.assertIn('SyntheticPersonality', (self.root / 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md').read_text())

    def test_private_skill_metadata_is_absent_from_routing(self):
        self.skill.write_text('---\nname: SyntheticPrivateSkill\ndescription: <private>SyntheticPrivateDescription</private>\n---\n')
        rendered = self.native()
        self.assertTrue(rendered['ok'], rendered)
        self.assertNotIn('SyntheticPrivate', json.dumps(rendered))

    def preferences(self):
        from lifeos_hook_bridge.memory_preferences import MemoryPreferences
        self.fixture.configuration.update(lambda value: value['accounts'].update({'dashboard:owner': 'owner'}))
        return MemoryPreferences(self.fixture.configuration.path, self.root,
            self.fixture.fixture.home / 'keys', Path('/usr/bin/python3'), Path(__file__).parents[1] / 'lifeos_hook_bridge/memory_mcp.py')

    def test_owner_publication_has_a_fixed_destination_and_idempotent_retry(self):
        preferences = self.preferences()
        preview = preferences.preview_prompt(account='dashboard:owner')
        self.assertEqual(preview['bundle'], {key: value for key, value in self.native().items() if key != 'ok'})
        request = {key: preview[key] for key in ('signature', 'previous_digest')}
        request['keep_output_format'] = False
        receipt = preferences.publish_prompt(request, account='dashboard:owner')
        self.assertEqual(receipt['status'], 'committed', receipt)
        soul = self.fixture.configuration.path.parent / 'SOUL.md'
        self.assertEqual(soul.read_text(), preview['bundle']['soul'])
        self.assertEqual(soul.stat().st_mode & 0o777, 0o600)
        self.assertEqual(preferences.publish_prompt(request, account='dashboard:owner')['status'], 'unchanged')
        self.assertFalse(self.fixture.configuration.load().get('ownership_enabled', False))

    def test_stale_source_preview_cannot_publish(self):
        preferences = self.preferences()
        preview = preferences.preview_prompt(account='dashboard:owner')
        self.write('LIFEOS/USER/PROJECTS.md', '| **SyntheticLaterProject** | active |\n')
        receipt = preferences.publish_prompt({key: preview[key] for key in ('signature','previous_digest')} |
            {'keep_output_format': False}, account='dashboard:owner')
        self.assertEqual(receipt['status'], 'conflict')
        self.assertFalse((self.fixture.configuration.path.parent / 'SOUL.md').exists())

    def test_stale_destination_preview_preserves_the_later_prompt(self):
        preferences = self.preferences()
        preview = preferences.preview_prompt(account='dashboard:owner')
        soul = self.fixture.configuration.path.parent / 'SOUL.md'
        soul.write_text('SyntheticLaterPrompt')
        receipt = preferences.publish_prompt({key: preview[key] for key in ('signature','previous_digest')} |
            {'keep_output_format': False}, account='dashboard:owner')
        self.assertEqual(receipt['status'], 'conflict')
        self.assertEqual(soul.read_text(), 'SyntheticLaterPrompt')

    def test_non_owner_cannot_preview_or_publish_private_prompt(self):
        preferences = self.preferences()
        with self.assertRaises(PermissionError):
            preferences.preview_prompt(account='dashboard:other')
        with self.assertRaises(PermissionError):
            preferences.publish_prompt({'signature': 'a' * 64, 'previous_digest': 'absent',
                'keep_output_format': False}, account='dashboard:other')

    def test_prompt_destination_redirect_is_refused(self):
        preferences = self.preferences()
        target = self.fixture.fixture.home / 'synthetic-other-file'
        target.write_text('PreserveSyntheticTarget')
        (self.fixture.configuration.path.parent / 'SOUL.md').symlink_to(target)
        with self.assertRaises(RuntimeError):
            preferences.preview_prompt(account='dashboard:owner')
        self.assertEqual(target.read_text(), 'PreserveSyntheticTarget')

    def mount(self, *, context=True, check=False):
        profile = self.fixture.configuration.path.parent
        if not (profile / 'config.yaml').exists():
            (profile / 'config.yaml').write_text('model: synthetic\n')
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), HERMES_HOME=str(profile),
            HERMES_WORKSPACE=str(self.fixture.fixture.home / 'workspace'), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run([self.memory.bun, '--no-install', str(self.root / 'LIFEOS/HERMES/Mount.ts'),
            *(['--check'] if check else [])], text=True, capture_output=True, cwd=self.root, env=environment, timeout=45)

    def test_actual_mount_publishes_the_admitted_bundle_and_policy_name(self):
        control = self.native()
        result = self.mount()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        profile = self.fixture.configuration.path.parent
        self.assertEqual((profile / 'SOUL.md').read_text(), control['soul'])
        self.assertEqual((profile / 'SOUL.md').stat().st_mode & 0o777, 0o600)
        policy = json.loads((profile / 'plugins/lifeos/policy.json').read_text())
        self.assertIn('syntheticassistant', policy['shellDenyGlobs'])
        result = self.mount(check=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_actual_mount_refuses_without_context_and_preserves_previous_prompt(self):
        soul = self.fixture.configuration.path.parent / 'SOUL.md'
        soul.write_text('SyntheticPreviousPrompt')
        result = self.mount(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unavailable under current memory policy', result.stderr)
        self.assertEqual(soul.read_text(), 'SyntheticPreviousPrompt')
        self.assertFalse((self.fixture.configuration.path.parent / 'plugins/lifeos').exists())

    def test_restricted_context_cannot_read_or_publish_an_owner_prompt(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(read=['project']))
        self.assertFalse(self.native()['ok'])
        result = self.mount()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.fixture.configuration.path.parent / 'SOUL.md').exists())

    def test_forgotten_fact_invalidates_a_reviewed_publication(self):
        saved = self.memory.remember(OWNER, category='principal', content='RULE: SyntheticCurrentPromptFact',
            title='', project='', request_id='publish-forget')
        preferences = self.preferences()
        preview = preferences.preview_prompt(account='dashboard:owner')
        self.memory.forget(OWNER, saved['reference'], 'publish-forgotten')
        # The constitution is unclassified and older than retirement. Publication must refuse review.
        with self.assertRaisesRegex(RuntimeError, 'constitution requires current source review'):
            preferences.publish_prompt({key: preview[key] for key in ('signature', 'previous_digest')} |
                {'keep_output_format': False}, account='dashboard:owner')
        self.assertFalse((self.fixture.configuration.path.parent / 'SOUL.md').exists())

    def test_skill_directory_alias_is_refused(self):
        directory = self.skill.parent
        self.skill.unlink()
        directory.rmdir()
        directory.symlink_to(self.root / 'LIFEOS/USER/CONFIG')
        rendered = self.native()
        self.assertFalse(rendered['ok'], rendered)

    def test_publication_refuses_a_profile_other_than_the_connector_profile(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        result = MemoryService(self.fixture.configuration).native(self.fixture.context, 'prompt_preview',
            {'home': str(self.fixture.fixture.home / 'other-profile'), 'keepOutputFormat': False})
        self.assertFalse(result['ok'])
        self.assertIn('configured Hermes profile', result['message'])

    def test_empty_write_grant_cannot_publish_a_prompt(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertTrue(self.native()['ok'])
        result = self.mount()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.fixture.configuration.path.parent / 'SOUL.md').exists())

    def test_authenticated_http_owner_previews_and_publishes_the_prompt(self):
        import importlib.util
        from unittest.mock import patch
        import warnings
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            from fastapi import FastAPI
            from test_memory_dashboard import owner_client
        self.assertTrue(all(issubclass(warning.category, DeprecationWarning) and
            'BlockingPortal alias is deprecated' in str(warning.message) for warning in recorded))
        from lifeos_hook_bridge.memory_service import MemoryConfiguration
        profile = self.fixture.configuration.path.parent
        MemoryConfiguration(profile / 'lifeos-memory.json').save(self.fixture.configuration.load())
        api_path = Path(__file__).parents[1] / 'lifeos_hook_bridge/dashboard/plugin_api.py'
        with patch.dict(os.environ, {'HOME': str(self.fixture.fixture.home), 'HERMES_HOME': str(profile)}):
            spec = importlib.util.spec_from_file_location('memory_dashboard_prompt_http', api_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            app = FastAPI()
            module.install_memory_cache_headers(app)
            app.include_router(module.router, prefix='/api/plugins/lifeos-hook-bridge')
            with owner_client(app, profile) as client:
                endpoint = '/api/plugins/lifeos-hook-bridge/memory/prompt'
                response = client.post(endpoint + '/preview', json={'keep_output_format': False})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIn('no-store', response.headers['Cache-Control'])
                preview = response.json()
                self.assertIn('SyntheticSafetyDoctrine', preview['bundle']['soul'])
                request = {key: preview[key] for key in ('signature', 'previous_digest')} | {'keep_output_format': False}
                response = client.post(endpoint, json=request)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['status'], 'committed')
                self.assertEqual((profile / 'SOUL.md').read_text(), preview['bundle']['soul'])
                self.assertEqual(client.post(endpoint, json=request | {'path': '/tmp/other'}).status_code, 409)

    def test_source_change_during_native_formatting_refuses_publication(self):
        from unittest.mock import patch
        from lifeos_hook_bridge.memory_access import NativeMemory
        preferences = self.preferences()
        preview = preferences.preview_prompt(account='dashboard:owner')
        original = NativeMemory._native
        def change_source(memory, action, **values):
            result = original(memory, action, **values)
            if action == 'prompt_bundle':
                self.write('LIFEOS/USER/PROJECTS.md', '| **SyntheticRacingProject** | active |\n')
            return result
        with patch.object(NativeMemory, '_native', change_source):
            with self.assertRaisesRegex(RuntimeError, 'sources changed during rendering'):
                preferences.publish_prompt({key: preview[key] for key in ('signature','previous_digest')} |
                    {'keep_output_format': False}, account='dashboard:owner')
        self.assertFalse((self.fixture.configuration.path.parent / 'SOUL.md').exists())

    def test_owner_revocation_during_formatting_refuses_publication(self):
        from unittest.mock import patch
        from lifeos_hook_bridge.memory_access import NativeMemory
        preferences = self.preferences()
        preview = preferences.preview_prompt(account='dashboard:owner')
        original = NativeMemory._native
        def revoke_owner(memory, action, **values):
            result = original(memory, action, **values)
            if action == 'prompt_bundle':
                self.fixture.configuration.update(lambda value: value['accounts'].pop('dashboard:owner'))
            return result
        with patch.object(NativeMemory, '_native', revoke_owner):
            with self.assertRaises(PermissionError):
                preferences.publish_prompt({key: preview[key] for key in ('signature','previous_digest')} |
                    {'keep_output_format': False}, account='dashboard:owner')
        self.assertFalse((self.fixture.configuration.path.parent / 'SOUL.md').exists())

    def test_pinned_public_constitution_preserves_standalone_format(self):
        self.write('LIFEOS/LIFEOS_SYSTEM_PROMPT.md', (SOURCE / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md').read_text())
        control = self.native(managed=False)
        governed = self.native()
        self.assertTrue(control['ok'], control)
        self.assertTrue(governed['ok'], governed)
        self.assertEqual(governed, control)

    def test_mount_cannot_remove_launcher_denial_when_identity_is_excluded(self):
        saved = self.memory.remember(OWNER, category='principal', content='RULE: SyntheticPersonality',
            title='', project='', request_id='launcher-policy')
        self.memory.forget(OWNER, saved['reference'], 'launcher-policy-forgotten')
        self.write('LIFEOS/LIFEOS_SYSTEM_PROMPT.md', self.sources['systemPrompt'])
        soul = self.fixture.configuration.path.parent / 'SOUL.md'
        soul.write_text('SyntheticPreviousPrompt')
        result = self.mount()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('launcher policy requires current identity review', result.stderr)
        self.assertEqual(soul.read_text(), 'SyntheticPreviousPrompt')

    def test_matching_prompt_with_public_permissions_is_published_privately(self):
        preferences = self.preferences()
        soul = self.fixture.configuration.path.parent / 'SOUL.md'
        soul.write_text(self.native()['soul'])
        soul.chmod(0o644)
        preview = preferences.preview_prompt(account='dashboard:owner')
        receipt = preferences.publish_prompt({key: preview[key] for key in ('signature','previous_digest')} |
            {'keep_output_format': False}, account='dashboard:owner')
        self.assertEqual(soul.stat().st_mode & 0o777, 0o600)
        self.assertEqual(receipt['status'], 'committed')
