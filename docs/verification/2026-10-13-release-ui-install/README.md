# Hermes installation and update controls

The 0.4.2 test prereleases add **Install LifeOS**, **Update LifeOS**, and **Update plugin** to the LifeOS releases page. Both update actions prepare the complete qualified integration. The owner reviews its operation, commit, and package hash before installation starts.

## Package qualification

The first package uses program commit `914ad24b0eea7f0022e75edc815f5be08566d0f9` and archive SHA-256 `5fe78efb7dc45ee4cf6e49766c7e72c8f64e0d0113fd3643290e75adc6d8ebdb`.

- [The official native gate](native-sealed-914ad24b.json) passes all 716 tests across 38 files. The extracted native source remains unchanged.
- [The archive-bound integration gate](integration-archive-bound-914ad24b.json) passes all 661 tests. All 21,085 archived regular files match before and after testing.
- [The version derivative check](corrected-numeric-update-version-delta.json) compares both actual archives. The second package changes five version declarations, the changelog, and their authenticated release metadata. Native source manifests and dependency closures remain identical.
- [The independent evidence review](../../agents/2026-10-13-pr18-release-ui-review-12/pr18-release-ui-review-12.md) is clear. Six archive-binding controls pass.

The second package uses program commit `6a0a241a0b1227d440938aa7156d8d59b87e5740` and archive SHA-256 `6fd4a6af3e1fa37f0b57b8db86daf4b72974d0f0993b4d12cba583c84575cbe6`.

Both [published prereleases](public-prerelease-assets-verified.json) have immutable archives, dashboard assets, and certificates. Release 0.4.1 remains the latest stable release. The certificates qualify synthetic managed-dashboard installation and complete-package updates. They do not qualify daily deployment or automatic memory activation.

## Actual installation controls

The stock Hermes web form installs the 0.4.1 release manager from the public GitHub URL. The native web form also installs the candidate manager from a local checkout of the public feature branch. Hermes chat reloads the dashboard after manager replacement.

[Actual fresh interruption and recovery](baseline-preserved-fresh-recovery.json) pass on container 106. Recovery preserves a later synthetic file and restores the managed dashboard. [The private complete-package update](baseline-preserved-private-update.json), [numeric update](corrected-numeric-private-update.json), and [numeric rollback](private-numeric-rollback.json) pass on container 105.

The public [Install LifeOS](public-installation.json), [Update LifeOS](public-lifeos-update.json), and [numeric rollback](public-numeric-rollback.json) checks pass. [Hermes chat prepares](conversational-public-preparation.json) the public numeric update, and [the owner dashboard applies it](conversational-public-update.json). After restart, [Hermes reports the applied state](conversational-public-post-update.txt), and [the version command verifies the installed plugin sources](conversational-public-version.json). The public [Update plugin action](public-plugin-update.json) also passes a numeric update. Both installed plugin versions match 0.4.2-rc.2, and the reviewed transaction changes the Hermes launchers. The later synthetic file and its permissions remain intact. [PROGRESS.json](PROGRESS.json) records the current operations. The primary public test guest is container 106 at `192.168.8.249`. The conversational update runs on container 105 at `192.168.8.250`. After safe evidence export, [cleanup removes](diagnostic-guest-cleanup.json) diagnostic containers 103, 104, and 105. Container 106 remains available for the post-merge replay. Neither test guest imports personal data or contains a Discord credential. [The final development and daily health check](existing-guests-final-health.json) confirms the same release identities and all three service process identifiers.

[The combined public acceptance receipt](PUBLIC-USER-ACTION-ACCEPTANCE.json) records all five action cases and exact evidence hashes. [The publication receipt](public-user-action-asset-publication.json) verifies the new acceptance asset on both prereleases. Existing release assets and certificates remain unchanged. Their pending acceptance field records the earlier publication checkpoint.

## Measured corrections

Actual trials identify and correct isolated Python bytecode writes, flow YAML formatting, systemd unit syntax, recovery lease identity, retained-worker verification, unchanged service publication, and an unchanged-native baseline timestamp. The native test fixture also drains its queued log writer before it removes its temporary home.

The package checks bind extracted manifests and retained worker files to the authenticated archive. First installation drains the stock dashboard through a separate worker service. Missing gateway and Pulse definitions enter the reviewed transaction and remain disabled and inactive. Existing model and tier settings stay in place.

An incorrectly quoted provisioning command replaces the Proxmox SSH authorization file. [The recovery receipt](host-key-recovery.json) verifies restoration of the exact prior file. A cloned guest receives the development address through DHCP. [The address correction receipt](existing-guests-after-clone-address-correction.json) verifies disconnection, a static test address, and unchanged development and daily program identities. Key contents and credentials do not enter the evidence.

## Limits and next gate

The native web form has no revision field. A GitHub tree URL does not select a branch or commit. Installation of the new controls from the default public GitHub URL therefore requires PR18 to merge. That replay remains a separate post-merge gate.

First installation requires an authenticated Linux owner dashboard user service, supported physical paths, and a package with the first-installation service interface. A foreground dashboard and historical packages without that interface refuse preparation. Existing installation updates keep their three-service checks.

These tests do not activate memory ownership, configure Discord, import personal data, or deploy a test release to `.252` or `.253`. Whole-guest backup and daily production acceptance remain release requirements before a daily update.
