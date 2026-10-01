// ABOUTME: Exercises native Observability Knowledge rendering from declared current sources.
// ABOUTME: Returns real native response bodies while keeping source maps isolated per request.
function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

const input: unknown = JSON.parse(await Bun.stdin.text());
if (!object(input) || !Array.isArray(input.requests)) throw new Error('Knowledge test requests are required');
const module: unknown = await import(process.argv[2]);
if (!object(module) || typeof module.renderKnowledgeView !== 'function') throw new Error('Native Knowledge rendering is required');
const results: unknown[] = [];
if (input.standalone === true) {
  if (typeof module.startObservability !== 'function' || typeof module.handleObservabilityRequest !== 'function') {
    throw new Error('Standalone native Knowledge control is unavailable');
  }
  module.startObservability({enabled: true});
}
for (const request of input.requests) {
  if (!object(request) || typeof request.path !== 'string' || !Array.isArray(request.sources)) {
    throw new Error('Knowledge test requests require a path and declared sources');
  }
  try {
    const response: unknown = input.standalone === true && typeof module.handleObservabilityRequest === 'function'
      ? await module.handleObservabilityRequest(new Request('http://127.0.0.1' + request.path))
      : module.renderKnowledgeView(request.sources, request.path);
    if (!(response instanceof Response)) throw new Error('Native Knowledge rendering did not return a response');
    results.push({status: response.status, body: await response.json()});
  } catch (error: unknown) {
    results.push({error: String(error)});
  }
}
process.stdout.write(JSON.stringify(results) + '\n');
