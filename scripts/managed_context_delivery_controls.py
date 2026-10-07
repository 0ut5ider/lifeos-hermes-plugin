# ABOUTME: Measures native startup source admission through actual private Hermes model requests.
# ABOUTME: Uses synthetic work titles and refuses delivery after caller or destination revocation.
import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading
from datetime import datetime


def host(output, mode):
    from hermes_cli.plugins import discover_plugins,unload_plugins
    from gateway.session_context import set_session_vars,clear_session_vars
    from run_agent import AIAgent
    from lifeos_hook_bridge.memory_service import MemoryConfiguration
    home=Path.home();profile=home/'.hermes';configuration=MemoryConfiguration(profile/'lifeos-memory.json')
    discover_plugins()
    model=json.loads((profile/'config.yaml').read_text())['model']
    agent=AIAgent(api_key=model['api_key'],base_url=model['base_url'],provider='custom',api_mode='chat_completions',
        model=model['default'],enabled_toolsets=[],quiet_mode=True,platform='api_server',skip_memory=True,
        skip_background_review=True,max_iterations=4,ephemeral_system_prompt='Read the admitted synthetic startup context. '
        'Report the requested work title exactly. Do not invent unavailable context.')
    tokens=set_session_vars(platform='api_server',user_id='100',chat_id='200' if mode=='admitted' else 'unregistered',
        chat_type='private',session_id=agent.session_id,session_key=agent.session_id,async_delivery=False)
    try:
        result=agent.run_conversation('What is the current synthetic active-work title in your startup context?')
        (output/(mode+'-result.json')).write_text(json.dumps(result,indent=2)+'\n')
        if mode=='admitted':
            assert result.get('completed') and 'PAIR_ALLOWED_ACTIVE_WORK' in result.get('final_response',''),result
            configuration.update(lambda value:value['accounts'].pop('api_server:100'))
            revoked=agent.run_conversation('Repeat the current work title.',conversation_history=result['messages'])
            (output/'revoked-result.json').write_text(json.dumps(revoked,indent=2)+'\n')
            assert revoked.get('turn_exit_reason')=='prompt_blocked' and revoked.get('api_calls')==0 and 'PAIR_ALLOWED_ACTIVE_WORK' not in revoked.get('final_response',''),revoked
        else:
            assert result.get('turn_exit_reason')=='prompt_blocked' and result.get('api_calls')==0 and 'PAIR_ALLOWED_ACTIVE_WORK' not in result.get('final_response',''),result
    finally:
        clear_session_vars(tokens);agent.close();unload_plugins()


