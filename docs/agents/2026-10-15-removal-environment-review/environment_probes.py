# ABOUTME: Tests prepared environment bytes against the actual pinned stock sanitizer and migration.
# ABOUTME: Uses synthetic credentials, actual filesystem transactions, and isolated child interpreters.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from optional.lifeos_release_manager import removal_configuration as operation
from optional.lifeos_release_manager.release_programs import ProgramTransaction,publish
import test_removal_preparation as fixtures

OUTPUT=Path(__file__).parent
RUNTIME=Path('/home/outsider/.cache/lifeos-memory-portability-20261015/stock-full-9b204dad/runtime')

class EnvironmentReview(unittest.TestCase):
    def child(self,profile,*,migrate=False):
        code='''import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from hermes_constants import set_hermes_home_override
set_hermes_home_override(sys.argv[2])
from hermes_cli.config import sanitize_env_file,migrate_config
from agent.secret_scope import load_env_file
path=Path(sys.argv[2])/'.env';before=path.read_bytes()
if sys.argv[3]=='migration':
 result=migrate_config(interactive=False,quiet=True)
else:result=sanitize_env_file()
after=path.read_bytes()
print(json.dumps({'unchanged':before==after,'result':result,'parsed':load_env_file(path),'source':__import__('hermes_cli.config',fromlist=['']).__file__}))
'''
        command=[str(RUNTIME/'python-environment/bin/python'),'-B','-X','pycache_prefix='+str(profile/'unused-cache'),'-I','-c',code,str(RUNTIME/'hermes'),str(profile),'migration' if migrate else 'sanitize']
        env={'PATH':os.environ['PATH'],'HOME':str(profile.parent),'HERMES_HOME':str(profile),'PYTHONDONTWRITEBYTECODE':'1','TZ':'UTC','LANG':'C.UTF-8'}
        child=subprocess.run(command,env=env,capture_output=True,text=True,timeout=60)
        self.assertEqual(child.returncode,0,child.stdout+child.stderr);self.assertEqual(child.stderr,'')
        result=json.loads(child.stdout);self.assertEqual(Path(result['source']),RUNTIME/'hermes/hermes_cli/config.py')
        self.assertFalse((profile/'unused-cache').exists());return result

    def test_semantics_and_bytes_survive_stock_sanitizer_and_startup_migration(self):
        cases={
            'missing-lf':(b'API_TOKEN=synthetic-token',b'API_TOKEN=synthetic-token\n',{'API_TOKEN':'synthetic-token'}),
            'crlf':(b'API_TOKEN=synthetic-token\r\nOTHER=x\r\n',b'API_TOKEN=synthetic-token\nOTHER=x\n',{'API_TOKEN':'synthetic-token','OTHER':'x'}),
            'cr-only':(b'API_TOKEN=synthetic-token\rOTHER=x\r',b'API_TOKEN=synthetic-token\nOTHER=x\n',{'API_TOKEN':'synthetic-token','OTHER':'x'}),
            'bom':(b'\xef\xbb\xbfAPI_TOKEN=synthetic-token',b'API_TOKEN=synthetic-token\n',{'API_TOKEN':'synthetic-token'}),
            'comments-and-blank':(b' # Owner comment  \r\n  \r\nAPI_TOKEN=synthetic-token',b' # Owner comment  \n  \nAPI_TOKEN=synthetic-token\n',{'API_TOKEN':'synthetic-token'}),
            'opaque-variable-name':(b'API_TOKEN=pre DISCORD_BOT_TOKEN=synthetic=tail#hash',b'API_TOKEN=pre DISCORD_BOT_TOKEN=synthetic=tail#hash\n',{'API_TOKEN':'pre DISCORD_BOT_TOKEN=synthetic=tail#hash'}),
            'quoted-spaces':(b'  API_TOKEN="  synthetic token  "  \r\n',b'API_TOKEN="  synthetic token  "\n',{'API_TOKEN':'  synthetic token  '}),
            'quoted-hash':(b"API_TOKEN='synthetic # token' # comment\n",b"API_TOKEN='synthetic # token' # comment\n",{'API_TOKEN':'synthetic # token'}),
            'escapes':(b'API_TOKEN="synthetic\\\\path\\\"quote"\n',b'API_TOKEN="synthetic\\\\path\\\"quote"\n',{'API_TOKEN':'synthetic\\path"quote'}),
            'export':(b' export API_TOKEN = synthetic-token  ',b'export API_TOKEN = synthetic-token\n',{'API_TOKEN':'synthetic-token'}),
            'duplicate-keys':(b'API_TOKEN=old\nAPI_TOKEN=new\n',b'API_TOKEN=old\nAPI_TOKEN=new\n',{'API_TOKEN':'new'}),
            'empty-value':(b'API_TOKEN=\n',b'API_TOKEN=\n',{'API_TOKEN':''}),
            'unicode':('API_TOKEN=synthetic-\u00e9\n'.encode(),'API_TOKEN=synthetic-\u00e9\n'.encode(),{'API_TOKEN':'synthetic-\u00e9'}),
            'blank-only':(b' \t\r\n\r',b' \t\n\n',{}),
            'empty':(b'',b'',{}),
        }
        receipts=[]
        for label,(data,expected,parsed) in cases.items():
            with self.subTest(label=label),tempfile.TemporaryDirectory() as folder:
                profile=Path(folder)/'.hermes';profile.mkdir(mode=0o700);workspace=profile/'workspace'
                prepared=operation.environment(data+operation.environment_block(profile,workspace),profile,workspace)
                self.assertEqual(prepared,expected)
                publish(profile/'.env',prepared)
                publish(profile/'config.yaml',b'memory: {provider: builtin, memory_enabled: true, user_profile_enabled: true}\nplugins: {enabled: []}\nplatforms: {discord: {enabled: false}}\n')
                sanitized=self.child(profile);self.assertTrue(sanitized['unchanged']);self.assertEqual(sanitized['parsed'],parsed)
                migrated=self.child(profile,migrate=True);self.assertTrue(migrated['unchanged']);self.assertEqual(migrated['parsed'],parsed)
                receipts.append({'case':label,'prepared_sha256':hashlib.sha256(prepared).hexdigest(),'sanitizer_unchanged':True,'startup_migration_unchanged':True,'synthetic_values_preserved':True})
        (OUTPUT/'stock-environment-matrix.json').write_text(json.dumps(receipts,indent=2)+'\n')

    def test_duplicate_owned_blocks_and_invalid_utf8_refuse_before_output(self):
        profile=Path('/synthetic/.hermes');workspace=profile/'workspace';block=operation.environment_block(profile,workspace)
        with self.assertRaisesRegex(ValueError,'ambiguous'):operation.environment(b'API_TOKEN=synthetic\n'+block+block,profile,workspace)
        for invalid in (b'\xff',b'API_TOKEN=synthetic\xc3',b'\xef\xbb\xbfAPI_TOKEN=\x80',b'API_TOKEN=\xed\xa0\x80'):
            with self.subTest(invalid=invalid),self.assertRaisesRegex(ValueError,'valid UTF-8'):operation.environment(invalid+block,profile,workspace)
        custom=b'HERMES_WRITE_SAFE_ROOT=/synthetic/custom\r\nAPI_TOKEN=synthetic'
        self.assertEqual(operation.environment(custom,profile,workspace),b'HERMES_WRITE_SAFE_ROOT=/synthetic/custom\nAPI_TOKEN=synthetic\n')

    def test_actual_transaction_survives_stock_then_refuses_later_edit_and_restores_original(self):
        fixture=fixtures.RemovalSoftwarePlanTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        (fixture.profile/'plugins').mkdir(mode=0o700);(fixture.home/'.local/bin').mkdir(parents=True,mode=0o700)
        original=b'API_TOKEN=synthetic-token'+operation.environment_block(fixture.profile,fixture.workspace)
        publish(fixture.profile/'.env',original)
        directories,files,dependencies,expected=fixture.plan()
        self.assertEqual(files[fixture.profile/'.env'].read_bytes(),b'API_TOKEN=synthetic-token\n')
        tx=ProgramTransaction(fixture.home/'env-transaction');tx.prepare(directories=directories,files=files,dependencies=dependencies,expected_before=expected)
        tx.apply();self.assertTrue(self.child(fixture.profile)['unchanged']);tx.check_applied()
        later=b'API_TOKEN=synthetic-owner-later\n';publish(fixture.profile/'.env',later)
        with self.assertRaises(ValueError):tx.check_applied()
        with self.assertRaises(ValueError):tx.restore()
        self.assertEqual((fixture.profile/'.env').read_bytes(),later)
        publish(fixture.profile/'.env',b'API_TOKEN=synthetic-token\n');tx.restore()
        self.assertEqual((fixture.profile/'.env').read_bytes(),original)
        (OUTPUT/'transaction-environment.json').write_text(json.dumps({'actual_transaction_apply':True,'stock_sanitizer_no_rewrite':True,'later_edit_refused_and_preserved':True,'exact_original_bytes_restored':True},indent=2)+'\n')

    def test_baseline_unterminated_result_is_rewritten_by_real_stock(self):
        with tempfile.TemporaryDirectory() as folder:
            profile=Path(folder)/'.hermes';profile.mkdir(mode=0o700)
            old=b'API_TOKEN=synthetic-token';publish(profile/'.env',old)
            result=self.child(profile);self.assertFalse(result['unchanged']);self.assertEqual(result['result'],1)
            self.assertEqual((profile/'.env').read_bytes(),old+b'\n')
            (OUTPUT/'baseline-startup-red.json').write_text(json.dumps({'baseline_bytes':len(old),'stock_bytes':len(old)+1,'stock_added_only_lf':True,'sanitizer_fixes':1},indent=2)+'\n')
