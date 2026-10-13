# ABOUTME: Audits PR17 release evidence and public asset identities without deployment actions.
# ABOUTME: Records reproducible hash, receipt, source, and published metadata checks.
import ast
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CANDIDATE = ROOT / 'docs/verification/2026-10-12-release-0.4.1/candidate-96f4f8fb'
BASE = '6c13407f33e5d7c2a982c1618b1a26dd0511f855'
HEAD = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
PROGRAM = '96f4f8fbef21f53ee704eb16f34698bc35b5dc77'
checks = []


def read(name):
    return json.loads((CANDIDATE / name).read_bytes())


def check(name, condition, detail=None):
    checks.append({'check': name, 'status': 'PASS' if condition else 'FAIL', 'detail': detail})


def command(arguments):
    return subprocess.check_output(arguments, cwd=ROOT)


publication = read('publication.json')
certificate = read('RELEASE-CERTIFICATE.json')
acceptance = read('public-installation-verification.json')
published_receipt = read('public-acceptance-asset-publication.json')
certificate_hash = hashlib.sha256((CANDIDATE / 'RELEASE-CERTIFICATE.json').read_bytes()).hexdigest()
check('public certificate exact hash', certificate_hash == acceptance['certificate_sha256'])
check('certificate actual qualification', certificate['production_qualified'] is True and not certificate.get('test_fixture_only'))
check('archive and program identities agree', all(value == PROGRAM for value in (
    publication['program_commit'], certificate['program_commit'], acceptance['program_commit']))
    and publication['assets']['0.4.1-96f4f8fb.tgz']['digest'] == 'sha256:' + certificate['archive_sha256']
    and acceptance['archive_sha256'] == certificate['archive_sha256'])
for name, digest in acceptance['receipts_sha256'].items():
    actual = hashlib.sha256((CANDIDATE / name).read_bytes()).hexdigest()
    check('acceptance receipt ' + name, actual == digest, actual)
for name, digest in certificate['qualification_receipt_sha256'].items():
    actual = hashlib.sha256((CANDIDATE / name).read_bytes()).hexdigest()
    check('qualification receipt ' + name, actual == digest, actual)
check('fresh explicit public installation', read('public-install-verification.json')['status'] == 'PASS'
      and read('public-install-verification.json')['version_selection'] == 'explicit')
check('owner admission binds actual update', read('owner-public-actions-after-bootstrap.json')['operation']
      == read('development-public-update.json')['operation']
      == read('development-public-preparation-after-bootstrap.json')['preparation']['identifier'])
check('143 targets including all aliases', read('development-public-plan-metadata.json')
      [read('development-public-update.json')['operation']]['program_targets'] == 143
      and set(read('development-public-plan-metadata.json')
      [read('development-public-update.json')['operation']]['public_aliases'])
      == {'hermes', 'hermes-agent', 'hermes-acp'})
check('daily and automatic morning limits remain explicit', acceptance['daily_checkpoint']['identity']['version'] == '0.3.1'
      and acceptance['daily_checkpoint']['read_only'] is True
      and acceptance['daily_promotion_verified'] is False
      and acceptance['automatic_morning_observed_for_041'] is False)

for name in ('observe_public_development.py', 'prepare_public_update_after_bootstrap.py'):
    ast.parse((CANDIDATE / name).read_bytes(), filename=name)
    check('helper syntax ' + name, True)
for name in ('cli.py', 'release_programs.py', 'release_worker.py'):
    before = gzip.decompress((CANDIDATE / ('prior-manager-' + name + '.gz')).read_bytes()).decode()
    after = command(['git', 'show', PROGRAM + ':optional/lifeos_release_manager/' + name]).decode()
    expected = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='installed/' + name, tofile='candidate/' + name))
    actual = gzip.decompress((CANDIDATE / ('prior-manager-' + name + '.diff.gz')).read_bytes()).decode()
    check('captured manager diff ' + name, actual == expected)
    release_source = command(['git', 'show', BASE + ':optional/lifeos_release_manager/' + name])
    check('published manager matches sealed product ' + name, release_source == after.encode())
check('bootstrap worker matches sealed product', read('manager-bootstrap.json')['worker_sha256']
      == hashlib.sha256(command(['git', 'show', PROGRAM + ':optional/lifeos_release_manager/release_worker.py'])).hexdigest())

changed = command(['git', 'diff', '--name-only', BASE, HEAD]).decode().splitlines()
check('PR changes documentation only', all(name in {'README.md', 'TODO.md'} or name.startswith('docs/') for name in changed), len(changed))
for tag in ('v0.3.1', 'v0.4.0', 'v0.4.1'):
    live = json.loads(command(['gh', 'api', 'repos/0ut5ider/lifeos-hermes-plugin/releases/tags/' + tag]))
    safe = {key: live[key] for key in ('id', 'tag_name', 'draft', 'prerelease', 'published_at')}
    safe['assets'] = [{key: asset[key] for key in ('id', 'name', 'size', 'digest', 'updated_at')}
                      for asset in live['assets']]
    (OUT / (tag + '-live-assets.json')).write_text(json.dumps(safe, indent=2) + '\n')
    if tag != 'v0.4.1':
        before = read(tag + '-assets-pre-publication.json')
        after = read(tag + '-assets-post-publication.json')
        check(tag + ' historic snapshots unchanged', before == after)
        live_by_name = {asset['name']: asset for asset in safe['assets']}
        check(tag + ' live immutable assets match', all(
            all(live_by_name[asset['name']][key] == asset[key] for key in ('id', 'size', 'digest', 'updated_at'))
            for asset in before['assets']))
    else:
        live_by_name = {asset['name']: asset for asset in safe['assets']}
        check('live 041 original assets match', all(
            all(live_by_name[name][key] == entry[key] for key in ('size', 'digest'))
            for name, entry in publication['assets'].items()))
        check('live 041 acceptance asset matches', all(
            live_by_name[published_receipt['asset']['name']][key] == published_receipt['asset'][key]
            for key in ('id', 'size', 'digest')))
        check('local acceptance asset matches publication',
            'sha256:' + hashlib.sha256((CANDIDATE / 'public-installation-verification.json').read_bytes()).hexdigest()
            == published_receipt['asset']['digest'])
        check('public release is stable', not live['draft'] and not live['prerelease'])
latest = json.loads(command(['gh', 'api', 'repos/0ut5ider/lifeos-hermes-plugin/releases/latest']))
check('latest stable release is 041', latest['tag_name'] == 'v0.4.1')
print(json.dumps({'head': HEAD, 'status': 'PASS' if all(item['status'] == 'PASS' for item in checks) else 'FAIL',
                  'checks': checks}, indent=2))
