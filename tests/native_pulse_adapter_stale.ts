// ABOUTME: Executes the actual native PULSE age and stale-state reader.
// ABOUTME: Captures refusal while preserving native missing-file semantics.
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

const root = process.argv[2];
if (!root) throw new Error("An actual synthetic PULSE root is required");
const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/lib/data-plane.ts")).href);
if (!object(module) || typeof module.isStale !== "function") throw new Error("The native stale reader is unavailable");
try {
  const result: unknown = module.isStale("synthetic", 24);
  console.log(JSON.stringify({ok: true, value: result}));
} catch (error: unknown) {
  console.log(JSON.stringify({ok: false, message: error instanceof Error ? error.message : String(error)}));
}
