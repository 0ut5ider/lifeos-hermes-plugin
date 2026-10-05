# ABOUTME: Compares native reference LifeOS program hashes with the prepared Hermes LifeOS source manifest.
# ABOUTME: Lists differing files that no lifeos-*.patch at 71987ce touches. Run from docs/verification.
import json, subprocess
REPO = '/home/outsider/Projects/Hermes_agent/LifeOS_plugin'
native = json.load(open('2026-10-05-paired-tool-log/runtime-check.json'))['native_program_sha256']
prepared = {k[len('lifeos/'):]: v for k, v in json.load(open(
    '2026-10-05-paired-context-response/runtime-manifest.json'))['source_sha256'].items() if k.startswith('lifeos/')}
patched = set()
names = subprocess.run(['git', '-C', REPO, 'ls-tree', '-r', '71987ce', '--name-only', 'patches'],
                       capture_output=True, text=True).stdout.split()
for name in (n for n in names if '/lifeos-' in n):
    out = subprocess.run(['git', '-C', REPO, 'show', f'71987ce:{name}'], capture_output=True, text=True).stdout
    patched |= {l[len('+++ b/LifeOS/install/'):] for l in out.splitlines() if l.startswith('+++ b/LifeOS/install/')}
diff = sorted(k for k in native if k in prepared and native[k] != prepared[k])
unexplained = [k for k in diff if k not in patched]
print('native programs', len(native), 'also in prepared', sum(k in prepared for k in native), 'differ', len(diff),
      'explained by a lifeos patch', len(diff) - len(unexplained), 'unexplained', len(unexplained))
print('\n'.join(unexplained))
