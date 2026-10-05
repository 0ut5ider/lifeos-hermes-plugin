# ABOUTME: Checks the state assertions used by paired native lifecycle controls.
# ABOUTME: Rejects matching outcomes that omit the required filesystem effect.
import unittest
import json
from pathlib import Path
import tempfile

from scripts.paired_lifecycle_effects import CASES, check_pair, make_fixture


class PairedLifecycleEffectTests(unittest.TestCase):
    def context_case(self, name, *, loaded=False, marker=None, timing=True):
        after = {'relationship_present': loaded, 'wisdom_present': loaded,
                 'low_confidence_present': False, 'advisory_present': loaded,
                 'sources_preserved': True, 'timing_recorded': timing,
                 'marker': marker, 'ready_present': not loaded and timing}
        return self.new_case(name, 'SessionStart', {'marker_present': marker is not None and not loaded}, after)

    def test_context_requires_all_admitted_sources_and_exact_advisory_marker(self):
        case = self.context_case('context-desktop', loaded=True,
                                 marker={'keys': ['doc.integrity.memory_dir missing_active:KNOWLEDGE'],
                                         'sessions_since_emit': 0, 'last_emitted_at_present': True})
        self.assertEqual(check_pair(case), [])
        case['native']['after']['wisdom_present'] = False
        self.assertIn('context-desktop: context effect is missing', check_pair(case))

    def delivery_case(self, name, loaded):
        case = self.context_case(name, loaded=loaded,
                                 marker={'keys': ['doc.integrity.memory_dir missing_active:KNOWLEDGE'],
                                         'sessions_since_emit': 0, 'last_emitted_at_present': True} if loaded else None)
        for side in ('native', 'hermes'):
            case[side]['cli_exit_code'] = 1
            case[side]['model_generation_requests'] = 1
            case[side]['after']['model_context_contains'] = {
                'relationship': loaded, 'wisdom': loaded, 'advisory': loaded, 'low_confidence': False}
        return case

    def test_context_delivery_requires_a_real_model_request_containing_the_hook_output(self):
        case = self.delivery_case('context-delivery-desktop', True)
        self.assertEqual(check_pair(case), [])
        case['native']['after']['model_context_contains']['advisory'] = False
        self.assertIn('context-delivery-desktop: context effect is missing', check_pair(case))

    def test_remote_delivery_requires_a_model_request_without_owner_context(self):
        case = self.delivery_case('context-delivery-remote', False)
        self.assertEqual(check_pair(case), [])
        case['hermes']['after']['model_context_contains']['relationship'] = True
        self.assertIn('context-delivery-remote: context effect is missing', check_pair(case))

    def test_disabled_delivery_cannot_pass_without_reaching_the_model_boundary(self):
        case = self.delivery_case('context-delivery-disabled', False)
        self.assertEqual(check_pair(case), [])
        case['hermes']['model_generation_requests'] = 0
        self.assertIn('context-delivery-disabled: model delivery was not observed', check_pair(case))

    def response_case(self, name, loaded):
        case = self.delivery_case(name, loaded)
        for side in ('native', 'hermes'):
            case[side]['cli_exit_code'] = 0
            case[side]['model_successful_responses'] = 1
            case[side]['after']['user_response_delivered'] = True
        return case

    def test_context_response_requires_successful_generation_and_user_delivery(self):
        case = self.response_case('context-response-desktop', True)
        self.assertEqual(check_pair(case), [])
        case['native']['after']['user_response_delivered'] = False
        self.assertIn('context-response-desktop: context effect is missing', check_pair(case))

    def test_remote_response_preserves_owner_context_exclusion(self):
        case = self.response_case('context-response-remote', False)
        self.assertEqual(check_pair(case), [])
        case['hermes']['after']['model_context_contains']['wisdom'] = True
        self.assertIn('context-response-remote: context effect is missing', check_pair(case))

    def test_disabled_response_cannot_count_an_unsuccessful_model_request(self):
        case = self.response_case('context-response-disabled', False)
        self.assertEqual(check_pair(case), [])
        case['hermes']['model_successful_responses'] = 0
        self.assertIn('context-response-disabled: successful model response was not observed', check_pair(case))

    def test_response_cache_requires_the_current_delivered_answer(self):
        for name, prior in (('response-cache-empty', False), ('response-cache-replace', True)):
            with self.subTest(name=name):
                side = {'before': {'cache_present': prior, 'prior_marker_present': prior},
                    'after': {'cache_present': True, 'cache_is_nonempty': True,
                        'prior_marker_present': False, 'cache_within_limit': True,
                        'cache_matches_stop_message': True, 'stop_message_matches_user_response': True, 'user_response_delivered': True},
                    'hook_exit_codes': [0], 'event': 'Stop', 'cli_exit_code': 0,
                    'model_generation_requests': 1, 'model_successful_responses': 1}
                case = {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}
                self.assertEqual(check_pair(case), [])
                case['hermes']['after']['cache_matches_stop_message'] = False
                self.assertIn(f'{name}: response cache effect is missing', check_pair(case))

    def test_response_cache_limit_requires_a_long_answer_and_exact_prefix(self):
        side = {'before': {'cache_present': True, 'prior_marker_present': True},
            'after': {'cache_present': True, 'cache_is_nonempty': True, 'prior_marker_present': False,
                'cache_within_limit': True, 'cache_matches_stop_message': True, 'stop_message_matches_user_response': True,
                'user_response_delivered': True, 'user_response_exceeds_limit': True, 'cache_characters': 2000},
            'hook_exit_codes': [0], 'event': 'Stop', 'cli_exit_code': 0,
            'model_generation_requests': 1, 'model_successful_responses': 1}
        case = {'id': 'response-cache-limit', 'native': side, 'hermes': json.loads(json.dumps(side))}
        self.assertEqual(check_pair(case), [])
        case['hermes']['after']['user_response_exceeds_limit'] = False
        self.assertIn('response-cache-limit: response cache effect is missing', check_pair(case))

    def test_disabled_context_requires_neutral_output_and_no_marker(self):
        case = self.context_case('context-disabled')
        self.assertEqual(check_pair(case), [])
        case['native']['after']['advisory_present'] = True
        self.assertIn('context-disabled: context effect is missing', check_pair(case))

    def test_remote_context_requires_no_owner_content_or_marker(self):
        case = self.context_case('context-remote')
        self.assertEqual(check_pair(case), [])
        case['native']['after']['relationship_present'] = True
        self.assertIn('context-remote: context effect is missing', check_pair(case))

    def test_subagent_context_requires_no_context_or_session_timing(self):
        case = self.context_case('context-subagent', timing=False)
        self.assertEqual(check_pair(case), [])
        case['native']['after']['timing_recorded'] = True
        self.assertIn('context-subagent: context effect is missing', check_pair(case))

    def test_steady_advisory_requires_suppression_and_incremented_marker(self):
        case = self.context_case('context-advisory-steady',
                                 marker={'keys': ['doc.integrity.memory_dir missing_active:KNOWLEDGE'],
                                         'sessions_since_emit': 1, 'last_emitted_at_present': True})
        self.assertEqual(check_pair(case), [])
        case['native']['after']['marker']['sessions_since_emit'] = 0
        self.assertIn('context-advisory-steady: context effect is missing', check_pair(case))

    def test_cleared_advisory_requires_empty_marker_and_no_old_warning(self):
        case = self.context_case('context-advisory-cleared',
                                 marker={'keys': [], 'sessions_since_emit': 0, 'last_emitted_at_present': True})
        self.assertEqual(check_pair(case), [])
        case['native']['after']['marker']['keys'] = ['doc.integrity.memory_dir missing_active:KNOWLEDGE']
        self.assertIn('context-advisory-cleared: context effect is missing', check_pair(case))

    def test_remote_terminal_requires_preserved_existing_state(self):
        case = self.new_case('kitty-remote', 'SessionStart', {'stale_title_present': True},
                             {'shared_environment_present': False, 'session_environment_present': False,
                              'stale_title_preserved': True})
        self.assertEqual(check_pair(case), [])
        case['native']['after']['stale_title_preserved'] = False
        self.assertIn('kitty-remote: terminal gate effect is missing', check_pair(case))

    def test_subagent_terminal_requires_no_session_environment_write(self):
        case = self.new_case('kitty-subagent', 'SessionStart', {'stale_title_present': True},
                             {'shared_environment_present': False, 'session_environment_present': False,
                              'stale_title_preserved': True})
        self.assertEqual(check_pair(case), [])
        case['native']['after']['session_environment_present'] = True
        self.assertIn('kitty-subagent: terminal gate effect is missing', check_pair(case))

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


