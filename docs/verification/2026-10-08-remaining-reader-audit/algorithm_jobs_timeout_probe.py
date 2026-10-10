# ABOUTME: Measures actual concurrent Algorithm request durations with native listener settings.
# ABOUTME: Compares the test listener default with the installed managed Pulse timeout.
import json
from pathlib import Path
import unittest
import test_memory_algorithm_jobs

original = Path.write_text
records = []
for managed in (False, True):
    capture = Path(__file__).with_name('algorithm-jobs-timeout-' + ('managed' if managed else 'default') + '.jsonl').resolve()
    def instrument(path, text, *args, **kwargs):
        if path.name == 'conduit-lifetime.ts':
            text = 'import {appendFileSync} from "node:fs";' + text
            if managed:
                module = path.parent / '.lifeos/LIFEOS/TOOLS/lib/MemoryAccess.ts'
                # The generated module import includes the actual fixture root.
                marker = 'LIFEOS/PULSE/modules/algorithm-tab.ts'
                start = text.index('from "') + len('from "')
                end = text.index(marker) + len(marker)
                module = text[start:end].replace(marker, 'LIFEOS/TOOLS/lib/MemoryAccess.ts')
                text = 'import {memoryHTTPServerOptions} from ' + json.dumps(module) + ';' + text
                text = text.replace('port:0,async fetch', 'port:0,...memoryHTTPServerOptions(),async fetch')
            text = text.replace('async fetch(request){', 'async fetch(request){const started=performance.now();try{')
            text = text.replace('status:404})}});', 'status:404})}finally{appendFileSync(' + json.dumps(str(capture)) + ',JSON.stringify({path:new URL(request.url).pathname,elapsed_ms:performance.now()-started,aborted:request.signal.aborted})+"\\n")}}});')
        return original(path, text, *args, **kwargs)
    Path.write_text = instrument
    suite = unittest.defaultTestLoader.loadTestsFromName('test_memory_algorithm_jobs.MemoryAlgorithmJobRelayTests.test_simultaneous_stale_reads_start_one_job_and_module_stop_ends_children')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    records.append({'managed_server_options':managed,'success':result.wasSuccessful(),'tests':result.testsRun})
Path.write_text = original
original(Path(__file__).with_name('algorithm-jobs-timeout-comparison.json'), json.dumps(records, indent=2)+'\n')
