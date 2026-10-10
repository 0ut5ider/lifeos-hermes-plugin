# ABOUTME: Builds the current Hermes dashboard through its pinned native source builder.
# ABOUTME: Keeps dependency and application output within the isolated acceptance home.
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
package = stage / 'package'
installed = Path(json.loads((stage / 'fresh-store-installed.json').read_text())['fresh_store_review']['installed'])
os.environ.update(HOME=str(installed.parent), HERMES_HOME=str(stage / 'profile'),
    TZ='America/Toronto', CI='1', PATH='/home/lifeos-hermes/.local/bin:/usr/bin:/bin')
sys.path.insert(0, str(package / 'hermes'))
from hermes_cli.source_build import source_build_env, prepare_source_dependencies, build_source_web
environment = source_build_env(explicit=True)
prepare_source_dependencies(package / 'hermes', ('web',), env=environment, explicit=True)
build_source_web(package / 'hermes', env=environment)
index = package / 'hermes/hermes_cli/web_dist/index.html'
if not index.is_file():
    raise RuntimeError('The native dashboard build has no entry page')
print(json.dumps({'dashboard_entry': str(index), 'live_services_changed': False}))
