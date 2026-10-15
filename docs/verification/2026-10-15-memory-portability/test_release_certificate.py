# ABOUTME: Checks that release certification refuses missing, mixed, and incomplete qualification evidence.
# ABOUTME: Uses copied safe receipts and actual package identities without running a guest or model.
import importlib.util
from pathlib import Path
import tempfile
import unittest

path=Path(__file__).with_name('certify_release.py')
spec=importlib.util.spec_from_file_location('portability_certificate',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CertificateEvidenceTests(unittest.TestCase):
    def test_identity_refuses_another_package(self):
        for key in ('version','commit','package_sha256'):
            active={**module.IDENTITY,'verification':'verified','modified_files':[]}
            active[key]='another-package'
            with self.subTest(key=key),self.assertRaises(ValueError):module.identity(active)

    def test_identity_refuses_modified_or_unverified_code(self):
        for change in ({'modified_files':['changed.py']},{'verification':'unverified'}):
            active={**module.IDENTITY,'verification':'verified','modified_files':[],**change}
            with self.subTest(change=change),self.assertRaises(ValueError):module.identity(active)

    def test_incomplete_removal_refuses(self):
        value={'workflow':module.FAULT,'workflow_status':{'state':'verified'},
            'publication_status':{'state':'verification_required'},
            'workflow_receipt':{'application_verified':True},
            'active_software_present':{'lifeos':False,'lifeos-hook-bridge':False,'lifeos-release-manager':False},
            'native_configuration_present':False,'removal_marker_present':True,'recovery_helper_present':True}
        with self.assertRaises(ValueError):module.removed(value,module.FAULT)

    def test_partial_software_inventory_refuses(self):
        value={'workflow':module.FAULT,'workflow_status':{'state':'verified'},
            'publication_status':{'state':'verified'},'workflow_receipt':{'application_verified':True},
            'active_software_present':{'lifeos':False},'native_configuration_present':False,
            'removal_marker_present':True,'recovery_helper_present':True}
        with self.assertRaises(ValueError):module.removed(value,module.FAULT)

    def test_optimized_python_is_not_required_for_checks(self):
        with self.assertRaises(ValueError):module.require(False,'measured refusal')

    def test_learning_requires_actual_effects(self):
        value={'actual_tool_success':False,'later_fact_published':False,'prior_memory_preserved':False}
        with self.assertRaises(ValueError):module.effects(value,tuple(value))

    def test_recall_requires_the_marker_and_tool_selection(self):
        value={'marker_matched':False,'expected_tool_selection':False}
        with self.assertRaises(ValueError):module.effects(value,tuple(value))

    def test_authentication_requires_the_expected_workflow_and_action(self):
        value={'workflow':module.NORMAL,'action':'rollback'}
        with self.assertRaises(ValueError):module.authentication(value,module.FAULT,'recover')

    def test_missing_review_closure_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):module.review_closure(Path(directory))


if __name__=='__main__':unittest.main()
