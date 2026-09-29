# ABOUTME: Runs the real SSH and Docker LifeOS bridge tests against a prepared Hermes source.
# ABOUTME: Fails when a selected live case skips because its disposable fixture is missing.

from __future__ import annotations

import argparse
import os
import sys
import unittest
from pathlib import Path


SSH_MODULES = (
    "tests.test_live_nested_ssh_hooks",
    "tests.test_live_remote_project_hooks",
    "tests.test_live_ssh_command_policy",
    "tests.test_live_project_hook_transport",
    "tests.test_live_remote_isa",
    "tests.test_live_ssh_web_cache",
)
DOCKER_MODULES = (
    "tests.test_live_container_file_hooks",
    "tests.test_live_container_project_hooks",
    "tests.test_live_container_command_policy",
    "tests.test_live_container_isa",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live remote LifeOS hook tests")
    parser.add_argument("--ssh", action="store_true")
    parser.add_argument("--docker", action="store_true")
    args = parser.parse_args()
    if not args.ssh and not args.docker:
        parser.error("Select --ssh, --docker, or both")
    source = os.environ.get("LIFEOS_HERMES_SOURCE")
    if not source or not (Path(source) / "hermes_bootstrap.py").is_file():
        parser.error("LIFEOS_HERMES_SOURCE must point to the prepared Hermes checkout")
    sys.path.insert(0, source)
    import hermes_bootstrap  # noqa: F401  Loads Hermes's managed dependencies.

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    modules = (SSH_MODULES if args.ssh else ()) + (DOCKER_MODULES if args.docker else ())
    tests_dir = Path(__file__).resolve().parents[1] / "tests"
    suite = unittest.TestSuite(unittest.defaultTestLoader.discover(
        str(tests_dir), pattern=name.rsplit(".", 1)[-1] + ".py") for name in modules)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        print(f"Live gate skipped {len(result.skipped)} selected cases", file=sys.stderr)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
