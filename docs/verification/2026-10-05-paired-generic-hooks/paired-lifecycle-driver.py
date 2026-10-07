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
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from zoneinfo import ZoneInfo


# Cases that compare every LifeOS file change and every hook output between the clients.
# Each entry: registration, hook program, user prompt.
GENERIC_CASES = {
    'generic-reminder-router': ('UserPromptSubmit.3.1', 'hooks/ReminderRouter.hook.ts', 'remind me to water the plants tomorrow'),
    'generic-memory-turn': ('UserPromptSubmit.5.1', 'hooks/MemoryTurnStart.hook.ts', 'Reply with READY.'),
    'generic-algorithm-nudge': ('UserPromptSubmit.7.1', 'hooks/AlgorithmNudge.hook.ts', 'Reply with READY.'),
    'generic-model-rung': ('UserPromptSubmit.9.1', 'hooks/ModelRungGuard.hook.ts', 'Reply with READY.'),
    'generic-prompt-processing': ('UserPromptSubmit.1.1', 'hooks/PromptProcessing.hook.ts', 'Reply with READY.'),
    'generic-tab-state': ('Stop.1.2', 'hooks/TabState.hook.ts', 'Reply with READY.'),
    'generic-voice-completion': ('Stop.1.3', 'hooks/VoiceCompletion.hook.ts', 'Reply with READY.'),
    'generic-spend-auditor': ('Stop.1.5', 'hooks/SpendAuditor.hook.ts', 'Reply with READY.'),
    'generic-stop-gates': ('Stop.1.6', 'hooks/StopGates.hook.ts', 'Reply with READY.'),
    'generic-memory-review': ('Stop.1.7', 'hooks/MemoryReviewFire.hook.ts', 'Reply with READY.'),
    'generic-stop-health': ('Stop.2.1', 'hooks/MemoryHealthGate.hook.ts', 'Reply with READY.'),
    'generic-integrity-check': ('SessionEnd.1.6', 'hooks/IntegrityCheck.hook.ts', 'Reply with READY.'),
}
# Measured effects that both clients must produce: changed LifeOS files, whether each hook printed output,
# and whether each printed context reached the model request.
STATE = '.claude/LIFEOS/MEMORY/STATE/'
OBSERVED = '.claude/LIFEOS/MEMORY/OBSERVABILITY/'
GENERIC_EXPECTED = {
    'generic-reminder-router': ([], [False], []),
    'generic-memory-turn': ([STATE + 'delta-surface-heartbeat', STATE + 'memory-inject/<session>.json'], [True], [True]),
    'generic-algorithm-nudge': ([STATE + 'isa-nudge/<session>.json', STATE + 'skill-usewhen-index.json'], [False], []),
    'generic-model-rung': ([OBSERVED + 'model-rung.jsonl'], [False], []),
    'generic-prompt-processing': ([STATE + 'work-events.jsonl', STATE + 'work.json'], [False], []),
    'generic-tab-state': ([], [False], []),
    'generic-voice-completion': (['.claude/LIFEOS/MEMORY/VOICE/voice-events.jsonl'], [False], []),
    'generic-spend-auditor': ([OBSERVED + 'spend-audit.jsonl', STATE + 'spend-audit-state.json'], [False], []),
    'generic-stop-gates': ([OBSERVED + 'format-gate.jsonl', OBSERVED + 'verification-gate.jsonl',
                            OBSERVED + 'writing-gate.jsonl'], [False], []),
    'generic-memory-review': ([OBSERVED + 'review-state.json', STATE + 'memory-review/<session>.json'], [False], []),
    'generic-stop-health': ([], [False], []),
    'generic-integrity-check': ([], [False], []),
}
# Differences that a plugin patch makes on purpose. Both sides are normalized the same way, and the unit
# record names the patch. The model rung patch adds the reasoning effort to the rung log.
ACCEPTED_DIFFERENCES = {'generic-model-rung': [(r',"reasoning_effort":"[^"]*"', '')]}
PINNED_SETTINGS = {'UserPromptSubmit.1.1': (True, 30), 'UserPromptSubmit.3.1': (True, 5),
                   'UserPromptSubmit.9.1': (True, 5), 'UserPromptSubmit.5.1': (False, 8)}
# Claude Code in print mode exits before an asynchronous Stop hook finishes and then emits no SessionEnd.
# The Stop health case therefore runs the hook synchronously; its pinned setting is asynchronous with timeout 15.


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
    'feedback-rating': [('UserPromptSubmit.2.1', 'hooks/SatisfactionCapture.hook.ts')],
    'feedback-bare-rating': [('UserPromptSubmit.2.1', 'hooks/SatisfactionCapture.hook.ts')],
    'feedback-praise': [('UserPromptSubmit.2.1', 'hooks/SatisfactionCapture.hook.ts')],
    'feedback-neutral': [('UserPromptSubmit.2.1', 'hooks/SatisfactionCapture.hook.ts')],
    'feedback-low-rating': [('UserPromptSubmit.2.1', 'hooks/SatisfactionCapture.hook.ts')],
    'feedback-async-rating': [('UserPromptSubmit.2.1', 'hooks/SatisfactionCapture.hook.ts')],
    'feedback-async-bare-rating': [('UserPromptSubmit.2.1', 'hooks/SatisfactionCapture.hook.ts')],
    'feedback-async-praise': [('UserPromptSubmit.2.1', 'hooks/SatisfactionCapture.hook.ts')],
    'feedback-async-neutral': [('UserPromptSubmit.2.1', 'hooks/SatisfactionCapture.hook.ts')],
    'feedback-async-low-rating': [('UserPromptSubmit.2.1', 'hooks/SatisfactionCapture.hook.ts')],
    'format-contract-empty': [('UserPromptSubmit.6.1', 'hooks/DriftReminder.hook.ts')],
    'format-contract-clean': [('UserPromptSubmit.6.1', 'hooks/DriftReminder.hook.ts')],
    'format-contract-violations': [('UserPromptSubmit.6.1', 'hooks/DriftReminder.hook.ts')],
    'format-contract-depth': [('UserPromptSubmit.6.1', 'hooks/DriftReminder.hook.ts')],
    'format-contract-stale': [('UserPromptSubmit.6.1', 'hooks/DriftReminder.hook.ts')],
    'time-context-sync-utc': [('UserPromptSubmit.8.1', 'hooks/TimeContext.hook.ts')],
    'time-context-sync-toronto': [('UserPromptSubmit.8.1', 'hooks/TimeContext.hook.ts')],
    'time-context-async-utc': [('UserPromptSubmit.8.1', 'hooks/TimeContext.hook.ts')],
    'time-context-invalid-zone': [('UserPromptSubmit.8.1', 'hooks/TimeContext.hook.ts')],
    **{name: [('UserPromptSubmit.4.1', 'hooks/VersionDrift.hook.ts')] for name in (
        'version-drift-count', 'version-drift-aged', 'version-drift-below', 'version-drift-bump',
        'version-drift-recent', 'version-drift-untagged', 'version-drift-async-count')},
    **{name: [('Stop.1.4', 'hooks/ISARenderOnStop.hook.ts')] for name in (
        'isa-render-absent', 'isa-render-first-authoring', 'isa-render-missing', 'isa-render-complete',
        'isa-render-resumed', 'isa-render-existing-page')},
    **{name: [('PostToolUse.13.1', 'hooks/AtlasEventCapture.hook.ts')] for name in (
        'atlas-bash-systemd', 'atlas-bash-plain', 'atlas-bash-multiple')},
    **{name: [('PreToolUse.5.1', 'hooks/PreToolGuard.hook.ts')] for name in (
        'guard-bash-plutil-block', 'guard-bash-plutil-safe', 'guard-bash-plain')},
    'tool-log-success': [('PostToolUse.11.1', 'hooks/EventLogger.hook.ts'),
                         ('PostToolUse.12.2', 'hooks/LoopDetector.hook.ts')],
    'tool-log-repeat': [('PostToolUse.12.2', 'hooks/LoopDetector.hook.ts')],
    'tool-log-failure': [('PostToolUseFailure.1.1', 'hooks/EventLogger.hook.ts'),
                         ('PostToolUseFailure.3.1', 'hooks/LoopDetector.hook.ts')],
    **{name: [('PostToolUse.8.5', 'hooks/AtlasEventCapture.hook.ts'), ('PostToolUse.8.4', 'hooks/ConfigEvalFire.hook.ts')]
       for name in ('file-hint-write-projects', 'file-hint-write-plain', 'file-hint-sentinel-debounced',
                   'file-hint-sentinel-no-runner')},
    'file-hint-edit-gear': [('PostToolUse.9.5', 'hooks/AtlasEventCapture.hook.ts'),
                            ('PostToolUse.9.4', 'hooks/ConfigEvalFire.hook.ts')],
    **{name: [('PostToolUse.8.6', 'hooks/KnowledgeWriteGuard.hook.ts')]
       for name in ('knowledge-off-schema', 'knowledge-index-file')},
    **{name: [(f'PostToolUse.{group}.{index}', 'hooks/' + hook + '.hook.ts') for index, hook in enumerate((
        'ISASync', 'ISAStaleWriteGuard', 'CheckpointPerISC', 'ConfigEvalFire', 'AtlasEventCapture',
        'KnowledgeWriteGuard', 'ComplexityRatchet'), 1)] for name, group in (('isa-edit-close', 9), ('isa-write-create', 8))},
    'isa-read-view': [('PostToolUse.7.1', 'hooks/ISAStaleWriteGuard.hook.ts')],
    **{name: [(identifier, relative)] for name, (identifier, relative, _) in GENERIC_CASES.items()},
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
RESPONSE_PREFIXES = ('context-response-', 'response-cache-', 'feedback-', 'format-contract-', 'time-context-',
                     'version-drift-', 'isa-render-', 'atlas-bash-', 'guard-bash-', 'tool-log-', 'file-hint-', 'knowledge-', 'isa-edit-', 'isa-write-', 'isa-read-', 'generic-')
