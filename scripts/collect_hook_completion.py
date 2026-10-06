# ABOUTME: Verifies and exports synthetic hook completion evidence from the development container.
# ABOUTME: Retains public artifacts and model wire hashes while keeping full request bodies private.

import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

import paired_lifecycle_effects as driver


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def export(configuration, output, pulse, question, config_name, web, batch):
    config = driver.read_json(configuration)
    public = output / 'public'
    public.mkdir(exist_ok=True)
    copy(configuration, public / 'configuration.json')
    for name in ('paired_lifecycle_effects.py', 'paired_response_server.py', 'paired_pulse_guards.py',
                 'clarify_fixture_host.py', 'paired_config_audit.py', 'config_audit_fixture_host.py',
                 'verify_web_safety.py', 'web_fixture_host.py', 'batch_patch_fixture.py',
                 'test_native_pulse_guards.py', 'collect_hook_completion.py', 'launch.py'):
        copy(configuration.parent / name, public / 'runners' / name)
    proof = []

    def client(home, destination):
        result = driver.read_json(home / 'result.json')
        for name, digest in result['raw_artifacts'].items():
            assert sha(home / name) == digest, (home, name)
            copy(home / name, destination / name)
        copy(home / 'result.json', destination / 'result.json')
        for name in ('waiting-state.json', 'question-presented.json', 'terminal.log'):
            if (home / name).exists():
                copy(home / name, destination / name)
        requests = driver.read_json(home / 'requests-private.json')
        assert (home / 'requests-private.json').stat().st_mode & 0o777 == 0o600
        conversation = [r for r in requests if driver.conversation_request(r, home.name)]
        for row in conversation:
            assert row['upstream_status'] == 200, (home, row['path'], row.get('upstream_status'))
            for field in ('body', 'response_body'):
                assert hashlib.sha256(base64.b64decode(row[field + '_base64'])).hexdigest() == row[field + '_sha256']
        for definition in result['hook_definitions']:
            for name, digest in definition['source_files'].items():
                assert sha(Path(name)) == digest, name
        proof.append({'case': home.name, 'home': str(home), 'session_id': result['session_id'],
                      'request_sha256': [r['body_sha256'] for r in conversation],
                      'response_sha256': [r['response_body_sha256'] for r in conversation],
                      'upstream_status': [r['upstream_status'] for r in conversation],
                      'actual_model': sorted({r['actual_model'] for r in conversation}),
                      'raw_artifacts_verified': True})

    paired = []
    for name in (pulse, question):
        assert (output / (name + '.done')).read_text().strip() == '0'
        copy(output / (name + '.done'), public / (name + '.done'))
        copy(output / (name + '.log'), public / (name + '.log'))
        result_path = output / ('results-' + name) / 'paired-results.json'
        records = driver.read_json(result_path)['cases']
        for record in records:
            assert driver.check_pair(record) == [], record
            for side in ('native', 'hermes'):
                home = Path(config[side]['home_root']) / ('results-' + name) / record['id']
                client(home, public / side / record['id'])
        paired.extend(records)
    driver.write_json(public / 'paired-results.json', {'cases': paired})

    assert (output / (config_name + '.done')).read_text().strip() == '0'
    changes = driver.read_json(output / ('results-' + config_name) / 'config-results.json')
    assert changes['native'] == changes['hermes'] and changes['native']['hook_calls'] == 8
    copy(output / ('results-' + config_name) / 'config-results.json', public / 'config-results.json')
    for side in ('native', 'hermes'):
        home = Path(config[side]['home_root']) / ('results-' + config_name) / 'config-audit'
        for name in ('events.jsonl', 'hooks.jsonl', 'terminal.log', 'bridge.log',
                     '.claude/LIFEOS/MEMORY/OBSERVABILITY/config-changes.jsonl'):
            if (home / name).exists():
                copy(home / name, public / side / 'config-audit' / name)

    assert (output / (web + '.done')).read_text().strip() == '0'
    web_results = driver.read_json(output / ('results-' + web) / 'web-results.json')
    assert len(web_results['cases']) == 4
    copy(output / ('results-' + web) / 'web-results.json', public / 'web-results.json')
    for record in web_results['cases']:
        home = Path(config['hermes']['home_root']) / ('results-' + web) / record['id']
        client(home, public / 'hermes' / record['id'])
        copy(output / ('results-' + web) / (record['id'] + '-native-handler.json'),
             public / 'native' / record['id'] / 'handler-result.json')

    assert (output / (batch + '.done')).read_text().strip() == '0'
    batch_results = driver.read_json(output / ('results-' + batch) / 'batch-results.json')
    assert len(batch_results['cases']) == 2
    copy(output / ('results-' + batch) / 'batch-results.json', public / 'batch-results.json')
    for record in batch_results['cases']:
        assert record['native'] == record['hermes']
        for side in ('native', 'hermes'):
            home = Path(config['hermes']['home_root']) / ('results-' + batch) / record['id'] / side
            for name in ('plan.json', 'tool-result.txt', 'hooks.jsonl', 'host.log', 'batch-result.json',
                         '.claude/LIFEOS/MEMORY/STATE/work.json',
                         '.claude/LIFEOS/MEMORY/STATE/complexity-ratchet/batch-fixture.json',
                         '.claude/LIFEOS/MEMORY/WORK/pair-run/ISA.md',
                         '.claude/LIFEOS/MEMORY/WORK/pair-run/.checkpoint-state.json'):
                if (home / name).exists():
                    copy(home / name, public / side / record['id'] / name)
            for program in __import__('batch_patch_fixture').PROGRAMS:
                assert sha(home / '.claude/hooks' / (program + '.hook.ts')) == sha(
                    Path(config[side]['hook_root']) / 'hooks' / (program + '.hook.ts'))
    for name in (config_name, web, batch):
        copy(output / (name + '.done'), public / (name + '.done'))
        copy(output / (name + '.log'), public / (name + '.log'))
    native = Path(config['native']['hook_root'])
    hermes = Path(config['hermes']['hook_root'])
    selected = ['hooks/' + name + '.hook.ts' for name in (
        'TabState', 'EventLogger', 'Safety', *__import__('batch_patch_fixture').PROGRAMS)]
    selected += ['LIFEOS/PULSE/modules/hooks.ts']
    programs = {name: {'native': sha(native / name), 'hermes': sha(hermes / name)} for name in selected}
    differences = sorted(name for name, row in programs.items() if row['native'] != row['hermes'])
    # Prepared Hermes hooks include privacy, remote-file, and checkpoint patches.
    # The comparison asserts selected effects, not identical full programs.
    driver.write_json(public / 'wire-proof.json', proof)
    hermes_source = Path(config['hermes']['environment']['PYTHONPATH'].split(':')[0])
    critical = ('agent/display.py', 'agent/tool_guardrails.py', 'agent/tool_result_classification.py')
    critical_hashes = {name: sha(hermes_source / name) for name in critical}
    for name in critical:
        copy(hermes_source / name, public / 'runtime-source' / name)
    bridge = Path(config['hermes']['plugins_path']) / 'lifeos-hook-bridge/bridge.py'
    copy(bridge, public / 'runtime-source/bridge.py')
    driver.write_json(public / 'runtime-check.json', {'native_cli_sha256': sha(Path(config['native']['command'][0])),
        'hermes_interpreter_sha256': sha(Path(config['hermes']['command'][0])), 'selected_program_sha256': programs,
        'runner_sha256': {path.name: sha(path) for path in (public / 'runners').iterdir()},
        'native_patch_differences': differences,
        'hermes_critical_source_sha256': critical_hashes, 'bridge_sha256': sha(bridge),
        'native_cli_version': '2.1.272', 'native_web_and_multiedit_cli_dispatch': False,
        'hermes_base': '758ad514eb0e800547e015edf05aa18f78b78d82',
        'lifeos_base': '5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c'})
    with tarfile.open(output / 'hook-completion-public.tar.gz', 'w:gz') as archive:
        archive.add(public, arcname='hook-completion')
    print(json.dumps({'verified_model_clients': len(proof), 'selected_programs': len(programs),
                      'archive': str(output / 'hook-completion-public.tar.gz')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('configuration', type=Path)
    parser.add_argument('output', type=Path)
    for name in ('pulse', 'question', 'config', 'web', 'batch'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    export(args.configuration, args.output, args.pulse, args.question, args.config, args.web, args.batch)
