# ABOUTME: Runs an isolated profile writer and child inside a real user systemd service.
# ABOUTME: Records process readiness without using messaging adapters or production configuration.
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    role, marker, *arguments = sys.argv[1:]
    marker = Path(marker)
    if arguments:
        marker.with_suffix('.child-ready').write_text(str(os.getpid()))
    else:
        child = subprocess.Popen([sys.executable, __file__, role, str(marker), 'child'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        marker.with_suffix('.ready').write_text(str(os.getpid()))
    while True:
        marker.with_suffix('.child-heartbeat' if arguments else '.heartbeat').write_text(
            json.dumps({'role': role, 'pid': os.getpid(), 'monotonic_ns': time.monotonic_ns()}))
        time.sleep(0.05)


if __name__ == '__main__':
    main()
