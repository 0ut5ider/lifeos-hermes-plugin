# ABOUTME: Independently verifies stable program and Bun asset identities and unchanged native locks.
# ABOUTME: Reads sealed sources without bytecode writes and records only public program metadata.
import hashlib,json,subprocess,sys,tarfile,tempfile,zipfile
from pathlib import Path
repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
out=Path(__file__).parent
source=repo/'docs/verification/2026-10-12-release-0.4.0'
build=json.loads((source/'stable-bunfixed-build.json').read_bytes())
temporary=tempfile.TemporaryDirectory(prefix='pr15-immutable-archive-')
package=Path(temporary.name)/'package';package.mkdir(mode=0o700)
with tarfile.open(build['archive']) as archive:
    archive.extractall(package,filter='data')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(build['archive'])==build['archive_sha256']
assert Path(build['archive']).stat().st_size==build['archive_bytes']
sys.path.insert(0,str(package))
from optional.lifeos_release_manager.release_stage import validate_package
cert=json.loads((source/'BUNFIXED-PRIVATE-CERTIFICATE.json').read_bytes())
manifest=validate_package(package,cert)
assert manifest['head']==build['head'] and manifest['version']=='0.4.0'
catalog=json.loads((package/'lifeos_hook_bridge/dependency_locks/catalog.json').read_bytes())
assert len(catalog['packages'])==12 and catalog['bun_version']=='1.4.3'
locks=[]
for row in catalog['packages'].values():
    relative='lifeos_hook_bridge/dependency_locks/'+row['lock_file']
    before=subprocess.check_output(['git','show','origin/main:'+relative],cwd=repo)
    current=(repo/relative).read_bytes()
    sealed=(package/relative).read_bytes()
    assert before==current==sealed
    locks.append({'path':relative,'sha256':hashlib.sha256(sealed).hexdigest()})
tools=json.loads((package/'optional/lifeos_release_manager/release-tools.json').read_bytes())['linux-x86_64']
bunroot=Path('/home/outsider/.cache/lifeos-hermes-managed-20261012/fixed-bun-tools')
archive=bunroot/tools['name']
assert archive.stat().st_size==tools['size'] and sha(archive)==tools['sha256']
with zipfile.ZipFile(archive) as z:
    binary=z.read(tools['member'])
assert hashlib.sha256(binary).hexdigest()==sha(bunroot/'bun')
version=subprocess.check_output([str(bunroot/'bun'),'--version'],text=True).strip()
assert version==tools['version']==catalog['bun_version']
result={'status':'PASS','reviewed_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
'program_commit':build['head'],'program_archive_sha256':build['archive_sha256'],'archive_bytes':build['archive_bytes'],
'qualified_source_manifests_valid':True,'hermes_patch_count':build['hermes_patch_count'],'lifeos_patch_count':build['lifeos_patch_count'],
'unchanged_locks':locks,'bun_version':version,'bun_archive_bytes':tools['size'],'bun_archive_sha256':tools['sha256'],
'bun_binary_sha256':sha(bunroot/'bun'),'certificate_used':'Private fixture only, no public release qualified'}
(out/'asset-identity-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
