# ABOUTME: Checks the state assertions used by paired native lifecycle controls.
# ABOUTME: Rejects matching outcomes that omit the required filesystem effect.
import unittest

from scripts.paired_lifecycle_effects import CASES, check_pair


class PairedLifecycleEffectTests(unittest.TestCase):
    def new_case(self, name, event, before, after):
        side = {'before': before, 'after': after, 'hook_exit_codes': [0],
                'event': event, 'cli_exit_code': 0, 'model_generation_requests': 0}
        return {'id': name, 'native': side, 'hermes': dict(side)}

    def test_containment_requires_a_refusal_and_unchanged_external_file(self):
        after = {'target_executable': False, 'containment_refused': True, 'target_content_preserved': True}
        case = self.new_case('healer-containment', 'SessionStart', {'target_executable': False}, after)
        self.assertEqual(check_pair(case), [])
        after['target_executable'] = True
        self.assertIn('healer-containment: containment effect is missing', check_pair(case))

    def test_kitty_requires_current_session_persistence_and_stale_title_removal(self):
        after = {'shared_environment_matches': True, 'session_environment_matches': True,
                 'stale_title_present': False}
        case = self.new_case('kitty-cli', 'SessionStart', {'environment_present': False,
                             'stale_title_present': True}, after)
        self.assertEqual(check_pair(case), [])
        after['session_environment_matches'] = False
        self.assertIn('kitty-cli: terminal persistence effect is missing', check_pair(case))

    def test_health_requires_a_real_report_and_nonblocking_warning(self):
        after = {'health_rows': 1, 'overall': 'critical', 'required_hook_missing': True,
                 'critical_count': 3, 'critical_count_matches': True, 'warning_present': True}
        case = self.new_case('memory-health-critical', 'SessionEnd', {'health_rows': 0}, after)
        self.assertEqual(check_pair(case), [])
        after['health_rows'] = 0
        self.assertIn('memory-health-critical: health effect is missing', check_pair(case))

    def test_document_inventory_requires_exact_findings_and_preserved_existing_event(self):
        after = {'inventory_events': 1, 'ok': False, 'finding_count': 2,
                 'finding_keys': ['missing_active:KNOWLEDGE', 'unknown_on_disk:SURPRISE'],
                 'unrelated_event_preserved': True}
        case = self.new_case('doc-inventory-drift', 'SessionEnd', {'inventory_events': 0}, after)
        self.assertEqual(check_pair(case), [])
        after['finding_keys'] = ['unknown_on_disk:SURPRISE']
        self.assertIn('doc-inventory-drift: inventory effect is missing', check_pair(case))

    def test_clean_inventory_requires_an_explicit_empty_finding_set(self):
        after = {'inventory_events': 1, 'ok': True, 'finding_count': 0, 'finding_keys': [],
                 'unrelated_event_preserved': True}
        case = self.new_case('doc-inventory-clean', 'SessionEnd', {'inventory_events': 0}, after)
        self.assertEqual(check_pair(case), [])
        after['inventory_events'] = 0
        self.assertIn('doc-inventory-clean: inventory effect is missing', check_pair(case))

    def test_unparseable_inventory_requires_a_report_rather_than_silence(self):
        after = {'inventory_events': 1, 'ok': False, 'finding_count': 1,
                 'finding_keys': ['inventory_unparseable:doc'], 'unrelated_event_preserved': True}
        case = self.new_case('doc-inventory-unparseable', 'SessionEnd', {'inventory_events': 0}, after)
        self.assertEqual(check_pair(case), [])
        after['ok'] = True
        self.assertIn('doc-inventory-unparseable: inventory effect is missing', check_pair(case))

    def case(self, name, before, after):
        side = {'before': before, 'after': after, 'hook_exit_codes': [0] * len(CASES[name]),
                'event': CASES[name][0][0].split('.')[0], 'cli_exit_code': 0,
                'model_generation_requests': 0}
        return {'id': name, 'native': side, 'hermes': dict(side)}

    def test_matching_no_repair_does_not_verify_healer(self):
        case = self.case('healer-executable', {'executable': False},
                         {'executable': False, 'healed_target': False, 'unrelated_preserved': True})
        self.assertIn('healer-executable: executable repair is missing', check_pair(case))
        case['native']['after'] = case['hermes']['after'] = {
            'executable': True, 'healed_target': True, 'unrelated_preserved': True}
        self.assertEqual(check_pair(case), [])

    def test_settings_case_requires_snapshot_and_preserved_direct_edit(self):
        after = {'system_value': 'system', 'user_value': 'edited',
                 'overlay_value': 'edited', 'snapshot_matches_generated': False}
        case = self.case('settings-backport', {'user_value': 'original'}, after)
        self.assertIn('settings-backport: settings effect is missing', check_pair(case))
        after['snapshot_matches_generated'] = True
        self.assertEqual(check_pair(case), [])

    def test_cleanup_requires_unrelated_session_and_work_completion(self):
        after = {'work_phase': 'complete', 'isa_phase': 'complete', 'isa_status': 'COMPLETED',
                 'current_name_present': False, 'unrelated_name_preserved': False}
        case = self.case('cleanup-work', {'work_phase': 'execute'}, after)
        self.assertIn('cleanup-work: cleanup effect is missing', check_pair(case))
        after['unrelated_name_preserved'] = True
        self.assertEqual(check_pair(case), [])

    def test_pair_rejects_unequal_state_or_failed_hook(self):
        case = self.case('update-counts-no-oauth', {'credentials_present': False},
                         {'usage_cache_present': False, 'credentials_present': False})
        case['hermes'] = {**case['hermes'], 'hook_exit_codes': [1]}
        self.assertIn('update-counts-no-oauth: hook failed', check_pair(case))
        case['hermes'] = {**case['hermes'], 'hook_exit_codes': [0],
                          'after': {'usage_cache_present': True, 'credentials_present': False}}
        self.assertIn('update-counts-no-oauth: paired state differs', check_pair(case))

    def test_matching_state_does_not_hide_a_model_generation_request(self):
        case = self.case('update-counts-no-oauth', {'credentials_present': False},
                         {'usage_cache_present': False, 'credentials_present': False})
        case['hermes'] = {**case['hermes'], 'model_generation_requests': 1}
        self.assertIn('update-counts-no-oauth: model generation was attempted', check_pair(case))

    def test_matching_state_requires_the_expected_event_and_complete_hook_count(self):
        case = self.case('update-counts-no-oauth', {'credentials_present': False},
                         {'usage_cache_present': False, 'credentials_present': False})
        case['hermes'] = {**case['hermes'], 'event': 'SessionStart', 'hook_exit_codes': [0, 0]}
        self.assertIn('update-counts-no-oauth: lifecycle event differs', check_pair(case))
        self.assertIn('update-counts-no-oauth: hook invocation count differs', check_pair(case))

    def test_matching_state_requires_a_successful_cli_exit(self):
        case = self.case('update-counts-no-oauth', {'credentials_present': False},
                         {'usage_cache_present': False, 'credentials_present': False})
        case['native'] = {**case['native'], 'cli_exit_code': 1}
        self.assertIn('update-counts-no-oauth: CLI failed', check_pair(case))
