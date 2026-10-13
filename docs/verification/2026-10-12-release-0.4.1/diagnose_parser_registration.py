# ABOUTME: Captures actual native parser registration under the selected development profile.
# ABOUTME: Records plugin errors and command names without running handlers or reading memory records.
import faulthandler
import io
import json
import logging
from pathlib import Path
import sys
import time

sys.path.insert(0, sys.argv[1])
folder = Path(sys.argv[2])
sys.argv = ['hermes', 'lifeos-version']
from hermes_cli import main
stream = io.StringIO()
handler = logging.StreamHandler(stream)
logger = logging.getLogger('hermes_cli.main')
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
with (folder / 'parser-registration-stack.txt').open('w') as output:
    faulthandler.dump_traceback_later(8, file=output)
    started = time.monotonic()
    parser, subparsers = main._build_cli_parser()
    faulthandler.cancel_dump_traceback_later()
from hermes_cli.plugins import get_plugin_manager
manager = get_plugin_manager()
value = {'elapsed_seconds': time.monotonic() - started,
    'interpreter': sys.executable, 'prefix': sys.prefix, 'no_user_site': sys.flags.no_user_site,
    'plugins': {name: {'error': plugin.error, 'version': plugin.manifest.version}
        for name, plugin in manager._plugins.items() if 'lifeos' in name},
    'registered_commands': sorted(name for name in manager._cli_commands if name.startswith('lifeos')),
    'attached_commands': sorted(name for name in subparsers.choices if name.startswith('lifeos')),
    'discovery_diagnostics': stream.getvalue()}
(folder / 'parser-registration.json').write_text(json.dumps(value, indent=2) + '\n')
manager.unload()
