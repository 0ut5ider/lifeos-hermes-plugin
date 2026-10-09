# Operational history growth baseline

Date: 2026-10-08. The baseline uses the fixed operational-views-third candidate and its independent original native control.

The native algorithm reader folds complete work-event history. It keeps up to 200 movement points per run and then keeps the 500 most recently moved run series. It does not restrict the complete event file to one MiB or 2,048 records. A quiet active run can therefore retain a progress curve from an event before the reader's recent tail window.

Two actual authenticated HTTP cases reproduce the managed limit. A 2,051-record log contains 336,357 bytes. A 5,001-record log contains 1,320,157 bytes. Each file starts with a current quiet run's movement event. Later rows describe a different run. The independent native response retains the first run's one-point curve. The managed response returns 503 in both cases. baseline.txt retains the exact inputs' measured sizes and the two failed assertions.

The correction must preserve the native all-time fold. It must continue to exclude private and retired event records and check current source identity and authority before delivery. It must retain bounded per-record validation, private temporary processing, native response limits, and cancellation. Truncating the source to a recent tail would remove the measured quiet-run curve and would not meet this acceptance case.

No large-history implementation or passing growth result exists at the time of this baseline. The operational route boundary and asynchronous stream have separate accepted focused evidence. This growth case remains a daily-release gate.
