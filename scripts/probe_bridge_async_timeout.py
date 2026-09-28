# ABOUTME: Measures Hermes bridge execution of a timed asynchronous LifeOS hook.
# ABOUTME: Uses disposable markers and waits for a child launched by the bridge.

import json
import sys
import tempfile
import time
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


with tempfile.TemporaryDirectory(prefix="lifeos-bridge-async-timeout-") as temporary:
    root = Path(temporary)
    started = root / "started"
    finished = root / "finished"
    hook = root / "hook.py"
    hook.write_text(
        "import json,sys,time\nfrom pathlib import Path\n"
        "json.load(sys.stdin)\n"
        f"Path({str(started)!r}).touch()\n"
        "time.sleep(3)\n"
        f"Path({str(finished)!r}).touch()\n"
    )
    settings = root / "settings.json"
    settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [{
        "type": "command", "command": f"{sys.executable} {hook}", "async": True, "timeout": 1,
    }]}]}}))
    bridge = HookBridge(settings, root)
    try:
        bridge.pre_llm_call("Reply READY", session_id="async-timeout-probe")
        time.sleep(4)
        print(json.dumps({"started": started.exists(), "finished_after_four_seconds": finished.exists()}))
    finally:
        bridge.close()
