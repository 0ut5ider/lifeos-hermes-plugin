# Service fixture isolation

Date: 2026-10-06. Machine: the development workstation. Services: synthetic user units only.

Three concurrently launched test processes share one actual user service manager. Distinct unit names do not isolate the manager state. Before fixture isolation, the retained second experiment runs 23 tests and reports one assertion failure and seven admission errors. The first experiment also fails. Neither experiment passes a regression gate.

The trace records `NeedDaemonReload=yes` while bound fragment and drop-in contents, paths, and timestamps stay unchanged. Admission correctly refuses that manager state. Two ordinary link and disable probes do not reproduce the flag. The enablement probe does: enabling another unit without a reload changes the bound unit from `no` to `yes`. Reloading restores `no`. The probe cleanup initially raises after a second disable. Its three fixture units are then explicitly stopped, disabled, and unloaded.

The installed systemd version is `259.9-1.fc44`. Its [unit reload check](https://github.com/systemd/systemd/blob/v259/src/core/unit.c) checks manager-wide outdated unit-file state before individual files. The [manager API](https://github.com/systemd/systemd/blob/v259/src/core/dbus-manager.c) sets that state after an install operation modifies unit enablement. This source explains the measured unrelated-unit effect.

`ProfileServicesTests` now holds one reentrant file lease for the entire fixture lifecycle. Nested fixtures share the lease. Separate processes wait before changing the shared manager. Each fixture still starts actual parent and child writers, drains their control groups, and tests interrupted recovery. Product admission remains unchanged.

The repeated concurrent launch passes all 23 tests: 13 service tests, five inactive-owner repetitions, and five restarted-host repetitions. The retained property traces contain no admission exceptions and only `NeedDaemonReload=no`. This is a focused passing gate. The complete regression inventory remains a separate gate.
