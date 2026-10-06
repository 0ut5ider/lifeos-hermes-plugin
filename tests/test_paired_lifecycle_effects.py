# ABOUTME: Checks the state assertions used by paired native lifecycle controls.
# ABOUTME: Rejects matching outcomes that omit the required filesystem effect.
import unittest
import json
from pathlib import Path
import tempfile
import time

from scripts.paired_lifecycle_effects import CASES, check_pair, make_fixture, state_snapshot


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
        if name.startswith('format-contract-'):
            path = source / 'hooks/lib/banned-vocab.ts'
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

    def test_feedback_fixture_preserves_a_prior_rating_and_binds_to_prompt_submission(self):
        home, settings, definitions = self.fixture('feedback-rating')
        self.assertEqual(settings['hooks']['UserPromptSubmit'][-1]['hooks'][0]['command'],
                         definitions[0]['command'])
        self.assertEqual(json.loads((home / 'before-state.json').read_text()),
                         {'rating_count': 1, 'learning_count': 0, 'cache_present': True})
        self.assertEqual(state_snapshot(home, 'feedback-rating', 'current-session', after=True),
                         {'unrelated_rating_preserved': True, 'cache_preserved': True,
                          'captured_ratings': [], 'learning_count': 0})

    def test_format_fixture_seeds_recent_and_stale_caches_without_changing_their_bytes(self):
        for name, stale in [('format-contract-clean', False), ('format-contract-stale', True)]:
            with self.subTest(name=name):
                home, settings, definitions = self.fixture(name)
                self.assertEqual(settings['hooks']['UserPromptSubmit'][-1]['hooks'][0]['command'], definitions[0]['command'])
                before = json.loads((home / 'before-state.json').read_text())
                self.assertEqual(before['state']['turn_count'], 6)
                self.assertEqual(before['state']['last_fired_turn'], 6)
                cache = home / '.claude/LIFEOS/MEMORY/STATE/last-response.txt'
                self.assertEqual(time.time() - cache.stat().st_mtime > 1800, stale)

    def test_async_feedback_fixture_uses_the_pinned_execution_setting(self):
        home, settings, definitions = self.fixture('feedback-async-rating')
        hook = settings['hooks']['UserPromptSubmit'][-1]['hooks'][0]
        self.assertTrue(hook['async'])
        self.assertEqual(hook['timeout'], 20)
        self.assertEqual(hook['command'], definitions[0]['command'])
        self.assertEqual(json.loads((home / 'before-state.json').read_text())['rating_count'], 1)


class PairedFeedbackEffectTests(unittest.TestCase):
    def case(self, name, rating=None, learning=False):
        after = {'unrelated_rating_preserved': True, 'cache_preserved': True,
                 'captured_ratings': [rating] if rating else [], 'learning_count': int(learning),
                 'user_response_delivered': True}
        if learning:
            after['learning_checks'] = {'rating_matches': True, 'source_matches': True,
                'feedback_matches': True, 'context_matches': True, 'principal_matches': True}
        side = {'before': {'rating_count': 1, 'learning_count': 0, 'cache_present': True},
                'after': after, 'hook_exit_codes': [0], 'event': 'UserPromptSubmit',
                'cli_exit_code': 0, 'model_generation_requests': 1, 'model_successful_responses': 1}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def rating(self, value, **fields):
        return {'rating': value, 'source': 'explicit', 'timestamp_valid': True,
                'session_matches': True, 'response_preview_matches_cache': True, **fields}

    def test_explicit_and_bare_ratings_require_current_session_context(self):
        for name, rating in [('feedback-rating', self.rating(8, comment='great result')),
                             ('feedback-bare-rating', self.rating(10))]:
            with self.subTest(name=name):
                case = self.case(name, rating)
                self.assertEqual(check_pair(case), [])
                case['hermes']['after']['captured_ratings'][0]['session_matches'] = False
                self.assertIn(f'{name}: feedback effect is missing', check_pair(case))

    def test_praise_requires_the_native_summary_and_confidence(self):
        case = self.case('feedback-praise', {**self.rating(8), 'source': 'implicit',
            'sentiment_summary': 'Direct praise: "great job"', 'confidence': 0.95})
        self.assertEqual(check_pair(case), [])
        case['native']['after']['captured_ratings'][0]['confidence'] = 1
        self.assertIn('feedback-praise: feedback effect is missing', check_pair(case))

    def test_numeric_work_text_cannot_create_a_rating_or_erase_prior_ratings(self):
        case = self.case('feedback-neutral')
        self.assertEqual(check_pair(case), [])
        case['hermes']['after']['unrelated_rating_preserved'] = False
        self.assertIn('feedback-neutral: feedback effect is missing', check_pair(case))
        case = self.case('feedback-neutral', self.rating(2))
        self.assertIn('feedback-neutral: feedback effect is missing', check_pair(case))

    def test_low_rating_requires_learning_with_the_cached_response_and_principal(self):
        case = self.case('feedback-low-rating', self.rating(4, comment='needs clearer details'), learning=True)
        self.assertEqual(check_pair(case), [])
        case['native']['after']['learning_checks']['context_matches'] = False
        self.assertIn('feedback-low-rating: feedback effect is missing', check_pair(case))

    def test_feedback_requires_a_successful_complete_client_response(self):
        case = self.case('feedback-neutral')
        self.assertEqual(check_pair(case), [])
        case['hermes']['model_successful_responses'] = 0
        self.assertIn('feedback-neutral: successful model response was not observed', check_pair(case))
        case = self.case('feedback-neutral')
        case['native']['after']['user_response_delivered'] = False
        self.assertIn('feedback-neutral: feedback effect is missing', check_pair(case))

    def test_asynchronous_feedback_requires_the_same_complete_effects(self):
        examples = [('rating', self.rating(8, comment='great result'), False),
                    ('bare-rating', self.rating(10), False),
                    ('praise', {**self.rating(8), 'source': 'implicit',
                       'sentiment_summary': 'Direct praise: "great job"', 'confidence': 0.95}, False),
                    ('neutral', None, False),
                    ('low-rating', self.rating(4, comment='needs clearer details'), True)]
        for suffix, rating, learning in examples:
            with self.subTest(suffix=suffix):
                name = 'feedback-async-' + suffix
                case = self.case(name, rating, learning)
                self.assertEqual(check_pair(case), [])
                case['hermes']['after']['cache_preserved'] = False
                self.assertIn(f'{name}: feedback effect is missing', check_pair(case))


