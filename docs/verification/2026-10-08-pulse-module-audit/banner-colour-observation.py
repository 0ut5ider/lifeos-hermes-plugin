# ABOUTME: Observes actual native banner admission using a disposable synthetic owner fixture.
# ABOUTME: Records the operation outcome without reading installed personal data.
from test_memory_banner import MemoryBannerTests
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge import memory_banner as module
from lifeos_hook_bridge.memory_operational_views import projection
from datetime import datetime,timezone
import json,re
case=MemoryBannerTests();case.setUp()
try:
 case.seed();service=MemoryService(case.fixture.configuration);scope=service.scope(case.fixture.context);memory=case.fixture.fixture.memory
 with memory._transaction() as connection:
  contents,_=module.collect(memory,scope,connection);result=memory._native('banner_view',sources=contents,counts=module.counts(memory),args=['--design=navy'],width=100)
  raw=projection(json.dumps(result));colour=re.compile(r'\x1b\[[0-9;]*m');plain=projection(json.dumps({**result,'stdout':colour.sub('',result['stdout'])}))
  print(json.dumps({'native_colour_sequences':len(colour.findall(result['stdout'])),'validation_accepted':memory._native('validate_source_batch',contents=[raw,plain])['accepted'],'raw_excluded':memory._filter_history(connection,scope,raw,datetime.now(timezone.utc).isoformat())['excluded'],'plain_excluded':memory._filter_history(connection,scope,plain,datetime.now(timezone.utc).isoformat())['excluded']}))
finally:case.doCleanups()
