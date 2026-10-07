import json,signal,sys,unittest
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:])
previous=str(signal.getsignal(signal.SIGINT))
signal.signal(signal.SIGINT,signal.default_int_handler)
print("INTERRUPT_DEFAULT="+str(signal.getsignal(signal.SIGINT)),flush=True)
result=unittest.TextTestRunner(verbosity=2).run(suite)
with open(sys.argv[1],"w") as output:
 json.dump({"tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skips":len(result.skipped),"successful":result.wasSuccessful(),"interrupt_before":previous,"failed_cases":[case.id() for case,detail in result.failures+result.errors]},output,indent=2)
 output.write("\n")
sys.exit(0 if result.wasSuccessful() else 1)
