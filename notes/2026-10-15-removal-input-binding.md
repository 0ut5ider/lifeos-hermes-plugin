# Bind transformed inputs before publication review

Date: 2026-10-15.

The removal preparer generates stock config.yaml and .env outputs from the current files. It then asks ProgramTransaction.prepare to capture the before-images. The independent review edits both input files between these steps. The transaction accepts the newer files as its original state, applies the older transformed outputs, and reports success. Both later owner settings disappear.

The fix passes explicit expected-before identities into transaction preparation. The identities describe the inputs used for transformation. The transaction refuses a mismatch before recording a plan. Native inventory supplies its admitted software and settings identities. The preparer binds plugin identities to its exact retained copies and launchers to their qualified generation.

The primary reproduces all four preparer findings before correction. The other three controls demonstrate a Bun executable with basename argv[0], a service with %h paths, and a hook with ${HOME}. Consumer checks now inspect the executable path and normalize supported home forms. The adapted original controls and the broader transaction, native inventory, consumer, and preparation tests pass all 38 tests.

This result does not certify a complete installed removal. It establishes the transformed-input contract and the measured consumer boundaries. The disposable installed flow and final independent review remain required.
