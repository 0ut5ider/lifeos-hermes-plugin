# ABOUTME: Verifies fresh Atlas graph, updates, actual model narratives, and owner refusal on .252.
# ABOUTME: Observes the unchanged private model route and recovers an interrupted installed publication.
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
assert not graph.exists() and not snapshot.exists() and not cache.exists()
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
out = stage/'atlas-installed-acceptance'
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
    for path in ('/api/atlas','/api/atlas/insights'):
        assert request(path,logged_in=False)[0] == 401
    assert request('/auth/password-login',dashboard=True,data={'provider':'basic',
        'username':'acceptance-owner','password':'synthetic-application-acceptance-password'})[0] == 200
    originals = {}
    for name, content in {
        'GEAR.md':'## Computing\n| **Laptop** | Synthetic Atlas Acceptance Machine | daily |\n',
        'PROJECTS.md':'| Name | Path | URL | Deploy |\n| --- | --- | --- | --- |\n'
            '| Synthetic Atlas Acceptance Project | /synthetic/atlas | atlas.example.invalid | local |\n'}.items():
        path = root/'LIFEOS/USER'/name
        original = path.read_bytes() if path.exists() else None
        originals[name] = None if original is None else hashlib.sha256(original).hexdigest()
        if original is not None:
            (out/(name+'.before')).write_bytes(original)
        module('memory_transaction').publish(path,content.encode())
    first = job('atlas-sync')
    assert json.loads(first['output'])['ok'] is True
    with closing(sqlite3.connect(graph)) as connection:
        identities = connection.execute('SELECT id, canonical_key FROM asset ORDER BY id').fetchall()
        assert len(identities)==3
    status, view = request('/api/atlas')
    assert status==200 and view['available'] is True and len(view['assets'])==3
    prepared_insight = native('atlas_insight_prepare')
    assert prepared_insight['ok'] is True
    job('atlas-insights')
    value = json.loads(cache.read_text())
    assert value['narrative'].strip() and value['hash']==prepared_insight['plan']['hash']
    assert len(wire)==1 and wire[0]['upstream_status']==200 and wire[0]['reasoning_effort']=='xhigh'
    assert wire[0]['requested_model']==selected['model']['default']
    identity = lambda path:(sha(path),path.stat().st_ino,path.stat().st_mtime_ns)
    before = identity(cache)
    status, current = request('/api/atlas/insights')
    assert status==200 and current['stale'] is False and current['narrative']==value['narrative']
    assert identity(cache)==before and len(wire)==1
    job('atlas-sync')
    with closing(sqlite3.connect(graph)) as connection:
        assert connection.execute('SELECT id, canonical_key FROM asset ORDER BY id').fetchall()==identities
    gear = root/'LIFEOS/USER/GEAR.md'
    module('memory_transaction').publish(gear,b'## Computing\n| **Laptop** | Synthetic Atlas Acceptance Machine Two | daily |\n')
    job('atlas-sync')
    assert native('atlas_insight_check',signature=prepared_insight['signature'])['ok'] is False
    with closing(sqlite3.connect(graph)) as connection:
        assert connection.execute("SELECT fresh FROM source_observation JOIN asset ON asset.id=source_observation.asset_id WHERE canonical_key='gear:laptop-synthetic-atlas-acceptance-machine'").fetchone()[0]==0
        assert connection.execute('SELECT COUNT(*) FROM asset').fetchone()[0]==4
    job('atlas-insights')
    assert len(wire)==2 and all(row['reasoning_effort']=='xhigh' and row['upstream_status']==200
        and row['requested_model']==selected['model']['default'] for row in wire)
    status, insight = request('/api/atlas/insights')
    assert status==200 and insight['available'] is True and insight['stale'] is False
    assert insight['narrative']==json.loads(cache.read_text())['narrative']
    before = {path:sha(path) for path in (graph,snapshot,cache)}
    terminal = 'terminal:'+str(profile)
    for mode in ('disabled','read-only','unbound'):
        prior = configuration.load()
        if mode=='disabled':
            configuration.update(lambda value:value.update(ownership_enabled=False))
        elif mode=='read-only':
            configuration.update(lambda value:value['destinations'][terminal].update(write=[]))
        else:
            configuration.update(lambda value:value['accounts'].pop('terminal:'+str(os.getuid())))
        try:
            job('atlas-sync',success=False)
            assert {path:sha(path) for path in before}==before
        finally:
            configuration.save(prior)
    account = 'dashboard:basic:acceptance-owner'
    binding = configuration.load()['accounts'][account]
    configuration.update(lambda value:value['accounts'].pop(account))
    try:
        for path in ('/api/atlas','/api/atlas/insights'):
            assert request(path)[0]==403
    finally:
        configuration.update(lambda value:value['accounts'].update({account:binding}))
    assert request('/api/atlas')[0]==200
    originals_before_interrupt = {path:path.read_bytes() for path in (graph,snapshot,cache)}
    result = subprocess.run([sys.executable,str(stage/'installed-atlas-interruption.py'),json.dumps(asdict(context()))],
        env=environment,cwd=profile,capture_output=True,text=True,timeout=45)
    assert (result.returncode,result.stdout,result.stderr)==(73,'','')
    memory = module('memory_access').NativeMemory(root)
    assert memory.transaction.journal.exists()
    with closing(sqlite3.connect(memory.database)) as connection:
        assert any(json.loads(row[0])['status']=='unknown' for row in connection.execute('SELECT receipt FROM operations'))
    with memory._transaction():
        pass
    assert not memory.transaction.journal.exists()
    assert {path:path.read_bytes() for path in originals_before_interrupt}==originals_before_interrupt
    with closing(sqlite3.connect(memory.database)) as connection:
        assert all(json.loads(row[0])['status']!='unknown' for row in connection.execute('SELECT receipt FROM operations'))
    assert request('/api/atlas/insights')[1]['stale'] is False
    assert (profile/'config.yaml').read_bytes()==original_yaml
    assert configuration.load()==original_configuration
    assert all(path.stat().st_mode & 0o777==0o600 for path in (graph,snapshot,cache))
    report.update(status='PASS',wire_requests=wire,tier_efforts=efforts,pinned_tier=settings['pinned_tier'],
        model_configuration_sha256=hashlib.sha256(original_yaml).hexdigest(),
        model_configuration_changed=False,configuration_route_changed=False,
        initial_assets=3,updated_assets=4,narrative_characters=len(insight['narrative']),
        native_snapshot_verified=True,repeat_identity_verified=True,cache_reuse_without_inference_verified=True,
        old_signature_refused=True,owner_refusal_modes=['disabled','read-only','unbound'],
        authenticated_views_verified=True,anonymous_and_revoked_readers_refused=True,
        installed_process_death_exit_code=73,exact_publication_group_recovery_verified=True,
        source_originals=originals,artifact_sha256={path.name:sha(path) for path in (graph,snapshot,cache)})
finally:
    observer.shutdown()
    observer.server_close()
    report.update(jobs=jobs,observations=observations,wire_requests=wire)
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (stage/'installed-atlas-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key not in ('jobs','observations')},indent=2))
