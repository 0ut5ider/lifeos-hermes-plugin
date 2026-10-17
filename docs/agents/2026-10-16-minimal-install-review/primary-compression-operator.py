# ABOUTME: Measures hypothetical archive layouts without publishing installable release assets.
# ABOUTME: Counts compressed bytes in memory and preserves the qualified source archive.
import hashlib, json, subprocess, tarfile
from pathlib import Path

root=Path(__file__).parent
source=Path('/home/outsider/.cache/lifeos-release-0.7.3-20261016/packages/0.7.3-70fa8390.tgz')
class Sink:
    def __init__(self):self.count=0;self.sha=hashlib.sha256()
    def write(self,data):self.count+=len(data);self.sha.update(data);return len(data)
    def flush(self):pass

result={'status':'RUNNING','installable_or_qualified':False,'compression':'Python tarfile streaming gzip, default level 9','variants':{}}
try:
    for variant in ['all','without_git_metadata','without_git_metadata_and_stock']:
        sink=Sink();included=0;uncompressed=0
        with tarfile.open(source,'r|gz') as old,tarfile.open(fileobj=sink,mode='w|gz') as new:
            for member in old:
                if variant!='all' and '.git' in Path(member.name).parts:continue
                if variant=='without_git_metadata_and_stock' and member.name=='stock-hermes.tgz':continue
                stream=old.extractfile(member) if member.isfile() else None
                new.addfile(member,stream)
                included+=1;uncompressed+=member.size
        result['variants'][variant]={'compressed_bytes':sink.count,'tar_member_bytes':uncompressed,'members':included}
        (root/'compression.json').write_text(json.dumps(result,indent=2)+'\n')
    result['status']='PASS'
finally:
    (root/'compression.json').write_text(json.dumps(result,indent=2)+'\n')
    (root/'compression.done').write_text('0\n' if result['status']=='PASS' else '1\n')
