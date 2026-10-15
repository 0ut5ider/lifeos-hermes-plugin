# ABOUTME: Tests removal inventory and publication boundaries with synthetic files and real services.
# ABOUTME: Records measured refusal gaps without changing product code or production data.
import json
from pathlib import Path
import tempfile
import unittest

import test_removal_inventory as inventory_fixture
import test_removal_services as service_fixture
from optional.lifeos_release_manager.release_programs import ProgramTransaction,ProgramConflict

OUTPUT=Path(__file__).parent


class NativeInventoryReview(unittest.TestCase):
    def test_extra_native_tool_refuses_unqualified_removal(self):
        fixture=inventory_fixture.RemovalInventoryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        owner=fixture.installed/'LIFEOS/TOOLS/OwnerCustom.ts'
        owner.write_text('// Synthetic owner tool that needs native dependencies.\n')
        observed={}
        try:
            result=fixture.operation().native(fixture.installed,fixture.source,fixture.reference,bridge=fixture.bridge)
            observed['admitted']=True;observed['owner_tool_selected_for_removal']=owner in result['files']
            observed['native_dependency_trees_selected']=len(result['dependencies'])
            transaction=ProgramTransaction(fixture.home/'review-removal-transaction')
            transaction.prepare(directories={},files=result['files'],dependencies=result['dependencies'])
            transaction.apply()
            observed['owner_tool_preserved_after_removal']=owner.is_file()
            observed['native_dependencies_removed']=not (fixture.installed/'node_modules').exists()
            transaction.restore()
        except ValueError as error:observed['refused']=str(error)
        (OUTPUT/'extra-native-tool.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertIn('refused',observed)


class ServiceDefinitionReview(unittest.TestCase):
    def test_added_pulse_override_refuses_before_gateway_stop(self):
        fixture=service_fixture.RemovalServicesTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        operation=fixture.operation();signature=operation.prepare(removed=[fixture.installed_pulse])
        before={role:fixture.fixture.properties(role)['MainPID'] for role in fixture.fixture.units}
        directory=fixture.installed_pulse.with_name(fixture.installed_pulse.name+'.d')
        directory.mkdir();path=directory/'50-owner-review.conf'
        path.write_text('[Service]\nEnvironment=SYNTHETIC_REVIEW_FLAG=1\n');path.chmod(0o600)
        observed={'before':before}
        try:
            try:operation.stop(signature)
            except ValueError as error:observed['refused']=str(error)
            observed['after']={role:fixture.fixture.properties(role)['MainPID'] for role in fixture.fixture.units}
        finally:
            path.unlink();directory.rmdir();fixture.fixture.command('systemctl','--user','daemon-reload')
        (OUTPUT/'added-pulse-override.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertEqual(observed['after'],before)


class PublicationReview(unittest.TestCase):
    def test_changed_staged_directory_refuses_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'current';source=root/'candidate'
            target.mkdir();source.mkdir()
            (target/'program.py').write_text('synthetic-original\n')
            (source/'program.py').write_text('synthetic-candidate\n')
            transaction=ProgramTransaction(root/'transaction')
            transaction.prepare(directories={target:source},files={})
            def checkpoint(point):
                if point=='directory-retained':
                    (root/'transaction/incoming-0/program.py').write_text('synthetic-unreviewed-candidate\n')
            observed={}
            try:transaction.apply(checkpoint=checkpoint);observed['apply_succeeded']=True
            except ProgramConflict as error:observed['refused']=str(error)
            observed['unreviewed_candidate_published']=target.exists() and (target/'program.py').read_text()=='synthetic-unreviewed-candidate\n'
            observed['journal_state']=json.loads((root/'transaction/programs.json').read_text())['state']
            (OUTPUT/'staged-edit-before-candidate.json').write_text(json.dumps(observed,indent=2)+'\n')
            self.assertFalse(observed['unreviewed_candidate_published'])

    def test_retained_directory_edit_refuses_candidate_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'current';source=root/'candidate'
            target.mkdir();source.mkdir()
            (target/'program.py').write_text('synthetic-original\n')
            (source/'program.py').write_text('synthetic-candidate\n')
            transaction=ProgramTransaction(root/'transaction')
            transaction.prepare(directories={target:source},files={})
            def checkpoint(point):
                if point=='directory-retained':
                    (root/'transaction/before-0/program.py').write_text('synthetic-later-retained-edit\n')
            observed={}
            try:transaction.apply(checkpoint=checkpoint);observed['apply_succeeded']=True
            except ProgramConflict as error:observed['refused']=str(error)
            observed['candidate_published']=target.exists()
            observed['journal_state']=json.loads((root/'transaction/programs.json').read_text())['state']
            try:transaction.check_applied();observed['completed_state_valid']=True
            except ProgramConflict as error:observed['completed_state_refusal']=str(error)
            (OUTPUT/'retained-edit-before-candidate.json').write_text(json.dumps(observed,indent=2)+'\n')
            self.assertIn('refused',observed)
