# ABOUTME: Changes one declared Pulse schedule for an authorized evening acceptance run.
# ABOUTME: Reuses installed execution and Discord observers and restores the normal schedule.
import argparse
from datetime import datetime, timedelta
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
import types
from zoneinfo import ZoneInfo

PROFILE = Path('/home/lifeos-hermes/.hermes')
STATE = PROFILE / 'operations/evening-acceptance-20261014'
JOB = 'life-morning-brief'
NORMAL = '0 7 * * *'
EVENING = '2 18 14 10 *'
START = datetime(2026, 10, 14, 18, 2, tzinfo=ZoneInfo('America/Toronto'))
END = START + timedelta(minutes=15)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    path = path.resolve(strict=True) if path.exists() else path
    fd, name = tempfile.mkstemp(prefix='.evening-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def replace_schedule(data, before, after):
    text = data.decode('utf-8')
    parsed = tomllib.loads(text)
    matches = [job for job in parsed.get('job', []) if job.get('name') == JOB]
    if len(matches) != 1 or matches[0].get('schedule') != before:
        raise ValueError('The selected job does not have the expected current schedule')
    if matches[0].get('enabled', True) is not True or matches[0].get('type', 'script') != 'script':
        raise ValueError('The selected job must remain an enabled script')
    blocks = list(re.finditer(r'(?m)^\[\[job\]\][ \t]*$', text))
    selected = []
    for index, match in enumerate(blocks):
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(text)
        block = text[match.start():end]
        if tomllib.loads(block)['job'][0].get('name') == JOB:
            selected.append((match.start(), end, block))
    if len(selected) != 1: raise ValueError('The job definition must be unambiguous')
    start, end, block = selected[0]
    block, count = re.subn(r'(?m)^(schedule[ \t]*=[ \t]*)"' + re.escape(before) + r'"[ \t]*$',
        lambda match: match[1] + json.dumps(after), block)
    if count != 1: raise ValueError('The selected schedule line must be unambiguous')
    result = (text[:start] + block + text[end:]).encode()
    matches[0]['schedule'] = after
    if tomllib.loads(result.decode()) != parsed:
        raise ValueError('Only the selected schedule may change')
    return result


def paths():
    config = json.loads((PROFILE / 'lifeos-memory.json').read_bytes())
    root = Path(config['root'])
    return config, root, root / 'LIFEOS/USER/CONFIG/PULSE.user.toml'


def service(*args):
    env = dict(os.environ, XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
        DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
    return subprocess.run(args, env=env, capture_output=True, text=True, timeout=30, check=True).stdout


def prepare():
    if datetime.now(START.tzinfo) >= START - timedelta(seconds=30):
        raise ValueError('The acceptance schedule must be prepared before its due time')
    _, root, user = paths()
    before = user.read_bytes()
    after = replace_schedule(before, NORMAL, EVENING)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=False)
    (STATE / 'pulse-user-before.toml').write_bytes(before)
    (STATE / 'pulse-user-before.toml').chmod(0o600)
    manifest = {'root': str(root), 'before_sha256': digest(before), 'after_sha256': digest(after),
        'normal_schedule': NORMAL, 'evening_schedule': EVENING,
        'window_start': START.isoformat(), 'window_end': END.isoformat()}
    (STATE / 'request.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (STATE / 'request.json').chmod(0o600)
    atomic(user, after)
    service('systemctl', '--user', 'restart', 'com.lifeos.pulse.service')
    if user.read_bytes() != after: raise ValueError('The schedule changes during preparation')
    return {'status': 'PREPARED', **manifest}


def restore():
    _, root, user = paths()
    request = json.loads((STATE / 'request.json').read_bytes())
    if str(root) != request['root']: raise ValueError('The selected installation changes')
    current = user.read_bytes()
    jobs = [job for job in tomllib.loads(current.decode()).get('job', []) if job.get('name') == JOB]
    if len(jobs) != 1: raise ValueError('The selected job definition changes')
    if jobs[0]['schedule'] == NORMAL:
        service('systemctl', '--user', 'restart', 'com.lifeos.pulse.service')
        return {'status': 'RESTORED', 'normal_schedule': NORMAL, 'already_restored': True}
    atomic(user, replace_schedule(current, EVENING, NORMAL))
    service('systemctl', '--user', 'restart', 'com.lifeos.pulse.service')
    receipt = {'status': 'RESTORED', 'normal_schedule': NORMAL,
        'all_original_bytes_restored': digest(user.read_bytes()) == request['before_sha256']}
    (STATE / 'restore.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def observe():
    if datetime.now(START.tzinfo) < END: raise ValueError('The full observation window has not finished')
    config, root, user = paths()
    request = json.loads((STATE / 'request.json').read_bytes())
    if str(root) != request['root'] or digest(user.read_bytes()) != request['after_sha256']:
        raise ValueError('The observed scheduler configuration changes')
    active = json.loads(service(str(PROFILE.parent / '.local/bin/hermes'), 'lifeos-version'))['active']
    if (active['version'] != '0.4.3' or active['verification'] != 'verified'
            or active['commit'] != 'a1abb579558edcf29f7cd04ecfd998995d48db54'
            or active['package_sha256'] != '1c7de7abc4014bfee83bc9bdcd4bfdb6c169526844d44491741d56645f400177'):
        raise ValueError('The active qualified package changes')
    properties = dict(line.split('=', 1) for line in service('systemctl', '--user', 'show',
        'com.lifeos.pulse.service', '--property=ActiveState', '--property=MainPID').splitlines() if '=' in line)
    if properties.get('ActiveState') != 'active': raise ValueError('Pulse must remain active')
    environment = dict(item.split(b'=', 1) for item in (Path('/proc') / properties['MainPID'] / 'environ').read_bytes().split(b'\0') if b'=' in item)
    if environment.get(b'TZ') != b'America/Toronto': raise ValueError('Pulse must use the selected timezone')
    package = types.ModuleType('installed_evening_observer')
    package.__path__ = [str(PROFILE / 'plugins/lifeos-hook-bridge')]
    sys.modules[package.__name__] = package
    module = importlib.import_module(package.__name__ + '.morning_observation')
    api = importlib.import_module(package.__name__ + '.discord_audience')
    journal = service('journalctl', '--user', '-u', 'com.lifeos.pulse.service', '--since', START.isoformat(),
        '--until', END.isoformat(), '--output=json', '--no-pager')
    state_path = root / 'LIFEOS/PULSE/state/state.json'
    state = json.loads(state_path.read_bytes())['jobs'][JOB]
    channel = '1558870196784205927'
    if config['discord_channels'][channel]['bot'] != '1558867947152347198':
        raise ValueError('The selected observation must use the existing Cerebo bot')
    execution = module.morning_execution(journal, state, START, END, channel)
    from dotenv import dotenv_values
    token = dotenv_values(PROFILE / '.env').get('DISCORD_BOT_TOKEN', '')
    delivery = module.morning_delivery(api.DiscordAPI(token), channel, config['discord_channels'][channel]['bot'], START, END)
    if not datetime.fromisoformat(execution['started_at']) <= datetime.fromisoformat(delivery['message_timestamp']) <= datetime.fromisoformat(execution['completed_at']):
        raise ValueError('The real delivery must occur inside the real cron execution')
    if digest(user.read_bytes()) != request['after_sha256'] or state != json.loads(state_path.read_bytes())['jobs'][JOB]:
        raise ValueError('The observed scheduling metadata changes before delivery')
    return {'format': 3, 'status': 'PASS', 'observation_kind': 'owner-rescheduled-automatic-run',
        'version': active['version'], 'commit': active['commit'], 'package_sha256': active['package_sha256'],
        'window_start': START.isoformat(), 'window_end': END.isoformat(),
        'automatic_execution_verified': True, 'discord_delivery_verified': True,
        'original_0700_wall_clock_observed': False,
        'scheduler': {key: value for key, value in request.items() if key != 'root'},
        'execution': execution, 'discord': delivery}


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'observe', 'restore'))
    args = parser.parse_args()
    if args.action == 'observe':
        try:
            result = observe()
        except Exception as error:
            result = {'format': 3, 'status': 'FAIL', 'error_type': type(error).__name__,
                'error': str(error) if isinstance(error, ValueError) else 'Inspect safe observer service metadata'}
        try:
            result['schedule_restoration'] = restore()
        except Exception as error:
            result['schedule_restoration'] = {'status': 'FAIL', 'error_type': type(error).__name__}
            result['status'] = 'FAIL'
        (STATE / 'automatic-evening-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    else:
        result = prepare() if args.action == 'prepare' else restore()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] != 'FAIL' else 1)
