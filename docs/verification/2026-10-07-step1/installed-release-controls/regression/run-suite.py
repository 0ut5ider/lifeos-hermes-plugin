import json,signal,sys,unittest,subprocess
from lifeos_hook_bridge import profile_services
original_service_run=profile_services._run
def traced_service_run(*arguments):
 try:
  return original_service_run(*arguments)
 except Exception:
  unit=arguments[-1] if arguments else ''
  row={'arguments':arguments}
  for name,command in [('show',['systemctl','--user','show',unit]),('journal',['journalctl','--user','-u',unit,'-n','30','--no-pager'])]:
   result=subprocess.run(command,capture_output=True,text=True)
   row[name]={'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
  with open(sys.argv[1]+'.service-refusals.jsonl','a') as trace:trace.write(json.dumps(row)+'\n')
  raise
profile_services._run=traced_service_run
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:])
previous=str(signal.getsignal(signal.SIGINT))
signal.signal(signal.SIGINT,signal.default_int_handler)
print("INTERRUPT_DEFAULT="+str(signal.getsignal(signal.SIGINT)),flush=True)
result=unittest.TextTestRunner(verbosity=2).run(suite)
with open(sys.argv[1],"w") as output:
 json.dump({"tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skips":len(result.skipped),"successful":result.wasSuccessful(),"interrupt_before":previous,"failed_cases":[case.id() for case,detail in result.failures+result.errors]},output,indent=2)
 output.write("\n")
sys.exit(0 if result.wasSuccessful() else 1)
