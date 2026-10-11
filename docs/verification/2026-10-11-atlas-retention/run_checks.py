# ABOUTME: Records Atlas retention tests against the complete certified native sources.
# ABOUTME: Saves commands, output, source hashes, and durable completion markers.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
root = Path(__file__).resolve().parents[3]
out = Path(__file__).parent
label = sys.argv[1]
package = Path(os.environ.get("ATLAS_RETENTION_PACKAGE", "/home/outsider/.cache/lifeos-atlas-20261010/daily-text-0.2.0-11577ed4"))
environment = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(root)+":"+str(root/"tests")+":"+str(package/"hermes"),
 "LIFEOS_HERMES_SOURCE": str(package/"hermes"), "LIFEOS_MEMORY_SOURCE": os.environ.get("LIFEOS_MEMORY_SOURCE", "/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install")}
environment["LIFEOS_TASK_HOOK_PATH"] = str(Path(environment["LIFEOS_MEMORY_SOURCE"])/"hooks/TaskGovernance.hook.ts")
command = [sys.executable, "-W", "error::ResourceWarning", "-m", "unittest", "-v", *sys.argv[2:]]
paths = [*root.glob("lifeos_hook_bridge/memory_atlas*.py"), root/"lifeos_hook_bridge/memory_access.py", root/"lifeos_hook_bridge/memory_service.py", root/"lifeos_hook_bridge/cli.py", *root.glob("tests/*atlas*retention*.py")]
source_hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
started = time.monotonic()
result = subprocess.run(command, cwd=root, env=dict(os.environ, **environment), capture_output=True, text=True)
record = {"command": command, "environment_overrides": environment, "exit_code": result.returncode,
 "duration_seconds": time.monotonic()-started, "source_hashes": source_hashes, "source_hashes_unchanged": all(hashlib.sha256((root/p).read_bytes()).hexdigest() == value for p,value in source_hashes.items())}
(out/(label+".json")).write_text(json.dumps(record, indent=2)+"\n")
(out/(label+".stdout")).write_text(result.stdout)
(out/(label+".stderr")).write_text(result.stderr)
(out/(label+".done")).write_text(str(result.returncode)+"\n")
