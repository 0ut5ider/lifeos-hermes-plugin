# ABOUTME: Runs matching filesystem fixtures through real Claude Code and Hermes lifecycle events.
# ABOUTME: Retains hook input, file state, and explicit assertions for selected native effects.
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import http.server
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import threading
import time


CASES = {
    'healer-executable': [('SessionStart.1.1', 'hooks/HookHealer.hook.ts')],
    'healer-containment': [('SessionStart.1.1', 'hooks/HookHealer.hook.ts')],
    'kitty-cli': [('SessionStart.1.2', 'hooks/KittyEnvPersist.hook.ts')],
    'kitty-remote': [('SessionStart.1.2', 'hooks/KittyEnvPersist.hook.ts')],
    'kitty-subagent': [('SessionStart.1.2', 'hooks/KittyEnvPersist.hook.ts')],
    'context-desktop': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-disabled': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-remote': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-subagent': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-advisory-steady': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-advisory-cleared': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-delivery-desktop': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-delivery-remote': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-delivery-disabled': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-response-desktop': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-response-remote': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'context-response-disabled': [('SessionStart.1.3', 'hooks/LoadContext.hook.ts')],
    'response-cache-empty': [('Stop.1.1', 'hooks/LastResponseCache.hook.ts')],
    'response-cache-replace': [('Stop.1.1', 'hooks/LastResponseCache.hook.ts')],
    'response-cache-limit': [('Stop.1.1', 'hooks/LastResponseCache.hook.ts')],
    'freshness-reviewed': [('SessionStart.1.4', 'LIFEOS/TOOLS/FreshnessCache.ts')],
    'settings-merge': [('SessionStart.1.5', 'LIFEOS/TOOLS/MergeSettings.ts')],
    'settings-backport': [('SessionStart.1.5', 'LIFEOS/TOOLS/SettingsBackport.ts')],
    'cleanup-work': [('SessionEnd.1.2', 'hooks/SessionCleanup.hook.ts')],
    'learning-active': [('SessionEnd.1.1', 'hooks/WorkCompletionLearning.hook.ts')],
    'learning-complete': [('SessionEnd.1.1', 'hooks/WorkCompletionLearning.hook.ts')],
    'cleanup-learning-parallel': [('SessionEnd.1.1', 'hooks/WorkCompletionLearning.hook.ts'),
                                  ('SessionEnd.1.2', 'hooks/SessionCleanup.hook.ts')],
    'update-counts-no-oauth': [('SessionEnd.1.3', 'hooks/UpdateCounts.hook.ts')],
    'memory-health-critical': [('SessionEnd.1.4', 'hooks/MemoryHealthGate.hook.ts')],
    'doc-inventory-drift': [('SessionEnd.1.5', 'hooks/DocIntegrity.hook.ts')],
    'doc-inventory-clean': [('SessionEnd.1.5', 'hooks/DocIntegrity.hook.ts')],
    'doc-inventory-unparseable': [('SessionEnd.1.5', 'hooks/DocIntegrity.hook.ts')],
}
BLOCK_REASON = 'PAIR_BLOCK_BEFORE_MODEL'
ADVISORY_KEY = 'doc.integrity.memory_dir missing_active:KNOWLEDGE'
RELATIONSHIP_TEXT = '- PAIR_RELATIONSHIP_NOTE\n'
WISDOM_TEXT = '### PAIR_WISDOM_GUIDANCE [CRYSTAL: 95%]\n### PAIR_LOW_CONFIDENCE [CRYSTAL: 50%]\n'
RESPONSE_PREFIXES = ('context-response-', 'response-cache-')


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_pair(case: dict) -> list[str]:
    name = case['id']
    if name not in CASES:
        return [f'{name}: unknown case']
    errors = []
    response = name.startswith(RESPONSE_PREFIXES)
    delivery = response or name.startswith('context-delivery-')
    native, hermes = case['native'], case['hermes']
    if native['before'] != hermes['before'] or native['after'] != hermes['after']:
        errors.append(f'{name}: paired state differs')
    for side in (native, hermes):
        if side.get('cli_exit_code') != (1 if delivery and not response else 0):
            errors.append(f'{name}: CLI failed')
        if side.get('event') != CASES[name][0][0].split('.')[0]:
            errors.append(f'{name}: lifecycle event differs')
        if len(side.get('hook_exit_codes', [])) != len(CASES[name]):
            errors.append(f'{name}: hook invocation count differs')
        if not side.get('hook_exit_codes') or any(code != 0 for code in side['hook_exit_codes']):
            errors.append(f'{name}: hook failed')
        if delivery and side.get('model_generation_requests') != 1:
            errors.append(f'{name}: model delivery was not observed')
        elif not delivery and side.get('model_generation_requests') != 0:
            errors.append(f'{name}: model generation was attempted')
        if response and side.get('model_successful_responses') != 1:
            errors.append(f'{name}: successful model response was not observed')
        before, after = side['before'], side['after']
        if name.startswith('context-'):
            loaded = name in {'context-desktop', 'context-delivery-desktop', 'context-response-desktop'}
            marker = None
            if loaded or name in {'context-advisory-steady', 'context-advisory-cleared'}:
                marker = {'keys': [] if name == 'context-advisory-cleared' else [ADVISORY_KEY],
                          'sessions_since_emit': 1 if name == 'context-advisory-steady' else 0,
                          'last_emitted_at_present': True}
            expected = {'relationship_present': loaded, 'wisdom_present': loaded,
                        'low_confidence_present': False, 'advisory_present': loaded,
                        'sources_preserved': True, 'marker': marker,
                        'timing_recorded': name != 'context-subagent',
                        'ready_present': not loaded and name != 'context-subagent'}
            if delivery:
                expected['model_context_contains'] = {'relationship': loaded, 'wisdom': loaded,
                                                      'advisory': loaded, 'low_confidence': False}
            if response:
                expected['user_response_delivered'] = True
            if before != {'marker_present': name in {'context-advisory-steady', 'context-advisory-cleared'}} or after != expected:
                errors.append(f'{name}: context effect is missing')
        elif name.startswith('response-cache-'):
            prior = name != 'response-cache-empty'
            expected = {
                    'cache_present': True, 'cache_is_nonempty': True, 'prior_marker_present': False,
                    'cache_within_limit': True, 'cache_matches_stop_message': True,
                    'stop_message_matches_user_response': True,
                    'user_response_delivered': True}
            if name == 'response-cache-limit':
                expected.update(user_response_exceeds_limit=True, cache_characters=2000)
            if before != {'cache_present': prior, 'prior_marker_present': prior} or after != expected:
                errors.append(f'{name}: response cache effect is missing')
        elif name in {'kitty-remote', 'kitty-subagent'}:
            if before != {'stale_title_present': True} or after != {
                    'shared_environment_present': False, 'session_environment_present': False,
                    'stale_title_preserved': True}:
                errors.append(f'{name}: terminal gate effect is missing')
        elif name == 'healer-executable':
            if before.get('executable') is not False or not all(after.get(key) is True for key in
                    ('executable', 'healed_target', 'unrelated_preserved')):
                errors.append(f'{name}: executable repair is missing')
        elif name == 'healer-containment':
            if not (before.get('target_executable') is False and after.get('target_executable') is False
                    and after.get('containment_refused') is True and after.get('target_content_preserved') is True):
                errors.append(f'{name}: containment effect is missing')
        elif name == 'kitty-cli':
            if not (before.get('environment_present') is False and before.get('stale_title_present') is True
                    and after.get('shared_environment_matches') is True
                    and after.get('session_environment_matches') is True and after.get('stale_title_present') is False):
                errors.append(f'{name}: terminal persistence effect is missing')
        elif name == 'memory-health-critical':
            if not (before.get('health_rows') == 0 and after.get('health_rows') == 1
                    and after.get('overall') == 'critical' and after.get('critical_count', 0) > 0
                    and after.get('critical_count_matches') is True
                    and after.get('required_hook_missing') is True and after.get('warning_present') is True):
                errors.append(f'{name}: health effect is missing')
        elif name.startswith('doc-inventory-'):
            expected = {'doc-inventory-drift': ['missing_active:KNOWLEDGE', 'unknown_on_disk:SURPRISE'],
                        'doc-inventory-clean': [], 'doc-inventory-unparseable': ['inventory_unparseable:doc']}[name]
            if not (before.get('inventory_events') == 0 and after.get('inventory_events') == 1
                    and after.get('ok') is (not expected) and after.get('finding_count') == len(expected)
                    and after.get('finding_keys') == expected and after.get('unrelated_event_preserved') is True):
                errors.append(f'{name}: inventory effect is missing')
        elif name == 'freshness-reviewed':
            if before.get('cache_present') is not False or not (
                    after.get('telos_stale') is False and after.get('total_matches_files') is True
                    and after.get('fresh_count', 0) > 0 and after.get('generated_at_present') is True):
                errors.append(f'{name}: freshness effect is missing')
        elif name in {'settings-merge', 'settings-backport'}:
            expected = 'edited' if name == 'settings-backport' else 'overlay'
            if not (after.get('system_value') == 'system' and after.get('user_value') == expected
                    and after.get('overlay_value') == expected and after.get('snapshot_matches_generated') is True):
                errors.append(f'{name}: settings effect is missing')
        elif name in {'cleanup-work', 'cleanup-learning-parallel'}:
            if not (before.get('work_phase') == 'execute' and after.get('work_phase') == 'complete'
                    and after.get('isa_phase') == 'complete' and after.get('isa_status') == 'COMPLETED'
                    and after.get('current_name_present') is False and after.get('unrelated_name_preserved') is True):
                errors.append(f'{name}: cleanup effect is missing')
        elif name == 'update-counts-no-oauth':
            if not (before.get('credentials_present') is False and
                    after.get('credentials_present') is False and after.get('usage_cache_present') is False):
                errors.append(f'{name}: credential-free no-op is missing')
        elif name not in {'learning-active', 'learning-complete'}:
            errors.append(f'{name}: unknown case')
        if name in {'learning-active', 'learning-complete', 'cleanup-learning-parallel'}:
            if not (before.get('learning_count') == 0 and after.get('learning_count') == 1
                    and after.get('learning_session_matches') is True and after.get('claims_closed') == '1/1'):
                errors.append(f'{name}: learning effect is missing')
    return sorted(set(errors))


