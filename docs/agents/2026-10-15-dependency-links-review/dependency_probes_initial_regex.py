# ABOUTME: Exercises the complete software plan with two dependency roots and exact admitted identities.
# ABOUTME: Reproduces the baseline link refusal without editing product sources and preserves later data.
import importlib.util
import json
import os
from pathlib import Path
import unittest

import test_removal_preparation as fixtures
from optional.lifeos_release_manager.release_programs import ProgramTransaction,fingerprint,publish

OUTPUT=Path(__file__).parent

class DependencyPlanReview(unittest.TestCase):
    def fixture(self):
        fixture=fixtures.RemovalSoftwarePlanTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        (fixture.home/'.local/bin').mkdir(parents=True,mode=0o700);(fixture.profile/'plugins').mkdir(mode=0o700)
        first=fixture.dependency();second=fixture.installed/'LIFEOS/PULSE/Observability/node_modules'
        (second/'package').mkdir(parents=True);publish(second/'package/tool.js',b'// Synthetic second dependency\n')
        (second/'.bin').mkdir();(second/'.bin/tool').symlink_to('../package/tool.js')
        (second/'package-alias').symlink_to('package',target_is_directory=True)
        fixture.native['dependencies'][second]=None;fixture.native['before'][second]=fingerprint(second,allow_links=True)
        return fixture,first,second

    def test_baseline_source_reproduces_contained_link_refusal_before_transforms(self):
        fixture,first,second=self.fixture()
        path=OUTPUT/'baseline/optional/lifeos_release_manager/removal_preparation.py'
        spec=importlib.util.spec_from_file_location('optional.lifeos_release_manager.review_dependency_baseline',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        memory=(fixture.profile/'memories/MEMORY.md').read_bytes()
        with self.assertRaisesRegex(ValueError,'regular owner artifacts') as caught:
            module.software(fixture.profile,fixture.installed,fixture.generation,fixture.native,fixture.runtime,fixture.generated,
                workspace=fixture.workspace,pulse=fixture.pulse)
        self.assertFalse((fixture.generated/'config.yaml').exists());self.assertEqual((fixture.profile/'memories/MEMORY.md').read_bytes(),memory)
        (OUTPUT/'baseline-contained-link-refusal.json').write_text(json.dumps({'baseline_failure_reproduced':True,
            'exception':type(caught.exception).__name__,'reason':str(caught.exception),'generated_config_absent':True,
            'retained_memory_unchanged':True},indent=2)+'\n')

    def test_combined_plan_removes_and_restores_both_admitted_roots(self):
        fixture,first,second=self.fixture();before={root:fingerprint(root,allow_links=True) for root in (first,second)}
        memory=(fixture.profile/'memories/MEMORY.md').read_bytes();soul=(fixture.profile/'SOUL.md').read_bytes()
        directories,files,dependencies,expected=fixture.plan()
        self.assertEqual(set(dependencies),{first,second});self.assertEqual({root:expected[root] for root in dependencies},before)
        tx=ProgramTransaction(fixture.home/'combined-dependency-transaction')
        tx.prepare(directories=directories,files=files,dependencies=dependencies,expected_before=expected)
        linked={Path(entry['target']) for entry in tx._load()['entries'] if entry['allow_links']}
        self.assertEqual(linked,{first,second})
        tx.apply();self.assertFalse(first.exists());self.assertFalse(second.exists())
        tx.restore();self.assertEqual({root:fingerprint(root,allow_links=True) for root in (first,second)},before)
        self.assertTrue((first/'.bin/tool').is_symlink());self.assertTrue((second/'package-alias').is_symlink())
        self.assertEqual((fixture.profile/'memories/MEMORY.md').read_bytes(),memory);self.assertEqual((fixture.profile/'SOUL.md').read_bytes(),soul)
        self.assertEqual((fixture.workspace/'owner.txt').read_bytes(),b'Synthetic owner work')
        (OUTPUT/'combined-plan.json').write_text(json.dumps({'dependency_roots':2,'allow_links_only_for_dependencies':True,
            'native_before_identities_preserved':True,'actual_apply_and_restore':True,'file_and_directory_links_restored':True,
            'memory_prompt_and_workspace_unchanged':True},indent=2)+'\n')

    def test_later_second_root_edit_refuses_before_any_transaction_publication(self):
        fixture,first,second=self.fixture();directories,files,dependencies,expected=fixture.plan()
        unchanged=fingerprint(first,allow_links=True);path=second/'package/tool.js';later=b'// Synthetic owner edit after complete plan\n';path.write_bytes(later)
        tx=ProgramTransaction(fixture.home/'later-dependency-conflict')
        with self.assertRaisesRegex(ValueError,'input changes'):
            tx.prepare(directories=directories,files=files,dependencies=dependencies,expected_before=expected)
        self.assertFalse(tx.journal.exists());self.assertEqual(path.read_bytes(),later);self.assertEqual(fingerprint(first,allow_links=True),unchanged)
        (OUTPUT/'later-root-edit.json').write_text(json.dumps({'refused_before_journal':True,'edited_root_bytes_retained':True,
            'other_root_unchanged':True},indent=2)+'\n')

    def test_link_between_selected_roots_still_refuses_per_package_boundary(self):
        fixture,first,second=self.fixture();link=first/'.bin/tool';link.unlink()
        link.symlink_to(os.path.relpath(second/'package/tool.js',link.parent))
        before=link.readlink();target=(second/'package/tool.js').read_bytes()
        with self.assertRaisesRegex(ValueError,'Dependency links must stay inside'):
            fixture.plan()
        self.assertEqual(link.readlink(),before);self.assertEqual((second/'package/tool.js').read_bytes(),target)
        self.assertFalse((fixture.generated/'config.yaml').exists())
        (OUTPUT/'cross-root-link-refusal.json').write_text(json.dumps({'both_roots_selected':True,'cross_root_link_refused':True,
            'link_and_target_retained':True,'generated_config_absent':True},indent=2)+'\n')

    def test_regular_program_target_does_not_gain_link_permission(self):
        fixture,first,second=self.fixture();target=fixture.installed/'Owned.ts';target.unlink();target.symlink_to('node_modules/package/tool.js')
        with self.assertRaisesRegex(ValueError,'regular files or directories'):
            fixture.plan()
        self.assertTrue(target.is_symlink());self.assertFalse((fixture.generated/'config.yaml').exists())
