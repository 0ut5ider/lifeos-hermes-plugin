# ABOUTME: Compares private authorized source copies with the pinned Hermes entry parser.
# ABOUTME: Exports content-free parsing evidence and leaves native memory ownership disabled.
from pathlib import Path
import hashlib,json,os,tarfile,sys
from tools.memory_tool_store import MemoryStore
from test_memory_import import MemoryImportTests
from lifeos_hook_bridge.memory_import import _chunks
root=Path(__file__).resolve().parent
os.chmod(root,0o700)
f=MemoryImportTests();f.setUp()
try:
 with tarfile.open(root/'hermes-213-private.tar') as archive:
  for name in ('MEMORY.md','USER.md'):
   data=archive.extractfile(name).read()
   (f.sources/name).write_bytes(data)
   os.chmod(f.sources/name,0o600)
 preview=f.preview()
 snapshot=root/'private-source-review-final'
 saved=f.operation().prepare(snapshot,preview['signature'],account='dashboard:owner')
 proof=[]
 for source in preview['sources']:
  name=Path(source['path']).name
  original=(f.sources/name).read_bytes()
  native=MemoryStore._parse_entries(MemoryStore._read_raw_checked(f.sources/name)[0])
  actual=[row['content'] for row in source['chunks'] if row['content']]
  assert actual==native
  assert (snapshot/'sources'/name).read_bytes()==original
  proof.append({'file':name,'size':len(original),'digest':hashlib.sha256(original).hexdigest(),
    'occurrences':len(source['chunks']),'nonempty_entries':len(actual),'native_parser_matches':True,
    'source_bytes_preserved':True})
 assert not f.configuration.load()['ownership_enabled']
 with f.fixture.memory._transaction() as connection:
  assert connection.execute('SELECT COUNT(*) FROM records').fetchone()[0]==0
  assert connection.execute('SELECT COUNT(*) FROM operations').fetchone()[0]==0
 for data in (b'\xef\xbb\xbf first\r\nline\r\n\xc2\xa7\r\n second\r',b'\n\xc2\xa7\n',b'\xef\xbb\xbf',b'bare \xc2\xa7 symbol',b'a\r\xc2\xa7\rb'):
  path=f.sources/'MEMORY.md';path.write_bytes(data)
  checked=_chunks('MEMORY.md',data)
  assert [row['content'] for row in checked['chunks'] if row['content']]==MemoryStore._parse_entries(MemoryStore._read_raw_checked(path)[0])
 report={'host':'192.168.8.213','source_copies':proof,'ownership_enabled':False,
  'native_publications':0,'synthetic_newline_and_bom_controls':5,
  'hermes_source':str(Path(__import__('tools.memory_tool_store',fromlist=['MemoryStore']).__file__).resolve()),
  'importer_sha256':hashlib.sha256(Path(__import__('lifeos_hook_bridge.memory_import',fromlist=['MemoryImport']).__file__).read_bytes()).hexdigest(),
  'hermes_parser_sha256':hashlib.sha256(Path(__import__('tools.memory_tool_store',fromlist=['MemoryStore']).__file__).read_bytes()).hexdigest()}
 (root/'source-parsing-proof.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'files':len(proof),'native_parser_matches':True,'preserved_source_bytes':True,'native_publications':0}))
finally:f.doCleanups()
