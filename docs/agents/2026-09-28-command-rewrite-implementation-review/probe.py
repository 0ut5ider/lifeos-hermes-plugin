import ast, json, sys, types
from pathlib import Path
source = Path("tools/approval.py").read_text()
fn = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "_plugin_command_decision")
module = ast.Module(body=[fn], type_ignores=[])
plugin = types.ModuleType("hermes_cli.plugins")
sys.modules["hermes_cli.plugins"] = plugin
namespace = {"get_current_session_key": lambda: "review-probe"}
exec(compile(module, "tools/approval.py", "exec"), namespace)
rows = []
for decisions in [
    [{"action":"review"}, {"action":"rewrite", "command":"printf REPLACED"}],
    [{"action":"review"}, {"action":"rewrite", "command":""}],
    [{"action":"review"}, {"action":"rewrite", "command":"pwd"}, {"action":"rewrite", "command":"date"}],
]:
    plugin.invoke_hook = lambda *a, **k: decisions
    rows.append({"input": decisions, "result": namespace["_plugin_command_decision"]("printf ORIGINAL", "", "")})
source = Path("tools/schema_sanitizer.py").read_text()
fn = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "unrename_tool_args")
ns = {"Any": object, "_rename_property_keys": lambda props, path: {}}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "tools/schema_sanitizer.py", "exec"), ns)
outer = {"command":"printf ORIGINAL"}
inner = ns["unrename_tool_args"]({"properties":{"command":{"type":"string"}}}, outer)
inner["command"] = "printf REPLACED"
rows.append({"audit_original_args": outer, "registry_mutated_args": inner, "same_object": outer is inner})
print(json.dumps(rows, indent=2))
