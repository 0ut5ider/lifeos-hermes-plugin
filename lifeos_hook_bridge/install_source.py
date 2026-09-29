# ABOUTME: Prepares an exact upstream LifeOS revision for plugin-managed installation.
# ABOUTME: Publishes a candidate only after every bundled compatibility patch applies.

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


UPSTREAM_LIFEOS = "https://github.com/danielmiessler/LifeOS.git"
SUPPORTED_LIFEOS_COMMIT = "5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c"
LIFEOS_PATCHES = (
    "lifeos-task-governance.patch",
    "lifeos-agent-watchdog.patch",
    "lifeos-terminal-audit.patch",
    "lifeos-checkpoint-verification.patch",
    "lifeos-failure-capture.patch",
    "lifeos-remote-desktop-gate.patch",
    "lifeos-remote-isa-view.patch",
    "lifeos-model-rung-effort.patch",
    "lifeos-hermes-carrier-probe.patch",
)
INSTALL_STEPS = ("InstallSettings", "DeployCore", "ScaffoldUser", "LinkUser",
                 "InstallHooks", "ActivateImports")


class IncompatibleLifeOS(Exception):
    pass


def _git(*args: str, cwd: Path | None = None, timeout: int = 300) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=cwd or Path.home(), text=True, capture_output=True,
                                check=True, timeout=timeout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        detail = getattr(error, "stderr", "") or str(error)
        raise IncompatibleLifeOS(f"Git {args[0]} failed: {detail.strip()}") from error
    return result.stdout.strip()


def latest_revision(source: str = UPSTREAM_LIFEOS) -> str:
    answer = _git("ls-remote", source, "HEAD", timeout=30)
    revision = answer.split("\t", 1)[0]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise IncompatibleLifeOS("LifeOS upstream did not return one Git commit")
    return revision


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for directory, names, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        names[:] = sorted(name for name in names if name != ".git")
        for name in names:
            if (parent / name).is_symlink():
                raise IncompatibleLifeOS(f"LifeOS candidate contains a symbolic link: {parent / name}")
        for name in sorted(files):
            if name == "lifeos-source-manifest.json":
                continue
            path = parent / name
            if path.is_symlink() or not path.is_file():
                raise IncompatibleLifeOS(f"LifeOS candidate contains a non-regular file: {path}")
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode() + b"\n")
    return digest.hexdigest()


def validate_candidate(target: Path, supported_revision: str, patches: Path,
                       patch_names: tuple[str, ...]) -> dict:
    manifest_path = target / "lifeos-source-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as error:
        raise IncompatibleLifeOS("LifeOS candidate manifest is missing or invalid") from error
    expected_patches = []
    for name in patch_names:
        patch = patches / name
        if not patch.is_file():
            raise IncompatibleLifeOS(f"LifeOS compatibility patch is missing: {name}")
        expected_patches.append({"name": name, "sha256": hashlib.sha256(patch.read_bytes()).hexdigest()})
    if manifest.get("upstream_commit") != supported_revision or manifest.get("patches") != expected_patches:
        raise IncompatibleLifeOS("LifeOS candidate does not match the supported patch set")
    if _git("rev-parse", "HEAD", cwd=target) != supported_revision:
        raise IncompatibleLifeOS("LifeOS candidate Git revision changed")
    if manifest.get("tree_sha256") != _tree_digest(target):
        raise IncompatibleLifeOS("LifeOS candidate files changed after preparation")
    return manifest