class PairedFormatContractTests(unittest.TestCase):
    def case(self, name, *, previous='', state_present=True):
        budget = 'depth requested, line cap lifted' if name == 'format-contract-depth' else 'max 15 prose lines'
        contract = ('FORMAT CONTRACT (check before writing, not after): ' + budget +
                    '; banner first, 🗣️ closer last, max 2 em-dashes.' + previous)
        before = {'state': {'last_fired_turn': 6, 'turn_count': 6, 'last_text': 'PAIR_PRIOR_CONTRACT',
                           'schema_version': 1} if state_present else None,
                  'cache_present': name != 'format-contract-empty'}
        after = {'state': {'last_fired_turn': 7 if state_present else 1, 'turn_count': 7 if state_present else 1,
                          'last_text': contract, 'schema_version': 1},
                 'cache_preserved': True, 'hook_context': contract,
                 'model_contract_present': True, 'user_response_delivered': True}
        side = {'before': before, 'after': after, 'hook_exit_codes': [0], 'event': 'UserPromptSubmit',
                'cli_exit_code': 0, 'model_generation_requests': 1, 'model_successful_responses': 1}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_first_prompt_initializes_state_and_delivers_the_contract_to_the_model(self):
        case = self.case('format-contract-empty', state_present=False)
        self.assertEqual(check_pair(case), [])
        case['hermes']['after']['model_contract_present'] = False
        self.assertIn('format-contract-empty: format contract effect is missing', check_pair(case))

    def test_clean_response_still_emits_on_the_next_turn_and_advances_state(self):
        case = self.case('format-contract-clean', previous=' Last response was clean (3 lines).')
        self.assertEqual(check_pair(case), [])
        case['native']['after']['state']['last_fired_turn'] = 6
        self.assertIn('format-contract-clean: format contract effect is missing', check_pair(case))

    def test_depth_lifts_only_the_line_limit_and_preserves_measured_violations(self):
        previous = " Last response broke: no banner, no closer, 3 em-dashes, banned word 'delve'."
        case = self.case('format-contract-depth', previous=previous)
        self.assertEqual(check_pair(case), [])
        case['hermes']['after']['hook_context'] += ' 17 lines (cap 15).'
        self.assertIn('format-contract-depth: format contract effect is missing', check_pair(case))

    def test_default_budget_reports_all_seeded_violations(self):
        case = self.case('format-contract-violations',
            previous=" Last response broke: no banner, no closer, 3 em-dashes, banned word 'delve', 17 lines (cap 15).")
        self.assertEqual(check_pair(case), [])
        case['native']['after']['cache_preserved'] = False
        self.assertIn('format-contract-violations: format contract effect is missing', check_pair(case))

    def test_stale_cache_cannot_contribute_previous_session_violations(self):
        case = self.case('format-contract-stale')
        self.assertEqual(check_pair(case), [])
        case['native']['after']['hook_context'] += ' Last response broke: no banner.'
        self.assertIn('format-contract-stale: format contract effect is missing', check_pair(case))


class PairedTimeContextTests(unittest.TestCase):
    def case(self, name):
        invalid = name == 'time-context-invalid-zone'
        asynchronous = name == 'time-context-async-utc'
        zone = 'PAIR_INVALID_ZONE' if invalid else 'America/Toronto' if name.endswith('toronto') else 'UTC'
        side = {'before': {'configured_timezone': zone, 'asynchronous': asynchronous},
                'after': {'clock_emitted': not invalid, 'clock_valid': not invalid,
                    'clock_is_current': not invalid, 'settings_preserved': True,
                    'clock_context_in_model': not invalid and not asynchronous,
                    'user_response_delivered': True},
                'hook_exit_codes': [0], 'event': 'UserPromptSubmit', 'cli_exit_code': 0,
                'model_generation_requests': 1, 'model_successful_responses': 1}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_synchronous_live_clock_requires_current_timezone_value_and_model_delivery(self):
        for name in ('time-context-sync-utc', 'time-context-sync-toronto'):
            with self.subTest(name=name):
                case = self.case(name)
                self.assertEqual(check_pair(case), [])
                case['native']['after']['clock_is_current'] = False
                self.assertIn(f'{name}: time context effect is missing', check_pair(case))

    def test_async_first_turn_cannot_claim_delivery_without_a_clock_in_the_request(self):
        case = self.case('time-context-async-utc')
        self.assertEqual(check_pair(case), [])
        case['hermes']['after']['clock_context_in_model'] = True
        self.assertIn('time-context-async-utc: time context effect is missing', check_pair(case))

    def test_invalid_timezone_fails_open_without_clock_or_configuration_changes(self):
        case = self.case('time-context-invalid-zone')
        self.assertEqual(check_pair(case), [])
        case['native']['after']['settings_preserved'] = False
        self.assertIn('time-context-invalid-zone: time context effect is missing', check_pair(case))


