# ABOUTME: Verifies complete Discord morning windows and real Pulse scheduling metadata.
# ABOUTME: Returns safe aggregate receipts without retaining narration or triggering jobs.
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tomllib
from urllib.parse import urlencode


JOB = 'life-morning-brief'


def morning_delivery(api, channel, bot, start, end, *, max_pages=100):
    """Read backwards until all messages in the observation window are covered."""
    if start >= end or start.tzinfo is None or end.tzinfo is None or not 1 <= max_pages <= 100:
        raise ValueError('The morning observation requires a bounded timezone-aware window')
    if not all(isinstance(value, str) and value.isascii() and value.isdecimal()
               and 0 < int(value) < 2**64 for value in (channel, bot)):
        raise ValueError('The morning observation requires numeric Discord identifiers')
    before, previous_time, matches = None, None, []
    examined, oldest = 0, None
    for pages in range(1, max_pages + 1):
        query = {'limit': 100}
        if before is not None:
            query['before'] = str(before)
        rows = api.get('/channels/' + channel + '/messages?' + urlencode(query))
        if not isinstance(rows, list) or len(rows) > 100:
            raise ValueError('Discord observation history has an invalid page')
        for row in rows:
            try:
                identifier = row['id']
                if not isinstance(identifier, str) or not identifier.isascii() or not identifier.isdecimal():
                    raise ValueError
                number = int(identifier)
                at = datetime.fromisoformat(row['timestamp'])
                if (not 0 < number < 2**64 or at.tzinfo is None
                        or (before is not None and number >= before)
                        or (previous_time is not None and at > previous_time)
                        or row['channel_id'] != channel or not isinstance(row['content'], str)
                        or not isinstance(row['author']['id'], str)):
                    raise ValueError
            except (KeyError, TypeError, ValueError, OverflowError):
                raise ValueError('Discord observation history has invalid channel, order, or message metadata') from None
            before, previous_time, oldest = number, at, at
            examined += 1
            if (start <= at <= end and row['author']['id'] == bot
                    and row['content'].startswith('LifeOS morning brief\n\n')):
                matches.append({'message_id': identifier, 'message_timestamp': at.isoformat(), 'channel_id': channel})
        covered = len(rows) < 100 or (oldest is not None and oldest < start)
        if covered:
            if len(matches) != 1:
                raise ValueError('Discord must contain exactly one morning brief in the complete observation window')
            return {**matches[0], 'pages': pages, 'messages_examined': examined, 'window_covered': True,
                    'coverage_basis': 'history_exhausted' if len(rows) < 100 else 'before_window',
                    'oldest_message_timestamp': oldest.isoformat() if oldest is not None else None}
    raise ValueError('Discord observation cannot establish complete window coverage within its page limit')


def morning_schedule(system_path: Path, user_path: Path, timezone: str):
    """Resolve the same named user override as the native Pulse config loader."""
    if timezone != 'America/Toronto':
        raise ValueError('The running Pulse timezone must be America/Toronto')
    selected = None
    fingerprints = {}
    for source, path in [('system', system_path), ('user', user_path)]:
        if source == 'user' and not path.exists():
            continue
        try:
            data = path.read_bytes()
            jobs = tomllib.loads(data.decode()).get('job', [])
            if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
                raise ValueError
            matches = [job for job in jobs if job.get('name') == JOB]
            if len(matches) > 1:
                raise ValueError
        except (OSError, UnicodeError, ValueError):
            raise ValueError('The current Pulse job definitions are unavailable or ambiguous') from None
        fingerprints[source] = hashlib.sha256(data).hexdigest()
        if matches:
            selected = {**matches[0], 'source': source}
    if (selected is None or selected.get('schedule') != '0 7 * * *'
            or selected.get('enabled', True) is not True or selected.get('type', 'script') != 'script'
            or not isinstance(selected.get('command'), str) or not selected['command'].strip()
            or '${' in selected['command']):
        raise ValueError('The morning job must be enabled as the selected 07:00 script schedule')
    return {'schedule': selected['schedule'], 'timezone': timezone, 'enabled': True,
            'source': selected['source'], 'configuration_sha256': fingerprints,
            'command_sha256': hashlib.sha256(selected['command'].encode()).hexdigest()}


