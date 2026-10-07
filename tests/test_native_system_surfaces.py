# ABOUTME: Checks the native system-line renderer with observed file details.
# ABOUTME: Preserves grouping, limits, and prior detail when a later entry has none.
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Native system surfaces and Bun are required')
class NativeSystemSurfaceTests(unittest.TestCase):
    def render(self, entries):
        program = 'import {renderSystemLine} from ' + json.dumps(str(Path(SOURCE) / 'hooks/lib/system-surfaces.ts')) + '; console.log(JSON.stringify(renderSystemLine(JSON.parse(process.env.PAIR_ENTRIES!))));'
        result = subprocess.run(['bun', '-e', program], env={**os.environ, 'PAIR_ENTRIES': json.dumps(entries)},
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_no_changes_returns_no_line(self):
        self.assertIsNone(self.render([]))

    def test_latest_observed_detail_replaces_the_first_detail(self):
        self.assertEqual(self.render([{'tier': 'isa', 'label': 'fixture', 'detail': '0 closed'},
                                      {'tier': 'isa', 'label': 'fixture', 'detail': '0→1'},
                                      {'tier': 'isa', 'label': 'fixture', 'detail': '0→2'}]),
                         '⚙️ SYSTEM: ISA fixture 0→2')

    def test_entry_without_detail_keeps_prior_observation(self):
        self.assertEqual(self.render([{'tier': 'isa', 'label': 'fixture', 'detail': '0→1'},
                                      {'tier': 'isa', 'label': 'fixture'}]), '⚙️ SYSTEM: ISA fixture 0→1')

    def test_group_order_deduplication_and_six_item_limit(self):
        entries = [{'tier': 'machinery', 'label': str(i)} for i in range(7)]
        entries += [{'tier': 'identity', 'label': 'OWNER'}, {'tier': 'doctrine', 'label': 'RULES'}, {'tier': 'isa', 'label': 'fixture'}]
        value = self.render(entries)
        self.assertTrue(value.startswith('⚙️ SYSTEM: ISA fixture · RULES · OWNER'), value)
        self.assertIn('+4', value)
