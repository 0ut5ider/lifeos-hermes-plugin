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
