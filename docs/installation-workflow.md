# Install LifeOS into your Hermes

LifeOS installs into the Hermes you already run. The release manager plugin checks that your Hermes is a supported version, downloads the LifeOS integration (about 2 MB plus the pinned LifeOS source), and patches your Hermes checkout in place. It never replaces Hermes, its Python environment, or your other plugins and tools.

The [0.7.x managed-runtime guide](history/2026-10-17-managed-installation-workflow.md) describes the earlier complete-package releases. [Source preparation](clean-install.md) is a separate development workflow.

## What a supported Hermes looks like

- Hermes `v0.21.7` (commit `71d34bad`), installed with the official installer as a Git checkout that your account owns.
- No local edits to the Hermes source. Files that Git ignores, such as the Python environment, are fine.
- One profile. Named profiles under `~/.hermes/profiles` share the source and are not supported yet.
- Linux with systemd user services. The stock gateway unit from `hermes gateway install` is supported.

Open **LifeOS releases** (or run `hermes lifeos-release compatibility`) to see the result for your installation. The check reads your Hermes and changes nothing. When it refuses, it names the reason: a different Hermes version, changed files, extra profiles, a dependency conflict, or an unsupported layout. Upstream Hermes moves quickly; a newer Hermes needs a LifeOS release that qualifies it.

## Install the release manager

1. Open the Hermes **Plugins** page.
2. Install this GitHub subdirectory URL:

   ```text
   https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager
   ```

3. Enable **lifeos-release-manager**, then restart the Hermes dashboard so it loads the plugin page.
4. Open **LifeOS releases**, at `/lifeos-releases`.

Hermes can report a CAUTION verdict because the manager runs processes and manages user services. Read the findings against the selected source before you confirm. For a pinned command-line install, use the full program commit from the release record:

```bash
hermes plugins install 'https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager' --ref FULL_RELEASE_COMMIT
hermes plugins enable lifeos-release-manager
```

## Prepare, review, and apply

1. Check that **Hermes compatibility** says LifeOS can be installed.
2. Select **Install LifeOS** and enter the user and assistant display names.
3. Wait for preparation. It downloads the release, fetches the pinned LifeOS commit, stages the Hermes patches, and resolves the bridge's Python packages against your environment. Nothing in your installation changes.
4. Select **Review release**. The review lists:
   - the Hermes files that change (69 changed and 27 added for `v0.21.7`) and the update hold;
   - the Python packages that are added (`tree-sitter` and `tree-sitter-bash`; preparation refuses when an existing package would change);
   - the services that restart, and any user service that is created;
   - the tested scope.
5. Select **Install this release**.

The worker then stops every Hermes process that uses the source, patches the files with a journal, adds the packages through Hermes's own environment manager, installs LifeOS, restarts the services, and checks that the restarted gateway loaded LifeOS with the patched hooks. Any failure restores the earlier files, configuration, and environment.

If the dashboard or gateway runs by hand rather than as a user service, the review offers to create its standard user service and stops the hand-started process during installation. Close any interactive Hermes sessions first; the installer refuses to patch files that a running session uses.

Check the result:

```bash
hermes lifeos-release status IDENTIFIER
hermes lifeos-version
```

An `applied` operation and a `verified` version establish installation.

## While LifeOS is installed

`hermes update` refuses with a LifeOS hold message, because an update would move the patches onto an untested Hermes version. Update LifeOS from the releases page instead. When a LifeOS release supports a newer Hermes, its notes say how to move.

The releases page reports `host_drift` if a patched Hermes file changes or Hermes disables the bridge plugin. LifeOS does not repair drift silently.

## Ask Hermes to install or update

The manager registers the [`lifeos-release` skill](../optional/lifeos_release_manager/skills/lifeos-release/SKILL.md). Ask Hermes to check compatibility, install LifeOS, update it, or recover an interrupted operation. The owner still reviews and applies each operation in the dashboard, because LifeOS's native memory mount needs the owner's grant.

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

## Updates, interruptions, and removal

**Update LifeOS** and **Update plugin** download the newer integration and move the patched files from the recorded state to the new one. They follow the same review and apply flow. **Restore prior programs** returns to the previous release.

If an operation is interrupted, keep its directory and journals and use the offered recovery control. A first installation that stopped after LifeOS was initialized finishes forward; any other operation rolls back.

Complete removal follows a verified return to built-in memory. It restores the original Hermes files from the copies kept at installation, removes the update hold and the LifeOS plugins, returns the configuration values that LifeOS changed (keeping any you changed since), and rebuilds the Python environment without the bridge. It disables Discord, because stock Hermes lacks LifeOS's private-channel restrictions. See [update policy](update-policy.md) for recovery boundaries.

## Moving from a managed 0.7.x installation

A 0.7.x installation runs Hermes from a private runtime under `~/.hermes/.lifeos-releases`. To move to an in-place installation:

1. Back up the account, or take a guest snapshot.
2. Install stock Hermes `v0.21.7` with the official installer and `--skip-setup`. Your profile, configuration, Discord settings, and memory stay where they are.
3. Update the release manager plugin, then open **LifeOS releases**. It shows that the next update moves LifeOS to the stock installation.
4. Prepare, review, and apply **Update LifeOS**. The operation patches the stock checkout and points `hermes`, `hermes-agent`, and `hermes-acp` at it. Restoring it returns to the managed runtime.
