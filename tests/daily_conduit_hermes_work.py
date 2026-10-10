# ABOUTME: Writes an ISA through installed Hermes file tools and the native ISASync hook.
# ABOUTME: Reports the actual work registry events for governed Conduit scheduling checks.
import io
import json
import os
from pathlib import Path
import sys
import warnings
from contextlib import redirect_stdout
from datetime import datetime, timezone

with warnings.catch_warnings(record=True) as import_warnings:
    warnings.simplefilter('always', SyntaxWarning)
    from gateway.session_context import clear_session_vars, set_session_vars
    from hermes_cli import plugins
    from model_tools import handle_function_call
    from tools.terminal_tool import cleanup_all_environments


def main():
    inputs = json.load(sys.stdin)
    root = Path(inputs['root'])
    session = 'synthetic-conduit-hermes-work'
    tokens = set_session_vars(platform='cli', session_id=session)
    os.umask(0o077)
    diagnostics = io.StringIO()
    try:
        with redirect_stdout(diagnostics):
            plugins.discover_plugins()
            admission = plugins.invoke_hook('pre_prompt_admission', user_message='Synthetic Conduit ISA check',
                session_id=session, platform='cli', is_first_turn=True, **inputs['route'])
            if any(isinstance(value, dict) and value.get('action') == 'block' for value in admission):
                raise RuntimeError('The selected owner prompt does not pass admission')
            path = root / 'LIFEOS/MEMORY/WORK/synthetic-conduit-hermes/ISA.md'
            path.parent.mkdir(parents=True, exist_ok=True)
            content = ('---\ntitle: Synthetic Conduit Hermes work\nstarted: '
                + datetime.now(timezone.utc).isoformat()
                + '\nphase: observe\nprogress: 0/1\n---\n\n## Claims\n'
                + '- [ ] ISC-1: Record synthetic work activity\n')
            result = handle_function_call('write_file', {'path': str(path), 'content': content},
                task_id=session, session_id=session, tool_call_id=session)
            value, end = json.JSONDecoder().raw_decode(result)
            if value.get('error'):
                raise RuntimeError(result)
            if path.read_text() != content:
                raise RuntimeError('The Hermes file tool does not retain the selected ISA')
            ledger = root / 'LIFEOS/MEMORY/STATE/work-events.jsonl'
            events = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
            registry = json.loads((root / 'LIFEOS/MEMORY/STATE/work.json').read_text())
        print(json.dumps({'events': events, 'registry': registry, 'tool_context': result[end:].strip(),
            'diagnostics': diagnostics.getvalue(), 'import_warnings': [
                {'filename': warning.filename, 'line': warning.lineno, 'message': str(warning.message)}
                for warning in import_warnings]}))
    finally:
        plugins.unload_plugins()
        cleanup_all_environments()
        clear_session_vars(tokens)


if __name__ == '__main__':
    main()
