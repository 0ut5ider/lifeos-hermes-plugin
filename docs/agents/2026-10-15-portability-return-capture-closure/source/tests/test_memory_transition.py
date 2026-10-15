# ABOUTME: Exercises provider-return orchestration with native facts and real user services.
# ABOUTME: Verifies persistent Pulse admission and exact recovery after interrupted publication.
import json
from pathlib import Path
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable
import test_memory_return as return_fixture
import test_profile_services as service_fixture


class MemoryTransitionTests(unittest.TestCase):
    def setUp(self):
        self.returned=return_fixture.MemoryReturnTests();self.returned.setUp()
        self.addCleanup(self.returned.doCleanups)
        self.profile=self.returned.profile
        self.services=service_fixture.ProfileServicesTests()
        self.services.fixture_home=self.returned.fixture.fixture.fixture.home
        self.services.fixture_profile=self.profile
        self.services.setUp();self.addCleanup(self.services.doCleanups)
        self.prepared=self.returned.prepare()

    def operation(self):
        from lifeos_hook_bridge.memory_transition import MemoryTransition
        return MemoryTransition(self.returned.configuration,units=self.services.units)

    def prepare(self):
        return self.operation().prepare_return(self.returned.fixture.snapshot,self.prepared['signature'],account='dashboard:owner')

    def test_return_drains_real_services_and_keeps_pulse_stopped(self):
        review=self.prepare()
        self.assertEqual(review['state'],'ready')
        self.assertTrue(self.returned.configuration.load()['ownership_enabled'])
        result=self.operation().apply(review['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'verification_required')
        self.assertFalse(result['application_verified'])
        self.assertFalse(self.returned.configuration.load()['ownership_enabled'])
        self.assertEqual(self.services.properties('pulse')['ActiveState'],'inactive')
        for role in ('dashboard','gateway'):
            self.assertEqual(self.services.properties(role)['ActiveState'],'active')
        self.assertEqual(self.operation().apply(review['signature'],account='dashboard:owner'),result)
        rolled=self.operation().rollback(review['signature'],account='dashboard:owner')
        self.assertEqual(rolled['state'],'rolled_back')
        self.assertTrue(self.returned.configuration.load()['ownership_enabled'])
        for role in self.services.units:self.assertEqual(self.services.properties(role)['ActiveState'],'active')

    def test_changed_profile_refuses_before_services_stop(self):
        review=self.prepare()
        pids={role:self.services.properties(role)['MainPID'] for role in self.services.units}
        path=self.profile/'config.yaml';path.write_bytes(path.read_bytes()+b'later_owner_setting: true\n')
        with self.assertRaises(MemoryUnavailable):self.operation().apply(review['signature'],account='dashboard:owner')
        self.assertEqual({role:self.services.properties(role)['MainPID'] for role in self.services.units},pids)
        self.assertTrue(self.returned.configuration.load()['ownership_enabled'])

    def test_installed_enabled_pulse_stays_disabled_until_reviewed_rollback(self):
        fixture=self.services
        definition=fixture.home/'units'/fixture.units['pulse']
        directory=Path.home()/'.config/systemd/user';directory.mkdir(parents=True,exist_ok=True)
        installed=directory/fixture.units['pulse']
        self.assertFalse(installed.exists())
        fixture.command('systemctl','--user','stop',fixture.units['pulse'])
        fixture.command('systemctl','--user','--quiet','disable','--runtime',fixture.units['pulse'])
        installed.write_text(definition.read_text()+'[Install]\nWantedBy=default.target\n')
        installed.chmod(0o600)
        try:
            fixture.command('systemctl','--user','daemon-reload')
            fixture.command('systemctl','--user','--quiet','enable',fixture.units['pulse'])
            fixture.command('systemctl','--user','start',fixture.units['pulse'])
            self.assertEqual(self.operation()._enablement(),'enabled')
            review=self.prepare()
            self.operation().apply(review['signature'],account='dashboard:owner')
            self.assertEqual(self.operation()._enablement(),'disabled')
            self.assertEqual(fixture.properties('pulse')['ActiveState'],'inactive')
            self.operation().rollback(review['signature'],account='dashboard:owner')
            self.assertEqual(self.operation()._enablement(),'enabled')
            self.assertEqual(fixture.properties('pulse')['ActiveState'],'active')
        finally:
            fixture.command('systemctl','--user','stop',fixture.units['pulse'])
            fixture.command('systemctl','--user','--quiet','disable',fixture.units['pulse'])
            installed.unlink()
            fixture.command('systemctl','--user','--quiet','link','--runtime',str(definition))
            fixture.command('systemctl','--user','daemon-reload')

    def test_interrupted_return_resumes_and_later_builtin_edit_blocks_rollback(self):
        review=self.prepare()
        def checkpoint(point):
            if point=='configured':raise InterruptedError('Synthetic interruption after return publication')
        with self.assertRaises(InterruptedError):self.operation().apply(review['signature'],account='dashboard:owner',checkpoint=checkpoint)
        for role in self.services.units:self.assertEqual(self.services.properties(role)['ActiveState'],'inactive')
        result=self.operation().apply(review['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'verification_required')
        path=self.profile/'memories/MEMORY.md';later=path.read_bytes()+b'\nSynthetic later built-in entry.';path.write_bytes(later)
        with self.assertRaises(MemoryUnavailable):self.operation().rollback(review['signature'],account='dashboard:owner')
        self.assertEqual(path.read_bytes(),later)
