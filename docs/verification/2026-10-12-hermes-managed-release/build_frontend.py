# ABOUTME: Builds the pinned Hermes dashboard through its native package manager APIs.
# ABOUTME: Records compiled artifact provenance without selecting a live release.
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile
import time
out = Path(__file__).resolve().parent
root = Path('/home/outsider/.cache/lifeos-hermes-managed-20261012/ported')
profile = Path('/home/outsider/.cache/lifeos-hermes-managed-20261012/frontend-profile')
profile.mkdir(mode=0o700, exist_ok=True)
os.environ.update(HERMES_HOME=str(profile), PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0, str(root))
from hermes_cli.source_build import source_build_env, prepare_source_dependencies, build_source_web
start = time.monotonic()
try:
    env = source_build_env(explicit=True)
    prepare_source_dependencies(root, ('web',), env=env, explicit=True)
    build_source_web(root, env=env)
    archive = profile / 'hermes-dashboard.tgz'
    with tarfile.open(archive, 'w:gz') as output:
        output.add(root / 'hermes_cli/web_dist', arcname='hermes_cli/web_dist')
    report = {'status': 'PASS', 'source': str(root), 'archive': str(archive),
        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'bytes': archive.stat().st_size,
        'elapsed_seconds': time.monotonic() - start}
    (out / 'frontend-build.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'frontend-build.done').write_text('0\n')
except BaseException:
    (out / 'frontend-build.done').write_text('1\n')
    raise
