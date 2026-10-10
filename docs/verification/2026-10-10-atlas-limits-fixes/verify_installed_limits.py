# ABOUTME: Verifies installed Atlas capacity refusal and governed refresh in the isolated .252 profile.
# ABOUTME: Checks the selected native schedule, current views, and unchanged private model routing.
from contextlib import closing
from dataclasses import asdict
import hashlib
import http.cookiejar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from ruamel.yaml import YAML


stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage/'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
sys.path[:0] = [str(profile/'plugins'), str(stage/'package/hermes')]
module = lambda name: importlib.import_module('lifeos-hook-bridge.'+name)
configuration = module('memory_service').MemoryConfiguration(profile/'lifeos-memory.json')
service = module('memory_service').MemoryService(configuration)
original_configuration = configuration.load()
original_yaml = (profile/'config.yaml').read_bytes()
selected = YAML(typ='safe').load(original_yaml)
settings = selected['plugins']['entries']['lifeos-hook-bridge']['settings']
efforts = {name: settings[name+'_effort'] for name in ('haiku','sonnet','opus','fable')}
assert efforts == {'haiku':'low','sonnet':'medium','opus':'xhigh','fable':'xhigh'}
endpoint = selected['model']['base_url'].rstrip('/')
assert urllib.parse.urlsplit(endpoint).scheme == 'http'
graph = root.parent/'.local/state/lifeos/atlas/atlas.db'
snapshot = graph.with_name('snapshot.json')
cache = root/'LIFEOS/MEMORY/STATE/atlas-insights.json'
assert graph.exists() and snapshot.exists() and cache.exists()
environment = {'HOME':str(root.parent), 'HERMES_HOME':str(profile),
    'PATH':str(stage/'bin')+':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    'PYTHONPATH':str(stage/'package/hermes'), 'LANG':'C.UTF-8','TZ':'America/Toronto',
    'LIFEOS_DIR':str(root/'LIFEOS'), 'LIFEOS_HOOK_SETTINGS':str(root/'settings.json'),
    'LIFEOS_NOTIFICATION_CHANNEL':'headless','BUN_CONFIG_NO_AUTO_INSTALL':'1','PYTHONDONTWRITEBYTECODE':'1'}
wire, jobs, observations = [], [], []
direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))

class Observer(BaseHTTPRequestHandler):
    def do_POST(self):
        target = self.path
        if not target.startswith(endpoint+'/'):
            self.send_error(403, 'Choose the configured private endpoint')
            return
        content = self.rfile.read(int(self.headers['Content-Length']))
        body = json.loads(content)
        request = urllib.request.Request(target, data=content, headers={
            'Content-Type':'application/json', 'Authorization':self.headers.get('Authorization','')})
        try:
            reply = direct.open(request, timeout=180)
        except urllib.error.HTTPError as error:
            reply = error
        with reply:
            data = reply.read(16*1024*1024+1)
            assert len(data) <= 16*1024*1024
            status = reply.status
            content_type = reply.headers.get('Content-Type','application/json')
        decoded = json.loads(data)
        wire.append({'path':urllib.parse.urlsplit(target).path,'requested_model':body.get('model'),
            'reasoning_effort':body.get('reasoning_effort'),'upstream_status':status,
            'actual_model':decoded.get('model'),'response_sha256':hashlib.sha256(data).hexdigest(),
            'body_keys':sorted(body)})
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *_):
        pass

observer = ThreadingHTTPServer(('127.0.0.1',0), Observer)
threading.Thread(target=observer.serve_forever,daemon=True).start()
proxy = 'http://127.0.0.1:'+str(observer.server_port)
environment.update({name:proxy for name in ('HTTP_PROXY','http_proxy','HTTPS_PROXY','https_proxy','ALL_PROXY','all_proxy')})
environment.update(NO_PROXY='',no_proxy='')
os.environ.update(PATH=environment['PATH'], HOME=str(root.parent), HERMES_HOME=str(profile))
out = stage/'atlas-limits-acceptance'
assert not out.exists()
out.mkdir(mode=0o700)
sha = lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

def job(name, *, success=True):
    started = time.monotonic()
    result = subprocess.run([str(stage/'bin/hermes'),'lifeos-job',name],env=environment,cwd=profile,
        capture_output=True,text=True,timeout=570)
    row = {'job':name,'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-started,
        'stdout':result.stdout,'stderr':result.stderr}
    jobs.append(row)
    (out/'jobs.json').write_text(json.dumps(jobs,indent=2)+'\n')
    assert result.stderr == ''
    receipt = json.loads(result.stdout)
    if success:
        assert result.returncode == 0 and receipt['status']=='completed', receipt
    else:
        assert result.returncode != 0
    assert (profile/'config.yaml').read_bytes() == original_yaml
    print(json.dumps({'job':name,'success':success,'status':receipt['status']}),flush=True)
    return receipt

def context():
    value = configuration.load()
    grant = value['destinations']['terminal:'+str(profile)]
    return module('memory_policy').SessionContext('terminal',str(os.getuid()),str(profile),'private',
        (value['principal'],),grant['model_routes'][0],'atlas-installed-'+uuid4().hex)

def native(name, **arguments):
    return service.native(context(),name,arguments)

cookies = http.cookiejar.CookieJar()
authenticated = urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(cookies))

