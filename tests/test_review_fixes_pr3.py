# ABOUTME: Regression tests for defects that the independent review of pull request 3 confirms.
# ABOUTME: Covers fail-closed middleware registration and the configuration lock during fresh-store preparation.
import fcntl
import os
import sys
import types
import unittest
from unittest.mock import patch

from lifeos_hook_bridge import fresh_store, memory_provider
from lifeos_hook_bridge.memory_provider import MemoryAdmissionError
import test_memory_import as import_fixture


class Context:
    def __init__(self):
        self.middleware = []

    def register_memory_provider(self, provider):
        self.provider = provider

    def register_middleware(self, kind, callback, *, required=False):
        self.middleware.append((kind, required))


class RequiredMiddlewareRegistrationTests(unittest.TestCase):
    def register(self, version, enabled):
        package = types.ModuleType('hermes_cli')
        package.__path__ = []
        module = types.ModuleType('hermes_cli.middleware')
        module.REQUIRED_MIDDLEWARE_API_VERSION = version
        context = Context()
        with patch.dict(sys.modules, {'hermes_cli': package, 'hermes_cli.middleware': module}), \
                patch.object(memory_provider.MemoryRuntime, 'enabled', lambda runtime: enabled):
            memory_provider.register_provider(context)
        return context.middleware

    def test_supported_host_version_registers_both_required_checks(self):
        self.assertEqual(self.register(1, True), [('llm_execution', True), ('llm_admission', True)])

    def test_unsupported_host_version_refuses_enabled_lasting_memory(self):
        with self.assertRaisesRegex(MemoryAdmissionError, 'required model-request checks'):
            self.register(2, True)

    def test_unsupported_host_version_loads_while_lasting_memory_is_disabled(self):
        self.assertEqual(self.register(2, False), [])


class FreshStoreLockTests(unittest.TestCase):
    def test_native_installation_runs_without_the_configuration_lock(self):
        fixture = import_fixture.MemoryImportTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        os.chmod(fixture.profile, 0o700)
        configuration = fixture.configuration
        observed = []

        def install(*_):
            descriptor = os.open(configuration.path.with_name(configuration.path.name + '.lock'), os.O_RDWR)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                observed.append('free')
            except BlockingIOError:
                observed.append('held')
            finally:
                os.close(descriptor)
            raise RuntimeError('stop after the lock observation')

        with patch.object(fresh_store, 'validate_prepared_lifeos', lambda candidate: {'lifeos_commit': 'synthetic'}), \
                patch.object(fresh_store, 'install_prepared_lifeos', install):
            with self.assertRaisesRegex(RuntimeError, 'lock observation'):
                fresh_store.FreshStore(configuration).prepare(
                    fixture.fixture.home / 'candidate', principal_name='Adrian', assistant_name='Cerebo',
                    account='dashboard:owner')
        self.assertEqual(observed, ['free'])


class FreshStoreBindingTests(unittest.TestCase):
    def test_binding_ignores_unrelated_settings_and_detects_owner_changes(self):
        selected = {'root': '/installed', 'principal': 'owner', 'accounts': {'dashboard:owner': 'owner'},
                    'sharing_enabled': False, 'clients': {}}
        changed = {**selected, 'sharing_enabled': True, 'clients': {'reader': {'enabled': False}}}
        binding = fresh_store.owner_binding
        self.assertEqual(binding(selected, 'dashboard:owner'), binding(changed, 'dashboard:owner'))
        for key, value in (('root', '/other'), ('principal', 'other'), ('accounts', {'dashboard:owner': 'other'})):
            self.assertNotEqual(binding(selected, 'dashboard:owner'), binding({**selected, key: value}, 'dashboard:owner'))


class UnverifiableConfigurationTests(unittest.TestCase):
    def test_unsupported_host_refuses_a_configuration_that_cannot_be_read(self):
        package = types.ModuleType('hermes_cli')
        package.__path__ = []
        module = types.ModuleType('hermes_cli.middleware')
        module.REQUIRED_MIDDLEWARE_API_VERSION = 2

        def unreadable(runtime):
            raise ValueError('synthetic malformed configuration')
        with patch.dict(sys.modules, {'hermes_cli': package, 'hermes_cli.middleware': module}), \
                patch.object(memory_provider.MemoryRuntime, 'enabled', unreadable):
            with self.assertRaisesRegex(MemoryAdmissionError, 'cannot confirm'):
                memory_provider.register_provider(Context())
