# ABOUTME: Verifies post-hook dependencies with actual child processes and shared files.
# ABOUTME: Preserves independent concurrency and configured context order.
import json
from pathlib import Path
import shlex
import sys
import tempfile
import unittest

from lifeos_hook_bridge.bridge import HookBridge


class PostHookOrderTests(unittest.TestCase):
    def test_view_runs_after_sync_while_output_keeps_configured_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hooks = root / 'hooks'
            hooks.mkdir()
            value = root / 'value'
            value.write_text('submitted')
            sync = hooks / 'ISASync.hook.ts'
            view = hooks / 'ISAStaleWriteGuard.hook.ts'
            sync.write_text('#!' + sys.executable + '\nimport json,time\nfrom pathlib import Path\n'
                           'time.sleep(.1)\n' + f'Path({str(value)!r}).write_text("final")\n'
                           'print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"sync"}}))\n')
            view.write_text('#!' + sys.executable + '\nimport json\nfrom pathlib import Path\n'
                           'print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse",'
                           f'"additionalContext":Path({str(value)!r}).read_text()}}}}))\n')
            for path in (sync, view):
                path.chmod(0o755)
            settings = root / 'settings.json'
            settings.write_text(json.dumps({'hooks': {'PostToolUse': [{'hooks': [
                {'type': 'command', 'command': shlex.quote(str(view))},
                {'type': 'command', 'command': shlex.quote(str(sync))}]}]}}))
            bridge = HookBridge(settings, root)
            try:
                context = bridge.post_tool_call('write_file', {'path': str(value), 'content': 'submitted'}, '{}', session_id='order')
                self.assertEqual(context, 'final\n\nsync')
            finally:
                bridge.close()

    def test_independent_hooks_run_concurrently_and_keep_context_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commands = []
            for index in range(2):
                script = root / ('worker-' + str(index) + '.py')
                marker = root / ('ready-' + str(index))
                other = root / ('ready-' + str(1 - index))
                script.write_text('import json,time\nfrom pathlib import Path\n'
                    + f'Path({str(marker)!r}).touch()\n'
                    + 'deadline=time.monotonic()+2\n'
                    + f'while not Path({str(other)!r}).exists() and time.monotonic()<deadline: time.sleep(.01)\n'
                    + f'assert Path({str(other)!r}).exists(), "independent hook did not run"\n'
                    + 'print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse",'
                    + f'"additionalContext":"worker-{index}"}}}}))\n')
                commands.append(shlex.quote(sys.executable) + ' ' + shlex.quote(str(script)))
            settings = root / 'settings.json'
            settings.write_text(json.dumps({'hooks': {'PostToolUse': [{'hooks': [
                {'type': 'command', 'command': command} for command in commands]}]}}))
            bridge = HookBridge(settings, root)
            try:
                self.assertEqual(bridge.post_tool_call('terminal', {'command': 'true'}, '{}', session_id='parallel'),
                                 'worker-0\n\nworker-1')
            finally:
                bridge.close()
