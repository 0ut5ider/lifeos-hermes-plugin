# ABOUTME: Measures actual delegated child inference and correlated native lifecycle records.
# ABOUTME: Uses isolated profiles and the private gateway relay without synthetic model responses.
import argparse
import asyncio
import base64
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import shlex
import sys
import threading
import time


def host(output, mode):
    from hermes_cli.plugins import discover_plugins, unload_plugins
    from gateway.session_context import clear_session_vars, set_session_vars
    from run_agent import AIAgent
    from tools.process_registry import process_registry

    home = Path.home()
    model = json.loads((home / '.hermes/config.yaml').read_text())['model']
    discover_plugins()
    progress = []
    def observe(event, tool_name=None, preview=None, args=None, **details):
        progress.append({'event': str(event), 'tool': tool_name, **details})
    database = None
    if mode == 'gateway-pulse':
        from hermes_state import SessionDB
        database = SessionDB(home / '.hermes/state.db')
    agent = AIAgent(api_key=model['api_key'], base_url=model['base_url'], provider='custom',
        api_mode='chat_completions', model=model['default'], enabled_toolsets=['delegation', 'terminal'],
        tool_progress_callback=observe,
        quiet_mode=True, platform='api_server' if mode == 'gateway-pulse' else 'cli',
        session_db=database, max_iterations=5, skip_memory=True,
        reasoning_config={'effort':'xhigh'} if mode == 'tiers' else None,
        skip_background_review=True, ephemeral_system_prompt='Run only the requested synthetic delegation control.')
    tokens = set_session_vars(platform='api_server' if mode == 'gateway-pulse' else 'cli', session_id=agent.session_id, session_key=agent.session_id,
                              async_delivery=True)
    try:
        prompt = ('Call delegate_task once with exactly two tasks. Set each task toolsets to an empty list. '
                  'The first task goal is: Reply with exactly PAIR_CHILD_A. '
                  'The second task goal is: Reply with exactly PAIR_CHILD_B. '
                  'After the dispatch acknowledgment, reply with exactly PAIR_PARENT_DISPATCHED. '
                  'Do not call delegate_task again.')
        if mode == 'tiers':
            prompt = ('Call delegate_task exactly once with two tasks. Both task toolsets must be empty. '
                      'The first task must set model to haiku and reply PAIR_CHILD_A. '
                      'The second task must omit model and reasoning_effort and reply PAIR_CHILD_B. '
                      'After dispatch, end this turn with PAIR_PARENT_DISPATCHED. Make no additional tool calls.')
        elif mode == 'cancel':
            prompt = ('Call delegate_task once with exactly two tasks. Set each task toolsets to [terminal]. '
                      'The first goal is: Call terminal with command sleep 30, then reply with PAIR_CHILD_A. '
                      'The second goal is: Call terminal with command sleep 30, then reply with PAIR_CHILD_B. '
                      'After the dispatch acknowledgment, reply with PAIR_PARENT_DISPATCHED. Do not wait for the children.')
        elif mode == 'gateway-pulse':
            prompt = ('Call delegate_task exactly once with two tasks. Set both task toolsets to [terminal]. '
                      'The first task must call terminal with sleep 5, then reply PAIR_CHILD_A. '
                      'The second task must call terminal with sleep 5, then reply PAIR_CHILD_B. '
                      'After dispatch, end this turn with PAIR_PARENT_DISPATCHED. Make no additional tool calls.')
        result = agent.run_conversation(prompt)
        calls = [row for row in result.get('messages', []) if row.get('role') == 'tool']
        dispatched = [row for row in calls if '"mode": "background"' in str(row.get('content'))]
        assert len(dispatched) == 1, {'tools': calls, 'final': result.get('final_response')}
        if mode == 'cancel':
            from tools.async_delegation import interrupt_for_session
            from hermes_cli.lifecycle import finalize_session
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                running_tools = [row for row in progress if row['event'] == 'subagent.tool' and row['tool'] == 'terminal']
                if len(running_tools) == 2:
                    break
                time.sleep(.05)
            assert len(running_tools) == 2, progress
            interrupted = interrupt_for_session(parent_session_id=agent.session_id, reason='session_end')
            assert interrupted == 1, interrupted
            finalize_session(session_id=agent.session_id, reason='prompt_input_exit', platform='cli')
        completions = []
        watchdog = []
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline and len(completions) < 1:
            try:
                event = process_registry.completion_queue.get(timeout=.1)
            except Empty:
                continue
            if event.get('type') == 'async_delegation' and not event.get('task_failure_notice'):
                completions.append(event)
            elif event.get('type') == 'watch_match':
                watchdog.append(event)
        assert len(completions) == 1, completions
        summary = json.dumps(completions)
        if mode in {'concurrent', 'gateway-pulse', 'tiers'}:
            assert 'PAIR_CHILD_A' in summary and 'PAIR_CHILD_B' in summary, completions
        elif mode == 'cancel':
            assert completions[0]['status'] == 'error', completions
            assert all(row['status'] == 'interrupted' for row in completions[0]['results']), completions
        else:
            assert completions[0]['status'] == 'error', completions
            assert all(row['status'] == 'failed' and row.get('error') for row in completions[0]['results']), completions
        delivered = None
        durable = None
        gateway_delivery = None
        if mode == 'gateway-pulse':
            assert watchdog and all(row.get('session_key') == agent.session_id for row in watchdog), watchdog
            gateway_delivery = asyncio.run(deliver_gateway_watchdog(watchdog[0], agent.session_id))
        if mode in {'concurrent', 'gateway-pulse', 'tiers'}:
            from hermes_cli.cli_process_notifications import CLIProcessNotificationsMixin
            from tools.async_delegation import get_durable_delegation
            class CompletionConsumer(CLIProcessNotificationsMixin):
                def __init__(self):
                    self.session_id = agent.session_id
                    self._pending_input = Queue()
            consumer = CompletionConsumer()
            process_registry.completion_queue.put(completions[0])
            consumer._drain_process_notifications('fixture-parent-consumer')
            notification = consumer._pending_input.get_nowait()
            assert notification.display_kind == 'async_delegation_complete', notification
            delivered = agent.run_conversation(notification)
            assert delivered.get('completed') and delivered.get('final_response'), delivered
            consumer._drain_process_notifications('fixture-parent-consumer')
            assert consumer._pending_input.empty()
            durable = get_durable_delegation(completions[0]['delegation_id'])
            assert durable['delivery_state'] == 'delivered', durable
        path = home / '.claude/LIFEOS/MEMORY/OBSERVABILITY/subagent-events.jsonl'
        events = [json.loads(line) for line in path.read_text().splitlines()]
        cache = home/'.claude/LIFEOS/MEMORY/STATE/last-response.txt'
        final = delivered.get('final_response') if delivered else result.get('final_response')
        assert cache.read_text() == final[:2000], 'The native cache does not contain the completed parent response'
        output.write_text(json.dumps({'actual_parent_response': result.get('final_response'),
            'actual_completions': completions, 'native_events': events,
            'parent_session_id': agent.session_id, 'progress': progress,
            'gateway_delivery': gateway_delivery, 'actual_watchdog_events': watchdog,
            'actual_response_cache': cache.read_text(),
            'parent_completion_response': delivered.get('final_response') if delivered else None,
            'durable_delivery': durable, 'main_callbacks': [json.loads(line) for line in (home/'main-callbacks.jsonl').read_text().splitlines()]}, indent=2) + '\n')
        main_callbacks = [json.loads(line) for line in (home/'main-callbacks.jsonl').read_text().splitlines()]
        assert main_callbacks and all(row['session_id'] == agent.session_id for row in main_callbacks), main_callbacks
        starts = [row for row in events if row['event'] == 'subagent_start']
        stops = [row for row in events if row['event'] == 'subagent_stop']
        assert len(starts) == len(stops) == 2, {'starts': len(starts), 'stops': len(stops)}
        assert {row['subagent_id'] for row in starts} == {row['subagent_id'] for row in stops}
        assert all(row['subagent_model'] == model['default'] for row in starts), starts
        if mode == 'tiers':
            assert sum(row.get('subagent_requested_model') == 'haiku' for row in starts) == 1, starts
            assert {row.get('subagent_reasoning_effort') for row in starts} == {'low', 'xhigh'}, starts
            assert sum(row['subagent_level'] == 'session-inherited' for row in starts) == 1, starts
    finally:
        clear_session_vars(tokens)
        agent.close()
        unload_plugins()
        if database:
            database.close()