FEEDBACK_PROMPTS = {'feedback-rating': '8 great result', 'feedback-bare-rating': '10',
                    'feedback-praise': 'great job', 'feedback-neutral': '2 of the files were inspected',
                    'feedback-low-rating': '4 needs clearer details'}
FEEDBACK_PROMPTS.update({name.replace('feedback-', 'feedback-async-', 1): prompt
                        for name, prompt in list(FEEDBACK_PROMPTS.items())})
FEEDBACK_RESPONSE = 'PAIR_FEEDBACK_RESPONSE\n' + 'Synthetic prior response context. ' * 24
PRIOR_RATING = {'timestamp': '2026-10-01T00:00:00Z', 'rating': 6,
                'session_id': 'unrelated-session', 'source': 'explicit', 'comment': 'Keep existing rating'}
PRIOR_FORMAT_STATE = {'last_fired_turn': 6, 'turn_count': 6,
                      'last_text': 'PAIR_PRIOR_CONTRACT', 'schema_version': 1}
CLEAN_FORMAT_RESPONSE = '════ LifeOS ════\nFixture response.\n🗣️ Done.'
BROKEN_FORMAT_RESPONSE = 'delve ' + chr(0x2014) * 3 + '\n' + ''.join(f'Line {index}.\n' for index in range(16))


def format_cache(case: str) -> str | None:
    if case == 'format-contract-empty':
        return None
    return CLEAN_FORMAT_RESPONSE if case == 'format-contract-clean' else BROKEN_FORMAT_RESPONSE


def expected_format_contract(case: str) -> str:
    budget = 'depth requested, line cap lifted' if case == 'format-contract-depth' else 'max 15 prose lines'
    previous = ''
    if case == 'format-contract-clean':
        previous = ' Last response was clean (3 lines).'
    if case in {'format-contract-depth', 'format-contract-violations'}:
        previous = " Last response broke: no banner, no closer, 3 em-dashes, banned word 'delve'"
        previous += ', 17 lines (cap 15).' if case == 'format-contract-violations' else '.'
    return ('FORMAT CONTRACT (check before writing, not after): ' + budget +
            '; banner first, 🗣️ closer last, max 2 em-dashes.' + previous)


def expected_feedback(case: str) -> dict:
    case = case.replace('feedback-async-', 'feedback-', 1)
    result = {'unrelated_rating_preserved': True, 'cache_preserved': True,
              'captured_ratings': [], 'learning_count': int(case == 'feedback-low-rating'),
              'user_response_delivered': True}
    if case != 'feedback-neutral':
        rating = {'rating': {'feedback-rating': 8, 'feedback-bare-rating': 10,
                            'feedback-praise': 8, 'feedback-low-rating': 4}[case],
                  'source': 'implicit' if case == 'feedback-praise' else 'explicit',
                  'timestamp_valid': True, 'session_matches': True, 'response_preview_matches_cache': True}
        if case in {'feedback-rating', 'feedback-low-rating'}:
            rating['comment'] = FEEDBACK_PROMPTS[case].split(' ', 1)[1]
        if case == 'feedback-praise':
            rating.update(sentiment_summary='Direct praise: "great job"', confidence=0.95)
        result['captured_ratings'] = [rating]
    if case == 'feedback-low-rating':
        result['learning_checks'] = {key: True for key in (
            'rating_matches', 'source_matches', 'feedback_matches', 'context_matches', 'principal_matches')}
    return result


DRIFT_TAG = 'v1.0.0'
DRIFT_STATE = 'LIFEOS/MEMORY/STATE/version-drift-nag.json'
PRIOR_DRIFT_NAG = {'count': 3, 'tag': 'v0.9.0'}


def drift_before(case: str) -> dict:
    single = case in {'version-drift-aged', 'version-drift-below'}
    return {'changed_core_files': 1 if single else 10,
            'tag': None if case == 'version-drift-untagged' else DRIFT_TAG,
            'tag_age_hours': 72 if case == 'version-drift-aged' else 0,
            'version': '1.0.1' if case == 'version-drift-bump' else '1.0.0',
            'prior_nag_present': case == 'version-drift-recent',
            'asynchronous': case == 'version-drift-async-count'}


def drift_after(case: str) -> dict:
    before = drift_before(case)
    nag = case in {'version-drift-count', 'version-drift-aged', 'version-drift-async-count'}
    line = state = None
    if nag:
        age = f" (tag {before['tag_age_hours']}h old)" if before['tag_age_hours'] else ''
        line = (f"⏫ VERSION-DRIFT: {before['changed_core_files']} core file(s) ahead of {DRIFT_TAG}{age}, "
                f'no bump in flight {chr(0x2014)} run the VersionBump workflow (/vb: classify → bump → ship) '
                'before this ages further, or defer explicitly to the principal.')
        state = {'count': before['changed_core_files'], 'tag': DRIFT_TAG, 'timestamp_current': True}
    if before['prior_nag_present']:
        state = {**PRIOR_DRIFT_NAG, 'timestamp_current': False}
    return {'hook_context': line, 'state': state, 'worktree_preserved': True,
            'model_nag_present': nag and not before['asynchronous'], 'user_response_delivered': True}


def git(root: Path, *arguments: str, when: datetime | None = None) -> str:
    environment = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(root),
                   'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1'}
    if when:
        environment.update(GIT_AUTHOR_DATE=when.isoformat(), GIT_COMMITTER_DATE=when.isoformat())
    return subprocess.run(
        ['git', '-C', str(root), '-c', 'safe.directory=*', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
         '-c', 'commit.gpgsign=false', '-c', 'init.defaultBranch=main', *arguments],
        env=environment, check=True, capture_output=True, text=True).stdout


def seed_drift(root: Path, case: str) -> None:
    shape = drift_before(case)
    files = [root / f'hooks/core-{index}.txt' for index in range(10)]
    for path in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Tagged core content\n')
    version = root / 'LIFEOS/VERSION'
    version.parent.mkdir(parents=True, exist_ok=True)
    version.write_text(shape['version'] + '\n')
    tagged = datetime.now(timezone.utc).replace(microsecond=0)
    if shape['tag_age_hours']:
        tagged = datetime.fromtimestamp(tagged.timestamp() - shape['tag_age_hours'] * 3600, timezone.utc)
    git(root, 'init', '--quiet')
    git(root, 'add', 'settings.json', 'hooks', 'LIFEOS/VERSION')
    git(root, 'commit', '--quiet', '-m', 'Tagged fixture release', when=tagged)
    if shape['tag']:
        git(root, 'tag', shape['tag'])
    for path in files[:shape['changed_core_files']]:
        path.write_text('Changed core content\n')
    if shape['prior_nag_present']:
        recent = datetime.fromtimestamp(time.time() - 600, timezone.utc).isoformat()
        write_json(root / DRIFT_STATE, {'ts': recent, **PRIOR_DRIFT_NAG})


# case: seeded phase, iteration, prior page, expected log entry, expected page
RENDER_SHAPES = {
    'isa-render-absent': (None, None, False, None, 'absent'),
    'isa-render-first-authoring': ('execute', 1, False, ('skipped', 'paired-work/ISA.md:pre-completion'), 'absent'),
    'isa-render-missing': (None, None, False, ('skipped', 'absent-work/ISA.md:missing'), 'absent'),
    'isa-render-complete': ('complete', 1, False, ('rendered', 'paired-work/ISA.md'), 'rendered'),
    'isa-render-resumed': ('execute', 2, False, ('rendered', 'paired-work/ISA.md'), 'rendered'),
    'isa-render-existing-page': ('execute', 1, True, ('rendered', 'paired-work/ISA.md'), 'rendered'),
}
RENDER_WORK = 'LIFEOS/MEMORY/WORK'


