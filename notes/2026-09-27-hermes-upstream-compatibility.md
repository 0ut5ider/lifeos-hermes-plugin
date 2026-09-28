# 2026-09-27: The core patch still applies to newer Hermes

The isolated `.212` runtime uses the Hermes test branch based on commit `758ad514e`. The public Hermes HEAD moved to `bac0c45d8593ed9d53a8e3fcacecdc920b71a2c4`, so clean application of the core patch could not be assumed.

A temporary checkout of that public HEAD accepted [the core patch](../patches/hermes-hook-controls.patch) with `git apply --check`. The patched checkout ran five focused Hermes test modules using the isolated account's existing Python environment: 116 tests passed. The installed LifeOS bridge then passed the native TaskCreated probe and produced a routed watchdog `watch_match` event from a real async delegation record against the newer checkout. The route used a synthetic Discord chat ID.

The active `.212` dashboard remains on its original patched test branch. The newer checkout was a temporary verification tree. A direct Discord delivery test and a full Hermes suite on the newer checkout have not been run.