def fixture_files(home: Path) -> dict:
    root = home / '.claude'
    files = list(root.glob('settings*.json'))
    for name in ('hooks', 'LIFEOS'):
        files.extend(path for path in (root / name).rglob('*') if path.is_file())
    return {str(path.relative_to(root)): {'mode': oct(path.stat().st_mode & 0o777),
                                         'content_base64': base64.b64encode(path.read_bytes()).decode()}
            for path in sorted(files)}


def seed_work(home: Path, case: str, session_id: str) -> None:
    lifeos = home / '.claude/LIFEOS'
    state = lifeos / 'MEMORY/STATE'
    work = lifeos / 'MEMORY/WORK/paired-work'
    now = datetime.now(timezone.utc).isoformat()
    phase = 'complete' if case == 'learning-complete' else 'execute'
    write_json(state / 'work.json', {'sessions': {'paired-work': {
        'sessionUUID': session_id, 'phase': phase, 'task': 'Verify paired learning',
        'updatedAt': now, 'started': now, 'progress': '1/1', 'isa': True,
    }}})
    write_json(state / 'session-names.json', {session_id: 'Paired Current Session',
                                            'unrelated-session': 'Keep Unrelated Session'})
    work.mkdir(parents=True, exist_ok=True)
    status = 'COMPLETED' if phase == 'complete' else 'ACTIVE'
    (work / 'ISA.md').write_text(
        f'---\ntask: Verify paired learning\nphase: {phase}\nstatus: {status}\n'
        f'created_at: {now}\ncompleted_at: null\nupdated: {now}\n---\n'
        '# Paired work\n\n## Claims\n- [x] Learning survives cleanup\n')


