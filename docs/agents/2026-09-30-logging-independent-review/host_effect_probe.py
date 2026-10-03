# ABOUTME: Observes native Hermes permission enforcement and context construction.
# ABOUTME: Uses a disposable plugin home and synthetic content without a model request.
# Historical aborted probe: importing hermes_bootstrap can rebuild shared host assets.
# Do not run this script. The report records why the original attempt was stopped.

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace


parser = argparse.ArgumentParser()
parser.add_argument('--traced', action='store_true')
args = parser.parse_args()
home = Path.home()
host = home / 'workspace/hermes-agent'
development = home / 'workspace/development-hook-capture/development'
with tempfile.TemporaryDirectory(prefix='independent-host-effects-') as temporary:
    root = Path(temporary)
    os.chdir(root)
    isolated_home = root / 'hermes'
    plugin = isolated_home / 'plugins/lifeos-hook-bridge'
    plugin.parent.mkdir(parents=True)
    shutil.copytree(home / '.hermes/plugins/lifeos-hook-bridge', plugin)
    (isolated_home / 'config.yaml').write_text('plugins:\n  enabled:\n    - lifeos-hook-bridge\napprovals:\n  mode: manual\n')
    settings = root / 'settings.json'
    hook = root / 'deny.py'
    hook.write_text('import json,sys\njson.load(sys.stdin)\nprint(json.dumps({"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"deny","message":"SYNTHETIC-DENY"}}}))\n')
    settings.write_text(json.dumps({'hooks': {'PermissionRequest': [{'matcher': 'Bash', 'hooks': [
        {'type': 'command', 'command': str(sys.executable) + ' ' + str(hook)}]}]}}))
    os.environ['HERMES_HOME'] = str(isolated_home)
    os.environ['LIFEOS_HOOK_SETTINGS'] = str(settings)
    sys.path.insert(0, str(host))
    import hermes_bootstrap
    if args.traced:
        sys.path.insert(0, str(development))
        from hook_capture.instrument import install
        from hook_capture.setup import HOST_FILES, PLUGIN_FILES
        paths = [plugin / name for name in PLUGIN_FILES] + [host / name for name in HOST_FILES]
        config = root / 'capture-config.json'
        config.write_text(json.dumps({'enabled': True, 'root': str(root / 'capture'), 'run_id': 'host-effects',
            'plugin_root': str(plugin), 'host_root': str(host),
            'capture_sources': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in (development / 'hook_capture').glob('*.py')},
            'fingerprints': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}))
        config.chmod(0o600)
        install(config)
    from hermes_cli import plugins
    plugins._reset_plugin_managers_for_tests()
    from tools import terminal_tool
    marker = root / 'original-command-ran'
    outcome = json.loads(terminal_tool._handle_terminal({'command': 'printf EFFECT > ' + str(marker), 'workdir': str(root)}, task_id='synthetic-policy'))
    from agent.turn_context import build_api_messages
    agent = SimpleNamespace(session_id='SYNTHETIC-SESSION', _current_turn_id='SYNTHETIC-TURN',
        _current_turn_timestamp=0, ephemeral_system_prompt='SYNTHETIC-EPHEMERAL',
        _copy_reasoning_content_for_api=lambda message, output: None,
        _should_sanitize_tool_calls=lambda: False)
    result = build_api_messages(agent, [{'role': 'user', 'content': 'SYNTHETIC-PROMPT'}],
        current_turn_user_idx=0, ext_prefetch_cache='', plugin_user_context='SYNTHETIC-CONTEXT',
        moa_config=None, active_system_prompt='SYNTHETIC-SYSTEM')
    events = [json.loads(line) for path in (root / 'capture').glob('runs/*/events/*/*.jsonl')
              for line in path.read_text().splitlines()]
    context_events = [event for event in events if event['stage'].startswith('host.build_api_messages.')]
    context_return = next((event for event in context_events if event['stage'].endswith('.returned')), None)
    captured_context_has_marker = False
    if context_return:
        payload = gzip.decompress((root / 'capture' / context_return['data_ref']['path']).read_bytes()).decode()
        captured_context_has_marker = 'SYNTHETIC-CONTEXT' in payload
    print(json.dumps({'traced': args.traced, 'permission_result_status': outcome.get('status'),
        'permission_result_contains_deny': 'SYNTHETIC-DENY' in json.dumps(outcome),
        'command_side_effect_occurred': marker.exists(),
        'built_context_contains_injection': 'SYNTHETIC-CONTEXT' in str(result),
        'captured_context_contains_injection': captured_context_has_marker,
        'context_events': len(context_events), 'context_events_with_turn_id': sum(bool(event.get('turn_id')) for event in context_events),
        'context_events_with_session_id': sum(bool(event.get('session_id')) for event in context_events),
        'capture_gap_events': sum(event.get('status') == 'capture_gap' for event in events),
        'captured_stages': sorted(set(event['stage'] for event in events))}, indent=2))
    plugins._reset_plugin_managers_for_tests()
