# SessionEnd integrity effect

Date: 2026-09-27

The parity record showed that installed SessionEnd handlers exited successfully, but did not prove that `IntegrityCheck` consumed the bridge transcript and wrote state. A disposable `.212` probe supplied a synthetic Write result, then ran the installed native hook.

The first probe invoked the script from the source checkout, outside the installed Bun dependency tree, and failed to load `yaml`. The installed hook under `~/.claude/hooks/` loads that package correctly. A second probe used `LIFEOS/TOOLS/Probe.ts`, which the native change classifier intentionally categorizes as null. The hook read one Write entry but made no integrity state. Capturing its stderr showed the classification decision.

The final fixture used a synthetic path under a temporary home directory's `.claude/hooks/`. It did not write a hook file. The bridge recorded the Write tool use, then dispatched SessionEnd to the installed `IntegrityCheck.hook.ts`. The native classifier found one `[hook]` system change and wrote `MEMORY/STATE/integrity-state.json` under the temporary LifeOS root. The root contained no `IntegrityMaintenance.ts`, so no maintenance child ran. This verifies transcript parsing, change classification, SessionEnd dispatch, and the native state effect through the bridge.
