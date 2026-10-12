# Hermes-managed release development

Date: 2026-10-12. Adrian authorizes complete installation and updates from Hermes, latest Hermes compatibility, and development evaluation on `.252`.

The accepted daily release remains 0.3.1 on `.253`. Historical release assets remain immutable. This directory records the next candidate, not a new production acceptance.

The roadmap now marks Atlas retention and all six 0.3.1 release steps complete. The current plan distinguishes current status from dated checkpoints.

## Automatic morning observation

The candidate adds `hermes lifeos-observe-morning --date YYYY-MM-DD`. An optional `--channel` selects a configured private channel when necessary. The command observes without starting a job or sending a message. It emits only a safe JSON receipt to standard output; an operator can save that receipt as a new asset after qualification.

The observer reads the actual system and user job definitions and applies the native named user override. It requires an enabled 07:00 script job and the running Pulse process timezone. It checks one cron start and completion against the current successful state. It pages backwards through Discord until the observation window is covered or history ends. A duplicate on a later page, invalid metadata, or incomplete coverage refuses success. The receipt records coverage counts, configuration hashes, and cron provenance. It does not claim to audit every possible outside manual action.

The ten new observation checks and three existing lifecycle checks pass on the accepted runtime. Tests use an actual local HTTP server, the native Pulse config loader, and the actual Hermes command parser. The initial native-loader check failed because the sealed archive had no runtime `smol-toml` dependency. The repeat uses the prepared native dependency fixture and passes. Raw results remain in this directory. The original 0.3.1 observer and published morning receipt are unchanged.

## Latest Hermes target

The GitHub latest stable release at task start is `v0.21.7`, published October 12, at commit `71d34bad1045610252eda02ee79549436896e784`. The target stays immutable during qualification. A separate current main observation is retained for comparison and does not select production code.

Ten of the eleven existing Hermes patches fail direct application checks against the clean target. These independent checks do not replace ordered source preparation. Three-way porting retains both required LifeOS behavior and upstream changes. Full compatibility, installation, update, recovery, and `.252` evaluation remain open.
