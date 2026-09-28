# Native SessionStart effects through Hermes

On 2026-09-28, four native LifeOS SessionStart effects were exercised through the plugin on the isolated `.212` account. Every probe used a disposable home or LifeOS directory. No installed settings or hook executable was changed by the probes.

- HookHealer found a directly registered script with mode `0644`, changed its executable bit, and wrote a `healed` observability row.
- SettingsBackport compared a direct edit to generated `settings.json` with the previous merge snapshot and wrote the edited value into the user overlay. MergeSettings then retained that value in generated settings.
- A separate MergeSettings probe combined a system setting and user overlay setting, then wrote a snapshot equal to the generated output.
- FreshnessCache wrote its cache and marked a freshly reviewed disposable TELOS file as fresh. An initial test wrongly expected an empty fixture to produce zero total files. `TelosFreshness.ts` defines eight registry entries regardless of whether the files exist; the corrected fixture uses a reviewed file to prove the reader selected the disposable root.

The complete plugin suite passed 103 tests on `.212` with all native paths supplied and no skips. These probes verify the named effects and the bridge event route. They do not establish every possible state change of those native tools.
