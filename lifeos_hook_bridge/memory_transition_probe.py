# ABOUTME: Verifies reviewed built-in memory through a fresh actual Hermes agent and system prompt.
# ABOUTME: Returns only content hashes, entry counts, and provider admission without a model turn.
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
from pathlib import Path
from uuid import uuid4


def verify_builtin(expected):
    if (not isinstance(expected,dict) or set(expected)!={'MEMORY.md','USER.md'}
            or any(not isinstance(text,str) for text in expected.values())):
        raise ValueError('The fresh-session probe requires the exact reviewed memory files')
    from hermes_constants import get_hermes_home
    from .memory_access import MemoryUnavailable
    from .mount_transaction import _read
    profile=get_hermes_home().absolute()
    names=('config.yaml','SOUL.md','lifeos-memory.json','memories/MEMORY.md','memories/USER.md')
    captured={name:_read(profile/name) for name in names}
    for name,text in expected.items():
        if captured['memories/'+name][0]!=text.encode():
            raise MemoryUnavailable('Built-in memory does not match the reviewed export')
    from dotenv import load_dotenv
    load_dotenv(profile/'.env',override=False)
    agent=None
    manager=None
    diagnostics=io.StringIO()
    try:
        with redirect_stdout(diagnostics),redirect_stderr(diagnostics):
            from hermes_cli.config import load_config_readonly
            from hermes_cli.runtime_provider import resolve_runtime_provider
            from hermes_cli.plugins import get_plugin_manager
            from tools.memory_tool_store import MemoryStore
            from agent.system_prompt import build_system_prompt
            from run_agent import AIAgent
            config=load_config_readonly()
            memory=config.get('memory',{})
            if (not isinstance(memory,dict) or memory.get('provider','builtin') not in (None,'','builtin')
                    or memory.get('memory_enabled',True) is not True
                    or memory.get('user_profile_enabled',True) is not True):
                raise MemoryUnavailable('Both built-in stores must be selected before fresh-session verification')
            model=config.get('model',{})
            model={'default':model} if isinstance(model,str) else model
            runtime=resolve_runtime_provider(requested=model.get('provider'),target_model=model.get('default'),
                explicit_api_key=model.get('api_key'),explicit_base_url=model.get('base_url'))
            manager=get_plugin_manager()
            agent=AIAgent(model=model.get('default'),api_key=runtime.get('api_key'),base_url=runtime.get('base_url'),
                provider=runtime.get('provider'),api_mode=runtime.get('api_mode'),
                session_id='memory-return-'+uuid4().hex,platform='cli',quiet_mode=True,
                enabled_toolsets=['memory','skills'],skip_background_review=True,cwd=str(profile))
            prompt=build_system_prompt(agent)
            providers=[provider.name for provider in agent._memory_manager.providers] if agent._memory_manager else []
            plugins=[item['name'] for item in manager.list_plugins() if item['enabled']]
            if (not agent._memory_enabled or not agent._user_profile_enabled or agent._memory_store is None
                    or 'lifeos-hook-bridge' in providers or {'lifeos','lifeos-hook-bridge'} & set(plugins)
                    or any(name.startswith('lifeos_memory_') for name in agent.valid_tool_names)
                    or 'memory' not in agent.valid_tool_names):
                raise MemoryUnavailable('The fresh Hermes agent does not select built-in memory exclusively')
            counts={}
            for name,target,entries in (('MEMORY.md','memory',agent._memory_store.memory_entries),
                                       ('USER.md','user',agent._memory_store.user_entries)):
                reviewed=list(dict.fromkeys(MemoryStore._parse_entries(expected[name])))
                block=agent._memory_store.format_for_system_prompt(target)
                if entries!=reviewed or reviewed and (not block or block not in prompt):
                    raise MemoryUnavailable('The fresh Hermes prompt does not contain all reviewed built-in entries')
                counts[name]=len(entries)
            proof={'format':1,'provider':'builtin','fresh_agent_verified':True,'model_turn_executed':False,
                'entry_counts':counts,'native_providers':providers,'active_plugins':plugins,
                'profile':str(profile),'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                'files':{name:metadata for name,(_,metadata) in captured.items()}}
    except MemoryUnavailable:
        raise
    except Exception:
        raise MemoryUnavailable('The fresh Hermes agent cannot verify the reviewed built-in memory') from None
    finally:
        with redirect_stdout(diagnostics),redirect_stderr(diagnostics):
            if agent is not None:agent.close()
            if manager is not None:manager.unload()
    if any(_read(profile/name)!=captured[name] for name in names):
        raise MemoryUnavailable('The reviewed profile changes during fresh-session verification')
    return proof