def state_snapshot(home: Path, case: str, session_id: str = '', *, after: bool = False) -> dict:
    root = home / '.claude'
    lifeos = root / 'LIFEOS'
    if case.startswith('response-cache-'):
        path = lifeos / 'MEMORY/STATE/last-response.txt'
        content = path.read_text() if path.is_file() else ''
        result = {'cache_present': path.is_file(), 'prior_marker_present': 'PAIR_PREVIOUS_RESPONSE' in content}
        if after:
            result.update(cache_is_nonempty=bool(content), cache_within_limit=len(content) <= 2000)
        return result
    if case.startswith('context-'):
        marker_path = lifeos / 'MEMORY/STATE/advisory-readback.json'
        if not after:
            return {'marker_present': marker_path.exists()}
        trace = read_json_lines(home / 'hooks.jsonl')[0]
        stdout = trace['stdout']
        marker = read_json(marker_path) if marker_path.exists() else None
        if marker is not None:
            marker = {'keys': marker['keys'], 'sessions_since_emit': marker['sessions_since_emit'],
                      'last_emitted_at_present': bool(marker['last_emitted_at'])}
        sources = read_json(home / 'context-sources.json')
        return {'relationship_present': 'PAIR_RELATIONSHIP_NOTE' in stdout,
                'wisdom_present': 'PAIR_WISDOM_GUIDANCE' in stdout,
                'low_confidence_present': 'PAIR_LOW_CONFIDENCE' in stdout,
                'advisory_present': 'PAIR_ADVISORY_FINDING' in stdout,
                'sources_preserved': all((root / name).read_text() == content for name, content in sources.items()),
                'marker': marker, 'timing_recorded': 'Session start time recorded' in trace['stderr'],
                'ready_present': 'LifeOS session ready' in stdout}
    if case in {'kitty-remote', 'kitty-subagent'}:
        state = lifeos / 'MEMORY/STATE'
        stale = state / 'tab-titles/777.json'
        if not after:
            return {'stale_title_present': stale.exists()}
        return {'shared_environment_present': (state / 'kitty-env.json').exists(),
                'session_environment_present': (state / 'kitty-sessions' / (session_id + '.json')).exists(),
                'stale_title_preserved': stale.exists() and read_json(stale) == {
                    'title': 'Old session title', 'state': 'working'}}
    if case == 'healer-containment':
        target = home / 'outside.sh'
        result = {'target_executable': bool(target.stat().st_mode & 0o111)}
        if after:
            audit = lifeos / 'MEMORY/OBSERVABILITY/hook-healer.jsonl'
            rows = [json.loads(line) for line in audit.read_text().splitlines()] if audit.exists() else []
            result.update(containment_refused=any(row.get('event') == 'containment-refused'
                          and row.get('path') == str(root / 'hooks/Registered.hook.sh') for row in rows),
                          target_content_preserved=target.read_text() == '#!/bin/sh\nexit 0\n')
        return result
    if case == 'kitty-cli':
        state = lifeos / 'MEMORY/STATE'
        stale = state / 'tab-titles/777.json'
        shared = state / 'kitty-env.json'
        if not after:
            return {'environment_present': shared.exists(), 'stale_title_present': stale.exists()}
        session = state / 'kitty-sessions' / (session_id + '.json')
        listen = 'unix:' + str(home / 'no-kitty.sock')
        return {'shared_environment_matches': shared.exists() and read_json(shared) == {
                    'KITTY_LISTEN_ON': listen, 'KITTY_WINDOW_ID': '777'},
                'session_environment_matches': session.exists() and read_json(session) == {
                    'listenOn': listen, 'windowId': '777'}, 'stale_title_present': stale.exists()}
    if case == 'memory-health-critical':
        path = lifeos / 'MEMORY/OBSERVABILITY/memory-health.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        if not after:
            return {'health_rows': len(rows)}
        report = rows[-1] if rows else {}
        findings = report.get('findings', [])
        traces = [json.loads(line) for line in (home / 'hooks.jsonl').read_text().splitlines()]
        critical = report.get('counts', {}).get('critical', 0)
        return {'health_rows': len(rows), 'overall': report.get('overall'), 'critical_count': critical,
                'critical_count_matches': critical == sum(row.get('severity') == 'critical' for row in findings),
                'required_hook_missing': any(row.get('id') == 'hook-file-missing:MemoryTurnStart.hook.ts'
                                            for row in findings),
                'warning_present': any('Memory health: CRITICAL' in row['stderr'] for row in traces)}
    if case.startswith('doc-inventory-'):
        path = lifeos / 'MEMORY/STATE/events.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        inventory = [row for row in rows if row.get('type') == 'doc.integrity.memory_dir']
        if not after:
            return {'inventory_events': len(inventory)}
        report = inventory[-1] if inventory else {}
        return {'inventory_events': len(inventory), 'ok': report.get('ok'),
                'finding_count': report.get('finding_count'),
                'finding_keys': sorted(row['key'] for row in report.get('findings', [])),
                'unrelated_event_preserved': rows[0] == {'type': 'fixture.unrelated', 'value': 'Keep existing event'}}
    if case == 'healer-executable':
        target = root / 'hooks/Registered.hook.sh'
        if not after:
            return {'executable': bool(target.stat().st_mode & 0o111)}
        audit = lifeos / 'MEMORY/OBSERVABILITY/hook-healer.jsonl'
        rows = [json.loads(line) for line in audit.read_text().splitlines()] if audit.exists() else []
        return {'executable': bool(target.stat().st_mode & 0o111),
                'healed_target': any(row.get('event') == 'healed' and row.get('path') == str(target) for row in rows),
                'unrelated_preserved': (root / 'hooks/Unregistered.sh').stat().st_mode & 0o777 == 0o644}
    if case == 'freshness-reviewed':
        cache = lifeos / 'USER/CACHE/freshness.json'
        if not after:
            return {'cache_present': cache.exists()}
        data = read_json(cache)
        telos = next(row for row in data['files'] if row['slug'] == 'telos')
        return {'total': data['total'], 'fresh_count': data['fresh_count'],
                'total_matches_files': data['total'] == len(data['files']), 'telos_stale': telos['stale'],
                'generated_at_present': bool(data.get('generated_at')),
                'cache_without_generated_at': {key: value for key, value in data.items() if key != 'generated_at'}}
    if case in {'settings-merge', 'settings-backport'}:
        merged = read_json(root / 'settings.json')
        if not after:
            return {'user_value': merged.get('env', {}).get('USER_VALUE')}
        user = read_json(lifeos / 'USER/CONFIG/settings.user.json')
        snapshot = read_json(lifeos / 'MEMORY/STATE/settings-merge-snapshot.json')
        return {'system_value': merged['env']['SYSTEM_VALUE'], 'user_value': merged['env']['USER_VALUE'],
                'overlay_value': user['env']['USER_VALUE'], 'snapshot_matches_generated': snapshot == merged}
    if case == 'update-counts-no-oauth':
        result = {'credentials_present': (root / '.credentials.json').exists()}
        if after:
            result['usage_cache_present'] = (lifeos / 'MEMORY/STATE/usage-cache.json').exists()
        return result
    state = lifeos / 'MEMORY/STATE'
    registry = read_json(state / 'work.json')['sessions']['paired-work']
    learnings = list((lifeos / 'MEMORY/LEARNING').rglob('*_work_*.md'))
    if not after:
        return {'work_phase': registry['phase'], 'learning_count': len(learnings)}
    result = {}
    if case in {'cleanup-work', 'cleanup-learning-parallel'}:
        names = read_json(state / 'session-names.json')
        isa = (lifeos / 'MEMORY/WORK/paired-work/ISA.md').read_text()
        result.update(work_phase=registry['phase'], isa_phase='complete' if '\nphase: complete\n' in isa else 'other',
                      isa_status='COMPLETED' if '\nstatus: COMPLETED\n' in isa else 'other',
                      current_name_present=session_id in names,
                      unrelated_name_preserved=names.get('unrelated-session') == 'Keep Unrelated Session')
    if case in {'learning-active', 'learning-complete', 'cleanup-learning-parallel'}:
        content = learnings[0].read_text() if len(learnings) == 1 else ''
        result.update(learning_count=len(learnings), learning_session_matches=f'**Session:** {session_id}' in content,
                      claims_closed='1/1' if '1/1 closed' in content else 'other')
    return result


