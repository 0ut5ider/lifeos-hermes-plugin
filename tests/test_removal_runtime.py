# ABOUTME: Checks the exact executable closure selected for complete LifeOS removal.
# ABOUTME: Preserves reviewed commands and refuses later interpreter, dependency, and launcher edits.
from pathlib import Path
import json
import os
import subprocess
import sys
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

    def test_contained_links_must_target_hashed_execution_components(self):
        for name in ('tools/private-python','hermes/.hermes/private-python','python-environment/.lock'):
            with self.subTest(name=name):
                target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                publish(target,b'#!/bin/sh\nexit 94\n',0o700)
                path=self.root/'python-environment/bin/python';path.unlink();path.symlink_to(target)
                with self.assertRaises(ValueError):self.plan()

    def test_directory_link_cannot_hide_unbound_executable_files(self):
        target=self.root/'hermes/.hermes/unbound';target.mkdir(parents=True)
        publish(target/'synthetic.py',b'Synthetic unbound executable')
        (self.root/'python-environment/lib/hidden').symlink_to(target,target_is_directory=True)
        with self.assertRaises(ValueError):self.plan()

    def test_later_bytecode_changes_executable_review(self):
        plan=self.plan();publish(self.root/'python-environment/lib/site-packages/synthetic.pyc',b'Synthetic cache')
        with self.assertRaises(ValueError):_stock(self.job,plan)

    def test_non_executable_environment_lock_does_not_change_review(self):
        plan=self.plan()
        publish(self.root/'python-environment/.lock',b'',0o666)
        self.assertEqual(_stock(self.job,plan),self.runtime)

    def test_stock_child_ignores_adjacent_cache_and_writes_no_cache(self):
        import importlib.util
        import importlib._bootstrap_external
        from optional.lifeos_release_manager.removal_runtime import command
        source=self.root/'hermes/synthetic.py';source.write_text("VALUE='reviewed-source'\n")
        cache=Path(importlib.util.cache_from_source(str(source)));cache.parent.mkdir(mode=0o700)
        metadata=source.stat()
        cache.write_bytes(importlib._bootstrap_external._code_to_timestamp_pyc(
            compile("VALUE='unreviewed-cache'\n",str(source),'exec'),
            mtime=int(metadata.st_mtime),source_size=metadata.st_size))
        run=[sys.executable,'-I','-c','import json,sys;sys.path.insert(0,sys.argv[1]);import synthetic;print(json.dumps(synthetic.VALUE))',str(source.parent)]
        result=subprocess.run(command(run,self.runtime),capture_output=True,text=True,timeout=15,
            env=dict(os.environ,PYTHONPYCACHEPREFIX=str(cache.parent)))
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,'')
        self.assertEqual(json.loads(result.stdout),'reviewed-source')
        self.assertFalse((self.root/'bytecode').exists())
