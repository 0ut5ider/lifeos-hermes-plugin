# ABOUTME: Checks the logging closure fixes with synthetic native hook evidence.
# ABOUTME: Saves count-only outcomes for credentials and artifact references.
import base64
import gzip
import importlib.util
import json
import sqlite3
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'development'))
from hook_capture.store import Recorder
from hook_capture.analysis import rebuild, summary

spec = importlib.util.spec_from_file_location('closure_test_fixture', ROOT / 'development/tests/test_capture.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
case = fixture.OverlayTests()
results = {}

def artifacts(root, events):
    for event in events:
        if event.get('data_ref'):
            yield event, json.loads(gzip.decompress((root / 'capture' / event['data_ref']['path']).read_bytes()))

def expanded(value):
    if isinstance(value, dict):
        if value.get('encoding') == 'base64':
            return base64.b64decode(value['bytes']).decode('utf8', 'replace')
        return ' '.join(expanded(item) for item in value.values())
    if isinstance(value, list):
        return ' '.join(expanded(item) for item in value)
    return str(value)

try:
    bearer = 'SYNTHETIC-CLOSURE-BEARER-283749'
    setup = '''
def invoke(bridge):
    import json, sys
    path=bridge.root/'bearer-hook.py'
    value={'headers':{'Authorization':'Bearer SYNTHETIC-CLOSURE-BEARER-283749'}, 'echo':'SYNTHETIC-CLOSURE-BEARER-283749'}
    path.write_text('import json\\nprint(json.dumps('+repr(value)+'))\\n')
    bridge.hooks['PreToolUse'][0]['hooks'][0]['command']=sys.executable+' '+str(path)
    return bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='bearer')
'''
    hooks={'PreToolUse':[{'hooks':[{'type':'command','command':'true'}]}]}
    _, baseline, _=case.run_bridge(hooks,'invoke(bridge)',setup=setup,traced=False)
    root, observed, events=case.run_bridge(hooks,'invoke(bridge)',setup=setup)
    results['real_bearer_hook']={'same_native_outcome':baseline==observed,
        'leak_stages':sorted({event['stage'] for event,value in artifacts(root,events) if bearer in expanded(value)}),
        'observed_stages':sorted({event['stage'] for event in events})}

    cookie='SYNTHETIC-CLOSURE-COOKIE-192837'
    second='SYNTHETIC-SECOND-COOKIE-837291'
    body=json.dumps({'echo':cookie,'second_echo':second}).encode()
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            self.send_response(200)
            self.send_header('Set-Cookie','session='+cookie+'; HttpOnly; Path=/')
            self.send_header('Set-Cookie','access='+second+'; HttpOnly; Path=/')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self,*args):
            pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        hooks={'PreToolUse':[{'hooks':[{'type':'http','url':f'http://127.0.0.1:{server.server_port}/'}]}]}
        action="bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='cookie')"
        _,baseline,_=case.run_bridge(hooks,action,traced=False)
        root,observed,events=case.run_bridge(hooks,action)
        captured = list(artifacts(root, events))
        (Path(__file__).parent / 'primary-multiple-cookie-artifacts.json').write_text(json.dumps(
            [{'event': event, 'value': value} for event, value in captured], indent=2))
        results['real_cookie_http_hook']={'same_native_outcome':baseline==observed,
            'leak_stages':sorted({event['stage'] for event,value in artifacts(root,events) if cookie in expanded(value) or second in expanded(value)}),
            'http_header_redacted':all(value['headers']['Set-Cookie']=='[REDACTED]' for event,value in artifacts(root,events) if event['stage']=='http.response_read'),
            'event_count':len(events),
            'first_cookie_leak_stages': sorted({event['stage'] for event,value in captured if cookie in expanded(value)}),
            'second_cookie_leak_stages': sorted({event['stage'] for event,value in captured if second in expanded(value)}),
            'source_hashes': next(value['capture_sources_actual'] for event,value in captured if event['stage']=='process.initialized')}
    finally:
        server.shutdown()
        server.server_close()

    results['reference_orders']={}
    for order in ('valid_then_bad','bad_then_valid'):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            recorder=Recorder(root,'reference')
            event=recorder.emit('inventory.observed',data={'registrations':[{'registration_id':'valid-registration'}]})
            bad={**event,'event_id':'bad-reference','data_ref':{**event['data_ref'],'sha256':'0'*64}}
            rows=[event,bad] if order=='valid_then_bad' else [bad,event]
            recorder.event_path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            results['reference_orders'][order]=summary(rebuild(root))

    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary)
        recorder=Recorder(root,'reference-only-bad')
        event=recorder.emit('observed.valid',data={'registrations':[{'registration_id':'must-not-index'}]})
        bad={**event,'event_id':'bad-reference','stage':'inventory.observed','data_ref':{**event['data_ref'],'sha256':'0'*64}}
        with recorder.event_path.open('a') as stream:
            stream.write(json.dumps(bad)+'\n')
        results['invalid_reference_cannot_index']=summary(rebuild(root))
finally:
    case.doCleanups()
print(json.dumps(results,indent=2,sort_keys=True))