def fixture_event(case: str) -> None:
    payload = json.load(sys.stdin)
    home = Path.home()
    event = payload['hook_event_name']
    with (home / 'fixture-events.jsonl').open('a') as stream:
        stream.write(json.dumps(payload) + '\n')
    if event == 'SessionStart' and case in {
            'cleanup-work', 'learning-active', 'learning-complete', 'cleanup-learning-parallel'}:
        seed_work(home, case, payload['session_id'])
        write_json(home / 'before-state.json', state_snapshot(home, case, payload['session_id']))
        write_json(home / 'fixture-files-before.json', fixture_files(home))
    if event == 'UserPromptSubmit' and not (case.startswith(RESPONSE_PREFIXES) or case.startswith('context-delivery-')):
        print(json.dumps({'decision': 'block', 'reason': BLOCK_REASON}))


def read_json_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def seed_context(home: Path, case: str) -> None:
    root = home / '.claude'
    today = datetime.now(timezone.utc)
    relationship = f'LIFEOS/MEMORY/RELATIONSHIP/{today:%Y-%m}/{today:%Y-%m-%d}.md'
    event = {'type': 'doc.integrity.memory_dir', 'source': 'fixture',
             'timestamp': today.isoformat(), 'ok': case == 'context-advisory-cleared',
             'findings': [] if case == 'context-advisory-cleared' else [
                 {'key': 'missing_active:KNOWLEDGE', 'detail': 'PAIR_ADVISORY_FINDING'}]}
    sources = {relationship: RELATIONSHIP_TEXT, 'LIFEOS/MEMORY/WISDOM/FRAMES/fixture.md': WISDOM_TEXT,
               'LIFEOS/MEMORY/STATE/events.jsonl': json.dumps(event) + '\n'}
    for name, content in sources.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    write_json(home / 'context-sources.json', sources)
    if case in {'context-advisory-steady', 'context-advisory-cleared'}:
        write_json(root / 'LIFEOS/MEMORY/STATE/advisory-readback.json', {
            'v': 1, 'keys': [ADVISORY_KEY], 'sessions_since_emit': 0,
            'last_emitted_at': '2026-10-01T00:00:00.000Z'})


