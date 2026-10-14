# ABOUTME: Serves the compiled Pulse assistant page against real synthetic owner and native core-file routes.
# ABOUTME: Keeps browser verification isolated and exposes only owned fixture endpoint metadata.
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

from test_memory_core_editor import MemoryCoreEditorTests

fixture = MemoryCoreEditorTests()
fixture.setUp()
source = fixture.seed()
fixture.seed_programs()
folder = Path(sys.argv[1]).resolve()
folder.mkdir(parents=True, exist_ok=True)
compiled = Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/PULSE/Observability/out'
assert (compiled / 'assistant.html').is_file()
program = fixture.fixture.home / 'core-browser-proxy.ts'
program.write_text('import {resolve} from "node:path";'
    'const native=' + json.dumps(fixture.native) + ';const dashboard=' + json.dumps(fixture.dashboard) + ';'
    'const compiled=' + json.dumps(str(compiled)) + ';'
    'const server=Bun.serve({hostname:"127.0.0.1",port:0,async fetch(request){'
    'const url=new URL(request.url);if(url.pathname==="/blank")return new Response("<!doctype html><title>Fixture authentication</title>",{headers:{"content-type":"text/html"}});'
    'if(url.pathname.startsWith("/api/")||url.pathname.startsWith("/auth/")){'
    'const target=url.pathname.startsWith("/auth/")||url.pathname.startsWith("/api/auth/")?dashboard:native;'
    'const headers=new Headers(request.headers);const origin=headers.get("origin");'
    'if(origin&&origin!==url.origin)return new Response("Invalid fixture origin",{status:403});'
    'headers.set("host",new URL(target).host);if(origin)headers.set("origin",target);'
    'return fetch(target+url.pathname+url.search,{method:request.method,headers,'
    'body:["GET","HEAD"].includes(request.method)?undefined:await request.arrayBuffer(),redirect:"manual"});}'
    'const name=url.pathname==="/assistant"?"assistant.html":url.pathname.slice(1);const path=resolve(compiled,name);'
    'if(!path.startsWith(compiled+"/"))return new Response("Invalid fixture path",{status:400});'
    'const file=Bun.file(path);return await file.exists()?new Response(file):new Response("Missing compiled fixture asset",{status:404});}});console.log(server.port);')
process = subprocess.Popen(['bun', '--no-install', str(program)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
assert select.select([process.stdout], [], [], 10)[0], 'The compiled browser proxy does not start'
url = 'http://127.0.0.1:' + process.stdout.readline().strip()
fixture.fixture.configuration.update(lambda value: value['pulse_http'].update(dashboard_browser_url=url))
metadata = {'url': url, 'source': str(source), 'configuration': str(fixture.fixture.configuration.path),
    'pid': os.getpid(), 'compiled_page': 'assistant.html', 'personal_data_used': False}
(folder / 'browser-endpoint.json').write_text(json.dumps(metadata, indent=2) + '\n')
(folder / 'browser-ready').write_text('ready\n')
stopping = False


def stop(signum, frame):
    global stopping
    stopping = True


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    while not stopping:
        if (folder / 'observe-request').exists():
            result = {'source_text': source.read_text(), 'source_mode': source.stat().st_mode & 0o777,
                'private_backups': len(list((fixture.root / 'LIFEOS/MEMORY/STATE/hermes-edits').glob('*.bak')))}
            (folder / 'browser-source-observation.json').write_text(json.dumps(result, indent=2) + '\n')
            (folder / 'observe-request').unlink()
        time.sleep(0.2)
finally:
    process.terminate()
    _, error = process.communicate(timeout=10)
    (folder / 'proxy.stderr').write_text(error)
    fixture.doCleanups()
    (folder / 'process.done').write_text('0\n')
