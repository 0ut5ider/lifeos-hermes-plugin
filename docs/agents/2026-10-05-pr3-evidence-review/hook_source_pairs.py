# ABOUTME: Compares the selected hook source digests that each client recorded in result.json for every case.
# ABOUTME: Shows which paired cases ran a different hook program on the native and Hermes sides.
import json, glob, os
for p in sorted(glob.glob('2026-10-05-paired-*/paired-results.json')) + ['2026-10-05-paired-context-response/final/paired-results.json']:
    for case in json.load(open(p))['cases']:
        hs = {}
        for side in ('native', 'hermes'):
            r = json.load(open(os.path.join(os.path.dirname(p), side, case['id'], 'result.json')))
            hs[side] = {'/'.join(k.split('/')[-2:]): v for d in r['hook_definitions'] for k, v in d['source_files'].items()}
        diff = {k: (hs['native'].get(k, '')[:10], hs['hermes'].get(k, '')[:10])
                for k in set(hs['native']) | set(hs['hermes']) if hs['native'].get(k) != hs['hermes'].get(k)}
        print(os.path.dirname(p), case['id'], 'SAME' if not diff else 'DIFF ' + json.dumps(diff, sort_keys=True))
