# LifeOS plugin for Hermes

Run LifeOS hooks, lasting memory, and the main Pulse dashboard through Hermes. The integration also provides owner-reviewed installation into your existing Hermes, updates, memory import and return, and optional HTTP access for other agents.

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

## Install LifeOS into your Hermes

LifeOS installs into the Hermes you already run. It checks your Hermes version first, patches your existing checkout in place, and leaves your other plugins, tools, models, and data where they are. A release download is about 2 MB.

In the Hermes **Plugins** page, install this GitHub subdirectory URL:

```text
https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager
```

Enable the manager and restart the dashboard. Open **LifeOS releases** and read **Hermes compatibility**. When it says LifeOS can be installed, select **Install LifeOS**, wait for preparation, select **Review release** to see exactly what changes, then select **Install this release**.

While LifeOS is installed, `hermes update` is held: an update would carry the patches onto an untested Hermes version. Update LifeOS from the releases page instead. You can also ask Hermes to check compatibility or prepare an update through its `lifeos-release` skill; the owner still reviews and applies in the dashboard.

After an applied operation, check its identity:

```bash
hermes lifeos-release compatibility
hermes lifeos-version
```

The [installation guide](docs/installation-workflow.md) covers supported layouts, the review, recovery, removal, and moving from a managed 0.7.x installation. The [update policy](docs/update-policy.md) covers recovery and qualification.

## Compatibility target

This release supports Hermes `v0.21.7` (commit `71d34bad1045610252eda02ee79549436896e784`) installed with the official installer as a single-profile Git checkout, and LifeOS `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. It applies eleven Hermes patch groups (96 files) and twenty-five LifeOS patches. The [compatibility manifest](optional/lifeos_release_manager/host-compatibility.json), [source declarations](lifeos_hook_bridge/install_source.py), and [patch map](docs/patch-footprint.md) define the supported combination.

Any other Hermes version is refused with its reason. Stock Hermes lacks some required admission, lifecycle, and final-answer controls, so the bridge alone does not supply the full integration. A newer upstream Hermes needs a ported and qualified patch set. The [installation plan](docs/in-place-installation-plan.md) and [design](docs/in-place-installation-design.md) record why LifeOS patches the existing installation instead of replacing it.

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
