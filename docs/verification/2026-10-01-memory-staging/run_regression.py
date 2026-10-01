# ABOUTME: Runs the complete memory regression against owned distributed source fixtures.
# ABOUTME: Writes raw test output and an exit marker for detached execution.
from pathlib import Path
import os
import subprocess
import sys

root=Path(__file__).resolve().parents[3]
output=Path(__file__).resolve().parent
command=[sys.executable,'-m','unittest','discover','-v','-s','tests','-p','test_memory*.py']
with (output/'regression.txt').open('w') as stream:
    stream.write('Source revision: 39e7bae\n');stream.flush()
    result=subprocess.run(command,cwd=root,stdout=stream,stderr=subprocess.STDOUT,env=os.environ)
(output/'regression.done').write_text(str(result.returncode)+'\n')
