# LifeOS plugin for Hermes

Run LifeOS hooks, lasting memory, and the main Pulse dashboard through Hermes. The integration also provides owner-reviewed installation, complete-package updates, memory import and return, and optional HTTP access for other agents.

**Stable release: [0.7.3](https://github.com/0ut5ider/lifeos-hermes-plugin/releases/tag/v0.7.3).** The [release record](docs/verification/2026-10-16-release-0.7.3/README.md) identifies its exact package, review, tests, deployment, and limits. [VERSION](VERSION) identifies the source version; [CHANGELOG.md](CHANGELOG.md) records changes.

## Start here

| Your task | Read |
| --- | --- |
| Install LifeOS or update an installation | [Installation guide](docs/installation-workflow.md) |
| Connect another agent to memory | [HTTP MCP guide](docs/http-memory-mcp.md) |
| Configure Discord text access | [Discord guide](docs/discord-setup.md) |
| Import memory, return to Hermes, or remove LifeOS | [Memory portability](docs/memory-portability.md) |
| Change the integration or navigate its source | [Contributor guide](CONTRIBUTING.md), then [codebase map](docs/codebase.md) |
| Find a specific guide or historical decision | [Documentation index](docs/README.md) |
| Check unfinished product work | [TODO.md](TODO.md) |

## Install and update complete releases from Hermes

Start with a configured Hermes model and an authenticated owner dashboard running as a Linux systemd user service. The dashboard service must use the account home as its working directory, a private `UMask=0077`, and the selected physical `HERMES_HOME`.

In the Hermes **Plugins** page, install this GitHub subdirectory URL:

```text
https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager
```

Enable the manager and restart the dashboard. Open **LifeOS releases**. Select **Install LifeOS**, supply the user and assistant names, and leave the release version empty for the latest stable package. When preparation finishes, select **Review release**, check its version, commit, and package hash, then select **Install this release**.

**Update LifeOS** and **Update plugin** prepare the same complete qualified integration, including Hermes, LifeOS, the bridge, release manager, dependencies, and dashboard. Preparation preserves the running installation. Only the reviewed apply action changes active programs.

You can also ask Hermes to install or update LifeOS. Its `lifeos-release` skill prepares the package and directs the installation owner to the authenticated review. Memory ownership requires its own owner review and activation. Installation does not import personal data or select lasting-memory ownership automatically.

After an applied operation, check its actual identity:

```bash
hermes lifeos-release status
hermes lifeos-version
```

The [installation guide](docs/installation-workflow.md) covers service prerequisites, scanner confirmation, command-line use, and activation. The [update policy](docs/update-policy.md) covers recovery, rollback, and qualification.

## Compatibility target

The qualified 0.7.3 package targets Hermes `v0.21.7`, base commit `71d34bad1045610252eda02ee79549436896e784`, and LifeOS base `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. It includes ten Hermes patch groups and twenty-five LifeOS patches. [Source declarations](lifeos_hook_bridge/install_source.py) and the [patch map](docs/patch-footprint.md) define the supported combination.

Stock Hermes lacks some required admission, lifecycle, and final-answer controls. Installing only the bridge does not supply the full integration. A newer upstream commit needs a port and behavior qualification before it can replace the supported combination.

The accepted [installation redesign](docs/in-place-installation-plan.md) uses the existing Hermes installation, checks exact compatibility, and applies reversible host patches. It has no replacement-runtime option. Implementation and qualification are pending; the 0.7.3 instructions above still describe the published managed-runtime release.

The development branch includes the first step: a read-only compatibility check. Run `hermes lifeos-release compatibility` or open **Hermes compatibility** on the LifeOS releases page. The check compares the exact Hermes commit, the SHA-256 hash of each of the 94 patch target files, the Git working tree, the installation layout, profiles, and Python dependencies. It reports every blocking reason and changes nothing.

The [Step 1 ledger](docs/parity/step1-acceptance.md) records 152 accepted scenarios. These selected comparisons do not prove equivalence for every possible Claude Code event or handler branch.

## Lasting memory, experimental

LifeOS memory is an explicit ownership choice for a Hermes profile. The owner reviews sources, model routes, permitted readers, and recovery before activation. Governed reads and writes check the current authority and source state. Configuration changes can require a fresh review.

External agents use the included Streamable HTTP Model Context Protocol (MCP) server. Each connection needs its own owner-approved grant. Tailscale Serve is the recommended private HTTPS transport. Network access does not grant memory permission. See [HTTP setup](docs/http-memory-mcp.md).

Import, reverse export, return to preserved Hermes memory, and complete software removal are explicit dashboard workflows. They preserve source stores and recovery data. [Memory portability](docs/memory-portability.md) describes the controls and limits. Data erasure is a separate action.

## Install the plugin

For the full experience, use the release-manager workflow above. The standalone runtime plugin is `lifeos_hook_bridge/`. Direct bridge installation and [source preparation](docs/clean-install.md) are development paths; they do not qualify an arbitrary existing Hermes and LifeOS combination.

Open **LifeOS Bridge** at `/lifeos-bridge` to configure model tiers and Stop hook behavior. Haiku, Sonnet, Opus, and Fable are LifeOS tier names. Each can select a Hermes provider, model, and effort. They do not require four different model services. See [model and hook configuration](docs/configuration.md).

## Versioning

A release version identifies a tested complete integration. A Git commit identifies source. The installed `hermes lifeos-version` result identifies the selected package and reports integrity differences. A source checkout or queued update is not an installed release.

Use `NEXT-dev.N` for development packages and `NEXT-rc.N` for acceptance candidates. Publish the final version only after review and exact-package qualification. Preserve published packages and certificates. See the [contributor release guidance](CONTRIBUTING.md#release-changes).

## Development evidence

The [codebase map](docs/codebase.md) gives source entry points and focused tests. [Verification records](docs/verification/README.md) retain dated results, failures, and acceptance limits. [Agent reports](docs/agents/README.md) retain independent review evidence. Earlier narrative status is preserved in the [dated README snapshot](docs/history/2026-10-16-readme.md).

For 0.7.3, all 57 interface tests and 51 focused Python tests pass. The complete archive executes 1,129 cases. The workstation passes 1,126 cases; the three environment-specific cases pass in separate boundary and backup-module replays. This is coverage across environments. The release record retains the failed attempts, measured causes, and inherited-check limits.

Discord voice input, spoken replies, and Content media processing remain [deferred work](TODO.md).

## Reminder routing and privacy

The native ReminderRouter can send eligible reminders to GitHub when the owner configures that optional destination. Review the destination and access before enabling it. The selected daily text profile omits that integration. Captured prompts, raw traces, exports, and profile backups can contain private data; keep them outside Git. The [development capture guide](development/README.md) describes the opt-in recorder and its limits.

## License

This repository uses the [MIT License](LICENSE). Upstream Hermes, LifeOS, and packaged dependencies retain their own licenses.
