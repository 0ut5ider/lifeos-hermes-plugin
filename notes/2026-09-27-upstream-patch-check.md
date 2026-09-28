# Hermes patch against current upstream

Date: 2026-09-27. Public upstream: `NousResearch/hermes-agent` HEAD `9a0a1625` at the time of the check.

The public `patches/hermes-hook-controls.patch`, based on Hermes `758ad514e`, passed `git apply --check` against a fresh upstream checkout. It then applied without conflicts. Python compiled the changed conversation loop, turn context, plugin dispatch, approval module, and new prompt-block test. `git diff --check` found no whitespace errors.

This is an application and syntax check, not a runtime regression test on upstream HEAD. The fresh checkout had no pytest environment. The isolated `.212` fork ran 37 focused Hermes tests and the full plugin suite ran 86 tests. A fresh installer should still run the included tests after applying the patch.
