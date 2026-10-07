# ABOUTME: Measures complete installed hook groups through real persistent Hermes conversations.
# ABOUTME: Retains actual requests, hook outcomes, file effects, questions, and resumed delivery.
import argparse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
from queue import Empty, Queue
import shlex
import subprocess
import sys
import threading
import time


def host(output):
    from hermes_cli.plugins import discover_plugins, unload_plugins
    from hermes_cli.lifecycle import finalize_session
    from gateway.session_context import set_session_vars, clear_session_vars
    from run_agent import AIAgent
    from tools import clarify_gateway
    from tools.process_registry import process_registry

    discover_plugins()
    modules=[module for module in sys.modules.values() if getattr(module,'__file__',None)
             and str(module.__file__).endswith('/lifeos-hook-bridge/bridge.py')]
    assert len(modules)==1, [module.__name__ for module in modules]
    HookBridge=modules[0].HookBridge
    lock = threading.Lock()
    trace = output/'hook-trace.jsonl'
    original = HookBridge._run_command
    original_async = HookBridge._run_async

    def measure(self, event, command, payload, timeout, environment, process_cwd):
        started = time.monotonic()
        result = original(self, event, command, payload, timeout, environment, process_cwd)
        row = {'event':event,'command':command,'payload':payload,'elapsed_seconds':time.monotonic()-started,
               'returncode':result.returncode if result else None,
               'stdout':result.stdout if result else '', 'stderr':result.stderr if result else ''}
        with lock:
            with trace.open('a') as stream:stream.write(json.dumps(row)+'\n')
        return result

    def measure_async(self,command,payload,environment,process_cwd):
        with lock:
            with trace.open('a') as stream:stream.write(json.dumps({'event':payload.get('hook_event_name'),
                'command':command,'payload':payload,'asynchronous':True,'state':'queued'})+'\n')
        return original_async(self,command,payload,environment,process_cwd)
    HookBridge._run_command = measure
    HookBridge._run_async = measure_async
    model = json.loads((Path.home()/'.hermes/config.yaml').read_text())['model']
    discover_plugins()
    answers = []

    def answer(question, choices, multi_select=False):
        identifier = 'installed-fixture-question'
        clarify_gateway.register(identifier,'installed-fixture-chat',question,choices,multi_select)
        assert clarify_gateway.resolve_gateway_clarify(identifier,'PAIR_INSTALLED_BLUE')
        resolved = clarify_gateway.wait_for_response(identifier,5)
        clarify_gateway.clear_session('installed-fixture-chat')
        answers.append({'question':question,'choices':choices,'answer':resolved})
        return resolved

    agent = AIAgent(api_key=model['api_key'],base_url=model['base_url'],provider='custom',
        api_mode='chat_completions',model=model['default'],enabled_toolsets=['terminal','file','clarify','delegation'],
        quiet_mode=True,platform='cli',clarify_callback=answer,max_iterations=12,
        skip_memory=True,skip_background_review=True,reasoning_config={'effort':'medium'},
        ephemeral_system_prompt='Run the requested isolated acceptance controls. Use only the requested tools. '
        'Report actual results. Keep the requested format and do not perform unrelated maintenance.')
    tokens = set_session_vars(platform='cli',session_id=agent.session_id,session_key=agent.session_id,async_delivery=True)
    fixture = Path.home()/'Projects/installed-fixture/fixture.txt'
    root=Path(os.environ['LIFEOS_DIR'])
    state=root/'MEMORY/STATE/work.json'
    slug='synthetic-installed-completion'
    isa=root/'MEMORY/WORK'/slug/'ISA.md';isa.parent.mkdir(parents=True,exist_ok=True)
    started=datetime.now(timezone.utc).isoformat()
    content='---\ntitle: Synthetic installed completion\nstarted: '+started+'\nphase: build\nprogress: 0/1\n---\n\n## Claims\n- [ ] ISC-1: Verify the synthetic file content.\n'
    isa.write_text(content)
    registry=json.loads(state.read_text()) if state.exists() else {'sessions':{}}
    registry.setdefault('sessions',{})[slug]={'sessionUUID':agent.session_id,'phase':'build','task':'Synthetic installed completion',
                                          'started':started,'isa':str(isa)}
    state.write_text(json.dumps(registry))
    turns = []
    history = []
    try:
        prompts = [
            'Use read_file to read '+str(fixture)+'. Use write_file to replace its content with exactly '
            'PAIR_INSTALLED_FILE\n. Then use terminal with command cat '+str(fixture)+'. '
            'Report the actual file contents briefly. Start your final reply with 🧪 Cerebo:',
            'Use clarify exactly once to ask "Choose the synthetic mode" with choices PAIR_INSTALLED_BLUE '
            'and PAIR_INSTALLED_RED. Wait for the answer. Then reply with the chosen value. Start with 🧪 Cerebo:',
            'Use terminal exactly once with command cat '+str(fixture.parent/'absent-failure-fixture.txt')+'. Report the actual failure. '
            'Do not claim success or retry. Start your final reply with 🧪 Cerebo:',
            'Use terminal exactly once with command printf PAIR_INSTALLED_RECOVERY. '
            'Report the actual successful output. Start your final reply with 🧪 Cerebo:',
            'Use delegate_task once with two tasks. Their goals are "Reply with PAIR_INSTALLED_CHILD_A" '
            'and "Reply with PAIR_INSTALLED_CHILD_B". Omit background. End this turn after the dispatch acknowledgment. '
            'Start your final reply with 🧪 Cerebo:',
            'Use read_file to read '+str(fixture)+' and '+str(isa)+' in the same turn. '
            'Report the actual file marker and the current ISA phase. Start your final reply with 🧪 Cerebo:',
            'Use terminal once with the exact command false && gh repo create synthetic-denied-fixture --public. '
            'This is a denial control. Report the actual guard refusal. Do not retry or request approval. '
            'Start your final reply with 🧪 Cerebo:',
            'Use read_file to read '+str(isa)+'. Then use write_file to replace it with this exact content:\n'+
            content.replace('phase: build','phase: complete').replace('progress: 0/1','progress: 1/1').replace('- [ ]','- [x]')+
            '\nReport that the synthetic criterion is closed. Start your final reply with 🧪 Cerebo:',
        ]
        for prompt in prompts:
            result = agent.run_conversation(prompt,conversation_history=history)
            history = result["messages"]
            turns.append(result)
            (output/'turns.json').write_text(json.dumps(turns,indent=2)+'\n')
            assert result.get('completed') and not result.get('failed'),result
            assert result.get('final_response'),result
            if len(turns)==5:
                from hermes_cli.cli_process_notifications import CLIProcessNotificationsMixin
                from tools.async_delegation import get_durable_delegation
                deadline=time.monotonic()+100
                completion=None
                while time.monotonic()<deadline:
                    try:event=process_registry.completion_queue.get(timeout=.1)
                    except Empty:continue
                    if event.get('type')=='async_delegation' and not event.get('task_failure_notice'):
                        completion=event;break
                assert completion and all(marker in json.dumps(completion) for marker in
                    ('PAIR_INSTALLED_CHILD_A','PAIR_INSTALLED_CHILD_B')),completion
                class Consumer(CLIProcessNotificationsMixin):
                    def __init__(self):
                        self.session_id=agent.session_id
                        self._pending_input=Queue()
                consumer=Consumer();process_registry.completion_queue.put(completion)
                consumer._drain_process_notifications('installed-fixture-consumer')
                notification=consumer._pending_input.get_nowait()
                delivered=agent.run_conversation(notification,conversation_history=history)
                history=delivered['messages']
                assert delivered.get('completed') and all(marker in delivered.get('final_response','') for marker in
                    ('PAIR_INSTALLED_CHILD_A','PAIR_INSTALLED_CHILD_B')),delivered
                assert get_durable_delegation(completion['delegation_id'])['delivery_state']=='delivered'
                (output/'delegation-delivery.json').write_text(json.dumps({'completion':completion,'delivered':delivered},indent=2)+'\n')
        assert fixture.read_text().strip()=='PAIR_INSTALLED_FILE',fixture.read_text()
        assert len(answers)==1 and answers[0]['answer']=='PAIR_INSTALLED_BLUE',answers
        assert 'PAIR_INSTALLED_BLUE' in turns[1]['final_response'],turns[1]
        assert 'PAIR_INSTALLED_RECOVERY' in turns[3]['final_response'],turns[3]
        failures=[json.loads(row['content']) for row in turns[2]['messages'] if row.get('role')=='tool'
                  and isinstance(row.get('content'),str) and row['content'].startswith('{')]
        assert any(row.get('exit_code')==1 and not row.get('approval_pending') for row in failures),failures
        denial=[row for row in turns[6]['messages'] if row.get('role')=='tool' and
                ('blocked' in str(row.get('content')).lower() or 'denied' in str(row.get('content')).lower())]
        assert denial,turns[6]
        assert 'phase: complete' in isa.read_text() and '- [x] ISC-1' in isa.read_text(),isa.read_text()
        session = agent.session_id
        history = turns[-1]['messages']
        finalize_session(session_id=session,reason='prompt_input_exit',platform='cli')
        agent.close();unload_plugins()
        learnings=[path for path in (root/'MEMORY/LEARNING').rglob('*_work_*.md') if session in path.read_text()]
        assert len(learnings)==1,[str(path) for path in learnings]
        deadline=time.monotonic()+8
        page=isa.with_suffix('.html')
        while not page.exists() and time.monotonic()<deadline:time.sleep(.05)
        assert page.exists() and 'Synthetic installed completion' in page.read_text(),str(page)
        registry=json.loads(state.read_text())
        assert registry['sessions'][slug]['phase']=='complete',registry
        names=root/'MEMORY/STATE/session-names.json'
        assert not names.exists() or session not in json.loads(names.read_text()),str(names)
        children=[json.loads(line) for line in trace.read_text().splitlines()
                  if 'AgentInvocation.hook.ts' in line]
        assert len([row for row in children if row['event']=='PreToolUse'])==2,children
        assert len([row for row in children if row['event']=='PostToolUse'])==2,children
        (output/'restart-input.json').write_text(json.dumps({'session_id':session,'messages':history,'answers':answers},indent=2)+'\n')
        (output/'host-result.json').write_text(json.dumps({'session_id':session,'turns':len(turns),
            'file_content':fixture.read_text(),'answers':answers,'learning':str(learnings[0]),
            'isa_rendered':True,'registry_completed':True,'session_name_cleaned':True,'child_start_count':2,'child_stop_count':2,
            'denial_observed':True,'completed':True},indent=2)+'\n')
    finally:
        clear_session_vars(tokens);agent.close();unload_plugins();HookBridge._run_command=original;HookBridge._run_async=original_async


