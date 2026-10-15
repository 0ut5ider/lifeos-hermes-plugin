# ABOUTME: Exercises exact removal of verified native software with retained user data.
# ABOUTME: Tests changed programs, additional plugins, linked paths, and current hook preservation.
import json
import os
from pathlib import Path
import tempfile
import unittest


class RemovalInventoryTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        from optional.lifeos_release_manager.release_stage import load_bridge
        self.bridge=load_bridge(Path(__file__).resolve().parents[1]/'lifeos_hook_bridge')
        self.home=Path(self.directory.name);self.installed=self.home/'.claude'
        self.source=self.home/'source';self.reference=self.home/'reference'
        for root in (self.installed,self.source,self.reference):
            for name,data in {'hooks/Tool.hook.ts':'// Synthetic hook\n','skills/Test/SKILL.md':'# Synthetic skill\n',
                              'LIFEOS/TOOLS/Tool.ts':'// Synthetic tool\n','LIFEOS/VERSION':'1.2.3\n',
                              'CLAUDE.md':'# Synthetic native instructions\n'}.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
        for root in (self.installed,self.reference):
            for name,data in {'package.json':'{"name":"synthetic-test"}\n','bun.lock':'{}\n',
                              'node_modules/package/index.js':'// Synthetic dependency\n'}.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
            (root/'node_modules/.bin').mkdir();(root/'node_modules/.bin/synthetic').symlink_to('../package/index.js')
        (self.source/'package.json').write_text('{"name":"synthetic-test"}\n')
        hooks={'SessionStart':[{'hooks':[{'type':'command','command':'bun ~/.claude/hooks/Tool.hook.ts'}]}]}
        (self.source/'hooks/hooks.json').write_text(json.dumps({'hooks':hooks}))
        settings={'hooks':hooks,'custom':'keep'}
        settings['hooks']['SessionEnd']=[{'hooks':[{'type':'command','command':'echo synthetic-foreign'}]}]
        (self.installed/'settings.json').write_text(json.dumps(settings));(self.installed/'settings.json').chmod(0o600)
        data=self.home/'.config/LIFEOS/USER';data.mkdir(parents=True)
        (data/'fact.txt').write_text('Synthetic retained data.');(self.installed/'LIFEOS/USER').symlink_to(data)
        (self.installed/'LIFEOS/MEMORY').symlink_to(data)

    def operation(self):
        from optional.lifeos_release_manager import removal_inventory
        return removal_inventory

    def test_native_plan_removes_qualified_programs_and_keeps_foreign_hooks_and_data(self):
        from optional.lifeos_release_manager.release_programs import ProgramTransaction,publish
        plan=self.operation().native(self.installed,self.source,self.reference,bridge=self.bridge)
        self.assertIn(self.installed/'hooks/Tool.hook.ts',plan['files'])
        self.assertIn(self.installed/'CLAUDE.md',plan['files'])
        self.assertEqual(plan['dependencies'],{self.installed/'node_modules':None})
        self.assertTrue(all('USER' not in path.parts and 'MEMORY' not in path.parts for path in plan['files']))
        generated=self.home/'generated';generated.mkdir(mode=0o700)
        settings=generated/'settings.json';publish(settings,plan['settings'])
        tx=ProgramTransaction(self.home/'transaction');tx.prepare(directories={},
            files={**plan['files'],self.installed/'settings.json':settings},dependencies=plan['dependencies'])
        tx.apply()
        self.assertFalse((self.installed/'hooks/Tool.hook.ts').exists())
        self.assertFalse((self.installed/'node_modules').exists())
        self.assertEqual((self.installed/'LIFEOS/USER/fact.txt').read_text(),'Synthetic retained data.')
        self.assertEqual(json.loads((self.installed/'settings.json').read_text()),{
            'hooks':{'SessionEnd':[{'hooks':[{'type':'command','command':'echo synthetic-foreign'}]}]},'custom':'keep'})
        tx.restore();self.assertTrue((self.installed/'hooks/Tool.hook.ts').exists())
        self.assertEqual((self.installed/'LIFEOS/USER/fact.txt').read_text(),'Synthetic retained data.')

    def test_edited_program_or_dependency_refuses_before_plan(self):
        for name in ('hooks/Tool.hook.ts','node_modules/package/index.js','CLAUDE.md'):
            path=self.installed/name;before=path.read_bytes();path.write_bytes(before+b'// Later edit\n')
            with self.subTest(name=name),self.assertRaises(ValueError):self.operation().native(self.installed,self.source,self.reference,bridge=self.bridge)
            self.assertTrue(path.read_bytes().endswith(b'// Later edit\n'));path.write_bytes(before)

    def test_unreviewed_hook_and_linked_source_refuse(self):
        path=self.installed/'hooks/Custom.hook.ts';path.write_text('// Owner program\n')
        with self.assertRaises(ValueError):self.operation().native(self.installed,self.source,self.reference,bridge=self.bridge)
        path.unlink();path.symlink_to(self.installed/'hooks/Tool.hook.ts')
        with self.assertRaises(ValueError):self.operation().native(self.installed,self.source,self.reference,bridge=self.bridge)

    def test_plugin_directory_requires_exact_current_manifest(self):
        root=self.home/'plugin';root.mkdir();(root/'__init__.py').write_text('# Synthetic plugin\n')
        import hashlib
        files={'__init__.py':hashlib.sha256((root/'__init__.py').read_bytes()).hexdigest()}
        self.operation().plugin(root,files)
        (root/'extra.py').write_text('# Unreviewed extension\n')
        with self.assertRaises(ValueError):self.operation().plugin(root,files)
