# ABOUTME: Measures real detached configuration evaluations after actual file operations.
# ABOUTME: Preserves runner results and separates completed evaluations from skipped branches.
import base64
import json
import os
from pathlib import Path
import shlex
import time


EVALUATION_CASES = {
    'evaluation-write-pass': ('Write', 'pair.hook.ts', 'pass'),
    'evaluation-edit-pass': ('Edit', 'pair.hook.ts', 'pass'),
    'evaluation-write-fail': ('Write', 'pair.hook.ts', 'fail'),
    'evaluation-write-debounce': ('Write', 'pair.hook.ts', 'debounce'),
    'evaluation-write-no-runner': ('Write', 'pair.hook.ts', 'no-runner'),
    'evaluation-write-nonsentinel': ('Write', 'notes.md', 'nonsentinel'),
    'evaluation-write-claude': ('Write', 'CLAUDE.md', 'pass'),
}
STATE = 'LIFEOS/MEMORY/OBSERVABILITY/config-eval-state.json'
LOG = 'LIFEOS/MEMORY/OBSERVABILITY/config-eval-fires.jsonl'
RESULTS = 'LIFEOS/MEMORY/STATE/Evals-Results'
CONTENT = 'PAIR_FILE_CONTENT'
TRIAL_OUTPUT = 'PAIR_EVAL_READY'
SUITE = 'paired-config-fixture'


def read_json(path):
    return json.loads(path.read_text()) if path.is_file() else None


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def expected_evaluation(case):
    tool, _, branch = EVALUATION_CASES[case]
    run = branch in ('pass', 'fail')
    before = {'target_present': tool == 'Edit', 'prior_fire_present': branch == 'debounce'}
    after = {'target_matches': True, 'input_matches': True, 'tool_names': [tool],
             'runner_lock_absent': True, 'fire_state_matches': True,
             'run_events': int(run), 'passed': branch == 'pass' if run else None,
             'trial_output_matches': True if run else None,
             'published_result_matches': True if run else None, 'user_response_delivered': True}
    return before, after


def check_evaluation(case, before, after):
    expected_before, expected_after = expected_evaluation(case)
    return [] if (before, after) == (expected_before, expected_after) else [f'{case}: real evaluation effect is missing']


def seed_evaluation(home, source, case):
    root = home / '.claude'
    (root / 'LIFEOS').mkdir(parents=True, exist_ok=True)
    _, _, branch = EVALUATION_CASES[case]
    if branch != 'no-runner':
        (root / 'LIFEOS/TOOLS').symlink_to(source / 'LIFEOS/TOOLS', target_is_directory=True)
    custom = root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/Evals'
    write_json(custom / 'config.json', {'config_change_suite': SUITE})
    (custom / 'Suites').mkdir()
    expected = TRIAL_OUTPUT if branch != 'fail' else 'PAIR_IMPOSSIBLE_EXPECTATION'
    # JSON is a valid YAML document and uses the real installed suite parser.
    write_json(custom / f'Suites/{SUITE}.yaml', {
        'name': SUITE, 'type': 'regression', 'trials': 1, 'pass_threshold': 1,
        'agent_level': 'medium', 'judge_level': 'medium',
        'system_prompt': 'Reply with exactly ' + TRIAL_OUTPUT + '.',
        'cases': [{'id': 'marker', 'prompt': 'Reply with exactly ' + TRIAL_OUTPUT + '.',
                   'assert': [{'type': 'equals', 'value': expected}]}]})
    if branch == 'debounce':
        write_json(root / STATE, {'last_fire': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})