def render_state(home: Path, session_id: str) -> Path:
    return home / '.claude/LIFEOS/MEMORY/STATE/isa-render-debounce' / (session_id + '.json')


def seed_render_state(home: Path, case: str, session_id: str) -> None:
    if case == 'isa-render-absent':
        return
    folder = 'absent-work' if case == 'isa-render-missing' else 'paired-work'
    write_json(render_state(home, session_id),
               {'edited_isas': [str(home / '.claude' / RENDER_WORK / folder / 'ISA.md')]})


def render_page(home: Path) -> str:
    page = home / '.claude' / RENDER_WORK / 'paired-work/ISA.html'
    if not page.is_file():
        return 'absent'
    content = page.read_text()
    if 'PAIR_PRIOR_PAGE' in content:
        return 'prior'
    return 'rendered' if 'PAIR_ISA_TITLE' in content and '<html' in content else 'other'


# Real tool cases: the model runs one exact shell command, so each client makes two requests.
TOOL_PREFIXES = ('atlas-bash-', 'guard-bash-', 'tool-log-', 'file-hint-', 'knowledge-', 'isa-edit-', 'isa-write-', 'isa-read-')
TOOL_SYSTEM_PROMPT = ('This is a synthetic hook fixture. Run the exact shell command from the user message once '
                      'with the shell tool. Do not change the command. Then reply with exactly READY. '
                      'If the tool call is blocked or fails, do not retry it. Reply with exactly READY.')
TOOL_COMMANDS = {
    'atlas-bash-systemd': "printf 'PAIR_ATLAS systemctl --user daemon-reload'",
    'atlas-bash-plain': "printf 'PAIR_ATLAS plain command'",
    'atlas-bash-multiple': "printf 'PAIR_ATLAS gh repo create fixture; launchctl load fixture'",
}
TOOL_COMMANDS.update({
    'guard-bash-plutil-block': "printf 'PAIR_%s' GUARD_OUTPUT; plutil -extract key raw fixture.plist",
    'guard-bash-plutil-safe': "printf 'PAIR_%s plutil -extract key raw -o - fixture.plist' GUARD_OUTPUT",
    'guard-bash-plain': "printf 'PAIR_%s' GUARD_OUTPUT",
})
TOOL_COMMANDS.update({
    'tool-log-success': "printf 'PAIR_%s' TOOL_LOG",
    'tool-log-repeat': "printf 'PAIR_%s' TOOL_LOG",
    'tool-log-failure': 'ls pair-missing-tool-log',
})
# Repeat cases ask for three identical calls. The model can add calls, so three is the required minimum.
TOOL_REPEATS = {'tool-log-repeat': 3}
TOOL_REPEAT_SYSTEM_PROMPT = ('This is a synthetic hook fixture. Run the exact shell command from the user message '
                             'three times with the shell tool, as three separate tool calls with identical input. '
                             'Make one tool call in each response and wait for its result before the next call. '
                             'Do not change the command. Do not make a fourth call, even when a hook reports a loop. '
                             'Then reply with exactly READY.')
TOOL_FAILURE_ERROR = "Exit code 2\nls: cannot access 'pair-missing-tool-log': No such file or directory"
LOOP_ALERT = "[LOOP DETECTED] You've called Bash 3 times with the same input this session without progress."
PINNED_ASYNC = {'tool-log-success': {'PostToolUse.11.1': 5}}
TOOL_MATCHERS = {'atlas-bash-': 'Bash', 'guard-bash-': 'Bash|Write|Edit|MultiEdit'}
EXPECTED_EXITS = {'guard-bash-plutil-block': [2]}
GUARD_BLOCK_MESSAGE = '[PreToolGuard] blocked `plutil -extract` without -o'
ATLAS_SOURCES = {'atlas-bash-systemd': ['systemd'], 'atlas-bash-plain': [],
                 'atlas-bash-multiple': ['github', 'launchd']}
ATLAS_EVENTS = '.local/state/lifeos/atlas/events.jsonl'
PRIOR_ATLAS_EVENT = {'ts': '2026-10-01T00:00:00.000Z', 'source': 'projects', 'tool': 'Write'}


def clock_timezone(case: str) -> str:
    if case == 'time-context-invalid-zone':
        return 'PAIR_INVALID_ZONE'
    return 'America/Toronto' if case.endswith('toronto') else 'UTC'


GENERIC_ROOTS = ('.claude/LIFEOS', '.local/state/lifeos')
GENERIC_EXCLUDED = ('.claude/LIFEOS/MEMORY/STATE/hermes-transcripts/',)
TIME_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?')
ID_PATTERN = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|\b[0-9a-f]{32,64}\b')


def normalize(text: str, home: Path, session_id: str) -> str:
    # Removes values that differ by client run only: paths, session identities, clock values, and digests.
    text = text.replace(str(home), '<home>')
    if session_id:
        text = text.replace(session_id, '<session>')
    text = TIME_PATTERN.sub('<time>', text)
    text = re.sub(r'\b1[789]\d{11}\b', '<epoch-ms>', text)
    # Each client keeps its transcript in its own place, and the event offset counts session identity bytes.
    text = re.sub(r'<home>/\.claude/projects/[^/"]+/<session>\.jsonl', '<transcript>', text)
    text = text.replace('<home>/.claude/LIFEOS/MEMORY/STATE/hermes-transcripts/<session>.jsonl', '<transcript>')
    text = re.sub(r'"_events_offset": \d+', '"_events_offset": <offset>', text)
    return ID_PATTERN.sub('<id>', text)


