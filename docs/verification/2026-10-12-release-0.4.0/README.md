# LifeOS 0.4.0 release qualification

PR14 is merged at `be215380dcbda35c92e6f28b23b4a1d7bc15004e`.
The stable version changes the five version declarations and release documentation.
The program logic is the reviewed PR14 implementation.
The published certificate will bind the exact stable archive and its qualification receipts.

The daily server remains on accepted 0.3.1 during qualification.
Existing 0.3.1 release assets remain immutable.

The initial version-check command omitted the required tests directory from `PYTHONPATH`.
One test could not import its helper.
The corrected command uses the existing test environment and passes all eight checks.
