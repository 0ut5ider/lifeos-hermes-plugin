# ABOUTME: Runs supported Hermes model paths against an isolated HTTP fixture.
# ABOUTME: Keeps memory admission, model clients, and compression on their actual runtime paths.
import asyncio
import json
import os
from pathlib import Path
import sys

sys.path[:0] = [str(Path(__file__).parents[1]), os.environ['LIFEOS_HERMES_SOURCE']]

from gateway.session_context import set_session_vars, clear_session_vars
from hermes_cli.plugins import PluginContext, PluginManifest, get_plugin_manager
from lifeos_hook_bridge.memory_runtime import MemoryRuntime


def main():
    settings = json.loads(sys.stdin.read())
    runtime = MemoryRuntime(Path(os.environ['HERMES_HOME']) / 'lifeos-memory.json')
    tokens = set_session_vars(platform='chat-a', user_id=settings['author'], chat_id='200',
                             chat_type='dm', session_id='session')
    manager = get_plugin_manager()
    manager.discover_and_load()
    context = PluginContext(PluginManifest(name='memory-model-fixture', version='1.0.0', description='Synthetic fixture'), manager)
    context.register_middleware('llm_admission', runtime.check_call, required=True)
    try:
        from agent.prompt_builder import load_soul_md
        soul = load_soul_md(home_override=Path(os.environ['HERMES_HOME']))
        if settings.get('refresh_after_load'):
            (Path(os.environ['HERMES_HOME'])/'SOUL.md').write_text('# Synthetic refreshed public prompt\n')
        metadata = {'HERMES_SESSION_PLATFORM':'chat-a','HERMES_SESSION_USER_ID':'100',
                    'HERMES_SESSION_CHAT_ID':'200','HERMES_SESSION_CHAT_TYPE':'dm','HERMES_SESSION_ID':'session'}
        route = settings['route']
        runtime.admit(metadata, **settings['parent_route'], is_first_turn=settings['first'])
        messages = ([{'role':'system','content':soul}] if soul else []) + [{'role':'user','content':settings['marker']}]
        variant = settings.get('request_variant','')
        if variant == 'tuple-messages':
            messages = tuple(messages)
        elif variant == 'tuple-blocks' and soul:
            messages[0]['content'] = ({'type':'text','text':soul},)
        elif variant == 'generator-messages':
            messages = (message for message in messages)
        if settings['operation'] in ('primary','responses-compression','responses-primary'):
            from openai import OpenAI
            from hermes_cli.middleware import run_llm_execution_middleware
            with OpenAI(base_url=route['base_url'], api_key='synthetic-key', max_retries=0) as client:
                request = {'model':route['model'],'messages':messages}
                if settings['operation'].startswith('responses-'):
                    request = {'model':route['model'],'input':'\n'.join((soul or '',settings['marker']))}
                if variant == 'extra-body':
                    request.update(messages=[{'role':'user','content':settings['marker']}],extra_body={'messages':messages})
                elif variant == 'extra-model':
                    request['extra_body'] = {'model':'unapproved-model'}
                execute = (client.responses.create if settings['operation'].startswith('responses-')
                           else client.chat.completions.create)
                auxiliary = {'aux_task':'compression'} if settings['operation']=='responses-compression' else {}
                response = run_llm_execution_middleware(
                    request,
                    lambda request:execute(**request), **route, session_id='session', **auxiliary)
            result = response.output_text if settings['operation'].startswith('responses-') else response.choices[0].message.content
        elif settings['operation'] == 'compression':
            from agent.context_compressor import ContextCompressor
            compressor = ContextCompressor(model=route['model'], provider=route['provider'],
                base_url=route['base_url'], api_key='synthetic-key', api_mode=route['api_mode'],
                config_context_length=16384, quiet_mode=True, abort_on_summary_failure=True)
            result = compressor._generate_summary(messages, memory_context=settings['marker'])
        else:
            from agent.auxiliary_client import call_llm, async_call_llm
            arguments = dict(route, api_key='synthetic-key', task='compression', messages=messages,
                             timeout=5, max_tokens=128, allow_provider_fallback=False)
            if settings['operation'] == 'async':
                arguments.pop('api_mode')
                arguments.pop('allow_provider_fallback')
                response = asyncio.run(async_call_llm(**arguments))
            else:
                response = call_llm(**arguments)
            result = response.choices[0].message.content
        print(json.dumps({'result':result}))
    finally:
        runtime.clear()
        manager.unload()
        clear_session_vars(tokens)


if __name__ == '__main__':
    main()
