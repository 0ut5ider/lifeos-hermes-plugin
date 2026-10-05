# Authenticated fresh-store preparation

Date: 2026-10-05. The candidate exposes `POST /memory/fresh/prepare` under the LifeOS plugin API. It accepts `principal_name` and `assistant_name`. The server selects the prepared source and the private destination. Production on `.212` stays unchanged.

The [native HTTP test](http-output.txt) passes through actual Hermes password sessions and all six LifeOS installation tools. It returns Adrian and Cerebo with zero active facts. The [review metadata](authenticated-fresh-review.json) retains the source revision, dependency catalog hash, new data path, and original return destination. The current selected root, original Hermes bytes, and missing USER memory file stay unchanged.

The route refuses five path or account override fields with HTTP 400. It refuses cross-origin requests and revoked owner bindings with HTTP 403. Missing prepared source returns a generic HTTP 409 without exposing its source path. Successful reviews and route errors carry `Cache-Control: no-store`. Hermes's outer authentication middleware returns a generic HTTP 401 before plugin routing for a missing session. That host denial does not carry the plugin cache header or any fresh-store metadata.

The [four neighboring tests](neighbors-output.txt) pass for established import review and memory dashboard behavior. The [expected before control](before.txt) uses the committed source at the recorded parent revision. It returns HTTP 404 for the missing route. Two earlier fixture assumptions remain recorded: the ordinary import fixture has no USER.md, and the host's outer authentication response has no plugin cache header. The corrected test checks preserved absence and the generic host denial.

Run `python3 docs/verification/2026-10-05-fresh-store-http/verify.py` to check the artifact and source hashes. The command records identify the actual native and Hermes sources. The [detached worker](run-http-tests.py) and [exit marker](http.done) retain the native test result.

This endpoint performs preparation in a request worker. It does not provide a page button, restart-safe background preparation, interrupted preparation recovery, review listing, selected-store cutover, ownership activation, or return acceptance. The integration must complete those workflows before release. The [complete release plan](../../full-experience-release-plan.md) retains the other open gates.
