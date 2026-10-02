# ABOUTME: Runs a staged LifeOS update outside the Hermes gateway process.
# ABOUTME: Verifies native hooks and the restarted gateway before marking an update applied.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import types
from pathlib import Path

if not __package__:
    package = types.ModuleType("lifeos_hook_bridge")
    package.__path__ = [str(Path(__file__).resolve().parent)]
    sys.modules[package.__name__] = package
    __package__ = package.__name__

from .install_source import (LIFEOS_PATCHES, SUPPORTED_LIFEOS_COMMIT,
                             install_lifeos, validate_prepared_lifeos)
from .update_hooks import replace_owned_hooks
from .update_transaction import apply_update, recover_update, restore_update
from .version_drift import changed_paths, create_baseline, load_baseline, save_baseline
from .memory_administration import (mount_environment, job_binding, required, revoke)
from .memory_service import MemoryConfiguration


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_prior_source(baseline: dict, prior_source: Path, installed: Path) -> None:
    if prior_source.is_symlink() or not prior_source.is_dir():
        raise ValueError("The prior LifeOS source is missing")
    if baseline.get("source_root") != str(prior_source.resolve()):
        raise ValueError("VersionDrift baseline belongs to another LifeOS source")
    expected = baseline.get("files", {}).get("hooks/hooks.json")
    prior_hooks = prior_source / "hooks/hooks.json"
    installed_hooks = installed / "hooks/hooks.json"
    if (not expected or prior_hooks.is_symlink() or installed_hooks.is_symlink()
            or not prior_hooks.is_file() or not installed_hooks.is_file()
            or _digest(prior_hooks) != expected or _digest(installed_hooks) != expected):
        raise ValueError("The prior hook source changed since the VersionDrift baseline")
    commit = baseline.get("source_commit")
    if commit:
        result = subprocess.run(["git", "-C", str(prior_source), "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=20)
        if result.returncode or result.stdout.strip() != commit:
            raise ValueError("The prior LifeOS source commit changed")


def check_template_compatibility(prior_source: Path, selected_source: Path) -> None:
    for filename, label in (("CLAUDE.template.md", "CLAUDE template"),
                            ("settings.system.json", "settings template")):
        before = prior_source / filename
        after = selected_source / filename
        if (not before.is_file() or not after.is_file() or before.is_symlink() or after.is_symlink()
                or _digest(before) != _digest(after)):
            raise ValueError(f"LifeOS {label} changed; a reviewed migration is required")


def _write_status(job: Path, state: str, error: str | None = None) -> None:
    target = job / "status.json"
    temporary = job / ".status.json.tmp"
    previous = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
    with temporary.open("w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump({"state": state, **({"unit": previous["unit"]} if "unit" in previous else {}),
                   **({"error": error[:400]} if error else {})}, stream)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)


def _run(command: list[str | Path], *, home: Path, timeout: int = 180, environment=None) -> str:
    result = subprocess.run([str(item) for item in command], cwd=home,
                            env=dict(os.environ, HOME=str(home)) if environment is None else environment, capture_output=True,
                            text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} exited with code {result.returncode}")
    return result.stdout.strip()


def _service(action: str, home: Path) -> str:
    return _run(["systemctl", "--user", action, "hermes-gateway.service"], home=home, timeout=45)


def _gateway_pid(home: Path) -> str:
    result = _run(["systemctl", "--user", "show", "hermes-gateway.service",
                   "-p", "MainPID", "--value"], home=home, timeout=30)
    if not result.isdigit() or int(result) <= 0:
        raise RuntimeError("Hermes gateway has no running process")
    return result


def _check_gateway_launcher(hermes: Path, home: Path, *, require_active: bool = True) -> None:
    if hermes.is_symlink() or not hermes.is_file():
        raise ValueError("Hermes command is missing")
    result = _run(["systemctl", "--user", "show", "hermes-gateway.service",
                   "-p", "ExecStart", "--value"], home=home, timeout=30)
    match = re.search(r"\bpath=([^ ;}]+)", result)
    if match is None or match.group(1) != str(hermes):
        raise ValueError("The gateway service does not run this Hermes command")
    if require_active and _service("is-active", home) != "active":
        raise ValueError("A running Hermes gateway service is required")


