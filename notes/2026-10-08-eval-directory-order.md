# Evals directory order

2026-10-08. The native Evals reader enumerates suite directories, then sorts results by timestamp. Equal timestamps retain enumeration order.

A disposable Linux directory contains eight names, including Greek, accented, emoji, hidden, and draft names. Bun 1.3.14 `readdirSync` and Python `os.listdir` return the same directory order. UTF-16 sorting returns a different order. The observation is in `docs/verification/2026-10-08-pulse-module-audit/registered-directory-order.json`.

The admitted reader must preserve the selected enumeration order before the native timestamp sort. It must still exclude native hidden and draft entries. A deterministic alphabetic sort would change native results for equal timestamps. This measurement covers the current Linux and Bun versions. It does not establish ordering on another filesystem or runtime.
