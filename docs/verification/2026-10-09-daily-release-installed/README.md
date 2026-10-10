# Current daily package installed preparation

Date: October 9, 2026. Adrian selects the main Pulse dashboard only. This operator unit stages the complete current package in an isolated directory on .252. It does not select that package for the live profile or change the bot connection.

The [package identity](package-identity.json) records bridge commit 581d76a7, 197 bridge files, and three daily template files. The canonical Hermes and LifeOS candidates retain their pinned commits and bundled patch manifests. The [archive identity](archive-identity.json) records the 338,588,056-byte archive and its SHA256. The remote archive checksum matches. The package is staged under /home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7.

The [package validation](package-validation.txt) verifies both complete native source manifests, every selected bridge file, and every daily template. The current installed Python dependency inputs pyproject.toml, uv.lock, and pm/lock.json match the candidate bytes. The target Bun version is 1.3.14. This allows isolated runtime checks against the existing dependency generation without changing its selection.

The [local fresh-store gate](fresh-store-local.txt) passes both native cases in 20.535 seconds. Actual installation produces the selected Adrian and Cerebo names, no adopted facts, and disabled ownership and sharing. Original fixture stores remain unchanged. The [installed preparation](fresh-store-installed.json) runs the six native installation steps on .252, prepares the named store, and returns its signed review in 31.515 seconds. The bootstrap receipt records native version 7.40.4 and all twelve locked dependency packages. No candidate service starts.

The nested shell launcher writes the invalid completion marker n 0. The [original marker](fresh-store-installed-original.done) remains unchanged. It does not establish an exit status. The separate [revalidation](fresh-store-revalidation.txt) completes successfully through the actual FreshStore.review_home method. It checks the signed review and current owner binding. The review retains Adrian and Cerebo, zero active facts, and disabled ownership and sharing.

The [live preservation check](live-profile-preservation.json) compares the live configuration metadata and all three service states and paths before and after preparation. They remain unchanged. These operator probes read operational configuration and code paths. They read no live memory record or transport credential.

The first clean-worktree package attempt starts before worktree creation finishes. Its clean-source guard refuses. The operator waits for completion, checks clean status, and then prepares both canonical candidates successfully. This is an orchestration correction and changes no deployed code.

Installed application acceptance, scheduled execution, restart, current-package recovery, private-channel acceptance, version and combined review, and the separate daily guest remain open. The staged test store remains separate from the live fresh store. To retain or reverse this operator unit, stop any later acceptance units and archive the isolated staging directory. This unit changes no live configuration that needs restoration.
