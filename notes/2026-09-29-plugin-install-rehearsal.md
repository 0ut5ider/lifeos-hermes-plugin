# Plugin installation rehearsal on .212

Date: 2026-09-29. Account: `lifeos-plugin-install-probe` on `192.168.8.212`. This account had no LifeOS or Hermes data before the rehearsal. It is separate from the running `lifeos-hermes` account and gateway.

The plugin fetched public LifeOS commit `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. All nine bundled patches applied. The candidate manifest recorded its Git revision, patch hashes, and a working-tree digest. The fresh installer ran `InstallSettings`, `DeployCore`, `ScaffoldUser`, `LinkUser`, `InstallHooks`, and `ActivateImports`. It installed LifeOS 7.40.4 under a mode `0700` `.claude` directory. The resulting settings file had 11 hook event groups and 27 hook entries.

The first preparation attempt inherited `/home/outsider` as its working directory while running under the new account. Git stopped with `fatal: error reading '/home/outsider/.git'`. Running from the new account's workspace succeeded. The plugin Git helper now uses the target account's home directory when no source directory is specified.

The plugin then prepared a separate stock Hermes checkout at base `758ad514eb0e800547e015edf05aa18f78b78d82`. All 19 bundled patches applied in 3.1 seconds. The candidate manifest recorded the base, patch hashes, and tree digest. Preparation did not alter the stock checkout.

A release transaction staged the stock Hermes tree, plugin tree, synthetic Hermes config, and LifeOS system-file overlay. The overlay reported 2 updated files, 8 created files, and 1615 already current files. The transaction applied the candidate and passed a source hook check. It then restored the stock checkout. `git status --porcelain --untracked-files=all` was empty after restoration. SHA-256 hashes of synthetic `LIFEOS/USER/CONFIG/probe.txt` and `LIFEOS/MEMORY/probe.txt` remained unchanged. The LifeOS overlay made a `CLAUDE.md` backup in the test account, which remains for inspection.

This rehearsal had no Hermes gateway service or model route. It did not test a dashboard click, a service restart, a live turn, a Discord path, or all 74 hook registrations. It proves source preparation and a no-service transaction using real candidate trees, not full hook parity or a safe general-purpose patch button.
