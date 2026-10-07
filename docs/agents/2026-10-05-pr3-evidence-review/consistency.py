# ABOUTME: Checks every 2026-10-05 paired client record against its result.json, state files, and raw hashes.
# ABOUTME: Run from docs/verification of a tree that holds the 71987ce files plus the ignored raw captures.
import json, glob, os, hashlib
n = bad = 0
for p in sorted(glob.glob('2026-10-05-paired-*/paired-results.json')) + ['2026-10-05-paired-context-response/final/paired-results.json']:
    base = os.path.dirname(p)
    for case in json.load(open(p))['cases']:
        for side in ('native', 'hermes'):
            d = f'{base}/{side}/{case["id"]}'
            r = json.load(open(f'{d}/result.json'))
            rec = case[side]
            issues = [f'result.json[{k}]' for k, v in rec.items() if r.get(k) != v]
            if json.load(open(f'{d}/after-state.json')) != rec['after']: issues.append('after-state.json')
            if json.load(open(f'{d}/before-state.json')) != rec['before']: issues.append('before-state.json')
            for a, h in r['raw_artifacts'].items():
                f = f'{d}/{a}'
                if not os.path.exists(f): issues.append(f'missing {a}')
                elif hashlib.sha256(open(f, 'rb').read()).hexdigest() != h: issues.append(f'hash {a}')
            n += 1
            if issues: bad += 1; print(p, case['id'], side, issues)
print('client records checked', n, 'with issues', bad)
