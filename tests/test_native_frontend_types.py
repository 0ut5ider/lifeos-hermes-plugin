# ABOUTME: Checks native dashboard types and preserves the rendered subordinate tabs.
# ABOUTME: Exercises the configuration CLI and import with actual Bun in a disposable home.

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SOURCE = os.environ.get('LIFEOS_MEMORY_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared LifeOS and Bun are required')
class NativeFrontendTypeTests(unittest.TestCase):
    def setUp(self):
        self.source = Path(SOURCE)
        self.dashboard = self.source / 'LIFEOS/PULSE/Observability'
        self.config = self.source / 'LIFEOS/TOOLS/LifeosConfig.ts'
        self.temporary = tempfile.TemporaryDirectory(prefix='native-frontend-types-')
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        config = self.home / '.claude/LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml'
        config.parent.mkdir(parents=True)
        config.write_text('[principal]\nname="Synthetic Owner"\ntimezone="UTC"\n'
                          '[da]\nname="Synthetic Assistant"\n'
                          '[da.voices.main]\nvoice_id="synthetic"\n')
        self.environment = {**os.environ, 'HOME': str(self.home)}
        self.environment.pop('LIFEOS_CONFIG_PATH', None)

    def run_bun(self, *arguments, cwd=None):
        result = subprocess.run(['bun', *map(str, arguments)], cwd=cwd,
                                env=self.environment, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stderr, '')
        return result.stdout

    def test_subordinate_tabs_ignore_unused_callback(self):
        (self.home / 'node_modules').symlink_to(self.dashboard / 'node_modules', target_is_directory=True)
        component = self.dashboard / 'src/app/telos/_v7/subtabs.tsx'
        data = component.parent / 'data.ts'
        entry = self.home / 'render.ts'
        entry.write_text('import {createElement} from "react";\n'
                         'import {renderToStaticMarkup} from "react-dom/server";\n'
                         f'import {{SubTabs}} from {json.dumps(str(component))};\n'
                         f'import {{TELOS}} from {json.dumps(str(data))};\n'
                         'let calls=0;\n'
                         'const extra={telos:TELOS,openFile:()=>{calls++;}};\n'
                         'console.log(JSON.stringify({\n'
                         'plain:renderToStaticMarkup(createElement(SubTabs,{telos:TELOS})),\n'
                         'extra:renderToStaticMarkup(createElement(SubTabs,extra)),calls}));\n')
        rendered = json.loads(self.run_bun(entry))
        self.assertEqual(rendered['plain'], rendered['extra'])
        self.assertEqual(rendered['calls'], 0)
        self.assertIn('The corners of life', rendered['plain'])
        self.assertIn('class="sub-card"', rendered['plain'])
        print('SubTabs markup SHA256:', hashlib.sha256(rendered['plain'].encode()).hexdigest())

    def test_configuration_cli_emits_native_normalized_config(self):
        config = json.loads(self.run_bun(self.config))
        self.assertEqual(config['principal'], {'name': 'Synthetic Owner', 'timezone': 'UTC'})
        self.assertEqual(config['da']['name'], 'Synthetic Assistant')
        self.assertEqual(config['paths']['userDir'], str(self.home / '.claude/LIFEOS/USER'))

    def test_configuration_import_does_not_run_cli(self):
        entry = self.home / 'import.ts'
        entry.write_text(f'import {{loadLifeosConfig}} from {json.dumps(str(self.config))};\n'
                         'console.log(loadLifeosConfig().principal.name);\n')
        self.assertEqual(self.run_bun(entry), 'Synthetic Owner\n')

    def test_dashboard_strict_typecheck_passes(self):
        self.run_bun(self.dashboard / 'node_modules/typescript/bin/tsc', '--noEmit',
                     '--incremental', 'false', '--pretty', 'false', cwd=self.dashboard)
