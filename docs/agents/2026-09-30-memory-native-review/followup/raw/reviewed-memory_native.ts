// ABOUTME: Executes native LifeOS memory functions for an isolated governed operation.
// ABOUTME: Returns native validation and write results without starting a model or runtime.

import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

async function main(): Promise<void> {
  const root = process.argv[2];
  if (!root) throw new Error("An installed LifeOS root is required");
  const input: unknown = JSON.parse(await Bun.stdin.text());
  if (!object(input)) throw new Error("Native memory input must be an object");
  const system: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemorySystem.ts")).href);
  const writer: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryWriter.ts")).href);
  if (!object(system) || !object(writer)) throw new Error("Native memory exports are unavailable");
  let result: unknown;
  if (input.action === "rank") {
    const retriever: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryRetriever.ts")).href);
    if (!object(retriever) || retriever.SUPPLIED_CORPUS_API_VERSION !== 1 || typeof retriever.getRelevantContext !== "function") {
      throw new Error("The governed native retrieval capability is unavailable");
    }
    if (typeof input.query !== "string" || !Array.isArray(input.corpus)) throw new Error("Invalid retrieval input");
    const options = object(input.options) ? input.options : {topK: input.limit, excerptChars: 65536};
    result = retriever.getRelevantContext(input.query, {...options, corpus: input.corpus});
  } else if (input.action === "route") {
    const types: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryTypes.ts")).href);
    if (!object(types) || typeof types.resolveStoragePath !== "function") throw new Error("Native memory routing is unavailable");
    result = { path: types.resolveStoragePath(input.item) };
  } else if (input.action === "add" || input.action === "validate") {
    if (typeof system.sanitizeTypedItemForPersistence !== "function" || typeof system.add !== "function") {
      throw new Error("Native memory validation or add operation is unavailable");
    }
    const checked: unknown = system.sanitizeTypedItemForPersistence(input.item);
    if (!object(checked) || checked.ok !== true || input.action === "validate") result = checked;
    else result = system.add(checked.item);
  } else if (input.action === "read_hot") {
    if (typeof writer.read !== "function" || typeof input.path !== "string") throw new Error("Invalid hot-memory read");
    result = writer.read(input.path);
  } else if (input.action === "set_hot") {
    if (typeof writer.setEntries !== "function" || typeof input.path !== "string" || !Array.isArray(input.entries)
        || input.entries.some((entry: unknown) => typeof entry !== "string")) throw new Error("Invalid hot-memory curation");
    result = writer.setEntries(input.path, input.entries, { updatedBy: input.writer, allowDrastic: input.allowDrastic === true });
  } else {
    throw new Error("Unknown native memory operation");
  }
  process.stdout.write(JSON.stringify(result) + "\n");
}

main().catch((error: unknown) => {
  process.stderr.write(String(error) + "\n");
  process.exitCode = 1;
});
