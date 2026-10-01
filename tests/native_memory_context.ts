// ABOUTME: Exercises the native context builder repeatedly in one real process.
// ABOUTME: Accepts synthetic request contexts and reports results without log pollution.
import { createInterface } from "node:readline";
import { dirname, resolve } from "node:path";

const logs: unknown[][] = [];
console.log = (...args: unknown[]): void => { logs.push(args); };
const module = await import(process.argv[2]);
const access = await import(resolve(dirname(process.argv[2]), "../../TOOLS/lib/MemoryAccess.ts"));
for await (const line of createInterface({ input: process.stdin })) {
  const request = JSON.parse(line);
  if (request.context === null) delete process.env.LIFEOS_MEMORY_CONTEXT;
  else process.env.LIFEOS_MEMORY_CONTEXT = JSON.stringify(request.context);
  try {
    if (request.probe === true) {
      process.stdout.write(JSON.stringify({ access: access.canReadMemorySources() }) + "\n");
      continue;
    }
    const block = await module.buildLifeosContextBlock(request.query);
    process.stdout.write(JSON.stringify({ block, logs: logs.splice(0) }) + "\n");
  } catch (error: unknown) {
    process.stdout.write(JSON.stringify({ error: String(error), logs: logs.splice(0) }) + "\n");
  }
}
