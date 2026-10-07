# ABOUTME: Diffs raw per-client effect files for every 2026-10-05 paired case after light normalization.
# ABOUTME: Shows which native-versus-Hermes differences the driver's summarized after-state hides.
import base64, json, re, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/pr3full')
UNITS = sorted((ROOT / 'docs/verification').glob('2026-10-05-paired-*'))


def files(path):
    data = json.loads(path.read_text())
    return {k: base64.b64decode(v['content_base64']).decode(errors='replace') for k, v in data.items()}


def normalize(text, side_dir, session):
    text = text.replace(session, '<SESSION>')
    text = re.sub(r'/home/[^"\s]*?/results/[^/"\s]+', '<HOME>', text)
    text = re.sub(r'/home/[^"\s]*?/workspace/[^"\s]*?/(results|final)/[^/"\s]+', '<HOME>', text)
    text = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?', '<TS>', text)
    text = re.sub(r'\b1[78]\d{11}\b', '<EPOCH_MS>', text)
    return text


for unit in UNITS:
    base = unit / 'final' if (unit / 'final/paired-results.json').exists() else unit
    cases = json.loads((base / 'paired-results.json').read_text())['cases']
    for case in cases:
        name = case['id']
        changed = {}
        for side in ('native', 'hermes'):
            d = base / side / name
            result = json.loads((d / 'result.json').read_text())
            before, after = files(d / 'fixture-files-before.json'), files(d / 'fixture-files-after.json')
            changed[side] = {k: normalize(v, d, result['session_id']) for k, v in after.items()
                             if before.get(k) != v and k != 'settings.json'}
            changed[side]['__removed__'] = json.dumps(sorted(set(before) - set(after)))
            changed[side] = {k: v for k, v in changed[side].items() if 'hermes-transcripts/' not in k}
        keys = sorted(set(changed['native']) | set(changed['hermes']))
        diffs = [k for k in keys if changed['native'].get(k) != changed['hermes'].get(k)]
        print(f'== {unit.name[16:]} {name}: changed={sorted(k for k in keys if k != "__removed__")} differing={diffs}')
        for k in diffs:
            print(f'   [{k}]')
            print('     native:', (changed['native'].get(k) or 'ABSENT')[:700].replace('\n', '\\n'))
            print('     hermes:', (changed['hermes'].get(k) or 'ABSENT')[:700].replace('\n', '\\n'))