async def deliver_gateway_watchdog(event, parent_session_id):
    from gateway.config import GatewayConfig, Platform, PlatformConfig
    from gateway.platforms.api_server import APIServerAdapter
    from gateway.run import GatewayRunner
    from hermes_state import SessionDB

    config = PlatformConfig(enabled=True, extra={'host':'127.0.0.1', 'port':0,
        'key':'PAIR_GATEWAY_PULSE_FIXTURE_KEY_TEST'})
    runner = GatewayRunner(GatewayConfig(platforms={Platform.API_SERVER: config}, multiplex_profiles=False))
    adapter = APIServerAdapter(config)
    adapter.gateway_runner = runner
    runner.adapters[Platform.API_SERVER] = adapter
    try:
        assert await adapter.connect(), 'The actual API gateway did not start'
        adapter._port = adapter._site._server.sockets[0].getsockname()[1]
        pending = Queue()
        pending.put(event)
        await runner._drain_watch_notifications(pending)
        assert pending.empty(), 'The actual gateway refused the watchdog delivery'
        db = SessionDB(Path.home()/'.hermes/state.db')
        try:
            messages = db.get_messages_as_conversation(parent_session_id)
        finally:
            db.close()
        assert any('WATCHDOG:' in str(row.get('content')) for row in messages), messages
        assert messages[-1]['role'] == 'assistant' and messages[-1].get('content'), messages
        return {'parent_session_id': parent_session_id, 'messages': messages, 'remaining_queue': pending.qsize()}
    finally:
        await adapter.disconnect()


