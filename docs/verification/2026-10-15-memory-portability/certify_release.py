# ABOUTME: Binds the portability release to exact archived tests and installed removal recovery evidence.
# ABOUTME: Keeps historical runtime-equivalent checks distinct from exact candidate and public installation gates.
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

COMMIT='c86b5887b899ca779afbb217c33843e1ee12c381'
SHA='9e2a1939efbaccc94abaa879b265f1af447f9bdfe0b82aecc76f872f15fa9fb7'
IDENTITY={'version':'0.6.0','commit':COMMIT,'package_sha256':SHA}
FAULT='ab99723289884679b706440c7005fa5c'
NORMAL='16403c963170432a822bc9e9a60ab649'
PLUGINS={'lifeos','lifeos-hook-bridge','lifeos-release-manager'}
OPERATORS={'verify_restored_removal.py','restore_removed_guest.py','verify_fresh_candidate.py',
    'configure_fresh_release_model.py','provision_release_guest.py','bootstrap_release_guest.py',
    'prepare_fresh_release_candidate.py','certify_release.py','test_release_certificate.py'}


def require(condition,message):
    if not condition:raise ValueError(message)


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def identity(active):
    require(all(active.get(key)==value for key,value in IDENTITY.items()),'The active package differs')
    require(active.get('verification')=='verified' and active.get('modified_files')==[],
        'The active source verification is incomplete')


def effects(value,names):
    require(all(value.get(name) is True for name in names),'A required actual effect does not pass')


def authentication(value,workflow,action):
    require(value.get('workflow')==workflow and value.get('action')==action,
        'The retained authentication belongs to another workflow or action')
    effects(value,('actual_terminal','username_prompt','password_prompt','password_echo_disabled',
        'admitted','builtin_memory_unchanged'))
    require(value['wrong_password'] is False and value['exit_code']==0,
        'The retained owner authentication does not succeed')
    require(value['before_sha256']==value['after_sha256'],'Memory changes during owner authentication')


def review_closure(folder):
    value=json.loads((folder/'operator-review-closure.json').read_bytes())
    require(value['status']=='CLEAR','The verification operator review is not clear')
    root=Path(__file__).resolve().parents[3]
    report=(root/value['report']).resolve()
    require(report.is_relative_to(root/'docs/agents') and report.suffix=='.md',
        'The independent review report is outside the project review records')
    require(digest(report)==value['report_sha256'] and 'Review status: CLEAR' in report.read_text().splitlines(),
        'The independent review report does not match its clear closure')
    prefix='docs/verification/2026-10-15-memory-portability/'
    require(set(value['source_sha256'])=={prefix+name for name in OPERATORS},
        'The review does not cover every verification operator')
    require(all(digest(root/name)==expected for name,expected in value['source_sha256'].items()),
        'An operator changes after the independent review')
    return value


def removed(value,workflow):
    require(value['workflow']==workflow,'The removal workflow differs')
    require(value['workflow_status']['state']==value['publication_status']['state']=='verified',
        'The removal has not completed')
    require(value['workflow_receipt']['application_verified'] is True,'Removal application is not verified')
    require(set(value['active_software_present'])==PLUGINS and
        all(item is False for item in value['active_software_present'].values()),'Active LifeOS software remains')
    require(value['native_configuration_present'] is False and value['removal_marker_present'] is True
        and value['recovery_helper_present'] is True,'The retained recovery selection differs')


