# ABOUTME: Verifies the actual unpatched stock source before the public installation replay.
# ABOUTME: Admits only exact source and dashboard archive files before any plugin installation.
import hashlib,json,os,stat,tarfile
from pathlib import Path

home=Path('/home/lifeos-hermes')
stage=home/'releases/qualification-0.5.0'
runtime=home/'runtime/stock-hermes'
source=home/'releases/stock-source.tar'
metadata=json.loads((stage/'stock-source.json').read_bytes())
assert metadata['commit']=='71d34bad1045610252eda02ee79549436896e784' and metadata['patched'] is False
assert hashlib.sha256(source.read_bytes()).hexdigest()==metadata['archive_sha256']=='e8acf0dfc6329d85b75c5625412c463798d1cd3ae6507aaf88b717dc74e2c6fc'
frontend=home/'releases/hermes-dashboard.tgz'
frontend_sha256=hashlib.sha256(frontend.read_bytes()).hexdigest()
assert frontend_sha256=='e7c93e754de99b6ec66ae17ae313377dc513104da2776a099c391a7aab347bec'
expected=set()
counts=[]
for admitted in (source,frontend):
 files=links=0
 with tarfile.open(admitted) as archive:
  for item in archive.getmembers():
   name=Path(item.name);assert not name.is_absolute() and '..' not in name.parts
   selected=runtime/name
   if item.isfile():
    assert selected.resolve().is_relative_to(runtime) and selected.is_file() and not selected.is_symlink()
    assert selected.read_bytes()==archive.extractfile(item).read()
    expected.add(name.as_posix());files+=1
   elif item.issym():
    assert selected.is_symlink() and os.readlink(selected)==item.linkname
    expected.add(name.as_posix());links+=1
   else:assert item.isdir()
 counts.append((files,links))
actual=set()
for directory,folders,names in os.walk(runtime,followlinks=False):
 for name in folders+names:
  selected=Path(directory)/name
  mode=selected.lstat().st_mode
  if stat.S_ISDIR(mode):continue
  assert stat.S_ISREG(mode) or stat.S_ISLNK(mode)
  actual.add(selected.relative_to(runtime).as_posix())
assert actual==expected
plugins=home/'.hermes/plugins'
assert not plugins.is_symlink()
assert not plugins.exists() or plugins.is_dir() and not any(plugins.iterdir())
assert not (home/'.claude').exists()
assert not (home/'.hermes/integration-release.json').exists()
report={'status':'PASS','guest':113,'address':'192.168.8.244','hermes_commit':metadata['commit'],'hermes_patches':0,'stock_source_sha256':metadata['archive_sha256'],'source_files_verified':counts[0][0],'source_links_verified':counts[0][1],'dashboard_sha256':frontend_sha256,'dashboard_files_verified':counts[1][0],'runtime_files_verified':len(actual),'complete_runtime_file_set_verified':True,'release_manager_installed':False,'lifeos_installed':False,'production_guest_changed':False,'public_installation_verified':False}
(stage/'stock-source-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
