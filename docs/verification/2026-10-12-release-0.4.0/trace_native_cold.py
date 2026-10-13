# ABOUTME: Traces the public native deployment command in a retained failed reference installation.
# ABOUTME: Keeps raw filesystem diagnostics private and reports only execution status and resource limits.
import json,os,resource,subprocess,sys
from pathlib import Path
job=Path('/home/lifeos-hermes/.hermes/.lifeos-releases/67d6e3a05d24436cae2a4dd41c32028c')
package=job/'package';home=job/'cold-trace-home';home.mkdir(mode=0o700);root=home/'.claude'
sys.path.insert(0,str(package))
from lifeos_hook_bridge.native_dependencies import dependency_environment
bun=job/'tools/bun';catalog=package/'lifeos_hook_bridge/dependency_locks'
environment=dict(os.environ,HOME=str(home),CLAUDE_CONFIG_DIR=str(root),LIFEOS_DIR=str(root/'LIFEOS'),LIFEOS_CONFIG_DIR=str(home/'.config/LIFEOS'),PROJECTS_DIR=str(home/'Projects'),PYTHONDONTWRITEBYTECODE='1')
if True:
 script='import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from lifeos_hook_bridge.install_source import install_lifeos,SUPPORTED_LIFEOS_COMMIT,LIFEOS_PATCHES;install_lifeos(Path(sys.argv[1])/"lifeos",Path(sys.argv[2])/".claude",Path(sys.argv[2])/"failed",sys.argv[3],SUPPORTED_LIFEOS_COMMIT,Path(sys.argv[1])/"lifeos_hook_bridge/patches",LIFEOS_PATCHES)'
 command=['strace','-f','-e','trace=%file,process','-o',str(job/'native-cold-trace.log'),sys.executable,'-B','-c',script,str(package),str(home),str(bun)]
 with (job/'native-cold-trace.stdout').open('w') as stdout,(job/'native-cold-trace.stderr').open('w') as stderr:
  result=subprocess.run(command,cwd=home,env=environment,stdout=stdout,stderr=stderr,timeout=600)
report={'operation':job.name,'diagnostic_command':'Public install_lifeos with frozen dependency wrapper and filesystem syscall tracing','exit_code':result.returncode,'nofile_limit':list(resource.getrlimit(resource.RLIMIT_NOFILE)),'active_profile_changed':False,'raw_trace_private':True}
(job/'native-cold-trace-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
(job/'native-cold-trace.done').write_text(str(result.returncode)+'\n')
print(json.dumps(report,indent=2))
