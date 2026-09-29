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
SUPPORTED_HERMES_COMMIT = "758ad514eb0e800547e015edf05aa18f78b78d82"
HERMES_PATCHES = (
    "hermes-hook-controls.patch",
    "hermes-command-denial.patch",
    "hermes-remote-file-staleness.patch",
    "hermes-stop-effort.patch",
    "hermes-delegate-tier-routing.patch",
    "hermes-cron-worker-bootstrap.patch",
    "hermes-delegate-provider-routing.patch",
    "hermes-direct-provider-inference.patch",
    "hermes-stop-fail-closed.patch",
    "hermes-command-policy.patch",
    "hermes-command-context.patch",
    "hermes-command-rewrite.patch",
    "hermes-session-reasons.patch",
    "hermes-prompt-exit-reason.patch",
    "hermes-empty-session-clear.patch",
    "hermes-empty-session-resume.patch",
    "hermes-permanent-policy-precedence.patch",
    "hermes-policy-batch-order.patch",
    "hermes-bypass-policy.patch",
)
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


def _tree_digest(root: Path, manifest_name: str = "lifeos-source-manifest.json") -> str:
    digest = hashlib.sha256()
    for directory, names, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        names[:] = sorted(name for name in names if name != ".git")
        for name in names:
            if (parent / name).is_symlink():
                raise IncompatibleLifeOS(f"LifeOS candidate contains a symbolic link: {parent / name}")
        for name in sorted(files):
            if name == manifest_name:
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


def validate_hermes_candidate(target: Path, supported_revision: str, patches: Path,
                              patch_names: tuple[str, ...]) -> dict:
    try:
        manifest = json.loads((target / "hermes-source-manifest.json").read_text())
    except (OSError, ValueError) as error:
        raise IncompatibleLifeOS("Hermes candidate manifest is missing or invalid") from error
    expected = []
    for name in patch_names:
        patch = patches / name
        if not patch.is_file() or patch.is_symlink():
            raise IncompatibleLifeOS(f"Hermes compatibility patch is missing: {name}")
        expected.append({"name": name, "sha256": hashlib.sha256(patch.read_bytes()).hexdigest()})
    if manifest.get("base_commit") != supported_revision or manifest.get("patches") != expected:
        raise IncompatibleLifeOS("Hermes candidate does not match the tested patch set")
    if _git("rev-parse", "HEAD", cwd=target) != supported_revision:
        raise IncompatibleLifeOS("Hermes candidate Git revision changed")
    if manifest.get("tree_sha256") != _tree_digest(target, "hermes-source-manifest.json"):
        raise IncompatibleLifeOS("Hermes candidate files changed after preparation")
    return manifest


