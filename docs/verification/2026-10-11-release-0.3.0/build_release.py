# ABOUTME: Builds committed integration packages with matching versions and pinned native sources.
# ABOUTME: Seals exact program and operator hashes without selecting a live installation.
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

os.umask(0o077)
repo=Path(__file__).resolve().parents[3]
out=Path(__file__).parent
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo).strip()
version=(repo/'VERSION').read_text().strip()
cache=Path('/home/outsider/.cache/lifeos-release-20261011')
cache.mkdir(parents=True,exist_ok=True,mode=0o700)
package=cache/(version+'-'+head[:8])
archive=Path(str(package)+'.tgz')
assert not package.exists() and not archive.exists()
package.mkdir(mode=0o700)
selected=['lifeos_hook_bridge','scripts','tests','docs/deployment/daily-text','VERSION','CHANGELOG.md','README.md',
    'docs/verification/2026-10-11-daily-guest/deliver_morning.py']
committed=subprocess.check_output(['git','archive',head,'--',*selected],cwd=repo)
with tarfile.open(fileobj=io.BytesIO(committed)) as source:source.extractall(package,filter='data')
sys.path.insert(0,str(package))
from lifeos_hook_bridge import install_source,release_version
assert release_version.versions(package)==version
sources=Path('/home/outsider/.cache/lifeos-daily-text-20261007')
started=time.monotonic()
lifeos=install_source.prepare_lifeos(str(sources/'channel-sources/lifeos'),package/'lifeos',
    install_source.SUPPORTED_LIFEOS_COMMIT,package/'lifeos_hook_bridge/patches',install_source.LIFEOS_PATCHES)
hermes=install_source.prepare_supported_hermes(sources/'daily-hermes-clean-base',package/'hermes')
assert install_source.validate_prepared_lifeos(package/'lifeos')==lifeos
assert install_source.validate_supported_hermes(package/'hermes')==hermes
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
files={str(path.relative_to(package)):sha(path) for path in sorted((package/'lifeos_hook_bridge').rglob('*'))
    if path.is_file() and '__pycache__' not in path.parts}
operators={'morning':{'path':'docs/verification/2026-10-11-daily-guest/deliver_morning.py',
    'sha256':sha(package/'docs/verification/2026-10-11-daily-guest/deliver_morning.py')}}
manifest={'version':version,'head':head,'status':'release_candidate','plugin_files':files,'operators':operators,
    'daily_configuration_files':{str(p.relative_to(package)):sha(p) for p in (package/'docs/deployment/daily-text').iterdir() if p.is_file()},
    'prepared_manifest_files':{name:sha(package/name) for name in ['lifeos/lifeos-source-manifest.json','hermes/hermes-source-manifest.json']},
    'native_manifests_verified':True,'live_selection_changed':False,'combined_release_verified':False}
(package/'DAILY-CANDIDATE.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(archive,'w:gz',compresslevel=6) as output:
    for path in sorted(package.iterdir()):
        output.add(path,arcname=path.name,filter=lambda info:None if '__pycache__' in Path(info.name).parts else info)
report={'status':'PASS','version':version,'head':head,'package':str(package),'archive':str(archive),
    'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'plugin_file_count':len(files),
    'hermes_base':hermes['base_commit'],'lifeos_base':lifeos['upstream_commit'],
    'hermes_patch_count':len(hermes['patches']),'lifeos_patch_count':len(lifeos['patches']),
    'elapsed_seconds':round(time.monotonic()-started,3),'native_manifests_verified':True,
    'live_selection_changed':False,'combined_release_verified':False}
(out/(version+'-build.json')).write_text(json.dumps(report,indent=2)+'\n')
(out/(version+'-build.done')).write_text('0\n')
print(json.dumps(report,indent=2))
