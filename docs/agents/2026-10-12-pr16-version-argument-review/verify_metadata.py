# ABOUTME: Verifies reviewed patch declarations and unchanged native metadata against the sealed candidate archive.
# ABOUTME: Records public program identities without extracting or modifying the sealed source.
import hashlib,json,subprocess,tarfile
from pathlib import Path
repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin');out=Path(__file__).parent
paths=['VERSION','lifeos_hook_bridge/plugin.yaml','lifeos_hook_bridge/dashboard/manifest.json','optional/lifeos_release_manager/plugin.yaml','optional/lifeos_release_manager/dashboard/manifest.json']
versions={}
for name in paths:
 text=(repo/name).read_text()
 versions[name]=text.strip() if name=='VERSION' else json.loads(text)['version'] if name.endswith('.json') else next(line.split(':',1)[1].strip() for line in text.splitlines() if line.startswith('version:'))
assert set(versions.values())=={'0.4.1'}
for name in ['lifeos_hook_bridge/patches','lifeos_hook_bridge/dependency_locks','optional/lifeos_release_manager/release-tools.json']:
 assert subprocess.run(['git','diff','--quiet','origin/main...HEAD','--',name],cwd=repo).returncode==0
result={'status':'PASS','reviewed_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'versions':versions,'patch_groups_unchanged':True,'all_native_locks_and_bun_metadata_unchanged':True}
buildfile=Path('/home/outsider/.cache/lifeos-hermes-managed-20261012/packages/0.4.1-223cbfc1-build.json')
if buildfile.exists():
 build=json.loads(buildfile.read_bytes());assert build['version']=='0.4.1' and build['head']=='223cbfc1681f0b4d3a7bad668d40822a9267137e'
 archive=Path(build['archive']);assert archive.stat().st_size==build['archive_bytes'] and hashlib.sha256(archive.read_bytes()).hexdigest()==build['archive_sha256']
 assert (build['hermes_patch_count'],build['lifeos_patch_count'])==(10,25)
 with tarfile.open(archive) as source:
  for name in paths:assert source.extractfile(name).read()==(repo/name).read_bytes()
  assert source.extractfile('optional/lifeos_release_manager/cli.py').read()==(repo/'optional/lifeos_release_manager/cli.py').read_bytes()
 result['sealed_candidate']={'commit':build['head'],'sha256':build['archive_sha256'],'bytes':build['archive_bytes'],'all_five_declarations_and_cli_match_reviewed_code':True,'hermes_patch_count':10,'lifeos_patch_count':25,'qualification_claimed':False}
else:result['sealed_build_receipt_available_at_expected_path']=False
(out/'metadata-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
