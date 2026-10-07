# ABOUTME: Recomputes selected paired after-states from raw per-client captures without the driver code.
# ABOUTME: Compares each recomputed value with the after-state recorded in result.json and the ledger.
import base64
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/pr3full')
V = ROOT / 'docs/verification'
LEDGER = json.loads((ROOT / 'docs/parity/handler-effects.json').read_text())


def lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def files(path):
    return {k: base64.b64decode(v['content_base64']).decode() for k, v in json.loads(Path(path).read_text()).items()}


def ledger_case(case_id):
    out = []
    for row in LEDGER['registrations']:
        for case in row.get('paired_cases', []):
            if case['id'] == case_id:
                out.append((row['id'], case))
    return out


def client(unit, side, case):
    d = V / unit / side / case
    return d, json.loads((d / 'result.json').read_text())


def user_response(d, side):
    rows = []
    for text in (d / 'cli.log').read_text().splitlines():
        try:
            row = json.loads(text)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get('type') == 'result':
            rows.append(row)
    assert len(rows) == 1, (d, len(rows))
    return rows[0].get('result' if side == 'native' else 'text', '')


report = []


def check(case, side, label, mine, recorded):
    ok = mine == recorded
    report.append({'case': case, 'side': side, 'field': label, 'recomputed': mine, 'recorded': recorded, 'match': ok})


# 1. feedback-low-rating: rating row and learning file from the raw after-file snapshot.
for side in ('native', 'hermes'):
    d, r = client('2026-10-05-paired-feedback', side, 'feedback-low-rating')
    after = files(d / 'fixture-files-after.json')
    ratings = [json.loads(x) for x in after['LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'].splitlines()]
    new = ratings[1:]
    mine = [{'rating': x['rating'], 'source': x['source'], 'comment': x.get('comment'),
             'session_matches': x['session_id'] == r['session_id']} for x in new]
    rec = [{'rating': x['rating'], 'source': x['source'], 'comment': x.get('comment'),
            'session_matches': x['session_matches']} for x in r['after']['captured_ratings']]
    check('feedback-low-rating', side, 'captured_ratings(core)', mine, rec)
    learn = [k for k in after if '_LEARNING_' in k]
    check('feedback-low-rating', side, 'learning_count', len(learn), r['after']['learning_count'])
    body = after[learn[0]]
    check('feedback-low-rating', side, 'learning feedback line',
          '**Feedback:** needs clearer details' in body, r['after']['learning_checks']['feedback_matches'])
    check('feedback-low-rating', side, 'learning principal line',
          'rated 4/10 by FixtureOwner.' in body, r['after']['learning_checks']['principal_matches'])

# 2. format-contract-violations: persisted state and emitted context.
for side in ('native', 'hermes'):
    d, r = client('2026-10-05-paired-format-contract', side, 'format-contract-violations')
    after = files(d / 'fixture-files-after.json')
    state = json.loads(after['LIFEOS/MEMORY/STATE/drift-reminder.json'])
    hook = lines(d / 'hooks.jsonl')
    context = json.loads(hook[0]['stdout'])['hookSpecificOutput']['additionalContext']
    check('format-contract-violations', side, 'state', state, r['after']['state'])
    check('format-contract-violations', side, 'hook_context', context, r['after']['hook_context'])
    check('format-contract-violations', side, 'state.last_text == emitted', state['last_text'] == context, True)
    # Independent count of the seeded broken response lines.
    seeded = after['LIFEOS/MEMORY/STATE/last-response.txt']
    check('format-contract-violations', side, 'seeded line count reported',
          f'{len(seeded.splitlines())} lines (cap 15)' in context, True)

