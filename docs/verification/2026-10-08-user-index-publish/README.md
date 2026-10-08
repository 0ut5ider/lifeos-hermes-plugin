# Native user index publication

Date: 2026-10-08. Bun is 1.3.14. The gate uses the prepared user-index publisher candidate.

The managed native CLI, exported lifecycle, and Markdown watcher use the owner publication service. The service admits current sources, runs the native index calculation, checks authority and source state again, and publishes only the fixed user-index cache. The cache has mode 0600. Direct native cache writes refuse in managed mode. Read-only queries do not publish. The original summary format and unmanaged command behavior remain intact.

The fixed user-index owner job uses the existing local account and model-route admission. This change adds no scheduled job. The pinned Pulse daemon does not register the user-index module. The authenticated Observability route remains the active index reader. The exported handler has no authenticated request argument, so managed data requests refuse there.

Publication binds the owner scope, exact sources, physical metadata, directory entries, and retirement state. Same-request retries return the committed index without rewriting the cache. Changed sources or later cache edits refuse the retry and preserve the later data. Read-only grants, missing owner context, revoked accounts, connector loss, symlink destinations, and hardlink destinations refuse publication.

The baseline runs five tests in 1.072 seconds. It reports three failures and one error. It demonstrates raw publication, mode 0644, retired-source disclosure, and the missing fixed owner job. The initial implementation then reports four failures. The [journal probe](journal-probe.json) records unchanged admitted sources and the transaction journal's entry in the owner directory. Source comparison now excludes exactly that journal filename. Discovery still counts it against the entry limit. Other directory entries remain part of the signature.

The expanded gate passes ten cases in 12.439 seconds. The lifecycle gate adds actual watcher publication, watcher revocation, hardlink refusal, native summary comparison, and changes after completed native rendering. Its first run fails because the observer imports the wrong context class. The corrected [lifecycle gate](lifecycle-final.txt) passes fourteen cases in 17.368 seconds. Warnings are errors.

A separate Python process exits with status 86 after the actual atomic cache replacement. The next service process recovers the previous cache from the retained journal. It preserves the edited source and removes the recovered journal. Separate rendering observers execute the real native calculation before changing source bytes or revoking authority. Both cases withhold output before publication.

The adjacent gate is recorded separately when it completes. Complete caller coverage, installed ownership acceptance, recurring jobs, current-package recovery, and combined release verification remain open. This candidate is not deployed during these checks.