def prepare_hermes(source: Path, target: Path, supported_revision: str,
                   patches: Path, patch_names: tuple[str, ...]) -> dict:
    source = source.absolute()
    target = target.absolute()
    if source.is_symlink() or not source.is_dir():
        raise IncompatibleLifeOS("Hermes source must be a regular directory")
    if _git("rev-parse", "HEAD", cwd=source) != supported_revision:
        raise IncompatibleLifeOS(f"Hermes source is not the tested commit {supported_revision}")
    if _git("status", "--porcelain", "--untracked-files=all", cwd=source):
        raise IncompatibleLifeOS("Hermes source must be clean before preparing a patch candidate")
    if target.exists() or target.is_symlink():
        raise IncompatibleLifeOS(f"Hermes candidate already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    stage.chmod(0o700)
    try:
        _git("clone", "--quiet", "--no-checkout", "--", str(source), str(stage))
        _git("checkout", "--quiet", "--detach", supported_revision, cwd=stage)
        applied = []
        for name in patch_names:
            patch = patches / name
            if not patch.is_file() or patch.is_symlink():
                raise IncompatibleLifeOS(f"Hermes compatibility patch is missing: {name}")
            _git("apply", "--check", str(patch), cwd=stage)
            _git("apply", str(patch), cwd=stage)
            applied.append({"name": name, "sha256": hashlib.sha256(patch.read_bytes()).hexdigest()})
        _git("diff", "--check", cwd=stage)
        manifest = {"base_commit": supported_revision, "patches": applied,
                    "tree_sha256": _tree_digest(stage, "hermes-source-manifest.json")}
        (stage / "hermes-source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        os.replace(stage, target)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def prepare_supported_hermes(source: Path, target: Path) -> dict:
    return prepare_hermes(source, target, SUPPORTED_HERMES_COMMIT,
                          Path(__file__).parent / "patches", HERMES_PATCHES)


def validate_supported_hermes(candidate: Path) -> dict:
    return validate_hermes_candidate(candidate, SUPPORTED_HERMES_COMMIT,
                                     Path(__file__).parent / "patches", HERMES_PATCHES)


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


def finalize_lifeos(candidate: Path, installed: Path, hermes_home: Path, baseline_path: Path,
                    bun: str, hermes: str, supported_revision: str, patches: Path,
                    patch_names: tuple[str, ...], create_baseline, save_baseline) -> dict:
    manifest = validate_candidate(candidate, supported_revision, patches, patch_names)
    installed = installed.absolute()
    hermes_home = hermes_home.absolute()
    baseline_path = baseline_path.absolute()
    if installed.is_symlink() or hermes_home.is_symlink():
        raise IncompatibleLifeOS("LifeOS and Hermes install roots must be regular directories")
    if baseline_path.exists() or baseline_path.is_symlink():
        raise IncompatibleLifeOS("A VersionDrift baseline already exists")
    if not (installed / "LIFEOS/HERMES/Mount.ts").is_file():
        raise IncompatibleLifeOS("Installed LifeOS lacks Mount.ts")
    if not (installed / "settings.json").is_file() or not (hermes_home / "config.yaml").is_file():
        raise IncompatibleLifeOS("LifeOS settings and Hermes config must exist before mounting")
    source_version = (candidate / "LifeOS/install/LIFEOS/VERSION").read_text().strip()
    if (installed / "LIFEOS/VERSION").read_text().strip() != source_version:
        raise IncompatibleLifeOS("Installed LifeOS version differs from the prepared source")
    bun_executable = shutil.which(bun)
    hermes_executable = shutil.which(hermes)
    if not bun_executable or not hermes_executable:
        raise IncompatibleLifeOS("Bun and the Hermes command are required to finish setup")

    targets = ("config.yaml", "SOUL.md", ".env", "plugins/lifeos")
    for relative in targets:
        if (hermes_home / relative).is_symlink():
            raise IncompatibleLifeOS(f"Hermes mount target is a symbolic link: {relative}")
    baseline_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot = Path(tempfile.mkdtemp(prefix="mount-snapshot-", dir=baseline_path.parent))
    snapshot.chmod(0o700)
    existing = []
    for relative in targets:
        path = hermes_home / relative
        if path.exists():
            existing.append(relative)
            backup = snapshot / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            if path.is_dir():
                shutil.copytree(path, backup, symlinks=True)
            else:
                shutil.copy2(path, backup)

    environment = dict(os.environ, HERMES_HOME=str(hermes_home))
    mount = installed / "LIFEOS/HERMES/Mount.ts"
    try:
        for command, label in (
            ([bun_executable, str(mount)], "Mount"),
            ([bun_executable, str(mount), "--check"], "Mount check"),
            ([hermes_executable, "config", "check"], "Hermes config check"),
        ):
            result = subprocess.run(command, cwd=installed.parent, env=environment,
                                    text=True, capture_output=True, timeout=120)
            if result.returncode:
                raise IncompatibleLifeOS(f"LifeOS {label} exited with code {result.returncode}")
        baseline = create_baseline(candidate / "LifeOS/install", installed)
        save_baseline(baseline, baseline_path)
    except BaseException as error:
        try:
            for relative in targets:
                path = hermes_home / relative
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                elif path.exists() or path.is_symlink():
                    path.unlink()
                if relative in existing:
                    backup = snapshot / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if backup.is_dir():
                        shutil.copytree(backup, path, symlinks=True)
                    else:
                        shutil.copy2(backup, path)
            baseline_path.unlink(missing_ok=True)
        except OSError as rollback_error:
            raise IncompatibleLifeOS(
                f"LifeOS setup failed and Hermes files could not be restored. Snapshot: {snapshot}"
            ) from rollback_error
        if isinstance(error, KeyboardInterrupt):
            raise
        raise IncompatibleLifeOS(f"{error}. Hermes files were restored from {snapshot}") from error
    return {"mounted": True, "baseline_created": True, "upstream_commit": manifest["upstream_commit"],
            "snapshot": str(snapshot), "restart_required": True}


def finalize_prepared_lifeos(candidate: Path, installed: Path, hermes_home: Path,
                             baseline_path: Path, create_baseline, save_baseline) -> dict:
    return finalize_lifeos(candidate, installed, hermes_home, baseline_path, "bun", "hermes",
                           SUPPORTED_LIFEOS_COMMIT, Path(__file__).parent / "patches", LIFEOS_PATCHES,
                           create_baseline, save_baseline)
