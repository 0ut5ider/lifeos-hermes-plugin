# ABOUTME: Builds the committed stable candidate with fixed native sources and dependency inputs.
# ABOUTME: Retains the sealed archive and safe build receipt outside temporary build storage.
import json
import os
from pathlib import Path
import shutil
import subprocess

out = Path(os.environ.get('LIFEOS_QUALIFICATION_OUTPUT', str(Path(__file__).resolve().parent)))
out.mkdir(mode=0o700, parents=True, exist_ok=True)
repo = Path(__file__).resolve().parents[3]
cache = Path('/home/outsider/.cache/lifeos-hermes-managed-20261012')
scratch = Path('/tmp/lifeos-release-0.4.2-20261013')
retained = Path('/home/outsider/.cache/lifeos-release-0.4.2-20261013')
scratch.mkdir(mode=0o700, exist_ok=True)
retained.mkdir(mode=0o700, exist_ok=True)
command = [str(cache/'native-test-environment/bin/python'), '-B', str(repo/'scripts/build_managed_release.py'),
    '--output', str(scratch/'packages'), '--hermes-source', str(cache/'upstream'),
    '--lifeos-source', '/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos',
    '--python-closure', str(cache/'dependency-profile/installs/86c8a0d486dc06f6/environments/279bc6c8268c436487b3322f8bd97285/workspace')]
try:
    with (out/'build.stdout').open('w') as stdout, (out/'build.stderr').open('w') as stderr:
        result = subprocess.run(command, cwd=repo, env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'},
            stdout=stdout, stderr=stderr, timeout=1800)
    if result.returncode:
        raise RuntimeError('Candidate build refuses; inspect the retained diagnostic output')
    report = json.loads((out/'build.stdout').read_text())
    archive = Path(report['archive'])
    target = retained/archive.name
    if target.exists():
        raise FileExistsError('The retained candidate archive already exists')
    shutil.copy2(archive, target)
    report['archive'] = str(target)
    (out/'stable-build.json').write_text(json.dumps(report, indent=2)+'\n')
    (out/'build.done').write_text('0\n')
except BaseException:
    (out/'build.done').write_text('1\n')
    raise
