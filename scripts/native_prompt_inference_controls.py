# ABOUTME: Measures native prompt naming through actual configured private child inference.
# ABOUTME: Retains successful naming, provider refusal, subsequent prompt behavior, and raw wire data.
import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import subprocess
import threading


def run(configuration, output, plugins):
    from paired_response_server import model_environment, response_handler
    config = json.loads(configuration.read_text())
    spec = config['hermes']
    plugins = plugins.resolve(strict=True)
    output.mkdir()
    endpoint, carrier, _ = model_environment(config['model_environment'])
    bad_environment = output/'refused-environment'
    bad_environment.write_text('\n'.join(key+'='+shlex.quote(value) for key,value in {
        'ANTHROPIC_BASE_URL':endpoint.geturl(),'ANTHROPIC_MODEL':carrier,
        'ANTHROPIC_AUTH_TOKEN':'PAIR_INVALID_AUTHORIZATION'}.items())+'\n')
    bad_environment.chmod(0o600)
    servers = []
    results = []
    try:
        for mode, model_env in (('success',config['model_environment']),('provider-failure',bad_environment)):
            server = ThreadingHTTPServer(('127.0.0.1',0),response_handler(model_env))
            server.observed = []
            threading.Thread(target=server.serve_forever,daemon=True).start()
            servers.append((mode,server))
            home = Path(spec['home_root'])/(output.name+'-'+mode)
            root = home/'.claude'
            root.mkdir(parents=True)
            (root/'hooks').symlink_to(Path(spec['hook_root'])/'hooks',target_is_directory=True)
            (root/'LIFEOS').mkdir()
            (root/'LIFEOS/TOOLS').symlink_to(Path(spec['hook_root'])/'LIFEOS/TOOLS',target_is_directory=True)
            (root/'settings.json').write_text('{}')
            (root/'LIFEOS/MEMORY/OBSERVABILITY').mkdir(parents=True)
            profile = home/'.hermes'
            profile.mkdir()
            (profile/'plugins').symlink_to(plugins,target_is_directory=True)
            (profile/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['lifeos-hook-bridge']},
                'model':{'provider':'custom','base_url':f'http://127.0.0.1:{server.server_port}/v1',
                    'api_key':'PAIR_NATIVE_PROMPT','default':'lifecycle-fixture','api_mode':'chat_completions'},
                'agent':{'reasoning_effort':'medium'}}))
            binaries = home/'bin'
            binaries.mkdir()
            hermes = binaries/'hermes'
            hermes.write_text('#!/bin/sh\nexec '+shlex.quote(spec['command'][0])+' -m hermes_cli.main \"$@\"\n')
            hermes.chmod(0o755)
            hook_env = home/'hook-model.env'
            hook_env.write_text('ANTHROPIC_MODEL=lifecycle-fixture\n')
            hook_env.chmod(0o600)
            for item in (home,*home.rglob('*')):
                if not item.is_symlink():
                    os.chown(item,spec['uid'],spec['gid'])
            environment = {**spec['environment'],'HOME':str(home),'HERMES_HOME':str(profile),
                'LIFEOS_DIR':str(root/'LIFEOS'),'LIFEOS_HOOK_SETTINGS':str(root/'settings.json'),
                'LIFEOS_NOTIFICATION_CHANNEL':'headless','LIFEOS_ACCOUNT_HOME':str(home),
                'LIFEOS_HOOK_MODEL_ENV':str(hook_env),'PYTHONUNBUFFERED':'1',
                'PATH':str(binaries)+os.pathsep+str(plugins/'lifeos-hook-bridge/bin')+os.pathsep+spec['environment']['PATH'],
                'LIFEOS_MODEL_TIER_MAP':json.dumps({name:{'provider':'custom','model':'lifecycle-fixture','effort':effort}
                    for name,effort in (('haiku','low'),('sonnet','medium'),('opus','xhigh'),('fable','xhigh'))})}
            session = 'native-prompt-'+mode
            commands = []
            for index,prompt in enumerate(('Build the synthetic fixture dashboard for the laboratory','Thanks')):
                before_requests = len([r for r in server.observed if r.get('upstream_status') is not None])
                actual = subprocess.run(['bun',str(root/'hooks/PromptProcessing.hook.ts')],
                    input=json.dumps({'hook_event_name':'UserPromptSubmit','session_id':session,'prompt':prompt}),
                    env=environment,cwd=home,user=spec['uid'],group=spec['gid'],extra_groups=[],
                    text=True,capture_output=True,timeout=90)
                (output/(mode+'-'+str(index)+'.stdout')).write_text(actual.stdout)
                (output/(mode+'-'+str(index)+'.stderr')).write_text(actual.stderr)
                assert actual.returncode == 0, actual.stderr
                names = json.loads((root/'LIFEOS/MEMORY/STATE/session-names.json').read_text())
                assert names.get(session), names
                telemetry = [json.loads(line) for line in (root/'LIFEOS/MEMORY/OBSERVABILITY/prompt-processing.jsonl').read_text().splitlines()]
                requests = [r for r in server.observed if r.get('upstream_status') is not None]
                if index == 0:
                    assert len(requests)==1, requests
                    if mode == 'success':
                        assert requests[0]['upstream_status']==200 and telemetry[-1]['source']=='inference', telemetry
                    else:
                        assert requests[0]['upstream_status'] in (401,403) and telemetry[-1]['source']=='inference-failed', telemetry
                    prior_name = names[session]
                else:
                    assert names[session] == prior_name, names
                    assert len(requests)==before_requests, 'A subsequent prompt repeats title inference'
                commands.append({'command':actual.args,'session_name':names[session],
                    'telemetry':telemetry,'inference_requests':len(requests),'returncode':actual.returncode})
            results.append({'mode':mode,'commands':commands})
        (output/'result.json').write_text(json.dumps(results,indent=2)+'\n')
        (output/'.done').write_text('0\n')
    finally:
        for mode,server in servers:
            (output/(mode+'-wire.json')).write_text(json.dumps(server.observed,indent=2)+'\n')
            server.shutdown()
            server.server_close()
        bad_environment.unlink(missing_ok=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('configuration',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('plugins',type=Path)
    args = parser.parse_args()
    run(args.configuration,args.output,args.plugins)