def generic_files(home: Path, session_id: str, case: str = '') -> dict:
    files = {}
    for base in GENERIC_ROOTS:
        root = home / base
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            relative = path.relative_to(home).as_posix()
            if path.is_symlink() or not path.is_file() or relative.startswith(GENERIC_EXCLUDED):
                continue
            data = path.read_bytes()
            try:
                content = normalize(data.decode(), home, session_id)
                for pattern, replacement in ACCEPTED_DIFFERENCES.get(case, []):
                    content = re.sub(pattern, replacement, content)
            except UnicodeDecodeError:
                content = 'binary:' + hashlib.sha256(data).hexdigest()
            files[normalize(relative, home, session_id)] = content
    return files


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
        invocations = len(side.get('hook_exit_codes', []))
        if name in TOOL_REPEATS or name in FILE_CASES:
            if invocations < len(CASES[name]) * TOOL_REPEATS.get(name, 1) or invocations % len(CASES[name]):
                errors.append(f'{name}: hook invocation count differs')
        elif invocations != len(CASES[name]):
            errors.append(f'{name}: hook invocation count differs')
        if name in EXPECTED_EXITS:
            if side.get('hook_exit_codes') != EXPECTED_EXITS[name]:
                errors.append(f'{name}: hook exit code differs')
        elif not side.get('hook_exit_codes') or any(code != 0 for code in side['hook_exit_codes']):
            errors.append(f'{name}: hook failed')
        if name in TOOL_REPEATS or name in FILE_CASES:
            if (side.get('model_generation_requests', 0) < 2
                    or side.get('model_successful_responses') != side.get('model_generation_requests')):
                errors.append(f'{name}: tool turn was not completed')
        elif name.startswith(TOOL_PREFIXES):
            if side.get('model_generation_requests') != 2 or side.get('model_successful_responses') != 2:
                errors.append(f'{name}: tool turn was not completed')
        elif delivery and side.get('model_generation_requests') != 1:
            errors.append(f'{name}: model delivery was not observed')
        elif not delivery and side.get('model_generation_requests') != 0:
            errors.append(f'{name}: model generation was attempted')
        if response and not name.startswith(TOOL_PREFIXES) and side.get('model_successful_responses') != 1:
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
        elif name.startswith('feedback-'):
            if before != {'rating_count': 1, 'learning_count': 0, 'cache_present': True} or after != expected_feedback(name):
                errors.append(f'{name}: feedback effect is missing')
        elif name.startswith('format-contract-'):
            initial = name == 'format-contract-empty'
            contract = expected_format_contract(name)
            expected_before = {'state': None if initial else PRIOR_FORMAT_STATE, 'cache_present': not initial}
            expected_after = {'state': {'last_fired_turn': 1 if initial else 7,
                'turn_count': 1 if initial else 7, 'last_text': contract, 'schema_version': 1},
                'cache_preserved': True, 'hook_context': contract,
                'model_contract_present': True, 'user_response_delivered': True}
            if before != expected_before or after != expected_after:
                errors.append(f'{name}: format contract effect is missing')
        elif name.startswith('time-context-'):
            invalid = name == 'time-context-invalid-zone'
            asynchronous = name == 'time-context-async-utc'
            expected_before = {'configured_timezone': clock_timezone(name), 'asynchronous': asynchronous}
            expected_after = {'clock_emitted': not invalid, 'clock_valid': not invalid,
                'clock_is_current': not invalid, 'settings_preserved': True,
                'clock_context_in_model': not invalid and not asynchronous,
                'user_response_delivered': True}
            if before != expected_before or after != expected_after:
                errors.append(f'{name}: time context effect is missing')
        elif name.startswith('generic-'):
            files, printed, delivered = GENERIC_EXPECTED[name]
            if (not isinstance(after.get('changed'), dict) or sorted(after['changed']) != files
                    or [bool(output) for output in after.get('outputs', [])] != printed
                    or after.get('context_in_model') != delivered or after.get('user_response_delivered') is not True):
                errors.append(f'{name}: generic effect is missing')
        elif name in ISA_CASES:
            if before != {'isa_closed': False, 'repo_commits': 1, 'repo_dirty': True} or after != isa_after(name):
                errors.append(f'{name}: ISA edit effect is missing')
        elif name.startswith('knowledge-'):
            warned = name == 'knowledge-off-schema'
            expected = {'target_content_matches': True, 'tool_names': ['Write'], 'file_path_matches': True,
                        'warning_emitted': warned, 'other_output': False, 'model_received_warning': warned,
                        'user_response_delivered': True}
            if before != {'target_present': False} or after != expected:
                errors.append(f'{name}: knowledge guard effect is missing')
        elif name.startswith('file-hint-'):
            tool, _, sources = FILE_CASES[name]
            expected = {'prior_event_preserved': True, 'hint_sources': sources,
                        'hint_tools': [tool] if sources else [], 'hints_current': True, 'one_hint_per_call': True,
                        'target_content_matches': True, 'tool_names': [tool], 'file_path_matches': True,
                        'hook_outputs_empty': True, 'evaluation_state_preserved': True,
                        'user_response_delivered': True}
            if before != {'atlas_rows': 1, 'target_present': tool == 'Edit',
                          'evaluation_state_present': name in SEEDED_EVALUATION_STATE} or after != expected:
                errors.append(f'{name}: file hint effect is missing')
        elif name.startswith('tool-log-'):
            failure, repeat = name == 'tool-log-failure', name in TOOL_REPEATS
            row = {'event': 'tool_failure' if failure else 'tool_use', 'tool_name': 'Bash',
                   'session_matches': True, 'preview_command_matches': True}
            expected = {
                'activity': [{**row, 'ground_truth_command_matches': True, 'output_recorded': True}]
                if name == 'tool-log-success' else [],
                'activity_rows_match_calls': True,
                'failures': [{**row, 'error_text_matches': True}] if failure else [],
                'loop': {'session_matches': True, 'seq_matches_calls': True, 'last_alert': 3 if repeat else 0,
                         'alert_count': int(repeat), 'tools': ['Bash'], 'failed': [failure],
                         'one_signature': True, 'state_count': 1},
                'alert_positions': {identifier: [3] if repeat else [] for identifier, _ in CASES[name]},
                'other_context': False, 'at_least_required_calls': True,
                'events': ['PostToolUseFailure' if failure else 'PostToolUse'], 'tool_names': ['Bash'],
                'commands_match': True, 'model_received_loop_alert': repeat,
                'tool_output_in_model': not failure, 'user_response_delivered': True}
            if before != {'activity_rows': 0, 'failure_rows': 0, 'loop_states': 0} or after != expected:
                errors.append(f'{name}: tool log effect is missing')
        elif name.startswith('guard-bash-'):
            blocked = name in EXPECTED_EXITS
            expected = {'project_files': [], 'tool_name': 'Bash', 'command_matches': True,
                        'block_message_emitted': blocked, 'model_received_block': blocked,
                        'tool_output_in_model': not blocked, 'user_response_delivered': True}
            if before != {'project_files': []} or after != expected:
                errors.append(f'{name}: guard decision is missing')
        elif name.startswith('atlas-bash-'):
            expected = {'prior_event_preserved': True,
                        'hints': [{'source': source, 'tool': 'Bash', 'timestamp_current': True}
                                  for source in ATLAS_SOURCES[name]],
                        'tool_name': 'Bash', 'command_matches': True, 'user_response_delivered': True}
            if before != {'event_rows': 1} or after != expected:
                errors.append(f'{name}: mutation hint effect is missing')
        elif name.startswith('isa-render-'):
            phase, iteration, prior, entry, page = RENDER_SHAPES[name]
            log = [{'session_matches': True, 'rendered': [], 'skipped': [], entry[0]: [entry[1]]}] if entry else []
            expected_before = {'state_present': name != 'isa-render-absent', 'isa_phase': phase,
                               'isa_iteration': iteration, 'page': 'prior' if prior else 'absent'}
            expected_after = {'state_present': False, 'log': log, 'page': page, 'isa_preserved': True,
                              'hook_output': {'continue': True}, 'user_response_delivered': True}
            if before != expected_before or after != expected_after:
                errors.append(f'{name}: render effect is missing')
        elif name.startswith('version-drift-'):
            if before != drift_before(name) or after != drift_after(name):
                errors.append(f'{name}: version drift effect is missing')
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
    if case.startswith('time-context-'):
        if not after:
            return {'configured_timezone': clock_timezone(case), 'asynchronous': case == 'time-context-async-utc'}
        output = read_json_lines(home / 'hooks.jsonl')[0]['stdout']
        match = re.search(r'Current time: ([A-Za-z]{3}) (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) ([A-Z]+) \(([^)]+)\)', output)
        valid = current = False
        if match:
            value = datetime.strptime(match[2], '%Y-%m-%d %H:%M').replace(tzinfo=ZoneInfo(clock_timezone(case)))
            hour = value.hour
            relative = 'late night' if hour < 5 or hour >= 21 else 'early morning' if hour < 9 else 'morning' if hour < 12 else 'afternoon' if hour < 17 else 'evening'
            valid = match[1] == value.strftime('%a') and match[3] == value.tzname() and match[4] == relative
            bounds = read_json(home / 'clock-bounds.json')
            start, end = (datetime.fromisoformat(bounds[key]).replace(second=0, microsecond=0)
                          for key in ('started_at', 'finished_at'))
            current = start <= value.astimezone(timezone.utc) <= end
        original = read_json(home / 'fixture-files-before.json')['settings.json']
        return {'clock_emitted': bool(output.strip()), 'clock_valid': valid, 'clock_is_current': current,
                'settings_preserved': original == fixture_files(home)['settings.json']}
    if case.startswith('generic-'):
        if not after:
            return {'files': len(generic_files(home, ''))}
        before_files = read_json(home / 'generic-before.json')
        current = generic_files(home, session_id, case)
        changed = {name: content for name, content in current.items() if before_files.get(name) != content}
        changed.update({name: '<deleted>' for name in before_files if name not in current})
        traces = read_json_lines(home / 'hooks.jsonl')
        return {'changed': dict(sorted(changed.items())),
                'outputs': [normalize(trace['stdout'].strip(), home, session_id) for trace in traces],
                'stderr_present': [bool(trace['stderr'].strip()) for trace in traces]}
    if case in ISA_CASES:
        work = project_dir(home, case)
        target = work / 'ISA.md'
        repo = home / CHECKPOINT_REPO
        commits = git(repo, 'log', '--format=%s').splitlines()
        if not after:
            return {'isa_closed': target.is_file() and '- [x] ISC-1:' in target.read_text(), 'repo_commits': len(commits),
                    'repo_dirty': bool(git(repo, 'status', '--porcelain').strip())}
        traces = read_json_lines(home / 'hooks.jsonl')
        payloads = [json.loads(base64.b64decode(trace['stdin_base64'])) for trace in traces]
        outputs = {}
        for trace in traces:
            text = trace['stdout'].strip()
            parsed = json.loads(text) if text.startswith('{') else None
            context = (parsed or {}).get('hookSpecificOutput', {}).get('additionalContext', '')
            outputs.setdefault(trace['id'], []).append({'continue_only': parsed == {'continue': True},
                'empty': not text, 'context_head': context.split('\n')[0][:80] if context else ''})
        registry = read_json(lifeos / 'MEMORY/STATE/work.json')['sessions'].get('pair-run', {}) \
            if (lifeos / 'MEMORY/STATE/work.json').is_file() else {}
        views = read_json(lifeos / 'MEMORY/STATE/isa-session-view' / (session_id + '.json'))['views'] \
            if (lifeos / 'MEMORY/STATE/isa-session-view' / (session_id + '.json')).is_file() else {}
        debounce = lifeos / 'MEMORY/STATE/isa-render-debounce' / (session_id + '.json')
        state = work / '.checkpoint-state.json'
        content = target.read_text()
        return {'isa_closed': '- [x] ISC-1:' in content,
                'tool_names': sorted({payload.get('tool_name') for payload in payloads}),
                'file_path_matches': all(payload.get('tool_input', {}).get('file_path') == str(target) for payload in payloads),
                'registry': {key: registry.get(key) for key in ('phase', 'progress', 'isa', 'task')},
                'view_matches_content': views.get(str(target)) == hashlib.sha256(content.encode()).hexdigest(),
                'render_state_lists_isa': debounce.is_file() and read_json(debounce).get('edited_isas') == [str(target)],
                'checkpoint_state': None if not state.is_file() else {
                    'committed_iscs': read_json(state)['committed_iscs'],
                    'sha_matches_head': read_json(state)['last_commit_sha'] == {str(repo): git(repo, 'rev-parse', 'HEAD').strip()}},
                # The plugin's checkpoint patch writes a conventional subject and keeps the stock text in the body.
                'checkpoint_commit': {'count': len(commits), 'names_criterion':
                    CHECKPOINT_TEXT in git(repo, 'log', '-1', '--format=%B'),
                    'changed_files': git(repo, 'show', '--name-only', '--format=', 'HEAD').split()},
                'repo_dirty': bool(git(repo, 'status', '--porcelain').strip()),
                'atlas_rows': len(read_json_lines(home / ATLAS_EVENTS)),
                'evaluation_state_present': (root / CONFIG_EVAL_STATE).is_file(),
                'outputs': {key: value[0] for key, value in sorted(outputs.items())}}
    if case.startswith('knowledge-'):
        _, name, _ = FILE_CASES[case]
        target = project_dir(home, case) / name
        if not after:
            return {'target_present': target.is_file()}
        traces = read_json_lines(home / 'hooks.jsonl')
        payloads = [json.loads(base64.b64decode(trace['stdin_base64'])) for trace in traces]
        contexts = [json.loads(trace['stdout'])['hookSpecificOutput']['additionalContext'] if trace['stdout'].strip() else ''
                    for trace in traces]
        return {'target_content_matches': target.is_file() and target.read_text().strip() == 'PAIR_FILE_CONTENT',
                'tool_names': sorted({payload.get('tool_name') for payload in payloads}),
                'file_path_matches': all(payload.get('tool_input', {}).get('file_path') == str(target) for payload in payloads),
                'warning_emitted': any(context.startswith(KNOWLEDGE_WARNING) for context in contexts),
                'other_output': any(context and not context.startswith(KNOWLEDGE_WARNING) for context in contexts)}
    if case.startswith('file-hint-'):
        tool, name, sources = FILE_CASES[case]
        target = project_dir(home, case) / name
        rows = read_json_lines(home / ATLAS_EVENTS)
        state = root / CONFIG_EVAL_STATE
        if not after:
            return {'atlas_rows': len(rows), 'target_present': target.is_file(),
                    'evaluation_state_present': state.is_file()}
        bounds = read_json(home / 'clock-bounds.json')
        started, finished = (datetime.fromisoformat(bounds[key]) for key in ('started_at', 'finished_at'))
        traces = read_json_lines(home / 'hooks.jsonl')
        payloads = [json.loads(base64.b64decode(trace['stdin_base64'])) for trace in traces]
        original = read_json(home / 'fixture-files-before.json').get(CONFIG_EVAL_STATE)
        expected = 'PAIR_FILE_CONTENT' if tool == 'Write' else FILE_SEED.replace('PAIR_OLD_LINE', 'PAIR_NEW_LINE').strip()
        calls = len(traces) // len(CASES[case])
        return {'prior_event_preserved': rows[:1] == [PRIOR_ATLAS_EVENT],
                'hint_sources': sorted({row.get('source') for row in rows[1:]}),
                'hint_tools': sorted({row.get('tool') for row in rows[1:]}),
                'hints_current': all(started.replace(microsecond=0) <= datetime.fromisoformat(
                    row['ts'].replace('Z', '+00:00')) <= finished for row in rows[1:]),
                'one_hint_per_call': len(rows) - 1 == calls * len(sources),
                'target_content_matches': target.is_file() and target.read_text().strip() == expected,
                'tool_names': sorted({payload.get('tool_name') for payload in payloads}),
                'file_path_matches': all(payload.get('tool_input', {}).get('file_path') == str(target)
                                         for payload in payloads),
                'hook_outputs_empty': all(not trace['stdout'].strip() for trace in traces),
                'evaluation_state_preserved': fixture_files(home).get(CONFIG_EVAL_STATE) == original}
    if case.startswith('tool-log-'):
        observability = lifeos / 'MEMORY/OBSERVABILITY'
        rows = {name: read_json_lines(observability / (name + '.jsonl')) if (observability / (name + '.jsonl')).is_file() else []
                for name in ('tool-activity', 'tool-failures')}
        states = sorted((lifeos / 'MEMORY/STATE/loop-detector').glob('*.json'))
        if not after:
            return {'activity_rows': len(rows['tool-activity']), 'failure_rows': len(rows['tool-failures']),
                    'loop_states': len(states)}
        command = TOOL_COMMANDS[case]
        preview = lambda row: json.loads(row.get('tool_input_preview') or '{}').get('command') == command
        traces = read_json_lines(home / 'hooks.jsonl')
        payloads = [json.loads(base64.b64decode(trace['stdin_base64'])) for trace in traces]
        calls = len(traces) // len(CASES[case])
        required = TOOL_REPEATS.get(case, 1)
        loop = None
        if states:
            state = read_json(states[0])
            loop = {'session_matches': states[0].stem == session_id, 'seq_matches_calls': state['seq'] == calls,
                    'last_alert': state['lastAlert'], 'alert_count': len(state['alerted']),
                    'tools': sorted({entry['tool'] for entry in state['window'][:required]}),
                    'failed': sorted({entry['failed'] for entry in state['window'][:required]}),
                    'one_signature': len({entry['sig'] for entry in state['window'][:required]}) == 1,
                    'state_count': len(states)}
        alerts, other_context = {}, False
        for identifier, _ in CASES[case]:
            selected = [trace for trace in traces if trace['id'] == identifier]
            contexts = [json.loads(trace['stdout'])['hookSpecificOutput']['additionalContext']
                        if trace['stdout'].strip() else '' for trace in selected]
            alerts[identifier] = [index for index, context in enumerate(contexts, 1) if LOOP_ALERT in context]
            other_context = other_context or any(context and LOOP_ALERT not in context for context in contexts)
        summarize = lambda entries, extra: [dict(row) for row in sorted({tuple(sorted({
            'event': row.get('event'), 'tool_name': row.get('tool_name'),
            'session_matches': row.get('session_id') == session_id,
            'preview_command_matches': preview(row), **extra(row)}.items())) for row in entries})]
        return {'activity': summarize(rows['tool-activity'], lambda row: {
                    'ground_truth_command_matches': row.get('ground_truth', {}).get('command') == command,
                    'output_recorded': 'PAIR_TOOL_LOG' in (row.get('ground_truth', {}).get('stdout_preview')
                                                           or row.get('ground_truth', {}).get('combined_output_preview') or '')}),
                'activity_rows_match_calls': len(rows['tool-activity']) in (0, calls),
                'failures': summarize(rows['tool-failures'], lambda row: {
                    'error_text_matches': row.get('error') == TOOL_FAILURE_ERROR}),
                'loop': loop, 'alert_positions': alerts, 'other_context': other_context,
                'at_least_required_calls': calls >= required,
                'events': sorted({payload.get('hook_event_name') for payload in payloads}),
                'tool_names': sorted({payload.get('tool_name') for payload in payloads}),
                'commands_match': all(payload.get('tool_input', {}).get('command') == command
                                      for payload in payloads[:required * len(CASES[case])])}
    if case.startswith('guard-bash-'):
        result = {'project_files': sorted(path.name for path in project_dir(home, case).iterdir())}
        if after:
            trace = read_json_lines(home / 'hooks.jsonl')[0]
            payload = json.loads(base64.b64decode(trace['stdin_base64']))
            result.update(tool_name=payload.get('tool_name'),
                          command_matches=payload.get('tool_input', {}).get('command') == TOOL_COMMANDS[case],
                          block_message_emitted=trace['stderr'].startswith(GUARD_BLOCK_MESSAGE))
        return result
    if case.startswith('atlas-bash-'):
        rows = read_json_lines(home / ATLAS_EVENTS)
        if not after:
            return {'event_rows': len(rows)}
        bounds = read_json(home / 'clock-bounds.json')
        started, finished = (datetime.fromisoformat(bounds[key]) for key in ('started_at', 'finished_at'))
        payload = json.loads(base64.b64decode(read_json_lines(home / 'hooks.jsonl')[0]['stdin_base64']))
        return {'prior_event_preserved': rows[:1] == [PRIOR_ATLAS_EVENT],
                'hints': [{'source': row.get('source'), 'tool': row.get('tool'),
                           'timestamp_current': started.replace(microsecond=0) <= datetime.fromisoformat(
                               row['ts'].replace('Z', '+00:00')) <= finished} for row in rows[1:]],
                'tool_name': payload.get('tool_name'),
                'command_matches': payload.get('tool_input', {}).get('command') == TOOL_COMMANDS[case]}
    if case.startswith('isa-render-'):
        work = root / RENDER_WORK
        document = work / 'paired-work/ISA.md'
        result = {'state_present': render_state(home, session_id).is_file(), 'page': render_page(home)}
        if not after:
            content = document.read_text() if document.is_file() else ''
            phase = re.search(r'^phase: (\w+)$', content, re.M)
            iteration = re.search(r'^iteration: (\d+)$', content, re.M)
            return {**result, 'isa_phase': phase[1] if phase else None,
                    'isa_iteration': int(iteration[1]) if iteration else None}
        name = RENDER_WORK + '/paired-work/ISA.md'
        relative = lambda value: value.replace(str(work) + '/', '', 1)
        log = lifeos / 'MEMORY/OBSERVABILITY/isa-render.jsonl'
        rows = read_json_lines(log) if log.is_file() else []
        return {**result,
                'isa_preserved': read_json(home / 'fixture-files-before.json').get(name) == fixture_files(home).get(name),
                'hook_output': json.loads(read_json_lines(home / 'hooks.jsonl')[0]['stdout']),
                'log': [{'session_matches': row.get('session_id') == session_id,
                         'rendered': [relative(value) for value in row.get('rendered', [])],
                         'skipped': [relative(value) for value in row.get('skipped', [])]} for row in rows]}
    if case.startswith('version-drift-'):
        state_path = root / DRIFT_STATE
        if not after:
            tags = git(root, 'tag', '-l').split()
            reference = tags[0] if tags else 'HEAD'
            tagged = int(git(root, 'log', '-1', '--format=%ct', reference))
            return {'changed_core_files': len(git(root, 'diff', '--name-only', reference).split()),
                    'tag': tags[0] if tags else None, 'tag_age_hours': round((time.time() - tagged) / 3600),
                    'version': (lifeos / 'VERSION').read_text().strip(),
                    'prior_nag_present': state_path.is_file(),
                    'asynchronous': case == 'version-drift-async-count'}
        stdout = read_json_lines(home / 'hooks.jsonl')[0]['stdout']
        state = read_json(state_path) if state_path.is_file() else None
        if state is not None:
            bounds = read_json(home / 'clock-bounds.json')
            written = datetime.fromisoformat(state.pop('ts').replace('Z', '+00:00'))
            started, finished = (datetime.fromisoformat(bounds[key]) for key in ('started_at', 'finished_at'))
            state['timestamp_current'] = started.replace(microsecond=0) <= written <= finished
        original = read_json(home / 'fixture-files-before.json')
        current = fixture_files(home)
        return {'hook_context': json.loads(stdout)['hookSpecificOutput']['additionalContext'] if stdout.strip() else None,
                'state': state,
                'worktree_preserved': all(current.get(name) == value for name, value in original.items()
                                          if name != DRIFT_STATE)}
    if case.startswith('format-contract-'):
        state_path = lifeos / 'MEMORY/STATE/drift-reminder.json'
        state = read_json(state_path) if state_path.is_file() else None
        cache = lifeos / 'MEMORY/STATE/last-response.txt'
        if not after:
            return {'state': state, 'cache_present': cache.is_file()}
        expected_cache = format_cache(case)
        preserved = cache.read_text() == expected_cache if cache.is_file() else expected_cache is None
        traces = read_json_lines(home / 'hooks.jsonl')
        stdout = json.loads(traces[0]['stdout'])
        return {'state': state, 'cache_preserved': preserved,
                'hook_context': stdout['hookSpecificOutput']['additionalContext']}
    if case.startswith('feedback-'):
        case = case.replace('feedback-async-', 'feedback-', 1)
        ratings_path = lifeos / 'MEMORY/LEARNING/SIGNALS/ratings.jsonl'
        ratings = read_json_lines(ratings_path) if ratings_path.is_file() else []
        learnings = sorted((lifeos / 'MEMORY/LEARNING').rglob('*_LEARNING_*.md'))
        cache = lifeos / 'MEMORY/STATE/last-response.txt'
        if not after:
            return {'rating_count': len(ratings), 'learning_count': len(learnings), 'cache_present': cache.is_file()}
        captured = []
        for entry in ratings[1:]:
            entry = dict(entry)
            timestamp = entry.pop('timestamp', '')
            try:
                timestamp_valid = datetime.fromisoformat(timestamp).tzinfo is not None
            except (ValueError, TypeError):
                timestamp_valid = False
            session_matches = entry.pop('session_id', None) == session_id
            preview_matches = entry.pop('response_preview', None) == FEEDBACK_RESPONSE[:500]
            captured.append({**entry, 'timestamp_valid': timestamp_valid,
                             'session_matches': session_matches, 'response_preview_matches_cache': preview_matches})
        result = {'unrelated_rating_preserved': bool(ratings) and ratings[0] == PRIOR_RATING,
                  'cache_preserved': cache.is_file() and cache.read_text() == FEEDBACK_RESPONSE,
                  'captured_ratings': captured, 'learning_count': len(learnings)}
        if case == 'feedback-low-rating':
            content = learnings[0].read_text() if len(learnings) == 1 else ''
            result['learning_checks'] = {
                'rating_matches': 'rating: 4\n' in content and '**Rating:** 4/10' in content,
                'source_matches': 'source: explicit\n' in content and '**Detection Method:** Explicit Rating' in content,
                'feedback_matches': '**Feedback:** needs clearer details' in content,
                'context_matches': '## Context\n\n' + FEEDBACK_RESPONSE + '\n\n---' in content,
                'principal_matches': 'rated 4/10 by FixtureOwner.' in content}
        return result
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
    if event == 'SessionStart' and case.startswith('isa-render-'):
        seed_render_state(home, case, payload['session_id'])
        write_json(home / 'before-state.json', state_snapshot(home, case, payload['session_id']))
        write_json(home / 'fixture-files-before.json', fixture_files(home))
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
        if case.startswith('format-contract-'):
            source_files.append(source / 'hooks/lib/banned-vocab.ts')
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
            sys.executable, str(trace_script), 'run', identifier, str(home / 'hooks.jsonl'), encoded))
        commands.append((identifier, wrapped, source_files))
    return commands


