# ABOUTME: Exercises the retained removal command through a real password-authenticated terminal.
# ABOUTME: Sends fixture credentials only after terminal echo is disabled and exports safe admission metadata.
import argparse
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import signal
import termios
import time

os.umask(0o077)
parser=argparse.ArgumentParser()
parser.add_argument('identifier');parser.add_argument('action',choices=('recover','rollback'))
parser.add_argument('--wrong-password',action='store_true');parser.add_argument('--label',required=True)
args=parser.parse_args()
home=Path('/home/lifeos-hermes');profile=home/'.hermes'
assert os.getuid()==1000 and Path.home()==home
assert len(args.identifier)==32 and all(x in '0123456789abcdef' for x in args.identifier)
assert args.label and all(x in 'abcdefghijklmnopqrstuvwxyz0123456789-' for x in args.label)
output=home/'install-input/recovery-auth'/args.label;output.mkdir(parents=True,mode=0o700)
helper=profile/'.lifeos-portability'/args.identifier/'removal/recover'
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
password='synthetic-deliberately-wrong-password' if args.wrong_password else credentials['password']
before={name:hashlib.sha256((profile/'memories'/name).read_bytes()).hexdigest() for name in ('MEMORY.md','USER.md')}
started=time.monotonic();pid,terminal=pty.fork()
if pid==0:
    os.execv(str(helper),[str(helper),args.action])
captured=bytearray();username_sent=False;password_sent=False;exit_code=None
receipt={'status':'FAIL','daily_changed':False,'action':args.action,'workflow':args.identifier,
    'actual_terminal':True,'wrong_password':args.wrong_password,'raw_credentials_exported':False}
try:
    while time.monotonic()-started<180:
        readable,_,_=select.select([terminal],[],[],0.25)
        if readable:
            try:data=os.read(terminal,65536)
            except OSError:data=b''
            if data:captured.extend(data)
        if not username_sent and b'Dashboard username: ' in captured:
            os.write(terminal,(credentials['username']+'\n').encode());username_sent=True
        if not password_sent and b'Dashboard password: ' in captured:
            if termios.tcgetattr(terminal)[3] & termios.ECHO:
                raise RuntimeError('The password prompt does not disable terminal echo')
            os.write(terminal,(password+'\n').encode());password_sent=True
        finished,status=os.waitpid(pid,os.WNOHANG)
        if finished:
            exit_code=os.waitstatus_to_exitcode(status);break
    if exit_code is None:
        os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
        raise TimeoutError('The retained recovery command does not finish')
    admitted=('The authenticated removal recovery starts. Operation: '+args.identifier).encode() in captured
    after={name:hashlib.sha256((profile/'memories'/name).read_bytes()).hexdigest() for name in before}
    receipt.update(exit_code=exit_code,username_prompt=username_sent,password_prompt=password_sent,
        password_echo_disabled=password_sent,admitted=admitted,builtin_memory_unchanged=before==after,
        before_sha256=before,after_sha256=after)
    expected=(exit_code==1 and not admitted) if args.wrong_password else (exit_code==0 and admitted)
    if expected and username_sent and password_sent and before==after:receipt['status']='PASS'
except Exception as error:
    receipt['error_type']=type(error).__name__
finally:
    try:
        finished,_=os.waitpid(pid,os.WNOHANG)
        if not finished:os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
    except ChildProcessError:pass
    os.close(terminal)
    safe=bytes(captured).replace(credentials['password'].encode(),b'[redacted]').replace(password.encode(),b'[redacted]')
    (output/'terminal.txt').write_bytes(safe)
    receipt['elapsed_seconds']=time.monotonic()-started
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (output/'observation.done').write_text('0\n' if receipt['status']=='PASS' else '1\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status']=='PASS' else 1)
