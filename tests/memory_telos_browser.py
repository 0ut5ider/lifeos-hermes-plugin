# ABOUTME: Serves the actual TELOS editor against disposable native and authenticated owner servers.
# ABOUTME: Writes synthetic browser endpoint metadata and retains the original HTTP save effects.
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

from test_memory_telos_editor import MemoryTelosEditorTests
from test_memory_native import SOURCE

fixture = MemoryTelosEditorTests()
fixture.setUp()
source = fixture.seed()
folder = Path(sys.argv[1]).resolve()
folder.mkdir(parents=True, exist_ok=True)
(fixture.fixture.home / 'node_modules').symlink_to(
    SOURCE / 'LIFEOS/PULSE/Observability/node_modules', target_is_directory=True)
entry = fixture.fixture.home / 'telos-editor-browser.tsx'
entry.write_text('import {createRoot} from ' + json.dumps(str(SOURCE / 'LIFEOS/PULSE/Observability/node_modules/react-dom/client')) + ';\n'
    'import {useState} from ' + json.dumps(str(SOURCE / 'LIFEOS/PULSE/Observability/node_modules/react')) + ';\n'
    'import {FileEditor} from ' + json.dumps(str(SOURCE / 'LIFEOS/PULSE/Observability/src/app/telos/_v7/file-editor.tsx')) + ';\n'
    'function Editor(){const [open,setOpen]=useState(true);const [saved,setSaved]=useState(0);'
    'return <><button onClick={()=>setOpen(true)}>Open GOALS</button><p>Saved count: {saved}</p>'
    '<FileEditor open={open} filename="GOALS.md" onClose={()=>setOpen(false)} onSaved={()=>setSaved(saved+1)}/></>};'
    'const element=document.getElementById("root");if(!element)throw new Error("Missing fixture root");'
    'createRoot(element).render(<Editor/>);\n')
bundle = fixture.fixture.home / 'browser-bundle'
result = subprocess.run(['bun', 'build', str(entry), '--target=browser', '--outdir=' + str(bundle)],
    capture_output=True, text=True, timeout=40)
(folder / 'browser-build.txt').write_text(result.stdout + result.stderr)
if result.returncode:
    fixture.doCleanups()
    raise SystemExit(result.returncode)
program = fixture.fixture.home / 'telos-browser-proxy.ts'
program.write_text('const native=' + json.dumps(fixture.native) + ';const dashboard=' + json.dumps(fixture.dashboard) + ';'
    'const bundle=' + json.dumps(str(bundle / 'telos-editor-browser.js')) + ';'
    'const server=Bun.serve({hostname:"127.0.0.1",port:0,async fetch(request){'
    'const url=new URL(request.url);if(url.pathname==="/editor.js")return new Response(Bun.file(bundle),'
    '{headers:{"content-type":"text/javascript"}});'
    'if(url.pathname.startsWith("/api/")||url.pathname.startsWith("/auth/")){'
    'const target=url.pathname.startsWith("/auth/")?dashboard:native;'
    'const headers=new Headers(request.headers);const origin=headers.get("origin");'
    'if(origin&&origin!==url.origin)return new Response("Invalid fixture origin",{status:403});'
    'headers.set("host",new URL(target).host);if(origin)headers.set("origin",target);'
    'return fetch(target+url.pathname+url.search,{method:request.method,headers,'
    'body:["GET","HEAD"].includes(request.method)?undefined:await request.arrayBuffer(),redirect:"manual"});}'
    'return new Response("<!doctype html><html><body><div id=\\"root\\"></div>'
    '<script type=\\"module\\" src=\\"/editor.js\\"></script></body></html>",'
    '{headers:{"content-type":"text/html"}});}});console.log(server.port);\n')
process = subprocess.Popen(['bun', '--no-install', str(program)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
if not select.select([process.stdout], [], [], 10)[0]:
    process.terminate()
    process.communicate(timeout=10)
    fixture.doCleanups()
    raise SystemExit('The browser fixture does not start')
endpoint = {'url': 'http://127.0.0.1:' + process.stdout.readline().strip(),
    'source': str(source), 'configuration': str(fixture.fixture.configuration.path), 'pid': os.getpid()}
(folder / 'browser-endpoint.json').write_text(json.dumps(endpoint, indent=2) + '\n')
(folder / 'browser-ready').write_text('ready\n')
stopping = False

def stop(signum, frame):
    global stopping
    stopping = True

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    while not stopping: time.sleep(0.2)
finally:
    process.terminate()
    output, errors = process.communicate(timeout=10)
    (folder / 'browser-proxy.txt').write_text(output + errors)
    fixture.doCleanups()
    (folder / 'browser-stopped').write_text('stopped\n')
