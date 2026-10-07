# Successful hook response controls

Date: 2026-10-05.

The first authenticated response run failed all three paired startup cases. The native client sent `/v1/messages?beta=true`. The test relay admitted only the exact path `/v1/messages` and returned HTTP 401 before the private gateway received the request. All three Hermes main turns returned `READY`. The failing pair prevented a false success claim.

The request record also exposed a second inference call from Hermes. Its automatic session title upgrade ran after the main turn. One title request returned HTTP 500, while two returned HTTP 200. The selected startup comparison needs one main turn, so its isolated configuration disables the supported title model upgrade. This scope does not verify title generation. Step 5 must test auxiliary model routing separately. Production configuration and tier mapping remain unchanged.

A real HTTP transport regression reproduces the query rejection: expected HTTP 200, observed HTTP 401. The relay now admits the parsed endpoint path and forwards the original query. The regression also checks exact request and response bytes, model substitution, and exclusion of credentials from records. The focused candidate suite passes 36 tests. The second real paired run passes all three pairs and all six clients. Each main request returns HTTP 200 and each client delivers `READY`. The primary verifies exact request and response byte hashes and all marker assertions.

The second run still logs a development recorder startup warning. The reused Python interpreter has a startup file that pins the recorder to another account root. The sandbox denies that recorder's write. A third run uses a private interpreter copy without that startup file and passes all six clients without the warning. The installed interpreter remains unchanged. The final focused suite passes 38 tests. The evidence bundle preserves the earlier run and points its ledger claims at the final run.
