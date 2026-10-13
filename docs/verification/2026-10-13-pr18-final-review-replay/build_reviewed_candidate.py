# ABOUTME: Builds the committed UI-action prerelease candidate with pinned native sources.
# ABOUTME: Keeps build output and completion status detached from this interactive session.
from pathlib import Path
import subprocess,os
base=Path('/home/outsider/.cache/lifeos-ui-install-20261013')
out=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-13-pr18-final-review-replay')
repo=base/'build-source-final'
cache=Path('/home/outsider/.cache/lifeos-hermes-managed-20261012')
command=[str(cache/'native-test-environment/bin/python'),'-B',str(repo/'scripts/build_managed_release.py'),'--output',str(base/'packages'),'--hermes-source',str(cache/'upstream'),'--lifeos-source','/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos','--python-closure',str(cache/'dependency-profile/installs/86c8a0d486dc06f6/environments/279bc6c8268c436487b3322f8bd97285/workspace')]
with (out/'reviewed-build.stdout').open('w') as stdout,(out/'reviewed-build.stderr').open('w') as stderr:
 r=subprocess.run(command,cwd=repo,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr)
(out/'reviewed-build.done').write_text(str(r.returncode)+'\n')
