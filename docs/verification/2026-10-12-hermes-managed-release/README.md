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

The port now prepares and validates the exact v0.21.7 source. Patch reconstruction passes with 117 subtests. The official native runner passes 469 tests across 33 files, with no failures or skipped SSH cases. The target uses ten Hermes patch groups and twenty-five LifeOS patch groups. The unused protected-instruction patch remains as an inactive historical file. The upstream protected-file behavior passes unattended and interactive controls.

Compatibility qualification still needs the frozen dependency generation, combined integration checks, and installed development evaluation. Installation and update work remains in progress.

## Candidate checkpoint

The development version is 0.4.0-dev.1. The expanded official native runner passes 716 tests across 38 files. All twelve upstream checks pass. Topical native siblings retain public facade paths and the required policy behavior. The regenerated bundle contains ten groups covering 92 changed files.

The standalone release manager supplies native Hermes CLI registration, release download, package validation, frozen dependency preparation, a program transaction, a worker prototype, and an authenticated dashboard prototype. Twenty-nine focused tests and eleven subtests pass. The checks cover version identity, the catalog, stage validation, program recovery, and CLI registration/status. Three focused native mount checks pass, including retained rollback, later-edit refusal, and ordinary credential-snapshot pruning.

The full worker and its dashboard approval flow are not qualified. Fresh installation, actual second-release updates, dependency failure, process interruption, later data, and installed rollback remain acceptance requirements. The current complete-package builder and current native dashboard asset also remain unfinished. The first combined run has seven fixture/assertion failures; its relevant fixtures are revised, but the full combined repeat remains required.

Neither live server changes. Installed development qualification has not begun. The continuation details are in RESUME.md. This checkpoint is not a release qualification or deployment receipt.
