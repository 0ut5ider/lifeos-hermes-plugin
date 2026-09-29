# Plugin-managed LifeOS finalization probe

Date: 2026-09-29. Target: `lifeos-plugin-install-probe` on `192.168.8.212`, separate from the running `lifeos-hermes` account.

The plugin's finalization routine validated the prepared LifeOS candidate at `5e2f2e8`, ran the installed `Mount.ts`, ran `Mount.ts --check`, and ran `hermes config check` from the test account's newly installed Hermes runtime. It saved a VersionDrift baseline for 1,796 installed system files. An immediate drift comparison reported zero changed files. The mount snapshot is private under `~/.local/state/lifeos-hook-bridge/` in that account.

The first baseline attempt failed before mounting. The account's `.local` parent was owned by root, while its `.local/bin` child belonged to the test user. The test user could run Bun but could not create `.local/state`. Changing only the `.local` parent owner to the test user allowed the default baseline path. The prior probe used a state path under the account's workspace and also recorded 1,796 files with zero drift. This showed that an executable in `.local/bin` does not prove the account can create plugin state under `.local`.

The account has no gateway service and its Hermes config names a probe model. This run does not verify a restart, a model call, dashboard browser interaction, or full hook parity. The finalization unit tests cover restoration after a failed mount. They do not cover service restart or recovery from process termination during a file write.
