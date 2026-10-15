# ABOUTME: Verifies the actual unpatched stock source before the public installation replay.
# ABOUTME: Compares source archive entries and confirms no manager or LifeOS installation exists.
import hashlib,json,os,tarfile
from pathlib import Path

home=Path('/home/lifeos-hermes')
stage=home/'releases/qualification-0.5.0'
runtime=home/'runtime/stock-hermes'
source=home/'releases/stock-source.tar'
metadata=json.loads((stage/'stock-source.json').read_bytes())
assert metadata['commit']=='71d34bad1045610252eda02ee79549436896e784' and metadata['patched'] is False
assert hashlib.sha256(source.read_bytes()).hexdigest()==metadata['archive_sha256']=='e8acf0dfc6329d85b75c5625412c463798d1cd3ae6507aaf88b717dc74e2c6fc'
files=links=0
with tarfile.open(source) as archive:
 for item in archive.getmembers():
  name=Path(item.name);assert not name.is_absolute() and '..' not in name.parts
  selected=runtime/name
  if item.isfile():
   assert selected.resolve().is_relative_to(runtime) and selected.is_file() and not selected.is_symlink()
   assert selected.read_bytes()==archive.extractfile(item).read()
   files+=1
  elif item.issym():
   assert selected.is_symlink() and os.readlink(selected)==item.linkname
   links+=1
  else:assert item.isdir()
plugins=home/'.hermes/plugins'
assert not plugins.is_symlink()
assert not plugins.exists() or plugins.is_dir() and not any(plugins.iterdir())
assert not (home/'.claude').exists()
assert not (home/'.hermes/integration-release.json').exists()
report={'status':'PASS','guest':113,'address':'192.168.8.244','hermes_commit':metadata['commit'],'hermes_patches':0,'stock_source_sha256':metadata['archive_sha256'],'source_files_verified':files,'source_links_verified':links,'release_manager_installed':False,'lifeos_installed':False,'production_guest_changed':False,'public_installation_verified':False}
(stage/'stock-source-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
