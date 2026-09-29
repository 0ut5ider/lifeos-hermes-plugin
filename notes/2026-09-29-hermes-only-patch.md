# Hermes-only patch worker probe

Date: 2026-09-29. Target: `lifeos-plugin-install-probe` on `192.168.8.212`, separate from the connected `lifeos-hermes` gateway.

The plugin staged the prepared 19-patch Hermes candidate against a clean stock checkout at `758ad514e`. The narrow snapshot covered 52 changed or added files and the Hermes config. A detached user systemd worker stopped the test gateway, copied only those files, started a new process, checked service activity, and ran `hermes config check`. The snapshot recorded `applied`. A second detached worker restored the stock files and restarted the service. The snapshot recorded `rolled_back`, and `git status --porcelain --untracked-files=all` returned no rows.

The Hermes-only worker made no LifeOS overlay. The existing VersionDrift baseline still reported zero changed files after apply. SHA-256 hashes for the synthetic `LIFEOS/USER/CONFIG/probe.txt` and `LIFEOS/MEMORY/probe.txt` files remained `d9912feeda679977785d364d4e115c7f1e6dbc27d3a96bd4dc5142e01ddb787d` and `f6063f6ca5ee718d1372828e04af9c8156e3ef4933fc86946d4dd6991e747a62`.

The page action and status polling have API and UI tests, but this probe launched the same worker command directly from the shell. It did not click the page, make a model call, verify Discord, or compare all LifeOS hooks. The test service must be uninstalled and user linger disabled after the remaining service probes.