def make_fixture(home: Path, case: str, source: Path, trace_script: Path) -> list[dict]:
    home.mkdir(parents=True)
    root = home / '.claude'
    root.mkdir()
    (home / 'project').mkdir()
    project_dir(home, case).mkdir(parents=True, exist_ok=True)
    observer = ' '.join(shlex.quote(value) for value in (
        sys.executable, str(Path(__file__).resolve()), 'fixture-event', case))
    commands = hook_commands(home, case, source, trace_script)
    hooks = {event: [{'hooks': [{'type': 'command', 'command': observer}]}]
             for event in ('SessionStart', 'UserPromptSubmit', 'SessionEnd')}
    event = commands[0][0].split('.')[0]
    hooks.setdefault(event, []).append({'hooks': [{'type': 'command', 'command': command, 'timeout': 30}
                                   for _, command, _ in commands]})
    for hook, (identifier, _, _) in zip(hooks[event][-1]['hooks'], commands):
        if case.startswith('generic-') and identifier in PINNED_SETTINGS:
            asynchronous, timeout = PINNED_SETTINGS[identifier]
            hook.update(timeout=timeout, **({'async': True} if asynchronous else {}))
        if identifier in PINNED_ASYNC.get(case, {}):
            hook.update(timeout=PINNED_ASYNC[case][identifier], **{'async': True})
    if case in FILE_CASES:
        tool, name, _ = FILE_CASES[case]
        hooks[event][-1]['matcher'] = tool
        events = home / ATLAS_EVENTS
        events.parent.mkdir(parents=True, exist_ok=True)
        events.write_text(json.dumps(PRIOR_ATLAS_EVENT) + '\n')
        if tool == 'Edit':
            project_dir(home, case).mkdir(parents=True, exist_ok=True)
            (project_dir(home, case) / name).write_text(FILE_SEED)
        if case in ISA_CASES:
            started = datetime.fromtimestamp(time.time() - 60, timezone.utc).isoformat()
            project_dir(home, case).mkdir(parents=True, exist_ok=True)
            if case != 'isa-write-create':
                (project_dir(home, case) / name).write_text(ISA_SEED.format(started=started))
            else:
                (home / 'isa-started.txt').write_text(started)
            repo = home / CHECKPOINT_REPO
            repo.mkdir()
            (repo / 'tracked.txt').write_text('Committed fixture content\n')
            git(repo, 'init', '--quiet')
            git(repo, 'config', 'user.name', 'Fixture')
            git(repo, 'config', 'user.email', 'fixture@example.invalid')
            git(repo, 'add', 'tracked.txt')
            git(repo, 'commit', '--quiet', '-m', 'Fixture base')
            (repo / 'tracked.txt').write_text('Run change for the checkpoint\n')
            (root / 'checkpoint-repos.txt').write_text(str(repo) + '\n')
        if case in SEEDED_EVALUATION_STATE:
            write_json(root / CONFIG_EVAL_STATE, {'last_fire': datetime.now(timezone.utc).isoformat()})
    for prefix, matcher in TOOL_MATCHERS.items():
        if case.startswith(prefix):
            hooks[event][-1]['matcher'] = matcher
    if case.startswith('atlas-bash-'):
        events = home / ATLAS_EVENTS
        events.parent.mkdir(parents=True)
        events.write_text(json.dumps(PRIOR_ATLAS_EVENT) + '\n')
    if case.startswith('feedback-async-'):
        for hook in hooks[event][-1]['hooks']:
            hook.update(timeout=20, **{'async': True})
    if case == 'time-context-async-utc':
        hooks[event][-1]['hooks'][0].update(timeout=5, **{'async': True})
    if case == 'version-drift-async-count':
        hooks[event][-1]['hooks'][0].update(timeout=10, **{'async': True})
    settings = {'hooks': hooks}
    if case.startswith('time-context-'):
        settings['principal'] = {'timezone': clock_timezone(case)}
    if case == 'generic-model-rung':
        settings['model'] = 'fable'
    if case.startswith('format-contract-') and case != 'format-contract-empty':
        write_json(root / 'LIFEOS/MEMORY/STATE/drift-reminder.json', PRIOR_FORMAT_STATE)
        cache = root / 'LIFEOS/MEMORY/STATE/last-response.txt'
        cache.write_text(format_cache(case))
        if case == 'format-contract-stale':
            old = time.time() - 3600
            os.utime(cache, (old, old))
    if case.startswith('feedback-'):
        settings['principal'] = {'name': 'FixtureOwner'}
        cache = root / 'LIFEOS/MEMORY/STATE/last-response.txt'
        cache.parent.mkdir(parents=True)
        cache.write_text(FEEDBACK_RESPONSE)
        ratings = root / 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
        ratings.parent.mkdir(parents=True)
        ratings.write_text(json.dumps(PRIOR_RATING) + '\n')
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
    if case.startswith('isa-render-'):
        (root / 'LIFEOS').mkdir(exist_ok=True)
        (root / 'LIFEOS/TOOLS').symlink_to(source / 'LIFEOS/TOOLS', target_is_directory=True)
        phase, iteration, prior, _, _ = RENDER_SHAPES[case]
        work = root / RENDER_WORK / 'paired-work'
        work.mkdir(parents=True)
        if phase:
            status = 'COMPLETED' if phase == 'complete' else 'ACTIVE'
            (work / 'ISA.md').write_text(
                f'---\ntask: PAIR_ISA_TITLE\nphase: {phase}\niteration: {iteration}\nstatus: {status}\n---\n'
                '# Paired work\n\n## Claims\n- [x] The page follows completed work\n')
        if prior:
            page = work / 'ISA.html'
            page.write_text('<html>PAIR_PRIOR_PAGE</html>\n')
            old = time.time() - 3600
            os.utime(page, (old, old))
    write_json(root / 'settings.json', settings)
    if case.startswith('version-drift-'):
        seed_drift(root, case)
    if event == 'SessionStart' or case in {'update-counts-no-oauth', 'memory-health-critical'} or case.startswith(('doc-inventory-', 'response-cache-', 'feedback-', 'format-contract-', 'time-context-', 'version-drift-', 'atlas-bash-', 'guard-bash-', 'tool-log-', 'file-hint-', 'knowledge-', 'isa-edit-', 'isa-write-', 'isa-read-', 'generic-')):
        write_json(home / 'before-state.json', state_snapshot(home, case))
        if case.startswith('generic-'):
            write_json(home / 'generic-before.json', generic_files(home, '', case))
        write_json(home / 'fixture-files-before.json', fixture_files(home))
    return [{'id': identifier, 'command': command,
             'source_files': {str(path): digest(path) for path in paths}}
            for identifier, command, paths in commands]


