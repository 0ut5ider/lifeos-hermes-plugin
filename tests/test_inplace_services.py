# ABOUTME: Checks the in-place service inventory with actual user systemd units and real child processes.
# ABOUTME: Units use unique synthetic names so the account's own Hermes services are never touched.
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import uuid4

from optional.lifeos_release_manager.inplace_services import inventory, replace_with_units
from optional.lifeos_release_manager.release_catalog import ReleaseRejected


class InplaceServicesTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.source = self.root / 'hermes-agent'
        self.source.mkdir()
        self.state = self.root / 'installs/0123456789abcdef'
        self.state.mkdir(parents=True)
        suffix = uuid4().hex[:8]
        self.units = {'gateway': 'lifeos-test-gateway-' + suffix + '.service',
                      'dashboard': 'lifeos-test-dashboard-' + suffix + '.service',
                      'pulse': 'lifeos-test-pulse-' + suffix + '.service'}

    def unit(self, role):
        path = self.root / self.units[role]
        path.write_text('[Unit]\nDescription=LifeOS synthetic inventory control\n[Service]\nType=simple\n'
                        'Environment=PYTHONPATH=' + str(self.source) + '\n'
                        'ExecStart=' + sys.executable + ' -c "import time; time.sleep(120)" gateway run\n'
                        '[Install]\nWantedBy=default.target\n')
        subprocess.run(['systemctl', '--user', '--quiet', 'link', '--runtime', str(path)], check=True)
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', '--user', 'start', self.units[role]], check=True)
        def cleanup():
            subprocess.run(['systemctl', '--user', 'stop', self.units[role]], check=False)
            subprocess.run(['systemctl', '--user', '--quiet', 'disable', '--runtime', self.units[role]], check=False)
            subprocess.run(['systemctl', '--user', 'daemon-reload'], check=False)
        self.addCleanup(cleanup)
        time.sleep(0.5)

    def process(self, *arguments):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)', *arguments],
                                 env={**os.environ, 'PYTHONPATH': str(self.source)})
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        time.sleep(0.2)
        return child.pid

    def test_unit_consumers_are_bound_and_not_reported(self):
        self.unit('gateway')
        result = inventory(self.source, self.state, units=self.units)
        self.assertEqual(result['bound'], ['gateway'])
        self.assertEqual(result['consumers'], [])

    def test_inventory_records_whether_each_bound_unit_is_enabled(self):
        self.unit('gateway')
        self.unit('pulse')
        subprocess.run(['systemctl', '--user', '--quiet', 'enable', '--runtime', self.units['pulse']], check=True)
        result = inventory(self.source, self.state, units=self.units)
        self.assertEqual(result['enabled'], {'gateway': 'linked-runtime', 'pulse': 'enabled-runtime'})

    def test_hand_started_dashboard_is_offered_a_unit(self):
        pid = self.process('dashboard', '--no-open')
        result = inventory(self.source, self.state, units=self.units)
        self.assertEqual(result['offers'], ['dashboard'])
        self.assertEqual(result['blocking'], [])
        self.assertEqual([item['pid'] for item in result['consumers']], [pid])
        self.assertEqual(result['dashboard_options'], {})

    def test_offered_dashboard_unit_keeps_the_hand_started_address(self):
        self.process('dashboard', '--host', '0.0.0.0', '--port=9200', '--no-open')
        result = inventory(self.source, self.state, units=self.units)
        self.assertEqual(result['dashboard_options'], {'host': '0.0.0.0', 'port': 9200})

    def test_dashboards_with_different_addresses_block(self):
        self.process('dashboard', '--host', '0.0.0.0')
        self.process('dashboard', '--port', '9200')
        with self.assertRaisesRegex(ReleaseRejected, 'different addresses'):
            inventory(self.source, self.state, units=self.units)

    def test_hand_started_dashboard_with_its_unit_present_blocks(self):
        self.unit('dashboard')
        pid = self.process('dashboard')
        result = inventory(self.source, self.state, units=self.units)
        self.assertEqual(result['offers'], [])
        self.assertEqual([item['pid'] for item in result['blocking']], [pid])

    def test_interactive_session_blocks(self):
        pid = self.process('chat')
        result = inventory(self.source, self.state, units=self.units)
        self.assertEqual([(item['pid'], item['role']) for item in result['blocking']], [(pid, 'other')])

    def test_operator_processes_do_not_block_but_a_hand_started_dashboard_is_still_offered(self):
        from optional.lifeos_release_manager.inplace_services import ancestors
        operator = self.process('lifeos-release', 'prepare')
        dashboard = self.process('dashboard')
        result = inventory(self.source, self.state, units=self.units, operators={operator, dashboard})
        self.assertEqual([item['pid'] for item in result['consumers']], [dashboard])
        self.assertEqual(result['offers'], ['dashboard'])
        self.assertEqual(result['blocking'], [])
        self.assertIn(os.getppid(), ancestors())

    def test_profile_units_bind_only_existing_units_on_an_in_place_host(self):
        from optional.lifeos_release_manager.inplace_services import profile_units
        self.unit('gateway')
        self.unit('pulse')
        profile = self.root / '.hermes'
        profile.mkdir()
        self.assertIsNone(profile_units(profile, units=self.units))
        (profile / 'lifeos-host.json').write_text('{}')
        self.assertEqual(profile_units(profile, units=self.units),
                         {'gateway': self.units['gateway'], 'pulse': self.units['pulse']})

    def test_replacement_requires_the_reviewed_process_incarnation(self):
        pid = self.process('dashboard')
        admitted = inventory(self.source, self.state, units=self.units)['consumers']
        self.assertEqual([item['pid'] for item in replace_with_units(admitted, ['dashboard'])], [pid])
        self.assertEqual(replace_with_units(admitted, []), [])
        changed = [{**admitted[0], 'start_time': admitted[0]['start_time'] + 1}]
        with self.assertRaises(ReleaseRejected):
            replace_with_units(changed, ['dashboard'])


class ParseShowTests(unittest.TestCase):
    def test_a_repeated_property_keeps_each_value_on_its_own_line(self):
        from optional.lifeos_release_manager.inplace_services import parse_show
        output = ('LoadState=loaded\n'
                  'ExecStart={ path=/bin/true ; argv[]=/bin/true ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }\n'
                  'ExecStart={ path=/bin/echo ; argv[]=/bin/echo a=b ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }\n'
                  'DropInPaths=\n')
        values = parse_show(output)
        self.assertEqual(values['LoadState'], 'loaded')
        self.assertEqual(values['DropInPaths'], '')
        self.assertEqual([line.split(' ; ')[0] for line in values['ExecStart'].splitlines()],
                         ['{ path=/bin/true', '{ path=/bin/echo'])


if __name__ == '__main__':
    unittest.main()
