# Stock Hermes installs, updates, and restores the plugin

Date: 2026-10-05. This unit installs the plugin into stock Hermes with the normal Hermes installer in the disposable guest CT `100` on `192.168.8.101`. Production on `.212` stays unchanged.

## Steps and results

1. Stock Hermes: `install.sh --commit 758ad514… --non-interactive --skip-browser` as the user `hermes` on Ubuntu 24.04. The first run fails: the bundled Node program needs `libatomic.so.1`, which the stock Ubuntu container image lacks ([install-output-first.txt](install-output-first.txt)). After `apt-get install libatomic1`, the second run completes at `758ad514` ([install-output.txt](install-output.txt)).
2. Admission: `hermes plugins install https://github.com/0ut5ider/lifeos-hermes-plugin.git#lifeos_hook_bridge --ref d44fccd… --enable`. The scan result is `Allowed (clean scan)`, and the plugin installs pinned to that commit ([plugin-install.txt](plugin-install.txt)). The non-interactive run skips the dependency install.
3. Enable: `hermes plugins enable lifeos-hook-bridge` with consent installs the four declared Python dependencies and enables the plugin ([plugin-enable.txt](plugin-enable.txt)).
4. Validation: `hermes plugins validate` passes every check, including the capability probe and the security scan ([checks.txt](checks.txt)). A one-shot turn against private FlashNext answers `READY`.
5. Update: `hermes plugins update` refuses a pinned plugin and names the supported command. `hermes plugins install … --force --ref c565857…` replaces the code, keeps the plugin enabled, and changes the pinned commit ([plugin-update.txt](plugin-update.txt)). A turn answers `READY`.
6. Restore: the same command with `--ref d44fccd…` returns the earlier code; the `bridge.py` digest matches the first installation ([plugin-rollback.txt](plugin-rollback.txt)). A turn answers `READY`.

Two guest snapshots retain the states: `hermes-stock-758ad514` and `plugin-d44fccd`.

## What this does not cover

- On stock Hermes without the plugin's host patches and without LifeOS, the plugin registers no hooks. `hermes plugins doctor` reports `0 hook(s)` and warns about each declared hook. The plugin works in reduced mode only.
- The patched Hermes host, the LifeOS installation, the coordinated update of the plugin, Hermes, and LifeOS as one package, interruption during replacement, and later user data are not tested here.
- `libatomic1` is a host prerequisite of Hermes, not of the plugin. The installation guide must name it for minimal Ubuntu images.
- The guest has outbound Internet access for the Hermes and plugin downloads.
