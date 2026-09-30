# ABOUTME: Checks shared credential containers and bounded cycle discovery.
# ABOUTME: Records synthetic capture failure recovery and source identities.

import base64
import dataclasses
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'development'))
from hook_capture.store import Recorder, declared_secrets
from hook_capture.analysis import rebuild, summary

results = {'source_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (ROOT / 'development/hook_capture').glob('*.py')}}
secret = 'SYNTHETIC-ALIASED-CREDENTIAL-574839'

@dataclasses.dataclass
class Values:
    ordinary: list
    api_key: list

shared = [secret]
nested = {'ordinary_value': secret}
basic = base64.b64encode(('synthetic-user:' + secret).encode()).decode()
authorization = ['Basic ' + basic]
cookie = ['session=' + secret + '; HttpOnly; Path=/']
cases = {
    'shared_list': {'ordinary': shared, 'api_key': shared},
    'shared_nested_dict': {'ordinary': nested, 'api_key': nested},
    'shared_dataclass_list': Values(shared, shared),
    'shared_basic_list': {'ordinary': authorization, 'Authorization': authorization, 'echo': secret},
    'shared_cookie_list': {'ordinary': cookie, 'Set-Cookie': cookie, 'echo': secret},
}
results['aliases'] = {}
with tempfile.TemporaryDirectory(prefix='logging-protocol-cycles-') as directory:
    root = Path(directory)
    for name, value in cases.items():
        recorder = Recorder(root / name, 'synthetic')
        ref = recorder.artifact({'value': value, 'prompt': 'Preserve this ordinary prompt.'})
        data = json.loads(gzip.decompress((recorder.root / ref['path']).read_bytes()))
        raw = json.dumps(data)
        results['aliases'][name] = {'bare_secret_leak': secret in raw,
                                    'encoded_secret_leak': basic in raw,
                                    'ordinary_prompt_preserved': data['prompt'] == 'Preserve this ordinary prompt.',
                                    'bare_secret_learned': secret in recorder.secrets}
    cyclic_list = [secret]
    cyclic_list.append(cyclic_list)
    cyclic_dict = {'ordinary': secret}
    cyclic_dict['self'] = cyclic_dict
    results['cycles'] = {}
    for name, value in (('list', cyclic_list), ('dict', cyclic_dict)):
        learned = set(declared_secrets({'ordinary': value, 'api_key': value}))
        recorder = Recorder(root / ('cycle-' + name), 'synthetic')
        event = recorder.emit('cyclic.artifact', data=value)
        following = recorder.emit('valid.following', data={'prompt': 'Preserve this ordinary prompt.'})
        results['cycles'][name] = {'discovery_terminates_and_learns_secret': secret in learned,
                                   'cyclic_event_returns_none': event is None,
                                   'following_event_written': following is not None,
                                   'recorder_failures': recorder.failures,
                                   'summary': summary(rebuild(recorder.root))}
print(json.dumps(results, indent=2, sort_keys=True))
