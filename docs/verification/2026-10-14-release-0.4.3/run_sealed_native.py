# ABOUTME: Runs the official Hermes test runner with isolated home and actual SSH fixtures.
# ABOUTME: Writes safe test output and completion state without exposing credential contents.
import hashlib, json, os, subprocess, time, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from optional.lifeos_release_manager.release_catalog import extract_package
from lifeos_hook_bridge.install_source import validate_supported_hermes
out=Path(__file__).parent
build=json.loads(Path(os.environ['LIFEOS_QUALIFICATION_BUILD']).read_bytes());identity=build['head'][:8]
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha(build['archive'])==build['archive_sha256']
assert Path(build['archive']).stat().st_size==build['archive_bytes']
workspace=Path(tempfile.mkdtemp(prefix='native-bound-',dir='/home/outsider/.cache/lifeos-daily-promotion-20261014/native-workspaces'))
package=workspace/'package';extract_package(build['archive'],package)
root=package/'hermes'
source_manifest=validate_supported_hermes(root)
manifest_sha=sha(root/'hermes-source-manifest.json')
original_files={str(path.relative_to(root)):sha(path) for path in root.rglob('*') if path.is_file()}
config=subprocess.run(['ssh','-G','root@192.168.8.252'],capture_output=True,text=True,check=True).stdout
key=next(Path(line.split(' ',1)[1]).expanduser() for line in config.splitlines() if line.startswith('identityfile ') and Path(line.split(' ',1)[1]).expanduser().is_file())
env={'PYTHONDONTWRITEBYTECODE':'1', 'PATH': '/home/outsider/.cache/lifeos-daily-promotion-20261014/local-fixture-repeat/account/.hermes/.lifeos-releases/577a8a31d59e49c19d522ed3444e1b31/tools:/home/outsider/.bun/bin:/home/outsider/.local/bin:/home/outsider/.opencode/bin:/home/outsider/.npm-global/bin:/home/outsider/.local/bin:/home/outsider/bin:/home/outsider/.codex/packages/standalone/releases/0.162.1-x86_64-unknown-linux-musl/codex-path:/home/outsider/.codex/tmp/arg0/codex-arg0LZM6cJ:/home/outsider/.bun/bin:/home/outsider/.local/bin:/home/outsider/.opencode/bin:/home/outsider/.cargo/bin:/home/outsider/.npm-global/bin:/home/outsider/bin:/home/outsider/.nvm/versions/node/v22.22.3/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin', 'HOME': str(workspace/'home'), 'HERMES_PYTHON': '/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python', 'HERMES_TEST_FILE_RETRIES': '0', 'HERMES_TEST_SSH_HOST': '192.168.8.252', 'HERMES_TEST_SSH_USER': 'root', 'HERMES_TEST_SSH_HOME': '/tmp/lifeos-managed-ssh-043'}
env['HERMES_TEST_SSH_KEY']=str(key)
env['TZ']='UTC'
Path(env['HOME']).mkdir(mode=0o700)
bun=Path(env['PATH'].split(':')[0])/'bun'
bun_version=subprocess.check_output([str(bun),'--version'],text=True).strip()
assert bun_version=='1.4.3'
assert sha(bun)=='7ce7d6b654eddeec20afddf2396317fba6dc19ab52788a27e894e1806bf8f24b'
command=['bash', str(root/'scripts/run_tests.sh'), '-j', '4', 'tests/agent/test_prompt_hook_block.py', 'tests/agent/test_terminal_approval_batch.py', 'tests/agent/test_tool_result_context_hook.py', 'tests/agent/test_turn_context.py', 'tests/agent/test_verification_continuation_budget.py', 'tests/gateway/test_clarify_cancellation_outcome.py', 'tests/gateway/test_clarify_delivery_fallback.py', 'tests/gateway/test_discord_command_identity.py', 'tests/gateway/test_discord_connect.py', 'tests/gateway/test_discord_guild_channel_only.py', 'tests/gateway/test_discord_sync_limit.py', 'tests/gateway/test_resume_command.py', 'tests/gateway/test_stop_clarify_waiters.py', 'tests/hermes_cli/test_approval_transport.py', 'tests/hermes_cli/test_cli_resume_command.py', 'tests/hermes_cli/test_plugins.py', 'tests/hermes_cli/test_required_middleware.py', 'tests/hermes_cli/test_required_policy_hooks.py', 'tests/hermes_cli/test_session_boundary_hooks.py', 'tests/hermes_cli/test_stop_policy_dispatch.py', 'tests/plugins/test_transform_tool_result_hook.py', 'tests/test_lifeos_aux_no_fallback.py', 'tests/test_lifeos_batch_schema.py', 'tests/test_lifeos_delegate_tier_route.py', 'tests/test_lifeos_execute_code_session.py', 'tests/tools/test_approval_plugin_hooks.py', 'tests/tools/test_code_execution.py', 'tests/tools/test_code_execution_file_rpc.py', 'tests/tools/test_code_kernel.py', 'tests/tools/test_code_kernel_remote.py', 'tests/tools/test_plugin_command_approval.py', 'tests/tools/test_remote_file_staleness.py', 'tests/tools/test_protected_instruction_cli_channel.py']
command.extend(['tests/hermes_cli/test_plugin_policy_arguments.py','tests/hermes_cli/test_plugins_middleware_chain.py','tests/agent/test_auxiliary_client.py','tests/agent/test_auxiliary_fallback_multihop.py','tests/hermes_cli/test_plugin_async_dispatch.py'])
# The actual SSH fixture returns after the independent stop-mode guest backup.
ready_deadline=time.monotonic()+1800
while True:
 ready=subprocess.run(['ssh','-o','ConnectTimeout=5','root@192.168.8.252','true'],capture_output=True,timeout=15)
 if ready.returncode==0:break
 assert time.monotonic()<ready_deadline,'The actual SSH fixture does not return'
 time.sleep(5)
started=time.monotonic()
with (out/('native-sealed-'+identity+'.stdout')).open('w') as stdout,(out/('native-sealed-'+identity+'.stderr')).open('w') as stderr:
 r=subprocess.run(command,cwd=root,env=env,stdout=stdout,stderr=stderr,timeout=1800)
unchanged=all((root/name).is_file() and sha(root/name)==digest for name,digest in original_files.items())
assert unchanged
(out/('native-sealed-'+identity+'.json')).write_text(json.dumps({'package_commit':build['head'],'archive_sha256':build['archive_sha256'],
 'source_manifest_sha256':manifest_sha,'source_tree_sha256':source_manifest['tree_sha256'],
 'archived_source_files_unchanged':unchanged,'bun_version':bun_version,'bun_binary_sha256':sha(bun),
 'command':command,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-started,'home_isolated':True,'live_ssh_fixture':True},indent=2)+'\n')
(out/('native-sealed-'+identity+'.done')).write_text(str(r.returncode)+'\n')
