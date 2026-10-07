# ABOUTME: Checks native source aliases against an actual competing SQLite writer.
# ABOUTME: Verifies source refusal preserves the registry transaction lock before file reads.
import json
import os
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_sources import _source_path, read_markdown, source_projection
import test_memory_native as native_fixture


class MemorySourceRegistryAliasTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.saved = self.fixture.remember('Synthetic source registry guard', 'source-alias')
        self.memory = self.fixture.memory

    def probe(self):
        program = '''import json,sqlite3,sys
connection=sqlite3.connect(sys.argv[1],timeout=0)
try:
    connection.execute('BEGIN IMMEDIATE')
    connection.rollback()
    result={'state':'acquired'}
except sqlite3.OperationalError as error:
    result={'state':'blocked','message':str(error)}
finally:
    connection.close()
print(json.dumps(result))
'''
        result = subprocess.run([sys.executable, '-c', program, str(self.memory.database)],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_markdown_registry_alias_refusal_preserves_the_open_sqlite_lock(self):
        paths = ['LIFEOS/USER/TELOS/CURRENT_STATE/HEALTH.md',
                 'LIFEOS/MEMORY/WORK/synthetic-source/ISA.md',
                 'LIFEOS/DOCUMENTATION/synthetic-source.md']
        for relative in paths:
            with self.subTest(relative=relative):
                path = self.memory.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                os.link(self.memory.database, path)
                with self.memory._transaction() as connection:
                    before = self.probe()
                    self.assertEqual(before['state'], 'blocked', before)
                    with self.assertRaises(MemoryUnavailable) as refused:
                        read_markdown(self.memory, native_fixture.OWNER, [str(path)], connection=connection)
                    after = self.probe()
                    self.assertEqual(after['state'], 'blocked', {'path': relative,
                        'before': before, 'after': after, 'refusal': str(refused.exception)})
                self.assertEqual(self.probe()['state'], 'acquired')
                path.unlink()

    def test_other_source_interfaces_preserve_the_registry_lock(self):
        cases = [
            ('path-check', 'LIFEOS/USER/TELOS/TELOS.md',
             lambda path: _source_path(self.memory, native_fixture.OWNER, str(path))),
            ('diagnostic', 'LIFEOS/MEMORY/OBSERVABILITY/reviewer-runs.jsonl',
             lambda path: _source_path(self.memory, native_fixture.OWNER, str(path), diagnostic=True)),
            ('fact-projection', 'LIFEOS/MEMORY/KNOWLEDGE/Research/synthetic.md',
             lambda path: source_projection(self.memory, path.relative_to(self.memory.root).as_posix(),
                                           'Synthetic unchanged content')),
        ]
        for operation, relative, call in cases:
            with self.subTest(operation=operation):
                path = self.memory.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                os.link(self.memory.database, path)
                with self.memory._transaction():
                    self.assertEqual(self.probe()['state'], 'blocked')
                    try:
                        call(path)
                    except (MemoryUnavailable, UnicodeError) as error:
                        refusal = error
                    else:
                        refusal = None
                    after = self.probe()
                    self.assertEqual(after['state'], 'blocked', {'operation': operation,
                        'after': after, 'refusal': str(refusal)})
                    self.assertIsInstance(refusal, MemoryUnavailable)
                self.assertEqual(self.probe()['state'], 'acquired')
                path.unlink()
