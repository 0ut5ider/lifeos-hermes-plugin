# ABOUTME: Reproduces recorder defects with synthetic input and real hook processes.
# ABOUTME: Writes sanitized evidence without reading production conversation artifacts.

import argparse
import dataclasses
import gzip
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--development', required=True)
    parser.add_argument('--plugin', required=True)
    args = parser.parse_args()
    sys.path.insert(0, args.development)
    from hook_capture.store import Recorder, safe
    from hook_capture.analysis import rebuild, summary
    from hook_capture import instrument as observer
    evidence = {}
    secret = 'SYNTHETIC-CREDENTIAL-529841'
    body = json.dumps({'api_key': secret, 'echo': secret})
    evidence['http_credentials'] = {
        'header_value_leaked': secret in str(safe({'headers': {'X-API-Key': secret}})),
        'url_password_leaked': secret in safe('http://alice:' + secret + '@localhost/'),
        'url_query_token_leaked': secret in safe('http://localhost/?access_token=' + secret),
    }

    @dataclasses.dataclass
    class Declared:
        api_key: str
        echo: str

    with tempfile.TemporaryDirectory(prefix='independent-recorder-probe-') as temporary:
        root = Path(temporary)
        recorder = Recorder(root / 'capture', 'review')
        for label, value in [('json_string', {'stdout': body}),
                             ('dataclass', Declared(secret, secret)),
                             ('completed_process', subprocess.CompletedProcess(['fixture'], 0, stdout=body, stderr=''))]:
            ref = recorder.artifact(value)
            raw = gzip.decompress((recorder.root / ref['path']).read_bytes()).decode()
            evidence[label] = {'declared_field_redacted': '[REDACTED]' in raw,
                               'echo_credential_stored': secret in raw}
        for name, value in [('nan', float('nan')), ('cycle', [])]:
            if name == 'cycle':
                value.append(value)
            recorder.emit('synthetic.failed_storage', data=value)
        recovered = recorder.emit('synthetic.recovered')
        evidence['capture_loss'] = {'reported_prior_failures': recovered.get('prior_capture_failures'),
                                   'summary': summary(rebuild(recorder.root))}
        failed = Recorder(root / 'failed-summary', 'review')
        failed.emit('hook.failed', invocation_id='failed-invocation', registration_id='failed-registration', status='exception')
        evidence['failed_hook_summary'] = summary(rebuild(failed.root))

        for label, row in [('array', []), ('null', None),
                           ('bad_ref', {'schema_version': 1, 'data_ref': ['bad']}),
                           ('bad_status', {'schema_version': 1, 'status': ['bad']})]:
            case = root / label
            events = case / 'runs/r/events/day/p.jsonl'
            events.parent.mkdir(parents=True)
            events.write_text(json.dumps(row) + '\n')
            try:
                evidence['malformed_' + label] = {'summary': summary(rebuild(case))}
            except Exception as error:
                evidence['malformed_' + label] = {'analysis_exception': type(error).__name__}

        corrupt = Recorder(root / 'corrupt', 'review')
        row = corrupt.emit('synthetic.artifact', data={'content': 'a' * 1000})
        artifact = corrupt.root / row['data_ref']['path']
        damaged = bytearray(artifact.read_bytes())
        damaged[10:14] = b'\xff\xff\xff\xff'
        artifact.write_bytes(damaged)
        try:
            evidence['corrupt_gzip'] = {'summary': summary(rebuild(corrupt.root))}
        except Exception as error:
            evidence['corrupt_gzip'] = {'analysis_exception': type(error).__name__, 'module': type(error).__module__}

        inventory_recorder = Recorder(root / 'inventory', 'review')
        observer.RECORDER = inventory_recorder
        registration_ids = []
        for origin in ('project-a', 'project-b'):
            group = {'hooks': [{'type': 'command', 'command': 'true'}]}
            bridge = SimpleNamespace(settings_path=root / origin / 'settings.json',
                                     hooks={'PreToolUse': [group]}, project_hook_settings={})
            token = observer.CURRENT.set({'_groups': {}})
            observer.groups(bridge, 'PreToolUse', [group])
            registration_ids.append(observer.registration(bridge, 'PreToolUse', group, group['hooks'][0])['registration_id'])
            observer.CURRENT.reset(token)
        inventory_summary = summary(rebuild(inventory_recorder.root))
        evidence['registration_origins'] = {'distinct_origins': 2, 'distinct_registration_ids': len(set(registration_ids)),
                                            'indexed_registrations': inventory_summary['known_registrations']}

        plugin = Path(args.plugin).resolve()
        config = root / 'fixture-config.json'
        fixture_capture = root / 'actual-hook-capture'
        config.write_text(json.dumps({'enabled': True, 'root': str(fixture_capture), 'run_id': 'fixture',
            'plugin_root': str(plugin), 'host_root': '',
            'capture_sources': {'instrument.py': '0' * 64},
            'fingerprints': {str(plugin / name): hashlib.sha256((plugin / name).read_bytes()).hexdigest()
                             for name in ('bridge.py', 'remote_hooks.py', '__init__.py', 'bin/hook_runner.py')}}))
        config.chmod(0o600)
        hook = root / 'fixture_hook.py'
        hook.write_text('import json\nprint(json.dumps({"api_key": ' + repr(secret) + ', "echo": ' + repr(secret) + '}))\n')
        settings = root / 'settings.json'
        settings.write_text(json.dumps({'hooks': {'PreToolUse': [{'hooks': [
            {'type': 'command', 'command': str(sys.executable) + ' ' + str(hook)}]}]}}))
        code = 'from hook_capture.instrument import install\ninstall(' + repr(str(config)) + ')\n'
        code += 'from pathlib import Path\nimport importlib.util,sys\n'
        code += 'spec=importlib.util.spec_from_file_location("review_plugin",' + repr(str(plugin / '__init__.py')) + ',submodule_search_locations=[' + repr(str(plugin)) + '])\n'
        code += 'module=importlib.util.module_from_spec(spec)\nsys.modules["review_plugin"]=module\nspec.loader.exec_module(module)\nHookBridge=module.HookBridge\n'
        code += 'bridge=HookBridge(Path(' + repr(str(settings)) + '),Path(' + repr(str(root)) + '))\n'
        code += 'result=bridge.pre_tool_call("terminal",{"command":"pwd"},session_id="fixture-session")\n'
        code += 'print("OUTCOME:"+__import__("json").dumps(result))\nbridge.close()\n'
        env = dict(os.environ, PYTHONPATH=os.pathsep.join((args.development, str(plugin.parent))))
        traced = subprocess.run([sys.executable, '-c', code], env=env, cwd=root, capture_output=True, text=True, timeout=20)
        baseline = subprocess.run([sys.executable, '-c', code.split('\n', 2)[2]], env=env,
                                  cwd=root, capture_output=True, text=True, timeout=20)
        stages = []
        events = []
        failures = []
        for path in fixture_capture.glob('runs/*/events/*/*.jsonl'):
            for line in path.read_text().splitlines():
                event = json.loads(line)
                events.append(event)
                if event.get('data_ref'):
                    raw = gzip.decompress((fixture_capture / event['data_ref']['path']).read_bytes()).decode()
                    if secret in raw:
                        stages.append(event['stage'])
                    if event['stage'] == 'process.failed':
                        failures.append(json.loads(raw).get('error'))
        evidence['actual_hook'] = {'baseline_exit': baseline.returncode, 'traced_exit': traced.returncode,
                                  'same_outcome': baseline.stdout == traced.stdout,
                                  'credential_leaking_stages': stages,
                                  'process_failures': failures,
                                  'event_stages': sorted(set(event['stage'] for event in events))}
        if baseline.returncode or traced.returncode:
            evidence['actual_hook']['synthetic_stderr'] = {'baseline': baseline.stderr, 'traced': traced.stderr}
        evidence['observer_source_drift'] = {'configured_instrument_hash_incorrect': True,
            'runtime_capture_gap_events': sum(event.get('status') == 'capture_gap' for event in events),
            'observer_hooks_active': any(event['stage'] == 'hook.completed' for event in events)}

    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
