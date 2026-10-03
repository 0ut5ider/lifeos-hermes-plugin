# ABOUTME: Enables private instrumentation in the selected development interpreter.
# ABOUTME: Reads account configuration for gateway and detached runner processes.

import os
from pathlib import Path


def start(configuration=None):
    path=Path(configuration if configuration is not None else os.environ.get(
        "HERMES_HOOK_CAPTURE_CONFIG",str(Path.home()/".config/lifeos-development-capture/config.json")))
    if not path.is_file():
        return
    try:
        if path.stat().st_uid!=os.getuid() or path.stat().st_mode & 0o077:
            raise PermissionError("Development capture configuration must be private")
        from .instrument import install
        install(path)
    except Exception as error:
        try:
            os.write(2,f"Development capture startup failed ({type(error).__name__})\n".encode())
        except OSError:
            pass
