# ABOUTME: Reproduces bridge permission edge cases in disposable roots.
# ABOUTME: Prints decisions without running any denied file operation.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from lifeos_hook_bridge import bridge as module
from lifeos_hook_bridge.bridge import HookBridge
from lifeos_hook_bridge.bash_permissions import bash_file_targets

rows = []
original_cwd = Path.cwd()
with tempfile.TemporaryDirectory(prefix='lifeos-fresh-review-') as temporary:
    root = Path(temporary)
    workspace = root / 'workspace'
    workspace.mkdir()
    (workspace / 'sub').mkdir()
    (workspace / 'sub' / 'secret').write_text('SYNTHETIC-ONLY\n')
    os.chdir(workspace)
    settings = root / 'settings.json'
    def create(data):
        settings.write_text(json.dumps(data))
        return HookBridge(settings, root)
    absolute_deny = 'Read(/' + str(workspace / 'sub' / 'secret') + ')'
    b = create({'permissions': {'allow':['Bash(*)'], 'deny':[absolute_deny]}})
    try:
        for command in ['cat sub/secret', 'cd sub && cat secret', '(cd sub && cat secret)', 'cd sub; cat secret']:
            rows.append({'case':'cwd_target', 'command':command, 'targets':bash_file_targets(command), 'decision':b.command_approval(command, cwd=str(workspace))})
    finally:
        b.close()
    allow_hook = root / 'allow.py'
    allow_hook.write_text("import json; print(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest','decision':{'behavior':'allow'}}}))\n")
    policy = root / 'policy'
    policy.mkdir()
    (policy / 'managed-settings.json').write_text('{')
    old_policy = module.POLICY_DIRECTORY
    module.POLICY_DIRECTORY = policy
    b = create({'hooks':{'PermissionRequest':[{'matcher':'Bash|Write|Edit','hooks':[{'type':'command','command':f'{sys.executable} {allow_hook}'}]}]}})
    try:
        rows.append({'case':'malformed_managed', 'tool':'read_file', 'decision':b.pre_tool_call('read_file', {'path':str(workspace / 'allowed.txt')})})
        rows.append({'case':'malformed_managed', 'tool':'write_file', 'decision':b.pre_tool_call('write_file', {'path':str(workspace / 'allowed.txt'), 'content':'synthetic'})})
        rows.append({'case':'malformed_managed', 'tool':'Bash', 'decision':b.command_approval('cat allowed.txt', cwd=str(workspace))})
    finally:
        b.close()
        module.POLICY_DIRECTORY = old_policy
    ask_hook = root / 'ask.py'
    ask_hook.write_text("import json; print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'ask','permissionDecisionReason':'Synthetic ask'}}))\n")
    b = create({'hooks':{'PreToolUse':[{'matcher':'Read','hooks':[{'type':'command','command':f'{sys.executable} {ask_hook}'}]}]}})
    try:
        rows.append({'case':'pretool_ask', 'decision':b.pre_tool_call('read_file', {'path':str(workspace / 'allowed.txt')})})
    finally:
        b.close()
    marker = root / 'session-start-marker'
    start_hook = root / 'start.py'
    start_hook.write_text(f"from pathlib import Path; Path({str(marker)!r}).write_text('started')\n")
    b = create({'hooks':{'SessionStart':[{'matcher':'startup','hooks':[{'type':'command','command':f'{sys.executable} {start_hook}'}]}]}})
    try:
        b.pre_llm_call('synthetic prompt', session_id='synthetic', is_first_turn=True)
        rows.append({'case':'session_start_matcher', 'marker_exists':marker.exists()})
    finally:
        b.close()
    os.chdir(original_cwd)
print(json.dumps(rows, indent=2))
