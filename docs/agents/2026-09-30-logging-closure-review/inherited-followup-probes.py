# ABOUTME: Verifies capture corrections with synthetic evidence and real subprocesses.
# ABOUTME: Saves count-only results without reading real conversation artifacts.
import argparse
import base64
import dataclasses
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--development', required=True)
    parser.add_argument('--plugin', required=True)
    args = parser.parse_args()
    development = Path(args.development).resolve()
    plugin = Path(args.plugin).resolve()
    sys.path.insert(0, str(development))
    from hook_capture.store import Recorder
    from hook_capture.analysis import rebuild, summary
    from hook_capture import instrument
    results = {}
    with tempfile.TemporaryDirectory(prefix='logging-followup-') as temporary:
        root = Path(temporary)
        disabled = root / 'disabled.json'
        disabled.write_text('{"enabled":false}')
        disabled.chmod(0o600)
        # Every subprocess suppresses an account startup observer before startup.
        env = dict(os.environ, HERMES_HOOK_CAPTURE_CONFIG=str(disabled),
                   PYTHONPATH=os.pathsep.join((str(development), str(plugin.parent), os.environ.get('PYTHONPATH', ''))))
        config = {'enabled': True, 'run_id': 'synthetic', 'plugin_root': str(plugin), 'host_root': '',
                  'capture_sources': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in (development / 'hook_capture').glob('*.py')},
                  'fingerprints': {str(plugin / name): hashlib.sha256((plugin / name).read_bytes()).hexdigest()
                                   for name in ('bridge.py', 'remote_hooks.py', '__init__.py', 'bin/hook_runner.py')}}

        def execute(label, code, drift=False):
            capture = root / (label + '-capture')
            configuration = root / (label + '.json')
            configured = {**config, 'root': str(capture)}
            if drift:
                configured['capture_sources'] = {'instrument.py': '0' * 64}
            configuration.write_text(json.dumps(configured))
            configuration.chmod(0o600)
            prefix = 'from hook_capture.instrument import install\ninstall(' + repr(str(configuration)) + ')\n'
            baseline = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=20)
            traced = subprocess.run([sys.executable, '-c', prefix + code], env=env, capture_output=True, text=True, timeout=20)
            events = [json.loads(line) for p in capture.glob('runs/*/events/*/*.jsonl')
                      for line in p.read_text().splitlines()]
            artifacts = [(event, json.loads(gzip.decompress((capture / event['data_ref']['path']).read_bytes())))
                         for event in events if event.get('data_ref')]
            metadata = {'baseline_exit': baseline.returncode, 'traced_exit': traced.returncode,
                        'same_outcome': baseline.stdout == traced.stdout,
                        'event_count': len(events), 'stderr': {'baseline': baseline.stderr, 'traced': traced.stderr}}
            return metadata, events, artifacts

        secret = 'SYNTHETIC-FOLLOWUP-DECLARATION-418293'
        hook = root / 'command-hook.py'
        hook.write_text('import json\nprint(json.dumps(' + repr({'api_key': secret, 'echo': secret}) + '))\n')
        settings = root / 'settings.json'
        settings.write_text(json.dumps({'hooks': {'PreToolUse': [{'hooks': [{'type': 'command', 'command': sys.executable + ' ' + str(hook)}]}]}}))
        code = ('from pathlib import Path\nfrom lifeos_hook_bridge.bridge import HookBridge\n'
                'bridge=HookBridge(Path(' + repr(str(settings)) + '),Path(' + repr(str(root)) + '))\n'
                'print(__import__("json").dumps(bridge.pre_tool_call("terminal",{"command":"pwd"},session_id="synthetic-session")))\nbridge.close()\n')
        metadata, events, artifacts = execute('command', code)
        stages = {'process.completed', 'run_command.returned', 'hook.completed', 'response.parsed.entered'}
        metadata.update({'checked_stages': sorted({e['stage'] for e, _ in artifacts if e['stage'] in stages}),
                         'credential_leak_stages': sorted({e['stage'] for e, value in artifacts if secret in json.dumps(value)})})
        results['actual_command'] = metadata
        metadata, drift_events, drift_artifacts = execute('source-drift', code, drift=True)
        metadata.update({'capture_gap_count': sum(e.get('status') == 'capture_gap' for e in drift_events),
                         'observer_hooks_active': any(e['stage'] == 'hook.completed' for e in drift_events),
                         'actual_source_manifest_recorded': any(e['stage'] == 'process.initialized' and value.get('capture_sources_actual') == config['capture_sources'] for e, value in drift_artifacts)})
        results['source_drift_separate_fixture'] = metadata

        http_code = r'''
import json, threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from lifeos_hook_bridge.bridge import HookBridge
root=Path(ROOT)
query='SYNTHETIC-HTTP-QUERY-572819'
response_secret='SYNTHETIC-HTTP-RESPONSE-572819'
body=json.dumps({'api_key':response_secret,'echo':response_secret}).encode()
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers['Content-Length']))
        self.send_response(200)
        self.send_header('X-API-Key',response_secret)
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
settings=root/'http-settings.json'
settings.write_text(json.dumps({'hooks':{'PreToolUse':[{'hooks':[{'type':'http','url':f'http://127.0.0.1:{server.server_port}/?access_token={query}'}]}]}}))
bridge=HookBridge(settings,root)
print(json.dumps(bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='http-session')))
bridge.close()
server.shutdown();server.server_close()
'''.replace('Path(ROOT)', 'Path(' + repr(str(root)) + ')')
        metadata, events, artifacts = execute('http', http_code)
        def expanded(value):
            if isinstance(value, dict):
                if value.get('encoding') == 'base64':
                    return base64.b64decode(value['bytes']).decode('utf8', 'replace')
                return ' '.join(expanded(v) for v in value.values())
            if isinstance(value, list):
                return ' '.join(expanded(v) for v in value)
            return str(value)
        metadata.update({'checked_stages': sorted({e['stage'] for e, _ in artifacts if e['stage'] in {'http.request','http.response_read','hook.completed','run_http.returned','inventory.observed'}}),
                         'decoded_credential_leak_stages': sorted({e['stage'] for e, value in artifacts if any(s in expanded(value) for s in ('SYNTHETIC-HTTP-QUERY-572819','SYNTHETIC-HTTP-RESPONSE-572819'))})})
        results['actual_http'] = metadata

        # The backend executes the unchanged native Bash transport locally.
        # It is not a remote-selection or network-transport coverage assertion.
        transport_code = r'''
import json,subprocess
from lifeos_hook_bridge.remote_hooks import run_project_hook
from hook_capture.instrument import CURRENT
class LocalProcessBackend:
    def execute(self,command,cwd='',stdin_data=None,timeout=60):
        result=subprocess.run(['/bin/bash','-c',command],cwd=cwd,input=stdin_data,text=True,capture_output=True,timeout=timeout)
        return {'returncode':result.returncode,'output':result.stdout+result.stderr}
CURRENT.set({'invocation_id':'transport-invocation','session_id':'transport-session'})
result=run_project_hook(LocalProcessBackend(),COMMAND,{'hook_event_name':'PreToolUse'},ROOT,5,{})
print(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}))
'''.replace('COMMAND', repr(sys.executable + ' ' + str(hook))).replace('ROOT', repr(str(root)))
        metadata, events, artifacts = execute('transport', transport_code)
        leaked = []
        for event, value in artifacts:
            content = expanded(value)
            if event['stage'] == 'transport.completed':
                lines = value['output'].split('\n')
                for index,line in enumerate(lines):
                    if line.startswith('__LIFEOS_HOOK_') and not line.endswith('_END'):
                        for position in (index+2,index+3):
                            if position < len(lines):
                                content += base64.b64decode(lines[position]).decode('utf8','replace')
            if secret in content:
                leaked.append(event['stage'])
        metadata.update({'credential_leak_stages': sorted(set(leaked)), 'event_stages': sorted({e['stage'] for e in events})})
        results['actual_native_encoded_transport'] = metadata

        @dataclasses.dataclass
        class Declared:
            api_key: str
            echo: str
        forms = {'json': json.dumps({'api_key':secret,'echo':secret}), 'bytes': json.dumps({'api_key':secret,'echo':secret}).encode(),
                 'dataclass': Declared(secret,secret), 'command_result': subprocess.CompletedProcess(['true'],0,json.dumps({'api_key':secret,'echo':secret}),secret),
                 'timeout_result': subprocess.TimeoutExpired(['true'],1,json.dumps({'api_key':secret,'echo':secret}),secret),
                 'partial_json': '{"api_key":"'+secret+'","echo":"'+secret+'"'}
        results['supported_representations']={}
        for label,value in forms.items():
            recorder=Recorder(root / ('supported-shape-'+label), 'shapes')
            ref=recorder.artifact({'input':value,'echo':secret})
            value=json.loads(gzip.decompress((recorder.root/ref['path']).read_bytes()))
            results['supported_representations'][label]={'leak':secret in expanded(value)}
        urls=['http://operator:'+secret+'@localhost/?ordinary=yes', 'http://localhost/?access_token='+secret, 'http://localhost/#access_token='+secret]
        results['url_and_header_declarations']={}
        for index,declared in enumerate([{'headers':{'X-API-Key':secret}}]+[{'url':url} for url in urls]):
            case=Recorder(root / ('url'+str(index)),'url')
            ref=case.artifact({**declared,'echo':secret})
            results['url_and_header_declarations'][str(index)]={'leak':secret in gzip.decompress((case.root/ref['path']).read_bytes()).decode()}
        loss=Recorder(root/'loss','loss')
        loss.emit('bad.nan',data={'value':float('nan')})
        cycle=[];cycle.append(cycle)
        loss.emit('bad.cycle',data=cycle)
        loss.emit('good.first');loss.emit('good.second')
        loss2=Recorder(root/'loss','loss')
        loss2.emit('bad.nan',data=float('nan'));loss2.emit('good.third')
        results['loss_summary']=summary(rebuild(loss.root))

        broken=Recorder(root/'malformed','malformed')
        event=broken.emit('valid.before',data={'content':'a'*1000})
        artifact=broken.root/event['data_ref']['path'];damaged=bytearray(artifact.read_bytes());damaged[10:14]=b'\xff'*4;artifact.write_bytes(damaged)
        with broken.event_path.open('a') as stream:
            for row in ([],None,{**event,'data_ref':['bad']},{**event,'status':['bad']}):
                stream.write(json.dumps(row)+'\n')
        broken.emit('valid.after')
        results['malformed_recovery']=summary(rebuild(broken.root))

        for label,data in [('inventory_mapping', {'registrations':[{'registration_id':'r','native_event':'PreToolUse','hook_kind':'command','matcher':[],'settings_origin':'synthetic'}]}),
                           ('inventory_wrong_top_level', []), ('inventory_wrong_registration_list', {'registrations':'bad'}),
                           ('sequence_overflow', None)]:
            case=Recorder(root/label,label)
            if data is not None:
                case.emit('inventory.observed',data=data)
            else:
                e=case.emit('valid.first')
                with case.event_path.open('a') as stream: stream.write(json.dumps({**e,'event_id':'huge','sequence':2**100})+'\n')
            case.emit('valid.after')
            try: results['extra_malformed_'+label]={'summary':summary(rebuild(case.root))}
            except Exception as error: results['extra_malformed_'+label]={'analysis_exception':type(error).__name__,'message':str(error)}

        origin=Recorder(root/'origins','origins');instrument.RECORDER=origin
        ids=[]
        for settings_name in ('first.json','second.json','first.json'):
            group={'hooks':[{'type':'command','command':'true'}]}
            bridge=SimpleNamespace(settings_path=root/settings_name,hooks={'PreToolUse':[group]},project_hook_settings={})
            token=instrument.CURRENT.set({'_groups':{}})
            instrument.groups(bridge,'PreToolUse',[group])
            ids.append(instrument.registration(bridge,'PreToolUse',group,group['hooks'][0])['registration_id'])
            instrument.CURRENT.reset(token)
        results['origins']={'distinct_origins_distinct_ids':ids[0]!=ids[1],'same_origin_stable_id':ids[0]==ids[2],'known_registrations':summary(rebuild(origin.root))['known_registrations']}
        host=Recorder(root/'host','host');instrument.RECORDER=host
        class Agent:
            session_id='same-session';_current_turn_id='first-turn'
        agent=Agent()
        def boundary(agent): return agent._current_turn_id
        wrapped=instrument.observed(boundary,'host.synthetic_context')
        assert wrapped(agent)=='first-turn'
        agent._current_turn_id='second-turn';assert wrapped(agent)=='second-turn'
        host_events=[json.loads(line) for line in host.event_path.read_text().splitlines()]
        results['host_turn_identity']={'turns':[e.get('turn_id') for e in host_events], 'session_retained':all(e.get('session_id')=='same-session' for e in host_events)}
        failed=Recorder(root/'failed','failed')
        failed.emit('hook.failed',registration_id='failed',invocation_id='failed',status='exception',duration_ns=100)
        results['failed_hook_summary']=summary(rebuild(failed.root))
    print(json.dumps(results,indent=2,sort_keys=True))

if __name__=='__main__':main()