def run(configuration, output, plugins, mode):
    from paired_response_server import response_handler
    config = json.loads(configuration.read_text())
    spec = config['hermes']
    plugins = plugins.resolve(strict=True)
    output.mkdir()
    server = ThreadingHTTPServer(('127.0.0.1', 0), response_handler(config['model_environment']))
    server.observed = []
    failure_server = None
    if mode == "provider-failure":
        from paired_response_server import model_environment
        endpoint, carrier, _ = model_environment(config["model_environment"])
        bad_environment = output / "refused-environment"
        values = {"ANTHROPIC_BASE_URL": endpoint.geturl(), "ANTHROPIC_MODEL": carrier,
                  "ANTHROPIC_AUTH_TOKEN": "PAIR_INVALID_AUTHORIZATION"}
        bad_environment.write_text("\n".join(key+"="+shlex.quote(value) for key,value in values.items())+"\n")
        bad_environment.chmod(0o600)
        failure_server = ThreadingHTTPServer(("127.0.0.1", 0), response_handler(bad_environment))
        failure_server.observed = []
        threading.Thread(target=failure_server.serve_forever, daemon=True).start()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    home = Path(spec['home_root']) / output.name
    home.mkdir()
    profile = home / '.hermes'
    profile.mkdir()
    (profile / 'plugins').symlink_to(plugins, target_is_directory=True)
    root = home / '.claude'
    root.mkdir()
    (root / 'hooks').symlink_to(Path(spec['hook_root']) / 'hooks', target_is_directory=True)
    (root / 'LIFEOS').mkdir()
    (root / 'LIFEOS/TOOLS').symlink_to(Path(spec['hook_root']) / 'LIFEOS/TOOLS', target_is_directory=True)
    (root / 'settings.json').write_text(json.dumps({'hooks': {event: [{'matcher': 'Agent', 'hooks': [
        {'type': 'command', 'command': 'bun ' + str(root / 'hooks/AgentInvocation.hook.ts')}]}]
        for event in ('PreToolUse', 'PostToolUse')}}))
    settings = json.loads((root / 'settings.json').read_text())
    for event in ('SessionStart', 'UserPromptSubmit', 'Stop'):
        settings['hooks'][event] = [{'hooks': [{'type': 'command', 'command': shlex.join([spec['command'][0],str(Path(__file__).resolve()),'record'])}]}]
    settings['hooks']['Stop'][0]['hooks'].append({'type':'command',
        'command':'bun '+str(root/'hooks/LastResponseCache.hook.ts')})
    (root / 'settings.json').write_text(json.dumps(settings))
    pulse = None
    if mode == 'gateway-pulse':
        os.environ['PATH'] = spec['environment']['PATH']
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests'))
        from test_native_pulse_guards import PulseFixture
        pulse = PulseFixture(output/'pulse-home', Path(spec['hook_root']))
        pulse.start()
        settings['hooks']['PreToolUse'][0]['hooks'].insert(0, {'type':'http',
            'url':f'http://127.0.0.1:{pulse.port}/hooks/agent-guard'})
        (root/'settings.json').write_text(json.dumps(settings))
    (profile / 'config.yaml').write_text(json.dumps({'plugins': {'enabled': ['lifeos-hook-bridge']},
        'database': {'journal_mode': 'delete'},
        'platform_toolsets': {'api_server': []},
        'model': {'provider': 'custom', 'base_url': f'http://127.0.0.1:{server.server_port}/v1',
            'api_key': 'PAIR_DELEGATION', 'default': 'lifecycle-fixture', 'api_mode': 'chat_completions'},
        'delegation': {'max_spawn_depth': 1, 'orchestrator_enabled': False,
            **({'provider': 'custom', 'base_url': f'http://127.0.0.1:{failure_server.server_port}/v1',
                'api_key': 'PAIR_REFUSED_CHILD', 'model': 'lifecycle-fixture', 'api_mode': 'chat_completions',
                'fallback_providers': []} if failure_server else {})}}))
    for item in (home, *home.rglob('*')):
        if not item.is_symlink():
            os.chown(item, spec['uid'], spec['gid'])
    env = {**spec['environment'], 'HOME': str(home), 'HERMES_HOME': str(profile),
        'LIFEOS_DIR': str(root / 'LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(root / 'settings.json'),
        'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'TERMINAL_CWD': str(home), 'PYTHONUNBUFFERED': '1'}
    if mode == 'gateway-pulse':
        env.update(LIFEOS_WATCHDOG_SILENCE_SECONDS='0.1', LIFEOS_WATCHDOG_CHECK_SECONDS='0.1')
    try:
        with (output / 'host.log').open('w') as stream:
            result = subprocess.run([spec['command'][0], str(Path(__file__).resolve()), 'host', str(home / 'result.json'), mode],
                env=env, cwd=home, user=spec['uid'], group=spec['gid'], extra_groups=[],
                stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        if (home / 'result.json').exists():
            (output / 'result.json').write_bytes((home / 'result.json').read_bytes())
        (output / 'wire.json').write_text(json.dumps(server.observed, indent=2)+'\n')
        if result.returncode == 0:
            recorded = json.loads((output / 'result.json').read_text())
            served = {json.loads(base64.b64decode(row['response_body_base64'])).get('model')
                for row in server.observed if row.get('upstream_status') == 200}
            stops = [row for row in recorded['native_events'] if row['event'] == 'subagent_stop']
            if mode == 'provider-failure':
                assert all('subagent_observed_model' not in row for row in stops), stops
            else:
                assert served and all(row.get('subagent_observed_model') in served for row in stops), stops
        if failure_server:
            (output / 'refused-wire.json').write_text(json.dumps(failure_server.observed, indent=2)+'\n')
            refused = [row for row in failure_server.observed if row.get('upstream_status') is not None]
            assert len(refused) == 2 and all(row['upstream_status'] in (401,403) for row in refused), 'Actual upstream authentication refusal was not measured'
        (output / '.done').write_text(str(result.returncode)+'\n')
        assert result.returncode == 0, (output / 'host.log').read_text()
    finally:
        server.shutdown()
        if failure_server:
            failure_server.shutdown()
            bad_environment.unlink(missing_ok=True)
        if pulse:
            pulse.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='action', required=True)
    child = commands.add_parser('host')
    child.add_argument('output', type=Path)
    child.add_argument('mode', choices=['concurrent', 'provider-failure', 'cancel', 'gateway-pulse', 'tiers'])
    commands.add_parser('record')
    control = commands.add_parser('run')
    control.add_argument('configuration', type=Path)
    control.add_argument('output', type=Path)
    control.add_argument('plugins', type=Path)
    control.add_argument('--mode', choices=['concurrent', 'provider-failure', 'cancel', 'gateway-pulse', 'tiers'], default='concurrent')
    args = parser.parse_args()
    if args.action == 'record':
        payload = json.load(sys.stdin)
        with (Path.home()/'main-callbacks.jsonl').open('a') as stream:
            stream.write(json.dumps({'session_id': payload['session_id'], 'event': payload['hook_event_name']})+'\n')
    elif args.action == 'host':
        host(args.output, args.mode)
    else:
        run(args.configuration, args.output, args.plugins, args.mode)
