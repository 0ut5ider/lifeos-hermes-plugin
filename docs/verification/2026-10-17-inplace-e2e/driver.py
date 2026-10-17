# ABOUTME: Drives in-place preparation and actions through the installed release manager for qualification.
# ABOUTME: Uses the loopback release server instead of GitHub, and issues the owner grant as the dashboard does.
import importlib, json, sys, types
from pathlib import Path

directory = Path.home() / ".hermes/plugins/lifeos-release-manager"
namespace = types.ModuleType("lrm")
namespace.__path__ = [str(directory)]
sys.modules["lrm"] = namespace
cli = importlib.import_module("lrm.cli")
catalog = importlib.import_module("lrm.release_catalog")
profile = Path.home() / ".hermes"
action = sys.argv[1]
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
    raise SystemExit("Choose prepare, status, apply, recover, restore, or crash")
print(json.dumps(value, indent=2))