# 3. time-context-sync-toronto: parse the clock, recompute weekday, zone, day period, interval.
for side in ('native', 'hermes'):
    d, r = client('2026-10-05-paired-time-context', side, 'time-context-sync-toronto')
    out = lines(d / 'hooks.jsonl')[0]['stdout']
    m = re.search(r'Current time: (\w{3}) (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) (\w+) \((.+?)\)', out)
    bounds = json.loads((d / 'clock-bounds.json').read_text())
    lo = datetime.fromisoformat(bounds['started_at']).astimezone(ZoneInfo('America/Toronto'))
    hi = datetime.fromisoformat(bounds['finished_at']).astimezone(ZoneInfo('America/Toronto'))
    shown = datetime.strptime(m[2], '%Y-%m-%d %H:%M').replace(tzinfo=ZoneInfo('America/Toronto'))
    in_window = lo.replace(second=0, microsecond=0) <= shown <= hi
    weekday_ok = m[1] == shown.strftime('%a')
    zone_ok = m[3] == shown.tzname()
    h = shown.hour
    period = ('late night' if h < 5 or h >= 21 else 'early morning' if h < 9 else 'morning' if h < 12
              else 'afternoon' if h < 17 else 'evening')
    check('time-context-sync-toronto', side, 'clock_is_current', in_window, r['after']['clock_is_current'])
    check('time-context-sync-toronto', side, 'clock_valid', weekday_ok and zone_ok and m[4] == period,
          r['after']['clock_valid'])
    report.append({'case': 'time-context-sync-toronto', 'side': side, 'field': 'raw clock line',
                   'recomputed': m[0], 'recorded': f"interval {lo:%H:%M:%S}-{hi:%H:%M:%S} {lo.tzname()}", 'match': None})

# 4. response-cache-limit: cache equals first 2000 chars of the Stop message, which equals the user response.
for side in ('native', 'hermes'):
    d, r = client('2026-10-05-paired-response-cache', side, 'response-cache-limit')
    after = files(d / 'fixture-files-after.json')
    cache = after['LIFEOS/MEMORY/STATE/last-response.txt']
    stop = json.loads(base64.b64decode(lines(d / 'hooks.jsonl')[0]['stdin_base64']))['last_assistant_message']
    resp = user_response(d, side)
    check('response-cache-limit', side, 'cache_matches_stop_message', cache == stop[:2000],
          r['after']['cache_matches_stop_message'])
    check('response-cache-limit', side, 'stop_message_matches_user_response', stop.strip() == resp.strip(),
          r['after']['stop_message_matches_user_response'])
    check('response-cache-limit', side, 'cache_characters', len(cache), r['after']['cache_characters'])
    report.append({'case': 'response-cache-limit', 'side': side, 'field': 'stop message length',
                   'recomputed': len(stop), 'recorded': None, 'match': None})

# 5. version-drift-aged: nag state and exact warning line.
for side in ('native', 'hermes'):
    d, r = client('2026-10-05-paired-version-drift', side, 'version-drift-aged')
    after = files(d / 'fixture-files-after.json')
    state = json.loads(after['LIFEOS/MEMORY/STATE/version-drift-nag.json'])
    out = lines(d / 'hooks.jsonl')[0]['stdout']
    ctx = json.loads(out)['hookSpecificOutput']['additionalContext']
    check('version-drift-aged', side, 'state.count/tag', {k: state[k] for k in ('count', 'tag')},
          {k: r['after']['state'][k] for k in ('count', 'tag')})
    check('version-drift-aged', side, 'warning mentions 1 file and 72h',
          '1 core file(s) ahead of v1.0.0 (tag 72h old)' in ctx, True)
    check('version-drift-aged', side, 'hook_context', ctx, r['after']['hook_context'])

# 6. tool-log-repeat: loop state and alert positions from raw hook output.
for side in ('native', 'hermes'):
    d, r = client('2026-10-05-paired-tool-log', side, 'tool-log-repeat')
    after = files(d / 'fixture-files-after.json')
    key = 'LIFEOS/MEMORY/STATE/loop-detector/' + r['session_id'] + '.json'
    state = json.loads(after[key])
    hooks = lines(d / 'hooks.jsonl')
    alert = "[LOOP DETECTED] You've called Bash 3 times"
    positions = [i for i, h in enumerate(hooks, 1) if alert in h['stdout']]
    check('tool-log-repeat', side, 'seq', state['seq'], 3)
    check('tool-log-repeat', side, 'alert positions', positions, r['after']['alert_positions']['PostToolUse.12.2'])
    check('tool-log-repeat', side, 'lastAlert', state['lastAlert'], r['after']['loop']['last_alert'])

