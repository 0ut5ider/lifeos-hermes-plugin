# ABOUTME: Captures the real prompt hook output during the complete candidate suite.
# ABOUTME: Keeps execution unchanged and saves diagnostic records to a private artifact.
import json,pathlib,sys,unittest
from lifeos_hook_bridge.bridge import HookBridge
original=HookBridge._run_command
output=pathlib.Path(sys.argv[1])
def observe(self,event,command,payload,timeout,environment,process_cwd):
 result=original(self,event,command,payload,timeout,environment,process_cwd)
 if 'PromptProcessing.hook.ts' in command:
  row={'event':event,'command':command,'cwd':process_cwd,'timeout':timeout,'environment_names':sorted(environment),
       'exit_code':None if result is None else result.returncode,'stdout':'' if result is None else result.stdout,
       'stderr':'' if result is None else result.stderr}
  with output.open('a') as log: log.write(json.dumps(row)+'\n')
 return result
HookBridge._run_command=observe
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'))
sys.exit(0 if result.wasSuccessful() else 1)
