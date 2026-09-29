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


class IncompatibleLifeOS(Exception):
    pass


def _git(*args: str, cwd: Path | None = None, timeout: int = 300) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True,
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
        manifest = {"upstream": source, "upstream_commit": revision, "patches": applied}
        (stage / "lifeos-source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        os.replace(stage, target)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def prepare_latest_lifeos(target: Path) -> dict:
    return prepare_lifeos(UPSTREAM_LIFEOS, target, SUPPORTED_LIFEOS_COMMIT,
                          Path(__file__).parent / "patches", LIFEOS_PATCHES)
