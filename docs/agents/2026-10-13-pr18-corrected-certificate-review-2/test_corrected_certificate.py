# ABOUTME: Exercises the certificate checker against actual qualification evidence and altered receipts.
# ABOUTME: Keeps all certificate output in temporary directories and never publishes a release asset.
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

OUT=Path(__file__).resolve().parent
FILES=('private-stage-candidate-build.json','integration-archive-bound-10459df6.json',
    'integration-archive-bound-10459df6.stderr','private-stage-native-equality.json',
    'private-stage-interruption-observation.json','private-stage-recovery-admission.json',
    'private-stage-fresh-recovery.json','private-stage-installed-update.json',
    'permissions-before.stderr','permissions-after.stderr')

class CorrectedCertificateTests(unittest.TestCase):
    def run_certificate(self, file=None, mutation=None):
        with tempfile.TemporaryDirectory(prefix='certificate-control-',dir=OUT.parent) as folder:
            root=Path(folder)
            shutil.copy2(OUT/'certify_corrected_prerelease.py',root/'certify_corrected_prerelease.py')
            for name in FILES:
                shutil.copy2(OUT/name,root/name)
            (root/'primary-native-metadata').mkdir()
            shutil.copy2(OUT/'primary-native-metadata/native-metadata-probe.json',root/'primary-native-metadata/native-metadata-probe.json')
            if file:
                value=json.loads((root/file).read_text());mutation(value)
                (root/file).write_text(json.dumps(value))
            result=subprocess.run([sys.executable,'-B',str(root/'certify_corrected_prerelease.py')],
                cwd=OUT.parents[2],capture_output=True,text=True,timeout=40)
            published=(root/'test-release-0.4.2-rc.3/RELEASE-CERTIFICATE.json').exists()
            return result,published

    def test_valid_actual_receipts_create_a_scoped_test_certificate(self):
        result,published=self.run_certificate()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(result.stderr,'');self.assertTrue(published)

    def test_invalid_recovery_admission_refuses_certificate_creation(self):
        mutations=(lambda v:v.update(exit_code=1),lambda v:v.update(identifier='f'*32),
            lambda v:v.update(stderr='Synthetic admission failure'),
            lambda v:v.update(stdout=json.dumps({'identifier':v['identifier'],'state':'queued','action':'apply'})))
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)):
                result,published=self.run_certificate('private-stage-recovery-admission.json',mutation)
                self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertFalse(published)
                self.assertIn('AssertionError',result.stderr)

    def test_missing_inactive_services_refuse_certificate_creation(self):
        for name in ('private-stage-fresh-recovery.json','private-stage-installed-update.json'):
            for unit in ('hermes-gateway.service','com.lifeos.pulse.service'):
                with self.subTest(receipt=name,unit=unit):
                    result,published=self.run_certificate(name,lambda v:v['services'][unit].update(LoadState='not-found'))
                    self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertFalse(published)
                    self.assertIn('AssertionError',result.stderr)

    def test_missing_native_program_publication_refuses_certificate_creation(self):
        for changes in ({'native_present':False},{'program_state':'preparing'},{'program_targets':0}):
            with self.subTest(changes=changes):
                result,published=self.run_certificate('private-stage-fresh-recovery.json',lambda v:v.update(changes))
                self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertFalse(published)
                self.assertIn('AssertionError',result.stderr)

if __name__=='__main__':
    unittest.main(verbosity=2)
