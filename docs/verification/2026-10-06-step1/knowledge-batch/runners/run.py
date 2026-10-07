import traceback
from pathlib import Path
from knowledge_batch_delivery import run
root=Path(__file__).parent
code=1
try:
 code=run(root/'configuration.json',root/'knowledge-batch-delivery-final-results')
except BaseException:
 traceback.print_exc()
finally:
 (root/'run.done').write_text(str(code)+'\n')
