# ABOUTME: Installs or removes account-private development capture startup files.
# ABOUTME: Pins inspected runtime sources and retains the configuration for rollback.

import argparse
import datetime
import hashlib
import json
import os
import site
import sys
import subprocess
from pathlib import Path


HOST_FILES = ("hermes_cli/plugins.py", "agent/tool_executor.py", "agent/turn_context.py",
              "agent/turn_stop_gates.py", "plugins/platforms/discord/adapter.py",
              "gateway/run_agent_cache.py")
PLUGIN_FILES = ("__init__.py", "bridge.py", "remote_hooks.py", "bin/hook_runner.py")


def install(plugin_root, host_root, root, configuration, site_directory):
    plugin_root, host_root = Path(plugin_root).resolve(), Path(host_root).resolve()
    sources = [plugin_root / name for name in PLUGIN_FILES] + [host_root / name for name in HOST_FILES]
    fingerprints = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    configuration = Path(configuration)
    if configuration.resolve() != (Path.home() / ".config/lifeos-development-capture/config.json").resolve():
        raise ValueError("Installation requires the account's standard private configuration path")
    directory = Path(site_directory)
    startup = directory / "lifeos_development_capture.pth"
    overlay = Path(__file__).resolve().parents[1]
    text = f"import sys; sys.path.insert(0, {str(overlay)!r}); from hook_capture.bootstrap import start; start({str(configuration)!r})\n"
    if startup.exists() and startup.read_text() != text:
        raise ValueError("An unrelated startup file already exists")
    configuration.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise PermissionError("Capture root must be private and owned by this account")
    data = {"enabled": True, "root": str(root.resolve()),
            "run_id": datetime.datetime.now(datetime.timezone.utc).strftime("development-%Y%m%dT%H%M%SZ"),
            "plugin_root": str(plugin_root), "host_root": str(host_root), "fingerprints": fingerprints,
            "credential_files": [str(Path.home() / ".hermes/.env")], "interpreter": sys.executable}
    data["capture_sources"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in Path(__file__).parent.glob("*.py")}
    revision = subprocess.run(["git", "-C", str(host_root), "rev-parse", "HEAD"], capture_output=True, text=True)
    data["hermes_revision"] = revision.stdout.strip() if revision.returncode == 0 else None
    if configuration.exists():
        previous = json.loads(configuration.read_text())
        data["run_id"] = previous["run_id"]
        backup = configuration.with_name(configuration.name + ".before-install")
        if not backup.exists():
            backup.write_bytes(configuration.read_bytes())
            backup.chmod(0o600)
    temporary = configuration.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream, indent=2)
    os.replace(temporary, configuration)
    # Detached systemd processes use the same private configuration as the parent recorder.
    startup.write_text(text)
    startup.chmod(0o600)
    return {"config": str(configuration), "startup": str(startup), "run_id": data["run_id"], "fingerprints": len(fingerprints)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("install", "disable", "remove"))
    parser.add_argument("--plugin-root", type=Path)
    parser.add_argument("--host-root", type=Path)
    parser.add_argument("--root", type=Path, default=Path.home() / ".local/state/lifeos-development-capture")
    parser.add_argument("--configuration", type=Path, default=Path.home() / ".config/lifeos-development-capture/config.json")
    parser.add_argument("--site-directory", type=Path, default=Path(site.getsitepackages()[0]))
    args = parser.parse_args()
    if args.action == "install":
        if not args.plugin_root or not args.host_root:
            parser.error("install requires --plugin-root and --host-root")
        print(json.dumps(install(args.plugin_root, args.host_root, args.root, args.configuration, args.site_directory)))
    else:
        data = json.loads(args.configuration.read_text())
        data["enabled"] = False
        args.configuration.write_text(json.dumps(data, indent=2))
        if args.action == "remove":
            (args.site_directory / "lifeos_development_capture.pth").unlink(missing_ok=True)
        print(json.dumps({"enabled": False, "raw_evidence_retained": True}))


if __name__ == "__main__":
    main()
