# ABOUTME: Checks native audit facts after actual installed skill, file, shell, and MCP operations.
# ABOUTME: Uses synthetic work registry state and the actual detached reconciliation tool.
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from hermes_cli import plugins
from model_tools import handle_function_call
from tools.file_tools import read_file_tool
from tools.mcp_tool_discovery import register_mcp_servers
from tools.mcp_tool_lifecycle import shutdown_mcp_servers
from tools.terminal_tool import cleanup_all_environments

home = Path.home()
root = home / '.claude'
source = Path(os.environ['PAIR_FILE_SOURCE'])
profile = Path(os.environ['HERMES_HOME'])
root.mkdir()
(root / 'LIFEOS').mkdir()
(root / 'LIFEOS/TOOLS').symlink_to(source / 'LIFEOS/TOOLS', target_is_directory=True)
(root / 'hooks').symlink_to(source / 'hooks', target_is_directory=True)
(profile / 'config.yaml').write_text(json.dumps({'plugins': {'enabled': ['lifeos-hook-bridge']}, 'terminal': {'env_type': 'local'}}))
(root / 'settings.json').write_text(json.dumps({'permissions': {'allow': ['Read','Write','Edit','Bash','mcp__audit__ping']},
    'hooks': {event: [{'hooks': [{'type': 'command', 'command': 'bun ' + str(root / 'hooks/EventLogger.hook.ts')}]}]
              for event in ('PostToolUse','PostToolUseFailure')}}))
(skill := profile / 'skills/audit-fixture/SKILL.md').parent.mkdir(parents=True)
skill.write_text('---\nname: audit-fixture\ndescription: Synthetic audit fixture\n---\n# Fixture\nPAIR_SKILL_CONTENT\n')
isa = root / 'LIFEOS/MEMORY/WORK/audit/ISA.md'
isa.parent.mkdir(parents=True)
started = (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
isa.write_text(f'---\ntitle: Audit fixture\nstarted: {started}\nphase: observe\nprogress: 0/1\n---\n## Claims\n- [ ] ISC-1: Fixture\n')
process = subprocess.run(['bun', str(source / 'hooks/ISASync.hook.ts')],
    input=json.dumps({'hook_event_name':'PostToolUse','session_id':'audit','tool_name':'Write','tool_input':{'file_path':str(isa)}}),
    capture_output=True,text=True)
assert process.returncode == 0, process
assert all('[tab-setter] getKittyEnv: no kitty env found' in line for line in process.stderr.splitlines()), process.stderr
config=json.loads((profile/'config.yaml').read_text())
mutation='sed -i s/observe/build/ '+str(isa)
config['command_allowlist']=[mutation]
(profile/'config.yaml').write_text(json.dumps(config))
plugins._reset_plugin_managers_for_tests()
plugins.discover_plugins()
from tools.approval import load_permanent_allowlist
load_permanent_allowlist()


def call(name, args, identity):
    result = handle_function_call(name,args,task_id='audit',session_id='audit',tool_call_id=identity)
    value,_ = json.JSONDecoder().raw_decode(result)
    return value


def read_json(path):
    return json.loads(path.read_text())


def wait(predicate, label):
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.05)
    raise AssertionError(label)


try:
    skill_result=call('skill_view',{'name':'audit-fixture'},'skill')
    assert 'PAIR_SKILL_CONTENT' in json.dumps(skill_result),skill_result
    reconcile = root / 'LIFEOS/MEMORY/STATE/work-reconcile.json'
    wait(reconcile.exists,'Initial actual reconciliation did not finish')
    target=home/'project/file.txt'
    result=call('write_file',{'path':str(target),'content':'x'*600},'write')
    assert not result.get('error') and target.read_text()=='x'*600,result
    registry=root/'LIFEOS/MEMORY/STATE/work.json'
    state=read_json(registry)
    state['sessions']['audit']['lastToolActivity']='2020-01-01T00:00:00.000Z'
    registry.write_text(json.dumps(state))
    reconcile_state=read_json(reconcile)
    reconcile_state['checkedAt']='2020-01-01T00:00:00.000Z'
    reconcile.write_text(json.dumps(reconcile_state))
    os.utime(reconcile,(1,1))
    result=call('terminal',{'command':mutation},'mutate')
    assert result.get('exit_code')==0,result
    wait(lambda:read_json(registry)['sessions']['audit']['phase']=='build','Actual detached reconciliation did not update the ISA phase')
    heartbeat=read_json(registry)['sessions']['audit']['lastToolActivity']
    assert not heartbeat.startswith('2020'),heartbeat
    failed=call('terminal',{'command':'false'},'shell-failure')
    assert failed.get('exit_code')==1,failed
    locked=home/'locked/failure.txt'
    locked.parent.mkdir()
    locked.write_text('OLD')
    locked.chmod(0o444)
    locked.parent.chmod(0o555)
    try:
        assert not json.loads(read_file_tool(str(locked),task_id='audit')).get('error')
        failed_file=call('write_file',{'path':str(locked),'content':'DENIED'},'file-failure')
        assert 'Permission denied' in failed_file.get('error',''),failed_file
    finally:
        locked.parent.chmod(0o755)
        locked.chmod(0o644)
    names=register_mcp_servers({'audit':{'command':sys.executable,'args':[str(Path(__file__).with_name('audit_mcp_server.py'))]}})
    assert 'mcp__audit__ping' in names,names
    failed_mcp=call('mcp__audit__ping',{},'mcp-failure')
    assert 'PAIR_ACTUAL_MCP_FAILURE' in failed_mcp.get('error',''),failed_mcp
    activity=[json.loads(line) for line in (root/'LIFEOS/MEMORY/OBSERVABILITY/tool-activity.jsonl').read_text().splitlines()]
    skills=[json.loads(line) for line in (root/'LIFEOS/MEMORY/SKILLS/execution.jsonl').read_text().splitlines()]
    failures=[json.loads(line) for line in (root/'LIFEOS/MEMORY/OBSERVABILITY/tool-failures.jsonl').read_text().splitlines()]
    assert [row['tool_name'] for row in activity]==['Skill','Write','Bash'],activity
    assert len(skills)==1 and 'audit-fixture' in json.dumps(skills),skills
    assert len(activity[1]['ground_truth']['content_preview'])==500+len('...[truncated]'),activity[1]
    assert activity[1]['ground_truth']['content_bytes']==600
    assert [row['tool_name'] for row in failures]==['Bash','Write','mcp__audit__ping'],failures
    assert '1' in failures[0]['error'] and 'Permission denied' in failures[1]['error'] and 'PAIR_ACTUAL_MCP_FAILURE' in failures[2]['error'],failures
    (home/'audit-results.json').write_text(json.dumps({'activity':activity,'skills':skills,'failures':failures,
        'actual_reconciled_phase':'build','heartbeat_advanced':True,'actual_failed_file_retained':locked.read_text()=='OLD'},indent=2)+'\n')
finally:
    shutdown_mcp_servers()
    plugins.unload_plugins()
    cleanup_all_environments()
