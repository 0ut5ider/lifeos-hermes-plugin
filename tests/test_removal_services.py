# ABOUTME: Verifies removal service barriers across real changed and absent unit definitions.
# ABOUTME: Keeps unrelated fixture services intact and rejects later definition edits.
from pathlib import Path
import unittest

import test_profile_services as fixture


class RemovalServicesTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.ProfileServicesTests()
        if hasattr(self,'fixture_home'):self.fixture.fixture_home=self.fixture_home
        if hasattr(self,'fixture_profile'):self.fixture.fixture_profile=self.fixture_profile
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.home=self.fixture.home;self.profile=self.fixture.profile
        self.definitions={role:self.home/'units'/unit for role,unit in self.fixture.units.items()}
        root=Path.home()/'.config/systemd/user';root.mkdir(parents=True,exist_ok=True)
        self.installed_definitions={role:root/unit for role,unit in self.fixture.units.items()}
        self.pulse=self.definitions['pulse'];self.installed_pulse=self.installed_definitions['pulse']
        self.fixture.command('systemctl','--user','stop',self.fixture.units['pulse'])
        for role,unit in self.fixture.units.items():
            self.fixture.command('systemctl','--user','--quiet','disable','--runtime',unit)
            path=self.installed_definitions[role]
            path.write_text(self.definitions[role].read_text()+('[Install]\nWantedBy=default.target\n' if role=='pulse' else ''))
            path.chmod(0o600)
        self.fixture.command('systemctl','--user','daemon-reload')
        self.addCleanup(self.restore_units)

    def restore_units(self):
        for role,unit in self.fixture.units.items():
            self.installed_definitions[role].unlink(missing_ok=True)
            self.fixture.command('systemctl','--user','--quiet','link','--runtime',str(self.definitions[role]))
        self.fixture.command('systemctl','--user','daemon-reload')

    def operation(self):
        from optional.lifeos_release_manager.removal_services import RemovalServices
        return RemovalServices(self.fixture.barrier(),self.home/'removal-service.json')

    def test_actual_removed_pulse_definition_keeps_only_hermes_services_active(self):
        import json
        paths={}
        for role,unit in self.fixture.units.items():
            values=dict(line.split('=',1) for line in self.fixture.command('systemctl','--user','show',unit,'--property=FragmentPath,DropInPaths').splitlines())
            for number,path in enumerate([values['FragmentPath'],*values['DropInPaths'].split()]):paths[role+str(number)]=path
        output=self.home/'removal-service-layout.json'
        output.write_text(json.dumps({role:{'path':path,'mode':oct(Path(path).lstat().st_mode),'uid':Path(path).lstat().st_uid,'link':Path(path).is_symlink()} for role,path in paths.items()},indent=2)+'\n')
        operation=self.operation();review=operation.prepare(removed=[self.installed_pulse])
        operation.stop(review)
        for role in self.fixture.units:self.assertEqual(self.fixture.properties(role)['MainPID'],'0')
        self.installed_pulse.unlink()
        operation.resume(review)
        self.assertEqual(dict(line.split('=',1) for line in self.fixture.command('systemctl','--user','show',self.fixture.units['pulse'],'--property=LoadState').splitlines())['LoadState'],'not-found')
        self.assertEqual(self.fixture.properties('pulse')['ActiveState'],'inactive')
        for role in ('gateway','dashboard'):self.assertEqual(self.fixture.properties(role)['ActiveState'],'active')
        operation.verify(review)
        operation.stop(review)
        for role in self.fixture.units:self.assertEqual(self.fixture.properties(role)['MainPID'],'0')
        self.installed_pulse.write_text(self.pulse.read_text()+'[Install]\nWantedBy=default.target\n');self.installed_pulse.chmod(0o600)
        operation.resume(review,restored=True)
        self.assertEqual(self.fixture.properties('pulse')['ActiveState'],'inactive')
        for role in ('gateway','dashboard'):self.assertEqual(self.fixture.properties(role)['ActiveState'],'active')

    def test_in_place_host_binds_only_gateway_and_pulse(self):
        from lifeos_hook_bridge.profile_services import ProfileServices
        from optional.lifeos_release_manager.removal_services import RemovalServices
        units={role:self.fixture.units[role] for role in ('gateway','pulse')}
        barrier=ProfileServices(self.profile,self.fixture.installed,units=units,roles=tuple(units))
        operation=RemovalServices(barrier,self.home/'removal-host-service.json')
        dashboard=self.fixture.properties('dashboard')['MainPID']
        review=operation.prepare(removed=[self.installed_pulse])
        operation.stop(review)
        self.assertEqual(self.fixture.properties('gateway')['MainPID'],'0')
        self.assertEqual(self.fixture.properties('dashboard')['MainPID'],dashboard)
        self.installed_pulse.unlink()
        operation.resume(review)
        self.assertEqual(self.fixture.properties('gateway')['ActiveState'],'active')
        self.assertEqual(self.fixture.properties('dashboard')['MainPID'],dashboard)
        self.assertEqual(operation.verify(review)['pulse_definition_removed'],True)

    def test_host_without_a_bound_pulse_refuses(self):
        from lifeos_hook_bridge.profile_services import ProfileServices
        from optional.lifeos_release_manager.removal_services import RemovalServices
        barrier=ProfileServices(self.profile,self.fixture.installed,units={'gateway':self.fixture.units['gateway']},
            roles=('gateway',))
        with self.assertRaisesRegex(ValueError,'Pulse'):
            RemovalServices(barrier,self.home/'removal-host-service.json').prepare(removed=[self.installed_pulse])

    def test_later_unit_edit_refuses_before_stopping(self):
        operation=self.operation();review=operation.prepare(removed=[self.installed_pulse])
        path=self.installed_definitions['gateway'];before=path.read_bytes()
        pids={role:self.fixture.properties(role)['MainPID'] for role in self.fixture.units}
        try:
            path.write_bytes(before+b'\n# Synthetic later edit\n')
            with self.assertRaises(ValueError):operation.stop(review)
            self.assertEqual({role:self.fixture.properties(role)['MainPID'] for role in self.fixture.units},pids)
        finally:path.write_bytes(before)

    def test_enabled_or_active_pulse_refuses_preparation(self):
        operation=self.operation()
        self.fixture.command('systemctl','--user','--quiet','enable',self.fixture.units['pulse'])
        try:
            with self.assertRaises(ValueError):operation.prepare(removed=[self.installed_pulse])
        finally:self.fixture.command('systemctl','--user','--quiet','disable',self.fixture.units['pulse'])
        self.fixture.command('systemctl','--user','start',self.fixture.units['pulse'])
        with self.assertRaises(ValueError):operation.prepare(removed=[self.installed_pulse])
