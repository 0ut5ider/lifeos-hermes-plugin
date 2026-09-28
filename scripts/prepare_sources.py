# ABOUTME: Prepares tested Hermes and LifeOS source revisions with ordered compatibility patches.
# ABOUTME: Publishes both patched trees together only after every patch and whitespace check passes.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "hermes": {
        "base": "758ad514eb0e800547e015edf05aa18f78b78d82",
        "patches": (
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
        ),
    },
    "lifeos": {
        "base": "5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c",
        "patches": (
            "lifeos-task-governance.patch",
            "lifeos-agent-watchdog.patch",
            "lifeos-terminal-audit.patch",
            "lifeos-checkpoint-verification.patch",
            "lifeos-failure-capture.patch",
            "lifeos-remote-desktop-gate.patch",
            "lifeos-remote-isa-view.patch",
            "lifeos-model-rung-effort.patch",
            "lifeos-hermes-carrier-probe.patch",
        ),
    },
}


class PreparationError(Exception):
    pass


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PreparationError(f"{' '.join(args[:2])} failed: {detail}")
    return result.stdout.strip()


def check_source(name: str, repo: Path, base: str) -> None:
    if not repo.is_dir() or run("git", "-C", str(repo), "rev-parse", "--is-inside-work-tree") != "true":
        raise PreparationError(f"{name} source is not a Git working tree: {repo}")
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{base}^{{commit}}"],
        text=True, capture_output=True,
    )
    if result.returncode:
        raise PreparationError(f"{name} source lacks required base revision {base}: {repo}")


def prepare_source(name: str, repo: Path, output: Path) -> dict[str, object]:
    source = SOURCES[name]
    base = str(source["base"])
    run("git", "clone", "--quiet", "--no-checkout", "--", str(repo), str(output))
    run("git", "checkout", "--quiet", "-b", "feature/lifeos-hook-parity", base, cwd=output)
    applied = []
    for filename in source["patches"]:
        patch = ROOT / "patches" / filename
        if not patch.is_file():
            raise PreparationError(f"missing patch: {patch}")
        run("git", "apply", "--check", str(patch), cwd=output)
        run("git", "apply", str(patch), cwd=output)
        applied.append({"name": filename, "sha256": hashlib.sha256(patch.read_bytes()).hexdigest()})
    run("git", "diff", "--check", cwd=output)
    return {"base": base, "patches": applied}


def prepare(hermes_repo: Path, lifeos_repo: Path, output: Path) -> None:
    if output.exists() or output.is_symlink():
        raise PreparationError(f"output already exists: {output}")
    for name, repo in (("hermes", hermes_repo), ("lifeos", lifeos_repo)):
        check_source(name, repo, str(SOURCES[name]["base"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        manifest = {
            "hermes": prepare_source("hermes", hermes_repo, staging / "hermes"),
            "lifeos": prepare_source("lifeos", lifeos_repo, staging / "lifeos"),
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        os.replace(staging, output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare pinned Hermes and LifeOS source trees")
    parser.add_argument("--hermes-repo", required=True, type=Path)
    parser.add_argument("--lifeos-repo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        prepare(args.hermes_repo.expanduser().resolve(), args.lifeos_repo.expanduser().resolve(),
                args.output.expanduser().absolute())
    except PreparationError as error:
        print(f"Source preparation failed: {error}", file=sys.stderr)
        return 1
    print(f"Prepared patched sources at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
