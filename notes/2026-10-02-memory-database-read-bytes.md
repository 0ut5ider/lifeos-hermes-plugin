# A metadata read changes the update restore fingerprint

Date: 2026-10-02

The isolated browser installation applies a real same-revision update successfully. Its subsequent restore preflight finds two changed paths. Both paths resolve to the same `STATE/memory-access.sqlite` file through the native USER and MEMORY links. No other user file differs.

The initial explanation was that a memory operation changes stored records. An isolated database test disproves that explanation for the connection opener. The SQLite dump is identical before and after opening the database. The database bytes differ in the header counters.

`NativeMemory._connect` executes `PRAGMA user_version=4` on every open. SQLite writes the database even when the assigned version is already 4. The regression reproduces the change in 0.005 seconds. The conditional assignment preserves every byte in the same test in 0.003 seconds. Initialization and schema migration still set the version.

The restore guard continues to compare all user data. We do not replace the historical snapshot digest to make the live restore pass. The installed browser control refuses the changed snapshot with HTTP 409. It preserves the request, update status, and running gateway. A fresh live successful restore remains a separate acceptance case.
