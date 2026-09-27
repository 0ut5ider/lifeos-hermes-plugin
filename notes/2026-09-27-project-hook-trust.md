# 2026-09-27: Project hooks need an explicit trust boundary

The bridge watched project `.claude/settings.json` files for ConfigChange but only executed hook registrations from the user settings file. A characterization test placed a Bash PreToolUse deny hook in a project settings file. The bridge allowed the synthetic call, confirming the gap.

The first implementation loaded project hooks from every observed tool working directory. That would execute shell commands from an untrusted checkout. Hermes already exposes `is_project_root_trusted`, backed by `skills.trusted_project_dirs`, for local project skills. The bridge now applies that same explicit trust decision before running project hooks. User hooks run first, followed by trusted project settings and local settings. Project settings changes reload the cached groups after the ConfigChange gate accepts them.

On `.212`, a synthetic project hook was skipped while its root was untrusted. A process-local test then supplied that root through Hermes's trusted project function. The same hook blocked the synthetic Bash call. No persistent trust list changed. The full local suite passed 58 tests, with four optional native tests skipped. The native TaskCreated probe still blocked a short description and task 51 after this change.

A follow-up characterization test found that project `env` values were absent in the hook child process. The bridge now merges trusted project and local `env` values into a copy of the user hook environment for the matching session. A second project session did not inherit the first project's value. A process test on `.212` confirmed the value reached a native command hook.

Current limits: The bridge does not discover a project root above the observed working directory. A session that enters multiple repositories needs a separate scope test. Project hook commands are powerful, so the trust gate remains fail closed if Hermes's trust function is unavailable.