def request(path, *, logged_in=True, data=None, dashboard=False):
    url = 'http://127.0.0.1:'+('18819' if dashboard else '18837')+path
    req = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),
        headers={} if data is None else {'Content-Type':'application/json'})
    try:
        reply = (authenticated if logged_in else direct).open(req,timeout=45)
    except urllib.error.HTTPError as error:
        reply = error
    with reply:
        body = json.loads(reply.read())
        status, control = reply.status, reply.headers.get('Cache-Control')
    observations.append({'path':path,'status':status,'authenticated':logged_in,'cache_control':control})
    return status, body

report = {'status':'FAIL','isolated_acceptance_profile_only':True,'live_profile_changed':False}
try:
    assert request('/auth/password-login',dashboard=True,data={'provider':'basic',
        'username':'acceptance-owner','password':'synthetic-application-acceptance-password'})[0]==200
    selected_candidate=json.loads((stage/'APPLICATION-CANDIDATE.json').read_text())
    gear=root/'LIFEOS/USER/GEAR.md'
    projects=root/'LIFEOS/USER/PROJECTS.md'
    originals={path:path.read_bytes() for path in (gear,projects)}
    prior={path:path.read_bytes() for path in (graph,snapshot,cache)}
    identity_before=json.loads(cache.read_text())['hash']
    try:
        value='| Name | Path | URL | Deploy |\n| --- | --- | --- | --- |\n'+''.join(
            f'| Synthetic capacity project {index} | /synthetic/{index} github.com/synthetic/repo-{index} '
            f'| app-{index}.example.invalid | local |\n' for index in range(85))
        module('memory_transaction').publish(projects,value.encode())
        refused=job('atlas-sync',success=False)
        assert refused['status']=='failed' and 'capacity' in refused['output'].lower()
        assert {path:path.read_bytes() for path in prior}==prior
        assert not module('memory_access').NativeMemory(root).transaction.journal.exists()
    finally:
        for path,content in originals.items(): module('memory_transaction').publish(path,content)
    canonical=stage/'pulse-daemon-types-source/lifeos/LifeOS/install'
    assert sha(root/'LIFEOS/PULSE/lib.ts')==sha(canonical/'LIFEOS/PULSE/lib.ts')
    program=Path(selected_candidate['atlas_initialization_candidate'])/'package/tests/native_daily_pulse_profile.ts'
    selected_profile=root/'LIFEOS/USER/CONFIG/PULSE.user.toml'
    command=['/home/lifeos-hermes/.local/bin/bun','--no-install',str(program),str(root),str(selected_profile),'atlas-sync']
    result=subprocess.run(command,env=environment,cwd=profile,capture_output=True,text=True,timeout=60)
    assert result.returncode==0 and not result.stderr,result
    scheduled=json.loads(json.loads(result.stdout)['output'])
    assert scheduled['status']=='completed'
    capacity=json.loads(scheduled['output'])['capacity']
    assert capacity['graph_fields']['used']<=capacity['graph_fields']['limit']
    module('memory_transaction').publish(gear,
        b'## Computing\n| **Laptop** | Synthetic Atlas installed capacity refresh | daily |\n')
    refreshed=job('atlas-insights')
    assert len(wire)==1 and wire[0]['upstream_status']==200 and wire[0]['reasoning_effort']=='xhigh'
    assert wire[0]['requested_model']==selected['model']['default']
    with closing(sqlite3.connect(graph)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM asset WHERE display_name='Synthetic Atlas installed capacity refresh'").fetchone()[0]==1
    current=json.loads(cache.read_text())
    assert current['hash']!=identity_before
    assert request('/api/atlas')[0]==200
    status,insight=request('/api/atlas/insights')
    assert status==200 and insight['available'] is True and insight['stale'] is False
    assert insight['narrative']==current['narrative']
    stable={path:sha(path) for path in (graph,snapshot,cache)}
    prior_configuration=configuration.load()
    configuration.update(lambda value:value.update(ownership_enabled=False))
    try:
        rejected=job('atlas-sync',success=False)
        assert rejected['status']=='rejected'
        assert {path:sha(path) for path in stable}==stable
    finally: configuration.save(prior_configuration)
    assert (profile/'config.yaml').read_bytes()==original_yaml
    assert configuration.load()==original_configuration
    assert all(path.stat().st_mode & 0o777==0o600 for path in (graph,snapshot,cache))
    report.update(status='PASS',head=selected_candidate['head'],capacity_refusal_before_publication=True,
        no_recovery_journal_for_capacity_refusal=True,exact_artifacts_preserved_on_refusal=True,
        actual_native_schedule_spawn_verified=True,capacity=capacity,
        native_schedule_loader_sha256=sha(root/'LIFEOS/PULSE/lib.ts'),
        regeneration_reconciles_source_before_model=True,current_narrative_verified=True,
        disabled_owner_refuses_without_changes=True,model_configuration_changed=False,
        model_configuration_sha256=hashlib.sha256(original_yaml).hexdigest(),
        pinned_tier=settings['pinned_tier'],tier_efforts=efforts,
        daily_profile_sha256=sha(selected_profile),artifact_sha256={path.name:sha(path) for path in (graph,snapshot,cache)})
finally:
    observer.shutdown();observer.server_close()
    report.update(jobs=jobs,observations=observations,wire_requests=wire)
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (stage/'installed-atlas-limits-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key not in ('jobs','observations')},indent=2))
