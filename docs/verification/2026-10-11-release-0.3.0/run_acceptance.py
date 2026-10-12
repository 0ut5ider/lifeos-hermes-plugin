# ABOUTME: Runs combined integration acceptance against a sealed release package.
# ABOUTME: Retains exact source hashes, commands, raw output, and completion markers.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

parser=argparse.ArgumentParser()
parser.add_argument('package',type=Path)
parser.add_argument('--label',default='combined-final')
parser.add_argument('--modules',nargs='+')
args=parser.parse_args()
repo=Path(__file__).resolve().parents[3];out=Path(__file__).parent
package=args.package.resolve();manifest=json.loads((package/'DAILY-CANDIDATE.json').read_text())
sys_version=manifest['version']
assert sys_version.startswith('0.3.')
assert all(hashlib.sha256((package/name).read_bytes()).hexdigest()==digest for name,digest in manifest['plugin_files'].items())
previous=json.loads((repo/'docs/verification/2026-10-10-daily-text-release/combined-final.json').read_text())
names=args.modules or previous['command'][6:]+['test_memory_atlas_retention','test_release_version',
    'test_footprint_contracts','test_daily_morning_delivery','test_plugin_lifecycle','test_memory_life_source_review']
native=Path('/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install')
environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',
    PYTHONPATH=str(package)+':'+str(package/'tests')+':'+str(package/'hermes'),
    LIFEOS_HERMES_SOURCE=str(package/'hermes'),LIFEOS_MEMORY_SOURCE=str(native),
    LIFEOS_TASK_HOOK_PATH=str(native/'hooks/TaskGovernance.hook.ts'),
    LIFEOS_FRESH_SOURCE=str(package/'lifeos'),LIFEOS_TAB_STATE_SOURCE=str(native),
    LIFEOS_HARVEST_CONTROL_SOURCE='/home/outsider/.cache/lifeos-plugin-memory/source/LifeOS/install')
command=['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python',
    '-W','error::ResourceWarning','-m','unittest','-v',*names]
started=time.monotonic()
with (out/(args.label+'.stdout')).open('w') as stdout,(out/(args.label+'.stderr')).open('w') as stderr:
    result=subprocess.run(command,cwd=package,env=environment,stdout=stdout,stderr=stderr,timeout=7200)
unchanged=all(hashlib.sha256((package/name).read_bytes()).hexdigest()==digest for name,digest in manifest['plugin_files'].items())
report={'version':manifest['version'],'head':manifest['head'],'package':str(package),
    'command':command,'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-started,
    'source_hashes':manifest['plugin_files'],'source_hashes_unchanged':unchanged,
    'native_fixture':str(native),'scope':'Sealed package with synthetic native, HTTP, SDK, and subprocess fixtures'}
(out/(args.label+'.json')).write_text(json.dumps(report,indent=2)+'\n')
(out/(args.label+'.done')).write_text(str(result.returncode if unchanged else 1)+'\n')
