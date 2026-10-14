# ABOUTME: Binds public installation and update acceptance to actual installed receipts.
# ABOUTME: Creates a separate public checkpoint and preserves the immutable qualification certificate.
import hashlib
import json
from pathlib import Path

out = Path(__file__).resolve().parent
used = set()


def load(name):
    used.add(name)
    value = json.loads((out / name).read_bytes())
    assert value['status'] == 'PASS', name
    return value


identity = {'version': '0.4.2', 'commit': '87205092832c550a09fce6e1cb3ca944fdb69a8c',
    'package_sha256': '76c1c10e82ce75f86858a2cd27ae609f5f7eb8a8bc79612d94df6f95f45136a4'}
certificate_sha = 'd937719db08eb0218a4f3f037a7132537f4e7ba55b48790467936df8a59e977e'
assert hashlib.sha256((out / 'RELEASE-CERTIFICATE.json').read_bytes()).hexdigest() == certificate_sha
manager = load('public-default-github-manager-install.json')
assert manager['guest'] == 111 and manager['force_reinstall'] is False
assert manager['initial_manager_hash_inventory_captured'] is True
assert manager['complete_lifeos_not_installed_yet'] is True and len(manager['files']) == 19
assert manager['metadata']['source'] == 'https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager'
assert manager['metadata']['revision'] == '7ac93c6902dd1311fea804f160f4a765c42b9e01'
assert manager['explicit_branch_or_commit_selected'] is False and manager['metadata']['pinned'] is False
assert manager['manager_program_commit'] == identity['commit']
baseline = load('public-rc3-baseline.json')
assert baseline['active_identity']['version'] == '0.4.2-rc.3'
assert baseline['actual_update_lifeos_button'] is True
prior_reference = baseline['synthetic_fact_preserved']['reference']
assert prior_reference == {'id': 'da7e20b95b904ca7ac4aab594c23b5ee', 'revision': 1}
assert baseline['synthetic_fact_preserved']['actual_authenticated_mcp_get'] is True
model_hash = baseline['model_selection_sha256']
operations = {}
for label, intent in [('fresh', 'install'), ('plugin-update', 'plugin'), ('lifeos-update', 'update')]:
    prefix = {'fresh': 'fresh', 'plugin-update': 'plugin-update', 'lifeos-update': 'lifeos-update'}[label]
    prepare = load('public-latest-' + prefix + '-preparation.json')
    applied = load({'fresh': 'public-fresh-install-applied.json',
        'plugin-update': 'public-plugin-update-applied.json',
        'lifeos-update': 'public-lifeos-update-applied.json'}[label])
    assert prepare['request'] == applied['active_identity'] == identity
    assert prepare['certificate_sha256'] == certificate_sha
    assert prepare['preparation']['intent'] == intent and prepare['preparation']['version'] is None
    assert prepare['blank_latest_stable_selected'] is True
    assert applied['operation_state'] == applied['program_transaction_state'] == 'applied'
    assert applied['operation'] == prepare['operation']
    assert applied['model_selection_sha256'] == model_hash
    assert applied['selected_models_and_tiers_preserved'] is True
    if label != 'fresh':
        memory = load('public-' + prefix + '-memory-preservation.json')
        assert memory['operation'] == applied['operation']
        assert memory['http_status'] == 200 and memory['matched_content'] is True
        assert memory['reference'] == prior_reference
    operations[label] = applied['operation']
owner = load('public-fresh-ownership-activation.json')
turn = load('public-fresh-owner-turn-verification.json')
assert owner['operation'] == operations['fresh'] and owner['authenticated_owner_verified'] is True
assert owner['connector_verified'] is True and owner['selected_model_and_tiers_preserved'] is True
assert owner['personal_data_imported'] is owner['sharing_enabled'] is False
assert turn['verification_active_identity'] == identity and turn['actual_write_and_fresh_conversation_read_verified'] is True
assert len(turn['sessions']) == 2 and turn['sessions'][0] != turn['sessions'][1]
assert turn['sessions'] == ['20261013_234822_ffa873', '20261013_234904_3c2b20']
assert turn['reference'] == {'id': '62a426513bfc4031bc786c025f91da64', 'revision': 1}
assert turn['writer'] == 'terminal:1000' and turn['synthetic_data_only'] is True
assert turn['synthetic_profile_only'] is True and turn['model'] == 'flashnext-w4a16-fp8ple'
conversation = load('public-conversation-preparation.json')
assert conversation['actual_terminal_input'] == {'command': 'hermes lifeos-release prepare', 'timeout': 300}
tool = conversation['actual_terminal_result']
assert tool['exit_code'] == 0 and tool['error'] is None
assert tool['approval'] == 'Command required approval (Plugin command policy requires review) and was approved by the user.'
prepared = json.loads(tool['output'])
assert prepared == conversation['prepared_operation'] and prepared['state'] == 'ready'
assert {key: prepared[key] for key in identity} == identity
assert conversation['interactive_owner_approval_verified'] is True
applied = load('public-conversation-update-applied.json')
assert applied['operation'] == prepared['identifier'] and applied['active_identity'] == identity
assert applied['operation_state'] == applied['program_transaction_state'] == 'applied'
assert applied['model_selection_sha256'] == model_hash
memory = load('public-conversation-memory-preservation.json')
assert memory['operation'] == applied['operation'] and memory['reference'] == prior_reference
assert memory['http_status'] == 200 and memory['tool_status'] == 'ok' and memory['matched_content'] is True
operations['conversation-update'] = applied['operation']
assert len(set(operations.values())) == 4
historical = load('protected-all-release-assets-after.json')
assert historical['historical_releases'] == 7 and historical['historical_assets'] == 41
assert historical['all_asset_ids_sizes_and_digests_unchanged'] is True
servers = load('final-server-identities.json')
assert servers['servers'][0]['active_identity'] == identity
assert servers['servers'][1]['active_identity']['version'] == '0.3.1'
publication = load('stable-publication.json')
assert publication['latest_stable_verified'] is True and publication['tag'] == 'v0.4.2'
assert publication['certificate_sha256'] == certificate_sha
report = {'format': 1, 'status': 'PASS', 'version': '0.4.2', 'program_commit': identity['commit'],
    'archive_sha256': identity['package_sha256'], 'qualification_certificate_sha256': certificate_sha,
    'public_latest_stable_verified': True, 'default_github_url_installation_verified': True,
    'blank_latest_install_lifeos_verified': True, 'rc3_to_stable_update_plugin_verified': True,
    'blank_latest_update_lifeos_verified': True, 'interactive_hermes_update_verified': True,
    'fresh_governed_memory_save_and_recall_verified': True,
    'existing_synthetic_fact_and_model_mapping_preserved': True,
    'operations': operations, 'historical_release_assets_unchanged': 41,
    'daily_server_version': '0.3.1', 'daily_server_changed': False,
    'daily_promotion_verified': False, 'automatic_morning_observed': False,
    'qualification_certificate_replaced': False,
    'receipt_sha256': {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in sorted(used)}}
target = out / 'PUBLIC-LATEST-ACCEPTANCE.json'
assert not target.exists(), 'The public acceptance checkpoint already exists'
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'operations': operations, 'public_receipts': len(used)}))