def _runtime(request: dict, *, require_active: bool = True, job=None, action='apply'):
    installed = Path(request["installed"])
    hermes_home = Path(request["hermes_home"])
    baseline_path = Path(request["baseline"])
    home = installed.parent
    bun = shutil.which("bun") or str(home / ".local/bin/bun")
    hermes = Path(request["hermes_command"])
    if not Path(bun).is_file():
        raise ValueError("Bun is missing")
    environment = mount_environment(installed, hermes_home, request.get('memory_authorization'),
                                    binding=job_binding(job, request, action) if job is not None else None)
    _check_gateway_launcher(hermes, home, require_active=require_active)
    original_pid = _gateway_pid(home) if require_active else None

    def mount():
        from .mount_transaction import MountTransaction
        MountTransaction(installed, hermes_home, baseline_path).execute(environment, bun, str(hermes),
            binding=job_binding(job, request, action) if job is not None else None)

    def renew(current: Path, selected: Path):
        save_baseline(create_baseline(selected, current), baseline_path, renew=True)

    def verify():
        time.sleep(3)
        if _service("is-active", home) != "active" or _gateway_pid(home) == original_pid:
            raise RuntimeError("Hermes gateway did not restart")
        _run([bun, installed / "LIFEOS/TOOLS/Doctor.ts", "--hooks"], home=home)
        _run([bun, installed / "LIFEOS/HERMES/Mount.ts", "--check"], home=home, environment=environment)
        _run([hermes, "config", "check"], home=home)
        if changed_paths(load_baseline(baseline_path, installed), installed):
            raise RuntimeError("VersionDrift reported changed system files after update")
        selected_hooks = json.loads((installed / "hooks/hooks.json").read_text())["hooks"]
        settings = json.loads((installed / "settings.json").read_text())
        replace_owned_hooks(settings, selected_hooks, selected_hooks)

    def verify_restored():
        time.sleep(3)
        if _service("is-active", home) != "active":
            raise RuntimeError("Hermes gateway did not restart after rollback")
        _run([hermes, "config", "check"], home=home)

    return {"stop": lambda: _service("stop", home),
            "start": lambda: _service("start", home), "mount": mount,
            "renew": renew, "verify": verify, "verify_restored": verify_restored}


def _execute_update_job(job: Path, action: str = "apply") -> dict:
    if job.is_symlink() or not job.is_dir():
        raise ValueError("LifeOS update job is missing")
    request = json.loads((job / "request.json").read_text(encoding="utf-8"))
    installed = Path(request["installed"])
    hermes_home = Path(request["hermes_home"])
    baseline_path = Path(request["baseline"])
    candidate = Path(request["candidate"])
    prior_source = Path(request["prior_source"])
    snapshot = job / "snapshot"
    home = installed.parent
    runtime = _runtime(request, require_active=action == "apply", job=job, action=action)
    if action == "restore":
        _write_status(job, "restoring")
        result = restore_update(snapshot, stop=runtime["stop"], start=runtime["start"],
                                verify=runtime["verify_restored"])
        _write_status(job, result["state"])
        return result
    if action == "recover":
        _write_status(job, "recovering")
        from .mount_transaction import MountTransaction
        transaction = MountTransaction(installed, hermes_home, baseline_path)
        if transaction.status()['recovery_required']:
            transaction.recover()
        result = recover_update(snapshot, stop=runtime["stop"], start=runtime["start"],
                                verify=runtime["verify_restored"])
        _write_status(job, result["state"])
        return result
    if action != "apply":
        raise ValueError("Unknown LifeOS update action")

    _write_status(job, "preparing")
    baseline = load_baseline(baseline_path, installed)
    check_prior_source(baseline, prior_source, installed)
    manifest = validate_prepared_lifeos(candidate)
    check_template_compatibility(prior_source, candidate / "LifeOS/install")
    if manifest["upstream_commit"] != request["candidate_commit"]:
        raise ValueError("Prepared LifeOS candidate changed after request")
    reference_home = job / "reference-home"
    reference_home.mkdir(mode=0o700)
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = str(reference_home)
    try:
        bun = shutil.which("bun") or str(home / ".local/bin/bun")
        install_lifeos(candidate, reference_home / ".claude", reference_home / "failed",
                       bun, SUPPORTED_LIFEOS_COMMIT, Path(__file__).parent / "patches", LIFEOS_PATCHES)
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home
    validate_prepared_lifeos(candidate)
    _write_status(job, "applying")
    result = apply_update(installed, hermes_home, prior_source,
                          candidate / "LifeOS/install", reference_home / ".claude",
                          baseline_path, snapshot, **runtime)
    _write_status(job, result["state"])
    shutil.rmtree(reference_home)
    return result


def run_update_job(job: Path, action: str = 'apply') -> dict:
    if job.is_symlink() or not job.is_dir():
        raise ValueError('LifeOS update job is missing')
    request = json.loads((job / 'request.json').read_text(encoding='utf-8'))
    installed, profile = Path(request['installed']), Path(request['hermes_home'])
    managed = required(installed, profile)
    if managed:
        mount_environment(installed, profile, request.get('memory_authorization'),
                          binding=job_binding(job, request, action))
    try:
        return _execute_update_job(job, action)
    finally:
        if managed:
            revoke(MemoryConfiguration(profile / 'lifeos-memory.json'), request['memory_authorization'])


def _main() -> int:
    parser = argparse.ArgumentParser(description="Run a prepared LifeOS update")
    parser.add_argument("job", type=Path)
    parser.add_argument("--action", choices=("apply", "restore", "recover"), default="apply")
    args = parser.parse_args()
    try:
        result = run_update_job(args.job, args.action)
    except Exception as error:
        try:
            manifest = args.job / "snapshot/manifest.json"
            state = json.loads(manifest.read_text())["state"] if manifest.is_file() else "failed"
            _write_status(args.job, state if state in {"rolled_back", "rollback_failed"} else "failed", str(error))
        except (OSError, ValueError, KeyError):
            pass
        print(f"LifeOS update {args.action} failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"action": args.action, "state": result["state"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