# Real file tool cases: tool, project file, expected Atlas sources. The model can repeat a file call,
# so each case requires at least one call and one hint for each call.
FILE_CASES = {
    'file-hint-write-projects': ('Write', 'PROJECTS.md', ['projects']),
    'file-hint-write-plain': ('Write', 'notes.md', []),
    'file-hint-edit-gear': ('Edit', 'GEAR.md', ['gear']),
    'file-hint-sentinel-debounced': ('Write', 'example.hook.ts', []),
    'file-hint-sentinel-no-runner': ('Write', 'example.hook.ts', []),
    'knowledge-off-schema': ('Write', 'pair-idea.md', []),
    'knowledge-index-file': ('Write', '_index.md', []),
    'isa-edit-close': ('Edit', 'ISA.md', []),
    'isa-write-create': ('Write', 'ISA.md', []),
    'isa-read-view': ('Read', 'ISA.md', []),
}
ISA_CASES = ('isa-edit-close', 'isa-write-create', 'isa-read-view')
ISA_SEED = ('---\ntask: PAIR_ISA_TASK\nslug: pair-run\nphase: execute\nprogress: 0/1\nstarted: {started}\n---\n'
            '# Paired run\n\n## ISC Criteria\n- [ ] ISC-1: Paired criterion closes\n')