def certify(folder,build_path,dashboard):
    used={}
    def load(name):
        path=folder/name;used[name]=digest(path)
        return json.loads(path.read_bytes())
    def text(name):
        path=folder/name;used[name]=digest(path)
        return path.read_text()
    def passed(name):
        value=load(name);require(value['status']=='PASS',name+' does not pass');return value
    build=json.loads(build_path.read_bytes());archive=Path(build['archive'])
    require(build['head']==COMMIT and build['version']=='0.6.0','The candidate build differs')
    require(build['archive_sha256']==digest(archive)==SHA,'The candidate archive digest differs')
    require(build['archive_bytes']==archive.stat().st_size==288167820,'The archive size differs')
    for name,count in [('archive-integration-c86b5887',995),('native-sealed-c86b5887',716),('ui-archive-c86b5887',33)]:
        value=load(name+'.json')
        require(value['package_commit']==COMMIT and value['archive_sha256']==SHA and value['exit_code']==0,
            'The test result belongs to another package')
        require(text(name+'.done').strip()=='0','The test process does not complete successfully')
        stdout=text(name+'.stdout');stderr=text(name+'.stderr')
        if name.startswith('archive-integration'):
            require(value['status']=='PASS' and value['archive_files_match_before'] is True
                and value['archive_files_match_after'] is True,'The tested archive sources differ')
            require('Ran 995 tests' in stderr and stderr.rstrip().endswith('OK'),'The integration count differs')
            require(not any(word in stderr for word in ('ResourceWarning','skipped','Exception ignored')),
                'The integration output has unhandled diagnostics')
        elif name.startswith('native'):
            require('38 files, 716 tests passed, 0 failed (100% complete)' in stdout and not stderr,
                'The native test output differs')
            require(value['archived_source_files_unchanged'] is True and value['home_isolated'] is True,
                'Native source or account isolation differs')
        else:
            require('# tests 33\n' in stdout and '# pass 33\n' in stdout and '# fail 0\n' in stdout
                and '# skipped 0\n' in stdout and not stderr,'The component test output differs')
            require(value['test_sources_unchanged'] is True,'The tested component files differ')
    review=load('primary-pr29-archive.json')
    require(review['review_commit']==COMMIT and review['archive_sha256']==SHA
        and review['program_and_dependency_maps_verified'] is True,'The independent package identity differs')
    normal_archive=archive.with_name('0.5.0-b35cf86e.tgz')
    require(digest(normal_archive)=='d51eb1a5d5c175f3a0ef04871e29f443b4c07707e75899fba686934302161a82',
        'The runtime-equivalent normal-removal archive differs')
    declarations={'lifeos_hook_bridge/plugin.yaml','lifeos_hook_bridge/dashboard/manifest.json',
        'optional/lifeos_release_manager/plugin.yaml','optional/lifeos_release_manager/dashboard/manifest.json'}
    def runtime_map(path):
        with tarfile.open(path) as package:
            return {member.name:hashlib.sha256(package.extractfile(member).read()).hexdigest()
                for member in package if member.isfile() and member.name not in declarations
                and member.name.startswith(('lifeos_hook_bridge/','optional/lifeos_release_manager/'))}
    require(runtime_map(archive)==runtime_map(normal_archive),'The normal-removal runtime code differs')
    normal=load('installed-normal-removal-verified.json');removed(normal,NORMAL)
    current=load('installed-060-recovery-verified.json');removed(current,FAULT)
    identity(load('installed-060-update-identity.json')['result']['active'])
    fresh=passed('fresh-private-verification.json');identity(fresh['active_identity'])
    require(fresh['kind']=='private' and fresh['fresh_installation'] is True and fresh['native_mount_required'] is True
        and fresh['actual_model_round_trip'] is True and fresh['selected_model_and_tiers_preserved'] is True,
        'The fresh candidate installation is incomplete')
    require(fresh['personal_data_imported_or_reset'] is False and fresh['tool_names']==[],
        'The fresh installation model claim differs')
    post=passed('fresh-private-post-model-verification.json');identity(post['active_identity'])
    require(post['prior_model_receipt_sha256']==digest(folder/'fresh-private-verification.json')
        and post['model_session']==fresh['model_session'] and post['sealed_programs_verified_after_model'] is True
        and post['selected_model_and_tiers_unchanged_after_model'] is True,'The post-model verification differs')
    manager=passed('fresh-native-manager-install.json')
    require(manager['actual_native_web_install_http_status']==200 and manager['owner_ui_authenticated'] is True
        and manager['all_qualified_manager_files_match'] is True and manager['native_store_present'] is False
        and manager['native_memory_policy_present'] is False,'The native Git installation is incomplete')
    injected=passed('installed-060-worker-interruption.json')
    require(injected['workflow']==FAULT and injected['signal_sent'] is True and injected['exact_main_pid_bound'] is True
        and injected['pidfd_used'] is True and injected['all_active_plugins_absent'] is True,
        'The actual removal interruption is not bound')
    for name,workflow,action in (('installed-060-recovery-authentication.json',FAULT,'recover'),
            ('installed-normal-rollback-authentication.json',NORMAL,'rollback')):
        value=passed(name)
        authentication(value,workflow,action)
    refused=passed('installed-stock-wrong-password-refusal.json')
    require(refused['admitted'] is False and refused['wrong_password'] is True and refused['exit_code']==1,
        'The wrong-password control does not refuse')
    require(refused['workflow']==NORMAL and refused['action']=='rollback','The password refusal uses another action')
    effects(refused,('actual_terminal','password_echo_disabled','builtin_memory_unchanged'))
    before=load('installed-stock-before-reboot.json');after=passed('installed-stock-after-reboot.json')
    require(before['boot_id']!=after['boot_id'] and before['builtin_files']==after['builtin_files'],
        'The reboot or retained memory proof differs')
    rollback=load('installed-normal-authenticated-rollback.json')
    require(rollback['workflow_status']['state']==rollback['publication_status']['state']=='rolled_back'
        and all(rollback['active_software_present'].values()) and rollback['removal_marker_present'] is False,
        'Normal authenticated software rollback does not complete')
    require(rollback['builtin_files']==current['builtin_files'],'Later Hermes learning changes during recovery')
    sessions=[]
    for name in ('installed-new-native-learning.json','installed-new-native-recall.json',
            'installed-new-native-fact-builtin-recall.json','installed-stock-builtin-recall.json',
            'installed-stock-later-learning.json','installed-stock-postboot-later-recall.json',
            'installed-postrollback-later-recall.json','installed-imported-fact-pass.json'):
        value=passed(name)
        require(value['model_turn_executed'] is True and value['fresh_session'] is True and value['exit_code']==0,
            'The actual fresh model turn does not pass')
        sessions.append(value['session_id'])
    require(len(sessions)==len(set(sessions)),'The model turns reuse a session')
    effects(load('installed-stock-later-learning.json'),('actual_tool_success','later_fact_published',
        'prior_memory_preserved','exact_tool_selection'))
    for name in ('installed-stock-builtin-recall.json','installed-stock-postboot-later-recall.json',
            'installed-postrollback-later-recall.json'):
        value=load(name)
        effects(value,('marker_matched','expected_tool_selection','configured_route_used'))
        require(value['actual_search']['verified'] is True and value['tool_names']==[],
            'The actual stock recall proof differs')
    native_return=load('installed-new-native-fact-builtin-recall.json')
    effects(native_return,('actual_proof',));require(native_return['tool_names']==[],
        'The native fact return uses an unexpected tool')
    learned=load('installed-new-native-learning.json');recalled=load('installed-new-native-recall.json')
    require(learned['actual_tool_status']=='committed' and learned['reference'] in recalled['actual_search']['references']
        and recalled['actual_proof'] is True,'New native learning is not recalled')
    effects(learned,('actual_proof','exact_arguments'))
    require(learned['tool_names']==['lifeos_memory_remember'] and recalled['tool_names']==['lifeos_memory_search']
        and recalled['actual_search']['verified'] is True,'The native learning tool proof differs')
    effects(load('installed-imported-fact-pass.json'),('original_source_digest_matches','exact_tool_selection',
        'actual_tool_ok','exact_reference'))
    returned=load('installed-corrected-provider-return.json')
    require(returned['workflow_status']['state']=='verified' and returned['workflow_receipt']['application_verified'] is True,
        'The provider return is incomplete')
    exported=load('installed-corrected-native-export.json')
    require(exported['all_required'] is True and exported['all_exported'] is True and len(exported['references'])==6
        and all(row['revision']==1 for row in exported['references']),'The portable export is incomplete')
    replay=passed('installed-portable-bundle-replay.json')
    require(replay['actual_owner_browser_upload_review_apply'] is True and replay['required_items_verified'] is True
        and replay['unique_references']==4,'The portable bundle replay is incomplete')
    cold=passed('cold-restore-verification.json')
    require(cold['source_guest']==110 and cold['restored_guest']==111 and cold['workflow']==FAULT
        and cold['archive'].startswith('PBS-01:backup/ct/110/') and cold['archive_protected'] is True
        and cold['network_disconnected'] is True and cold['software_rollback_verified'] is True,
        'The cold whole-guest restore is incomplete')
    identity(cold['active_identity'])
    require(isinstance(cold.get('retained_helper_authentication'),dict),
        'The cold restored rollback authentication is absent')
    authentication(cold['retained_helper_authentication'],FAULT,'rollback')
    require(cold['builtin_files']==current['builtin_files'] and cold['native_consistency']['native_consistency_signature_verified'] is True
        and cold['all_original_guest_states_preserved'] is True,'The cold restored data differs')
    require(digest(folder/'cold-restore-operations.json')==cold['operations_sha256'],
        'The cold restore operations differ')
    operations=load('cold-restore-operations.json')
    require(all(row['exit_code']==0 for row in operations),'A cold restore command fails')
    require({'backup-source','restore','disconnect','boot-offline','restored-native-verification',
        'restored-authentication','restored-version','shutdown-restore'} <= {row['label'] for row in operations},
        'A cold restore command is absent')
    require(text('cold-restore-process.done').strip()=='0','The cold restore does not complete')
    require(digest(dashboard)=='e7c93e754de99b6ec66ae17ae313377dc513104da2776a099c391a7aab347bec',
        'The qualified Hermes dashboard asset differs')
    closure=review_closure(folder)
    used['operator-review-closure.json']=digest(folder/'operator-review-closure.json')
    return {'format':1,'status':'QUALIFIED','production_qualified':True,'version':'0.6.0',
        'program_commit':COMMIT,'archive_sha256':SHA,'archive_bytes':288167820,
        'hermes_dashboard_sha256':digest(dashboard),'hermes_base':build['hermes_base'],
        'lifeos_base':build['lifeos_base'],'hermes_patch_count':build['hermes_patch_count'],
        'lifeos_patch_count':build['lifeos_patch_count'],'integration_tests':995,'native_tests':716,
        'ui_component_tests':33,'qualification_receipt_sha256':used,
        'qualification_scope':'Exact archive regression, fresh candidate installation, authenticated update, memory import and return, complete removal, actual stock model learning, reboot, worker-exit recovery, and disconnected whole-guest restore with authenticated software rollback',
        'historical_checks':'The normal removal, stock model, reboot, and normal rollback use b35cf86e. All bridge and manager runtime files match c86b5887, except four version declarations. Earlier source import and portable replay retain their named checkpoints.',
        'verification_operator_review':closure,
        'complete_software_removal_data_erasure':False,'shared_211_import_verified':False,
        'development_promotion_verified':False,'daily_promotion_verified':False,
        'public_default_url_replay_for_060':'Pending public publication',
        'live_discord_acceptance_for_060':False,'automatic_morning_observed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--dashboard',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    certificate=certify(Path(__file__).resolve().parent,args.build,args.dashboard)
    with args.output.open('x') as output:output.write(json.dumps(certificate,indent=2)+'\n')
    print(json.dumps({'status':'QUALIFIED','program_commit':COMMIT,'certificate_sha256':digest(args.output)}))
