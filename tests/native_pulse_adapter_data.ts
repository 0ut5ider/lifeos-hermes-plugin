// ABOUTME: Executes real native PULSE data-plane reads and page publication.
// ABOUTME: Reports captured refusal without substituting a native operation result.
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

const input: unknown = JSON.parse(await Bun.stdin.text());
const root = process.argv[2];
if (!root || !object(input) || typeof input.action !== "string" || typeof input.id !== "string") {
  throw new Error("A fixture root and declared PULSE operation are required");
}
const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/lib/data-plane.ts")).href);
if (!object(module)) throw new Error("The actual native PULSE data module is unavailable");
try {
  let value: unknown;
  if (input.action === "read_page" && typeof module.readPage === "function") value = module.readPage(input.id);
  else if (input.action === "read_meta" && typeof module.readMeta === "function") value = module.readMeta(input.id);
  else if (input.action === "read_index" && typeof module.readIndex === "function") value = module.readIndex();
  else if (input.action === "write_page" && typeof module.writePage === "function") value = module.writePage(input.id, input.value);
  else throw new Error("Choose an available actual PULSE operation");
  console.log(JSON.stringify({ok: true, value: value ?? null}));
} catch (error: unknown) {
  console.log(JSON.stringify({ok: false, message: error instanceof Error ? error.message : String(error)}));
}