CHECKPOINT_REPO = 'checkpoint-repo'
CHECKPOINT_TEXT = 'ISC-1 (pair-run): Paired criterion closes'
ISA_EDIT_AFTER = {
    'isa_closed': True, 'tool_names': ['Edit'], 'file_path_matches': True,
    'registry': {'phase': 'execute', 'progress': '0/1', 'isa': 'MEMORY/WORK/pair-run/ISA.md', 'task': 'PAIR_ISA_TASK'},
    'view_matches_content': True, 'render_state_lists_isa': True,
    'checkpoint_state': {'committed_iscs': ['ISC-1'], 'sha_matches_head': True},
    'checkpoint_commit': {'count': 2, 'names_criterion': True, 'changed_files': ['tracked.txt']},
    'repo_dirty': False, 'atlas_rows': 1, 'evaluation_state_present': False,
    'outputs': {'PostToolUse.9.1': {'continue_only': False, 'empty': False, 'context_head': '<lifeos-ascent-delta>'},
                'PostToolUse.9.2': {'continue_only': True, 'empty': False, 'context_head': ''},
                'PostToolUse.9.3': {'continue_only': True, 'empty': False, 'context_head': ''},
                **{f'PostToolUse.9.{index}': {'continue_only': False, 'empty': True, 'context_head': ''} for index in (4, 5, 6, 7)}},
    'user_response_delivered': True}
# Cases whose tool target lies inside the LifeOS memory tree use that tree as the working directory,
# so both clients grant the write without a separate permission rule.
PROJECT_DIRS = {name: '.claude/LIFEOS/MEMORY/KNOWLEDGE/Ideas' for name in ('knowledge-off-schema', 'knowledge-index-file')}
PROJECT_DIRS.update({name: '.claude/LIFEOS/MEMORY/WORK/pair-run' for name in ISA_CASES})
KNOWLEDGE_WARNING = '\u26a0 Knowledge note written off-schema \u2014 `Ideas/pair-idea.md`'


def isa_after(case: str) -> dict:
    if case == 'isa-read-view':
        return {'isa_closed': False, 'tool_names': ['Read'], 'file_path_matches': True,
                'registry': dict.fromkeys(('phase', 'progress', 'isa', 'task')), 'view_matches_content': True,
                'render_state_lists_isa': False, 'checkpoint_state': None,
                'checkpoint_commit': {'count': 1, 'names_criterion': False, 'changed_files': ['tracked.txt']},
                'repo_dirty': True, 'atlas_rows': 1, 'evaluation_state_present': False,
                'outputs': {'PostToolUse.7.1': {'continue_only': True, 'empty': False, 'context_head': ''}},
                'user_response_delivered': True}
    if case == 'isa-edit-close':
        return ISA_EDIT_AFTER
    group = {f'PostToolUse.8.{key[-1]}': value for key, value in ISA_EDIT_AFTER['outputs'].items()}
    return {**ISA_EDIT_AFTER, 'tool_names': ['Write'], 'outputs': group}


