# ABOUTME: Checks the exact executable closure selected for complete LifeOS removal.
# ABOUTME: Preserves reviewed commands and refuses later interpreter, dependency, and launcher edits.
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.release_programs import publish
from optional.lifeos_release_manager.release_stage import runtime_source_fingerprint,sha
from optional.lifeos_release_manager.removal_workflow import _stock


class RemovalRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.job=Path(self.directory.name);self.root=self.job/'stock-runtime';self.root.mkdir(mode=0o700)
        for name in ('hermes/main.py','bin/hermes','bin/hermes-agent','bin/hermes-acp',
                'python-environment/lib/site-packages/synthetic.py','dependency-profile/tools/python/bin/python3',
                'pm-runtime/pm/__main__.py','enabled-features.json','manifest.json','runtime.json'):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            publish(path,b'Synthetic stock runtime artifact\n',0o700)
        target=self.root/'dependency-profile/tools/python/bin/python3'
        (self.root/'python-environment/bin').mkdir()
        (self.root/'python-environment/bin/python').symlink_to(target)
        self.runtime={'python':str(self.root/'python-environment/bin/python'),'source':str(self.root/'hermes'),
            'hermes':str(self.root/'bin/hermes'),'integration':False}

    def plan(self):
        from optional.lifeos_release_manager.removal_runtime import identity
        return {'stock_runtime':self.runtime,'stock_runtime_source':runtime_source_fingerprint(self.root/'hermes'),
            'stock_runtime_manifest_sha256':sha(self.root/'manifest.json'),'stock_runtime_execution':identity(self.root)}

    def test_later_executable_artifact_edits_refuse(self):
        for name in ('bin/hermes','bin/hermes-agent','bin/hermes-acp',
                'python-environment/lib/site-packages/synthetic.py','dependency-profile/tools/python/bin/python3',
                'pm-runtime/pm/__main__.py','enabled-features.json'):
            with self.subTest(name=name):
                plan=self.plan();self.assertEqual(_stock(self.job,plan),self.runtime)
                path=self.root/name;original=path.read_bytes();publish(path,b'Synthetic later edit\n',0o700)
                try:
                    with self.assertRaises(ValueError):_stock(self.job,plan)
                finally:publish(path,original,0o700)

    def test_interpreter_link_cannot_leave_reviewed_runtime(self):
        plan=self.plan();path=self.root/'python-environment/bin/python';path.unlink();path.symlink_to('/usr/bin/python3')
        with self.assertRaises(ValueError):_stock(self.job,plan)

    def test_bytecode_does_not_change_executable_review(self):
        plan=self.plan();publish(self.root/'python-environment/lib/site-packages/synthetic.pyc',b'Synthetic cache')
        publish(self.root/'python-environment/.lock',b'',0o666)
        self.assertEqual(_stock(self.job,plan),self.runtime)
