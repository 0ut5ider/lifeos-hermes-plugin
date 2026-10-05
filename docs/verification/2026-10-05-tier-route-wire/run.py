# ABOUTME: Sends one LifeOS child call per model tier through the candidate Hermes provider route.
# ABOUTME: Records the effort and model on each wire request and the response status from private FlashNext.
import base64
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import threading

from paired_response_server import response_handler

root=Path(__file__).resolve().parent
config=json.loads((root/'configuration.json').read_text())
spec=config['hermes']
MAPPING={'haiku':'low','sonnet':'medium','opus':'xhigh','fable':'xhigh'}
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),response_handler(config['model_environment']))
server.observed=[]
threading.Thread(target=server.serve_forever,daemon=True).start()
endpoint=f'http://127.0.0.1:{server.server_port}'
base=Path(spec['home_root']).parent/'tier-route-wire-20261005'
records=[]
status=1
try:
    for tier,effort in MAPPING.items():
        home=base/tier
        profile=home/'.hermes'
        (home/'bin').mkdir(parents=True)
        profile.mkdir()
        (profile/'plugins').symlink_to(spec['plugins_path'],target_is_directory=True)
        (profile/'config.yaml').write_text(json.dumps({
            'model':{'provider':'custom','base_url':endpoint+'/v1','api_key':'PAIR_TIER_ROUTE',
                     'default':'lifecycle-fixture','api_mode':'chat_completions'},
            'plugins':{'enabled':['lifeos-hook-bridge']}},indent=2)+'\n')
        launcher=home/'bin/hermes'
        launcher.write_text('#!/bin/sh\nexec '+spec['command'][0]+' -m hermes_cli.main "$@"\n')
        launcher.chmod(0o755)
        for item in (base,home,*home.rglob('*')):
            if not item.is_symlink():os.chown(item,spec['uid'],spec['gid'])
        environment={**spec['environment'],'HOME':str(home),'HERMES_HOME':str(profile),'LANG':'C.UTF-8',
            'PATH':str(home/'bin')+':'+spec['environment']['PATH'],
            'LIFEOS_MODEL_TIER_MAP':json.dumps({name:{'provider':'custom','model':'lifecycle-fixture','effort':value}
                                                for name,value in MAPPING.items()})}
        environment.pop('HERMES_EPHEMERAL_SYSTEM_PROMPT',None)
        before=len(server.observed)
        command=[spec['plugins_path']+'/lifeos-hook-bridge/bin/claude','--print','--model',tier,'--effort','medium',
                 '--output-format','json','--system-prompt','Reply with exactly READY.']
        result=subprocess.run(command,input='Reply with READY.',text=True,capture_output=True,env=environment,
                              cwd=home,user=spec['uid'],group=spec['gid'],extra_groups=[],timeout=180)
        requests=server.observed[before:]
        private=home/'requests-private.json'
        descriptor=os.open(private,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(descriptor,'w') as stream:stream.write(json.dumps(requests,indent=2)+'\n')
        generation=[row for row in requests if row['path'].startswith('/v1/')]
        record={'tier':tier,'configured_effort':effort,'command':command,'exit_code':result.returncode,
            'stdout_sha256':hashlib.sha256(result.stdout.encode()).hexdigest(),'stdout':result.stdout[-2000:],
            'stderr':result.stderr[-2000:],
            'requests':[{'path':row['path'],'body_sha256':row['body_sha256'],'body_keys':sorted(row['body']),
                'requested_model':row['body'].get('model'),'actual_model':row.get('actual_model'),
                'upstream_status':row.get('upstream_status'),
                'effort_fields':{key:row['body'][key] for key in ('reasoning_effort','reasoning','extra_body','thinking','output_config') if key in row['body']},
                'response_body_sha256':row.get('response_body_sha256')} for row in requests],
            'generation_requests':len(generation)}
        records.append(record)
        (root/'tier-results.json').write_text(json.dumps({'mapping':MAPPING,'tiers':records},indent=2)+'\n')
        print(json.dumps({'tier':tier,'exit_code':result.returncode,'requests':len(requests)}),flush=True)
    status=0
finally:
    server.shutdown()
    (root/'run.done').write_text(str(status)+'\n')
