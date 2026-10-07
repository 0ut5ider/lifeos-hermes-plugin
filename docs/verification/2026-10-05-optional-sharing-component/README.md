# Optional SSH sharing component

Date: 2026-10-05. Adrian approves moving SSH sharing enrollment out of the plugin package. The enrollment code now lives in `optional/lifeos-memory-sharing/`, outside the installed `lifeos_hook_bridge/` directory. Production on `.212` stays unchanged.

| Hermes check on `lifeos_hook_bridge/` | Before | After |
| --- | --- | --- |
| Security scan verdict | `dangerous`, 16 critical `ssh_backdoor` findings of 62 | `safe`, no critical finding, 46 medium or low findings |
| Installer decision | Blocked, with and without `--force` | `Allowed (clean scan)` |
| `hermes plugins validate` | Fails on the security scan | Every check passes |

[validator-report.json](validator-report.json) retains the complete result. These results use the Hermes source with the corrected required-middleware patch from the [capability validation unit](../2026-10-05-capability-validation/README.md).

## Behavior

The plugin package no longer contains code that reads or writes the SSH authorized keys file. A test fails if that file name appears in any package file.

The operator installs the component explicitly with `optional/lifeos-memory-sharing/install.py`. The plugin loads the component from `<Hermes home>/lifeos-memory-sharing/` only when the directory and file are owner files without shared write access and the file hash equals the hash recorded in the plugin. The loader refuses an altered, linked, or writable component.

Without the component:

- The memory status reports `connection_enrollment_available: false`, and the dashboard shows an installation note in place of the connection form.
- Enrollment is refused and changes no file.
- Revocation still disables the connection grant. The memory service refuses a disabled grant. The response reports `credential_entry_removed: false`, because the SSH entry stays until the component removes it.

With the component, enrollment and revocation behave as before. The existing sharing, preference, real SSH, and dashboard tests run against the component.

`MemoryPreferences` no longer takes the keys file path. Its constructor takes the component directory and options as keyword arguments. This changes the constructor signature for every caller in the repository.

## Verification

The new tests fail before implementation ([before.txt](before.txt)). The final gate ([tests-output.txt](tests-output.txt)) covers the component, sharing, preferences, real SSH, dashboard, Pulse, prompt, capability validation, footprint, and fresh-store suites: 162 tests pass with two optional skips. The dashboard interface tests pass 9 and 13 cases.

## Limits

- The stock Hermes installer has not yet installed this package in the disposable guest. That acceptance run remains open, together with the update workflow.
- The scan result depends on the corrected host patch for validation. The scan itself reads only the package files.
- The first version of the loader read the file twice and accepted a planted bytecode file. The [follow-up corrections](../2026-10-05-pr3-followup-fixes/README.md) close both defects.
- The component has no automatic update. A plugin release that changes the component needs a new installer run.
