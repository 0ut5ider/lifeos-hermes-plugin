# ABOUTME: Verifies the actual failed development operation restored every recorded program target.
# ABOUTME: Compares preserved configuration and service metadata without exporting personal records.
import importlib,json,runpy,sys,types
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

stage=Path('/home/lifeos-hermes/releases/qualification-0.5.0')
profile=Path('/home/lifeos-hermes/.hermes')
identifier='86340dd2f6f8473280cc411f5a3e4102'
baseline=json.loads((stage/'development-prepromotion-baseline.json').read_bytes())
sys.argv=[str(stage/'record_promotion_baseline.py'),'development']
output=StringIO()
with redirect_stdout(output):runpy.run_path(sys.argv[0],run_name='__main__')
current=json.loads(output.getvalue())
assert current==baseline
namespace=types.ModuleType('rollback_manager');namespace.__path__=[str(profile/'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__]=namespace
cli=importlib.import_module(namespace.__name__+'.cli')
programs=importlib.import_module(namespace.__name__+'.release_programs')
job,request=cli.operation(profile,identifier)
assert cli.read_private(job/'status.json')['state']=='rolled_back'
assert request['commit']=='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
assert request['package_sha256']=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
plan=importlib.import_module(namespace.__name__+'.release_operation').validate_plan(job,request)
transaction=programs.ProgramTransaction(job/'program-snapshot',expected_entries_sha256=plan['program_entries_sha256'])
snapshot=transaction._load();assert snapshot['state']=='restored'
for entry in snapshot['entries']:
 assert programs.fingerprint(entry['target'],allow_links=entry['allow_links'])==entry['before']
failure=cli.read_private(job/'worker-failure.json')
assert failure['exception']=='MountError'
assert any(frame['function']=='_run' and frame['line']==69 for frame in failure['frames'])
report={'status':'PASS','operation':identifier,'state':'rolled_back','prior_identity':current['prior_identity'],
 'program_targets_restored':len(snapshot['entries']),'model_and_tiers_preserved':True,
 'credential_file_bytes_preserved':True,'memory_configuration_bytes_preserved':True,
 'all_three_services_and_homes_preserved':True,'failure':failure,
 'personal_records_read':False,'personal_data_imported_or_reset':False,'daily_guest_changed':False}
print(json.dumps(report,indent=2))
