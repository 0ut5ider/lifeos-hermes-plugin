# ABOUTME: Runs corrected isolated client controls for native hook decisions.
# ABOUTME: Records nonzero completion when a measured requirement fails.
import json,traceback
from pathlib import Path
from paired_lifecycle_effects import GUARD_FILE_BRANCHES,run_controls
root=Path(__file__).resolve().parent
code=1
try:
 code=run_controls(json.loads((root/'configuration.json').read_text()),root/'file-results-corrected',list(GUARD_FILE_BRANCHES))
except BaseException:
 traceback.print_exc()
finally:
 (root/'run.done').write_text(str(code)+'\n')