def project_dir(home: Path, case: str) -> Path:
    return home / PROJECT_DIRS.get(case, 'project')
# A file name that ends in .hook.ts is a ConfigEvalFire sentinel. The fixture has no evaluation runner.
SEEDED_EVALUATION_STATE = {'file-hint-sentinel-debounced'}
FILE_SYSTEM_PROMPT = ('This is a synthetic hook fixture. Perform the exact file operation from the user message '
                      'with the file tools. Then reply with exactly READY. '
                      'If a tool call is blocked or fails, do not retry it. Reply with exactly READY.')
FILE_SEED = 'First fixture line\nPAIR_OLD_LINE\nLast fixture line\n'
CONFIG_EVAL_STATE = 'LIFEOS/MEMORY/OBSERVABILITY/config-eval-state.json'
MINIMUM_FREE_BYTES = 2 << 30


def require_free_space(path: Path, minimum: int) -> None:
    if shutil.disk_usage(path).free < minimum:
        raise RuntimeError('The paired run needs more free space on the fixture host')


def remove_tool_cache(home: Path) -> None:
    # Hermes fetches about 360 MB of tool programs into each new profile that uses the terminal toolset.
    shutil.rmtree(home / '.hermes/tools', ignore_errors=True)


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
                       TERMINAL_CWD=str(project_dir(home, case)), HERMES_WRITE_SAFE_ROOT=str(project_dir(home, case)),
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
    if case.startswith('feedback-'):
        command[-1] = FEEDBACK_PROMPTS[case]
    if case == 'format-contract-depth':
        command[-1] = 'Give a detailed report.'
    if case.startswith('generic-'):
        command[-1] = GENERIC_CASES[case][2]
    if case in FILE_CASES:
        tool, name, _ = FILE_CASES[case]
        target = project_dir(home, case) / name
        command[-1] = (f'Write a file at the absolute path {target} whose complete content is the single line '
                       'PAIR_FILE_CONTENT. Use the file writing tool once.' if tool == 'Write' else
                       f'In the file at the absolute path {target}, replace the text PAIR_OLD_LINE with '
                       'PAIR_NEW_LINE. Use the file editing tool. Do not rewrite the whole file.')
        if case == 'isa-edit-close':
            command[-1] = (f'In the file at the absolute path {target}, replace the exact text "- [ ] ISC-1:" with '
                           '"- [x] ISC-1:". Use the file editing tool once. Do not change anything else.')
        if case == 'isa-write-create':
            content = ISA_SEED.format(started=(home / 'isa-started.txt').read_text()).replace('- [ ] ISC-1:', '- [x] ISC-1:')
            command[-1] = (f'Create the file at the absolute path {target} with the file writing tool once. '
                           'Its complete content is exactly the text between the markers, without the markers.\n'
                           'BEGIN\n' + content + 'END')
        if case == 'isa-read-view':
            command[-1] = f'Read the file at the absolute path {target} once with the file reading tool.'
        if side == 'native':
            command[command.index('--tools') + 1] = {'Write': 'Write', 'Read': 'Read'}.get(tool, 'Read,Edit')
            command[command.index('--append-system-prompt') + 1] = FILE_SYSTEM_PROMPT
            # Claude Code treats files below its configuration directory as sensitive and asks for approval
            # even in acceptEdits mode. Cases that write into the LifeOS memory tree use bypass mode.
            mode = 'bypassPermissions' if case in PROJECT_DIRS else 'acceptEdits'
            command[-1:-1] = ['--permission-mode', mode, '--max-turns', '5']
        else:
            command[command.index('-t') + 1] = 'file'
            environment['HERMES_EPHEMERAL_SYSTEM_PROMPT'] = FILE_SYSTEM_PROMPT
    elif case.startswith(TOOL_PREFIXES):
        command[-1] = 'Run this exact shell command once: ' + TOOL_COMMANDS[case]
        system_prompt = TOOL_SYSTEM_PROMPT
        if case in TOOL_REPEATS:
            command[-1] = 'Run this exact shell command three times: ' + TOOL_COMMANDS[case]
            system_prompt = TOOL_REPEAT_SYSTEM_PROMPT
        if side == 'native':
            command[command.index('--tools') + 1] = 'Bash'
            command[command.index('--append-system-prompt') + 1] = system_prompt
            command[-1:-1] = ['--permission-mode', 'default', '--max-turns', '6' if case in TOOL_REPEATS else '3']
        else:
            command[command.index('-t') + 1] = 'terminal'
            environment['HERMES_EPHEMERAL_SYSTEM_PROMPT'] = system_prompt
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
    clock_started = datetime.now(timezone.utc).isoformat()
    execution = {'user': spec['uid'], 'group': spec['gid'], 'extra_groups': []} if os.geteuid() == 0 else {}
    with (home / 'cli.log').open('w') as log:
        process = subprocess.Popen(command, env=environment, cwd=project_dir(home, case),
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True, **execution)
        try:
            exit_code = process.wait(timeout=120 if response else 60)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
            raise
    if case.startswith(('time-context-', 'version-drift-', 'atlas-bash-', 'file-hint-')):
        write_json(home / 'clock-bounds.json', {'started_at': clock_started,
                   'finished_at': datetime.now(timezone.utc).isoformat()})
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
    observed_ids = sorted(row['id'] for row in traces)
    repeats = len(observed_ids) // len(expected_ids)
    if (case in TOOL_REPEATS or case in FILE_CASES) and repeats >= TOOL_REPEATS.get(case, 1):
        expected_ids = expected_ids * repeats
    if observed_ids != sorted(expected_ids):
        raise ValueError('The real lifecycle did not invoke each selected hook exactly once')
    if case.startswith('isa-render-') and RENDER_SHAPES[case][4] == 'rendered':
        deadline = time.monotonic() + 30
        while render_page(home) != 'rendered' and time.monotonic() < deadline:
            time.sleep(0.5)
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
            if case.startswith('time-context-'):
                combined = json.dumps([row['body'] for row in generation], ensure_ascii=False)
                clock_lines = [line for line in traces[0]['stdout'].splitlines() if 'Current time:' in line]
                after['clock_context_in_model'] = '<time-now>' in combined and len(clock_lines) == 1 and clock_lines[0] in combined
            if case.startswith('generic-'):
                combined = json.dumps([row['body'] for row in generation], ensure_ascii=False)
                contexts = []
                for trace in traces:
                    try:
                        value = json.loads(trace['stdout']).get('hookSpecificOutput', {}).get('additionalContext', '')
                    except (ValueError, AttributeError):
                        value = trace['stdout'].strip() if trace['event'] == 'UserPromptSubmit' else ''
                    if value:
                        contexts.append(value)
                after['context_in_model'] = [json.dumps(context, ensure_ascii=False)[1:-1] in combined
                                             for context in contexts]
            if case.startswith('knowledge-'):
                later = json.dumps([row['body'] for row in generation[1:]], ensure_ascii=False)
                after['model_received_warning'] = KNOWLEDGE_WARNING in later
            if case.startswith('tool-log-'):
                later = json.dumps([row['body'] for row in generation[1:]], ensure_ascii=False)
                after['model_received_loop_alert'] = LOOP_ALERT in later
                after['tool_output_in_model'] = 'PAIR_TOOL_LOG' in later
            if case.startswith('guard-bash-'):
                later = json.dumps([row['body'] for row in generation[1:]], ensure_ascii=False)
                after['model_received_block'] = GUARD_BLOCK_MESSAGE in later
                after['tool_output_in_model'] = 'PAIR_GUARD_OUTPUT' in later
            if case.startswith('version-drift-'):
                combined = json.dumps([row['body'] for row in generation], ensure_ascii=False)
                after['model_nag_present'] = bool(after['hook_context']) and after['hook_context'] in combined
            if case.startswith('format-contract-'):
                combined = json.dumps([row['body'] for row in generation], ensure_ascii=False)
                after['model_contract_present'] = expected_format_contract(case) in combined
            results = []
            for line in (home / 'cli.log').read_text().splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict) and row.get('type') == 'result':
                    results.append(row)
            user_response = (results[0].get('result', '') if side == 'native' else results[0].get('text', '')) if len(results) == 1 else ''
            after['user_response_delivered'] = bool(user_response) and (case.startswith(('feedback-', 'format-contract-', 'time-context-', 'version-drift-', 'file-hint-', 'knowledge-', 'isa-edit-', 'isa-write-', 'isa-read-', 'generic-')) or 'READY' in user_response)
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
    remove_tool_cache(home)
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
                require_free_space(Path(config[side]['home_root']).parent, MINIMUM_FREE_BYTES)
                try:
                    paired[side] = run_side(side, config[side], case, output, endpoint, guard)
                finally:
                    remove_tool_cache(Path(config[side]['home_root']) / output.name / case)
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
