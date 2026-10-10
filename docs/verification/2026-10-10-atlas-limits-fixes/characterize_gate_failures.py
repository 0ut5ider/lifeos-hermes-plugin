# ABOUTME: Records the exact fixture causes of the Atlas limits combined-gate failures.
# ABOUTME: Observes real service instance creation and native job output without changing runtime code.
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import test_memory_atlas_capacity as capacity
import test_memory_atlas_jobs as jobs
from lifeos_hook_bridge.memory_access import NativeMemory

report = {}
case = capacity.MemoryAtlasCapacityTests()
case.setUp()
seen = []
original = NativeMemory._native
def observed(memory, action, **arguments):
    seen.append({'action':action,'fixture_instance':memory is case.owner.fixture.memory})
    return original(memory, action, **arguments)
NativeMemory._native = observed
try:
    case.inventory(1,1)
    report['private_fixture'] = {'receipt':case.sync(),'native_calls':seen}
finally:
    NativeMemory._native = original
    case.doCleanups()
case = jobs.MemoryAtlasJobRelayTests()
case.setUp()
try:
    case.seed_graph('SyntheticAtlasHeldJob')
    environment, received, requests = case.held_inference()
    graph = case.directory/'atlas.db'
    sources = [case.root/'LIFEOS/USER'/name for name in ('GEAR.md','PROJECTS.md')]
    report['lifetime_fixture'] = {'sources':{path.name:path.read_text() if path.exists() else None for path in sources},
        'companions_before':[path.name for path in case.directory.iterdir()]}
    with closing(sqlite3.connect(graph)) as connection:
        report['lifetime_fixture']['journal_mode'] = connection.execute('PRAGMA journal_mode').fetchone()[0]
    env = dict(os.environ, HOME=str(case.fixture.home), HERMES_HOME=str(case.fixture.profile),
        PYTHONPATH=os.pathsep.join([os.environ['LIFEOS_HERMES_SOURCE'],os.environ.get('PYTHONPATH','')]),
        LIFEOS_HOOK_MODEL_ENV=str(environment),BUN_CONFIG_NO_AUTO_INSTALL='1')
    result = subprocess.run([sys.executable,'-B','-m','hermes_cli.main','lifeos-job','atlas-insights'],
        env=env,cwd=case.fixture.profile,capture_output=True,text=True,timeout=30)
    report['lifetime_fixture'].update(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,
        model_request_count=len(requests),companions_after=[path.name for path in case.directory.iterdir()])
finally:
    case.doCleanups()
Path(__file__).with_name('gate-failure-causes.json').write_text(json.dumps(report,indent=2)+'\n')
