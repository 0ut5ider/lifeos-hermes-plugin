# Profile backup scope

Date: 2026-10-05. An independent review reports that the profile backup cannot complete on a real profile. The backup copied the complete Hermes home under a 256 MiB limit. The active `.212` profile measures 8.6 GB. Adrian approves a backup of user state with recorded exclusions. Production on `.212` stays unchanged.

## Scope

The backup now copies every profile entry that is not classified as excluded. It records each excluded entry in the manifest.

| Reason | Entries | Rule |
| --- | --- | --- |
| `regenerable` | `installs`, `tools`, `cache`, `image_cache`, `audio_cache`, `logs`, `hermes-agent`, `models_dev_cache.json`, `models_dev_cache.etag` | Top-level name |
| `other_profile` | `profiles` | Top-level name |
| `dependencies` | Each `node_modules` directory below the top level | Directory name at depth two or more |
| `runtime` | Top-level names that end in `.pid`, `.sock`, or `.lock`, and each socket at any depth | Name or file type. `bun.lock` is content and stays in the backup. |

The top-level `node_modules` directory stays in the backup. The recovered native tools use it, and it measures 0.7 MiB on `.212`.

The manifest version is now 2 and has the `excluded` list. Inspection refuses a version 1 manifest, an unknown reason, a path outside the profile, and a copied path inside an excluded entry. The recovery receipt carries the list, so the operator can see what a restore must install again. The `create` result reports the number of excluded entries.

When the copied bytes exceed the limit, the backup raises `ProfileBackupTooLarge`. The error and the `lifeos-backup` command name the five largest top-level entries.

## Change from the approved recommendation

The recommendation said that the backup refuses an unclassified top-level entry. The implementation copies an unclassified entry instead. An existing requirement keeps unknown owner files in the backup, and a refusal would lose that protection. A new Hermes state directory is therefore copied without a plugin update. A new large regenerable directory stops the backup at the byte limit, and the error names it. No entry is dropped silently.

## Measurement on the real profile

[real-profile-measure.json](real-profile-measure.json) is a read-only walk of `/home/lifeos-hermes/.hermes` on `.212` with the new rules. It runs as the profile owner and writes nothing in the profile.

- 2,960 files and 29.6 MiB are in scope. The limit is 256 MiB.
- 31 entries are excluded and recorded.
- The first walk failed on a socket in `state/`. That result added the rule for sockets at any depth.

This measurement checks the scope only. A complete backup, an inspection, and a recovery of the real profile are not run yet, because they need the selected lasting-memory configuration.

## Verification

The three new tests fail before the implementation ([before.txt](before.txt)). The final gate passes 71 tests across the backup, recovery, ownership, and command suites ([after.txt](after.txt)).

## Limits

- A restore needs a new installation of Hermes, the plugin, the tool programs, and the nested dependency directories at the recorded versions. No test covers that reinstallation yet.
- No earlier backup can be read, because the manifest version changes. No production backup exists.
- The rule list reflects the `.212` profile of this date. Another Hermes version can add entries that need a classification.