def hook_commands(home: Path, case: str, source: Path, trace_script: Path) -> list[tuple[str, str, list[Path]]]:
    root = home / '.claude'
    commands = []
    for identifier, relative in CASES[case]:
        path = source / relative
        source_files = [path]
        if case == 'memory-health-critical':
            source_files.append(source / 'LIFEOS/TOOLS/MemoryHealthCheck.ts')
        if case.startswith('context-'):
            source_files.extend(source / name for name in (
                'hooks/lib/learning-readback.ts', 'hooks/lib/advisory-readback.ts',
                'hooks/lib/notifications.ts'))
            access = source / 'LIFEOS/TOOLS/lib/MemoryAccess.ts'
            if access.exists():
                source_files.append(access)
        command = f'bun {shlex.quote(str(path))}'
        if case == 'freshness-reviewed':
            command += ' --quiet'
        if case in {'settings-merge', 'settings-backport'}:
            merge = source / 'LIFEOS/TOOLS/MergeSettings.ts'
            command = ' '.join(shlex.quote(value) for value in (
                'bun', str(merge), '--system', str(root / 'settings.system.json'),
                '--user', str(root / 'LIFEOS/USER/CONFIG/settings.user.json'),
                '--output', str(root / 'settings.json')))
            if case == 'settings-backport':
                command = f'bun {shlex.quote(str(path))}; ' + command
                source_files.append(merge)
        encoded = base64.b64encode(command.encode()).decode()
        wrapped = ' '.join(shlex.quote(value) for value in (
            '/usr/bin/python3', str(trace_script), 'run', identifier, str(home / 'hooks.jsonl'), encoded))
        commands.append((identifier, wrapped, source_files))
    return commands


