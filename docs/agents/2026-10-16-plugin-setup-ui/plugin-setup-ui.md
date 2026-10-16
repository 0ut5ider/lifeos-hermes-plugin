# Plugin setup UI evaluation and implementation

Date: 2026-10-16
Role: UI evaluation and implementation agent
Question: How can the complete LifeOS plugin setup experience show clear actions, fields, and sections?
Model: gpt-6.1-sol, inherited model and reasoning configuration

## Measured cause

Both plugin manifests omit the optional `css` entry. The compiled Hermes host explicitly loads that entry in `web/src/plugins/usePlugins.ts`, lines 104 through 113. Many Bridge buttons have no class. Other controls depend on utility classes generated from the host source. The plugin does not provide its own stylesheet.

The primary agent measures the installed host before implementation. Enabled plain buttons have transparent backgrounds, zero border width, and zero padding. No LifeOS stylesheet is loaded. This matches Adrian's screenshot.

## Complete control inventory

The Bridge retains all 58 button call sites. The release manager retains all 11 button call sites. Every original button label expression remains present with the same count. `action-inventory.json` records the labels and handler paths. Some expressions render several buttons, so these numbers describe source call sites, not one screen's visible buttons.

The Bridge retains these functions:

- Check memory status and claim an unconfigured installation.
- Set the HTTP origin, enable HTTP, show the connection URL, and disable HTTP.
- Set each connection's name, projects, declared model route, and optional permissions.
- Review pending OAuth requests, approve or deny them, and return to the requesting agent.
- Create a manual token, display it once, hide it, and revoke existing HTTP connections.
- Clear unused OAuth registrations.
- Review Hermes memory, upload profile files, upload portable bundles, and resume saved imports.
- Review import entries and publication plans, apply reviewed imports, and prepare ownership activation.
- Review reverse exports, select items, review capacity, create an export, and download it.
- Prepare a reviewed provider return with a replacement Hermes prompt.
- Preview existing LifeOS sources, assign projects, paginate sources, and add reviewed sources.
- Search governed facts and inspect fact references.
- Review pending preference changes, accept, reject, edit, and record an outcome applied elsewhere.
- Enable or disable sharing, inspect SSH connections, add a permitted SSH connection, and remove credentials.
- Prepare fresh stores, inspect their state, select a store, return to the prior installation, recover, and remove a store.
- Prepare, install, update, restore, and recover LifeOS programs.
- Prepare, apply, restore, and recover the tested Hermes extension.
- Select each tier's provider/model and effort, configure Stop behavior and a pinned tier, and save settings.
- Preview and review baseline files, create a baseline, and renew it.

The release manager retains these functions:

- Choose a release version and initial owner/assistant names.
- Prepare an installation, a LifeOS update, or a plugin update.
- Refresh operations, review prepared releases, and explicitly approve installation.
- Restore prior programs and recover interrupted operations.
- Review ownership activation, provider return, and complete removal.
- Require the Discord acknowledgement before preparing complete removal.
- Display the recovery command and restore provider settings or integration software.

## Presentation changes

Each manifest declares `dist/style.css`. Each plugin includes the same scoped stylesheet because the release manager can be installed independently. Every rule targets a `.lifeos-setup` root. The stylesheet does not rely on generated utility classes or external imports.

The stylesheet uses the current host's `--midground-base` and `--background-base` theme colors. It avoids the host's transparent `--foreground` token. It defines visible button surfaces, borders, minimum target sizes, primary and destructive actions, disabled states, and keyboard focus. It defines field labels, inset form controls, disclosure headers, section cards, notices, and responsive grids.

The Bridge page provides labelled navigation for lasting memory, agent access, memory stores, installation, models, and release maintenance. Model tiers use a two-column grid on wide screens. Stores, migration, SSH connections, and source-baseline maintenance use named disclosures. Existing installation and recovery controls remain available.

The HTTP workflow has four groups:

1. Set the connection address.
2. Choose the agent permissions.
3. Review sign-in requests.
4. Inspect connected agents.

The approval button links to a visible explanation of missing permissions. Manual token creation has a separate Advanced disclosure. The permission fields sit outside the manual-token form. Pressing Enter while editing OAuth permissions cannot submit a hidden token action. The explicit token action sends the same request as before.

The release page separates preparation from operations and installation review. It explains why preparation is unavailable. Advanced memory ownership and removal controls remain in their own disclosure. Complete removal keeps its required acknowledgement and uses a destructive button style.

## Verification

The initial regression run reports seven tests: three pass and four fail. The failures identify absent manifest stylesheets, absent scoped navigation, and absent linked approval guidance. `component-tests-red.txt` retains the raw output.

The final component run reports 42 tests, all passing, with no skips. `component-tests-green.txt` retains the raw output. Both authored JavaScript bundles pass `node --check`. `git diff --check` passes.

The existing SDK tests use controlled API responses. They verify component and request contracts. They are not end-to-end tests. The parent agent separately verifies the actual compiled dashboard in the browser, with all non-GET actions blocked.

No package manager, transpilation step, or frontend dependency is added. These plugin bundles are authored directly as Hermes SDK JavaScript.

## Exact implementation files

- `lifeos_hook_bridge/dashboard/dist/index.js`
- `lifeos_hook_bridge/dashboard/dist/style.css`
- `lifeos_hook_bridge/dashboard/manifest.json`
- `optional/lifeos_release_manager/dashboard/dist/index.js`
- `optional/lifeos_release_manager/dashboard/dist/style.css`
- `optional/lifeos_release_manager/dashboard/manifest.json`
- `tests/test_memory_remote_ui.cjs`
- `tests/test_setup_presentation.cjs`

The primary agent owns the README change, measured browser evidence, and engineering note. This agent does not edit those files.

## Limits and external changes

No server, owner grant, memory record, credential, scheduler, model mapping, or backend policy changes. No deployment, push, merge, or commit. The primary agent must complete browser verification and release qualification before deployment.

The main review risks are the placement of advanced controls, the theme-token adaptation, and the visibility of disabled-action explanations. All original action labels and API request contracts remain available for comparison.
