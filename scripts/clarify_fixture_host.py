# ABOUTME: Supplies a synthetic answer through supported native and Hermes interaction hosts.
# ABOUTME: Uses the real clarification queue and records waiting state before answering.

import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time


def save_waiting():
    home = Path(os.environ['HOME'])
    state = home / '.claude/LIFEOS/MEMORY/STATE/tab-titles/777.json'
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        value = json.loads(state.read_text())
        if value.get('activity') == 'waiting':
            (home / 'waiting-state.json').write_text(json.dumps(value))
            return
        time.sleep(0.05)
    raise RuntimeError('Question waiting state was not observed')


def native_answer():
    payload = json.load(sys.stdin)
    save_waiting()
    questions = payload['tool_input']['questions']
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'allow',
                     'updatedInput': {'questions': questions, 'answers': {q['question']: 'PAIR_QUESTION_A' for q in questions}}}}))


def hermes_agent(prompt):
    from hermes_cli.plugins import discover_plugins, unload_plugins
    from run_agent import AIAgent
    from tools import clarify_gateway as queue

    discover_plugins()
    home = Path(os.environ['HOME'])
    config = json.loads((home / '.hermes/config.yaml').read_text())['model']

    def answer(question, choices, multi_select=False):
        save_waiting()
        entry = 'fixture-question'
        queue.register(entry, 'fixture-chat', question, choices, multi_select)
        (home / 'question-presented.json').write_text(json.dumps({'question': question, 'choices': choices}))

        def choose():
            time.sleep(0.1)
            assert queue.resolve_gateway_clarify(entry, 'PAIR_QUESTION_A')

        chooser = threading.Thread(target=choose)
        chooser.start()
        try:
            return queue.wait_for_response(entry, 5)
        finally:
            chooser.join(timeout=6)
            queue.clear_session('fixture-chat')

    agent = AIAgent(api_key=config['api_key'], base_url=config['base_url'], provider='custom',
                    api_mode='chat_completions', model=config['default'], enabled_toolsets=['clarify'],
                    quiet_mode=True, platform='cli', clarify_callback=answer, max_iterations=4,
                    skip_memory=True, skip_background_review=True,
                    ephemeral_system_prompt=os.environ['HERMES_EPHEMERAL_SYSTEM_PROMPT'])
    try:
        result = agent.run_conversation(prompt)
        print(json.dumps({'type': 'result', 'text': result.get('final_response', '')}))
    finally:
        from hermes_cli.lifecycle import finalize_session
        finalize_session(session_id=agent.session_id, reason='prompt_input_exit', platform='cli')
        agent.close()
        unload_plugins()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['native-answer', 'hermes-agent'])
    parser.add_argument('prompt', nargs='?')
    args = parser.parse_args()
    native_answer() if args.action == 'native-answer' else hermes_agent(args.prompt)
