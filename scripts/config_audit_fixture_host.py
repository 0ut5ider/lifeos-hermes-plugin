# ABOUTME: Runs native configuration audit commands and an idle Hermes bridge in a test home.
# ABOUTME: Records original watcher payloads and preserves native audit output.

import json
import os
from pathlib import Path
import subprocess
import sys
import time


home = Path(os.environ['HOME'])

if sys.argv[1] == 'trace':
    payload = json.load(sys.stdin)
    if payload['hook_event_name'] == 'ConfigChange':
        result = subprocess.run(['bun', os.environ['PAIR_NATIVE_PROGRAM']], input=json.dumps(payload),
                                text=True, capture_output=True, timeout=15)
        record = {'payload': payload, 'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode}
        with (home / 'hooks.jsonl').open('a') as stream:
            stream.write(json.dumps(record) + '\n')
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
    with (home / 'events.jsonl').open('a') as stream:
        stream.write(json.dumps(payload) + '\n')
else:
    from lifeos_hook_bridge.bridge import HookBridge
    root = home / '.claude'
    bridge = HookBridge(root / 'settings.json', root, lifeos_home=home)
    try:
        bridge.pre_llm_call('Synthetic idle configuration fixture', session_id='config-fixture', platform='cli')
        deadline = time.monotonic() + 120
        while not (home / 'finish').exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        bridge.session_end('config-fixture')
    finally:
        bridge.close()