class PairedVersionDriftTests(unittest.TestCase):
    SHAPES = {'version-drift-count': (10, True), 'version-drift-aged': (1, True),
              'version-drift-below': (1, False), 'version-drift-bump': (10, False),
              'version-drift-recent': (10, False), 'version-drift-untagged': (10, False),
              'version-drift-async-count': (10, True)}

    def line(self, name):
        age = ' (tag 72h old)' if name == 'version-drift-aged' else ''
        dash = chr(0x2014)
        return (f'⏫ VERSION-DRIFT: {self.SHAPES[name][0]} core file(s) ahead of v1.0.0{age}, no bump in flight {dash} '
                'run the VersionBump workflow (/vb: classify → bump → ship) before this ages further, '
                'or defer explicitly to the principal.')

    def case(self, name):
        changed, nag = self.SHAPES[name]
        recent = name == 'version-drift-recent'
        asynchronous = name == 'version-drift-async-count'
        state = {'count': changed, 'tag': 'v1.0.0', 'timestamp_current': True} if nag else None
        if recent:
            state = {'count': 3, 'tag': 'v0.9.0', 'timestamp_current': False}
        side = {'before': {'changed_core_files': changed,
                           'tag': None if name == 'version-drift-untagged' else 'v1.0.0',
                           'tag_age_hours': 72 if name == 'version-drift-aged' else 0,
                           'version': '1.0.1' if name == 'version-drift-bump' else '1.0.0',
                           'prior_nag_present': recent, 'asynchronous': asynchronous},
                'after': {'hook_context': self.line(name) if nag else None, 'state': state,
                          'worktree_preserved': True, 'model_nag_present': nag and not asynchronous,
                          'user_response_delivered': True},
                'hook_exit_codes': [0], 'event': 'UserPromptSubmit', 'cli_exit_code': 0,
                'model_generation_requests': 1, 'model_successful_responses': 1}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_every_selected_branch_accepts_only_its_required_effect(self):
        for name in self.SHAPES:
            with self.subTest(name=name):
                self.assertEqual(check_pair(self.case(name)), [])

    def test_threshold_nag_requires_the_exact_line_state_and_model_delivery(self):
        for key, value in (('model_nag_present', False), ('state', None), ('hook_context', None)):
            with self.subTest(key=key):
                case = self.case('version-drift-count')
                case['native']['after'][key] = case['hermes']['after'][key] = value
                self.assertIn('version-drift-count: version drift effect is missing', check_pair(case))

    def test_aged_tag_requires_the_reported_tag_age(self):
        case = self.case('version-drift-aged')
        for side in ('native', 'hermes'):
            case[side]['after']['hook_context'] = case[side]['after']['hook_context'].replace(' (tag 72h old)', '')
        self.assertIn('version-drift-aged: version drift effect is missing', check_pair(case))

    def test_silent_branches_reject_a_nag_or_a_replaced_prior_state(self):
        for name in ('version-drift-below', 'version-drift-bump', 'version-drift-untagged', 'version-drift-recent'):
            with self.subTest(name=name):
                case = self.case(name)
                for side in ('native', 'hermes'):
                    case[side]['after']['state'] = {'count': 10, 'tag': 'v1.0.0', 'timestamp_current': True}
                self.assertIn(f'{name}: version drift effect is missing', check_pair(case))

    def test_async_first_turn_cannot_claim_model_delivery(self):
        case = self.case('version-drift-async-count')
        for side in ('native', 'hermes'):
            case[side]['after']['model_nag_present'] = True
        self.assertIn('version-drift-async-count: version drift effect is missing', check_pair(case))


class PairedVersionDriftFixtureTests(unittest.TestCase):
    def fixture(self, name):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        source = base / 'source'
        (source / 'hooks').mkdir(parents=True)
        (source / 'hooks/VersionDrift.hook.ts').write_text('Fixture source identity\n')
        home = base / 'home'
        make_fixture(home, name, source, base / 'trace.py')
        return home, json.loads((home / '.claude/settings.json').read_text())

    def test_fixture_measures_the_seeded_repository_before_the_client_runs(self):
        expected = {'version-drift-count': (10, 'v1.0.0', 0, '1.0.0', False),
                    'version-drift-aged': (1, 'v1.0.0', 72, '1.0.0', False),
                    'version-drift-below': (1, 'v1.0.0', 0, '1.0.0', False),
                    'version-drift-bump': (10, 'v1.0.0', 0, '1.0.1', False),
                    'version-drift-recent': (10, 'v1.0.0', 0, '1.0.0', True),
                    'version-drift-untagged': (10, None, 0, '1.0.0', False)}
        for name, (changed, tag, age, version, prior) in expected.items():
            with self.subTest(name=name):
                home, _ = self.fixture(name)
                self.assertEqual(json.loads((home / 'before-state.json').read_text()), {
                    'changed_core_files': changed, 'tag': tag, 'tag_age_hours': age, 'version': version,
                    'prior_nag_present': prior, 'asynchronous': False})

    def test_async_fixture_uses_the_pinned_execution_setting(self):
        home, settings = self.fixture('version-drift-async-count')
        hook = settings['hooks']['UserPromptSubmit'][-1]['hooks'][0]
        self.assertEqual((hook['async'], hook['timeout']), (True, 10))
        self.assertTrue(json.loads((home / 'before-state.json').read_text())['asynchronous'])

    def test_after_state_reports_a_preserved_worktree_and_an_untouched_prior_nag(self):
        home, _ = self.fixture('version-drift-recent')
        (home / 'hooks.jsonl').write_text(json.dumps({'stdout': ''}) + '\n')
        now = time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime())
        (home / 'clock-bounds.json').write_text(json.dumps({'started_at': now, 'finished_at': now}))
        self.assertEqual(state_snapshot(home, 'version-drift-recent', 'current-session', after=True), {
            'hook_context': None, 'state': {'count': 3, 'tag': 'v0.9.0', 'timestamp_current': False},
            'worktree_preserved': True})
        (home / '.claude/hooks/core-0.txt').write_text('changed by a client\n')
        self.assertFalse(state_snapshot(home, 'version-drift-recent', 'current-session', after=True)['worktree_preserved'])


