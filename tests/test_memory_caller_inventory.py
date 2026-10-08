# ABOUTME: Checks that a source inventory describes current program bytes and source lines.
# ABOUTME: Detects USER-only callers and refuses historical paths absent from the current tree.
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / 'docs/verification/2026-10-08-memory-caller-current/trace_callers.py'
spec = importlib.util.spec_from_file_location('caller_inventory', SCRIPT)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class MemoryCallerInventoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='lifeos-source-inventory-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'source'
        self.output = Path(temporary.name) / 'evidence'
        self.root.mkdir()
        self.output.mkdir()
        for name in ('settings.system.json', 'settings.enhancements.json', 'hooks/hooks.json'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"hooks": {}}')
        (self.output / 'manual-entrypoints.json').write_text('{"roots": []}')
        self.seed = self.output / 'source-traces.json'
        self.seed.write_text('[]')

    def scan(self):
        inventory.capture(self.root, self.output)
        return json.loads((self.output / 'caller-inventory.json').read_text())

    def test_user_only_program_is_discovered_without_reading_user_records(self):
        (self.root / 'brief.ts').write_text('const path = "LIFEOS/USER/TELOS/GOALS.md";\n')
        private = self.root / 'LIFEOS/USER/TELOS/GOALS.md'
        private.parent.mkdir(parents=True)
        private.write_text('PRIVATE RECORD MUST NOT ENTER INVENTORY')
        rows = self.scan()
        self.assertEqual([row['path'] for row in rows], ['brief.ts'])
        self.assertNotIn('PRIVATE RECORD MUST NOT ENTER INVENTORY', json.dumps(rows))

    def test_seed_lines_are_replaced_by_current_source_evidence(self):
        current = 'const path = "LIFEOS/USER/TELOS/GOALS.md";\n'
        (self.root / 'brief.ts').write_text(current)
        self.seed.write_text(json.dumps([{'path': 'brief.ts', 'sha256': 'historical',
            'source_evidence': [{'line': 99, 'text': 'HISTORICAL SOURCE LINE'}]}]))
        rows = self.scan()
        self.assertEqual(rows[0]['sha256'], rows[0]['source_sha256'])
        self.assertEqual(rows[0]['source_evidence'], [{'line': 1, 'text': current.strip()}])
        self.assertNotIn('HISTORICAL SOURCE LINE', json.dumps(rows))

    def test_missing_seed_source_refuses_instead_of_hashing_empty_text(self):
        self.seed.write_text(json.dumps([{'path': 'missing.ts', 'sha256': 'historical'}]))
        with self.assertRaisesRegex(ValueError, 'missing.ts'):
            self.scan()


if __name__ == '__main__':
    unittest.main()
