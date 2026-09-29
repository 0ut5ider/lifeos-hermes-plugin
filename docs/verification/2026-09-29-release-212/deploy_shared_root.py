# ABOUTME: Applies the reviewed patch bundle to the shared-root .212 test installation.
# ABOUTME: Uses private snapshots and restores managed files if verification fails.

import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
if HOME != Path("/home/lifeos-hermes") or os.getuid() != 1004:
    raise SystemExit("This release script is restricted to lifeos-hermes on the .212 test server")
RELEASE = HOME / "workspace/releases/20260929-patch-footprint-e762ac6"
PACKAGE = RELEASE / "plugin-source"
PROFILE = HOME / ".hermes"
HERMES = HOME / "workspace/hermes-agent"
PLUGIN = PROFILE / "plugins/lifeos-hook-bridge"
PRIOR_SOURCE = HOME / "workspace/LifeOS/LifeOS/install"
SOURCE = RELEASE / "prepared/lifeos/LifeOS/install"
CANDIDATE = RELEASE / "prepared/hermes"
BASELINE = HOME / ".local/state/lifeos-hook-bridge/version-drift-baseline.json"
BACKUP = RELEASE / "snapshot"
COMMAND = HERMES / ".hermes/bin/hermes"
BUN = HOME / ".bun/bin/bun"
UNITS = ["hermes-dashboard.service", "hermes-gateway.service", "com.lifeos.pulse.service"]
os.environ.update(HERMES_HOME=str(PROFILE), XDG_RUNTIME_DIR="/run/user/1004",
                  DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1004/bus", TMPDIR=str(RELEASE))
os.environ["PATH"] = ":".join([str(HOME / ".bun/bin"), str(HOME / ".local/bin"), str(COMMAND.parent), os.environ.get("PATH", "")])
sys.path.insert(0, str(PACKAGE))
from scripts.release_transaction import _copy_tree, _sync_tree, _digest_tree, _files, _digest_file
from scripts.system_overlay_snapshot import source_files, take_snapshot, verify_overlay, restore_snapshot
from lifeos_hook_bridge.native_capabilities import supports_task_count
from lifeos_hook_bridge.update_hooks import replace_owned_hooks
from lifeos_hook_bridge.version_drift import load_baseline, changed_paths, create_baseline, save_baseline


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = RELEASE / name
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def run(argv, *, input=None, timeout=300, extra=None):
    result = subprocess.run([str(x) for x in argv], cwd=HOME, input=input,
                            env=dict(os.environ, **(extra or {})), text=True,
                            capture_output=True, timeout=timeout)
    if result.returncode:
        print(result.stdout, result.stderr, flush=True)
        raise RuntimeError(f"{Path(argv[0]).name} returned {result.returncode}")
    return result.stdout.strip()


def git(*args):
    return run(["git", "-C", HERMES, *args])


def service(unit, action):
    return run(["systemctl", "--user", action, unit], timeout=120)


def user_hashes():
    found = {}
    for name in ("LIFEOS/USER", "LIFEOS/MEMORY", "USER.md", "MEMORY.md"):
        path = PROFILE / name
        files = path.rglob("*") if path.is_dir() else [path]
        for file in files:
            if file.is_file():
                found[str(file.relative_to(PROFILE))] = sha(file)
    return found


def prepare():
    assert not git("status", "--porcelain"), "Running Hermes source has local changes"
    assert not changed_paths(load_baseline(BASELINE, PROFILE), PROFILE), "LifeOS has unmanaged drift"
    current = json.loads((PROFILE / "settings.json").read_text())
    selected, counts = replace_owned_hooks(current,
        json.loads((PRIOR_SOURCE / "hooks/hooks.json").read_text())["hooks"],
        json.loads((SOURCE / "hooks/hooks.json").read_text())["hooks"])
    assert counts == {"old_hooks": 74, "new_hooks": 74, "foreign_hooks": 0}
    assert current == selected, "Hook registrations need migration"
    for name in ("uv.lock", "pyproject.toml", "pm/lock.json"):
        assert sha(HERMES / name) == sha(CANDIDATE / name), f"Hermes dependency change: {name}"
    import yaml
    assert yaml.safe_load((PLUGIN / "plugin.yaml").read_text())["python_dependencies"] == yaml.safe_load((PACKAGE / "lifeos_hook_bridge/plugin.yaml").read_text())["python_dependencies"]
    for path in SOURCE.rglob("*"):
        if path.is_file() and path.name in {"package.json", "bun.lock", "bun.lockb"}:
            before = PRIOR_SOURCE / path.relative_to(SOURCE)
            assert before.is_file() and sha(before) == sha(path), "LifeOS dependencies need migration"
    for name in ("CLAUDE.template.md", "settings.system.json", "LIFEOS/LIFEOS_SYSTEM_PROMPT.md"):
        assert sha(SOURCE / name) == sha(PRIOR_SOURCE / name), "Generated identity files need migration"
    payload = RELEASE / "overlay/LifeOS/install"
    for name in ("hooks", "skills", "agents", "LIFEOS/TOOLS", "LIFEOS/DOCUMENTATION", "LIFEOS/ALGORITHM", "LIFEOS/RULES", "LIFEOS/PULSE"):
        (payload / name).mkdir(parents=True, exist_ok=True)
    changes = []
    for source, relative in source_files(SOURCE):
        prior = PRIOR_SOURCE / source.relative_to(SOURCE)
        if prior.is_file() and sha(prior) == sha(source):
            continue
        destination = payload / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        changes.append(str(relative))
    version = payload / "LIFEOS/VERSION"
    shutil.copy2(SOURCE / "LIFEOS/VERSION", version)
    run(["git", "-C", SOURCE, "add", "-N", "hooks/lifeos-bridge-capabilities.json"])
    record = {"revision": run(["git", "-C", PACKAGE, "rev-parse", "HEAD"]),
              "hermes_release_branch": "feature/lifeos-release-20260929-" + str(int(time.time())),
              "hermes_before": git("rev-parse", "HEAD"), "hermes_branch_before": git("branch", "--show-current"),
              "hermes_digest_before": _digest_tree(HERMES), "hermes_digest_after": _digest_tree(CANDIDATE),
              "plugin_digest_after": _digest_tree(PACKAGE / "lifeos_hook_bridge"),
              "config_hash": sha(PROFILE / "config.yaml"), "env_hash": sha(PROFILE / ".env"),
              "settings_hash": sha(PROFILE / "settings.json"), "baseline_hash": sha(BASELINE),
              "identity_hashes": {name: (sha(PROFILE / name) if (PROFILE / name).is_file() else None) for name in ["SOUL.md", "CLAUDE.md", "LIFEOS/LIFEOS_SYSTEM_PROMPT.md"]},
              "hooks": counts, "lifeos_changes": sorted(changes), "gateway_pid_before": run(["systemctl", "--user", "show", "hermes-gateway.service", "-p", "MainPID", "--value"])}
    save("preflight.json", record)
    print(json.dumps({"state": "prepared", "revision": record["revision"], "lifeos_changes": sorted(changes), "hooks": counts}), flush=True)


def verify(record):
    expected = {str(relative): _digest_file(path) for relative, path in _files(CANDIDATE)}
    actual = {str(relative): _digest_file(path) for relative, path in _files(HERMES)}
    missing = sorted(expected.keys() - actual.keys())
    modified = sorted(name for name in expected.keys() & actual.keys() if expected[name] != actual[name])
    generated = sorted(actual.keys() - expected.keys())
    invalid = [name for name in generated if subprocess.run(["git", "-C", str(HERMES), "check-ignore", "-q", "--", name]).returncode]
    save("source-check.json", {"missing": missing, "modified": modified, "runtime_paths": generated, "unexpected": invalid})
    assert not missing and not modified and not invalid, "Running Hermes source differs from the staged source"
    assert not git("status", "--porcelain"), "Hermes source is dirty after service restart"
    assert _digest_tree(PLUGIN) == record["plugin_digest_after"]
    assert sha(PROFILE / "config.yaml") == record["config_hash"]
    assert sha(PROFILE / ".env") == record["env_hash"]
    for name, digest in record["identity_hashes"].items():
        assert (sha(PROFILE / name) if (PROFILE / name).is_file() else None) == digest, f"Identity changed: {name}"
    assert supports_task_count(PROFILE), "Native task capabilities failed verification"
    baseline = load_baseline(BASELINE, PROFILE)
    assert not changed_paths(baseline, PROFILE)
    for unit in UNITS:
        assert service(unit, "is-active") == "active", unit
    pid = run(["systemctl", "--user", "show", "hermes-gateway.service", "-p", "MainPID", "--value"])
    assert pid != record["gateway_pid_before"] and int(pid) > 0
    print(run([COMMAND, "config", "check"]), flush=True)
    print(run([COMMAND, "plugins", "validate", PLUGIN]), flush=True)
    print(run([BUN, PROFILE / "LIFEOS/HERMES/Mount.ts", "--check"]), flush=True)
    print(run([COMMAND, "lifeos-probe", "--check-main-rung", "fable"]), flush=True)
    result = json.loads(run([COMMAND, "lifeos-infer", "--print", "--model", "flashnext-w4a16-fp8ple", "--effort", "low", "--output-format", "json", "--system-prompt", "Return exactly RELEASE-212-READY."], input="Return exactly RELEASE-212-READY.", extra={"LIFEOS_CHILD_PROVIDER": "custom"}, timeout=240))
    assert result.get("is_error") is False and result.get("result", "").strip() == "RELEASE-212-READY", "Private model smoke test failed"
    print("Private model: RELEASE-212-READY", flush=True)
    return {"gateway_pid": pid, "baseline_files": len(baseline["files"]), "baseline_changed": 0,
            "capability_verified": True, "model_smoke": "RELEASE-212-READY", "services": {unit: "active" for unit in UNITS}}


def apply():
    record = json.loads((RELEASE / "preflight.json").read_text())
    assert not BACKUP.exists()
    assert _digest_tree(HERMES) == record["hermes_digest_before"]
    assert sha(PROFILE / "config.yaml") == record["config_hash"]
    assert sha(PROFILE / ".env") == record["env_hash"]
    assert sha(PROFILE / "settings.json") == record["settings_hash"]
    assert sha(BASELINE) == record["baseline_hash"]
    changed = False
    try:
        save("status.json", {"state": "stopping"})
        for unit in UNITS:
            service(unit, "stop")
        assert not changed_paths(load_baseline(BASELINE, PROFILE), PROFILE), "LifeOS changed since preflight"
        BACKUP.mkdir(mode=0o700)
        run(["cp", "-a", "--reflink=auto", PROFILE, BACKUP / "profile-before"])
        _copy_tree(HERMES, BACKUP / "hermes-before")
        shutil.copy2(BASELINE, BACKUP / "baseline-before.json")
        before = user_hashes()
        save("user-hashes-before.json", before)
        take_snapshot(RELEASE / "overlay/LifeOS/install", PROFILE, BACKUP / "native")
        save("status.json", {"state": "applying"})
        changed = True
        git("switch", "-c", record["hermes_release_branch"])
        _sync_tree(CANDIDATE, HERMES)
        _sync_tree(PACKAGE / "lifeos_hook_bridge", PLUGIN)
        assert _digest_tree(HERMES) == record["hermes_digest_after"], "Hermes copy differs before startup"
        for name in (".env", "install-stamp.json", ".hermes-bootstrap-complete"):
            prior = BACKUP / "hermes-before" / name
            if prior.is_file():
                assert subprocess.run(["git", "-C", str(HERMES), "check-ignore", "-q", "--", name]).returncode == 0
                shutil.copy2(prior, HERMES / name)
        for tree in (HERMES, PLUGIN):
            for parent, directories, files in os.walk(tree):
                directories[:] = [name for name in directories if name not in {"node_modules", ".hermes", ".venv", ".git"}]
                if "__pycache__" in directories:
                    shutil.rmtree(Path(parent) / "__pycache__")
                    directories.remove("__pycache__")
        run([BUN, RELEASE / "prepared/lifeos/LifeOS/Tools/OverlaySystem.ts", "--config-root", PROFILE, "--skill-root", RELEASE / "overlay/LifeOS", "--apply"])
        verify_overlay(BACKUP / "native", PROFILE)
        assert user_hashes() == before, "Existing LifeOS user data changed during apply"
        save_baseline(create_baseline(SOURCE, PROFILE), BASELINE, renew=True)
        metadata_path = PROFILE / "plugins/.install-metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["lifeos-hook-bridge"] = {"pinned": True, "revision": record["revision"], "source": "https://github.com/0ut5ider/lifeos-hermes-plugin.git#lifeos_hook_bridge"}
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
        tracked = git("diff", "--name-only", "HEAD").splitlines()
        new = git("ls-files", "--others", "--exclude-standard").splitlines()
        names = sorted(set(tracked + [name for name in new if (CANDIDATE / name).is_file()]))
        git("add", "--", *names)
        git("-c", "user.name=LifeOS Release", "-c", "user.email=lifeos-release@localhost", "commit", "-m", "fix(plugins): apply reviewed LifeOS bridge release")
        assert not git("status", "--porcelain"), "Hermes source is dirty after release commit"
        for unit in reversed(UNITS):
            service(unit, "start")
        time.sleep(5)
        result = verify(record)
        result.update(state="applied", plugin_revision=record["revision"], hermes_revision=git("rev-parse", "HEAD"),
                      lifeos_base="5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c", hooks=record["hooks"],
                      existing_user_data_unchanged_at_apply=True, lifeos_changes=record["lifeos_changes"])
        save("result.json", result)
        save("status.json", {"state": "applied"})
        print(json.dumps(result, indent=2), flush=True)
    except BaseException as error:
        for unit in UNITS:
            service(unit, "stop")
        if changed:
            _sync_tree(BACKUP / "hermes-before", HERMES)
            git("reset", "--mixed", record["hermes_before"])
            git("switch", record["hermes_branch_before"])
            _sync_tree(BACKUP / "profile-before/plugins/lifeos-hook-bridge", PLUGIN)
            restore_snapshot(BACKUP / "native", PROFILE, preserve_divergent=True)
            shutil.copy2(BACKUP / "baseline-before.json", BASELINE)
            shutil.copy2(BACKUP / "profile-before/plugins/.install-metadata.json", PROFILE / "plugins/.install-metadata.json")
        for unit in reversed(UNITS):
            service(unit, "start")
        save("status.json", {"state": "rolled_back" if changed else "failed_before_apply", "error": str(error)[:500]})
        raise



def restore():
    record = json.loads((RELEASE / "preflight.json").read_text())
    result = json.loads((RELEASE / "result.json").read_text())
    assert json.loads((RELEASE / "status.json").read_text())["state"] == "applied"
    assert git("rev-parse", "HEAD") == result["hermes_revision"]
    assert not git("status", "--porcelain"), "Hermes source has changes after the release"
    assert sha(PROFILE / "settings.json") == record["settings_hash"], "Hook settings changed after the release"
    assert _digest_tree(BACKUP / "hermes-before") == record["hermes_digest_before"]
    for unit in UNITS:
        service(unit, "stop")
    try:
        _sync_tree(BACKUP / "hermes-before", HERMES)
        git("reset", "--mixed", record["hermes_before"])
        git("switch", record["hermes_branch_before"])
        _sync_tree(BACKUP / "profile-before/plugins/lifeos-hook-bridge", PLUGIN)
        restore_snapshot(BACKUP / "native", PROFILE, preserve_divergent=True)
        shutil.copy2(BACKUP / "baseline-before.json", BASELINE)
        shutil.copy2(BACKUP / "profile-before/plugins/.install-metadata.json", PROFILE / "plugins/.install-metadata.json")
        assert _digest_tree(HERMES) == record["hermes_digest_before"]
        assert not git("status", "--porcelain")
    except BaseException as error:
        save("status.json", {"state": "restore_failed", "error": str(error)[:500]})
        raise
    finally:
        for unit in reversed(UNITS):
            service(unit, "start")
    assert all(service(unit, "is-active") == "active" for unit in UNITS)
    save("status.json", {"state": "restored", "hermes_revision": record["hermes_before"]})
    print("Prior code, native system files, metadata, and baseline restored; services active", flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    elif sys.argv[1:] == ["apply"]:
        with (RELEASE / "apply.log").open("w") as output:
            sys.stdout = sys.stderr = output
            try:
                apply()
            except BaseException:
                import traceback
                traceback.print_exc()
                (RELEASE / "apply.done").write_text("1\n")
                raise
            else:
                (RELEASE / "apply.done").write_text("0\n")
    elif sys.argv[1:] == ["restore"]:
        restore()
    else:
        raise SystemExit("Specify prepare, apply, or restore")
