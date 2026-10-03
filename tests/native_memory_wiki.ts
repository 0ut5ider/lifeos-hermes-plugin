// ABOUTME: Exercises the native wiki renderer with declared synthetic source text.
// ABOUTME: Keeps index, search, excerpts, bodies, backlinks, and graph in one process.
function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

const input: unknown = JSON.parse(await Bun.stdin.text());
if (!object(input) || !Array.isArray(input.requests)) throw new Error('Wiki test requests are required');
const module: unknown = await import(process.argv[2]);
if (!object(module) || typeof module.startWiki !== 'function' || typeof module.stopWiki !== 'function'
    || typeof module.handleWikiRequest !== 'function') throw new Error('Native wiki exports are required');
const results: unknown[] = [];
if (input.standalone === true) module.startWiki();
try {
  for (const request of input.requests) {
    if (!object(request) || typeof request.path !== 'string' || !Array.isArray(request.sources)
        || (request.method !== undefined && typeof request.method !== 'string')) {
      throw new Error('Wiki test requests require a path, sources, and an optional method');
    }
    const url = 'http://127.0.0.1' + request.path;
    try {
      const nativeRequest = new Request(url, { method: request.method ?? 'GET' });
      if (input.standalone !== true && typeof module.renderWikiView !== 'function') {
        throw new Error('Declared wiki rendering is unavailable');
      }
      const response: unknown = input.standalone === true
        ? await module.handleWikiRequest(nativeRequest, new URL(url).pathname)
        : await module.renderWikiView(request.sources, nativeRequest, new URL(url).pathname);
      if (!(response instanceof Response)) throw new Error('The native wiki did not return a response');
      results.push({ status: response.status, body: await response.json() });
    } catch (error: unknown) {
      results.push({ error: String(error) });
    }
  }
} finally {
  if (input.standalone === true) module.stopWiki();
}
process.stdout.write(JSON.stringify(results) + '\n');
