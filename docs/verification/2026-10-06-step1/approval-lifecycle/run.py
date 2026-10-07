# ABOUTME: Runs real protected instruction approval controls.
# ABOUTME: Retains completion through disconnection.
import traceback
from pathlib import Path
from permission_approval_controls import run
root=Path(__file__).parent
code=1
try:
 code=run(root/"configuration.json",root/"approval-complete-results")
except BaseException:
 traceback.print_exc()
finally:
 (root/"run.done").write_text(str(code)+"\n")