class PairedISARenderTests(unittest.TestCase):
    # case: seeded phase, iteration, prior page, expected log entry, expected page
    SHAPES = {'isa-render-absent': (None, None, False, None, 'absent'),
              'isa-render-first-authoring': ('execute', 1, False, ('skipped', 'paired-work/ISA.md:pre-completion'), 'absent'),
              'isa-render-missing': (None, None, False, ('skipped', 'absent-work/ISA.md:missing'), 'absent'),
              'isa-render-complete': ('complete', 1, False, ('rendered', 'paired-work/ISA.md'), 'rendered'),
              'isa-render-resumed': ('execute', 2, False, ('rendered', 'paired-work/ISA.md'), 'rendered'),
              'isa-render-existing-page': ('execute', 1, True, ('rendered', 'paired-work/ISA.md'), 'rendered')}

    def case(self, name):
        phase, iteration, prior, entry, page = self.SHAPES[name]
        log = []
        if entry:
            log = [{'session_matches': True, 'rendered': [], 'skipped': [], entry[0]: [entry[1]]}]
        side = {'before': {'state_present': name != 'isa-render-absent', 'isa_phase': phase,
                           'isa_iteration': iteration, 'page': 'prior' if prior else 'absent'},
                'after': {'state_present': False, 'log': log, 'page': page,
                          'isa_preserved': True, 'hook_output': {'continue': True},
                          'user_response_delivered': True},
                'hook_exit_codes': [0], 'event': 'Stop', 'cli_exit_code': 0,
                'model_generation_requests': 1, 'model_successful_responses': 1}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_every_selected_branch_accepts_only_its_required_effect(self):
        for name in self.SHAPES:
            with self.subTest(name=name):
                self.assertEqual(check_pair(self.case(name)), [])

    def test_completed_work_requires_a_rendered_page_and_cleared_state(self):
        for key, value in (('page', 'absent'), ('state_present', True), ('log', [])):
            with self.subTest(key=key):
                case = self.case('isa-render-complete')
                case['native']['after'][key] = case['hermes']['after'][key] = value
                self.assertIn('isa-render-complete: render effect is missing', check_pair(case))

    def test_first_authoring_rejects_a_rendered_page(self):
        case = self.case('isa-render-first-authoring')
        for side in ('native', 'hermes'):
            case[side]['after']['page'] = 'rendered'
        self.assertIn('isa-render-first-authoring: render effect is missing', check_pair(case))

    def test_existing_page_requires_replacement_of_the_prior_content(self):
        case = self.case('isa-render-existing-page')
        for side in ('native', 'hermes'):
            case[side]['after']['page'] = 'prior'
        self.assertIn('isa-render-existing-page: render effect is missing', check_pair(case))


class PairedISARenderFixtureTests(unittest.TestCase):
    def fixture(self, name):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        source = base / 'source'
        (source / 'hooks').mkdir(parents=True)
        (source / 'LIFEOS/TOOLS').mkdir(parents=True)
        (source / 'hooks/ISARenderOnStop.hook.ts').write_text('Fixture source identity\n')
        (source / 'LIFEOS/TOOLS/ISARender.ts').write_text('Fixture source identity\n')
        home = base / 'home'
        make_fixture(home, name, source, base / 'trace.py')
        return home, json.loads((home / '.claude/settings.json').read_text())

    def test_fixture_binds_the_hook_to_stop_and_links_the_native_renderer(self):
        home, settings = self.fixture('isa-render-complete')
        self.assertIn('Stop.1.4', settings['hooks']['Stop'][0]['hooks'][0]['command'])
        self.assertTrue((home / '.claude/LIFEOS/TOOLS').is_symlink())

    def test_session_start_seeds_the_edit_state_for_the_real_session(self):
        from scripts.paired_lifecycle_effects import seed_render_state
        for name, expected in (('isa-render-absent', {'state_present': False, 'isa_phase': None,
                                                      'isa_iteration': None, 'page': 'absent'}),
                               ('isa-render-existing-page', {'state_present': True, 'isa_phase': 'execute',
                                                             'isa_iteration': 1, 'page': 'prior'}),
                               ('isa-render-resumed', {'state_present': True, 'isa_phase': 'execute',
                                                       'isa_iteration': 2, 'page': 'absent'})):
            with self.subTest(name=name):
                home, _ = self.fixture(name)
                seed_render_state(home, name, 'current-session')
                self.assertEqual(state_snapshot(home, name, 'current-session'), expected)

    def test_after_state_normalizes_paths_and_classifies_the_page(self):
        from scripts.paired_lifecycle_effects import seed_render_state
        home, _ = self.fixture('isa-render-existing-page')
        seed_render_state(home, 'isa-render-existing-page', 'current-session')
        (home / 'fixture-files-before.json').write_text(json.dumps(
            __import__('scripts.paired_lifecycle_effects', fromlist=['fixture_files']).fixture_files(home)))
        work = home / '.claude/LIFEOS/MEMORY/WORK/paired-work'
        log = home / '.claude/LIFEOS/MEMORY/OBSERVABILITY/isa-render.jsonl'
        log.parent.mkdir(parents=True)
        log.write_text(json.dumps({'ts': 'now', 'session_id': 'current-session',
                                   'rendered': [str(work / 'ISA.md')], 'skipped': []}) + '\n')
        (home / 'hooks.jsonl').write_text(json.dumps({'stdout': '{"continue":true}\n'}) + '\n')
        self.assertEqual(state_snapshot(home, 'isa-render-existing-page', 'current-session', after=True), {
            'state_present': True, 'page': 'prior', 'isa_preserved': True, 'hook_output': {'continue': True},
            'log': [{'session_matches': True, 'rendered': ['paired-work/ISA.md'], 'skipped': []}]})


