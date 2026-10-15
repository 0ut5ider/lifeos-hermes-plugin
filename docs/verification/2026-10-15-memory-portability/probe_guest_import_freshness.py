# ABOUTME: Separates current configuration, source, and policy differences for a saved import review.
# ABOUTME: Uses the authenticated owner importer and exports equality flags without source contents.
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import types

home=Path('/home/lifeos-hermes');profile=home/'.hermes'
if os.getuid()!=1000 or Path.home()!=home:raise RuntimeError('Use the disposable guest owner')
os.umask(0o077)
package=types.ModuleType('portability_freshness_probe')
package.__path__=[str(profile/'plugins/lifeos-release-manager')];sys.modules[package.__name__]=package
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
owner=importlib.import_module(package.__name__+'.removal_recovery').authenticate(profile,
    credentials['username'],credentials['password'],'dashboard:basic:portability-owner')
del credentials
source,configuration=importlib.import_module(package.__name__+'.memory_workflow')._source(profile)
identifier='da1f3ebcb4ba4c6fb2f3625c8bb40b73'
signature='a2af9e18628bd2a36e0a5b1cdc58653df19850cea7c3e9619723ae2b6f593dc3'
importer=source.memory_module('memory_import').MemoryImport(configuration)
with importer._locks(owner) as selected:
    directory=source.memory_module('memory_import_sources').directory(profile,identifier)
    review=importer.inspect(directory,signature,account=owner)['review']
    settings,_=importer._settings();sources,_=importer._sources()
    fields={'path','status','size','digest','identity','mode','mtime_ns','byte_order_mark'}
    binding=lambda rows:[{key:value for key,value in row.items() if key in fields} for row in rows]
    receipt={'read_only':True,'owner_authenticated':True,'daily_changed':False,'import_identifier':identifier,
        'changed_settings_fields':sorted(key for key in settings if settings.get(key)!=review['settings'].get(key)),
        'source_bindings_equal':binding(sources)==binding(review['sources']),
        'source_origin_equal':importer._source_origin()==review['source_origin'],
        'policy_digest_equal':hashlib.sha256(json.dumps(selected,sort_keys=True).encode()).hexdigest()==review['configuration_digest']}
(home/'install-input/import-freshness-probe.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
