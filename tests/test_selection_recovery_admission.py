# ABOUTME: Tests interrupted dashboard recovery and selection exclusion across account profiles.
# ABOUTME: Uses real child processes, owner configurations, and file locks with local service recorders.
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import unittest

import test_selection_profile_isolation as profile_fixture
from lifeos_hook_bridge.installation_selection import account_selection_lock
from lifeos_hook_bridge.lifeos_installation import publish
from lifeos_hook_bridge.memory_service import MemoryConfiguration


class SelectionRecoveryAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = profile_fixture.SelectionProfileIsolationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def interrupt_selection(self):
        fixture = self.fixture
        job = fixture.job(fixture.b, 'selection-own-interrupted', journal=False)
        target = fixture.home / 'fresh-store/home'
        (target / '.claude/LIFEOS').mkdir(parents=True)
        request = json.loads((job / 'request.json').read_text())
        request['target_home'] = str(target)
        (job / 'request.json').write_text(json.dumps(request))
        program = '''
import os, sys
from pathlib import Path
from lifeos_hook_bridge import installation_selection as module
from lifeos_hook_bridge.memory_service import MemoryConfiguration
profile, target, job = map(Path, sys.argv[1:])
class Services:
    def stop(self): pass
    def start(self): pass
    def point_pulse(self, home): pass
record = module._record
def interrupted(job, journal, state):
    record(job, journal, state)
    if state == 'published': os._exit(91)
module._record = interrupted
module.select_home(job, profile=profile, target=target,
    configuration=MemoryConfiguration(profile / 'lifeos-memory.json'), services=Services(),
    mount=lambda installed, baseline: None, recover_mount=lambda installed: None,
    verify=lambda: None, baseline_data=None)
'''
        result = subprocess.run([sys.executable, '-c', program, str(fixture.b), str(target),
            str(job / 'transaction')], text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 91, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads((job / 'transaction/journal.json').read_text())['state'], 'published')
        return job, target

    def test_running_dashboard_owner_can_recover_after_the_selected_root_changes(self):
        job, target = self.interrupt_selection()
        fixture = self.fixture
        self.assertNotEqual(fixture.api.INSTALLED_ROOT, target / '.claude')
        with self.assertRaisesRegex(RuntimeError, 'different LifeOS installation'):
            fixture.api._memory_preferences()._configuration(account=fixture.owner_b)
        self.assertEqual(fixture.recover(), {'state': 'recovering', 'job': str(job)})
        command = json.loads(fixture.recorder.read_text())
        self.assertEqual(command[command.index('--account') + 1], fixture.owner_b)
        self.assertIn(f'--setenv=HERMES_HOME={fixture.b}', command)

    def test_recovery_still_refuses_a_revoked_owner_after_the_root_changes(self):
        job, _ = self.interrupt_selection()
        fixture = self.fixture
        MemoryConfiguration(fixture.b / 'lifeos-memory.json').update(lambda config: config['accounts'].clear())
        with self.assertRaises(fixture.api.HTTPException) as raised:
            fixture.recover()
        self.assertEqual(raised.exception.status_code, 403)
        self.assertFalse(fixture.recorder.exists())
        self.assertEqual(json.loads((job / 'status.json').read_text())['state'], 'interrupted')

    def test_recovery_refuses_a_root_outside_the_interrupted_journal(self):
        self.interrupt_selection()
        fixture = self.fixture
        MemoryConfiguration(fixture.b / 'lifeos-memory.json').update(
            lambda config: config.update(root=str(fixture.home / 'unrelated/.claude')))
        with self.assertRaises(fixture.api.HTTPException) as raised:
            fixture.recover()
        self.assertEqual(raised.exception.status_code, 409)
        self.assertFalse(fixture.recorder.exists())

    def test_recovery_refuses_a_journal_for_another_profile_before_launch(self):
        job, _ = self.interrupt_selection()
        fixture = self.fixture
        journal = job / 'transaction/journal.json'
        document = json.loads(journal.read_text())
        document['profile'] = str(fixture.a)
        journal.write_text(json.dumps(document))
        with self.assertRaises(fixture.api.HTTPException) as raised:
            fixture.recover()
        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn('another Hermes profile', raised.exception.detail)
        self.assertFalse(fixture.recorder.exists())

    def test_worker_refuses_a_root_outside_the_interrupted_journal_before_service_access(self):
        job, _ = self.interrupt_selection()
        fixture = self.fixture
        MemoryConfiguration(fixture.b / 'lifeos-memory.json').update(
            lambda config: config.update(root=str(fixture.home / 'unrelated/.claude')))
        fixture.worker_refuses(job, 'recovery roots disagree')

    def test_two_profiles_admit_exactly_one_pending_account_selection(self):
        fixture = self.fixture
        gate = fixture.home / 'gate'
        gate.mkdir()
        for name, profile in (('a', fixture.a), ('b', fixture.b)):
            home = fixture.home / ('fresh-' + name) / 'home'
            (home / '.claude/LIFEOS').mkdir(parents=True)
            publish(profile, home, fixture.home / 'HermesWorkspace')
            MemoryConfiguration(profile / 'lifeos-memory.json').update(
                lambda config, home=home: config.update(root=str(home / '.claude')))
        program = '''
import importlib.util, json, sys, time
from pathlib import Path
api_path, gate, name, owner = sys.argv[1:]
gate = Path(gate)
other = 'b' if name == 'a' else 'a'
spec = importlib.util.spec_from_file_location('concurrent_selection_api_' + name, api_path)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
def wait_for(predicate):
    deadline = time.monotonic() + 10
    while not predicate():
        if time.monotonic() > deadline: raise RuntimeError('selection scheduling timeout')
        time.sleep(.01)
scan = api._selection_jobs
def paused_scan():
    result = scan()
    (gate / (name + '.scanned')).touch()
    wait_for(lambda: (gate / (other + '.scanned')).exists() or (gate / (other + '.done')).exists())
    return result
api._selection_jobs = paused_scan
(gate / (name + '.ready')).touch()
wait_for(lambda: (gate / (other + '.ready')).exists())
try:
    try:
        response = api._installation_action(lambda: api._queue_selection(owner, None))
    except api.HTTPException as error:
        response = {'http_status': error.status_code, 'detail': error.detail}
    print(json.dumps(response))
finally:
    (gate / (name + '.done')).touch()
'''
        children = []
        api_path = Path(__file__).parents[1] / 'lifeos_hook_bridge/dashboard/plugin_api.py'
        for name, profile, owner in (('a', fixture.a, fixture.owner_a), ('b', fixture.b, fixture.owner_b)):
            child = subprocess.Popen([sys.executable, '-c', program, str(api_path), str(gate), name, owner],
                env={**os.environ, 'HERMES_HOME': str(profile)}, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            children.append(child)
            self.addCleanup(self.finish, child)
        responses = []
        for child in children:
            output, error = child.communicate(timeout=30)
            self.assertEqual(child.returncode, 0, output + error)
            self.assertEqual(error, '')
            responses.append(json.loads(output))
        self.assertEqual(sum(response.get('state') == 'queued' for response in responses), 1, responses)
        self.assertEqual(sum(response.get('http_status') == 409 for response in responses), 1, responses)
        self.assertEqual(len(list(fixture.api.SELECTION_ROOT.glob('*/request.json'))), 1)

    def test_worker_waits_for_the_account_lock_before_accessing_services(self):
        fixture = self.fixture
        job = fixture.job(fixture.b, 'selection-worker', state='queued', journal=False)
        program = '''
import sys
from pathlib import Path
from lifeos_hook_bridge import selection_worker as worker
job, profile, marker = map(Path, sys.argv[1:4])
class Services:
    def __init__(self, account): marker.write_text('services')
    def stop(self): pass
    def start(self): pass
    def point_pulse(self, home): pass
    def verify(self): pass
worker.SystemdServices = Services
worker._mount = lambda profile, request: lambda installed, baseline: None
print('ready', flush=True)
print(worker.run_selection_job(job, profile=profile, account=sys.argv[4])['state'], flush=True)
'''
        marker = fixture.home / 'worker-services'
        with account_selection_lock(fixture.a):
            child = subprocess.Popen([sys.executable, '-c', program, str(job), str(fixture.b),
                str(marker), fixture.owner_b], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.addCleanup(self.finish, child)
            self.assertTrue(select.select([child.stdout], [], [], 5)[0])
            self.assertEqual(child.stdout.readline(), 'ready\n')
            self.assertEqual(select.select([child.stdout], [], [], .3)[0], [])
            self.assertFalse(marker.exists())
        output, error = child.communicate(timeout=10)
        self.assertEqual(child.returncode, 0, output + error)
        self.assertEqual(error, '')
        self.assertEqual(output, 'applied\n')
        self.assertTrue(marker.exists())

    @staticmethod
    def finish(child):
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)
