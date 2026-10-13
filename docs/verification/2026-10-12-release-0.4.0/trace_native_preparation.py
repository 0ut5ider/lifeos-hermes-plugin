# ABOUTME: Traces the public native deployment command in a retained failed reference installation.
# ABOUTME: Keeps raw filesystem diagnostics private and reports only execution status and resource limits.
import json,os,resource,subprocess,sys
from pathlib import Path
job=Path('/home/lifeos-hermes/.hermes/.lifeos-releases/67d6e3a05d24436cae2a4dd41c32028c')
package=job/'package';root=job/'reference-home/failed';home=job/'reference-home'
sys.path.insert(0,str(package))
from lifeos_hook_bridge.native_dependencies import dependency_environment
bun=job/'tools/bun';catalog=package/'lifeos_hook_bridge/dependency_locks'
environment=dict(os.environ,HOME=str(home),CLAUDE_CONFIG_DIR=str(root),LIFEOS_DIR=str(root/'LIFEOS'),LIFEOS_CONFIG_DIR=str(home/'.config/LIFEOS'),PROJECTS_DIR=str(home/'Projects'),PYTHONDONTWRITEBYTECODE='1')
with dependency_environment(root,bun,catalog) as paths:
 environment.update(paths)
 command=['strace','-f','-e','trace=%file,process','-o',str(job/'native-trace.log'),str(bun),str(package/'lifeos/LifeOS/Tools/DeployCore.ts'),'--config-root',str(root),'--config-dir',str(home/'.config/LIFEOS'),'--skill-root',str(package/'lifeos/LifeOS'),'--apply']
 with (job/'native-trace.stdout').open('w') as stdout,(job/'native-trace.stderr').open('w') as stderr:
  result=subprocess.run(command,cwd=home,env=environment,stdout=stdout,stderr=stderr,timeout=600)
report={'operation':job.name,'diagnostic_command':'Public DeployCore with frozen dependency wrapper and filesystem syscall tracing','exit_code':result.returncode,'nofile_limit':list(resource.getrlimit(resource.RLIMIT_NOFILE)),'active_profile_changed':False,'raw_trace_private':True}
(job/'native-trace-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
(job/'native-trace.done').write_text(str(result.returncode)+'\n')
print(json.dumps(report,indent=2))
