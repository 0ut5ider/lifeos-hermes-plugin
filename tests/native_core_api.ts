// ABOUTME: Checks real dashboard HTTP errors and owner-denial callbacks without replacing fetch.
// ABOUTME: Preserves successful responses and ordinary conflicts while reporting revoked access.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const base = process.argv[2];
assert.ok(base);
const api = await import(pathToFileURL(`${base}/src/lib/local-api.ts`).href);
const server = Bun.serve({hostname: "127.0.0.1", port: 0, fetch(request) {
  const status = Number(new URL(request.url).pathname.slice(1));
  return Response.json({marker: "SyntheticCoreAPI", method: request.method,
    contentType: request.headers.get("content-type")}, {status});
}});
const results: Array<{status: number; denial: boolean}> = [];
try {
  assert.equal(api.localOnlyApiCall, api.localApiCall);
  const result = await api.localApiCall(`${server.url}200`, {method: "POST", body: "{}"});
  assert.equal(result.marker, "SyntheticCoreAPI");
  assert.equal(result.method, "POST");
  assert.equal(result.contentType, "application/json");
  for (const status of [401, 403, 409, 503]) {
    let failure: unknown;
    try { await api.localApiCall(`${server.url}${status}`); } catch (error) { failure = error; }
    assert.ok(failure instanceof Error);
    assert.ok(failure.message.startsWith(`API error: ${status}`));
    assert.ok(typeof api.LocalAPIError === "function", "HTTP errors must expose their status");
    assert.ok(failure instanceof api.LocalAPIError);
    assert.ok('status' in failure);
    assert.equal(failure.status, status);
  }
  const core = await import(pathToFileURL(`${base}/src/lib/core-api.ts`).href);
  for (const status of [200, 401, 403, 409, 503]) {
    let denial = false;
    try { await core.coreApiCall(`${server.url}${status}`, () => { denial = true; }); }
    catch (error) { assert.ok(error instanceof api.LocalAPIError); }
    assert.equal(denial, status === 401 || status === 403);
    results.push({status, denial});
  }
  console.log(JSON.stringify({status: "PASS", actualHTTP: true, cases: results}));
} finally { server.stop(true); }
