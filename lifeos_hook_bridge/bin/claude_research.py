# ABOUTME: Runs the native child web research request through the selected Hermes agent.
# ABOUTME: Confines tools to web search and extraction and preserves current memory admission.
from contextlib import redirect_stdout
import os
from uuid import uuid4
import sys


def run(args, system_prompt, content, provider, runtime):
    from gateway.session_context import clear_session_vars, set_session_vars
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from run_agent import AIAgent

    if not isinstance(content, str):
        raise ValueError('Native web research requires a text prompt')
    selected = resolve_runtime_provider(requested=provider, target_model=args.model)
    route = {key: selected[key] for key in ('provider', 'base_url', 'api_mode')}
    route['model'] = args.model
    runtime.check_call(request={'model': args.model, 'messages': [
        {'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': content}]},
        **route, aux_task='lifeos_child')
    session = 'owner-research-' + uuid4().hex
    if runtime.enabled():
        runtime.fork_owner_job(session, route=route)
    tokens = set_session_vars(platform='cli', user_id=str(os.getuid()),
        chat_id=str(runtime.configuration.path.parent), chat_type='private', session_id=session)
    agent = None
    try:
        with redirect_stdout(sys.stderr):
            agent = AIAgent(**route, api_key=selected.get('api_key'),
                session_id=session or None, platform='cli', user_id=str(os.getuid()),
                chat_id=str(runtime.configuration.path.parent), chat_type='private',
                enabled_toolsets=['web'], quiet_mode=True,
                max_tokens=int(os.environ['LIFEOS_CHILD_MAX_TOKENS'])
                    if 'LIFEOS_CHILD_MAX_TOKENS' in os.environ else None,
                reasoning_config={'enabled': True, 'effort': args.effort},
                ephemeral_system_prompt=system_prompt, skip_context_files=True,
                load_soul_identity=False, skip_memory=True, skip_background_review=True,
                save_trajectories=False, run_budget_seconds=300,
                cwd=str(runtime.configuration.path.parent))
            if agent.valid_tool_names != {'web_search', 'web_extract'}:
                raise ValueError('Native web research requires only the available web tools')
            result = agent.run_conversation(content)
        if result.get('completed') is not True or result.get('failed'):
            raise ValueError('Native web research does not complete successfully')
        response = result.get('final_response')
        if not isinstance(response, str) or not response.strip():
            raise ValueError('Native web research requires a final text response')
        if runtime.enabled():
            from ..memory_service import MemoryService
            context = runtime.context()
            if context is None:
                raise ValueError('Native web research requires current owner admission')
            from datetime import datetime, timezone
            filtered = MemoryService(runtime.configuration).native(context, 'filter_history',
                {'content': response, 'timestamp': datetime.now(timezone.utc).isoformat()})
            if not filtered.get('ok', True) or filtered.get('excluded'):
                raise ValueError('Native web research output is unavailable under the current owner policy')
            response = filtered['content']
        return response
    finally:
        if agent is not None:
            with redirect_stdout(sys.stderr): agent.close()
        clear_session_vars(tokens)
