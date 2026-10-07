# ABOUTME: Measures interruption during a real model request with all installed native hook groups active.
# ABOUTME: Checks completed-response and work state before recovery in a fresh operating-system process.
import argparse
import contextvars
import faulthandler
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import threading
import time


def host(output):
    from hermes_cli.plugins import discover_plugins,unload_plugins
    from gateway.session_context import set_session_vars,clear_session_vars
    from run_agent import AIAgent
    from hermes_cli.lifecycle import finalize_session
    faulthandler.dump_traceback_later(30,repeat=True)
    discover_plugins()
    profile=Path.home()/'.hermes';model=json.loads((profile/'config.yaml').read_text())['model']
    agent=AIAgent(api_key=model['api_key'],base_url=model['base_url'],provider='custom',api_mode='chat_completions',
        model=model['default'],enabled_toolsets=[],quiet_mode=True,platform='cli',max_iterations=4,
        skip_memory=True,skip_background_review=True)
    tokens=set_session_vars(platform='cli',session_id=agent.session_id,session_key=agent.session_id)
    cache=Path.home()/'.claude/LIFEOS/MEMORY/STATE/last-response.txt'
    before=cache.read_bytes() if cache.exists() else None
    results=[]
    def request():results.append(agent.run_conversation('Start your reply with 🧪 Cerebo: and then write a long synthetic count from 1 to 300.'))
    context=contextvars.copy_context()
    thread=threading.Thread(target=lambda:context.run(request))
    try:
        thread.start();deadline=time.monotonic()+100
        while not (output/'actual-request-started').exists() and thread.is_alive() and time.monotonic()<deadline:time.sleep(.01)
        assert (output/'actual-request-started').exists(),'No actual request reached the relay'
        assert agent.interrupt(hard_cancel=True)
        thread.join(timeout=30);assert not thread.is_alive(),'The actual request did not cancel'
        assert len(results)==1 and results[0].get('interrupted') and not results[0].get('completed'),results
        assert (cache.read_bytes() if cache.exists() else None)==before,'Interrupted text replaced completed response'
        finalize_session(session_id=agent.session_id,reason='interrupted',platform='cli')
        (output/'interrupted-result.json').write_text(json.dumps(results[0],indent=2)+'\n')
        (output/'result.json').write_text(json.dumps({'actual_request_started':True,'interrupted':True,
            'completed_response_unchanged':True,'session_finalized':True},indent=2)+'\n')
    finally:
        clear_session_vars(tokens);agent.close();unload_plugins()



def recovery(output):
    from hermes_cli.plugins import discover_plugins,unload_plugins
    from gateway.session_context import set_session_vars,clear_session_vars
    from hermes_cli.lifecycle import finalize_session
    from run_agent import AIAgent
    faulthandler.dump_traceback_later(30,repeat=True)
    discover_plugins();model=json.loads((Path.home()/'.hermes/config.yaml').read_text())['model']
    agent=AIAgent(api_key=model['api_key'],base_url=model['base_url'],provider='custom',api_mode='chat_completions',
        model=model['default'],enabled_toolsets=[],quiet_mode=True,platform='cli',max_iterations=4,
        skip_memory=True,skip_background_review=True)
    tokens=set_session_vars(platform='cli',session_id=agent.session_id,session_key=agent.session_id)
    try:
        result=agent.run_conversation('Start with 🧪 Cerebo: and return PAIR_INTERRUPT_RECOVERED exactly once.')
        assert result.get('completed') and 'PAIR_INTERRUPT_RECOVERED' in result.get('final_response',''),result
        (output/'recovery-result.json').write_text(json.dumps(result,indent=2)+'\n')
        finalize_session(session_id=agent.session_id,reason='prompt_input_exit',platform='cli')
    finally:
        clear_session_vars(tokens);agent.close();unload_plugins()

def run(configuration,output,plugins):
    from paired_response_server import response_handler
    config=json.loads(configuration.read_text());spec=config['hermes'];output.mkdir();os.chown(output,spec['uid'],spec['gid'])
    home=Path(spec['home_root'])/config['installed_home'];profile=home/'.hermes'
    server=ThreadingHTTPServer(('127.0.0.1',0),response_handler(config['model_environment']));server.observed=[]
    threading.Thread(target=server.serve_forever,daemon=True).start()
    configfile=profile/'config.yaml';original=configfile.read_bytes();settings=json.loads(original)
    settings['model']['base_url']=f'http://127.0.0.1:{server.server_port}/v1';configfile.write_text(json.dumps(settings))
    environment={**spec['environment'],'HOME':str(home),'HERMES_HOME':str(profile),'LIFEOS_DIR':str(home/'.claude/LIFEOS'),
        'LIFEOS_HOOK_SETTINGS':str(home/'.claude/settings.json'),'LIFEOS_NOTIFICATION_CHANNEL':'headless'}
    def observe():
        while not any(row['path']=='/v1/chat/completions' for row in server.observed):time.sleep(.01)
        (output/'actual-request-started').touch()
    threading.Thread(target=observe,daemon=True).start()
    try:
        actual=subprocess.run([spec['command'][0],str(Path(__file__).resolve()),'host',str(output)],
            env=environment,cwd=home,user=spec['uid'],group=spec['gid'],extra_groups=[],capture_output=True,text=True,timeout=150)
        (output/'host.stdout').write_text(actual.stdout);(output/'host.stderr').write_text(actual.stderr)
        assert actual.returncode==0,(actual.stdout[-2000:],actual.stderr[-6000:])
        recovered=subprocess.run([spec['command'][0],str(Path(__file__).resolve()),'recovery',str(output)],
            env=environment,cwd=home,user=spec['uid'],group=spec['gid'],extra_groups=[],capture_output=True,text=True,timeout=150)
        (output/'recovery.stdout').write_text(recovered.stdout);(output/'recovery.stderr').write_text(recovered.stderr)
        assert recovered.returncode==0,(recovered.stdout[-2000:],recovered.stderr[-6000:])
        deadline=time.monotonic()+100
        while any('upstream_status' not in row for row in server.observed if row['path']=='/v1/chat/completions') and time.monotonic()<deadline:time.sleep(.05)
        actual_requests=[row for row in server.observed if row['path']=='/v1/chat/completions']
        assert actual_requests and all(row.get('upstream_status')==200 for row in actual_requests),server.observed
        (output/'.done').write_text('0\n')
    finally:
        (output/'wire.json').write_text(json.dumps(server.observed,indent=2)+'\n')
        configfile.write_bytes(original);server.shutdown();server.server_close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','host','recovery']);parser.add_argument('paths',nargs='+',type=Path)
    args=parser.parse_args()
    if args.action=='run':run(*(path.resolve() for path in args.paths))
    elif args.action=='host':host(*args.paths)
    else:recovery(*args.paths)