def make_fixture(home: Path, case: str, source: Path, trace_script: Path) -> list[dict]:
    home.mkdir(parents=True)
    root = home / '.claude'
    root.mkdir()
    (home / 'project').mkdir()
    observer = ' '.join(shlex.quote(value) for value in (
        '/usr/bin/python3', str(Path(__file__).resolve()), 'fixture-event', case))
    commands = hook_commands(home, case, source, trace_script)
    hooks = {event: [{'hooks': [{'type': 'command', 'command': observer}]}]
             for event in ('SessionStart', 'UserPromptSubmit', 'SessionEnd')}
    event = commands[0][0].split('.')[0]
    hooks.setdefault(event, []).append({'hooks': [{'type': 'command', 'command': command, 'timeout': 30}
                                   for _, command, _ in commands]})
    settings = {'hooks': hooks}
    if case.startswith('response-cache-'):
        cache = root / 'LIFEOS/MEMORY/STATE/last-response.txt'
        cache.parent.mkdir(parents=True)
        if case != 'response-cache-empty':
            cache.write_text('PAIR_PREVIOUS_RESPONSE\n')
    if case in {'healer-executable', 'healer-containment'}:
        folder = root / 'hooks'
        folder.mkdir()
        for name in ('Registered.hook.sh', 'Unregistered.sh'):
            target = folder / name
            target.write_text('#!/bin/sh\nexit 0\n')
            target.chmod(0o644)
        hooks['Stop'] = [{'hooks': [{'type': 'command', 'command': str(folder / 'Registered.hook.sh')}]}]
        if case == 'healer-containment':
            external = home / 'outside.sh'
            external.write_text('#!/bin/sh\nexit 0\n')
            external.chmod(0o644)
            (folder / 'Registered.hook.sh').unlink()
            (folder / 'Registered.hook.sh').symlink_to(external)
    if case.startswith('kitty-'):
        write_json(root / 'LIFEOS/MEMORY/STATE/tab-titles/777.json',
                   {'title': 'Old session title', 'state': 'working'})
    if case.startswith('context-'):
        seed_context(home, case)
        if case in {'context-disabled', 'context-delivery-disabled', 'context-response-disabled', 'context-advisory-steady', 'context-advisory-cleared'}:
            settings['dynamicContext'] = {key: False for key in (
                'relationshipContext', 'learningReadback', 'advisoryReadback', 'activeWorkSummary')}
            if case not in {'context-disabled', 'context-delivery-disabled', 'context-response-disabled'}:
                settings['dynamicContext']['advisoryReadback'] = True
    if case == 'memory-health-critical':
        tools = root / 'LIFEOS/TOOLS'
        tools.mkdir(parents=True)
        (tools / 'MemoryHealthCheck.ts').symlink_to(source / 'LIFEOS/TOOLS/MemoryHealthCheck.ts')
    if case.startswith('doc-inventory-'):
        document = root / 'LIFEOS/DOCUMENTATION/Memory/MemorySystem.md'
        document.parent.mkdir(parents=True)
        content = '# Synthetic inventory\n'
        if case != 'doc-inventory-unparseable':
            content += ('\n## Directory Inventory\n\n| Directory | Class | Status | Purpose | Primary writers |\n'
                        '| --- | --- | --- | --- | --- |\n| `STATE/` | core | active | State | Fixture |\n'
                        '| `KNOWLEDGE/` | core | active | Notes | Fixture |\n'
                        '| `LEARNING/` | core | on-demand | Learning | Fixture |\n')
        document.write_text(content)
        memory = root / 'LIFEOS/MEMORY'
        (memory / '_PRIVATE').mkdir(parents=True)
        if case == 'doc-inventory-drift':
            (memory / 'SURPRISE').mkdir()
        elif case == 'doc-inventory-clean':
            (memory / 'KNOWLEDGE').mkdir()
        events = memory / 'STATE/events.jsonl'
        events.parent.mkdir(parents=True)
        events.write_text(json.dumps({'type': 'fixture.unrelated', 'value': 'Keep existing event'}) + '\n')
    if case == 'freshness-reviewed':
        telos = root / 'LIFEOS/USER/TELOS/TELOS.md'
        telos.parent.mkdir(parents=True)
        today = datetime.now(timezone.utc).date().isoformat()
        telos.write_text(f'---\nlast_updated: {today}\nlast_reviewed: {today}\nlast_reviewed_by: fixture\n---\n# Synthetic TELOS\n')
    if case in {'settings-merge', 'settings-backport'}:
        settings['env'] = {'SYSTEM_VALUE': 'system'}
        write_json(root / 'settings.system.json', settings)
        write_json(root / 'LIFEOS/USER/CONFIG/settings.user.json',
                   {'env': {'USER_VALUE': 'original' if case == 'settings-backport' else 'overlay'}})
        if case == 'settings-backport':
            settings['env']['USER_VALUE'] = 'original'
            write_json(root / 'LIFEOS/MEMORY/STATE/settings-merge-snapshot.json', settings)
            settings['env']['USER_VALUE'] = 'edited'
    write_json(root / 'settings.json', settings)
    if event == 'SessionStart' or case in {'update-counts-no-oauth', 'memory-health-critical'} or case.startswith(('doc-inventory-', 'response-cache-')):
        write_json(home / 'before-state.json', state_snapshot(home, case))
        write_json(home / 'fixture-files-before.json', fixture_files(home))
    return [{'id': identifier, 'command': command,
             'source_files': {str(path): digest(path) for path in paths}}
            for identifier, command, paths in commands]


