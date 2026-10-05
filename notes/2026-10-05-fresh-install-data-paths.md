# 2026-10-05: A separate program root still links the current data store

The selected `.212` experience must start without existing facts. A direct native scaffold and link experiment uses separate synthetic current and selected homes. Both tools exit zero, but the selected `.claude/LIFEOS/USER` link resolves to the current home's `.config/LIFEOS/USER`. The selected store exposes the retained synthetic marker.

The plugin installer supplies `--config-root` but preserves the parent `HOME` and `LIFEOS_CONFIG_DIR`. Native ScaffoldUser and LinkUser derive their user-data destination from those inherited values. InstallSettings expands template paths from the same inherited home. A separate program directory therefore does not establish a separate native store.

The correction must bind child home and native configuration paths to the selected installation. Native scaffold and link controls must confirm a new target and preserve the original store. A passing program-root check alone cannot verify fresh data isolation. The initial small payload test lacks the atomic-write dependency of native InstallSettings; retain that fixture failure and fix the fixture before evaluating the regression.

The corrected focused gate passes 12 tests. A second control completes all six native installation steps with LifeOS 7.40.4 and all ten patch groups. The selected USER link and installed environment paths identify the new home. The original synthetic store retains its exact file hashes. Native deployment still leaves MEMORY in the program tree, so complete governed-memory setup remains required.
