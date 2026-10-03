// ABOUTME: Drives real native LifeOS memory APIs in an isolated integration fixture.
// ABOUTME: Keeps sequential reviewer reads and writes in the same native process.

import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

const input: unknown = JSON.parse(await Bun.stdin.text());
if (!Array.isArray(input)) throw new Error("A native operation sequence is required");
const root = process.argv[2];
if (!root) throw new Error("A native installation root is required");
const system: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemorySystem.ts")).href);
const writer: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryWriter.ts")).href);
const retriever: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryRetriever.ts")).href);
const loader: unknown = await import(pathToFileURL(resolve(root, "hooks/LoadMemory.hook.ts")).href);
if (!object(system) || !object(writer) || !object(retriever)) throw new Error("Native exports are unavailable");
const results: unknown[] = [];
for (const operation of input) {
  if (!object(operation)) throw new Error("A native operation must be an object");
  if (operation.name === "add" && typeof system.add === "function") results.push(system.add(operation.item));
  else if (operation.name === "read" && typeof writer.read === "function") results.push(writer.read(operation.path));
  else if (operation.name === "set" && typeof writer.setEntries === "function") results.push(writer.setEntries(operation.path, operation.entries));
  else if (operation.name === "rank" && typeof retriever.getRelevantContext === "function") results.push(retriever.getRelevantContext(operation.query));
  else if (operation.name === "load" && object(loader) && typeof loader.run === "function") results.push(loader.run());
  else if (operation.name === "review_prompt") {
    const reviewer: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryReviewer.ts")).href);
    if (!object(reviewer) || typeof reviewer.buildReviewerUserPrompt !== "function" || typeof reviewer.readCurrentMemorySnapshot !== "function") {
      throw new Error("Native reviewer functions are unavailable");
    }
    results.push(reviewer.buildReviewerUserPrompt(operation.exchanges, reviewer.readCurrentMemorySnapshot()));
  }
  else throw new Error("Unknown native operation");
}
process.stdout.write(JSON.stringify(results) + "\n");
