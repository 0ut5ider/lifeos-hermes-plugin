# ABOUTME: Records hook contract behavior with disposable roots and real child hooks.
# ABOUTME: Executes bridge decisions without running a file tool or modifying user data.
import json
from pathlib import Path
import sys
import tempfile
from lifeos_hook_bridge.bridge import HookBridge

rows = []
with tempfile.TemporaryDirectory(prefix='parity-inventory-') as directory:
    root = Path(directory)
    for name, event, matcher, output in [
        ('matcher_star', 'PreToolUse', '*', {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny'}}),
        ('matcher_comma', 'PreToolUse', 'Read, Write', {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny'}}),
        ('matcher_prefix', 'PreToolUse', '^Re', {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny'}}),
        ('matcher_exact_control', 'PreToolUse', 'Read', {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny'}}),
        ('post_block_reason', 'PostToolUse', 'Read', {'decision': 'block', 'reason': 'SYNTHETIC POST BLOCK'}),
        ('pre_continue_false', 'PreToolUse', 'Read', {'continue': False, 'stopReason': 'SYNTHETIC STOP'}),
        ('permission_updated_input', 'PermissionRequest', 'Write', {'hookSpecificOutput': {'hookEventName': 'PermissionRequest', 'decision': {'behavior': 'allow', 'updatedInput': {'file_path': str(root/'replacement'), 'content': 'REPLACEMENT'}}}}),
        ('session_end_other', 'SessionEnd', 'other', {}),
    ]:
        marker = root / (name + '.marker')
        hook = root / (name + '.py')
        hook.write_text('import json\nfrom pathlib import Path\n' + f'Path({str(marker)!r}).write_text("ran")\nprint({json.dumps(output)!r})\n')
        settings = root/'settings.json'
        settings.write_text(json.dumps({'hooks': {event: [{'matcher': matcher, 'hooks': [{'type': 'command', 'command': f'{sys.executable} {hook}'}]}]}}))
        bridge = HookBridge(settings, root)
        try:
            if event == 'PostToolUse':
                result = bridge.post_tool_call('read_file', {'path': str(root/'original')}, 'SYNTHETIC RESULT', session_id=name)
            elif event == 'SessionEnd':
                result = bridge.session_end(session_id=name)
            elif event == 'PermissionRequest':
                result = bridge.pre_tool_call('write_file', {'path': str(root/'original'), 'content': 'ORIGINAL'}, session_id=name)
            else:
                result = bridge.pre_tool_call('read_file', {'path': str(root/'original')}, session_id=name)
            rows.append({'case': name, 'result': result, 'hook_ran': marker.exists()})
        except Exception as error:
            rows.append({'case': name, 'error': type(error).__name__ + ': ' + str(error), 'hook_ran': marker.exists()})
        finally:
            bridge.close()
print(json.dumps(rows, indent=2))
