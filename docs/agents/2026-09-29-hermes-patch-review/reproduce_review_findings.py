# ABOUTME: Reproduces review findings from the exact patched Hermes source.
# ABOUTME: Uses source-extracted functions and minimal boundary doubles, without providers or deployment.
from __future__ import annotations
import ast
import hashlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/hermes-astra-review-20260929')
sys.path.insert(0, str(ROOT))
results = {}

def extract(relative, names, ns):
    tree = ast.parse((ROOT / relative).read_text())
    selected = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *selected], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(ROOT / relative), 'exec'), ns)

# Stock dispatch is imported intact. Only plugin discovery/config resolution is replaced.
from hermes_cli import plugins_dispatch as dispatch
plugin_api = types.ModuleType('hermes_cli.plugins')
plugin_api._resolve_hook_callback_timeout = lambda: 30
plugin_api.resolve_plugin_command_result = lambda x: x
sys.modules['hermes_cli.plugins'] = plugin_api
class Manager(dispatch.PluginDispatchMixin):
    def __init__(self): self._hooks = {}; self.errors = []
    def _report_hook_failure(self, name, cb, kwargs, exc, **rest): self.errors.append((name, type(exc).__name__))
    def _run_hook_callback_bounded(self, *a): return dispatch._HOOK_SKIPPED
manager = Manager()
def broken(**kwargs): raise ValueError('synthetic policy parse error')
for name in ['pre_command_approval', 'pre_turn_stop']:
    manager._hooks[name] = [broken]
    results[name + '_exception_returns'] = manager.invoke_hook(name)
manager._hooks['pre_llm_call'] = [lambda **k: {'action': 'block'}]
results['pre_llm_call_timeout_returns'] = manager.invoke_hook('pre_llm_call')
results['dispatch_recorded_errors'] = manager.errors
results['new_policy_hooks_are_timeout_bounded'] = {name: dispatch._hook_uses_callback_timeout(name, 30) for name in ['pre_command_approval','pre_turn_stop']}
assert results['pre_command_approval_exception_returns'] == []
assert results['pre_turn_stop_exception_returns'] == []
assert results['pre_llm_call_timeout_returns'] == []

# A prior session approval suppresses a later workspace's review of identical text.
batch = types.ModuleType('agent.terminal_approval_batch')
batch.consume_prepared_guard = lambda *a: None
sys.modules['agent.terminal_approval_batch'] = batch
approved_keys = set(); prompts = []; policy_calls = []
def policy(command, pattern, description, **kw): policy_calls.append(kw); return 'review'
def human(spec, **kw):
    prompts.append(kw['command'])
    approved_keys.update(kw['pattern_keys'])
    return {'approved': True}
ns = dict(hashlib=hashlib, _should_skip_container_guards=lambda *a,**k:False, _floor_block=lambda *a,**k:None,
    approval_context=SimpleNamespace(_get_approval_mode=lambda:'manual'), _yolo_active=lambda:False,
    detect_dangerous_command=lambda c:(False,None,None), get_current_session_key=lambda:'same-session',
    _plugin_command_decision=policy, is_approved=lambda s,k:k in approved_keys, _approved=lambda:{'approved':True},
    _command_matches_permanent_allowlist=lambda c:False, _presence=lambda cb:(cb,True,False,False),
    _tirith_scan=lambda c:{'action':'allow'}, _human_decision=human, _COMMAND_GATE=object())
extract('tools/approval.py', {'check_all_command_guards'}, ns)
for cwd in ['/workspace/project-a','/workspace/project-b']:
    assert ns['check_all_command_guards']('echo hello', 'ssh', cwd=cwd, task_id='turn')['approved']
results['workspace_review'] = {'policy_workspaces':[x['cwd'] for x in policy_calls], 'human_prompt_count':len(prompts),'grant_keys':sorted(approved_keys)}
assert len(prompts)==1

# The generic Stop merger loses a later veto's fail-on-limit policy.
plugin_api.invoke_hook = lambda *a,**k:[{'action':'continue','message':'first check'}, {'action':'continue','message':'required second check','on_limit':'fail'}]
ns = {'invoke_hook':plugin_api.invoke_hook}
extract('hermes_cli/plugins.py', {'get_pre_turn_stop_continue_message'}, ns)
results['multiple_stop_callbacks'] = ns['get_pre_turn_stop_continue_message'](final_response='draft')
assert results['multiple_stop_callbacks']=='first check'

# Duplicate top-level has_hook definitions are objectively visible in the final module.
mod=ast.parse((ROOT/'hermes_cli/plugins.py').read_text())
results['has_hook_definition_lines']=[n.lineno for n in mod.body if isinstance(n,ast.FunctionDef) and n.name=='has_hook']
assert len(results['has_hook_definition_lines'])==2
print(json.dumps(results,indent=2))
