# ABOUTME: Interrupts an actual installed gateway waiter and serializes its clarification result.
# ABOUTME: Verifies a later answer in the same session without connecting synthetic identities to Discord.
import asyncio
import contextvars
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time

stage=Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
sys.path.insert(0,str(stage/'package/hermes'))
from gateway.config import GatewayConfig,Platform
from gateway.run import GatewayRunner,_AGENT_PENDING_SENTINEL
from gateway.session import SessionSource
from hermes_constants import set_hermes_home_override,reset_hermes_home_override
from tools import clarify_gateway as queue
from tools.clarify_tool import clarify_tool


async def verify():
    with tempfile.TemporaryDirectory(prefix='daily-release-cancellation-') as temporary:
        home=Path(temporary)
        (home/'config.yaml').write_text('database:\n  journal_mode: wal\n')
        with sqlite3.connect(home/'state.db') as database:
            database.execute('PRAGMA journal_mode=WAL')
        token=set_hermes_home_override(home)
        runner=None
        key='daily-release-synthetic-cancellation'
        try:
            runner=GatewayRunner(config=GatewayConfig())
            source=SessionSource(platform=Platform.DISCORD,chat_id='synthetic-release-channel',
                chat_type='group',user_id='synthetic-release-owner')
            runner._running_agents[key]=_AGENT_PENDING_SENTINEL
            generation=runner._begin_session_run_generation(key)
            entered=threading.Event()

            def callback(question,choices):
                entry=queue.register('daily-release-question',key,question,choices)
                entered.set()
                return queue.wait_for_response(entry,30)

            with ThreadPoolExecutor(max_workers=1) as worker:
                future=worker.submit(contextvars.copy_context().run,clarify_tool,
                    'Synthetic release cancellation',['A','B'],callback=callback)
                assert entered.wait(3)
                started=time.monotonic()
                await runner._interrupt_and_clear_session(key,source,
                    interrupt_reason='explicit stop requested',invalidation_reason='stop_command')
                outcome=json.loads(await asyncio.wait_for(asyncio.wrap_future(future),3))
                elapsed=time.monotonic()-started
            assert outcome.get('cancelled') is True and 'timed_out' not in outcome,outcome
            assert outcome['user_response']==''
            assert queue.get_pending_for_session(key,include_choice_prompts=True) is None
            assert not queue.resolve_gateway_clarify('daily-release-question','late answer')
            assert key not in runner._running_agents
            assert runner._current_session_run_generation(key)>generation
            successor=queue.register('daily-release-question',key,'Synthetic recovery',['A','B'])
            assert queue.resolve_gateway_clarify(successor.clarify_id,'B')
            recovered=json.loads(clarify_tool('Synthetic recovery',['A','B'],
                callback=lambda *_:queue.wait_for_response(successor,3)))
            assert recovered['user_response']=='B' and not recovered.get('cancelled'),recovered
            report={'status':'PASS','outcome':outcome,'recovery':recovered,'stop_seconds':elapsed,
                'late_answer_refused':True,'actual_gateway_interruption':True,
                'discord_network_delivery_verified':False,'synthetic_data_only':True}
            (stage/'release-cancellation.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report,indent=2))
        finally:
            queue.clear_session(key)
            if runner is not None:runner._session_db._db.close()
            reset_hermes_home_override(token)


asyncio.run(verify())