def prepare_lifeos(source: str, target: Path, supported_revision: str,
                   patches: Path, patch_names: tuple[str, ...]) -> dict:
    revision = latest_revision(source)
    if revision != supported_revision:
        raise IncompatibleLifeOS(
            f"Latest LifeOS commit {revision} is not the tested commit {supported_revision}"
        )
    target = target.absolute()
    if target.exists() or target.is_symlink():
        raise IncompatibleLifeOS(f"LifeOS candidate already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    stage.chmod(0o700)
    try:
        _git("clone", "--quiet", "--no-checkout", "--", source, str(stage))
        _git("checkout", "--quiet", "--detach", revision, cwd=stage)
        if _git("rev-parse", "HEAD", cwd=stage) != revision:
            raise IncompatibleLifeOS("Cloned LifeOS revision differs from the selected commit")
        applied = []
        for name in patch_names:
            patch = patches / name
            if not patch.is_file() or patch.is_symlink():
                raise IncompatibleLifeOS(f"LifeOS compatibility patch is missing: {name}")
            _git("apply", "--check", str(patch), cwd=stage)
            _git("apply", str(patch), cwd=stage)
            applied.append({"name": name, "sha256": hashlib.sha256(patch.read_bytes()).hexdigest()})
        _git("diff", "--check", cwd=stage)
        manifest = {"upstream": source, "upstream_commit": revision, "patches": applied,
                    "tree_sha256": _tree_digest(stage)}
        (stage / "lifeos-source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        os.replace(stage, target)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def prepare_latest_lifeos(target: Path) -> dict:
    return prepare_lifeos(UPSTREAM_LIFEOS, target, SUPPORTED_LIFEOS_COMMIT,
                          Path(__file__).parent / "patches", LIFEOS_PATCHES)


def validate_prepared_lifeos(candidate: Path) -> dict:
    return validate_candidate(candidate, SUPPORTED_LIFEOS_COMMIT,
                              Path(__file__).parent / "patches", LIFEOS_PATCHES)


def install_lifeos(candidate: Path, installed: Path, failed: Path, bun: str,
                   supported_revision: str, patches: Path,
                   patch_names: tuple[str, ...]) -> dict:
    manifest = validate_candidate(candidate, supported_revision, patches, patch_names)
    installed = installed.absolute()
    failed = failed.absolute()
    if installed.name != ".claude":
        raise IncompatibleLifeOS("LifeOS fresh install target must be a .claude directory")
    if installed.exists() or installed.is_symlink():
        raise IncompatibleLifeOS(f"LifeOS install target already exists: {installed}")
    if failed.exists() or failed.is_symlink():
        raise IncompatibleLifeOS(f"LifeOS failed-install archive already exists: {failed}")
    executable = shutil.which(bun)
    if not executable:
        raise IncompatibleLifeOS("Bun is required to install LifeOS")
    skill_root = candidate / "LifeOS"
    template = skill_root / "install/CLAUDE.template.md"
    if not template.is_file():
        raise IncompatibleLifeOS("LifeOS candidate lacks CLAUDE.template.md")
    for name in INSTALL_STEPS:
        if not (skill_root / "Tools" / f"{name}.ts").is_file():
            raise IncompatibleLifeOS(f"LifeOS candidate lacks {name}.ts")
    installed.parent.mkdir(parents=True, exist_ok=True)
    installed.mkdir(mode=0o700)
    try:
        shutil.copy2(template, installed / "CLAUDE.md")
        for name in INSTALL_STEPS:
            result = subprocess.run(
                [executable, str(skill_root / "Tools" / f"{name}.ts"),
                 "--config-root", str(installed), "--skill-root", str(skill_root), "--apply"],
                cwd=installed.parent, text=True, capture_output=True, timeout=300,
            )
            if result.returncode:
                raise IncompatibleLifeOS(f"LifeOS {name} exited with code {result.returncode}")
        source_version = (skill_root / "install/LIFEOS/VERSION").read_text().strip()
        version = (installed / "LIFEOS/VERSION").read_text().strip()
        settings = json.loads((installed / "settings.json").read_text())
        if version != source_version or not isinstance(settings.get("hooks"), dict) or not settings["hooks"]:
            raise IncompatibleLifeOS("LifeOS installation did not create the expected version and hooks")
    except BaseException as error:
        failed.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(installed, failed)
        except OSError as rollback_error:
            raise IncompatibleLifeOS(
                f"LifeOS install failed and partial files remain at {installed}: {rollback_error}"
            ) from error
        if isinstance(error, KeyboardInterrupt):
            raise
        raise IncompatibleLifeOS(f"{error}. Partial files were kept at {failed}") from error
    return {"installed_version": version, "upstream_commit": manifest["upstream_commit"],
            "steps": list(INSTALL_STEPS), "restart_required": True}


def install_prepared_lifeos(candidate: Path, installed: Path, failed: Path) -> dict:
    return install_lifeos(candidate, installed, failed, "bun", SUPPORTED_LIFEOS_COMMIT,
                          Path(__file__).parent / "patches", LIFEOS_PATCHES)