def configure_evaluation(home, side, spec, endpoint, environment):
    private = home / '.config/lifeos-reference/model.env'
    private.parent.mkdir(parents=True)
    private.write_text('export ANTHROPIC_BASE_URL=' + shlex.quote(endpoint) + '\n'
                       'export ANTHROPIC_AUTH_TOKEN=PAIR_EVAL\n'
                       'export ANTHROPIC_MODEL=lifecycle-fixture\n')
    private.chmod(0o600)
    folder = home / '.local/bin'
    folder.mkdir(parents=True)
    if side == 'native':
        (folder / 'native-claude').symlink_to(spec['command'][0])
        adapter = ('#!/usr/bin/env python3\n'
                   '# ABOUTME: Restores the isolated private relay for native child inference.\n'
                   '# ABOUTME: Uses the pinned native CLI and selected local medium effort.\n'
                   'import os,sys\n'
                   f'os.environ.update(ANTHROPIC_BASE_URL={endpoint!r}, ANTHROPIC_AUTH_TOKEN="PAIR_EVAL",'
                   ' ANTHROPIC_MODEL="lifecycle-fixture", CLAUDE_CODE_EFFORT_LEVEL="medium")\n'
                   'args=sys.argv[1:]\n'
                   'for flag,value in [("--model","lifecycle-fixture"),("--effort","medium")]:\n'
                   ' if flag in args: args[args.index(flag)+1]=value\n'
                   f'os.execv({str(folder / "native-claude")!r},["claude",*args])\n')
        (folder / 'claude').write_text(adapter)
        (folder / 'claude').chmod(0o755)
    else:
        shim = Path(spec['plugins_path']) / 'lifeos-hook-bridge/bin/claude'
        (folder / 'claude').symlink_to(shim)
        environment.update(LIFEOS_HOOK_MODEL_ENV=str(private), LIFEOS_CHILD_INFERENCE_DIRECT='1',
                           LIFEOS_MODEL_TIER_MAP=json.dumps({'sonnet': {'model': 'lifecycle-fixture', 'effort': 'medium'}}))
    environment['PATH'] = str(folder) + ':' + environment['PATH']
    # Every generated child entry point is owned by the same fixture identity.
    if os.geteuid() == 0:
        for parent in (home / '.config', private.parent, private, home / '.local', folder, *folder.iterdir()):
            if not parent.is_symlink():
                os.chown(parent, spec['uid'], spec['gid'])


def wait_evaluation(home, case):
    if EVALUATION_CASES[case][2] not in ('pass', 'fail'):
        return
    deadline = time.monotonic() + 115
    root = home / '.claude'
    while time.monotonic() < deadline:
        log = root / LOG
        if log.is_file() and not (root / RESULTS / '.config-eval.lock').exists():
            rows = [json.loads(line) for line in log.read_text().splitlines()]
            if any(row.get('event') in ('run', 'error') for row in rows):
                return
        time.sleep(0.2)
    raise ValueError('The actual detached evaluation did not finish')


def evaluation_snapshot(home, case, after=False):
    tool, name, branch = EVALUATION_CASES[case]
    root = home / '.claude'
    target = home / 'project' / name
    state = read_json(root / STATE)
    if not after:
        return {'target_present': target.is_file(), 'prior_fire_present': state is not None}
    rows = [json.loads(line) for line in (root / LOG).read_text().splitlines()] if (root / LOG).is_file() else []
    runs = [row for row in rows if row.get('event') == 'run']
    latest = read_json(root / RESULTS / SUITE / 'latest.json')
    detail = read_json(root / RESULTS / SUITE / latest['run_id'] / 'run.json') if latest else None
    trials = detail.get('detail', [{}])[0].get('trials', []) if detail else []
    before_state = read_json(home / 'fixture-files-before.json').get(STATE)
    preserved = not state if branch in ('no-runner', 'nonsentinel') else bool(state)
    if branch == 'debounce':
        before = json.loads(base64.b64decode(before_state['content_base64']))
        preserved = state == before
    traces = [json.loads(line) for line in (home / 'hooks.jsonl').read_text().splitlines()]
    inputs = [json.loads(base64.b64decode(row['stdin_base64'])) for row in traces]
    expected = CONTENT if tool == 'Write' else 'First fixture line\nPAIR_NEW_LINE\nLast fixture line'
    key, value = ('content', CONTENT) if tool == 'Write' else ('new_string', 'PAIR_NEW_LINE')
    return {'target_matches': target.is_file() and target.read_text().rstrip('\n') == expected,
            'input_matches': all(row.get('tool_input', {}).get(key, '').rstrip('\n') == value for row in inputs),
            'tool_names': sorted({row.get('tool_name') for row in inputs}),
            'runner_lock_absent': not (root / RESULTS / '.config-eval.lock').exists(),
            'fire_state_matches': preserved, 'run_events': len(runs),
            'passed': runs[0].get('passed') if len(runs) == 1 else None,
            'trial_output_matches': len(trials) == 1 and trials[0].get('output') == TRIAL_OUTPUT if runs else None,
            'published_result_matches': (bool(latest) and latest.get('passed') == runs[0].get('passed')
                                         and latest.get('score') == runs[0].get('score')) if runs else None}
