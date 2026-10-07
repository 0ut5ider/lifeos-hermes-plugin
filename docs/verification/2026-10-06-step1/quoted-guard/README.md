# Shell quote regression through actual clients

Date: 2026-10-06. Target: isolated accounts on `192.168.8.252`.

Both actual clients submit the Python literal write with shell quote concatenation. The installed guard exits 2. Neither command executes, the prior protected content remains intact, and the model receives the denial before its final response.

The final sources include 11 Hermes patches and 14 LifeOS patches. The frozen runner, hook dependencies, native CLI, plugin files, and actual wire hashes are retained. The first trial submits a simplified Hermes command instead of the exact requested quote encoding. That trial remains failed on the server. The repeated trial explicitly preserves every command character and passes both clients.

The direct native scanner reproduction before the shell literal correction is retained in the adjacent guard-parser evidence. These controls measure literal target discovery. Indirect variable values and copied-file contents remain native scanner limits.
