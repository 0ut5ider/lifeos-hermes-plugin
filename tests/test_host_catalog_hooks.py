# ABOUTME: Checks result delivery from real Hermes catalog tools to installed LifeOS hooks.
# ABOUTME: Runs the host dispatcher and child hooks in a separate disposable profile.
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = os.environ.get('LIFEOS_HERMES_SOURCE')


@unittest.skipUnless(SOURCE, 'prepared Hermes source is required')
class HostCatalogHookTests(unittest.TestCase):
    def test_catalog_result_reaches_hook_and_context_returns_to_caller(self):
        with tempfile.TemporaryDirectory(prefix='catalog-hook-') as directory:
            home = Path(directory)
            profile = home / '.hermes'
            profile.mkdir()
            package = Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge'
            shutil.copytree(package, profile / 'plugins/lifeos-hook-bridge',
                            ignore=shutil.ignore_patterns('__pycache__'))
            (profile / 'config.yaml').write_text(json.dumps({
                'plugins': {'enabled': ['lifeos-hook-bridge']},
                'tools': {'tool_search': {'enabled': 'on'}},
            }))
            native = home / '.claude'
            native.mkdir()
            marker = home / 'events.jsonl'
            child = home / 'observe.py'
            child.write_text(
                '# ABOUTME: Records catalog hook input from the real host dispatcher.\n'
                '# ABOUTME: Returns a synthetic context marker to verify delivery.\n'
                'import json,sys\nfrom pathlib import Path\n'
                f'with Path({str(marker)!r}).open("a") as out: out.write(json.dumps(json.load(sys.stdin))+"\\n")\n'
                'print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"CATALOG_HOOK_CONTEXT"}}))\n'
            )
            (native / 'settings.json').write_text(json.dumps({'hooks': {'PostToolUse': [{
                'matcher': 'ToolSearch', 'hooks': [{
                    'type': 'command', 'command': f'{sys.executable} {child}',
                }],
            }]}}))
            driver = home / 'dispatch.py'
            driver.write_text(
                '# ABOUTME: Calls the real catalog dispatcher with an enabled LifeOS plugin.\n'
                '# ABOUTME: Saves the caller-visible result from one bounded search.\n'
                'import json,sys\nfrom pathlib import Path\n'
                f'sys.path.insert(0,{SOURCE!r})\n'
                'import hermes_bootstrap\n'
                'from model_tools import handle_function_call\n'
                'result=handle_function_call("tool_search",{"queries":["todo"]},'
                'enabled_toolsets=["todo"],session_id="catalog-hook",tool_call_id="search-one")\n'
                f'Path({str(home / "result.json")!r}).write_text(json.dumps({{"result":result}}))\n'
            )
            environment = {key: value for key, value in os.environ.items()
                           if key in ('PATH', 'LANG', 'TZ')}
            environment.update(HOME=str(home), HERMES_HOME=str(profile),
                               LIFEOS_HOOK_SETTINGS=str(native / 'settings.json'),
                               PYTHONDONTWRITEBYTECODE='1')
            process = subprocess.run([sys.executable, str(driver)], cwd=home,
                                     env=environment, text=True, capture_output=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertTrue(marker.exists(), 'ToolSearch did not reach its PostToolUse hook')
            rows = [json.loads(line) for line in marker.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['tool_name'], 'ToolSearch')
            self.assertEqual(rows[0]['tool_input']['queries'], ['todo'])
            self.assertIn('todo_list', rows[0]['tool_response']['tools'])
            result = json.loads((home / 'result.json').read_text())['result']
            self.assertIn('CATALOG_HOOK_CONTEXT', result)
