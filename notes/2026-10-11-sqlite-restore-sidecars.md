# SQLite sidecars during whole-guest restore verification

Date: 2026-10-11. Role: primary installation operator.

The first baseline restore coverage check expects `state.db-wal`, but the restored file is absent. The recorded WAL contains zero bytes. The main database has the exact recorded SHA-256 value, `07107aa24f1e6679f101704c3c93ae11309e5396a848d11b3b2e010f7e56cee7`.

An actual offline probe on restored container 103 checks the database before opening it, while it is open, and after the connection and cursor close. The WAL and shared-memory file are absent before opening. Both exist while the connection is open. Both disappear after closing. The main database hash remains unchanged in all three stages. The integrity result is `ok`.

The operator corrects the coverage recorder to checkpoint stopped SQLite writers and close cursors before recording file hashes. The verifier accepts a volatile sidecar only when the recorded WAL is empty, the current WAL is empty or absent, and the main database has its exact recorded hash. A nonempty recorded WAL still requires exact file verification. The baseline receipt identifies 648 exact files and two volatile sidecars separately.

A second operator assertion compares native `sqlite3.Row` objects to tuples. An actual transaction probe returns a row whose tuple value is `('ok',)`. The operator corrects the assertion to compare row values. The application code remains unchanged. The restored baseline then passes exact artifact, logical governance database, source, session, and program verification.

The first failed coverage traceback remains in the verification directory. The Proxmox restore completed before that operator assertion failed.
