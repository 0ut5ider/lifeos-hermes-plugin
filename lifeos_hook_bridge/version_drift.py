# ABOUTME: Tracks installed LifeOS system-file drift in plugin-owned state.
# ABOUTME: Answers the native VersionDrift hook's fixed Git queries without a home repository.

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


CORE_PATHS = (
    "hooks/", "LIFEOS/ALGORITHM/", "skills/", "settings.json", "CLAUDE.md",
    "LIFEOS/LIFEOS_SYSTEM_PROMPT.md", "LIFEOS/TOOLS/", "agents/", "commands/",
    "LIFEOS/PULSE/", "LIFEOS/ATLAS/", "test/", "LIFEOS/DOCUMENTATION/",
)
SKIP_PARTS = frozenset({
    ".git", ".cache", ".venv", "venv", "node_modules", "__pycache__",
    "dist", "build", ".next", ".bun", "coverage",
})
NEW_FILE_SUFFIXES = frozenset({
    ".ts", ".tsx", ".js", ".mjs", ".cjs", ".py", ".sh", ".md",
    ".json", ".yaml", ".yml", ".toml", ".txt",
})
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")


def default_baseline_path() -> Path:
    return Path.home() / ".local" / "state" / "lifeos-hook-bridge" / "version-drift-baseline.json"


def adapter_error_path(baseline_path: Path) -> Path:
    return Path(baseline_path).with_name("version-drift-error.json")


def record_adapter_error(baseline_path: Path, message: str) -> None:
    destination = adapter_error_path(baseline_path)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                     prefix=".version-drift-error-", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump({"time": int(time.time()), "message": message[:400]}, stream)
        stream.write("\n")
    try:
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _eligible(path: str) -> bool:
    parts = Path(path).parts
    if not parts or Path(path).is_absolute() or any(
        part in SKIP_PARTS or part in {".", ".."} or part.startswith(".") for part in parts
    ):
        return False
    return any(path.startswith(core) if core.endswith("/") else path == core for core in CORE_PATHS)


def _installed_file(root: Path, name: str) -> Path | None:
    if not _eligible(name):
        return None
    path = root / name
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        return None
    return path


def _digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _git(source: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()


def create_baseline(source: Path, installed: Path) -> dict[str, Any]:
    source = Path(source).resolve()
    installed = Path(installed).resolve()
    source_version = (source / "LIFEOS/VERSION").read_text().strip()
    installed_version = (installed / "LIFEOS/VERSION").read_text().strip()
    if not VERSION.fullmatch(installed_version) or source_version != installed_version:
        raise ValueError("Source and installed LifeOS versions must match a semantic version")
    prefix = _git(source, "rev-parse", "--show-prefix")
    commit = _git(source, "rev-parse", "HEAD")
    tracked = subprocess.check_output(
        ["git", "-C", str(source), "ls-files", "-z", "--full-name", "--", *CORE_PATHS],
    ).decode("utf-8").split("\0")
    files = {}
    for item in tracked:
        if not item or not item.startswith(prefix):
            continue
        name = item[len(prefix):]
        path = _installed_file(installed, name)
        if path is not None:
            files[name] = _digest(path)
    if not files:
        raise ValueError("No tracked LifeOS system files are installed")
    return {
        "schema": 1,
        "version": installed_version,
        "created_at": int(time.time()),
        "source_commit": commit,
        "installed_root": str(installed),
        "files": dict(sorted(files.items())),
    }


def baseline_fingerprint(baseline: dict[str, Any]) -> str:
    reviewed = {key: baseline[key] for key in ("version", "source_commit", "installed_root", "files")}
    return hashlib.sha256(json.dumps(reviewed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def save_baseline(baseline: dict[str, Any], path: Path, renew: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".version-drift-", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(baseline, stream, sort_keys=True, indent=2)
        stream.write("\n")
    try:
        os.chmod(temporary, 0o600)
        if renew:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_baseline(path: Path, installed: Path) -> dict[str, Any]:
    baseline = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(baseline, dict) or baseline.get("schema") != 1:
        raise ValueError("Unsupported VersionDrift baseline schema")
    if not VERSION.fullmatch(str(baseline.get("version", ""))):
        raise ValueError("Invalid VersionDrift baseline version")
    if baseline.get("installed_root") != str(Path(installed).resolve()):
        raise ValueError("VersionDrift baseline belongs to another installation")
    if not isinstance(baseline.get("created_at"), int) or baseline["created_at"] <= 0:
        raise ValueError("Invalid VersionDrift baseline timestamp")
    files = baseline.get("files")
    if not isinstance(files, dict) or not files or any(
        not isinstance(name, str) or not _eligible(name) or not isinstance(digest, str)
        or not HASH.fullmatch(digest) for name, digest in files.items()
    ):
        raise ValueError("Invalid VersionDrift baseline file list")
    return baseline


def _new_system_files(installed: Path, baseline_files: dict[str, str]):
    owned_skills = {
        Path(name).parts[1] for name in baseline_files
        if name.startswith("skills/") and len(Path(name).parts) > 2
    }
    for core in CORE_PATHS:
        if not core.endswith("/"):
            continue
        directory = installed / core
        if not directory.is_dir() or directory.is_symlink():
            continue
        for root, dirs, files in os.walk(directory, followlinks=False):
            dirs[:] = [name for name in dirs if name not in SKIP_PARTS and not name.startswith(".")
                       and not (Path(root) / name).is_symlink()]
            if core == "skills/" and Path(root) == directory:
                dirs[:] = [name for name in dirs if name in owned_skills]
            for name in files:
                if core == "skills/" and Path(root) == directory:
                    continue
                path = Path(root) / name
                relative = path.relative_to(installed).as_posix()
                if path.suffix in NEW_FILE_SUFFIXES and _installed_file(installed, relative) is not None:
                    yield relative


def changed_paths(baseline: dict[str, Any], installed: Path) -> list[str]:
    installed = Path(installed).resolve()
    if baseline.get("installed_root") != str(installed):
        raise ValueError("VersionDrift baseline belongs to another installation")
    files = baseline["files"]
    changed = set()
    for name, previous in files.items():
        path = _installed_file(installed, name)
        if path is None or _digest(path) != previous:
            changed.add(name)
    changed.update(name for name in _new_system_files(installed, files) if name not in files)
    return sorted(changed)


def git_response(baseline: dict[str, Any], installed: Path, args: list[str]) -> str:
    tag = "v" + baseline["version"]
    if args == ["tag", "-l", "v[0-9]*.[0-9]*.[0-9]*"]:
        return tag + "\n"
    if args == ["log", "-1", "--format=%ct", tag]:
        return str(baseline["created_at"]) + "\n"
    if len(args) >= 5 and args[:4] == ["diff", "--name-only", tag, "--"]:
        requested = args[4:]
        if not requested or any(path not in CORE_PATHS for path in requested):
            raise ValueError("Unsupported VersionDrift core path query")
        return "".join(name + "\n" for name in changed_paths(baseline, installed)
                       if any(name == path or name.startswith(path) for path in requested))
    raise ValueError("Unsupported VersionDrift Git query")