def resume(output):
    from hermes_cli.plugins import discover_plugins, unload_plugins
    from hermes_cli.lifecycle import finalize_session
    from gateway.session_context import set_session_vars, clear_session_vars
    from run_agent import AIAgent
    previous = json.loads((output/'restart-input.json').read_text())
    model = json.loads((Path.home()/'.hermes/config.yaml').read_text())['model']
    discover_plugins()
    agent = AIAgent(api_key=model['api_key'],base_url=model['base_url'],provider='custom',
        api_mode='chat_completions',model=model['default'],enabled_toolsets=[],quiet_mode=True,
        platform='cli',session_id=previous['session_id'],max_iterations=4,skip_memory=True,
        skip_background_review=True,ephemeral_system_prompt='Report the previous synthetic mode from the supplied conversation.')
    tokens = set_session_vars(platform='cli',session_id=agent.session_id,session_key=agent.session_id)
    try:
        result=agent.run_conversation('Which synthetic mode did I choose earlier? Start with 🧪 Cerebo:',
                                      conversation_history=previous['messages'])
        (output/'resume-result.json').write_text(json.dumps(result,indent=2)+'\n')
        assert result.get('completed') and 'PAIR_INSTALLED_BLUE' in result.get('final_response',''),result
        finalize_session(session_id=agent.session_id,reason='prompt_input_exit',platform='cli')
    finally:
        clear_session_vars(tokens);agent.close();unload_plugins()


