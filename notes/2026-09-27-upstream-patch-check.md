# Hermes patch against current upstream

Date: 2026-09-27. Public upstream: `NousResearch/hermes-agent` HEAD `9a0a1625` at the time of the check.

The public `patches/hermes-hook-controls.patch`, based on Hermes `758ad514e`, passed `git apply --check` against a fresh upstream checkout. It then applied without conflicts. Python compiled the changed conversation loop, turn context, plugin dispatch, approval module, and new prompt-block test. `git diff --check` found no whitespace errors.

The patched checkout was copied into a disposable directory on `.212` and run with the existing Hermes test environment. Nine affected test modules passed 153 tests in 23.34 seconds. The installed `.212` Hermes source branch was unchanged. The installed fork separately passed 37 focused Hermes tests, and the plugin suite passed 86 tests. A fresh installer should still run the included tests after applying the patch.
