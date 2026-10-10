# ABOUTME: Runs the combined native publication and preparation regression checks.
# ABOUTME: Retains exact commands, output, and completion status across session disconnects.
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import hashlib

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
PYTHON = '/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'
HERMES = '/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed/hermes'
ENVIRONMENT = {
    'PYTHONDONTWRITEBYTECODE':'1',
    'PYTHONPATH':str(ROOT)+':'+str(ROOT/'tests')+':'+HERMES,
    'LIFEOS_HERMES_SOURCE':HERMES,
    'LIFEOS_MEMORY_SOURCE':'/home/outsider/.cache/lifeos-daily-text-20261007/content-response-first/lifeos/LifeOS/install',
    'LIFEOS_HARVEST_CONTROL_SOURCE':'/home/outsider/.cache/lifeos-plugin-memory/source/LifeOS/install',
}
MODULES = [
    'test_memory_publication_revocation', 'test_memory_session_harvest', 'test_memory_proposal_gc',
    'test_memory_knowledge_harvest', 'test_memory_staging', 'test_memory_staging_writers',
    'test_memory_native', 'test_memory_native_response_authority',
    'test_memory_algorithm_edits', 'test_memory_algorithm_edit_rpc',
    'test_memory_algorithm_summary', 'test_memory_algorithm_summary_edges',
    'test_memory_algorithm_jobs', 'test_memory_algorithm_job_cooldown', 'test_memory_algorithm_tab',
    'test_memory_local_refresh', 'test_memory_local_refresh_native', 'test_memory_local_refresh_publication',
    'test_memory_local_refresh_runs', 'test_memory_local_refresh_cache', 'test_memory_local_refresh_jobs',
    'test_memory_local_refresh_lifetime', 'test_memory_conduit_insight', 'test_memory_conduit',
    'test_memory_conduit_jobs', 'test_memory_conduit_capture', 'test_memory_conduit_capture_job',
    'test_patch_bundle', 'test_prepare_sources', 'test_hermes_install_source', 'test_lifeos_install_source',
]

def run(label, modules):
    command = [PYTHON, '-m', 'unittest', '-v', *modules]
    start = time.time()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    paths = subprocess.check_output(['git', 'ls-files', 'lifeos_hook_bridge', 'tests'], cwd=ROOT, text=True).splitlines()
    hashes = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}
    with (OUT/(label+'.txt')).open('w') as log:
        result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, **ENVIRONMENT),
            stdout=log, stderr=subprocess.STDOUT)
    record = {'command':command, 'cwd':str(ROOT), 'environment_overrides':ENVIRONMENT,
        'revision':revision, 'source_hashes':hashes, 'exit_code':result.returncode,
        'duration_seconds':time.time()-start, 'output':label+'.txt'}
    (OUT/(label+'.json')).write_text(json.dumps(record, indent=2)+'\n')
    (OUT/(label+'.done')).write_text(str(result.returncode)+'\n')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(run(sys.argv[1] if len(sys.argv)>1 else 'combined', sys.argv[2:] or MODULES))
