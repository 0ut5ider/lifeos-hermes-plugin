# ABOUTME: Drives real Hermes conversations and session rotation through native compression.
# ABOUTME: Retains admission, database lineage, and the first continuation result after compression.
from contextlib import redirect_stdout
import io
import json
import logging
import os
from pathlib import Path
import sys
import threading

sys.path[:0] = [str(Path(__file__).parents[1]), os.environ['LIFEOS_HERMES_SOURCE']]

from gateway.session_context import clear_session_vars, set_session_vars
from hermes_cli.plugins import get_plugin_manager
from hermes_state import SessionDB
from run_agent import AIAgent


def main():
    settings = json.loads(sys.stdin.read())
    tokens = set_session_vars(platform='chat-a', user_id='100', chat_id='200', chat_type='dm', session_id='session')
    manager = get_plugin_manager()
    database_warnings = io.StringIO()
    logger = logging.getLogger('hermes_state')
    handler = logging.StreamHandler(database_warnings)
    handler.setLevel(logging.WARNING)
    logger.addHandler(handler)
    logger.propagate = False
    database = SessionDB(Path(os.environ['HERMES_HOME']) / 'state.db')
    agent = None
    diagnostics = io.StringIO()
    admission_trace = []
    def trace(frame, event, arg):
        if frame.f_code.co_name == '_check_call' and event == 'exception':
            values = frame.f_locals
            context = values.get('context')
            admission_trace.append({'thread': threading.current_thread().name,
                'session': values.get('session_id'), 'bound_session': getattr(context, 'session_id', None),
                'aux_task': values.get('kwargs', {}).get('aux_task'), 'error': str(arg[1])})
        return trace
    sys.settrace(trace)
    threading.settrace(trace)
    try:
        with redirect_stdout(diagnostics):
            agent = AIAgent(**settings['route'], api_key='synthetic-key', session_id='session', session_db=database,
                            platform='chat-a', user_id='100', chat_id='200', chat_type='dm', quiet_mode=True,
                            enabled_toolsets=['memory', 'skills'], skip_context_files=True, skip_background_review=True,
                            cwd=os.environ['HERMES_HOME'])
            history = None
            for index in range(6):
                turn = agent.run_conversation((f'Synthetic owner turn {index}: ' + ('Synthetic retained work context. ' * 200)).rstrip(),
                                              conversation_history=history)
                if turn.get('failed') or turn.get('turn_exit_reason') == 'prompt_blocked':
                    raise RuntimeError(json.dumps({'index': index, 'session': agent.session_id,
                        'reason': turn.get('turn_exit_reason'), 'api_calls': turn.get('api_calls'),
                        'response': turn.get('final_response'), 'diagnostics': diagnostics.getvalue()}))
                history = turn['messages']
            parent = agent.session_id
            compressed, system_prompt = agent._compress_context(history, agent._cached_system_prompt, force=True)
            child = agent.session_id
            parent_row = database.get_session(parent)
            child_row = database.get_session(child)
            continuation = agent.run_conversation('Continue the synthetic owner conversation after compression.',
                                                  conversation_history=compressed)
        print(json.dumps({'parent': parent, 'child': child, 'parent_row': parent_row, 'child_row': child_row,
                          'compressed': compressed, 'system_prompt': system_prompt,
                          'continuation': continuation, 'diagnostics': diagnostics.getvalue(),
                          'admission_trace': admission_trace,
                          'database_warnings': database_warnings.getvalue(),
                          'journal_mode': database._conn.execute('PRAGMA journal_mode').fetchone()[0]}))
    finally:
        sys.settrace(None)
        threading.settrace(None)
        if agent is not None:
            agent.close()
        database.close()
        logger.removeHandler(handler)
        manager.unload()
        clear_session_vars(tokens)


if __name__ == '__main__':
    main()