def run(configuration,output,plugins):
    from paired_response_server import response_handler
    from lifeos_hook_bridge.memory_context import route_identity
    from lifeos_hook_bridge.memory_service import MemoryConfiguration
    config=json.loads(configuration.read_text());spec=config['hermes'];output.mkdir()
    server=ThreadingHTTPServer(('127.0.0.1',0),response_handler(config['model_environment']));server.observed=[]
    threading.Thread(target=server.serve_forever,daemon=True).start()
    endpoint=f'http://127.0.0.1:{server.server_port}/v1';results=[]
    try:
        for mode in ['admitted','unregistered']:
            home=Path(spec['home_root'])/(output.name+'-'+mode);root=home/'.claude';root.mkdir(parents=True)
            (root/'hooks').symlink_to(Path(spec['hook_root'])/'hooks',target_is_directory=True)
            (root/'LIFEOS').mkdir()
            (root/'LIFEOS/TOOLS').symlink_to(Path(spec['hook_root'])/'LIFEOS/TOOLS',target_is_directory=True)
            data=home/'.config/LIFEOS/USER';(data/'MEMORY/OBSERVABILITY').mkdir(parents=True)
            (root/'LIFEOS/USER').symlink_to(data,target_is_directory=True);(root/'LIFEOS/MEMORY').symlink_to(data/'MEMORY',target_is_directory=True)
            for name,filename in [('PRINCIPAL','PRINCIPAL_MEMORY.md'),('DIGITAL_ASSISTANT','DA_MEMORY.md')]:
                p=data/name/filename;p.parent.mkdir();p.write_text('<!-- BEGIN ENTRIES -->\n<!-- END ENTRIES -->\n')
            work=data/'MEMORY/WORK'/(datetime.now().strftime('%Y%m%d-%H%M%S')+'_synthetic');work.mkdir(parents=True)
            (work/'ISA.md').write_text('---\ntitle: PAIR_ALLOWED_ACTIVE_WORK\nphase: climbing\nprogress: 0/1\n---\n')
            profile=home/'.hermes';profile.mkdir();(profile/'plugins').symlink_to(plugins.resolve(strict=True),target_is_directory=True)
            (profile/'SOUL.md').write_text('Synthetic managed startup fixture.\n')
            (profile/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['lifeos-hook-bridge']},
                'model':{'provider':'custom','api_mode':'chat_completions','base_url':endpoint,'api_key':'PAIR_MANAGED_DELIVERY',
                         'default':'lifecycle-fixture'},'agent':{'reasoning_effort':'medium'}}))
            path=profile/'lifeos-memory.json'
            MemoryConfiguration(path).save({'version':1,'root':str(root),'principal':'owner','ownership_enabled':True,
                'accounts':{'api_server:100':'owner'},'destinations':{'api_server:200':{'visibility':'private','participants':['owner'],
                'read':['principal','assistant','project'],'write':['principal','assistant','project'],'projects':['*'],
                'model_routes':[route_identity('custom','lifecycle-fixture',endpoint,'chat_completions')]}}})
            (data/'CONFIG').mkdir();connector=data/'CONFIG/memory-access.json'
            connector.write_text(json.dumps({'version':1,'command':[spec['command'][0],
                str(plugins.resolve(strict=True)/'lifeos-hook-bridge/memory_rpc.py'),'--configuration',str(path)]}));connector.chmod(0o600)
            (root/'settings.json').write_text(json.dumps({'hooks':{'SessionStart':[{'hooks':[{'type':'command',
                'command':'bun '+str(root/'hooks/LoadContext.hook.ts')}]}]}}))
            for p in [home,output,*home.rglob('*')]:
                if not p.is_symlink():os.chown(p,spec['uid'],spec['gid'])
            environment={**spec['environment'],'HOME':str(home),'HERMES_HOME':str(profile),'LIFEOS_DIR':str(root/'LIFEOS'),
                'LIFEOS_HOOK_SETTINGS':str(root/'settings.json'),'LIFEOS_NOTIFICATION_CHANNEL':'headless',
                'PYTHONPATH':str(plugins.resolve(strict=True).parent)+':'+spec['environment']['PYTHONPATH']}
            before=len(server.observed)
            actual=subprocess.run([spec['command'][0],str(Path(__file__).resolve()),'host',str(output),mode],
                env=environment,cwd=home,user=spec['uid'],group=spec['gid'],extra_groups=[],text=True,capture_output=True,timeout=150)
            (output/(mode+'.stdout')).write_text(actual.stdout);(output/(mode+'.stderr')).write_text(actual.stderr)
            assert actual.returncode==0,(mode,actual.stderr[-8000:])
            wire=[row for row in server.observed[before:] if row.get('upstream_status') is not None]
            if mode=='admitted':assert len(wire)==1 and wire[0]['upstream_status']==200 and 'PAIR_ALLOWED_ACTIVE_WORK' in json.dumps(wire[0]['body']),wire
            else:assert not wire,wire
            results.append({'mode':mode,'requests':len(wire),'exit_code':actual.returncode})
        (output/'result.json').write_text(json.dumps(results,indent=2)+'\n');(output/'.done').write_text('0\n')
    finally:
        (output/'wire.json').write_text(json.dumps(server.observed,indent=2)+'\n');server.shutdown();server.server_close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','host']);parser.add_argument('paths',nargs='+')
    args=parser.parse_args()
    if args.action=='run':run(*(Path(p) for p in args.paths))
    else:host(Path(args.paths[0]),args.paths[1])
