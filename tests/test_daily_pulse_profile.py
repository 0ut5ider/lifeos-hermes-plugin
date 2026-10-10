# ABOUTME: Verifies the staged daily Pulse choices with its actual native configuration loader.
# ABOUTME: Runs governed jobs through native spawning and the actual Hermes command parser.
import json
from contextlib import closing
import sqlite3
import os
from pathlib import Path
import shlex
import subprocess
import sys
import unittest

import test_memory_owner_job_command as command_fixture


ROOT = Path(__file__).parents[1]
PROFILE = ROOT / 'docs/deployment/daily-text/PULSE.user.toml'
SOURCE = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
PROGRAM = Path(__file__).with_name('native_daily_pulse_profile.ts')


class DailyPulseProfileTests(unittest.TestCase):
    def call(self, *, environment=None, name=None):
        args = ['bun', '--no-install', str(PROGRAM), str(SOURCE), str(PROFILE)]
        if name: args.append(name)
        return subprocess.run(args, env=environment or dict(os.environ), capture_output=True, text=True, timeout=45)

    def config(self):
        self.assertTrue(PROFILE.is_file(), 'The daily profile must exist before native acceptance')
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_native_module_merger_disables_only_the_selected_optional_surfaces(self):
        modules = self.config()['modules']
        for name in ('voice', 'work', 'synapse', 'usage', 'bunker', 'imessage', 'syslog', 'da', 'hermes'):
            with self.subTest(module=name): self.assertFalse(modules[name])
        for name in ('telos', 'memory', 'projects', 'books', 'upgrades', 'hypotheses',
                     'algorithm', 'docs', 'health', 'finances', 'business', 'content'):
            with self.subTest(module=name): self.assertTrue(modules[name])

    def test_native_job_merger_has_no_raw_memory_command_or_external_output(self):
        jobs = self.config()['jobs']
        self.assertEqual(len(jobs), 11)
        self.assertEqual(len({job['name'] for job in jobs}), 11)
        active = {job['name']: job for job in jobs if job['enabled']}
        self.assertEqual(set(active), {'cost-aggregation', 'healthcheck', 'memory-consolidation',
                                      'proposal-gc', 'life-morning-brief', 'conduit-capture', 'atlas-sync'})
        for name in ('memory-consolidation', 'proposal-gc', 'life-morning-brief', 'conduit-capture', 'atlas-sync'):
            self.assertEqual(active[name]['command'], 'hermes lifeos-job ' + name)
            self.assertEqual(active[name]['timeout_ms'], 600000)
            self.assertEqual(active[name]['_source'], 'user')
        for job in active.values():
            self.assertEqual(job['type'], 'script')
            self.assertEqual(job['output'], 'log')
            self.assertNotIn('scheduleError', job)
        self.assertEqual(active['life-morning-brief']['schedule'], '0 7 * * *')
        self.assertEqual(active['atlas-sync']['schedule'], '50 6 * * *')

    def owner_fixture(self):
        self.assertTrue(PROFILE.is_file(), 'The daily profile must exist before native acceptance')
        fixture = command_fixture.MemoryOwnerJobCommandTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        pulse = fixture.native.root / 'LIFEOS/PULSE'
        pulse.mkdir()
        for item in (SOURCE / 'LIFEOS/PULSE').iterdir():
            if item.name != 'PULSE.toml':
                (pulse / item.name).symlink_to(item, target_is_directory=item.is_dir())
        (pulse / 'PULSE.toml').write_bytes((SOURCE / 'LIFEOS/PULSE/PULSE.toml').read_bytes())
        launcher = fixture.native.home / 'pulse-test-bin/hermes'
        launcher.parent.mkdir()
        launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' -m hermes_cli.main "$@"\n')
        launcher.chmod(0o700)
        environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'TZ') if key in os.environ}
        environment.update(HOME=str(fixture.native.home), HERMES_HOME=str(fixture.fixture.home),
            PYTHONPATH=str(command_fixture.model_fixture.HOST),
            LIFEOS_HOOK_SETTINGS=str(fixture.native.root / 'settings.json'),
            BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment['PATH'] = str(launcher.parent) + os.pathsep + environment['PATH']
        return fixture, environment

    def test_native_spawn_and_actual_hermes_parser_publish_one_weekly_synthesis(self):
        fixture, environment = self.owner_fixture()
        first = self.call(environment=environment, name='memory-consolidation')
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(first.stderr, '')
        body = json.loads(json.loads(first.stdout)['output'])
        self.assertEqual(body['status'], 'completed')
        reports = list(fixture.synthesis.rglob('*.md'))
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(fixture.fixture.fixture.received, [])

    def test_native_spawn_and_actual_hermes_parser_render_the_morning_brief(self):
        fixture, environment = self.owner_fixture()
        path = fixture.native.root / 'LIFEOS/USER/TELOS/GOALS.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('- G1: Synthetic staged-profile goal\n')
        result = self.call(environment=environment, name='life-morning-brief')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        body = json.loads(json.loads(result.stdout)['output'])
        self.assertEqual(body['status'], 'completed')
        self.assertIn('Synthetic staged-profile goal', body['output'])
        self.assertEqual(fixture.fixture.fixture.received, [])

    def test_native_spawn_refuses_memory_job_when_ownership_is_disabled(self):
        fixture, environment = self.owner_fixture()
        fixture.configuration.update(lambda value: value.update(ownership_enabled=False))
        result = self.call(environment=environment, name='memory-consolidation')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Script exited 1', result.stderr)
        self.assertFalse(fixture.synthesis.exists())
        self.assertEqual(fixture.fixture.fixture.received, [])

    def test_native_spawn_runs_proposal_cleanup_through_the_actual_owner_command(self):
        fixture, environment = self.owner_fixture()
        result = self.call(environment=environment, name='proposal-gc')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        body = json.loads(json.loads(result.stdout)['output'])
        self.assertEqual(body['status'], 'completed')
        self.assertEqual(body['job'], 'proposal-gc')
        self.assertEqual(fixture.fixture.fixture.received, [])

    def test_native_spawn_cannot_borrow_a_discord_author_when_local_grant_is_removed(self):
        fixture, environment = self.owner_fixture()
        fixture.configuration.update(lambda value: value['accounts'].pop(f'terminal:{os.getuid()}'))
        environment.update(HERMES_SESSION_PLATFORM='discord', HERMES_SESSION_USER_ID='owner')
        result = self.call(environment=environment, name='memory-consolidation')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Script exited 1', result.stderr)
        self.assertFalse(fixture.synthesis.exists())
        self.assertEqual(fixture.fixture.fixture.received, [])

    def test_native_spawn_runs_healthcheck_without_an_external_destination(self):
        fixture, environment = self.owner_fixture()
        result = self.call(environment=environment, name='healthcheck')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout)['output'], 'NO_ACTION')

    def test_native_schedule_spawn_initializes_and_refreshes_atlas_without_inference(self):
        fixture, environment = self.owner_fixture()
        atlas = fixture.native.root/'LIFEOS/ATLAS'
        atlas.symlink_to(SOURCE/'LIFEOS/ATLAS',target_is_directory=True)
        gear = fixture.native.root/'LIFEOS/USER/GEAR.md'
        gear.write_text('## Computing\n| **Laptop** | Synthetic scheduled device | daily |\n')
        result = self.call(environment=environment,name='atlas-sync')
        self.assertEqual((result.returncode,result.stderr),(0,''),result.stdout)
        body = json.loads(json.loads(result.stdout)['output'])
        self.assertEqual(body['status'],'completed')
        self.assertTrue(json.loads(body['output'])['ok'])
        graph = fixture.native.root.parent/'.local/state/lifeos/atlas/atlas.db'
        self.assertTrue(graph.is_file())
        gear.write_text('## Computing\n| **Laptop** | Synthetic scheduled replacement | daily |\n')
        result = self.call(environment=environment,name='atlas-sync')
        self.assertEqual((result.returncode,result.stderr),(0,''),result.stdout)
        with closing(sqlite3.connect(graph)) as connection:
            self.assertIn('Synthetic scheduled replacement',
                [row[0] for row in connection.execute('SELECT display_name FROM asset')])
        self.assertEqual(fixture.fixture.fixture.received,[])


if __name__ == '__main__':
    unittest.main()
