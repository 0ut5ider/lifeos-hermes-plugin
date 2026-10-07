# Hermes capability validation

Date: 2026-10-05. Hermes validates a plugin with `hermes plugins validate` before a managed installation. This unit resolves the capability-probe defect and the missing middleware declaration. The security scan still blocks installation. Production on `.212` stays unchanged.

| Check | Before | After |
| --- | --- | --- |
| Capability probe | Fails: the validator stub rejects `required` in `register_middleware`. | Passes on the corrected host source. |
| Declared middleware | Not reached. After the probe correction, it fails for `llm_admission` and `llm_execution`. | Passes: the manifest declares both kinds. |
| Security scan | Dangerous verdict: 16 critical `ssh_backdoor` findings of 62. | Unchanged. The installer refuses the package with and without `--force`. |

The host correction belongs to `hermes-required-middleware.patch`. That patch adds the `required` argument to the actual plugin manager, so it now also adds the argument to the validator stub. The stub refuses a non-boolean value with the same message as the manager. Two new host tests fail before the correction ([host-before.txt](host-before.txt)). The three host suites pass 126 tests afterward ([host-after.txt](host-after.txt)).

The regenerated patch changes two files: `hermes_cli/plugin_validate.py` and the host test file. Regeneration from the corrected checkout reproduces the content of the other eight patches. The patch regeneration test now requires both additions.

The new plugin test runs the actual host validator against the runtime package. It fails before the manifest change ([manifest-before.txt](manifest-before.txt)) and passes afterward ([manifest-after.txt](manifest-after.txt)). The final plugin gate passes 206 tests with four optional skips ([plugin-after.txt](plugin-after.txt)).

[validator-report.json](validator-report.json) retains the complete validator result. One warning remains by design: the manifest declares `pre_llm_call`, and the plugin registers that hook only on a host without the prompt-admission extension.

## Open scanner decision

All 16 critical findings match the literal SSH authorized-keys file name. They are in the optional memory-sharing enrollment code: 13 in `memory_sharing.py`, two in `memory_preferences.py`, and one in `dashboard/plugin_api.py`. The scanner reports a real capability: enrollment writes a restricted key entry to that file. Renaming identifiers to avoid the pattern would hide the capability from the scanner, so this unit does not do that.

The remaining 46 findings are medium or low. Without the critical findings, the verdict requires confirmation and no longer blocks installation. Adrian must select the resolution for the sharing code. The recommended option moves SSH enrollment into a separate optional component that the operator installs explicitly.
