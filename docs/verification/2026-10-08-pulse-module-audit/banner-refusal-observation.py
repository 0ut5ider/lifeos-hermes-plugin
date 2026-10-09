# ABOUTME: Observes actual native banner admission using a disposable synthetic owner fixture.
# ABOUTME: Records the operation outcome without reading installed personal data.
from test_memory_banner import MemoryBannerTests
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge.memory_banner import run
import traceback,json
case=MemoryBannerTests();case.setUp()
try:
 case.seed();service=MemoryService(case.fixture.configuration);scope=service.scope(case.fixture.context)
 print(json.dumps(service.native(case.fixture.context,'banner',{'args':['--design=navy'],'width':100})))
 try:run(case.fixture.fixture.memory,scope,args=['--design=navy'],width=100,check_current=lambda:None)
 except Exception:traceback.print_exc()
finally:case.doCleanups()