def morning_execution(journal: str, state: dict, start, end, channel):
    starts, completions = [], []
    for line in journal.splitlines():
        try:
            outer = json.loads(line)
            event = json.loads(outer['MESSAGE'])
            if not isinstance(event, dict) or event.get('subsystem') != 'cron':
                continue
            msg = event.get('msg', '')
            if msg != 'Running: ' + JOB and not msg.startswith(JOB + ' completed'):
                continue
            at = datetime.fromtimestamp(int(outer['__REALTIME_TIMESTAMP']) / 1000000, start.tzinfo)
        except (ValueError, KeyError, TypeError, OverflowError):
            continue
        if start <= at <= end:
            (starts if msg == 'Running: ' + JOB else completions).append((at, event))
    if len(starts) != 1 or len(completions) != 1 or starts[0][0] > completions[0][0]:
        raise ValueError('Pulse must record exactly one cron start and completion in the observation window')
    try:
        completed = datetime.fromtimestamp(state['lastRun'] / 1000, start.tzinfo)
        delivery = json.loads(completions[0][1]['outputPreview'])
        valid = (state['lastResult'] == 'ok' and state.get('consecutiveFailures', 0) == 0
                 and start <= completed <= end and 0 <= (completed - completions[0][0]).total_seconds() <= 5
                 and delivery['status'] == 'delivered' and delivery['channel_id'] == channel)
    except (KeyError, ValueError, TypeError, OverflowError):
        valid = False
    if not valid:
        raise ValueError('The current Pulse state and cron delivery receipt must agree')
    return {'execution_source': 'pulse-cron-journal', 'cron_starts': 1, 'cron_completions': 1,
            'started_at': starts[0][0].isoformat(), 'completed_at': completed.isoformat()}


def observe(profile: Path, date: str, channel: str | None = None):
    """Inspect the selected local profile without running a job or sending a message."""
    from datetime import timedelta
    import os
    import subprocess
    from zoneinfo import ZoneInfo
    from dotenv import dotenv_values
    from .discord_audience import DiscordAPI

    start = datetime.fromisoformat(date + 'T07:00:00').replace(tzinfo=ZoneInfo('America/Toronto'))
    end = start + timedelta(minutes=15)
    if datetime.now(start.tzinfo) < end:
        raise ValueError('The automatic observation window has not finished')
    configuration = json.loads((profile / 'lifeos-memory.json').read_text())
    bindings = configuration.get('discord_channels', {})
    if channel is None:
        if len(bindings) != 1:
            raise ValueError('The observation requires one selected private Discord channel')
        channel = next(iter(bindings))
    if channel not in bindings:
        raise ValueError('The observation channel must belong to the selected profile')
    root = Path(configuration['root'])
    environment = dict(os.environ, XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
        DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
    process = subprocess.run(['systemctl', '--user', 'show', 'com.lifeos.pulse.service',
        '--property=ActiveState', '--property=MainPID'], capture_output=True, text=True,
        env=environment, timeout=20, check=True)
    properties = dict(line.split('=', 1) for line in process.stdout.splitlines() if '=' in line)
    if properties.get('ActiveState') != 'active' or not properties.get('MainPID', '').isdecimal():
        raise ValueError('The selected Pulse service must be active')
    process_environment = Path('/proc') / properties['MainPID'] / 'environ'
    variables = dict(item.split(b'=', 1) for item in process_environment.read_bytes().split(b'\0') if b'=' in item)
    timezone = variables.get(b'TZ', b'').decode()
    if not timezone:
        timezone = subprocess.run(['timedatectl', 'show', '--property=Timezone', '--value'],
            capture_output=True, text=True, timeout=20, check=True).stdout.strip()
    system_path, user_path = root/'LIFEOS/PULSE/PULSE.toml', root/'LIFEOS/USER/CONFIG/PULSE.user.toml'
    schedule = morning_schedule(system_path, user_path, timezone)
    journal = subprocess.run(['journalctl', '--user', '-u', 'com.lifeos.pulse.service',
        '--since', start.isoformat(), '--until', end.isoformat(), '--output=json', '--no-pager'],
        capture_output=True, text=True, env=environment, timeout=30, check=True).stdout
    state_path = root/'LIFEOS/PULSE/state/state.json'
    state = json.loads(state_path.read_text())['jobs'].get(JOB, {})
    execution = morning_execution(journal, state, start, end, channel)
    token = dotenv_values(profile / '.env').get('DISCORD_BOT_TOKEN', '')
    delivery = morning_delivery(DiscordAPI(token), channel, bindings[channel]['bot'], start, end)
    if not datetime.fromisoformat(execution['started_at']) <= datetime.fromisoformat(delivery['message_timestamp']) <= datetime.fromisoformat(execution['completed_at']):
        raise ValueError('The Discord delivery must occur during the observed cron execution')
    if schedule != morning_schedule(system_path, user_path, timezone) or state != json.loads(state_path.read_text())['jobs'].get(JOB, {}):
        raise ValueError('The morning source metadata changed during observation')
    release = json.loads((profile/'integration-release.json').read_text())
    return {'format': 2, 'status': 'PASS', 'version': release['version'], 'commit': release['commit'],
            'automatic_execution_verified': True, 'discord_delivery_verified': True,
            'window_start': start.isoformat(), 'window_end': end.isoformat(),
            'scheduler': schedule, 'execution': execution, 'discord': delivery}