class RequestGuard(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self.server.observed.append({'path': self.path, 'body': json.loads(body),
                                     'body_base64': base64.b64encode(body).decode(),
                                     'body_sha256': hashlib.sha256(body).hexdigest()})
        self.send_response(401)
        self.end_headers()
        self.wfile.write(b'{"error":{"type":"authentication_error","message":"MODEL_CALL_NOT_EXPECTED"}}')

    def log_message(self, *_):
        pass


def run_side(side: str, spec: dict, case: str, output: Path, endpoint: str, guard) -> dict:
    home = Path(spec['home_root']) / output.name / case
    definitions = make_fixture(home, case, Path(spec['hook_root']), Path(spec['trace_script']))
    environment = {key: value for key, value in os.environ.items() if key in {'PATH', 'LANG'}}
    environment.update(spec.get('environment', {}))
    environment.update(HOME=str(home), CLAUDE_CONFIG_DIR=str(home / '.claude'), TZ='UTC',
                       LIFEOS_DIR=str(home / '.claude/LIFEOS'), LIFEOS_CONFIG_DIR=str(home / '.claude'),
                       LIFEOS_HOOK_SETTINGS=str(home / '.claude/settings.json'), LIFEOS_NOTIFICATION_CHANNEL='discord',
                       TERMINAL_CWD=str(home / 'project'), HERMES_WRITE_SAFE_ROOT=str(home / 'project'),
                       ANTHROPIC_BASE_URL=endpoint, ANTHROPIC_AUTH_TOKEN='PAIR_LIFECYCLE',
                       ANTHROPIC_MODEL='lifecycle-fixture', CLAUDE_CODE_MAX_RETRIES='0',
                       CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1', DISABLE_TELEMETRY='1', DISABLE_ERROR_REPORTING='1')
    if case.startswith(('kitty-', 'context-')):
        environment.update(LIFEOS_NOTIFICATION_CHANNEL='discord' if case.endswith('-remote') else 'desktop',
                           TERM='xterm-kitty',
                           KITTY_LISTEN_ON='unix:' + str(home / 'no-kitty.sock'), KITTY_WINDOW_ID='777')
        if case.endswith('-subagent'):
            environment['CLAUDE_CODE_FORK_SUBAGENT'] = '1'
    if side == 'hermes':
        profile = home / '.hermes'
        profile.mkdir()
        (profile / 'plugins').symlink_to(spec['plugins_path'], target_is_directory=True)
        write_json(profile / 'config.yaml', {
            'model': {'provider': 'custom', 'base_url': endpoint + '/v1', 'api_key': 'PAIR_LIFECYCLE',
                      'default': 'lifecycle-fixture', 'api_mode': 'chat_completions'},
            **({'auxiliary': {'title_generation': {'model_upgrade_enabled': False}}}
               if case.startswith(RESPONSE_PREFIXES) else {}),
            'plugins': {'enabled': ['lifeos-hook-bridge']}})
        environment['HERMES_HOME'] = str(profile)
    if os.geteuid() == 0:
        for item in (home, *home.rglob('*')):
            if not item.is_symlink():
                os.chown(item, spec['uid'], spec['gid'])
        for parent in (home.parent, home.parent.parent):
            os.chown(parent, spec['uid'], spec['gid'])
    response = case.startswith(RESPONSE_PREFIXES)
    delivery = response or case.startswith('context-delivery-')
    command = [*spec['command'], 'Reply with READY.' if delivery else BLOCK_REASON]
    if case == 'response-cache-limit':
        command[-1] = ('Start with READY. Explain how to verify a reversible software installation in '
                       '24 numbered paragraphs. Each paragraph must contain three full sentences and '
                       'a distinct concrete example. Cover installation, configuration, dependencies, '
                       'permissions, service restart, interruption, backup, user data, and rollback. '
                       'Write every paragraph in full. Do not abbreviate or summarize the requested answer.')
    if spec.get('isolate_tmp'):
        command = ['bwrap', '--ro-bind', '/', '/', '--dev-bind', '/dev', '/dev', '--bind', str(home), str(home),
                   '--tmpfs', '/tmp', *command]
    before_requests = len(guard.observed)
    started = time.monotonic()
    execution = {'user': spec['uid'], 'group': spec['gid'], 'extra_groups': []} if os.geteuid() == 0 else {}
    with (home / 'cli.log').open('w') as log:
        process = subprocess.Popen(command, env=environment, cwd=home / 'project',
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True, **execution)
        try:
            exit_code = process.wait(timeout=120 if response else 60)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
            raise
    events = [json.loads(line) for line in (home / 'fixture-events.jsonl').read_text().splitlines()]
    starts = [row for row in events if row['hook_event_name'] == 'SessionStart']
    ends = [row for row in events if row['hook_event_name'] == 'SessionEnd']
    prompts = [row for row in events if row['hook_event_name'] == 'UserPromptSubmit']
    if (len(starts) != 1 or len(ends) != 1 or len(prompts) != 1 or
            len({row['session_id'] for row in events}) != 1):
        raise ValueError('A complete real lifecycle boundary was not observed')
    session_id = starts[0]['session_id']
    traces = [json.loads(line) for line in (home / 'hooks.jsonl').read_text().splitlines()]
    expected_ids = [row['id'] for row in definitions]
    if sorted(row['id'] for row in traces) != sorted(expected_ids):
        raise ValueError('The real lifecycle did not invoke each selected hook exactly once')
    requests = guard.observed[before_requests:]
    generation = [row for row in requests if row['path'] != '/api/show' or
                  set(row['body']) - {'name', 'model', 'verbose'}]
    after = state_snapshot(home, case, session_id, after=True)
    if delivery:
        if case.startswith('context-'):
            combined = json.dumps([row['body'] for row in generation])
            after['model_context_contains'] = {
                'relationship': 'PAIR_RELATIONSHIP_NOTE' in combined,
                'wisdom': 'PAIR_WISDOM_GUIDANCE' in combined,
                'advisory': 'PAIR_ADVISORY_FINDING' in combined,
                'low_confidence': 'PAIR_LOW_CONFIDENCE' in combined}
        if response:
            results = []
            for line in (home / 'cli.log').read_text().splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict) and row.get('type') == 'result':
                    results.append(row)
            user_response = (results[0].get('result', '') if side == 'native' else results[0].get('text', '')) if len(results) == 1 else ''
            after['user_response_delivered'] = bool(user_response) and 'READY' in user_response
            if case.startswith('response-cache-'):
                cache = home / '.claude/LIFEOS/MEMORY/STATE/last-response.txt'
                stop_message = json.loads(base64.b64decode(traces[0]['stdin_base64']))['last_assistant_message']
                after['cache_matches_stop_message'] = cache.is_file() and cache.read_text() == stop_message[:2000]
                after['stop_message_matches_user_response'] = stop_message.strip() == user_response.strip()
                if case == 'response-cache-limit':
                    after.update(user_response_exceeds_limit=len(stop_message) > 2000,
                                 cache_characters=len(cache.read_text()) if cache.is_file() else 0)
        private_requests = home / 'requests-private.json'
        descriptor = os.open(private_requests, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(json.dumps(requests, indent=2) + '\n')
        requests = [{'path': row['path'], 'body_sha256': row['body_sha256'],
                     'model': row['body'].get('model'),
                     **({key: row[key] for key in ('upstream_status', 'response_body_sha256', 'actual_model')
                         if key in row} if response else {}),
                     'body_keys': sorted(row['body'])} for row in requests]
    record = {'before': read_json(home / 'before-state.json'), 'after': after,
              'hook_exit_codes': [row['exit_code'] for row in traces],
              'event': traces[0]['event'], 'cli_exit_code': exit_code,
              'model_generation_requests': len(generation),
              'metadata_requests': len(requests) - len(generation)}
    if response:
        record['model_successful_responses'] = sum(row.get('upstream_status') == 200 for row in generation)
    write_json(home / 'after-state.json', after)
    write_json(home / 'fixture-files-after.json', fixture_files(home))
    write_json(home / 'result.json', {**record, 'session_id': session_id,
               'seconds': round(time.monotonic() - started, 3),
               'command': command, 'hook_definitions': definitions, 'requests': requests,
               'source': starts[0].get('source'), 'reason': ends[0].get('reason'),
               'raw_artifacts': {name: digest(home / name) for name in
                                 ('hooks.jsonl', 'fixture-events.jsonl', 'cli.log', 'before-state.json', 'after-state.json',
                                  'fixture-files-before.json', 'fixture-files-after.json')}})
    return record


def run_controls(config: dict, output: Path, cases: list[str]) -> int:
    output.mkdir(parents=True)
    if any(case.startswith(RESPONSE_PREFIXES) for case in cases):
        if any(not case.startswith(RESPONSE_PREFIXES) for case in cases):
            raise ValueError('Response controls run separately from blocked and refused controls')
        if __package__:
            from .paired_response_server import response_handler
        else:
            from paired_response_server import response_handler
        handler = response_handler(config['model_environment'])
    else:
        handler = RequestGuard
    guard = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    guard.observed = []
    thread = threading.Thread(target=guard.serve_forever, daemon=True)
    thread.start()
    endpoint = f'http://127.0.0.1:{guard.server_port}'
    records = []
    try:
        for case in cases:
            paired = {'id': case, 'registrations': [identifier for identifier, _ in CASES[case]]}
            for side in ('native', 'hermes'):
                paired[side] = run_side(side, config[side], case, output, endpoint, guard)
            paired['errors'] = check_pair(paired)
            records.append(paired)
            write_json(output / 'paired-results.json', {'cases': records})
            print(json.dumps({'case': case, 'errors': paired['errors']}), flush=True)
    finally:
        guard.shutdown()
        guard.server_close()
        thread.join(timeout=10)
    return 1 if any(row['errors'] for row in records) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Compare selected real native lifecycle effects')
    sub = parser.add_subparsers(dest='action', required=True)
    fixture = sub.add_parser('fixture-event')
    fixture.add_argument('case', choices=CASES)
    run = sub.add_parser('run')
    run.add_argument('configuration', type=Path)
    run.add_argument('output', type=Path)
    run.add_argument('--case', choices=CASES, action='append')
    check = sub.add_parser('check')
    check.add_argument('results', type=Path)
    args = parser.parse_args()
    if args.action == 'fixture-event':
        fixture_event(args.case)
        return 0
    if args.action == 'check':
        errors = [error for case in read_json(args.results)['cases'] for error in check_pair(case)]
        for error in errors:
            print(error)
        return 1 if errors else 0
    cases = args.case or [case for case in CASES if not case.startswith(RESPONSE_PREFIXES)]
    return run_controls(read_json(args.configuration), args.output, cases)


if __name__ == '__main__':
    raise SystemExit(main())
