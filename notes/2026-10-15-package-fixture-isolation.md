# Service diagnostics and immutable package checks

Date: 2026-10-15.

The actual removal-service control passes while rewriting a tracked diagnostic inside its checkout. The complete package verifier independently checks every archived file after the tests. Those checks have different purposes. A successful behavioral assertion cannot establish package immutability when a fixture changes a packaged evidence file.

A dedicated control runs the actual service test and compares the diagnostic bytes before and afterward. The first control fails after the nested test succeeds. The recorded hashes differ because the output contains a newly generated synthetic unit identifier. The control saves that changed diagnostic privately and restores the exact initial fixture. The product services are synthetic and use the existing test lock.

The test now writes the same diagnostic under its private temporary home. The dedicated isolation control and all three service controls pass with clean output. The archived checkout file stays byte-identical. The new committed archivebb947b4a includes this fixture correction and starts a full integration repeat. The earlier archive4db55b09 remains separate historical evidence and does not qualify the corrected package. No product behavior or daily deployment changes through this correction.