class PairedAtlasHintTests(unittest.TestCase):
    SOURCES = {'atlas-bash-systemd': ['systemd'], 'atlas-bash-plain': [],
               'atlas-bash-multiple': ['github', 'launchd']}

    def case(self, name):
        side = {'before': {'event_rows': 1},
                'after': {'prior_event_preserved': True,
                          'hints': [{'source': source, 'tool': 'Bash', 'timestamp_current': True}
                                    for source in self.SOURCES[name]],
                          'tool_name': 'Bash', 'command_matches': True, 'user_response_delivered': True},
                'hook_exit_codes': [0], 'event': 'PostToolUse', 'cli_exit_code': 0,
                'model_generation_requests': 2, 'model_successful_responses': 2}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_every_selected_command_accepts_only_its_required_hints(self):
        for name in self.SOURCES:
            with self.subTest(name=name):
                self.assertEqual(check_pair(self.case(name)), [])

    def test_hint_requires_the_exact_executed_command_and_a_preserved_prior_row(self):
        for key in ('command_matches', 'prior_event_preserved'):
            with self.subTest(key=key):
                case = self.case('atlas-bash-systemd')
                case['native']['after'][key] = case['hermes']['after'][key] = False
                self.assertIn('atlas-bash-systemd: mutation hint effect is missing', check_pair(case))

    def test_plain_command_rejects_any_hint(self):
        case = self.case('atlas-bash-plain')
        for side in ('native', 'hermes'):
            case[side]['after']['hints'] = [{'source': 'systemd', 'tool': 'Bash', 'timestamp_current': True}]
        self.assertIn('atlas-bash-plain: mutation hint effect is missing', check_pair(case))

    def test_tool_case_requires_the_tool_request_and_the_final_response(self):
        case = self.case('atlas-bash-multiple')
        for side in ('native', 'hermes'):
            case[side]['model_generation_requests'] = case[side]['model_successful_responses'] = 1
        self.assertIn('atlas-bash-multiple: tool turn was not completed', check_pair(case))

    def test_fixture_binds_the_hook_to_the_bash_matcher_and_seeds_a_prior_row(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        source = base / 'source'
        (source / 'hooks').mkdir(parents=True)
        (source / 'hooks/AtlasEventCapture.hook.ts').write_text('Fixture source identity\n')
        home = base / 'home'
        make_fixture(home, 'atlas-bash-systemd', source, base / 'trace.py')
        settings = json.loads((home / '.claude/settings.json').read_text())
        group = settings['hooks']['PostToolUse'][0]
        self.assertEqual(group['matcher'], 'Bash')
        self.assertIn('PostToolUse.13.1', group['hooks'][0]['command'])
        self.assertEqual(json.loads((home / 'before-state.json').read_text()), {'event_rows': 1})


class PairedPreToolGuardTests(unittest.TestCase):
    def case(self, name):
        blocked = name == 'guard-bash-plutil-block'
        side = {'before': {'project_files': []},
                'after': {'project_files': [], 'tool_name': 'Bash', 'command_matches': True,
                          'block_message_emitted': blocked, 'model_received_block': blocked,
                          'tool_output_in_model': not blocked, 'user_response_delivered': True},
                'hook_exit_codes': [2 if blocked else 0], 'event': 'PreToolUse', 'cli_exit_code': 0,
                'model_generation_requests': 2, 'model_successful_responses': 2}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_every_selected_command_accepts_only_its_required_decision(self):
        for name in ('guard-bash-plutil-block', 'guard-bash-plutil-safe', 'guard-bash-plain'):
            with self.subTest(name=name):
                self.assertEqual(check_pair(self.case(name)), [])

    def test_block_requires_exit_two_the_message_and_no_execution(self):
        for key, value in (('tool_output_in_model', True), ('model_received_block', False),
                           ('block_message_emitted', False)):
            with self.subTest(key=key):
                case = self.case('guard-bash-plutil-block')
                case['native']['after'][key] = case['hermes']['after'][key] = value
                self.assertIn('guard-bash-plutil-block: guard decision is missing', check_pair(case))
        case = self.case('guard-bash-plutil-block')
        case['native']['hook_exit_codes'] = case['hermes']['hook_exit_codes'] = [0]
        self.assertIn('guard-bash-plutil-block: hook exit code differs', check_pair(case))

    def test_safe_form_rejects_a_block_and_requires_execution(self):
        case = self.case('guard-bash-plutil-safe')
        case['native']['hook_exit_codes'] = case['hermes']['hook_exit_codes'] = [2]
        self.assertIn('guard-bash-plutil-safe: hook failed', check_pair(case))
        case = self.case('guard-bash-plutil-safe')
        case['native']['after']['tool_output_in_model'] = case['hermes']['after']['tool_output_in_model'] = False
        self.assertIn('guard-bash-plutil-safe: guard decision is missing', check_pair(case))

    def test_fixture_uses_the_pinned_matcher(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        source = base / 'source'
        (source / 'hooks').mkdir(parents=True)
        (source / 'hooks/PreToolGuard.hook.ts').write_text('Fixture source identity\n')
        home = base / 'home'
        make_fixture(home, 'guard-bash-plain', source, base / 'trace.py')
        group = json.loads((home / '.claude/settings.json').read_text())['hooks']['PreToolUse'][0]
        self.assertEqual(group['matcher'], 'Bash|Write|Edit|MultiEdit')
        self.assertIn('PreToolUse.5.1', group['hooks'][0]['command'])


class PairedRunStorageTests(unittest.TestCase):
    def test_run_refuses_to_start_without_the_required_free_space(self):
        from scripts.paired_lifecycle_effects import require_free_space
        with tempfile.TemporaryDirectory() as directory:
            require_free_space(Path(directory), 1)
            with self.assertRaisesRegex(RuntimeError, 'free space'):
                require_free_space(Path(directory), 1 << 60)

    def test_hermes_tool_cache_is_removed_and_evidence_files_remain(self):
        from scripts.paired_lifecycle_effects import remove_tool_cache
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.hermes/tools/fetch-fixture').mkdir(parents=True)
            (home / '.hermes/tools/fetch-fixture/binary').write_text('regenerable\n')
            (home / '.hermes/state.db').write_text('retained\n')
            remove_tool_cache(home)
            self.assertFalse((home / '.hermes/tools').exists())
            self.assertEqual((home / '.hermes/state.db').read_text(), 'retained\n')
            remove_tool_cache(home)


class PairedToolLogTests(unittest.TestCase):
    def case(self, name):
        failure, repeat = name == 'tool-log-failure', name == 'tool-log-repeat'
        event = 'PostToolUseFailure' if failure else 'PostToolUse'
        identifiers = {'tool-log-success': ['PostToolUse.11.1', 'PostToolUse.12.2'],
                       'tool-log-repeat': ['PostToolUse.12.2'],
                       'tool-log-failure': ['PostToolUseFailure.1.1', 'PostToolUseFailure.3.1']}[name]
        row = {'event': 'tool_failure' if failure else 'tool_use', 'tool_name': 'Bash',
               'session_matches': True, 'preview_command_matches': True}
        after = {'activity': [{**row, 'ground_truth_command_matches': True, 'output_recorded': True}]
                 if name == 'tool-log-success' else [],
                 'activity_rows_match_calls': True,
                 'failures': [{**row, 'error_text_matches': True}] if failure else [],
                 'loop': {'session_matches': True, 'seq_matches_calls': True, 'last_alert': 3 if repeat else 0,
                          'alert_count': int(repeat), 'tools': ['Bash'], 'failed': [failure],
                          'one_signature': True, 'state_count': 1},
                 'alert_positions': {identifier: [3] if repeat else [] for identifier in identifiers},
                 'other_context': False, 'at_least_required_calls': True, 'events': [event],
                 'tool_names': ['Bash'], 'commands_match': True, 'model_received_loop_alert': repeat,
                 'tool_output_in_model': not failure, 'user_response_delivered': True}
        calls = 3 if repeat else 1
        side = {'before': {'activity_rows': 0, 'failure_rows': 0, 'loop_states': 0}, 'after': after,
                'hook_exit_codes': [0] * len(identifiers) * calls, 'event': event, 'cli_exit_code': 0,
                'model_generation_requests': calls + 1, 'model_successful_responses': calls + 1}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def change(self, case, key, value):
        for side in ('native', 'hermes'):
            case[side]['after'][key] = value
        return check_pair(case)

    def test_every_selected_case_accepts_only_its_required_effect(self):
        for name in ('tool-log-success', 'tool-log-repeat', 'tool-log-failure'):
            with self.subTest(name=name):
                self.assertEqual(check_pair(self.case(name)), [])

    def test_success_requires_the_activity_row_and_an_unalerted_loop_state(self):
        self.assertIn('tool-log-success: tool log effect is missing',
                      self.change(self.case('tool-log-success'), 'activity', []))
        self.assertIn('tool-log-success: tool log effect is missing',
                      self.change(self.case('tool-log-success'), 'loop', None))

    def test_repeat_requires_the_alert_on_the_third_call_and_model_delivery(self):
        self.assertIn('tool-log-repeat: tool log effect is missing',
                      self.change(self.case('tool-log-repeat'), 'alert_positions', {'PostToolUse.12.2': [2]}))
        self.assertIn('tool-log-repeat: tool log effect is missing',
                      self.change(self.case('tool-log-repeat'), 'model_received_loop_alert', False))

    def test_repeat_accepts_additional_calls_after_the_third(self):
        case = self.case('tool-log-repeat')
        for side in ('native', 'hermes'):
            case[side]['hook_exit_codes'] = [0] * 4
            case[side]['model_generation_requests'] = case[side]['model_successful_responses'] = 5
        self.assertEqual(check_pair(case), [])
        case['native']['hook_exit_codes'] = [0] * 2
        self.assertIn('tool-log-repeat: hook invocation count differs', check_pair(case))

    def test_failure_requires_the_failure_event_row_and_failed_loop_entry(self):
        self.assertIn('tool-log-failure: tool log effect is missing',
                      self.change(self.case('tool-log-failure'), 'failures', []))
        case = self.case('tool-log-failure')
        for side in ('native', 'hermes'):
            case[side]['after']['loop']['failed'] = [False]
        self.assertIn('tool-log-failure: tool log effect is missing', check_pair(case))

    def test_failure_requires_the_complete_native_error_text(self):
        case = self.case('tool-log-failure')
        for side in ('native', 'hermes'):
            case[side]['after']['failures'][0]['error_text_matches'] = False
        self.assertIn('tool-log-failure: tool log effect is missing', check_pair(case))

    def test_success_requires_the_recorded_command_output(self):
        case = self.case('tool-log-success')
        for side in ('native', 'hermes'):
            case[side]['after']['activity'][0]['output_recorded'] = False
        self.assertIn('tool-log-success: tool log effect is missing', check_pair(case))

    def test_success_fixture_keeps_the_pinned_asynchronous_logger(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        source = base / 'source'
        (source / 'hooks').mkdir(parents=True)
        for name in ('EventLogger', 'LoopDetector'):
            (source / f'hooks/{name}.hook.ts').write_text('Fixture source identity\n')
        home = base / 'home'
        make_fixture(home, 'tool-log-success', source, base / 'trace.py')
        group = json.loads((home / '.claude/settings.json').read_text())['hooks']['PostToolUse'][0]
        self.assertNotIn('matcher', group)
        self.assertEqual([(hook.get('async', False), hook['timeout']) for hook in group['hooks']],
                         [(True, 5), (False, 30)])


class PairedFileHintTests(unittest.TestCase):
    SHAPES = {'file-hint-write-projects': ('Write', ['projects']), 'file-hint-write-plain': ('Write', []),
              'file-hint-edit-gear': ('Edit', ['gear']), 'file-hint-sentinel-debounced': ('Write', []),
              'file-hint-sentinel-no-runner': ('Write', [])}
    SEEDED = {'file-hint-sentinel-debounced'}

    def case(self, name):
        tool, sources = self.SHAPES[name]
        event = 'PostToolUse'
        side = {'before': {'atlas_rows': 1, 'target_present': tool == 'Edit',
                           'evaluation_state_present': name in self.SEEDED},
                'after': {'prior_event_preserved': True, 'hint_sources': sources,
                          'hint_tools': [tool] if sources else [], 'hints_current': True, 'one_hint_per_call': True,
                          'target_content_matches': True, 'tool_names': [tool], 'file_path_matches': True,
                          'hook_outputs_empty': True, 'evaluation_state_preserved': True,
                          'user_response_delivered': True},
                'hook_exit_codes': [0, 0], 'event': event, 'cli_exit_code': 0,
                'model_generation_requests': 3, 'model_successful_responses': 3}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_every_selected_file_operation_accepts_only_its_required_effect(self):
        for name in self.SHAPES:
            with self.subTest(name=name):
                self.assertEqual(check_pair(self.case(name)), [])

    def test_tracked_file_requires_the_hint_the_real_content_and_the_exact_path(self):
        for key, value in (('hint_sources', []), ('one_hint_per_call', False),
                           ('target_content_matches', False), ('file_path_matches', False),
                           ('tool_names', ['Bash'])):
            with self.subTest(key=key):
                case = self.case('file-hint-edit-gear')
                case['native']['after'][key] = case['hermes']['after'][key] = value
                self.assertIn('file-hint-edit-gear: file hint effect is missing', check_pair(case))

    def test_untracked_file_rejects_a_hint_or_an_evaluation_state_change(self):
        for key, value in (('hint_sources', ['projects']),
                           ('evaluation_state_preserved', False)):
            with self.subTest(key=key):
                case = self.case('file-hint-write-plain')
                case['native']['after'][key] = case['hermes']['after'][key] = value
                self.assertIn('file-hint-write-plain: file hint effect is missing', check_pair(case))

    def test_repeated_file_call_is_accepted_and_a_missing_call_is_rejected(self):
        case = self.case('file-hint-edit-gear')
        for side in ('native', 'hermes'):
            case[side]['hook_exit_codes'] = [0] * 4
        self.assertEqual(check_pair(case), [])
        case['native']['hook_exit_codes'] = [0]
        self.assertIn('file-hint-edit-gear: hook invocation count differs', check_pair(case))

    def test_fixture_uses_the_tool_matcher_and_seeds_only_the_edit_target(self):
        for name, (tool, _) in self.SHAPES.items():
            with self.subTest(name=name):
                folder = tempfile.TemporaryDirectory()
                self.addCleanup(folder.cleanup)
                base = Path(folder.name)
                source = base / 'source'
                (source / 'hooks').mkdir(parents=True)
                for hook in ('AtlasEventCapture', 'ConfigEvalFire'):
                    (source / f'hooks/{hook}.hook.ts').write_text('Fixture source identity\n')
                home = base / 'home'
                make_fixture(home, name, source, base / 'trace.py')
                group = json.loads((home / '.claude/settings.json').read_text())['hooks']['PostToolUse'][0]
                self.assertEqual(group['matcher'], tool)
                self.assertEqual(json.loads((home / 'before-state.json').read_text()),
                                 {'atlas_rows': 1, 'target_present': tool == 'Edit',
                                  'evaluation_state_present': name in self.SEEDED})

    def test_sentinel_cases_reject_a_changed_or_created_evaluation_state(self):
        for name in ('file-hint-sentinel-debounced', 'file-hint-sentinel-no-runner'):
            with self.subTest(name=name):
                case = self.case(name)
                for side in ('native', 'hermes'):
                    case[side]['after']['evaluation_state_preserved'] = False
                self.assertIn(f'{name}: file hint effect is missing', check_pair(case))


class PairedKnowledgeGuardTests(unittest.TestCase):
    def case(self, name):
        warned = name == 'knowledge-off-schema'
        side = {'before': {'target_present': False},
                'after': {'target_content_matches': True, 'tool_names': ['Write'], 'file_path_matches': True,
                          'warning_emitted': warned, 'other_output': False, 'model_received_warning': warned,
                          'user_response_delivered': True},
                'hook_exit_codes': [0], 'event': 'PostToolUse', 'cli_exit_code': 0,
                'model_generation_requests': 2, 'model_successful_responses': 2}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_each_case_accepts_only_its_required_effect(self):
        for name in ('knowledge-off-schema', 'knowledge-index-file'):
            with self.subTest(name=name):
                self.assertEqual(check_pair(self.case(name)), [])

    def test_off_schema_note_requires_the_warning_and_its_delivery(self):
        for key in ('warning_emitted', 'model_received_warning', 'target_content_matches'):
            with self.subTest(key=key):
                case = self.case('knowledge-off-schema')
                case['native']['after'][key] = case['hermes']['after'][key] = False
                self.assertIn('knowledge-off-schema: knowledge guard effect is missing', check_pair(case))

    def test_index_file_rejects_a_warning(self):
        case = self.case('knowledge-index-file')
        for side in ('native', 'hermes'):
            case[side]['after']['warning_emitted'] = case[side]['after']['model_received_warning'] = True
        self.assertIn('knowledge-index-file: knowledge guard effect is missing', check_pair(case))

    def test_fixture_runs_inside_the_knowledge_tree_with_the_write_matcher(self):
        from scripts.paired_lifecycle_effects import project_dir
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        (base / 'source/hooks').mkdir(parents=True)
        (base / 'source/hooks/KnowledgeWriteGuard.hook.ts').write_text('Fixture source identity\n')
        home = base / 'home'
        make_fixture(home, 'knowledge-off-schema', base / 'source', base / 'trace.py')
        self.assertEqual(project_dir(home, 'knowledge-off-schema'), home / '.claude/LIFEOS/MEMORY/KNOWLEDGE/Ideas')
        self.assertTrue(project_dir(home, 'knowledge-off-schema').is_dir())
        group = json.loads((home / '.claude/settings.json').read_text())['hooks']['PostToolUse'][0]
        self.assertEqual(group['matcher'], 'Write')
        self.assertIn('PostToolUse.8.6', group['hooks'][0]['command'])


class PairedISAEditGroupTests(unittest.TestCase):
    def case(self):
        from scripts.paired_lifecycle_effects import ISA_EDIT_AFTER
        side = {'before': {'isa_closed': False, 'repo_commits': 1, 'repo_dirty': True},
                'after': json.loads(json.dumps(ISA_EDIT_AFTER)), 'hook_exit_codes': [0] * 7,
                'event': 'PostToolUse', 'cli_exit_code': 0,
                'model_generation_requests': 3, 'model_successful_responses': 3}
        return {'id': 'isa-edit-close', 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_complete_group_accepts_the_measured_effects(self):
        self.assertEqual(check_pair(self.case()), [])
        self.assertEqual(len(CASES['isa-edit-close']), 7)

    def test_each_hook_effect_is_required(self):
        for path, value in ((('registry', 'phase'), 'observe'), (('view_matches_content',), False),
                            (('render_state_lists_isa',), False), (('checkpoint_state',), None),
                            (('checkpoint_commit', 'count'), 1), (('outputs', 'PostToolUse.9.1', 'context_head'), ''),
                            (('repo_dirty',), True)):
            with self.subTest(path=path):
                case = self.case()
                for side in ('native', 'hermes'):
                    target = case[side]['after']
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = value
                self.assertIn('isa-edit-close: ISA edit effect is missing', check_pair(case))

    def test_fixture_seeds_an_open_criterion_a_dirty_repository_and_its_allowlist(self):
        from scripts.paired_lifecycle_effects import project_dir
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        (base / 'source/hooks').mkdir(parents=True)
        for _, relative in CASES['isa-edit-close']:
            (base / 'source' / relative).write_text('Fixture source identity\n')
        home = base / 'home'
        make_fixture(home, 'isa-edit-close', base / 'source', base / 'trace.py')
        self.assertEqual(json.loads((home / 'before-state.json').read_text()),
                         {'isa_closed': False, 'repo_commits': 1, 'repo_dirty': True})
        self.assertEqual((home / '.claude/checkpoint-repos.txt').read_text().strip(), str(home / 'checkpoint-repo'))
        self.assertIn('- [ ] ISC-1:', (project_dir(home, 'isa-edit-close') / 'ISA.md').read_text())
        group = json.loads((home / '.claude/settings.json').read_text())['hooks']['PostToolUse'][0]
        self.assertEqual((group['matcher'], len(group['hooks'])), ('Edit', 7))


class PairedISAWriteAndReadTests(unittest.TestCase):
    def case(self, name):
        from scripts.paired_lifecycle_effects import isa_after
        side = {'before': {'isa_closed': False, 'repo_commits': 1, 'repo_dirty': True},
                'after': json.loads(json.dumps(isa_after(name))), 'hook_exit_codes': [0] * len(CASES[name]),
                'event': 'PostToolUse', 'cli_exit_code': 0,
                'model_generation_requests': 2, 'model_successful_responses': 2}
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_write_group_and_read_registration_accept_their_measured_effects(self):
        for name, count in (('isa-write-create', 7), ('isa-read-view', 1)):
            with self.subTest(name=name):
                self.assertEqual(len(CASES[name]), count)
                self.assertEqual(check_pair(self.case(name)), [])

    def test_write_requires_the_checkpoint_and_read_rejects_one(self):
        case = self.case('isa-write-create')
        for side in ('native', 'hermes'):
            case[side]['after']['checkpoint_state'] = None
        self.assertIn('isa-write-create: ISA edit effect is missing', check_pair(case))
        case = self.case('isa-read-view')
        for side in ('native', 'hermes'):
            case[side]['after']['repo_dirty'] = False
        self.assertIn('isa-read-view: ISA edit effect is missing', check_pair(case))

    def test_read_requires_the_recorded_view(self):
        case = self.case('isa-read-view')
        for side in ('native', 'hermes'):
            case[side]['after']['view_matches_content'] = False
        self.assertIn('isa-read-view: ISA edit effect is missing', check_pair(case))


class PairedGenericEffectTests(unittest.TestCase):
    def case(self, name):
        from scripts.paired_lifecycle_effects import GENERIC_EXPECTED
        files, printed, delivered = GENERIC_EXPECTED[name]
        identifier = CASES[name][0][0]
        side = {'before': {'files': 0},
                'after': {'changed': {path: 'content' for path in files},
                          'outputs': ['context' if value else '' for value in printed],
                          'stderr_present': [False], 'context_in_model': delivered, 'user_response_delivered': True},
                'hook_exit_codes': [0], 'event': identifier.split('.')[0], 'cli_exit_code': 0,
                'model_generation_requests': 1, 'model_successful_responses': 1}
        if name.startswith(('generic-tool-', 'generic-mcp-')):
            side['model_generation_requests'] = side['model_successful_responses'] = 2
        return {'id': name, 'native': side, 'hermes': json.loads(json.dumps(side))}

    def test_every_generic_case_accepts_its_measured_effect(self):
        from scripts.paired_lifecycle_effects import GENERIC_CASES
        for name in GENERIC_CASES:
            with self.subTest(name=name):
                self.assertEqual(check_pair(self.case(name)), [])

    def test_a_missing_file_change_output_or_delivery_is_rejected(self):
        case = self.case('generic-stop-gates')
        for side in ('native', 'hermes'):
            case[side]['after']['changed'].pop('.claude/LIFEOS/MEMORY/OBSERVABILITY/format-gate.jsonl')
        self.assertIn('generic-stop-gates: generic effect is missing', check_pair(case))
        case = self.case('generic-memory-turn')
        for side in ('native', 'hermes'):
            case[side]['after']['context_in_model'] = [False]
        self.assertIn('generic-memory-turn: generic effect is missing', check_pair(case))

    def test_one_side_with_a_different_file_content_is_unequal(self):
        case = self.case('generic-model-rung')
        case['hermes']['after']['changed'][next(iter(case['hermes']['after']['changed']))] = 'other'
        self.assertIn('generic-model-rung: paired state differs', check_pair(case))

    def test_normalization_removes_run_values_and_keeps_content(self):
        from scripts.paired_lifecycle_effects import normalize
        home = Path('/home/fixture/run')
        text = ('{"ts":"2026-10-05T12:00:01.123Z","session":"abc-session","path":"/home/fixture/run/.claude/projects/'
                '-x/abc-session.jsonl","_events_offset": 412,"value":"kept"}')
        self.assertEqual(normalize(text, home, 'abc-session'),
                         '{"ts":"<time>","session":"<session>","path":"<transcript>","_events_offset": <offset>,"value":"kept"}')
