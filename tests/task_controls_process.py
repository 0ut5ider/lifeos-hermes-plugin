# ABOUTME: Creates actual synthetic kanban tasks through installed native governance.
# ABOUTME: Checks session limits, read operations, and delegated-child rejection with a real board.
import json
import logging
import os
from pathlib import Path

from hermes_cli import plugins
from model_tools import handle_function_call
from agent.delegation_context import delegated_child_context
from hermes_cli import kanban_db as board
from hermes_cli import kanban_db_connect

class WarningCapture(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.rows = []
    def emit(self, record):
        self.rows.append(record.getMessage())


warning_capture = WarningCapture()
logging.getLogger().addHandler(warning_capture)
home = Path.home()
root = home / '.claude'
source = Path(os.environ['PAIR_FILE_SOURCE'])
profile = Path(os.environ['HERMES_HOME'])
root.mkdir()
(root / 'hooks').symlink_to(source / 'hooks', target_is_directory=True)
(profile / 'config.yaml').write_text(json.dumps({'plugins': {'enabled': ['lifeos-hook-bridge']}, 'toolsets': ['kanban']}))
(root / 'settings.json').write_text(json.dumps({'hooks': {'TaskCreated': [{'hooks': [
    {'type': 'command', 'command': 'bun ' + str(root / 'hooks/TaskGovernance.hook.ts')}]}]}}))
plugins._reset_plugin_managers_for_tests()
plugins.discover_plugins()


def call(args, session, id, name='kanban_create'):
    result = handle_function_call(name, args, task_id=session, session_id=session, tool_call_id=id)
    value, _ = json.JSONDecoder().raw_decode(result)
    return value


try:
    short = call({'title': 'short', 'assignee': 'fixture'}, 'parent', 'short')
    assert short.get('error') and 'description too short' in short['error'], short
    ids = []
    for number in range(50):
        args = {'title': 'Fixture task ' + str(number), 'body': 'Verify the synthetic task ' + str(number), 'assignee': 'fixture'}
        result = call(args, 'parent', 'task-' + str(number))
        assert result.get('ok') and result.get('task_id'), result
        ids.append(result['task_id'])
    result = call({'title': 'Extra meaningful task', 'assignee': 'fixture'}, 'parent', 'task-51')
    assert result.get('error') and 'session limit of 50' in result['error'], result
    actual = call({'task_id': ids[-1]}, 'parent', 'read', name='kanban_show')
    assert actual.get('task', {}).get('id') == ids[-1], actual
    other = call({'title': 'Other meaningful task', 'assignee': 'fixture'}, 'other-parent', 'other')
    assert other.get('ok'), other
    with delegated_child_context('fixture-child'):
        child = call({'title': 'Child meaningful task', 'assignee': 'fixture'}, 'child-session', 'child')
        assert child.get('error') and 'delegate_task child agents' in child['error'], child
    conn = kanban_db_connect.connect()
    try:
        rows = board.list_tasks(conn, limit=200)
        assert len(rows) == 51, len(rows)
        assert set(task.id for task in rows) == set(ids + [other['task_id']])
    finally:
        conn.close()
    state = root / 'LIFEOS/MEMORY/STATE/hermes-task-counts'
    states = [json.loads(path.read_text()) for path in state.glob('*.json')]
    assert len(warning_capture.rows) <= 1 and all('WAL-reset corruption bug' in row and 'journal_mode=DELETE' in row for row in warning_capture.rows), warning_capture.rows
    assert sorted(row['count'] for row in states) == [1, 50], states
    (home / 'task-results.json').write_text(json.dumps({'actual_board_tasks': 51, 'accepted_parent_tasks': 50,
        'denied_51st_task': True, 'short_denied': True, 'reads_allowed_at_limit': True,
        'other_parent_count': 1, 'delegated_child_denied_by_native_host': True, 'failed_child_reservation_released': True}, indent=2)+'\n')
finally:
    plugins.unload_plugins()
