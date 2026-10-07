# Actual SSH and Docker adapter controls

Date: 2026-10-06. Target: development container `192.168.8.252`. Production configuration is unchanged.

All 19 selected tests pass with no skips. They exercise actual SSH and Docker processes, installed plugin discovery, native Safety and ISA programs, backend-bound project trust, path aliases, remote HTTP hooks, asynchronous hooks after parent exit, nested file tools, web caches, and file-view tracking. These tests do not use model responses.

The command manifest binds the copied plugin and test source hashes, prepared Hermes path, native hook path, and immutable container image. The container uses a pinned Python base image and the actual `curl` package recorded in `container-packages.json`. The SSH fixture uses a temporary key authorized only on the development host. The export contains the key path but no key data.

The first run passes 16 tests and fails three fixture checks. Two nested tools lack the installed default plugin profile. One container HTTP hook lacks `curl`. The final run prepares that profile and uses the pinned image with `curl`. The tests capture and assert intentional trust warnings. The command-policy fixture disables an unrelated container disk quota request.

Docker and temporary SSH authorization are test tooling on the development host. They remain available for the rest of Step 1 verification. The final cleanup removes the test authorization and owned test containers. No production Docker project is enabled.
