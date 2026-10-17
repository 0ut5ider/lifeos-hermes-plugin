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
                        'ExecStart=' + sys.executable + ' -c "import time; time.sleep(120)" gateway run\n')
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

    def test_hand_started_dashboard_is_offered_a_unit(self):
        pid = self.process('dashboard', '--no-open')
        result = inventory(self.source, self.state, units=self.units)
        self.assertEqual(result['offers'], ['dashboard'])
        self.assertEqual(result['blocking'], [])
        self.assertEqual([item['pid'] for item in result['consumers']], [pid])

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

    def test_replacement_requires_the_reviewed_process_incarnation(self):
        pid = self.process('dashboard')
        admitted = inventory(self.source, self.state, units=self.units)['consumers']
        self.assertEqual([item['pid'] for item in replace_with_units(admitted, ['dashboard'])], [pid])
        self.assertEqual(replace_with_units(admitted, []), [])
        changed = [{**admitted[0], 'start_time': admitted[0]['start_time'] + 1}]
        with self.assertRaises(ReleaseRejected):
            replace_with_units(changed, ['dashboard'])


if __name__ == '__main__':
    unittest.main()
