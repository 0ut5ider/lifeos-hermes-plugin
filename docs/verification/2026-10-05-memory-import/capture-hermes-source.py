# ABOUTME: Copies two authorized Hermes source files under their actual writer locks.
# ABOUTME: Sends a private byte archive without changing original memory contents or configuration.
from contextlib import ExitStack
from pathlib import Path
import fcntl,hashlib,io,json,os,stat,sys,tarfile
root=Path('/root/.hermes/memories')
with ExitStack() as stack:
 for name in ('MEMORY.md','USER.md'):
  descriptor=os.open(root/(name+'.lock'),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
  stack.callback(os.close,descriptor)
  fcntl.flock(descriptor,fcntl.LOCK_EX)
 files={};proof={}
 for name in ('MEMORY.md','USER.md'):
  p=root/name;before=p.lstat()
  assert stat.S_ISREG(before.st_mode) and before.st_size<=1024*1024
  data=p.read_bytes();after=p.lstat()
  stamp=lambda s:(s.st_dev,s.st_ino,s.st_mtime_ns,s.st_size,s.st_mode)
  assert stamp(before)==stamp(after)
  files[name]=data;proof[name]={'size':len(data),'digest':hashlib.sha256(data).hexdigest(),'mode':stat.S_IMODE(after.st_mode),'mtime_ns':after.st_mtime_ns}
 for name,data in files.items():assert (root/name).read_bytes()==data
 files['source-receipt.json']=(json.dumps({'host':'192.168.8.213','source':str(root),'originals_preserved':True,'files':proof},indent=2)+'\n').encode()
 with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as archive:
  for name,data in files.items():
   item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o600
   archive.addfile(item,io.BytesIO(data))
