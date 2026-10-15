# ABOUTME: Verifies authenticated unpatched Hermes archives for complete integration removal.
# ABOUTME: Exercises real archive extraction, changed bytes, source edits, and pinned Git archive creation.
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
import tarfile
import tempfile
import unittest


class StockHermesTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.archive=self.root/'stock-hermes.tgz'
        with tarfile.open(self.archive,'w:gz') as archive:
            for name,data in [('run_agent.py',b'# Synthetic stock program\n'),('pyproject.toml',b'# Synthetic project\n')]:
                member=tarfile.TarInfo(name);member.mode=0o644;member.size=len(data)
                archive.addfile(member,io.BytesIO(data))
        self.archive.chmod(0o600)
        self.identity={'format':1,'commit':'a'*40,'path':'stock-hermes.tgz',
            'sha256':hashlib.sha256(self.archive.read_bytes()).hexdigest(),'bytes':self.archive.stat().st_size}

    def module(self):
        from optional.lifeos_release_manager import stock_hermes
        return stock_hermes

    def test_verified_stock_source_refuses_a_later_source_edit(self):
        target=self.root/'stock'
        record=self.module().prepare_source(self.archive,target,self.identity)
        self.assertEqual(record['commit'],'a'*40)
        self.assertEqual(record['patches'],0)
        self.assertEqual(self.module().verify_source(target,record),record)
        (target/'run_agent.py').write_text('# Synthetic later edit\n')
        with self.assertRaises(ValueError):self.module().verify_source(target,record)

    def test_changed_archive_and_symlink_refuse_before_destination_creation(self):
        self.archive.write_bytes(self.archive.read_bytes()+b'changed')
        with self.assertRaises(ValueError):self.module().prepare_source(self.archive,self.root/'changed',self.identity)
        self.assertFalse((self.root/'changed').exists())
        linked=self.root/'linked.tgz';linked.symlink_to(self.archive)
        with self.assertRaises(ValueError):self.module().prepare_source(linked,self.root/'linked',self.identity)
        self.assertFalse((self.root/'linked').exists())

    def test_git_archive_selects_the_exact_pinned_stock_commit(self):
        source=Path('/home/outsider/.cache/lifeos-daily-promotion-20261014/upstream-hermes')
        self.assertTrue((source/'.git').exists(),'The qualified upstream Git fixture is required')
        commit='71d34bad1045610252eda02ee79549436896e784'
        archive=self.root/'pinned.tgz'
        identity=self.module().build_archive(source,archive,commit)
        self.assertEqual(identity['commit'],commit)
        self.assertEqual(identity['path'],'stock-hermes.tgz')
        with tarfile.open(archive) as contents:
            names=contents.getnames()
            self.assertIn('run_agent.py',names)
            self.assertNotIn('hermes-source-manifest.json',names)
            self.assertNotIn('.git',names)

    def test_fifo_archive_refuses_without_waiting_for_a_writer(self):
        path=self.root/'fifo.tgz';os.mkfifo(path,0o600)
        code='import json,sys\nfrom pathlib import Path\nfrom optional.lifeos_release_manager.stock_hermes import prepare_source\ntry: prepare_source(Path(sys.argv[1]),Path(sys.argv[2]),json.loads(sys.argv[3]))\nexcept ValueError: raise SystemExit(0)\nraise SystemExit(1)\n'
        result=subprocess.run([sys.executable,'-B','-c',code,str(path),str(self.root/'fifo'),json.dumps(self.identity)],
            text=True,capture_output=True,timeout=3)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(result.stdout+result.stderr,'')
        self.assertFalse((self.root/'fifo').exists())
