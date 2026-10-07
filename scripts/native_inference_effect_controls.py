# ABOUTME: Runs native lifecycle inference through the configured private model.
# ABOUTME: Retains actual routing, model output, and governed proposal publication in disposable homes.
import argparse
from dataclasses import asdict
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import subprocess
import threading


def run(configuration, output, plugins, modes):
    from paired_response_server import response_handler
    from lifeos_hook_bridge.memory_context import route_identity
    from lifeos_hook_bridge.memory_runtime import MemoryRuntime
    from lifeos_hook_bridge.memory_service import MemoryConfiguration
    config = json.loads(configuration.read_text())
    spec = config['hermes']
    plugins = plugins.resolve(strict=True)
    source = Path(spec['hook_root'])
    output.mkdir()
    server = ThreadingHTTPServer(('127.0.0.1', 0), response_handler(config['model_environment']))
    server.observed = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    endpoint = f'http://127.0.0.1:{server.server_port}/v1'
    results = []
    try:
        for mode in modes:
            home = Path(spec['home_root'])/(output.name+'-'+mode)
            root = home/'.claude'
            (root/'hooks').mkdir(parents=True)
            for item in (source/'hooks').iterdir():
                (root/'hooks'/item.name).symlink_to(item, target_is_directory=item.is_dir())
            (root/'LIFEOS').mkdir()
            for name in ('TOOLS','PULSE'):
                (root/'LIFEOS'/name).symlink_to(source/'LIFEOS'/name,target_is_directory=True)
            data = home/'.config/LIFEOS/USER'
            (data/'MEMORY/OBSERVABILITY').mkdir(parents=True)
            (root/'LIFEOS/USER').symlink_to(data,target_is_directory=True)
            (root/'LIFEOS/MEMORY').symlink_to(data/'MEMORY',target_is_directory=True)
            for name,filename in (('PRINCIPAL','PRINCIPAL_MEMORY.md'),('DIGITAL_ASSISTANT','DA_MEMORY.md')):
                target=data/name/filename
                target.parent.mkdir()
                target.write_text('<!-- BEGIN ENTRIES -->\n<!-- END ENTRIES -->\n')
            (data/'CONFIG').mkdir()
            (root/'settings.json').write_text('{}')
            profile=home/'.hermes';profile.mkdir()
            (profile/'SOUL.md').write_text('Synthetic native inference fixture.\n')
            (profile/'plugins').symlink_to(plugins,target_is_directory=True)
            (profile/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['lifeos-hook-bridge']},
                'model':{'provider':'custom','base_url':endpoint,'api_key':'PAIR_NATIVE_EFFECT',
                         'default':'lifecycle-fixture','api_mode':'chat_completions'},
                'agent':{'reasoning_effort':'medium'}}))
            binaries=home/'bin';binaries.mkdir()
            launcher=binaries/'hermes'
            launcher.write_text('#!/bin/sh\nexec '+shlex.quote(spec['command'][0])+' -m hermes_cli.main "$@"\n')
            launcher.chmod(0o755)
            hook_env=home/'hook-model.env';hook_env.write_text('ANTHROPIC_MODEL=lifecycle-fixture\n');hook_env.chmod(0o600)
            environment={**spec['environment'],'HOME':str(home),'HERMES_HOME':str(profile),
                'LIFEOS_DIR':str(root/'LIFEOS'),'LIFEOS_HOOK_SETTINGS':str(root/'settings.json'),
                'LIFEOS_NOTIFICATION_CHANNEL':'headless','LIFEOS_ACCOUNT_HOME':str(home),
                'LIFEOS_HOOK_MODEL_ENV':str(hook_env),'BUN_CONFIG_NO_AUTO_INSTALL':'1',
                'PATH':str(binaries)+os.pathsep+str(plugins/'lifeos-hook-bridge/bin')+os.pathsep+spec['environment']['PATH'],
                'LIFEOS_MODEL_TIER_MAP':json.dumps({name:{'provider':'custom','model':'lifecycle-fixture','effort':effort}
                    for name,effort in (('haiku','low'),('sonnet','medium'),('opus','xhigh'),('fable','xhigh'))})}
            transcript=home/'synthetic-transcript.jsonl'
            messages=[{'type':'user','message':{'role':'user','content':
                'Always confirm before deploying to the synthetic laboratory. This is a permanent operational rule, '
                'and it belongs in the operational rules file. The assistant must request my approval before each '
                'deployment. The previous answer ignored this rule and claimed success after a failing command.'}},
                {'type':'assistant','message':{'role':'assistant','content':[{'type':'tool_use','id':'failed-command',
                  'name':'Bash','input':{'command':"sh -c 'exit 7'"}},{'type':'text','text':'Done. The command succeeded.'}]}},
                {'type':'user','message':{'role':'user','content':'2/10. You claimed success after the command failed.'}},
                {'type':'assistant','message':{'role':'assistant','content':'The command failed with exit status 7.'}}]
            transcript.write_text(''.join(json.dumps(row)+'\n' for row in messages))
            if mode=='failure-capture':
                cache=data/'MEMORY/STATE/last-response.txt';cache.parent.mkdir(parents=True)
                cache.write_text('The synthetic command succeeded, despite exit status 7.')
                command=['bun',str(root/'hooks/SatisfactionCapture.hook.ts')]
            elif mode=='capability-audit':
                # The native sweep uses the last genuine user prompt length, not monetary cost.
                transcript.write_text(''.join(json.dumps(row)+'\n' for row in messages[:2]))
                command=['bun',str(root/'hooks/SpendAuditor.hook.ts'),'--audit',str(transcript),'capability-control']
            elif mode=='documentation':
                changed=root/'hooks/FixtureControl.hook.ts'
                changed.write_text('// ABOUTME: Reports actual file-operation failures.\n// ABOUTME: Emits a warning for exit status 7.\nconsole.error("Command failed with exit status 7");\n')
                document=root/'LIFEOS/DOCUMENTATION/Hooks/HookSystem.md';document.parent.mkdir(parents=True)
                document.write_text('# Hook system\n\n## FixtureControl\nFixtureControl.hook.ts reports all command failures as successful.\n')
                transcript.write_text(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','id':'source-change',
                    'name':'Edit','input':{'file_path':str(changed),'old_string':'success','new_string':'failure'}}]}})+'\n')
                driver=home/'doc-control.ts'
                driver.write_text('import {handleDocCrossRefIntegrity} from '+json.dumps(str(source/'hooks/handlers/DocCrossRefIntegrity.ts'))+';\n'
                    'await handleDocCrossRefIntegrity({} as any,'+json.dumps({'session_id':'doc-control',
                        'hook_event_name':'SessionEnd','transcript_path':str(transcript)})+');\n')
                environment['DOCINTEGRITY_INFERENCE']='1'
                command=['bun',str(driver)]
            else:
                target=data/'CONFIG/OPERATIONAL_RULES.md';target.write_text('# Operational rules\n')
                configuration_path=profile/'lifeos-memory.json'
                route=route_identity('custom','lifecycle-fixture',endpoint,'chat_completions')
                MemoryConfiguration(configuration_path).save({'version':1,'root':str(root),'principal':'owner','ownership_enabled':True,
                    'accounts':{'chat-a:100':'owner'},'destinations':{'chat-a:200':{'visibility':'private',
                    'participants':['owner'],'read':['principal','assistant','project'],
                    'write':['principal','assistant','project'],'projects':['*'],'model_routes':[route],
                    'proposals':['create','review']}}})
                connector=data/'CONFIG/memory-access.json'
                connector.write_text(json.dumps({'version':1,'command':[spec['command'][0],
                    str(plugins/'lifeos-hook-bridge/memory_rpc.py'),'--configuration',str(configuration_path)]}))
                connector.chmod(0o600)
                runtime=MemoryRuntime(configuration_path)
                runtime.admit({'HERMES_SESSION_PLATFORM':'chat-a','HERMES_SESSION_USER_ID':'100',
                    'HERMES_SESSION_CHAT_ID':'200','HERMES_SESSION_CHAT_TYPE':'private',
                    'HERMES_SESSION_ID':'native-effect-review'},provider='custom',model='lifecycle-fixture',
                    base_url=endpoint,api_mode='chat_completions',is_first_turn=True,user_message=messages[0]['message']['content'])
                environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(runtime.context()))
                environment['LIFEOS_MEMORY_CONFIGURATION']=str(configuration_path)
                transcript.write_text(''.join(json.dumps(row)+'\n' for row in messages[:2]))
                command=['bun',str(root/'LIFEOS/TOOLS/MemoryReviewer.ts'),'review','--input',str(transcript),'--turns','8']
            for item in (home,*home.rglob('*')):
                if not item.is_symlink():os.chown(item,spec['uid'],spec['gid'])
            before=len(server.observed)
            actual=subprocess.run(command,input=json.dumps({'prompt':'2/10. You claimed success after a failing command.','session_id':'native-failure-control','transcript_path':str(transcript)}) if mode=='failure-capture' else None,
                env=environment,cwd=home,user=spec['uid'],group=spec['gid'],
                extra_groups=[],text=True,capture_output=True,timeout=150)
            (output/(mode+'.stdout')).write_text(actual.stdout)
            (output/(mode+'.stderr')).write_text(actual.stderr)
            wire=server.observed[before:]
            (output/(mode+'-wire.json')).write_text(json.dumps(wire,indent=2)+'\n')
            requests=[row for row in wire if row.get('upstream_status') is not None]
            if mode=='memory-review':
                review_result=json.loads(actual.stdout)
                if actual.returncode:
                    assert actual.returncode==1 and review_result['parse_ok'] and review_result['dispatch_summary']['proposals_auto_apply_failed']>0,review_result
                    assert review_result.get('error','').startswith('auto-apply failed for '),review_result
            else:
                assert actual.returncode==0,(mode,actual.stdout,actual.stderr)
            assert requests and all(row['upstream_status']==200 for row in requests),(mode,wire,actual.stderr)
            assert all(row['body']['reasoning_effort']==('low' if mode=='capability-audit' else 'medium') for row in requests),(mode,wire)
            detail={'mode':mode,'command':command,'returncode':actual.returncode,'requests':len(requests)}
            if mode=='failure-capture':
                captures=list((data/'MEMORY/LEARNING/FAILURES').glob('*/*/sentiment.json'))
                assert len(captures)==1,captures
                sentiment=json.loads(captures[0].read_text());assert sentiment['rating']==2,sentiment
                detail['capture']=str(captures[0].parent)
            elif mode=='capability-audit':
                rows=[json.loads(line) for line in (data/'MEMORY/OBSERVABILITY/spend-audit.jsonl').read_text().splitlines()]
                assert rows[-1]['audited'] and rows[-1]['trigger']=='zero-capability-sweep',rows
                detail['audit']=rows[-1]
            elif mode=='documentation':
                assert '[INFERENCE] Completed' in actual.stderr and '(success: true)' in actual.stderr,actual.stderr
                assert 'reports all command failures as successful' not in document.read_text(),actual.stderr
                assert '[INFERENCE-APPLY]' in actual.stderr or '[UPDATED] [INFERENCE]' in actual.stderr,actual.stderr
                detail['document_after']=document.read_text()
            else:
                result=json.loads(actual.stdout)
                assert result['parse_ok'] and not result.get('skipped'),result
                queue=data/'MEMORY/OBSERVABILITY/pending-proposals.jsonl'
                proposals=[json.loads(line) for line in queue.read_text().splitlines()] if queue.exists() else []
                assert proposals and all(row['status']=='pending' for row in proposals),result
                assert target.read_text()=='# Operational rules\n',target.read_text()
                assert result['dispatch_summary']['proposals_auto_applied']==0,result
                detail.update(review=result,proposals=proposals,target_unchanged=True)
            results.append(detail)
            (output/'result.json').write_text(json.dumps(results,indent=2)+'\n')
        (output/'.done').write_text('0\n')
    finally:
        (output/'all-wire.json').write_text(json.dumps(server.observed,indent=2)+'\n')
        server.shutdown();server.server_close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('configuration',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('plugins',type=Path)
    parser.add_argument('--modes',nargs='+',choices=('failure-capture','documentation','capability-audit','memory-review'),
        default=['failure-capture','documentation','capability-audit','memory-review'])
    args=parser.parse_args()
    run(args.configuration,args.output,args.plugins,args.modes)