def run(configuration, output, plugins):
    from paired_response_server import response_handler
    config=json.loads(configuration.read_text());spec=config['hermes']
    home=Path(spec['home_root'])/config.get('installed_home','full-installed-pinned');root=home/'.claude'
    output.mkdir()
    server=ThreadingHTTPServer(('127.0.0.1',0),response_handler(config['model_environment']))
    server.observed=[]
    threading.Thread(target=server.serve_forever,daemon=True).start()
    profile=home/'.hermes';profile.mkdir(exist_ok=True)
    if not (profile/'plugins').exists():
        (profile/'plugins').symlink_to(plugins.resolve(strict=True),target_is_directory=True)
    (profile/'SOUL.md').write_text('Synthetic complete installed-session fixture.\n')
    endpoint=f'http://127.0.0.1:{server.server_port}/v1'
    (profile/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['lifeos-hook-bridge']},
        'model':{'provider':'custom','base_url':endpoint,'api_key':'PAIR_INSTALLED_SESSION',
                 'default':'lifecycle-fixture','api_mode':'chat_completions'},'agent':{'reasoning_effort':'medium'},
        'terminal':{'env_type':'local'},'approvals':{'mode':'manual'}}))
    binaries=home/'bin';binaries.mkdir(exist_ok=True)
    (binaries/'hermes').write_text('#!/bin/sh\nexec '+shlex.quote(spec['command'][0])+' -m hermes_cli.main "$@"\n')
    (binaries/'hermes').chmod(0o755)
    hook_env=home/'hook-model.env';hook_env.write_text('ANTHROPIC_MODEL=lifecycle-fixture\n');hook_env.chmod(0o600)
    user_settings=root/'settings.user.json'
    user=json.loads(user_settings.read_text()) if user_settings.exists() else {}
    user.setdefault('permissions',{}).setdefault('allow',[]).extend(['Bash','Read','Write','Edit'])
    user_settings.write_text(json.dumps(user))
    review=root/'LIFEOS/USER/CONFIG/memory-review.json'
    review.write_text(json.dumps({'turn_threshold':99,'min_minutes_between':30}));os.chown(review,spec['uid'],spec['gid'])
    project=home/'Projects/installed-fixture';project.mkdir(parents=True,exist_ok=True)
    (project/'fixture.txt').write_text('PAIR_INITIAL_FILE\n')
    environment={**spec['environment'],'HOME':str(home),'HERMES_HOME':str(profile),
        'LIFEOS_DIR':str(root/'LIFEOS'),'LIFEOS_HOOK_SETTINGS':str(root/'settings.json'),
        'LIFEOS_NOTIFICATION_CHANNEL':'headless','LIFEOS_ACCOUNT_HOME':str(home),
        'LIFEOS_HOOK_MODEL_ENV':str(hook_env),'HERMES_WRITE_SAFE_ROOT':str(home),'TERMINAL_CWD':str(project),
        'PATH':str(binaries)+':'+str(plugins/'lifeos-hook-bridge/bin')+':'+spec['environment']['PATH'],
        'LIFEOS_MODEL_TIER_MAP':json.dumps({name:{'provider':'custom','model':'lifecycle-fixture','effort':effort}
            for name,effort in [('haiku','low'),('sonnet','medium'),('opus','xhigh'),('fable','xhigh')]})}
    for item in [home,output,profile,user_settings,hook_env,project,*profile.rglob('*'),binaries,*binaries.rglob('*'),*project.rglob('*')]:
        if not item.is_symlink():os.chown(item,spec['uid'],spec['gid'])
    import re
    declaration=(root/'LIFEOS/PULSE/lib/modules.ts').read_text().split('export const MODULE_DEFAULTS')[1].split('}')[0]
    pulse_settings=root/'LIFEOS/PULSE/PULSE.toml'
    pulse_settings.write_text('port = 31337\n[hooks]\nenabled = true\n[modules]\n'+
        ''.join(name+' = false\n' for name in re.findall(r'\b(\w+): (?:true|false)',declaration)))
    os.chown(pulse_settings,spec['uid'],spec['gid'])
    with (output/'pulse.log').open('w') as pulse_log:
        pulse=subprocess.Popen(['bun',str(root/'LIFEOS/PULSE/pulse.ts')],env=environment,
            user=spec['uid'],group=spec['gid'],extra_groups=[],stdout=pulse_log,stderr=subprocess.STDOUT)
    from urllib.request import urlopen
    from urllib.error import URLError
    try:
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            assert pulse.poll() is None,(output/'pulse.log').read_text()
            try:
                with urlopen('http://127.0.0.1:31337/api/pulse/health',timeout=2):break
            except URLError:time.sleep(.05)
        else:raise AssertionError((output/'pulse.log').read_text())
        results=[]
        for mode in ['host','resume']:
            result=subprocess.run([spec['command'][0],str(Path(__file__).resolve()),mode,str(output)],
                env=environment,cwd=project,user=spec['uid'],group=spec['gid'],extra_groups=[],
                capture_output=True,text=True,timeout=600)
            (output/(mode+'.stdout')).write_text(result.stdout)
            (output/(mode+'.stderr')).write_text(result.stderr)
            results.append({'mode':mode,'exit_code':result.returncode})
            (output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
            assert result.returncode==0,(mode,result.stdout[-4000:],result.stderr[-8000:])
        (output/'.done').write_text('0\n')
    finally:
        (output/'wire.json').write_text(json.dumps(server.observed,indent=2)+'\n')
        server.shutdown();server.server_close()
        if pulse.poll() is None:
            pulse.terminate()
            try:pulse.wait(timeout=5)
            except subprocess.TimeoutExpired:pulse.kill();pulse.wait(timeout=5)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['run','host','resume'])
    parser.add_argument('paths',nargs='+',type=Path)
    args=parser.parse_args()
    if args.action=='run':run(*args.paths)
    elif args.action=='host':host(*args.paths)
    else:resume(*args.paths)
