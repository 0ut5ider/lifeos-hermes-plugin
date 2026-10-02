# ABOUTME: Verifies owner-authorized native mounting without a conversation identity.
# ABOUTME: Exercises scoped grants, native RPC refusal, installation roots, and revocation.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import test_memory_prompt as prompt_fixture


class MemoryAdministrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = prompt_fixture.MemoryPromptTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.preferences()
        self.root = self.fixture.root
        self.profile = self.fixture.fixture.configuration.path.parent
        self.configuration = MemoryConfiguration(self.profile / 'lifeos-memory.json')
        self.configuration.save(self.fixture.fixture.configuration.load())
        connector = json.loads(self.fixture.connector.read_text())
        connector['command'][-1] = str(self.configuration.path)
        self.fixture.connector.write_text(json.dumps(connector))
        self.fixture.connector.chmod(0o600)
        (self.profile / 'config.yaml').write_text('model:\n  default: local\n')

    def admin(self):
        from lifeos_hook_bridge import memory_administration
        return memory_administration

    def issue(self, **options):
        return self.admin().issue(self.configuration, 'dashboard:owner', **options)

    def rpc(self, grant, operation='prompt_bundle', arguments=None, **environment):
        values = dict(os.environ, HOME=str(self.root.parent), HERMES_HOME=str(self.profile),
                      LIFEOS_MEMORY_ADMINISTRATION=str(grant), **environment)
        result = subprocess.run([sys.executable, str(Path(__file__).parents[1] / 'lifeos_hook_bridge/memory_rpc.py'),
            '--configuration', str(self.configuration.path)],
            input=json.dumps({'operation': operation, 'arguments': {'keepOutputFormat': False} if arguments is None else arguments}),
            env=values, text=True, capture_output=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def mount(self, grant, *, check=False):
        environment = self.admin().mount_environment(self.root, self.profile, grant)
        command = [self.fixture.memory.bun, '--no-install', str(self.root / 'LIFEOS/HERMES/Mount.ts')]
        if check:
            command.append('--check')
        return subprocess.run(command, cwd=self.root.parent, env=environment, text=True,
                              capture_output=True, timeout=90)

    def test_native_mount_accepts_a_bound_owner_grant_without_conversation_metadata(self):
        control = self.fixture.native(managed=False)
        grant = self.issue()
        self.addCleanup(self.admin().revoke, self.configuration, grant)
        result = self.mount(grant)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual((self.profile / 'SOUL.md').read_text(), control['soul'])
        self.assertEqual((self.profile / 'SOUL.md').stat().st_mode & 0o777, 0o600)
        policy = json.loads((self.profile / 'plugins/lifeos/policy.json').read_text())
        self.assertIn('syntheticassistant', policy['shellDenyGlobs'])
        checked = self.mount(grant, check=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertFalse(self.configuration.load().get('ownership_enabled', False))

    def test_unbound_and_missing_owner_accounts_cannot_issue_authority(self):
        for account in (None, 'dashboard:other', 'chat-a:100'):
            with self.subTest(account=account), self.assertRaises(PermissionError):
                self.admin().issue(self.configuration, account)

    def test_a_mount_grant_cannot_read_or_write_arbitrary_memory(self):
        grant = self.issue()
        self.addCleanup(self.admin().revoke, self.configuration, grant)
        for operation, arguments in (('retrieve', {'query': 'Synthetic', 'options': {}}),
                                    ('read_source', {'path': str(self.root / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md')}),
                                    ('prompt_preview', {'home': '/tmp/other', 'keepOutputFormat': False})):
            with self.subTest(operation=operation):
                self.assertFalse(self.rpc(grant, operation, arguments)['ok'])

    def test_forged_expired_and_revoked_grants_refuse_without_context_fallback(self):
        valid_context = json.dumps(__import__('dataclasses').asdict(self.fixture.fixture.context))
        grant = self.issue()
        document = json.loads(grant.read_text())
        document['payload']['account'] = 'dashboard:forged'
        grant.write_text(json.dumps(document))
        self.assertFalse(self.rpc(grant, LIFEOS_MEMORY_CONTEXT=valid_context)['ok'])
        self.admin().revoke(self.configuration, grant)
        self.assertFalse(self.rpc(grant, LIFEOS_MEMORY_CONTEXT=valid_context)['ok'])
        with patch.object(self.admin().time, 'time', return_value=1):
            expired = self.issue()
        self.addCleanup(self.admin().revoke, self.configuration, expired)
        self.assertFalse(self.rpc(expired, LIFEOS_MEMORY_CONTEXT=valid_context)['ok'])

    def test_invalid_signature_encoding_returns_a_sanitized_refusal(self):
        grant = self.issue()
        self.addCleanup(self.admin().revoke, self.configuration, grant)
        document = json.loads(grant.read_text())
        document['signature'] = '\u2603' * 64
        grant.write_text(json.dumps(document))
        result = self.rpc(grant)
        self.assertEqual(result, {'ok': False, 'code': 'EWRITE_FAILED',
                                 'message': 'Administrative prompt mounting is unavailable'})

    def test_revocation_during_native_rendering_prevents_prompt_publication(self):
        from lifeos_hook_bridge.memory_access import NativeMemory
        grant = self.issue()
        service = MemoryService(self.configuration)
        options = {'home': str(self.profile), 'keepOutputFormat': False}
        plan = service.administrative(grant, 'prompt_preview', options)
        self.assertTrue(plan['ok'], plan)
        (self.profile / 'SOUL.md').write_text('SyntheticPreviousPrompt\n')
        # Collect a fresh destination digest before testing a change during the actual renderer call.
        plan = service.administrative(grant, 'prompt_preview', options)
        native = NativeMemory._native

        def render_then_revoke(memory, *arguments, **keywords):
            result = native(memory, *arguments, **keywords)
            self.admin().revoke(self.configuration, grant)
            return result

        with patch.object(NativeMemory, '_native', render_then_revoke):
            result = service.administrative(grant, 'prompt_publish', {**options,
                'signature': plan['signature'], 'previous_digest': plan['previous_digest']})
        self.assertFalse(result['ok'], result)
        self.assertEqual((self.profile / 'SOUL.md').read_text(), 'SyntheticPreviousPrompt\n')

    def test_owner_revocation_and_configuration_change_invalidate_the_grant(self):
        grant = self.issue()
        self.addCleanup(self.admin().revoke, self.configuration, grant)
        self.configuration.update(lambda value: value['accounts'].pop('dashboard:owner'))
        self.assertFalse(self.rpc(grant)['ok'])
        self.configuration.update(lambda value: value['accounts'].update({'dashboard:owner': 'owner'}))
        fresh = self.issue()
        self.addCleanup(self.admin().revoke, self.configuration, fresh)
        self.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertFalse(self.rpc(fresh)['ok'])

    def test_job_binding_and_profile_binding_are_checked_before_mounting(self):
        binding = {'job': 'synthetic-job', 'request_digest': 'a' * 64, 'action': 'apply'}
        grant = self.issue(binding=binding)
        self.addCleanup(self.admin().revoke, self.configuration, grant)
        self.assertIn('LIFEOS_MEMORY_ADMINISTRATION',
            self.admin().mount_environment(self.root, self.profile, grant, binding=binding))
        for changed in ({**binding, 'action': 'recover'}, {**binding, 'request_digest': 'b' * 64}):
            with self.assertRaises(PermissionError):
                self.admin().mount_environment(self.root, self.profile, grant, binding=changed)
        with self.assertRaises((PermissionError, RuntimeError)):
            self.admin().mount_environment(self.root, self.profile / 'other', grant)

    def test_private_permissions_and_connector_loss_are_not_bypassable(self):
        grant = self.issue()
        self.addCleanup(self.admin().revoke, self.configuration, grant)
        grant.chmod(0o644)
        self.assertFalse(self.rpc(grant)['ok'])
        grant.chmod(0o600)
        self.fixture.connector.unlink()
        with self.assertRaises(RuntimeError):
            self.admin().mount_environment(self.root, self.profile, grant)

    def test_environment_removes_inherited_internal_and_conversation_bypasses(self):
        grant = self.issue()
        self.addCleanup(self.admin().revoke, self.configuration, grant)
        with patch.dict(os.environ, {'HOME': '/tmp/wrong-home', 'LIFEOS_MEMORY_INTERNAL': '1',
            'LIFEOS_MEMORY_CONTEXT': '{}', 'LIFEOS_MEMORY_ADMINISTRATION': '/tmp/forged'}):
            environment = self.admin().mount_environment(self.root, self.profile, grant)
        self.assertNotIn('LIFEOS_MEMORY_INTERNAL', environment)
        self.assertNotIn('LIFEOS_MEMORY_CONTEXT', environment)
        self.assertEqual(environment['HOME'], str(self.root.parent))
        self.assertEqual(environment['HERMES_HOME'], str(self.profile))
        self.assertEqual(environment['LIFEOS_MEMORY_ADMINISTRATION'], str(grant))


if __name__ == '__main__':
    unittest.main()
