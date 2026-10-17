# Install the complete LifeOS integration

Use the release manager for a supported installation. It prepares one qualified package containing Hermes, LifeOS, the bridge, manager, dependencies, dashboard, and public commands. Installing only `lifeos_hook_bridge/` does not provide the complete integration.

The [current release record](verification/2026-10-16-release-0.7.3/README.md) identifies the supported package. [Source preparation](clean-install.md) is a separate development workflow.

## Before installation

Configure a working model in Hermes. The installer preserves that model and the configured LifeOS tier mapping. Have an authenticated Hermes dashboard owner account available.

The supported managed first-installation path runs on Linux with systemd user services. The dashboard service must:

- Run as the intended Hermes account, with its account home as the working directory.
- Use that account's `~/.local/bin/hermes` launcher.
- Declare the physical selected profile in `HERMES_HOME`, without an environment file.
- Use `UMask=0077` for private profile and recovery files.

Use physical account-home, profile, and native installation paths without whitespace, dollar signs, quotes, backslashes, semicolons, or closing braces. The manager verifies the service definition and running profile before it changes programs. A foreground dashboard or foreign service binding does not satisfy this managed path.

Keep a private backup before enabling memory or changing an existing installation. Profile backups and whole-guest backups have different coverage; see [recovery boundaries](update-policy.md#recovery-and-rollback).

## Install the release manager

1. Open the Hermes **Plugins** page.
2. Install this GitHub subdirectory URL:

   ```text
   https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager
   ```

3. Enable **lifeos-release-manager**.
4. Restart the Hermes dashboard so it loads the plugin API and page.
5. Open **LifeOS releases**, at `/lifeos-releases`.

The web form installs the default branch. It has no revision field. A GitHub tree URL does not select a commit.

Hermes can report a CAUTION verdict because the manager runs processes and manages user services. Read the findings against the selected source before confirming. The native **Force reinstall** control can confirm a trusted source, but it also replaces an existing manager directory. Do not use it without inspecting an existing installation and retaining its recovery path. Never disable the scanner to make installation pass.

For a pinned command-line bootstrap, use the full 40-character program commit from the selected release record:

```bash
hermes plugins install 'https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager' --ref FULL_RELEASE_COMMIT
hermes plugins enable lifeos-release-manager
```

Hermes does not accept a tag for `--ref`. Restart the dashboard after bootstrap or replacement. Older managers can refuse newer package plans; use the manager from the selected qualified release when a bootstrap is required.

## Prepare and apply a release

1. Select **Install LifeOS**.
2. Enter the user and assistant display names for a fresh store.
3. Leave the version empty for the latest stable package, or enter an exact published version.
4. Wait for the detached preparation to finish. The running installation remains selected during preparation.
5. Select **Review release** for the prepared operation.
6. Check its exact version, program commit, and package hash.
7. Select **Install this release**.
8. After the dashboard returns, check the operation state and installed version:

   ```bash
   hermes lifeos-release status IDENTIFIER
   hermes lifeos-version
   ```

Use the returned operation identifier in place of `IDENTIFIER`. An `applied` operation and a verified installed identity establish installation. `queued`, `preparing`, or `applying` states do not establish success.

The installer keeps existing model choices and personal data. A fresh installation creates missing gateway and Pulse service definitions but leaves those services disabled and inactive. Configure and verify messaging, owner authority, and selected jobs before starting them. Existing installation updates verify and drain all three services.

## Ask Hermes to install or update

The manager registers the [`lifeos-release` skill](../optional/lifeos_release_manager/skills/lifeos-release/SKILL.md). Ask Hermes to install LifeOS, update it, check its version, or recover an interrupted operation. Hermes can prepare the complete package:

```bash
hermes lifeos-release prepare --name 'Your name' --assistant 'Your assistant'
```

For an existing installation, use `hermes lifeos-release prepare`. Add `--version X.Y.Z` only when selecting an exact published version.

The authenticated owner still reviews and applies the operation in the dashboard. A native mount under managed memory requires that owner grant. The command-line `start` action is limited to installations that do not require managed native-memory authorization.

## Choose memory ownership separately

Installation does not activate lasting-memory ownership or import existing data automatically.

For the current reviewed-import activation path:

1. Open **LifeOS Bridge**, at `/lifeos-bridge`.
2. Open **Lasting memory** and claim the installation if no owner is configured.
3. Open **Import Hermes memory**, then select **Review Hermes memory** for the intended source.
4. Review each source entry, select **Review publication plan**, then **Apply reviewed import**.
5. Check that publication is `published` and required entries are verified.
6. Select **Prepare LifeOS ownership activation**. This creates the separate ownership workflow.
7. Open **LifeOS releases**, then **Advanced: memory ownership and removal**.
8. Review that workflow and select **Activate reviewed LifeOS ownership** when its checks pass.
9. Start a fresh conversation after activation and verify governed save and recall.

Review sources before importing them. Do not import unwanted material solely to expose activation. Preparing or selecting a fresh store does not activate ownership.

**Known empty-source limitation:** the current Bridge page hides **Review publication plan** when the review has no decisions. An entirely empty review therefore cannot complete this click-only activation path. Keep ownership disabled and report that state; do not fabricate an import or edit journals. The [tracked follow-up](../TODO.md#documentation-audit-follow-ups) requires an explicit empty/no-import activation path and its verification.

A separate owner review controls imports, remote readers, and return to Hermes. See [memory portability](memory-portability.md) and [HTTP MCP setup](http-memory-mcp.md). For Discord, verify the actual private audience before memory activation; see [Discord setup](discord-setup.md).

## Updates and interruptions

**Update LifeOS** and **Update plugin** both prepare the complete qualified integration. They follow the same review and apply flow. A preparation does not overwrite running programs, and duplicate preparations are refused while one is active.

If an operation is interrupted, keep its directory and journals. Use its current status and the offered recovery controls. The [update policy](update-policy.md) describes recovery, expired rollback, and qualification. Do not run independent upstream updates over a managed package.

## Earlier component installation

The [dated installation snapshot](history/2026-10-16-installation-workflow.md) preserves the earlier bridge-first controls, reduced stock-Hermes behavior, and component mounting design. Those controls remain implementation references. They do not replace this complete-package installation path.
