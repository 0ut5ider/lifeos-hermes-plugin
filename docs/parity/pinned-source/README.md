# Historical hook evidence source

Date: 2026-10-05. The effect ledger originally hashes the active `patches/hermes-plugin-events.patch` and its packaged copy. Later memory work changes both files. Those active paths no longer identify the historical tested source.

The [retained patch](hermes-plugin-events.patch) has SHA-256 `c0a94b49f5e26b4fa45c809eafc1212e27c5c018501535159e1ce46d82f79ee2`. Git revision `968de9d58e8aa9b068bae766f2a94c78766bee0f` contains these exact bytes at `patches/hermes-plugin-events.patch`. Revision `b02c53637d8d31569541608bd29af0da97e34f8b` contains the same packaged copy. The primary verifies both against the existing ledger hashes before replacing the two mutable artifact paths with this retained file.

This file preserves historical evidence. It is not the current installation patch. The October 5 successful-response bundle separately records its prepared source identities.
