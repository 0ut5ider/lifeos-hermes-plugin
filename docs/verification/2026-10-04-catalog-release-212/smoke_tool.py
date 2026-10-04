# ABOUTME: Runs a real terminal turn against the updated active .212 installation.
# ABOUTME: Retains raw streams privately and emits a synthetic success record.
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from deploy_catalog import layout, save

os.umask(0o077)
ctx = layout(sys.argv[1])
release = ctx['release']
marker = 'CATALOG-212-' + ctx['target'].upper() + '-TOOL-READY'
prompt = release / 'tool-prompt.txt'
prompt.write_text('Use the terminal tool to execute pwd. After the successful tool result, reply exactly ' + marker + '.')
started = time.time()
try:
    with (release / 'tool-stream.jsonl').open('w') as output, (release / 'tool-stderr.txt').open('w') as errors:
        result = subprocess.run(
            [str(ctx['host'] / '.hermes/bin/hermes'), 'chat', '--oneshot', '-Q', '--format',
             'stream-json', '-t', 'terminal', '--query-file', str(prompt)],
            cwd=ctx['home'], env=ctx['environment'], stdout=output, stderr=errors, timeout=300)
    rows = []
    for line in (release / 'tool-stream.jsonl').read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    uses = [row for row in rows if row.get('type') == 'tool_use' and row.get('name') == 'terminal']
    results = [row for row in rows if row.get('type') == 'tool_result'
               and row.get('name') == 'terminal' and not row.get('is_error')]
    final = [row for row in rows if row.get('type') == 'result']
    assert result.returncode == 0 and uses and results and final, 'Inspect private tool streams'
    assert final[-1].get('exit_code') == 0 and marker in final[-1].get('text', ''), 'Expected reply marker'
    assert any(row.get('input', {}).get('command', '').strip() == 'pwd' for row in uses), 'Expected pwd'
    record = {'target': ctx['target'], 'exit_code': 0, 'tool': 'terminal', 'command': 'pwd',
              'tool_succeeded': True, 'final_reply_marker': marker,
              'session_id': final[-1]['session_id'], 'started': started, 'finished': time.time()}
    save(release / 'tool-result.json', record)
    print(json.dumps(record))
    (release / 'tool.exit').write_text('0\n')
except BaseException:
    (release / 'tool.exit').write_text('1\n')
    raise
finally:
    (release / 'tool.done').touch()
