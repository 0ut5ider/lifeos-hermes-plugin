# ABOUTME: Drives in-place preparation and actions through the installed release manager for qualification.
# ABOUTME: Uses the loopback release server instead of GitHub, and issues the owner grant as the dashboard does.
import importlib, json, sys, types
from pathlib import Path

directory = Path.home() / ".hermes/plugins/lifeos-release-manager"
namespace = types.ModuleType("lrm")
namespace.__path__ = [str(directory)]
sys.modules["lrm"] = namespace
cli = importlib.import_module("lrm.cli")
# Removal deletes the installed manager directory while this driver waits, so load every module first.
for module in sorted(directory.glob("*.py")):
    if module.stem not in {"__init__", "memory_workflow_worker", "removal_recovery", "removal_bootstrap", "dependency_plan"}:
        importlib.import_module("lrm." + module.stem)
catalog = importlib.import_module("lrm.release_catalog")
profile = Path.home() / ".hermes"
action = sys.argv[1]
OWNER = "dashboard:basic:owner"
STATE = Path("/tmp/e2e-memory-state.json")


def _bridge():
    stage = importlib.import_module("lrm.release_stage")
    return stage.load_bridge(profile / "plugins/lifeos-hook-bridge")


def _preferences():
    bridge = _bridge()
    preferences = bridge.memory_module("memory_preferences")
    installed = bridge.memory_module("lifeos_installation").selection(profile).installed
    return preferences.MemoryPreferences(profile / "lifeos-memory.json", installed, Path(sys.executable),
                                         profile / "plugins/lifeos-hook-bridge/memory_mcp.py")


def _remember(**values):
    current = json.loads(STATE.read_text()) if STATE.exists() else {}
    current.update(values)
    STATE.write_text(json.dumps(current, indent=2))
    return current


def claim():
    return _preferences().claim(account=OWNER)


def export():
    preferences = _preferences()
    review = preferences.preview_export(account=OWNER)
    saved = preferences.prepare_export({"signature": review["signature"]}, account=OWNER)
    decisions = [{"id": item["id"], "action": "export", "required": True, "file": "MEMORY.md",
                  "content": item["content"]} for item in review["items"]]
    request = {"identifier": saved["identifier"], "signature": saved["signature"]}
    plan = preferences.export_action("plan", {**request, "decisions": decisions}, account=OWNER)
    result = preferences.export_action("apply", {**request, "plan_signature": plan["signature"]}, account=OWNER)
    _remember(export_identifier=saved["identifier"], export_signature=saved["signature"],
              export_plan_signature=plan["signature"])
    return {"items": len(review["items"]), "plan": plan, "result": result}


def _workflow():
    return importlib.import_module("lrm.memory_workflow")


def _wait(identifier, accepted):
    import time
    workflow = _workflow()
    for _ in range(400):
        for operation in workflow.status(profile, owner=OWNER)["operations"]:
            if operation["identifier"] == identifier and operation["state"] in accepted:
                return operation
        time.sleep(3)
    raise SystemExit("The memory workflow did not reach " + ", ".join(sorted(accepted)))


FINAL = {"ready", "verified", "interrupted", "rolled_back", "cancelled", "verification_required", "configured"}


def provider_return():
    state = json.loads(STATE.read_text())
    workflow = _workflow()
    queued = workflow.queue(profile, {"kind": "return", "identifier": state["export_identifier"],
                                      "signature": state["export_signature"],
                                      "plan_signature": state["export_plan_signature"],
                                      "prompt": "You are Hermes. Use the selected built-in memory."},
                            owner=OWNER, launch=workflow.launch)
    prepared = _wait(queued["identifier"], FINAL)
    if prepared["state"] != "ready":
        return prepared
    workflow.admit(profile, queued["identifier"], "apply", prepared["review"]["signature"], owner=OWNER,
                   launch=workflow.launch)
    result = _wait(queued["identifier"], FINAL - {"ready"})
    _remember(return_identifier=queued["identifier"], return_signature=prepared["review"]["signature"])
    return result


def removal_prepare():
    state = json.loads(STATE.read_text())
    workflow = _workflow()
    queued = workflow.queue(profile, {"kind": "removal", "identifier": state["return_identifier"],
                                      "signature": state["return_signature"], "disable_discord": True},
                            owner=OWNER, launch=workflow.launch)
    # Return at once: removal refuses while any process with the Hermes source on its path is running,
    # so the shell waits for the result by reading the workflow status file.
    _remember(removal_identifier=queued["identifier"])
    return queued


def removal_admit(action="apply"):
    state = json.loads(STATE.read_text())
    workflow = _workflow()
    reviewed = next(item for item in workflow.status(profile, owner=OWNER)["operations"]
                    if item["identifier"] == state["removal_identifier"])
    return workflow.admit(profile, state["removal_identifier"], action, reviewed["review"]["signature"], owner=OWNER,
                          launch=workflow.launch)


def workflows():
    return _workflow().status(profile, owner=OWNER)


MEMORY_ACTIONS = {"claim": claim, "export": export, "return": provider_return, "removal-prepare": removal_prepare,
                  "removal-admit": removal_admit, "workflows": workflows}
if action == "prepare":
    origin = "http://127.0.0.1:8765"
    value = cli.prepare(profile, name="Owner", assistant="Hermes", intent=sys.argv[2],
                        catalog=catalog.ReleaseCatalog(api_origin=origin, asset_origin=origin))
elif action == "status":
    value = cli.status(profile, *sys.argv[2:3])
elif action in {"apply", "recover", "restore"}:
    worker = importlib.import_module("lrm.release_worker")
    job, request = cli.operation(profile, sys.argv[2])
    if action == "apply":
        selected, plan = worker.review_operation(job, request)
    else:
        plan = worker.validate_plan(job, request)
        selected = {"installed": Path(request["installed"]), "current": worker.recovery_bridge(job, profile)}
    administration = selected["current"].memory_administration()
    authorization = None
    if plan["native_mount_required"] and administration.required(selected["installed"], profile):
        configuration = administration.MemoryConfiguration(profile / "lifeos-memory.json")
        authorization = administration.issue(configuration, "dashboard:basic:owner", ttl=3600,
                                             binding=administration.job_binding(job, request, action))
    value = cli.launch(profile, sys.argv[2], action, authorization=authorization)
elif action in MEMORY_ACTIONS:
    value = MEMORY_ACTIONS[action](*sys.argv[2:])
elif action == "crash":
    # Admit like the launcher, then run the worker in this process and exit hard at the nth checkpoint hit.
    import os
    worker = importlib.import_module("lrm.release_worker")
    identifier, point, count = sys.argv[2], sys.argv[3], int(sys.argv[4])
    job, request = cli.operation(profile, identifier)
    selected, plan = worker.review_operation(job, request)
    administration = selected["current"].memory_administration()
    authorization = None
    if plan["native_mount_required"] and administration.required(selected["installed"], profile):
        configuration = administration.MemoryConfiguration(profile / "lifeos-memory.json")
        authorization = administration.issue(configuration, "dashboard:basic:owner", ttl=3600,
                                             binding=administration.job_binding(job, request, "apply"))
    worker.admit_operation(job, request, "apply", authorization=authorization)
    hits = {"count": 0}
    def checkpoint(name):
        if name == point:
            hits["count"] += 1
            if hits["count"] == count:
                os._exit(9)
    value = worker.execute(job, "apply", checkpoint=checkpoint)
else:
    raise SystemExit("Choose prepare, status, apply, recover, restore, crash, or a memory action")
print(json.dumps(value, indent=2))
