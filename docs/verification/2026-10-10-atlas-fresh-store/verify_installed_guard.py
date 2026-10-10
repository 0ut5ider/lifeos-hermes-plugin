# ABOUTME: Verifies the final Atlas planner directory guard in the installed acceptance profile.
# ABOUTME: Preserves current graph identities, cached narrative bytes, and private configuration.
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
original_yaml = (profile/'config.yaml').read_bytes()
original_policy = (profile/'lifeos-memory.json').read_bytes()
graph = root.parent/'.local/state/lifeos/atlas/atlas.db'
snapshot = graph.with_name('snapshot.json')
cache = root/'LIFEOS/MEMORY/STATE/atlas-insights.json'
manifest = json.loads((stage/'APPLICATION-CANDIDATE.json').read_text())
assert manifest['head'].startswith('ef946c3f')
sha = lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
cache_before = (sha(cache),cache.stat().st_ino,cache.stat().st_mtime_ns)
with closing(sqlite3.connect(graph)) as connection:
    assets_before = connection.execute('SELECT id, canonical_key FROM asset ORDER BY id').fetchall()
outside = stage/'atlas-guard-unselected-directory'
assert not outside.exists()
environment = {'HOME':str(root.parent),'HERMES_HOME':str(profile),
    'PATH':str(stage/'bin')+':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    'PYTHONPATH':str(stage/'package/hermes'),'LANG':'C.UTF-8','TZ':'America/Toronto',
    'LIFEOS_DIR':str(root/'LIFEOS'),'LIFEOS_HOOK_SETTINGS':str(root/'settings.json'),
    'LIFEOS_NOTIFICATION_CHANNEL':'headless','BUN_CONFIG_NO_AUTO_INSTALL':'1',
    'PYTHONDONTWRITEBYTECODE':'1','ATLAS_DIR':str(outside)}
result = subprocess.run([str(stage/'bin/hermes'),'lifeos-job','atlas-sync'],
    env=environment,cwd=profile,capture_output=True,text=True,timeout=60)
assert result.returncode==0 and not result.stderr, result
receipt=json.loads(result.stdout)
assert receipt['status']=='completed' and json.loads(receipt['output'])['ok'] is True
assert not outside.exists()
with closing(sqlite3.connect(graph)) as connection:
    assert connection.execute('SELECT id, canonical_key FROM asset ORDER BY id').fetchall()==assets_before
assert cache_before==(sha(cache),cache.stat().st_ino,cache.stat().st_mtime_ns)
assert (profile/'config.yaml').read_bytes()==original_yaml
assert (profile/'lifeos-memory.json').read_bytes()==original_policy
cookies=http.cookiejar.CookieJar()
authenticated=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(cookies))
login=urllib.request.Request('http://127.0.0.1:18819/auth/password-login',
    data=json.dumps({'provider':'basic','username':'acceptance-owner',
        'password':'synthetic-application-acceptance-password'}).encode(),
    headers={'Content-Type':'application/json'})
with authenticated.open(login,timeout=30) as reply: assert reply.status==200
views=[]
for path in ('/api/atlas','/api/atlas/insights'):
    with authenticated.open('http://127.0.0.1:18837'+path,timeout=30) as reply:
        value=json.loads(reply.read())
        assert reply.status==200 and value['available'] is True
        if path.endswith('insights'): assert value['stale'] is False
        else: assert len(value['assets'])==4
        views.append({'path':path,'status':reply.status,'available':value['available']})
assert all(path.stat().st_mode & 0o777==0o600 for path in (graph,snapshot,cache))
report={'status':'PASS','head':manifest['head'],'outside_directory_created':False,
    'native_identity_preserved':True,'cache_bytes_inode_mtime_preserved':True,
    'configuration_bytes_preserved':True,'authenticated_views':views,
    'artifact_sha256':{path.name:sha(path) for path in (graph,snapshot,cache)},
    'job':{'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr},
    'live_profile_changed':False,'isolated_acceptance_profile_only':True}
(stage/'installed-atlas-guard-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
