# ABOUTME: Verifies native asynchronous reminder delivery to an approved private GitHub repository.
# ABOUTME: Measures real issue contents, repeated submissions, concurrent delivery, and authenticated retry.
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from uuid import uuid4

from lifeos_hook_bridge.bridge import HookBridge


def run(native, installed_settings, gh, bun, repository, home, output, token):
    os.umask(0o077)
    assert token and '\n' not in token, 'A credential must arrive through standard input'
    home.mkdir(mode=0o700)
    os.chdir(home)
    output.mkdir(mode=0o700)
    root = home / '.claude'
    work = root / 'LIFEOS/USER/WORK'
    work.mkdir(parents=True)
    (root / 'LIFEOS/MEMORY/STATE').mkdir(parents=True)
    (root / 'hooks').symlink_to(native / 'hooks', target_is_directory=True)
    for name in ('TOOLS', 'PULSE'):
        (root / 'LIFEOS' / name).symlink_to(native / 'LIFEOS' / name, target_is_directory=True)
    binaries = home / 'bin'
    binaries.mkdir()
    (binaries / 'gh').symlink_to(gh)
    (binaries / 'bun').symlink_to(bun)
    environment = {**os.environ, 'HOME': str(home), 'GH_CONFIG_DIR': str(home / '.config/gh'),
                   'GH_TOKEN': token, 'PATH': str(binaries) + os.pathsep + os.environ['PATH'],
                   'LIFEOS_DIR': str(root / 'LIFEOS'), 'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'TZ': 'UTC'}
    for key in ('GITHUB_TOKEN', 'GH_ENTERPRISE_TOKEN', 'GITHUB_ENTERPRISE_TOKEN', 'GH_HOST',
                'LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_INTERNAL', 'CLAUDE_CONFIG_DIR', 'LIFEOS_CONFIG_DIR'):
        environment.pop(key, None)

    def github(arguments, check=True):
        result = subprocess.run([str(gh), *arguments], env=environment, cwd=home,
                                capture_output=True, text=True, timeout=40)
        if check:
            assert result.returncode == 0, (arguments, result.returncode, result.stderr)
        return result

    metadata = json.loads(github(['api', 'repos/' + repository]).stdout)
    assert metadata['private'] and metadata['full_name'].lower() == repository.lower(), metadata
    (output / 'repository.json').write_text(json.dumps({key: metadata[key] for key in
        ('full_name', 'private', 'html_url', 'has_issues')}, indent=2) + '\n')
    labels = ['Type:reminder', 'Type:research', 'Type:queue', 'Property:internal',
              'Status:queued', 'Priority:P3', 'Agent:Cerebo', 'pai-sync']
    for label in labels:
        github(['label', 'create', label, '--repo', repository, '--color', '6E7781', '--force'])
    attestation = {'repo': repository, 'privacy': {'verified_private': True,
        'verified_at': datetime.now(timezone.utc).isoformat(), 'visibility': 'PRIVATE',
        'verification_command': 'gh api repos/' + repository}}
    (work / 'work_repo.json').write_text(json.dumps(attestation, indent=2) + '\n')
    registered = json.loads(installed_settings.read_text())['hooks']['UserPromptSubmit']
    hooks = [hook for group in registered for hook in group['hooks']
             if 'ReminderRouter.hook.ts' in hook.get('command', '')]
    assert len(hooks) == 1 and hooks[0].get('async') is True, hooks
    settings = root / 'settings.json'
    settings.write_text(json.dumps({'daidentity': {'name': 'Cerebo'},
        'hooks': {'UserPromptSubmit': [{'hooks': hooks}]}}))
    (output / 'registration.json').write_text(json.dumps(hooks[0], indent=2) + '\n')
    (output / 'source-identity.json').write_text(json.dumps({str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [native / 'hooks/ReminderRouter.hook.ts', native / 'hooks/lib/work-config.ts',
                     Path(__file__).resolve(), Path(sys.modules[HookBridge.__module__].__file__)]}, indent=2) + '\n')
    processes = []
    lock = threading.Lock()
    actual_popen = subprocess.Popen

    def observe(arguments, *args, **kwargs):
        process = actual_popen(arguments, *args, **kwargs)
        if isinstance(arguments, list) and any(str(part).endswith('/hook_runner.py') for part in arguments):
            with lock:
                processes.append(process)
        return process

    bridges = []
    measurements = []
    marker = 'SYNTHETIC_LIFEOS_' + uuid4().hex[:12]
    issue_numbers = []

    def bridge(credential=token):
        current = HookBridge(settings, root, lifeos_home=home)
        current.environment.update(environment, GH_TOKEN=credential)
        bridges.append(current)
        return current

    def deliver(current, prompt, session):
        result = current.pre_llm_call(prompt, session_id=session)
        assert result is None, result

    def finish():
        for process in processes:
            code = process.wait(timeout=40)
            assert code == 0, (process.pid, code)
        for current in bridges:
            assert not list(current.transcript_dir.glob('async-hook-*.json')), 'A detached payload remains'

    def issues():
        query = '/issues?state=all&per_page=100&acceptance_read=' + str(time.time_ns())
        rows = json.loads(github(['api', 'repos/' + repository + query,
                                 '-H', 'Cache-Control: no-cache']).stdout)
        return [row for row in rows if marker in row.get('body', '') and 'pull_request' not in row]

    def matching_issues(prompt):
        deadline = time.monotonic() + 30
        while True:
            matching = [row for row in issues() if prompt in row['body']]
            if matching or time.monotonic() >= deadline:
                return matching
            time.sleep(1)

    def state():
        path = root / 'LIFEOS/MEMORY/STATE/reminder-router-seen.json'
        return json.loads(path.read_text()) if path.exists() else {}

    subprocess.Popen = observe
    try:
        for kind, prompt in [('reminder', 'Remind me to inspect ' + marker + ' tomorrow'),
                             ('research', 'Research the ' + marker + ' paper'),
                             ('queue', 'Queue this for later ' + marker)]:
            session = marker + '-' + kind
            deliver(bridge(), prompt, session)
            finish()
            matching = matching_issues(prompt)
            assert len(matching) == 1, matching
            issue = matching[0]
            actual_labels = {label['name'] for label in issue['labels']}
            assert set(labels) - {'Type:reminder', 'Type:research', 'Type:queue'} <= actual_labels, actual_labels
            assert 'Type:' + kind in actual_labels and '**Kind:** ' + kind in issue['body'], issue
            if kind == 'reminder':
                due = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
                assert '**Due:** ' + due in issue['body'], issue
            else:
                assert '**Due:**' not in issue['body'], issue
            before = state()
            deliver(bridge(), prompt, session)
            finish()
            assert state() == before
            assert len([row for row in issues() if prompt in row['body']]) == 1
            measurements.append({'kind': kind, 'issue_number': issue['number'],
                'url': issue['html_url'], 'labels': sorted(actual_labels), 'repeat_count': 2, 'issue_count': 1})
        parallel_prompt = 'Remind me to inspect concurrent ' + marker + ' tomorrow'
        parallel_session = marker + '-parallel'
        parallel_bridges = [bridge() for _ in range(8)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda current: deliver(current, parallel_prompt, parallel_session), parallel_bridges))
        finish()
        parallel = matching_issues(parallel_prompt)
        assert len(parallel) == 1 and len(state()[parallel_session]) == 1, (parallel, state())
        measurements.append({'kind': 'concurrent', 'submissions': 8, 'issue_count': 1,
                             'issue_number': parallel[0]['number'], 'url': parallel[0]['html_url']})
        retry_prompt = 'Remind me to inspect authenticated retry ' + marker + ' tomorrow'
        retry_session = marker + '-retry'
        failed = bridge('SYNTHETIC_INVALID_CREDENTIAL')
        invalid = {**environment, 'GH_TOKEN': 'SYNTHETIC_INVALID_CREDENTIAL'}
        refusal = subprocess.run([str(gh), 'api', 'repos/' + repository], env=invalid,
                                 capture_output=True, text=True, timeout=30)
        assert refusal.returncode != 0 and '401' in refusal.stderr, refusal.stderr
        (output / 'authentication-refusal.txt').write_text(refusal.stderr)
        deliver(failed, retry_prompt, retry_session)
        finish()
        assert retry_session not in state() and not [row for row in issues() if retry_prompt in row['body']]
        deliver(bridge(), retry_prompt, retry_session)
        finish()
        retried = matching_issues(retry_prompt)
        assert len(retried) == 1 and len(state()[retry_session]) == 1, (retried, state())
        deliver(bridge(), retry_prompt, retry_session)
        finish()
        assert len([row for row in issues() if retry_prompt in row['body']]) == 1
        measurements.append({'kind': 'authenticated-retry', 'failure_http_status': 401,
            'failure_published_marker': False, 'retry_issue_count': 1,
            'issue_number': retried[0]['number'], 'url': retried[0]['html_url']})
        observed = issues()
        assert len(observed) == 5, observed
        (output / 'issues-created.json').write_text(json.dumps(observed, indent=2) + '\n')
        (output / 'delivery-state.json').write_text(json.dumps(state(), indent=2) + '\n')
        (output / 'result.json').write_text(json.dumps({'repository': repository, 'private': True,
            'target': '192.168.8.252', 'marker': marker, 'controls': measurements,
            'actual_runner_processes': len(processes), 'runner_exit_codes': [p.returncode for p in processes],
            'issues_created': len(observed)}, indent=2) + '\n')
    finally:
        subprocess.Popen = actual_popen
        for current in bridges:
            current.close()
        finish()
        observed = issues()
        closed = []
        for issue in observed:
            result = github(['api', '--method', 'PATCH', 'repos/' + repository + '/issues/' + str(issue['number']),
                             '-f', 'state=closed'])
            closed.append(json.loads(result.stdout))
            issue_numbers.append(issue['number'])
        assert all(row['state'] == 'closed' for row in closed), closed
        (output / 'issues-closed.json').write_text(json.dumps(closed, indent=2) + '\n')
        (work / 'work_repo.json').unlink(missing_ok=True)
        (binaries / 'gh').unlink(missing_ok=True)
        assert not (home / '.config/gh/hosts.yml').exists(), 'GitHub authentication was persisted'
        (output / 'cleanup.json').write_text(json.dumps({'closed_issue_numbers': issue_numbers,
            'work_repository_binding_removed': True, 'gh_binary_link_removed': True,
            'github_login_persisted': False}, indent=2) + '\n')
    (output / '.done').write_text('0\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('native', 'installed-settings', 'gh', 'bun', 'home', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository', required=True)
    arguments = parser.parse_args()
    run(arguments.native, arguments.installed_settings, arguments.gh, arguments.bun,
        arguments.repository, arguments.home, arguments.output, sys.stdin.read().strip())
