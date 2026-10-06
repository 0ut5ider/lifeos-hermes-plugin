# ABOUTME: Validates selected configuration, web, and batch functional evidence.
# ABOUTME: Rejects false native CLI claims and missing effects even when recorded sides match.


def check_control(record):
    name = record.get('id', '')
    errors = []
    native, hermes = record.get('native'), record.get('hermes')
    if native != hermes:
        errors.append('control outcomes differ')
    if name == 'config-external-sources':
        changes = (native or {}).get('changes', [])
        expected = [('user-one', 'user_settings', '.claude/settings.json', 'env'),
                    ('user-two', 'user_settings', '.claude/settings.json', 'env'),
                    ('project', 'project_settings', 'project/.claude/settings.json', 'initial'),
                    ('project-two', 'project_settings', 'project/.claude/settings.json', 'env'),
                    ('local', 'local_settings', 'project/.claude/settings.local.json', 'initial'),
                    ('local-two', 'local_settings', 'project/.claude/settings.local.json', 'env'),
                    ('skill', 'skills', '.claude/skills/fixture-config/SKILL.md', 'initial'),
                    ('skill-two', 'skills', '.claude/skills/fixture-config/SKILL.md', 'content')]
        if ([(row.get('id'), row.get('source'), row.get('file_path'), row.get('config_key')) for row in changes] != expected
                or native.get('hook_calls') != 8 or native.get('duplicate_rows') != 0
                or any(row.get('native_audit_path') != '<home>/' + row.get('file_path', '')
                       or not row.get('change_summary') for row in changes)):
            errors.append('configuration source, path, diff, or duplicate check is missing')
        return errors
    if record.get('native_cli_dispatch') is not False or record.get('hermes_tool_dispatch') is not True:
        errors.append('functional control dispatch scope is invalid')
    if name.startswith('generic-web-'):
        expected = {'warning_present': True, 'injection_marker': name.endswith('-injection'),
                    'ordinary_body_not_duplicated': True}
        actual = record.get('hermes_record', {})
        if (native != expected or record.get('content_in_next_model_request') is not True
                or record.get('context_in_next_model_request') is not True
                or actual.get('cli_exit_code') != 0 or actual.get('model_successful_responses', 0) < 2
                or actual.get('model_generation_requests') != actual.get('model_successful_responses')
                or actual.get('after', {}).get('context_in_model') != [True]
                or actual.get('after', {}).get('user_response_delivered') is not True):
            errors.append('web result, safety annotation, or model delivery is missing')
    elif name in {'batch-success', 'batch-partial'}:
        partial = name == 'batch-partial'
        expected = {'isa_closed': True, 'view_matches_content': True, 'registry_present': True,
                    'render_state_lists_isa': True, 'checkpoint_commits': 1 if partial else 2,
                    'checkpoint_records_criterion': not partial, 'atlas_sources': [] if partial else ['projects'],
                    'knowledge_warning': not partial, 'complexity_lines': 0 if partial else 250,
                    'dependency_count': 0 if partial else 1, 'evaluation_debounce_preserved': True,
                    'all_files_match': True, 'applied_files': 1 if partial else 6,
                    'failed_files': 1 if partial else 0, 'hook_calls': 6 if partial else 42}
        if native != expected:
            errors.append('batch mutation, hook effects, or partial checkpoint safety is missing')
    else:
        errors.append('unknown functional control')
    return errors