# 7. atlas-bash-multiple: appended Atlas rows.
for side in ('native', 'hermes'):
    d, r = client('2026-10-05-paired-atlas-hints', side, 'atlas-bash-multiple')
    rows = lines(d / 'atlas-events.jsonl')
    check('atlas-bash-multiple', side, 'hint sources in order', [x['source'] for x in rows[1:]],
          [x['source'] for x in r['after']['hints']])
    bounds = json.loads((d / 'clock-bounds.json').read_text())
    lo = datetime.fromisoformat(bounds['started_at']).replace(microsecond=0)
    hi = datetime.fromisoformat(bounds['finished_at'])
    check('atlas-bash-multiple', side, 'timestamps in interval',
          all(lo <= datetime.fromisoformat(x['ts'].replace('Z', '+00:00')) <= hi for x in rows[1:]),
          all(x['timestamp_current'] for x in r['after']['hints']))

# 8. guard-bash-plutil-block: exit code and message.
for side in ('native', 'hermes'):
    d, r = client('2026-10-05-paired-pre-tool-guard', side, 'guard-bash-plutil-block')
    hooks = lines(d / 'hooks.jsonl')
    check('guard-bash-plutil-block', side, 'hook exit codes', [h['exit_code'] for h in hooks], r['hook_exit_codes'])
    check('guard-bash-plutil-block', side, 'block message',
          hooks[0]['stderr'].startswith('[PreToolGuard] blocked `plutil -extract` without -o'),
          r['after']['block_message_emitted'])

# 9. isa-render-first-authoring: log row and cleared state.
for side in ('native', 'hermes'):
    d, r = client('2026-10-05-paired-isa-render', side, 'isa-render-first-authoring')
    before, after = files(d / 'fixture-files-before.json'), files(d / 'fixture-files-after.json')
    log = [json.loads(x) for x in after['LIFEOS/MEMORY/OBSERVABILITY/isa-render.jsonl'].splitlines()]
    skipped = [re.sub(r'^.*/LIFEOS/MEMORY/WORK/', '', s) for s in log[0]['skipped']]
    check('isa-render-first-authoring', side, 'skipped', skipped, r['after']['log'][0]['skipped'])
    removed = [k for k in before if k not in after]
    check('isa-render-first-authoring', side, 'state removed',
          any('isa-render-debounce' in k for k in removed), not r['after']['state_present'])

# 10. file-hint-edit-gear: target content and hints.
for side in ('native', 'hermes'):
    d, r = client('2026-10-05-paired-file-hints', side, 'file-hint-edit-gear')
    target = (d / 'target-GEAR.md').read_text()
    check('file-hint-edit-gear', side, 'target content', target,
          'First fixture line\nPAIR_NEW_LINE\nLast fixture line\n')
    rows = lines(d / 'atlas-events.jsonl')
    check('file-hint-edit-gear', side, 'hints', [(x['source'], x['tool']) for x in rows[1:]], [('gear', 'Edit')])

# Ledger equality with result.json for every recomputed case.
for case_id in sorted({x['case'] for x in report}):
    for reg, lc in ledger_case(case_id):
        for side in ('native', 'hermes'):
            unit = lc['result_artifact'].split('/')[2]
            _, r = client(unit, side, case_id)
            check(case_id, side, f'ledger[{reg}].after == result.json.after', lc[side]['after'], r['after'])

bad = [x for x in report if x['match'] is False]
print(json.dumps({'checks': sum(x['match'] is not None for x in report), 'mismatches': bad}, indent=1, default=str))
print('\n'.join(f"{x['case']:<28} {x['side']:<6} {x['field']}: {x['recomputed'] if x['match'] is None else x['match']}"
                for x in report if x['match'] is None))
