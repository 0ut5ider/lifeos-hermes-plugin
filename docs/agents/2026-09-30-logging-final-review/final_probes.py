# ABOUTME: Probes declared bearer echoes and offline artifact integrity boundaries.
# ABOUTME: Saves synthetic evidence from isolated source and real local hook processes.

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PLUGIN = ROOT / 'lifeos_hook_bridge'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision')
    args = parser.parse_args()
    results = {}
    with tempfile.TemporaryDirectory(prefix='logging-final-review-') as directory:
        root = Path(directory)
        source = root / 'development'
        shutil.copytree(ROOT / 'development', source)
        if args.revision:
            for path in (source / 'hook_capture').glob('*.py'):
                content = subprocess.run(['git', 'show', args.revision + ':development/hook_capture/' + path.name],
                    cwd=ROOT, capture_output=True, check=True).stdout
                path.write_bytes(content)
        results['source_revision'] = args.revision or 'working-tree-snapshot'
        sys.path.insert(0, str(source))
        from hook_capture.store import Recorder
        from hook_capture.analysis import rebuild, summary
        results['source_hashes'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in (source / 'hook_capture').glob('*.py')}
        secret = 'SYNTHETIC-BEARER-CREDENTIAL-482739'
        capture = root / 'primitive-capture'
        recorder = Recorder(capture, 'synthetic')
        first = recorder.artifact({'headers': {'Authorization': 'Bearer ' + secret}, 'stdout': secret})
        first_value = json.loads(gzip.decompress((capture / first['path']).read_bytes()))
        second = recorder.artifact({'stdout': secret})
        second_value = json.loads(gzip.decompress((capture / second['path']).read_bytes()))
        results['declared_bearer_echo'] = {'first_artifact': first_value, 'later_artifact': second_value,
                                            'token_learned': secret in recorder.secrets}

        disabled = root / 'disabled.json'
        disabled.write_text('{"enabled": false}')
        disabled.chmod(0o600)
        env = dict(os.environ, HERMES_HOOK_CAPTURE_CONFIG=str(disabled),
                   PYTHONPATH=os.pathsep.join((str(source), str(ROOT))))
        hook = root / 'bearer-hook.py'
        hook.write_text('import json\nprint(json.dumps(' + repr({'authorization': 'Bearer ' + secret, 'echo': secret}) + '))\n')
        settings = root / 'settings.json'
        settings.write_text(json.dumps({'hooks': {'PreToolUse': [{'hooks': [{'type': 'command',
            'command': sys.executable + ' ' + str(hook)}]}]}}))
        capture = root / 'real-capture'
        config = {'enabled': True, 'run_id': 'synthetic', 'root': str(capture),
                  'plugin_root': str(PLUGIN), 'host_root': '', 'capture_sources': results['source_hashes'],
                  'fingerprints': {str(PLUGIN / name): hashlib.sha256((PLUGIN / name).read_bytes()).hexdigest()
                                   for name in ('bridge.py', 'remote_hooks.py', '__init__.py', 'bin/hook_runner.py')}}
        configuration = root / 'config.json'
        configuration.write_text(json.dumps(config))
        configuration.chmod(0o600)
        code = ('from pathlib import Path\nfrom lifeos_hook_bridge.bridge import HookBridge\n'
                'bridge=HookBridge(Path(' + repr(str(settings)) + '),Path(' + repr(str(root)) + '))\n'
                'print(__import__("json").dumps(bridge.pre_tool_call("terminal", {"command":"pwd"}, session_id="synthetic-bearer")))\n'
                'bridge.close()\n')
        baseline = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=20)
        prefix = 'from hook_capture.instrument import install\ninstall(' + repr(str(configuration)) + ')\n'
        traced = subprocess.run([sys.executable, '-c', prefix + code], env=env, capture_output=True, text=True, timeout=20)
        events = [json.loads(line) for p in capture.glob('runs/*/events/*/*.jsonl') for line in p.read_text().splitlines()]
        artifacts = [{'event': event, 'value': json.loads(gzip.decompress((capture / event['data_ref']['path']).read_bytes()))}
                     for event in events if event.get('data_ref')]
        results['real_bearer_hook'] = {'baseline_exit': baseline.returncode, 'traced_exit': traced.returncode,
            'same_outcome': baseline.stdout == traced.stdout, 'baseline_stdout': baseline.stdout, 'traced_stdout': traced.stdout,
            'baseline_stderr': baseline.stderr, 'traced_stderr': traced.stderr,
            'leak_stages': sorted({item['event']['stage'] for item in artifacts if secret in json.dumps(item['value'])})}
        label = args.revision or 'working-tree'
        (OUT / (label + '-real-bearer-hook-artifacts.json')).write_text(json.dumps(artifacts, indent=2))

        capture = root / 'integrity-capture'
        recorder = Recorder(capture, 'synthetic')
        first = recorder.emit('valid.artifact', data={'content': 'ordinary evidence'})
        second = {**first, 'event_id': uuid.uuid4().hex, 'sequence': 2, 'stage': 'corrupted.reference',
                  'data_ref': {**first['data_ref'], 'sha256': '0' * 64}}
        with recorder.event_path.open('a') as stream:
            stream.write(json.dumps(second) + '\n')
        results['repeated_path_wrong_digest'] = {'first_reference': first['data_ref'],
                                                'second_reference': second['data_ref'], 'summary': summary(rebuild(capture))}

        capture = root / 'deep-record-capture'
        recorder = Recorder(capture, 'synthetic')
        recorder.emit('valid.before')
        with recorder.event_path.open('a') as stream:
            stream.write('{"nested":' + '[' * 1100 + '0' + ']' * 1100 + '}\n')
        recorder.emit('valid.after')
        try:
            results['deeply_nested_record'] = {'summary': summary(rebuild(capture))}
        except Exception as error:
            results['deeply_nested_record'] = {'exception_type': type(error).__name__, 'exception': str(error)}
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