class PairedLifecycleFixtureTests(unittest.TestCase):
    def fixture(self, name):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        source = base / 'source'
        for _, relative in CASES[name]:
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Fixture source identity\n')
        if name.startswith('context-'):
            for relative in ('hooks/lib/learning-readback.ts', 'hooks/lib/advisory-readback.ts',
                             'hooks/lib/notifications.ts'):
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('Fixture source identity\n')
        home = base / 'home'
        definitions = make_fixture(home, name, source, base / 'trace.py')
        return home, json.loads((home / '.claude/settings.json').read_text()), definitions

    def test_existing_startup_and_end_fixtures_preserve_their_selected_event(self):
        for name, event in (('context-desktop', 'SessionStart'), ('update-counts-no-oauth', 'SessionEnd')):
            with self.subTest(name=name):
                home, settings, definitions = self.fixture(name)
                self.assertEqual(set(settings['hooks']), {'SessionStart', 'UserPromptSubmit', 'SessionEnd'})
                self.assertEqual(settings['hooks'][event][-1]['hooks'][0]['command'], definitions[0]['command'])
                self.assertTrue((home / 'before-state.json').is_file())

    def test_response_cache_fixture_uses_stop_and_preserves_the_selected_prior_state(self):
        for name, prior in (('response-cache-empty', False), ('response-cache-replace', True)):
            with self.subTest(name=name):
                home, settings, definitions = self.fixture(name)
                self.assertEqual(settings['hooks']['Stop'][0]['hooks'][0]['command'], definitions[0]['command'])
                self.assertEqual(len(settings['hooks']['SessionEnd']), 1)
                self.assertEqual(json.loads((home / 'before-state.json').read_text()),
                    {'cache_present': prior, 'prior_marker_present': prior})
