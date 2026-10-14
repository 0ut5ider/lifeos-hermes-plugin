# ABOUTME: Tests full Discord observation windows and current morning scheduler metadata.
# ABOUTME: Uses an actual local HTTP server with synthetic messages and no Discord writes.
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from lifeos_hook_bridge.discord_audience import DiscordAPI
from lifeos_hook_bridge.morning_observation import morning_delivery, morning_schedule, morning_execution


def message(at, *, brief=False, author='1558867947152347198'):
    identifier = str((int(at.timestamp() * 1000) - 1420070400000) << 22)
    return {'id': identifier, 'timestamp': at.isoformat(), 'channel_id': '1558870196784205927',
            'author': {'id': author}, 'content': 'LifeOS morning brief\n\nSynthetic.' if brief else 'Synthetic.'}


class MorningObservationTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 10, 12, 7, tzinfo=ZoneInfo('America/Toronto'))
        self.end = self.start + timedelta(minutes=15)
        self.rows, self.requests = [], []
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                owner.requests.append(self.path)
                query = parse_qs(urlsplit(self.path).query)
                before = int(query.get('before', ['18446744073709551615'])[0])
                rows = [row for row in owner.rows if int(row['id']) < before][:100]
                payload = json.dumps(rows).encode()
                self.send_response(200); self.end_headers(); self.wfile.write(payload)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.api = DiscordAPI('synthetic', origin='http://127.0.0.1:' + str(server.server_port))

    def delivery(self, **kwargs):
        return morning_delivery(self.api, '1558870196784205927', '1558867947152347198', self.start, self.end, **kwargs)

    def test_pages_until_window_is_covered_without_exporting_content(self):
        self.rows = [message(self.end + timedelta(seconds=200-i)) for i in range(105)]
        brief = message(self.start + timedelta(minutes=1), brief=True)
        self.rows += [brief, message(self.start-timedelta(seconds=1))]
        result = self.delivery()
        self.assertEqual(result['message_id'], brief['id'])
        self.assertEqual(result['pages'], 2)
        self.assertEqual(result['messages_examined'], 107)
        self.assertTrue(result['window_covered'])
        self.assertNotIn('content', json.dumps(result))
        self.assertEqual(len(self.requests), 2)
        self.assertIn('before=', self.requests[1])

    def test_second_brief_beyond_first_page_refuses_success(self):
        self.rows = [message(self.end-timedelta(seconds=i), brief=i==0) for i in range(100)]
        self.rows += [message(self.start+timedelta(seconds=1), brief=True)]
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.delivery()
        self.assertEqual(len(self.requests), 2)

    def test_page_limit_refuses_incomplete_window(self):
        self.rows = [message(self.end-timedelta(milliseconds=i), brief=i==0) for i in range(100)]
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.delivery(max_pages=1)

    def test_short_page_ends_history_but_zero_or_wrong_author_refuses(self):
        for rows in [[], [message(self.start, brief=True, author='1')]]:
            self.rows = rows
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                self.delivery()

    def test_window_boundaries_and_wrong_channel(self):
        self.rows = [message(self.end+timedelta(seconds=1), brief=True), message(self.start, brief=True),
                     message(self.start-timedelta(seconds=1), brief=True)]
        self.assertEqual(self.delivery()['message_id'], self.rows[1]['id'])
        self.rows[1]['channel_id'] = '1'
        with self.assertRaisesRegex(ValueError, 'channel'):
            self.delivery()

    def test_current_schedule_uses_native_user_override_and_enabled_state(self):
        with tempfile.TemporaryDirectory() as temp:
            system, user = Path(temp)/'system.toml', Path(temp)/'user.toml'
            system.write_text('[[job]]\nname="life-morning-brief"\nschedule="0 6 * * *"\nenabled=false\n')
            user.write_text('[[job]]\nname="life-morning-brief"\nschedule="0 7 * * *"\ntype="script"\ncommand="python /fixed/morning.py"\nenabled=true\n')
            result = morning_schedule(system, user, 'America/Toronto')
            self.assertEqual(result['schedule'], '0 7 * * *')
            self.assertEqual(result['source'], 'user')
            self.assertTrue(result['enabled'])
            self.assertNotIn('command', result)
            for replacement in ['enabled=false', 'schedule="0 8 * * *"', 'type="claude"']:
                original = user.read_text()
                field = replacement.split('=')[0]
                user.write_text('\n'.join(replacement if line.startswith(field+'=') else line for line in original.splitlines()))
                with self.assertRaises(ValueError):
                    morning_schedule(system, user, 'America/Toronto')
                user.write_text(original)
            with self.assertRaisesRegex(ValueError, 'timezone'):
                morning_schedule(system, user, 'UTC')

    def test_native_loader_and_observer_agree_on_user_override(self):
        native = Path(os.environ['LIFEOS_MEMORY_SOURCE'])/'LIFEOS/PULSE/lib.ts'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            system, user = root/'PULSE.toml', root/'user.toml'
            system.write_text('[[job]]\nname="life-morning-brief"\nschedule="0 6 * * *"\nenabled=false\n')
            user.write_text('[[job]]\nname="life-morning-brief"\nschedule="0 7 * * *"\ncommand="python /fixed/morning.py"\nenabled=true\n')
            script = root/'metadata.ts'
            script.write_text('import {loadConfig} from ' + json.dumps(str(native)) + ';\n'
                'const c=await loadConfig(process.argv[2],process.argv[3]);\n'
                'const j=c.jobs.find(j=>j.name==="life-morning-brief");\n'
                'console.log(JSON.stringify({schedule:j?.schedule,enabled:j?.enabled,source:j?._source}));\n')
            result = subprocess.run(['bun','--no-install',str(script),str(root),str(user)],
                capture_output=True,text=True,timeout=20)
            self.assertEqual((result.returncode,result.stderr),(0,''),result.stdout)
            actual = morning_schedule(system,user,'America/Toronto')
            self.assertEqual(json.loads(result.stdout), {key:actual[key] for key in ('schedule','enabled','source')})

    def test_duplicate_schedule_and_malformed_user_config_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            system,user = Path(temp)/'system.toml',Path(temp)/'user.toml'
            job = '[[job]]\nname="life-morning-brief"\nschedule="0 7 * * *"\ncommand="python /fixed/morning.py"\n'
            system.write_text(job)
            for data in ['[invalid', job+job]:
                user.write_text(data)
                with self.assertRaisesRegex(ValueError,'unavailable or ambiguous'):
                    morning_schedule(system,user,'America/Toronto')

    def test_real_hermes_parser_registers_observation_without_running_it(self):
        host = os.environ['LIFEOS_HERMES_SOURCE']
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)/'.hermes'
            plugin = profile/'plugins/lifeos-hook-bridge'
            plugin.parent.mkdir(parents=True)
            shutil.copytree(Path(__file__).resolve().parents[1]/'lifeos_hook_bridge', plugin,
                ignore=shutil.ignore_patterns('__pycache__'))
            (profile/'config.yaml').write_text('plugins:\n  enabled:\n    - lifeos-hook-bridge\n')
            environment = {key:os.environ[key] for key in ('PATH','LANG','TZ') if key in os.environ}
            environment.update(HOME=temp,HERMES_HOME=str(profile),PYTHONPATH=host,PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run([sys.executable,'-m','hermes_cli.main','lifeos-observe-morning','--help'],
                env=environment,capture_output=True,text=True,timeout=40)
            self.assertEqual((result.returncode,result.stderr),(0,''),result.stdout)
            self.assertIn('--date', result.stdout)
            self.assertIn('--channel', result.stdout)
            self.assertEqual(self.requests, [])

    def test_execution_requires_cron_start_and_completion_and_current_state(self):
        started, completed = self.start+timedelta(seconds=1), self.start+timedelta(minutes=1)
        def event(at, body):
            body['ts'] = at.isoformat()
            return json.dumps({'__REALTIME_TIMESTAMP': str(int(at.timestamp()*1000000)), 'MESSAGE': json.dumps(body)})
        lines = [event(started, {'subsystem':'cron','msg':'Running: life-morning-brief'}),
                 event(completed, {'subsystem':'cron','msg':'life-morning-brief completed; dispatched to log',
                     'outputPreview':json.dumps({'status':'delivered','channel_id':'1558870196784205927'})})]
        state = {'lastResult':'ok','lastRun':int(completed.timestamp()*1000),'consecutiveFailures':0}
        result = morning_execution('\n'.join(lines), state, self.start, self.end, '1558870196784205927')
        self.assertEqual(result['execution_source'], 'pulse-cron-journal')
        self.assertEqual(result['started_at'], started.isoformat())
        for journal, bad_state in [(lines[1],state), ('\n'.join(lines+lines),state), ('\n'.join(lines),dict(state,lastResult='error'))]:
            with self.assertRaises(ValueError):
                morning_execution(journal,bad_state,self.start,self.end,'1558870196784205927')

    def test_native_completion_precedes_its_asynchronous_journal_capture(self):
        started = self.start + timedelta(seconds=53, milliseconds=6)
        completed = self.start + timedelta(minutes=1, seconds=19, milliseconds=76)
        lines = []
        for at, delay, body in (
                (started, 212, {'msg': 'Running: life-morning-brief'}),
                (completed, 475, {'msg': 'life-morning-brief completed; dispatched to log',
                    'outputPreview': json.dumps({'status': 'delivered', 'channel_id': '1558870196784205927'})})):
            body.update(subsystem='cron', ts=at.isoformat())
            lines.append(json.dumps({'__REALTIME_TIMESTAMP': str(int(at.timestamp() * 1000000) + delay),
                'MESSAGE': json.dumps(body)}))
        state = {'lastResult': 'ok', 'lastRun': int(completed.timestamp() * 1000), 'consecutiveFailures': 0}
        result = morning_execution('\n'.join(lines), state, self.start, self.end, '1558870196784205927')
        self.assertEqual(result['completed_at'], completed.isoformat())
        self.assertEqual(result['timestamp_basis'], 'native-pulse-event')
        self.assertAlmostEqual(result['journal_capture_delay_ms']['completion'], 0.475)

    def test_execution_rejects_invalid_event_clocks_and_stale_state(self):
        started = self.start + timedelta(seconds=1)
        completed = self.start + timedelta(minutes=1)
        state = {'lastResult': 'ok', 'lastRun': int(completed.timestamp() * 1000), 'consecutiveFailures': 0}
        def journal(delay, timestamp):
            rows = []
            for at, body in ((started, {'msg': 'Running: life-morning-brief'}),
                    (completed, {'msg': 'life-morning-brief completed; dispatched to log',
                        'outputPreview': json.dumps({'status': 'delivered', 'channel_id': '1558870196784205927'})})):
                body.update(subsystem='cron', ts=at.isoformat() if at == started else timestamp)
                rows.append(json.dumps({'__REALTIME_TIMESTAMP': str(int(at.timestamp() * 1000000) + delay),
                    'MESSAGE': json.dumps(body)}))
            return '\n'.join(rows)
        for delay in (0, 475, 2_000_000, 5_000_000):
            with self.subTest(valid_delay_us=delay):
                result = morning_execution(journal(delay, completed.isoformat()), state,
                    self.start, self.end, '1558870196784205927')
                self.assertEqual(result['completed_at'], completed.isoformat())
        for delay, timestamp in ((-1, completed.isoformat()), (5_000_001, completed.isoformat()),
                (0, completed.replace(tzinfo=None).isoformat()), (0, None), (0, 'invalid')):
            with self.subTest(delay=delay, timestamp=timestamp), self.assertRaises(ValueError):
                morning_execution(journal(delay, timestamp), state, self.start, self.end, '1558870196784205927')
        for offset in (-1, 5001):
            with self.subTest(state_offset_ms=offset), self.assertRaises(ValueError):
                morning_execution(journal(475, completed.isoformat()),
                    dict(state, lastRun=state['lastRun'] + offset), self.start, self.end, '1558870196784205927')


if __name__ == '__main__':
    unittest.main()
