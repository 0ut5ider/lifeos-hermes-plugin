# ABOUTME: Computes owner-review digests for public native skill documents in the exact package.
# ABOUTME: Uses configured installation identity without reading memory records or installed source contents.
import hashlib,json,tarfile
from pathlib import Path

profile=Path('/home/lifeos-hermes/.hermes')
config=json.loads((profile/'lifeos-memory.json').read_bytes())
archive=Path('/home/lifeos-hermes/releases/qualification-0.5.0/0.5.0-04efe633.tgz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
expected={}
with tarfile.open(archive) as tar:
 for item in tar.getmembers():
  prefix='lifeos/LifeOS/install/'
  if item.isfile() and item.name.startswith(prefix+'skills/') and item.name.endswith('/SKILL.md'):
   path=item.name[len(prefix):]
   value={'root':str(Path(config['root'])),'principal':config['principal'],'path':path,'content':tar.extractfile(item).read().decode()}
   expected[path]=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
assert len(expected)==56
print(json.dumps(expected,sort_keys=True))
