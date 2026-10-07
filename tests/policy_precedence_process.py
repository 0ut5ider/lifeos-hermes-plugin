# ABOUTME: Verifies current permission policy around actual installed file and shell effects.
# ABOUTME: Uses disposable managed policy and trusted project roots without replacing permission decisions.
import json
import logging
import os
from pathlib import Path
import shlex
import sys

from hermes_cli import plugins
from model_tools import handle_function_call
from tools.terminal_tool import cleanup_all_environments, set_approval_callback


def main():
    home = Path.home()
    profile = Path(os.environ['HERMES_HOME'])
    settings = Path(os.environ['LIFEOS_HOOK_SETTINGS'])
    settings.parent.mkdir(parents=True)
    policy = home / 'policy'
    policy.mkdir()
    project = home / 'project'
    (project / '.git').mkdir(parents=True)
    (project / '.claude').mkdir()
    target = project / 'target.txt'
    rule = 'Edit(//' + str(target).lstrip('/') + ')'
    approval_choice = "deny"
    callbacks = []
    records = []
    messages = []

    class Capture(logging.Handler):
        def emit(self, record):
            messages.append(record.getMessage())

    def configure(permissions, *, managed=None, project_rules=None, trusted=False):
        settings.write_text(json.dumps({'permissions': permissions, 'hooks': {}}))
        managed_path = policy / 'managed-settings.json'
        if managed is None:
            managed_path.unlink(missing_ok=True)
        else:
            managed_path.write_text(managed if isinstance(managed, str) else json.dumps(managed))
        (project / '.claude/settings.json').write_text(json.dumps({'permissions': project_rules or {}}))
        (profile / 'config.yaml').write_text(json.dumps({'plugins': {'enabled': ['lifeos-hook-bridge']},
            'approvals': {'mode': 'manual'}, 'terminal': {'env_type': 'local'},
            'skills': {'trusted_project_dirs': [str(project)] if trusted else []}}))
        plugins._reset_plugin_managers_for_tests()
        plugins.discover_plugins()
        # Bind the managed policy directory to this disposable process, preserving its actual reader.
        modules = [module for name, module in sys.modules.items() if name.endswith('.bridge')
                   and getattr(module, '__file__', '').endswith('/lifeos-hook-bridge/bridge.py')]
        assert len(modules) == 1, [(m.__name__, m.__file__) for m in modules]
        module = modules[0]
        module.POLICY_DIRECTORY = policy
        module.LOG.handlers = [Capture()]
        module.LOG.propagate = False

    def approve(command, description, **kwargs):
        callbacks.append({'command': command, 'description': description})
        return approval_choice

    set_approval_callback(approve)

    def write(identifier, admitted, reviewed=False):
        callbacks.clear()
        target.unlink(missing_ok=True)
        result = handle_function_call('write_file', {'path': str(target), 'content': 'APPLIED'},
            task_id='policy', session_id='policy-session', tool_call_id=identifier)
        assert target.exists() is admitted, (identifier, result, callbacks)
        assert bool(callbacks) is reviewed, (identifier, callbacks, result)
        records.append({'id': identifier, 'admitted': admitted, 'reviewed': reviewed,
                        'verified': True, 'result': result})

    try:
        configure({'ask': [rule]})
        approval_choice = 'once'
        write('reviewed-write-before-deny', True, True)
        approval_choice = 'deny'
        settings.write_text(json.dumps({'permissions': {'deny': [rule]}, 'hooks': {}}))
        write('denial-after-human-approval', False)
        configure({'allow': [rule]})
        write('initial-user-allow', True)
        # Change policy without restarting the plugin or changing the session.
        settings.write_text(json.dumps({'permissions': {'allow': [rule], 'deny': [rule]}, 'hooks': {}}))
        write('changed-user-deny-after-grant', False)
        configure({'allow': [rule]}, managed={'permissions': {'deny': [rule]}})
        write('managed-deny-over-user-allow', False)
        configure({'allow': [rule]}, managed={'allowManagedPermissionRulesOnly': True,
                                            'permissions': {'ask': [rule]}})
        write('managed-only-review', False, True)
        messages.clear()
        configure({'allow': [rule]}, managed='{')
        write('malformed-managed-review', False, True)
        assert any('managed permission policy could not be read' in message for message in messages), messages
        configure({'allow': [rule]}, project_rules={'deny': ['Edit(*)']})
        write('untrusted-project-deny-does-not-govern', True)
        configure({'allow': [rule]}, project_rules={'deny': ['Edit(*)']}, trusted=True)
        write('trusted-project-deny', False)

        marker = project / 'marker'
        touch = 'touch ' + shlex.quote(str(marker))
        commands = [
            ('compound', 'printf PAIR; ' + touch, 'Bash(' + touch + ')'),
            ('timeout', 'timeout 10 ' + touch, 'Bash(' + touch + ')'),
            ('environment', 'env PAIR=1 ' + touch, 'Bash(' + touch + ')'),
            ('redirect', 'printf PAIR > ' + shlex.quote(str(marker)),
             'Edit(//' + str(marker).lstrip('/') + ')'),
            ('directory', 'cd ' + shlex.quote(str(project)) + ' && printf PAIR > marker',
             'Edit(//' + str(marker).lstrip('/') + ')'),
        ]
        link = project / 'alias'
        link.symlink_to(marker)
        commands.append(('symlink', 'printf PAIR > ' + shlex.quote(str(link)),
                         'Edit(//' + str(marker).lstrip('/') + ')'))
        for identifier, command, deny in commands:
            configure({'allow': ['Bash(*)'], 'deny': [deny]})
            callbacks.clear()
            marker.unlink(missing_ok=True)
            result = handle_function_call('terminal', {'command': command, 'workdir': str(project), 'timeout': 10},
                task_id='policy-shell', session_id='policy-shell', tool_call_id=identifier)
            assert not marker.exists() and not callbacks, (identifier, result, callbacks)
            assert 'denied' in result.lower() or 'blocked' in result.lower(), (identifier, result)
            records.append({'id': identifier, 'admitted': False, 'reviewed': False,
                            'verified': True, 'command': command, 'result': result})
        (home / 'policy-results.json').write_text(json.dumps({'cases': records, 'captured_policy_warnings': messages}, indent=2) + '\n')
    finally:
        plugins.unload_plugins()
        set_approval_callback(None)
        cleanup_all_environments()


if __name__ == '__main__':
    main()
