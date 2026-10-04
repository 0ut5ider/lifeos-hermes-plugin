# Extended paired lifecycle effects

Date: 2026-10-04. Six new cases compare actual Claude Code 2.1.272 and Hermes lifecycle events in disposable synthetic homes. All 12 CLI runs and 12 selected native hook invocations exit with status zero. The results establish selected branches for three additional registrations and another branch of HookHealer. Complete handler effects remain open.

| Case | Registration | Required effect |
| --- | --- | --- |
| `healer-containment` | `SessionStart.1.1` | Refuse to repair a registered symlink whose target is outside the configuration root. Preserve the target bytes and non-executable mode. Retain the native refusal event. |
| `kitty-cli` | `SessionStart.1.2` | Persist the synthetic Kitty environment and current session mapping. Remove the prior window title on real CLI startup. |
| `memory-health-critical` | `SessionEnd.1.4` | Run the genuine MemoryHealthCheck tool. Append one report with 14 critical findings, report the critical condition, and retain a successful nonblocking hook exit. |
| `doc-inventory-drift` | `SessionEnd.1.5` | Record exactly the missing active Knowledge directory and unknown Surprise directory. Preserve the existing event and exclude the private skill directory. |
| `doc-inventory-clean` | `SessionEnd.1.5` | Record an explicit completed check with an empty finding set. Preserve the existing event. |
| `doc-inventory-unparseable` | `SessionEnd.1.5` | Record an inventory parsing warning instead of silently reporting success. Preserve the existing event. |

The [driver](../../../scripts/paired_lifecycle_effects.py) uses the existing blocked-prompt lifecycle boundary. Each client emits SessionStart, UserPromptSubmit, and SessionEnd with one consistent session identity. The prompt hook prevents model generation. A loopback guard retains requests and returns HTTP 401. Native runs make no requests. Each Hermes run makes two model metadata requests and no generation request. These are actual client events, rather than fabricated event dispatch.

[paired-results.json](paired-results.json) contains the compared state and assertions. Each client/case directory retains the exact synthetic files before and after execution, child input and output, CLI output, event payloads, and source hashes. [configuration.json](configuration.json) records command and fixture paths. [runtime-manifest.json](runtime-manifest.json) verifies that the native binary, Hermes modules, and plugin source match the preceding comparison fixture. The driver source changes; product source does not change.

The Kitty fixture has no terminal server. Its scope is persistence and stale-title removal, not visible tab rendering. The health fixture links the actual native tool into the disposable root. Missing memory components intentionally produce a critical report; this is not a health finding about either active installation. Documentation cases select the memory-inventory handler inside the real DocIntegrity hook. They do not establish every documentation handler or inference branch.

Six assertion tests fail before the cases exist. All 13 assertion tests pass afterward. Each new test also rejects a matching result that omits the required effect. Historical October 3 evidence retains its original driver bytes as [paired-lifecycle-driver.py](../2026-10-03-paired-lifecycle-effects/paired-lifecycle-driver.py). Its artifact hashes remain unchanged.

The cumulative ledger contains selected paired cases for 11 registrations. Dispatch evidence remains at 65 matched registrations with nine missing native controls. Full effect completion remains open. Active services, ownership settings, and installed code on `.212` remain unchanged by this work. The full-experience release remains staged.
