# ABOUTME: Checks the exact unpublished PR29 archive and version declarations without installation.
# ABOUTME: Verifies candidate identity, selected source bytes, manifests, and catalog compatibility.
from pathlib import Path, PurePosixPath
import hashlib,json,sys,tarfile,re
root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root))
from lifeos_hook_bridge.release_version import versions
from optional.lifeos_release_manager.release_catalog import VERSION,MAX_MEMBERS,MAX_EXTRACTED_BYTES
from optional.lifeos_release_manager.release_stage import validate_files
from ruamel.yaml import YAML
pin='c86b5887b899ca779afbb217c33843e1ee12c381'
package=Path('/home/outsider/.cache/lifeos-memory-portability-20261015/removal-workflow-packages/0.6.0-c86b5887')
archive=package.with_name(package.name+'.tgz')
expected='9e2a1939efbaccc94abaa879b265f1af447f9bdfe0b82aecc76f872f15fa9fb7'
with archive.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
assert digest==expected and archive.stat().st_size==288167820
manifest=json.loads((package/'DAILY-CANDIDATE.json').read_bytes())
assert manifest['version']=='0.6.0' and manifest['head']==pin
assert manifest['status']=='release_candidate' and manifest['combined_release_verified'] is False
assert manifest['live_selection_changed'] is False
assert versions(package)=='0.6.0' and VERSION.fullmatch('0.6.0')
declarations={'VERSION':(package/'VERSION').read_text().strip()}
for name in ('lifeos_hook_bridge','optional/lifeos_release_manager'):
 for suffix in ('plugin.yaml','dashboard/manifest.json'):
  path=name+'/'+suffix;data=(package/path).read_bytes()
  assert data==(root/path).read_bytes()
  value=YAML(typ='safe').load(data) if path.endswith('.yaml') else json.loads(data)
  assert value['version']=='0.6.0';declarations[path]=value['version']
validate_files(package/'lifeos_hook_bridge',{name.removeprefix('lifeos_hook_bridge/'):value for name,value in manifest['plugin_files'].items()},forbid_bytecode=True)
validate_files(package/'optional/lifeos_release_manager',manifest['manager_files'],forbid_bytecode=True)
validate_files(package/'python-runtime',manifest['python_runtime_files'],forbid_bytecode=True)
selected=set(declarations)|{'DAILY-CANDIDATE.json'};seen=set();total=0;archived={}
with tarfile.open(archive,'r|gz') as source:
 for number,member in enumerate(source,1):
  name=member.name.rstrip('/');relative=PurePosixPath(name);total+=member.size
  assert number<=MAX_MEMBERS and total<=MAX_EXTRACTED_BYTES
  assert name and name not in seen and not relative.is_absolute() and str(relative)==name
  assert not any(part in ('.','..') for part in relative.parts) and '\\' not in name
  assert member.isfile() or member.isdir();seen.add(name)
  if name in selected:
   assert member.isfile()
   with source.extractfile(member) as stream:data=stream.read()
   assert data==(package/name).read_bytes();archived[name]=hashlib.sha256(data).hexdigest()
assert set(archived)==selected
assert 'RELEASE-CERTIFICATE.json' not in seen
result={'review_commit':pin,'archive_sha256':digest,'archive_bytes':archive.stat().st_size,'declarations':declarations,'exact_source_and_archive_declarations_match':True,'program_and_dependency_maps_verified':True,'archive_members':len(seen),'archive_expanded_bytes':total,'catalog_limits_and_version_compatible':True,'candidate_not_qualified':True,'combined_release_verified':False,'live_selection_changed':False,'qualified_certificate_present':False,'selected_archived_sha256':archived}
print(json.dumps(result,indent=2))
