# ABOUTME: Stages the private committed checkpoint on the disposable installed guest for browser qualification.
# ABOUTME: Uses actual archive assets and labels the operation as a nonproduction fixture, without a public GitHub claim.
import hashlib
import argparse
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import types

os.umask(0o077);sys.dont_write_bytecode=True
parser=argparse.ArgumentParser()
parser.add_argument('--checkpoint',required=True)
parser.add_argument('--previous',required=True)
arguments=parser.parse_args()
if (len(arguments.checkpoint)!=40 or len(arguments.previous)!=32
        or any(character not in '0123456789abcdef' for character in arguments.checkpoint+arguments.previous)):
    raise ValueError('Use exact checkpoint and previous operation identifiers')
home=Path('/home/lifeos-hermes');profile=home/'.hermes'
inputs=home/'install-input'/('removal-'+arguments.checkpoint[:8])
build=json.loads((inputs/('0.5.0-'+arguments.checkpoint[:8]+'-build.json')).read_bytes())
assert build['head']==arguments.checkpoint
assert not build['combined_release_verified'] and not build['live_selection_changed']
previous=profile/'.lifeos-releases'/arguments.previous
assert json.loads((previous/'status.json').read_bytes())['state']=='applied'
request=json.loads((previous/'request.json').read_bytes())
sys.path.insert(0,request['runtime']['source'])
namespace=types.ModuleType('portability_checkpoint_manager');namespace.__path__=[str(profile/'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__]=namespace
commands=importlib.import_module(namespace.__name__+'.cli')
archive=inputs/Path(build['archive']).name
assert archive.stat().st_size==build['archive_bytes']
with archive.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==build['archive_sha256']
dashboard=previous/'download/hermes-dashboard.tgz'
certificate={**build,'format':1,'status':'QUALIFIED','program_commit':build['head'],
    'production_qualified':False,'test_fixture_only':True,
    'hermes_dashboard_sha256':hashlib.sha256(dashboard.read_bytes()).hexdigest()}


class CheckpointAssets:
    def download(self,directory,version):
        assert version==build['version']
        directory.mkdir(mode=0o700)
        for source in (archive,dashboard):shutil.copy2(source,directory/source.name)
        return {'archive':str(directory/archive.name),'dashboard':str(directory/dashboard.name),'certificate':certificate}


report={'checkpoint':build['head'],'version':build['version'],'test_fixture_only':True,'production_qualified':False,
    'public_github_installation_replayed':False,'daily_changed':False,'status':'FAIL'}
started=time.monotonic()
try:
    result=commands.prepare(profile,build['version'],catalog=CheckpointAssets(),intent='update')
    assert result['state']=='ready'
    report.update(status='PASS',operation=result['identifier'],prepared_before_live_change=True)
except Exception as error:
    report['error_type']=type(error).__name__
    raise
finally:
    report['elapsed_seconds']=time.monotonic()-started
    (inputs/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    (inputs/'preparation.done').write_text('0\n' if report['status']=='PASS' else '1\n')
