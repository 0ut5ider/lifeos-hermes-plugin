# ABOUTME: Exercises real Hermes agent initialization and prompt construction in a private fixture.
# ABOUTME: Reports lasting-memory ownership, available tools, and retained session capabilities.
import json
import io
import logging
import os
from contextlib import redirect_stdout
from pathlib import Path
import sys
import threading

sys.path[:0] = [str(Path(__file__).parents[1]),os.environ['LIFEOS_HERMES_SOURCE']]

from gateway.session_context import clear_session_vars,set_session_vars
from hermes_cli.plugins import get_plugin_manager
from agent.system_prompt import build_system_prompt
from run_agent import AIAgent


def main():
    settings = json.loads(sys.stdin.read())
    author = settings.get('author','100')
    tokens = set_session_vars(platform='chat-a',user_id=author,chat_id='200',chat_type='dm',session_id='session')
    manager = get_plugin_manager()
    agent = None
    warnings = io.StringIO()
    logger = logging.getLogger('run_agent')
    handler = logging.StreamHandler(warnings)
    handler.setLevel(logging.WARNING)
    logger.addHandler(handler)
    try:
        agent = AIAgent(**settings['route'],api_key='synthetic-key',session_id='session',platform='chat-a',
                        user_id=author,chat_id='200',chat_type='dm',quiet_mode=True,
                        enabled_toolsets=['memory','skills'],skip_context_files=True,skip_background_review=True,
                        cwd=os.environ['HERMES_HOME'])
        prompt = build_system_prompt(agent)
        providers = [provider.name for provider in agent._memory_manager.providers] if agent._memory_manager else []
        tools = sorted(agent.valid_tool_names)
        conversation = None
        diagnostics = io.StringIO()
        if settings.get('operation') == 'conversation':
            with redirect_stdout(diagnostics):
                conversation = agent.run_conversation(settings['message'],
                                                       conversation_history=settings.get('conversation_history'))
        review_done = None
        review_summaries = []
        followup = None
        if settings.get('background_review'):
            agent.background_review_callback = review_summaries.append
            with redirect_stdout(diagnostics):
                agent._spawn_background_review(conversation['messages'],review_skills=True,
                                               focus=settings.get('review_focus'),explicit=settings.get('review_explicit',False))
                review_run = getattr(agent,'_background_review_run',None)
                review_done = review_run is None or review_run.request_done.wait(timeout=20)
                for thread in threading.enumerate():
                    if thread.name == 'bg-review':
                        thread.join(timeout=20)
                        review_done = review_done and not thread.is_alive()
        if settings.get('followup_message') is not None:
            with redirect_stdout(diagnostics):
                followup = agent.run_conversation(settings['followup_message'],
                                                  conversation_history=conversation['messages'])
        denied_writes = []
        if agent._memory_store is None:
            from tools.memory_tool import memory_tool,load_on_disk_store
            disk_store = load_on_disk_store()
            for target in ('memory','user'):
                for store in (agent._memory_store,disk_store):
                    denied_writes.append(json.loads(memory_tool(action='add',target=target,
                                      content='Synthetic disabled store write marker',store=store)))
        print(json.dumps({'memory_enabled':agent._memory_enabled,'user_profile_enabled':agent._user_profile_enabled,
                          'has_builtin_store':agent._memory_store is not None,'providers':providers,'tools':tools,
                          'prompt':prompt,'skill_nudge_interval':agent._skill_nudge_interval,'disabled_writes':denied_writes,
                          'warnings':warnings.getvalue(),'conversation':conversation,'diagnostics':diagnostics.getvalue(),
                          'review_done':review_done,'review_summaries':review_summaries,'followup':followup}))
    finally:
        if agent is not None:
            agent.close()
        manager.unload()
        logger.removeHandler(handler)
        clear_session_vars(tokens)


if __name__ == '__main__':
    main()
